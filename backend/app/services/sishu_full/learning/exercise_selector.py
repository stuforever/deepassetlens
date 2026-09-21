"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.services.sishu_full.learning.learner_profile import (
    _strip_chapter_prefix,
    build_learner_profile,
)

# priority 越小越先做
PRIORITY_WEAK = 0     # 薄弱点 -> 优先
PRIORITY_DUE = 1      # 到期复习 -> 次之
PRIORITY_MASTERED = 2 # 已掌握 -> 抽查
PRIORITY_NORMAL = 3   # 其他

REASON_WEAK = "weak"
REASON_DUE = "due"
REASON_MASTERED = "review"
REASON_NORMAL = "normal"


def _dominant_error_types(kp: Any) -> list[str]:
    """kp.error_types 出现次数降序去重（众数在前）；无数据返回空列表。"""
    ets = getattr(kp, "error_types", None) or []
    if not ets:
        return []
    return [t for t, _c in Counter(ets).most_common()]


def _weak_reason(kp: Any) -> str:
    """薄弱命中理由（E1）：带主导错因——「weak·计算错误为主」；无错因回退原值。"""
    dom = _dominant_error_types(kp)
    if dom and dom[0]:
        return f"{REASON_WEAK}·{dom[0]}为主"
    return REASON_WEAK


def _feature_bias(ex: dict[str, Any], dominant: str) -> float:
    """错因导向的题面特征分（E1，仅同 priority 内部次级排序）：
    - 计算错误 -> questions 数量多（>=3）或题干含运算式 -> 前移
    - 审题 -> 题干总长 >60 字（情境复杂）-> 前移
    返回 >0 表示该组应在同优先级内前移。"""
    questions = ex.get("questions") or []
    texts = " ".join(
        str(q.get("content") or q.get("question") or "")
        for q in questions
        if isinstance(q, dict)
    )
    if dominant == "计算错误":
        if len(questions) >= 3:
            return 1.0
        if any(ch in texts for ch in "+-×÷*/=运算计算①"):
            return 1.0
    elif dominant == "审题":
        if len(texts) > 60:
            return 1.0
    return 0.0


def _score_exercise(exercise: dict[str, Any], profile: Any) -> tuple[int, str, Any]:
    """返回 (priority, reason, kp)：根据 exercise.title 匹配学情。

    M1（第十八篇 D 批）：题库已批量标注 q.kp_id —— 题级 KP 精确匹配优先，
    无标注再回退「章节名 ↔ 知识点名」桥接。
    E1：薄弱命中返回带主导错因的 reason，并回传命中的 kp 供特征偏向用。"""
    # ── M1：题级 kp_id 精确匹配（标注过的题组）────────────────────────
    q_kp_ids = {
        str(q.get("kp_id") or "")
        for q in (exercise.get("questions") or [])
        if isinstance(q, dict) and q.get("kp_id")
    }
    if q_kp_ids:
        for kid in profile.weak_points:
            if kid in q_kp_ids:
                return PRIORITY_WEAK, _weak_reason(profile.kp_mastery.get(kid)), profile.kp_mastery.get(kid)
        for due in profile.due_reviews:
            if str(due.get("kp_id") or "") in q_kp_ids:
                return PRIORITY_DUE, REASON_DUE, None
        for kid in profile.strong_points:
            if kid in q_kp_ids:
                return PRIORITY_MASTERED, REASON_MASTERED, None

    title = _strip_chapter_prefix(str(exercise.get("title") or ""))
    if not title:
        return PRIORITY_NORMAL, REASON_NORMAL, None

    # 薄弱点
    for kid in profile.weak_points:
        kp = profile.kp_mastery.get(kid)
        if kp and (title in kp.kp_name or kp.kp_name in title):
            return PRIORITY_WEAK, _weak_reason(kp), kp

    # 到期复习
    for due in profile.due_reviews:
        kp_name = str(due.get("kp_name") or "")
        if kp_name and (title in kp_name or kp_name in title):
            return PRIORITY_DUE, REASON_DUE, None

    # 已掌握
    for kid in profile.strong_points:
        kp = profile.kp_mastery.get(kid)
        if kp and (title in kp.kp_name or kp.kp_name in title):
            return PRIORITY_MASTERED, REASON_MASTERED, None

    return PRIORITY_NORMAL, REASON_NORMAL, None


def select_exercises(
    exercises: list[dict[str, Any]],
    profile: Any | None = None,
) -> dict[str, Any]:
    """自适应排序一个章节的闯关题目。

    Args:
        exercises: grade7 exercise 项列表（含 title / questions）。
        profile: LearnerProfile；None 时实时构建。

    Returns:
        {
          "adapted": bool,          # 是否有排序调整
          "ordered": list,          # 排序后的 exercise 项（每题附 adaptive_reason）
          "summary": list[str],     # 排序原因摘要（供前端提示条）
        }
    """
    profile = profile or build_learner_profile()
    scored = []
    weak_doms: list[str] = []
    for ex in exercises:
        priority, reason, kp = _score_exercise(ex, profile)
        ex = dict(ex)
        questions = ex.get("questions") or []
        # E1：同 priority 内部次级排序的特征分（错因导向）
        feature = 0.0
        if priority == PRIORITY_WEAK:
            dom = _dominant_error_types(kp)
            if dom:
                weak_doms.append(dom[0])
                feature = _feature_bias(ex, dom[0])
        ex["questions"] = [
            {**q, "adaptive_reason": reason} if isinstance(q, dict) else q
            for q in questions
        ]
        ex["priority"] = priority
        ex["adaptive_reason"] = reason
        scored.append((priority, -feature, ex))

    scored.sort(key=lambda pair: (pair[0], pair[1]))
    ordered = [ex for _prio, _feat, ex in scored]

    weak_count = sum(1 for p, _f, _e in scored if p == PRIORITY_WEAK)
    due_count = sum(1 for p, _f, _e in scored if p == PRIORITY_DUE)
    mastered_count = sum(1 for p, _f, _e in scored if p == PRIORITY_MASTERED)
    adapted = any(p != PRIORITY_NORMAL for p, _f, _e in scored)

    summary: list[str] = []
    if weak_count:
        # E1：薄弱主导错因汇总——「本章命中 N 个薄弱点练习（计算错误为主）…」
        dom_summary = ""
        if weak_doms:
            top_dom = Counter(weak_doms).most_common(1)[0][0]
            dom_summary = f"（{top_dom}为主）"
        summary.append(
            f"本章命中 {weak_count} 个薄弱点练习{dom_summary}，建议优先完成"
        )
    if due_count:
        summary.append(f"{due_count} 组练习涉及到期复习知识点")
    if mastered_count:
        summary.append(f"{mastered_count} 组已掌握，可快速抽查")

    return {"adapted": adapted, "ordered": ordered, "summary": summary}


__all__ = [
    "PRIORITY_DUE",
    "PRIORITY_MASTERED",
    "PRIORITY_NORMAL",
    "PRIORITY_WEAK",
    "REASON_DUE",
    "REASON_MASTERED",
    "REASON_NORMAL",
    "REASON_WEAK",
    "select_exercises",
]
