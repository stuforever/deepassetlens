"""test_skill_router_v2.py - 确定性路由测试（受控 Skill 问答平台 v2，替代已删除的旧
test_skill_router.py 关键词分类器测试）。

设计 §11 最小验收用例（代码级）：
 1. "所有用电户与配变户变关系" -> 精确命中 distribution-overload / relationship 步骤
 2. "哪些台区过载" -> overload 步骤
 3. "客户负载占有率倒排" -> load_ratio 步骤
 4. 通用问题 -> 低权限只读 generic 契约（不回退自由 free-plan）
 5. 连续上下文沿用（last_skill/last_step + scope）
 6. 场景未命中绝不回退自由 plan（断言 generic 契约禁止 task/Shell/写文件）
"""
import pytest

from app.services.skill_router import SkillRouter
from app.services.query_contract import ABSOLUTE_FORBIDDEN_TOOLS


@pytest.fixture
def router():
    return SkillRouter()


class TestScenarioRouting:
    def test_relationship_case(self, router):
        """验收用例1：所有用电户与配变户变关系 -> distribution-overload.relationship"""
        r = router.route("所有用电户与配变户变关系")
        assert r.route_type == "scenario"
        assert r.skill_id == "distribution-overload"
        assert r.workflow_step == "relationship"
        assert r.contract is not None
        assert r.contract.skill_id == "distribution-overload"
        assert r.contract.workflow_step == "relationship"

    def test_overload_case(self, router):
        """哪些台区过载 -> overload 步骤（可继续 load_ratio）"""
        r = router.route("哪些台区过载了？")
        assert r.route_type == "scenario"
        assert r.skill_id == "distribution-overload"
        assert r.workflow_step == "overload"
        # overload 步骤允许 next -> load_ratio（终端标志应为 False）
        assert r.contract._runtime.get("terminal") is False

    def test_load_ratio_case(self, router):
        """客户负载占有率倒排 -> load_ratio 步骤（终端，拿到结果即终止）"""
        r = router.route("请对客户负载占有率倒排")
        assert r.route_type == "scenario"
        assert r.skill_id == "distribution-overload"
        assert r.workflow_step == "load_ratio"
        assert r.contract._runtime.get("terminal") is True


class TestGenericFallback:
    def test_generic_low_permission_no_task(self, router):
        """通用问题 -> generic 契约，禁止 Shell/写文件（不回退自由 free-plan）。

        批13-Q 变更：task 契约层放行（allow_subagents=True，委派作为探索加速器），
        运行时层由 SkillPolicy 复合校验（caps.subagents.enabled AND contract.allow_subagents）；
        subagents 关闭或护栏拒绝时 task 仍被拒（capability_events.task_reject）。
        """
        r = router.route("查一下用电客户总数")
        assert r.route_type == "generic"
        assert r.fallback_level == "generic"
        # 绝对禁止（除 task 外）仍生效
        assert {"execute", "write_file", "edit_file", "grep", "glob"} <= set(r.contract.forbidden_tools)
        # 批13-Q：task 入白名单（契约层），运行时层复合校验仍在
        assert r.contract.allow_subagents is True
        assert "task" in r.contract.allowed_tools
        assert "task" not in r.contract.forbidden_tools
        assert "execute" not in r.contract.allowed_tools
        assert "write_file" not in r.contract.allowed_tools

    def test_hello_generic(self, router):
        r = router.route("你好")
        assert r.route_type == "generic"
        assert r.contract.route_type == "generic"

    def test_generic_contract_no_templates(self, router):
        """generic 契约不绑定场景模板（只读查询，无 SQL 白名单）"""
        r = router.route("随便问")
        assert r.contract.template_ids == []


class TestConfirmedContext:
    def test_context_reuse_skill_step(self, router):
        """上轮已确认场景+步骤，本轮无新触发 -> 沿用同一契约"""
        ctx = {"last_skill": "distribution-overload", "last_step": "relationship",
               "last_scope": {"customer_names": ["客户001"], "ordered": True, "commitment": "exact_set"}}
        r = router.route("再看一遍", ctx)
        assert r.route_type == "scenario"
        assert r.skill_id == "distribution-overload"
        assert r.workflow_step == "relationship"
        assert r.contract.scope["customer_names"] == ["客户001"]

    def test_new_trigger_overrides_context(self, router):
        """本轮出现新场景触发词 -> 新场景胜出，不沿用旧上下文"""
        ctx = {"last_skill": "distribution-overload", "last_step": "relationship", "last_scope": {}}
        r = router.route("哪些台区过载？", ctx)
        assert r.workflow_step == "overload"


class TestRoutePriority:
    def test_route_reason_recorded(self, router):
        r = router.route("所有用电户与配变户变关系")
        assert r.route_reason
        assert r.confidence == "deterministic"
        assert r.priority <= 2  # scenario 优先级

    def test_route_never_free_plan_fallback(self, router):
        """设计铁律：场景未命中也不回退"完全自由 free-plan"，而是低权限只读 generic"""
        r = router.route("给我讲讲电力的历史")
        assert r.route_type in ("generic", "fallback")
        assert r.contract.route_type in ("generic", "fallback")


class TestAggregateIntent:
    """S1 稳定性攻坚（L1）：聚合分布意图标记 -> 契约注入受控指令。"""

    def test_分布触发词_标记意图(self, router):
        r = router.route("各电压等级的用电客户分布是怎样的")
        assert r.route_type == "generic"
        assert r.contract.aggregate_intent is not None
        assert r.contract.aggregate_intent["trigger"] == "分布"
        assert "GROUP BY" in r.contract.aggregate_intent["required_shape"]

    def test_占比触发词_标记意图(self, router):
        r = router.route("按重要性等级统计占比")
        assert r.contract.aggregate_intent is not None
        assert r.contract.aggregate_intent["trigger"] in ("占比", "统计")

    def test_普通计数_不标记意图(self, router):
        r = router.route("统计一下当前有多少用电客户")
        assert r.route_type == "generic"
        assert r.contract.aggregate_intent is None

    def test_契约消息_含聚合指令(self):
        """L1：契约 SystemMessage 追加「禁止返回明细全表」受控指令。"""
        from app.api.data_intelligence import _build_contract_system_message
        from app.services.skill_router import route_user_input
        rr = route_user_input("各电压等级的用电客户分布是怎样的")
        assert rr.contract.aggregate_intent is not None
        msg = _build_contract_system_message(rr.contract, question="各电压等级的用电客户分布是怎样的")
        assert "聚合分布" in msg and "禁止返回明细全表" in msg
        # 普通问题无聚合指令
        rr2 = route_user_input("统计一下当前有多少用电客户")
        msg2 = _build_contract_system_message(rr2.contract, question="统计一下当前有多少用电客户")
        assert "禁止返回明细全表" not in msg2
