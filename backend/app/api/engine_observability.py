# -*- coding: utf-8 -*-
"""engine_observability.py - 数据引擎观测端点（批3 轻观测 + P4/P5 深化）

- GET    /api/engine/health          三引擎健康快照（懒探测+60s缓存）
- GET    /api/engine/cache/stats      API 内存缓存命中率
- POST   /api/engine/cache/invalidate 缓存失效（endpoint_id 或全部）
- GET    /api/engine/queries          引擎查询日志列表
- POST   /api/engine/explain          Doris EXPLAIN 执行计划（两档：EXPLAIN / VERBOSE）
- GET    /api/engine/circuits         DuckDB API 端点熔断/限速状态（P3）
- POST   /api/engine/pushdown/debug   Pushdown 调试器（解析+下推树，不真实执行，P3/P5）
- GET    /api/engine/profile          Profile 代理（Doris FE 18030 查询画像，P4）
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services import duckdb_engine, engine_health

router = APIRouter(prefix="/api/engine", tags=["engine-observability"])


class CacheInvalidateRequest(BaseModel):
    endpoint_id: Optional[str] = None   # None=清全部


class ExplainRequest(BaseModel):
    sql: str
    catalog: Optional[str] = None
    verbose: bool = False               # P4：EXPLAIN VERBOSE 两档


class PushdownDebugRequest(BaseModel):
    sql: str


@router.get("/health")
def engine_health_endpoint():
    """三引擎健康快照（doris/duckdb/pg）。"""
    return {"code": 200, "data": engine_health.snapshot()}


@router.get("/cache/stats")
def cache_stats():
    """API 内存缓存命中率/条目数。"""
    return {"code": 200, "data": duckdb_engine.cache_stats()}


@router.post("/cache/invalidate")
def cache_invalidate(payload: CacheInvalidateRequest):
    """缓存失效（endpoint_id 缺省=清全部）。配置保存时前端也应触发。"""
    n = duckdb_engine.invalidate_endpoint_cache(payload.endpoint_id)
    return {"code": 200, "data": {"cleared": n, "scope": payload.endpoint_id or "all"}}


@router.get("/queries")
def queries(limit: int = 20, offset: int = 0, engine: Optional[str] = None, status: Optional[str] = None):
    """引擎查询日志（批1 落库，批3 最简列表）。"""
    from app.services.engine_query_log import list_queries
    return {"code": 200, "data": list_queries(limit=limit, offset=offset, engine=engine, status=status)}


@router.get("/circuits")
def circuits():
    """P3：各 API 端点的熔断/限速状态（CLOSED/OPEN/HALF_OPEN + 连续失败数）。"""
    return {"code": 200, "data": duckdb_engine.circuit_status()}


@router.post("/pushdown/debug")
def pushdown_debug(payload: PushdownDebugRequest, db: Session = Depends(get_db)):
    """P3/P5：Pushdown 调试器 —— 解析 SQL 产出下推树，不真实执行。

    对每个涉及 API 端点：eq/in/range/like 逐列 kind + 是否真正触达上游 +
    未下推审计。需虚拟表名与配置匹配（取 DB 内 endpoints）。
    """
    sql = (payload.sql or "").strip()
    if not sql:
        return {"code": 400, "data": {"error": "SQL 为空", "error_class": "SYNTAX"}}
    try:
        endpoints = duckdb_engine.load_endpoints_from_db(db)
        tables, where_filters = duckdb_engine._parse_sql_tables_and_filters(sql)
        trace: Dict[str, Any] = {}
        not_pushed: list = []
        for alias, tbl in tables.items():
            if tbl not in endpoints or tbl in trace:
                continue
            meta = {
                "id": endpoints[tbl].get("id"), "params": endpoints[tbl].get("params") or [],
                "rate_limit_min_interval_ms": (endpoints[tbl].get("run_config") or {}).get("rate_limit_min_interval_ms"),
                "circuit_threshold": (endpoints[tbl].get("run_config") or {}).get("circuit_threshold"),
                "circuit_open_seconds": (endpoints[tbl].get("run_config") or {}).get("circuit_open_seconds"),
            }
            filters = where_filters.get(tbl, {})
            sent = set(duckdb_engine._build_query_params(meta, filters).keys())
            param_cols = {p["column"]: p for p in (endpoints[tbl].get("params") or [])}
            cols_trace: Dict[str, Any] = {}
            for col_name, val in (filters or {}).items():
                p = param_cols.get(col_name)
                if isinstance(val, dict) and "_range" in val:
                    kind, detail = "range", {"range": val["_range"]}
                    pushed = bool(p and (p.get("range") or p.get("map_to") == "range")
                                  and (f"{p.get('name')}_min" in sent or f"{p.get('name')}_max" in sent))
                elif isinstance(val, dict) and "_like" in val:
                    kind, detail = "like", {"pattern": val["_like"]}
                    pushed = bool(p and (p.get("prefix") or p.get("map_to") == "prefix") and p.get("name") in sent)
                elif isinstance(val, (list, tuple)):
                    kind, detail = "in", {"values": val}
                    pushed = bool(p and p.get("name") in sent)
                else:
                    kind, detail = "eq", {"value": val}
                    pushed = bool(p and p.get("name") in sent)
                cols_trace[col_name] = {"kind": kind, "pushed_to_api": pushed, **detail}
                if not pushed:
                    not_pushed.append({"table": tbl, "column": col_name, "kind": kind,
                                       "reason": "endpoint 未声明该参数或未声明 range/prefix 支持"})
            trace[tbl] = {"endpoint": endpoints[tbl].get("name"), "cols": cols_trace,
                          "pushed_to_api": any(c["pushed_to_api"] for c in cols_trace.values())}
        rebuilt = duckdb_engine.build_sql_with_filters(sql, {
            c: v for f in where_filters.values() for c, v in f.items()})
        return {"code": 200, "data": {
            "sql": sql,
            "tables": {a: t for a, t in tables.items()},
            "pushdown_trace": trace,
            "not_pushed": not_pushed,
            "sql_with_filters": rebuilt,
        }}
    except Exception as e:
        from app.services.engine_errors import apply_error_class
        return {"code": 500, "data": apply_error_class({"error": str(e)})}


@router.post("/explain")
def explain(payload: ExplainRequest):
    """Doris EXPLAIN 执行计划（两档：EXPLAIN / EXPLAIN VERBOSE；诊断慢 SQL）。"""
    from app.services import doris_engine
    sql = (payload.sql or "").strip()
    if not sql:
        return {"code": 400, "data": {"error": "SQL 为空", "error_class": "SYNTAX"}}
    keyword = "EXPLAIN VERBOSE" if payload.verbose else "EXPLAIN"
    final_sql = f"{keyword} {sql.rstrip(';')}"
    conn = doris_engine.get_conn()
    try:
        cur = conn.cursor()
        if payload.catalog:
            doris_engine._check_ident(payload.catalog)
            cur.execute(f"SWITCH {payload.catalog}")
        cur.execute(final_sql)
        rows = cur.fetchall()
        plan = "\n".join(str(r[0]) for r in rows)
        return {"code": 200, "data": {"plan": plan, "sql": sql, "catalog": payload.catalog,
                                      "verbose": payload.verbose}}
    except Exception as e:
        from app.services.engine_errors import apply_error_class
        return {"code": 500, "data": apply_error_class({"error": str(e)})}
    finally:
        # 三轨M3/8：SWITCH 联邦 catalog 后归还池前复位（2026-08-21 线上回归同源防线）
        try:
            doris_engine._reset_connection_catalog(cur)
        except Exception:
            pass
        conn.close()


@router.get("/profile")
def profile(query_id: str):
    """P4：Profile 代理 —— 转发 Doris FE HTTP(18030) 查询画像。

    优先 /api/query_profile（Doris 2.x+），失败降级 /rest/v1/query_profile（历史路径）。
    """
    import urllib.parse
    from app.services import doris_engine
    from app.services.engine_errors import apply_error_class
    cfg = doris_engine._load_config()
    fe_host = "localhost"
    fe_port = 18030
    try:
        import urllib3
        urllib3.disable_warnings()
    except Exception:
        pass
    paths = ["/api/query_profile", "/rest/v1/query_profile"]
    last_err = ""
    import requests as _rq
    for base in paths:
        try:
            url = f"http://{fe_host}:{fe_port}{base}?query_id={urllib.parse.quote(str(query_id))}"
            resp = _rq.get(url, timeout=15, verify=False)
            if resp.status_code == 200:
                try:
                    return {"code": 200, "data": {"query_id": query_id, "profile": resp.json()}}
                except Exception:
                    return {"code": 200, "data": {"query_id": query_id, "profile": resp.text}}
            last_err = f"HTTP {resp.status_code}"
        except Exception as e:
            last_err = str(e)
    return {"code": 500, "data": apply_error_class({"error": f"FE Profile 代理失败: {last_err}"})}


# --------------------------------------------------------------------------- #
# P5：预聚合加速器（kg_engine_accelerators）
# --------------------------------------------------------------------------- #

class AcceleratorPayload(BaseModel):
    name: str
    description: Optional[str] = None
    source_tables: list = []
    agg_expr: Optional[str] = None
    agg_col: Optional[str] = None
    target_catalog: str = "internal"
    target_db: str = "test_db"
    target_table: str
    refresh_sql: str
    refresh_minutes: int = 60
    staleness_note: bool = True
    enabled: bool = True


@router.get("/accelerators")
def accelerator_list(enabled_only: bool = False):
    """P5：加速器列表。"""
    from app.services import engine_accelerator
    items = engine_accelerator.list_accelerators(enabled_only=enabled_only)
    return {"code": 200, "data": items, "count": len(items)}


@router.post("/accelerators")
def accelerator_create(payload: AcceleratorPayload):
    from app.services import engine_accelerator
    return {"code": 200, "data": engine_accelerator.create_accelerator(payload.dict())}


@router.put("/accelerators/{acc_id}")
def accelerator_update(acc_id: str, payload: AcceleratorPayload):
    from app.services import engine_accelerator
    data = engine_accelerator.update_accelerator(acc_id, payload.dict())
    if data is None:
        return {"code": 404, "data": {"error": "加速器不存在"}}
    return {"code": 200, "data": data}


@router.delete("/accelerators/{acc_id}")
def accelerator_delete(acc_id: str):
    from app.services import engine_accelerator
    ok = engine_accelerator.delete_accelerator(acc_id)
    if not ok:
        return {"code": 404, "data": {"error": "加速器不存在"}}
    return {"code": 200, "data": {"deleted": acc_id}}


@router.post("/accelerators/{acc_id}/refresh")
def accelerator_refresh(acc_id: str):
    """P5：立即刷新目标表（INSERT OVERWRITE / CREATE TABLE AS）。"""
    from app.services import engine_accelerator
    r = engine_accelerator.refresh_accelerator(acc_id)
    if not r.get("ok"):
        return {"code": 500, "data": {"error": r.get("error")}}
    return {"code": 200, "data": r["accelerator"]}


@router.post("/accelerators/refresh/all")
def accelerator_refresh_all():
    """P5：手动触发全部到期加速器刷新。"""
    from app.services import engine_accelerator
    return {"code": 200, "data": engine_accelerator.refresh_due_all()}
