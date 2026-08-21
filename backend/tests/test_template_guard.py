"""test_template_guard.py - SQL 模板校验测试（受控 Skill 问答平台 v2，设计 §6.2）

覆盖：SELECT-only、表集合 ⊆ 模板、UNION（模板内合法合并 vs 越界拦截）、
DDL/DML 拦截、模板渲染参数白名单、实体别名解析。
"""
from pathlib import Path

import pytest

from app.services.skill_catalog import SkillCatalog
from app.services.template_guard import (
    TEMPLATE_MODE_STRICT,
    canonicalize_sql,
    extract_tables,
    fingerprint,
    has_unrendered_params,
    render_template,
    resolve_entity_aliases,
    structural_fingerprint,
    validate_against_template,
)

REAL_SKILL = "distribution-overload"


@pytest.fixture
def step1_template_sql():
    """解析后的 step1 模板 SQL（⟦中文名⟧ -> 物理表名，供真实环境比对）。"""
    catalog = SkillCatalog()
    skill = catalog.load_skill(REAL_SKILL)
    assert skill is not None
    from app.services.template_guard import load_template
    from app.services.tupu_deepagent import _resolve_entity_refs
    raw = load_template(Path(skill.path.parent) / "templates/step1_household_transformer.sql")
    resolved = resolve_entity_aliases(raw, skill.entity_aliases)
    return _resolve_entity_refs(resolved)


class TestSelectOnly:
    def test_ddl_rejected(self, step1_template_sql):
        chk = validate_against_template("DROP TABLE dim_cst_elec_cons_cust", step1_template_sql, "t1")
        assert chk.ok is False
        assert "SELECT" in chk.reason

    def test_dml_rejected(self, step1_template_sql):
        chk = validate_against_template("DELETE FROM dim_cst_elec_cons_cust WHERE 1=1", step1_template_sql, "t1")
        assert chk.ok is False

    def test_empty_rejected(self, step1_template_sql):
        chk = validate_against_template("   ", step1_template_sql, "t1")
        assert chk.ok is False


class TestTableScope:
    def test_tables_within_template_pass(self, step1_template_sql):
        sql = """
        SELECT ec.elec_cons_cust_id AS cid, c.cust_name, i.inst_id AS iid
        FROM dim_cst_elec_cons_cust ec
        JOIN cms20_cst_cust c ON ec.cust_id = c.cust_id
        JOIN dim_cst_inst_elec_cons i ON ec.elec_cons_cust_id = i.elec_cons_cust_id
        LEFT JOIN dim_cst_dist_sta ds ON i.dist_sta_id = ds.dist_sta_id
        WHERE i.inst_usage_cls = '01'
        """
        chk = validate_against_template(sql, step1_template_sql, "t1")
        assert chk.ok is True
        assert {"dim_cst_elec_cons_cust", "cms20_cst_cust", "dim_cst_inst_elec_cons"} <= chk.tables

    def test_out_of_scope_table_rejected(self, step1_template_sql):
        sql = "SELECT * FROM dim_cst_elec_cons_cust JOIN secret_table s ON 1=1"
        chk = validate_against_template(sql, step1_template_sql, "t1")
        assert chk.ok is False
        assert "secret_table" in chk.reason

    def test_union_within_template_tables_pass(self, step1_template_sql):
        """模板自身用 UNION ALL 合并用电户/发电户，表集合在模板内 -> 合法。"""
        sql = "SELECT * FROM dim_cst_elec_cons_cust UNION ALL SELECT * FROM dim_cst_gpc"
        chk = validate_against_template(sql, step1_template_sql, "t1")
        assert chk.ok is True

    def test_union_extra_table_rejected(self, step1_template_sql):
        """UNION 引入模板外表 -> 表集合检查拦截。"""
        sql = "SELECT * FROM dim_cst_elec_cons_cust UNION SELECT * FROM outside_table"
        chk = validate_against_template(sql, step1_template_sql, "t1")
        assert chk.ok is False
        assert "outside_table" in chk.reason


class TestTemplateHelpers:
    def test_render_whitelist_params(self):
        tpl = "SELECT * FROM t WHERE cust_name IN (/* {{customer_scope}} */)"
        out = render_template(tpl, {"customer_scope": "'客户001','客户002'"})
        assert "'客户001','客户002'" in out

    def test_render_unknown_param_ignored(self):
        tpl = "SELECT * FROM t WHERE /* {{evil_param}} */ 1=1"
        out = render_template(tpl, {"evil_param": "1 OR 1=1"})
        assert "{{evil_param}}" in out  # 未知参数不替换

    def test_fingerprint_stable(self):
        assert fingerprint("SELECT 1") == fingerprint("SELECT 1")
        assert fingerprint("SELECT 1") != fingerprint("SELECT 2")

    def test_extract_tables(self):
        tables = extract_tables("SELECT * FROM a JOIN b ON 1=1")
        assert tables == {"a", "b"}

    def test_entity_alias_resolution(self):
        aliases = {"用电户": "dim_cst_elec_cons_cust"}
        out = resolve_entity_aliases("FROM ⟦用电户⟧ ec", aliases)
        assert "dim_cst_elec_cons_cust" in out
        assert "⟦" not in out


class TestStructuralFingerprint:
    """批4 模板指纹精确比对（设计 §1.2/§6.1：模板哈希 + 参数注入点校验）。"""

    def test_canonicalize_normalizes_literals(self):
        assert canonicalize_sql("SELECT * FROM t WHERE a = 1 AND b = 'x'") == \
               canonicalize_sql("SELECT * FROM t WHERE a = 2 AND b = 'y'")
        assert "?" in canonicalize_sql("SELECT 1")

    def test_canonicalize_keeps_structure(self):
        # 同表但结构不同 -> 骨架不同（指纹不同）
        assert canonicalize_sql("SELECT a FROM t WHERE x=1") != \
               canonicalize_sql("SELECT a FROM t GROUP BY a")

    def test_structure_match_reported(self, step1_template_sql):
        """候选即模板本身（字面量级等价）-> 结构指纹一致。"""
        chk = validate_against_template(step1_template_sql, step1_template_sql, "t1")
        assert chk.ok is True
        assert chk.structure_match is True
        assert chk.template_fingerprint == chk.candidate_fingerprint

    def test_literal_variation_still_matches(self, step1_template_sql):
        """字面量差异（参数注入）不影响结构指纹。"""
        import re
        variant = re.sub(r"'01'", "'99'", step1_template_sql)
        chk = validate_against_template(variant, step1_template_sql, "t1")
        assert chk.ok is True
        assert chk.structure_match is True

    def test_structure_drift_reported_but_allowed(self, step1_template_sql):
        """同表集合但结构不同（加 GROUP BY）-> 评审 P0-2 分级：strict 拒绝 / extensible 允许并报告漂移。"""
        sql = """
        SELECT i.dist_sta_id, COUNT(*) AS n
        FROM dim_cst_inst_elec_cons i
        GROUP BY i.dist_sta_id
        """
        # extensible（默认）：允许同表结构变化，但报告漂移审计
        chk = validate_against_template(sql, step1_template_sql, "t1")
        assert chk.ok is True  # 表集合在模板内
        assert chk.structure_match is False  # 但结构漂移（审计信号）
        assert "结构" in chk.reason
        # strict（评审强牢笼）：模板派生 SQL 强制结构一致 -> 直接拒绝
        chk_strict = validate_against_template(sql, step1_template_sql, "t1",
                                               mode=TEMPLATE_MODE_STRICT)
        assert chk_strict.ok is False
        assert "scenario_strict" in chk_strict.reason
        assert chk_strict.structure_match is False

    def test_unrendered_params_detected(self):
        assert has_unrendered_params("SELECT * FROM t WHERE /* {{customer_scope}} */") is True
        assert has_unrendered_params("SELECT * FROM t") is False

    def test_structural_fingerprint_stable(self):
        assert structural_fingerprint("SELECT a FROM t WHERE x=1") == \
               structural_fingerprint("SELECT a FROM t WHERE x=99")

    def test_unrendered_params_rejected_in_all_modes(self, step1_template_sql):
        """评审 P0-2：未渲染参数占位（/* {{param}} */）任何模式一律拒绝。"""
        import re
        # 在模板末尾语句内注入一个未渲染的日期过滤占位（保持 SELECT-only 可解析）
        tpl = re.sub(r";\s*$", "", step1_template_sql)
        sql = tpl + " /* {{date_filter}} */;"
        for mode in (TEMPLATE_MODE_STRICT, "scenario_extensible", "generic"):
            chk = validate_against_template(sql, step1_template_sql, "t1", mode=mode)
            assert chk.ok is False, f"mode={mode} 未拒绝未渲染参数"
            assert "未渲染" in chk.reason

    def test_declared_dynamic_extension_passes_strict(self, step1_template_sql):
        """评审 P0-2：strict 允许唯一声明过的 AST 变化 = 模板【动态】片段（客户范围）。"""
        sql = step1_template_sql.replace(
            "-- 【动态】用户限定客户: AND c.cust_name IN ('客户001','客户003')",
            "AND c.cust_name IN ('客户001','客户003')",
        )
        chk = validate_against_template(sql, step1_template_sql, "t1", mode=TEMPLATE_MODE_STRICT)
        assert chk.ok is True
        assert chk.structure_match is True

    def test_undeclared_extension_rejected_strict(self, step1_template_sql):
        """评审 P0-2：strict 拒绝未声明的结构变化（新增非【动态】WHERE 连接项）。"""
        sql = step1_template_sql.replace(
            "WHERE i.inst_usage_cls = '01' AND i.elec_cons_cust_id IS NOT NULL",
            "WHERE i.inst_usage_cls = '01' AND i.elec_cons_cust_id IS NOT NULL AND i.inst_stat = '5'",
        )
        chk = validate_against_template(sql, step1_template_sql, "t1", mode=TEMPLATE_MODE_STRICT)
        assert chk.ok is False
        assert "scenario_strict" in chk.reason

    def test_generic_mode_allows_structure_drift(self, step1_template_sql):
        """评审 P0-2：generic 允许结构变化（表集合仍是闸门）。"""
        sql = "SELECT i.dist_sta_id, COUNT(*) AS n FROM dim_cst_inst_elec_cons i GROUP BY i.dist_sta_id"
        chk = validate_against_template(sql, step1_template_sql, "t1", mode="generic")
        assert chk.ok is True
        assert chk.structure_match is False

    def test_canonicalize_strips_comments(self):
        """评审 P0-2（二轮）：注释必须真正剥离，不污染结构指纹（sqlglot 30.x 不支持 comments=False）。"""
        assert canonicalize_sql("SELECT a FROM t /* 块注释 */ WHERE b=1") == \
               canonicalize_sql("SELECT a FROM t WHERE b=1")
        # 行注释：独占一行，不影响后续 WHERE
        assert canonicalize_sql("SELECT a FROM t\n-- 中文说明\nWHERE b=1") == \
               canonicalize_sql("SELECT a FROM t WHERE b=1")
        # 字符串字面量里的 '--' 不被误当注释（否则会被截断成 `select '?'` 无 as x）
        assert canonicalize_sql("SELECT 'a--b' AS x") == "select '?' as x"

    def test_strict_rejects_dynamic_plus_other_branch_change(self, step1_template_sql):
        """评审 P0-2（二轮）：第一个 WHERE 加合法动态 + 同时改其他结构（投影/GROUP BY/JOIN）必须拒绝。"""
        v = step1_template_sql.replace(
            "-- 【动态】用户限定客户: AND c.cust_name IN ('客户001','客户003')",
            "AND c.cust_name IN ('客户001','客户003')")
        # 合法动态本身通过
        assert validate_against_template(v, step1_template_sql, "t1", mode=TEMPLATE_MODE_STRICT).ok is True
        # 改第一分支投影列
        chk = validate_against_template(v.replace("c.cust_name,", "UPPER(c.cust_name),", 1),
                                        step1_template_sql, "t1", mode=TEMPLATE_MODE_STRICT)
        assert chk.ok is False and "scenario_strict" in chk.reason
        # 改 JOIN 条件
        chk2 = validate_against_template(
            v.replace("LEFT JOIN pg_tupu.public.dim_cst_dist_sta ds ON i.dist_sta_id = ds.dist_sta_id",
                      "LEFT JOIN pg_tupu.public.dim_cst_dist_sta ds ON i.dist_sta_id = ds.dist_sta_id AND ds.dist_sta_level = '1'"),
            step1_template_sql, "t1", mode=TEMPLATE_MODE_STRICT)
        assert chk2.ok is False and "scenario_strict" in chk2.reason
        # 第二分支新增未声明 WHERE 条件（find_all 覆盖，不只第一个 WHERE）
        chk3 = validate_against_template(
            v.replace("AND i.gpc_id IS NOT NULL", "AND i.gpc_id IS NOT NULL AND i.inst_stat = '5'"),
            step1_template_sql, "t1", mode=TEMPLATE_MODE_STRICT)
        assert chk3.ok is False and "scenario_strict" in chk3.reason

    def test_strict_rejects_deleting_template_condition(self, step1_template_sql):
        """评审 P0-2（二轮）：候选不得删除模板既有条件（t_conjs ⊆ c_conjs 硬校验）。"""
        sql = step1_template_sql.replace("AND i.elec_cons_cust_id IS NOT NULL", "")
        chk = validate_against_template(sql, step1_template_sql, "t1", mode=TEMPLATE_MODE_STRICT)
        assert chk.ok is False
