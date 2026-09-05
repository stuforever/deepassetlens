# -*- coding: utf-8 -*-
"""四题 e2e 取数凭证核对（临时）：kg_engine_query_logs 最近 8 条。"""
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from app.core.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    rows = db.execute(text(
        "SELECT * FROM kg_engine_query_logs ORDER BY id DESC LIMIT 8")).mappings().fetchall()
    for r in rows:
        d = dict(r)
        keep = {k: d.get(k) for k in d if any(s in k for s in ("id", "tool", "engine", "rows", "duration", "created", "sql", "run_id"))}
        print({k: (str(v)[:60] if isinstance(v, str) and len(str(v)) > 60 else v) for k, v in keep.items()})
finally:
    db.close()
