"""E1 错因→出题闭环单测：薄弱命中文案带错因、同优先级特征偏向、无错因回退。"""

from __future__ import annotations

from deeptutor.learning.exercise_selector import (
    PRIORITY_WEAK,
    REASON_WEAK,
    select_exercises,
)


class FakeKP:
    def __init__(self, name: str, error_types: list[str]):
        self.kp_name = name
        self.error_types = error_types


class FakeProfile:
    def __init__(self, weak: dict[str, FakeKP]):
        self.weak_points = list(weak.keys())
        self.due_reviews: list = []
        self.strong_points: list = []
        self.kp_mastery = weak


def _ex(title: str, questions: list[str]) -> dict:
    return {
        "title": title,
        "questions": [{"content": q} for q in questions],
    }


def test_weak_reason_carries_dominant_error_type():
    profile = FakeProfile({"kp1": FakeKP("有理数的乘方", ["计算错误", "计算错误", "审题"])})
    out = select_exercises(
        [_ex("第一章 有理数的乘方", ["题目A"])],
        profile=profile,
    )
    ex = out["ordered"][0]
    assert ex["priority"] == PRIORITY_WEAK
    assert ex["adaptive_reason"] == f"{REASON_WEAK}·计算错误为主"
    # 每题自适应理由联动
    assert ex["questions"][0]["adaptive_reason"] == f"{REASON_WEAK}·计算错误为主"
    # summary 联动
    assert any("计算错误为主" in s for s in out["summary"])


def test_computation_error_biases_calculation_heavy_first():
    profile = FakeProfile({"kp1": FakeKP("有理数的乘方", ["计算错误"])})
    light = _ex("第一章 有理数的乘方", ["简短题干"])
    heavy = _ex("第一章 有理数的乘方", ["1+2×3=?", "4-5÷(1+2)=?", "(-3)²-2×3=?"])
    out = select_exercises([light, heavy], profile=profile)
    ordered = out["ordered"]
    # 同优先级内：运算密集组排前（heavy 在前）
    assert ordered[0]["questions"][0]["content"].startswith("1+2×3")


def test_reading_error_biases_long_stem_first():
    profile = FakeProfile({"kp1": FakeKP("一元一次方程", ["审题"])})
    short = _ex("第二章 一元一次方程", ["求 x。"])
    long_ = _ex("第二章 一元一次方程", ["小明从家出发去学校，全程 1200 米，前 400 米步行速度为 1 米每秒，其余路程骑自行车速度为 4 米每秒，问他到达学校共需多少秒？"])
    out = select_exercises([short, long_], profile=profile)
    assert out["ordered"][0]["questions"][0]["content"].startswith("小明从家出发")


def test_no_error_type_falls_back_to_plain_weak():
    profile = FakeProfile({"kp1": FakeKP("有理数的乘方", [])})
    out = select_exercises(
        [_ex("第一章 有理数的乘方", ["题目A"])],
        profile=profile,
    )
    assert out["ordered"][0]["adaptive_reason"] == REASON_WEAK
    assert out["summary"] == ["本章命中 1 个薄弱点练习，建议优先完成"]


def test_no_profile_normal_reason():
    out = select_exercises([_ex("随便一节", ["题目A"])])
    assert out["ordered"][0]["adaptive_reason"] == "normal"
    assert out["adapted"] is False
