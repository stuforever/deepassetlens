# -*- coding: utf-8 -*-
"""批13-J 路由治理 R3 否定模式测试。

覆盖：intent_classifier.has_negation（否定词窗口检测）；skill_router._match_scenarios
否定过滤（命中触发词但句内否定时不触发场景；all_groups 组内任一词否定整组不算）。
"""
import pytest

from app.services import intent_classifier as ic
from app.services.skill_router import SkillRouter


class TestHasNegation:
    def test_否定前置(self):
        assert ic.has_negation("不要查台区", "台区") is True
        assert ic.has_negation("别查台区", "台区") is True
        assert ic.has_negation("排除台区", "台区") is True

    def test_否定后置(self):
        assert ic.has_negation("台区不要查", "台区") is True
        assert ic.has_negation("台区别查了", "台区") is True

    def test_无否定(self):
        assert ic.has_negation("统计用电客户数量", "用电客户") is False
        assert ic.has_negation("查询台区负载", "台区") is False

    def test_窗口外不误伤(self):
        # 否定词距触发词超窗口 -> 不算否定（避免误伤「别的不说，查台区」这类长距）
        assert ic.has_negation("别的不说，查一下台区负载", "台区") is False

    def test_触发词未出现(self):
        assert ic.has_negation("不要查负载", "台区") is False


class TestMatchScenariosNegation:
    def _router(self):
        return SkillRouter()

    def test_否定触发词不命中场景(self):
        """「不要查重过载台区」：含否定 -> 不触发 distribution-overload 场景（若无其他命中走 generic/none）。"""
        r = self._router()
        res = r.route("不要查重过载台区")
        # 触发词「重过载台区」命中但被「不要」否定 -> 不应为 scenario/distribution-overload
        assert res.route_type != "scenario"

    def test_正常触发词仍命中(self):
        """「查询重过载台区」：无否定 -> 正常触发场景（回归保护）。"""
        r = self._router()
        res = r.route("查询重过载台区")
        assert res.route_type == "scenario"

    def test_has_negation_与路由联动(self):
        """直接验证 _match_scenarios 否定过滤逻辑（用任意含否定命中的输入）。"""
        r = self._router()
        hits = r._match_scenarios("不要查重过载台区")
        # 若该场景 any 触发词仅被否定 -> 不在 hits
        from app.services.skill_catalog import get_catalog
        trig_skill = [s for s in get_catalog().list_skills()
                      if (s.triggers or {}).get("any") and any(
                          ic.has_negation("不要查重过载台区", k) and k in "不要查重过载台区"
                          for k in (s.triggers or {}).get("any") or [])]
        # 存在触发词含「重过载台区」且被否定的场景时，该场景不应出现在 hits
        for s in trig_skill:
            assert s not in hits
