"""修复方向再评估（2026-08-20）：技能优先修复的回归防线测试（Fix 3）。

覆盖：
  1. validate_sql「当前拒绝 Union 根」锁定单测 —— 把"未实现"显性化为"已定义行为"，
     给未来 Fix 4（放行 UNION）留显式翻转锚点（须改本测试）；
  2. validate_sql 拒绝 -> SECURITY_VALIDATION 分类（错误分类学补全，Fix 2）；
  3. 用电户/发电户单段变体模板注册（relationship + overload 步骤，Fix 1 载体）；
  4. 变体模板「天然双通过」：validate_sql + template_guard scenario_strict 双过；
     模型第一次尝试（只跑用电户段 + 可选动态客户过滤）严格派生即通过；
  5. skill_policy：SECURITY_VALIDATION -> fail-fast（set_stop_reached 出失败卡，
     不纠错重试、不累计 corrections；幂等）。
"""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from app.services.skill_catalog import SkillCatalog
from app.services.secure_query_executor import validate_sql
from app.services.engine_errors import apply_error_class, classify_by_message
from app.services.query_contract import QueryContract
from app.services import skill_policy as sp
from app.services.skill_policy import SkillPolicyMiddleware
from app.services.template_guard import TEMPLATE_MODE_STRICT, load_template, resolve_entity_aliases, validate_against_template

REAL_SKILL = "distribution-overload"
VARIANTS = ("step1_household_transformer_elec.sql", "step1_household_transformer_gen.sql")


def _resolve_template(skill, rel_path: str) -> str:
    """读取 + 解析（⟦中文名⟧ -> 物理表 + 精确实体名解析）模板 SQL。"""
    from app.services.tupu_deepagent import _resolve_entity_refs
    raw = load_template(Path(skill.path.parent) / "templates" / rel_path)
    resolved = resolve_entity_aliases(raw, skill.entity_aliases)
    return _resolve_entity_refs(resolved)

# --------------------------------------------------------------------------- #
# 1. validate_sql「当前拒绝 Union 根」锁定单测（Fix 3 关键技巧）
# --------------------------------------------------------------------------- #
class TestUnionRootLocked:
    def test_union_all_root_rejected(self):
        """UNION ALL 根（如户变关系全量模板）当前被 validate_sql 拒绝（未实现，不是误设计）。"""
        chk = validate_sql("SELECT '用电户' AS t FROM dim_cst_elec_cons_cust "
                           "UNION ALL SELECT '发电户' FROM dim_cst_gpc")
        assert chk.ok is False
        assert "不支持的语句类型" in chk.reason

    def test_union_root_reason_is_security_validation(self):
        """拒绝分类为 SECURITY_VALIDATION（层间裁决不一致，非引擎错误）。"""
        chk = validate_sql("SELECT 1 UNION SELECT 2")
        assert chk.ok is False
        assert classify_by_message(f"SQL安全校验未通过: {chk.reason}") == "SECURITY_VALIDATION"
        # apply_error_class 兜底也归为 SECURITY_VALIDATION
        res = apply_error_class({"error": f"SQL安全校验未通过: {chk.reason}"})
        assert res["error_class"] == "SECURITY_VALIDATION"

    def test_with_select_root_still_allowed(self):
        """WITH...SELECT 根是 Select -> 仍通过（validate_sql 初衷覆盖）。"""
        chk = validate_sql("WITH c AS (SELECT 1 AS n) SELECT n FROM c")
        assert chk.ok is True


# --------------------------------------------------------------------------- #
# 2. 变体模板注册（Fix 1 载体）
# --------------------------------------------------------------------------- #
class TestVariantTemplatesRegistered:
    def _skill(self):
        catalog = SkillCatalog()
        skill = catalog.load_skill(REAL_SKILL)
        assert skill is not None
        return skill

    def _step(self, step_id: str):
        skill = self._skill()
        step = next((s for s in skill.steps if s.id == step_id), None)
        assert step is not None, f"步骤 {step_id} 不存在"
        return step

    def test_relationship_step_has_variants(self):
        step = self._step("relationship")
        tpls = step.templates or []
        for v in VARIANTS:
            assert any(v in t for t in tpls), f"relationship 步骤缺少变体 {v}"

    def test_overload_step_has_variants(self):
        step = self._step("overload")
        tpls = step.templates or []
        for v in VARIANTS:
            assert any(v in t for t in tpls), f"overload 步骤缺少变体 {v}"

    def test_golden_single_segment_question_routes_to_variant(self):
        """金标单段用例（确定性形态，Fix 3）：「所有用电户与配变户变关系」路由到
        distribution-overload relationship 步骤，且用电户变体在可选模板中 ——
        模型第一次尝试（只跑用电户段）即可命中变体，不再依赖对 UNION 模板删段。"""
        from app.services.skill_router import route_user_input
        r = route_user_input("所有用电户与配变户变关系")
        assert r.route_type == "scenario"
        assert r.contract.skill_id == "distribution-overload"
        assert r.contract.workflow_step == "relationship"
        tids = r.contract.template_ids or []
        assert any("step1_household_transformer_elec.sql" in t for t in tids), \
            f"relationship 步骤应含用电户变体: {tids}"


# --------------------------------------------------------------------------- #
# 3. 变体「天然双通过」：validate_sql + scenario_strict（Fix 1 核心验证）
# --------------------------------------------------------------------------- #
class TestVariantDualPass:
    def _load(self, rel: str):
        catalog = SkillCatalog()
        skill = catalog.load_skill(REAL_SKILL)
        assert skill is not None
        return _resolve_template(skill, rel)

    def test_elec_variant_passes_validate_sql(self):
        sql = self._load("step1_household_transformer_elec.sql")
        chk = validate_sql(sql)
        assert chk.ok is True, f"用电户变体应过 validate_sql: {chk.reason}"

    def test_gen_variant_passes_validate_sql(self):
        sql = self._load("step1_household_transformer_gen.sql")
        chk = validate_sql(sql)
        assert chk.ok is True, f"发电户变体应过 validate_sql: {chk.reason}"

    def test_elec_variant_self_derived_passes_strict(self):
        """模型第一次尝试（只跑用电户段，即变体本身）在 scenario_strict 下直接通过。"""
        sql = self._load("step1_household_transformer_elec.sql")
        chk = validate_against_template(sql, sql, "elec-variant", mode=TEMPLATE_MODE_STRICT)
        assert chk.ok is True
        assert chk.structure_match is True

    def test_gen_variant_self_derived_passes_strict(self):
        sql = self._load("step1_household_transformer_gen.sql")
        chk = validate_against_template(sql, sql, "gen-variant", mode=TEMPLATE_MODE_STRICT)
        assert chk.ok is True
        assert chk.structure_match is True

    def test_elec_variant_dynamic_customer_scope_passes_strict(self):
        """变体 + 声明过的【动态】客户限定 -> strict 仍通过（本问题原封不动的场景）。"""
        sql = self._load("step1_household_transformer_elec.sql")
        cand = sql.replace(
            "-- 【动态】用户限定客户: AND c.cust_name IN ('客户001','客户003')",
            "AND c.cust_name IN ('客户001','客户003')",
        )
        chk = validate_against_template(cand, sql, "elec-variant", mode=TEMPLATE_MODE_STRICT)
        assert chk.ok is True, f"动态客户限定应变体派生通过: {chk.reason}"
        assert chk.structure_match is True

    def test_union_template_still_rejected_by_validate_sql(self):
        """对照组：UNION 全量模板仍被 validate_sql 拒（Fix 4 推迟期的既定行为）。"""
        sql = self._load("step1_household_transformer.sql")
        chk = validate_sql(sql)
        assert chk.ok is False, "UNION 全量模板当前仍应被 validate_sql 拒绝"


# --------------------------------------------------------------------------- #
# 4. skill_policy：SECURITY_VALIDATION -> fail-fast（Fix 2）
# --------------------------------------------------------------------------- #
class TestSecurityFailFast:
    def _request(self, tool_name="execute_sql"):
        req = SimpleNamespace(
            tool_call={"name": tool_name, "id": f"id-{tool_name}"},
            runtime=SimpleNamespace(context={}, config=None),
        )
        return req

    def test_security_validation_stops_immediately(self):
        captured = []

        async def _dispatcher(event_name, payload, config):
            captured.append((event_name, dict(payload)))

        async def _main():
            contract = QueryContract.generic()
            mw = SkillPolicyMiddleware(dispatcher=_dispatcher)
            mw._check_controlled_degradation(
                contract, "execute_sql",
                json.dumps({"error_class": "SECURITY_VALIDATION", "error": "不支持的语句类型: Union"}),
                self._request())
            assert contract.stop_reached is True, "SECURITY_VALIDATION 应 fail-fast 出失败卡"
            assert contract._runtime.get("terminal") is True
            assert "execute_sql" not in contract.allowed_tools, "数据工具应被移除"
            # 不累计纠错（模型无错，不进入纠错闭环）
            assert contract._runtime.get("corrections", 0) == 0
            # 再次同类结果 -> 幂等（不重复终止/不崩）
            mw._check_controlled_degradation(
                contract, "execute_doris_sql",
                json.dumps({"error_class": "SECURITY_VALIDATION", "error": "禁止多语句"}),
                self._request("execute_doris_sql"))
            assert contract.stop_reached is True

        asyncio.run(_main())
        assert any(ev == "correction.attempt" for ev, _ in captured), "应派发终止事件"
        stopped = [p for ev, p in captured if ev == "correction.attempt" and p.get("stopped")]
        assert stopped and stopped[0].get("error_class") == "SECURITY_VALIDATION"

    def test_security_validation_not_correctable(self):
        """SECURITY_VALIDATION 不在可纠错集 -> 不走降级/纠错计数。"""
        assert "SECURITY_VALIDATION" not in sp._CORRECTABLE_CLASSES
        assert "SECURITY_VALIDATION" in sp._CORRECTION_GUIDES, "引导存在（告诉模型禁重试、直接结论）"
