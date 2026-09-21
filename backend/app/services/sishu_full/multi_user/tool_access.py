"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from .context import get_current_user
from .grants import load_grant


def _current_grant() -> dict | None:
    """The current user's grant, or ``None`` when unrestricted (admin)."""
    user = get_current_user()
    if user.is_admin:
        return None
    return load_grant(user.id)


def allowed_optional_tools() -> set[str] | None:
    """Whitelist of user-toggleable tool names, ``None`` = unrestricted."""
    grant = _current_grant()
    if grant is None:
        return None
    value = grant.get("enabled_tools")
    if value is None:
        return None
    return {str(name) for name in value}


def allowed_mcp_tools() -> set[str] | None:
    """Whitelist of MCP (deferred) tool names.

    ``None`` means unrestricted and is reserved for administrators. Real
    non-admin users fail closed when the grant omits ``mcp_tools`` so a chat
    turn cannot discover or load deployment-wide MCP host tools until an admin
    explicitly grants the tool names.
    """
    grant = _current_grant()
    if grant is None:
        return None
    value = grant.get("mcp_tools")
    if value is None:
        return set()
    return {str(name) for name in value}


def allowed_cli_apps() -> set[str] | None:
    """Whitelist of installed CLI app ids this caller may invoke.

    ``None`` means unrestricted and is reserved for administrators. Every other
    account fails closed when the grant omits ``cli_apps``: an installed app is
    third-party code, and the deployment installing one is not the same decision
    as every account being able to run it.
    """
    grant = _current_grant()
    if grant is None:
        return None
    value = grant.get("cli_apps")
    if value is None:
        return set()
    return {str(name) for name in value}


def exec_override() -> bool | None:
    """Per-user exec override: ``None`` follows the deployment policy."""
    grant = _current_grant()
    if grant is None:
        return None
    value = grant.get("exec_enabled")
    return value if isinstance(value, bool) else None


def combine_whitelists(caller: set[str] | None, user: set[str] | None) -> set[str] | None:
    """Intersect two optional whitelists; ``None`` = unrestricted."""
    if caller is None:
        return user
    if user is None:
        return caller
    return caller & user


__all__ = [
    "allowed_cli_apps",
    "allowed_mcp_tools",
    "allowed_optional_tools",
    "combine_whitelists",
    "exec_override",
]
