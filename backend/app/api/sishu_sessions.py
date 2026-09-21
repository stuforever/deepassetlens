# -*- coding: utf-8 -*-
"""三轨M14(批8) 8.1：平台会话族 REST——vendor sessions.py 端点面 1:1（PG sishu_sessions/
messages/turns/turn_events 四表族）。?u= 语义=sishu_user_binding 单点（协议 F②）。
生成面（流式/turn 写入）仍走批1-5 编排桥；本件承接管理面 CRUD。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.services.sishu.compat.context import get_current_user_or_none
from app.services.sishu_data.pg import engine

router = APIRouter()


def _scope_user() -> str:
    """?u= 隔离——vendor 经 user_context 切库，PG 换 user_id 列（同 mq 惯例）。"""
    cu = get_current_user_or_none()
    if cu is None:
        return "local-admin"
    return getattr(getattr(cu, "scope", None), "user_id", "") or "local-admin"


@router.get("")
def list_sessions(limit: int = Query(default=50, ge=1, le=200),
                  offset: int = Query(default=0, ge=0)):
    u = _scope_user()
    with engine.connect() as c:
        rows = c.execute(text("""
            SELECT session_id, title, created_at, updated_at
            FROM sishu_sessions WHERE user_id=:u
            ORDER BY updated_at DESC LIMIT :l OFFSET :o"""),
            {"u": u, "l": limit, "o": offset}).mappings().all()
    return {"sessions": [
        {"id": r["session_id"], "title": r["title"] or "",
         "created_at": r["created_at"].timestamp() if r["created_at"] else 0,
         "updated_at": r["updated_at"].timestamp() if r["updated_at"] else 0}
        for r in rows
    ]}


@router.get("/{session_id}")
def get_session(session_id: str):
    u = _scope_user()
    with engine.connect() as c:
        sess = c.execute(text(
            "SELECT session_id, title, created_at, updated_at FROM sishu_sessions "
            "WHERE session_id=:s AND user_id=:u"), {"s": session_id, "u": u}).mappings().first()
        if not sess:
            raise HTTPException(404, "会话不存在")
        msgs = c.execute(text("""
            SELECT role, content, payload, seq FROM sishu_messages
            WHERE session_id=:s ORDER BY seq"""), {"s": session_id}).mappings().all()
    return {
        "session": {"id": sess["session_id"], "title": sess["title"] or "",
                    "created_at": sess["created_at"].timestamp() if sess["created_at"] else 0,
                    "updated_at": sess["updated_at"].timestamp() if sess["updated_at"] else 0},
        "messages": [
            {"role": m["role"], "content": m["content"] or "",
             "payload": m["payload"] or {}, "seq": m["seq"]}
            for m in msgs
        ],
    }


class SessionRename(BaseModel):
    title: str


@router.patch("/{session_id}")
def rename_session(session_id: str, body: SessionRename):
    u = _scope_user()
    with engine.begin() as c:
        n = c.execute(text(
            "UPDATE sishu_sessions SET title=:t, updated_at=now() "
            "WHERE session_id=:s AND user_id=:u"), {"t": body.title, "s": session_id, "u": u}).rowcount
    if not n:
        raise HTTPException(404, "会话不存在")
    return {"updated": True}


@router.delete("/{session_id}")
def delete_session(session_id: str):
    u = _scope_user()
    with engine.begin() as c:
        n = c.execute(text("DELETE FROM sishu_sessions WHERE session_id=:s AND user_id=:u"),
                      {"s": session_id, "u": u}).rowcount
    if not n:
        raise HTTPException(404, "会话不存在")
    with engine.begin() as c:
        c.execute(text("DELETE FROM sishu_messages WHERE session_id=:s"), {"s": session_id})
        c.execute(text("DELETE FROM sishu_turns WHERE session_id=:s"), {"s": session_id})
    return {"deleted": True}


class BranchSelection(BaseModel):
    message_id: int
    branch_index: int = 0


@router.put("/{session_id}/branch-selection")
def set_branch_selection(session_id: str, body: BranchSelection):
    return {"ok": True, "session_id": session_id, **body.model_dump()}


@router.delete("/{session_id}/messages/{message_id}")
def delete_message(session_id: str, message_id: int):
    with engine.begin() as c:
        n = c.execute(text("DELETE FROM sishu_messages WHERE id=:m AND session_id=:s"),
                      {"m": message_id, "s": session_id}).rowcount
    if not n:
        raise HTTPException(404, "消息不存在")
    return {"deleted": True}


@router.post("/{session_id}/quiz-results")
def save_quiz_result(session_id: str, payload: dict = None):
    return {"ok": True, "session_id": session_id, "stored": False,
            "note": "quiz-results 走批4 判题桥持久化，本端点为 vendor 契约占位"}
