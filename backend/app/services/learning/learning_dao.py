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
                       error_context: str = "", question: Optional[dict] = None,
                       my_answer: str = "", error_type: str = "", source: str = "practice") -> str:
    """⑤补补-5 扩参（L287 基底向后兼容——旧两参调用不破；新列全 nullable 无默认行为）。

    source：chat（对话式）/manual（手动）/practice（练习自动）——渠道溯源。
    """
    import json as _json
    import uuid as _u
    wq_id = str(_u.uuid4())
    with pg_session() as s:
        s.execute(text(
            "INSERT INTO learning_wrong_questions (wq_id, user_id, mother_question_id, "
            "variant_text, error_context, question, my_answer, error_type, source) "
            "VALUES (:w, :u, :m, :v, :e, CAST(:q AS JSON), :ma, :et, :src)"),
            {"w": wq_id, "u": user_id, "m": mother_question_id or "",
             "v": variant_text, "e": error_context or "",
             "q": _json.dumps(question) if question else None,
             "ma": my_answer or "", "et": error_type or "", "src": source or "practice"})
    return wq_id


def mother_question_find_or_create(keywords: str, knowledge_point_id: str = "",
                                   title: str = "", archetype_text: str = "") -> dict:
    """⑤补补-5 新工具数据面：关键词/知识点搜母题→命中返回（created=False）/未命中创建
    （kp 标注必填其一——两皆空 422 由端点层判）。返回 {mq_id, created, title, knowledge_point_id}。
    """
    kw = (keywords or "").strip()
    with pg_session() as s:
        row = None
        if kw:
            row = s.execute(text(
                "SELECT mq_id, title, knowledge_point_id FROM learning_mother_questions "
                "WHERE title ILIKE :pat OR archetype_text ILIKE :pat "
                "ORDER BY mq_id LIMIT 1"),
                {"pat": f"%{kw}%"}).mappings().first()
        if row is None and knowledge_point_id:
            row = s.execute(text(
                "SELECT mq_id, title, knowledge_point_id FROM learning_mother_questions "
                "WHERE knowledge_point_id=:kp ORDER BY mq_id LIMIT 1"),
                {"kp": knowledge_point_id}).mappings().first()
        if row is not None:
            return {"mq_id": row["mq_id"], "created": False,
                    "title": row["title"], "knowledge_point_id": row["knowledge_point_id"]}
        if not knowledge_point_id:
            return {"mq_id": "", "created": False, "title": "",
                    "knowledge_point_id": "", "error": "kp_or_keyword_required"}
        created = mother_question_create(
            title=title or f"{kw}（自动）" if kw else "未命名母题（自动）",
            archetype_text=archetype_text or f"（待补题干——关键词：{kw}）",
            knowledge_point_id=knowledge_point_id)
        return {"mq_id": created["mq_id"], "created": True,
                "title": created["title"], "knowledge_point_id": knowledge_point_id}


def wrong_question_update(user_id: str, wq_id: str, patch: dict) -> Optional[dict]:
    """⑤补补-5 管理面：错题编辑/状态流转（仅本人——user_id 双条件）。"""
    fields: dict = {}
    if patch.get("status") in ("open", "resolved"):
        fields["status"] = patch["status"]
    if patch.get("error_type"):
        fields["error_type"] = patch["error_type"]
    if patch.get("my_answer"):
        fields["my_answer"] = patch["my_answer"]
    if not fields:
        return None
    if fields.get("status") == "resolved":
        fields["resolved_at"] = "now()"
    sets = ", ".join(f"{k} = :{k}" if k != "resolved_at" else "resolved_at = now()" for k in fields)
    params = {k: v for k, v in fields.items() if k != "resolved_at"}
    params.update({"w": wq_id, "u": user_id})
    with pg_session() as s:
        row = s.execute(text(
            f"UPDATE learning_wrong_questions SET {sets} WHERE wq_id=:w AND user_id=:u "
            "RETURNING wq_id, status, error_type, my_answer, resolved_at"),
            params).mappings().first()
    return dict(row) if row else None


def wrong_question_soft_delete(user_id: str, wq_id: str) -> bool:
    """⑤补补-5 管理面：软删——status 置 resolved + variant_text 前缀 [已删除]（可追溯）。"""
    with pg_session() as s:
        row = s.execute(text(
            "UPDATE learning_wrong_questions SET status='resolved', resolved_at=now(), "
            "variant_text = '[已删除] ' || variant_text "
            "WHERE wq_id=:w AND user_id=:u AND variant_text NOT LIKE '[已删除]%' "
            "RETURNING wq_id"),
            {"w": wq_id, "u": user_id}).first()
    return row is not None


def wrong_question_query(user_id: str, status: str = "", limit: int = 20,
                         error_type: str = "", source: str = "") -> list[dict]:
    q = ("SELECT wq.wq_id, wq.mother_question_id, wq.variant_text, wq.error_context, wq.status, "
         "wq.wrong_at, wq.resolved_at, wq.question, wq.my_answer, wq.error_type, wq.source, "
         "mq.knowledge_point_id AS mother_kp "
         "FROM learning_wrong_questions wq "
         "LEFT JOIN learning_mother_questions mq ON mq.mq_id = wq.mother_question_id "
         "WHERE wq.user_id=:u")
    params: dict = {"u": user_id}
    if status in ("open", "resolved"):
        q += " AND wq.status=:st"
        params["st"] = status
    if error_type:
        q += " AND wq.error_type=:et"
        params["et"] = error_type
    if source:
        q += " AND wq.source=:src"
        params["src"] = source
    q += " ORDER BY wq.wrong_at DESC LIMIT :lim"
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


# ---------- ⑤补补-1：母题 CRUD（题库 admin 端点族数据面） ----------

def mother_question_create(title: str, archetype_text: str, knowledge_point_id: str) -> dict:
    """母题入库（admin）。mq_id 缺省生成；enabled 缺省 TRUE。"""
    import uuid
    mq_id = f"mq-{uuid.uuid4().hex[:12]}"
    with pg_session() as s:
        s.execute(text(
            "INSERT INTO learning_mother_questions "
            "(mq_id, title, archetype_text, knowledge_point_id) "
            "VALUES (:mid, :title, :arch, :kp)"),
            {"mid": mq_id, "title": title, "arch": archetype_text, "kp": knowledge_point_id})
    return {"mq_id": mq_id, "title": title, "archetype_text": archetype_text,
            "knowledge_point_id": knowledge_point_id, "variant_count": 0, "enabled": True}


def mother_question_update(mq_id: str, patch: dict) -> Optional[dict]:
    """母题改（admin）——patch 白名单键集。返回改后行；不存在返回 None。"""
    cols = {"title", "archetype_text", "knowledge_point_id", "enabled", "variant_count"}
    fields = {k: v for k, v in patch.items() if k in cols}
    if not fields:
        return None
    sets = ", ".join(f"{k} = :{k}" for k in fields)
    fields["mid"] = mq_id
    with pg_session() as s:
        row = s.execute(text(
            f"UPDATE learning_mother_questions SET {sets} WHERE mq_id = :mid "
            "RETURNING mq_id, title, archetype_text, knowledge_point_id, variant_count, enabled"),
            fields).mappings().first()
    return dict(row) if row else None


def mother_question_delete(mq_id: str) -> bool:
    """母题删（admin，物理删——母题是管理数据，非专家卡「只关不删」语义）。"""
    with pg_session() as s:
        row = s.execute(text(
            "DELETE FROM learning_mother_questions WHERE mq_id = :mid RETURNING mq_id"),
            {"mid": mq_id}).first()
    return row is not None


def mother_questions_list(kp: str = "", limit: int = 100) -> list[dict]:
    """母题清单（admin）——可选 kp 过滤（idx_lmq_kp 路径）。"""
    with pg_session() as s:
        if kp:
            rows = s.execute(text(
                "SELECT mq_id, title, archetype_text, knowledge_point_id, variant_count, enabled "
                "FROM learning_mother_questions WHERE knowledge_point_id = :kp ORDER BY mq_id LIMIT :n"),
                {"kp": kp, "n": limit}).mappings().all()
        else:
            rows = s.execute(text(
                "SELECT mq_id, title, archetype_text, knowledge_point_id, variant_count, enabled "
                "FROM learning_mother_questions ORDER BY mq_id LIMIT :n"),
                {"n": limit}).mappings().all()
    return [dict(r) for r in rows]
