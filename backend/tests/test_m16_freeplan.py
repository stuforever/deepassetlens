# -*- coding: utf-8 -*-
"""M16 单测：SSE 帧/think 流分流/输出契约/收尾交付纯函数/会话锁（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M16 spec §十验收标准锚定现有实现）。
e2e 主链全帧序留批次 4 尾 Playwright 串行验收（AGENTS.md 铁律）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from types import SimpleNamespace  # noqa: E402


# ---------------------------------------------------------------------------
# SSE 帧纯函数（spec §三事件面）
# ---------------------------------------------------------------------------

def test_sse_line_format():
    """sse_line 产标准 SSE 帧（event:+data:\\n\\n，spec §三）。
    变异锚点：帧格式漂移 → 前端 EventSource 解析断。"""
    from app.api.freeplan.sse import sse_line
    line = sse_line("token", {"delta": "x"})
    assert line.startswith("event: token\ndata: ")
    assert line.endswith("\n\n")


# ---------------------------------------------------------------------------
# think 流双通道分流（spec §五六状态）
# ---------------------------------------------------------------------------

def test_translator_decision_answer_split():
    """【下一步判断】前缀：WAIT→DECISION_FIRST→DECISION_DELTA（spec §五）。
    变异锚点：状态机乱 → 决策/答案草稿混流。"""
    from app.api.freeplan.translator import (
        ANSWER_DELTA, ANSWER_FIRST, DECISION_DELTA, DECISION_FIRST, WAIT,
        ThinkRoundClassifier,
    )
    c = ThinkRoundClassifier()
    actions = [c.feed(t) for t in "【下一步判断】先统计台区"]
    assert actions[0] == WAIT                       # 标记未完整，攒 token
    assert DECISION_FIRST in actions                # 首帧冲刷
    assert DECISION_DELTA in actions                # 增量帧
    assert ThinkRoundClassifier.kind_of(DECISION_DELTA) == "decision_draft"


def test_translator_plain_text_is_answer():
    """普通文本直落答案流（ANSWER_FIRST→ANSWER_DELTA，spec §五）。
    变异锚点：answer 流丢 → 前端结论区空。"""
    from app.api.freeplan.translator import ANSWER_DELTA, ANSWER_FIRST, ThinkRoundClassifier
    c = ThinkRoundClassifier()
    assert c.feed("统计") == ANSWER_FIRST
    assert c.feed("完成") == ANSWER_DELTA
    assert ThinkRoundClassifier.kind_of(ANSWER_FIRST) == "answer_draft"


def test_translator_tool_notes_skip():
    """工具任务笔记（## SESSION INTENT 等四标记）零推帧 SKIP（spec §五/§十.2）。
    变异锚点：notes 泄帧 → 过程中间产物污染答案区。"""
    from app.api.freeplan.translator import ANSWER_FIRST, SKIP, ThinkRoundClassifier
    c = ThinkRoundClassifier()
    assert c.feed("## SESSION INTENT\n问数统计") == SKIP
    assert c.feed("更多") == SKIP                    # notes 态持续跳过
    # 非笔记非标记 → 答案流
    c2 = ThinkRoundClassifier()
    assert c2.feed("普通结论") == ANSWER_FIRST


# ---------------------------------------------------------------------------
# 收尾交付纯函数族（spec §六）
# ---------------------------------------------------------------------------

def test_apply_output_contract_scrubs_md_table():
    """输出契约：final 带 Markdown 明细表且有 UI 结果 → 剥离+scrubbed 留痕（spec §六/§十.3）。
    变异锚点：剥离删 → final 与前端查询结果表双明细（契约破坏）。"""
    from app.api.freeplan.delivery import apply_output_contract
    md = "统计完成\n| 台区 | 数量 |\n|---|---|\n| a | 1 |"
    out = apply_output_contract(md, {"row_count": 1}, forbid_md=True)
    assert out["scrubbed"] is True and "|---|" not in out["answer"]
    # 无 UI 结果 → 不剥（明细无处展示，保留原文）
    out2 = apply_output_contract(md, None, forbid_md=True)
    assert out2["scrubbed"] is False and out2["answer"] == md


def test_build_evidence_chain():
    """证据链三源合一+置信度三级（contract+tool_results+final_answer，spec §六：M3 G7 高/中/低）。
    变异锚点：证据链断 → 交付不可追溯；置信度逻辑乱 → 前端黄条误报。"""
    from app.api.freeplan.delivery import build_evidence
    def _c(runtime):
        return SimpleNamespace(skill_id="s1", scenario="smart_qa", route_type="sql",
                               _runtime=runtime, to_dict=lambda: {"skill_id": "s1"})
    ev = build_evidence(_c({}), {"sql_result": {"rows": 1}, "sql_executed": True}, "最终答案")
    assert isinstance(ev, dict) and "evidence" in ev and "confidence" in ev
    # rubric satisfied 且无 warning → 高
    ev_hi = build_evidence(_c({"rubric_status": "satisfied", "rubric_iterations": 1}),
                           {"sql_result": {"rows": 1}, "sql_executed": True}, "完成")
    assert ev_hi["confidence"] == "高"
    # corrections>0 → 低
    ev_lo = build_evidence(_c({"rubric_status": "satisfied", "corrections": 2}),
                           {"sql_result": {"rows": 1}, "sql_executed": True}, "完成")
    assert ev_lo["confidence"] == "低"


def test_build_recommendations_default_three():
    """默认推荐三连（spec §六：统计用电客户总数/查客户的联系电话/什么是变压器）。
    变异锚点：默认推荐漂移 → 首问体验不一致。"""
    from app.api.freeplan.delivery import build_recommendations
    recs = build_recommendations(None, "答案")
    assert recs[:3] == ["统计用电客户总数", "查客户的联系电话", "什么是变压器"]


def test_build_done_payload_signature():
    """done 帧载荷构建器关键字契约（spec §六：完整载荷收口）。
    变异锚点：载荷键删 → 前端 done 处理断。"""
    import inspect
    from app.api.freeplan.delivery import build_done_payload
    params = set(inspect.signature(build_done_payload).parameters)
    assert {"thread_id", "confirmed", "final_answer", "sql_result_data",
            "evidence", "recs"} <= params


# ---------------------------------------------------------------------------
# 会话锁与流挂载（spec §四/§十.5）
# ---------------------------------------------------------------------------

def test_session_lock_cap_and_reuse():
    """同 thread 锁复用+锁池上限 200（spec §四/§十.5）。
    变异锚点：锁不复用 → 同会话并发失控；上限删 → 锁池无界增长。"""
    from app.api.freeplan.session import _SESSION_LOCK_MAX, _get_session_lock
    assert _SESSION_LOCK_MAX == 200
    l1 = _get_session_lock("m16-thread-x")
    l2 = _get_session_lock("m16-thread-x")
    assert l1 is l2


def test_stream_endpoints_mounted():
    """流挂载两端点（POST /chat/freeplan/stream + /resume，spec §三/§十二）。
    变异锚点：resume 删 → HITL 挂起后无法续跑。"""
    from app.api import data_intelligence_stream as S
    paths = " ".join(getattr(r, "path", "") for r in S.router.routes)
    assert "freeplan/stream" in paths
    assert "resume" in paths


def test_chat_request_contract_fields():
    """ChatRequest 契约字段（spec §三：thread_id/user_input/user_selection/format/llm_connection_id）。
    变异锚点：user_selection 删 → 点选上下文断（M18 联测前提）。"""
    from app.api.data_intelligence import ChatRequest
    fields = set(ChatRequest.model_fields.keys())
    assert {"thread_id", "user_input", "user_selection", "format", "llm_connection_id"} <= fields
