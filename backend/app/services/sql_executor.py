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
                from sqlalchemy import create_engine
                # 按 db_type 选 driver：postgresql -> psycopg2，其余 -> mysql+pymysql
                if (ds.db_type or "").lower() in ("postgresql", "postgres", "pg"):
                    url = f"postgresql+psycopg2://{ds.username}:{ds.password}@{ds.host}:{ds.port}/{ds.database}"
                else:
                    url = f"mysql+pymysql://{ds.username}:{ds.password}@{ds.host}:{ds.port}/{ds.database}?charset=utf8mb4"
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
    def _execute(sql: str) -> Dict[str, Any]:
        import time as _t
        import json as _json
        from decimal import Decimal
        from datetime import datetime as _dt, date as _date
        _t0 = _t.time()
        try:
            from sqlalchemy import text
            eng = _get_biz_engine(data_source_id=data_source_id)
            with eng.connect() as conn:
                result = conn.execute(text(sql))
                columns = list(result.keys()) if hasattr(result, "keys") else []
                rows = []
                for row in result.fetchall():
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
                return {
                    "columns": columns,
                    "rows": rows,
                    "row_count": len(rows),
                    "exec_time_ms": _elapsed,
                    "data_source": _BIZ_ENGINE_CACHE.get(src_key, ""),
                }
        except Exception as e:
            return {"columns": [], "rows": [], "row_count": 0, "exec_time_ms": 0, "error": str(e)}
    return _execute


# 向后兼容别名（原 data_intelligence_graph._build_execute_query_fn）
_build_execute_query_fn = build_execute_query_fn
