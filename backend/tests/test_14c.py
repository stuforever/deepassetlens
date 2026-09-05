# -*- coding: utf-8 -*-
"""批14-C AB-4 两项豁免收口单测。

§3.1 TTL 降级：env 旋钮（TUPU_QRS_TTL_SECONDS/TUPU_QRS_CAP，默认不变）+过期路径单元级
（e2e 剧本结构性不可达——首派发总在 TTL 内（on_tool_end 立即派发），过期只影响重取，
登记为单元级验收）。
§3.2 并发帧序：ThinkRoundClassifier 状态机单元级不变量——乱序/交错/逐字符输入 →
输出序确定（wait→first→delta 单调、notes 恒 skip、决策/答案流互不串流）。
e2e 层豁免永久登记（Playwright 串行铁律下的正确取舍，非欠账）。
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _reload_qrs(monkeypatch, ttl=None, cap=None):
    import app.services.query_result_store as qrs
    if ttl is not None:
        monkeypatch.setenv("TUPU_QRS_TTL_SECONDS", str(ttl))
    if cap is not None:
        monkeypatch.setenv("TUPU_QRS_CAP", str(cap))
    return importlib.reload(qrs)


def test_ttl_defaults_unchanged(monkeypatch):
    """默认值不变=零行为变化（设计 §3.1 硬要求）。"""
    for k in ("TUPU_QRS_TTL_SECONDS", "TUPU_QRS_CAP"):
        monkeypatch.delenv(k, raising=False)
    qrs = _reload_qrs(monkeypatch)
    assert qrs._RESULT_TTL == 600
    assert qrs._MAX_ENTRIES == 64


def test_ttl_env_knob(monkeypatch):
    qrs = _reload_qrs(monkeypatch, ttl=5, cap=3)
    assert qrs._RESULT_TTL == 5
    assert qrs._MAX_ENTRIES == 3


def test_ttl_expiry_returns_none(monkeypatch):
    """TTL=5：put 后未过期可取；模拟时间推进 >5s 后 get 返回 None 且条目已删。"""
    qrs = _reload_qrs(monkeypatch, ttl=5)
    key = qrs.put({"rows": [1, 2]})
    assert qrs.get(key) == {"rows": [1, 2]}
    # 时间推进（直接改 store 内 ts，避免 sleep）
    ts, payload = qrs._store[key]
    qrs._store[key] = (ts - 6, payload)
    assert qrs.get(key) is None
    assert key not in qrs._store  # 过期已删


def test_cap_eviction(monkeypatch):
    """容量淘汰：cap=3 时 put 第 4 条淘汰最旧。"""
    qrs = _reload_qrs(monkeypatch, cap=3)
    k1 = qrs.put({"n": 1})
    k2 = qrs.put({"n": 2})
    k3 = qrs.put({"n": 3})
    k4 = qrs.put({"n": 4})
    assert k1 not in qrs._store
    assert qrs.get(k4) == {"n": 4}
    assert qrs.get(k3) == {"n": 3}


def test_sweep_removes_expired(monkeypatch):
    qrs = _reload_qrs(monkeypatch, ttl=5)
    k1 = qrs.put({"n": 1})
    ts, payload = qrs._store[k1]
    qrs._store[k1] = (ts - 10, payload)
    qrs.sweep()
    assert k1 not in qrs._store


# ---------------------------------------------------------------------------
# §3.2 并发帧序：状态机不变量（单元级）
# ---------------------------------------------------------------------------

from app.api.freeplan.translator import (  # noqa: E402
    ANSWER_DELTA, ANSWER_FIRST, DECISION_DELTA, DECISION_FIRST, SKIP, WAIT,
    ThinkRoundClassifier,
)


def _feed_all(clf, tokens):
    return [clf.feed(t) for t in tokens]


def test_invariant_decision_stream_order():
    """决策流：wait*→decision_first→decision_delta* 单调不回退。"""
    clf = ThinkRoundClassifier()
    toks = list("【下一步判断】查询台区")
    acts = _feed_all(clf, toks)
    assert acts[0] == WAIT, "首 token 必为 wait（前缀未定）"
    i_first = acts.index(DECISION_FIRST)
    assert all(a == WAIT for a in acts[:i_first])
    assert all(a == DECISION_DELTA for a in acts[i_first + 1:])
    assert clf.kind_of(DECISION_FIRST) == "decision_draft"


def test_invariant_answer_stream_order():
    """答案流：非标记文本首 token 即 answer_first（无歧义前缀无 wait），后续恒 delta。"""
    clf = ThinkRoundClassifier()
    acts = _feed_all(clf, list("台区重过载统计如下"))
    assert acts[0] == ANSWER_FIRST
    assert all(a == ANSWER_DELTA for a in acts[1:])
    assert clf.kind_of(ANSWER_FIRST) == "answer_draft"


def test_invariant_notes_always_skip():
    """notes 流（工具任务笔记）：识别后恒 skip，不推任何帧。"""
    clf = ThinkRoundClassifier()
    marker = "## SUMMARY"
    acts = _feed_all(clf, list(marker + "内容若干"))
    assert SKIP in acts
    i_skip = acts.index(SKIP)
    assert all(a == SKIP for a in acts[i_skip:])


def test_invariant_chunked_input_equivalent():
    """分块不变量：终态、累积内容、帧 kind 流向与分块大小无关（delta 粒度天然随分块变化）。"""
    text = "【下一步判断】执行第2步计数模板"
    states, accs, firsts = [], [], []
    for chunk in (1, 3, len(text)):
        clf = ThinkRoundClassifier()
        acts = []
        for i in range(0, len(text), chunk):
            acts.append(clf.feed(text[i:i + chunk]))
        states.append(clf.state)
        accs.append(clf.accumulated)
        na = [a for a in acts if a != WAIT]
        assert na and na[0] == DECISION_FIRST, "去 wait 后首动作必为 decision_first（冲刷语义）"
        assert all(a in (DECISION_FIRST, DECISION_DELTA) for a in na), "决策流不混答案帧"
        firsts.append(clf.kind_of(na[0]))
    assert states == ["decision"] * 3
    assert accs == [text] * 3
    assert firsts == ["decision_draft"] * 3


def test_invariant_interleaved_instances_independent():
    """多实例交错（模拟并发轮次各自分类器）：实例间状态互不污染。"""
    c1, c2 = ThinkRoundClassifier(), ThinkRoundClassifier()
    a1 = c1.feed("【")     # 歧义前缀 → wait
    a2 = c2.feed("台")     # 非标记文本 → 直接 answer_first
    assert a1 == WAIT and a2 == ANSWER_FIRST
    seq1 = [c1.feed(t) for t in list("下一步判断】内容")]
    seq2 = [c2.feed(t) for t in list("区统计回答")]
    n1 = [a for a in seq1 if a != WAIT]  # 前缀期 wait 合法
    assert DECISION_FIRST in n1 and all(a in (DECISION_FIRST, DECISION_DELTA) for a in n1)
    assert all(a == ANSWER_DELTA for a in seq2)
    assert c1.state == "decision" and c2.state == "answer"
