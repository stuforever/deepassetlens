"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from typing import Any

from ..models import BlockType, SourceAnchor
from .base import BlockContext, BlockGenerator


class UserNoteGenerator(BlockGenerator):
    block_type = BlockType.USER_NOTE

    async def _generate(
        self, ctx: BlockContext
    ) -> tuple[dict[str, Any], list[SourceAnchor], dict[str, Any]]:
        params = ctx.block.params
        body = str(params.get("body") or "").strip()
        return (
            {"format": "markdown", "body": body, "author": "user"},
            [],
            {},
        )


__all__ = ["UserNoteGenerator"]
