# -*- coding: utf-8 -*-
"""权限重构T6批3（design §7 批3）：平台→vendor 身份桥——vendor auth 清零后的唯一存活面。

原 routers/auth.py 的桥接层整体迁出至此；vendor JWT 登录/用户存储面（services/auth.py
+ users.json）随批3 物理删除。身份源=平台 AuthMiddleware（auth=1）或本地管理员
（ENABLE_AUTH=0 开发态语义，design §7「local-admin 语义保留」，目录不漂移）。

HTTP 依赖用法：platform_require_auth / platform_require_admin（T6.1 换轨执法位）、
require_auth / require_admin（vendor 装配表原依赖名——api/main.py 与 multi_user
router 沿用）；WS 用法：ws_require_auth（失败返回 ws_auth_failed，调用方须立即
return——连接已被 4001 关闭）。

⚠ 不变量（#481）：每个鉴权入口必须先 _install_current_user 再进 handler——
缺装会让 get_current_path_service() 回落 admin 工作区（静默分目录根因）。
"""
from __future__ import annotations

import logging
from contextvars import Token as _CtxToken
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    status,
)
from fastapi.responses import HTMLResponse

from app.services.sishu_full.multi_user.context import set_current_user, user_from_token_payload
from app.services.sishu_full.multi_user.models import LOCAL_ADMIN_ID, LOCAL_ADMIN_USERNAME
from app.services.sishu_full.multi_user.paths import local_admin_user

logger = logging.getLogger(__name__)


def _platform_enabled() -> bool:
    """平台 ENABLE_AUTH（core.auth 同源；懒取避免权限判定路径反向依赖重导入链）。"""
    from app.core.auth import ENABLE_AUTH

    return bool(ENABLE_AUTH)


def _install_current_user(payload: Any | None) -> _CtxToken:
    """Install the request-local current-user ContextVar from an auth result.

    ``payload is None`` means "no JWT was required"（auth=0）and resolves to the
    local admin user; a platform payload resolves through ``user_from_token_payload``
    （T6.3 双形态：.sub/.roles 平台侧优先，slug=username）。

    Returns the ContextVar reset token. HTTP callers ignore it; WebSocket callers
    keep it and call ``reset_current_user`` in their ``finally`` block.
    """
    user = local_admin_user() if payload is None else user_from_token_payload(payload)
    return set_current_user(user)


class PlatformBridgePayload:
    """平台 AuthUser → vendor 兼容载荷。attr 双形态（.sub/.roles 平台侧 +
    .user_id/.role vendor 侧），user_from_token_payload 按 T6.3 双形态消费。"""

    def __init__(self, platform_user) -> None:
        self.sub = platform_user.sub
        self.roles = list(getattr(platform_user, "roles", []) or [])
        self.user_id = platform_user.sub
        self.username = platform_user.username
        self.role = "admin" if "admin" in self.roles else "user"
        self.email = getattr(platform_user, "email", None)


class LocalAdminPayload:
    """auth=0 合成管理员载荷（原 _local_admin_token_payload；vendor TokenPayload
    随 services/auth.py 退役）。user_from_token_payload 走 vendor 分支解析出
    local-admin 身份（role=admin + username=local → id=local-admin）。"""

    username = LOCAL_ADMIN_USERNAME
    role = "admin"
    user_id = LOCAL_ADMIN_ID
    sub = ""


def _platform_state_user(request: Request | None):
    """平台 AuthMiddleware 注入的 request.state.user（非匿名才有效）。"""
    if request is None:
        return None
    u = getattr(request.state, "user", None)
    return u if (u is not None and not getattr(u, "is_anonymous", False)) else None


def _platform_payload_from_token(token: str) -> PlatformBridgePayload | None:
    """裸平台 JWT（无中间件直连场景：vendor 独立模式/SSE 静态包装）验签 → 桥载荷。"""
    try:
        from app.core.auth import _upsert_user as _plat_upsert
        from app.core.auth import _verify_jwt as _plat_verify
        from app.core.database import SessionLocal as _SL

        claims = _plat_verify(token)
        _db = _SL()
        try:
            _au = _plat_upsert(_db, claims)
        finally:
            _db.close()
        return PlatformBridgePayload(_au)
    except Exception:
        return None


async def platform_require_auth(request: Request = None):
    """T6.1 换轨依赖（_auth 族）：require_expert("use","sishu") 执法 + vendor
    ContextVar 桥（path_service 分目录语义不变）。
    auth=0（匿名）→ _install_current_user(None)——vendor local-admin 语义原样保留，
    目录不漂移。"""
    from app.services.expert_auth import require_expert

    user = require_expert("use", "sishu")(request) if request is not None else None
    if user is None or getattr(user, "is_anonymous", False):
        _install_current_user(None)
        return None
    payload = PlatformBridgePayload(user)
    _install_current_user(payload)
    return payload


async def platform_require_admin(request: Request = None):
    """T6.1 换轨依赖（_admin 族）：require_permission("sishu","manage") 执法 + 桥。
    auth=0 匿名 → local-admin 语义（同 platform_require_auth）。"""
    from app.core.auth import require_permission

    user = require_permission("sishu", "manage")(request) if request is not None else None
    if user is None or getattr(user, "is_anonymous", False):
        _install_current_user(None)
        return None
    payload = PlatformBridgePayload(user)
    _install_current_user(payload)
    return payload


async def require_auth(request: Request = None) -> PlatformBridgePayload | None:
    """鉴权依赖（vendor 装配表原依赖名，api/main.py `_auth` 族 + multi_user router）。

    批3 起唯一身份源=平台：中间件已验签（request.state.user）→ 桥载荷；裸平台
    Bearer → 验签桥接；auth=0 → local-admin。vendor JWT 流随 services/auth.py
    退役（批3 物理删除）。

    从 request 手工取 Authorization 头而非 Header() 标注——本函数同时被
    _AuthedStatic 以构造 Request 直调（无 FastAPI 依赖注入），Header() 标注在
    直调下会落 Marker 对象导致误判。
    """
    plat = _platform_state_user(request)
    if plat is not None:
        payload = PlatformBridgePayload(plat)
        _install_current_user(payload)
        return payload

    if not _platform_enabled():
        _install_current_user(None)
        return None

    authorization = request.headers.get("Authorization") if request is not None else None
    token = None
    if authorization:
        parts = authorization.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip() or None
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _platform_payload_from_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    _install_current_user(payload)
    return payload


class _WsAuthFailed:
    """Sentinel: ws_require_auth failed and closed the WebSocket."""


ws_auth_failed: _WsAuthFailed = _WsAuthFailed()


async def ws_require_auth(ws: WebSocket) -> _CtxToken | _WsAuthFailed:
    """Authenticate a WebSocket connection and set the user ContextVar.

    Must be called **before** ``ws.accept()`` so the server can reject
    unauthenticated upgrades cleanly.

    Returns a ContextVar reset token on success, or ``ws_auth_failed``
    on failure (the WebSocket is already closed — the caller should
    ``return`` immediately).

    Usage::

        user_token = await ws_require_auth(ws)
        if user_token is ws_auth_failed:
            return
        await ws.accept()
        try:
            ...
        finally:
            reset_current_user(user_token)
    """
    if not _platform_enabled():
        return _install_current_user(None)

    # T6 批1 WS 口径：?token= 携平台 Bearer（vendor dt_token cookie 随 vendor
    # login 面退役）；验签失败仍 4001 close——design §7 批1。
    token = ws.query_params.get("token")
    if token:
        payload = _platform_payload_from_token(token)
        if payload is not None:
            return _install_current_user(payload)
    await ws.close(code=4001)
    return ws_auth_failed


async def require_admin(
    payload: PlatformBridgePayload | None = Depends(require_auth),
):
    """管理员依赖（vendor 装配表原依赖名）。auth=0 → 合成 admin；auth=1 非管理员 403。"""
    if not _platform_enabled():
        return LocalAdminPayload()

    if payload is None or payload.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return payload


# ---------------------------------------------------------------------------
# Codex OAuth 回调（vendor settings/providers/openai-codex 流的投递端点）
# ---------------------------------------------------------------------------

codex_callback_router = APIRouter()


@codex_callback_router.get("/openai-codex/callback")
async def receive_codex_oauth_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> HTMLResponse:
    """openai-codex OAuth 浏览器回跳投递点（同路径原样迁移自 routers/auth.py）。

    主投递路径是 codex_auth service 自起的本地监听（service.py redirect_uri=
    localhost:{port}/auth/callback）；本端点为后端同域回跳的兜底面。"""
    from app.services.sishu_full.services.codex_auth.contracts import CodexAuthError
    from app.services.sishu_full.services.codex_auth.service import deliver_codex_oauth_callback

    headers = {"Cache-Control": "no-store"}
    try:
        callback_state = state if len(request.query_params.getlist("state")) == 1 else None
        await deliver_codex_oauth_callback(code, callback_state, error)
    except CodexAuthError as exc:
        return HTMLResponse(
            (
                "<!doctype html><title>DeepTutor Codex</title>"
                "<p>Authentication could not be received. Return to DeepTutor and try again.</p>"
            ),
            status_code=exc.http_status,
            headers=headers,
        )
    return HTMLResponse(
        (
            "<!doctype html><title>DeepTutor Codex</title>"
            "<p>Authentication received. You can return to DeepTutor.</p>"
        ),
        headers=headers,
    )


__all__ = [
    "LocalAdminPayload",
    "PlatformBridgePayload",
    "codex_callback_router",
    "platform_require_admin",
    "platform_require_auth",
    "require_admin",
    "require_auth",
    "ws_auth_failed",
    "ws_require_auth",
]
