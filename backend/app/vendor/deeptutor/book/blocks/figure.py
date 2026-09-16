"""Figure block – static visual figure (svg / chartjs / mermaid).

Wraps :class:`deeptutor.agents.visualize.pipeline.VisualizePipeline` with
``render_mode="figure"`` so the LLM picks the best static rendering for the
chapter, but never falls back to interactive HTML (handled by the
``interactive`` block type).

Like the chat capability, the draft is checked by the deterministic local
``validate_visualization``; only on failure do we spend one targeted repair
call. If the code still fails after repair we raise ``GenerationFailure`` so
the book engine can retry, instead of baking a broken figure into the book.
"""

from __future__ import annotations

import logging
from html import escape
from typing import Any

from ..models import BlockType, SourceAnchor
from .base import BlockContext, BlockGenerator, GenerationFailure

logger = logging.getLogger(__name__)


_SPATIAL_FIGURE_TERMS = (
    "方位",
    "空间",
    "介词",
    "位置",
    "spatial",
    "preposition",
    "position",
    "in, on",
)


def _is_spatial_figure(ctx: BlockContext) -> bool:
    params = ctx.block.params
    searchable = " ".join(
        str(value or "")
        for value in (
            ctx.chapter.title,
            ctx.chapter.summary,
            *ctx.chapter.learning_objectives,
            params.get("focus"),
        )
    ).lower()
    return any(term.lower() in searchable for term in _SPATIAL_FIGURE_TERMS)


def _spatial_fallback_svg(ctx: BlockContext, reason: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a deterministic classroom diagram when the LLM is unavailable."""
    title = escape(str(ctx.chapter.title or "Spatial relations"))
    note = escape(reason[:180])
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 480">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
      <path d="M2 1L8 5L2 9" fill="none" stroke="context-stroke" stroke-width="1.5"/>
    </marker>
  </defs>
  <text class="th" x="380" y="34" text-anchor="middle">{title}</text>
  <text class="ts" x="380" y="58" text-anchor="middle">English spatial prepositions</text>
  <g class="c-gray">
    <rect class="box" x="292" y="190" width="176" height="90" rx="12"/>
    <text class="th" x="380" y="224" text-anchor="middle">the desk</text>
    <text class="ts" x="380" y="250" text-anchor="middle">参照物</text>
  </g>
  <g class="c-blue">
    <rect class="box" x="90" y="120" width="130" height="54" rx="10"/>
    <text class="th" x="155" y="143" text-anchor="middle">in</text>
    <text class="ts" x="155" y="162" text-anchor="middle">在里面</text>
    <path class="arr" d="M220 147L292 215" marker-end="url(#arrow)"/>
  </g>
  <g class="c-teal">
    <rect class="box" x="540" y="120" width="130" height="54" rx="10"/>
    <text class="th" x="605" y="143" text-anchor="middle">on</text>
    <text class="ts" x="605" y="162" text-anchor="middle">在表面上</text>
    <path class="arr" d="M540 147L468 215" marker-end="url(#arrow)"/>
  </g>
  <g class="c-purple">
    <rect class="box" x="90" y="330" width="130" height="54" rx="10"/>
    <text class="th" x="155" y="353" text-anchor="middle">under</text>
    <text class="ts" x="155" y="372" text-anchor="middle">在下面</text>
    <path class="arr" d="M220 357L326 280" marker-end="url(#arrow)"/>
  </g>
  <g class="c-coral">
    <rect class="box" x="540" y="330" width="130" height="54" rx="10"/>
    <text class="th" x="605" y="353" text-anchor="middle">over</text>
    <text class="ts" x="605" y="372" text-anchor="middle">在上方</text>
    <path class="arr" d="M540 357L434 280" marker-end="url(#arrow)"/>
  </g>
  <text class="ts" x="380" y="438" text-anchor="middle">The book is on the desk.  The cat is under the desk.</text>
</svg>'''
    return (
        {
            "render_type": "svg",
            "code": {"language": "svg", "content": svg},
            "description": "用参照物展示 in、on、under、over 的空间关系。",
            "chart_type": "spatial_relations",
        },
        {
            "fallback": True,
            "fallback_reason": note,
            "review_changed": False,
            "review_notes": "Used deterministic spatial-relations fallback.",
        },
    )


class FigureGenerator(BlockGenerator):
    block_type = BlockType.FIGURE

    async def _generate(
        self, ctx: BlockContext
    ) -> tuple[dict[str, Any], list[SourceAnchor], dict[str, Any]]:
        params = ctx.block.params
        chapter_title = params.get("chapter_title", ctx.chapter.title)
        chapter_summary = params.get("chapter_summary", ctx.chapter.summary)
        objectives = params.get("objectives") or ctx.chapter.learning_objectives
        variant = str(params.get("variant") or "diagram")
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
        user_input = (
            f"Create a {variant} figure for the chapter "
            f'"{chapter_title}"{focus_clause}. The figure should help a '
            "learner build intuition about the core relationships covered above."
        )

        try:
            from deeptutor.agents.visualize.models import ReviewResult
            from deeptutor.agents.visualize.pipeline import VisualizePipeline
            from deeptutor.agents.visualize.utils import validate_visualization
            from deeptutor.services.llm.config import get_llm_config

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
                render_mode="figure",
            )
            code = await pipeline.run_code_generation(
                user_input=user_input,
                history_context=history_context,
                analysis=analysis,
            )
            ok, validation_error = validate_visualization(code, analysis.render_type)
            if ok:
                review = ReviewResult(
                    optimized_code=code,
                    changed=False,
                    review_notes="Passed local validation.",
                )
            else:
                review = await pipeline.run_repair(
                    user_input=user_input,
                    analysis=analysis,
                    code=code,
                    error=validation_error,
                )
        except Exception as exc:
            logger.warning(f"FigureGenerator failed: {exc}", exc_info=True)
            if _is_spatial_figure(ctx):
                payload, metadata = _spatial_fallback_svg(ctx, str(exc))
                return payload, [], metadata
            raise GenerationFailure(f"figure generation failed: {exc}") from exc

        final_code = review.optimized_code or code
        render_type = analysis.render_type
        final_ok, residual_error = validate_visualization(final_code, render_type)
        if not final_ok:
            if _is_spatial_figure(ctx):
                payload, metadata = _spatial_fallback_svg(ctx, residual_error)
                return payload, [], metadata
            raise GenerationFailure(f"figure failed validation after repair: {residual_error}")
        lang_tag = {
            "svg": "svg",
            "mermaid": "mermaid",
            "chartjs": "javascript",
        }.get(render_type, "svg")

        return (
            {
                "render_type": render_type,
                "code": {"language": lang_tag, "content": final_code},
                "description": analysis.description,
                "chart_type": analysis.chart_type,
            },
            [],
            {
                "review_changed": review.changed,
                "review_notes": review.review_notes,
            },
        )


__all__ = ["FigureGenerator"]
