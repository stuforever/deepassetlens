# -*- coding: utf-8 -*-
"""mastery 空内容诊断：dump 全事件流。"""
import io, json, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests

body = {"skill_code": "tutor/mastery", "message": "我现在的学情怎么样", "tools": [],
        "knowledge_bases": [], "attachments": [], "history_references": [], "config": {}}
r = requests.post("http://127.0.0.1:28000/api/v2/skills/capability", json=body, stream=True, timeout=300)
n_think = 0
think_acc = []
for raw in r.iter_lines(decode_unicode=True):
    if not raw or not raw.startswith("data:"):
        continue
    try:
        e = json.loads(raw[5:].strip())
    except Exception:
        continue
    t = e.get("type")
    if t == "thinking":
        n_think += 1
        think_acc.append(e.get("content", ""))
        continue
    print(f"{t:16s} stage={str(e.get('stage')):8s} content={str(e.get('content'))[:100]}")
print(f"\nthinking 帧数: {n_think} 合计 {sum(len(x) for x in think_acc)} 字")
print("thinking 尾 200:", "".join(think_acc)[-200:])
