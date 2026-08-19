"""test_skill_governance.py - 批4 生产治理测试（审计 + 运行指标 + 编译期校验）。

覆盖：
1. SkillGovernance 注册表：路由/策略/输出三类指标 + 审计轨迹（快照/重置/线程安全）；
2. skill_catalog 编译期校验（设计 §1.2）：output_mode 枚举 / allowed_next 引用 /
   triggers 结构 / allowed_tools∈全局名册 -> 非法即禁用；
3. 治理端点逻辑（catalog 快照 / metrics 快照 / simulate-route 别名）。
"""
import pytest

from app.services.skill_catalog import (
    OUTPUT_MODE_ENUM, GLOBAL_TOOL_REGISTRY, SkillCatalog,
)
from app.services.skill_governance import (
    EVENT_OUTPUT_SCRUBBED, EVENT_POLICY_BLOCKED, EVENT_POLICY_REJECTED,
    EVENT_ROUTE_SCENARIO, SkillGovernance,
)
from app.services.skill_router import SkillRouter


@pytest.fixture
def governance():
    g = SkillGovernance()
    g.reset()
    return g


# ----------------------------------------------------------------------
# 1. SkillGovernance 注册表
# ----------------------------------------------------------------------
class TestGovernanceRegistry:
    def test_record_route_snapshot(self, governance):
        r = SkillRouter().route("所有用电户与配变户变关系")
        governance.record_route(r)
        snap = governance.snapshot()
        assert snap["counters"]["route_total"] == 1
        assert snap["by_route_type"].get("scenario") == 1
        assert snap["by_skill"].get("distribution-overload") == 1
        assert snap["by_step"].get("relationship") == 1
        assert snap["audit"][0]["event"] == EVENT_ROUTE_SCENARIO
        assert snap["audit"][0]["payload"]["workflow_step"] == "relationship"

    def test_record_policy_reject_and_block(self, governance):
        governance.record_policy(EVENT_POLICY_REJECTED, "distribution-overload", "relationship",
                                 "调用禁用工具 task", attempt=1)
        governance.record_policy(EVENT_POLICY_BLOCKED, "distribution-overload", "relationship",
                                 "调用禁用工具 task", attempt=2)
        snap = governance.snapshot()
        assert snap["counters"]["rejected_total"] == 1
        assert snap["counters"]["blocked_total"] == 1
        assert snap["policy_by_event"][EVENT_POLICY_REJECTED] == 1
        assert snap["policy_by_reason"]["调用禁用工具 task"] == 2  # 同原因聚合

    def test_record_output_scrubbed(self, governance):
        governance.record_output(EVENT_OUTPUT_SCRUBBED, "markdown_detail_table")
        snap = governance.snapshot()
        assert snap["counters"]["output_scrubbed_total"] == 1
        assert snap["output_by_event"][EVENT_OUTPUT_SCRUBBED] == 1

    def test_reset_clears(self, governance):
        governance.record_route(SkillRouter().route("哪些台区过载了？"))
        assert governance.snapshot()["counters"]["route_total"] == 1
        governance.reset()
        assert governance.snapshot()["counters"]["route_total"] == 0

    def test_audit_ring_buffer_bounded(self):
        g = SkillGovernance(audit_limit=5)
        for i in range(10):
            g.record_output(EVENT_OUTPUT_SCRUBBED, f"e{i}")
        assert len(g.snapshot()["audit"]) == 5  # 只保留最近 5 条

    def test_record_never_raises(self, governance):
        governance.record_route(None)     # 容错：None 输入不抛
        governance.record_policy("x.y.z", reason=None)
        governance.record_output("x", detail=None)
        assert governance.snapshot()["counters"]["route_total"] == 1  # None route 仍计数为 none


# ----------------------------------------------------------------------
# 2. SkillCatalog 编译期校验（设计 §1.2）
# ----------------------------------------------------------------------
class TestCompileTimeValidation:
    @pytest.fixture
    def real_skill(self):
        """当前唯一 x_tupu 样板：distribution-overload 必须通过全部编译期校验。"""
        return SkillCatalog().load_skill("distribution-overload")

    def test_real_skill_passes(self, real_skill):
        assert real_skill is not None
        assert real_skill.version == "1.0"
        assert real_skill.enabled is True
        # allowed_tools 全部 ∈ 全局工具名册
        for step in real_skill.steps:
            assert set(step.allowed_tools) <= GLOBAL_TOOL_REGISTRY, f"{step.id}: {step.allowed_tools}"
        # allowed_next 引用合法
        ids = {s.id for s in real_skill.steps}
        for step in real_skill.steps:
            for nxt in step.allowed_next:
                assert nxt == "final" or nxt in ids

    def test_output_mode_enum(self):
        assert "single_result_table" in OUTPUT_MODE_ENUM
        assert "analysis_and_result_table" in OUTPUT_MODE_ENUM

    def test_bad_output_mode_rejected(self, tmp_path):
        md = tmp_path / "bad" / "SKILL.md"
        md.parent.mkdir(parents=True)
        md.write_text(_skill_text(output_mode="fancy_table"), encoding="utf-8")
        cat = SkillCatalog(scenarios_dir=tmp_path)
        assert cat.load_skill("bad") is None
        assert any("output" in w for w in cat.warnings)

    def test_bad_allowed_next_rejected(self, tmp_path):
        md = tmp_path / "bad2" / "SKILL.md"
        md.parent.mkdir(parents=True)
        md.write_text(_skill_text(allowed_next=["ghost_step"]), encoding="utf-8")
        cat = SkillCatalog(scenarios_dir=tmp_path)
        assert cat.load_skill("bad2") is None
        assert any("allowed_next" in w for w in cat.warnings)

    def test_bad_triggers_structure_rejected(self, tmp_path):
        md = tmp_path / "bad3" / "SKILL.md"
        md.parent.mkdir(parents=True)
        text = _skill_text().replace(
            "any: [户变关系]",
            "any: 户变关系",  # 非法：不是数组
        )
        md.write_text(text, encoding="utf-8")
        cat = SkillCatalog(scenarios_dir=tmp_path)
        assert cat.load_skill("bad3") is None
        assert any("triggers.any" in w for w in cat.warnings)

    def test_unknown_tool_rejected(self, tmp_path):
        md = tmp_path / "bad4" / "SKILL.md"
        md.parent.mkdir(parents=True)
        text = _skill_text().replace(
            "- batch_entity_source_mode",
            "- totally_unknown_tool",
        )
        md.write_text(text, encoding="utf-8")
        cat = SkillCatalog(scenarios_dir=tmp_path)
        assert cat.load_skill("bad4") is None
        assert any("未知工具" in w for w in cat.warnings)

    def test_version_stability_warning(self, tmp_path):
        """同 version 内容哈希变化 -> 记"未灰度改动"告警（不阻断运行）。"""
        md = tmp_path / "vs" / "SKILL.md"
        md.parent.mkdir(parents=True)
        md.write_text(_skill_text(), encoding="utf-8")
        cat = SkillCatalog(scenarios_dir=tmp_path)
        assert cat.load_skill("vs") is not None
        md.write_text(_skill_text().replace("title: 户变关系查询", "title: 户变关系查询(改)"), encoding="utf-8")
        assert cat.load_skill("vs") is not None  # 仍可用（SKILL.md 是唯一来源）
        assert any("未灰度改动" in w for w in cat.warnings)


# ----------------------------------------------------------------------
# 3. 治理端点逻辑
# ----------------------------------------------------------------------
class TestGovernanceEndpoints:
    def test_catalog_snapshot(self):
        from app.api.data_intelligence import skills_catalog
        out = skills_catalog()
        assert out["ok"] is True
        names = {s["skill_id"] for s in out["catalog"]}
        assert "distribution-overload" in names
        entry = next(s for s in out["catalog"] if s["skill_id"] == "distribution-overload")
        assert entry["enabled"] is True
        assert entry["version"] == "1.0"
        assert entry["sha256"]  # 哈希已计算
        assert "relationship" in entry["steps"]
        assert entry["template_count"] >= 1
        assert entry["entity_alias_count"] >= 1
        # 评审 P0-2：目录快照输出模板校验模式（strict/extensible/generic）
        assert entry["template_mode"] == "scenario_strict"
        # 批4 场景迁移：project-lifecycle-cost 已启用（多引擎）
        plc = next((s for s in out["catalog"] if s["skill_id"] == "project-lifecycle-cost"), None)
        assert plc is not None and plc["enabled"] is True
        assert "analysis" in plc["steps"]

    def test_metrics_snapshot(self):
        from app.api.data_intelligence import skills_metrics
        out = skills_metrics()
        assert out["ok"] is True
        assert "counters" in out and "by_route_type" in out and "audit" in out

    def test_simulate_route_alias(self):
        from app.api.data_intelligence import simulate_route
        from app.api.data_intelligence import RoutePreviewRequest
        out = simulate_route(RoutePreviewRequest(user_input="哪些台区过载了？"))
        assert out["ok"] is True
        assert out["route"]["route_type"] == "scenario"
        assert out["route"]["workflow_step"] == "overload"


# ----------------------------------------------------------------------
# 工具：构造最小合法/非法 SKILL.md
# ----------------------------------------------------------------------
def _skill_text(output_mode: str = "single_result_table", allowed_next=None) -> str:
    allowed_next = allowed_next or []
    return f"""---
name: tmp
description: 测试技能
category: scenario
x_tupu:
  version: "1.0"
  enabled: true
  priority: 10
  triggers:
    any: [户变关系]
  output:
    mode: {output_mode}
  steps:
    - id: s1
      title: 户变关系查询
      triggers:
        any: [户变关系]
      allowed_tools:
        - batch_entity_source_mode
        - execute_sql
      templates:
        - templates/t1.sql
      allowed_next: {allowed_next}
---
"""
