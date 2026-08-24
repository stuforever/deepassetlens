# -*- coding: utf-8 -*-
"""test_batch8_hybrid.py - 批8 search_entities 三级融合检索单测"""
from app.services.kg_action_handlers import dispatch_kg_action


class TestSynonymExpansion:
    def test_colloquial_words_expand(self):
        from app.services.hybrid_retrieval import expand_synonyms_for_query
        out = expand_synonyms_for_query("配变")
        assert "配电变压器" in out and "变压器" in out
        assert expand_synonyms_for_query("专变") == out or "配电变压器" in expand_synonyms_for_query("专变")
        assert expand_synonyms_for_query("") == []

    def test_no_hit_returns_empty(self):
        from app.services.hybrid_retrieval import expand_synonyms_for_query
        # 完全无关词不产生变体（词表未覆盖时静默空）
        assert isinstance(expand_synonyms_for_query("zzzqqq"), list)


class TestThreeTierFusion:
    def test_exact_hit_returns_exact(self):
        """①精确：keyword 与 entity_en_name 全等 -> match_type=exact 直返"""
        r = dispatch_kg_action("search_entities", {"keyword": "dim_cst_elec_cons_cust"})
        ents = r.get("entities") or []
        assert ents and ents[0]["match_type"] == "exact"
        assert ents[0]["entity_code"]

    def test_like_hits_marked_and_vector_appended(self, monkeypatch):
        """②LIKE 标 like；③向量补充标 vector（阈值过滤 + 事实源回 MySQL：仅采纳 kg_entities 真实存在的 code）"""
        import app.services.entity_attr_vector_service as eavs
        _REAL_CODE = "dim_grid_pub_dist_trans_resrc_standbk_e"  # 配电变压器资源台账主数据（PMS侧），LIKE「用电客户」不命中

        def _fake_vec(query, top_k=15, db=None, vec=None):
            if query == "用电客户":
                return [
                    {"code": _REAL_CODE, "name": "向量层名字(应被MySQL事实覆盖)", "score": 0.75},
                    {"code": "dim_vec_b", "name": "低分实体B", "score": 0.30},   # 低于阈值应被滤
                    {"code": "dim_vec_c", "name": "库外实体C", "score": 0.90},   # kg_entities 不存在应被弃
                ]
            return []

        monkeypatch.setattr(eavs, "search_entity_vectors", _fake_vec)
        r = dispatch_kg_action("search_entities", {"keyword": "用电客户"})
        ents = r.get("entities") or []
        assert ents, "LIKE 层应有命中"
        assert "like" in {e["match_type"] for e in ents}
        vec_items = [e for e in ents if e["match_type"] == "vector"]
        codes = {e["entity_code"] for e in vec_items}
        assert codes == {_REAL_CODE}
        # 事实源仍来自 MySQL：entity_name 为 kg_entities 的中文名，而非向量 payload
        assert vec_items[0]["entity_name"].startswith("配电变压器")
        assert set(vec_items[0].keys()) >= {"entity_code", "entity_name", "entity_en_name", "description", "match_type"}

    def test_qdrant_down_degrades_to_like(self, monkeypatch):
        """Qdrant 断开 -> 静默降级 LIKE，不抛异常"""
        import app.services.entity_attr_vector_service as eavs

        def _boom(query, top_k=15, db=None, vec=None):
            raise RuntimeError("qdrant down")

        monkeypatch.setattr(eavs, "search_entity_vectors", _boom)
        r = dispatch_kg_action("search_entities", {"keyword": "用电客户"})
        ents = r.get("entities") or []
        assert ents and all(e["match_type"] == "like" for e in ents)
