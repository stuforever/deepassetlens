"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.sishu_full.services.rag.factory import DEFAULT_PROVIDER, normalize_provider_name


def load_kb_config_entry(kb_base_dir: str | Path, kb_name: str) -> dict[str, Any]:
    """Return the raw ``kb_config.json`` entry for ``kb_name``, if present."""
    config_path = Path(kb_base_dir) / "kb_config.json"
    if not config_path.exists():
        return {}
    try:
        with open(config_path, encoding="utf-8") as handle:
            entry = json.load(handle).get("knowledge_bases", {}).get(kb_name, {})
        return entry if isinstance(entry, dict) else {}
    except Exception:
        return {}


def load_metadata_provider(kb_base_dir: str | Path, kb_name: str) -> str | None:
    """Return the provider stored in legacy ``metadata.json``, if present."""
    metadata_path = Path(kb_base_dir) / kb_name / "metadata.json"
    if not metadata_path.exists():
        return None
    try:
        with open(metadata_path, encoding="utf-8") as handle:
            provider = json.load(handle).get("rag_provider")
    except Exception:
        return None
    return normalize_provider_name(provider) if provider else None


def resolve_bound_provider(kb_base_dir: str | Path, kb_name: str | None) -> str:
    """Resolve the provider DeepTutor has bound to a KB.

    Order:
    1. ``kb_config.json``: authoritative runtime state.
    2. ``metadata.json``: legacy/import fallback.
    3. default provider.
    """
    if kb_name:
        entry = load_kb_config_entry(kb_base_dir, kb_name)
        provider = entry.get("rag_provider")
        if provider:
            return normalize_provider_name(provider)

        metadata_provider = load_metadata_provider(kb_base_dir, kb_name)
        if metadata_provider:
            return metadata_provider

    return DEFAULT_PROVIDER


__all__ = [
    "load_kb_config_entry",
    "load_metadata_provider",
    "resolve_bound_provider",
]
