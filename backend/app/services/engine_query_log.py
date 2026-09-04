# -*- coding: utf-8 -*-
"""engine_query_log.py - 引擎查询日志（批1）

一张 EngineQueryLog 表（kg_engine_query_logs），两引擎 execute 出口统一落库，
try/finally 保证异常不影响主流程；默认 30 天自动清理（挂 TaskWorker 低优先级周期任务）。
批3 提供最简列表端点（queries）。
"""
from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import text

logger = logging.getLogger(__name__)

_RETENTION_DAYS = 30


def _sql_hash(sql: str) -> str:
    try:
        return hashlib.sha1((sql or "").encode("utf-8")).hexdigest()[:8]
    except Exception:
        return ""


def record_query_log(engine: str, sql: str, rows_returned: int = 0, duration_ms: int = 0,
                     status: str = "ok", error_class: Optional[str] = None,
                     run_id: Optional[str] = None, direct_pipeline: bool = False) -> None:
    """落一条查询日志（best-effort，异常吞掉不影响主流程）。批9：direct_pipeline 直通标记。
    批13-I C4：附列 LLM 前缀缓存观测（contextvar 桥读最近一次 LLM 调用缓存态；None=未透传）。"""
    try:
        try:
            from app.services.llm_client import get_last_llm_cache as _glc
            _cache = _glc() or {}
        except Exception:
            _cache = {}
        from app.models.base import EngineQueryLog
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            db.add(EngineQueryLog(
                run_id=(run_id or "")[:64] or None,
                engine=engine, sql_hash=_sql_hash(sql), sql=(sql or "")[:4000],
                rows_returned=int(rows_returned or 0), duration_ms=int(duration_ms or 0),
                status=status, error_class=error_class,
                direct_pipeline=bool(direct_pipeline),
                cache_hit_tokens=_cache.get("cache_hit_tokens"),
                cache_miss_tokens=_cache.get("cache_miss_tokens"),
            ))
            db.commit()
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[EngineQueryLog] 落库失败（忽略）: {e}")


def purge_old_logs(retention_days: int = _RETENTION_DAYS) -> int:
    """删除超过 retention_days 的查询日志，返回删除行数（best-effort）。"""
    try:
        from app.core.database import engine
        cutoff = (datetime.utcnow() - timedelta(days=retention_days)).strftime("%Y-%m-%d %H:%M:%S")
        with engine.begin() as conn:
            r = conn.execute(
                text("DELETE FROM kg_engine_query_logs WHERE created_at < :cutoff"),
                {"cutoff": cutoff},
            )
            deleted = r.rowcount if r.rowcount is not None else 0
        if deleted:
            logger.info(f"[EngineQueryLog] 清理 {retention_days} 天前日志 {deleted} 条")
        return deleted
    except Exception as e:
        logger.warning(f"[EngineQueryLog] 清理失败（忽略）: {e}")
        return 0


def register_purge_job(task_worker_manager, retention_days: int = _RETENTION_DAYS,
                       interval_seconds: float = 6 * 3600) -> None:
    """把 30 天清理挂到 TaskWorker 低优先级周期任务（批1）。"""
    try:
        task_worker_manager.register_periodic(interval_seconds, lambda: purge_old_logs(retention_days))
        logger.info(f"[EngineQueryLog] 已注册周期清理（{retention_days} 天 / {int(interval_seconds)}s）")
    except Exception as e:
        logger.warning(f"[EngineQueryLog] 注册周期清理失败（忽略）: {e}")


def list_queries(limit: int = 20, offset: int = 0, engine: Optional[str] = None,
                 status: Optional[str] = None) -> Dict[str, Any]:
    """批3 最简查询日志列表（按时间倒序）。"""
    try:
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            q = ("SELECT id, run_id, engine, sql_hash, `sql`, rows_returned, duration_ms, "
                 "status, error_class, direct_pipeline, created_at FROM kg_engine_query_logs")
            conds, params = [], {}
            if engine:
                conds.append("engine = :engine")
                params["engine"] = engine
            if status:
                conds.append("status = :status")
                params["status"] = status
            if conds:
                q += " WHERE " + " AND ".join(conds)
            q += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            params["limit"] = max(1, min(int(limit or 20), 200))
            params["offset"] = max(0, int(offset or 0))
            rows = db.execute(text(q), params).fetchall()
            items = [
                {
                    "id": r[0], "run_id": r[1], "engine": r[2], "sql_hash": r[3],
                    "sql": r[4], "rows_returned": r[5], "duration_ms": r[6],
                    "status": r[7], "error_class": r[8],
                    "direct_pipeline": bool(r[9]) if r[9] is not None else False,
                    "created_at": r[10].isoformat() if r[10] else None,
                }
                for r in rows
            ]
            total = db.execute(text(
                "SELECT COUNT(*) FROM kg_engine_query_logs" + (" WHERE " + " AND ".join(conds) if conds else "")
            ), {k: v for k, v in params.items() if k not in ("limit", "offset")}).scalar() or 0
            return {"items": items, "total": total, "limit": params["limit"], "offset": params["offset"]}
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[EngineQueryLog] 列表查询失败: {e}")
        return {"items": [], "total": 0, "limit": limit, "offset": offset, "error": str(e)}
