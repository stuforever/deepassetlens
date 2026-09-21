"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from typing import Any

# A connected Obsidian vault: a pointer (``vault_path``) to a folder of
# Markdown the user already owns. No index, no embeddings — the Obsidian
# capability navigates the live files. See ``capabilities/obsidian``.
OBSIDIAN_KB_TYPE = "obsidian"

# A linked engine index: a pointer (``external_path``) to a folder that already
# contains a self-contained index built by one of our local providers. We mount
# it in place and retrieve via the bound provider — no copy, no re-index.
LINKED_KB_TYPE = "linked"

# A connected subagent: a pointer to a local agent CLI (Claude Code / Codex).
# No path on disk — ``agent_kind`` names the backend, optional ``cwd`` is the
# working directory. Driven live via ``consult_subagent``; never indexed.
SUBAGENT_KB_TYPE = "subagent"

# A connected external LightRAG server: a pointer (``server_url`` + optional
# ``api_key``) to a standalone LightRAG instance the user runs. No path on disk
# and no local index — retrieval is offloaded over HTTP to the server's
# ``/query`` endpoint by the ``lightrag-server`` provider.
LIGHTRAG_SERVER_KB_TYPE = "lightrag_server"

# A connected Tencent IMA knowledge base: a pointer (``client_id`` + ``api_key``
# + ``knowledge_base_id``) to a library the user curates in IMA. No path on disk
# and no local index — retrieval is offloaded over HTTPS to IMA's
# ``search_knowledge`` OpenAPI by the ``ima`` provider.
IMA_KB_TYPE = "ima"

# Every pointer/connected KB type. Membership here is what makes the manager
# skip the index pipeline, the orphan prune and the embedding reconcile.
CONNECTED_KB_TYPES = frozenset(
    {
        OBSIDIAN_KB_TYPE,
        LINKED_KB_TYPE,
        SUBAGENT_KB_TYPE,
        LIGHTRAG_SERVER_KB_TYPE,
        IMA_KB_TYPE,
    }
)


def is_connected_kb(entry: Any) -> bool:
    """True for pointer KBs whose data lives outside ``data/knowledge_bases``."""
    return isinstance(entry, dict) and entry.get("type") in CONNECTED_KB_TYPES


def external_root_of(entry: Any) -> str | None:
    """Absolute path a connected KB points at, or ``None`` for ordinary KBs.

    ``linked`` KBs store it under ``external_path``; ``obsidian`` vaults under
    the older ``vault_path`` field. One accessor so callers don't care which.
    """
    if not isinstance(entry, dict):
        return None
    return entry.get("external_path") or entry.get("vault_path")


__all__ = [
    "OBSIDIAN_KB_TYPE",
    "LINKED_KB_TYPE",
    "SUBAGENT_KB_TYPE",
    "LIGHTRAG_SERVER_KB_TYPE",
    "IMA_KB_TYPE",
    "CONNECTED_KB_TYPES",
    "is_connected_kb",
    "external_root_of",
]
