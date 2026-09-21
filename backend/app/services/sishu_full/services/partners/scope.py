"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from app.services.sishu_full.multi_user.models import CurrentUser, UserScope
from app.services.sishu_full.partners.config.paths import get_partner_workspace

PARTNER_USER_PREFIX = "partner_"


def partner_user_id(partner_id: str) -> str:
    return f"{PARTNER_USER_PREFIX}{partner_id}"


def is_partner_user_id(user_id: str) -> bool:
    """Whether *user_id* names a synthetic partner scope rather than a person."""
    return user_id.startswith(PARTNER_USER_PREFIX)


def partner_scope(partner_id: str) -> UserScope:
    workspace = get_partner_workspace(partner_id)
    return UserScope(
        kind="user",
        user_id=partner_user_id(partner_id),
        root=workspace.resolve(),
    )


def partner_user(partner_id: str, *, name: str = "") -> CurrentUser:
    scope = partner_scope(partner_id)
    return CurrentUser(
        id=scope.user_id,
        username=name or partner_id,
        role="user",
        scope=scope,
    )


__all__ = [
    "PARTNER_USER_PREFIX",
    "is_partner_user_id",
    "partner_scope",
    "partner_user",
    "partner_user_id",
]
