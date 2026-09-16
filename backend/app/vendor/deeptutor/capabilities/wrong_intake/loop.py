"""wrong_intake loop-capability hooks.

The chat agent loop IS the intake flow: it extracts the question fields from
the learner's own words, uses ``ask_user`` to clarify missing pieces, and calls
``save_wrong_question`` once everything is confirmed. This capability only adds
the system prompt (field checklist + when to stop asking) and ensures the write
tool is available on the turn.
"""

from __future__ import annotations

from importlib import resources
from typing import Any

from deeptutor.capabilities.wrong_intake.tools import WRONG_INTAKE_TOOL_NAMES
from deeptutor.capabilities.protocol import PromptBlock
from deeptutor.core.context import UnifiedContext


class WrongIntakeLoopCapability:
    """Turn-scoped integration for conversational wrong-question intake."""

    name = "wrong_intake"
    owned_tools = WRONG_INTAKE_TOOL_NAMES

    def is_active(self, context: UnifiedContext) -> bool:
        return bool(context.metadata.get("wrong_intake"))

    def system_block(
        self,
        context: UnifiedContext,
        *,
        language: str,
        prompts: dict[str, Any],
    ) -> PromptBlock | None:
        if not self.is_active(context):
            return None
        override = _prompt_text(prompts, ("wrong_intake", "system"))
        content = override or _load_system_prompt(language)
        return PromptBlock("wrong_intake", content)

    def augment_kwargs(
        self,
        tool_name: str,
        kwargs: dict[str, Any],
        context: UnifiedContext,
    ) -> dict[str, Any]:
        _ = (tool_name, context)
        return kwargs

    def pre_loop_seed(self, context: UnifiedContext) -> str:
        _ = context
        return ""


def _prompt_text(prompts: dict[str, Any], path: tuple[str, ...]) -> str:
    value: Any = prompts
    for key in path:
        if not isinstance(value, dict):
            return ""
        value = value.get(key)
    return value if isinstance(value, str) and value else ""


def _load_system_prompt(language: str) -> str:
    lang = "zh" if language.lower().startswith("zh") else "en"
    prompt = resources.files(__package__).joinpath("prompts", lang, "system.md")
    return prompt.read_text(encoding="utf-8").strip()


__all__ = ["WrongIntakeLoopCapability"]
