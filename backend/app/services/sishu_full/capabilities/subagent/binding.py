"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from app.services.sishu_full.core.context import UnifiedContext
from app.services.sishu_full.knowledge.kb_types import SUBAGENT_KB_TYPE

# Cached on context.metadata: a {"name", "kind", "cwd", "partner_id"} dict, or ""
# once we've looked and found none. Absence of the key means "not resolved yet".
_CACHE_KEY = "_subagent_connection"
_UNSET = object()


def connection_for_turn(context: UnifiedContext) -> dict[str, str] | None:
    """Return ``{"name", "kind", "cwd", "partner_id"}`` of the selected subagent, or ``None``."""
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
        if not meta or meta.get("type") != SUBAGENT_KB_TYPE:
            continue
        kind = str(meta.get("agent_kind") or "").strip()
        if not kind:
            continue
        return {
            "name": str(meta.get("name") or ref),
            "kind": kind,
            "cwd": str(meta.get("cwd") or "").strip(),
            "partner_id": str(meta.get("partner_id") or "").strip(),
        }
    return None


def subagent_refs(context: UnifiedContext) -> set[str]:
    """Return every selected KB ref that resolves to a connected subagent.

    A subagent "KB" is a delegate consulted via ``consult_subagent``, not a rag
    index — exclude these refs from the rag surface so a co-selected real KB
    stays reachable (issue #650) and the agent ref never appears as a rag choice.
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
            and meta.get("type") == SUBAGENT_KB_TYPE
            and str(meta.get("agent_kind") or "").strip()
        ):
            refs.add(ref)
    return refs


__all__ = ["connection_for_turn", "subagent_refs"]
