# -*- coding: utf-8 -*-
"""批⑥（v4§11/§十二.3）：契约轨迹服务——done 帧契约视图按 thread_id 落库/查询。

写入为 fire-and-forget 线程（record_event 惯例）：不阻塞流式主链，失败仅告警。
查询供运行观测「契约回放」（admin-gated 路由）。
"""

import logging
import threading
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def record_contract_trace(thread_id: str, expert_id: str, contract: Optional[Dict[str, Any]]) -> None:
    """upsert 一条契约轨迹（fire-and-forget；contract=None 时跳过）。"""

    def _do() -> None:
        if not thread_id or contract is None:
            return
        try:
            from app.models.contract_trace import ContractTrace
            from app.core.database import SessionLocal

            db = SessionLocal()
            try:
                row = db.query(ContractTrace).filter(ContractTrace.thread_id == thread_id).first()
                if row is None:
                    row = ContractTrace(thread_id=thread_id[:64], expert_id=expert_id[:64] or "wenshu",
                                        payload=contract)
                    db.add(row)
                else:
                    row.payload = contract
                    row.expert_id = expert_id[:64] or row.expert_id
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[ContractTrace] 落库失败(不阻塞主链路): {e}")

    threading.Thread(target=_do, daemon=True).start()


def get_contract_trace(thread_id: str) -> Optional[Dict[str, Any]]:
    """按 thread_id 取契约轨迹（含 route/contract 视图与时间戳）。"""
    from app.models.contract_trace import ContractTrace
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        row = db.query(ContractTrace).filter(ContractTrace.thread_id == thread_id).first()
        if row is None:
            return None
        return {
            "thread_id": row.thread_id,
            "expert_id": row.expert_id,
            "contract": row.payload,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
    finally:
        db.close()
