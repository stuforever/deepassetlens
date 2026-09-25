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

import hmac
import os
import json
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
# 权限重构T3（design §4.2）：身份提供方表驱动 + 双跑。AUTH_PROVIDER 只决定"登录签发
# 面向前端暴露的口径"；验签双跑期两路 token 都收（_verify_jwt 依 iss 提示排序候选）。
AUTH_PROVIDER = os.environ.get("AUTH_PROVIDER", "authentik")  # authentik|supertokens
SUPERTOKENS_JWKS_URL = os.environ.get(
    # 实施实测（T3）：Core 9.x 公开 JWKS = /.well-known/jwks.json（无需 api-key）；
    # design §4.2 初稿写的 /auth/jwt/jwks.json 是废弃路径（镜像内 "Unknown API" 实证）
    "SUPERTOKENS_JWKS_URL", "http://127.0.0.1:13567/.well-known/jwks.json"
)
_PROVIDERS = {
    "authentik": {"jwks": AUTHENTIK_JWKS_URL, "issuer": AUTHENTIK_ISSUER, "aud": AUTHENTIK_AUDIENCE},
    # ST access token 不校验 iss/aud——验签+exp 即可（design §4.2）
    "supertokens": {"jwks": SUPERTOKENS_JWKS_URL, "issuer": None, "aud": None},
}
# 🛠R6（v1.1）：GROUP_ROLE_MAP 整体退役——auth_user_roles 自 T3 起为唯一角色权威，
# 登录不再从 group claim 覆盖角色（双跑期管理页的角色编辑才不会被登录冲掉）。
# 不需要鉴权的路径（前缀匹配）
_PUBLIC_PATHS = (
    "/",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/v1/auth/config",  # 暴露身份层配置给前端
    "/api/v1/auth/dev-login",  # 开发模式登录（仅 ENABLE_AUTH=0）
    "/api/v1/auth/session",  # T3：ST 登录签发/续期（design §4.4）
)
# /api/v1/auth/me 走"可选 token"逻辑：有就解析，无就匿名
_OPTIONAL_AUTH_PATHS = (
    "/api/v1/auth/me",
)
# P3-a: MCP 内部服务身份路径（R1批后仅接受 Bearer TUPU_INTERNAL_TOKEN——
# X-Internal-Service header 兜底已废除，header 客户端完全可控）
_MCP_INTERNAL_PATHS = (
    "/mcp",
)
_INTERNAL_SERVICE_NAME = "tupu-agent"


# --------------------------------------------------------------------------- #
# JWKS 缓存（provider 分桶——design §4.2 🛠：双跑期 ST/Authentik 键互不串）
# --------------------------------------------------------------------------- #


_JWKS_LOCK = threading.Lock()
_JWKS_CACHE: Dict[str, Dict[str, Any]] = {
    p: {"keys": [], "fetched_at": 0.0, "ttl": 600} for p in _PROVIDERS
}


def _fetch_remote_jwks(url: str) -> List[Dict[str, Any]]:
    """远端 JWKS 拉取薄封装（测试 monkeypatch 点——请求出网逻辑收敛于此）。"""
    r = requests.get(url, timeout=5)
    r.raise_for_status()
    return r.json().get("keys") or []


def _fetch_jwks(provider: str) -> List[Dict[str, Any]]:
    with _JWKS_LOCK:
        bucket = _JWKS_CACHE.setdefault(provider, {"keys": [], "fetched_at": 0.0, "ttl": 600})
        now = time.time()
        if now - bucket.get("fetched_at", 0) < bucket["ttl"] and bucket.get("keys"):
            return bucket["keys"]
        try:
            keys = _fetch_remote_jwks(_PROVIDERS[provider]["jwks"])
            bucket["keys"] = keys
            bucket["fetched_at"] = now
            return keys
        except Exception as exc:
            # 拉不到时返回旧缓存（如果有）；都没有就抛
            if bucket.get("keys"):
                return bucket["keys"]
            raise RuntimeError(f"无法拉取 {provider} JWKS: {exc}") from exc


def _verify_provider_jwt(token: str, provider: str) -> Dict[str, Any]:
    """单 provider 验签：RS256 + kid 匹配；iss/aud 仅 authentik 桶校验（ST 无 iss/aud）。"""
    p = _PROVIDERS[provider]
    if provider == "supertokens":
        # ST 通道不校验 iss/aud，但拒绝 Authentik 签发方的 iss——否则双跑期
        # Authentik 签发、aud 校验失败的令牌会经宽松 ST 通道漏过（M02 wrong-aud
        # 用例实证）。ST 自身 JWT 的 iss = api_domain + "/auth"（实施实测），
        # 形态任意，故只精确拒 Authentik issuer。
        unverified_iss = jwt.decode(token, options={"verify_signature": False}).get("iss")
        if unverified_iss is not None and unverified_iss == AUTHENTIK_ISSUER:
            raise jwt.PyJWTError(f"非 ST 签发令牌（iss={unverified_iss}）")
    kid = jwt.get_unverified_header(token).get("kid")
    pubkey = None
    for k in _fetch_jwks(provider):
        if k.get("kid") == kid:
            pubkey = jwt.algorithms.RSAAlgorithm.from_jwk(k)
            break
    if pubkey is None:
        raise jwt.PyJWTError(f"{provider} JWKS 找不到 kid={kid}")

    options = {"verify_signature": True, "verify_exp": True,
               "verify_aud": bool(p["aud"]), "verify_iss": bool(p["issuer"])}
    kwargs: Dict[str, Any] = {}
    if p["aud"]:
        kwargs["audience"] = p["aud"]
    if p["issuer"]:
        kwargs["issuer"] = p["issuer"]
    return jwt.decode(token, pubkey, algorithms=["RS256"], options=options, **kwargs)


def _verify_jwt(token: str) -> Dict[str, Any]:
    """双跑验签入口（design §4.2）：按未验签 iss 提示排序候选（ST → Authentik 为先），
    任一 provider 通过即放行；两路皆败 401。失败原因不外泄（防探测）。"""
    try:
        jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"无效 JWT 头部: {exc}")
    try:
        iss = jwt.decode(token, options={"verify_signature": False}).get("iss")
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"无效 JWT 载荷: {exc}")

    if iss is None or "api.supertokens.io" in iss or "supertokens" in iss:
        candidates = ["supertokens", "authentik"]
    elif iss == AUTHENTIK_ISSUER:
        candidates = ["authentik", "supertokens"]
    else:
        candidates = ["supertokens", "authentik"]  # 未知 iss：两路都试，全败即 401

    last_error: Optional[Exception] = None
    for provider in candidates:
        try:
            claims = _verify_provider_jwt(token, provider)
            # Authentik 路径补充：调 userinfo 拿完整 profile（access_token 默认不含
            # username/groups）；ST token 无 userinfo 面，跳过。
            if provider == "authentik":
                try:
                    userinfo_url = AUTHENTIK_ISSUER.rstrip("/").rsplit("/o/", 1)[0] + "/o/userinfo/"
                    r = requests.get(
                        userinfo_url,
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=5,
                    )
                    if r.status_code == 200:
                        ui = r.json() or {}
                        for k, v in ui.items():
                            if k not in claims and v is not None:
                                claims[k] = v
                        for k in ("preferred_username", "email", "name", "groups", "nickname"):
                            if ui.get(k) is not None:
                                claims[k] = ui[k]
                except Exception:
                    pass  # userinfo 拿不到不影响验签
            return claims
        except HTTPException:
            raise
        except jwt.ExpiredSignatureError as exc:
            raise HTTPException(status_code=401, detail="Token 已过期") from exc
        except jwt.InvalidAudienceError as exc:
            # aud/iss 定错属终判——authentik 提示令牌 aud 不匹配无需再试 ST
            # （ST 通道已拒他方 iss），保留原错误语义（M02 契约）
            raise HTTPException(status_code=401, detail="audience 不匹配") from exc
        except jwt.InvalidIssuerError as exc:
            raise HTTPException(status_code=401, detail="issuer 不匹配") from exc
        except jwt.PyJWTError as exc:
            last_error = exc
            continue
        except RuntimeError as exc:
            last_error = exc
            continue
    raise HTTPException(status_code=401, detail=f"JWT 验证失败: {last_error}")


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
    """根据 JWT claims upsert auth_users（T3 重写——design §4.3，🛠R3/R6/R12）。

    - 匹配顺序：sub → legacy_sub → email（email 多行=查重跳过+告警，防静默错绑）；
    - email/legacy_sub 命中 → 同事务 sub 迁移（旧值写 legacy_sub，user_roles 与
      principal_type='user' 的 ACL 引用同步）；
    - 角色权威在库：登录不再从 group claim 覆盖（🛠R6），无角色兜底 viewer。
    """
    import logging

    logger = logging.getLogger("tupu.auth")

    from app.models.auth import ResourceACL, Role, User, UserRole

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

    user = db.query(User).filter(User.sub == sub).first()
    if user is None:
        # 🛠R3：sub 未命中 → legacy_sub → email（唯一行才迁）兜底匹配
        legacy = db.query(User).filter(User.legacy_sub == sub).first() if sub else None
        if legacy is None and email:
            email_rows = db.query(User).filter(User.email == email).all()
            if len(email_rows) == 1:
                legacy = email_rows[0]
            elif len(email_rows) > 1:
                logger.warning(
                    "[auth] 同 email %s 命中 %d 行，跳过 sub 迁移（新建镜像行），"
                    "请人工裁定归属（🛠R12）", email, len(email_rows),
                )
        if legacy is not None and legacy.sub != sub:
            old_sub = legacy.sub
            # 复制式迁移（design §4.3 同事务三表）：auth_user_roles.user_sub 的 FK
            # 只有 ON DELETE CASCADE、无 ON UPDATE CASCADE——父行原位改 PK 会被
            # MySQL 1451 拒绝，故「插新行 → 搬子表 → 删旧行」：
            new_row = User(
                sub=sub,
                legacy_sub=old_sub,
                username=username,
                email=email,
                display_name=claims.get("name") or username,
                groups_snapshot=groups,
                is_active=legacy.is_active,
                last_login_at=datetime.utcnow(),
                created_at=legacy.created_at,
            )
            db.add(new_row)
            db.flush()  # 新父行先落（子表 FK 目标才存在）
            db.query(UserRole).filter(UserRole.user_sub == old_sub).update(
                {"user_sub": sub}, synchronize_session=False)
            db.query(ResourceACL).filter(
                ResourceACL.principal_type == "user",
                ResourceACL.principal_id == old_sub).update(
                {"principal_id": sub}, synchronize_session=False)
            db.delete(legacy)
            db.commit()
            roles = sorted({ur.role_code for ur in
                            db.query(UserRole).filter(UserRole.user_sub == sub).all()})
            return AuthUser(sub=sub, username=username, email=email,
                            groups=groups, roles=roles, is_anonymous=False)

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
        # T3 实测修复：ST access token 的 JWT claims 只带 sub/exp——**缺字段不回填
        # 缺省值**（原实现 preferred_username 或 email or sub 恒真，每请求把管理面
        # 用户名改成 sub、email 清空）。仅在 claims 真携带时更新。
        if claims.get("preferred_username"):
            user.username = claims["preferred_username"]
        if email:
            user.email = email
        if claims.get("name"):
            user.display_name = claims["name"]
        user.groups_snapshot = groups or user.groups_snapshot
        user.last_login_at = datetime.utcnow()

    # 🛠R6：group-claim 角色覆盖退役——角色权威在 auth_user_roles，登录只读不写；
    # 无任何角色的用户兜底 viewer（语义保留）。
    roles = {ur.role_code for ur in db.query(UserRole).filter(UserRole.user_sub == sub).all()}
    if not roles:
        roles = {"viewer"}
        if not db.query(Role).filter(Role.code == "viewer").first():
            db.add(Role(code="viewer", name="Viewer", is_system=True,
                        default_permissions=_DEFAULT_ROLE_PERMS.get("viewer", {})))
        db.add(UserRole(user_sub=sub, role_code="viewer", granted_by="system_fallback"))

    db.commit()

    # T3 实测修复：展示名以 DB 行为准（ST JWT claims 无 preferred_username/email，
    # 用 claims 链会把管理面用户名顶成 sub、email 顶成 None——/auth/me 实测）
    return AuthUser(
        sub=sub,
        username=user.username or username,
        email=user.email,
        groups=groups,
        roles=sorted(roles),
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


def _path_matches(path: str, prefixes) -> bool:
    return any(path == p or path.startswith(p + "/") for p in prefixes)


def _read_auth_header(scope) -> str:
    for k, v in scope.get("headers") or []:
        if k == b"authorization":
            return v.decode("latin-1")
    return ""


async def _send_json_response(send, status_code: int, detail: str):
    """纯 ASGI 方式直接写一条 JSON 响应（不走 app，不经过 body_iterator）。"""
    body = json.dumps({"detail": detail}, ensure_ascii=False).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status_code,
        "headers": [
            (b"content-type", b"application/json; charset=utf-8"),
            (b"content-length", str(len(body)).encode("latin-1")),
        ],
    })
    await send({"type": "http.response.body", "body": body, "more_body": False})


class AuthMiddleware:
    """纯 ASGI 鉴权中间件。

    为什么不用 BaseHTTPMiddleware：Starlette 的 BaseHTTPMiddleware 会把响应 body
    经 body_iterator 二次封装，对 SSE StreamingResponse 有已知断言失败
    (AssertionError: Unexpected message: http.response.start content-length: 0)，
    表现为前端走 dev proxy 取流时 agent 立刻"卡住"。纯 ASGI 直接透传 send，
    StreamingResponse 的 http.response.start + 分片 http.response.body 原样下发，
    流不受影响。鉴权逻辑（ENABLE_AUTH=0 注入匿名 / 公共路径 / OPTIONS / JWT 验签 /
    401）全部保留，只是换了一层壳。
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # 非 http（lifespan / websocket）直接透传
        if scope.get("type") != "http":
            return await self.app(scope, receive, send)

        # FastAPI/Starlette 从 scope["state"] 读 request.state
        if "state" not in scope:
            scope["state"] = {}
        state = scope["state"]

        path = scope.get("path", "")
        method = scope.get("method", "")

        # 短路：关闭鉴权 / 公共路径 / OPTIONS 预检 -> 注入匿名，透传 send
        if (not ENABLE_AUTH) or _path_matches(path, _PUBLIC_PATHS) or method == "OPTIONS":
            state["user"] = _ANONYMOUS
            return await self.app(scope, receive, send)

        auth_header = _read_auth_header(scope)

        # P3-a: MCP 内部服务身份校验（ENABLE_AUTH=1 时，/mcp 路径仅接受 Bearer 内部 token）
        if _path_matches(path, _MCP_INTERNAL_PATHS):
            _internal_token = os.getenv("TUPU_INTERNAL_TOKEN", "")
            # R1批（R#1 critical）：X-Internal-Service 兜底移除——该 header 客户端完全可控
            # 且服务名是公开常量，无 token 配置时兜底=鉴权绕过提权 admin。内部调用方
            # （tupu_deepagent）与主进程同源读 env（main.py 启动自动生成 token 注入），
            # Bearer 通道始终可用；外部客户端无 token → 一律 401。
            if _internal_token and auth_header.lower().startswith("bearer ") \
                    and hmac.compare_digest(auth_header[7:].strip(), _internal_token):
                # Minor（R3批）：token 比较改常量时间——直等 == 存在理论时序侧信道
                state["user"] = _ANONYMOUS
                return await self.app(scope, receive, send)
            await _send_json_response(send, 401, "MCP 端点需 Bearer 内部 token（X-Internal-Service 兜底已废除）")
            return

        # 可选 token 路径：有就解析，无就匿名
        is_optional = _path_matches(path, _OPTIONAL_AUTH_PATHS)
        if is_optional and not auth_header.lower().startswith("bearer "):
            state["user"] = _ANONYMOUS
            return await self.app(scope, receive, send)

        if not auth_header.lower().startswith("bearer "):
            await _send_json_response(send, 401, "缺少 Authorization: Bearer <token>")
            return

        token = auth_header[7:].strip()
        try:
            claims = _verify_jwt(token)
        except HTTPException as exc:
            await _send_json_response(send, exc.status_code, str(exc.detail))
            return

        db = SessionLocal()
        try:
            user = _upsert_user(db, claims)
        finally:
            db.close()

        state["user"] = user
        return await self.app(scope, receive, send)


# --------------------------------------------------------------------------- #
# 依赖：get_current_user / require_permission / check_resource_permission
# --------------------------------------------------------------------------- #


def get_current_user(request: Request) -> AuthUser:
    # request=None（直调默认形参）与未走中间件同归匿名——AttributeError 防护
    user: Optional[AuthUser] = getattr(request.state, "user", None) if request is not None else None
    if user is None:
        # 未走中间件（比如直接调函数测试）→ 返回匿名
        return _ANONYMOUS
    return user


def _has_permission_via_role_default(
    db: Optional[Session], roles: List[str], resource_type: str, action: str
) -> bool:
    # 权限重构 T2（验收 #4 地基）：DB auth_roles.default_permissions 行权威——
    # 角色有 DB 行（含显式 {}）则整行取代静态映射，矩阵编辑器的收缩/扩张都生效；
    # 无 DB 行回退静态 _DEFAULT_ROLE_PERMS（兼容未播种角色）。🛠 design §6.1
    # "auth_roles.default_permissions 的 tool:execute" 也以此为前提。
    db_rows: Dict[str, Optional[dict]] = {}
    if db is not None and roles:
        from app.models.auth import Role as RoleModel

        for row in db.query(RoleModel).filter(RoleModel.code.in_(roles)).all():
            db_rows[row.code] = row.default_permissions
    for r in roles:
        if r in db_rows and db_rows[r] is not None:
            perms = db_rows[r] or {}
        else:
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
    if _has_permission_via_role_default(db, user.roles, resource_type, action):
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
    "AuthMiddleware",
    "get_current_user",
    "require_permission",
    "check_resource_permission",
    "check_permission",
    "GROUP_ROLE_MAP",
    "_DEFAULT_ROLE_PERMS",
    "_verify_jwt",  # 单测用
]
