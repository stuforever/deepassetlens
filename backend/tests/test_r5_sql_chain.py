# -*- coding: utf-8 -*-
"""R5批②（清单安全）契约测试：SQL 执行信任链模块级只读防线。

- build_execute_query_fn._execute：DELETE/UPDATE/DROP 拒绝（原仅靠调用方自觉校验）
- 校验先于引擎获取（校验拦截不触库）
- sql_db_helper.run_sql：非只读 SQL 返回空串（原 docstring 虚假声明「自动 LIMIT 保护」）
变异锚点：模块级校验删除 → 前两测红；run_sql 门删除 → 第三测红。
"""
import pytest


def test_execute_rejects_non_select():
    from app.services.sql_executor import build_execute_query_fn
    fn = build_execute_query_fn()
    for bad in ("DELETE FROM t", "UPDATE t SET a=1", "DROP TABLE t",
                "INSERT INTO t VALUES (1)"):
        with pytest.raises(ValueError):
            fn(bad)


def test_execute_gate_runs_for_every_sql(monkeypatch):
    """校验门对每次执行都先跑（含被拒 SQL）——模块级防线实证。"""
    called = {}
    import app.services.secure_query_executor as _sqe
    _real = _sqe.validate_sql

    def _spy(sql, **k):
        called["sql"] = sql
        return _real(sql, **k)

    monkeypatch.setattr(_sqe, "validate_sql", _spy)
    from app.services.sql_executor import build_execute_query_fn
    fn = build_execute_query_fn()
    with pytest.raises(ValueError):
        fn("DELETE FROM t")
    assert called.get("sql") == "DELETE FROM t"


def test_run_sql_rejects_non_readonly():
    from app.services.sql_db_helper import run_sql
    assert run_sql("DELETE FROM t") == ""
    assert run_sql("DROP TABLE t") == ""
