# -*- coding: utf-8 -*-
"""IA 件批1 1.0 存照：manifest baseline_ia + TUTOR_TOOLS 实测 + PG learning 表清单。
照 ⑤R 复-0 存照模式（_inv_5r.py 同款）。用途：批间 diff 断言 wenshu 零感知——
IA 各批只动 tutor/tutor-h5/前端结构，wenshu 装配 manifest 应逐字节不变。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from sqlalchemy import text

m = requests.get("http://127.0.0.1:28000/api/capabilities/manifest", timeout=30).json()
json.dump(m, open("scripts/_diag_assembly_baseline_ia.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("baseline_ia saved:", len(m), "top keys")

from app.services.query_contract import TUTOR_TOOLS  # noqa: E402
print("TUTOR_TOOLS =", len(TUTOR_TOOLS))

from app.services.learning.pg import _engine  # noqa: E402
with _engine.connect() as c:
    rows = c.execute(text("SELECT tablename FROM pg_tables WHERE tablename LIKE 'learning%'")).fetchall()
print("learning tables:", sorted(r[0] for r in rows))
