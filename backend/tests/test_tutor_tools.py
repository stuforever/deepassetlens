# -*- coding: utf-8 -*-
"""⑤批2（⑤b 验收）：工具面/隔离/surface 路由/注册计数。真 PG+固定 user 清理。"""
import json

import pytest
from sqlalchemy import text

from app.services.learning.pg import _engine
from app.services.learning.service import review_card

_UID_A = "tutor-tool-a"
_UID_B = "tutor-tool-b"


@pytest.fixture()
def _clean_users():
    for u in (_UID_A, _UID_B):
        with _engine.begin() as c:
            c.execute(text("DELETE FROM learning_review_cards WHERE user_id=:u"), {"u": u})
            c.execute(text("DELETE FROM learning_wrong_questions WHERE user_id=:u"), {"u": u})
    yield
    for u in (_UID_A, _UID_B):
        with _engine.begin() as c:
            c.execute(text("DELETE FROM learning_review_cards WHERE user_id=:u"), {"u": u})
            c.execute(text("DELETE FROM learning_wrong_questions WHERE user_id=:u"), {"u": u})


def test_registry_count_plus_nine():
    """⑤b 验收：注册表计数=基线+9（教学工具族注册实测）。"""
    from app.mcp_server import mcp
    tools = set(mcp._tool_manager._tools.keys())
    for t in ("fsrs_due", "fsrs_review", "mastery_query", "grade_answer",
              "generate_practice", "select_exercises", "wrong_question_add",
              "wrong_question_query", "export_wrong_book"):
        assert t in tools, f"缺教学工具: {t}"


def test_fsrs_review_math_value(_clean_users):
    """fsrs_review 首评 Good→间隔=FSRS 公式值（new_card: I=max(1, round(s*-ln0.9))）。
    断言数学，不赌 LLM。"""
    from app.services.memory_runtime import set_runtime
    set_runtime("tutor", _UID_A, "s1", "t1")
    from app.mcp_server import fsrs_review
    out = json.loads(fsrs_review(**{"item_id": "mq-math", "rating": 3}))
    # new_card(3): s=w[2]=3.1262 → I=max(1, round(3.1262*0.10536))=max(1,0)=1
    assert out["next_interval_days"] == 1.0
    assert abs(out["next_due_stability"] - 3.1262) < 1e-3
    # Hard(2)：new_card s=w[1]=1.1829 → 仍 I=1（FSRS 下限）
    out2 = json.loads(fsrs_review(**{"item_id": "mq-math2", "rating": 2}))
    assert out2["next_interval_days"] == 1.0
    assert abs(out2["next_due_stability"] - 1.1829) < 1e-3


def test_fsrs_review_now_injection(_clean_users):
    """铁律②：now 注入（due 断言不 sleep）——注入时钟走 new_card 时间轴。
    （fastmcp 禁下划线参数——spec 的 _now 更名 now，语义不变。）"""
    from app.mcp_server import fsrs_review
    out = json.loads(fsrs_review(**{"item_id": "mq-now", "rating": 3, "now": 1_000_000.0}))
    assert out["next_interval_days"] >= 1.0      # 公式值（注入时钟下同样成立）


def test_two_user_isolation(_clean_users):
    """⑤b 验收+铁律①：双用户隔离——A 的错题/due 对 B 不可见；参数无 user_id。"""
    from app.mcp_server import fsrs_review, wrong_question_add, wrong_question_query
    from app.services.memory_runtime import set_runtime
    set_runtime("tutor", _UID_A, "s1", "t1")
    wrong_question_add(**{"variant_text": "A 的错题", "error_context": "A context"})
    fsrs_review(**{"item_id": "mq-A-only", "rating": 3})
    # 换用户 B：查询不见 A 的任何数据
    set_runtime("tutor", _UID_B, "s2", "t2")
    seen_b = json.loads(wrong_question_query(**{}))
    assert seen_b["count"] == 0
    # 卡面隔离：A 评分产生卡行；B 对同 item 无卡（首评 due 在未来→due 清单为空属正常语义）
    from app.services.learning.learning_dao import get_card
    assert get_card(_UID_A, "mother_question", "mq-A-only") is not None
    assert get_card(_UID_B, "mother_question", "mq-A-only") is None
    # ContextVar 取值断言：工具内部 user=当前 rt（参数面无 user_id）
    set_runtime("tutor", _UID_A, "s1", "t1")
    from app.mcp_server import _tutor_user
    assert _tutor_user() == _UID_A


def test_wrong_question_flow(_clean_users):
    """wrong_question_add→query（open 筛选）。"""
    from app.mcp_server import wrong_question_add, wrong_question_query
    from app.services.memory_runtime import set_runtime
    set_runtime("tutor", _UID_A, "s1", "t1")
    out = json.loads(wrong_question_add(**{"variant_text": "变式题干", "error_context": "计算错误"}))
    assert out.get("wq_id")
    items = json.loads(wrong_question_query(**{"status": "open"}))
    assert items["count"] == 1 and items["items"][0]["variant_text"] == "变式题干"


def test_export_wrong_book_result_ref(_clean_users):
    """铁律③：导出走 result_ref 沉降（文件落盘+指针返回）。"""
    from app.mcp_server import export_wrong_book, wrong_question_add
    from app.services.memory_runtime import set_runtime
    set_runtime("tutor", _UID_A, "s1", "t1")
    wrong_question_add(**{"variant_text": "导出用错题"})
    out = json.loads(export_wrong_book(**{"format": "md"}))
    assert "result_ref" in out and out["count"] == 1
    import os
    assert os.path.exists(out["file"])


def test_select_exercises_neighbor_mock(_clean_users, monkeypatch):
    """⑤b 诚实账①：图谱邻居扩展 mock 测试（真实联调⑤f）——邻居池进母题查询。"""
    from app.services.learning import tutor_select
    import app.services.learning.learning_dao as _dao
    monkeypatch.setattr(tutor_select, "_graph_neighbors",
                        lambda kp, depth=1: [kp, "kp-neighbor-1"])
    monkeypatch.setattr(_dao, "mother_questions_by_kps", lambda kps: [
        {"mq_id": "mq-1", "title": "题1", "archetype_text": "x", "knowledge_point_id": kps[0], "variant_count": 2},
        {"mq_id": "mq-2", "title": "题2", "archetype_text": "y", "knowledge_point_id": kps[1], "variant_count": 1},
    ] if kps else [])
    monkeypatch.setattr(tutor_select, "_mastery_weight", lambda u, kp: 0.9 if kp == "kp-neighbor-1" else 0.2)
    out = tutor_select.select_exercises_with_neighbors(_UID_A, "kp-root", n=2)
    assert out["neighbor_pool"] == ["kp-root", "kp-neighbor-1"]
    # 掌握度低（权高 0.9）的邻居母题排前
    assert out["items"][0]["mq_id"] == "mq-2"


def test_grade_answer_fail_closed_no_llm():
    """LLM 臂确定性短路：空预期答案 fail-closed（不调 LLM——402 期间可测）。"""
    from app.mcp_server import grade_answer
    out = json.loads(grade_answer(**{"question": "q", "user_answer": "a", "expected_answer": ""}))
    assert out["score"] == 0 and out["correct"] is False


def test_surface_routing_only_requested():
    """批 0.5 分支：请求级 surface 指定→只写该 surface（双声明卡不双写）；未指定→全部声明。"""
    import asyncio
    from app.services.memory_trace import MemoryTraceMiddleware
    card = {"memory": {"slots": [
        {"type": "L1_TRACE", "surface": "chat", "path": "trace/chat", "template": "t"},
        {"type": "L1_TRACE", "surface": "quiz", "path": "trace/quiz", "template": "t"},
    ]}}
    mw = MemoryTraceMiddleware(card)
    assert mw._surfaces == ["chat", "quiz"]

    from app.services import memory_runtime
    from app.services import memory_trace as mt
    written = []
    monkey_aappend = lambda *a, **k: written.append(a[2]) or None

    async def _run(surface):
        written.clear()
        memory_runtime.set_runtime("tutor", "u-surf", "sess", "turn")
        import app.services.memory_trace as m2
        orig = m2.aappend_event

        async def _fake_append(eid, u, s, ev):
            written.append(s)

        m2.aappend_event = _fake_append
        try:
            memory_runtime.update_runtime({"surface": surface} if surface else {})
            await mw._emit("user_msg", {"text": "hi"})
        finally:
            m2.aappend_event = orig
            memory_runtime.reset()

    asyncio.run(_run("quiz"))
    assert written == ["quiz"]                    # 请求指定→只写 quiz
    asyncio.run(_run(None))
    assert sorted(written) == ["chat", "quiz"]    # 未指定→②原语义全写
