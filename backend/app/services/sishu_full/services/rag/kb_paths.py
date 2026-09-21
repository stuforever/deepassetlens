"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.sishu_full.knowledge.kb_types import external_root_of

KB_CONFIG_FILENAME = "kb_config.json"


def resolve_kb_dir(kb_base_dir: str | Path, kb_name: str) -> Path:
    """Return the directory holding ``kb_name``'s index.

    For a linked KB this is the user's external folder; for every other KB it
    is the conventional ``<kb_base_dir>/<kb_name>``.
    """
    base = Path(kb_base_dir)
    external = _external_path(base, kb_name)
    if external:
        return Path(external).expanduser()
    return base / kb_name


def _external_path(base: Path, kb_name: str) -> str | None:
    """Read a KB entry's external pointer from ``kb_config.json``, if any."""
    cfg = base / KB_CONFIG_FILENAME
    if not cfg.exists():
        return None
    try:
        with open(cfg, encoding="utf-8") as handle:
            entry = json.load(handle).get("knowledge_bases", {}).get(kb_name, {})
    except Exception:
        return None
    return external_root_of(entry)


__all__ = ["resolve_kb_dir"]
