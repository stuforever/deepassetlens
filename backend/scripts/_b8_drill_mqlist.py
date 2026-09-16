# -*- coding: utf-8 -*-
"""mq_list 嵌套形状下钻：顶层 vs 首元素 vs 全字段键集。"""
import json
from pathlib import Path
from urllib.request import urlopen, Request

def get(base, path):
    req = Request(base + path, headers={"Accept": "application/json"})
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

j1 = get("http://127.0.0.1:28000", "/api/v1/mother-questions?page=1&page_size=3")
j2 = get("http://127.0.0.1:31007", "/api/v1/mother-questions?page=1&page_size=3")

print("顶层键 tupu:", sorted(j1.keys()))
print("顶层键 orig:", sorted(j2.keys()))
i1 = (j1.get("items") or [{}])[0]
i2 = (j2.get("items") or [{}])[0]
k1, k2 = set(i1.keys()), set(i2.keys())
print("item 键 tupu:", sorted(k1))
print("item 键 orig:", sorted(k2))
print("tupu_only:", sorted(k1 - k2))
print("orig_only:", sorted(k2 - k1))
# 逐字段类型对比（None 视作与其声明类型并存——记录双侧类型元组）
types1 = {k: type(v).__name__ for k, v in i1.items()}
types2 = {k: type(v).__name__ for k, v in i2.items()}
for k in sorted(k1 | k2):
    t1, t2 = types1.get(k, "-"), types2.get(k, "-")
    if t1 != t2:
        print(f"  类型差 {k}: tupu={t1} orig={t2}")
