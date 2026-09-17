# -*- coding: utf-8 -*-
"""⑤R 后补对拍 v2：notebook/question-notebook/self-learning 真实路径活体探针（GET 面）。"""
import io
import json
from pathlib import Path

import requests

ORIG = "http://localhost:31007"
TUPU = "http://localhost:28000"
BASE = Path(__file__).resolve().parent / "dt_baseline"

ENDPOINTS = [
    "/api/v1/notebook/health",
    "/api/v1/notebook/list",
    "/api/v1/notebook/statistics",
    "/api/v1/question-notebook/categories",
    "/api/v1/question-notebook/entries",
    "/api/v1/self-learning/recite/materials",
    "/api/v1/learning/learner-profile",
]


def shape(x):
    if isinstance(x, dict):
        return {k: shape(v) for k, v in sorted(x.items())}
    if isinstance(x, list):
        return [shape(x[0])] if x else []
    return type(x).__name__


def probe(base, ep):
    try:
        r = requests.get(base + ep, timeout=15)
        try:
            body = r.json()
            return {"status": r.status_code, "shape": shape(body)}
        except Exception:
            return {"status": r.status_code, "shape": None}
    except Exception as e:
        return {"status": 0, "err": str(e)[:60]}


def main():
    out = []
    for ep in ENDPOINTS:
        o, t = probe(ORIG, ep), probe(TUPU, ep)
        same = o.get("status") == t.get("status") and o.get("shape") == t.get("shape")
        out.append({"ep": ep, "orig": o, "tupu": t, "match": same})
        print(f"{'MATCH ' if same else 'DIFF  '} {ep}: orig={o.get('status')} tupu={t.get('status')}")
        if not same:
            print(f"    orig shape={json.dumps(o.get('shape'), ensure_ascii=False)[:160]}")
            print(f"    tupu shape={json.dumps(t.get('shape'), ensure_ascii=False)[:160]}")
    json.dump(out, io.open(BASE / "r3_selflearn_api_compare.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n = sum(1 for x in out if x["match"])
    print(f"\n真实路径对比: {n}/{len(out)} MATCH")


if __name__ == "__main__":
    main()
