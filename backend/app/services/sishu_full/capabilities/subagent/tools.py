"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from app.services.sishu_full.core.tool_protocol import BaseTool, ToolDefinition, ToolParameter, ToolResult

if TYPE_CHECKING:  # avoid importing the services package at module-load time (cycle)
    from app.services.sishu_full.services.subagent import SubagentEvent

logger = logging.getLogger(__name__)

SUBAGENT_TOOL_NAMES: tuple[str, ...] = ("consult_subagent",)

# Single trace_kind for every streamed subagent event; the fine-grained channel
# (text / tool / tool_result / reasoning / log / result) rides in metadata so the
# sidebar can render a CLI-faithful transcript while filtering on one key.
_TRACE_KIND = "subagent_event"


class ConsultSubagentTool(BaseTool):
    """Put one question to the connected subagent and stream its native run."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="consult_subagent",
            description=(
                "Ask the connected external agent (a local agent CLI on the user's "
                "machine — Claude Code, Codex, Gemini CLI, Kimi CLI, opencode, MiMo "
                "Code — or one of their partners) a focused question and get its "
                "answer. A local agent runs on the user's machine with access to their "
                "files and tools; a partner answers with its own persona, library and "
                "skills. Either way its full step-by-step run is shown to the user "
                "live. Use it to delegate work it is better placed to do — inspecting "
                "a codebase, running commands, reproducing a bug, or drawing on a "
                "partner's dedicated knowledge. You may consult it more than once to "
                "drill down, but you have a limited number of consults this turn (the "
                "result tells you how many remain). When you have enough, stop calling "
                "this tool and answer the user yourself in your own voice — never "
                "impersonate the agent."
            ),
            parameters=[
                ToolParameter(
                    name="question",
                    type="string",
                    description=(
                        "The question or task to put to the agent. Be specific and "
                        "self-contained; the agent keeps context across your consults "
                        "this turn, so each one can build on the last."
                    ),
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        spec = kwargs.get("_subagent")
        if not isinstance(spec, dict):
            return ToolResult(
                content="No subagent is connected on this turn; consult_subagent is unavailable.",
                success=False,
            )
        question = str(kwargs.get("question") or "").strip()
        if not question:
            return ToolResult(
                content="consult_subagent needs a non-empty 'question'.", success=False
            )

        state = spec["state"]
        budget = int(spec["budget"])
        name = str(spec.get("name") or "the agent")
        if int(state.get("count", 0)) >= budget:
            return ToolResult(
                content=(
                    f"[Consult budget reached: you have already asked {name} {budget} "
                    "time(s) this turn — the maximum. Do not call consult_subagent "
                    "again. Answer the user now with what you have gathered.]"
                ),
                success=False,
            )

        from app.services.sishu_full.services.subagent import get_backend

        backend = get_backend(str(spec.get("kind") or ""))
        if backend is None:
            return ToolResult(
                content=f"Unknown subagent backend: {spec.get('kind')!r}", success=False
            )

        state["count"] = int(state.get("count", 0)) + 1
        consult_index = state["count"]
        event_sink = kwargs.get("event_sink")

        async def _stream(channel: str, text: str, extra: dict[str, object] | None = None) -> None:
            if event_sink is None or not text:
                return
            metadata: dict[str, object] = {
                "subagent_kind": backend.kind,
                "subagent_name": name,
                "subagent_channel": channel,
                "consult_index": consult_index,
            }
            # ``merge_id`` correlates a backend's start/finish (a web search) or
            # streaming deltas (the answer typing out) into one evolving row.
            # Namespace it by consult round so ids stay unique across the turn's
            # several consults (which share one transcript).
            merge_id = (extra or {}).get("merge_id")
            if merge_id:
                metadata["subagent_merge_id"] = f"{consult_index}:{merge_id}"
            await event_sink(_TRACE_KIND, text, metadata)

        async def on_event(event: SubagentEvent) -> None:
            await _stream(event.kind, event.text, event.meta)

        # Materialize any forwarded images (gated by the per-backend
        # ``forward_images`` setting) to a temp dir the CLI can ingest; cleaned up
        # in ``finally`` once the run ends.
        image_dir, image_paths = _stage_images(spec.get("images") or [])

        # Head this round with the question DeepTutor is putting to the agent, so
        # the transcript reads as a dialogue (esp. across several consults).
        await _stream("question", question)

        try:
            result = await backend.consult(
                question,
                on_event=on_event,
                cwd=spec.get("cwd") or None,
                session_id=state.get("session_id"),
                config=spec.get("config"),
                images=image_paths or None,
                partner_id=spec.get("partner_id") or None,
            )
        except Exception as exc:  # pragma: no cover - defensive: surface, don't crash the turn
            logger.warning("consult_subagent failed: %s", exc, exc_info=True)
            return ToolResult(content=f"The subagent run failed: {exc}", success=False)
        finally:
            if image_dir is not None:
                import shutil

                shutil.rmtree(image_dir, ignore_errors=True)

        if result.session_id:
            state["session_id"] = result.session_id
            # Remember it across turns so the next turn (and the sidebar) resume
            # this same live agent session.
            session_key_value = spec.get("session_key")
            if session_key_value:
                from app.services.sishu_full.services.subagent.sessions import remember_session

                remember_session(
                    str(session_key_value),
                    result.session_id,
                    kind=backend.kind,
                    cwd=str(spec.get("cwd") or ""),
                )

        remaining = max(0, budget - consult_index)
        metadata = {
            "subagent_kind": backend.kind,
            "consult_index": consult_index,
            "consult_remaining": remaining,
            "event_count": result.event_count,
        }
        if not result.final_text:
            detail = result.error or "the agent produced no final answer text"
            return ToolResult(
                content=f"[The agent returned no answer: {detail}]",
                success=False,
                metadata=metadata,
            )

        budget_note = (
            f"\n\n[{remaining} consult(s) left with {name} this turn.]"
            if remaining > 0
            else f"\n\n[No consults left with {name} — answer the user now.]"
        )
        return ToolResult(
            content=result.final_text + budget_note,
            success=result.success,
            metadata=metadata,
        )


def _stage_images(images: list[Any]) -> tuple[str | None, list[str]]:
    """Write forwarded image attachments to a temp dir for the CLI to ingest.

    Returns ``(dir, paths)`` — the caller removes ``dir`` once the run ends.
    ``(None, [])`` when there's nothing to forward.
    """
    if not images:
        return None, []
    from pathlib import Path
    import tempfile

    from app.services.sishu_full.services.subagent.images import materialize_images

    staging = tempfile.mkdtemp(prefix="dt-subagent-img-")
    paths = materialize_images(images, Path(staging))
    if not paths:
        import shutil

        shutil.rmtree(staging, ignore_errors=True)
        return None, []
    return staging, paths


SUBAGENT_TOOL_TYPES: tuple[type[BaseTool], ...] = (ConsultSubagentTool,)

__all__ = ["SUBAGENT_TOOL_NAMES", "SUBAGENT_TOOL_TYPES", "ConsultSubagentTool"]
