"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from typing import Any, Dict, List, Protocol, runtime_checkable


@runtime_checkable
class RAGPipeline(Protocol):
    """A knowledge-base index/retrieve engine bound to a KB by its provider."""

    async def initialize(self, kb_name: str, file_paths: List[str], **kwargs: Any) -> bool:
        """Build a fresh index for ``kb_name`` from ``file_paths``."""
        ...

    async def add_documents(self, kb_name: str, file_paths: List[str], **kwargs: Any) -> bool:
        """Incrementally add ``file_paths`` to ``kb_name``'s existing index."""
        ...

    async def search(self, query: str, kb_name: str, **kwargs: Any) -> Dict[str, Any]:
        """Retrieve grounded context for ``query`` from ``kb_name``.

        Returns a dict with at least ``query``, ``content``/``answer``,
        ``sources`` and ``provider`` keys.
        """
        ...

    async def delete(self, kb_name: str, **kwargs: Any) -> bool:
        """Delete ``kb_name`` and any engine-side resources."""
        ...


__all__ = ["RAGPipeline"]
