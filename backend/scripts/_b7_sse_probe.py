# -*- coding: utf-8 -*-
"""⑤R E1 7.3 动线调试：直打 freeplan SSE 端点，看 tutor chat 的帧实况。"""
import json
import requests

BASE = "http://127.0.0.1:28000/api/data-intelligence/chat/freeplan/stream"
payload = {
    "user_input": "请判分：一元二次方程 x^2-5x+6=0，我的答案是 x=2 和 x=-3，对吗？请调用判分工具给出正式分数，错了就把这道错题录入错题本",
    "expert_id": "tutor",
    "thread_id": "b7probe9",
    "llm_connection_id": "",
}
frames = []
with requests.post(BASE, json=payload, stream=True, timeout=600) as r:
    print("status:", r.status_code)
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("event:"):
            cur_event = line[6:].strip()
            continue
        if line.startswith("data:"):
            try:
                d = json.loads(line[5:].strip())
            except Exception:
                continue
            frames.append((cur_event, d))
            if cur_event == "done":
                break

from collections import Counter
cnt = Counter()
ans = []
for ev, d in frames:
    cnt[ev] += 1
    if ev == "think_token" and d.get("kind") in ("answer_draft", "answer_committed"):
        ans.append(d.get("delta", ""))
    if ev == "policy":
        print("policy:", json.dumps(d, ensure_ascii=False)[:200])
    if ev == "tool_started":
        print("tool_started:", json.dumps(d, ensure_ascii=False)[:200])
print("帧型分布:", dict(cnt))
print("answer 全文:", "".join(ans)[:800])
for ev, d in frames:
    if ev == "done":
        print("done.final_answer:", (d.get("final_answer") or "")[:600])
print("frames:", len(frames))
