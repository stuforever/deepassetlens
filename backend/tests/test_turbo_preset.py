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
