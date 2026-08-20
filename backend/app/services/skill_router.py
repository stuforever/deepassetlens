"""skill_router.py - 确定性路由（受控 Skill 问答平台 v2，设计 §4）

Router 不让模型猜命中什么：纯代码按优先级判定。
优先级固定（设计 §4.1）：
  1. 已确认的连续上下文（conversation_context）
  2. 精确场景剧本（SKILL.md x_tupu.triggers）
  3. 需要用户澄清（多场景同时命中 / 范围缺失）
  4. 通用受限能力（低权限只读 generic 契约）
  5. 低权限只读 fallback（与 4 等价，route_type=fallback）
  6. 拒绝执行（命中禁止 / 无可用能力）
禁止"场景未命中就回退为完全自由的 free-plan"。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.services.skill_catalog import SkillDefinition, get_catalog, match_all_groups, match_any_keywords
from app.services.query_contract import QueryContract

logger = logging.getLogger(__name__)

# 路由优先级枚举
PRIORITY_CONFIRMED_CONTEXT = 1
PRIORITY_SCENARIO = 2
PRIORITY_CLARIFICATION = 3
PRIORITY_GENERIC = 4
PRIORITY_FALLBACK = 5
PRIORITY_REJECT = 6


@dataclass
class RouteResult:
    """路由结果（设计 §4.1 输出）。"""

    route_type: str                                    # scenario | clarification | generic | fallback | reject
    skill_id: Optional[str] = None
    workflow_step: Optional[str] = None
    matched_rules: List[str] = field(default_factory=list)
    route_reason: str = ""
    confidence: str = "deterministic"
    fallback_level: str = "none"
    contract: Optional[QueryContract] = None           # 建好的受控契约
    candidates: List[Dict[str, str]] = field(default_factory=list)  # 多命中候选（clarification）
    priority: int = PRIORITY_GENERIC

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route_type": self.route_type,
            "skill_id": self.skill_id,
            "workflow_step": self.workflow_step,
            "matched_rules": list(self.matched_rules),
            "route_reason": self.route_reason,
            "confidence": self.confidence,
            "fallback_level": self.fallback_level,
            "contract": self.contract.to_dict() if self.contract else None,
            "candidates": list(self.candidates),
            "priority": self.priority,
        }


class SkillRouter:
    """确定性路由器。构造可注入 SkillCatalog（单测注入假目录）。"""

    def __init__(self, catalog=None) -> None:
        self._catalog = catalog or get_catalog()

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------
    def route(self, user_input: str,
              conversation_context: Optional[Dict[str, Any]] = None) -> RouteResult:
        result = self._route_inner(user_input, conversation_context)
        # 批4 治理：记录路由审计指标（容错，失败不影响路由）
        try:
            from app.services.skill_governance import get_governance
            get_governance().record_route(result)
        except Exception:
            pass
        return result

    def _route_inner(self, user_input: str,
                     conversation_context: Optional[Dict[str, Any]] = None) -> RouteResult:
        text = (user_input or "").strip()
        ctx = conversation_context or {}

        # 1) 已确认的连续上下文：上轮 skill+step 仍有效，且本轮无新冲突触发 -> 沿用
        confirmed = self._route_confirmed_context(text, ctx)
        if confirmed is not None:
            return confirmed

        # 2) 精确场景剧本
        scenario = self._route_scenario(text)
        if scenario.route_type == "scenario":
            return scenario

        # 3) 需要澄清（多场景同时命中）
        if scenario.route_type == "clarification":
            return scenario

        # 4) 通用受限能力（低权限只读）
        return self._route_generic(text)

    # ------------------------------------------------------------------
    # 优先级 1：连续上下文
    # ------------------------------------------------------------------
    def _route_confirmed_context(self, text: str, ctx: Dict[str, Any]) -> Optional[RouteResult]:
        last_skill = ctx.get("last_skill")
        last_step = ctx.get("last_step")
        last_scope = ctx.get("last_scope") or {}
        if not last_skill or not last_step:
            return None
        skill = self._catalog.load_skill(last_skill)
        if skill is None or not skill.enabled:
            return None
        step = skill.find_step(last_step)
        if step is None:
            return None
        # 本轮若有新的场景触发词，以新场景为准（冲突按优先级新场景胜出），不再沿用
        fresh = self._match_scenarios(text)
        if fresh:
            return None
        # 沿用上轮 scope 的精确客户名（"只看后一个客户"解析见 data_intelligence 层）
        scope = {
            "customer_names": list(last_scope.get("customer_names") or []),
            "ordered": bool(last_scope.get("ordered")),
            "commitment": last_scope.get("commitment", "user_input"),
            "source": "conversation_context",
        }
        contract = QueryContract.from_step(
            skill.name, skill.version, step, scope=scope,
            route_reason=f"沿用上轮已确认上下文：{last_skill}.{last_step}", route_type="scenario",
            multi_engine=skill.multi_engine,
            forbid_markdown_detail_table=bool((skill.output or {}).get("forbid_markdown_detail_table", True)),
            output_mode=step.output_mode or (skill.output or {}).get("mode") or (skill.output or {}).get("output_mode"),
            required_entities=skill.required_entity_codes(),
        )
        return RouteResult(
            route_type="scenario", skill_id=skill.name, workflow_step=step.id,
            matched_rules=["conversation_context: last_skill/last_step"],
            route_reason=f"沿用上轮已确认上下文 {last_skill}.{last_step}，且本轮无新场景触发",
            fallback_level="none", contract=contract, priority=PRIORITY_CONFIRMED_CONTEXT,
        )

    # ------------------------------------------------------------------
    # 优先级 2/3：精确场景剧本 / 澄清
    # ------------------------------------------------------------------
    def _match_scenarios(self, text: str) -> List[SkillDefinition]:
        """按触发词匹配所有启用的场景 Skill。"""
        hits = []
        for skill in self._catalog.list_skills():
            if not skill.enabled:
                continue
            trig = skill.triggers or {}
            any_hits = match_any_keywords(text, trig.get("any") or [])
            group_hits = match_all_groups(text, trig.get("all_groups") or [])
            if any_hits or group_hits:
                hits.append((skill, any_hits, group_hits))
        return [h[0] for h in hits]

    def _route_scenario(self, text: str) -> RouteResult:
        hits = self._match_scenarios(text)
        if not hits:
            # 未命中任何场景
            return RouteResult(
                route_type="none", route_reason="未命中任何场景剧本",
                fallback_level="generic", priority=PRIORITY_GENERIC,
            )
        if len(hits) > 1:
            # 多场景同时命中 -> 展示候选，要求用户确认（设计 §9）
            cands = [{"skill_id": s.name, "description": s.description} for s in hits]
            return RouteResult(
                route_type="clarification", candidates=cands,
                matched_rules=[f"多场景命中: {', '.join(s.name for s in hits)}"],
                route_reason="同时命中多个场景剧本，需用户确认",
                fallback_level="clarification", priority=PRIORITY_CLARIFICATION,
            )
        skill = hits[0]
        return self._select_step(skill, text)

    def _select_step(self, skill: SkillDefinition, text: str) -> RouteResult:
        """在命中 Skill 内按步骤触发词选步骤；无步骤命中则取第一个步骤。"""
        matched_rules = []
        any_hits = match_any_keywords(text, (skill.triggers or {}).get("any") or [])
        group_hits = match_all_groups(text, (skill.triggers or {}).get("all_groups") or [])
        if any_hits:
            matched_rules.append("triggers.any: " + ", ".join(any_hits[:5]))
        if group_hits:
            matched_rules.append("triggers.all_groups: " + "; ".join(group_hits[:3]))

        chosen = None
        step_hit_rule = ""
        for step in skill.steps:
            s_any = match_any_keywords(text, (step.triggers or {}).get("any") or [])
            s_groups = match_all_groups(text, (step.triggers or {}).get("all_groups") or [])
            if s_any or s_groups:
                chosen = step
                step_hit_rule = "step.triggers: " + (", ".join(s_any[:3]) if s_any else "; ".join(s_groups[:2]))
                break
        if chosen is None and skill.steps:
            chosen = skill.steps[0]
            step_hit_rule = f"step: 默认首个步骤 {chosen.id}"

        contract = QueryContract.from_step(
            skill.name, skill.version, chosen,
            route_reason=f"命中场景剧本 {skill.name}，步骤 {chosen.id}",
            route_type="scenario",
            multi_engine=skill.multi_engine,
            forbid_markdown_detail_table=bool((skill.output or {}).get("forbid_markdown_detail_table", True)),
            output_mode=chosen.output_mode or (skill.output or {}).get("mode") or (skill.output or {}).get("output_mode"),
            required_entities=skill.required_entity_codes(),
        )
        return RouteResult(
            route_type="scenario", skill_id=skill.name, workflow_step=chosen.id,
            matched_rules=matched_rules + ([step_hit_rule] if step_hit_rule else []),
            route_reason=f"命中「{skill.description[:40]}」场景，进入 {chosen.id}({chosen.title}) 步骤",
            confidence="deterministic", fallback_level="none",
            contract=contract, priority=PRIORITY_SCENARIO,
        )

    # ------------------------------------------------------------------
    # 优先级 4/5：低权限只读通用 / fallback
    # ------------------------------------------------------------------
    # S1 稳定性攻坚（L1）：聚合分布意图触发词——命中即要求 GROUP BY 聚合视图，禁止返回明细全表
    _AGGREGATE_TRIGGERS = ("分布", "占比", "构成", "比例", "合计", "汇总", "分组", "分别")

    @staticmethod
    def detect_aggregate_intent(text: str) -> Optional[Dict[str, Any]]:
        """识别聚合分布/占比/构成类意图。命中 -> aggregate_intent；否则 None。"""
        if not text:
            return None
        hit = [t for t in SkillRouter._AGGREGATE_TRIGGERS if t in text]
        if not hit:
            return None
        return {
            "trigger": hit[0],
            "dimension_hint": None,  # 维度列提示可选：命中已知维度列名（voltage_name 等）时给出
            "required_shape": "GROUP BY 维度列 + COUNT/SUM",
        }

    def _route_generic(self, text: str) -> RouteResult:
        agg_intent = self.detect_aggregate_intent(text)
        route_reason = "未命中场景剧本，进入低权限只读通用模式（禁止写/SQL执行外的工具）"
        if agg_intent:
            route_reason += f"；检测到聚合意图（触发词={agg_intent['trigger']}）"
        contract = QueryContract.generic(route_reason=route_reason, aggregate_intent=agg_intent)
        return RouteResult(
            route_type="generic", skill_id="__generic__", workflow_step="__generic__",
            matched_rules=["fallback: 无场景命中"],
            route_reason="未命中任何场景剧本，进入低权限只读通用模式（禁止 task/Shell/文件写入/自由 SQL 拼接）",
            fallback_level="generic", contract=contract, priority=PRIORITY_GENERIC,
        )


# 模块级单例
_ROUTER: SkillRouter | None = None


def get_router() -> SkillRouter:
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = SkillRouter()
    return _ROUTER


def route_user_input(user_input: str,
                     conversation_context: Optional[Dict[str, Any]] = None) -> RouteResult:
    """便捷入口：确定性路由（供 data_intelligence 调用）。"""
    return get_router().route(user_input, conversation_context)
