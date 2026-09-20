# -*- coding: utf-8 -*-
"""⑤（spec §四）：教学引擎函数——fsrs_review/fsrs_due/mastery_query 等的引擎臂
（②三分离：工具=薄包装，服务=唯一引擎；MCP 工具与 /api/tutor 同源包装本模块；
存储读写全部经 learning_dao——算法保持纯）。"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.services.learning import fsrs
from app.services.learning import learning_dao as dao
from app.services.learning.pg import pg_session


def review_card(user_id: str, kind: str, item_id: str, rating: int, now: float = None) -> dict:
    """fsrs_review 的引擎（②三分离 engine 臂）：评分→FSRS 调度→落卡+流水。
    rating ∈ 1-4（Again/Hard/Good/Easy）；kind ∈ mother_question/knowledge_point；
    now 可注入（⑤a 时钟纪律——测试不 sleep）。"""
    if rating not in (fsrs.AGAIN, fsrs.HARD, fsrs.GOOD, fsrs.EASY):
        raise ValueError(f"rating 白名单 1-4（收到 {rating}）")
    if kind not in ("mother_question", "knowledge_point"):
        raise ValueError(f"kind 白名单 mother_question/knowledge_point（收到 {kind}）")
    import unittest.mock as _m
    import time as _t
    now = now or _t.time()

    state = dao.get_card(user_id, kind, item_id)
    if state is None:
        with _m.patch.object(fsrs, "_now", lambda: now):
            out = fsrs.new_card(rating)
    else:
        out = fsrs.review(state, rating)  # review 内部 now=_now()——真实时钟路径
    card_id = dao.upsert_card(user_id, kind, item_id, out)
    dao.append_record(card_id, user_id, rating,
                      max(0.0, out["due"] - now) / fsrs.SECONDS_PER_DAY)
    return {"card_id": card_id, "kind": kind, "item_id": item_id,
            "rating": rating,
            "interval_days": round(max(0.0, out["due"] - now) / fsrs.SECONDS_PER_DAY, 1),
            "stability": out["stability"], "difficulty": out["difficulty"],
            "reps": out["reps"], "lapses": out["lapses"]}


def due_cards(user_id: str, kind: str | None = None, limit: int = 20) -> list[dict]:
    """fsrs_due 的引擎（读面）：due<=now 按 due 升序。"""
    q = ("SELECT card_id, kind, item_id, stability, difficulty, reps, lapses, due, last_review "
         "FROM sishu_review_cards WHERE user_id=:u AND due <= now()")
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
            "FROM sishu_review_cards WHERE kind='knowledge_point' AND item_id=:i AND user_id=:u"),
            {"i": knowledge_point_id, "u": user_id}).mappings().first()
        history = s.execute(text(
            "SELECT r.rating, r.scheduled_interval, r.reviewed_at FROM sishu_review_records r "
            "JOIN sishu_review_cards c ON c.card_id=r.card_id "
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
