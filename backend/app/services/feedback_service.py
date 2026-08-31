# -*- coding: utf-8 -*-
"""feedback_service.py - 用户反馈观测闭环（融合设计 §6.1 G5；批13-C 重定义）

POST /api/v1/data-intelligence/feedback {run_id, message_id, verdict, corrected_sql?, comment?}
批13-C 题库移除：👍👎 **纯观测信号**——唯一写路径为 KgFeedbackLog 观测表
（不再有任何示例库自动写路径：👍 直接入库 / 👎+修正进审核队列均已移除）。
聚合消费：候选推荐队列 = 近 N 天高频反馈且金标无覆盖的问题 TopM
（golden_qa_service.list_candidate_recommendations）；人工审核后经管理页录入金标。
run_id -> MetricQueryLog（user_query + executed_sql）取原问题与实际执行 SQL 作存证。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.base import EngineQueryLog, MetricQueryLog

logger = logging.getLogger(__name__)


def _lookup_run(db: Session, run_id: str) -> Dict[str, Any]:
    """按 run_id 取原问题 + 实际执行 SQL（MetricQueryLog 优先，EngineQueryLog 兜底）。"""
    row = db.query(MetricQueryLog).filter(MetricQueryLog.run_id == run_id).order_by(
        MetricQueryLog.created_at.desc()).first()
    if row:
        return {"question": row.user_query or "", "sql": row.executed_sql or ""}
    eng = db.query(EngineQueryLog).filter(EngineQueryLog.run_id == run_id,
                                          EngineQueryLog.status == "ok").order_by(
        EngineQueryLog.created_at.desc()).first()
    if eng:
        return {"question": "", "sql": eng.sql or ""}
    return {"question": "", "sql": ""}


def process_feedback(db: Session, *, run_id: str, message_id: Optional[str] = None,
                     verdict: str, corrected_sql: Optional[str] = None,
                     comment: Optional[str] = None) -> Dict[str, Any]:
    """处理一条反馈（批13-C：纯观测），返回 {ok, route: observed|ignored|noop, reason}。"""
    verdict = (verdict or "").strip().lower()
    if verdict not in ("up", "down"):
        return {"ok": False, "route": "noop", "reason": "verdict 必须为 up|down"}
    run = _lookup_run(db, run_id or "")
    question = (run.get("question") or "").strip()
    sql = (corrected_sql or "").strip() or (run.get("sql") or "").strip()
    try:
        from app.services.golden_qa_service import record_feedback
        res = record_feedback(
            db, run_id=run_id, verdict=verdict, question=question, sql=sql,
            corrected_sql=(corrected_sql or "").strip(), comment=(comment or "").strip())
        if not res.get("ok"):
            return {"ok": False, "route": "ignored", "reason": str(res.get("error", "观测记录失败"))}
        return {"ok": True, "route": "observed",
                "reason": f"👍👎 纯观测（批13-C）：已记录，聚合进候选推荐队列（无任何自动写路径）"}
    except Exception as e:
        logger.warning(f"[Feedback] 处理失败: {e}")
        return {"ok": False, "route": "noop", "reason": f"异常: {e}"}
