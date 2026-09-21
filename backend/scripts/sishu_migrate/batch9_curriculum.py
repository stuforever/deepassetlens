# -*- coding: utf-8 -*-
"""三轨M15(批9) 9.1：curriculum 盘上 JSON→PG 三表族（textbooks/chapters/kps）。"""
import sys, json
sys.path.insert(0, ".")
import os
os.environ.setdefault("DT_TUTOR_WORKSPACE_ROOT", "data/experts/tutor/workspace")
from pathlib import Path
from sqlalchemy import text
from app.services.sishu.services.path_service import get_path_service
from app.services.sishu_data.pg import engine
from app.services.sishu_data.cursor import append_asset_hashes

WS = get_path_service().get_workspace_dir()
DOMAIN = "batch9_curriculum"
n_t = n_c = n_k = 0

# vendor CurriculumStore 数据位置：data/user/workspace/curriculum/
cur_root = WS / "curriculum"

def _upsert(tbl, key, payload):
    with engine.begin() as c:
        c.execute(text(f"""
            INSERT INTO {tbl} (payload) VALUES (CAST(:p AS JSONB))
        """), {"p": payload})

# textbooks
tb_file = cur_root / "textbooks.json"
if tb_file.exists():
    items = json.loads(tb_file.read_text(encoding="utf-8"))
    if isinstance(items, dict):
        items = items.get("items") or items.get("textbooks") or list(items.values())
    for m in items:
        payload = json.dumps(m, ensure_ascii=False).replace(chr(0), "")
        tid = m.get("id") or m.get("textbook_id") or ""
        with engine.begin() as c:
            exists = c.execute(text(
                "SELECT 1 FROM sishu_textbooks WHERE textbook_id=:i"),
                {"i": tid}).fetchone()
            if not exists:
                c.execute(text("INSERT INTO sishu_textbooks (textbook_id, name, subject, payload) VALUES (:i, :n, :s, CAST(:p AS JSONB))"),
                          {"i": tid, "n": m.get("name"), "s": m.get("subject"), "p": payload})
                n_t += 1

# chapters
ch_file = cur_root / "chapters.json"
if ch_file.exists():
    items = json.loads(ch_file.read_text(encoding="utf-8"))
    if isinstance(items, dict):
        items = items.get("items") or items.get("chapters") or list(items.values())
    for m in items:
        payload = json.dumps(m, ensure_ascii=False).replace(chr(0), "")
        cid = m.get("id") or ""
        with engine.begin() as c:
            exists = c.execute(text(
                "SELECT 1 FROM sishu_chapters WHERE chapter_id=:i"),
                {"i": cid}).fetchone()
            if not exists:
                c.execute(text("INSERT INTO sishu_chapters (chapter_id, textbook_id, payload) VALUES (:i, :t, CAST(:p AS JSONB))"),
                          {"i": cid, "t": m.get("textbook_id"), "p": payload})
                n_c += 1

# kps
kp_file = cur_root / "knowledge_points.json"
if kp_file.exists():
    items = json.loads(kp_file.read_text(encoding="utf-8"))
    if isinstance(items, dict):
        items = items.get("items") or items.get("knowledge_points") or list(items.values())
    for m in items:
        payload = json.dumps(m, ensure_ascii=False).replace(chr(0), "")
        kid = m.get("id") or ""
        with engine.begin() as c:
            exists = c.execute(text(
                "SELECT 1 FROM sishu_knowledge_points WHERE payload->>'id'=:i"),
                {"i": kid}).fetchone()
            if not exists:
                c.execute(text("INSERT INTO sishu_knowledge_points (kp_id, payload) VALUES (:i, CAST(:p AS JSONB))"),
                          {"i": kid, "p": payload})
                n_k += 1

with engine.begin() as c:
    c.execute(text("""
        INSERT INTO sishu_migration_cursor (domain, last_id, rows_done, updated_at)
        VALUES (:d, :l, :r, now())
        ON CONFLICT (domain) DO UPDATE SET last_id=EXCLUDED.last_id, rows_done=EXCLUDED.rows_done, updated_at=now()"""),
        {"d": DOMAIN, "l": f"t={n_t},c={n_c},k={n_k}", "r": n_t + n_c + n_k})
print(f"textbooks={n_t} chapters={n_c} kps={n_k}")
