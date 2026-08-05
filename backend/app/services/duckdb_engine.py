# -*- coding: utf-8 -*-
"""DuckDB 多源API联邦查询引擎（配置驱动 + sqlglot 下推 + register DataFrame）

设计背景
========
DuckDB Python 1.5.x 不支持自定义 UDTF（表函数），create_function 只支持标量函数。
故采用"后端编排"模式：
  1. sqlglot 解析用户 SQL，提取涉及的表名 + WHERE 常量条件 + JOIN 等值条件
  2. 推导下推参数（WHERE 直接下推 + JOIN 传递 WHERE 值）
  3. 对每个表调 API（带下推参数）-> pandas DataFrame
  4. con.register(table_name, df) 注册为 DuckDB 临时表
  5. 执行原 SQL（DuckDB 内存 JOIN/聚合/过滤）

加新 API 零改代码：只在配置界面录入 meta（table_name/api_url/params/columns/data_path）。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import pandas as pd
import requests
import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

_conn: Optional[duckdb.DuckDBPyConnection] = None


def get_conn() -> duckdb.DuckDBPyConnection:
    """DuckDB 单例连接（内存库 + 可选 ATTACH PostgreSQL/Doris，跨源联邦）

    ATTACH PostgreSQL: physical_table 对象查 pg.表名（实体业务数据已迁 PG）
    ATTACH Doris: sql_integration 对象数据查 doris.视图/表
    API 虚拟表: register DataFrame（已有）

    注意：DuckDB 的 INSTALL <ext> 会联网下载扩展，本机网络环境下会长时间挂起。
    故这里只查 duckdb_extensions()，仅当扩展【已安装】时才 LOAD+ATTACH；
    未安装则跳过（不调 INSTALL），保证单源 API 预览（register DataFrame + SELECT）不被阻塞。
    跨对象 JOIN（pg.物理表）需先用 `FORCE INSTALL postgres` 装好扩展才可用。
    """
    import os
    global _conn
    if _conn is None:
        _conn = duckdb.connect(":memory:")

        def _ext_installed(name: str) -> bool:
            try:
                row = _conn.execute(
                    "SELECT count(*) FROM duckdb_extensions() WHERE extension_name=? AND installed=true",
                    [name],
                ).fetchone()
                return bool(row and row[0])
            except Exception:
                return False

        # PostgreSQL（pg.物理表 跨源JOIN）
        try:
            if _ext_installed("postgres"):
                _conn.execute("LOAD postgres;")
                _pg_host = os.getenv("TUPU_PG_HOST", "localhost")
                _pg_port = os.getenv("TUPU_PG_PORT", "5432")
                _pg_user = os.getenv("TUPU_PG_USER", "postgres")
                _pg_pwd = os.getenv("TUPU_PG_PASSWORD", "postgres")
                _pg_db = os.getenv("TUPU_PG_DB", "tupu")
                _conn.execute(
                    f"ATTACH 'host={_pg_host} port={_pg_port} user={_pg_user} password={_pg_pwd} db={_pg_db}' AS pg (TYPE postgres)"
                )
                logger.info("[DuckDB] ATTACH PostgreSQL 成功（physical_table 对象可查 pg.表名）")
            else:
                logger.warning("[DuckDB] postgres 扩展未安装，跳过 ATTACH pg（跨对象JOIN暂不可用，单源API预览不受影响）")
        except Exception as e:
            logger.warning(f"[DuckDB] ATTACH PostgreSQL 失败: {e}")

        # Doris（doris.视图 跨源JOIN，容器未起或扩展缺失时 graceful skip）
        try:
            if _ext_installed("mysql"):
                _conn.execute("LOAD mysql;")
                _conn.execute("ATTACH 'host=localhost port=9030 user=root' AS doris (TYPE mysql)")
                logger.info("[DuckDB] ATTACH Doris 成功（sql_integration 对象可查 doris.表名）")
            else:
                logger.warning("[DuckDB] mysql 扩展未安装，跳过 ATTACH doris")
        except Exception as e:
            logger.warning(f"[DuckDB] ATTACH Doris 失败: {e}")
    return _conn


def _get_nested(d: Any, path: str) -> Any:
    """按点号路径逐层取嵌套字典值（支持 ES 响应的 _source.col 这类 json_path）。"""
    cur = d
    for k in str(path).split("."):
        if isinstance(cur, dict):
            cur = cur.get(k)
        else:
            return None
    return cur


# --------------------------------------------------------------------------- #
# 通用 API 调用（所有 endpoint 共用，配置驱动）
# --------------------------------------------------------------------------- #

def _call_api(meta: Dict[str, Any], filters: Dict[str, Any]) -> pd.DataFrame:
    """通用 API 调用。meta=endpoint配置, filters=下推参数值{column: value}

    返回 pandas DataFrame，列名=meta.columns[].name。
    支持三种 API 形态：
      - 传统 REST：filters 拼进 URL query（params 配置）
      - ES _search：POST body_template（query DSL），filters 暂不下推（DuckDB 内存过滤）
      - 嵌套响应：json_path 支持点号（如 _source.col）
    """
    import json as _json
    url = meta["api_url"]
    method = (meta.get("method") or "POST").upper()
    cols: List[str] = [c["name"] for c in meta.get("columns") or []]
    json_paths: List[str] = [c["json_path"] for c in meta.get("columns") or []]

    # 按 params 配置把 filters 拼进 URL query
    query_parts = []
    for p in meta.get("params") or []:
        col = p["column"]
        if col in filters and filters[col] is not None:
            query_parts.append(f"{p['name']}={filters[col]}")
    if query_parts:
        url += ("&" if "?" in url else "?") + "&".join(query_parts)

    headers = meta.get("headers") or {}
    # POST 请求体：优先用 body_template（如 ES _search 的 query DSL），否则空 body
    body: Any = {}
    if method != "GET" and meta.get("body_template"):
        try:
            body = _json.loads(meta["body_template"])
        except Exception as e:
            logger.warning(f"[DuckDB] body_template 解析失败，回退空 body: {e}")
            body = {}
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=30)
        else:
            resp = requests.post(url, json=body, headers=headers, timeout=30)
        data = resp.json()
    except Exception as e:
        logger.error(f"[DuckDB] API调用失败 {url}: {e}")
        return pd.DataFrame(columns=cols)

    # 按 data_path 逐层提取列表（如 "data.TABLES.PROJECT_DEFINITION" 或 "hits.hits"）
    if meta.get("data_path"):
        for k in str(meta["data_path"]).split("."):
            data = data.get(k, []) if isinstance(data, dict) else data

    # 解析行数据（json_path 支持点号嵌套，如 _source.col）
    rows: List[List[Any]] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                rows.append([_get_nested(item, jp) for jp in json_paths])
            else:
                rows.append([None] * len(json_paths))
    return pd.DataFrame(rows, columns=cols) if cols else pd.DataFrame()


# --------------------------------------------------------------------------- #
# sqlglot 解析：提取表名 + WHERE 常量 + JOIN 等值，推导下推参数
# --------------------------------------------------------------------------- #

def _parse_sql_tables_and_filters(sql: str) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
    """解析 SQL，返回 (表名映射, 每表的下推参数)

    表名映射: {alias_or_name: real_table_name}
    下推参数: {table_name: {param_column: value}}，含 WHERE 直接条件 + JOIN 传递的值
    """
    ast = sqlglot.parse_one(sql)
    # 表名/别名 -> 真实表名
    tables: Dict[str, str] = {}
    for t in ast.find_all(exp.Table):
        real = t.name
        tables[t.alias or t.name] = real
        tables[real] = real

    where_filters: Dict[str, Dict[str, Any]] = {}

    def _record(tbl_key: str, col_name: str, value: Any):
        tbl = tables.get(tbl_key) or tables.get(col_name)
        if tbl:
            where_filters.setdefault(tbl, {})[col_name] = value

    # WHERE 常量等值条件 col = 'value'
    for cond in ast.find_all(exp.EQ):
        l, r = cond.this, cond.expression
        col, lit = None, None
        if isinstance(l, exp.Column) and isinstance(r, exp.Literal):
            col, lit = l, r
        elif isinstance(r, exp.Column) and isinstance(l, exp.Literal):
            col, lit = r, l
        if col and lit:
            _record(col.table or col.name, col.name, lit.this)

    # JOIN 等值条件：col1 = col2，把一侧已知的 WHERE 值传递给另一侧
    for j in ast.find_all(exp.Join):
        on = j.args.get("on")
        if not (on and isinstance(on, exp.EQ)):
            continue
        l, r = on.this, on.expression
        if isinstance(l, exp.Column) and isinstance(r, exp.Column):
            l_tbl = tables.get(l.table or l.name)
            r_tbl = tables.get(r.table or r.name)
            if l_tbl and r_tbl:
                # l 的值传给 r，r 的值传给 l
                if col_val := where_filters.get(l_tbl, {}).get(l.name):
                    where_filters.setdefault(r_tbl, {})[r.name] = col_val
                if col_val := where_filters.get(r_tbl, {}).get(r.name):
                    where_filters.setdefault(l_tbl, {})[l.name] = col_val

    return tables, where_filters


# --------------------------------------------------------------------------- #
# 联邦查询执行
# --------------------------------------------------------------------------- #

def build_sql_with_filters(pseudo_sql: str, filters: Dict[str, Any]) -> str:
    """把 filters 转成 WHERE 加到 pseudo_sql（SELECT 别名映射为原列名，确保 sqlglot 能下推）"""
    if not filters:
        return pseudo_sql
    alias_map = {}
    try:
        _ast = sqlglot.parse_one(pseudo_sql)
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
        return f"{pseudo_sql} WHERE " + " AND ".join(where_parts)
    return pseudo_sql


def execute_sql(sql: str, endpoints_by_table: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """执行多源API联邦SQL。

    Args:
        sql: 用户SQL，如 SELECT * FROM dim_ps_project_def p JOIN dim_ps_wbs_element w ON ...
        endpoints_by_table: {table_name: endpoint配置dict}（含 api_url/method/params/columns/data_path/headers）

    Returns:
        {columns, rows, row_count, pushed_down} 推到API的参数也回传便于调试
    """
    conn = get_conn()
    tables, where_filters = _parse_sql_tables_and_filters(sql)
    pushed_down: Dict[str, Dict[str, Any]] = {}

    # 对每个涉及的 API 表，调 API + register DataFrame
    registered: List[str] = []
    for _alias, tbl_name in tables.items():
        if tbl_name not in endpoints_by_table or tbl_name in registered:
            continue
        ep = endpoints_by_table[tbl_name]
        meta = {
            "api_url": ep["api_url"], "method": ep.get("method", "POST"),
            "params": ep.get("params") or [], "columns": ep.get("columns") or [],
            "data_path": ep.get("data_path"), "headers": ep.get("headers"),
            "body_template": ep.get("body_template"),
        }
        filters = where_filters.get(tbl_name, {})
        df = _call_api(meta, filters)
        conn.register(tbl_name, df)
        registered.append(tbl_name)
        if filters:
            pushed_down[tbl_name] = filters
            logger.info(f"[DuckDB] 表 {tbl_name} 下推参数: {filters}，取回 {len(df)} 行")
        else:
            logger.info(f"[DuckDB] 表 {tbl_name} 无下推参数（全量），取回 {len(df)} 行")

    # 执行原 SQL（DuckDB 内存 JOIN/聚合/过滤）
    cur = conn.execute(sql)
    columns = [d[0] for d in cur.description]
    rows = cur.fetchall()
    return {"columns": columns, "rows": [list(r) for r in rows], "row_count": len(rows),
            "pushed_down": pushed_down}


def test_endpoint(ep: Dict[str, Any], limit: int = 10) -> Dict[str, Any]:
    """单端点测试（无参全量拉，返前 limit 行）"""
    meta = {
        "api_url": ep["api_url"], "method": ep.get("method", "POST"),
        "params": ep.get("params") or [], "columns": ep.get("columns") or [],
        "data_path": ep.get("data_path"), "headers": ep.get("headers"),
        "body_template": ep.get("body_template"),
    }
    df = _call_api(meta, {})
    rows = df.head(limit).values.tolist()
    return {"columns": list(df.columns), "rows": rows, "row_count": len(rows)}


# --------------------------------------------------------------------------- #
# 从 DB 加载所有 endpoint 配置
# --------------------------------------------------------------------------- #

def load_endpoints_from_db(db) -> Dict[str, Dict[str, Any]]:
    """从数据库加载所有 ApiEndpoint，返回 {table_name: 配置dict}"""
    from app.models.base import ApiEndpoint
    out: Dict[str, Dict[str, Any]] = {}
    try:
        for ep in db.query(ApiEndpoint).all():
            out[ep.table_name] = {
                "id": ep.id, "name": ep.name, "table_name": ep.table_name,
                "entity_id": ep.entity_id, "api_url": ep.api_url, "method": ep.method,
                "params": ep.params, "columns": ep.columns, "data_path": ep.data_path,
                "headers": ep.headers, "body_template": ep.body_template,
                "description": ep.description,
            }
    except Exception as e:
        logger.error(f"[DuckDB] 加载 endpoints 失败: {e}")
    return out
