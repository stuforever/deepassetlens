# -*- coding: utf-8 -*-
"""v4批6 6.2：mother_questions 域迁移（协议 E v2）。
源=vendor JSON store（data/experts/tutor/workspace/data/user/workspace/mother_questions/
  index.json 184 题 + variants.json 6 变体 + review_state/tags/attempts JSON 文件），
目标=PG sishu_mq_docs/sishu_question_variants/sishu_mq_review_state/sishu_mq_tags/sishu_mq_attempts。
幂等（PK upsert）+游标断点+行数对账+文档哈希双账。vendor 窄表 learning_mother_questions
（批2 已改名 sishu_mother_questions）=错题联动实体，本脚本不触碰（异实体，E-60）。"""
import io
import json
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text

from app.services.sishu_data.pg import engine
from app.services.sishu_data.cursor import get_cursor, set_cursor, sha256_of, append_asset_hashes

STORE = Path(__file__).resolve().parents[2] / "data" / "experts" / "tutor" / "workspace" / "data" / "user" / "workspace" / "mother_questions"
DOMAIN = "mother_questions"


def _load(name: str):
    f = STORE / name
    if not f.exists():
        return []
    return json.loads(f.read_text(encoding="utf-8"))


def main() -> int:
    mqs = _load("index.json")
    vqs = _load("variants.json")
    rs = _load("review_state.json") or {}
    tags = _load("tags.json") or []
    atts = _load("attempts.json") or []
    cur = get_cursor(DOMAIN)
    print(f"源规模: mq={len(mqs)} variants={len(vqs)} rs={len(rs)} tags={len(tags)} attempts={len(atts)} | 游标={cur}")

    hashes = []
    inserted = 0
    with engine.begin() as c:
        for m in mqs:
            mid = m.get("id")
            if not mid:
                continue
            c.execute(text("""
                INSERT INTO sishu_mq_docs (mq_id, doc, status, subject, grade, knowledge_point_id,
                                           mastery_status, simhash, update_time)
                VALUES (:i, CAST(:d AS JSONB), :s, :sj, :g, :kp, :ms, :sh, :u)
                ON CONFLICT (mq_id) DO UPDATE SET doc=CAST(:d AS JSONB), status=:s, subject=:sj,
                  grade=:g, knowledge_point_id=:kp, mastery_status=:ms, simhash=:sh, update_time=:u"""),
                {"i": mid, "d": json.dumps(m, ensure_ascii=False),
                 "s": m.get("status") or "active", "sj": m.get("subject"), "g": m.get("grade"),
                 "kp": m.get("knowledge_point_id"), "ms": m.get("mastery_status"),
                 "sh": m.get("simhash"), "u": m.get("update_time") or m.get("update_time", 0)})
            inserted += 1
            if m.get("assets"):
                hashes.append({"key": f"mq/{mid}/assets",
                               "size": len(json.dumps(m.get("assets"), ensure_ascii=False)),
                               "sha256": sha256_of(json.dumps(m.get("assets"), ensure_ascii=False).encode("utf-8"))})
        for v in vqs:
            c.execute(text("""
                INSERT INTO sishu_question_variants (vq_id, mother_id, doc, status, update_time)
                VALUES (:i, :m, CAST(:d AS JSONB), :s, :u)
                ON CONFLICT (vq_id) DO UPDATE SET doc=CAST(:d AS JSONB), status=:s, update_time=:u"""),
                {"i": v.get("id"), "m": v.get("mother_id"), "d": json.dumps(v, ensure_ascii=False),
                 "s": v.get("status") or "active", "u": v.get("update_time")})
        for mid, st in rs.items():
            c.execute(text("""
                INSERT INTO sishu_mq_review_state (mq_id, doc) VALUES (:i, CAST(:d AS JSONB))
                ON CONFLICT (mq_id) DO UPDATE SET doc=CAST(:d AS JSONB)"""),
                {"i": mid, "d": json.dumps(st, ensure_ascii=False)})
        for tg in tags:
            c.execute(text("""
                INSERT INTO sishu_mq_tags (name, color, doc) VALUES (:n, :c, CAST(:d AS JSONB))
                ON CONFLICT (name) DO UPDATE SET color=:c, doc=CAST(:d AS JSONB)"""),
                {"n": tg.get("name"), "c": tg.get("color"), "d": json.dumps(tg, ensure_ascii=False)})
        for a in atts:
            c.execute(text("""
                INSERT INTO sishu_mq_attempts (attempt_id, mother_id, doc) VALUES (:i, :m, CAST(:d AS JSONB))
                ON CONFLICT (attempt_id) DO UPDATE SET doc=CAST(:d AS JSONB)"""),
                {"i": a.get("id"), "m": a.get("mother_id") or a.get("mother_question_id"),
                 "d": json.dumps(a, ensure_ascii=False)})
        set_cursor(DOMAIN, str(len(mqs)), inserted)

    # 行数对账
    with engine.connect() as c:
        n_doc = c.execute(text("SELECT COUNT(*) FROM sishu_mq_docs")).scalar()
        n_vq = c.execute(text("SELECT COUNT(*) FROM sishu_question_variants")).scalar()
        n_rs = c.execute(text("SELECT COUNT(*) FROM sishu_mq_review_state")).scalar()
    ok = n_doc == len(mqs) and n_vq == len(vqs)
    if hashes:
        append_asset_hashes(DOMAIN, hashes)
    print(f"对账: doc {n_doc}/{len(mqs)} vq {n_vq}/{len(vqs)} rs {n_rs}/{len(rs)} -> {'OK' if ok else 'MISMATCH!'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
