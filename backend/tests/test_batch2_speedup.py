# -*- coding: utf-8 -*-
"""test_batch2_speedup.py - 批2(P1) 提速链路单测：
   C 示例直通首选计划 / 计数同义归一化 / D 实体预解析注入 / E 指引预载"""
import pytest


# ---------------------------------------------------------------------------
# 批2-C 计数同义归一化（search_qa_examples Tier2 检索 query 归一化 + Tier1 别名通道）
# ---------------------------------------------------------------------------
class TestCountNormalize:
    def test_count_synonym_normalized(self):
        from app.services.qa_example_service import _count_normalize
        assert _count_normalize("统计用电客户数量") == "统计用电客户总数"
        assert _count_normalize("用电客户有多少个") == "用电客户有总数"

    def test_condition_question_not_normalized(self):
        """带条件词（数量大于1000）不归一化，防误直通 COUNT 全量示例"""
        from app.services.qa_example_service import _count_normalize
        assert _count_normalize("统计数量大于1000的客户") == "统计数量大于1000的客户"
        assert _count_normalize("数量超过500的变压器") == "数量超过500的变压器"

    def test_already_total_unchanged(self):
        from app.services.qa_example_service import _count_normalize
        assert _count_normalize("统计用电客户总数") == "统计用电客户总数"


# ---------------------------------------------------------------------------
# 批2-C 首选计划注入（_build_contract_system_message 内，高分示例 -> 「首选计划」块）
# ---------------------------------------------------------------------------
class TestDirectPlan:
    def _build(self, monkeypatch, score, sql="SELECT COUNT(*) AS total FROM cms20_cst_cust"):
        import app.services.qa_example_service as qes
        from app.services.query_contract import QueryContract
        from app.api.data_intelligence import _build_contract_system_message
        hits = [{"id": "e1", "score": score, "question_raw": "统计用电客户总数", "sql": sql, "engine": ""}]
        # 批7-E1 后契约消息改走 retrieve_context_bundle 单入口——mock 之
        monkeypatch.setattr(qes, "retrieve_context_bundle", lambda db, q, **kw: {
            "examples_block": "\n参考示例...", "example_hits": hits, "entity_hint_block": ""})
        monkeypatch.setattr(qes, "bump_hit_count", lambda db, ids: None)
        c = QueryContract.generic(route_reason="test")
        msg = _build_contract_system_message(c, question="统计用电客户数量")
        return c, msg

    def test_high_score_injects_direct_plan(self, monkeypatch):
        """sim>=0.90 且含 sql -> 块含「首选计划」"""
        c, msg = self._build(monkeypatch, score=0.95)
        assert "首选计划" in msg
        assert "跳过实体定位与读技能步骤" in msg
        assert c._runtime["example_hits"][0]["score"] == 0.95

    def test_low_score_no_direct_plan(self, monkeypatch):
        """sim<0.90 -> 不含「首选计划」（仍只给参考示例）"""
        c, msg = self._build(monkeypatch, score=0.80)
        assert "首选计划" not in msg
        assert "参考示例" in msg

    def test_no_sql_no_direct_plan(self, monkeypatch):
        """高分但无 sql -> 不直通"""
        c, msg = self._build(monkeypatch, score=0.95, sql="")
        assert "首选计划" not in msg


# ---------------------------------------------------------------------------
# 批2-D 实体预解析注入（子串扫描；Qdrant 不可用静默跳过）
# ---------------------------------------------------------------------------
class TestEntityHint:
    def test_substring_match_injects_hint(self, monkeypatch):
        """子串扫描命中 -> 注入「候选实体」且含用电客户主数据（不含无关实体）"""
        from app.services.qa_example_service import build_entity_hint_block
        points = [
            {"payload": {"entity_name": "用电客户主数据", "entity_code": "dim_cst_elec_cons_cust"}},
            {"payload": {"entity_name": "用电客户主数据（拉链表）", "entity_code": "dim_cst_elec_cons_cust_his"}},
            {"payload": {"entity_name": "里程碑主数据", "entity_code": "dim_ps_milestone"}},
        ]

        class _FakeClient:
            def __init__(self, *a, **k):
                pass

            def scroll_points(self, collection, limit=256, with_payload=True, with_vectors=False):
                for p in points:
                    yield p

        monkeypatch.setattr("app.services.tupu_qdrant_client.TupuQdrantClient", _FakeClient)
        block = build_entity_hint_block(None, "统计用电客户数量")
        assert block and "实体预解析" in block
        assert "用电客户主数据" in block
        assert "里程碑" not in block

    def test_qdrant_unavailable_skips_silently(self, monkeypatch):
        """Qdrant 不可用（子串扫描 + 向量检索均失败）-> 返回空串且不抛（降级不阻断）"""
        from app.services.qa_example_service import build_entity_hint_block

        class _DownClient:
            def __init__(self, *a, **k):
                pass

            def scroll_points(self, *a, **k):
                raise RuntimeError("qdrant down")

        monkeypatch.setattr("app.services.tupu_qdrant_client.TupuQdrantClient", _DownClient)
        monkeypatch.setattr("app.services.entity_attr_vector_service.search_entity_vectors",
                            lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down")))
        assert build_entity_hint_block(None, "统计用电客户数量") == ""


# ---------------------------------------------------------------------------
# 批2-E 指引预载（规则意图分类 -> sql-query/SKILL.md 小节摘录）
# ---------------------------------------------------------------------------
class TestGuidancePreload:
    def test_count_intent_injects_agg_guidance(self):
        from app.services.query_contract import build_guidance_block
        g = build_guidance_block("统计用电客户数量")
        assert g and "写法指引" in g and "COUNT(*)" in g

    def test_rank_intent_injects_rank_guidance(self):
        from app.services.query_contract import build_guidance_block
        g = build_guidance_block("用电量最大的前10个客户")
        assert g and "ORDER BY" in g

    def test_ratio_intent_injects_group_guidance(self):
        from app.services.query_contract import build_guidance_block
        g = build_guidance_block("各电压等级客户占比")
        assert g and ("占比" in g or "GROUP BY" in g)

    def test_no_intent_no_guidance(self):
        from app.services.query_contract import build_guidance_block
        assert build_guidance_block("什么是变压器") == ""
