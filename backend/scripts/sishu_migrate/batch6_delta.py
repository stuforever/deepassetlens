# -*- coding: utf-8 -*-
"""v4批6 6.2/6.5：学习数据域 delta 迁移（协议 E v2：幂等+游标+行数对账+资产哈希双账）。

补齐 mother_questions.py（批6 WIP）因文件名错位漏迁的两源：
  review_states.json（87 条——WIP 误读 review_state.json 空 dict）
  review_log.json  （27 行——WIP 未覆盖）
及本批新收编域：
  chat_history.db notebook 三表（entries/categories/link——session_title 快照随迁）
  recitation/attempts.json → sishu_recitation
  practice_gen/*.json      → sishu_practice_gen（kind='cache'）
mq/variants/attempts/tags 的首迁在 mother_questions.py（184+6+27+0），本脚本复核行数。

幂等：全表键 upsert/存在即跳；游标=sishu_migration_cursor（domain='batch6_learning_delta'）；
哈希=源 JSON 文件 sha256 追加 v4_asset_hashes.json（协议 E v2 双账）。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))

import os

os.environ.setdefault("DT_TUTOR_WORKSPACE_ROOT", "data/experts/tutor/workspace")

from sqlalchemy import text

from app.services.sishu_data.cursor import append_asset_hashes, get_cursor, set_cursor
from app.services.sishu_data.pg import engine
from app.services.sishu.services.path_service import get_path_service

DOMAIN = "batch6_learning_delta"
WS = get_path_service().get_workspace_dir()
MQ_ROOT = WS / "mother_questions"
ADMIN = "local-admin"


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _upsert_review_states() -> int:
    src = MQ_ROOT / "review_states.json"
    if not src.exists():
        return 0
    data = json.loads(src.read_text(encoding="utf-8"))
    n = 0
    with engine.begin() as c:
        for mid, card in data.items():
            c.execute(text("""
                INSERT INTO sishu_mq_review_state (mq_id, user_id, doc)
                VALUES (:i, :u, CAST(:d AS JSONB))
                ON CONFLICT (mq_id) DO UPDATE SET doc=CAST(:d AS JSONB)"""),
                {"i": mid, "u": ADMIN, "d": json.dumps(card, ensure_ascii=False)})
            n += 1
    return n


def _upsert_review_log() -> int:
    src = MQ_ROOT / "review_log.json"
    if not src.exists():
        return 0
    rows = json.loads(src.read_text(encoding="utf-8"))
    with engine.begin() as c:
        have = c.execute(text(
            "SELECT count(*) FROM sishu_mq_review_log WHERE user_id=:u"),
            {"u": ADMIN}).scalar()
        if int(have or 0) >= len(rows):
            return 0  # 幂等：已灌（或更多）即跳
        for entry in rows:
            c.execute(text(
                "INSERT INTO sishu_mq_review_log (user_id, doc) VALUES (:u, CAST(:d AS JSONB))"),
                {"u": ADMIN, "d": json.dumps(entry, ensure_ascii=False)})
    return len(rows)


def _migrate_notebook() -> dict:
    db = get_path_service().get_chat_history_db().resolve()
    if not db.exists():
        return {"entries": 0, "categories": 0, "links": 0}
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    now = time.time()
    entries = conn.execute("""
        SELECT n.*, COALESCE(s.title, '') AS session_title
        FROM notebook_entries n LEFT JOIN sessions s ON s.id = n.session_id
    """).fetchall()
    n_e = 0
    with engine.begin() as c:
        for r in entries:
            d = dict(r)
            images = json.loads(d.pop("user_answer_images_json") or "[]")
            try:
                options = json.loads(d.pop("options_json") or "{}")
            except Exception:
                options = {}
            doc = {
                "session_id": d.get("session_id") or "",
                "session_title": d.get("session_title") or "",
                "turn_id": d.get("turn_id") or "",
                "question_id": d.get("question_id") or "",
                "question": d.get("question") or "",
                "question_type": d.get("question_type") or "",
                "options": options if isinstance(options, dict) else {},
                "correct_answer": d.get("correct_answer") or "",
                "explanation": d.get("explanation") or "",
                "difficulty": d.get("difficulty") or "",
                "user_answer": d.get("user_answer") or "",
                "user_answer_images": images if isinstance(images, list) else [],
                "is_correct": bool(d.get("is_correct")),
                "bookmarked": bool(d.get("bookmarked")),
                "followup_session_id": d.get("followup_session_id") or "",
                "ai_judgment": d.get("ai_judgment") or "",
                "created_at": float(d.get("created_at") or 0),
                "updated_at": float(d.get("updated_at") or 0),
            }
            existing = c.execute(text(
                "SELECT id FROM sishu_notebook_entries WHERE user_id=:u AND session_id=:s "
                "AND COALESCE(turn_id,'')=:t AND COALESCE(question_id,'')=:q LIMIT 1"),
                {"u": ADMIN, "s": doc["session_id"], "t": doc["turn_id"],
                 "q": doc["question_id"]}).fetchone()
            if existing:
                c.execute(text("""
                    UPDATE sishu_notebook_entries SET payload=CAST(:p AS JSONB),
                      session_title=:st, is_correct=:ic, bookmarked=:bm,
                      created_at_epoch=:ca, updated_at_epoch=:ua WHERE id=:id"""),
                    {"p": json.dumps(doc, ensure_ascii=False), "st": doc["session_title"],
                     "ic": doc["is_correct"], "bm": doc["bookmarked"],
                     "ca": doc["created_at"], "ua": doc["updated_at"], "id": existing[0]})
            else:
                c.execute(text("""
                    INSERT INTO sishu_notebook_entries (user_id, session_id, session_title,
                      turn_id, question_id, is_correct, bookmarked, created_at_epoch,
                      updated_at_epoch, payload)
                    VALUES (:u, :s, :st, :t, :q, :ic, :bm, :ca, :ua, CAST(:p AS JSONB))"""),
                    {"u": ADMIN, "s": doc["session_id"], "st": doc["session_title"],
                     "t": doc["turn_id"], "q": doc["question_id"], "ic": doc["is_correct"],
                     "bm": doc["bookmarked"], "ca": doc["created_at"], "ua": doc["updated_at"],
                     "p": json.dumps(doc, ensure_ascii=False)})
            n_e += 1
    cats = conn.execute("SELECT id, name, created_at FROM notebook_categories").fetchall()
    n_c = 0
    with engine.begin() as c:
        for r in cats:
            exists = c.execute(text(
                "SELECT id FROM sishu_notebook_categories WHERE user_id=:u AND name=:n LIMIT 1"),
                {"u": ADMIN, "n": r["name"]}).fetchone()
            if exists:
                continue
            c.execute(text(
                "INSERT INTO sishu_notebook_categories (user_id, name, created_at_epoch, payload) "
                "VALUES (:u, :n, :ca, CAST(:p AS JSONB))"),
                {"u": ADMIN, "n": r["name"], "ca": float(r["created_at"]),
                 "p": json.dumps({"name": r["name"]}, ensure_ascii=False)})
            n_c += 1
    # 关联表：sqlite 自增 id ≠ PG BIGSERIAL id——按 (session,turn,question) 三元组+类别名重指
    n_l = 0
    if n_e:
        links = conn.execute("""
            SELECT n.session_id, n.turn_id, n.question_id, l.category_id
            FROM notebook_entry_categories l
            JOIN notebook_entries n ON n.id = l.entry_id
        """).fetchall()
        cat_map = {r["name"]: r["id"] for r in cats}
        with engine.begin() as c:
            for r in links:
                pg_cat = c.execute(text(
                    "SELECT id FROM sishu_notebook_categories WHERE user_id=:u AND name=:n"),
                    {"u": ADMIN, "n": next((k for k, v in cat_map.items() if v == r["category_id"]), "")}).fetchone()
                if not pg_cat:
                    continue
                pg_entry = c.execute(text(
                    "SELECT id FROM sishu_notebook_entries WHERE user_id=:u AND session_id=:s "
                    "AND COALESCE(turn_id,'')=:t AND COALESCE(question_id,'')=:q LIMIT 1"),
                    {"u": ADMIN, "s": r["session_id"], "t": r["turn_id"] or "",
                     "q": r["question_id"] or ""}).fetchone()
                if not pg_entry:
                    continue
                c.execute(text(
                    "INSERT INTO sishu_notebook_entry_categories (entry_id, category_id) "
                    "VALUES (:e, :c) ON CONFLICT DO NOTHING"),
                    {"e": pg_entry[0], "c": pg_cat[0]})
                n_l += 1
    conn.close()
    return {"entries": n_e, "categories": n_c, "links": n_l}


def _migrate_recitation() -> int:
    src = WS / "recitation" / "attempts.json"
    if not src.exists():
        return 0
    rows = json.loads(src.read_text(encoding="utf-8"))
    n = 0
    with engine.begin() as c:
        have = c.execute(text("SELECT count(*) FROM sishu_recitation")).scalar()
        if int(have or 0) >= len(rows):
            return 0
        for d in rows:
            c.execute(text(
                "INSERT INTO sishu_recitation (user_id, payload) VALUES (:u, CAST(:p AS JSONB))"),
                {"u": ADMIN, "p": json.dumps(d, ensure_ascii=False)})
            n += 1
    return n


def _migrate_practice_gen() -> int:
    root = WS / "practice_gen"
    if not root.exists():
        return 0
    n = 0
    for p in sorted(root.glob("*.json")):
        chapter_id = p.stem
        doc = json.loads(p.read_text(encoding="utf-8"))
        with engine.begin() as c:
            exists = c.execute(text(
                "SELECT id FROM sishu_practice_gen WHERE user_id=:u AND kind='cache' "
                "AND chapter_id=:ch LIMIT 1"),
                {"u": ADMIN, "ch": chapter_id}).fetchone()
            if exists:
                continue
            c.execute(text(
                "INSERT INTO sishu_practice_gen (user_id, kind, chapter_id, payload) "
                "VALUES (:u, 'cache', :ch, CAST(:p AS JSONB))"),
                {"u": ADMIN, "ch": chapter_id, "p": json.dumps(doc, ensure_ascii=False)})
        n += 1
    return n


def _reconcile() -> dict:
    """行数对账（协议 E v2——源行数 vs PG 行数）。"""
    def _j(p):
        d = json.loads(p.read_text(encoding="utf-8"))
        return len(d) if isinstance(d, list) else len(d or {})

    src_rs = _j(MQ_ROOT / "review_states.json") if (MQ_ROOT / "review_states.json").exists() else 0
    src_rl = _j(MQ_ROOT / "review_log.json") if (MQ_ROOT / "review_log.json").exists() else 0
    src_rec = _j(WS / "recitation" / "attempts.json") if (WS / "recitation" / "attempts.json").exists() else 0
    src_pg = WS / "practice_gen"
    src_pg_n = len(list(src_pg.glob("*.json"))) if src_pg.exists() else 0
    with engine.connect() as c:
        pg = {
            "mq": c.execute(text("SELECT count(*) FROM sishu_mq_docs")).scalar(),
            "variants": c.execute(text("SELECT count(*) FROM sishu_question_variants")).scalar(),
            "review_state": c.execute(text("SELECT count(*) FROM sishu_mq_review_state")).scalar(),
            "review_log": c.execute(text("SELECT count(*) FROM sishu_mq_review_log")).scalar(),
            "attempts": c.execute(text("SELECT count(*) FROM sishu_mq_attempts")).scalar(),
            "recitation": c.execute(text("SELECT count(*) FROM sishu_recitation")).scalar(),
            "practice_gen": c.execute(text(
                "SELECT count(*) FROM sishu_practice_gen WHERE kind='cache'")).scalar(),
            "nb_entries": c.execute(text("SELECT count(*) FROM sishu_notebook_entries")).scalar(),
            "nb_categories": c.execute(text("SELECT count(*) FROM sishu_notebook_categories")).scalar(),
        }
    checks = {
        "mq": (184, pg["mq"]),
        "variants": (6, pg["variants"]),
        "review_state": (src_rs, pg["review_state"]),
        "review_log": (src_rl, pg["review_log"]),
        "attempts": (27, pg["attempts"]),
        "recitation": (src_rec, pg["recitation"]),
        "practice_gen": (src_pg_n, pg["practice_gen"]),
    }
    ok = all(s == g for s, g in checks.values())
    return {"ok": ok, "checks": checks, "notebook": {
        "nb_entries": pg["nb_entries"], "nb_categories": pg["nb_categories"]}}


def main() -> int:
    cur = get_cursor(DOMAIN)
    print(f"[{DOMAIN}] 游标={cur}")
    rs_n = _upsert_review_states()
    rl_n = _upsert_review_log()
    nb = _migrate_notebook()
    rec_n = _migrate_recitation()
    pg_n = _migrate_practice_gen()
    print(f"迁移: review_states={rs_n} review_log={rl_n} notebook={nb} recitation={rec_n} practice_gen={pg_n}")
    # 资产哈希双账（协议 E v2 契约：[{key, mime, size, sha256}]）
    hashes = []
    for rel in ["mother_questions/index.json", "mother_questions/variants.json",
                "mother_questions/review_states.json", "mother_questions/review_log.json",
                "mother_questions/tags.json", "mother_questions/attempts.json",
                "recitation/attempts.json"]:
        p = WS / rel
        if p.exists():
            hashes.append({"key": rel, "mime": "application/json",
                           "size": p.stat().st_size, "sha256": _sha256(p)})
    db = get_path_service().get_chat_history_db().resolve()
    if db.exists():
        hashes.append({"key": "chat_history.db", "mime": "application/x-sqlite3",
                       "size": db.stat().st_size, "sha256": _sha256(db)})
    append_asset_hashes(DOMAIN, hashes)
    rec = _reconcile()
    print("对账:", json.dumps(rec, ensure_ascii=False))
    total_rows = rs_n + rl_n + rec_n + pg_n + nb["entries"] + nb["categories"] + nb["links"]
    set_cursor(DOMAIN, f"delta:{total_rows}", total_rows)
    print("计数:", {"review_states": rs_n, "review_log": rl_n, "notebook": nb,
                    "recitation": rec_n, "practice_gen": pg_n})
    return 0 if rec["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
