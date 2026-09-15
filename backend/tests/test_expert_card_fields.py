# -*- coding: utf-8 -*-
"""A-1 步骤 1.1：专家卡 suggestions/params 字段（TDD 红先）。

四处一致（计划锚 L34/L51/L70/L185/L206）：body/patch/校验/序列化。
白名单：suggestions ≤5 条每条 ≤120 字；params 键 ⊆ {"fsrs"}，
fsrs 子键 ⊆ {desired_retention, w}。
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.experts import router


@pytest.fixture()
def client(monkeypatch):
    app = FastAPI()
    app.include_router(router)
    # 匿名=admin（auth=0 基线；B 批前执法不拦测试）
    from app.core import auth
    monkeypatch.setattr(auth, "get_current_user", lambda req: None)
    return TestClient(app)


def _patch_card(client, payload):
    return client.patch("/api/experts/tutor", json=payload)


def test_patch_suggestions_ok(client):
    r = _patch_card(client, {"suggestions": ["出三道几何练习", "我今天该复习什么", "看看我的学情画像"]})
    assert r.status_code == 200, r.text
    card = r.json()
    assert card.get("suggestions") == ["出三道几何练习", "我今天该复习什么", "看看我的学情画像"]


def test_patch_suggestions_over_limit_422(client):
    r = _patch_card(client, {"suggestions": [f"建议{i}" for i in range(6)]})
    assert r.status_code == 422, r.text


def test_patch_suggestions_too_long_422(client):
    r = _patch_card(client, {"suggestions": ["长" * 121]})
    assert r.status_code == 422, r.text


def test_patch_params_fsrs_ok(client):
    r = _patch_card(client, {"params": {"fsrs": {"desired_retention": 0.9}}})
    assert r.status_code == 200, r.text
    assert r.json().get("params", {}).get("fsrs", {}).get("desired_retention") == 0.9


def test_patch_params_unknown_key_422(client):
    r = _patch_card(client, {"params": {"ocr": {"x": 1}}})
    assert r.status_code == 422, r.text


def test_patch_params_fsrs_subkey_out_422(client):
    r = _patch_card(client, {"params": {"fsrs": {"desired_retention": 0.9, "w": [1] * 19, "evil": 1}}})
    assert r.status_code == 422, r.text


def test_get_card_serializes_both_fields(client):
    _patch_card(client, {"suggestions": ["甲"], "params": {"fsrs": {"desired_retention": 0.85}}})
    r = client.get("/api/experts/tutor")
    assert r.status_code == 200, r.text
    card = r.json().get("data", r.json())
    assert card.get("suggestions") == ["甲"]
    assert card.get("params", {}).get("fsrs", {}).get("desired_retention") == 0.85
