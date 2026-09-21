"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from typing import Any

from app.services.sishu_full.core.agentic.usage import UsageTracker
from app.services.sishu_full.core.stream_bus import StreamBus


async def emit_capability_result(
    stream: StreamBus,
    payload: dict[str, Any],
    *,
    source: str,
    usage: UsageTracker | None = None,
) -> None:
    """Emit the final capability result, attaching cost_summary if available.

    ``payload`` is mutated in place: when ``usage`` has at least one
    recorded call, its ``summary()`` is merged into
    ``payload["metadata"]["cost_summary"]``. Any pre-existing
    ``payload["metadata"]`` dict is preserved.
    """
    if usage is not None:
        cs = usage.summary()
        if cs:
            meta = payload.get("metadata")
            if not isinstance(meta, dict):
                meta = {}
                payload["metadata"] = meta
            meta["cost_summary"] = cs
    await stream.result(payload, source=source)


__all__ = ["emit_capability_result"]
