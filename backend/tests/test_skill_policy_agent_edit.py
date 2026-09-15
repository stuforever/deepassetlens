# -*- coding: utf-8 -*-
"""②补验（B 组前置）：SkillPolicy agent_edit 槽例外单测锁——例外放行+非槽路径仍拒+wenshu 等值。
判定依据=**装配期快照** agent_edit_paths（langgraph 同步工具在 executor 线程，ContextVars 不跨线程
——②补验实证 #9）。工具名=write_memory_slot/edit_memory_slot（built-in write_file/edit_file 被
_ToolExclusionMiddleware 按名剥离，故自定义件换名——实证 #10）。"""
import asyncio

import pytest


class _Req:
    def __init__(self, name, args):
        self.tool_call = {"name": name, "args": args, "id": "t1"}


def _policy(paths):
    from app.services.skill_policy import SkillPolicyMiddleware
    return SkillPolicyMiddleware(allow_missing_contract=True, agent_edit_paths=paths)


@pytest.fixture()
def generic_contract():
    """generic 契约（write_file/edit_file/write_memory_slot 均不在 allowed——「通用只读」形状）。"""
    from app.services.skill_router import route_user_input
    return route_user_input("你好").contract


def _precheck(policy, contract, tool, req):
    return asyncio.run(policy._precheck(contract, tool, req))


def test_agent_edit_slot_write_allowed(generic_contract):
    """RAW_MD agent_edit 槽目标 → 记忆槽写入件例外放行（三层防线其余两层接管）。"""
    p = _policy(frozenset({"偏好.md"}))               # 装配期快照（剥 /memory/ 前缀形状）
    req = _Req("write_memory_slot", {"file_path": "/memory/偏好.md", "content": "测试"})
    assert _precheck(p, generic_contract, "write_memory_slot", req) is None
    # 根单段形状（模型把挂载区当虚拟根——#8）同过
    req2 = _Req("write_memory_slot", {"file_path": "/偏好.md", "content": "测试"})
    assert _precheck(p, generic_contract, "write_memory_slot", req2) is None
    # edit 件同放行
    req3 = _Req("edit_memory_slot", {"file_path": "/memory/偏好.md", "old_string": "a", "new_string": "b"})
    assert _precheck(p, generic_contract, "edit_memory_slot", req3) is None


def test_non_slot_path_still_rejected(generic_contract):
    """非槽路径（/memory/AGENTS.md 手册）→ 仍拒（手册双锁不破）。"""
    p = _policy(frozenset({"偏好.md"}))
    req = _Req("write_memory_slot", {"file_path": "/memory/AGENTS.md", "content": "越权"})
    v = _precheck(p, generic_contract, "write_memory_slot", req)
    assert v is not None and ("禁用工具" in v or "允许范围" in v)


def test_empty_paths_equivalence(generic_contract):
    """空白名单（wenshu slots=[] 装配形状）→ 例外永不触发（现状等值）。"""
    p = _policy(frozenset())
    req = _Req("write_memory_slot", {"file_path": "/memory/偏好.md", "content": "x"})
    v = _precheck(p, generic_contract, "write_memory_slot", req)
    assert v is not None


def test_multi_segment_absolute_rejected(generic_contract):
    """多段绝对路径（/etc/passwd 形状）→ 不归一，仍拒（域外防护不变）。"""
    p = _policy(frozenset({"偏好.md"}))
    req = _Req("write_memory_slot", {"file_path": "/etc/偏好.md", "content": "x"})
    v = _precheck(p, generic_contract, "write_memory_slot", req)
    assert v is not None
