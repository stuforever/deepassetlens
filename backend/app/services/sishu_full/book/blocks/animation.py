"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import importlib.util
import logging
from typing import Any

from ..models import BlockType, SourceAnchor
from .base import BlockContext, BlockGenerator, GenerationFailure

logger = logging.getLogger(__name__)


_LANGUAGE_ANIMATION_TERMS = {
    "英语",
    "英文",
    "词汇",
    "单词",
    "语法",
    "句型",
    "时态",
    "动词",
    "发音",
    "对话",
    "问候",
    "自我介绍",
    "english",
    "vocabulary",
    "grammar",
    "sentence",
    "tense",
    "verb",
    "pronunciation",
    "dialogue",
    "greeting",
    "self-introduction",
    "present continuous",
}


def _animation_mode(ctx: BlockContext) -> str:
    """Choose the light HTML route for language learning content.

    ``animation_mode`` is preferred when a planner supplies it. The keyword
    fallback keeps older persisted pages retryable because they predate that
    planner field.
    """
    params = ctx.block.params
    explicit = str(
        params.get("animation_mode") or params.get("engine") or ""
    ).strip().lower()
    if explicit in {"html", "interactive", "browser", "web"}:
        return "html"
    if explicit in {"manim", "video", "manim_video", "math"}:
        return "manim"

    searchable = " ".join(
        str(value or "")
        for value in (
            ctx.chapter.title,
            ctx.chapter.summary,
            *ctx.chapter.learning_objectives,
            params.get("focus"),
        )
    ).lower()
    return (
        "html"
        if any(term in searchable for term in _LANGUAGE_ANIMATION_TERMS)
        else "manim"
    )


class AnimationGenerator(BlockGenerator):
    block_type = BlockType.ANIMATION

    async def _generate(
        self, ctx: BlockContext
    ) -> tuple[dict[str, Any], list[SourceAnchor], dict[str, Any]]:
        if _animation_mode(ctx) == "html":
            return await self._generate_html_animation(ctx)

        if importlib.util.find_spec("manim") is None:
            raise GenerationFailure(
                "AnimationGenerator requires the optional math-animator extras. "
                "Install with `pip install -e '.[math-animator]'` "
                "or `pip install -r requirements/math-animator.txt`."
            )

        params = ctx.block.params
        chapter_title = params.get("chapter_title", ctx.chapter.title)
        chapter_summary = params.get("chapter_summary", ctx.chapter.summary)
        objectives = params.get("objectives") or ctx.chapter.learning_objectives
        focus = str(params.get("focus") or "")
        quality = str(params.get("quality") or "medium")
        style_hint = str(params.get("style_hint") or "")

        history_lines: list[str] = []
        if chapter_summary:
            history_lines.append(f"Chapter summary: {chapter_summary}")
        if objectives:
            history_lines.append("Learning objectives:")
            for obj in objectives:
                history_lines.append(f"- {obj}")
        history_context = "\n".join(history_lines)

        focus_clause = f" focusing on {focus}" if focus else ""
        user_input = (
            f"Create a short Manim animation that walks through the core "
            f'derivation of "{chapter_title}"{focus_clause}. Aim for a '
            "clear, step-by-step explanation a learner can follow."
        )

        try:
            from app.services.sishu_full.agents.math_animator.pipeline import MathAnimatorPipeline
            from app.services.sishu_full.agents.math_animator.request_config import (
                MathAnimatorRequestConfig,
            )
            from app.services.sishu_full.services.llm.config import get_llm_config

            llm_config = get_llm_config()
            request_config = MathAnimatorRequestConfig(
                output_mode="video",
                quality=quality if quality in ("low", "medium", "high") else "medium",
                style_hint=style_hint,
            )
            pipeline = MathAnimatorPipeline(
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
                api_version=llm_config.api_version,
                language=ctx.language,
            )
            turn_id = f"book-{ctx.book_id}-{ctx.block.id}"
            result = await pipeline.run(
                turn_id=turn_id,
                user_input=user_input,
                history_context=history_context,
                request_config=request_config,
                attachments=[],
            )
        except Exception as exc:
            logger.warning(f"AnimationGenerator failed: {exc}", exc_info=True)
            raise GenerationFailure(f"animation generation failed: {exc}") from exc

        render_result = result["render_result"]
        summary_payload = result["summary"]
        analysis = result["analysis"]
        artifacts = [artifact.model_dump() for artifact in render_result.artifacts]
        primary = next(
            (
                a
                for a in artifacts
                if a.get("type") == "video" or "video" in (a.get("content_type") or "")
            ),
            artifacts[0] if artifacts else None,
        )

        return (
            {
                "render_type": "video",
                "artifacts": artifacts,
                "video_url": (primary or {}).get("url", ""),
                "filename": (primary or {}).get("filename", ""),
                "summary": getattr(summary_payload, "summary_text", "") or "",
                "key_points": list(getattr(summary_payload, "key_points", []) or []),
                "description": getattr(analysis, "learning_goal", "") or "",
            },
            [],
            {
                "retry_attempts": render_result.retry_attempts,
                "quality": request_config.quality,
            },
        )

    async def _generate_html_animation(
        self, ctx: BlockContext
    ) -> tuple[dict[str, Any], list[SourceAnchor], dict[str, Any]]:
        """Generate a browser animation for language-learning chapters."""
        params = ctx.block.params
        chapter_title = params.get("chapter_title", ctx.chapter.title)
        chapter_summary = params.get("chapter_summary", ctx.chapter.summary)
        objectives = params.get("objectives") or ctx.chapter.learning_objectives
        focus = str(params.get("focus") or "")

        history_lines: list[str] = []
        if chapter_summary:
            history_lines.append(f"Chapter summary: {chapter_summary}")
        if objectives:
            history_lines.append("Learning objectives:")
            for obj in objectives:
                history_lines.append(f"- {obj}")
        history_context = "\n".join(history_lines)

        focus_clause = f" focusing on {focus}" if focus else ""
        guidance_language = (
            "Use concise Chinese guidance around the English examples."
            if ctx.language == "zh"
            else "Use concise learner-friendly guidance."
        )
        user_input = (
            f"Create a short interactive animated English-learning lesson for "
            f'the chapter "{chapter_title}"{focus_clause}. '
            "Animate the reveal of target words or sentences, highlight the "
            "grammar change or pronunciation pattern step by step, and include "
            "Next/Back or clickable practice controls. Keep the English examples "
            f"faithful to the supplied chapter context. {guidance_language} "
            "Make it work as a self-contained HTML page with no external assets."
        )

        try:
            from app.services.sishu_full.agents.visualize.pipeline import VisualizePipeline
            from app.services.sishu_full.services.llm.config import get_llm_config

            llm_config = get_llm_config()
            pipeline = VisualizePipeline(
                api_key=llm_config.api_key,
                base_url=llm_config.base_url,
                api_version=llm_config.api_version,
                language=ctx.language,
            )
            analysis = await pipeline.run_analysis(
                user_input=user_input,
                history_context=history_context,
                render_mode="html",
            )
            code = await pipeline.run_code_generation(
                user_input=user_input,
                history_context=history_context,
                analysis=analysis,
            )
        except Exception as exc:
            logger.warning(f"Language animation generation failed: {exc}", exc_info=True)
            raise GenerationFailure(f"language animation generation failed: {exc}") from exc

        from app.services.sishu_full.agents.visualize.utils import validate_visualization

        ok, validation_error = validate_visualization(code, "html")
        if not ok:
            raise GenerationFailure(
                f"language animation html failed validation: {validation_error}"
            )

        return (
            {
                "render_type": "html",
                "code": {"language": "html", "content": code},
                "summary": analysis.description,
                "description": analysis.description,
                "chart_type": analysis.chart_type or "animation",
            },
            [],
            {
                "animation_mode": "html",
                "review_changed": False,
                "review_notes": "Generated as a self-contained HTML learning animation.",
            },
        )


__all__ = ["AnimationGenerator"]
