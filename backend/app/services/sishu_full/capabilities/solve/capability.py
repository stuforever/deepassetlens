"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import logging
import re

from app.services.sishu_full.agents.chat.agentic_pipeline import AgenticChatPipeline
from app.services.sishu_full.capabilities.solve.session import DEFAULT_MAX_REPLANS
from app.services.sishu_full.capabilities.solve.tools import SOLVE_TOOL_NAMES
from app.services.sishu_full.core.capability_protocol import BaseCapability, CapabilityManifest
from app.services.sishu_full.core.context import UnifiedContext
from app.services.sishu_full.core.stream_bus import StreamBus
from app.services.sishu_full.runtime.request_contracts import get_capability_request_schema
from app.services.sishu_full.services.config.capabilities_settings import get_solve_params

logger = logging.getLogger(__name__)

_UNSAFE_ID_CHARS = re.compile(r"[^A-Za-z0-9_-]")


def _sanitize(raw: str) -> str:
    cleaned = _UNSAFE_ID_CHARS.sub("_", raw).strip("_")
    return cleaned or "default"


def resolve_solve_session_id(context: UnifiedContext) -> str:
    """Resolve the in-memory session key for this solve turn.

    A solve turn is one-shot, so the turn id (falling back to the session /
    message id) is enough to scope the plan + replan budget; concurrent turns
    get distinct keys and never race.
    """
    raw = str(
        context.metadata.get("turn_id")
        or context.session_id
        or context.metadata.get("message_id")
        or "default"
    )
    return _sanitize(raw)


class DeepSolveCapability(BaseCapability):
    manifest = CapabilityManifest(
        name="deep_solve",
        description="Multi-step problem solving driven by the chat agent loop.",
        stages=["responding"],
        tools_used=[*SOLVE_TOOL_NAMES, "rag", "code_execution", "geogebra_analysis", "reason"],
        cli_aliases=["solve"],
        request_schema=get_capability_request_schema("deep_solve"),
    )

    async def run(self, context: UnifiedContext, stream: StreamBus) -> None:
        context.metadata["solve_mode"] = True
        context.metadata["solve_session_id"] = resolve_solve_session_id(context)
        # Read the solve settings and forward them so the page actually drives
        # the loop: max_rounds → the loop's round budget, max_replans → the
        # SolveSession gate (via metadata, read in SolveLoopCapability),
        # temperature / max_tokens → the LLM calls.
        try:
            params = get_solve_params()
        except Exception as exc:  # pragma: no cover - defensive config read
            logger.warning("Failed to load solve params, using defaults: %s", exc)
            params = {}
        context.metadata["solve_max_replans"] = int(params.get("max_replans", DEFAULT_MAX_REPLANS))
        pipeline = AgenticChatPipeline(
            language=context.language,
            max_rounds=params.get("max_rounds"),
            temperature=params.get("temperature"),
            max_tokens=params.get("max_tokens"),
        )
        await pipeline.run(context, stream)


__all__ = ["DeepSolveCapability", "resolve_solve_session_id"]
