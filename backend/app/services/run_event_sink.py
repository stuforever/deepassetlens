"""run_event_sink.py - free-plan 流式问答关键事件持久化（v3.1 步骤5）

复用既有 RunEvent.event_order 机制（app/models/scheduler.RunEvent），把 free-plan 流式
端点的关键事件落库，供审计 / 按序补取（runs.py 的 since_order 尾拉）。

仅 TUPU_DECISION_GATE=1 时启用（为判定单闸门提供审计轨迹；闸门关时无需持久化）。

**容错铁律**：所有 DB 操作 try/except 包裹，失败只 log 不抛 -- 绝不影响 SSE 流式主流程。
一次 append 失败即停用后续持久化（避免反复报错刷日志），run.completed/run.failed 仍尝试收尾。

不复用 agent_run_runtime._append_event（私有函数 + 仅 flush 不 commit）：
本 sink 直接构造 RunEvent 并 commit，保证长流式期间事件逐条持久（客户端断开也不丢已落库事件）。
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.database import SessionLocal
from app.models.scheduler import AgentRun, RunEvent

logger = logging.getLogger(__name__)

# 复用 tupu_deepagent 的闸门 flag：开闸门才需要审计轨迹（同一开关）
try:
    from app.services.tupu_deepagent import _DECISION_GATE_ENABLED
except Exception:  # 导入失败(循环引用等) -> 不启用, 不影响流式
    _DECISION_GATE_ENABLED = False


class RunEventSink:
    """free-plan 关键事件持久化 sink（容错、flag-gated）。

    用法（在 event_iter / _consume_events 闭包里）::
        sink = RunEventSink(req.user_input)          # 闭包变量, _consume_events 内可访问
        sink.append("tool.started", {...}, step_id=str(sid))
        sink.complete({"final_answer": ...})         # 正常完成
        sink.fail("异常信息")                         # 或失败
        sink.close()                                  # finally 里必调

    flag 关或初始化失败 -> 所有方法 no-op，绝不抛异常到流式主流程。
    """

    SCENE = "free_plan"

    def __init__(self, user_query: str = "") -> None:
        self._active = False
        self._db = None
        self._run = None
        self._run_id = None  # 普通字符串, init 时锁定(避免 expire_on_commit 后 lazy load 报 DetachedInstance)
        self._order = 1
        if not _DECISION_GATE_ENABLED:
            return
        try:
            self._db = SessionLocal()
            self._run = AgentRun(
                run_code=f"run_{uuid.uuid4().hex[:12]}",
                scene_code=self.SCENE,
                page_code=self.SCENE,
                entry_type="workflow",
                target_type="workflow",
                status="running",
                input_payload={"user_query": user_query[:500]} if user_query else {},
                started_at=datetime.now(timezone.utc),
            )
            self._db.add(self._run)
            self._db.commit()
            self._db.refresh(self._run)
            self._run_id = self._run.id  # 锁定为普通字符串
            self._active = True
            self._append("run.started", {"user_query": user_query[:500]})
        except Exception as e:
            logger.warning(f"[RunEventSink] 初始化失败(不影响流式): {e}")
            self._safe_rollback()
            self._active = False

    @property
    def run_id(self) -> Optional[str]:
        """已创建的 AgentRun.id（供日志/调试；未启用时为 None）。"""
        return self._run_id

    def append(self, event_type: str, payload: Optional[Dict[str, Any]] = None,
               step_id: Optional[str] = None) -> None:
        """追加关键事件（tool.started / tool.completed / gate.rejected 等）。容错 no-op。"""
        if not self._active:
            return
        try:
            self._append(event_type, payload, step_id)
        except Exception as e:
            logger.warning(f"[RunEventSink] append {event_type} 失败(停用后续持久化, 不影响流式): {e}")
            self._safe_rollback()
            self._active = False  # 一次失败后停用, 避免长流式里反复报错

    def complete(self, payload: Optional[Dict[str, Any]] = None) -> None:
        """run 完成：追加 run.completed + 置 status=completed。容错。"""
        if not self._active or self._run is None:
            return
        try:
            self._append("run.completed", payload or {})
            self._run.status = "completed"
            self._run.completed_at = datetime.now(timezone.utc)
            if payload:
                self._run.output_payload = payload
            self._db.commit()
        except Exception as e:
            logger.warning(f"[RunEventSink] complete 失败(不影响流式): {e}")
            self._safe_rollback()

    def fail(self, message: str) -> None:
        """run 失败：追加 run.failed + 置 status=failed。容错。"""
        if not self._active or self._run is None:
            return
        try:
            self._append("run.failed", {"message": message[:500]})
            self._run.status = "failed"
            self._run.error_message = message[:2000]
            self._run.completed_at = datetime.now(timezone.utc)
            self._db.commit()
        except Exception as e:
            logger.warning(f"[RunEventSink] fail 失败(不影响流式): {e}")
            self._safe_rollback()

    def close(self) -> None:
        """关闭 DB session（finally 里必调）。"""
        if self._db is not None:
            try:
                self._db.close()
            except Exception:
                pass
            self._db = None

    # ---- 内部 ----

    def _append(self, event_type: str, payload: Optional[Dict[str, Any]],
                step_id: Optional[str] = None) -> None:
        """构造 RunEvent 并 commit（逐条持久，断开不丢已落库事件）。"""
        event = RunEvent(
            run_id=self._run.id,
            event_code=f"evt_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            event_order=self._order,
            step_id=step_id,
            payload=payload or {},
        )
        self._db.add(event)
        self._db.commit()
        self._order += 1

    def _safe_rollback(self) -> None:
        if self._db is not None:
            try:
                self._db.rollback()
            except Exception:
                pass
