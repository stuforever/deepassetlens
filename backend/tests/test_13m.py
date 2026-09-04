# -*- coding: utf-8 -*-
"""批13-M 定位优先主流程恢复 单测。

- locate_first 数据化链路：SKILL.md x_tupu 声明 -> catalog -> contract
- 契约消息「实体定位顺序」段：locate_first 注入 / 预解析路径不注入
- 守卫 policy 提示：search_entities 首跳 -> locate_order_warn 事件（放行不拦截）
- locate_used 标记：locate 类工具调用后置位，二次 search_entities 不再 warn
"""
import asyncio
import json
from types import SimpleNamespace

import pytest

from app.services.query_contract import QueryContract
from app.services.skill_catalog import get_catalog
from app.services.skill_policy import SkillPolicyMiddleware, _LOCATE_TOOLS
from app.services.skill_router import route_user_input


@pytest.fixture
def policy():
    return SkillPolicyMiddleware(catalog=get_catalog())


def _tc(name, args=None):
    return {"name": name, "id": f"id-{name}", "args": args or {}}


def _run(policy, contract, tc, result=None):
    req = SimpleNamespace(
        tool_call=tc,
        runtime=SimpleNamespace(context={"contract": contract}, config=None),
        state=None,
    )

    async def handler(request):
        if callable(result):
            return result(request)
        return result if result is not None else json.dumps({"ok": True})

    return asyncio.run(policy.awrap_tool_call(req, handler))


def test_locate_first数据化链路():
    """distribution-overload 声明 -> catalog True -> 契约 True；未声明场景 False。"""
    skill = get_catalog().load_skill("distribution-overload")
    assert skill.locate_first is True
    r = route_user_input("查询重过载台区")
    assert r.route_type == "scenario" and r.contract.locate_first is True
    # 预解析快捷路径（lifecycle-cost 未声明）防误伤
    r2 = route_user_input("哪些WBS超预算")
    assert r2.route_type == "scenario" and r2.contract.locate_first is False


def test_场景步骤含定位工具与兜底():
    """overload 步骤 allowed_tools 含 locate 类 + search_entities 兜底（标准顺序四步可用）。"""
    skill = get_catalog().load_skill("distribution-overload")
    step = skill.find_step("overload")
    for t in ("fetch_l1_l2_tree", "validate_l2", "fetch_subgraph", "search_entities"):
        assert t in step.allowed_tools, f"{t} 不在 allowed_tools"


def test_契约消息定位顺序段():
    """locate_first=True 契约消息含定位顺序段；False 不含（防误伤直通/预解析）。"""
    from app.api.data_intelligence import _build_contract_system_message, _CONTRACT_LOCATE_ORDER
    r = route_user_input("查询重过载台区")
    msg = _build_contract_system_message(r.contract)
    assert _CONTRACT_LOCATE_ORDER in msg
    r2 = route_user_input("哪些WBS超预算")
    msg2 = _build_contract_system_message(r2.contract)
    assert _CONTRACT_LOCATE_ORDER not in msg2


def test_守卫首跳warn放行(policy, monkeypatch):
    """search_entities 首跳（无 locate_used）-> 记 locate_order_warn + 放行（None）。"""
    r = route_user_input("查询重过载台区")
    contract = r.contract
    events = []
    import app.services.capability_config as cc
    monkeypatch.setattr(cc, "record_event",
                        lambda cid, action, detail=None: events.append((cid, action)))
    out = _run(policy, contract, _tc("search_entities", {"keyword": "台区"}))
    assert out == '{"ok": true}', f"warn 不得拦截（handler 结果应原样返回）: {out}"
    assert ("skill_policy", "locate_order_warn") in events


def test_已定位后不再warn(policy, monkeypatch):
    """validate_l2 后 locate_used 置位 -> search_entities 兜底不再记 warn。"""
    r = route_user_input("查询重过载台区")
    contract = r.contract
    events = []
    import app.services.capability_config as cc
    monkeypatch.setattr(cc, "record_event",
                        lambda cid, action, detail=None: events.append((cid, action)))
    _run(policy, contract, _tc("validate_l2", {"l2_id": "dms"}))  # locate 类 -> 置位
    assert contract._runtime.get("locate_used") is True
    _run(policy, contract, _tc("search_entities", {"keyword": "台区"}))
    assert ("skill_policy", "locate_order_warn") not in events


def test_预解析契约不warn(policy, monkeypatch):
    """lifecycle-cost（locate_first=False）search_entities 不触发 warn（防误伤预解析路径）。"""
    r2 = route_user_input("哪些WBS超预算")
    contract = r2.contract
    events = []
    import app.services.capability_config as cc
    monkeypatch.setattr(cc, "record_event",
                        lambda cid, action, detail=None: events.append((cid, action)))
    _run(policy, contract, _tc("search_entities", {"keyword": "wbs"}))
    assert ("skill_policy", "locate_order_warn") not in events


def test_定位工具集常量():
    """_LOCATE_TOOLS 覆盖设计标准顺序的三个 locate 类工具。"""
    assert _LOCATE_TOOLS == frozenset({"validate_l2", "fetch_subgraph", "fetch_l1_l2_tree"})
