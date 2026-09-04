# -*- coding: utf-8 -*-
"""批13-N 首响应延迟治理单测。

覆盖：
1. N2 首个 status yield 位于生成器第一行（get_tupu_agent/锁之前）
2. N3 aget_state 在编排段只出现一次（三次重复读取合并）
3. N4 改写块位于 route_user_input 之后且仅 generic 路径执行；超时预算环境变量化
4. N5 _build_contract_system_message(precomputed_bundle) 跳过内部同步检索
5. N6 main.py lifespan 含 agent 预热后台任务
6. prep 细分计时日志存在
"""
import os
from unittest.mock import patch, MagicMock

import pytest


STREAM_SRC = open(os.path.join(os.path.dirname(__file__), "..", "app", "api", "freeplan", "endpoint.py"),
                  encoding="utf-8").read()
PREP_SRC = open(os.path.join(os.path.dirname(__file__), "..", "app", "api", "freeplan", "prep.py"),
                encoding="utf-8").read()
DI_SRC = open(os.path.join(os.path.dirname(__file__), "..", "app", "api", "data_intelligence.py"),
              encoding="utf-8").read()
MAIN_SRC = open(os.path.join(os.path.dirname(__file__), "..", "app", "main.py"),
                encoding="utf-8").read()


class TestN2FirstByte:
    def test_status_yield_is_first_statement(self):
        """首个 yield(status) 必须在 get_tupu_agent 与锁获取之前。"""
        y = STREAM_SRC.find('yield f"event: status')
        g = STREAM_SRC.find("get_tupu_agent")
        lock = STREAM_SRC.find("_session_lock.acquire")
        assert 0 < y < g < lock, f"yield@{y} get_tupu_agent@{g} lock@{lock}"

    def test_old_status_yield_removed(self):
        """旧的编排尾部 status yield 已删除（全文仅一处）。"""
        assert STREAM_SRC.count('text\': \'小探正在运行中\'') == 1

    def test_prep_timing_log_exists(self):
        assert "[PrepTiming]" in STREAM_SRC and "_prep_timing" in STREAM_SRC


class TestN3SingleStateRead:
    def test_aget_state_once(self):
        """编排段 aget_state 只出现一次（批13-D：prep 段迁至 freeplan/prep.py，非 wait_for 恰 1 次）。"""
        n_prep = PREP_SRC.count("agent.aget_state(")
        n_prep_tail = PREP_SRC.count("wait_for(agent.aget_state(")
        assert n_prep - n_prep_tail == 1, f"prep 编排段 aget_state 出现 {n_prep - n_prep_tail} 次"

    def test_shared_state_values_used_for_scope_skill_history(self):
        for kw in ('_shared_state_values.get("last_scope")',
                   '_shared_state_values.get("last_skill")',
                   '_has_history = bool(_shared_state_values.get("messages"))'):
            assert kw in PREP_SRC


class TestN4RewriteAfterRoute:
    def test_rewrite_after_route(self):
        """改写块必须位于 route_user_input 调用之后（批13-D：prep 段迁至 freeplan/prep.py）。"""
        r = PREP_SRC.find("route_user_input(req.user_input")
        w = PREP_SRC.find("rewrite_followup_question, req.user_input")
        assert 0 < r < w

    def test_rewrite_only_generic(self):
        """改写执行条件含 generic 路由确认（批13-D：prep 段）。"""
        seg = PREP_SRC[PREP_SRC.find("S3b（G9）追问改写"):PREP_SRC.find('prep_timing["rewrite_ms"]')]
        assert "_is_generic_route" in seg and "if _is_generic_route and _contract is not None" in seg

    def test_timeout_env_var(self):
        from app.services import followup_rewrite as frw
        assert frw._REWRITE_TIMEOUT == float(os.getenv("TUPU_REWRITE_TIMEOUT", "8.0"))
        assert "TUPU_REWRITE_TIMEOUT" in open(
            os.path.join(os.path.dirname(__file__), "..", "app", "services", "followup_rewrite.py"),
            encoding="utf-8").read()


class TestN5PrefetchBundle:
    def test_build_msg_uses_precomputed_without_internal_retrieval(self):
        """precomputed_bundle 非空时不触发内部同步检索（批13-C：金标 bundle）。"""
        from app.api.data_intelligence import _build_contract_system_message
        from app.services.query_contract import QueryContract
        contract = QueryContract.generic(route_reason="test")
        bundle = {"golden_block": "\n金标锚定块", "golden_hits": [{"id": 1, "score": 0.99, "sql": "SELECT 1", "engine": "doris"}],
                  "entity_hint_block": ""}
        with patch("app.services.golden_qa_service.retrieve_golden_bundle") as mock_ret:
            msg = _build_contract_system_message(contract, question="查询项目数量", precomputed_bundle=bundle)
            mock_ret.assert_not_called()
        assert "首选计划" in msg or "金标锚定块" in msg
        hits = getattr(contract, "_runtime", {}).get("golden_hits")
        assert hits, "precomputed bundle 命中应写入 contract._runtime.golden_hits"

    def test_prefetch_task_wiring(self):
        """prep 段启动后台预取并在契约组装点收割（批13-D：prep 段迁至 freeplan/prep.py）。"""
        assert "asyncio.create_task(asyncio.to_thread(_prefetch_bundle))" in PREP_SRC
        assert "precomputed_bundle=_precomputed_bundle" in PREP_SRC


class TestN6Warmup:
    def test_main_has_warmup_task(self):
        assert "_warmup_tupu_agent" in MAIN_SRC and "create_task(_warmup_tupu_agent())" in MAIN_SRC
