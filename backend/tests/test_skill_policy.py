"""test_skill_policy.py - SkillPolicyMiddleware 硬校验测试（受控 Skill 问答平台 v2，设计 §6）

覆盖：禁用工具拦截、越权工具拦截、引擎优先（先 batch 再取数）、引擎锁定后其余
数据工具失效、模板外 SQL 拒绝、拿到结果后终止检索、第二次违规阻断、read_file 不误伤。
"""
import asyncio
import json
from types import SimpleNamespace

import pytest

from app.services.skill_catalog import SkillCatalog, get_catalog
from app.services.skill_policy import SkillPolicyMiddleware
from app.services.skill_router import route_user_input
from app.services.query_contract import QueryContract
from tests._tpl_helpers import relationship_template_sql

# step1 模板允许的物理表（与 SKILL.md x_tupu.entity_aliases 一致）
VALID_RELATIONSHIP_SQL = """
SELECT '用电户' AS ctype, ec.elec_cons_cust_id AS cid, c.cust_name, i.inst_id AS iid, i.dist_sta_id AS sid
FROM dim_cst_elec_cons_cust ec
JOIN cms20_cst_cust c ON ec.cust_id = c.cust_id
JOIN dim_cst_inst_elec_cons i ON ec.elec_cons_cust_id = i.elec_cons_cust_id
LEFT JOIN dim_cst_dist_sta ds ON i.dist_sta_id = ds.dist_sta_id
WHERE i.inst_usage_cls = '01'
"""


@pytest.fixture
def relationship_contract():
    r = route_user_input("所有用电户与配变户变关系")
    assert r.route_type == "scenario"
    return r.contract


@pytest.fixture
def policy():
    return SkillPolicyMiddleware(catalog=get_catalog())


def _tc(name, args=None):
    return {"name": name, "id": f"id-{name}", "args": args or {}}


def _make_request(policy, contract, tc, result=None):
    """构造中间件请求：result 为 handler 返回值（可传 callable 模拟 handler）。"""
    req = SimpleNamespace(
        tool_call=tc,
        runtime=SimpleNamespace(context={"contract": contract}, config=None),
        state=None,
    )

    async def handler(request):
        if callable(result):
            return result(request)
        return result if result is not None else json.dumps({"ok": True})

    return req, handler


def _run(policy, contract, tc, result=None):
    req, handler = _make_request(policy, contract, tc, result)
    return asyncio.run(policy.awrap_tool_call(req, handler))


class TestForbiddenAndAllowedTools:
    def test_task_blocked(self, policy, relationship_contract):
        out = _run(policy, relationship_contract, _tc("task", {"description": "x"}))
        assert "SkillPolicy" in out.content and "拒绝" in out.content
        assert "task" in out.content

    def test_write_file_blocked(self, policy, relationship_contract):
        out = _run(policy, relationship_contract, _tc("write_file", {}))
        assert "SkillPolicy" in out.content

    def test_glob_blocked(self, policy, relationship_contract):
        out = _run(policy, relationship_contract, _tc("glob", {}))
        assert "SkillPolicy" in out.content

    def test_out_of_allowed_tool_blocked(self, policy, relationship_contract):
        # execute 是禁用工具；用一个既不在允许集也不在禁用集的工具名
        out = _run(policy, relationship_contract, _tc("search_entities", {}))
        assert "不在本步骤允许范围" in out.content

    def test_read_file_allowed(self, policy, relationship_contract):
        out = _run(policy, relationship_contract, _tc("read_file", {"file_path": "/skills/scenarios/distribution-overload/SKILL.md"}))
        assert out == json.dumps({"ok": True}) or out.content == json.dumps({"ok": True})


class TestEngineFirst:
    def test_data_tool_before_engine_rejected(self, policy, relationship_contract):
        out = _run(policy, relationship_contract, _tc("execute_sql", {"sql": VALID_RELATIONSHIP_SQL}))
        assert "batch_entity_source_mode" in out.content  # 提示先确认数据源模式

    def test_batch_locks_engine(self, policy, relationship_contract):
        res = json.dumps({"entity_codes": ["dim_cst_elec_cons_cust"], "recommended_tool": "execute_doris_sql",
                          "has_catalog": True, "doris_catalog": "pg_tupu"})
        out = _run(policy, relationship_contract, _tc("batch_entity_source_mode", {"entity_codes": ["x"]}), res)
        assert relationship_contract.selected_engine == "doris"
        assert relationship_contract.engine_locked is True
        # 引擎锁定后只允许 doris 工具 + 非数据工具
        assert "execute_doris_sql" in relationship_contract.allowed_tools
        assert "execute_sql" not in relationship_contract.allowed_tools
        assert "execute_api_sql" not in relationship_contract.allowed_tools

    def test_engine_locked_other_tool_rejected(self, policy, relationship_contract):
        self.test_batch_locks_engine(policy, relationship_contract)
        out = _run(policy, relationship_contract, _tc("execute_sql", {"sql": VALID_RELATIONSHIP_SQL}))
        assert "引擎" in out.content or "不在本步骤允许范围" in out.content


class TestTemplateAndStop:
    def test_template_violation_rejected(self, policy):
        contract = route_user_input("所有用电户与配变户变关系").contract
        # 先锁引擎（physical），让 execute_sql 进入模板校验阶段
        _run(policy, contract, _tc("batch_entity_source_mode", {"entity_codes": ["x"]}),
             json.dumps({"recommended_tool": "execute_sql"}))
        bad = "SELECT * FROM dim_cst_elec_cons_cust UNION SELECT * FROM outside_table"
        out = _run(policy, contract, _tc("execute_sql", {"sql": bad}))
        assert "模板" in out.content

    def _lock_physical(self, policy, contract):
        _run(policy, contract, _tc("batch_entity_source_mode", {"entity_codes": ["x"]}),
             json.dumps({"recommended_tool": "execute_sql", "has_catalog": False, "has_api_integration": False}))
        assert contract.selected_engine == "physical"

    def test_valid_sql_passes_and_marks_result(self, policy, relationship_contract):
        self._lock_physical(policy, relationship_contract)
        res = json.dumps({"row_count": 101, "columns": ["a"], "rows": [["1"]], "result_available_for_ui": True})
        # P0-2 严格模式：合法 SQL 必须是模板派生（真实模板），自定义简化查询会被拒
        out = _run(policy, relationship_contract, _tc("execute_sql", {"sql": relationship_template_sql()}), res)
        # 终端步骤拿到结果 -> 标记 result_obtained
        assert relationship_contract.result_obtained is True

    def test_stop_when_blocks_requery(self, policy, relationship_contract):
        self.test_valid_sql_passes_and_marks_result(policy, relationship_contract)
        out = _run(policy, relationship_contract, _tc("execute_sql", {"sql": relationship_template_sql()}))
        assert "终止条件" in out.content

    def test_ddl_rejected(self, policy):
        contract = route_user_input("所有用电户与配变户变关系").contract
        out = _run(policy, contract, _tc("execute_sql", {"sql": "DROP TABLE dim_cst_elec_cons_cust"}))
        assert "拒绝" in out.content or "阻断" in out.content


class TestViolationBudget:
    def test_second_violation_blocks(self, policy, relationship_contract):
        _run(policy, relationship_contract, _tc("task", {}))       # 第1次：拒绝+指引
        out = _run(policy, relationship_contract, _tc("task", {}))  # 第2次：阻断
        assert "已阻断本轮" in out.content

    def test_first_violation_guidance_only(self, policy, relationship_contract):
        out = _run(policy, relationship_contract, _tc("task", {}))
        assert "拒绝" in out.content
        assert "已阻断本轮" not in out.content


class TestMultiEngine:
    """批4 场景迁移：多引擎逐源分发（project-lifecycle-cost 预算 duckdb + 成本 doris）。"""

    @pytest.fixture
    def multi_contract(self):
        r = route_user_input("哪些WBS超预算")
        assert r.route_type == "scenario"
        assert r.skill_id == "project-lifecycle-cost"
        assert r.contract.multi_engine is True
        return r.contract

    def _batch_multi(self, policy, contract):
        res = json.dumps({"items": [
            {"entity_code": "dim_ps_wbs_budget", "source_mode": "api_integration"},
            {"entity_code": "dim_ps_wbs_cost", "source_mode": "sql_integration"},
        ]})
        return _run(policy, contract, _tc("batch_entity_source_mode", {"entity_codes": ["a", "b"]}), res)

    def test_data_tool_before_confirmation_rejected(self, policy, multi_contract):
        out = _run(policy, multi_contract, _tc("execute_entity_api", {"entity_code": "dim_ps_wbs_budget"}))
        assert "batch_entity_source_mode" in out.content  # 先确认数据源模式

    def test_batch_confirms_both_engines(self, policy, multi_contract):
        self._batch_multi(policy, multi_contract)
        assert multi_contract.confirmed_engines() == ["doris", "duckdb"]
        # 确认后收窄为已确认引擎工具并集（两源并存，不唯一）
        assert "execute_entity_api" in multi_contract.allowed_tools
        assert "execute_doris_sql" in multi_contract.allowed_tools

    def test_both_engine_tools_allowed_after_confirm(self, policy, multi_contract):
        self._batch_multi(policy, multi_contract)
        o1 = _run(policy, multi_contract, _tc("execute_entity_api", {"entity_code": "dim_ps_wbs_budget"}))
        o2 = _run(policy, multi_contract, _tc("execute_doris_sql", {"entity_code": "dim_ps_wbs_cost"}))
        assert o1 == json.dumps({"ok": True})
        assert o2 == json.dumps({"ok": True})

    def test_foreign_engine_tool_rejected(self, policy, multi_contract):
        self._batch_multi(policy, multi_contract)
        out = _run(policy, multi_contract, _tc("execute_sql", {"sql": "SELECT 1"}))
        assert "SkillPolicy" in out.content  # execute_sql 不在已确认引擎

    def test_contract_flags(self, multi_contract):
        assert multi_contract.forbid_markdown_detail_table is False  # 答案呈现对比表，不剥离
        assert multi_contract._runtime.get("terminal") is False      # 多源取数后仍可续（取第二源）

    def test_forbidden_still_blocked(self, policy, multi_contract):
        out = _run(policy, multi_contract, _tc("write_file", {}))
        assert "拒绝" in out.content or "阻断" in out.content


class TestReviewP0:
    """评审 P0-1 fail-closed：受控路径契约缺失必须阻断，绝不降级成自由 Agent。"""

    def _no_contract_request(self, handler_result="ok"):
        req = SimpleNamespace(
            tool_call=_tc("execute_entity_api", {"entity_code": "dim_ps_wbs_budget"}),
            runtime=SimpleNamespace(context={}, config=None),  # 无 contract
            state=None,
        )
        async def handler(request):
            return handler_result
        return req, handler

    def test_missing_contract_blocked_by_default(self, policy):
        req, handler = self._no_contract_request()
        out = asyncio.run(policy.awrap_tool_call(req, handler))
        assert "SkillPolicy" in out.content and "契约缺失" in out.content
        assert "拒绝" in out.content or "阻断" in out.content

    def test_missing_contract_passthrough_only_in_compat_mode(self):
        # 仅显式兼容模式放行（测试/显式授权）；生产 path 不允许
        policy = SkillPolicyMiddleware(allow_missing_contract=True)
        req, handler = self._no_contract_request("ok")
        out = asyncio.run(policy.awrap_tool_call(req, handler))
        assert out == "ok"


class TestReviewP1_1IncrementalConfirm:
    """评审 P1-1：多引擎逐实体确认 —— 每次真实新引擎都增量并入（不再要求 confirmed 为空）。"""

    @pytest.fixture
    def multi_contract(self):
        r = route_user_input("哪些WBS超预算")
        assert r.route_type == "scenario"
        return r.contract

    def _batch_one(self, policy, contract, items):
        res = json.dumps({"items": items})
        return _run(policy, contract, _tc("batch_entity_source_mode", {"entity_codes": ["x"]}), res)

    def test_incremental_confirm_accumulates_both_engines(self, policy, multi_contract):
        # 第一次确认：只有预算 -> duckdb
        self._batch_one(policy, multi_contract,
                        [{"entity_code": "dim_ps_wbs_budget", "source_mode": "api_integration"}])
        assert multi_contract.confirmed_engines() == ["duckdb"]
        # 第二次确认：成本 -> doris（P1-1：不再因 confirmed 非空而跳过）
        self._batch_one(policy, multi_contract,
                        [{"entity_code": "dim_ps_wbs_cost", "source_mode": "sql_integration"}])
        assert multi_contract.confirmed_engines() == ["doris", "duckdb"]
        # 实体 -> 引擎映射真实记录
        assert multi_contract.entity_engine_map.get("dim_ps_wbs_budget") == "duckdb"
        assert multi_contract.entity_engine_map.get("dim_ps_wbs_cost") == "doris"

    def test_required_engines_snapshot_grows(self, policy, multi_contract):
        self._batch_one(policy, multi_contract,
                        [{"entity_code": "dim_ps_wbs_budget", "source_mode": "api_integration"}])
        assert multi_contract._runtime.get("required_engines") == ["duckdb"]
        self._batch_one(policy, multi_contract,
                        [{"entity_code": "dim_ps_wbs_cost", "source_mode": "sql_integration"}])
        assert multi_contract._runtime.get("required_engines") == ["doris", "duckdb"]


class TestReviewP1_2CompositeStop:
    """评审 P1-2：多引擎复合终止 —— 两源均取到结果 -> stop.reached + terminal + 移除全部数据工具。"""

    @pytest.fixture
    def multi_contract(self):
        r = route_user_input("哪些WBS超预算")
        assert r.route_type == "scenario"
        return r.contract

    def _confirm_both(self, policy, contract):
        res = json.dumps({"items": [
            {"entity_code": "dim_ps_wbs_budget", "source_mode": "api_integration"},
            {"entity_code": "dim_ps_wbs_cost", "source_mode": "sql_integration"},
        ]})
        _run(policy, contract, _tc("batch_entity_source_mode", {"entity_codes": ["a", "b"]}), res)
        assert contract.confirmed_engines() == ["doris", "duckdb"]

    def test_both_sources_result_triggers_composite_stop(self, policy, multi_contract):
        self._confirm_both(policy, multi_contract)
        assert multi_contract.stop_reached is False
        data_out = json.dumps({"row_count": 5, "columns": ["a"]})
        # 预算源（duckdb -> execute_entity_api）取到结果
        _run(policy, multi_contract, _tc("execute_entity_api", {"entity_code": "dim_ps_wbs_budget"}), data_out)
        assert multi_contract.stop_reached is False  # 仅一源完成，未达复合终止
        # 成本源（doris -> execute_doris_sql）取到结果 -> 复合终止
        _run(policy, multi_contract, _tc("execute_doris_sql", {"entity_code": "dim_ps_wbs_cost"}), data_out)
        assert multi_contract.stop_reached is True
        assert multi_contract._runtime.get("terminal") is True
        # 全部 DATA_TOOLS 从 allowed_tools 移除
        for t in ("execute_sql", "execute_doris_sql", "execute_api_sql", "execute_entity_api"):
            assert t not in multi_contract.allowed_tools

    def test_requery_rejected_after_composite_stop(self, policy, multi_contract):
        self.test_both_sources_result_triggers_composite_stop(policy, multi_contract)
        out = _run(policy, multi_contract, _tc("execute_doris_sql", {"entity_code": "dim_ps_wbs_cost"}),
                   json.dumps({"row_count": 1, "columns": []}))
        assert "多引擎复合终止" in out.content

    def test_single_engine_result_does_not_trigger_composite_stop(self, policy, multi_contract):
        self._confirm_both(policy, multi_contract)
        data_out = json.dumps({"row_count": 5, "columns": ["a"]})
        _run(policy, multi_contract, _tc("execute_entity_api", {"entity_code": "dim_ps_wbs_budget"}), data_out)
        assert multi_contract.stop_reached is False

    def test_interleaved_confirm_query_no_premature_stop(self, policy, multi_contract):
        """评审 P1-1（二轮）：确认预算 -> 取预算 -> 确认成本 -> 取成本，不得提前终止。"""
        # 1) get_entity_source_mode(预算) -> 确认 duckdb
        _run(policy, multi_contract, _tc("get_entity_source_mode", {"entity_code": "dim_ps_wbs_budget"}),
             json.dumps({"entity_code": "dim_ps_wbs_budget", "source_mode": "api_integration"}))
        assert multi_contract.confirmed_engines() == ["duckdb"]
        assert multi_contract.stop_reached is False
        # 2) 取预算（duckdb）-> 只完成 budget，required 含 cost -> 不得提前终止
        _run(policy, multi_contract, _tc("execute_entity_api", {"entity_code": "dim_ps_wbs_budget"}),
             json.dumps({"row_count": 5, "columns": ["a"]}))
        assert multi_contract.stop_reached is False, "只取预算不得触发复合终止"
        # 3) get_entity_source_mode(成本) -> 追加 doris
        _run(policy, multi_contract, _tc("get_entity_source_mode", {"entity_code": "dim_ps_wbs_cost"}),
             json.dumps({"entity_code": "dim_ps_wbs_cost", "source_mode": "sql_integration"}))
        assert multi_contract.confirmed_engines() == ["doris", "duckdb"]
        assert multi_contract.stop_reached is False
        # 4) 取成本 -> 两源取齐 -> 复合终止
        _run(policy, multi_contract, _tc("execute_doris_sql", {"entity_code": "dim_ps_wbs_cost"}),
             json.dumps({"row_count": 3, "columns": ["a"]}))
        assert multi_contract.stop_reached is True
        assert multi_contract._runtime.get("terminal") is True
