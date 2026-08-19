"""test_query_contract.py - 受控执行契约测试（设计 §5）

覆盖：from_step 契约构造（工具/模板/范围/终止）、read_file 只读能力、
绝对禁用工具永不可减、引擎锁定收窄工具集、to_dict 序列化、generic 契约。
"""
import pytest

from app.services.skill_catalog import SkillCatalog
from app.services.query_contract import ABSOLUTE_FORBIDDEN_TOOLS, QueryContract
from app.services.query_engine_router import resolve_engine

REAL_SKILL = "distribution-overload"


@pytest.fixture
def relationship_contract():
    catalog = SkillCatalog()
    skill = catalog.load_skill(REAL_SKILL)
    step = skill.find_step("relationship")
    return QueryContract.from_step(skill.name, skill.version, step)


class TestFromStep:
    def test_contract_fields(self, relationship_contract):
        assert relationship_contract.skill_id == REAL_SKILL
        assert relationship_contract.workflow_step == "relationship"
        assert relationship_contract.output_mode == "single_result_table"
        assert relationship_contract.template_ids
        assert any("step1_household_transformer.sql" in t for t in relationship_contract.template_ids)

    def test_read_file_always_allowed(self, relationship_contract):
        """模型须读 SKILL.md 与步骤模板，read_file 是永久只读能力。"""
        assert "read_file" in relationship_contract.allowed_tools

    def test_absolute_forbidden_never_allowed(self, relationship_contract):
        for t in ABSOLUTE_FORBIDDEN_TOOLS:
            assert t not in relationship_contract.allowed_tools
        assert set(ABSOLUTE_FORBIDDEN_TOOLS) <= set(relationship_contract.forbidden_tools)

    def test_terminal_flag_by_step(self):
        catalog = SkillCatalog()
        skill = catalog.load_skill(REAL_SKILL)
        rel = QueryContract.from_step(skill.name, skill.version, skill.find_step("relationship"))
        load = QueryContract.from_step(skill.name, skill.version, skill.find_step("load_ratio"))
        ovl = QueryContract.from_step(skill.name, skill.version, skill.find_step("overload"))
        assert rel._runtime["terminal"] is True
        assert load._runtime["terminal"] is True
        assert ovl._runtime["terminal"] is False  # overload 可继续 load_ratio

    def test_scope_default(self, relationship_contract):
        assert relationship_contract.scope["customer_names"] == []
        assert relationship_contract.scope["commitment"] == "none"


class TestEngineLock:
    def test_lock_engine_narrows_tools(self, relationship_contract):
        relationship_contract.lock_engine("doris", "batch 推荐")
        assert relationship_contract.selected_engine == "doris"
        assert relationship_contract.engine_locked is True
        assert "execute_doris_sql" in relationship_contract.allowed_tools
        assert "execute_sql" not in relationship_contract.allowed_tools
        assert "execute_api_sql" not in relationship_contract.allowed_tools
        assert "execute_entity_api" not in relationship_contract.allowed_tools
        assert "read_file" in relationship_contract.allowed_tools  # 非数据工具保留

    def test_lock_engine_duckdb(self, relationship_contract):
        relationship_contract.lock_engine("duckdb", "api 联邦")
        assert "execute_api_sql" in relationship_contract.allowed_tools
        assert "execute_entity_api" in relationship_contract.allowed_tools

    def test_lock_engine_physical(self, relationship_contract):
        relationship_contract.lock_engine("physical", "未纳管 catalog")
        assert "execute_sql" in relationship_contract.allowed_tools
        assert "execute_doris_sql" not in relationship_contract.allowed_tools


class TestGeneric:
    def test_generic_contract(self):
        c = QueryContract.generic(route_reason="未命中场景")
        assert c.route_type == "generic"
        assert c.skill_id == "__generic__"
        assert c.template_ids == []
        assert "task" not in c.allowed_tools
        assert set(ABSOLUTE_FORBIDDEN_TOOLS) <= set(c.forbidden_tools)

    def test_generic_allows_real_kg_tools(self):
        """P0 整改：generic 白名单必须是真实注册的 MCP 工具（见 test_mcp_whitelist_alignment）。"""
        c = QueryContract.generic()
        assert "read_file" in c.allowed_tools
        # 定位类只读工具（此前被白名单挡住的真实工具）
        assert "fetch_l1_l2_tree" in c.allowed_tools
        assert "search_entities" in c.allowed_tools
        assert "search_concepts" in c.allowed_tools
        assert "list_tables" in c.allowed_tools
        assert "get_entity_relations" in c.allowed_tools
        # 幽灵工具必须移除
        assert "kg_api" not in c.allowed_tools


class TestWhitelistAlignedToRegisteredMCP:
    """P0 防回归（单一事实源）：契约白名单必须 ⊆ mcp_server.py 实际注册的工具集。

    这是本次 P0 事故（工具层拆 16 个 MCP 工具、白名单/提示词/测试三处未同步）的根因闸门：
    - 白名单里若残留幽灵工具名（如 kg_api），模型会被合规地引向不存在的工具；
    - Policy 拒绝消息会把允许清单喂给模型，清单里有幽灵名 = 主动误导模型。
    本测试对 generic 白名单 + 所有场景 SKILL.md 步骤 allowed_tools 做交叉校验。
    """

    @staticmethod
    def _registered_tool_names() -> set:
        """从 mcp_server.py 实际注册的 FastMCP 实例取工具名（单一事实源，非并行常量）。"""
        import asyncio

        from app.mcp_server import mcp

        async def _names() -> set:
            tools = await mcp.list_tools()
            return {t.name for t in tools}

        return asyncio.run(_names())

    def test_generic_whitelist_subset_of_registered(self):
        from app.services.query_contract import GENERIC_ALLOWED_TOOLS

        registered = self._registered_tool_names()
        non_mcp_framework_tools = {"read_file"}  # deepagents 框架注入，非 MCP 注册
        whitelist_mcp = set(GENERIC_ALLOWED_TOOLS) - non_mcp_framework_tools
        phantom = whitelist_mcp - registered
        assert not phantom, f"generic 白名单含未注册的幽灵工具: {sorted(phantom)}"

    def test_generic_whitelist_covers_meta_read_tools(self):
        """generic 低权限只读 fallback 至少放行定位/搜索/校验类工具。"""
        from app.services.query_contract import GENERIC_ALLOWED_TOOLS

        must_have = {
            "fetch_l1_l2_tree", "validate_l2", "fetch_subgraph",
            "search_entities", "search_concepts", "get_entity_relations", "list_tables",
            "validate_attributes", "fetch_join_expr", "validate_safe_sql",
        }
        missing = must_have - set(GENERIC_ALLOWED_TOOLS)
        assert not missing, f"generic 白名单缺只读工具: {sorted(missing)}"

    def test_scenario_skills_whitelist_subset_of_registered(self):
        """所有场景 SKILL.md 步骤声明的 allowed_tools ⊆ 实际注册工具 + 框架工具。"""
        from app.services.query_contract import GENERIC_ALLOWED_TOOLS
        from app.services.skill_catalog import SkillCatalog

        registered = self._registered_tool_names()
        framework_tools = {"read_file"}  # read_file 由 deepagents 中间件注入
        all_registered = registered | framework_tools
        catalog = SkillCatalog()
        for skill in catalog.list_skills():
            for step in skill.steps:
                unknown = [t for t in step.allowed_tools if t not in all_registered]
                assert not unknown, f"{skill.name}.{step.id} 声明未注册工具: {sorted(unknown)}"
        # 场景不应用通用只读元数据定位工具（设计 §1.1：场景自带表结构/SQL）
        # —— 仅作注册完备性断言，避免未来工具演进再次静默分裂。
        assert GENERIC_ALLOWED_TOOLS <= all_registered, (
            f"GENERIC_ALLOWED_TOOLS 含未注册工具: {sorted(set(GENERIC_ALLOWED_TOOLS) - all_registered)}"
        )


class TestSerialization:
    def test_to_dict(self, relationship_contract):
        d = relationship_contract.to_dict()
        assert d["skill_id"] == REAL_SKILL
        assert d["workflow_step"] == "relationship"
        assert isinstance(d["allowed_tools"], list)
        assert isinstance(d["template_ids"], list)
        assert isinstance(d["scope"], dict)
        assert "run_id" in d

    def test_violations_tracking(self, relationship_contract):
        assert relationship_contract.record_violation() == 1
        assert relationship_contract.record_violation() == 2


class TestEngineRouter:
    """query_engine_router：三引擎唯一选择（设计 §5.3）。"""

    def test_doris(self):
        d = resolve_engine({"recommended_tool": "execute_doris_sql", "has_catalog": True, "doris_catalog": "pg_tupu", "entity_codes": ["a"]})
        assert d.engine == "doris"
        assert d.exec_tools == ["execute_doris_sql"]

    def test_duckdb_api_sql(self):
        d = resolve_engine({"recommended_tool": "execute_api_sql", "has_api_integration": True})
        assert d.engine == "duckdb"
        assert "execute_api_sql" in d.exec_tools

    def test_duckdb_entity_api(self):
        d = resolve_engine({"recommended_tool": "execute_entity_api"})
        assert d.engine == "duckdb"

    def test_physical(self):
        d = resolve_engine({"recommended_tool": "execute_sql", "has_catalog": False})
        assert d.engine == "physical"
        assert d.exec_tools == ["execute_sql"]

    def test_unknown_tool_returns_none(self):
        assert resolve_engine({"recommended_tool": "mystery_tool"}) is None
        assert resolve_engine({}) is None
        assert resolve_engine(None) is None

    def test_lock_engine_matches_router(self, relationship_contract):
        d = resolve_engine({"recommended_tool": "execute_doris_sql"})
        relationship_contract.lock_engine(d.engine, d.reason)
        assert relationship_contract.selected_engine == "doris"
        assert set(d.exec_tools) <= set(relationship_contract.allowed_tools)

    def test_multi_engines_from_items(self):
        from app.services.query_engine_router import resolve_engines_multi
        batch = {"items": [
            {"entity_code": "budget", "source_mode": "api_integration"},
            {"entity_code": "cost", "source_mode": "sql_integration"},
        ]}
        assert resolve_engines_multi(batch) == ["duckdb", "doris"]
        assert resolve_engines_multi({"items": []}) is None
        assert resolve_engines_multi(None) is None
        assert resolve_engines_multi({"items": [{"entity_code": "x", "source_mode": "physical_table"}]}) == ["physical"]

    def test_multi_engine_confirm_narrows_union(self):
        from app.services.skill_router import route_user_input
        r = route_user_input("哪些WBS超预算")
        c = r.contract
        assert c.multi_engine is True
        assert c.forbid_markdown_detail_table is False
        c.confirm_engines(["duckdb", "doris"], "batch")
        assert c.confirmed_engines() == ["doris", "duckdb"]
        assert "execute_entity_api" in c.allowed_tools
        assert "execute_doris_sql" in c.allowed_tools
        assert "execute_sql" not in c.allowed_tools

    def test_required_entities_injected_from_skill(self):
        """评审 P1-1（二轮）：多引擎技能 required_sources 显式声明必达数据源 -> 契约注入。"""
        from app.services.skill_router import route_user_input
        r = route_user_input("哪些WBS超预算")
        assert r.contract.required_entities == ["dim_ps_wbs_budget", "dim_ps_wbs_cost"]

    def test_entity_based_done_same_engine(self):
        """评审 P1-1（二轮）：两实体同引擎时，第一个实体完成不得误判整个引擎完成。"""
        from app.services.skill_router import route_user_input
        c = route_user_input("哪些WBS超预算").contract
        c.required_entities = ["entity_a", "entity_b"]  # 模拟同引擎多实体
        c.confirm_entities(["entity_a", "entity_b"])
        c.mark_entity_result("entity_a")
        assert c.multi_engine_done() is False  # b 未完成 -> 不终止
        c.mark_entity_result("entity_b")
        assert c.multi_engine_done() is True
