# -*- coding: utf-8 -*-
"""活探 3 条 h5 疑点端点（OpenAPI 外但原仓前端在调——或为 include_in_schema=False 真路由）。"""
import json
from urllib.request import urlopen, Request

BASE = "http://127.0.0.1:28000"
ORIG = "http://127.0.0.1:31007"

def probe(base, path):
    req = Request(base + path)
    try:
        with urlopen(req, timeout=30) as r:
            body = r.read().decode()[:120]
            return r.status, body
    except Exception as e:
        code = getattr(e, "code", None)
        return code, str(e)[:80]

for path in ["/api/v1/sessions?limit=1", "/api/v1/learner-profile", "/api/v1/learning/profile"]:
    tupu = probe(BASE, path)
    orig = probe(ORIG, path)
    same = "SAME" if tupu[0] == orig[0] else "DIFF"
    print(f"{same} {path}\n   tupu={tupu[0]} {tupu[1][:70]}\n   orig={orig[0]} {orig[1][:70]}")
