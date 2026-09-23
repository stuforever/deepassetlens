"""SQL 执行器（多数据源：优先业务库，回退元数据库）

从原 data_intelligence_graph.py 迁出，供 kg_api / skill_runnable / tupu_deepagent 复用。
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# 业务数据源 engine 缓存（避免每次执行 SQL 都重新建连）
_BIZ_ENGINE_CACHE: Dict[str, Any] = {}


def _get_biz_engine(data_source_id=None):
    """获取业务数据源 engine（支持 per-entity 数据源绑定）。

    - data_source_id 非空：按该 id 查 DataSourceConfig，建独立 engine，缓存 key 含 id
    - data_source_id 为空：优先取 is_default=True 且 enabled=True 的 DataSourceConfig；
      找不到则回退到元数据库 SessionLocal 的 engine
    """
    cache_key = f"engine:{data_source_id}" if data_source_id else "engine:default"
    if cache_key in _BIZ_ENGINE_CACHE:
        return _BIZ_ENGINE_CACHE[cache_key]

    try:
        from app.core.database import SessionLocal
        from app.models.base import DataSourceConfig
        db = SessionLocal()
        try:
            ds = None
            if data_source_id:
                ds = db.query(DataSourceConfig).filter(DataSourceConfig.id == data_source_id).first()
            else:
                ds = db.query(DataSourceConfig).filter(
                    DataSourceConfig.is_default == True,
                    DataSourceConfig.enabled == True,
                ).first()
                if not ds:
                    ds = db.query(DataSourceConfig).filter(DataSourceConfig.enabled == True).first()
            if ds:
                # R5批②（清单安全）：凭证改 URL.create——原 f-string 直拼，username/password
                # 含 @ : / # ? 时破坏 URL 解析（错连主机/库），SQLAlchemy 对凭证自动转义
                from sqlalchemy import create_engine
                from sqlalchemy.engine import URL as _URL
                if (ds.db_type or "").lower() in ("postgresql", "postgres", "pg"):
                    url = _URL.create("postgresql+psycopg2", username=ds.username,
                                      password=ds.password, host=ds.host,
                                      port=ds.port, database=ds.database)
                else:
                    url = _URL.create("mysql+pymysql", username=ds.username,
                                      password=ds.password, host=ds.host,
                                      port=ds.port, database=ds.database,
                                      query={"charset": "utf8mb4"})
                eng = create_engine(url, pool_pre_ping=True, pool_recycle=3600, pool_size=5, max_overflow=10)
                _BIZ_ENGINE_CACHE[cache_key] = eng
                _BIZ_ENGINE_CACHE[f"{cache_key}:source"] = f"{ds.name}({ds.host}:{ds.port}/{ds.database})"
                return eng
        finally:
            db.close()
    except Exception as e:
        logger.debug("get biz engine failed: %s", e)

    # 回退：元数据库 engine（仅 data_source_id 为空时走到这）
    if data_source_id:
        # 指定了 data_source_id 但查不到，不回退元数据库，直接报错避免查错库
        raise RuntimeError(f"数据源不存在或未启用: data_source_id={data_source_id}")
    from app.core.database import engine as _meta_engine
    _BIZ_ENGINE_CACHE[cache_key] = _meta_engine
    _BIZ_ENGINE_CACHE[f"{cache_key}:source"] = "metadata_db(tupu)"
    return _meta_engine


def build_execute_query_fn(data_source_id=None):
    """构造 SQL 执行函数（支持 per-entity 数据源绑定）"""
    src_key = f"engine:{data_source_id}:source" if data_source_id else "engine:default:source"
    MAX_RETURN_ROWS = 500  # 应用层硬限制：不信任 SQL 是否带 LIMIT，fetchmany 强制截断
    def _execute(sql: str) -> Dict[str, Any]:
        import time as _t
        import json as _json
        from decimal import Decimal
        from datetime import datetime as _dt, date as _date
        # R5批②（清单安全）：模块级只读防线——只读性原依赖调用方先过 validate_sql
        # （golden_qa_service 等调用径实测未过，注释声明不成立），此处统一强制 AST 校验。
        try:
            from app.services.secure_query_executor import validate_sql as _vsql
            _chk = _vsql(sql)
        except Exception as _ve:
            raise ValueError(f"SQL 只读校验异常: {_ve}")
        if not _chk.ok:
            raise ValueError(f"SQL 校验未通过: {_chk.reason}")
        sql = _chk.sql or sql
        _t0 = _t.time()
        # P5：预聚合加速器拦截（同形单值聚合命中 -> 预聚合表服务，附数据截至标注）
        try:
            from app.services.engine_accelerator import try_serve
            served = try_serve(sql)
            if served is not None:
                served.setdefault("exec_time_ms", int((_t.time() - _t0) * 1000))
                return served
        except Exception:
            pass
        try:
            from sqlalchemy import text
            eng = _get_biz_engine(data_source_id=data_source_id)
            _is_pg = "postgresql" in str(eng.url)
            _is_mysql = "mysql" in str(eng.url)
            with eng.connect() as conn:
                # P0-2: 查询超时（PG 用 statement_timeout，MySQL 用 MAX_EXECUTION_TIME hint）
                if _is_pg:
                    conn.execute(text("SET LOCAL statement_timeout = '30s'"))
                elif _is_mysql:
                    # MySQL 5.7.4+ / 8.0+ 支持 MAX_EXECUTION_TIME(ms)，注入到 SELECT 前
                    # 仅对单条 SELECT 生效；已通过 validate_sql 确保是只读 SELECT
                    sql = f"/*+ MAX_EXECUTION_TIME(30000) */ {sql}"
                result = conn.execute(text(sql))
                columns = list(result.keys()) if hasattr(result, "keys") else []
                # fetchmany 多取1行用于判断是否截断，不信任 SQL 自带 LIMIT
                raw_rows = result.fetchmany(MAX_RETURN_ROWS + 1)
                truncated = len(raw_rows) > MAX_RETURN_ROWS
                rows = []
                for row in (raw_rows[:MAX_RETURN_ROWS] if truncated else raw_rows):
                    clean_row = []
                    for v in row:
                        if isinstance(v, Decimal):
                            clean_row.append(float(v))
                        elif isinstance(v, (_dt, _date)):
                            clean_row.append(v.isoformat())
                        elif v is None:
                            clean_row.append("")
                        else:
                            clean_row.append(v)
                    rows.append(clean_row)
                _elapsed = int((_t.time() - _t0) * 1000)
                _row_count = len(rows)
                result = {
                    "columns": columns,
                    "rows": rows,
                    "row_count": _row_count,
                    "truncated": truncated,
                    "total_hint": f">{MAX_RETURN_ROWS}" if truncated else str(_row_count),
                    "exec_time_ms": _elapsed,
                    "data_source": _BIZ_ENGINE_CACHE.get(src_key, ""),
                }
        except Exception as e:
            from app.services.engine_errors import apply_error_class
            result = apply_error_class(
                {"columns": [], "rows": [], "row_count": 0, "truncated": False,
                 "exec_time_ms": 0, "error": str(e)}
            )
        # 批1：查询日志（异常不影响主流程）
        try:
            from app.services.engine_query_log import record_query_log
            record_query_log(
                "sql", sql,
                rows_returned=result.get("row_count", 0),
                duration_ms=int((_t.time() - _t0) * 1000),
                status="error" if result.get("error") else "ok",
                error_class=result.get("error_class"),
            )
        except Exception:
            pass
        return result
    return _execute


# 向后兼容别名（原 data_intelligence_graph._build_execute_query_fn）
_build_execute_query_fn = build_execute_query_fn
