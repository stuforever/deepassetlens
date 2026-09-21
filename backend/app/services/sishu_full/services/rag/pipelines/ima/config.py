"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# IMA exposes exactly one retrieval call (``search_knowledge``) with no mode
# knob, so a KB bound to this engine has no per-KB search mode to pick. The
# empty tuple keeps the shared provider-mode plumbing happy while telling the
# UI there is nothing to offer.
SUPPORTED_MODES: tuple[str, ...] = ()
DEFAULT_MODE = ""


class ImaNotConfiguredError(RuntimeError):
    """Raised when a KB is missing the credentials or the knowledge base id."""


@dataclass(frozen=True)
class ImaConfig:
    """A KB's resolved connection to one Tencent IMA knowledge base."""

    client_id: str
    api_key: str
    knowledge_base_id: str


def config_from_entry(entry: dict[str, Any]) -> ImaConfig:
    """Build an :class:`ImaConfig` from a ``kb_config.json`` KB entry.

    Raises :class:`ImaNotConfiguredError` when any of the three required fields
    is missing, so retrieval fails with a clear message instead of an opaque
    HTTP error from IMA.
    """
    client_id = str(entry.get("client_id") or "").strip()
    api_key = str(entry.get("api_key") or "").strip()
    knowledge_base_id = str(entry.get("knowledge_base_id") or "").strip()
    missing = [
        label
        for label, value in (
            ("client ID", client_id),
            ("API key", api_key),
            ("knowledge base ID", knowledge_base_id),
        )
        if not value
    ]
    if missing:
        raise ImaNotConfiguredError(
            "This knowledge base is not fully connected to Tencent IMA "
            f"(missing {', '.join(missing)}). Re-create it with complete credentials."
        )
    return ImaConfig(
        client_id=client_id,
        api_key=api_key,
        knowledge_base_id=knowledge_base_id,
    )


__all__ = [
    "SUPPORTED_MODES",
    "DEFAULT_MODE",
    "ImaNotConfiguredError",
    "ImaConfig",
    "config_from_entry",
]
