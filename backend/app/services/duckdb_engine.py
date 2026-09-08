# -*- coding: utf-8 -*-
"""DuckDB 多源API联邦查询引擎（配置驱动 + sqlglot 下推 + register DataFrame）

设计背景
========
DuckDB Python 1.5.x 不支持自定义 UDTF（表函数），create_function 只支持标量函数。
故采用"后端编排"模式：
  1. sqlglot 解析用户 SQL，提取涉及的表名 + WHERE 常量条件 + JOIN 等值条件 + IN 条件
  2. 推导下推参数（WHERE 直接下推 + JOIN 传递 WHERE 值 + IN 数组）
  3. 对每个表调 API（带下推参数）-> pandas DataFrame
  4. con.register(table_name, df) 注册为 DuckDB 临时表
  5. 执行原 SQL（DuckDB 内存 JOIN/聚合/过滤）

批1（稳定性）：
  - 串行锁：DuckDB 全局单例连接非线程安全，v1 串行即正确（threading.Lock 跨线程池生效）
  - 内存护栏：memory_limit=2GB / threads=2 / 单端点行数上限 20 万（超限报错）
  - 异步入口 execute_federated_async：asyncio.wait_for + to_thread 双护栏（120s）
  - error_class：API 失败按 6 类结构化返回（CONNECTION/AUTH/TIMEOUT/UPSTREAM_API…）

批2（能力）：
  - API 内存缓存：key=(endpoint_id, 规范化下推参数 sha1)，TTL 默认 300s（0=禁用），
    配置保存即失效，LRU 上限 50；命中返回 data_snapshot_at（数据快照 HH:MM）
  - 类型推断：采样定 dtype 写入 columns[].dtype，register 前 astype（数值 SUM 从此正确）
  - 分页：页码型循环拉取（page_param/size_param/page_size/max_pages），不做 cursor
  - IN 下推：sqlglot exp.In 分支，下推值以数组形式附在 pushed_down 供调试

P3（完整版补全）：
  - 限速/熔断：per-endpoint min_interval_ms 令牌间隔 + 连续失败阈值熔断
    （OPEN 快速失败 / HALF_OPEN 试探 / CLOSED 恢复），状态可观测
  - Pushdown v2：范围（>=/<= 等）与 LIKE 前缀下推 + not_pushed 审计 +
    pushdown_trace（eq/in/range/like 逐列说明，供工作台 Pushdown 调试器）
  - parquet 落盘缓存：DuckDB 原生 COPY TO/read_parquet（零 pyarrow），缓存跨重启持久

加新 API 零改代码：只在配置界面录入 meta（table_name/api_url/params/columns/data_path）。
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

import duckdb
import pandas as pd
import requests
import sqlglot
from sqlglot import exp

from app.services.engine_errors import EngineError, classify_requests_error

logger = logging.getLogger(__name__)

_conn: Optional[duckdb.DuckDBPyConnection] = None
_CONN_LOCK = threading.Lock()   # get_conn 懒初始化串行
_EXEC_LOCK = threading.Lock()   # 联邦执行串行（DuckDB 单例非线程安全）

# 内存护栏
_MEMORY_LIMIT = "2GB"
_THREADS = 2
_MAX_ROWS_PER_ENDPOINT = 200_000   # 单 endpoint 拉取行数硬上限

# --------------------------------------------------------------------------- #
# P3：限速 / 熔断（per-endpoint，默认值可在 endpoint 配置覆盖）
# --------------------------------------------------------------------------- #

_CIRCUIT_THRESHOLD = 5          # 连续失败阈值
_CIRCUIT_OPEN_SECONDS = 60      # OPEN 持续时间
_CIRCUIT_STATE: Dict[str, Dict[str, Any]] = {}   # endpoint_id -> {state,failures,opened_at,last_call}


def _endpoint_key(meta: Dict[str, Any]) -> str:
    return str(meta.get("id") or meta.get("table_name") or "")


def circuit_status(endpoint_id: Optional[str] = None) -> Dict[str, Any]:
    """批3 观测：熔断状态（endpoint_id=None 返回全部）。"""
    if endpoint_id:
        s = _CIRCUIT_STATE.get(endpoint_id)
        return dict(s) if s else {"state": "CLOSED", "failures": 0, "opened_at": None}
    return {k: (dict(v) if v else {"state": "CLOSED", "failures": 0, "opened_at": None})
            for k, v in _CIRCUIT_STATE.items()}


def _enforce_rate_limit(meta: Dict[str, Any]) -> None:
    """限速：min_interval_ms 令牌间隔（0/缺省=不限速）。"""
    ep_key = _endpoint_key(meta)
    try:
        min_interval_ms = int(meta.get("rate_limit_min_interval_ms") or 0)
    except Exception:
        min_interval_ms = 0
    if min_interval_ms <= 0:
        return
    st = _CIRCUIT_STATE.setdefault(ep_key, {"state": "CLOSED", "failures": 0, "opened_at": None})
    last = st.get("last_call") or 0
    gap_ms = (time.time() - last) * 1000
    if gap_ms < min_interval_ms:
        time.sleep((min_interval_ms - gap_ms) / 1000.0)
    st["last_call"] = time.time()


def _check_circuit(meta: Dict[str, Any]) -> None:
    """熔断检查：OPEN 快速失败（不触达上游）；超时自动转 HALF_OPEN 放一次试探。"""
    ep_key = _endpoint_key(meta)
    st = _CIRCUIT_STATE.get(ep_key)
    if not st or st.get("state") != "OPEN":
        return
    try:
        open_seconds = int(meta.get("circuit_open_seconds") or _CIRCUIT_OPEN_SECONDS)
    except Exception:
        open_seconds = _CIRCUIT_OPEN_SECONDS
    opened_at = st.get("opened_at") or 0
    if time.time() - opened_at >= open_seconds:
        st["state"] = "HALF_OPEN"   # 放一次试探请求
        return
    raise EngineError("UPSTREAM_API", f"上游端点已熔断（OPEN {open_seconds}s），快速失败跳过请求",
                      detail=ep_key)


def _record_failure(meta: Dict[str, Any]) -> None:
    """失败计数；达阈值 -> OPEN（记录 opened_at）。"""
    ep_key = _endpoint_key(meta)
    st = _CIRCUIT_STATE.setdefault(ep_key, {"state": "CLOSED", "failures": 0, "opened_at": None})
    st["failures"] = st.get("failures", 0) + 1
    try:
        threshold = int(meta.get("circuit_threshold") or _CIRCUIT_THRESHOLD)
    except Exception:
        threshold = _CIRCUIT_THRESHOLD
    if st["failures"] >= threshold:
        st["state"] = "OPEN"
        st["opened_at"] = time.time()


def _record_success(meta: Dict[str, Any]) -> None:
    """成功复位：CLOSED + failures=0。"""
    ep_key = _endpoint_key(meta)
    st = _CIRCUIT_STATE.setdefault(ep_key, {"state": "CLOSED", "failures": 0, "opened_at": None})
    st["state"] = "CLOSED"
    st["failures"] = 0
    st["opened_at"] = None


# --------------------------------------------------------------------------- #
# 批2：API 内存缓存（(endpoint_id, params_hash) -> (fetched_at, df)，LRU）
# P3：并行 parquet 落盘（DuckDB 原生，跨重启持久）
# --------------------------------------------------------------------------- #

_CACHE: "OrderedDict[Tuple[str, str], Tuple[float, pd.DataFrame]]" = OrderedDict()
_CACHE_MAX = 50
_CACHE_HIT = 0
_CACHE_MISS = 0
_DISK_CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data", "duckdb_cache")


def _stable_repr(v: Any) -> str:
    """值 -> 稳定字符串（list 递归展开，保证同语义不同写法同 key）。"""
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(_stable_repr(x) for x in v) + "]"
    if isinstance(v, bool):
        return "true" if v else "false"
    return str(v)


def _cache_key(endpoint_id: str, filters: Dict[str, Any]) -> str:
    """规范化下推参数 -> sha1 前 8 位（排序后拼接，避免 dict 顺序抖动）。"""
    norm = "&".join(f"{c}={_stable_repr(v)}" for c, v in sorted((filters or {}).items()))
    raw = f"{endpoint_id}|{norm}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:8]


def _parquet_path(endpoint_id: str, params_key: str) -> str:
    """parquet 缓存文件路径（endpoint_id 净化防路径注入）。"""
    import re
    safe = re.sub(r"[^0-9A-Za-z_-]", "_", endpoint_id)
    return os.path.join(_DISK_CACHE_DIR, f"ep_{safe}__{params_key}.parquet")


def _df_to_parquet(df: pd.DataFrame, path: str) -> bool:
    """DuckDB 原生写 parquet（零 pyarrow）。失败仅告警不阻断主流程。"""
    try:
        c = duckdb.connect()
        try:
            c.register("_cache_df", df)
            c.execute(f"COPY (SELECT * FROM _cache_df) TO '{path.replace(chr(39), chr(39)+chr(39))}' (FORMAT PARQUET)")
        finally:
            c.close()
        return True
    except Exception as e:
        logger.warning(f"[DuckDB] parquet 写缓存失败(忽略): {e}")
        return False


def _parquet_to_df(path: str) -> Optional[pd.DataFrame]:
    """DuckDB 原生读 parquet；失败返回 None。"""
    try:
        c = duckdb.connect()
        try:
            return c.execute(f"SELECT * FROM read_parquet('{path.replace(chr(39), chr(39)+chr(39))}')").df()
        finally:
            c.close()
    except Exception as e:
        logger.warning(f"[DuckDB] parquet 读缓存失败: {e}")
        return None


def _cache_get(endpoint_id: str, params_key: str, ttl: int):
    global _CACHE_HIT, _CACHE_MISS
    key = (endpoint_id, params_key)
    entry = _CACHE.get(key)
    if entry is not None:
        fetched_at, df = entry
        if ttl and (time.time() - fetched_at) < ttl:
            _CACHE_HIT += 1
            _CACHE.move_to_end(key)
            return df, fetched_at
        _CACHE.pop(key, None)
    # P3：内存未命中 -> 尝试 parquet 落盘缓存（TTL 按文件 mtime）
    pq = _parquet_path(endpoint_id, params_key)
    if ttl and os.path.exists(pq):
        mtime = os.path.getmtime(pq)
        if (time.time() - mtime) < ttl:
            df = _parquet_to_df(pq)
            if df is not None:
                _CACHE_HIT += 1
                _CACHE[(endpoint_id, params_key)] = (mtime, df)
                _CACHE.move_to_end((endpoint_id, params_key))
                return df, mtime
        else:
            try:
                os.remove(pq)
            except Exception:
                pass
    _CACHE_MISS += 1
    return None


def _cache_put(endpoint_id: str, params_key: str, df: pd.DataFrame) -> None:
    _CACHE[(endpoint_id, params_key)] = (time.time(), df)
    _CACHE.move_to_end((endpoint_id, params_key))
    while len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    # P3：并行落盘 parquet（跨重启持久）；失败仅告警
    try:
        os.makedirs(_DISK_CACHE_DIR, exist_ok=True)
    except Exception:
        pass
    _df_to_parquet(df, _parquet_path(endpoint_id, params_key))


def invalidate_endpoint_cache(endpoint_id: Optional[str] = None) -> int:
    """清缓存：endpoint_id=None 清全部；否则清该 endpoint 全部条目。返回清理条数。

    在 ApiEndpoint 保存/删除、DorisConfig 变更（可能影响数据）后调用。
    内存 + parquet 落盘一并清除。
    """
    removed = []
    if endpoint_id is None:
        removed = list(_CACHE.keys())
        _CACHE.clear()
    else:
        removed = [k for k in list(_CACHE.keys()) if k[0] == endpoint_id]
        for k in removed:
            _CACHE.pop(k, None)
    for (ep_id, key) in removed:
        try:
            pq = _parquet_path(ep_id, key)
            if os.path.exists(pq):
                os.remove(pq)
        except Exception:
            pass
    return len(removed)


def cache_stats() -> Dict[str, Any]:
    """批3 观测：条目数/上限/命中/未命中/落盘条目。"""
    disk_entries = 0
    try:
        if os.path.isdir(_DISK_CACHE_DIR):
            disk_entries = len([f for f in os.listdir(_DISK_CACHE_DIR) if f.endswith(".parquet")])
    except Exception:
        disk_entries = 0
    return {
        "entries": len(_CACHE), "max": _CACHE_MAX,
        "hit": _CACHE_HIT, "miss": _CACHE_MISS,
        "hit_rate": round(_CACHE_HIT / (_CACHE_HIT + _CACHE_MISS), 4) if (_CACHE_HIT + _CACHE_MISS) else 0.0,
        "disk_entries": disk_entries,
    }


# --------------------------------------------------------------------------- #
# 类型推断（批2）：采样定 dtype -> 写入 columns[].dtype；register 前 astype
# --------------------------------------------------------------------------- #

def infer_dtypes(df: pd.DataFrame) -> Dict[str, str]:
    """采样定 dtype（数据已全量在内存，直接按 pandas 类型推断）。

    返回 {列名: pandas dtype 字符串}：
    - 数值列（含 API 返回的字符串数字）-> int64 / float64（解决 SUM/比较错误）
    - 布尔/日期 -> bool / datetime64[ns]
    - 其余保持 object
    """
    out: Dict[str, str] = {}
    for c in df.columns:
        col = df[c]
        try:
            if pd.api.types.is_bool_dtype(col):
                out[c] = "bool"
            elif pd.api.types.is_integer_dtype(col):
                out[c] = "int64"
            elif pd.api.types.is_float_dtype(col):
                out[c] = "float64"
            elif pd.api.types.is_datetime64_any_dtype(col):
                out[c] = "datetime64[ns]"
            else:
                # object：尝试数值化（API 常把数值当字符串返回）
                non_null = col.dropna()
                if len(non_null) == 0:
                    out[c] = "object"
                    continue
                coerced = pd.to_numeric(non_null, errors="coerce")
                if coerced.notna().sum() == len(non_null):
                    try:
                        out[c] = "int64" if (coerced == coerced.astype("int64")).all() else "float64"
                    except Exception:
                        out[c] = "float64"
                else:
                    out[c] = "object"
        except Exception:
            out[c] = "object"
    return out


def _apply_dtypes(df: pd.DataFrame, dtype_map: Optional[Dict[str, str]]) -> pd.DataFrame:
    """按配置 dtype 转换（register 前 astype；object 跳过；失败保持原类型）。

    数值列用 pandas 可空类型（Int64/Float64）以兼容 None/NaN 不炸 SUM。
    """
    if not dtype_map:
        return df
    convert = {}
    for c, t in dtype_map.items():
        if c in df.columns and t and str(t) not in ("object", "str", ""):
            _t = str(t)
            if _t == "int64":
                convert[c] = "Int64"
            elif _t == "float64":
                convert[c] = "Float64"
            else:
                convert[c] = _t
    if not convert:
        return df
    try:
        return df.astype(convert)
    except Exception as e:
        logger.warning(f"[DuckDB] astype 转换失败，保持原类型: {e}")
        return df


# --------------------------------------------------------------------------- #
# 通用 API 调用（所有 endpoint 共用，配置驱动）
# --------------------------------------------------------------------------- #

def _build_query_params(meta: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
    """按 params 配置把 filters 构造为 query_params dict（list 值逗号连接，适配 IN 下推）。

    P3：结构化值处理 ——
      - {"_range": [(op, val), ...]}：若该参数声明 range=true（或 map_to=="range"），
        映射为 {name}_min / {name}_max 两个 API 参数；未声明则不下推（内存过滤）
      - {"_like": "xx%"}：若该参数声明 prefix=true（或 map_to=="prefix"），
        映射为 name=<前缀>（去掉尾部 %）；未声明则不下推
    """
    query_params: Dict[str, Any] = {}
    for p in meta.get("params") or []:
        col = p["column"]
        if col not in filters or filters[col] is None:
            continue
        v = filters[col]
        name = p["name"]
        if isinstance(v, dict):
            if "_range" in v and (p.get("range") or (p.get("map_to") == "range")):
                vals = {op: val for op, val in v["_range"]}
                if vals.get(">=") is not None:
                    query_params[f"{name}_min"] = vals[">="]
                elif vals.get(">") is not None:
                    query_params[f"{name}_min"] = vals[">"]
                if vals.get("<=") is not None:
                    query_params[f"{name}_max"] = vals["<="]
                elif vals.get("<") is not None:
                    query_params[f"{name}_max"] = vals["<"]
            elif "_like" in v and (p.get("prefix") or (p.get("map_to") == "prefix")):
                query_params[name] = str(v["_like"]).rstrip("%")
            continue
        query_params[name] = ",".join(_stable_repr(x) for x in v) if isinstance(v, (list, tuple)) else v
    return query_params


def _build_body(meta: Dict[str, Any], method: str) -> Any:
    """POST 请求体：优先 body_template（如 ES _search query DSL），否则空 body。"""
    import json as _json
    body: Any = {}
    if method != "GET" and meta.get("body_template"):
        try:
            body = _json.loads(meta["body_template"])
        except Exception as e:
            logger.warning(f"[DuckDB] body_template 解析失败，回退空 body: {e}")
            body = {}
    return body


def _extract_rows(data: Any, json_paths: List[str]) -> List[List[Any]]:
    """按 data_path 已剥到列表层，再按 json_path 逐列取值。"""
    if isinstance(data, list):
        rows: List[List[Any]] = []
        for item in data:
            if isinstance(item, dict):
                rows.append([_get_nested(item, jp) for jp in json_paths])
            else:
                rows.append([None] * len(json_paths))
        return rows
    return []


def _fetch_once(url: str, method: str, query_params: Dict[str, Any], headers: Dict[str, Any],
                body: Any, data_path: Optional[str], json_paths: List[str], timeout: int = 30) -> List[List[Any]]:
    """单次 HTTP 拉取并解出行数据；失败抛 EngineError（结构化分类）。"""
    try:
        if method == "GET":
            resp = requests.get(url, params=query_params, headers=headers, timeout=timeout)
        else:
            resp = requests.post(url, json=body, params=query_params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except EngineError:
        raise
    except requests.exceptions.HTTPError as e:
        code = getattr(getattr(e, "response", None), "status_code", None)
        if code in (401, 403):
            raise EngineError("AUTH", f"API 鉴权失败（HTTP {code}）: {url}", detail=str(code))
        raise EngineError("UPSTREAM_API", f"API 返回 HTTP {code}: {url}", detail=str(code))
    except Exception as e:
        cls = classify_requests_error(e)
        raise EngineError(cls, f"API 调用失败 {url}: {e}")
    # 按 data_path 逐层提取列表（如 "data.TABLES.PROJECT_DEFINITION" 或 "hits.hits"）
    if data_path:
        for k in str(data_path).split("."):
            data = data.get(k, []) if isinstance(data, dict) else data
    return _extract_rows(data, json_paths)


def _fetch_with_pagination(meta: Dict[str, Any], query_params: Dict[str, Any], headers: Dict[str, Any],
                           body: Any, json_paths: List[str]) -> Tuple[List[List[Any]], Dict[str, Any]]:
    """单页或分页拉取（页码型循环）。返回 (行列表, 拉取信息)。

    pagination 配置: {"page_param":"page","size_param":"size","page_size":100,"max_pages":5}
    达到 max_pages 或单页不足 page_size 即停；行数超 _MAX_ROWS_PER_ENDPOINT 报错并明示。
    """
    url = meta["api_url"]
    method = (meta.get("method") or "POST").upper()
    data_path = meta.get("data_path")
    pagination = meta.get("pagination") or {}
    warnings: List[str] = []
    info: Dict[str, Any] = {"pages": 1}

    if not pagination or not pagination.get("page_param"):
        rows = _fetch_once(url, method, query_params, headers, body, data_path, json_paths)
        info["pages"] = 1
    else:
        page_param = str(pagination.get("page_param") or "page")
        size_param = str(pagination.get("size_param") or "size")
        try:
            page_size = int(pagination.get("page_size") or 100)
        except Exception:
            page_size = 100
        try:
            max_pages = int(pagination.get("max_pages") or 5)
        except Exception:
            max_pages = 5
        max_pages = max(1, min(max_pages, 50))  # 硬护栏：最多 50 页
        page_size = max(1, min(page_size, 1000))
        all_rows: List[List[Any]] = []
        page = 1
        for page in range(1, max_pages + 1):
            qp = dict(query_params)
            qp[page_param] = page
            qp[size_param] = page_size
            page_rows = _fetch_once(url, method, qp, headers, body, data_path, json_paths)
            all_rows.extend(page_rows)
            if len(page_rows) < page_size:
                break
        info["pages"] = page
        if page >= max_pages and len(all_rows) >= page_size:
            warnings.append(f"已达到分页上限 {max_pages} 页（每页 {page_size}），可能仍有后续数据")
        rows = all_rows

    if len(rows) > _MAX_ROWS_PER_ENDPOINT:
        raise EngineError(
            "UPSTREAM_API",
            f"单端点数据量超过 {_MAX_ROWS_PER_ENDPOINT} 行上限（实际 {len(rows)}），"
            f"为保护内存已拒绝执行；请加 WHERE 过滤或调小分页后再查",
            detail=url,
        )
    info["rows_fetched"] = len(rows)
    if warnings:
        info["warnings"] = warnings
    return rows, info


def _call_api(meta: Dict[str, Any], filters: Dict[str, Any], use_cache: bool = True,
              warnings: Optional[List[str]] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """通用 API 调用（缓存 + 分页 + 错误分类）。返回 (DataFrame, 调用信息)。

    meta=endpoint配置, filters=下推参数值{column: value}
    返回 DataFrame 列名=meta.columns[].name。
    支持三种 API 形态：
      - 传统 REST：filters 拼进 URL query（params 配置；IN 数组逗号连接）
      - ES _search：POST body_template（query DSL），filters 暂不下推（DuckDB 内存过滤）
      - 嵌套响应：json_path 支持点号（如 _source.col）
    """
    cols: List[str] = [c["name"] for c in meta.get("columns") or []]
    json_paths: List[str] = [c["json_path"] for c in meta.get("columns") or []]
    query_params = _build_query_params(meta, filters)
    headers = meta.get("headers") or {}
    body = _build_body(meta, (meta.get("method") or "POST").upper())

    # 批2：缓存命中直接复用（零 API 调用），TTL 内有效；0 = 禁用缓存
    endpoint_id = str(meta.get("id") or meta.get("table_name") or "")
    ttl_raw = meta.get("cache_ttl_seconds")
    try:
        ttl = int(ttl_raw) if ttl_raw is not None else 300
    except Exception:
        ttl = 300
    cacheable = bool(use_cache and endpoint_id and ttl and ttl > 0)
    params_key = ""
    if cacheable:
        params_key = _cache_key(endpoint_id, filters)
        hit = _cache_get(endpoint_id, params_key, ttl)
        if hit is not None:
            df, fetched_at = hit
            return df, {"source": "cache", "snapshot_at": fetched_at}

    # P3：仅未命中才触达上游 —— 限速（令牌间隔）+ 熔断（OPEN 快速失败）
    _enforce_rate_limit(meta)
    _check_circuit(meta)

    try:
        rows, info = _fetch_with_pagination(meta, query_params, headers, body, json_paths)
        _record_success(meta)
    except EngineError as e:
        _record_failure(meta)
        raise

    df = pd.DataFrame(rows, columns=cols) if cols else pd.DataFrame()
    if cacheable:
        _cache_put(endpoint_id, params_key, df)
        info["source"] = "api"
        info["snapshot_at"] = time.time()
    else:
        info["source"] = "api"
    if warnings is not None and info.get("warnings"):
        warnings.extend(info["warnings"])
    return df, info


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
# sqlglot 解析：提取表名 + WHERE 常量 + JOIN 等值 + IN 条件，推导下推参数
# --------------------------------------------------------------------------- #

def _parse_sql_tables_and_filters(sql: str) -> Tuple[Dict[str, str], Dict[str, Dict[str, Any]]]:
    """解析 SQL，返回 (表名映射, 每表的下推参数)

    表名映射: {alias_or_name: real_table_name}
    下推参数: {table_name: {param_column: value}}，含 WHERE 直接条件 + JOIN 传递的值 + IN 数组
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
        if not tbl:
            # 未限定列（如 WHERE name IN ...）：仅当 SQL 只涉及一张真实表时归属到该表
            real = set(tables.values())
            if len(real) == 1:
                tbl = next(iter(real))
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

    # 批2：WHERE IN ('a','b') 条件 -> 数组下推（附 pushdown 数组）
    for cond in ast.find_all(exp.In):
        col = cond.this
        vals = cond.expressions
        if isinstance(col, exp.Column) and vals and all(isinstance(v, exp.Literal) for v in vals):
            _record(col.table or col.name, col.name, [v.this for v in vals])

    # P3：范围条件（col >= 1 / col <= 10 / > / <）-> 结构化为 {"_range": [(op, val), ...]}
    _RANGE_OPS = {exp.GTE: ">=", exp.LTE: "<=", exp.GT: ">", exp.LT: "<"}
    for cond in ast.find_all((exp.GTE, exp.LTE, exp.GT, exp.LT)):
        l, r = cond.this, cond.expression
        col, lit = None, None
        if isinstance(l, exp.Column) and isinstance(r, exp.Literal):
            col, lit = l, r
        elif isinstance(r, exp.Column) and isinstance(l, exp.Literal):
            col, lit = r, l
        if not (col and lit):
            continue
        op = _RANGE_OPS.get(type(cond), "=")
        tbl_key = col.table or col.name
        tbl = tables.get(tbl_key) or tables.get(col.name)
        if not tbl:
            real = set(tables.values())
            if len(real) == 1:
                tbl = next(iter(real))
        if not tbl:
            continue
        prev = where_filters.setdefault(tbl, {}).get(col.name)
        if isinstance(prev, dict) and "_range" in prev:
            prev["_range"].append((op, lit.this))
        else:
            where_filters.setdefault(tbl, {})[col.name] = {"_range": [(op, lit.this)]}

    # P3：LIKE 前缀条件（col LIKE 'xx%'，仅纯前缀模式）-> 结构化为 {"_like": "xx%"}
    for cond in ast.find_all(exp.Like):
        col, pattern = cond.this, cond.expression
        if isinstance(col, exp.Column) and isinstance(pattern, exp.Literal):
            pat = str(pattern.this)
            # 仅当模式是纯前缀（仅结尾一个 %，无其它通配符）才可下推
            if pat.endswith("%") and "%" not in pat[:-1] and "_" not in pat:
                _record(col.table or col.name, col.name, {"_like": pat})

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
    """把 filters 转成 WHERE 加到 pseudo_sql（SELECT 别名映射为原列名，确保 sqlglot 能下推）

    F1-fix: 用 sqlglot AST 构造 WHERE 条件（exp.Literal.string 转义单引号），
    替代字符串拼接 f"{col}='{v}'"，防止 filter value 注入（如 x' OR 1=1 --）。
    """
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
    # F1-fix: 用 sqlglot AST 构造 WHERE 条件，exp.Literal.string 自动转义单引号
    where_conds = []
    for k, v in filters.items():
        col_name = alias_map.get(k, k)
        # 解析列名（可能含 table.col 形式）
        if "." in col_name:
            tbl, cname = col_name.split(".", 1)
            col_expr = exp.column(cname, table=tbl)
        else:
            col_expr = exp.column(col_name)
        if isinstance(v, (list, tuple)):
            # IN 数组 -> col IN ('a','b')（值转义由 sqlglot Literal 处理）
            lit_exprs = [exp.Literal.string(str(x)) for x in v]
            where_conds.append(exp.In(this=col_expr, expressions=lit_exprs))
        elif isinstance(v, dict) and "_range" in v:
            # P3：范围条件 -> col >= a AND col <= b
            for op, val in v["_range"]:
                lit_expr = exp.Literal.string(str(val))
                if op == ">=":
                    where_conds.append(exp.GTE(this=col_expr, expression=lit_expr))
                elif op == "<=":
                    where_conds.append(exp.LTE(this=col_expr, expression=lit_expr))
                elif op == ">":
                    where_conds.append(exp.GT(this=col_expr, expression=lit_expr))
                else:
                    where_conds.append(exp.LT(this=col_expr, expression=lit_expr))
        elif isinstance(v, dict) and "_like" in v:
            # P3：LIKE 前缀 -> col LIKE 'xx%'
            where_conds.append(exp.Like(this=col_expr, expression=exp.Literal.string(str(v["_like"]))))
        else:
            lit_expr = exp.Literal.string(str(v))
            where_conds.append(exp.EQ(this=col_expr, expression=lit_expr))
    if where_conds:
        try:
            _ast = sqlglot.parse_one(pseudo_sql)
            for cond in where_conds:
                _ast = _ast.where(cond)
            return _ast.sql()
        except Exception:
            # parse 失败时 fallback（不应发生，但保底用转义后的值）
            where_parts = []
            for k, v in filters.items():
                col_name = alias_map.get(k, k)
                if isinstance(v, (list, tuple)):
                    vals = ",".join(f"'{str(x).replace(chr(39), chr(39)+chr(39))}'" for x in v)
                    where_parts.append(f"{col_name} IN ({vals})")
                elif isinstance(v, dict) and "_range" in v:
                    for op, val in v["_range"]:
                        where_parts.append(f"{col_name} {op} '{str(val).replace(chr(39), chr(39)+chr(39))}'")
                elif isinstance(v, dict) and "_like" in v:
                    where_parts.append(f"{col_name} LIKE '{str(v['_like']).replace(chr(39), chr(39)+chr(39))}'")
                else:
                    where_parts.append(f"{col_name}='{str(v).replace(chr(39), chr(39)+chr(39))}'")
            return f"{pseudo_sql} WHERE " + " AND ".join(where_parts)
    return pseudo_sql


def _execute_federated(sql: str, endpoints_by_table: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """联邦执行（须在 _EXEC_LOCK 内调用）。"""
    conn = get_conn()
    tables, where_filters = _parse_sql_tables_and_filters(sql)
    pushed_down: Dict[str, Dict[str, Any]] = {}
    pushdown_trace: Dict[str, Dict[str, Any]] = {}   # P3：下推树（工作台调试器）
    not_pushed: List[Dict[str, Any]] = []            # P3：未下推审计
    warnings: List[str] = []
    cache_sources: List[Dict[str, Any]] = []   # 批2：命中缓存的表 + 快照时间

    # 对每个涉及的 API 表，调 API + register DataFrame
    registered: List[str] = []
    for _alias, tbl_name in tables.items():
        if tbl_name not in endpoints_by_table or tbl_name in registered:
            continue
        ep = endpoints_by_table[tbl_name]
        rc = ep.get("run_config") or {}
        meta = {
            "id": ep.get("id"), "api_url": ep["api_url"], "method": ep.get("method", "POST"),
            "params": ep.get("params") or [], "columns": ep.get("columns") or [],
            "data_path": ep.get("data_path"), "headers": ep.get("headers"),
            "body_template": ep.get("body_template"),
            "pagination": ep.get("pagination") or {}, "cache_ttl_seconds": ep.get("cache_ttl_seconds"),
            # P3：限速/熔断 per-endpoint（run_config 优先，dict 直接注入次之，缺省用默认）
            "rate_limit_min_interval_ms": rc.get("rate_limit_min_interval_ms", ep.get("rate_limit_min_interval_ms")),
            "circuit_threshold": rc.get("circuit_threshold", ep.get("circuit_threshold")),
            "circuit_open_seconds": rc.get("circuit_open_seconds", ep.get("circuit_open_seconds")),
        }
        filters = where_filters.get(tbl_name, {})
        # P3：Pushdown trace —— 逐列说明下推种类与是否真正触达上游 API
        trace_cols: Dict[str, Dict[str, Any]] = {}
        sent_params = set(_build_query_params(meta, filters).keys())
        param_cols = {p["column"]: p for p in (meta.get("params") or [])}
        not_pushed_for_tbl: List[Dict[str, Any]] = []
        for col_name, val in (filters or {}).items():
            p = param_cols.get(col_name)
            if isinstance(val, dict) and "_range" in val:
                kind = "range"
                pushed = bool(p and (p.get("range") or p.get("map_to") == "range")
                              and (f"{p.get('name')}_min" in sent_params or f"{p.get('name')}_max" in sent_params))
                detail = {"range": val["_range"]}
            elif isinstance(val, dict) and "_like" in val:
                kind = "like"
                pushed = bool(p and (p.get("prefix") or p.get("map_to") == "prefix")
                              and p.get("name") in sent_params)
                detail = {"pattern": val["_like"]}
            elif isinstance(val, (list, tuple)):
                kind = "in"
                pushed = bool(p and p.get("name") in sent_params)
                detail = {"values": val}
            else:
                kind = "eq"
                pushed = bool(p and p.get("name") in sent_params)
                detail = {"value": val}
            trace_cols[col_name] = {"kind": kind, "pushed_to_api": pushed, **detail}
            if not pushed:
                not_pushed_for_tbl.append({"table": tbl_name, "column": col_name, "kind": kind,
                                           "reason": "endpoint 未声明该参数或未声明 range/prefix 支持，改由 DuckDB 内存过滤"})
        try:
            df, _info = _call_api(meta, filters, warnings=warnings)
        except EngineError as e:
            logger.error(f"[DuckDB] 表 {tbl_name} 拉取失败[{e.cls}]: {e.message}")
            raise
        if _info.get("source") == "cache":
            cache_sources.append({"table": tbl_name, "snapshot_at": _info.get("snapshot_at")})
        dtype_map = {c.get("name"): c.get("dtype") for c in (meta.get("columns") or [])}
        df = _apply_dtypes(df, dtype_map)
        conn.register(tbl_name, df)
        registered.append(tbl_name)
        pushed_down[tbl_name] = filters
        pushdown_trace[tbl_name] = {"cols": trace_cols,
                                    "pushed_to_api": any(c["pushed_to_api"] for c in trace_cols.values())}
        not_pushed.extend(not_pushed_for_tbl)
        if filters:
            logger.info(f"[DuckDB] 表 {tbl_name} 下推参数: {filters}，取回 {len(df)} 行")
        else:
            logger.info(f"[DuckDB] 表 {tbl_name} 无下推参数（全量），取回 {len(df)} 行")

    # 执行原 SQL（DuckDB 内存 JOIN/聚合/过滤）
    cur = conn.execute(sql)
    columns = [d[0] for d in cur.description]
    rows = cur.fetchall()
    result: Dict[str, Any] = {"columns": columns, "rows": [list(r) for r in rows], "row_count": len(rows),
                              "pushed_down": pushed_down}
    # P3：下推树 + 未下推审计（工作台 Pushdown 调试器 / 审计）
    result["pushdown_trace"] = pushdown_trace
    result["not_pushed"] = not_pushed
    if warnings:
        result["warnings"] = warnings
    # 批2：命中缓存 -> 附数据快照时间（前端 DataAccessCard 显示「数据快照 HH:MM」）
    if cache_sources:
        import time as _time
        _earliest = min((s["snapshot_at"] for s in cache_sources), default=None)
        result["data_snapshot_at"] = _time.strftime("%H:%M", _time.localtime(_earliest)) if _earliest else None
        result["cache_sources"] = [s["table"] for s in cache_sources]
    return result


def execute_sql(sql: str, endpoints_by_table: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """执行多源API联邦SQL（串行锁保护 DuckDB 单例；API 失败结构化 error_class）。

    Args:
        sql: 用户SQL，如 SELECT * FROM dim_ps_project_def p JOIN dim_ps_wbs_element w ON ...
        endpoints_by_table: {table_name: endpoint配置dict}（含 api_url/method/params/columns/data_path/headers）

    Returns:
        {columns, rows, row_count, pushed_down, warnings?, data_snapshot_at?} 或
        {columns:[], rows:[], row_count:0, error, error_class}
    """
    import time as _time
    _t0 = _time.time()
    # P5：预聚合加速器拦截（同形单值聚合 -> 预聚合表服务，附数据截至标注）
    try:
        from app.services.engine_accelerator import try_serve
        served = try_serve(sql)
        if served is not None:
            served.setdefault("duration_ms", int((_time.time() - _t0) * 1000))
            return served
    except Exception:
        pass
    with _EXEC_LOCK:
        try:
            result = _execute_federated(sql, endpoints_by_table)
        except EngineError as e:
            logger.error(f"[DuckDB] 联邦查询失败[{e.cls}]: {e.message}")
            result = {"columns": [], "rows": [], "row_count": 0,
                      "error": e.message, "error_class": e.cls}
            if e.detail:
                result["error_detail"] = e.detail
        except Exception as e:
            from app.services.engine_errors import classify_duckdb_error
            logger.error(f"[DuckDB] 联邦查询异常: {e}")
            result = {"columns": [], "rows": [], "row_count": 0, "error": str(e),
                      "error_class": classify_duckdb_error(e)}
    # 批1：查询日志（异常不影响主流程）
    try:
        from app.services.engine_query_log import record_query_log
        record_query_log(
            "duckdb", sql,
            rows_returned=result.get("row_count", 0),
            duration_ms=int((_time.time() - _t0) * 1000),
            status="error" if result.get("error") else "ok",
            error_class=result.get("error_class"),
        )
    except Exception:
        pass
    return result


async def execute_federated_async(sql: str, endpoints_by_table: Dict[str, Dict[str, Any]],
                                  timeout: float = 120.0) -> Dict[str, Any]:
    """批1 异步入口：asyncio.wait_for + to_thread 双重超时护栏（不阻塞事件循环）。

    供 async 端点 / 后续 agent 路径使用；同步调用仍走 execute_sql（FastMCP/FastAPI 线程池已兜底）。
    """
    return await asyncio.wait_for(
        asyncio.to_thread(execute_sql, sql, endpoints_by_table),
        timeout=timeout,
    )


def test_endpoint(ep: Dict[str, Any], limit: int = 10) -> Dict[str, Any]:
    """单端点测试（绕过缓存，全量拉，返前 limit 行 + dtype 建议 + 分页信息）。"""
    meta = {
        "id": ep.get("id"), "api_url": ep["api_url"], "method": ep.get("method", "POST"),
        "params": ep.get("params") or [], "columns": ep.get("columns") or [],
        "data_path": ep.get("data_path"), "headers": ep.get("headers"),
        "body_template": ep.get("body_template"),
        "pagination": ep.get("pagination") or {}, "cache_ttl_seconds": 0,
    }
    try:
        df, info = _call_api(meta, {}, use_cache=False)
    except EngineError as e:
        return {"columns": [], "rows": [], "row_count": 0, "error": e.message, "error_class": e.cls}
    rows = df.head(limit).values.tolist()
    dtype_suggestions = infer_dtypes(df)   # 批2：采样定 dtype 建议（前端写入 columns[].dtype）
    return {"columns": list(df.columns), "rows": rows, "row_count": len(rows),
            "dtype_suggestions": dtype_suggestions, "info": info}


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
                "cache_ttl_seconds": getattr(ep, "cache_ttl_seconds", None),
                "pagination": getattr(ep, "pagination", None) or {},
                "run_config": getattr(ep, "run_config", None) or {},
            }
    except Exception as e:
        logger.error(f"[DuckDB] 加载 endpoints 失败: {e}")
    return out


def reset_conn():
    """关闭并清空 DuckDB 单例，下次 get_conn() 会用最新配置重新 ATTACH。

    在 DorisConfig / DataSourceConfig 变更后调用，确保 DuckDB 用新配置重连。
    """
    global _conn
    with _CONN_LOCK:
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
            _conn = None


def get_conn() -> duckdb.DuckDBPyConnection:
    """DuckDB 单例连接（内存库 + 可选 ATTACH PostgreSQL/Doris，跨源联邦）。

    配置来源（统一读 DB 配置表，不再硬编码）：
    - ATTACH PostgreSQL: 查 DataSourceConfig 表 (db_type=postgresql, is_default=true)
      找不到则回退环境变量 TUPU_PG_*（极端兜底）
    - ATTACH Doris: 调 doris_engine._load_config() 查 DorisConfig 表
      找不到则回退 _DORIS_CONFIG_DEFAULT
    - API 虚拟表: register DataFrame（已有）

    注意：DuckDB 的 INSTALL <ext> 会联网下载扩展，本机网络环境下会长时间挂起。
    故这里只查 duckdb_extensions()，仅当扩展【已安装】时才 LOAD+ATTACH；
    未安装则跳过（不调 INSTALL），保证单源 API 预览（register DataFrame + SELECT）不被阻塞。
    跨对象 JOIN（pg.物理表）需先用 `FORCE INSTALL postgres` 装好扩展才可用。

    配置变更后调用 reset_conn() 可触发下次 get_conn() 重新 ATTACH。

    批1：连接初始化后一次性设置内存护栏（memory_limit/threads）。
    """
    import os
    global _conn
    with _CONN_LOCK:
        if _conn is None:
            _conn = duckdb.connect(":memory:")
            # 批1：内存护栏一次性设置
            try:
                _conn.execute(f"SET memory_limit='{_MEMORY_LIMIT}';")
                _conn.execute(f"SET threads={_THREADS};")
            except Exception as e:
                logger.warning(f"[DuckDB] 设置内存护栏失败: {e}")

            def _ext_installed(name: str) -> bool:
                try:
                    row = _conn.execute(
                        "SELECT count(*) FROM duckdb_extensions() WHERE extension_name=? AND installed=true",
                        [name],
                    ).fetchone()
                    return bool(row and row[0])
                except Exception:
                    return False

            # PostgreSQL（pg.物理表 跨源JOIN）—— 读 DataSourceConfig 表
            try:
                if _ext_installed("postgres_scanner"):
                    _conn.execute("LOAD postgres_scanner;")
                    _pg_host = _pg_port = _pg_user = _pg_pwd = _pg_db = None
                    try:
                        from app.models.base import DataSourceConfig
                        from app.core.database import SessionLocal
                        _sess = SessionLocal()
                        try:
                            _ds = _sess.query(DataSourceConfig).filter(
                                DataSourceConfig.db_type.in_(("postgresql", "postgres", "pg")),
                                DataSourceConfig.is_default == True,
                                DataSourceConfig.enabled == True,
                            ).first()
                            if not _ds:
                                _ds = _sess.query(DataSourceConfig).filter(
                                    DataSourceConfig.db_type.in_(("postgresql", "postgres", "pg")),
                                    DataSourceConfig.enabled == True,
                                ).first()
                            if _ds:
                                _pg_host, _pg_port = _ds.host, _ds.port
                                _pg_user, _pg_pwd = _ds.username, _ds.password
                                _pg_db = _ds.database
                        finally:
                            _sess.close()
                    except Exception as e:
                        logger.warning(f"[DuckDB] 读取 DataSourceConfig(postgresql) 失败，回退环境变量: {e}")
                    # 兜底：DB 无记录时回退环境变量
                    _pg_host = _pg_host or os.getenv("TUPU_PG_HOST", "localhost")
                    _pg_port = _pg_port or os.getenv("TUPU_PG_PORT", "25432")
                    _pg_user = _pg_user or os.getenv("TUPU_PG_USER", "postgres")
                    _pg_pwd = _pg_pwd or os.getenv("TUPU_PG_PASSWORD", "postgres")
                    _pg_db = _pg_db or os.getenv("TUPU_PG_DB", "tupu")
                    _conn.execute(
                        f"ATTACH 'dbname={_pg_db} host={_pg_host} port={_pg_port} user={_pg_user} password={_pg_pwd}' AS pg (TYPE postgres)"
                    )
                    logger.info(f"[DuckDB] ATTACH PostgreSQL 成功: {_pg_host}:{_pg_port}/{_pg_db}（physical_table 对象可查 pg.表名）")
                else:
                    logger.warning("[DuckDB] postgres 扩展未安装，跳过 ATTACH pg（跨对象JOIN暂不可用，单源API预览不受影响）")
            except Exception as e:
                logger.warning(f"[DuckDB] ATTACH PostgreSQL 失败: {e}")

            # Doris（doris.视图 跨源JOIN）—— 读 DorisConfig 表
            try:
                if _ext_installed("mysql_scanner"):
                    _conn.execute("LOAD mysql_scanner;")
                    from app.services.doris_engine import _load_config as _load_doris_config
                    _dcfg = _load_doris_config()
                    _parts = [f"host={_dcfg['host']}", f"port={_dcfg['port']}", f"user={_dcfg['user']}"]
                    if _dcfg.get("password"):
                        _parts.append(f"password={_dcfg['password']}")
                    if _dcfg.get("database"):
                        _parts.append(f"database={_dcfg['database']}")
                    _conn.execute(f"ATTACH '{' '.join(_parts)}' AS doris (TYPE mysql)")
                    logger.info(f"[DuckDB] ATTACH Doris 成功: {_dcfg['host']}:{_dcfg['port']}/{_dcfg.get('database', '')}（sql_integration 对象可查 doris.表名）")
                else:
                    logger.warning("[DuckDB] mysql 扩展未安装，跳过 ATTACH doris")
            except Exception as e:
                logger.warning(f"[DuckDB] ATTACH Doris 失败: {e}")
    return _conn
