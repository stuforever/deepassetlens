"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from enum import Enum
import os


class RunMode(str, Enum):
    CLI = "cli"
    SERVER = "server"


_current_mode: RunMode | None = None


def _resolve_mode() -> RunMode:
    raw = os.environ.get("DEEPTUTOR_MODE", "").strip().lower()
    if raw == RunMode.SERVER.value:
        return RunMode.SERVER
    return RunMode.CLI


def get_mode() -> RunMode:
    global _current_mode
    if _current_mode is None:
        _current_mode = _resolve_mode()
    return _current_mode


def set_mode(mode: RunMode) -> None:
    """Explicitly set the run mode (call early in entry points)."""
    global _current_mode
    _current_mode = mode
    os.environ["DEEPTUTOR_MODE"] = mode.value


def is_cli() -> bool:
    return get_mode() == RunMode.CLI


def is_server() -> bool:
    return get_mode() == RunMode.SERVER
