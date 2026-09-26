# -*- coding: utf-8 -*-
"""h5 会话持久化 PG store（切换 R6/Wave2-4b）——vendor sqlite_session_store 的平台替换。

修两笔账：
1. 写读两张皮：桥（dt_agent_capabilities h5 块）此前写 per-user sqlite，而读侧
   /api/v1/sessions（sishu_sessions.py）读 PG sishu_sessions 四表族——h5 历史对
   管理面 API 不可见。本件直写同族 PG 表，读写合流。
2. turn_id 错位：sqlite create_turn 自造 id，桥以「外层 turn_id」调 append_turn_event
   → Turn not found 被吞→turn/事件持久化静默失败。本件 create_turn 接受调用方
   turn_id（平台语义），事件落账真实生效。

作用域：user_id 取 ?u= 绑定（scope.user_id，mq_store/sishu_sessions 同款惯例）——
store 零参数感知，h5_ctx 进入后实例化即落在正确隔离域。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from app.services.sishu_data.pg import engine


def _scope_user() -> str:
    from app.services.sishu.compat.context import get_current_user_or_none

    cu = get_current_user_or_none()
    if cu is None:
        return "local-admin"
    return getattr(getattr(cu, "scope", None), "user_id", "") or "local-admin"


def _next_seq(c, table: str, col: str, key: str, val: str) -> int:
    row = c.execute(text(f"SELECT COALESCE(MAX({col}), 0) AS s FROM {table} WHERE {key}=:k"),
                    {"k": val}).mappings().first()
    return int(row["s"] if row else 0) + 1


class H5PgSessionStore:
    """vendor SQLiteSessionStore h5 消费面（6 方法）的 PG 同族表实现。"""

    async def get_messages(self, session_id: str) -> List[Dict[str, Any]]:
        with engine.connect() as c:
            rows = c.execute(text(
                "SELECT id, role, content, payload FROM sishu_messages "
                "WHERE session_id=:s ORDER BY seq"), {"s": session_id}).mappings().all()
        return [{"id": r["id"], "role": r["role"], "content": r["content"] or "",
                 "attachments": (r["payload"] or {}).get("attachments") or []} for r in rows]

    async def delete_message(self, message_id: int | str) -> bool:
        with engine.begin() as c:
            n = c.execute(text("DELETE FROM sishu_messages WHERE id=:m"),
                          {"m": int(message_id)}).rowcount
        return n > 0

    async def create_session(self, title: str = "", session_id: Optional[str] = None,
                             expert_id: str = "sishu") -> str:
        sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        with engine.begin() as c:
            exists = c.execute(text("SELECT 1 FROM sishu_sessions WHERE session_id=:s"),
                               {"s": sid}).first()
            if exists:
                c.execute(text("UPDATE sishu_sessions SET title=:t, updated_at=now() "
                               "WHERE session_id=:s"), {"t": title, "s": sid})
            else:
                c.execute(text(
                    "INSERT INTO sishu_sessions (session_id, user_id, expert_id, title, "
                    "created_at, updated_at) VALUES (:s, :u, :e, :t, now(), now())"),
                    {"s": sid, "u": _scope_user(), "e": expert_id, "t": title})
        return sid

    async def create_turn(self, session_id: str, capability: str = "",
                          turn_id: Optional[str] = None) -> str:
        tid = turn_id or f"turn_{uuid.uuid4().hex[:12]}"
        with engine.begin() as c:
            # 旧 sqlite 时代会话不在 PG——自动补建会话行（迁移容错；title 空）
            owned = c.execute(text("SELECT 1 FROM sishu_sessions WHERE session_id=:s"),
                              {"s": session_id}).first()
            if not owned:
                c.execute(text(
                    "INSERT INTO sishu_sessions (session_id, user_id, expert_id, title, "
                    "created_at, updated_at) VALUES (:s, :u, 'sishu', '', now(), now())"),
                    {"s": session_id, "u": _scope_user()})
            c.execute(text(
                "INSERT INTO sishu_turns (turn_id, session_id, seq, payload, created_at, updated_at) "
                "VALUES (:t, :s, :q, CAST(:p AS JSONB), now(), now())"),
                {"t": tid, "s": session_id,
                 "q": _next_seq(c, "sishu_turns", "seq", "session_id", session_id),
                 "p": json.dumps({"capability": capability})})
        return tid

    async def add_message(self, session_id: str, role: str, content: str,
                          capability: str = "", attachments: Optional[list] = None) -> int:
        payload = {"capability": capability, "attachments": attachments or []}
        with engine.begin() as c:
            row = c.execute(text(
                "INSERT INTO sishu_messages (session_id, seq, role, content, payload, created_at) "
                "VALUES (:s, :q, :r, :c, CAST(:p AS JSONB), now()) RETURNING id"),
                {"s": session_id, "q": _next_seq(c, "sishu_messages", "seq", "session_id", session_id),
                 "r": role, "c": content, "p": json.dumps(payload, ensure_ascii=False)}).mappings().first()
            c.execute(text("UPDATE sishu_sessions SET updated_at=now() WHERE session_id=:s"),
                      {"s": session_id})
        return int(row["id"]) if row else 0

    async def append_turn_event(self, turn_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        with engine.begin() as c:
            owned = c.execute(text("SELECT 1 FROM sishu_turns WHERE turn_id=:t"),
                              {"t": turn_id}).first()
            if not owned:
                raise ValueError(f"Turn not found: {turn_id}")
            seq = _next_seq(c, "sishu_turn_events", "seq", "turn_id", turn_id)
            row = c.execute(text(
                "INSERT INTO sishu_turn_events (turn_id, seq, event_type, payload, created_at) "
                "VALUES (:t, :q, :et, CAST(:p AS JSONB), now()) RETURNING id"),
                {"t": turn_id, "q": seq,
                 "et": str(event.get("type") or ""),
                 "p": json.dumps(event, ensure_ascii=False, default=str)}).mappings().first()
        return {"id": int(row["id"]) if row else 0, "seq": seq}


def get_h5_pg_session_store() -> H5PgSessionStore:
    return H5PgSessionStore()
