"""
权限核心：Authentik OIDC 验签 + RBAC + 资源级 ACL
==================================================

特性开关
--------
- ENABLE_AUTH=0（默认）：完全关闭权限校验，请求里塞匿名 user
- ENABLE_AUTH=1：所有非 _PUBLIC_PATHS 的请求都需要 Bearer JWT

使用方式
--------
1. 全局中间件 AuthMiddleware（在 main.py add_middleware）
   → 解析 Authorization header
   → 验签 JWT (RS256, jwks 缓存 10 分钟)
   → upsert auth_users 表
   → 把 user 塞进 request.state.user

2. 路由级权限装饰
   from app.core.auth import require_permission
   @router.get("/skills/{code}")
   def get_skill(code: str, _ = Depends(require_permission("skill", "read"))):
       ...

3. 资源级 ACL（资源 id 在路径里）
   @router.get("/skills/{code}")
   def get_skill(code: str, request: Request):
       check_resource_permission(request, "skill", code, "read")

权限判定优先级
--------------
1. 用户绑了 admin 角色 → 全部允许
2. ResourceACL(principal=user, resource_type, resource_id) 命中 actions
3. ResourceACL(principal=role, resource_type, resource_id) 命中（用户的任一角色）
4. ResourceACL(principal=role, resource_type, resource_id='*') 命中
5. Role.default_permissions 中 resource_type 包含 action

任何一条命中即放行。
"""
from __future__ import annotations

import os
import time
import threading
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import jwt
import requests
from fastapi import HTTPException, Request, Depends, status
from sqlalchemy.orm import Session

from .database import SessionLocal


# --------------------------------------------------------------------------- #
# 配置
# --------------------------------------------------------------------------- #


def _get_bool_env(name: str, default: bool = False) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "on")


ENABLE_AUTH = _get_bool_env("ENABLE_AUTH", False)
AUTHENTIK_ISSUER = os.environ.get(
    "AUTHENTIK_ISSUER", "http://localhost:9100/application/o/tupu/"
)
AUTHENTIK_JWKS_URL = os.environ.get(
    "AUTHENTIK_JWKS_URL", "http://localhost:9100/application/o/tupu/jwks/"
)
AUTHENTIK_AUDIENCE = os.environ.get(
    "AUTHENTIK_AUDIENCE", "VzFcIQaMB1b2ETPl7oMg4bAF6VS25BbzERyZTPQf"
)
GROUP_ROLE_MAP = {
    "tupu-admin": "admin",
    "tupu-operator": "operator",
    "tupu-viewer": "viewer",
}
# 不需要鉴权的路径（前缀匹配）
_PUBLIC_PATHS = (
    "/",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/auth/config",  # 暴露 OIDC discovery 给前端
    "/api/v1/auth/dev-login",  # 开发模式登录（仅 ENABLE_AUTH=0）
)
# /api/v1/auth/me 走"可选 token"逻辑：有就解析，无就匿名
_OPTIONAL_AUTH_PATHS = (
    "/api/v1/auth/me",
)


# --------------------------------------------------------------------------- #
# JWKS 缓存
# --------------------------------------------------------------------------- #


_JWKS_LOCK = threading.Lock()
_JWKS_CACHE: Dict[str, Any] = {"keys": [], "fetched_at": 0.0, "ttl": 600}


def _fetch_jwks() -> List[Dict[str, Any]]:
    with _JWKS_LOCK:
        now = time.time()
        if now - _JWKS_CACHE.get("fetched_at", 0) < _JWKS_CACHE["ttl"] and _JWKS_CACHE.get("keys"):
            return _JWKS_CACHE["keys"]
        try:
            r = requests.get(AUTHENTIK_JWKS_URL, timeout=5)
            r.raise_for_status()
            keys = r.json().get("keys") or []
            _JWKS_CACHE["keys"] = keys
            _JWKS_CACHE["fetched_at"] = now
            return keys
        except Exception as exc:
            # 拉不到时返回旧缓存（如果有）；都没有就抛
            if _JWKS_CACHE.get("keys"):
                return _JWKS_CACHE["keys"]
            raise RuntimeError(f"无法拉取 Authentik JWKS: {exc}") from exc


def _verify_jwt(token: str) -> Dict[str, Any]:
    """RS256 验签 + 校验 iss/aud/exp，返回 claims。失败抛 HTTPException 401。"""
    try:
        unverified = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"无效 JWT 头部: {exc}")

    kid = unverified.get("kid")
    keys = _fetch_jwks()
    pubkey = None
    for k in keys:
        if k.get("kid") == kid:
            pubkey = jwt.algorithms.RSAAlgorithm.from_jwk(k)
            break
    if pubkey is None:
        raise HTTPException(status_code=401, detail=f"JWKS 找不到 kid={kid}")

    try:
        claims = jwt.decode(
            token,
            pubkey,
            algorithms=["RS256"],
            audience=AUTHENTIK_AUDIENCE,
            issuer=AUTHENTIK_ISSUER,
            options={"verify_signature": True, "verify_aud": True, "verify_iss": True, "verify_exp": True},
        )
        # 补充：调 userinfo 端点拿完整 profile（access_token 默认不含 username/groups）
        try:
            userinfo_url = AUTHENTIK_ISSUER.rstrip("/").rsplit("/o/", 1)[0] + "/o/userinfo/"
            r = requests.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {token}"},
                timeout=5,
            )
            if r.status_code == 200:
                ui = r.json() or {}
                # 合并 (userinfo 字段不覆盖关键的 sub/iss/aud/exp)
                for k, v in ui.items():
                    if k not in claims and v is not None:
                        claims[k] = v
                # 显式覆盖几个常用字段
                for k in ("preferred_username", "email", "name", "groups", "nickname"):
                    if ui.get(k) is not None:
                        claims[k] = ui[k]
        except Exception:
            pass  # userinfo 拿不到不影响验签
        return claims
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 已过期")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="audience 不匹配")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="issuer 不匹配")
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"JWT 验证失败: {exc}")


# --------------------------------------------------------------------------- #
# 用户上下文
# --------------------------------------------------------------------------- #


class AuthUser:
    """请求级用户上下文（不持有 DB 句柄）。"""

    def __init__(
        self,
        sub: str,
        username: str,
        email: Optional[str],
        groups: List[str],
        roles: List[str],
        is_anonymous: bool = False,
    ) -> None:
        self.sub = sub
        self.username = username
        self.email = email
        self.groups = groups
        self.roles = roles
        self.is_anonymous = is_anonymous

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def is_admin(self) -> bool:
        return "admin" in self.roles

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sub": self.sub,
            "username": self.username,
            "email": self.email,
            "groups": self.groups,
            "roles": self.roles,
            "is_anonymous": self.is_anonymous,
        }


_ANONYMOUS = AuthUser(
    sub="anonymous",
    username="anonymous",
    email=None,
    groups=[],
    roles=["admin"],  # 关闭 auth 时按 admin 处理，向后兼容
    is_anonymous=True,
)


def _upsert_user(db: Session, claims: Dict[str, Any]) -> AuthUser:
    """根据 JWT claims upsert auth_users + 同步角色。"""
    from app.models.auth import User, UserRole, Role

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="JWT 缺少 sub")
    username = (
        claims.get("preferred_username")
        or claims.get("nickname")
        or claims.get("email")
        or sub
    )
    email = claims.get("email")
    groups = claims.get("groups") or []
    if isinstance(groups, str):
        groups = [groups]

    # upsert User
    user = db.query(User).filter(User.sub == sub).first()
    if user is None:
        user = User(
            sub=sub,
            username=username,
            email=email,
            display_name=claims.get("name") or username,
            groups_snapshot=groups,
            is_active=True,
            last_login_at=datetime.utcnow(),
        )
        db.add(user)
    else:
        user.username = username
        user.email = email
        user.display_name = claims.get("name") or username
        user.groups_snapshot = groups
        user.last_login_at = datetime.utcnow()

    # 同步角色：从 group claim 映射 + 写 user_roles
    target_roles = {GROUP_ROLE_MAP[g] for g in groups if g in GROUP_ROLE_MAP}
    if not target_roles:
        target_roles = {"viewer"}  # 兜底

    # 确保 Role 行存在
    for rcode in target_roles:
        if not db.query(Role).filter(Role.code == rcode).first():
            db.add(Role(
                code=rcode,
                name=rcode.title(),
                is_system=True,
                default_permissions=_DEFAULT_ROLE_PERMS.get(rcode, {}),
            ))

    # 同步 user_roles：删除多余、补充新增
    existing = {ur.role_code for ur in db.query(UserRole).filter(UserRole.user_sub == sub).all()}
    for to_add in target_roles - existing:
        db.add(UserRole(user_sub=sub, role_code=to_add, granted_by="system_oidc"))
    for to_del in existing - target_roles:
        db.query(UserRole).filter(UserRole.user_sub == sub, UserRole.role_code == to_del).delete()

    db.commit()

    return AuthUser(
        sub=sub,
        username=username,
        email=email,
        groups=groups,
        roles=sorted(target_roles),
        is_anonymous=False,
    )


_DEFAULT_ROLE_PERMS = {
    "admin": {"*": ["*"]},
    "operator": {
        "skill": ["read", "execute"],
        "workflow": ["read", "execute"],
        "data_source": ["read"],
        "query_attribute": ["read", "execute"],
        "query_entity": ["read", "execute"],
    },
    "viewer": {
        "skill": ["read"],
        "workflow": ["read"],
        "data_source": ["read"],
        "query_attribute": ["read"],
        "query_entity": ["read"],
    },
}


# --------------------------------------------------------------------------- #
# Middleware
# --------------------------------------------------------------------------- #


async def auth_middleware(request: Request, call_next):
    """全局认证中间件。"""
    # 短路：开关关闭 → 注入匿名 admin
    if not ENABLE_AUTH:
        request.state.user = _ANONYMOUS
        return await call_next(request)

    path = request.url.path
    # 公共路径放行
    if any(path == p or path.startswith(p + "/") for p in _PUBLIC_PATHS):
        request.state.user = _ANONYMOUS
        return await call_next(request)

    # OPTIONS 预检放行（CORS）
    if request.method == "OPTIONS":
        request.state.user = _ANONYMOUS
        return await call_next(request)

    auth_header = request.headers.get("authorization", "")

    # 可选 token 路径：有就解析，无就匿名
    is_optional = any(path == p or path.startswith(p + "/") for p in _OPTIONAL_AUTH_PATHS)
    if is_optional and not auth_header.lower().startswith("bearer "):
        request.state.user = _ANONYMOUS
        return await call_next(request)

    if not auth_header.lower().startswith("bearer "):
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=401,
            content={"detail": "缺少 Authorization: Bearer <token>"},
        )

    token = auth_header[7:].strip()
    try:
        claims = _verify_jwt(token)
    except HTTPException as exc:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    db = SessionLocal()
    try:
        user = _upsert_user(db, claims)
    finally:
        db.close()

    request.state.user = user
    return await call_next(request)


# --------------------------------------------------------------------------- #
# 依赖：get_current_user / require_permission / check_resource_permission
# --------------------------------------------------------------------------- #


def get_current_user(request: Request) -> AuthUser:
    user: Optional[AuthUser] = getattr(request.state, "user", None)
    if user is None:
        # 未走中间件（比如直接调函数测试）→ 返回匿名
        return _ANONYMOUS
    return user


def _has_permission_via_role_default(roles: List[str], resource_type: str, action: str) -> bool:
    for r in roles:
        perms = _DEFAULT_ROLE_PERMS.get(r) or {}
        if "*" in perms.get("*", []):
            return True
        rt_perms = perms.get(resource_type) or perms.get("*", [])
        if "*" in rt_perms or action in rt_perms:
            return True
    return False


def _has_permission_via_acl(
    db: Session,
    user: AuthUser,
    resource_type: str,
    resource_id: Optional[str],
    action: str,
) -> bool:
    from app.models.auth import ResourceACL

    q = db.query(ResourceACL).filter(ResourceACL.resource_type == resource_type)
    if resource_id is not None:
        q = q.filter(ResourceACL.resource_id.in_([resource_id, "*"]))
    rows = q.all()
    now = datetime.utcnow()

    for row in rows:
        if row.expires_at and row.expires_at < now:
            continue
        actions = row.actions or []
        if action not in actions and "*" not in actions:
            continue
        if row.principal_type == "user" and row.principal_id == user.sub:
            return True
        if row.principal_type == "role" and row.principal_id in user.roles:
            return True
    return False


def check_permission(
    db: Session,
    user: AuthUser,
    resource_type: str,
    action: str,
    resource_id: Optional[str] = None,
) -> bool:
    """完整权限判定（角色默认 + ACL）。admin 一票通过。"""
    if user.is_admin():
        return True
    if _has_permission_via_role_default(user.roles, resource_type, action):
        return True
    if _has_permission_via_acl(db, user, resource_type, resource_id, action):
        return True
    return False


def require_permission(resource_type: str, action: str):
    """FastAPI 依赖工厂：粗粒度（不依赖路径里的 resource_id）。"""

    def _dep(request: Request) -> AuthUser:
        if not ENABLE_AUTH:
            return get_current_user(request)
        user = get_current_user(request)
        if user.is_anonymous:
            raise HTTPException(status_code=401, detail="未登录")
        db = SessionLocal()
        try:
            ok = check_permission(db, user, resource_type, action, resource_id=None)
        finally:
            db.close()
        if not ok:
            raise HTTPException(
                status_code=403,
                detail=f"无权限：{resource_type}.{action}",
            )
        return user

    return _dep


def check_resource_permission(
    request: Request,
    resource_type: str,
    resource_id: str,
    action: str,
):
    """细粒度：检查 user 对具体 resource_id 的 action 权限。"""
    user = get_current_user(request)
    if not ENABLE_AUTH:
        return user
    if user.is_anonymous:
        raise HTTPException(status_code=401, detail="未登录")
    db = SessionLocal()
    try:
        ok = check_permission(db, user, resource_type, action, resource_id=resource_id)
    finally:
        db.close()
    if not ok:
        raise HTTPException(
            status_code=403,
            detail=f"无权限：{resource_type}({resource_id}).{action}",
        )
    return user


__all__ = [
    "ENABLE_AUTH",
    "AuthUser",
    "auth_middleware",
    "get_current_user",
    "require_permission",
    "check_resource_permission",
    "check_permission",
    "GROUP_ROLE_MAP",
    "_DEFAULT_ROLE_PERMS",
    "_verify_jwt",  # 单测用
]
