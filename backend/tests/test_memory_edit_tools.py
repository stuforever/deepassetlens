# -*- coding: utf-8 -*-
"""②补验（B3 前置·第三道防线）：自定义记忆槽写入件——构造/白名单直通/无槽零变化。"""
import asyncio

import pytest


class _FakeResult:
    def __init__(self, path=None, error=None):
        self.path = path
        self.error = error


class _FakeMTB:
    def __init__(self):
        self.writes = []
        self.edits = []

    def write(self, file_path, content):
        self.writes.append((file_path, content))
        return _FakeResult(path="/memory/偏好.md")

    def edit(self, file_path, old_string, new_string, replace_all=False):
        self.edits.append((file_path, old_string, new_string))
        return _FakeResult(path="/memory/偏好.md")


def test_build_memory_edit_tools_two_named():
    """构造：两件、名字正确、有描述（**非 write_file/edit_file 名**——该两名被
    _ToolExclusionMiddleware 按名永久剥离，见 _build_memory_edit_tools 注记）。"""
    from app.services.tupu_deepagent import _build_memory_edit_tools
    tools = _build_memory_edit_tools(_FakeMTB())
    names = {t.name for t in tools}
    assert names == {"write_memory_slot", "edit_memory_slot"}
    assert all(t.description for t in tools)


def test_write_tool_passthrough_whitelist():
    """write 件直通 MTB.write（白名单逻辑在 MTB 侧，本件零自制策略）。"""
    from app.services.tupu_deepagent import _build_memory_edit_tools
    mtb = _FakeMTB()
    (w, e) = _build_memory_edit_tools(mtb)
    out = asyncio.run(w.ainvoke({"file_path": "/memory/偏好.md", "content": "x"}))
    assert "成功" in out
    assert mtb.writes == [("/memory/偏好.md", "x")]


def test_write_tool_error_passthrough():
    """MTB 拒（越权）如实上屏，不吞错不伪造成功。"""
    from app.services.tupu_deepagent import _build_memory_edit_tools

    class _Deny(_FakeMTB):
        def write(self, file_path, content):
            return _FakeResult(error="PERMISSION_DENIED: 未声明的可写槽: /memory/AGENTS.md")

    (w, _e) = _build_memory_edit_tools(_Deny())
    out = asyncio.run(w.ainvoke({"file_path": "/memory/AGENTS.md", "content": "x"}))
    assert "失败" in out and "PERMISSION_DENIED" in out


def test_edit_tool_passthrough():
    """edit 件直通 MTB.edit。"""
    from app.services.tupu_deepagent import _build_memory_edit_tools
    mtb = _FakeMTB()
    (_w, e) = _build_memory_edit_tools(mtb)
    out = asyncio.run(e.ainvoke({"file_path": "/memory/偏好.md", "old_string": "a", "new_string": "b"}))
    assert "成功" in out
    assert mtb.edits == [("/memory/偏好.md", "a", "b")]


def test_no_slot_card_no_tools():
    """无 agent_edit 槽卡（wenshu 形状）→ 装配不追加（零变化）。"""
    from app.services.tupu_deepagent import _card_has_agent_edit_slots
    assert _card_has_agent_edit_slots({"memory": None}) is False
    assert _card_has_agent_edit_slots({}) is False


def test_agent_edit_slot_rels_normalization():
    """装配期快照归一：槽声明 /memory/偏好.md → 相对基准 偏好.md（实证 #11——
    与 SkillPolicy 同基准，否则例外永不命中）。"""
    from app.services.tupu_deepagent import _agent_edit_slot_rels
    card = {"memory": {"slots": [
        {"key": "偏好", "type": "RAW_MD", "writer": "agent_edit", "path": "/memory/偏好.md"},
        {"key": "L2", "type": "L2_SUMMARY"},                      # 非 RAW_MD：不进集合
    ]}}
    assert _agent_edit_slot_rels(card) == frozenset({"偏好.md"})
    # 无槽卡与异常形状 → 空集
    assert _agent_edit_slot_rels({}) == frozenset()
    assert _agent_edit_slot_rels({"memory": None}) == frozenset()
