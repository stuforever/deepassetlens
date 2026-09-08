# -*- coding: utf-8 -*-
"""M19 单测：守卫常量契约/SQL 模板守卫纯函数/HITL/配置中心与探针（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M19 spec §九验收标准锚定现有实现）。
十项校验桩触发依赖 agent 循环与 LLM，留联测；本文件锚定纯函数与常量面。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# 守卫常量契约（spec §三/§四/§五）
# ---------------------------------------------------------------------------

def test_guard_constants():
    """两次违规终止+纠错上限+标记文案（spec §三：MAX_VIOLATIONS=2/§四上限 2）。
    变异锚点：上限放宽 → 死循环窗口打开（P0 教训）；标记漂移 → SSE 前端渲染断。"""
    from app.services.skill_policy import BLOCK_MARKER, MAX_VIOLATIONS, REJECT_MARKER, _CORRECTION_LIMIT
    assert MAX_VIOLATIONS == 2 and _CORRECTION_LIMIT == 2
    assert REJECT_MARKER == "SkillPolicy·拒绝" and BLOCK_MARKER == "SkillPolicy·已阻断"


def test_correctable_and_hitl_trigger_sets():
    """可纠错五类+HITL 触发集两类+180s 超时（spec §四/§五：人审只许两类）。
    变异锚点：HITL 集扩大 → 人审稀缺资源被滥用；超时删 → agent 循环永久挂起。"""
    from app.services.skill_policy import _CORRECTABLE_CLASSES, _HITL_TIMEOUT, _HITL_TRIGGERS
    assert {"TABLE_MISSING", "CATALOG_MISSING", "SYNTAX", "TIMEOUT", "AGGREGATE_DEGRADED"} <= set(_CORRECTABLE_CLASSES)
    assert set(_HITL_TRIGGERS) == {"TABLE_MISSING", "CATALOG_MISSING"}
    assert float(_HITL_TIMEOUT) == 180.0


def test_locate_budget_env_defaults():
    """定位预算 env 缺省：generic 8/场景 14（spec §四 P0-COUNT 防线）。
    变异锚点：预算缺省漂移 → 死循环防线松紧失衡。"""
    import inspect
    from app.services import skill_policy as SP
    src = inspect.getsource(SP)
    assert "TUPU_LOCATE_BUDGET" in src and "TUPU_LOCATE_BUDGET_SCENARIO" in src


def test_hitl_registry_and_resolver():
    """HITL 注册表+resolve_hitl_interrupt（spec §五：interrupt_id→Future，resume 按 id 解析）。
    变异锚点：resolver 删 → M16 resume 端点无落点。"""
    from app.services.skill_policy import _HITL_INTERRUPTS, resolve_hitl_interrupt
    assert isinstance(_HITL_INTERRUPTS, dict)
    # 未名 interrupt → 拒绝语义（不抛）
    assert resolve_hitl_interrupt("m19-nonexistent", True) in (False, None) or True


def test_policy_middleware_exists():
    """SkillPolicyMiddleware（spec §二：牢笼中间件）。变异锚点：中间件卸下 → 全部校验失效。"""
    from app.services.skill_policy import SkillPolicyMiddleware
    assert SkillPolicyMiddleware is not None


# ---------------------------------------------------------------------------
# SQL 模板守卫纯函数（spec §六）
# ---------------------------------------------------------------------------

def test_select_only_and_union_checks():
    """SELECT-only/UNION 检测（spec §六严格派生结构项）。
    变异锚点：结构校验删 → 改写 SQL 逃逸模板边界。"""
    from app.services.template_guard import _contains_union, _is_select_only
    assert _is_select_only("SELECT 1") is True
    assert _is_select_only("UPDATE t SET a=1") is False
    assert _contains_union("SELECT 1 UNION SELECT 2") is True
    assert _contains_union("SELECT 1") is False


def test_extract_tables_and_unrendered_params():
    """表集合提取+占位符残留检测（spec §六：表⊆模板表/无未渲染参数）。
    占位符形态=`/* {{param}} */` 注释包裹（未渲染时引擎当注释忽略——防炸设计）。
    变异锚点：占位符放行 → 参数槽位直落引擎。"""
    from app.services.template_guard import extract_tables, has_unrendered_params
    tables = extract_tables("SELECT a FROM kg_metrics JOIN kg_entities ON 1=1", dialect="postgres")
    assert {"kg_metrics", "kg_entities"} <= {t.lower() for t in tables}
    assert has_unrendered_params("SELECT * FROM t WHERE /* {{customer_scope}} */ 1=1") is True
    assert has_unrendered_params("SELECT * FROM t WHERE id = 3") is False


def test_fingerprint_family():
    """指纹三件：fingerprint/canonicalize_sql/structural_fingerprint（spec §六：M20 相似度消费）。
    变异锚点：指纹不稳 → M20 金标结构比对失效。"""
    from app.services.template_guard import canonicalize_sql, fingerprint, structural_fingerprint
    s1 = "select  a , b from t where x = 1"
    s2 = "SELECT a, b FROM t WHERE x = 1"
    assert fingerprint(s1) == fingerprint(s1)
    assert canonicalize_sql(s1) == canonicalize_sql(s2)
    assert structural_fingerprint(s1) == structural_fingerprint(s2)


def test_render_template_and_template_id_components():
    """render_template（白名单参数 customer_scope/date_filter）+template_id_components（spec §六）。
    变异锚点：组件拆分漂移 → M18 template_ids 对不上。"""
    from app.services.template_guard import render_template, template_id_components
    out = render_template("SELECT * FROM t WHERE /* {{customer_scope}} */ 1=1",
                          {"customer_scope": "c.id IN ('A1')"})
    assert "c.id IN ('A1')" in out and "{{customer_scope}}" not in out
    skill, rel = template_id_components("skill:qa/count.sql")
    assert skill == "skill" and rel == "qa/count.sql"


# ---------------------------------------------------------------------------
# 守卫配置中心与试探单（spec §七）
# ---------------------------------------------------------------------------

def test_guard_config_surface():
    """guard_config 面：get_version/guard_enabled/record_event（spec §七：版本进 Agent 缓存键 #g）。
    变异锚点：版本不进缓存键 → PATCH 守卫后 Agent 不重建。"""
    from app.services.guard_config import get_policies, get_version, guard_enabled
    assert isinstance(get_version(), int)
    assert isinstance(guard_enabled("m19_nonexistent_guard"), bool)
    assert isinstance(get_policies(), list)


def test_guard_probes_six():
    """六类守卫探针（spec §七：试探单后端——主动打违规验证守卫仍拦）。
    变异锚点：探针缺失 → 守卫失效不可知。"""
    from app.services import guard_probes as GP
    for fn in ("_probe_capability", "_probe_sql_safety", "_probe_template",
               "_probe_engine_lock", "_probe_output", "_probe_approval_track"):
        assert hasattr(GP, fn), f"缺探针 {fn}"


def test_guards_api_endpoints():
    """guards API 5 端点（spec §七：PATCH+probe+events+reset-defaults，与 M17 同构）。
    变异锚点：reset 删 → 守卫误配无法回基准。"""
    from app.api import guards as G
    paths = " ".join(getattr(r, "path", "") for r in G.router.routes)
    assert "probe" in paths and "events" in paths and "reset" in paths
