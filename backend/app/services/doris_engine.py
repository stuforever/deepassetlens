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
from typing import Any, Dict, List, Optional

import pymysql
from pymysql.constants import FIELD_TYPE
import sqlglot
from sqlglot import exp

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
                    "charset": cfg.charset,
                    "connect_timeout": cfg.connect_timeout,
                }
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[Doris] 读取 DorisConfig 失败，用默认配置: {e}")
    return dict(_DORIS_CONFIG_DEFAULT)


def get_conn():
    """获取 Doris 连接（Doris 兼容 MySQL 协议，pymysql 可连）"""
    return pymysql.connect(**_load_config())


def _check_ident(name: str) -> str:
    """校验 catalog/标识符名称合法，返回原值或抛 ValueError"""
    if not name or not _IDENT_RE.match(name):
        raise ValueError(f"非法标识符: {name!r}")
    return name


def build_sql_with_filters(sql: str, filters: Dict[str, Any]) -> str:
    """把 filters 转成 WHERE 加到 sql（SELECT 别名映射为原列名，确保下推）

    与 duckdb_engine.build_sql_with_filters 同逻辑（sqlglot 解析 SELECT 别名 -> 原 列名）。
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
    where_parts = [f"{alias_map.get(k, k)}='{v}'" for k, v in filters.items()]
    if where_parts:
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
    final_sql = f"SELECT * FROM ({sql}) t LIMIT {limit}" if limit > 0 else sql
    conn = get_conn()
    try:
        cur = conn.cursor()
        if catalog:
            _check_ident(catalog)
            cur.execute(f"SWITCH {catalog}")
        cur.execute(final_sql)
        columns = [d[0] for d in cur.description] if cur.description else []
        rows = [list(r) for r in cur.fetchall()]
        return {"columns": columns, "rows": rows, "row_count": len(rows)}
    except Exception as e:
        logger.error(f"[Doris] SQL执行失败: {e}")
        return {"columns": [], "rows": [], "row_count": 0, "error": str(e)}
    finally:
        conn.close()


def describe_sql_columns(sql: str, catalog: Optional[str] = None) -> List[Dict[str, str]]:
    """获取 SQL 输出列的列名+类型（执行 LIMIT 0 不取数据）

    用于 AI 字段校验：拿到输出列 name + pymysql 类型名，与实体 properties_schema 对比。
    与 execute_sql 分离，不影响现有 verify 的 columns 返回格式。
    """
    sql = sql.strip().rstrip(';').strip()
    final_sql = f"SELECT * FROM ({sql}) t LIMIT 0"
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
                   driver_class: str, driver_url: str) -> Dict[str, Any]:
    """创建 Doris jdbc catalog（DROP IF EXISTS + CREATE CATALOG）

    Returns: {"ok": True} 或 {"ok": False, "error": ...}
    """
    _check_ident(name)
    try:
        conn = get_conn()
    except Exception as e:
        return {"ok": False, "error": f"Doris 连接失败: {e}"}
    try:
        cur = conn.cursor()
        cur.execute(f"DROP CATALOG IF EXISTS {name}")
        cur.execute(
            f"CREATE CATALOG {name} PROPERTIES (\n"
            f'  "type"="jdbc",\n'
            f'  "user"="{jdbc_user}",\n'
            f'  "password"="{jdbc_password}",\n'
            f'  "jdbc_url"="{jdbc_url}",\n'
            f'  "driver_class"="{driver_class}",\n'
            f'  "driver_url"="{driver_url}"\n'
            f")"
        )
        return {"ok": True}
    except Exception as e:
        logger.error(f"[Doris] CREATE CATALOG {name} 失败: {e}")
        return {"ok": False, "error": str(e)}
    finally:
        conn.close()


def drop_catalog(name: str) -> Dict[str, Any]:
    """删除 Doris catalog"""
    _check_ident(name)
    try:
        conn = get_conn()
    except Exception as e:
        return {"ok": False, "error": f"Doris 连接失败: {e}"}
    try:
        cur = conn.cursor()
        cur.execute(f"DROP CATALOG IF EXISTS {name}")
        return {"ok": True}
    except Exception as e:
        logger.error(f"[Doris] DROP CATALOG {name} 失败: {e}")
        return {"ok": False, "error": str(e)}
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
