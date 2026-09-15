# -*- coding: utf-8 -*-
"""⑤补补-1 步骤 1.1：课程骨架 TDD 首批——questions CRUD 四测+图谱种子幂等测。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    from app.api.tutor_admin import router
    from app.core import auth
    app = FastAPI()
    app.include_router(router)
    # auth=0 基线：匿名=admin（get_current_user 真实路径由 conftest 外环境保证；
    # TestClient 无认证头——auth=0 下 get_current_user 返回 anonymous admin）
    monkeypatch.setattr(auth, "_ENABLE_AUTH", False, raising=False)
    return TestClient(app)


def test_questions_requires_admin(monkeypatch):
    """admin 门：auth=1 且非 admin → 403（执法点在端点依赖）。"""
    from app.api import tutor_admin
    from app.core.auth import AuthUser

    app = FastAPI()
    app.include_router(tutor_admin.router)
    # 构造非 admin 登录态——patch tutor_admin 模块命名空间内的引用（import 时已绑定）
    u = AuthUser(sub="u1", roles=["user"], username="u1", email="u1@x", groups=[])
    monkeypatch.setattr(tutor_admin, "get_current_user", lambda req: u)
    c = TestClient(app)
    r = c.get("/api/tutor-admin/questions")
    assert r.status_code == 403, r.text


def test_question_create_update_delete_roundtrip(client):
    """建改删回环：POST→PUT→DELETE→GET 404。"""
    body = {"title": "负数判断母题", "archetype_text": "判断 -3 是正数还是负数",
            "knowledge_point_id": "kp:正数与负数"}
    r = client.post("/api/tutor-admin/questions", json=body)
    assert r.status_code == 200, r.text
    mq = r.json().get("data") or r.json()
    mq_id = mq.get("mq_id")
    assert mq_id

    r2 = client.put(f"/api/tutor-admin/questions/{mq_id}", json={"title": "负数判断母题（改）"})
    assert r2.status_code == 200, r2.text

    r3 = client.delete(f"/api/tutor-admin/questions/{mq_id}")
    assert r3.status_code == 200, r3.text
    r4 = client.get("/api/tutor-admin/questions", params={"kp": "kp:正数与负数"})
    ids = [x.get("mq_id") for x in (r4.json().get("data") or {}).get("items", [])]
    assert mq_id not in ids


def test_question_kp_required_422(client):
    """kp 必填：knowledge_point_id 缺失 → 422。"""
    r = client.post("/api/tutor-admin/questions",
                    json={"title": "无 kp 母题", "archetype_text": "题干"})
    assert r.status_code == 422, r.text


def test_seed_curriculum_idempotent():
    """图谱种子幂等：同脚本跑两遍——教材/章节/KP 节点数不变+母题 ≥3。"""
    from scripts import seed_tutor_curriculum as seed

    seed.main()
    n1 = seed.count_nodes()
    m1 = seed.count_mother_questions()
    seed.main()
    n2 = seed.count_nodes()
    m2 = seed.count_mother_questions()
    assert n1 == n2, f"图谱节点数漂移: {n1} -> {n2}"
    assert m2 >= 3, f"母题种子不足 3: {m2}"
    assert m1 == m2, f"母题数漂移: {m1} -> {m2}"


# ---------- ⑤补补-5：错题全套 ----------

WQ_UID = "tdd-wq-user"


def test_wrong_question_columns_idempotent():
    """扩列幂等：ensure_columns 跑两遍——列集不变（+4 列存在）。"""
    from app.services.learning import pg as pg_mod

    pg_mod._ensure_wrong_question_columns()
    cols1 = _wq_columns()
    pg_mod._ensure_wrong_question_columns()
    cols2 = _wq_columns()
    assert cols1 == cols2
    for col in ("question", "my_answer", "error_type", "source"):
        assert col in cols1, f"缺列 {col}"


def _wq_columns() -> set:
    from app.services.learning.pg import _engine
    from sqlalchemy import text
    with _engine.begin() as c:
        rows = c.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='learning_wrong_questions'")).mappings().all()
    return {r["column_name"] for r in rows}


def test_wrong_question_add_backward_compatible(clean_wq):
    """扩参兼容：旧两参调用不破（新列 NULL，旧行为不变）。"""
    from app.services.learning import learning_dao as dao
    wq_id = dao.wrong_question_add(WQ_UID, "旧式变式题", mother_question_id="mq-seed-0001")
    assert wq_id
    rows = dao.wrong_question_query(WQ_UID)
    row = next(r for r in rows if r["wq_id"] == wq_id)
    assert row["status"] == "open"


@pytest.fixture()
def clean_wq():
    from app.services.learning.pg import _engine, ensure_tables
    from sqlalchemy import text
    ensure_tables()                                # TestClient 不走 main startup——先建列
    with _engine.begin() as c:
        c.execute(text("DELETE FROM learning_wrong_questions WHERE user_id=:u"), {"u": WQ_UID})
        c.execute(text("DELETE FROM learning_review_cards WHERE user_id=:u"), {"u": WQ_UID})
        c.execute(text("DELETE FROM learning_review_records WHERE user_id=:u"), {"u": WQ_UID})
        c.execute(text("DELETE FROM learning_mother_questions WHERE knowledge_point_id=:kp"),
                  {"kp": "kp:tdd隔离知识点"})
    yield
    with _engine.begin() as c:
        c.execute(text("DELETE FROM learning_wrong_questions WHERE user_id=:u"), {"u": WQ_UID})
        c.execute(text("DELETE FROM learning_review_cards WHERE user_id=:u"), {"u": WQ_UID})
        c.execute(text("DELETE FROM learning_review_records WHERE user_id=:u"), {"u": WQ_UID})
        c.execute(text("DELETE FROM learning_mother_questions WHERE knowledge_point_id=:kp"),
                  {"kp": "kp:tdd隔离知识点"})


def test_wrong_question_add_structured(clean_wq):
    """对话式录入落库：question JSON/my_answer/error_type/source 全字段回读。"""
    from app.services.learning import learning_dao as dao
    q = {"stem": "判断 -3 是什么数", "options": [], "correct_answer": "负数"}
    wq_id = dao.wrong_question_add(
        WQ_UID, "判断 -3 是什么数", mother_question_id="mq-seed-0001",
        question=q, my_answer="正数", error_type="concept", source="chat")
    rows = dao.wrong_question_query(WQ_UID)
    row = next(r for r in rows if r["wq_id"] == wq_id)
    assert row["source"] == "chat"
    assert row["error_type"] == "concept"
    assert row["my_answer"] == "正数"
    assert row["question"]["correct_answer"] == "负数"


def test_mother_question_find_or_create(clean_wq):
    """find_or_create 两态：新建→二次同关键词命中（同 mq_id）——用无种子 kp 隔离。"""
    from app.services.learning import learning_dao as dao
    kp = "kp:tdd隔离知识点"
    mq1 = dao.mother_question_find_or_create("测试专有关键词XYZ", knowledge_point_id=kp,
                                             title="测试母题（自动）", archetype_text="分类题干")
    assert mq1.get("created") is True and mq1.get("mq_id")
    mq2 = dao.mother_question_find_or_create("测试专有关键词XYZ", knowledge_point_id=kp)
    assert mq2.get("created") is False and mq2.get("mq_id") == mq1["mq_id"]
