"""
认证相关 API：
- GET  /api/v1/auth/config    OIDC 配置（前端用，无需登录）
- GET  /api/v1/auth/me        当前用户身份
- POST /api/v1/auth/dev-login 开发模式直连签发（仅当 ENABLE_AUTH=0 可用）
- GET  /api/v1/auth/users     管理员列出所有 user
- POST /api/v1/auth/grant     管理员授权资源给用户/角色
- DELETE /api/v1/auth/grant/{id} 撤销授权
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import (
    ENABLE_AUTH,
    AUTH_PROVIDER,
    AuthUser,
    get_current_user,
    require_permission,
)
from app.core.database import get_db


router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# SuperTokens 会话端点（T3，design §4.4 🛠R2）
# 实施裁定：不挂 ST 全局中间件——AuthMiddleware 纯 ASGI 先例（BaseHTTPMiddleware
# 断 SSE 流）；SDK 的 *_without_request_response 会话函数直接驱动，cookie 由本面手写。
# ---------------------------------------------------------------------------

_st_initialized = False


def _ensure_st_init() -> None:
    """supertokens-python 惰性初始化（仅登录签发/建号用，验签仍走自研 JWKS）。"""
    global _st_initialized
    if _st_initialized:
        return
    from supertokens_python import InputAppInfo, SupertokensConfig, init
    from supertokens_python.recipe import emailpassword, session

    init(
        supertokens_config=SupertokensConfig(
            connection_uri=os.environ.get("SUPERTOKENS_CONNECTION_URI", "http://127.0.0.1:13567"),
            api_key=os.environ.get("SUPERTOKENS_API_KEY") or None,
        ),
        app_info=InputAppInfo(
            app_name="tupu",
            api_domain=os.environ.get("TUPU_API_DOMAIN", "http://localhost:23000"),
            website_domain=os.environ.get("TUPU_WEBSITE_DOMAIN", "http://localhost:23000"),
        ),
        framework="fastapi",
        mode="asgi",
        recipe_list=[
            session.init(anti_csrf="NONE"),  # Bearer 头通道，无浏览器 SDK 的 CSRF 语义
            emailpassword.init(),
        ],
    )
    _st_initialized = True


def _token_pair(tokens) -> tuple:
    """get_all_session_tokens_dangerously 兼容面：0.29.2 返回 dict。"""
    if isinstance(tokens, dict):
        return tokens.get("accessToken") or tokens.get("access_token"), tokens.get("refreshToken") or tokens.get("refresh_token")
    return tokens.access_token, tokens.refresh_token


def _st_recipe_user_id(user_id: str):
    from supertokens_python.types import RecipeUserId

    return RecipeUserId(user_id)


def _set_st_cookies(response, access_token: str, refresh_token: str) -> None:
    """设计 §4.4：sAccessToken + sRefreshToken（HttpOnly）双 cookie——兼容 H5/SDK 通道。"""
    secure = os.environ.get("TUPU_HTTPS", "0") == "1"
    response.set_cookie("sAccessToken", access_token, httponly=True, samesite="lax", secure=secure, path="/")
    response.set_cookie("sRefreshToken", refresh_token, httponly=True, samesite="lax", secure=secure, path="/")


class SessionLoginRequest(BaseModel):
    email: str
    password: str


class SessionRefreshRequest(BaseModel):
    refresh_token: Optional[str] = None  # 缺省读 sRefreshToken cookie


@router.post("/session")
async def st_login(payload: SessionLoginRequest, response=None):
    """登录签发：ST SDK signin → 创建会话 → 返回 access_token + 用户镜像（🛠R2）。"""
    _ensure_st_init()
    from supertokens_python.recipe.emailpassword import asyncio as ep_asyncio
    from supertokens_python.recipe.emailpassword.interfaces import WrongCredentialsError
    from supertokens_python.recipe.session import asyncio as session_recipe

    result = await ep_asyncio.sign_in("", payload.email, payload.password)
    if isinstance(result, WrongCredentialsError):
        raise HTTPException(status_code=401, detail="邮箱或密码错误")

    s = await session_recipe.create_new_session_without_request_response(
        "", _st_recipe_user_id(result.user.id), disable_anti_csrf=True,
    )
    access_token, refresh_token = _token_pair(s.get_all_session_tokens_dangerously())

    from app.core.database import SessionLocal
    from app.core.auth import _upsert_user
    from app.models.auth import User as UserM

    email = None
    try:
        email = (result.user.emails or [None])[0]
    except AttributeError:
        pass
    db = SessionLocal()
    try:
        # 镜像用户名保护：admin 建号时已定 username——登录不改写（否则 email 前缀
        # 或 sub 会顶掉管理面用户名，e2e 实测）。仅新建镜像时才用 email 前缀。
        existing = db.query(UserM).filter(UserM.sub == result.user.id).first()
        preferred = existing.username if existing else (email.split("@")[0] if email else result.user.id)
        user = _upsert_user(db, {
            "sub": result.user.id,
            "email": email,
            "preferred_username": preferred,
        })
    finally:
        db.close()

    body = {"code": 200, "data": {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict(),
    }}
    from fastapi.responses import JSONResponse
    resp = JSONResponse(body)
    _set_st_cookies(resp, access_token, refresh_token)
    return resp


@router.post("/session/refresh")
async def st_refresh(request: Request, payload: Optional[SessionRefreshRequest] = None):
    """会话续期（🛠R2）：读 sRefreshToken cookie 或 body → SDK refresh → 新 access_token。"""
    _ensure_st_init()
    from supertokens_python.recipe.session import asyncio as session_recipe

    refresh_token = (payload.refresh_token if payload else None) or request.cookies.get("sRefreshToken")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="缺少 refresh token")
    try:
        s = await session_recipe.refresh_session_without_request_response(
            refresh_token, disable_anti_csrf=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"refresh 失败: {exc}") from exc
    access_token, refresh_token = _token_pair(s.get_all_session_tokens_dangerously())
    from fastapi.responses import JSONResponse
    resp = JSONResponse({"code": 200, "data": {"access_token": access_token}})
    _set_st_cookies(resp, access_token, refresh_token)
    return resp


@router.delete("/session")
async def st_logout(request: Request):
    """登出：凭 Bearer access token 撤销会话（🛠R2 revoke）。"""
    _ensure_st_init()
    from supertokens_python.recipe.session import asyncio as session_recipe

    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="缺少 Authorization: Bearer <token>")
    try:
        s = await session_recipe.get_session_without_request_response(auth_header[7:].strip())
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"会话无效: {exc}") from exc
    if s is None:
        raise HTTPException(status_code=401, detail="会话不存在")
    await session_recipe.revoke_session(s.get_handle())
    return {"code": 200, "data": {"revoked": s.get_handle()}}


@router.post("/dev-login")
def dev_login():
    """开发模式直连签发（仅 ENABLE_AUTH=0；M02 金标准对齐——spec §五端点缺失补实现）。
    变异锚点：ENABLE_AUTH 判定删除 → 生产可直连签发（安全洞）。
    ENABLE_AUTH=0 时返回 dev token + 匿名 admin 用户上下文（供开发脚本/调试工具链）；
    ENABLE_AUTH=1 时 403 自证（spec §九 dev-login 仅限开发）。"""
    if ENABLE_AUTH:
        raise HTTPException(status_code=403, detail="dev-login 仅限开发模式（ENABLE_AUTH=0）")
    # dev token：`dev.<用户名>` 形态（ENABLE_AUTH=0 下中间件短路不验签，作调试身份标记）
    import base64
    dev_user = os.environ.get("TUPU_DEV_USER", "anonymous")
    token = "dev." + base64.b64encode(dev_user.encode("utf-8")).decode("ascii")
    return {
        "code": 200,
        "data": {
            "token": token,
            "token_type": "Bearer",
            "user": {
                "sub": dev_user,
                "username": dev_user,
                "roles": ["admin"],   # 关闭 auth 时按 admin 处理（同 _ANONYMOUS 语义）
                "is_anonymous": True,
                "groups": [],
            },
        },
    }


@router.get("/config")
def auth_config():
    """身份层公开配置（T3 改 provider 口径——design §4.4）。

    provider=supertokens 时只暴露登录路径与 JWKS（不再暴露 Authentik OIDC 端点）；
    provider=authentik（双跑期缺省）保留 OIDC 字段供旧前端登录流。"""
    data: Dict[str, Any] = {"enable_auth": ENABLE_AUTH, "provider": AUTH_PROVIDER}
    if AUTH_PROVIDER == "supertokens":
        data.update({
            "login_path": "/api/v1/auth/session",
            "refresh_path": "/api/v1/auth/session/refresh",
        })
        return {"code": 200, "data": data}
    base = os.environ.get("AUTHENTIK_BASE_URL", "http://localhost:9100")
    issuer = os.environ.get("AUTHENTIK_ISSUER", f"{base}/application/o/tupu/")
    client_id = os.environ.get(
        "AUTHENTIK_CLIENT_ID", "VzFcIQaMB1b2ETPl7oMg4bAF6VS25BbzERyZTPQf"
    )
    redirect = os.environ.get(
        "AUTHENTIK_FRONTEND_REDIRECT", "http://localhost:3000/auth/callback"
    )
    data.update({
        "issuer": issuer,
        "client_id": client_id,
        "redirect_uri": redirect,
        "authorization_endpoint": f"{base}/application/o/authorize/",
        "token_endpoint": f"{base}/application/o/token/",
        "end_session_endpoint": f"{issuer}end-session/",
        "scopes": ["openid", "profile", "email", "groups"],
    })
    return {"code": 200, "data": data}


@router.get("/me")
def auth_me(request: Request):
    user = get_current_user(request)
    return {"code": 200, "data": user.to_dict()}


class GrantRequest(BaseModel):
    resource_type: str
    resource_id: str  # '*' 表示该 type 的所有资源
    principal_type: str  # 'user' | 'role'
    principal_id: str
    actions: List[str]
    expires_at: Optional[datetime] = None


@router.get("/check")
def check_resource(
    request: Request,
    resource_type: str,
    resource_id: str = "",
    action: str = "use",
):
    """⑥-2a A-4（附件四）：轻量判定面——前端守卫消费（管体验不管安全，spec D4.4）。

    返回 {allowed: bool}（不抛 403——判定本身即答案）。auth=0→匿名=admin→allowed=true。"""
    from app.core.auth import get_current_user, check_permission as _cp
    from app.core.database import SessionLocal as _SL
    user = get_current_user(request)
    db = _SL()
    try:
        allowed = _cp(db, user, resource_type, action, resource_id=resource_id)
    finally:
        db.close()
    return {"code": 200, "data": {"allowed": allowed}}


@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_permission("auth", "read")),
):
    from app.models.auth import User, UserRole

    users = db.query(User).all()
    out = []
    for u in users:
        roles = [
            ur.role_code
            for ur in db.query(UserRole).filter(UserRole.user_sub == u.sub).all()
        ]
        out.append({
            "sub": u.sub,
            "username": u.username,
            "email": u.email,
            "display_name": u.display_name,
            "roles": roles,
            "groups_snapshot": u.groups_snapshot,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
        })
    return {"code": 200, "data": out}


@router.post("/grant")
def grant_resource(
    payload: GrantRequest,
    request: Request,
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_permission("auth", "write")),
):
    from app.models.auth import ResourceACL

    if payload.principal_type not in ("user", "role"):
        raise HTTPException(status_code=400, detail="principal_type 必须是 user 或 role")
    if not payload.actions:
        raise HTTPException(status_code=400, detail="actions 不能为空")

    granter = _user.sub
    existing = (
        db.query(ResourceACL)
        .filter(
            ResourceACL.resource_type == payload.resource_type,
            ResourceACL.resource_id == payload.resource_id,
            ResourceACL.principal_type == payload.principal_type,
            ResourceACL.principal_id == payload.principal_id,
        )
        .first()
    )
    if existing:
        existing.actions = payload.actions
        existing.expires_at = payload.expires_at
        existing.granted_by = granter
        existing.granted_at = datetime.utcnow()
        db.commit()
        return {"code": 200, "data": {"id": existing.id, "updated": True}}

    row = ResourceACL(
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
        principal_type=payload.principal_type,
        principal_id=payload.principal_id,
        actions=payload.actions,
        granted_by=granter,
        expires_at=payload.expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"code": 200, "data": {"id": row.id, "created": True}}


@router.get("/grants")
def list_grants(
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_permission("auth", "read")),
):
    from app.models.auth import ResourceACL

    q = db.query(ResourceACL)
    if resource_type:
        q = q.filter(ResourceACL.resource_type == resource_type)
    if resource_id:
        q = q.filter(ResourceACL.resource_id == resource_id)
    rows = q.all()
    return {
        "code": 200,
        "data": [
            {
                "id": r.id,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "principal_type": r.principal_type,
                "principal_id": r.principal_id,
                "actions": r.actions,
                "granted_by": r.granted_by,
                "granted_at": r.granted_at.isoformat() if r.granted_at else None,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
            }
            for r in rows
        ],
    }


@router.delete("/grant/{grant_id}")
def revoke_grant(
    grant_id: int,
    db: Session = Depends(get_db),
    _user: AuthUser = Depends(require_permission("auth", "write")),
):
    from app.models.auth import ResourceACL

    row = db.query(ResourceACL).filter(ResourceACL.id == grant_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="授权不存在")
    db.delete(row)
    db.commit()
    return {"code": 200, "data": {"revoked": grant_id}}
