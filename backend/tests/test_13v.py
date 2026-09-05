# -*- coding: utf-8 -*-
"""P0-COUNT 死循环修复 单测：定位类工具预算闸门（L1 同参去重 + L2 总预算）。

背景（13-L 收口登记）：generic COUNT 题「统计配电变压器数量」实测同参 search_entities×28 +
batch_entity_source_mode×12 交替 163s 打结——执行类工具的 G2 纠错闸门管不到定位类工具。
修复：SkillPolicy._precheck 加 _locate_budget_check（正交于 capability 开关）。
"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.skill_policy import SkillPolicyMiddleware  # noqa: E402
from app.services.query_contract import QueryContract  # noqa: E402


def _mw() -> SkillPolicyMiddleware:
    return SkillPolicyMiddleware(allow_missing_contract=True)


def _req(tool: str, args: dict) -> SimpleNamespace:
    return SimpleNamespace(
        tool_call={"name": tool, "args": args, "id": "tc1"},
        runtime=SimpleNamespace(context={}),
    )


def _generic_contract() -> QueryContract:
    c = QueryContract.generic()
    c.allowed_tools = list(set(c.allowed_tools) | {"search_entities", "batch_entity_source_mode",
                                                   "validate_l2", "fetch_subgraph", "fetch_l1_l2_tree",
                                                   "execute_doris_sql"})
    return c


def test_same_args_second_call_rejected():
    """L1：同工具同参数第二次调用被拒（结果不会变化）。"""
    mw = _mw()
    c = _generic_contract()
    r1 = mw._locate_budget_check(c, "search_entities", _req("search_entities", {"keyword": "配电变压器"}))
    r2 = mw._locate_budget_check(c, "search_entities", _req("search_entities", {"keyword": "配电变压器"}))
    assert r1 is None, "首次同参调用应放行"
    assert r2 is not None and "完全相同" in r2, "第二次同参应被拒"


def test_different_args_allowed():
    """参数不同（模型改写检索词）不触发 L1——合法重试保留。"""
    mw = _mw()
    c = _generic_contract()
    assert mw._locate_budget_check(c, "search_entities", _req("search_entities", {"keyword": "配电变压器"})) is None
    assert mw._locate_budget_check(c, "search_entities", _req("search_entities", {"keyword": "配变"})) is None


def test_budget_exhausted_rejected():
    """L2：定位类累计超预算（generic 默认 8）后拒绝并注入前进指令。"""
    mw = _mw()
    c = _generic_contract()
    for i in range(8):
        assert mw._locate_budget_check(
            c, "search_entities", _req("search_entities", {"keyword": f"实体{i}"})) is None
    v = mw._locate_budget_check(c, "search_entities", _req("search_entities", {"keyword": "第9个"}))
    assert v is not None and "定位预算已耗尽" in v
    # batch 也在同一预算池内
    v2 = mw._locate_budget_check(c, "batch_entity_source_mode", _req("batch_entity_source_mode", {"entity_codes": ["x"]}))
    assert v2 is not None and "定位预算已耗尽" in v2


def test_scenario_budget_higher():
    """场景契约预算更高（14）——场景定位链（locate 三件+search）不被误伤。"""
    mw = _mw()
    c = _generic_contract()
    c.route_type = "scenario"
    for i in range(14):
        assert mw._locate_budget_check(
            c, "search_entities", _req("search_entities", {"keyword": f"实体{i}"})) is None
    assert mw._locate_budget_check(c, "validate_l2", _req("validate_l2", {"l2_id": f"L{i}"})) is not None


def test_data_tools_not_affected():
    """数据工具不在预算池——预算耗尽后 execute 仍可走（模型被迫前进的出口保持开放）。"""
    mw = _mw()
    c = _generic_contract()
    c._runtime["locate_calls"] = 99
    assert mw._locate_budget_check(c, "execute_doris_sql", _req("execute_doris_sql", {"sql": "SELECT 1"})) is None


def test_rejected_call_not_counted():
    """被拒调用不计数（预算不被无效调用加速耗尽）。"""
    mw = _mw()
    c = _generic_contract()
    for i in range(8):
        mw._locate_budget_check(c, "search_entities", _req("search_entities", {"keyword": f"实体{i}"}))
    before = c._runtime["locate_calls"]
    mw._locate_budget_check(c, "search_entities", _req("search_entities", {"keyword": "超预算调用"}))
    assert c._runtime["locate_calls"] == before, "被拒调用不应推进计数"


def test_env_budget_override(monkeypatch):
    """环境变量 TUPU_LOCATE_BUDGET 可调（运维面板兜底）。"""
    monkeypatch.setenv("TUPU_LOCATE_BUDGET", "2")
    import importlib
    import app.services.skill_policy as sp
    importlib.reload(sp)
    mw = sp.SkillPolicyMiddleware(allow_missing_contract=True)
    c = QueryContract.generic()
    c.allowed_tools = list(set(c.allowed_tools) | {"search_entities"})
    assert mw._locate_budget_check(c, "search_entities", _req("search_entities", {"keyword": "a"})) is None
    assert mw._locate_budget_check(c, "search_entities", _req("search_entities", {"keyword": "b"})) is None
    assert mw._locate_budget_check(c, "search_entities", _req("search_entities", {"keyword": "c"})) is not None
