"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Header
from pydantic import BaseModel, Field, field_validator

from app.services.sishu_full.services.session import get_session_store, get_sqlite_session_store
from app.services.sishu_full.services.storage.attachment_store import get_attachment_store

logger = logging.getLogger(__name__)

router = APIRouter()


class SessionRenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)


class BranchSelectionRequest(BaseModel):
    """Edit-branch picker state: `{parent_message_id: chosen_child_id}`.

    Stored inside the session preferences blob so it survives reloads
    without a dedicated column.
    """

    selected_branches: dict[str, int] = Field(default_factory=dict)


class QuizResultItem(BaseModel):
    question_id: str = ""
    question: str = Field(..., min_length=1)
    question_type: str = ""
    options: dict[str, str] | None = None
    user_answer: str = ""
    correct_answer: str = ""
    explanation: str | None = ""
    difficulty: str | None = ""
    is_correct: bool

    @field_validator("options", mode="before")
    @classmethod
    def _coerce_options(cls, v):
        return v if isinstance(v, dict) else {}

    @field_validator("explanation", "difficulty", mode="before")
    @classmethod
    def _coerce_str(cls, v):
        return v if isinstance(v, str) else ""


class QuizResultsRequest(BaseModel):
    answers: list[QuizResultItem] = Field(default_factory=list)
    turn_id: str = ""


def _format_quiz_results_message(answers: list[QuizResultItem]) -> str:
    total = len(answers)
    correct = sum(1 for item in answers if item.is_correct)
    score_pct = round((correct / total) * 100) if total else 0
    lines = ["[Quiz Performance]"]
    for idx, item in enumerate(answers, 1):
        question = item.question.strip().replace("\n", " ")
        user_answer = (item.user_answer or "").strip() or "(blank)"
        status = "Correct" if item.is_correct else "Incorrect"
        suffix = f" ({status})"
        if not item.is_correct and (item.correct_answer or "").strip():
            suffix = f" ({status}, correct: {(item.correct_answer or '').strip()})"
        qid = f"[{item.question_id}] " if item.question_id else ""
        lines.append(f"{idx}. {qid}Q: {question} -> Answered: {user_answer}{suffix}")
    lines.append(f"Score: {correct}/{total} ({score_pct}%)")
    return "\n".join(lines)


@router.get("")
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    u: str = Query(default="", description="H5 用户标识（?u=），隔离到该用户的会话库"),
    code: str = Query(default="", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    if u:
        from app.services.sishu_full.multi_user.h5 import h5_user_guarded
        from app.services.sishu_full.multi_user.paths import user_context

        with user_context(h5_user_guarded(u, code, x_access_code)):
            return await _list_sessions_inner(limit, offset)
    return await _list_sessions_inner(limit, offset)


async def _list_sessions_inner(
    limit: int, offset: int
) -> dict:
    store = get_session_store()
    sessions = await store.list_sessions(limit=limit, offset=offset)
    return {"sessions": sessions}


# Cap (in characters) for a single event payload returned to the UI. RAG
# tools can attach whole KB documents to ``tool_result``/``observation``
# events; the frontend TraceSurface only needs a preview, and the LLM context
# is built from a separate content-only store, so capping here never affects
# model input.
MAX_EVENT_PAYLOAD = 1024 * 1024
_TRUNCATION_NOTICE = "\n\n[... content truncated]"
_TRUNCATABLE_EVENT_TYPES = ("tool_result", "observation")


def _truncate_oversized_events(
    messages: list[dict[str, Any]], limit: int = MAX_EVENT_PAYLOAD
) -> None:
    """Cap oversized ``tool_result``/``observation`` payloads in place.

    The session store already returns each message's events as a parsed
    ``events`` list (see ``SqliteSessionStore._serialize_message``), so we
    mutate that list directly. Only the UI rendering path is affected.
    """

    def _cap(container: dict[str, Any], field: str) -> bool:
        value = container.get(field)
        if isinstance(value, str) and len(value) > limit:
            container[field] = value[:limit] + _TRUNCATION_NOTICE
            return True
        return False

    for msg in messages:
        events = msg.get("events")
        if not isinstance(events, list):
            continue
        for event in events:
            if not isinstance(event, dict) or event.get("type") not in _TRUNCATABLE_EVENT_TYPES:
                continue
            truncated = _cap(event, "content")
            tool_metadata = (event.get("metadata") or {}).get("tool_metadata")
            if isinstance(tool_metadata, dict):
                for field in ("content", "answer"):
                    truncated = _cap(tool_metadata, field) or truncated
            if truncated:
                event["_truncated"] = True


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    u: str = Query(default="", description="H5 用户标识（?u=），隔离到该用户的会话库"),
    code: str = Query(default="", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    if u:
        from app.services.sishu_full.multi_user.h5 import h5_user_guarded
        from app.services.sishu_full.multi_user.paths import user_context

        with user_context(h5_user_guarded(u, code, x_access_code)):
            return await _get_session_inner(session_id)
    return await _get_session_inner(session_id)


async def _get_session_inner(session_id: str):
    store = get_session_store()
    session = await store.get_session_with_messages(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    _truncate_oversized_events(session.get("messages", []))
    return session


@router.patch("/{session_id}")
async def rename_session(session_id: str, payload: SessionRenameRequest,
    u: str = Query(default="", description="H5 用户标识（?u=），隔离到该用户的会话库"),
    code: str = Query(default="", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    # R5批⑫（清单安全）：写端点补 H5 用户隔离（对齐读端点范式）——原仅凭 session_id 即可跨用户改/删
    with user_context(h5_user_guarded(u, code, x_access_code)):
        store = get_session_store()
        updated = await store.update_session_title(session_id, payload.title)
        if not updated:
            raise HTTPException(status_code=404, detail="Session not found")
        session = await store.get_session(session_id)
        return {"session": session}


@router.delete("/{session_id}")
async def delete_session(session_id: str,
    u: str = Query(default="", description="H5 用户标识（?u=），隔离到该用户的会话库"),
    code: str = Query(default="", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    # R5批⑫（清单安全）：写端点补 H5 用户隔离（对齐读端点范式）——原仅凭 session_id 即可跨用户改/删
    with user_context(h5_user_guarded(u, code, x_access_code)):
        store = get_session_store()
        deleted = await store.delete_session(session_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
        try:
            await get_attachment_store().delete_session(session_id)
        except Exception:
            logger.exception("failed to clean up attachments for session %s", session_id)
        return {"deleted": True, "session_id": session_id}


@router.put("/{session_id}/branch-selection")
async def update_branch_selection(session_id: str, payload: BranchSelectionRequest,
    u: str = Query(default="", description="H5 用户标识（?u=），隔离到该用户的会话库"),
    code: str = Query(default="", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    # R5批⑫（清单安全）：写端点补 H5 用户隔离（对齐读端点范式）——原仅凭 session_id 即可跨用户改/删
    with user_context(h5_user_guarded(u, code, x_access_code)):
        store = get_sqlite_session_store()
        session = await store.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        updated = await store.update_session_preferences(
            session_id, {"selected_branches": dict(payload.selected_branches)}
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"selected_branches": payload.selected_branches}


@router.delete("/{session_id}/messages/{message_id}")
async def delete_turn_by_message(session_id: str, message_id: int,
    u: str = Query(default="", description="H5 用户标识（?u=），隔离到该用户的会话库"),
    code: str = Query(default="", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    # R5批⑫（清单安全）：写端点补 H5 用户隔离（对齐读端点范式）——原仅凭 session_id 即可跨用户改/删
    with user_context(h5_user_guarded(u, code, x_access_code)):
        store = get_sqlite_session_store()
        result = await store.delete_turn_by_message(session_id, message_id)
        if result["was_running"]:
            raise HTTPException(
                status_code=409, detail="Cannot delete a message while its turn is running"
            )
        if not result["deleted"]:
            raise HTTPException(status_code=404, detail="Message not found")
        attachment_store = get_attachment_store()
        for aid in result["attachment_ids"]:
            try:
                await attachment_store.delete_attachment(session_id, aid)
            except Exception:
                logger.exception("failed to delete attachment %s for session %s", aid, session_id)
        return result


@router.post("/{session_id}/quiz-results")
async def record_quiz_results(session_id: str, payload: QuizResultsRequest,
    u: str = Query(default="", description="H5 用户标识（?u=），隔离到该用户的会话库"),
    code: str = Query(default="", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    # R5批⑫（清单安全）：写端点补 H5 用户隔离（对齐读端点范式）——原仅凭 session_id 即可跨用户改/删
    with user_context(h5_user_guarded(u, code, x_access_code)):
        if not payload.answers:
            raise HTTPException(status_code=400, detail="Quiz results are required")
        store = get_sqlite_session_store()
        session = await store.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        content = _format_quiz_results_message(payload.answers)
        await store.add_message(
            session_id=session_id,
            role="user",
            content=content,
            capability="deep_question",
        )
        notebook_count = 0
        try:
            notebook_count = await store.upsert_notebook_entries(
                session_id,
                [{**item.model_dump(), "turn_id": payload.turn_id} for item in payload.answers],
            )
        except Exception:
            logger.warning(
                "Failed to upsert notebook entries for session %s", session_id, exc_info=True
            )
        return {
            "recorded": True,
            "session_id": session_id,
            "answer_count": len(payload.answers),
            "notebook_count": notebook_count,
            "content": content,
        }
