"""S4 示例库运营测试（问数稳定性与体验_S阶段细化设计_20260820 §五）。

覆盖：
  1. S4a 命中事件落库：bump_hit_count 写 kg_example_hit_logs + 累计 hit_count + last_used_at
  2. S4a 30 天命中：list_qa_examples 的 hit_count_30d（近 30 天窗口，越界不算）
  3. S4a 相似预览：find_similar_examples 示例不存在/Qdrant 不可用 -> []（不抛）
  4. S4b 精确匹配直通：question_raw 带标点差异仍命中（normalize_text 规范化比较，score=1.0）
  5. S4b 阈值 env 化：TUPU_EXAMPLE_SIM_THRESHOLD 生效（默认 0.75）
  6. S4a 管理 API：GET /qa-examples/{id}/similar

运行方式：
    cd backend && python -m pytest tests/test_s4_examples_ops.py -v
"""
import os
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.core.database import SessionLocal, engine
from app.models.base import Base, KgExampleHitLog, KgVerifiedQaExample
from app.services.qa_example_service import (
    add_qa_example,
    bump_hit_count,
    find_similar_examples,
    list_qa_examples,
    search_qa_examples,
)

_QA = "test_s4_统计各电压等级客户分布"
_SQL = "SELECT voltage_level, COUNT(*) FROM dim_cst_elec_cons_cust GROUP BY voltage_level"


@pytest.fixture(scope="module")
def ensure_table():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def clean_rows(ensure_table):
    def _clean():
        db = SessionLocal()
        try:
            rows = db.query(KgVerifiedQaExample).filter(
                KgVerifiedQaExample.question_raw.like("test_s4_%")).all()
            ids = [str(r.id) for r in rows]
            for r in rows:
                db.delete(r)
            if ids:
                db.query(KgExampleHitLog).filter(
                    KgExampleHitLog.example_id.in_(ids)).delete(synchronize_session=False)
            db.commit()
        finally:
            db.close()

    _clean()
    yield
    _clean()


def _seed_one(db, q=_QA):
    r = add_qa_example(db, question_raw=q, sql=_SQL, route_type="generic", engine="physical", example_type="golden")
    assert r.get("ok"), r
    return r["id"]


class TestS4HitLog:
    def test_bump写命中事件与累计计数(self):
        db = SessionLocal()
        try:
            eid = _seed_one(db)
            assert db.query(KgExampleHitLog).filter(KgExampleHitLog.example_id == eid).count() == 0
            bump_hit_count(db, [eid])
            row = db.query(KgVerifiedQaExample).filter(KgVerifiedQaExample.id == eid).first()
            assert row.hit_count == 1
            assert row.last_used_at is not None
            assert db.query(KgExampleHitLog).filter(KgExampleHitLog.example_id == eid).count() == 1
            # 二次命中 -> 2 事件
            bump_hit_count(db, [eid, eid])  # 入参去重 -> 计 1 次
            assert db.query(KgExampleHitLog).filter(KgExampleHitLog.example_id == eid).count() == 2
            assert db.query(KgVerifiedQaExample).filter(KgVerifiedQaExample.id == eid).first().hit_count == 2
        finally:
            db.close()

    def test_list返回30天命中列(self):
        db = SessionLocal()
        try:
            eid = _seed_one(db)
            lst = list_qa_examples(db, page=1, size=100)
            row = next(i for i in lst["items"] if i["id"] == eid)
            assert "hit_count_30d" in row and row["hit_count_30d"] == 0
            bump_hit_count(db, [eid])
            lst2 = list_qa_examples(db, page=1, size=100)
            row2 = next(i for i in lst2["items"] if i["id"] == eid)
            assert row2["hit_count_30d"] == 1
        finally:
            db.close()

    def test_30天窗口外不计(self):
        """30 天命中只统计近 30 天事件：插入一条 40 天前的命中事件不计入。"""
        db = SessionLocal()
        try:
            eid = _seed_one(db)
            old = datetime.utcnow() - timedelta(days=40)
            db.add(KgExampleHitLog(example_id=eid, created_at=old))
            db.commit()
            bump_hit_count(db, [eid])  # 1 条今天的事件
            lst = list_qa_examples(db, page=1, size=100)
            row = next(i for i in lst["items"] if i["id"] == eid)
            assert row["hit_count"] == 1          # 累计命中只数 bump 的那次（旧事件未走 bump）
            assert row["hit_count_30d"] == 1      # 40 天前事件不计
        finally:
            db.close()


class TestS4ExactPassThrough:
    def test_带标点差异精确命中(self):
        """S4b 直通：question_raw「统计各电压等级客户分布」vs 输入「统计各电压等级客户分布。」（带句号）-> score=1.0。"""
        db = SessionLocal()
        try:
            _seed_one(db)
            hits = search_qa_examples(db, _QA + "。", top=3)
            assert hits and hits[0]["score"] == 1.0
            assert hits[0]["question_raw"] == _QA
        finally:
            db.close()

    def test_阈值env化(self):
        import app.services.qa_example_service as svc
        os.environ["TUPU_EXAMPLE_SIM_THRESHOLD"] = "0.9"
        try:
            assert svc._score_threshold() == 0.9
        finally:
            os.environ.pop("TUPU_EXAMPLE_SIM_THRESHOLD", None)
        assert svc._score_threshold() == 0.75  # 默认


class TestS4Similar:
    def test_示例不存在返回空(self):
        db = SessionLocal()
        try:
            assert find_similar_examples(db, "not-exist-id", top=5) == []
        finally:
            db.close()

    def test_qdrant不可用降级为空(self, monkeypatch):
        import app.services.qa_example_service as svc
        monkeypatch.setattr(svc, "_safe_client", lambda: None)
        db = SessionLocal()
        try:
            eid = _seed_one(db)
            assert find_similar_examples(db, eid, top=5) == []
        finally:
            db.close()

    def test_similar_api(self, monkeypatch):
        """Qdrant 不可用 -> similar 端点仍 200 且 items=[]（不抛）。"""
        import app.services.qa_example_service as svc
        monkeypatch.setattr(svc, "_safe_client", lambda: None)
        from app.main import app

        db = SessionLocal()
        try:
            eid = _seed_one(db)
        finally:
            db.close()
        tc = TestClient(app)
        r = tc.get(f"/api/v1/qa-examples/{eid}/similar")
        assert r.status_code == 200
        assert r.json()["data"]["items"] == []


class TestS4Table:
    def test_命中事件表已建(self):
        tables = set(inspect(engine).get_table_names())
        assert "kg_example_hit_logs" in tables
