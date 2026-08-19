"""test_engine_p3.py - 数据引擎增强 P3 补全（完整版）

覆盖：
- Pushdown v2：范围（>=/<=）+ LIKE 前缀解析、build_sql 结构化重建、pushdown_trace + not_pushed 审计
- 限速/熔断：per-endpoint 令牌间隔；连续失败熔断 OPEN 快速失败（不再触达上游）；HALF_OPEN 试探恢复
- parquet 落盘缓存：跨内存清空仍命中（跨重启持久），失效同步删文件
"""
import time

import pytest

from app.services import duckdb_engine
from app.services.engine_errors import EngineError

DUCK = duckdb_engine


class _FakeResp:
    def __init__(self, payload):
        self._p = payload
    def raise_for_status(self):
        pass
    def json(self):
        return self._p


def _ok_get(items, calls=None):
    def fake_get(url, params=None, headers=None, timeout=None):
        if calls is not None:
            calls.append(dict(url=url, params=dict(params or {})))
        return _FakeResp({"items": items})
    return fake_get


def _fail_get(err, calls=None):
    def fake_get(url, params=None, headers=None, timeout=None):
        if calls is not None:
            calls.append(1)
        raise err
    return fake_get


@pytest.fixture
def fake_ep():
    return {
        "id": "ep-p3-1", "name": "p3", "table_name": "t_p3",
        "api_url": "http://fake.local/p3", "method": "GET",
        "params": [{"name": "kw", "column": "kw"}],
        "columns": [{"name": "name", "json_path": "name", "type": "VARCHAR"},
                    {"name": "amt", "json_path": "amt", "type": "VARCHAR", "dtype": "float64"}],
        "data_path": "items", "headers": {}, "body_template": None,
        "cache_ttl_seconds": 300, "pagination": None, "description": None,
    }


@pytest.fixture(autouse=True)
def _reset_state():
    DUCK.invalidate_endpoint_cache()
    DUCK._CIRCUIT_STATE.clear()
    yield
    DUCK.invalidate_endpoint_cache()
    DUCK._CIRCUIT_STATE.clear()


# --------------------------------------------------------------------------- #
# Pushdown v2：范围 + LIKE 前缀
# --------------------------------------------------------------------------- #

class TestPushdownV2:
    def test_parse_range(self):
        tables, wf = DUCK._parse_sql_tables_and_filters(
            "SELECT * FROM t_p3 WHERE amt >= 10 AND amt <= 100"
        )
        assert wf["t_p3"]["amt"]["_range"] == [(">=", "10"), ("<=", "100")]

    def test_parse_like_prefix(self):
        tables, wf = DUCK._parse_sql_tables_and_filters(
            "SELECT * FROM t_p3 WHERE name LIKE 'A%'"
        )
        assert wf["t_p3"]["name"] == {"_like": "A%"}

    def test_parse_ignores_non_prefix_like(self):
        tables, wf = DUCK._parse_sql_tables_and_filters(
            "SELECT * FROM t_p3 WHERE name LIKE '%mid%'"
        )
        assert "name" not in wf.get("t_p3", {})

    def test_build_sql_range_like(self):
        sql = DUCK.build_sql_with_filters(
            "SELECT * FROM t_p3",
            {"amt": {"_range": [(">=", "10"), ("<=", "100")]}, "name": {"_like": "A%"}},
        )
        up = sql.upper()
        assert "AMT >= '10'" in up and "AMT <= '100'" in up and "LIKE 'A%'" in up

    def test_pushdown_trace_and_not_pushed(self, monkeypatch, fake_ep):
        """范围未声明 range 参数 -> not_pushed 审计 + trace 显示 kind=range pushed=false。"""
        DUCK.invalidate_endpoint_cache()
        monkeypatch.setattr(DUCK.requests, "get", _ok_get(
            [{"name": "a", "amt": "10"}, {"name": "b", "amt": "50"}]))
        endpoints = {"t_p3": fake_ep}
        r = DUCK.execute_sql(
            "SELECT * FROM t_p3 WHERE amt >= 10 AND amt <= 100", endpoints)
        assert r["row_count"] == 2
        trace = r["pushdown_trace"]["t_p3"]["cols"]["amt"]
        assert trace["kind"] == "range" and trace["pushed_to_api"] is False
        assert any(n["column"] == "amt" for n in r["not_pushed"])
        DUCK.invalidate_endpoint_cache()


# --------------------------------------------------------------------------- #
# 限速 / 熔断
# --------------------------------------------------------------------------- #

class TestCircuitBreaker:
    def test_open_fast_fail(self, monkeypatch, fake_ep):
        """连续失败达阈值 -> OPEN：后续调用不再触达上游（调用计数不再增）。"""
        calls = []
        monkeypatch.setattr(DUCK.requests, "get", _fail_get(
            DUCK.requests.exceptions.HTTPError("boom"), calls))
        ep = {**fake_ep, "circuit_threshold": 2, "circuit_open_seconds": 60}
        endpoints = {"t_p3": ep}
        for _ in range(2):
            r = DUCK.execute_sql("SELECT * FROM t_p3", endpoints)
            assert r.get("error"), "失败应返回 error"
        assert len(calls) == 2
        # 第 3 次：OPEN 快速失败，不再触达上游
        r3 = DUCK.execute_sql("SELECT * FROM t_p3", endpoints)
        assert "熔断" in (r3.get("error") or "")
        assert len(calls) == 2, "熔断后不得再触达上游"
        st = DUCK.circuit_status(fake_ep["id"])
        assert st["state"] == "OPEN" and st["failures"] == 2
        DUCK.invalidate_endpoint_cache()

    def test_half_open_recovers(self, monkeypatch, fake_ep):
        """OPEN 超时 -> HALF_OPEN 放一次试探；成功即 CLOSED 复位。"""
        calls = []
        monkeypatch.setattr(DUCK.requests, "get", _fail_get(
            DUCK.requests.exceptions.HTTPError("boom"), calls))
        ep = {**fake_ep, "circuit_threshold": 1, "circuit_open_seconds": 1}
        endpoints = {"t_p3": ep}
        DUCK.execute_sql("SELECT * FROM t_p3", endpoints)
        assert DUCK.circuit_status(fake_ep["id"])["state"] == "OPEN"
        # 等熔断窗口过期
        time.sleep(1.2)
        monkeypatch.setattr(DUCK.requests, "get", _ok_get([{"name": "a", "amt": "10"}]))
        r = DUCK.execute_sql("SELECT * FROM t_p3", endpoints)
        assert r["row_count"] == 1 and not r.get("error")
        assert DUCK.circuit_status(fake_ep["id"])["state"] == "CLOSED"
        DUCK.invalidate_endpoint_cache()

    def test_rate_limit_interval(self, monkeypatch, fake_ep):
        """min_interval_ms 令牌间隔：相邻真实 API 调用时间差 >= 间隔。"""
        calls = []
        monkeypatch.setattr(DUCK.requests, "get", _ok_get(
            [{"name": "a", "amt": "10"}], calls))
        ep = {**fake_ep, "rate_limit_min_interval_ms": 120, "cache_ttl_seconds": 0}
        endpoints = {"t_p3": ep}
        t0 = time.time()
        DUCK.execute_sql("SELECT * FROM t_p3", endpoints)
        DUCK.execute_sql("SELECT * FROM t_p3", endpoints)
        gap = time.time() - t0
        assert len(calls) == 2
        assert gap >= 0.11, f"两次调用应被间隔开，实际 {gap:.3f}s"
        DUCK.invalidate_endpoint_cache()

    def test_cache_hit_skips_circuit(self, monkeypatch, fake_ep):
        """熔断 OPEN 时缓存仍可服务（不触达上游即可）。"""
        calls = []
        # 先成功一次写入缓存
        monkeypatch.setattr(DUCK.requests, "get", _ok_get([{"name": "a", "amt": "10"}], calls))
        ep = {**fake_ep, "cache_ttl_seconds": 300}
        endpoints = {"t_p3": ep}
        r1 = DUCK.execute_sql("SELECT * FROM t_p3", endpoints)
        assert r1["row_count"] == 1
        # 手动置 OPEN
        DUCK._CIRCUIT_STATE[fake_ep["id"]] = {"state": "OPEN", "failures": 9, "opened_at": time.time()}
        r2 = DUCK.execute_sql("SELECT * FROM t_p3", endpoints)
        assert r2["row_count"] == 1 and r2.get("data_snapshot_at"), "缓存命中应跳过熔断"
        DUCK.invalidate_endpoint_cache()


# --------------------------------------------------------------------------- #
# parquet 落盘缓存
# --------------------------------------------------------------------------- #

class TestParquetCache:
    def test_disk_persistence(self):
        import pandas as pd
        DUCK.invalidate_endpoint_cache()
        df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})
        DUCK._cache_put("ep-disk-1", "kabc", df)
        import os
        assert os.path.exists(DUCK._parquet_path("ep-disk-1", "kabc"))
        # 清空内存（模拟进程重启）
        DUCK._CACHE.clear()
        hit = DUCK._cache_get("ep-disk-1", "kabc", ttl=300)
        assert hit is not None
        assert hit[0]["a"].tolist() == [1, 2, 3]
        stats = DUCK.cache_stats()
        assert stats["disk_entries"] >= 1
        # 失效同步删盘
        DUCK.invalidate_endpoint_cache()
        assert not os.path.exists(DUCK._parquet_path("ep-disk-1", "kabc"))
