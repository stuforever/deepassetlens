import json
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.models.scheduler import AgentRun, Conversation, ConversationMessage, RunEvent
from app.services.agent_run_runtime import create_agent_run, create_conversation, execute_agent_run, execute_agent_run_by_id


router = APIRouter()


def _serialize_dt(value):
    return value.isoformat() if value else None


def _serialize_conversation(item: Conversation) -> Dict[str, Any]:
    return {
        "id": str(item.id),
        "conversation_code": item.conversation_code,
        "scene_code": item.scene_code,
        "page_code": item.page_code,
        "title": item.title,
        "status": item.status,
        "metadata": item.conversation_meta or {},
        "last_message_at": _serialize_dt(item.last_message_at),
        "created_at": _serialize_dt(item.created_at),
        "updated_at": _serialize_dt(item.updated_at),
    }


def _serialize_message(item: ConversationMessage) -> Dict[str, Any]:
    return {
        "id": str(item.id),
        "message_code": item.message_code,
        "conversation_id": item.conversation_id,
        "role": item.role,
        "content": item.content,
        "payload": item.payload or {},
        "created_at": _serialize_dt(item.created_at),
    }


def _serialize_run(item: AgentRun) -> Dict[str, Any]:
    return {
        "id": str(item.id),
        "run_code": item.run_code,
        "conversation_id": item.conversation_id,
        "scene_code": item.scene_code,
        "page_code": item.page_code,
        "entry_type": item.entry_type,
        "target_type": item.target_type,
        "target_code": item.target_code,
        "workflow_code": item.workflow_code,
        "workflow_execution_code": item.workflow_execution_code,
        "status": item.status,
        "input_payload": item.input_payload or {},
        "output_payload": item.output_payload or {},
        "error_message": item.error_message,
        "started_at": _serialize_dt(item.started_at),
        "completed_at": _serialize_dt(item.completed_at),
        "created_at": _serialize_dt(item.created_at),
        "updated_at": _serialize_dt(item.updated_at),
    }


def _serialize_event(item: RunEvent) -> Dict[str, Any]:
    return {
        "id": str(item.id),
        "event_code": item.event_code,
        "run_id": item.run_id,
        "event_type": item.event_type,
        "event_order": item.event_order,
        "step_id": item.step_id,
        "payload": item.payload or {},
        "created_at": _serialize_dt(item.created_at),
    }


class ConversationCreateRequest(BaseModel):
    scene_code: Optional[str] = None
    page_code: Optional[str] = None
    title: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class RunCreateRequest(BaseModel):
    conversation_id: Optional[str] = None
    scene_code: Optional[str] = Field(default="query_entity")
    page_code: Optional[str] = Field(default="queryentity")
    message: str = Field(..., description="用户消息文本")
    input_payload: Optional[Dict[str, Any]] = None
    target_code: Optional[str] = Field(default=None, description="可选工作流编码；留空时按场景/页面自动路由")
    async_mode: bool = Field(default=True, description="是否异步创建 Run 并后台执行")


@router.post("/conversations", summary="创建统一会话")
def create_conversation_api(request: ConversationCreateRequest, db: Session = Depends(get_db)):
    conversation = create_conversation(
        db,
        scene_code=request.scene_code,
        page_code=request.page_code,
        title=request.title,
        metadata=request.metadata,
    )
    return {"success": True, "data": _serialize_conversation(conversation)}


@router.get("/conversations/{conversation_id}", summary="获取统一会话详情")
def get_conversation(conversation_id: str, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True, "data": _serialize_conversation(conversation)}


@router.get("/conversations/{conversation_id}/messages", summary="获取统一会话消息")
def get_conversation_messages(conversation_id: str, db: Session = Depends(get_db)):
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    messages = (
        db.query(ConversationMessage)
        .filter(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc())
        .all()
    )
    return {"success": True, "data": [_serialize_message(item) for item in messages]}


@router.post("/runs", summary="创建并执行统一 Run")
def create_run_api(request: RunCreateRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not str(request.message or "").strip():
        raise HTTPException(status_code=400, detail="message不能为空")
    try:
        run = create_agent_run(
            db,
            conversation_id=request.conversation_id,
            scene_code=request.scene_code,
            page_code=request.page_code,
            message=request.message,
            input_payload=request.input_payload,
            target_code=request.target_code,
        )
        if request.async_mode:
            background_tasks.add_task(execute_agent_run_by_id, str(run.id))
            db.refresh(run)
            return {"success": True, "data": _serialize_run(run)}
        run = execute_agent_run(db, run)
        return {"success": True, "data": _serialize_run(run)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/runs/{run_id}", summary="获取统一 Run 详情")
def get_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run不存在")
    return {"success": True, "data": _serialize_run(run)}


@router.get("/runs/by-code/{run_code}", summary="按编码获取统一 Run")
def get_run_by_code(run_code: str, db: Session = Depends(get_db)):
    run = db.query(AgentRun).filter(AgentRun.run_code == run_code).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run不存在")
    return {"success": True, "data": _serialize_run(run)}


@router.get("/runs/{run_id}/events", summary="获取统一 Run 事件流")
def get_run_events(run_id: str, since_order: int = 0, db: Session = Depends(get_db)):
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run不存在")
    events = (
        db.query(RunEvent)
        .filter(RunEvent.run_id == run_id)
        .filter(RunEvent.event_order > since_order)
        .order_by(RunEvent.event_order.asc())
        .all()
    )
    return {
        "success": True,
        "data": [_serialize_event(item) for item in events],
        "run_status": run.status,
    }


@router.get("/runs/{run_id}/events/stream", summary="SSE方式读取统一 Run 事件流")
def stream_run_events(run_id: str, since_order: int = 0, db: Session = Depends(get_db)):
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run不存在")
    events = (
        db.query(RunEvent)
        .filter(RunEvent.run_id == run_id)
        .filter(RunEvent.event_order > since_order)
        .order_by(RunEvent.event_order.asc())
        .all()
    )

    def event_iter():
        current_order = since_order
        idle_rounds = 0

        for item in events:
            payload = _serialize_event(item)
            current_order = item.event_order
            yield f"id: {item.event_order}\n"
            yield f"event: {item.event_type}\n"
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        while True:
            with SessionLocal() as stream_db:
                current_run = stream_db.query(AgentRun).filter(AgentRun.id == run_id).first()
                if not current_run:
                    yield "event: stream.error\n"
                    yield f"data: {json.dumps({'run_id': run_id, 'message': 'Run不存在'}, ensure_ascii=False)}\n\n"
                    break

                next_events = (
                    stream_db.query(RunEvent)
                    .filter(RunEvent.run_id == run_id)
                    .filter(RunEvent.event_order > current_order)
                    .order_by(RunEvent.event_order.asc())
                    .all()
                )

                if next_events:
                    idle_rounds = 0
                    for item in next_events:
                        payload = _serialize_event(item)
                        current_order = item.event_order
                        yield f"id: {item.event_order}\n"
                        yield f"event: {item.event_type}\n"
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                else:
                    idle_rounds += 1

                if current_run.status in {"completed", "failed"} and not next_events:
                    yield "event: stream.end\n"
                    yield f"data: {json.dumps({'run_id': run_id, 'run_status': current_run.status}, ensure_ascii=False)}\n\n"
                    break

            if idle_rounds >= 10:
                yield ": keepalive\n\n"
                idle_rounds = 0
            time.sleep(0.5)

    return StreamingResponse(event_iter(), media_type="text/event-stream")
