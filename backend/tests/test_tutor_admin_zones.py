# -*- coding: utf-8 -*-
"""附件四 A-3 步骤 1：progress 跨用户看板 + schedule 生效参数/覆写（admin 门）。"""
import pytest
from fastapi.testclient import TestClient

from app.core.auth import AuthUser
from app.services.learning.pg import ensure_tables, _engine
from sqlalchemy import text

ADMIN = AuthUser(sub="tdd-admin", roles=["admin"], username="admin", email="a@x", groups=[])
USER = AuthUser(sub="tdd-user", roles=["user"], username="u", email="u@x", groups=[])


@pytest.fixture()
def client():
    ensure_tables()
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.tutor_admin as ta
    app = FastAPI()
    app.include_router(ta.router)
    ta.get_current_user = lambda request: ADMIN     # 裸 app 挂 router——admin 门直接放行
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def clean_progress():
    yield
    with _engine.begin() as c:
        c.execute(text("DELETE FROM learning_review_cards WHERE user_id LIKE 'tdd-pa-%'"))
        c.execute(text("DELETE FROM learning_review_records WHERE user_id LIKE 'tdd-pa-%'"))


def test_progress_requires_admin(client):
    import app.api.tutor_admin as ta
    orig = ta.get_current_user
    ta.get_current_user = lambda request: USER
    try:
        r = client.get("/api/tutor-admin/progress")
        assert r.status_code == 403
    finally:
        ta.get_current_user = orig


def test_progress_aggregate(client, clean_progress):
    from app.services.learning.learning_dao import upsert_card, fsrs_new_card
    import time
    st = fsrs_new_card(3, time.time())
    upsert_card("tdd-pa-a", "mother_question", "kp:正数与负数", st)
    import app.api.tutor_admin as ta
    orig = ta.get_current_user
    ta.get_current_user = lambda request: ADMIN
    try:
        r = client.get("/api/tutor-admin/progress")
        assert r.status_code == 200
        items = r.json()["data"]["items"]
        row = next((x for x in items if x["user_id"] == "tdd-pa-a"), None)
        assert row and row["cards"] >= 1 and "mastery" in row
    finally:
        ta.get_current_user = orig


def test_schedule_get_put_roundtrip(client):
    import app.api.tutor_admin as ta
    orig = ta.get_current_user
    ta.get_current_user = lambda request: ADMIN
    try:
        r0 = client.get("/api/tutor-admin/schedule")
        assert r0.status_code == 200
        d0 = r0.json()["data"]
        assert d0["defaults"]["desired_retention"] == 0.9 and len(d0["defaults"]["w"]) == 19
        # 覆写 desired_retention
        r1 = client.put("/api/tutor-admin/schedule", json={"desired_retention": 0.85})
        assert r1.status_code == 200
        d1 = r1.json()["data"]["effective"]
        assert d1["desired_retention"] == 0.85
        # fsrs 算法面消费覆写（active_target）
        from app.services.learning.fsrs import active_target
        assert abs(active_target() - 0.85) < 1e-6
        # 复原（清覆写——恢复默认）
        from app.services.expert_config import get_card, update_card
        card = get_card("tutor") or {}
        params = dict(card.get("params") or {})
        params.pop("fsrs", None)
        update_card("tutor", params=params, updated_by="tdd-restore")
        assert abs(active_target() - 0.9) < 1e-6
    finally:
        ta.get_current_user = orig


def test_schedule_validation(client):
    import app.api.tutor_admin as ta
    orig = ta.get_current_user
    ta.get_current_user = lambda request: ADMIN
    try:
        assert client.put("/api/tutor-admin/schedule", json={}).status_code == 422
        assert client.put("/api/tutor-admin/schedule", json={"desired_retention": 1.5}).status_code == 422
        assert client.put("/api/tutor-admin/schedule", json={"w": [1, 2, 3]}).status_code == 422
    finally:
        ta.get_current_user = orig
