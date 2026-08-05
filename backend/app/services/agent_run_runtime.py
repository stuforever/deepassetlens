from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Callable, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from app.models.base import LLMConnectionConfig
from app.models.scheduler import AgentRun, Conversation, ConversationMessage, RunEvent
from app.core.database import SessionLocal
from app.services.llm_client import call_openai_compatible_messages, get_active_planner_config
from app.services.query_entity_service import build_metadata_from_system


DEFAULT_LLM_CHAT_PAGE = "llmchat"
DEFAULT_LLM_CHAT_SCENE = "llm_chat"

DEFAULT_WORKSPACE_CODE = "default_workspace"


def _now() -> datetime:
    return datetime.utcnow()


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_metadata_source(value: Any) -> str:
    source = _safe_text(value).lower()
    return "manual" if source == "manual" else "system"


def _new_code(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _serialize_dt(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _dedupe_keep_order(values: List[str]) -> List[str]:
    seen = set()
    ordered: List[str] = []
    for item in values:
        text = _safe_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        ordered.append(text)
    return ordered


def _extract_recent_topics(messages: List[str], limit: int = 6) -> List[str]:
    topics: List[str] = []
    for content in messages[-8:]:
        text = _safe_text(content)
        if not text:
            continue
        chunks = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,16}", text)
        if not chunks:
            chunks = [text[:16]]
        topics.extend(chunks[:4])
    return _dedupe_keep_order(topics)[:limit]


def _chunk_text(text: str, chunk_size: int = 24) -> List[str]:
    raw = _safe_text(text)
    if not raw:
        return []
    units = re.split(r"(?<=[。！？!?,，；;\n])", raw)
    chunks: List[str] = []
    current = ""
    for unit in units:
        piece = unit or ""
        if not piece:
            continue
        if len(current) + len(piece) <= chunk_size:
            current += piece
        else:
            if current:
                chunks.append(current)
            current = piece
    if current:
        chunks.append(current)
    if not chunks:
        chunks = [raw[i : i + chunk_size] for i in range(0, len(raw), chunk_size)]
    return chunks


def _append_event(
    db: Session,
    *,
    run: AgentRun,
    event_order: int,
    event_type: str,
    payload: Optional[Dict[str, Any]] = None,
    step_id: Optional[str] = None,
) -> int:
    event = RunEvent(
        run_id=run.id,
        event_code=_new_code("evt"),
        event_type=event_type,
        event_order=event_order,
        step_id=step_id,
        payload=payload or {},
    )
    db.add(event)
    db.flush()
    return event_order + 1


def _append_block_events(
    db: Session,
    *,
    run: AgentRun,
    event_order: int,
    block_id: str,
    block_type: str,
    title: str,
    chunks: List[str],
    data: Optional[Dict[str, Any]] = None,
) -> int:
    event_order = _append_event(
        db,
        run=run,
        event_order=event_order,
        event_type="block.started",
        payload={
            "block_id": block_id,
            "block_type": block_type,
            "title": title,
            "data": data or {},
        },
    )
    cumulative = ""
    for index, delta in enumerate(chunks):
        cumulative += delta
        event_order = _append_event(
            db,
            run=run,
            event_order=event_order,
            event_type="block.delta",
            payload={
                "block_id": block_id,
                "block_type": block_type,
                "title": title,
                "delta": delta,
                "text": cumulative,
                "index": index,
            },
        )
    event_order = _append_event(
        db,
        run=run,
        event_order=event_order,
        event_type="block.completed",
        payload={
            "block_id": block_id,
            "block_type": block_type,
            "title": title,
            "text": cumulative,
            "data": data or {},
        },
    )
    return event_order


def create_conversation(
    db: Session,
    *,
    scene_code: Optional[str] = None,
    page_code: Optional[str] = None,
    title: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Conversation:
    conversation = Conversation(
        conversation_code=_new_code("conv"),
        scene_code=_safe_text(scene_code) or None,
        page_code=_safe_text(page_code) or None,
        title=_safe_text(title) or None,
        conversation_meta=metadata or {},
        status="active",
        last_message_at=_now(),
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def add_conversation_message(
    db: Session,
    *,
    conversation_id: str,
    role: str,
    content: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> ConversationMessage:
    message = ConversationMessage(
        conversation_id=conversation_id,
        message_code=_new_code("msg"),
        role=_safe_text(role) or "assistant",
        content=_safe_text(content) or None,
        payload=payload or {},
    )
    db.add(message)
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation:
        conversation.last_message_at = _now()
    db.commit()
    db.refresh(message)
    return message


def _get_conversation(db: Session, conversation_id: Optional[str]) -> Optional[Conversation]:
    if not conversation_id:
        return None
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()


def _build_session_memory(history_rows: List[ConversationMessage]) -> Dict[str, Any]:
    user_messages = [_safe_text(item.content) for item in history_rows if _safe_text(item.role) == "user" and _safe_text(item.content)]
    assistant_messages = [_safe_text(item.content) for item in history_rows if _safe_text(item.role) == "assistant" and _safe_text(item.content)]
    recent_user_messages = user_messages[-5:]
    recent_assistant_messages = assistant_messages[-3:]
    recent_topics = _extract_recent_topics(recent_user_messages + recent_assistant_messages)
    return {
        "turn_count": len(user_messages),
        "message_count": len(history_rows),
        "recent_user_messages": recent_user_messages,
        "recent_assistant_messages": recent_assistant_messages,
        "recent_topics": recent_topics,
        "last_user_message": recent_user_messages[-1] if recent_user_messages else None,
        "last_assistant_message": recent_assistant_messages[-1] if recent_assistant_messages else None,
    }


def _build_runtime_context(
    *,
    run: AgentRun,
    conversation: Optional[Conversation],
    payload: Dict[str, Any],
    user_query: str,
    session_memory: Dict[str, Any],
) -> Dict[str, Any]:
    conversation_meta = (conversation.conversation_meta or {}) if conversation else {}
    workspace_code = (
        _safe_text(payload.get("workspace_code"))
        or _safe_text(conversation_meta.get("workspace_code"))
        or _safe_text(run.page_code)
        or DEFAULT_WORKSPACE_CODE
    )
    return {
        "protocol_version": "runtime_context_v1",
        "scene_code": run.scene_code,
        "page_code": run.page_code,
        "workspace": {
            "workspace_code": workspace_code,
            "page_code": run.page_code,
            "scene_code": run.scene_code,
        },
        "session": {
            "conversation_id": str(conversation.id) if conversation else None,
            "conversation_code": conversation.conversation_code if conversation else None,
            "title": conversation.title if conversation else None,
            "status": conversation.status if conversation else None,
            "last_message_at": _serialize_dt(conversation.last_message_at) if conversation else None,
        },
        "request": {
            "message": user_query,
            "entry_type": run.entry_type,
            "target_type": run.target_type,
            "target_code": run.target_code,
        },
        "memory": session_memory,
        "capabilities": {
            "supports_event_stream": True,
            "supports_cards": True,
            "supports_step_trace": False,
            "supports_multi_turn": True,
        },
    }


def _update_conversation_memory(
    db: Session,
    *,
    conversation: Optional[Conversation],
    session_memory: Dict[str, Any],
    runtime_context: Dict[str, Any],
) -> None:
    if not conversation:
        return
    meta = dict(conversation.conversation_meta or {})
    meta["session_memory"] = session_memory
    meta["last_runtime_context"] = runtime_context
    meta["updated_at"] = _serialize_dt(_now())
    conversation.conversation_meta = meta
    db.commit()
    db.refresh(conversation)


def _update_conversation_meta(
    db: Session,
    *,
    conversation: Optional[Conversation],
    patch: Dict[str, Any],
) -> None:
    if not conversation:
        return
    meta = dict(conversation.conversation_meta or {})
    meta.update(patch)
    meta["updated_at"] = _serialize_dt(_now())
    conversation.conversation_meta = meta
    db.commit()
    db.refresh(conversation)


def _unique_ordered(values: List[str]) -> List[str]:
    return _dedupe_keep_order(values)


def _contains_any(text: str, items: List[str]) -> bool:
    raw = _safe_text(text)
    return any(item in raw for item in items if _safe_text(item))


def _looks_like_new_query(text: str) -> bool:
    return bool(re.search(r"(查询|查下|查看|统计|分析|列出|展示|帮我查|帮我看)", _safe_text(text)))


def _build_clarification_card(
    *,
    question: str,
    slot_code: str,
    options: List[Dict[str, Any]],
    hint: Optional[str] = None,
    multi_select: bool = False,
    manual_allowed: bool = True,
) -> Dict[str, Any]:
    return {
        "protocol_version": "card_v1",
        "card_id": _new_code("card"),
        "card_type": "clarification",
        "title": "需要补充信息",
        "summary": question,
        "status": "waiting",
        "data": {
            "question": question,
            "slot_code": slot_code,
            "hint": hint,
            "multi_select": bool(multi_select),
            "manual_allowed": bool(manual_allowed),
            "options": [
                {
                    "label": _safe_text(item.get("label")),
                    "value": _safe_text(item.get("value") or item.get("label")),
                    "description": _safe_text(item.get("description")),
                    "submit_value": _safe_text(item.get("submit_value") or item.get("value") or item.get("label")),
                }
                for item in options
                if _safe_text(item.get("label") or item.get("value"))
            ],
        },
    }


def _build_clarification_output(
    *,
    response_type: str,
    runtime_context: Dict[str, Any],
    assistant_text: str,
    card: Dict[str, Any],
    scene_state: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "protocol_version": "run_response_v1",
        "response_type": response_type,
        "assistant_text": assistant_text,
        "cards": [card],
        "runtime_context": runtime_context or {},
        "scene_state": scene_state,
    }


def _compose_resumed_query(
    *,
    original_query: str,
    slot_code: str,
    answer_text: str,
    question: Optional[str] = None,
) -> str:
    value = _safe_text(answer_text)
    slot_prompts = {
        "target_l2": f"补充说明：客户类型为{value}",
        "target_l2x": f"补充说明：目标主数据实体为{value}",
        "target_l4x": f"补充说明：目标业务活动实体为{value}",
    }
    extra = slot_prompts.get(slot_code) or f"补充说明：{_safe_text(question) or '用户补充回答'}为{value}"
    return f"{_safe_text(original_query)}。{extra}"


def _compose_attribute_resumed_query(
    *,
    original_query: str,
    slot_code: str,
    answer_text: str,
    question: Optional[str] = None,
) -> str:
    value = _safe_text(answer_text)
    slot_prompts = {
        "target_l2": f"补充说明：目标主数据小类为{value}",
        "target_l2x": f"补充说明：目标主数据实体为{value}",
        "target_l4x": f"补充说明：目标业务活动实体为{value}",
        "attribute_scope": f"补充说明：属性范围为{value}",
        "attribute_disambiguation": f"补充说明：属性具体指代为{value}",
    }
    extra = slot_prompts.get(slot_code) or f"补充说明：{_safe_text(question) or '用户补充回答'}为{value}"
    return f"{_safe_text(original_query)}。{extra}"


def resolve_run_target(
    *,
    scene_code: Optional[str],
    page_code: Optional[str],
    target_code: Optional[str] = None,
) -> Dict[str, Any]:
    scene = _safe_text(scene_code) or None
    page = _safe_text(page_code) or None
    target = _safe_text(target_code) or None

    if target:
        return {
            "scene_code": scene,
            "page_code": page,
            "entry_type": "workflow",
            "target_type": "workflow",
            "target_code": target,
        }

    if page == DEFAULT_LLM_CHAT_PAGE or scene == DEFAULT_LLM_CHAT_SCENE:
        return {
            "scene_code": DEFAULT_LLM_CHAT_SCENE,
            "page_code": DEFAULT_LLM_CHAT_PAGE,
            "entry_type": "agent",
            "target_type": "llm_chat",
            "target_code": None,
        }

    raise ValueError("当前仅支持 llmchat/llm_chat 场景")


def create_agent_run(
    db: Session,
    *,
    conversation_id: Optional[str],
    scene_code: Optional[str],
    page_code: Optional[str],
    message: Optional[str],
    input_payload: Optional[Dict[str, Any]],
    target_code: Optional[str] = None,
) -> AgentRun:
    target = resolve_run_target(scene_code=scene_code, page_code=page_code, target_code=target_code)
    payload = input_payload.copy() if isinstance(input_payload, dict) else {}
    if _safe_text(message) and "user_query" not in payload:
        payload["user_query"] = _safe_text(message)
    run = AgentRun(
        run_code=_new_code("run"),
        conversation_id=conversation_id,
        scene_code=target["scene_code"],
        page_code=target["page_code"],
        entry_type=target["entry_type"],
        target_type=target["target_type"],
        target_code=target.get("target_code"),
        status="pending",
        input_payload={
            "message": _safe_text(message) or None,
            "input_payload": payload,
        },
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def _build_rich_text_card(*, title: str, text: str, summary: Optional[str] = None, status: str = "success") -> Dict[str, Any]:
    return {
        "protocol_version": "card_v1",
        "card_id": _new_code("card"),
        "card_type": "rich_text",
        "title": title,
        "summary": summary or text[:120],
        "status": status,
        "data": {
            "text": text,
            "format": "markdown",
        },
    }


def _resolve_llm_connection(db: Session, preferred_connection_id: Optional[str]) -> LLMConnectionConfig:
    items = db.query(LLMConnectionConfig).all()
    preferred = _safe_text(preferred_connection_id)
    if preferred:
        hit = next((x for x in items if str(x.id) == preferred and x.enabled), None)
        if hit:
            return hit
        raise ValueError("指定的大模型连接不存在或未启用")

    planner = get_active_planner_config(db)
    planner_conn_id = str(getattr(planner, "llm_connection_id", "") or "").strip() if planner else ""
    if planner_conn_id:
        hit = next((x for x in items if str(x.id) == planner_conn_id and x.enabled), None)
        if hit:
            return hit

    default_conn = next((x for x in items if getattr(x, "is_default", False) and x.enabled), None)
    if default_conn:
        return default_conn

    first_enabled = next((x for x in items if x.enabled), None)
    if first_enabled:
        return first_enabled

    raise ValueError("未找到可用的大模型连接，请先在配置管理中启用一个模型连接")


def _query_conversation_history(db: Session, conversation_id: Optional[str]) -> List[ConversationMessage]:
    if not conversation_id:
        return []
    return (
        db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )


def _build_llm_chat_output(
    *,
    answer: str,
    connection: LLMConnectionConfig,
    system_prompt: str,
    conversation_id: Optional[str],
    runtime_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    card = _build_rich_text_card(
        title="模型回复",
        text=answer,
        summary=f"{connection.name} / {connection.model_name}",
    )
    return {
        "protocol_version": "run_response_v1",
        "response_type": "llm_chat",
        "assistant_text": answer,
        "cards": [card],
        "answer": answer,
        "connection": {
            "id": str(connection.id),
            "name": connection.name,
            "provider": connection.provider,
            "model_name": connection.model_name,
        },
        "system_prompt": system_prompt,
        "conversation_id": conversation_id,
        "runtime_context": runtime_context or {},
    }


def execute_agent_run(db: Session, run: AgentRun) -> AgentRun:
    input_wrapper = run.input_payload or {}
    payload = (input_wrapper.get("input_payload") or {}) if isinstance(input_wrapper, dict) else {}
    user_query = _safe_text((payload or {}).get("user_query") or input_wrapper.get("message"))
    if not user_query:
        raise ValueError("统一 Run API 执行失败：缺少 user_query/message")

    run.status = "running"
    run.started_at = _now()
    if run.conversation_id:
        add_conversation_message(
            db,
            conversation_id=run.conversation_id,
            role="user",
            content=user_query,
            payload={"run_code": run.run_code},
        )
        db.refresh(run)
    else:
        db.commit()

    conversation = _get_conversation(db, run.conversation_id)
    history_rows_before = _query_conversation_history(db, run.conversation_id)
    session_memory_before = _build_session_memory(history_rows_before)
    runtime_context = _build_runtime_context(
        run=run,
        conversation=conversation,
        payload=payload,
        user_query=user_query,
        session_memory=session_memory_before,
    )

    event_order = 1
    event_order = _append_event(
        db,
        run=run,
        event_order=event_order,
        event_type="run.started",
        payload={
            "run_code": run.run_code,
            "scene_code": run.scene_code,
            "page_code": run.page_code,
            "message": user_query,
        },
    )
    event_order = _append_event(
        db,
        run=run,
        event_order=event_order,
        event_type="context.prepared",
        payload={"runtime_context": runtime_context},
    )
    context_summary = (
        f"场景：{run.scene_code or '-'}\n"
        f"页面：{run.page_code or '-'}\n"
        f"工作区：{((runtime_context.get('workspace') or {}).get('workspace_code')) or '-'}\n"
        f"会话轮数：{((runtime_context.get('memory') or {}).get('turn_count')) or 0}\n"
        f"近期话题：{'、'.join(((runtime_context.get('memory') or {}).get('recent_topics')) or []) or '无'}"
    )
    event_order = _append_block_events(
        db,
        run=run,
        event_order=event_order,
        block_id=_new_code("blk"),
        block_type="context",
        title="运行时上下文",
        chunks=[context_summary],
        data={"runtime_context": runtime_context},
    )
    db.commit()

    try:
        final_payload: Dict[str, Any]
        if run.page_code == DEFAULT_LLM_CHAT_PAGE or run.scene_code == DEFAULT_LLM_CHAT_SCENE:
            connection, system_prompt, _ = _resolve_llm_connection(db, payload)
            answer = _invoke_llm_with_fallback(db, connection, system_prompt, user_query)
            final_payload = _build_llm_chat_output(
                connection=connection,
                answer=answer,
                system_prompt=system_prompt,
                conversation_id=run.conversation_id,
                runtime_context=runtime_context,
            )
        else:
            raise ValueError("当前仅支持 llmchat/llm_chat 场景")

        history_rows_after = _query_conversation_history(db, run.conversation_id)
        session_memory_after = _build_session_memory(history_rows_after)
        _update_conversation_memory(
            db,
            conversation=conversation,
            session_memory=session_memory_after,
            runtime_context=runtime_context,
        )
        run.status = "completed"
        run.completed_at = _now()
        run.output_payload = {
            **(run.output_payload or {}),
            "response_type": final_payload.get("response_type"),
            "final_result": final_payload.get("final_result"),
            "result_panels": final_payload.get("result_panels"),
            "cards": final_payload.get("cards"),
            "assistant_text": final_payload.get("assistant_text"),
            "llm_error": final_payload.get("llm_error"),
            "step_trace": final_payload.get("step_trace"),
            "runtime_context": final_payload.get("runtime_context"),
            "execution_code": final_payload.get("execution_code"),
        }
        db.commit()
        db.refresh(run)

        if run.conversation_id:
            add_conversation_message(
                db,
                conversation_id=run.conversation_id,
                role="assistant",
                content=final_payload.get("assistant_text") or "统一 Run Runtime 已完成执行。",
                payload=final_payload,
            )
            db.refresh(run)
        return run
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)
        run.completed_at = _now()
        _append_event(
            db,
            run=run,
            event_order=event_order,
            event_type="run.failed",
            payload={"message": str(exc)},
        )
        db.commit()
        raise


def execute_agent_run_by_id(run_id: str) -> None:
    with SessionLocal() as db:
        run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
        if not run:
            return
        try:
            execute_agent_run(db, run)
        except Exception:
            # 错误已在 execute_agent_run 中落库为 run.failed
            pass
