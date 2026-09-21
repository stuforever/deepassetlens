"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from app.services.sishu_full.core.context import UnifiedContext
from app.services.sishu_full.knowledge.kb_types import OBSIDIAN_KB_TYPE

# Cached on context.metadata: a {"name", "path"} dict, or "" once we've looked
# and found none. Absence of the key means "not resolved yet".
_CACHE_KEY = "_obsidian_vault"


def vault_for_turn(context: UnifiedContext) -> dict[str, str] | None:
    """Return ``{"name", "path"}`` of the selected Obsidian vault, or ``None``."""
    cached = context.metadata.get(_CACHE_KEY, _UNSET)
    if cached is not _UNSET:
        return cached or None
    resolved = _resolve(context)
    context.metadata[_CACHE_KEY] = resolved or ""
    return resolved


def _resolve(context: UnifiedContext) -> dict[str, str] | None:
    from app.services.sishu_full.multi_user.knowledge_access import resolve_kb_metadata

    for ref in context.knowledge_bases or []:
        ref = str(ref).strip()
        if not ref:
            continue
        meta = resolve_kb_metadata(ref)
        if not meta or meta.get("type") != OBSIDIAN_KB_TYPE:
            continue
        path = str(meta.get("vault_path") or "").strip()
        if path:
            return {"name": str(meta.get("name") or ref), "path": path}
    return None


def obsidian_vault_refs(context: UnifiedContext) -> set[str]:
    """Return every selected KB ref that resolves to a connected Obsidian vault.

    The capability only *operates* on the first vault (see :func:`vault_for_turn`),
    but all vault refs are reported here so the chat pipeline can exclude them
    from the ``rag`` surface — ``rag`` has no index for a live vault (issue #650).
    """
    from app.services.sishu_full.multi_user.knowledge_access import resolve_kb_metadata

    refs: set[str] = set()
    for ref in context.knowledge_bases or []:
        ref = str(ref).strip()
        if not ref:
            continue
        meta = resolve_kb_metadata(ref)
        if (
            meta
            and meta.get("type") == OBSIDIAN_KB_TYPE
            and str(meta.get("vault_path") or "").strip()
        ):
            refs.add(ref)
    return refs


_UNSET = object()

__all__ = ["obsidian_vault_refs", "vault_for_turn"]
