# -*- coding: utf-8 -*-
"""批13-Z 子代理激活（路线A）单测。

- 剧本 SKILL.md x_tupu.allow_subagents 数据化声明生效（distribution-overload=true）
- 契约层放行：task 入 allowed_tools 且移出 forbidden（护栏1 契约层）
- fail-closed 保持：未声明剧本仍默认拒绝
"""
from app.services.skill_catalog import get_catalog
from app.services.query_contract import QueryContract


class _FakeStep:
    id = "step1"
    allowed_tools = ["search_entities", "execute_sql"]
    templates = []
    output_mode = None
    stop_when = []
    allowed_next = []


def test_剧本声明数据化生效():
    """distribution-overload（首发多实体域剧本）声明 allow_subagents: true。"""
    skill = get_catalog().load_skill("scenarios/distribution-overload") or get_catalog().load_skill("distribution-overload")
    assert skill is not None, "distribution-overload 剧本加载失败"
    assert skill.allow_subagents is True, "首发剧本应已声明 allow_subagents: true（批13-Z 点火）"


def test_声明后契约层放行task():
    """护栏1 契约层：allow_subagents=True -> task 入 allowed + 不在 forbidden。"""
    c = QueryContract.from_step("scenarios/distribution-overload", "1.0", _FakeStep(),
                                allow_subagents=True)
    assert "task" in c.allowed_tools
    assert "task" not in c.forbidden_tools
    assert c.allows("task")


def test_未声明剧本保持fail_closed():
    """未声明剧本（project-lifecycle-cost）默认 False——护栏1 fail-closed 语义不变。"""
    skill = get_catalog().load_skill("scenarios/project-lifecycle-cost") or get_catalog().load_skill("project-lifecycle-cost")
    if skill is None:
        return  # 剧本不存在时跳过（环境差异）
    assert skill.allow_subagents is False, "未声明剧本必须保持默认拒绝（fail-closed）"
    c = QueryContract.from_step("scenarios/project-lifecycle-cost", "1.0", _FakeStep(),
                                allow_subagents=False)
    assert "task" not in c.allowed_tools
    assert not c.allows("task")
