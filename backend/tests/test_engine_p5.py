"""test_engine_p5.py - 数据引擎增强 P5（预聚合加速器）

覆盖（mock doris execute，不触达真实 Doris）：
- try_serve 单值聚合拦截：SELECT COUNT(*) FROM src 命中 -> 加速返回 + 标注
- 不拦截：WHERE/GROUP BY/JOIN、非聚合、未知表、陈旧未刷新
- refresh_accelerator：INSERT OVERWRITE 尝试 + CREATE TABLE AS 兜底 + 状态更新
"""
import pytest

from app.core.database import SessionLocal
from app.models.base import EngineAccelerator
from app.services import engine_accelerator


@pytest.fixture
def acc_row():
    """在测试库建一个临时加速器行，测完删除。"""
    # 确保表存在（测试进程不跑 create_all）
    from app.core.database import engine
    from app.models.base import Base
    Base.metadata.create_all(engine, tables=[EngineAccelerator.__table__])
    acc = EngineAccelerator(
        name="测试客户总数", source_tables=["t_acc_test_src"],
        agg_expr="COUNT(*)", agg_col="customer_total",
        target_db="test_db", target_table="agg_customer_total_t",
        refresh_sql="SELECT COUNT(*) AS customer_total FROM test_db.dim_cst_elec_cons_cust",
        refresh_minutes=60, enabled=True,
    )
    db = SessionLocal()
    try:
        db.add(acc)
        db.commit()
        db.refresh(acc)
        acc_id = acc.id
    finally:
        db.close()
    yield acc_id
    db = SessionLocal()
    try:
        db.query(EngineAccelerator).filter(EngineAccelerator.id == acc_id).delete()
        db.commit()
    finally:
        db.close()


def _fake_doris_execute(result):
    def fake(sql):
        return dict(result)
    return fake


class TestTryServe:
    def test_hit_single_value_agg(self, monkeypatch, acc_row):
        # 先标记已刷新（新鲜）
        db = SessionLocal()
        try:
            a = db.query(EngineAccelerator).filter(EngineAccelerator.id == acc_row).first()
            from datetime import datetime
            a.last_refresh_at = datetime.now()
            db.commit()
        finally:
            db.close()
        monkeypatch.setattr("app.services.doris_engine.execute_sql", _fake_doris_execute(
            {"columns": ["customer_total"], "rows": [[10]], "row_count": 1}))
        res = engine_accelerator.try_serve("SELECT COUNT(*) FROM t_acc_test_src")
        assert res is not None
        assert res["accelerated"] is True
        assert res["accelerator"]["name"] == "测试客户总数"
        assert res["data_as_of"] is not None

    def test_hit_with_alias(self, monkeypatch, acc_row):
        db = SessionLocal()
        try:
            a = db.query(EngineAccelerator).filter(EngineAccelerator.id == acc_row).first()
            from datetime import datetime
            a.last_refresh_at = datetime.now()
            db.commit()
        finally:
            db.close()
        monkeypatch.setattr("app.services.doris_engine.execute_sql", _fake_doris_execute(
            {"columns": ["n"], "rows": [[10]], "row_count": 1}))
        res = engine_accelerator.try_serve("SELECT COUNT(*) AS n FROM t_acc_test_src")
        assert res is not None and res["accelerated"] is True

    def test_no_intercept_with_where(self, monkeypatch, acc_row):
        monkeypatch.setattr("app.services.doris_engine.execute_sql", _fake_doris_execute({}))
        assert engine_accelerator.try_serve(
            "SELECT COUNT(*) FROM t_acc_test_src WHERE cust_type='大工业'") is None

    def test_no_intercept_group_by(self, monkeypatch, acc_row):
        assert engine_accelerator.try_serve(
            "SELECT cust_type, COUNT(*) FROM t_acc_test_src GROUP BY cust_type") is None

    def test_no_intercept_unknown_table(self, monkeypatch, acc_row):
        assert engine_accelerator.try_serve("SELECT COUNT(*) FROM some_other_table") is None

    def test_no_intercept_stale(self, monkeypatch, acc_row):
        """从未刷新 -> 视为过期不拦截。"""
        monkeypatch.setattr("app.services.doris_engine.execute_sql", _fake_doris_execute({}))
        res = engine_accelerator.try_serve("SELECT COUNT(*) FROM t_acc_test_src")
        assert res is None

    def test_no_intercept_wrong_agg(self, monkeypatch, acc_row):
        db = SessionLocal()
        try:
            a = db.query(EngineAccelerator).filter(EngineAccelerator.id == acc_row).first()
            from datetime import datetime
            a.last_refresh_at = datetime.now()
            db.commit()
        finally:
            db.close()
        # SUM(col) 不匹配 COUNT(*)
        assert engine_accelerator.try_serve(
            "SELECT SUM(cust_id) FROM t_acc_test_src") is None

    def test_cross_catalog_guard(self, monkeypatch):
        """跨 catalog 同名表防护：显式带 catalog 且 != 加速器目标 catalog -> 不拦截
        （防止 pg_tupu 等目录的 COUNT 被 internal 预聚合值 10 顶替——M4 计数金标 3/10 摇摆根因）。"""
        from app.core.database import engine as _e
        from app.models.base import Base
        Base.metadata.create_all(_e, tables=[EngineAccelerator.__table__])
        acc = EngineAccelerator(
            name="catalog 防护测试", source_tables=["t_acc_cat_src"],
            agg_expr="COUNT(*)", agg_col="customer_total",
            target_db="test_db", target_table="agg_cat_t", target_catalog="internal",
            refresh_sql="SELECT COUNT(*) FROM test_db.t_acc_cat_src",
            refresh_minutes=60, enabled=True,
        )
        db = SessionLocal()
        try:
            db.add(acc)
            db.commit()
            db.refresh(acc)
            acc_id = acc.id
            from datetime import datetime
            acc.last_refresh_at = datetime.now()
            db.commit()
        finally:
            db.close()
        monkeypatch.setattr("app.services.doris_engine.execute_sql", _fake_doris_execute(
            {"columns": ["n"], "rows": [[10]], "row_count": 1}))
        try:
            # 裸表名（默认 internal 目录，冒烟锚点语义）-> 拦截
            r = engine_accelerator.try_serve("SELECT COUNT(*) FROM t_acc_cat_src")
            assert r is not None and r["accelerated"] is True
            # 显式匹配目录 internal -> 拦截
            r2 = engine_accelerator.try_serve("SELECT COUNT(*) FROM internal.test_db.t_acc_cat_src")
            assert r2 is not None and r2["accelerated"] is True
            # 显式其他目录（三段式 catalog.db.table，如 pg_tupu.public.*）-> 不拦截（同名表是不同实体）
            assert engine_accelerator.try_serve(
                "SELECT COUNT(*) FROM pg_tupu.test_db.t_acc_cat_src") is None
        finally:
            db = SessionLocal()
            try:
                db.query(EngineAccelerator).filter(EngineAccelerator.id == acc_id).delete()
                db.commit()
            finally:
                db.close()


class TestRefresh:
    def test_refresh_insert_overwrite(self, monkeypatch, acc_row):
        """目标表存在 -> INSERT OVERWRITE；不存在 -> CREATE TABLE AS 兜底。"""
        from app.services import doris_engine
        class _Cur:
            def __init__(self):
                self.log = []
                self.fail_once = False
            def execute(self, sql):
                self.log.append(sql)
                if sql.startswith("INSERT OVERWRITE"):
                    raise RuntimeError("table not exists")
        cur = _Cur()
        class _Conn:
            def cursor(self):
                return cur
            def close(self):
                pass
            def commit(self):
                pass
        monkeypatch.setattr(doris_engine, "get_conn", lambda: _Conn())
        r = engine_accelerator.refresh_accelerator(acc_row)
        assert r["ok"] is True
        assert any(s.startswith("INSERT OVERWRITE") for s in cur.log)
        assert any(s.startswith("CREATE TABLE") for s in cur.log)
        assert r["accelerator"]["last_status"] == "ok"
        assert r["accelerator"]["last_refresh_at"] is not None
