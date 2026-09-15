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
