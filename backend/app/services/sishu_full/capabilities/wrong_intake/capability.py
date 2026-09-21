"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from app.services.sishu_full.agents.chat.agentic_pipeline import AgenticChatPipeline
from app.services.sishu_full.capabilities.wrong_intake.tools import WRONG_INTAKE_TOOL_NAMES
from app.services.sishu_full.core.capability_protocol import BaseCapability, CapabilityManifest
from app.services.sishu_full.core.context import UnifiedContext
from app.services.sishu_full.core.stream_bus import StreamBus


class WrongIntakeCapability(BaseCapability):
    manifest = CapabilityManifest(
        name="wrong_intake",
        description=(
            "Conversational wrong-question intake: the tutor asks, clarifies, "
            "and saves the learner's wrong questions into their wrong-question "
            "book through a natural dialogue, then offers to record another."
        ),
        stages=["responding"],
        tools_used=[*WRONG_INTAKE_TOOL_NAMES, "ask_user"],
        cli_aliases=["wrong_intake", "record-wrong"],
    )

    async def run(self, context: UnifiedContext, stream: StreamBus) -> None:
        context.metadata["wrong_intake"] = True
        pipeline = AgenticChatPipeline(language=context.language)
        await pipeline.run(context, stream)


__all__ = ["WrongIntakeCapability"]
