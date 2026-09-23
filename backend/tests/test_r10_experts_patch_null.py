# -*- coding: utf-8 -*-
"""R3批 R#10 契约测试：experts PATCH 区分「未传/传 null」（exclude_unset）。

R#10 原文：前端 ExpertCardConfigEditor 提交 `llm_connection_id: null`，后端 PATCH 过滤
`if v is not None` ——清空连接被静默吞掉，UI 却报「已保存」（A→B 生效，A→空不生效）。

先红后绿（TDD）——实现前 test_patch_null_clears_connection 红（静默忽略，值残留）：
- 传 null → 字段清空生效
- 未传字段 → 不动（回归守卫：exclude_unset 不得误伤）
- 传 null 与其他字段同批 → 两者都生效
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.experts import router


@pytest.fixture()
def client(monkeypatch, tmp_path):
    """hermetic：tmp SQLite + 种子卡（照 test_expert_card_fields.py 隔离范式）。"""
    import threading as _threading

    import app.core.database as _db
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.models.base import ExpertEvent, ExpertProfile
    from app.services import expert_config as _ec

    eng = create_engine(f"sqlite:///{tmp_path}/r10.db",
                        connect_args={"check_same_thread": False})
    Base = ExpertProfile.metadata
    Base.create_all(eng, tables=[ExpertProfile.__table__, ExpertEvent.__table__])
    TestSess = sessionmaker(bind=eng, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(_db, "SessionLocal", TestSess)
    monkeypatch.setattr(_ec, "_CACHE",
                        {"rows": None, "ts": 0.0, "version": None,
                         "lock": _threading.Lock()})
    seed = TestSess()
    seed.add(ExpertProfile(expert_id="sishu", name="旧名", enabled=True,
                           entry_kind="chat", system_prompt="s",
                           llm_connection_id="conn-a", version=1))
    seed.commit()
    seed.close()

    app = FastAPI()
    app.include_router(router)
    from app.core import auth
    monkeypatch.setattr(auth, "get_current_user", lambda req: None)
    return TestClient(app)


def test_patch_null_clears_connection(client):
    """传 null → 清空生效（实现前：静默忽略=值残留 conn-a，本测红）。"""
    r = client.patch("/api/experts/sishu", json={"llm_connection_id": None})
    assert r.status_code == 200, r.text
    assert r.json().get("llm_connection_id") is None
    card = client.get("/api/experts/sishu").json()
    assert card.get("llm_connection_id") is None


def test_patch_unspecified_fields_untouched(client):
    """未传字段不动（回归守卫：exclude_unset 不得把缺省 None 当成显式清空）。"""
    r = client.patch("/api/experts/sishu", json={"name": "新名"})
    assert r.status_code == 200, r.text
    card = client.get("/api/experts/sishu").json()
    assert card.get("llm_connection_id") == "conn-a"
    assert card.get("name") == "新名"


def test_patch_null_and_field_same_batch(client):
    """传 null 与其他字段同批 → 两者都生效。"""
    r = client.patch("/api/experts/sishu",
                     json={"llm_connection_id": None, "description": "新描述"})
    assert r.status_code == 200, r.text
    card = client.get("/api/experts/sishu").json()
    assert card.get("llm_connection_id") is None
    assert card.get("description") == "新描述"
