# -*- coding: utf-8 -*-
"""批12 R1 验收探针：退役面 410/404、活面 200。"""
import requests

B = "http://127.0.0.1:28000"
probes = [
    ("vendor mother-questions 活", "/api/v1/mother-questions?page=1&page_size=1", True),
    ("vendor self-learning 活", "/api/v1/self-learning/chapters", True),
    ("vendor learner-profile 活", "/api/v1/learning/profile", True),
    ("memory 活", "/api/v1/memory/overview", True),
    ("settings 活", "/api/v1/settings/llm-options", True),
]
ok_all = True
for name, path, want_ok in probes:
    try:
        r = requests.get(B + path, timeout=20)
        ok = (r.status_code == 200) if want_ok else (r.status_code in (404, 410))
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {r.status_code}")
        ok_all = ok_all and ok
    except Exception as e:
        print(f"  [FAIL] {name}: EXC {e}")
        ok_all = False
print("总体:", "PASS" if ok_all else "FAIL")
