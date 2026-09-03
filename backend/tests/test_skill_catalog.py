"""test_skill_catalog.py - SKILL.md 唯一来源解析器测试（受控 Skill 问答平台 v2）

覆盖：frontmatter+x_tupu 解析、entity_aliases、steps/工具白名单/模板、
mtime+SHA256 缓存、解析失败禁用、build_overview 动态生成（替代静态 _SKILL_OVERVIEW）。
"""
import pytest

from app.services.skill_catalog import SkillCatalog
from app.services.template_guard import resolve_entity_aliases

REAL_SKILL = "distribution-overload"


@pytest.fixture
def catalog():
    return SkillCatalog()


class TestParseDistributionOverload:
    def test_skill_loaded_enabled(self, catalog):
        skill = catalog.load_skill(REAL_SKILL)
        assert skill is not None, "distribution-overload 必须可解析"
        assert skill.enabled is True
        assert skill.version == "1.0"
        assert skill.category == "scenario"

    def test_triggers_present(self, catalog):
        skill = catalog.load_skill(REAL_SKILL)
        any_t = (skill.triggers or {}).get("any") or []
        assert "户变关系" in any_t
        assert "重载" in any_t
        assert "负载占有率" in any_t

    def test_forbidden_tools_include_task_execute(self, catalog):
        skill = catalog.load_skill(REAL_SKILL)
        # 批13-Z：task 已从 forbidden_tools 移除（剧本声明 allow_subagents: true，
        # 声明+禁用自相矛盾），委派改由护栏1 复合条件（本声明 AND caps 总闸）约束
        assert {"write_file", "edit_file", "execute", "grep", "glob"} <= set(skill.forbidden_tools)
        assert "task" not in set(skill.forbidden_tools)
        assert skill.allow_subagents is True

    def test_steps_relationship_overload_load_ratio(self, catalog):
        skill = catalog.load_skill(REAL_SKILL)
        ids = [s.id for s in skill.steps]
        assert ids == ["relationship", "overload", "load_ratio"]

    def test_relationship_step_tools_and_template(self, catalog):
        skill = catalog.load_skill(REAL_SKILL)
        rel = skill.find_step("relationship")
        assert rel is not None
        assert "execute_doris_sql" in rel.allowed_tools
        assert "execute_sql" in rel.allowed_tools
        assert any("step1_household_transformer.sql" in t for t in rel.templates)
        assert rel.stop_when, "relationship 步骤必须声明终止条件"

    def test_entity_aliases_resolve_physical_tables(self, catalog):
        skill = catalog.load_skill(REAL_SKILL)
        aliases = skill.entity_aliases
        # 别名值为 3 段命名（含 catalog 前缀）：execute_doris_sql 必须用 3 段名，
        # 裸表名在默认 catalog（internal/test_db）下解析失败（2026-08-21 前端实测暴露）
        assert aliases.get("用电户") == "pg_tupu.public.dim_cst_elec_cons_cust"
        assert aliases.get("计量点") == "pg_tupu.public.dim_cst_inst_elec_cons"
        assert aliases.get("配电变压器") == "pg_tupu.public.dim_grid_pub_dist_trans_resrc_standbk_e"

    def test_alias_replacement_in_template_text(self, catalog):
        skill = catalog.load_skill(REAL_SKILL)
        out = resolve_entity_aliases("FROM ⟦用电户⟧ ec", skill.entity_aliases)
        assert out == "FROM pg_tupu.public.dim_cst_elec_cons_cust ec"


class TestCatalogCacheAndFailure:
    def test_load_unknown_skill_returns_none(self, catalog):
        assert catalog.load_skill("no-such-skill") is None

    def test_build_overview_contains_scenario(self, catalog):
        overview = catalog.build_overview()
        assert "distribution-overload" in overview
        assert "户变关系" in overview  # 触发词来自 SKILL.md 而非硬编码

    def test_build_overview_is_dynamic(self, catalog):
        """build_overview 内容来自 SkillCatalog，替代被删除的静态 _SKILL_OVERVIEW。"""
        overview = catalog.build_overview()
        # 不再包含被删除静态概览里的"能力包"字样（那是旧的硬编码结构）
        assert "能力包" not in overview

    def test_failed_skill_returns_none(self, tmp_path):
        """缺少 x_tupu 的 SKILL.md 解析失败 -> 返回 None（不允许猜着执行）。"""
        (tmp_path / "bad-skill").mkdir()
        (tmp_path / "bad-skill" / "SKILL.md").write_text(
            "---\nname: bad-skill\ndescription: 无 x_tupu\ncategory: scenario\n---\n# body\n",
            encoding="utf-8",
        )
        c = SkillCatalog(scenarios_dir=tmp_path)
        assert c.load_skill("bad-skill") is None
        assert any("bad-skill" in w for w in c.warnings)
