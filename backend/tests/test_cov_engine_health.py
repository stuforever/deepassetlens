# -*- coding: utf-8 -*-
"""覆盖补全批次1c：engine_health 懒探测缓存语义（此前零直接测试）。

characterization 纪律：每个测试注明会让它失败的生产改动。
隔离：monkeypatch _PROBES 条目（函数内 get），autouse 夹具清 _CACHE 防跨测试污染。
"""
import re
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services import engine_health as eh  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_cache():
    eh._CACHE.clear()
    yield
    eh._CACHE.clear()


def _mk_probe(ok=True, msg="boom"):
    calls = {"n": 0}

    def fn():
        calls["n"] += 1
        if not ok:
            raise RuntimeError(msg)

    return fn, calls


def test_probe_unknown_engine():
    """未知引擎名 -> status unknown + 错误提示，不落缓存探测函数。改动：unknown 分支被删 -> 失败。"""
    r = eh.probe("nosuch-engine")
    assert r["engine"] == "nosuch-engine" and r["status"] == "unknown"
    assert r["error"] == "未知引擎" and r["latency_ms"] == 0


def test_probe_success_and_ttl_cache(monkeypatch):
    """成功探测 status ok；60s 内二调命中缓存不重探；force=True 重探。改动：缓存早退被删 -> 失败。"""
    fn, calls = _mk_probe(ok=True)
    monkeypatch.setitem(eh._PROBES, "doris", fn)
    r1 = eh.probe("doris")
    assert r1["status"] == "ok" and r1["error"] is None
    assert "latency_ms" in r1 and "checked_at" in r1 and "checked_at_str" in r1
    eh.probe("doris")
    assert calls["n"] == 1  # 命中缓存
    eh.probe("doris", force=True)
    assert calls["n"] == 2  # 强制重测


def test_probe_failure_records_error(monkeypatch):
    """探测异常 -> status error + 截断到 200 字的 error 文本。改动：截断或 except 分支被删 -> 失败。"""
    fn, _ = _mk_probe(ok=False, msg="x" * 500)
    monkeypatch.setitem(eh._PROBES, "duckdb", fn)
    r = eh.probe("duckdb")
    assert r["status"] == "error" and len(r["error"]) == 200


def test_invalidate_single_engine_only(monkeypatch):
    """invalidate(engine) 只清该引擎缓存；invalidate() 全清。改动：invalidate 作用域逻辑改动 -> 失败。"""
    f1, c1 = _mk_probe(ok=True)
    f2, c2 = _mk_probe(ok=True)
    monkeypatch.setitem(eh._PROBES, "doris", f1)
    monkeypatch.setitem(eh._PROBES, "duckdb", f2)
    eh.probe("doris")
    eh.probe("duckdb")
    eh.invalidate("doris")
    eh.probe("doris")
    eh.probe("duckdb")
    assert c1["n"] == 2 and c2["n"] == 1  # 仅 doris 重探
    eh.invalidate()
    eh.probe("duckdb")
    assert c2["n"] == 2  # 全清后重探


def test_snapshot_covers_three_engines(monkeypatch):
    """snapshot 返回三引擎键。改动：键集合被改 -> 失败。"""
    for k in ("doris", "duckdb", "pg"):
        fn, _ = _mk_probe(ok=True)
        monkeypatch.setitem(eh._PROBES, k, fn)
    snap = eh.snapshot()
    assert set(snap.keys()) == {"doris", "duckdb", "pg"}


def test_fmt_hhmmss():
    """_fmt 输出 HH:MM:SS 8 位时间串。改动：格式被改 -> 失败。"""
    out = eh._fmt(1700000000.0)
    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", out)
