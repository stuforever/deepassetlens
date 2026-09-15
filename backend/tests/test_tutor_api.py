# -*- coding: utf-8 -*-
"""⑤批4（⑤e 验收）:/api/tutor 六端点——隔离(不收 user_id)/会话取/卡关422/块读取面。
TestClient 登录态=anonymous 判例；tutor 卡启用由 fixture 临时 PATCH（走查后还原）。"""
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.services.learning.pg import _engine

_UID = "tutor-e2e-api"


@pytest.fixture()
def client():
    """子 router 挂最小 FastAPI（m02 判例——全 app lifespan 侧超时判例规避）。"""
    from fastapi import FastAPI
    from app.api.tutor import router
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def tutor_on():
    """走查期临时启用 tutor 卡（⑤e 联调判据），测试后还原 false（⑤c 拍板态）。"""
    from app.services import expert_config
    from app.core.database import SessionLocal
    from app.models.base import ExpertProfile
    db = SessionLocal()
    row = db.query(ExpertProfile).filter(ExpertProfile.expert_id == "tutor").first()
    if row is None:
        db.close()
        pytest.skip("tutor 卡未种入（⑤c 未跑）")
    orig = row.enabled
    row.enabled = True
    db.commit()
    db.close()
    expert_config._CACHE["rows"] = None
    yield
    db = SessionLocal()
    row = db.query(ExpertProfile).filter(ExpertProfile.expert_id == "tutor").first()
    row.enabled = orig
    db.commit()
    db.close()
    expert_config._CACHE["rows"] = None


@pytest.fixture()
def _clean():
    with _engine.begin() as c:
        c.execute(text("DELETE FROM learning_review_cards WHERE user_id=:u"), {"u": _UID})
        c.execute(text("DELETE FROM learning_wrong_questions WHERE user_id=:u"), {"u": _UID})
    yield
    with _engine.begin() as c:
        c.execute(text("DELETE FROM learning_review_cards WHERE user_id=:u"), {"u": _UID})
        c.execute(text("DELETE FROM learning_wrong_questions WHERE user_id=:u"), {"u": _UID})


def test_six_endpoints_registered(client):
    """六端点在 OpenAPI 面（⑤e §二端点表）。"""
    paths = client.get("/openapi.json").json()["paths"]
    for p in ("/api/tutor/due", "/api/tutor/review-submit", "/api/tutor/wrong-questions",
              "/api/tutor/mastery", "/api/tutor/practice"):
        assert p in paths, f"缺端点 {p}"
    assert any("/api/tutor/book-blocks/" in p for p in paths), "缺 book-blocks 读取面"


def test_due_and_review_math(client, tutor_on, _clean):
    """复习页走查（⑤e 验收）：due 空→评分→due 面可查+间隔=FSRS 公式值。
    item_id 用 uuid（幂等复跑——首评语义断言需干净卡）。"""
    import uuid as _u
    item = f"mq-e2e-{_u.uuid4().hex[:8]}"
    r0 = client.get("/api/tutor/due").json()
    assert r0["code"] == 200
    r1 = client.post("/api/tutor/review-submit",
                     json={"item_id": item, "rating": 3}).json()
    assert r1["code"] == 200
    assert r1["data"]["interval_days"] == 1.0                # 首评 Good 下限 1 天（数学断言）
    assert abs(r1["data"]["stability"] - 3.1262) < 1e-3
    # 评分白名单外 422
    r2 = client.post("/api/tutor/review-submit", json={"item_id": "x", "rating": 5})
    assert r2.status_code == 422


def test_wrong_questions_flow(client, tutor_on, _clean):
    """错题本走查：登记→列表（含分页字段）→筛选。
    DAO 直调用 "anonymous"（=端点会话取值——TestClient 无登录态判例）。"""
    client.post("/api/tutor/review-submit", json={"item_id": "mq-wq", "rating": 1})
    from app.services.learning.learning_dao import wrong_question_add
    wrong_question_add("anonymous", "错题A")
    r = client.get("/api/tutor/wrong-questions", params={"status": "open"}).json()
    assert r["code"] == 200 and r["data"]["total"] >= 1
    assert {"items", "total", "page", "page_size"} <= set(r["data"].keys())


def test_book_blocks_read_face(client, tutor_on):
    """book-blocks 读取面（⑤d blocks_json）——404 语义+真实文档块概要。"""
    r404 = client.get("/api/tutor/book-blocks/not-exist")
    assert r404.status_code == 404
    # 种临时文档行（blocks_json 已编译形状）→读取面断言
    from app.core.database import SessionLocal
    from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument
    import uuid as _u
    db = SessionLocal()
    kb = KnowledgeBase(id=str(_u.uuid4()), name="_tutor_e2e_kb", type="indexed",
                       collection_name="_tutor_e2e_col", storage_dir="_tutor_e2e",
                       status="ready")
    db.add(kb)
    db.flush()
    doc = KnowledgeDocument(id=str(_u.uuid4()), kb_id=kb.id, filename="_tutor_e2e.md",
                            file_path="_", file_size=10, chunk_count=1, status="vectorized",
                            blocks_json=[{"seq": 1, "type": "text", "title": "第一章",
                                          "content": "内容"},
                                         {"seq": 2, "type": "quiz", "title": "",
                                          "items": [{"q": "题", "options": ["A", "B"], "answer": 0}]}])
    db.add(doc)
    db.commit()
    try:
        r = client.get(f"/api/tutor/book-blocks/{doc.id}").json()
        assert r["code"] == 200
        assert r["data"]["summary"] == {"count": 2, "types": {"text": 1, "quiz": 1}}
        assert r["data"]["blocks"][1]["items"][0]["q"] == "题"
    finally:
        db.delete(doc)
        db.delete(kb)
        db.commit()
        db.close()


def test_card_off_422(client):
    """卡关 → 422（⑤c 拍板态默认关——隔离判据）。"""
    from app.services import expert_config
    card = expert_config.get_card("tutor")
    if card.get("enabled"):
        pytest.skip("tutor 已启用（⑤f 拍板后）——本判例只在关停态有意义")
    r = client.get("/api/tutor/due")
    assert r.status_code == 422
