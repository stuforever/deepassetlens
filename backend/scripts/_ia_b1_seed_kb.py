# -*- coding: utf-8 -*-
"""引擎批1：L6 TC3 测试 KB（平台 knowledge center 数据面正路：create→upload→vectorize）。"""
import io
import time

import requests

BASE = "http://127.0.0.1:28000/api/v1/knowledge-bases"
NAME = "引擎批1-L6测试库"

r = requests.get(BASE, timeout=15)
rows = r.json().get("data") or []
kb_id = next((k["id"] for k in rows if k.get("name") == NAME), "")
if not kb_id:
    r = requests.post(BASE, json={"name": NAME, "description": "引擎批1 chat 全链 L6 TC3 用"}, timeout=30)
    print("create:", r.json().get("message"))
    kb_id = r.json()["data"]["id"]

doc_text = ("数据资产管理平台（tupu）是面向企业数据资产的全生命周期管理平台，"
            "覆盖元数据管理、数据源接入、知识图谱构建、指标中心与数据质量稽核。"
            "平台核心能力包括：一句话问数（wenshu）、多专家门户、知识库检索增强与技能编排。").encode("utf-8")
r = requests.post(f"{BASE}/{kb_id}/upload",
                  files={"file": ("tupu平台简介.txt", io.BytesIO(doc_text), "text/plain")}, timeout=30)
print("upload:", r.json().get("message"))

r = requests.post(f"{BASE}/{kb_id}/vectorize", timeout=180)
print("vectorize:", r.status_code, str(r.json())[:120])

for _ in range(20):
    info = requests.get(f"{BASE}/{kb_id}", timeout=15).json().get("data") or {}
    if (info.get("vector_count") or 0) > 0:
        print(f"ready: kb_id={kb_id} vector_count={info['vector_count']}")
        break
    time.sleep(3)
else:
    print("vectorize 未就绪")
    raise SystemExit(1)
