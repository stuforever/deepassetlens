# -*- coding: utf-8 -*-
"""批13-W W-1 白名单反转单测：换算语义/迁移/fail-safe/校验。"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.services import capability_config as cc


@pytest.fixture(autouse=True)
def _fresh_cache():
    """每测清 TTL 缓存，防跨测串扰。"""
    cc._CACHE["data"] = None
    yield
    cc._CACHE["data"] = None


def test_默认全勾_排除清单等于红线五件():
    """默认 allowed=勾选域全勾 -> excluded=红线 5 件=黑名单版现状（零行为变化）。"""
    out = cc.get_tool_exclusions()
    assert sorted(out["excluded"]) == sorted(cc.W1_REDLINE_EXCLUSIONS)
    assert out["locked"] == cc.W1_LOCKED_TOOLS


def test_取消一件_换算进排除清单():
    """allowed 去掉 execute_sql -> 换算后 excluded 含它（机制零新增，喂同一 HarnessProfile）。"""
    allowed = [t for t in cc.w1_default_allowed() if t != "execute_sql"]
    cc._CACHE["data"] = [{
        "capability_id": "tool_availability", "title": "工具白名单", "enabled": True,
        "params": {"allowed": allowed}, "risk_level": "red", "description": {},
        "confirm_required": True, "physical_blocked": False, "blocked_reason": None,
        "updated_by": None, "updated_at": None, "close_reason": None, "version": 2,
    }]
    out = cc.get_tool_exclusions()
    assert "execute_sql" in out["excluded"]
    assert "search_entities" not in out["excluded"]  # 仍勾选
    assert sorted(set(out["excluded"]) & set(cc.W1_REDLINE_EXCLUSIONS)) == sorted(cc.W1_REDLINE_EXCLUSIONS)


def test_锁定件绕过漏勾_运行时强制保留():
    """params 里漏了 read_file/task -> get_tool_allowance 强制补回（不可取消）。"""
    allowed = [t for t in cc.w1_default_allowed() if t not in ("read_file", "task")]
    cc._CACHE["data"] = [{
        "capability_id": "tool_availability", "title": "x", "enabled": True,
        "params": {"allowed": allowed}, "risk_level": "red", "description": {},
        "confirm_required": True, "physical_blocked": False, "blocked_reason": None,
        "updated_by": None, "updated_at": None, "close_reason": None, "version": 2,
    }]
    a = cc.get_tool_allowance()
    assert "read_file" in a["allowed"] and "task" in a["allowed"]
    out = cc.get_tool_exclusions()
    assert "read_file" not in out["excluded"] and "task" not in out["excluded"]


def test_读崩_fail_safe_全勾():
    """get_policy 抛异常 -> fail-safe 返回默认允许集（语义反转登记：黑名单版=默认排除，白名单版=默认允许）。"""
    orig = cc.get_policy
    try:
        cc.get_policy = lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("db down"))
        a = cc.get_tool_allowance()
        assert sorted(a["allowed"]) == sorted(cc.w1_default_allowed())
        out = cc.get_tool_exclusions()
        assert sorted(out["excluded"]) == sorted(cc.W1_REDLINE_EXCLUSIONS)
    finally:
        cc.get_policy = orig


def test_validate_未知名与锁定取消与旧键拒():
    universe = cc._w1_managed_universe()
    base = sorted(universe)
    # 未知名 400
    err = cc.validate_params("tool_availability", {"allowed": base + ["ghost_tool"]})
    assert err and "未知工具名" in err
    # 锁定件取消 400
    err2 = cc.validate_params("tool_availability", {"allowed": [t for t in base if t != "task"]})
    assert err2 and "不可取消" in err2
    # 旧 excluded 键直接拒（防黑名单语义混写）
    err3 = cc.validate_params("tool_availability", {"excluded": ["execute_sql"]})
    assert err3 and "已退役" in err3
    # 合法 PATCH 通过
    assert cc.validate_params("tool_availability", {"allowed": base}) is None


def test_迁移_旧excluded换算allowed():
    """旧 params {excluded:[...]} -> allowed = 勾选域 - excluded，写回删 excluded。"""
    class FakeRow:
        capability_id = "tool_availability"
        params = {"excluded": ["grep", "glob", "write_file", "edit_file", "execute", "sample_column_values"]}
        title = "工具黑名单"
        version = 3

    row = FakeRow()

    class FakeDB:
        def query(self, *_a):
            class Q:
                def filter(self, *_a):
                    return self
                def first(self):
                    return row
            return Q()
        def commit(self):
            pass
        def rollback(self):
            pass

    n = cc.migrate_tool_exclusions_to_allowlist(FakeDB())
    assert n == 1
    universe = cc._w1_managed_universe()
    assert row.params["allowed"] == sorted(universe - {"sample_column_values"})
    assert "excluded" not in row.params
    assert row.version == 4
    assert row.title == "工具白名单"


def test_迁移_已是白名单语义_跳过():
    row = type("R", (), {"capability_id": "tool_availability",
                         "params": {"allowed": ["search_entities"]},
                         "title": "工具白名单", "version": 5})()

    class FakeDB:
        def query(self, *_a):
            class Q:
                def filter(self, *_a):
                    return self
                def first(self):
                    return row
            return Q()

    assert cc.migrate_tool_exclusions_to_allowlist(FakeDB()) == 0
    assert row.version == 5  # 未动


# ---------------- W-4：DecisionGate 装卸 + scope_tools 入 params ----------------

def test_w4_env兜底_恒开(monkeypatch):
    """TUPU_DECISION_GATE=1 环境变量为启动兜底（恒开），管理页关也不覆盖 env=1。"""
    monkeypatch.setenv("TUPU_DECISION_GATE", "1")
    cc._CACHE["data"] = [{
        "capability_id": "decision_gate", "title": "x", "enabled": False,
        "params": {}, "risk_level": "yellow", "description": {},
        "confirm_required": True, "physical_blocked": False, "blocked_reason": None,
        "updated_by": None, "updated_at": None, "close_reason": None, "version": 1,
    }]
    cfg = cc.get_decision_gate_config()
    assert cfg["enabled"] is True
    assert cfg["scope_tools"] == cc.DECISION_GATE_SCOPE_DEFAULT


def test_w4_env未设_管理页为准(monkeypatch):
    """env 未设时以管理页 enabled 为准（默认 False=关）；scope_tools 从 params 读。"""
    monkeypatch.delenv("TUPU_DECISION_GATE", raising=False)
    cc._CACHE["data"] = [{
        "capability_id": "decision_gate", "title": "x", "enabled": True,
        "params": {"scope_tools": ["execute_sql"]}, "risk_level": "yellow", "description": {},
        "confirm_required": True, "physical_blocked": False, "blocked_reason": None,
        "updated_by": None, "updated_at": None, "close_reason": None, "version": 2,
    }]
    cfg = cc.get_decision_gate_config()
    assert cfg["enabled"] is True
    assert cfg["scope_tools"] == ["execute_sql"]


def test_w4_scope_tools校验():
    # 非法：空集
    err = cc.validate_params("decision_gate", {"scope_tools": []})
    assert err and "不能为空" in err
    # 非法：未知名
    err2 = cc.validate_params("decision_gate", {"scope_tools": ["ghost"]})
    assert err2 and "未知工具名" in err2
    # 合法
    assert cc.validate_params("decision_gate", {"scope_tools": ["execute_sql"]}) is None
