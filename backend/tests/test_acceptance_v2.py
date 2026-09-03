"""test_acceptance_v2.py - 受控 Skill 问答平台 v2 验收基线固化（设计 §11）

把设计最小验收用例固化为可执行基线：全部通过 = 受控边界未被破坏。
覆盖 10 条验收（代码级）；前端五卡展示由浏览器回归另测（见改动报告）。

铁律复核：场景未命中绝不回退自由 free-plan；引擎不由模型拍板；
拿到结果禁重查；二次违规阻断；输出契约清洗。
"""
import asyncio
import json
from types import SimpleNamespace

import pytest

from app.services.skill_catalog import get_catalog
from app.services.skill_policy import SkillPolicyMiddleware
from app.services.skill_router import route_user_input
from app.services.query_contract import ABSOLUTE_FORBIDDEN_TOOLS
from tests._tpl_helpers import relationship_template_sql


@pytest.fixture
def policy():
    return SkillPolicyMiddleware(catalog=get_catalog())


@pytest.fixture
def relationship_contract():
    r = route_user_input("所有用电户与配变户变关系")
    assert r.route_type == "scenario"
    return r.contract


def _tc(name, args=None):
    return {"name": name, "id": f"id-{name}", "args": args or {}}


def _run(policy, contract, tc, result=None):
    req = SimpleNamespace(
        tool_call=tc,
        runtime=SimpleNamespace(context={"contract": contract}, config=None),
        state=None,
    )

    async def handler(request):
        if callable(result):
            return result(request)
        return result if result is not None else json.dumps({"ok": True})

    return asyncio.run(policy.awrap_tool_call(req, handler))


class TestAcceptance:
    """设计 §11 验收用例（代码级固化）。"""

    # 1) 所有用电户与配变户变关系 -> 唯一命中 distribution-overload.relationship
    def test_acceptance_01_scenario_relationship(self):
        r = route_user_input("所有用电户与配变户变关系")
        assert r.route_type == "scenario"
        assert r.skill_id == "distribution-overload"
        assert r.workflow_step == "relationship"

    # 2) 白名单工具：batch_entity_source_mode + 数据工具 + read_file
    def test_acceptance_02_whitelist(self, relationship_contract):
        assert "batch_entity_source_mode" in relationship_contract.allowed_tools
        for t in ("execute_sql", "execute_doris_sql", "execute_api_sql"):
            assert t in relationship_contract.allowed_tools
        assert "read_file" in relationship_contract.allowed_tools

    # 3) task / 自由 Shell / 模板外 SQL 被拒
    def test_acceptance_03_forbidden_rejected(self, policy, relationship_contract):
        # 批13-Z 后剧本声明 allow_subagents=true（task 契约层放行）——拒绝路径显式置 False 构造
        relationship_contract.allow_subagents = False
        for name in ("task", "write_file", "execute", "grep", "glob"):
            out = _run(policy, relationship_contract, _tc(name, {}))
            assert "SkillPolicy" in out.content, f"{name} 未被拒"
        # 模板外 SQL（非法表）被拒：先锁定引擎，让执行到达模板校验分支
        batch_out = json.dumps({"recommended_tool": "execute_doris_sql", "entity_codes": ["a"]})
        _run(policy, relationship_contract, _tc("batch_entity_source_mode", {}), result=batch_out)
        out = _run(policy, relationship_contract, _tc("execute_doris_sql", {"sql": "SELECT * FROM secret_table"}))
        assert "模板校验" in out.content

    # 4) 引擎先确认后取数：batch 前禁数据工具
    def test_acceptance_04_engine_first(self, policy, relationship_contract):
        out = _run(policy, relationship_contract, _tc("execute_sql", {"sql": "SELECT 1"}))
        assert "batch_entity_source_mode" in out.content

    # 5) 引擎锁定后其余数据工具失效（allowed_tools 被收窄，其余工具直接不在允许范围）
    def test_acceptance_05_engine_lock_narrows(self, policy, relationship_contract):
        batch_out = json.dumps({"recommended_tool": "execute_doris_sql", "entity_codes": ["a"]})
        _run(policy, relationship_contract, _tc("batch_entity_source_mode", {}), result=batch_out)
        assert relationship_contract.selected_engine == "doris"
        # 锁定后收窄：仅保留 doris 引擎工具 + 非数据工具
        assert "execute_doris_sql" in relationship_contract.allowed_tools
        assert "execute_sql" not in relationship_contract.allowed_tools
        out = _run(policy, relationship_contract, _tc("execute_sql", {"sql": "SELECT 1"}))
        assert "SkillPolicy" in out.content
        assert "execute_doris_sql" in out.content  # 指引里明确只允许锁定引擎的工具

    # 6) 空结果不换引擎重查（拿到结果即终止）
    def test_acceptance_06_no_requery_after_result(self, policy, relationship_contract):
        # 终端步骤：先 batch 锁定引擎，再拿 row_count 结果 -> 再查被拒
        batch_out = json.dumps({"recommended_tool": "execute_doris_sql", "entity_codes": ["a"]})
        _run(policy, relationship_contract, _tc("batch_entity_source_mode", {}), result=batch_out)
        data_out = json.dumps({"row_count": 3, "columns": []})
        # P0-2 严格模式：数据工具 SQL 必须模板派生（真实模板），自定义 SELECT 1 会被拒
        out = _run(policy, relationship_contract, _tc("execute_doris_sql", {"sql": relationship_template_sql()}), result=data_out)
        # 数据工具返回 row_count -> 标记结果；终端步骤禁止继续检索
        out2 = _run(policy, relationship_contract, _tc("execute_doris_sql", {"sql": relationship_template_sql()}), result=data_out)
        assert "禁止重复/继续检索" in out2.content

    # 7) 场景未命中 -> 低权限只读 generic，绝不回退自由 free-plan
    def test_acceptance_07_no_free_plan_fallback(self):
        r = route_user_input("今天天气怎么样")
        assert r.route_type == "generic"
        assert ABSOLUTE_FORBIDDEN_TOOLS <= set(r.contract.forbidden_tools)
        assert "task" not in r.contract.allowed_tools

    # 8) 二次违规终止本轮
    def test_acceptance_08_second_violation_blocks(self, policy, relationship_contract):
        relationship_contract.allow_subagents = False  # 批13-Z：剧本默认放行 task，拒绝路径显式构造
        o1 = _run(policy, relationship_contract, _tc("task", {}))
        assert "拒绝" in o1.content and "阻断" not in o1.content
        o2 = _run(policy, relationship_contract, _tc("task", {}))
        assert "已阻断本轮" in o2.content

    # 9) 前端数据面：route/contract 契约字段完整（五卡数据源）
    def test_acceptance_09_contract_fields_complete(self):
        r = route_user_input("所有用电户与配变户变关系")
        d = r.to_dict()
        assert d["contract"]["skill_id"] == "distribution-overload"
        assert d["contract"]["workflow_step"] == "relationship"
        assert isinstance(d["contract"]["allowed_tools"], list) and d["contract"]["allowed_tools"]
        assert isinstance(d["contract"]["forbidden_tools"], list) and d["contract"]["forbidden_tools"]
        assert isinstance(d["contract"]["template_ids"], list) and d["contract"]["template_ids"]
        assert isinstance(d["contract"]["scope"], dict)
        assert "selected_engine" in d["contract"] and "stop_when" in d["contract"]
        assert d["contract"]["output_mode"]

    # 10) 页面展示与后端 QueryContract 一致（前端不猜测，全部字段来自 RouteResult.to_dict）
    def test_acceptance_10_frontend_uses_backend_contract_only(self):
        from app.api.data_intelligence import route_preview, RoutePreviewRequest
        out = route_preview(RoutePreviewRequest(user_input="所有用电户与配变户变关系"))
        assert out["ok"] is True
        # 与路由同一裁判：preview 与生产 route 一致
        prod = route_user_input("所有用电户与配变户变关系")
        assert out["route"]["skill_id"] == prod.skill_id
        assert out["route"]["workflow_step"] == prod.workflow_step
        assert set(out["route"]["contract"]["allowed_tools"]) == set(prod.contract.allowed_tools)

    # 11) 场景迁移：project-lifecycle-cost 多引擎逐源分发
    def test_acceptance_11_multi_engine_skill(self, policy):
        r = route_user_input("哪些WBS超预算")
        assert r.route_type == "scenario"
        assert r.skill_id == "project-lifecycle-cost"
        assert r.workflow_step == "analysis"
        c = r.contract
        assert c.multi_engine is True
        assert c.forbid_markdown_detail_table is False
        # 数据工具前必须先确认数据源模式
        out = _run(policy, c, _tc("execute_entity_api", {"entity_code": "dim_ps_wbs_budget"}))
        assert "batch_entity_source_mode" in out.content
        # batch 确认两源后，两引擎工具并存可用
        batch = json.dumps({"items": [
            {"entity_code": "dim_ps_wbs_budget", "source_mode": "api_integration"},
            {"entity_code": "dim_ps_wbs_cost", "source_mode": "sql_integration"},
        ]})
        _run(policy, c, _tc("batch_entity_source_mode", {"entity_codes": ["a", "b"]}), result=batch)
        assert c.confirmed_engines() == ["doris", "duckdb"]
        assert "execute_entity_api" in c.allowed_tools
        assert "execute_doris_sql" in c.allowed_tools

    # 12) 输出契约旗标：跨源汇总技能保留答案表格（forbid=false 不剥离）
    def test_acceptance_12_output_flag_respects_skill(self):
        from app.services.output_contract import validate_final_output
        answer = "| WBS | 预算 | 成本 |\n|---|---|---|\n| A | 100 | 120 |"
        # forbid=false：结果已推前端也不剥离（答案表格为权威）
        ok = validate_final_output(answer, result_available_for_ui=True, forbid_markdown_detail_table=False)
        assert ok.ok is True
        # forbid=true（distribution-overload）：剥离
        bad = validate_final_output(answer, result_available_for_ui=True, forbid_markdown_detail_table=True)
        assert bad.ok is False
        assert bad.detail_tables_found > 0
