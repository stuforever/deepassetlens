# -*- coding: utf-8 -*-
"""三轨M13(批7) 7.1：book_bk_* 目录七件套→PG（协议 E v2 幂等+双账+游标）。"""
import sys, json, hashlib

def _clean(s: str) -> str:
    """PG JSONB 不接受 \u0000——剥离 null 字节（vendor 盘上数据含之）。"""
    return s.replace('\\u0000', '')  # 6 字符文本序列（JSON 内  字面）
sys.path.insert(0, ".")
import os
os.environ.setdefault("DT_TUTOR_WORKSPACE_ROOT", "data/experts/tutor/workspace")
from pathlib import Path
from sqlalchemy import text
from app.services.sishu_data.pg import engine
from app.services.sishu_data.cursor import append_asset_hashes

BOOK_ROOT = Path("data/experts/tutor/workspace/data/user/workspace/book")
DOMAIN = "batch7_books"
hashes = []
migrated = skipped = 0

for book_dir in sorted(BOOK_ROOT.iterdir()):
    if not book_dir.is_dir():
        continue
    manifest_p = book_dir / "manifest.json"
    if not manifest_p.exists():
        continue
    m = json.loads(manifest_p.read_text(encoding="utf-8"))
    bid = m.get("id") or book_dir.name.replace("book_", "")
    hashes.append({"key": f"book/{book_dir.name}/manifest.json", "mime": "application/json",
                   "size": manifest_p.stat().st_size,
                   "sha256": hashlib.sha256(manifest_p.read_bytes()).hexdigest()})
    with engine.connect() as c:
        row = c.execute(text("SELECT book_id FROM sishu_books WHERE book_id=:b"), {"b": bid}).fetchone()
    if row:
        skipped += 1
        continue
    with engine.begin() as c:
        c.execute(text("""
            INSERT INTO sishu_books (book_id, title, description, language, status, manifest)
            VALUES (:b, :t, :d, :l, :s, CAST(:m AS JSONB))
            ON CONFLICT (book_id) DO NOTHING"""),
            {"b": bid, "t": m.get("title") or book_dir.name, "d": m.get("description"),
             "l": m.get("language") or "zh", "s": m.get("status") or "unknown",
             "m": _clean(json.dumps(m, ensure_ascii=False))})
        spine_p = book_dir / "spine.json"
        if spine_p.exists():
            spine = json.loads(spine_p.read_text(encoding="utf-8"))
            c.execute(text("""
                INSERT INTO sishu_book_spines (book_id, spine) VALUES (:b, CAST(:s AS JSONB))
                ON CONFLICT (book_id) DO UPDATE SET spine=CAST(:s AS JSONB)"""),
                {"b": bid, "s": _clean(json.dumps(spine, ensure_ascii=False))})
            hashes.append({"key": f"book/{book_dir.name}/spine.json", "mime": "application/json",
                           "size": spine_p.stat().st_size,
                           "sha256": hashlib.sha256(spine_p.read_bytes()).hexdigest()})
        pages_dir = book_dir / "pages"
        if pages_dir.exists():
            for pf in sorted(pages_dir.glob("*.json")):
                page = json.loads(pf.read_text(encoding="utf-8"))
                pid = page.get("id") or pf.stem
                c.execute(text("""
                    INSERT INTO sishu_book_pages (page_id, book_id, page_no, title, payload)
                    VALUES (:p, :b, :n, :t, CAST(:pl AS JSONB))
                    ON CONFLICT (page_id) DO NOTHING"""),
                    {"p": pid, "b": bid, "n": page.get("order") or 0,
                     "t": page.get("title"), "pl": _clean(json.dumps(page, ensure_ascii=False))})
                for blk in page.get("blocks") or []:
                    blk_id = blk.get("id") or f"{pid}_{hashlib.sha1(json.dumps(blk, sort_keys=True)).hexdigest()[:10]}"
                    c.execute(text("""
                        INSERT INTO sishu_book_blocks (block_id, page_id, block_type, payload)
                        VALUES (:i, :p, :t, CAST(:pl AS JSONB))
                        ON CONFLICT (block_id) DO NOTHING"""),
                        {"i": blk_id, "p": pid, "t": blk.get("type"),
                         "pl": _clean(json.dumps(blk, ensure_ascii=False))})
        inputs_p = book_dir / "inputs.json"
        if inputs_p.exists():
            c.execute(text("""
                INSERT INTO sishu_book_inputs (book_id, inputs)
                VALUES (:b, CAST(:pl AS JSONB))
                ON CONFLICT (book_id) DO UPDATE SET inputs=CAST(EXCLUDED.inputs AS JSONB)"""),
                {"b": bid, "pl": _clean(inputs_p.read_text(encoding="utf-8"))})
    migrated += 1

with engine.begin() as c:
    c.execute(text("""
        INSERT INTO sishu_migration_cursor (domain, last_id, rows_done, updated_at)
        VALUES (:d, :l, :r, now())
        ON CONFLICT (domain) DO UPDATE SET last_id=EXCLUDED.last_id, rows_done=EXCLUDED.rows_done, updated_at=now()"""),
        {"d": DOMAIN, "l": f"migrated={migrated},skipped={skipped}", "r": migrated + skipped})
append_asset_hashes(DOMAIN, hashes)

with engine.connect() as c:
    n_books = c.execute(text("SELECT count(*) FROM sishu_books")).scalar()
    n_pages = c.execute(text("SELECT count(*) FROM sishu_book_pages")).scalar()
    n_blocks = c.execute(text("SELECT count(*) FROM sishu_book_blocks")).scalar()
print(f"migrated={migrated} skipped={skipped} hashes={len(hashes)} | PG books={n_books} pages={n_pages} blocks={n_blocks}")
