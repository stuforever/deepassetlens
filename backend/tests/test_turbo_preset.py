# -*- coding: utf-8 -*-
"""极速模式预设与开关缺口（2026-09-12 spec）单测：B-1 预算接线 / B-2 模式锁降级 / A 预设与预热。

变异锚点：每测 docstring 标明何种生产改动会让它红。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# 任务 1：件 B-1 locate_budget 能力行 + 三级读取
# ---------------------------------------------------------------------------

class _Contract:
    """_locate_budget_check 最小契约桩（route_type/_runtime 即全部依赖）。"""
    def __init__(self, route_type="generic"):
        self.route_type = route_type
        self._runtime = {}


class _Req:
    def __init__(self, args):
        self.tool_call = {"args": args}


def _check(contract, tool, args):
    from app.services.skill_policy import SkillPolicyMiddleware
    # 函数体不使用 self：绕过 __init__ 直接取实例方法（零构造依赖）
    return SkillPolicyMiddleware._locate_budget_check(object.__new__(SkillPolicyMiddleware), contract, tool, _Req(args))


def test_locate_budget_params_override():
    """params 覆盖默认阈值：generic=2 时第 3 次定位拒（spec §六：预算 8→2 后第 3 次定位拒）。
    变异锚点：_locate_budget_policy 不读 params → 预算仍 8 → 此测红。"""
    from app.services import capability_config as cc
    _row = {"enabled": True, "params": {"generic": 2, "scenario": 2}}
    monkey = pytest.MonkeyPatch()
    monkey.setattr(cc, "get_policy", lambda cid: _row if cid == "locate_budget" else None)
    try:
        c = _Contract("generic")
        assert _check(c, "search_entities", {"keyword": "a"}) is None   # 1 次放行
        assert _check(c, "search_entities", {"keyword": "b"}) is None   # 2 次放行
        r3 = _check(c, "search_entities", {"keyword": "c"})
        assert r3 is not None and "定位预算已耗尽" in r3                   # 第 3 次拒
    finally:
        monkey.undo()


def test_locate_budget_disabled_skips():
    """enabled=False 跳过 L1 去重+L2 预算（spec B-1）。
    变异锚点：顶部无开关门 → 同参第 2 次仍被 L1 拒 → 此测红。"""
    from app.services import capability_config as cc
    monkey = pytest.MonkeyPatch()
    monkey.setattr(cc, "get_policy", lambda cid: {"enabled": False, "params": {}})
    try:
        c = _Contract("generic")
        for i in range(20):
            assert _check(c, "search_entities", {"keyword": "同参"}) is None  # 关=永不拒
    finally:
        monkey.undo()


def test_locate_budget_read_fail_fail_safe():
    """读失败 fail-safe 回落环境变量默认（预算保持开，spec B-1/§五）。
    变异锚点：异常外泄或回落关 → 此测红。"""
    from app.services import capability_config as cc
    from app.services.skill_policy import _locate_budget_policy, _LOCATE_BUDGET_DEFAULT, _LOCATE_BUDGET_SCENARIO
    monkey = pytest.MonkeyPatch()
    def _boom(cid):
        raise RuntimeError("db down")
    monkey.setattr(cc, "get_policy", _boom)
    try:
        on, gen, scn = _locate_budget_policy()
        assert on is True and gen == _LOCATE_BUDGET_DEFAULT and scn == _LOCATE_BUDGET_SCENARIO
    finally:
        monkey.undo()


def test_locate_budget_seed_row():
    """种子行存在（params {generic:8, scenario:14}，enabled 默认开）。
    变异锚点：CAPABILITY_POLICY_SEED 删 locate_budget 行 → 此测红。"""
    from app.core.init_db import CAPABILITY_POLICY_SEED
    row = next(p for p in CAPABILITY_POLICY_SEED if p["capability_id"] == "locate_budget")
    assert row["params"] == {"generic": 8, "scenario": 14}


# ---------------------------------------------------------------------------
# 任务 2：件 B-2 模式锁降级（engine_lock 关=放行+warning）
# ---------------------------------------------------------------------------

class _FakeEnt:
    source_mode = "api_integration"
    data_source_id = None


class _FakeQuery:
    def __init__(self, ent): self._ent = ent
    def filter(self, *a, **k): return self
    def first(self): return self._ent


class _FakeDB:
    def query(self, *a, **k): return _FakeQuery(_FakeEnt())
    def close(self): pass


def _run_execute_sql():
    from app.services.kg_action_handlers import _kg_execute_sql
    return _kg_execute_sql({"sql": "SELECT 1", "entity_code": "api_ent"}, "00:00:00")


def test_mode_lock_degrades_when_guard_off(monkeypatch, caplog):
    """守卫关：不返回模式锁错误卡+记 warning（spec B-2）。
    变异锚点：无前置守卫判断 → 仍返回模式锁 → 此测红。"""
    import logging
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: _FakeDB())
    from app.services import guard_config as gc
    monkeypatch.setattr(gc, "guard_enabled", lambda gid, sub_id=None: False)
    monkeypatch.setattr("app.services.sql_executor.build_execute_query_fn", lambda **k: None)
    import app.services.kg_action_handlers as kah
    with caplog.at_level(logging.WARNING):
        out = kah._kg_execute_sql({"sql": "SELECT 1", "entity_code": "api_ent"}, "00:00:00")
    assert "模式锁" not in (out.get("error") or "")          # 放行（走既有路径，此处执行函数桩为 None）
    assert any("engine_lock" in r.message for r in caplog.records)  # warning 在案


def test_mode_lock_intercepts_when_guard_on(monkeypatch):
    """守卫开：行为与现状逐字节一致（回归锚，spec B-2）。"""
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: _FakeDB())
    from app.services import guard_config as gc
    monkeypatch.setattr(gc, "guard_enabled", lambda gid, sub_id=None: True)
    import app.services.kg_action_handlers as kah
    out = kah._kg_execute_sql({"sql": "SELECT 1", "entity_code": "api_ent"}, "00:00:00")
    assert (out.get("error") or "").startswith("模式锁：实体 api_ent source_mode=api_integration")


def test_mode_lock_fails_closed_on_guard_read_error(monkeypatch):
    """读守卫失败：保持拦截（fail-closed 正确性件，spec B-2——方向与 B-1 fail-safe 开相反）。
    变异锚点：except 分支改 fail-open（_el_on=False）→ 放行走 execute 桩 → 此测红。
    （简报三测要求：plan 代码块仅含前两测，本测补 fail-closed 行为锚。）"""
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: _FakeDB())
    from app.services import guard_config as gc

    def _boom(gid, sub_id=None):
        raise RuntimeError("guard store read failed")

    monkeypatch.setattr(gc, "guard_enabled", _boom)
    monkeypatch.setattr("app.services.sql_executor.build_execute_query_fn", lambda **k: None)
    out = _run_execute_sql()
    assert (out.get("error") or "").startswith("模式锁：实体 api_ent source_mode=api_integration")


# ---------------------------------------------------------------------------
# 任务 3：件 A 预设服务+预热
# ---------------------------------------------------------------------------

def test_preset_turbo_then_safe_state():
    """turbo 后六关二保留（sql_safety/locate_budget 开）；safe 后全站回位（spec §三表/§六）。
    变异锚点：组合表错一站 → 对应断言红。测试后恢复 safe（现场零污染）。"""
    from app.services import guard_preset, guard_config, capability_config
    out = guard_preset.apply_preset("turbo", updated_by="test")
    assert out["all_ok"] is True
    pol = {p["guard_id"]: p["enabled"] for p in guard_config.get_policies(force=True)}
    assert pol["template"] is False and pol["output"] is False and pol["engine_lock"] is False
    assert pol["approval_track"] is False and pol["capability"] is False
    assert pol["sql_safety"] is True                                   # 保留开
    cap = {p["capability_id"]: p["enabled"] for p in capability_config.get_policies(force=True)}
    assert cap["decision_gate"] is False and cap["locate_budget"] is True   # 保留开
    out2 = guard_preset.apply_preset("safe", updated_by="test")        # 收尾恢复
    assert out2["all_ok"] is True
    pol2 = {p["guard_id"]: p["enabled"] for p in guard_config.get_policies(force=True)}
    assert all(pol2[g] is True for g in ("template", "output", "engine_lock", "approval_track",
                                          "capability", "sql_safety"))


def test_preset_invalid_mode():
    """非法 mode -> ValueError（端点层转 400，spec §五）。"""
    from app.services import guard_preset
    with pytest.raises(ValueError):
        guard_preset.apply_preset("fast", updated_by="test")


def test_preset_idempotent_second_call_skips():
    """幂等：目标态已一致跳过（changed=False，少 bump 少重建）。"""
    from app.services import guard_preset
    guard_preset.apply_preset("safe", updated_by="test")
    out = guard_preset.apply_preset("safe", updated_by="test")
    assert out["all_ok"] and all(s["changed"] is False for s in out["stations"])


@pytest.mark.asyncio
async def test_warmup_runs_and_silent_fail(monkeypatch):
    """预热：sleep 后调 get_tupu_agent("")一次；失败静默（spec §三 A/§五）。"""
    import asyncio
    from app.services import guard_preset
    calls = {"n": 0}
    async def _fake_agent(key):
        calls["n"] += 1
    async def _no_sleep(s):
        pass
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)
    import app.services.tupu_deepagent as td
    monkeypatch.setattr(td, "get_tupu_agent", _fake_agent)
    await guard_preset.warmup_default_agent()
    assert calls["n"] == 1
    async def _boom(key):
        raise RuntimeError("gateway down")
    monkeypatch.setattr(td, "get_tupu_agent", _boom)
    await guard_preset.warmup_default_agent()      # 失败静默不抛
