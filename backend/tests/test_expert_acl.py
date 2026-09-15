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
