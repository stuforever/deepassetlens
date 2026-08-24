# -*- coding: utf-8 -*-
"""test_batch56_cache_route.py - 批5 前缀缓存最大化 / 批6 路由健壮化 单测"""
import os


# ---------------------------------------------------------------------------
# 批5-C1：契约文案模板化（同场景逐字节一致）
# ---------------------------------------------------------------------------
class TestContractTemplating:
    def test_same_contract_byte_identical(self, monkeypatch):
        """同契约+同问题两次构建 -> 输出逐字节一致（前缀缓存命中前提）"""
        import app.services.qa_example_service as qes
        from app.services.query_contract import QueryContract
        from app.api.data_intelligence import _build_contract_system_message
        hits = [{"id": "e1", "score": 0.99, "question_raw": "统计用电客户总数",
                 "sql": "SELECT 1", "engine": "doris"}]
        monkeypatch.setattr(qes, "retrieve_context_bundle", lambda db, q, **kw: {
            "examples_block": "\n参考示例...", "example_hits": hits, "entity_hint_block": ""})
        monkeypatch.setattr(qes, "bump_hit_count", lambda db, ids: None)
        c = QueryContract.generic(route_reason="t")
        m1 = _build_contract_system_message(c, question="统计用电客户数量")
        c2 = QueryContract.generic(route_reason="t")
        m2 = _build_contract_system_message(c2, question="统计用电客户数量")
        assert m1 == m2

    def test_dynamic_blocks_at_tail(self, monkeypatch):
        """变化内容（示例块）追加在骨架之后：无指引触发的问题上，无命中消息是命中消息的前缀
        （骨架逐字节一致，差异只在尾部注入块）"""
        import app.services.qa_example_service as qes
        from app.services.query_contract import QueryContract
        from app.api.data_intelligence import _build_contract_system_message
        monkeypatch.setattr(qes, "bump_hit_count", lambda db, ids: None)
        c = QueryContract.generic(route_reason="t")
        monkeypatch.setattr(qes, "retrieve_context_bundle", lambda db, q, **kw: {
            "examples_block": "", "example_hits": [], "entity_hint_block": ""})
        m_no_hit = _build_contract_system_message(c, question="你好")  # 无指引触发词
        c2 = QueryContract.generic(route_reason="t")
        monkeypatch.setattr(qes, "retrieve_context_bundle", lambda db, q, **kw: {
            "examples_block": "\n参考示例...", "example_hits": [], "entity_hint_block": ""})
        m_hit = _build_contract_system_message(c2, question="你好")
        assert m_hit.startswith(m_no_hit)


# ---------------------------------------------------------------------------
# 批5-C3/C4：摘要治理事件 + 缓存字段提取
# ---------------------------------------------------------------------------
class TestCacheObservability:
    def test_extract_usage_reads_cached_tokens(self):
        """response_metadata.token_usage.prompt_tokens_details.cached_tokens 兜底捞取（ark 实测路径）"""
        from app.services.llm_client import _extract_usage

        class _Resp:
            additional_kwargs = {}
            response_metadata = {"token_usage": {
                "prompt_tokens": 100, "completion_tokens": 5, "total_tokens": 105,
                "prompt_tokens_details": {"cached_tokens": 2048},
            }}

        u = _extract_usage(_Resp())
        assert u["cache_hit_tokens"] == 2048
        assert u["prompt_tokens"] == 100

    def test_extract_usage_without_cache_fields(self):
        from app.services.llm_client import _extract_usage

        class _Resp:
            additional_kwargs = {}
            response_metadata = {}

        assert _extract_usage(_Resp()) is None

    def test_summarization_governance_event_wired(self):
        """批5-C3：摘要触发记治理事件（源码接线检查，防回归丢失可观测点）"""
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "app", "services", "tupu_deepagent.py"), encoding="utf-8") as f:
            src = f.read()
        assert "context.summarized" in src
        assert "_should_summarize" in src

    def test_tool_order_fixed(self):
        """批5-C2：MCP 工具装配按名排序（源码接线检查）"""
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "..", "app", "services", "tupu_deepagent.py"), encoding="utf-8") as f:
            src = f.read()
        assert 'sorted(mcp_tools' in src


# ---------------------------------------------------------------------------
# 批6-R2：intent_classifier 收拢（路由/指引预载/直出三处共用）
# ---------------------------------------------------------------------------
class TestIntentConsolidation:
    def test_guidance_uses_shared_module(self):
        """query_contract 指引预载走 intent_classifier.guidance_labels_for"""
        from app.services.query_contract import build_guidance_block
        from app.services.intent_classifier import guidance_labels_for
        assert guidance_labels_for("各电压等级客户占比")[0] == "聚合类"
        assert build_guidance_block("各电压等级客户占比") != ""  # 回归：占比仍触发聚合指引
        assert build_guidance_block("用电量最大的前10个客户") != ""  # 排名指引

    def test_classify_three_categories(self):
        from app.services.intent_classifier import classify_intent
        assert classify_intent("客户情况怎么样") == "vague"
        assert classify_intent("各电压等级客户分布") == "aggregate"
        assert classify_intent("合同容量最大的客户是谁") == "topn"
        assert classify_intent("统计用电客户数量") == "count"
