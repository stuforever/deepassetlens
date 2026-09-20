# -*- coding: utf-8 -*-
"""引擎批1：deepagent 桥端点 POST /api/v2/skills/capability（SSE）。
SSE 回 DT StreamEvent 形状（frontend/src/lib/unified-ws.ts L18-44 十四型逐字段）——
前端 30+ 复刻件契约零改（批2 AgentChatContext/批6 H5Chat 消费同一端点）。
h5_user 存在→会话记录写 vendor session store（批6 接线）；SkillExecLog 记派发。
台账登记：SkillExecLog.created_via='agent'（模型 CheckConstraint 白名单
manual/agent/workflow/schedule/debug——计划模板 'bridge' 违约修正）。"""
import asyncio
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
    skill_code: str                       # "sishu/chat" 等 8 技能
    action: Optional[str] = None          # quiz: "judge"（批4）
    session_id: Optional[str] = None
    message: str
    config: Dict[str, Any] = {}
    tools: List[str] = []
    knowledge_bases: List[str] = []
    attachments: List[Dict[str, Any]] = []
    history_references: List[Dict[str, Any]] = []
    h5_user: Optional[str] = None         # h5 端用户隔离（批6 消费）
    code: Optional[str] = None            # h5 访问码（P3-B/R4，h5_user_guarded）
    x_access_code: Optional[str] = None   # 访问码头字段等价体（REST 同名 Header）


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
                            execution_code=req.skill_code, input_data=_sanitize_log_input(req.model_dump()),
                            status="running", created_via="agent"))
        db.commit()
    finally:
        db.close()

    from .dt_agent_orchestrations import dispatch
    session_id = req.session_id or f"sess_{uuid.uuid4().hex[:12]}"
    turn_id = f"turn_{uuid.uuid4().hex[:12]}"
    is_regen = (req.config or {}).get("action") == "regenerate"

    async def gen():
        seq = 0
        # 6.2 h5 持久化：h5_user 存在→vendor session store（user_context 隔离键；
        # create_session/create_turn/append_turn_event/add_message 四方法，签名批内对齐）。
        h5_ctx = None
        store = None
        acc: List[str] = []
        final_text = ""
        regen_content = ""
        if req.h5_user:
            try:
                from deeptutor.multi_user.h5 import h5_user_guarded
                from deeptutor.multi_user.paths import user_context
                from deeptutor.services.session.sqlite_store import get_sqlite_session_store
                h5_ctx = user_context(h5_user_guarded(
                    req.h5_user, req.code or "", req.x_access_code or ""))
                h5_ctx.__enter__()
                store = get_sqlite_session_store()
                regen_content = ""
                if is_regen:
                    # DT unified_ws regenerate 语义（regenerate_last_turn）1:1：
                    # 删尾随 assistant 消息→复用最后一条 user 消息作为本轮内容
                    # （不重复落 user 消息；无 user 消息→nothing_to_regenerate）。
                    msgs = await store.get_messages(session_id)
                    while msgs and msgs[-1].get("role") == "assistant":
                        await store.delete_message(msgs[-1]["id"])
                        msgs.pop()
                    last_user = next((m for m in reversed(msgs)
                                      if m.get("role") == "user"), None)
                    if not last_user:
                        raise ValueError("nothing_to_regenerate")
                    regen_content = str(last_user.get("content") or "")
                    # 三轨M2/H8：regenerate 同样开新 turn——后续 append_turn_event(turn_id)
                    # 依赖该行（vendor sqlite 契约：turn 不存在抛 Turn not found）。
                    await store.create_turn(session_id, capability=req.skill_code)
                else:
                    if not req.session_id:
                        await store.create_session(title=(req.message or "新对话")[:40],
                                                   session_id=session_id)
                    await store.create_turn(session_id, capability=req.skill_code)
                    await store.add_message(session_id, "user", req.message,
                                            capability=req.skill_code,
                                            attachments=req.attachments)
            except Exception as e:
                # 三轨M2/H7：已进入的隔离上下文必须先退出再置空（原实现直接置 None
                # 导致 __exit__ 永不被调，用户隔离上下文泄漏到后续请求）。
                if h5_ctx is not None:
                    try:
                        h5_ctx.__exit__(type(e), e, e.__traceback__)
                    except Exception:
                        pass
                h5_ctx = None
                store = None
                ev = _evt("error", "bridge", "session_store", content=f"h5 会话隔离失败: {e}",
                          session_id=session_id, turn_id=turn_id)
                yield f"event: error\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
        try:
            dispatch_req = req
            if is_regen and regen_content:
                dispatch_req = req.model_copy(update={"message": regen_content})
            try:
                async for ev in dispatch(dispatch_req, session_id, turn_id, user_prefix=_user_prefix(req)):
                    ev["seq"] = seq
                    seq += 1
                    if store is not None:
                        try:
                            await store.append_turn_event(turn_id, ev)
                        except Exception:
                            pass
                    if ev.get("type") == "content" and ev.get("content"):
                        acc.append(ev["content"])
                    if ev.get("type") == "result" and ev.get("content"):
                        final_text = ev["content"]
                    yield f"event: {ev['type']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
                _finish_log(log_id)
            except (GeneratorExit, asyncio.CancelledError):
                # 三轨M2/H9：客户端断连（StreamingResponse 关闭生成器在 yield 点抛
                # GeneratorExit/CancelledError，均非 Exception 子类）——记账必达+
                # assistant 收尾消息落库，再 re-raise（GeneratorExit 必须上抛）。
                _finish_log(log_id, ok=False, err="client disconnected")
                try:
                    if store is not None:
                        _text = final_text or "".join(acc)
                        if _text:
                            await store.add_message(session_id, "assistant", _text,
                                                    capability=req.skill_code)
                except Exception:
                    pass
                raise
            except Exception as e:  # dispatch 抛异常→记账后 error 事件收尾
                _finish_log(log_id, ok=False, err=str(e))
                ev = _evt("error", "bridge", "dispatch", content=str(e),
                          metadata={"log_id": log_id}, session_id=session_id, turn_id=turn_id)
                yield f"event: error\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
            if store is not None:
                try:
                    text = final_text or "".join(acc)
                    if text:
                        await store.add_message(session_id, "assistant", text,
                                                capability=req.skill_code)
                except Exception:
                    pass
        finally:
            if h5_ctx is not None:
                try:
                    h5_ctx.__exit__(None, None, None)
                except Exception:
                    pass

    return StreamingResponse(gen(), media_type="text/event-stream")


def _sanitize_log_input(d: dict) -> dict:
    """三轨M2/S6：访问码脱敏后记账——code/x_access_code 掩码，其余字段原样。"""
    out = dict(d or {})
    if out.get("code"):
        out["code"] = "******"
    if out.get("x_access_code"):
        out["x_access_code"] = "******"
    return out


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
