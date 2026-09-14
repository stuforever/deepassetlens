# -*- coding: utf-8 -*-
"""⑤（spec §四）：教学引擎函数——fsrs_review/fsrs_due/mastery_query 等的引擎臂
（②三分离：工具=薄包装，服务=唯一引擎；MCP 工具与 /api/tutor 同源包装本模块）。"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text

from app.services.learning import fsrs
from app.services.learning.pg import pg_session


def review_card(user_id: str, kind: str, item_id: str, rating: int) -> dict:
    """fsrs_review 的引擎（②三分离 engine 臂）：评分→FSRS 调度→落卡+流水。
    rating ∈ 1-4（Again/Hard/Good/Easy）；kind ∈ mother_question/knowledge_point。"""
    if rating not in (fsrs.AGAIN, fsrs.HARD, fsrs.GOOD, fsrs.EASY):
        raise ValueError(f"rating 白名单 1-4（收到 {rating}）")
    if kind not in ("mother_question", "knowledge_point"):
        raise ValueError(f"kind 白名单 mother_question/knowledge_point（收到 {kind}）")
    with pg_session() as s:
        row = s.execute(text(
            "SELECT card_id, stability, difficulty, reps, lapses, "
            "EXTRACT(EPOCH FROM (last_review - now())) AS last_neg, "
            "stability AS st "
            "FROM learning_review_cards WHERE kind=:k AND item_id=:i AND user_id=:u FOR UPDATE"),
            {"k": kind, "i": item_id, "u": user_id}).mappings().first()
        import time as _t
        if row:
            state = {"stability": row["stability"], "difficulty": row["difficulty"],
                     "reps": row["reps"], "lapses": row["lapses"],
                     "due": _t.time(), "last_review": _t.time() + float(row["last_neg"] or 0),
                     "elapsed_days": 0}
            card_id = row["card_id"]
        else:
            state = None
            card_id = str(uuid.uuid4())
        if state is None:
            out = fsrs.new_card(rating)
        else:
            out = fsrs.review(state, rating)
        s.execute(text(
            "INSERT INTO learning_review_cards (card_id, kind, item_id, user_id, stability, "
            "difficulty, reps, lapses, due, last_review) "
            "VALUES (:c, :k, :i, :u, :st, :df, :rp, :lp, now() + make_interval(secs => :due_in), now()) "
            "ON CONFLICT (kind, item_id, user_id) DO UPDATE SET stability=EXCLUDED.stability, "
            "difficulty=EXCLUDED.difficulty, reps=EXCLUDED.reps, lapses=EXCLUDED.lapses, "
            "due=EXCLUDED.due, last_review=now()"),
            {"c": card_id, "k": kind, "i": item_id, "u": user_id,
             "st": out["stability"], "df": out["difficulty"], "rp": out["reps"],
             "lp": out["lapses"], "due_in": max(0.0, out["due"] - _t.time())})
        s.execute(text(
            "INSERT INTO learning_review_records (card_id, user_id, rating, scheduled_interval) "
            "SELECT :c, :u, :r, :si WHERE EXISTS (SELECT 1 FROM learning_review_cards WHERE card_id=:c)"),
            {"c": card_id, "u": user_id, "r": rating, "si": max(0.0, out["due"] - _t.time()) / fsrs.SECONDS_PER_DAY})
        return {"card_id": card_id, "kind": kind, "item_id": item_id,
                "rating": rating, "interval_days": round((out["due"] - _t.time()) / fsrs.SECONDS_PER_DAY, 1),
                "stability": out["stability"], "difficulty": out["difficulty"],
                "reps": out["reps"], "lapses": out["lapses"]}


def due_cards(user_id: str, kind: str | None = None, limit: int = 20) -> list[dict]:
    """fsrs_due 的引擎（读面）：due<=now 按 due 升序。"""
    q = ("SELECT card_id, kind, item_id, stability, difficulty, reps, lapses, due, last_review "
         "FROM learning_review_cards WHERE user_id=:u AND due <= now()")
    params: dict[str, Any] = {"u": user_id}
    if kind:
        q += " AND kind=:k"
        params["k"] = kind
    q += " ORDER BY due ASC LIMIT :lim"
    params["lim"] = max(1, min(int(limit), 100))
    with pg_session() as s:
        rows = s.execute(text(q), params).mappings().all()
    return [dict(r) for r in rows]


def mastery_query(user_id: str, knowledge_point_id: str) -> dict:
    """mastery_query 的引擎（读面）：kp 卡状态+复习史→compute_mastery 评分。"""
    with pg_session() as s:
        card = s.execute(text(
            "SELECT card_id, stability, difficulty, reps, lapses, due, last_review "
            "FROM learning_review_cards WHERE kind='knowledge_point' AND item_id=:i AND user_id=:u"),
            {"i": knowledge_point_id, "u": user_id}).mappings().first()
        history = s.execute(text(
            "SELECT r.rating, r.scheduled_interval, r.reviewed_at FROM learning_review_records r "
            "JOIN learning_review_cards c ON c.card_id=r.card_id "
            "WHERE c.kind='knowledge_point' AND c.item_id=:i AND c.user_id=:u ORDER BY r.reviewed_at ASC"),
            {"i": knowledge_point_id, "u": user_id}).mappings().all()
    from app.services.learning.mastery import compute_mastery
    correctness = [r["rating"] >= fsrs.HARD for r in history]
    return {
        "knowledge_point_id": knowledge_point_id,
        "card": (dict(card) if card else None),
        "attempts": len(history),
        "mastery": compute_mastery(correctness),
        "history": [dict(r) for r in history[-10:]],
    }
