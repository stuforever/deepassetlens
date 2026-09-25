"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Any

from .models import CurrentUser
from .paths import local_admin_user, scope_for_user

_current_user: ContextVar[CurrentUser | None] = ContextVar("deeptutor_current_user", default=None)


def set_current_user(user: CurrentUser) -> Token[CurrentUser | None]:
    return _current_user.set(user)


def reset_current_user(token: Token[CurrentUser | None]) -> None:
    _current_user.reset(token)


def get_current_user() -> CurrentUser:
    return _current_user.get() or local_admin_user()


def get_current_user_or_none() -> CurrentUser | None:
    return _current_user.get()


def user_from_token_payload(payload: Any | None) -> CurrentUser:
    if payload is None:
        return local_admin_user()
    # 权限重构T6.3（design §7 批2）：平台载荷（.sub/.roles——PlatformBridgePayload/
    # AuthUser）与 vendor TokenPayload（.user_id/.role）双形态。slug=username——
    # 分目录键随管理面用户名（唯一性由建号 409 保证），vendor 旧 id 目录孤儿化登记。
    sub = str(getattr(payload, "sub", "") or "")
    username = str(getattr(payload, "username", "") or "local")
    if sub:
        # 平台形态：admin 角色判定走 roles 集；slug=username
        roles = list(getattr(payload, "roles", []) or [])
        role = "admin" if "admin" in roles else str(getattr(payload, "role", "user") or "user")
        user_id = username
    else:
        user_id = str(getattr(payload, "user_id", "") or "")
        role = str(getattr(payload, "role", "user") or "user")
        if not user_id:
            user_id = "local-admin" if role == "admin" and username == "local" else username
    if role not in {"admin", "user"}:
        role = "user"
    if not user_id:
        user_id = "local-admin" if role == "admin" and username == "local" else username
    return CurrentUser(
        id=user_id,
        username=username,
        role=role,  # type: ignore[arg-type]
        scope=scope_for_user(user_id, is_admin=role == "admin"),
    )
