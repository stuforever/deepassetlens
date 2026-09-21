"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import json
import logging

from app.services.sishu_full.services.path_service import get_path_service

logger = logging.getLogger(__name__)

_STATE_FILENAME = "loaded_tools.json"


def _state_file(session_id: str):
    workspace = get_path_service().get_session_workspace("chat", session_id)
    return workspace / _STATE_FILENAME


def load_loaded_tools(session_id: str) -> set[str]:
    if not session_id:
        return set()
    try:
        path = _state_file(session_id)
        if not path.exists():
            return set()
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("loaded-tools state unreadable for %s", session_id, exc_info=True)
        return set()
    names = data.get("loaded_tools") if isinstance(data, dict) else None
    if not isinstance(names, list):
        return set()
    return {str(n) for n in names if str(n).strip()}


def record_loaded_tools(session_id: str, names: set[str]) -> None:
    if not session_id:
        return
    try:
        path = _state_file(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"loaded_tools": sorted(names)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        logger.warning("failed to persist loaded-tools state for %s", session_id, exc_info=True)


__all__ = ["load_loaded_tools", "record_loaded_tools"]
