# -*- coding: utf-8 -*-
"""feedback_service.py - 用户反馈闭环（融合设计 §6.1 G5）

POST /api/v1/data-intelligence/feedback {run_id, message_id, verdict, corrected_sql?, comment?}
入库路由：
  - 👍 且无修正 SQL -> 示例库 status=user_confirmed 直接入库 + Qdrant upsert（G1 良性数据源）
  - 👎 + 修正 SQL -> 示例库 status=review 进审核队列（管理页 /qa-examples 审核）
  - 👎 无修正 -> 仅记录（不污染示例库）
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
    """处理一条反馈，返回 {ok, route: created|review|ignored|noop, example_id?, reason}。"""
    verdict = (verdict or "").strip().lower()
    if verdict not in ("up", "down"):
        return {"ok": False, "route": "noop", "reason": "verdict 必须为 up|down"}
    run = _lookup_run(db, run_id or "")
    question = (run.get("question") or "").strip()
    sql = (corrected_sql or "").strip() or (run.get("sql") or "").strip()
    corrected = bool((corrected_sql or "").strip())
    try:
        from app.services.qa_example_service import add_qa_example
        if verdict == "up" and not corrected:
            # 👍 无修正 -> 直接入库（user_confirmed）+ Qdrant upsert
            if not question or not sql:
                return {"ok": False, "route": "ignored",
                        "reason": "无问题/SQL 存证（run_id 未命中 MetricQueryLog 或执行 SQL 为空）"}
            res = add_qa_example(db, question_raw=question, sql=sql,
                                 route_type="generic", example_type="user_confirmed",
                                 entity_codes=[])
            if not res.get("ok"):
                return {"ok": False, "route": "ignored", "reason": str(res.get("error", "入库失败"))}
            return {"ok": True, "route": "created", "example_id": res.get("id"),
                    "reason": "👍 无修正：user_confirmed 直接入库 + Qdrant"}
        if verdict == "down" and corrected:
            # 👎 + 修正 SQL -> review 审核队列（管理页审核后启用）
            if not question:
                return {"ok": False, "route": "ignored", "reason": "无原问题存证"}
            res = add_qa_example(db, question_raw=question, sql=sql,
                                 route_type="generic", example_type="user_confirmed",
                                 entity_codes=[], status="review")
            return {"ok": True, "route": "review", "example_id": res.get("id"),
                    "reason": "👎+修正：status=review 进审核队列"}
        return {"ok": True, "route": "noop", "reason": f"verdict={verdict} corrected={corrected}：仅记录"}
    except Exception as e:
        logger.warning(f"[Feedback] 处理失败: {e}")
        return {"ok": False, "route": "noop", "reason": f"异常: {e}"}
