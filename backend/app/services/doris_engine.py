# -*- coding: utf-8 -*-
"""Doris 执行引擎（sql_integration 模式 + 跨对象整合）

职责：
- 单对象 sql_integration 取数（执行 integration_sql，可指定 catalog）
- 多对象整合（有 sql 无 api）：Doris JOIN（物理表用 mysql_tupu catalog，sql对象用 integration_sql 子查询）
- 连接：从 kg_doris_config 表读取（无则用默认 localhost:9030 root 无密码）
- Catalog 管理：list_catalogs / create_catalog / drop_catalog
- filters 下推：build_sql_with_filters（sqlglot 别名映射，与 duckdb_engine 同逻辑）

对应设计文档第一阶段 sql_integration + 第二阶段"有 sql 无 api"场景。
"""
from __future__ import annotations

import logging
import re
import threading
from typing import Any, Dict, List, Optional

import pymysql
from pymysql.constants import FIELD_TYPE
import sqlglot
from sqlglot import exp

from app.services.engine_errors import apply_error_class, wrap_engine_exception

# pymysql 类型代码 -> 可读类型名（供 AI 字段校验对比类型用）
_TYPE_NAME = {v: k for k, v in FIELD_TYPE.__dict__.items() if isinstance(v, int)}
# Doris 经 MySQL 协议返回的 type_code 与标准 MySQL 有差异：
# Doris 的 STRING/VARCHAR 列返回 252（pymysql 标记为 BLOB），实际是字符串，修正为 VARCHAR
_TYPE_NAME[252] = "VARCHAR"

logger = logging.getLogger(__name__)

# Doris 连接默认配置（Docker 部署，9030 MySQL 协议，root 无密码）
# 当 kg_doris_config 表无记录时使用；否则用 DB 中首行配置
_DORIS_CONFIG_DEFAULT = {
    "host": "localhost",
    "port": 9030,
    "user": "root",
    "password": "",
    "database": "test_db",
    "charset": "utf8mb4",
    "connect_timeout": 10,
}

# catalog/标识符名称合法校验（防 SQL 注入）
_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _load_config() -> dict:
    """从 DB 读 DorisConfig 首行，无则返回默认配置"""
    try:
        from app.models.base import DorisConfig
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            cfg = db.query(DorisConfig).first()
            if cfg:
                return {
                    "host": cfg.host,
                    "port": cfg.port,
                    "user": cfg.user,
                    "password": cfg.password,
                    "database": cfg.database or "test_db",
                    "charset": cfg.charset,
                    "connect_timeout": cfg.connect_timeout,
                }
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[Doris] 读取 DorisConfig 失败，用默认配置: {e}")
    return dict(_DORIS_CONFIG_DEFAULT)


# --------------------------------------------------------------------------- #
# 连接池（批1：复用 SQLAlchemy，零新依赖；替代每次裸 pymysql.connect）
# --------------------------------------------------------------------------- #

_ENGINE = None
_ENGINE_LOCK = threading.Lock()

# Doris 查询超时（秒）：Doris 原生 query_timeout 会话级 hint，超时由 Doris 侧 kill 查询
_DORIS_QUERY_TIMEOUT = 60


def _pool():
    """模块级懒加载 SQLAlchemy 连接池（pool_pre_ping + recycle 防陈旧连接）。"""
    global _ENGINE
    if _ENGINE is None:
        with _ENGINE_LOCK:
            if _ENGINE is None:
                from sqlalchemy import create_engine
                c = _load_config()
                _ENGINE = create_engine(
                    f"mysql+pymysql://{c['user']}:{c['password']}@{c['host']}:{c['port']}/{c['database']}"
                    f"?charset={c.get('charset', 'utf8mb4')}&connect_timeout={c.get('connect_timeout', 10)}",
                    pool_size=3, max_overflow=3, pool_pre_ping=True, pool_recycle=1800,
                )
    return _ENGINE


def reset_pool():
    """关闭连接池并清空（DorisConfig 保存后调用，下次查询用新配置重建）。"""
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is not None:
            try:
                _ENGINE.dispose()
            except Exception as e:
                logger.warning(f"[Doris] dispose 连接池失败: {e}")
            _ENGINE = None


def get_conn():
    """获取 Doris 连接（从连接池借出底层 pymysql 连接，close() 归还池）。

    Doris 兼容 MySQL 协议；raw_connection() 返回的 PoolProxiedConnection
    代理底层 pymysql.Connection，cursor()/description/fetchall 等用法不变。
    """
    return _pool().raw_connection()


def _with_query_timeout(sql: str) -> str:
    """给 SQL 包一层 Doris 执行超时 hint（查询超时由 Doris 侧 kill）。

    仅对无 LIMIT 约束的裸查询包装（已带 LIMIT 的执行入口不再包，避免语义意外）；
    包装为 SELECT * FROM (原SQL) t，对只读 SELECT 等价。
    """
    s = sql.strip().rstrip(';').strip()
    low = s.lower()
    # 顶层是否已带 LIMIT（粗判：末尾 LIMIT n / 含 LIMIT 且非子查询内）——保守起见一律包装，
    # 因为外层 SELECT * FROM (...) t 对 Doris 合法，且 hint 只影响超时不影响语义。
    return f"SELECT /*+ SET_VAR(query_timeout={_DORIS_QUERY_TIMEOUT}) */ * FROM ({s}) t"


def _check_ident(name: str) -> str:
    """校验 catalog/标识符名称合法，返回原值或抛 ValueError"""
    if not name or not _IDENT_RE.match(name):
        raise ValueError(f"非法标识符: {name!r}")
    return name


def build_sql_with_filters(sql: str, filters: Dict[str, Any]) -> str:
    """把 filters 转成 WHERE 加到 sql（SELECT 别名映射为原列名，确保下推）

    与 duckdb_engine.build_sql_with_filters 同逻辑（sqlglot 解析 SELECT 别名 -> 原 列名）。
    F1-fix: 用 sqlglot AST 构造 WHERE 条件（exp.Literal.string 转义单引号），
    替代字符串拼接 f"{col}='{v}'"，防止 filter value 注入。
    """
    if not filters:
        return sql
    alias_map = {}
    try:
        _ast = sqlglot.parse_one(sql)
        for sel in _ast.expressions:
            if isinstance(sel, exp.Alias):
                col = sel.this
                if isinstance(col, exp.Column):
                    alias_map[sel.alias] = f"{col.table}.{col.name}" if col.table else col.name
            elif isinstance(sel, exp.Column):
                alias_map[sel.name] = f"{sel.table}.{sel.name}" if sel.table else sel.name
    except Exception:
        pass
    # F1-fix: 用 sqlglot AST 构造 WHERE 条件，exp.Literal.string 自动转义单引号
    where_conds = []
    for k, v in filters.items():
        col_name = alias_map.get(k, k)
        if "." in col_name:
            tbl, cname = col_name.split(".", 1)
            col_expr = exp.column(cname, table=tbl)
        else:
            col_expr = exp.column(col_name)
        lit_expr = exp.Literal.string(str(v))
        where_conds.append(exp.EQ(this=col_expr, expression=lit_expr))
    if where_conds:
        try:
            _ast = sqlglot.parse_one(sql)
            for cond in where_conds:
                _ast = _ast.where(cond)
            return _ast.sql()
        except Exception:
            where_parts = [f"{alias_map.get(k, k)}='{str(v).replace(chr(39), chr(39)+chr(39))}'"
                           for k, v in filters.items()]
            return f"{sql} WHERE " + " AND ".join(where_parts)
    return sql


def execute_sql(sql: str, limit: int = 0, catalog: Optional[str] = None) -> Dict[str, Any]:
    """执行 Doris SQL，返回 columns/rows/row_count

    Args:
        sql: Doris SQL（integration_sql 或跨对象 JOIN SQL）
        limit: 限制返回行数（0=不限制，>0 用子查询包装 LIMIT）
        catalog: 执行前 SWITCH 到该 catalog（None=不切换，SQL 用 3 段命名 mysql_tupu.tupu.table）
    """
    sql = sql.strip().rstrip(';').strip()  # 去末尾分号:用户拷贝SQL常带分号,子查询包装会语法错误
    # P5：预聚合加速器拦截（同形单值聚合 -> 预聚合表服务，附数据截至标注）
    try:
        from app.services.engine_accelerator import try_serve
        served = try_serve(sql)
        if served is not None:
            return served
    except Exception:
        pass
    final_sql = f"SELECT * FROM ({sql}) t LIMIT {limit}" if limit > 0 else sql
    final_sql = _with_query_timeout(final_sql)
    import time as _time
    _t0 = _time.time()
    conn = get_conn()
    result: Dict[str, Any]
    try:
        cur = conn.cursor()
        if catalog:
            _check_ident(catalog)
            cur.execute(f"SWITCH {catalog}")
        cur.execute(final_sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = [list(r) for r in cur.fetchall()]
        result = {"columns": columns, "rows": rows, "row_count": len(rows)}
    except Exception as e:
        logger.error(f"[Doris] SQL执行失败: {e}")
        result = apply_error_class({"columns": [], "rows": [], "row_count": 0, "error": str(e)})
    finally:
        conn.close()
    # 批1：查询日志（异常不影响主流程）
    try:
        from app.services.engine_query_log import record_query_log
        record_query_log(
            "doris", final_sql,
            rows_returned=result.get("row_count", 0),
            duration_ms=int((_time.time() - _t0) * 1000),
            status="error" if result.get("error") else "ok",
            error_class=result.get("error_class"),
        )
    except Exception:
        pass
    return result


def describe_sql_columns(sql: str, catalog: Optional[str] = None) -> List[Dict[str, str]]:
    """获取 SQL 输出列的列名+类型（执行 LIMIT 0 不取数据）

    用于 AI 字段校验：拿到输出列 name + pymysql 类型名，与实体 properties_schema 对比。
    与 execute_sql 分离，不影响现有 verify 的 columns 返回格式。
    """
    sql = sql.strip().rstrip(';').strip()
    final_sql = _with_query_timeout(f"SELECT * FROM ({sql}) t LIMIT 0")
    conn = get_conn()
    try:
        cur = conn.cursor()
        if catalog:
            _check_ident(catalog)
            cur.execute(f"SWITCH {catalog}")
        cur.execute(final_sql)
        if not cur.description:
            return []
        return [{"name": d[0], "type": _TYPE_NAME.get(d[1], f"UNKNOWN({d[1]})")} for d in cur.description]
    except Exception as e:
        logger.error(f"[Doris] 获取列信息失败: {e}")
        return []
    finally:
        conn.close()


def test_integration_sql(sql: str, catalog: Optional[str] = None) -> Dict[str, Any]:
    """验证 integration_sql（执行，限100行）"""
    return execute_sql(sql, limit=100, catalog=catalog)


def execute_with_filters(sql: str, filters: Optional[Dict[str, Any]] = None,
                         catalog: Optional[str] = None) -> Dict[str, Any]:
    """执行 SQL + filters 下推（build_sql_with_filters 加 WHERE）"""
    final_sql = build_sql_with_filters(sql, filters or {})
    return execute_sql(final_sql, catalog=catalog)


# --------------------------------------------------------------------------- #
# Catalog 管理（jdbc 联邦）
# --------------------------------------------------------------------------- #

def list_catalogs() -> List[Dict[str, Any]]:
    """SHOW CATALOGS，返回 [{name, type, comment}]；Doris 不可达时返回 []"""
    try:
        conn = get_conn()
    except Exception as e:
        logger.error(f"[Doris] SHOW CATALOGS 连接失败: {e}")
        return []
    try:
        cur = conn.cursor()
        cur.execute("SHOW CATALOGS")
        rows = cur.fetchall()
        # 列序: CatalogId | CatalogName | Type | IsCurrent | CreateTime | LastUpdateTime | Comment
        return [
            {
                "name": r[1],
                "type": r[2] if len(r) > 2 else "",
                "comment": r[6] if len(r) > 6 else "",
            }
            for r in rows
        ]
    except Exception as e:
        logger.error(f"[Doris] SHOW CATALOGS 失败: {e}")
        return []
    finally:
        conn.close()


def create_catalog(name: str, jdbc_url: str, jdbc_user: str, jdbc_password: str,
                   driver_class: str, driver_url: str, catalog_type: str = "jdbc",
                   es_hosts: str = "", es_user: str = "", es_password: str = "") -> Dict[str, Any]:
    """创建 Doris catalog（DROP IF EXISTS + CREATE CATALOG）

    catalog_type: jdbc（标准 JDBC 联邦）| es（Elasticsearch 联邦）| internal（内部库，仅作标记不建）
    Returns: {"ok": True} 或 {"ok": False, "error": ..., "error_class": ...}
    """
    if catalog_type == "internal":
        return {"ok": True, "note": "internal 为 Doris 内置 catalog，无需创建"}
    _check_ident(name)
    try:
        conn = get_conn()
    except Exception as e:
        return {"ok": False, **apply_error_class({"error": f"Doris 连接失败: {e}"})}
    try:
        cur = conn.cursor()
        cur.execute(f"DROP CATALOG IF EXISTS {name}")
        if catalog_type == "es":
            # ES 联邦 catalog：hosts 可逗号分隔多个地址；user/password 可选（无鉴权留空）
            props = [f'  "type"="es"', f'  "hosts"="{es_hosts}"']
            if es_user:
                props.append(f'  "user"="{es_user}"')
            if es_password:
                props.append(f'  "password"="{es_password}"')
            ddl = f"CREATE CATALOG {name} PROPERTIES (\n" + ",\n".join(props) + "\n)"
        else:
            ddl = (
                f"CREATE CATALOG {name} PROPERTIES (\n"
                f'  "type"="jdbc",\n'
                f'  "user"="{jdbc_user}",\n'
                f'  "password"="{jdbc_password}",\n'
                f'  "jdbc_url"="{jdbc_url}",\n'
                f'  "driver_class"="{driver_class}",\n'
                f'  "driver_url"="{driver_url}"\n'
                f")"
            )
        cur.execute(ddl)
        return {"ok": True}
    except Exception as e:
        logger.error(f"[Doris] CREATE CATALOG {name} 失败: {e}")
        return {"ok": False, **apply_error_class({"error": str(e)})}
    finally:
        conn.close()


def probe_catalog(name: str) -> Dict[str, Any]:
    """探活 catalog：SHOW DATABASES FROM {name}，返回可见数据库列表。

    Returns: {"ok": True, "databases": [...], "tables": N} 或 {"ok": False, ...}
    """
    _check_ident(name)
    try:
        conn = get_conn()
    except Exception as e:
        return {"ok": False, **apply_error_class({"error": f"Doris 连接失败: {e}"})}
    try:
        cur = conn.cursor()
        cur.execute(f"SHOW DATABASES FROM {name}")
        dbs = [str(r[0]) for r in cur.fetchall()]
        # 采样首库表数量，佐证可查询
        tables = 0
        if dbs:
            try:
                cur.execute(f"SHOW TABLES FROM {name}.`{dbs[0]}`")
                tables = len(cur.fetchall())
            except Exception:
                tables = -1   # 库无表或不可见，不影响探活结论
        return {"ok": True, "databases": dbs, "sample_db": dbs[0] if dbs else None, "sample_tables": tables}
    except Exception as e:
        logger.error(f"[Doris] PROBE CATALOG {name} 失败: {e}")
        return {"ok": False, **apply_error_class({"error": str(e)})}
    finally:
        conn.close()


def refresh_catalog(name: str) -> Dict[str, Any]:
    """刷新外部 catalog 元数据：REFRESH CATALOG {name}（es/jdbc 元数据缓存重建）。"""
    _check_ident(name)
    try:
        conn = get_conn()
    except Exception as e:
        return {"ok": False, **apply_error_class({"error": f"Doris 连接失败: {e}"})}
    try:
        cur = conn.cursor()
        cur.execute(f"REFRESH CATALOG {name}")
        return {"ok": True}
    except Exception as e:
        logger.error(f"[Doris] REFRESH CATALOG {name} 失败: {e}")
        return {"ok": False, **apply_error_class({"error": str(e)})}
    finally:
        conn.close()


def drop_catalog(name: str) -> Dict[str, Any]:
    """删除 Doris catalog"""
    _check_ident(name)
    try:
        conn = get_conn()
    except Exception as e:
        return {"ok": False, **apply_error_class({"error": f"Doris 连接失败: {e}"})}
    try:
        cur = conn.cursor()
        cur.execute(f"DROP CATALOG IF EXISTS {name}")
        return {"ok": True}
    except Exception as e:
        logger.error(f"[Doris] DROP CATALOG {name} 失败: {e}")
        return {"ok": False, **apply_error_class({"error": str(e)})}
    finally:
        conn.close()


def test_connection(host: str, port: int, user: str, password: str) -> Dict[str, Any]:
    """测试 Doris 连接（不保存）"""
    try:
        c = pymysql.connect(host=host, port=int(port), user=user, password=password,
                            charset="utf8mb4", connect_timeout=10)
        cur = c.cursor()
        cur.execute("SELECT 1")
        cur.fetchall()
        c.close()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
