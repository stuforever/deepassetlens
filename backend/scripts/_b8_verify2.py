# -*- coding: utf-8 -*-
"""核验 lectures 精确路径 + 动态 action 派发覆盖。"""
import json
import re
from pathlib import Path

spec = json.load(open(Path(__file__).parent / "dt_baseline" / "_openapi_cache.json", encoding="utf-8"))
lect = sorted(p for p in spec["paths"] if "/lectures/" in p)
print("lectures 路径:", lect)

actions = set()
for f in Path(r"D:\gitcangku\xiaobaohaohao\DeepTutor\web").rglob("*.tsx"):
    if ".next" in str(f):
        continue
    try:
        s = f.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    if "${ep}" in s or "${action}" in s:
        for mm in re.finditer(r'"(ai_solve|attribute|explain|generate_variants|similar|note)"', s):
            actions.add(mm.group(1))
print("动态 action 取值域:", sorted(actions))
for a in sorted(actions):
    hit = any(p.endswith("/" + a) for p in spec["paths"])
    print(f"  {a}: OpenAPI {hit}")
