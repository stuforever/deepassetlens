# -*- coding: utf-8 -*-
"""⑥-2a（用户权限与专家赋权）：expert ACL 执法测试。

B-0 首测：twin 用户解析随请求变（两请求两 user——共享桶不再恒 anonymous，spec A6 冒烟前置）。
B-1 将扩执法四测（列表过滤/chat 403/专家域同检/回权即时）。
"""
import json
import time

import pytest

from app.services.learning.pg import ensure_tables, _engine
from app.services.memory_runtime import set_runtime, reset
from sqlalchemy import text

U1 = "tdd-twin-u1"
U2 = "tdd-twin-u2"


@pytest.fixture()
def clean_twin():
    ensure_tables()
    yield
    with _engine.begin() as c:
        for u in (U1, U2):
            c.execute(text("DELETE FROM learning_wrong_questions WHERE user_id=:u"), {"u": u})


def test_twin_user_resolves_per_request(clean_twin):
    """两请求两 user：twin 写面随 runtime ContextVar 落各自名下——隔离断言。"""
    from app.services.learning.tutor_inprocess import build_inprocess_tutor_tools
    twins = {t.name: t for t in build_inprocess_tutor_tools()}
    add = twins["wrong_question_add"]
    query = twins["wrong_question_query"]

    set_runtime("tutor", U1, "s1", "t1")
    r1 = json.loads(add.invoke({"variant_text": "u1 专属错题题面"}))
    assert r1.get("wq_id")
    q1 = json.loads(query.invoke({}))
    assert any("u1 专属" in x["variant_text"] for x in q1["items"])
    reset()

    set_runtime("tutor", U2, "s2", "t2")
    add.invoke({"variant_text": "u2 专属错题题面"})
    q2 = json.loads(query.invoke({}))
    texts2 = json.dumps(q2, ensure_ascii=False)
    assert "u2 专属" in texts2 and "u1 专属" not in texts2      # u2 面看不到 u1 的
    reset()


def test_twin_fail_closed_without_runtime():
    """runtime 未置位→fail-closed 拒执行（绝不静默落 anonymous 共享桶——🔴-4）。"""
    from app.services.learning.tutor_inprocess import build_inprocess_tutor_tools
    twins = {t.name: t for t in build_inprocess_tutor_tools()}
    with pytest.raises(RuntimeError):
        twins["wrong_question_query"].invoke({})


# ---------- ⑥-2a B-1：expert 进 ACL——执法四测 ----------

def _mk_user(sub, roles):
    from app.core.auth import AuthUser
    return AuthUser(sub=sub, roles=roles, username=sub, email=f"{sub}@x", groups=[])


def _seed_wenshu_grant():
    """公共种子行直插（与 init_db._seed_expert_acl 同语义）——测试自足。MySQL auth 库。"""
    from app.core.database import SessionLocal
    from app.models.auth import ResourceACL
    db = SessionLocal()
    try:
        if not (db.query(ResourceACL)
                .filter(ResourceACL.resource_type == "expert",
                        ResourceACL.resource_id == "wenshu",
                        ResourceACL.principal_type == "role",
                        ResourceACL.principal_id == "viewer").first()):
            db.add(ResourceACL(resource_type="expert", resource_id="wenshu",
                               principal_type="role", principal_id="viewer",
                               actions=["use"], granted_by="test"))
            db.commit()
    finally:
        db.close()


def _grant_expert(sub, slug, actions):
    from app.core.database import SessionLocal
    from app.models.auth import ResourceACL
    db = SessionLocal()
    try:
        db.query(ResourceACL).filter(ResourceACL.resource_type == "expert",
                                     ResourceACL.resource_id == slug,
                                     ResourceACL.principal_type == "user",
                                     ResourceACL.principal_id == sub).delete()
        db.add(ResourceACL(resource_type="expert", resource_id=slug,
                           principal_type="user", principal_id=sub,
                           actions=actions, granted_by="test"))
        db.commit()
    finally:
        db.close()


def _revoke_expert(sub, slug):
    from app.core.database import SessionLocal
    from app.models.auth import ResourceACL
    db = SessionLocal()
    try:
        db.query(ResourceACL).filter(ResourceACL.resource_type == "expert",
                                     ResourceACL.resource_id == slug,
                                     ResourceACL.principal_type == "user",
                                     ResourceACL.principal_id == sub).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture()
def acl_env(monkeypatch):
    """auth=1 语义环境：ENABLE_AUTH 翻真+当前用户可切换+裸 app 挂 experts/tutor 路由。"""
    import app.core.auth as core_auth
    import app.services.expert_auth as ea
    monkeypatch.setattr(core_auth, "ENABLE_AUTH", True, raising=False)
    monkeypatch.setattr(ea, "ENABLE_AUTH", True, raising=False)
    ensure_tables()
    _seed_wenshu_grant()
    _cleanup_test_grants()
    yield ea
    _cleanup_test_grants()
    monkeypatch.setattr(core_auth, "ENABLE_AUTH", False, raising=False)
    monkeypatch.setattr(ea, "ENABLE_AUTH", False, raising=False)


def _cleanup_test_grants():
    from app.core.database import SessionLocal
    from app.models.auth import ResourceACL
    db = SessionLocal()
    try:
        db.query(ResourceACL).filter(ResourceACL.resource_type == "expert",
                                     ResourceACL.principal_type == "user",
                                     ResourceACL.principal_id.like("tdd-%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


def test_执法点1_列表过滤_nonadmin只见授权集(acl_env, monkeypatch):
    """非 admin 列表过滤：use 命中集（wenshu 种子可见+tutor 授予才可见）——直调面单测。"""
    from fastapi import Request
    from app.api.experts import list_experts
    req = Request({"type": "http", "method": "GET", "url": "", "headers": [], "query_string": b""})
    monkeypatch.setattr(acl_env, "get_current_user", lambda request: _mk_user("tdd-u1", ["viewer"]))
    resp = list_experts(req, enabled=None)
    rows = {r["expert_id"] for r in resp["items"]}
    assert "wenshu" in rows and "tutor" not in rows            # 种子命中/tutor 私有
    _grant_expert("tdd-u1", "tutor", ["use"])                  # 赋权→下次调用可见
    resp2 = list_experts(req, enabled=None)
    rows2 = {r["expert_id"] for r in resp2["items"]}
    assert "tutor" in rows2
    _revoke_expert("tdd-u1", "tutor")


def test_执法点2_chat入口_未授403(acl_env, monkeypatch):
    """chat 管线入口：未授专家 use→403 中文可读；admin 一票通过。"""
    from fastapi import HTTPException, Request
    req = Request({"type": "http", "method": "POST", "url": "", "headers": [], "query_string": b""})
    # 未授 user→403
    monkeypatch.setattr(acl_env, "get_current_user", lambda request: _mk_user("tdd-u2", ["viewer"]))
    with pytest.raises(HTTPException) as ei:
        acl_env.ensure_expert_allowed(req, "tutor", "use")
    assert "未获专家授权" in ei.value.detail
    # grant use→过
    _grant_expert("tdd-u2", "tutor", ["use"])
    acl_env.ensure_expert_allowed(req, "tutor", "use")             # 不抛=过
    # 回权即时（spec A2）：DELETE→下一请求 403（无缓存残留）
    _revoke_expert("tdd-u2", "tutor")
    with pytest.raises(HTTPException):
        acl_env.ensure_expert_allowed(req, "tutor", "use")
    # admin 一票通过
    monkeypatch.setattr(acl_env, "get_current_user", lambda request: _mk_user("tdd-ad", ["admin"]))
    acl_env.ensure_expert_allowed(req, "tutor", "use")


def test_执法点3_专家域API_manage分层(acl_env, monkeypatch):
    """专家域 API：use 过/manage 不过；manage 双动作过（A-4 分层对齐）。"""
    from fastapi import HTTPException, Request
    req = Request({"type": "http", "method": "GET", "url": "", "headers": [], "query_string": b""})
    _grant_expert("tdd-u3", "tutor", ["use"])
    monkeypatch.setattr(acl_env, "get_current_user", lambda request: _mk_user("tdd-u3", ["viewer"]))
    acl_env.ensure_expert_allowed(req, "tutor", "use")             # use 过
    with pytest.raises(HTTPException):
        acl_env.ensure_expert_allowed(req, "tutor", "manage")      # manage 不过
    _grant_expert("tdd-u3", "tutor", ["use", "manage"])
    acl_env.ensure_expert_allowed(req, "tutor", "manage")          # 双动作过
    _revoke_expert("tdd-u3", "tutor")


def test_执法点4_auth0全通_匿名admin(acl_env, monkeypatch):
    """auth=0 全通语义零变化：ENABLE_AUTH=False→匿名=admin 一票过（开发链路不破）。"""
    import app.core.auth as core_auth
    import app.services.expert_auth as ea
    monkeypatch.setattr(core_auth, "ENABLE_AUTH", False, raising=False)
    monkeypatch.setattr(ea, "ENABLE_AUTH", False, raising=False)
    from fastapi import Request
    req = Request({"type": "http", "method": "GET", "url": "", "headers": [], "query_string": b""})
    monkeypatch.setattr(ea, "get_current_user",
                        lambda request: _mk_user("anonymous", ["admin"]))
    ea.ensure_expert_allowed(req, "tutor", "use")                  # 不抛=全通
    ea.ensure_expert_allowed(req, "tutor", "manage")
