# -*- coding: utf-8 -*-
"""批6 种子：修正伙伴名（UTF-8 直写，绕 PS 控制台编码毁字）。"""
import requests

BASE = "http://127.0.0.1:28000"
NAME = "小宝助理"
DESC = "用来辅助小宝学习7年级知识的"

# 清掉旧种子（含 mojibake 版）
for p in requests.get(BASE + "/api/v1/partners", timeout=15).json():
    print("delete old:", p.get("partner_id"), repr(p.get("name"))[:30])
    requests.delete(BASE + "/api/v1/partners/" + p["partner_id"], timeout=15)

r = requests.post(BASE + "/api/v1/partners", json={"name": NAME, "description": DESC}, timeout=15)
pid = r.json().get("partner_id")
print("created:", pid)
d = requests.get(BASE + f"/api/v1/partners/{pid}", timeout=15).json()
print("name check:", repr(d.get("name")))
assert d.get("name") == NAME, "name mismatch"
print("OK")
