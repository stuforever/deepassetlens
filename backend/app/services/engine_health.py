# -*- coding: utf-8 -*-
"""engine_health.py - 引擎健康探测（批3：懒探测 + 60s 缓存）

不建后台轮询/状态机（完整版裁剪项），按需懒探测并用 60s 缓存缓解上游压力；
三引擎：doris（Doris 连接池 SELECT 1）/ duckdb（DuckDB 单例 SELECT 1）/ pg（业务引擎 SELECT 1）。
batch_entity_source_mode 与 GET /api/engine/health 共用本快照。
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_CACHE_TTL = 60
_CACHE: Dict[str, Dict[str, Any]] = {}
_LOCK = threading.Lock()


def _probe_doris() -> None:
    from app.services.doris_engine import _with_query_timeout, get_conn
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(_with_query_timeout("SELECT 1"))
        cur.fetchone()
    finally:
        conn.close()


def _probe_duckdb() -> None:
    from app.services.duckdb_engine import get_conn
    conn = get_conn()
    conn.execute("SELECT 1").fetchone()


def _probe_pg() -> None:
    from sqlalchemy import text
    from app.services.sql_executor import _get_biz_engine
    eng = _get_biz_engine()
    with eng.connect() as c:
        c.execute(text("SELECT 1"))


_PROBES = {"doris": _probe_doris, "duckdb": _probe_duckdb, "pg": _probe_pg}


def probe(engine: str, force: bool = False) -> Dict[str, Any]:
    """懒探测单个引擎（60s 缓存；force=True 强制重测）。"""
    now = time.time()
    with _LOCK:
        cached = _CACHE.get(engine)
        if cached and not force and (now - cached["checked_at"]) < _CACHE_TTL:
            return dict(cached)
    fn = _PROBES.get(engine)
    if fn is None:
        return {"engine": engine, "status": "unknown", "latency_ms": 0,
                "checked_at": now, "checked_at_str": _fmt(now), "error": "未知引擎"}
    t0 = time.time()
    err = None
    try:
        fn()
        status = "ok"
    except Exception as e:
        status = "error"
        err = str(e)[:200]
        logger.warning(f"[engine_health] {engine} 探测失败: {e}")
    entry = {
        "engine": engine, "status": status,
        "latency_ms": int((time.time() - t0) * 1000),
        "checked_at": now, "checked_at_str": _fmt(now), "error": err,
    }
    with _LOCK:
        _CACHE[engine] = entry
    return dict(entry)


def snapshot() -> Dict[str, Dict[str, Any]]:
    """三引擎健康快照（各走懒探测 + 缓存；首查并行探测控制延迟）。"""
    from concurrent.futures import ThreadPoolExecutor
    keys = ("doris", "duckdb", "pg")
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {k: pool.submit(probe, k) for k in keys}
        return {k: f.result() for k, f in futures.items()}


def invalidate(engine: Optional[str] = None) -> None:
    """清缓存（配置变更后调，强制下次重测）。"""
    with _LOCK:
        if engine:
            _CACHE.pop(engine, None)
        else:
            _CACHE.clear()


def _fmt(ts: float) -> str:
    try:
        import datetime as _dt
        return _dt.datetime.fromtimestamp(ts).strftime("%H:%M:%S")
    except Exception:
        return ""
