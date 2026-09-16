# -*- coding: utf-8 -*-
"""复现详情 404：POST 建题 → GET /{mid} → 对照原仓行为。"""
import json
from urllib.request import urlopen, Request
from urllib.error import HTTPError

BASE = "http://127.0.0.1:28000"
payload = {
    "title": "api复现404测试",
    "question_text": "已知 x^2-5x+6=0，求两根。（api 复现）",
    "subject": "math", "grade": "四年级", "category": "计算", "difficulty": 3,
    "standard_answer": "x1=2, x2=3", "wrong_answer": "x1=2, x2=-3",
    "detailed_analysis": "十字相乘 (x-2)(x-3)=0", "wrong_reason": "符号错误",
    "key_points": ["因式分解"], "tags": ["e2e"],
}

def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = Request(BASE + path, data=data, method=method,
                  headers={"Content-Type": "application/json"} if body else {})
    try:
        with urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}

st, created = call("POST", "/api/v1/mother-questions", payload)
print("POST:", st, "id=", created.get("id") if isinstance(created, dict) else created)
mid = created.get("id")
if mid:
    st2, got = call("GET", f"/api/v1/mother-questions/{mid}")
    print("GET /{mid}:", st2, "title=", got.get("title") if isinstance(got, dict) else got)
    if st2 != 200:
        print("  body:", json.dumps(got, ensure_ascii=False)[:300])
    # 对照：原仓同流程
    req = Request("http://127.0.0.1:31007" + f"/api/v1/mother-questions/{mid}")
    try:
        with urlopen(req, timeout=30) as r:
            print("原仓 GET 同 mid:", r.status)
    except HTTPError as e:
        print("原仓 GET 同 mid:", e.code, "(跨库 404 属预期——数据各自独立)")
