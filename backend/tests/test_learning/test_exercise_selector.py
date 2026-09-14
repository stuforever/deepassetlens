# -*- coding: utf-8 -*-
"""⑤批1（A1）：闯关自适应选题测试——DeepTutor 直迁（断言语义零改，只改 import）。"""

from __future__ import annotations

import pytest  # noqa: F401

from app.services.learning.exercise_selector import (
    PRIORITY_DUE,
    PRIORITY_MASTERED,
    PRIORITY_WEAK,
    REASON_DUE,
    REASON_MASTERED,
    REASON_WEAK,
    select_exercises,
)


class _KP:
    def __init__(self, kp_id, name, mastery=0.5, status="learning"):
        self.kp_id = kp_id
        self.kp_name = name
        self.mastery = mastery
        self.status = status


class _Profile:
    def __init__(self, kp_mastery, weak=None, strong=None, due=None):
        self.kp_mastery = kp_mastery
        self.weak_points = weak or []
        self.strong_points = strong or []
        self.due_reviews = due or []


def _ex(title: str, qcount: int = 2) -> dict:
    return {
        "id": title,
        "title": title,
        "count": qcount,
        "questions": [
            {"ask": f"{title}-q{i}", "type": "choice", "options": ["a", "b"], "answer": 0, "why": ""}
            for i in range(qcount)
        ],
    }


def test_weak_exercise_comes_first():
    kp = _KP("k1", "一元一次方程")
    profile = _Profile({"k1": kp}, weak=["k1"])
    exercises = [
        _ex("2.3 有理数的乘法"),
        _ex("1.1 一元一次方程"),  # matches weak kp
    ]
    result = select_exercises(exercises, profile=profile)
    ordered = result["ordered"]
    assert ordered[0]["title"] == "1.1 一元一次方程"
    assert ordered[0]["priority"] == PRIORITY_WEAK
    assert ordered[0]["adaptive_reason"] == REASON_WEAK
    assert ordered[0]["questions"][0]["adaptive_reason"] == REASON_WEAK
    assert result["adapted"] is True
    assert result["summary"]


def test_due_comes_after_weak_before_normal():
    kp_weak = _KP("k1", "去分母")
    kp_due = _KP("k2", "移项")
    profile = _Profile(
        {"k1": kp_weak, "k2": kp_due},
        weak=["k1"],
        due=[{"kp_name": "移项"}],
    )
    exercises = [
        _ex("3.2 有理数运算"),
        _ex("3.1 去分母"),
        _ex("3.0 移项"),
    ]
    ordered = select_exercises(exercises, profile=profile)["ordered"]
    assert [e["title"] for e in ordered] == ["3.1 去分母", "3.0 移项", "3.2 有理数运算"]
    assert ordered[1]["priority"] == PRIORITY_DUE
    assert ordered[1]["adaptive_reason"] == REASON_DUE


def test_mastered_flagged_as_review():
    kp = _KP("k1", "正数和负数")
    profile = _Profile({"k1": kp}, strong=["k1"])
    result = select_exercises([_ex("1.1 正数和负数")], profile=profile)
    ordered = result["ordered"]
    assert ordered[0]["priority"] == PRIORITY_MASTERED
    assert ordered[0]["adaptive_reason"] == REASON_MASTERED


def test_no_profile_matches_everything_normal():
    class _Empty:
        kp_mastery = {}
        weak_points = []
        strong_points = []
        due_reviews = []

    result = select_exercises([_ex("1.1 正数和负数")], profile=_Empty())
    assert result["adapted"] is False
    assert result["ordered"][0]["priority"] == 3
    assert result["summary"] == []


# ── M1（第十八篇 D）：题级 kp_id 精确匹配优先 ─────────────────────────────


class TestKpIdExactMatchPriority:
    def _kp(self, name, error_types=None):
        class _K:
            def __init__(self):
                self.kp_name = name
                self.error_types = error_types or []

        return _K()

    def _profile(self, km, weak=None, strong=None, due=None):
        class _P:
            def __init__(self):
                self.kp_mastery = km
                self.weak_points = weak or []
                self.strong_points = strong or []
                self.due_reviews = due or []

        return _P()

    def test_weak_kp_id_exact_match_prioritized(self):
        kp = self._kp("有理数的乘方", ["计算错误", "计算错误", "审题"])
        profile = self._profile({"k9": kp}, weak=["k9"])
        ex = {"title": "完全无关的章节名", "questions": [{"ask": "q1", "kp_id": "k9"}]}
        out = select_exercises([ex], profile=profile)
        assert out["ordered"][0]["priority"] == PRIORITY_WEAK
        assert out["ordered"][0]["adaptive_reason"] == f"{REASON_WEAK}·计算错误为主"
        assert out["adapted"] is True

    def test_kp_id_match_beats_title_bridge(self):
        # 标题桥接命中薄弱 k1，但题级 kp_id=k2 命中到期复习 —— kp_id 先判
        km = {"k1": self._kp("一元一次方程")}
        profile = self._profile(km, weak=["k1"], due=[{"kp_id": "k2", "kp_name": "移项"}])
        ex = {"title": "1.1 一元一次方程", "questions": [{"ask": "q1", "kp_id": "k2"}]}
        out = select_exercises([ex], profile=profile)
        assert out["ordered"][0]["priority"] == PRIORITY_DUE
        assert out["ordered"][0]["adaptive_reason"] == REASON_DUE

    def test_due_kp_id_exact_match(self):
        profile = self._profile({}, due=[{"kp_id": "k2", "kp_name": "移项"}])
        ex = {"title": "无关章节", "questions": [{"ask": "q1", "kp_id": "k2"}]}
        out = select_exercises([ex], profile=profile)
        assert out["ordered"][0]["priority"] == PRIORITY_DUE

    def test_mastered_kp_id_exact_match(self):
        profile = self._profile({"k3": self._kp("正数和负数")}, strong=["k3"])
        ex = {"title": "无关章节", "questions": [{"ask": "q1", "kp_id": "k3"}]}
        out = select_exercises([ex], profile=profile)
        assert out["ordered"][0]["priority"] == PRIORITY_MASTERED
        assert out["ordered"][0]["adaptive_reason"] == REASON_MASTERED

    def test_empty_kp_id_falls_back_to_title_bridge(self):
        # kp_id 为空串视为未标注，回退标题桥接
        profile = self._profile({"k1": self._kp("一元一次方程")}, weak=["k1"])
        ex = {"title": "1.1 一元一次方程", "questions": [{"ask": "q1", "kp_id": ""}]}
        out = select_exercises([ex], profile=profile)
        assert out["ordered"][0]["priority"] == PRIORITY_WEAK
        assert out["ordered"][0]["adaptive_reason"] == REASON_WEAK
