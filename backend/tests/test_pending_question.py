# -*- coding: utf-8 -*-
"""G1 询问 Future 测试（切换 R1，design §三 G1）：pending_question 注册表 +
ask_user 工具图内暂停/恢复 + run_chat 会话代答 + resume 通道 + 超时路径。"""
from __future__ import annotations

import asyncio

import pytest

from app.services import pending_question as pq


def test_resolve_by_id():
    async def flow():
        qid, fut, tmo = pq.create_question(question="哪个章节？", user_prefix="u", session_id="s1")
        assert pq.pending_for_session("u", "s1") == {"question_id": qid}
        assert pq.resolve(qid, "第三章", source="resume") is True
        result = await fut
        assert result == {"answer": "第三章", "source": "resume"}
        # 幂等：已答再 resolve 返回 False
        assert pq.resolve(qid, "again") is False
        pq.drop_question(qid)
        assert pq.pending_for_session("u", "s1") is None

    asyncio.run(flow())


def test_superseded_replaces_old_question():
    async def flow():
        q1, f1, _ = pq.create_question(question="旧问题", user_prefix="u", session_id="s2")
        q2, f2, _ = pq.create_question(question="新问题", user_prefix="u", session_id="s2")
        r1 = await f1
        assert r1["source"] == "superseded"  # 同会话仅一个活跃问题——旧问题被取代
        assert pq.pending_for_session("u", "s2") == {"question_id": q2}
        pq.drop_question(q2)

    asyncio.run(flow())


def test_timeout_path():
    async def flow():
        qid, fut, _ = pq.create_question(question="?", user_prefix="u", session_id="s3", timeout=0.05)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(fut, timeout=0.1)
        pq.drop_question(qid)

    asyncio.run(flow())


def test_ask_user_tool_roundtrip():
    """ask_user 工具：await 中被 resume 通道解析，答案回流为工具返回值。"""
    from app.services.tupu_deepagent import _ask_user_tool

    async def flow():
        tool = _ask_user_tool()
        task = asyncio.create_task(tool.ainvoke(
            {"question": "要练哪个知识点？", "options": "函数|几何"},
            config={"configurable": {"thread_id": "anonymous:sishu:sess-g1"}}))
        # 工具任务启动后已注册问题（await 点挂起；config 经 RunnableConfig 注入）
        for _ in range(50):
            await asyncio.sleep(0.02)
            info = pq.pending_for_session("anonymous", "sess-g1")
            if info:
                break
        assert info and info["question_id"]
        assert pq.resolve(info["question_id"], "函数", source="resume") is True
        out = await asyncio.wait_for(task, timeout=10)
        assert "函数" in out

    asyncio.run(flow())


def test_resume_endpoint_question_route():
    """复用 /resume 通道：question_id 真值路由到 pending_question（不触 HITL）。"""
    # 经 data_intelligence_stream 引入（直接 import endpoint 会撞路由文件环形导入）
    from app.api.data_intelligence_stream import HITLResumeRequest, resume_hitl

    async def flow():
        qid, fut, _ = pq.create_question(question="继续吗？", user_prefix="u", session_id="s4")
        body = HITLResumeRequest(question_id=qid, answer="继续")
        resp = await resume_hitl(body)
        assert resp["code"] == 200 and resp["data"]["answered"] is True
        result = await fut
        assert result["answer"] == "继续" and result["source"] == "resume"
        # 再次恢复=404
        resp2 = await resume_hitl(HITLResumeRequest(question_id=qid, answer="x"))
        assert resp2["code"] == 404

    asyncio.run(flow())
