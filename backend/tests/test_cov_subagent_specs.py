# -*- coding: utf-8 -*-
"""覆盖补全批次1b：subagent_specs 委派规格构建 + 四护栏逻辑（此前零直接测试）。

characterization 纪律：每个测试注明会让它失败的生产改动。
隔离：_global_tool_registry/record_event 均为函数内导入 -> monkeypatch 源模块即生效。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import subagent_specs as ss  # noqa: E402
from app.services import capability_config as cc  # noqa: E402


class _FakeTool:
    def __init__(self, name):
        self.name = name


def _patch(monkeypatch, registry=frozenset({"sql_query", "read_file"})):
    events = []
    monkeypatch.setattr(cc, "_global_tool_registry", lambda: registry)
    monkeypatch.setattr(cc, "record_event", lambda *a, **kw: events.append((a, kw)))
    return events


_MODEL = object()  # 哨兵模型：断言 model 原样透传


def test_disabled_policy_returns_none(monkeypatch):
    """关闭/空策略 -> None（降级回串行定位）。改动：enabled 早退被删 -> 失败。"""
    _patch(monkeypatch)
    assert ss.build_subagent_specs(None, _MODEL) is None
    assert ss.build_subagent_specs({}, _MODEL) is None
    assert ss.build_subagent_specs({"enabled": False, "params": {"specs": [{"name": "x", "tools": ["sql_query"]}]}}, _MODEL) is None


def test_empty_intersection_rejected_with_event(monkeypatch):
    """护栏3：工具集与注册表交集为空 -> 拒装配 + spec_invalid 事件。改动：护栏3 被删 -> 失败。"""
    events = _patch(monkeypatch, registry=frozenset({"sql_query"}))
    out = ss.build_subagent_specs(
        {"enabled": True, "params": {"specs": [{"name": "bad", "tools": ["write_file"]}]}}, _MODEL)
    assert out is None
    assert len(events) == 1
    args, kwargs = events[0]
    assert args[0] == "subagents" and args[1] == "spec_invalid"
    assert kwargs["detail"]["spec_name"] == "bad"
    assert "交集为空" in kwargs["detail"]["reason"]


def test_valid_spec_name_level(monkeypatch):
    """有效规格（无 parent_tools）-> 名字级工具清单 + 并发约束注入 + model 透传。改动：映射逻辑改动 -> 失败。"""
    _patch(monkeypatch, registry=frozenset({"sql_query", "read_file", "ls"}))
    out = ss.build_subagent_specs(
        {"enabled": True, "params": {
            "max_concurrent": 3,
            "specs": [{"name": "locator", "description": "定位", "prompt": "P", "tools": ["ls", "sql_query"]},
                      ]}},
        _MODEL)
    assert out is not None and len(out) == 1
    spec = out[0]
    assert spec["name"] == "locator" and spec["description"] == "定位"
    assert spec["model"] is _MODEL
    assert spec["tools"] == ["ls", "sql_query"]  # 交集且保持原顺序
    assert "最多 3 个委派并行" in spec["system_prompt"] and spec["system_prompt"].startswith("P")


def test_max_concurrent_one_no_constraint_line(monkeypatch):
    """max_concurrent=1 -> 不注入并发约束行。改动：>1 判断被删 -> 失败。"""
    _patch(monkeypatch)
    out = ss.build_subagent_specs(
        {"enabled": True, "params": {"max_concurrent": 1,
                                      "specs": [{"name": "s", "prompt": "P", "tools": ["sql_query"]}]}},
        _MODEL)
    assert out[0]["system_prompt"] == "P"


def test_parent_tools_mapping(monkeypatch):
    """parent_tools 传入 -> 交集内真实存在的映射为 BaseTool 对象。改动：对象映射逻辑改动 -> 失败。"""
    _patch(monkeypatch, registry=frozenset({"sql_query", "read_file"}))
    real_sql = _FakeTool("sql_query")
    out = ss.build_subagent_specs(
        {"enabled": True, "params": {"specs": [{"name": "s", "prompt": "P", "tools": ["sql_query", "read_file"]}]}},
        _MODEL, parent_tools=[real_sql])
    assert out[0]["tools"] == [real_sql]  # read_file 不在父工具面 -> 剔除


def test_parent_tools_missing_all_rejected(monkeypatch):
    """交集非空但父工具面全不存在 -> 拒装配 + 第二类 spec_invalid 理由。改动：该护栏分支被删 -> 失败。"""
    events = _patch(monkeypatch, registry=frozenset({"sql_query"}))
    out = ss.build_subagent_specs(
        {"enabled": True, "params": {"specs": [{"name": "s", "prompt": "P", "tools": ["sql_query"]}]}},
        _MODEL, parent_tools=[_FakeTool("unrelated")])
    assert out is None
    assert any("父代理工具面" in kw.get("detail", {}).get("reason", "") for _, kw in events)


def test_guard_middlewares_inherited(monkeypatch):
    """护栏2：守卫链显式传入 -> spec['middleware'] 携带。改动：护栏2 被删 -> 失败。"""
    _patch(monkeypatch)
    mw = [object()]
    out = ss.build_subagent_specs(
        {"enabled": True, "params": {"specs": [{"name": "s", "prompt": "P", "tools": ["sql_query"]}]}},
        _MODEL, guard_middlewares=mw)
    assert out[0]["middleware"] == mw


def test_all_specs_rejected_returns_none(monkeypatch):
    """全部规格被拒 -> None（整体降级）。改动：空 out 早退被删 -> 失败。"""
    _patch(monkeypatch, registry=frozenset({"sql_query"}))
    out = ss.build_subagent_specs(
        {"enabled": True, "params": {"specs": [
            {"name": "a", "tools": ["write_file"]},
            {"name": "b", "tools": []},
        ]}}, _MODEL)
    assert out is None
