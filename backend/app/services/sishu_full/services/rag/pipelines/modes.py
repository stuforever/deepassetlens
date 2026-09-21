"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Sequence


def resolve_kb_mode(
    kb_base_dir: str | Path,
    kb_name: Optional[str],
    provider: str,
    *,
    explicit: Any = None,
    supported: Sequence[str],
    default: str,
) -> str:
    candidates: list[Any] = [explicit]
    try:
        cfg_path = Path(kb_base_dir) / "kb_config.json"
        if cfg_path.exists():
            data = json.loads(cfg_path.read_text(encoding="utf-8"))
            if kb_name:
                entry = data.get("knowledge_bases", {}).get(kb_name, {})
                candidates.append(entry.get("search_mode"))
            candidates.append(data.get("defaults", {}).get("provider_modes", {}).get(provider))
    except Exception:  # pragma: no cover - defensive
        pass

    supported_set = {m.lower() for m in supported}
    for candidate in candidates:
        norm = (str(candidate) if candidate else "").strip().lower()
        if norm in supported_set:
            return norm
    return default


__all__ = ["resolve_kb_mode"]
