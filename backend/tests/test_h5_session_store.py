# -*- coding: utf-8 -*-
"""h5 会话 PG store 测试（R6/Wave2-4b）：六方法往返 + 读侧同源 + turn_id 平台语义。"""
from __future__ import annotations

import uuid

import pytest

from app.services.learning import h5_session_store as hs


@pytest.fixture()
def store(monkeypatch):
    monkeypatch.setattr(hs, "_scope_user", lambda: "h5_test_user")
    return hs.H5PgSessionStore()


def _cleanup(sid):
    from app.services.sishu_data.pg import engine
    from sqlalchemy import text
    with engine.begin() as c:
        c.execute(text("DELETE FROM sishu_turn_events WHERE turn_id IN "
                       "(SELECT turn_id FROM sishu_turns WHERE session_id=:s)"), {"s": sid})
        c.execute(text("DELETE FROM sishu_turns WHERE session_id=:s"), {"s": sid})
        c.execute(text("DELETE FROM sishu_messages WHERE session_id=:s"), {"s": sid})
        c.execute(text("DELETE FROM sishu_sessions WHERE session_id=:s"), {"s": sid})


def test_full_roundtrip(store):
    sid = f"sess_test_{uuid.uuid4().hex[:8]}"
    try:
        # 建会话+turn+user 消息
        out_sid = asyncio_run(store.create_session(title="测试会话", session_id=sid))
        assert out_sid == sid
        tid = asyncio_run(store.create_turn(sid, capability="sishu/chat", turn_id="turn_test1"))
        assert tid == "turn_test1"  # 平台语义：接受调用方 turn_id
        mid = asyncio_run(store.add_message(sid, "user", "解一道方程",
                                            capability="sishu/chat", attachments=[{"t": 1}]))
        assert mid > 0
        # 事件落账（旧 sqlite 形态在此静默失败——Turn not found 被吞）
        ev = asyncio_run(store.append_turn_event("turn_test1",
                                                 {"type": "content", "content": "x=1"}))
        assert ev["seq"] >= 1 and ev["id"] > 0
        # get_messages 往返
        msgs = asyncio_run(store.get_messages(sid))
        assert msgs[0]["role"] == "user" and "方程" in msgs[0]["content"]
        assert msgs[0]["attachments"] == [{"t": 1}]
        # assistant 收尾+删除消息（regen 语义）
        asyncio_run(store.add_message(sid, "assistant", "x=1"))
        msgs = asyncio_run(store.get_messages(sid))
        assert asyncio_run(store.delete_message(msgs[-1]["id"])) is True
        assert len(asyncio_run(store.get_messages(sid))) == 1
        # 读侧同源：sishu_sessions.py 同族表可见（user_id 隔离正确）
        from sqlalchemy import text
        from app.services.sishu_data.pg import engine
        with engine.connect() as c:
            row = c.execute(text("SELECT user_id, title FROM sishu_sessions WHERE session_id=:s"),
                            {"s": sid}).mappings().first()
        assert row["user_id"] == "h5_test_user" and row["title"] == "测试会话"
    finally:
        _cleanup(sid)


def test_create_turn_autocreates_missing_session(store):
    """旧 sqlite 时代会话不在 PG——create_turn 自动补建（迁移容错）。"""
    sid = f"sess_legacy_{uuid.uuid4().hex[:8]}"
    try:
        tid = asyncio_run(store.create_turn(sid, capability="sishu/quiz"))
        assert tid
        from sqlalchemy import text
        from app.services.sishu_data.pg import engine
        with engine.connect() as c:
            row = c.execute(text("SELECT user_id FROM sishu_sessions WHERE session_id=:s"),
                            {"s": sid}).mappings().first()
        assert row and row["user_id"] == "h5_test_user"
    finally:
        _cleanup(sid)


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)
