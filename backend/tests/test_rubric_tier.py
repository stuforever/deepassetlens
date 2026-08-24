# -*- coding: utf-8 -*-
"""test_rubric_tier.py - 批1-B rubric 分档直通单测（高分示例锚定 → rubric=None，省 20-40s grader 调用）"""
import pytest

from app.services.query_contract import QueryContract, apply_rubric_tier


def _generic_contract(**kw) -> QueryContract:
    return QueryContract.generic(**kw)


class TestRubricTier:
    def test_high_score_hit_skips_rubric(self):
        """高分示例锚定（score>=0.85）→ rubric=None + rubric_skipped=example_anchored"""
        c = _generic_contract()
        assert c.rubric is not None
        c._runtime["example_hits"] = [{"id": "e1", "score": 0.92, "sql": "SELECT 1"}]
        apply_rubric_tier(c)
        assert c.rubric is None
        assert c._runtime.get("rubric_skipped") == "example_anchored"

    def test_no_hit_keeps_rubric(self):
        """无示例命中 → rubric 保留（未锚定查询仍需自评）"""
        c = _generic_contract()
        apply_rubric_tier(c)
        assert c.rubric is not None
        assert "_runtime" not in c._runtime or "rubric_skipped" not in c._runtime

    def test_below_threshold_keeps_rubric(self):
        """示例分不足（<0.85）→ rubric 保留"""
        c = _generic_contract()
        c._runtime["example_hits"] = [{"id": "e1", "score": 0.70, "sql": "SELECT 1"}]
        apply_rubric_tier(c)
        assert c.rubric is not None

    def test_aggregate_intent_not_exempted(self):
        """聚合分布类问题（S1 不稳定源）不豁免：即使高分示例锚定也保留 rubric 自评兜底"""
        c = _generic_contract(aggregate_intent={"dimension_hint": "电压等级", "required_shape": "grouped"})
        c._runtime["example_hits"] = [{"id": "e1", "score": 0.95, "sql": "SELECT 1"}]
        apply_rubric_tier(c)
        assert c.rubric is not None

    def test_scenario_contract_untouched(self):
        """非 generic 契约（scenario）不参与分档"""
        from app.services.skill_catalog import SkillCatalog  # noqa: F401
        c = _generic_contract()
        c.route_type = "scenario"
        c._runtime["example_hits"] = [{"id": "e1", "score": 0.99, "sql": "SELECT 1"}]
        apply_rubric_tier(c)
        assert c.rubric is not None
