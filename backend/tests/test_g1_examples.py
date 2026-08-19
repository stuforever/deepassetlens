"""G1 验证示例库测试（融合设计 §4.1）。

覆盖：
  1. 表结构：kg_verified_qa_examples 已建（Base.metadata.create_all 覆盖）
  2. 服务 CRUD：新增/列表/启停/删除
  3. 两级检索：Tier1 DB 精确命中（弱 embedding 环境保底，score=1.0）
  4. 注入负载：build_examples_payload 非空 + 契约 SystemMessage 含参考示例 + _runtime.example_hits
  5. 降级：Qdrant 不可用 / 向量化失败时静默降级（仅 Tier1 / 空块），不阻断
  6. 管理 API：TestClient POST/GET/PATCH/DELETE

运行方式：
    cd backend && python -m pytest tests/test_g1_examples.py -v
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.core.database import SessionLocal, engine
from app.models.base import Base, KgVerifiedQaExample
from app.services.qa_example_service import (
    add_qa_example,
    build_examples_payload,
    delete_qa_example,
    list_qa_examples,
    search_qa_examples,
    set_qa_example_status,
)

_QA = "统计用电客户总数"
_SQL = "SELECT COUNT(*) FROM dim_cst_elec_cons_cust"


@pytest.fixture(scope="module")
def ensure_table():
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def clean_examples(ensure_table):
    def _clean():
        db = SessionLocal()
        try:
            db.query(KgVerifiedQaExample).delete()
            db.commit()
        finally:
            db.close()
        # 同步清理 Qdrant 残留点（防跨测试累积导致 Tier2 误命中）
        try:
            from app.services.qa_example_service import QDRANT_COLLECTION_QA_EXAMPLES
            from app.services.tupu_qdrant_client import TupuQdrantClient
            c = TupuQdrantClient()
            if c.healthcheck():
                c.delete_collection(QDRANT_COLLECTION_QA_EXAMPLES)
        except Exception:
            pass

    _clean()
    yield
    _clean()


def _seed_one(db, q=_QA, sql=_SQL):
    r = add_qa_example(db, question_raw=q, sql=sql, route_type="generic", engine="physical", example_type="golden")
    assert r.get("ok"), r
    return r["id"]


class TestG1TableAndCRUD:
    def test_表已建(self):
        tables = set(inspect(engine).get_table_names())
        assert "kg_verified_qa_examples" in tables

    def test_add_list_status_delete(self):
        db = SessionLocal()
        try:
            eid = _seed_one(db)
            lst = list_qa_examples(db, page=1, size=10)
            assert lst["total"] == 1
            assert lst["items"][0]["status"] == "enabled"
            r = set_qa_example_status(db, eid, "disabled")
            assert r["ok"] and r["status"] == "disabled"
            lst2 = list_qa_examples(db, status="disabled")
            assert lst2["total"] == 1
            r2 = delete_qa_example(db, eid)
            assert r2["ok"]
            assert list_qa_examples(db).get("total") == 0
        finally:
            db.close()


class TestG1Retrieval:
    def test_tier1精确命中(self):
        """Tier1: DB 精确匹配 question_raw == 问题，score=1.0（弱 embedding 保底）。"""
        db = SessionLocal()
        try:
            _seed_one(db)
            hits = search_qa_examples(db, _QA, top=3)
            assert len(hits) == 1
            assert hits[0]["question_raw"] == _QA
            assert hits[0]["score"] == 1.0
            assert hits[0]["sql"] == _SQL
        finally:
            db.close()

    def test_注入块非空(self):
        db = SessionLocal()
        try:
            _seed_one(db)
            payload = build_examples_payload(db, _QA, top=3)
            assert payload["block"], "注入块应为空串"
            assert "参考示例" in payload["block"]
            assert "禁止照抄执行" in payload["block"]
            assert len(payload["hits"]) == 1
        finally:
            db.close()

    def test_契约注入含示例与example_hits(self):
        from app.api.data_intelligence import _build_contract_system_message
        from app.services.query_contract import QueryContract

        db = SessionLocal()
        try:
            _seed_one(db)
        finally:
            db.close()
        qc = QueryContract.generic()
        msg = _build_contract_system_message(qc, question=_QA)
        assert "参考示例" in msg
        assert _SQL in msg
        assert qc._runtime.get("example_hits"), "example_hits 应被记录"


class TestG1Degrade:
    def test_qdrant不可用降级(self, monkeypatch):
        """Qdrant 不可用 -> 仅 Tier1 命中，不抛异常（设计 ⑤：停服问答不受影响）。"""
        import app.services.qa_example_service as svc
        monkeypatch.setattr(svc, "_safe_client", lambda: None)
        db = SessionLocal()
        try:
            _seed_one(db)
            hits = search_qa_examples(db, _QA, top=3)
            assert len(hits) == 1 and hits[0]["score"] == 1.0
            # 未命中精确问题时为空，不崩
            assert search_qa_examples(db, "完全不同的问题xyz", top=3) == []
        finally:
            db.close()

    def test_向量化失败降级(self, monkeypatch):
        """向量化失败 -> 仅 Tier1；无精确命中时为空，不崩。"""
        import app.services.qa_example_service as svc
        monkeypatch.setattr(svc, "_embed_question", lambda *a, **k: [])
        db = SessionLocal()
        try:
            _seed_one(db)
            assert len(search_qa_examples(db, _QA, top=3)) == 1
            assert search_qa_examples(db, "另一个问题", top=3) == []
        finally:
            db.close()


class TestG1AdminAPI:
    def test_crud_api(self):
        from app.main import app

        tc = TestClient(app)
        r = tc.post("/api/v1/qa-examples", json={
            "question_raw": _QA, "sql": _SQL, "route_type": "generic", "engine": "physical", "example_type": "golden"})
        assert r.status_code == 200
        eid = r.json()["data"]["id"]
        assert tc.get("/api/v1/qa-examples").json()["data"]["total"] == 1
        assert tc.patch(f"/api/v1/qa-examples/{eid}/status", json={"status": "disabled"}).status_code == 200
        assert tc.delete(f"/api/v1/qa-examples/{eid}").status_code == 200
        assert tc.get("/api/v1/qa-examples").json()["data"]["total"] == 0
