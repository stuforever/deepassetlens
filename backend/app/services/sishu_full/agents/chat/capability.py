"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from app.services.sishu_full.agents.chat.agentic_pipeline import CHAT_OPTIONAL_TOOLS, AgenticChatPipeline
from app.services.sishu_full.core.capability_protocol import BaseCapability, CapabilityManifest
from app.services.sishu_full.core.context import UnifiedContext
from app.services.sishu_full.core.stream_bus import StreamBus
from app.services.sishu_full.runtime.request_contracts import get_capability_request_schema


class ChatCapability(BaseCapability):
    manifest = CapabilityManifest(
        name="chat",
        description=(
            "Agentic chat: an exploring agent loop with tools, followed by "
            "a respond stage that streams the answer."
        ),
        stages=["exploring", "responding"],
        tools_used=CHAT_OPTIONAL_TOOLS,
        cli_aliases=["chat"],
        request_schema=get_capability_request_schema("chat"),
    )

    async def run(self, context: UnifiedContext, stream: StreamBus) -> None:
        pipeline = AgenticChatPipeline(language=context.language)
        await pipeline.run(context, stream)
