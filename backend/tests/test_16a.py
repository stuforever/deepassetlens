# -*- coding: utf-8 -*-
"""批16-A 直通资格路由门放开 单测（TDD：先写测试→红灯→改 L39→绿灯）。

变异锚点：每条注释标明何种生产代码改动会让它失败。
evaluate_direct_eligibility（direct_pipeline.py L32-61）七条直通资格链：
route_type 门 / 澄清卡门 / golden_hits 存在 / sim≥阈值 / SQL 非空 /
is_count_intent / 无动态条件 / engine∈(doris,physical)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.services.direct_pipeline import evaluate_direct_eligibility  # noqa: E402


class _Contract:
    """最小契约形状（evaluate_direct_eligibility 只读这些字段）。"""

    def __init__(self, route_type="scenario", clarify_required=False, hits=None):
        self.route_type = route_type
        self.clarify_required = clarify_required
        self._runtime = {"golden_hits": hits or []}


_GOLD_HIT = {"score": 0.97, "sql": "SELECT COUNT(DISTINCT 台区编号) AS 重过载台区数 FROM internal.t",
             "engine": "doris"}


def _scenario_contract(**kw):
    return _Contract(hits=[_GOLD_HIT], **kw)


def test_sanity_generic_baseline_still_eligible():
    """前置 sanity：generic 路由原资格链不变（改动前后都应通过）。
    变异锚点：L39 generic 分支被误删 → 此测先红。"""
    plan = evaluate_direct_eligibility(_Contract(route_type="generic", hits=[_GOLD_HIT]),
                                       "统计用电客户数量")
    assert plan is not None and plan["engine"] == "doris"


def test_scenario_count_with_golden_now_eligible():
    """场景 COUNT 题 + 金标命中 → 可直通（本批核心行为：路由门放开 scenario）。
    变异锚点：L39 路由门回退为 == "generic" → 此测红（回归守卫）。"""
    plan = evaluate_direct_eligibility(_scenario_contract(), "统计重过载台区数量")
    assert plan is not None
    assert plan["engine"] == "doris" and "COUNT" in plan["sql"] and plan["score"] == pytest.approx(0.97)


def test_scenario_non_count_not_eligible():
    """场景非 COUNT 题（明细问法）不直通——is_count_intent 门对 scenario 同样生效。
    变异锚点：L54 is_count_intent 门删 → 明细题误直通出单行计数。"""
    plan = evaluate_direct_eligibility(_scenario_contract(), "哪些台区重过载")
    assert plan is None


def test_scenario_dynamic_condition_not_eligible():
    """场景题含动态条件（日期/比较词）不直通。
    变异锚点：L56 has_dynamic_condition 门删 → 条件题误执行旧 SQL。"""
    plan = evaluate_direct_eligibility(_scenario_contract(), "统计重过载台区数量 对比上月")
    assert plan is None


def test_low_sim_not_eligible():
    """金标相似度低于直通阈值（默认 0.95）不直通。
    变异锚点：L48 阈值判定删 → 弱相关金标误直通。"""
    weak = dict(_GOLD_HIT, score=0.91)
    plan = evaluate_direct_eligibility(_Contract(hits=[weak]), "统计重过载台区数量")
    assert plan is None


def test_clarify_required_not_eligible():
    """需澄清卡 → 不直通（先问后答语义优先于直通）。
    变异锚点：L41 clarify 门删 → 该澄清的题跳过澄清。"""
    plan = evaluate_direct_eligibility(_scenario_contract(clarify_required=True), "统计重过载台区数量")
    assert plan is None


def test_empty_hits_not_eligible():
    """无金标命中 → 不直通（安全链第一环：无已验证 SQL 单源则不放行）。
    变异锚点：L44-45 hits 空判定删 → plan["sql"] 取空串 KeyError 或误放行。"""
    plan = evaluate_direct_eligibility(_Contract(hits=[]), "统计重过载台区数量")
    assert plan is None
