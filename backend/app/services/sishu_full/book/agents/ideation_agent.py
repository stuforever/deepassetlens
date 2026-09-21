"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from typing import Any

from app.services.sishu_full.agents.base_agent import BaseAgent
from app.services.sishu_full.utils.json_parser import parse_json_response

from ..inputs import IdeationContext
from ..models import BookProposal


MAX_BOOK_CHAPTERS = 14
LEGACY_TEXTBOOK_CHAPTERS = 13
TRANSITION_TEXTBOOK_CHAPTERS = 14


class IdeationAgent(BaseAgent):
    """LLM call that proposes a book given the four-source IdeationContext."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        api_version: str | None = None,
        language: str = "en",
        binding: str = "openai",
    ) -> None:
        super().__init__(
            module_name="book",
            agent_name="ideation_agent",
            api_key=api_key,
            base_url=base_url,
            api_version=api_version,
            language=language,
            binding=binding,
        )

    async def process(
        self,
        *,
        ideation_context: IdeationContext,
    ) -> BookProposal:
        from ..blocks._language import language_directive

        system_prompt = self.get_prompt("system") or _FALLBACK_SYSTEM
        system_prompt = system_prompt.rstrip() + language_directive(self.language)
        user_template = self.get_prompt("user_template") or _FALLBACK_USER
        user_prompt = user_template.format(ideation_context=ideation_context.render())

        chunks: list[str] = []
        async for chunk in self.stream_llm(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            response_format={"type": "json_object"},
            stage="ideation",
        ):
            chunks.append(chunk)
        raw = "".join(chunks)

        payload = parse_json_response(raw, logger_instance=self.logger, fallback={})
        if not isinstance(payload, dict):
            payload = {}

        return self._coerce_proposal(payload, ideation_context)

    @staticmethod
    def _coerce_proposal(data: dict[str, Any], ctx: IdeationContext) -> BookProposal:
        chapters_raw = data.get("estimated_chapters", 0) or 0
        try:
            estimated = max(2, min(MAX_BOOK_CHAPTERS, int(chapters_raw)))
        except (TypeError, ValueError):
            estimated = 4

        # A textbook-sequence request needs one top-level chapter per
        # Starter/Module/Revision section instead of a compressed summary.
        intent = (ctx.user_intent or "").casefold()
        transition_markers = (
            "4节",
            "4 + 10",
            "4+10",
            "四节",
            "14节",
            "十四节",
            "过渡复习",
            "十节新内容",
            "十个新单元",
        )
        sequence_markers = (
            "starter",
            "module 1",
            "module 10",
            "revision a",
            "revision b",
            "按教材顺序",
            "按教材章节",
            "教材同步",
        )
        if any(marker in intent for marker in transition_markers):
            estimated = TRANSITION_TEXTBOOK_CHAPTERS
        elif any(marker in intent for marker in sequence_markers):
            estimated = LEGACY_TEXTBOOK_CHAPTERS

        title = str(data.get("title") or "Untitled Book").strip() or "Untitled Book"
        return BookProposal(
            title=title[:120],
            description=str(data.get("description") or "").strip(),
            scope=str(data.get("scope") or "").strip(),
            target_level=str(data.get("target_level") or "mixed").strip(),
            estimated_chapters=estimated,
            rationale=str(data.get("rationale") or "").strip(),
        )


_FALLBACK_SYSTEM = (
    "Propose ONE coherent book that satisfies the learner's intent. "
    'Output JSON: {"title", "description", "scope", "target_level", '
    '"estimated_chapters", "rationale"}.'
)
_FALLBACK_USER = "{ideation_context}\n\nRespond with the JSON object only."


__all__ = ["IdeationAgent"]
