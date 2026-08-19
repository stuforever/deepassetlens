"""skill_governance.py - 生产治理：审计 + 运行指标（受控 Skill 问答平台 v2，批4）

设计对齐：
- §2.3「路由结果写入审计（route_mode/skill_name/workflow_step/route_reason）」；
- §3「违规策略（首次拒绝/再次终止）须可审计」；
- 阶段 C「运行观测台」的数据源 —— 本批先落**进程内内存注册表**，不新增 DB 表/不改 DB 结构。

铁律：
- 纯内存、线程安全（RLock）；不依赖外部服务；
- 所有 record_* 均 try/except 兜底 —— 审计失败绝不抛异常影响主流程；
- 审计轨迹为有界 ring buffer（默认保留最近 200 条），snapshot 返回复制品。
"""
from __future__ import annotations

import logging
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

AUDIT_LIMIT = 200  # 审计轨迹有界保留条数

# 事件类型常量（与 skill_policy 事件名对齐，便于观测台直接消费）
EVENT_ROUTE_SCENARIO = "route.scenario"
EVENT_ROUTE_CLARIFICATION = "route.clarification"
EVENT_ROUTE_GENERIC = "route.generic"
EVENT_ROUTE_FALLBACK = "route.fallback"
EVENT_ROUTE_REJECT = "route.reject"
EVENT_POLICY_REJECTED = "policy.rejected"    # 首次违规（指引）
EVENT_POLICY_BLOCKED = "policy.blocked"      # 再次违规（阻断）
EVENT_ENGINE_SELECTED = "engine.selected"
EVENT_STOP_REACHED = "stop.reached"
EVENT_TEMPLATE_BOUND = "template.bound"
EVENT_OUTPUT_SCRUBBED = "output.scrubbed"


class SkillGovernance:
    """进程内治理注册表：路由/策略/输出三类指标 + 有界审计轨迹。"""

    def __init__(self, audit_limit: int = AUDIT_LIMIT) -> None:
        self._lock = threading.RLock()
        self._audit_limit = audit_limit
        self._started_at = _now_iso()
        self._route_counts: Dict[str, int] = {}        # by route_type
        self._route_by_skill: Dict[str, int] = {}      # by skill_id
        self._route_by_step: Dict[str, int] = {}       # by step
        self._policy_counts: Dict[str, int] = {}       # by event(blocked/rejected/engine/stop/template)
        self._policy_by_reason: Dict[str, int] = {}    # 拒绝原因聚合（前 60 字符）
        self._output_counts: Dict[str, int] = {}       # by event(scrubbed)
        self._audit: Deque[Dict[str, Any]] = deque(maxlen=audit_limit)

    # ------------------------------------------------------------------
    # 记录（均容错：失败只 log，不抛）
    # ------------------------------------------------------------------
    def record_route(self, route: Any) -> None:
        """记录一次路由决策（SkillRouter.RouteResult）。"""
        try:
            rt = route.route_type if route is not None else "none"
            skill = route.skill_id if route is not None else None
            step = route.workflow_step if route is not None else None
            event = {
                "scenario": EVENT_ROUTE_SCENARIO,
                "clarification": EVENT_ROUTE_CLARIFICATION,
                "generic": EVENT_ROUTE_GENERIC,
                "fallback": EVENT_ROUTE_FALLBACK,
                "reject": EVENT_ROUTE_REJECT,
            }.get(rt, f"route.{rt}")
            with self._lock:
                self._route_counts[rt] = self._route_counts.get(rt, 0) + 1
                if skill:
                    self._route_by_skill[skill] = self._route_by_skill.get(skill, 0) + 1
                if step:
                    self._route_by_step[step] = self._route_by_step.get(step, 0) + 1
                self._audit.append({
                    "ts": _now_iso(), "event": event,
                    "payload": {"route_type": rt, "skill_id": skill, "workflow_step": step},
                })
        except Exception as e:
            logger.warning(f"[SkillGovernance] record_route 失败: {e}")

    def record_policy(self, event: str, skill_id: Optional[str] = None,
                      step: Optional[str] = None, reason: str = "",
                      attempt: Optional[int] = None) -> None:
        """记录一次策略裁决：rejected/blocked/engine_selected/stop_reached/template_bound。"""
        try:
            with self._lock:
                self._policy_counts[event] = self._policy_counts.get(event, 0) + 1
                if event in (EVENT_POLICY_REJECTED, EVENT_POLICY_BLOCKED) and reason:
                    key = reason[:60]
                    self._policy_by_reason[key] = self._policy_by_reason.get(key, 0) + 1
                self._audit.append({
                    "ts": _now_iso(), "event": event,
                    "payload": {"skill_id": skill_id, "workflow_step": step,
                                "reason": reason[:200], "attempt": attempt},
                })
        except Exception as e:
            logger.warning(f"[SkillGovernance] record_policy 失败: {e}")

    def record_output(self, event: str, detail: str = "") -> None:
        """记录一次输出契约处理（如 output.scrubbed）。"""
        try:
            with self._lock:
                self._output_counts[event] = self._output_counts.get(event, 0) + 1
                self._audit.append({
                    "ts": _now_iso(), "event": event, "payload": {"detail": detail[:200]},
                })
        except Exception as e:
            logger.warning(f"[SkillGovernance] record_output 失败: {e}")

    # ------------------------------------------------------------------
    # 快照 / 重置
    # ------------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """返回治理快照（复制品，调用方随意读）。"""
        with self._lock:
            return {
                "started_at": self._started_at,
                "counters": {
                    "route_total": sum(self._route_counts.values()),
                    "policy_total": sum(self._policy_counts.values()),
                    "output_total": sum(self._output_counts.values()),
                    "blocked_total": self._policy_counts.get(EVENT_POLICY_BLOCKED, 0),
                    "rejected_total": self._policy_counts.get(EVENT_POLICY_REJECTED, 0),
                    "engine_selected_total": self._policy_counts.get(EVENT_ENGINE_SELECTED, 0),
                    "stop_reached_total": self._policy_counts.get(EVENT_STOP_REACHED, 0),
                    "output_scrubbed_total": self._output_counts.get(EVENT_OUTPUT_SCRUBBED, 0),
                },
                "by_route_type": dict(self._route_counts),
                "by_skill": dict(self._route_by_skill),
                "by_step": dict(self._route_by_step),
                "policy_by_event": dict(self._policy_counts),
                "policy_by_reason": dict(self._policy_by_reason),
                "output_by_event": dict(self._output_counts),
                "audit": list(self._audit),
            }

    def reset(self) -> None:
        """清空指标与审计（测试/观测台刷新用）。"""
        with self._lock:
            self._route_counts.clear()
            self._route_by_skill.clear()
            self._route_by_step.clear()
            self._policy_counts.clear()
            self._policy_by_reason.clear()
            self._output_counts.clear()
            self._audit.clear()
            self._started_at = _now_iso()


# 模块级单例
_GOVERNANCE: Optional[SkillGovernance] = None
_GOVERNANCE_LOCK = threading.Lock()


def get_governance() -> SkillGovernance:
    global _GOVERNANCE
    if _GOVERNANCE is None:
        with _GOVERNANCE_LOCK:
            if _GOVERNANCE is None:
                _GOVERNANCE = SkillGovernance()
    return _GOVERNANCE


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")
