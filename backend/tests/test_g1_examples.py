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

_QA = "test_g1_统计用电客户总数"  # 测试专属问题（不与生产种子金标同题，避免 Tier1 命中冲突）
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
            # 只清测试自建行（sql 打点 _SQL），严禁触碰生产示例（真实种子金标/用户确认）
            db.query(KgVerifiedQaExample).filter(KgVerifiedQaExample.sql == _SQL).delete(synchronize_session=False)
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
            # 生产示例共存时不依赖绝对 total：断言测试行存在且默认 enabled
            row = next((i for i in lst["items"] if i["id"] == eid), None)
            assert row and row["status"] == "enabled"
            r = set_qa_example_status(db, eid, "disabled")
            assert r["ok"] and r["status"] == "disabled"
            lst2 = list_qa_examples(db, status="disabled")
            assert any(i["id"] == eid for i in lst2["items"])
            r2 = delete_qa_example(db, eid)
            assert r2["ok"]
            lst3 = list_qa_examples(db)
            assert all(i["id"] != eid for i in lst3["items"])
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

    def test_契约注入含金标与golden_hits(self):
        """批13-C：运行时契约注入切金标（golden_hits；示例库退役不再注入）。"""
        from app.api.data_intelligence import _build_contract_system_message
        from app.services.query_contract import QueryContract
        from app.models.base import KgGoldenQaSet

        _QG = "test_g1c_统计用电客户总数"
        _QG_SQL = "SELECT COUNT(*) FROM dim_cst_elec_cons_cust"
        db = SessionLocal()
        try:
            db.query(KgGoldenQaSet).filter(KgGoldenQaSet.question == _QG).delete(synchronize_session=False)
            db.add(KgGoldenQaSet(id="test-g1c-gold", question=_QG, expected_sql=_QG_SQL,
                                 expected_result_digest={"row_count": 1, "first_row_hash": "x"},
                                 route_type="generic", engine="doris", enabled=True))
            db.commit()
        finally:
            db.close()
        try:
            qc = QueryContract.generic()
            msg = _build_contract_system_message(qc, question=_QG)
            assert "金标锚定" in msg
            assert _QG_SQL in msg
            assert qc._runtime.get("golden_hits"), "golden_hits 应被记录"
        finally:
            db = SessionLocal()
            try:
                db.query(KgGoldenQaSet).filter(KgGoldenQaSet.id == "test-g1c-gold").delete(synchronize_session=False)
                db.commit()
            finally:
                db.close()


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
        """批13-C：qa-examples API 下线（410 deprecation 壳）；golden-qa CRUD 正常。"""
        from app.main import app

        tc = TestClient(app)
        # 示例库端点已 410
        assert tc.post("/api/v1/qa-examples", json={"question_raw": _QA, "sql": _SQL}).status_code == 200
        body = tc.post("/api/v1/qa-examples", json={"question_raw": _QA, "sql": _SQL}).json()
        assert body.get("code") == 410
        # 金标 CRUD（显式 digest 绕过 SQL 执行；同步向量失败仅告警不阻断）
        r = tc.post("/api/v1/golden-qa", json={
            "question": "test_g1c_金标CRUD专用问题", "expected_sql": _SQL,
            "expected_result_digest": {"row_count": 1, "first_row_hash": "x"},
            "route_type": "generic"})
        assert r.status_code == 200 and r.json().get("ok") is True
        gid = r.json()["id"]
        lst = tc.get("/api/v1/golden-qa").json()["data"]["items"]
        assert any(i["id"] == gid for i in lst)
        assert tc.patch(f"/api/v1/golden-qa/{gid}", json={"enabled": False}).status_code == 200
        assert tc.delete(f"/api/v1/golden-qa/{gid}").status_code == 200
        lst2 = tc.get("/api/v1/golden-qa").json()["data"]["items"]
        assert all(i["id"] != gid for i in lst2)
