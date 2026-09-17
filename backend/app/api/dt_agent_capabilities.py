# -*- coding: utf-8 -*-
"""引擎批1：deepagent 桥端点 POST /api/v2/skills/capability（SSE）。
SSE 回 DT StreamEvent 形状（frontend/src/lib/unified-ws.ts L18-44 十四型逐字段）——
前端 30+ 复刻件契约零改（批2 AgentChatContext/批6 H5Chat 消费同一端点）。
h5_user 存在→会话记录写 vendor session store（批6 接线）；SkillExecLog 记派发。
台账登记：SkillExecLog.created_via='agent'（模型 CheckConstraint 白名单
manual/agent/workflow/schedule/debug——计划模板 'bridge' 违约修正）。"""
import json
import time
import uuid
from datetime import datetime as _dt
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..core.database import SessionLocal
from ..models.skill import Skill, SkillExecLog, SkillVersion

router = APIRouter(prefix="/api/v2/skills")


class CapabilityRequest(BaseModel):
    skill_code: str                       # "tutor/chat" 等 8 技能
    action: Optional[str] = None          # quiz: "judge"（批4）
    session_id: Optional[str] = None
    message: str
    config: Dict[str, Any] = {}
    tools: List[str] = []
    knowledge_bases: List[str] = []
    attachments: List[Dict[str, Any]] = []
    history_references: List[Dict[str, Any]] = []
    h5_user: Optional[str] = None         # h5 端用户隔离（批6 消费）


def _evt(type_, source, stage, content="", metadata=None, session_id=None,
         turn_id=None, seq=0):
    """DT StreamEvent 十四型逐字段形状（unified-ws.ts L34-44）。"""
    return {"type": type_, "source": source, "stage": stage, "content": content,
            "metadata": metadata or {}, "session_id": session_id, "turn_id": turn_id,
            "seq": seq, "timestamp": time.time()}


@router.post("/capability")
async def capability(req: CapabilityRequest):
    db = SessionLocal()
    log_id = str(uuid.uuid4())
    try:
        skill = db.query(Skill).filter(Skill.skill_code == req.skill_code).first()
        if not skill:
            return _sse_err(log_id, f"未知技能: {req.skill_code}")
        version = db.query(SkillVersion).filter(
            SkillVersion.version_id == skill.current_version_id).first()
        db.add(SkillExecLog(log_id=log_id, skill_id=skill.skill_id,
                            version_id=version.version_id if version else None,
                            execution_code=req.skill_code, input_data=req.model_dump(),
                            status="running", created_via="agent"))
        db.commit()
    finally:
        db.close()

    from .dt_agent_orchestrations import dispatch
    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    turn_id = f"turn_{uuid.uuid4().hex[:12]}"

    async def gen():
        seq = 0
        try:
            async for ev in dispatch(req, session_id, turn_id, user_prefix=_user_prefix(req)):
                ev["seq"] = seq
                seq += 1
                yield f"event: {ev['type']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
            _finish_log(log_id)
        except Exception as e:  # dispatch 抛异常→记账后 error 事件收尾
            _finish_log(log_id, ok=False, err=str(e))
            ev = _evt("error", "bridge", "dispatch", content=str(e),
                      metadata={"log_id": log_id}, session_id=session_id, turn_id=turn_id)
            yield f"event: error\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


def _sse_err(log_id, msg):
    ev = _evt("error", "bridge", "dispatch", content=msg, metadata={"log_id": log_id})
    return StreamingResponse(
        iter([f"event: error\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"]),
        media_type="text/event-stream")


def _finish_log(log_id, ok=True, err=""):
    """SkillExecLog 记派发不记终态语义（诚实账 8：终态证据=会话记录）——
    completed/failed 仅作派发账；内容账由编排事件流与会话记录承载。"""
    db = SessionLocal()
    try:
        row = db.query(SkillExecLog).filter(SkillExecLog.log_id == log_id).first()
        if row:
            row.status = "completed" if ok else "failed"
            row.error_message = err or None
            row.completed_at = _dt.utcnow()
            db.commit()
    finally:
        db.close()


def _user_prefix(req) -> str:
    """h5 端用 h5_user（vendor session store 用户隔离键，批6 消费）；
    桌面端走平台会话（auth=0 匿名=admin——freeplan/endpoint.py L89-91 同款语义）。"""
    if req.h5_user:
        return f"h5:{req.h5_user}"
    return "anonymous"  # ENABLE_AUTH=1 时换 get_current_user(request).sub（B 件语义，本件不动开关）
