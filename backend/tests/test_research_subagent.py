# -*- coding: utf-8 -*-
"""R3 research 子代理测试：规格字段/工具面/系统提示词 B 档语义。"""
from __future__ import annotations

import asyncio

from app.services.tupu_deepagent import _research_subagent_spec, _web_search_tool


class _ModelStub:
    pass


def test_spec_shape():
    spec = _research_subagent_spec(_ModelStub(), [])
    assert spec["name"] == "research-analyst"
    assert spec["model"] is not None
    assert spec["description"]
    # B 档三节点语义在系统提示词中
    sp = spec["system_prompt"]
    assert "大纲" in sp and "分节" in sp and "汇总" in sp
    # 工具面恒含 web_search（进程内包装）；search_kb 交集按父面
    names = {getattr(t, "name", "") for t in spec["tools"]}
    assert "web_search" in names


def test_spec_narrows_parent_tools():
    class _FakeTool:
        def __init__(self, name):
            self.name = name

    parent = [_FakeTool("search_kb"), _FakeTool("execute_sql"), _FakeTool("fetch_l1_l2_tree")]
    spec = _research_subagent_spec(_ModelStub(), parent)
    names = {getattr(t, "name", "") for t in spec["tools"]}
    assert names == {"search_kb", "web_search"}  # 父面窄化+web_search 注入


def test_web_search_tool_wraps_twin():
    from app.services import tupu_deepagent as td

    async def fake_impl(query, max_results=5):
        return [{"title": "t", "snippet": "s", "url": "u"}]

    orig = td._web_search_tool  # 模块缓存无碍——monkeypatch 的是 orch 模块
    import app.api.dt_agent_orchestrations as orch
    real = orch._web_search
    orch._web_search = fake_impl
    try:
        out = asyncio.run(_web_search_tool().ainvoke({"query": "q"}))
        assert "t" in out and "u" in out
    finally:
        orch._web_search = real
    assert orig is not None
