"""wrong_intake capability — conversational wrong-question intake.

There is no bespoke state machine: the chat agent loop IS the intake flow. This
capability marks the turn as ``wrong_intake`` mode (mounting
``save_wrong_question`` + the intake playbook) and runs the standard agentic
chat pipeline. The model extracts fields from the learner's words, uses
``ask_user`` to clarify anything missing, confirms before saving, and calls
``save_wrong_question`` — which writes straight through the service layer into
the active user's wrong-question book (no HTTP round-trip, zero new storage).
"""

from __future__ import annotations

from deeptutor.agents.chat.agentic_pipeline import AgenticChatPipeline
from deeptutor.capabilities.wrong_intake.tools import WRONG_INTAKE_TOOL_NAMES
from deeptutor.core.capability_protocol import BaseCapability, CapabilityManifest
from deeptutor.core.context import UnifiedContext
from deeptutor.core.stream_bus import StreamBus


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
