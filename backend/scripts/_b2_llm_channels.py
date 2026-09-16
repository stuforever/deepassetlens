# -*- coding: utf-8 -*-
"""⑤R B2 e2e 渠道盘点：列出平台 LLM 连接与默认（用户指令：切平台默认渠道重跑 e2e）。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import create_engine, text  # noqa: E402

url = None
for line in open(Path(__file__).resolve().parents[1] / ".env", encoding="utf-8"):
    if line.startswith("DATABASE_URL="):
        url = line.split("=", 1)[1].strip()
eng = create_engine(url)
with eng.connect() as c:
    tabs = c.execute(text(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='tupu' AND (table_name LIKE '%llm%' OR table_name LIKE '%connection%')"
    )).fetchall()
    print("tables:", [r[0] for r in tabs])
    for t in tabs:
        if "llm" in t[0] or "connection" in t[0]:
            try:
                rows = c.execute(text(f"SELECT * FROM {t[0]} LIMIT 8")).mappings().fetchall()
                for r in rows:
                    d = dict(r)
                    for k in list(d):
                        if "key" in k.lower() and d[k]:
                            d[k] = str(d[k])[:6] + "..."
                    print(t[0], "->", d)
            except Exception as e:
                print(t[0], "err:", str(e)[:120])
