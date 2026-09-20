# -*- coding: utf-8 -*-
"""⑤批1 纯函数 + ⑤补补-2：learner_profile 真实现——PG 读取面（learning_dao 同库）。

- streak：review_records 按 `reviewed_at::date` DISTINCT 连续区间（今天/昨天为锚回溯）；
- due：sishu_review_cards due<=now 清单；
- weak：kind=knowledge_point 卡 retention 升序 top-5（FSRS 幂衰减近似 R(t,S)=(1+t/(3S))^-0.5）；
- kp_mastery：reps>0 卡 (reps-lapses)/reps clamp 0..1；
- 算法件（exercise_selector）消费面不变：kp_mastery/weak_points/strong_points/due_reviews。
"""
from __future__ import annotations

import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text

from app.services.learning.pg import _engine


def _strip_chapter_prefix(name: str) -> str:
    """`1.1_正数和负数` -> `正数和负数` (drop leading `n.n_`).——DeepTutor 纯函数搬运。"""
    return re.sub(r"^\d+(\.\d+)*_", "", name or "").strip()


def _retention(stability: float, last_review: datetime) -> float:
    """FSRS 幂衰减近似：R(t,S)=(1+t/(3S))^-0.5；S<=0 或无 last_review → 0。"""
    if not last_review or stability <= 0:
        return 0.0
    t = max(0.0, (datetime.now(timezone.utc) - last_review).total_seconds() / 86400.0)
    return float((1.0 + t / (3.0 * stability)) ** -0.5)


def _streak_days(user_id: str) -> int:
    """连续复习天数（reviewed_at::date DISTINCT；锚=今天，昨天也算连续起点）。"""
    with _engine.begin() as c:
        rows = c.execute(text(
            "SELECT DISTINCT reviewed_at::date AS d FROM sishu_review_records "
            "WHERE user_id=:u ORDER BY d DESC LIMIT 400"),
            {"u": user_id}).mappings().all()
    days = {r["d"] for r in rows}
    if not days:
        return 0
    today = datetime.now(timezone.utc).date()
    anchor = today if today in days else today - timedelta(days=1)
    if anchor not in days:
        return 0
    n = 0
    while anchor in days:
        n += 1
        anchor -= timedelta(days=1)
    return n


def build_learner_profile(user_id: str = "default") -> Any:
    """tupu 侧画像构建（⑤补补-2 真实现）：PG 面聚合，消费面与批 1 兼容。"""
    uid = user_id

    class _Profile:
        kp_mastery: dict = {}
        weak_points: list = []
        strong_points: list = []
        due_reviews: list = []
        streak_days: int = 0
        today_reviews: int = 0

    p = _Profile()
    p.user_id = uid
    now = datetime.now(timezone.utc)

    with _engine.begin() as c:
        cards = c.execute(text(
            "SELECT kind, item_id, stability, reps, lapses, due, last_review "
            "FROM sishu_review_cards WHERE user_id=:u"),
            {"u": uid}).mappings().all()
        p.streak_days = _streak_days(uid)
        p.today_reviews = int(c.execute(text(
            "SELECT count(*) AS n FROM sishu_review_records "
            "WHERE user_id=:u AND reviewed_at::date = CURRENT_DATE"),
            {"u": uid}).mappings().first()["n"])

    kps = []
    for r in cards:
        if r["kind"] == "knowledge_point" and (r["reps"] or 0) > 0:
            p.kp_mastery[r["item_id"]] = max(0.0, min(1.0, (r["reps"] - r["lapses"]) / r["reps"]))
            kps.append({"item_id": r["item_id"],
                        "retention": _retention(float(r["stability"]), r["last_review"])})
        if r["due"] and r["due"] <= now:
            p.due_reviews.append({"kind": r["kind"], "item_id": r["item_id"], "due": r["due"].isoformat()})

    ranked = sorted(kps, key=lambda x: x["retention"])
    p.weak_points = [{"item_id": x["item_id"], "retention": round(x["retention"], 4)}
                     for x in ranked[:5]]
    p.strong_points = [{"item_id": x["item_id"], "retention": round(x["retention"], 4)}
                       for x in sorted(kps, key=lambda x: -x["retention"])[:5]]
    return p


__all__ = ["_strip_chapter_prefix", "build_learner_profile"]
