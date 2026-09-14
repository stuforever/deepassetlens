# -*- coding: utf-8 -*-
"""⑤a：薄 DAO——算法函数保持纯，存储读写经此注入。三态+流水+恢复锚。
（批 1 补完：service.py 的直接 SQL 收编至此——一个引擎两张脸的存储面。）"""
from __future__ import annotations

import time
from typing import Optional

from sqlalchemy import text

from .pg import pg_session


def get_card(user_id: str, kind: str, item_id: str) -> Optional[dict]:
    """读态：miss 返回 None（调用方 new_card()）。"""
    with pg_session() as s:
        row = s.execute(text(
            "SELECT stability, difficulty, reps, lapses, "
            "EXTRACT(EPOCH FROM due) AS due, "
            "EXTRACT(EPOCH FROM last_review) AS last_review "
            "FROM learning_review_cards WHERE kind=:k AND item_id=:i AND user_id=:u"),
            {"k": kind, "i": item_id, "u": user_id}).mappings().first()
        if not row:
            return None
        d = dict(row)
        d["due"] = float(d["due"]) if d["due"] is not None else time.time()
        d["last_review"] = float(d["last_review"]) if d["last_review"] is not None else time.time()
        return d


def upsert_card(user_id: str, kind: str, item_id: str, st: dict) -> str:
    """写态：更新幂等（UNIQUE 冲突走更新）；返回 card_id（流水外键）。"""
    card_id = f"{kind}:{item_id}:{user_id}"
    with pg_session() as s:
        s.execute(text("""
            INSERT INTO learning_review_cards (card_id, kind, item_id, user_id,
                stability, difficulty, reps, lapses, due, last_review)
            VALUES (:c, :k, :i, :u, :st, :df, :r, :l,
                    to_timestamp(:d), to_timestamp(:lr))
            ON CONFLICT (kind, item_id, user_id) DO UPDATE SET
                stability=EXCLUDED.stability, difficulty=EXCLUDED.difficulty,
                reps=EXCLUDED.reps, lapses=EXCLUDED.lapses, due=EXCLUDED.due,
                last_review=EXCLUDED.last_review"""),
            {"c": card_id, "k": kind, "i": item_id, "u": user_id,
             "st": st["stability"], "df": st["difficulty"], "r": st["reps"], "l": st["lapses"],
             "d": st["due"], "lr": st["last_review"]})
    return card_id


def append_record(card_id: str, user_id: str, rating: int, interval: float) -> None:
    """流水：review_records 是对账原料+恢复锚（⑤a §二）。"""
    with pg_session() as s:
        s.execute(text("INSERT INTO learning_review_records (card_id, user_id, rating, "
                       "scheduled_interval) VALUES (:c, :u, :r, :si)"),
                  {"c": card_id, "u": user_id, "r": rating, "si": interval})


def list_records(user_id: str, kind: str, item_id: str) -> list[dict]:
    """重放原料：按时间升序的评分流水。"""
    with pg_session() as s:
        rows = s.execute(text(
            "SELECT r.rating, EXTRACT(EPOCH FROM r.reviewed_at) AS reviewed_at "
            "FROM learning_review_records r WHERE r.card_id=:c ORDER BY r.id ASC"),
            {"c": f"{kind}:{item_id}:{user_id}"}).mappings().all()
    return [{"rating": int(r["rating"]), "reviewed_at": float(r["reviewed_at"])} for r in rows]


def rebuild_card_from_records(user_id: str, kind: str, item_id: str) -> dict:
    """恢复锚：从流水重放重建卡状态（⑤a 验收：行级重建断言的载体）。
    逐条评分按其 reviewed_at 作为时钟回放 FSRS（首评 new_card，后续 review）。"""
    records = list_records(user_id, kind, item_id)
    if not records:
        raise ValueError(f"无流水可重放: {kind}/{item_id}/{user_id}")
    state: Optional[dict] = None
    for rec in records:
        if state is None:
            state = fsrs_new_card(rec["rating"], now=rec["reviewed_at"])
        else:
            state = fsrs_review(state, rec["rating"], now=rec["reviewed_at"])
    return state


# ---- FSRS 纯函数注入壳（时钟可注入——rebuild 重放用，不动物理算法码） ----

def fsrs_new_card(rating: int, now: float) -> dict:
    from . import fsrs as _f
    import unittest.mock as _m
    with _m.patch.object(_f, "_now", lambda: now):
        return _f.new_card(rating)


def fsrs_review(state: dict, rating: int, now: float) -> dict:
    from . import fsrs as _f
    import unittest.mock as _m
    snap = dict(state)
    snap["last_review"] = now  # 重放时钟=流水时间轴
    with _m.patch.object(_f, "_now", lambda: now):
        return _f.review(snap, rating)


# ---- 错题面（⑤b wrong_question_add/query + 导出） ----

def wrong_question_add(user_id: str, variant_text: str, mother_question_id: str = "",
                       error_context: str = "") -> str:
    import uuid as _u
    wq_id = str(_u.uuid4())
    with pg_session() as s:
        s.execute(text(
            "INSERT INTO learning_wrong_questions (wq_id, user_id, mother_question_id, "
            "variant_text, error_context) VALUES (:w, :u, :m, :v, :e)"),
            {"w": wq_id, "u": user_id, "m": mother_question_id or "",
             "v": variant_text, "e": error_context or ""})
    return wq_id


def wrong_question_query(user_id: str, status: str = "", limit: int = 20) -> list[dict]:
    q = ("SELECT wq_id, mother_question_id, variant_text, error_context, status, "
         "wrong_at, resolved_at FROM learning_wrong_questions WHERE user_id=:u")
    params: dict = {"u": user_id}
    if status in ("open", "resolved"):
        q += " AND status=:st"
        params["st"] = status
    q += " ORDER BY wrong_at DESC LIMIT :lim"
    params["lim"] = max(1, min(int(limit), 100))
    with pg_session() as s:
        rows = s.execute(text(q), params).mappings().all()
    return [dict(r) for r in rows]


def wrong_question_export_rows(user_id: str) -> list[dict]:
    """导出原料（⑤b export_wrong_book：全部 open+resolved，落文件走 result_ref）。"""
    return wrong_question_query(user_id, status="", limit=100)


def mother_questions_by_kps(kps: list[str]) -> list[dict]:
    """⑤b select_exercises 数据源：知识点池→母题清单。"""
    if not kps:
        return []
    with pg_session() as s:
        rows = s.execute(text(
            "SELECT mq_id, title, archetype_text, knowledge_point_id, variant_count "
            "FROM learning_mother_questions WHERE enabled=TRUE "
            "AND knowledge_point_id = ANY(:kps)"),
            {"kps": list(kps)}).mappings().all()
    return [dict(r) for r in rows]
