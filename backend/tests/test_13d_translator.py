# -*- coding: utf-8 -*-
"""批13-D Step3：ThinkRoundClassifier 三态单测（answer_first/decision 分流/notes skip+前缀等待）。"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.api.freeplan.translator import (
    ThinkRoundClassifier, WAIT, SKIP,
    DECISION_FIRST, ANSWER_FIRST, DECISION_DELTA, ANSWER_DELTA,
)


def _feed_all(tc, text):
    """整段文本逐字喂入，返回动作码序列（去 WAIT 重复）。"""
    return [tc.feed(ch) for ch in text]


def test_答案流首次冲刷_完整累积():
    tc = ThinkRoundClassifier()
    acts = _feed_all(tc, "配电变压器共")
    # '配' 不匹配任何前缀（'【'/'##'），首字符即落 answer 并 ANSWER_FIRST（delta=完整累积）
    assert acts[0] == ANSWER_FIRST
    # 落定后推增量
    assert tc.feed("5") == ANSWER_DELTA
    assert tc.accumulated == "配电变压器共5"


def test_决策流分流_下一步判断头():
    tc = ThinkRoundClassifier()
    acts = _feed_all(tc, "【下一步判断】需要")
    assert DECISION_FIRST in acts
    assert tc.feed("查") == DECISION_DELTA
    assert ThinkRoundClassifier.kind_of(DECISION_FIRST) == "decision_draft"
    assert ThinkRoundClassifier.kind_of(DECISION_DELTA) == "decision_draft"


def test_任务笔记_前缀等待后整体丢弃():
    tc = ThinkRoundClassifier()
    # "## S" 是 NOTE 前缀等待阶段（不足完整标记长度）
    assert tc.feed("#") == WAIT
    assert tc.feed("#") == WAIT
    assert tc.feed(" ") == WAIT
    assert tc.feed("S") == WAIT
    # 补全为完整标记后判 notes，后续全 SKIP（内部产物不上屏）
    acts = _feed_all(tc, "ESSION INTENT\n查询配电变压器")
    assert acts[-1] == SKIP
    assert tc.state == "notes"
    assert all(a in (WAIT, SKIP) for a in acts)


def test_注_标记与内联版一致性():
    """锚点：TOOL_NOTE_MARKERS/DECISION_MARKER 与拆分前内联版逐字一致。"""
    from app.api.freeplan.translator import TOOL_NOTE_MARKERS, DECISION_MARKER
    assert TOOL_NOTE_MARKERS == ("## SESSION INTENT", "## SUMMARY", "## ARTIFACTS", "## NEXT STEPS")
    assert DECISION_MARKER == "【下一步判断】"
