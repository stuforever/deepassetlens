"""test_engine_enhance.py - 数据引擎增强（批1 稳定性 / 批2 能力）

覆盖：
- 批1：错误分类（6 类）、Doris 超时包装+连接池懒初始化、DuckDB 串行锁并发、error_class 返回
- 批2：API 内存缓存（命中/失效/快照披露）、类型推断（字符串数字 SUM 正确）、IN 下推数组

验收点（设计文档 §7）：
- 并发 10 路无崩溃（串行锁）
- 同问题二问 API 调用计数为 0（缓存命中）
- 数值 SUM 正确（dtype）
- col IN 在 pushdown 数组（IN 下推）
"""
import threading
import time

import pytest

from app.services import duckdb_engine
from app.services.engine_errors import (
    EngineError,
    apply_error_class,
    classify_by_message,
    classify_pymysql_error,
    wrap_engine_exception,
)


# --------------------------------------------------------------------------- #
# 批1：错误分类
# --------------------------------------------------------------------------- #

class TestErrorClass:
    def test_engine_error_class(self):
        e = EngineError("TABLE_MISSING", "表不存在")
        assert e.cls == "TABLE_MISSING"
        r = e.to_result()
        assert r["error_class"] == "TABLE_MISSING" and "error" in r

    def test_classify_by_message_table_missing(self):
        assert classify_by_message("Table 'db.tbl' doesn't exist") == "TABLE_MISSING"
        assert classify_by_message("Error 1146 (42S02): Table 'x.y' doesn't exist") == "TABLE_MISSING"

    def test_classify_by_message_others(self):
        assert classify_by_message("Query execution timeout") == "TIMEOUT"
        assert classify_by_message("You have an error in your SQL syntax") == "SYNTAX"
        assert classify_by_message("Access denied for user") == "AUTH"
        assert classify_by_message("Can't connect to MySQL server") == "CONNECTION"

    def test_classify_pymysql_errno(self):
        class _Err(Exception):
            pass
        assert classify_pymysql_error(_Err(1146, "t")) == "TABLE_MISSING"
        assert classify_pymysql_error(_Err(1045, "t")) == "AUTH"
        assert classify_pymysql_error(_Err(2003, "t")) == "CONNECTION"
        assert classify_pymysql_error(_Err(1064, "t")) == "SYNTAX"
        assert classify_pymysql_error(_Err(3024, "t")) == "TIMEOUT"

    def test_apply_error_class_keeps_existing(self):
        assert apply_error_class({"error": "Table 'a.b' doesn't exist"})["error_class"] == "TABLE_MISSING"
        assert apply_error_class({"error": "x", "error_class": "SYNTAX"})["error_class"] == "SYNTAX"

    def test_wrap_engine_exception(self):
        assert wrap_engine_exception(EngineError("AUTH", "no"))["error_class"] == "AUTH"
        assert wrap_engine_exception(ValueError("timeout"))["error_class"] == "TIMEOUT"


# --------------------------------------------------------------------------- #
# 批1：Doris 超时包装 + 连接池懒初始化
# --------------------------------------------------------------------------- #

class TestDorisTimeout:
    def test_with_query_timeout_wraps(self):
        from app.services.doris_engine import _with_query_timeout
        wrapped = _with_query_timeout("SELECT 1")
        assert "SET_VAR(query_timeout=60)" in wrapped
        assert wrapped.startswith("SELECT")
        assert wrapped.rstrip().endswith(") t")

    def test_pool_reset_lazy(self):
        from app.services import doris_engine
        doris_engine.reset_pool()
        e = doris_engine._pool()
        assert e is not None
        doris_engine.reset_pool()
        assert doris_engine._ENGINE is None


# --------------------------------------------------------------------------- #
# 批2：缓存 / 类型 / IN 下推（纯单元）
# --------------------------------------------------------------------------- #

class TestCacheUnit:
    def test_cache_key_stable(self):
        k1 = duckdb_engine._cache_key("ep1", {"b": 2, "a": 1})
        k2 = duckdb_engine._cache_key("ep1", {"a": 1, "b": 2})
        assert k1 == k2 and len(k1) == 8

    def test_cache_put_get_invalidate(self):
        duckdb_engine.invalidate_endpoint_cache()
        import pandas as pd
        df = pd.DataFrame({"a": [1, 2]})
        duckdb_engine._cache_put("ep-x", "k1", df)
        hit = duckdb_engine._cache_get("ep-x", "k1", ttl=300)
        assert hit is not None and hit[0].equals(df)
        # TTL 过期自然失效（P3：内存 + parquet 落盘两层都过期才判失效）
        duckdb_engine._CACHE[("ep-x", "k1")] = (time.time() - 9999, df)
        import os
        _pq = duckdb_engine._parquet_path("ep-x", "k1")
        if os.path.exists(_pq):
            os.utime(_pq, (time.time() - 9999, time.time() - 9999))
        assert duckdb_engine._cache_get("ep-x", "k1", ttl=300) is None
        # 配置失效：清单 endpoint
        duckdb_engine._cache_put("ep-x", "k1", df)
        n = duckdb_engine.invalidate_endpoint_cache("ep-x")
        assert n == 1 and duckdb_engine.cache_stats()["entries"] == 0
        duckdb_engine.invalidate_endpoint_cache()  # 复位


class TestInferDtypes:
    def test_numeric_strings_coerced(self):
        import pandas as pd
        df = pd.DataFrame({"amt": ["10", "20", "30"], "name": ["a", "b", "c"]})
        dtypes = duckdb_engine.infer_dtypes(df)
        assert dtypes["amt"] in ("int64", "float64")
        assert dtypes["name"] == "object"

    def test_apply_dtypes_sum(self):
        import pandas as pd
        df = pd.DataFrame({"amt": ["10", "20", "30"]})
        typed = duckdb_engine._apply_dtypes(df, {"amt": "int64"})
        assert str(typed["amt"].dtype) in ("Int64", "int64")
        assert int(typed["amt"].sum()) == 60


class TestInPushdown:
    def test_parse_in_array(self):
        tables, wf = duckdb_engine._parse_sql_tables_and_filters(
            "SELECT * FROM t WHERE name IN ('a','b') AND city = 'sh'"
        )
        assert wf["t"]["name"] == ["a", "b"]
        assert wf["t"]["city"] == "sh"

    def test_build_in_clause(self):
        sql = duckdb_engine.build_sql_with_filters("SELECT name FROM t", {"name": ["a", "b"]})
        assert "IN" in sql.upper()


# --------------------------------------------------------------------------- #
# 批2：假 API 全链路（缓存命中 / dtype SUM / 快照 / 失效 / 并发）
# --------------------------------------------------------------------------- #

class _FakeResp:
    def __init__(self, payload):
        self._p = payload
    def raise_for_status(self):
        pass
    def json(self):
        return self._p


def _make_fake_get(items, calls=None):
    def fake_get(url, params=None, headers=None, timeout=None):
        if calls is not None:
            calls.append(dict(url=url, params=dict(params or {})))
        return _FakeResp({"items": items})
    return fake_get


@pytest.fixture
def fake_ep():
    return {
        "id": "ep-fake-1", "name": "fake", "table_name": "t_fake",
        "api_url": "http://fake.local/t", "method": "GET",
        "params": [{"name": "kw", "column": "kw"}],
        "columns": [
            {"name": "name", "json_path": "name", "type": "VARCHAR"},
            {"name": "amt", "json_path": "amt", "type": "VARCHAR", "dtype": "float64"},
        ],
        "data_path": "items", "headers": {}, "body_template": None,
        "cache_ttl_seconds": 300, "pagination": None, "description": None,
    }


class TestFakeApi:
    def test_cache_hit_zero_second_call(self, monkeypatch, fake_ep):
        duckdb_engine.invalidate_endpoint_cache()
        calls = []
        monkeypatch.setattr(duckdb_engine.requests, "get",
                            _make_fake_get([{"name": "a", "amt": "10"}], calls))
        endpoints = {"t_fake": fake_ep}
        r1 = duckdb_engine.execute_sql("SELECT * FROM t_fake", endpoints)
        assert r1["row_count"] == 1 and len(calls) == 1
        assert r1.get("data_snapshot_at") is None  # 首次走 API，无快照
        r2 = duckdb_engine.execute_sql("SELECT * FROM t_fake", endpoints)
        assert r2["row_count"] == 1 and len(calls) == 1  # 同问题二问：零 API 调用
        assert r2.get("data_snapshot_at") is not None  # 命中缓存带数据快照
        duckdb_engine.invalidate_endpoint_cache()

    def test_dtype_sum_correct(self, monkeypatch, fake_ep):
        duckdb_engine.invalidate_endpoint_cache()
        monkeypatch.setattr(duckdb_engine.requests, "get", _make_fake_get(
            [{"name": "a", "amt": "10"}, {"name": "b", "amt": "20"}, {"name": "c", "amt": "30"}]))
        endpoints = {"t_fake": fake_ep}
        r = duckdb_engine.execute_sql("SELECT SUM(amt) AS total FROM t_fake", endpoints)
        # 字符串数值 -> dtype float64 -> DuckDB 可直接 SUM，不报错且正确
        assert r.get("row_count") == 1
        total = r["rows"][0][0]
        assert total is not None and abs(float(total) - 60.0) < 1e-6
        duckdb_engine.invalidate_endpoint_cache()

    def test_in_pushdown_array(self, monkeypatch, fake_ep):
        duckdb_engine.invalidate_endpoint_cache()
        calls = []
        monkeypatch.setattr(duckdb_engine.requests, "get",
                            _make_fake_get([{"name": "a", "amt": "10"}], calls))
        endpoints = {"t_fake": fake_ep}
        r = duckdb_engine.execute_sql("SELECT * FROM t_fake WHERE name IN ('a','b')", endpoints)
        assert r.get("pushed_down", {}).get("t_fake", {}).get("name") == ["a", "b"]
        assert calls and calls[0]["params"].get("kw") is None  # name 未映射 param -> 不传
        duckdb_engine.invalidate_endpoint_cache()

    def test_error_class_propagated(self, monkeypatch, fake_ep):
        """API 失败 -> error_class=UPSTREAM_API/类，不静默空结果。"""
        duckdb_engine.invalidate_endpoint_cache()
        def boom(url, params=None, headers=None, timeout=None):
            raise duckdb_engine.requests.exceptions.HTTPError(
                "503 Service Unavailable", response=_FakeResp({}))
        monkeypatch.setattr(duckdb_engine.requests, "get", boom)
        endpoints = {"t_fake": fake_ep}
        r = duckdb_engine.execute_sql("SELECT * FROM t_fake", endpoints)
        assert r.get("error") and r.get("error_class") == "UPSTREAM_API"
        duckdb_engine.invalidate_endpoint_cache()

    def test_serial_lock_concurrent_no_crash(self, monkeypatch, fake_ep):
        """并发 10 路：DuckDB 串行锁下无崩溃、结果正确（设计验收点）。"""
        duckdb_engine.invalidate_endpoint_cache()
        monkeypatch.setattr(duckdb_engine.requests, "get", _make_fake_get(
            [{"name": "a", "amt": "10"}, {"name": "b", "amt": "20"}] * 50))
        endpoints = {"t_fake": fake_ep}
        errors, results = [], []
        def worker():
            try:
                r = duckdb_engine.execute_sql("SELECT COUNT(*) AS n FROM t_fake", endpoints)
                results.append(r)
            except Exception as e:  # noqa: BLE001
                errors.append(e)
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors, f"并发下异常: {errors[:3]}"
        assert len(results) == 10
        assert all(r.get("row_count") == 1 for r in results)
        duckdb_engine.invalidate_endpoint_cache()
