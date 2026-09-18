# -*- coding: utf-8 -*-
"""v4 批0.1 存照：manifest baseline_sishu + TUTOR_TOOLS 实测 + PG learning 表清单
+ 专家行/skill_code 前置态（批1 改名对照基线）。照 IA 批1/_ia_baseline.py 模式。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from sqlalchemy import text

m = requests.get("http://127.0.0.1:28000/api/capabilities/manifest", timeout=30).json()
json.dump(m, open("scripts/_diag_assembly_baseline_sishu.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("baseline_sishu saved:", len(m), "top keys")

from app.services.query_contract import TUTOR_TOOLS  # noqa: E402
print("TUTOR_TOOLS =", len(TUTOR_TOOLS))

from app.services.learning.pg import _engine  # noqa: E402
with _engine.connect() as c:
    rows = c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1")).fetchall()
    print("PG tables:", [r[0] for r in rows])
    exp = c.execute(text("SELECT expert_id FROM expert_profiles ORDER BY 1")).fetchall() if c.execute(text(
        "SELECT to_regclass('public.expert_profiles') IS NOT NULL")).scalar() else []
    print("expert_profiles:", [r[0] for r in exp])
    acl = c.execute(text("SELECT DISTINCT resource_id FROM auth_resource_acl ORDER BY 1")).fetchall() if c.execute(text(
        "SELECT to_regclass('public.auth_resource_acl') IS NOT NULL")).scalar() else []
    print("auth_resource_acl resource_id:", [r[0] for r in acl])
