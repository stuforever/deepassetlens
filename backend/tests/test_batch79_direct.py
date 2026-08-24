# -*- coding: utf-8 -*-
"""test_batch79_direct.py - 批7 检索单入口+短窗缓存 / 批9 模板直出管道 单测"""
import pytest


# ---------------------------------------------------------------------------
# 批6-R2/批9 前置：intent_classifier 纯规则判定
# ---------------------------------------------------------------------------
class TestIntentClassifier:
    def test_count_intent_positive(self):
        from app.services.intent_classifier import classify_intent, is_count_intent
        assert classify_intent("统计用电客户数量") == "count"
        assert is_count_intent("用电客户有多少个")
        assert is_count_intent("统计用电客户总数")

    def test_count_intent_negative(self):
        from app.services.intent_classifier import is_count_intent
        assert not is_count_intent("各电压等级客户占比")       # 聚合
        assert not is_count_intent("合同容量最大的用电客户是谁")  # 排名
        assert not is_count_intent("列出所有客户名称")

    def test_dynamic_condition_detection(self):
        from app.services.intent_classifier import has_dynamic_condition
        assert has_dynamic_condition("数量大于1000的客户")
        assert has_dynamic_condition("今年新增了多少客户")
        assert has_dynamic_condition("CUS0001 这个客户的容量")
        assert not has_dynamic_condition("统计用电客户数量")

    def test_aggregate_vague_delegation_consistency(self):
        """skill_router 委托 intent_classifier 后行为一致（批6-R2）"""
        from app.services.skill_router import SkillRouter
        from app.services import intent_classifier
        agg = SkillRouter.detect_aggregate_intent("各行业的用电客户分布")
        assert agg is not None and agg["dimension_hint"] == "ind_cls_name"
        assert agg == intent_classifier.detect_aggregate_intent("各行业的用电客户分布")
        assert SkillRouter.detect_vague_intent("客户情况怎么样")
        assert not SkillRouter.detect_vague_intent("统计用电客户总数")


# ---------------------------------------------------------------------------
# 批7：检索单入口 + 短窗缓存
# ---------------------------------------------------------------------------
class TestRetrieveContextBundle:
    def test_single_embedding_and_cache_hit(self, monkeypatch):
        """一次 embedding 双集合复用；60s 内二次提问 0 远程调用（缓存命中）"""
        from app.services import qa_example_service as qes
        qes.clear_bundle_cache()
        calls = {"embed": 0}

        def _fake_embed(db, texts):
            calls["embed"] += 1
            return [[0.1] * 4]

        monkeypatch.setattr(qes, "_embed_question", _fake_embed)
        monkeypatch.setattr(qes, "search_qa_examples",
                            lambda db, q, top=3, score_threshold=None, precomputed_vec=None: [
                                {"id": "e1", "score": 1.0, "question_raw": "统计用电客户总数",
                                 "sql": "SELECT 1", "route_type": "generic", "engine": "doris"}])
        # 实体提示走子串扫描（scroll，不消耗 embedding）
        class _FakeClient:
            def __init__(self, *a, **k):
                pass

            def scroll_points(self, collection, limit=256, **kw):
                return [{"payload": {"entity_name": "用电客户主数据", "entity_code": "dim_cst_elec_cons_cust"}}]

        monkeypatch.setattr("app.services.tupu_qdrant_client.TupuQdrantClient", _FakeClient)

        b1 = qes.retrieve_context_bundle(None, "统计用电客户数量")
        b2 = qes.retrieve_context_bundle(None, "统计用电客户数量")  # TTL 内二问
        assert calls["embed"] == 1, f"两次调用应只 embedding 一次，实际 {calls['embed']}"
        assert "统计用电客户总数" in b1["examples_block"]
        assert b1["example_hits"] and b1["example_hits"][0]["id"] == "e1"
        assert "实体预解析" in b1["entity_hint_block"]
        assert b2 is b1  # 缓存返回同一 bundle 对象（0 远程调用）

    def test_qdrant_down_degrades_silently(self, monkeypatch):
        """Qdrant 断开：示例块为空、实体提示为空、不抛异常"""
        from app.services import qa_example_service as qes
        qes.clear_bundle_cache()
        monkeypatch.setattr(qes, "_embed_question", lambda db, t: [])
        monkeypatch.setattr(qes, "_safe_client", lambda: None)

        class _BoomClient:
            def __init__(self, *a, **k):
                raise RuntimeError("qdrant down")

        monkeypatch.setattr("app.services.tupu_qdrant_client.TupuQdrantClient", _BoomClient)
        bundle = qes.retrieve_context_bundle(None, "统计用电客户数量")
        assert bundle["examples_block"] == ""
        assert bundle["example_hits"] == []
        assert bundle["entity_hint_block"] == ""


# ---------------------------------------------------------------------------
# 批9：模板直出管道
# ---------------------------------------------------------------------------
def _generic_contract_with_hit(score=0.99, sql="SELECT COUNT(*) AS total FROM pg_tupu.public.dim_cst_elec_cons_cust"):
    from app.services.query_contract import QueryContract
    c = QueryContract.generic(route_reason="test")
    c._runtime["example_hits"] = [{
        "id": "ex-1", "score": score, "question_raw": "统计用电客户总数",
        "sql": sql, "route_type": "generic", "engine": "doris",
    }]
    return c


class TestDirectEligibility:
    def test_eligible_count_question(self):
        from app.services.direct_pipeline import evaluate_direct_eligibility
        plan = evaluate_direct_eligibility(_generic_contract_with_hit(), "统计用电客户数量")
        assert plan is not None
        assert plan["engine"] == "doris" and plan["score"] >= 0.95
        assert "COUNT" in plan["sql"]

    def test_below_threshold_not_eligible(self):
        from app.services.direct_pipeline import evaluate_direct_eligibility
        assert evaluate_direct_eligibility(_generic_contract_with_hit(score=0.92), "统计用电客户数量") is None

    def test_dynamic_condition_not_eligible(self):
        from app.services.direct_pipeline import evaluate_direct_eligibility
        assert evaluate_direct_eligibility(_generic_contract_with_hit(), "统计用电客户中数量大于100的有几个") is None

    def test_scenario_route_not_eligible(self):
        from app.services.direct_pipeline import evaluate_direct_eligibility
        c = _generic_contract_with_hit()
        c.route_type = "scenario"
        assert evaluate_direct_eligibility(c, "统计用电客户数量") is None

    def test_empty_sql_or_api_engine_not_eligible(self):
        from app.services.direct_pipeline import evaluate_direct_eligibility
        c = _generic_contract_with_hit()
        c._runtime["example_hits"][0]["sql"] = ""
        assert evaluate_direct_eligibility(c, "统计用电客户数量") is None
        c2 = _generic_contract_with_hit()
        c2._runtime["example_hits"][0]["engine"] = "api_integration"
        assert evaluate_direct_eligibility(c2, "统计用电客户数量") is None


class TestAnswerRenderer:
    def test_scalar_count_rendering(self):
        from app.services.answer_renderer import render_template_answer
        hit = {"question_raw": "统计用电客户总数"}
        res = {"columns": ["total"], "rows": [[3]], "row_count": 1,
               "sql": "SELECT COUNT(*) AS total FROM pg_tupu.public.dim_cst_elec_cons_cust"}
        ans = render_template_answer("统计用电客户数量", hit, res)
        assert "**3**" in ans
        assert "统计口径" in ans and "dim_cst_elec_cons_cust" in ans
        assert "数据截至" in ans

    def test_multi_row_no_markdown_table(self):
        from app.services.answer_renderer import render_template_answer
        res = {"columns": ["a", "b"], "rows": [[1, 2], [3, 4]], "row_count": 2, "sql": "SELECT a,b FROM t"}
        ans = render_template_answer("随便看看", {}, res)
        assert "|---" not in ans and "2 行" in ans


class TestRunDirectPipeline:
    def _patch_env(self, monkeypatch, dispatch_fn):
        import app.services.kg_action_handlers as kgh
        monkeypatch.setattr(kgh, "dispatch_kg_action", dispatch_fn)
        import app.services.engine_query_log as eql
        monkeypatch.setattr(eql, "record_query_log", lambda **kw: None)
        import app.services.qa_example_service as qes
        monkeypatch.setattr(qes, "bump_hit_count", lambda db, ids: None)
        import app.services.direct_pipeline as dp

    def test_success_path(self, monkeypatch):
        from app.services.direct_pipeline import run_direct_pipeline

        def _fake_dispatch(action, body):
            if action == "validate_safe_sql":
                return {"safe": True}
            if action == "execute_doris_sql":
                return {"columns": ["total"], "rows": [[3]], "row_count": 1,
                        "sql": body.get("sql"), "verification": {"warnings": []}}
            raise AssertionError(f"unexpected action {action}")

        self._patch_env(monkeypatch, _fake_dispatch)
        plan = evaluate_direct_plan()
        out = run_direct_pipeline(plan, "统计用电客户数量", thread_id="t1")
        assert out["tool"] == "execute_doris_sql"
        assert "**3**" in out["answer"]
        assert out["result"]["row_count"] == 1

    def test_validate_reject_raises(self, monkeypatch):
        from app.services.direct_pipeline import run_direct_pipeline, DirectPipelineError

        def _fake_dispatch(action, body):
            if action == "validate_safe_sql":
                return {"safe": False, "reason": "非只读语句"}
            raise AssertionError(action)

        self._patch_env(monkeypatch, _fake_dispatch)
        with pytest.raises(DirectPipelineError):
            run_direct_pipeline(evaluate_direct_plan(), "统计用电客户数量")

    def test_exec_error_raises_fallback(self, monkeypatch):
        from app.services.direct_pipeline import run_direct_pipeline, DirectPipelineError

        def _fake_dispatch(action, body):
            if action == "validate_safe_sql":
                return {"safe": True}
            return {"error": "(1051,) Unknown table 'cms20_cst_cust'"}

        self._patch_env(monkeypatch, _fake_dispatch)
        with pytest.raises(DirectPipelineError):
            run_direct_pipeline(evaluate_direct_plan(), "统计用电客户数量")


def evaluate_direct_plan():
    """测试辅助：直接构造 plan（不经契约）"""
    from app.services.direct_pipeline import DIRECT_PIPELINE_SIM
    return {"hit": {"id": "ex-1", "score": 0.99, "question_raw": "统计用电客户总数"},
            "engine": "doris", "score": 0.99,
            "sql": "SELECT COUNT(*) AS total FROM pg_tupu.public.dim_cst_elec_cons_cust"}
