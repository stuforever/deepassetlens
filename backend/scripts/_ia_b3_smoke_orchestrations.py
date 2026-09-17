# -*- coding: utf-8 -*-
"""引擎批3 编排冒烟：solve/mastery/wrong-intake 三编排 + 批1 chat 回归。
直连桥端点 SSE（L6 契约断言——事件型序）。串行执行。"""
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests

BASE = "http://127.0.0.1:28000/api/v2/skills/capability"


def stream(skill, message, tools=None, session_id=None, kbs=None):
    """发一帧桥请求→返回事件列表。"""
    body = {"skill_code": skill, "message": message, "tools": tools or [],
            "knowledge_bases": kbs or [], "attachments": [],
            "history_references": [], "config": {}}
    if session_id:
        body["session_id"] = session_id
    r = requests.post(BASE, json=body, stream=True, timeout=300)
    events = []
    for raw in r.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data:"):
            continue
        try:
            events.append(json.loads(raw[5:].strip()))
        except Exception:
            continue
    return events, r.status_code


def types_of(events):
    return [e.get("type") for e in events]


def first_sess(events):
    for e in events:
        if e.get("session_id"):
            return e["session_id"]
    return None


def full_content(events):
    return "".join(e.get("content", "") for e in events if e.get("type") == "content")


PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS {name}")
    else:
        FAIL += 1
        print(f"FAIL {name} :: {detail}")


# ---- 批1 回归（chat 主链） ----
evs, code = stream("tutor/chat", "用一句话自我介绍")
t = types_of(evs)
check("chat TC1 session_meta", "session_meta" in t, str(t[:6]))
check("chat TC1 result+done", "result" in t and "done" in t, str(t[-4:]))
check("chat TC1 content 非空", len(full_content(evs)) > 5, full_content(evs)[:60])

# ---- solve TC1 单轮解题 ----
evs, code = stream("tutor/solve", "解方程 2x+3=11，给出 x")
t = types_of(evs)
check("solve TC1 session_meta", "session_meta" in t, str(t[:6]))
check("solve TC1 reason 阶段对", "stage_start" in t and "stage_end" in t, str(t))
check("solve TC1 解含 x=4", ("x = 4" in full_content(evs)) or ("x=4" in full_content(evs).replace(" ", "")), full_content(evs)[-80:])
check("solve TC1 result+done", "result" in t and "done" in t, str(t[-4:]))

# ---- solve TC3 记忆续接 ----
sid = first_sess(evs)
evs2, _ = stream("tutor/solve", "验证一下你的答案", session_id=sid)
check("solve TC3 同 session 续接", first_sess(evs2) == sid and "done" in types_of(evs2), f"{sid} vs {first_sess(evs2)}")

# ---- mastery TC1 状态查询 ----
evs, code = stream("tutor/mastery", "我现在的学情怎么样")
t = types_of(evs)
tc = [e for e in evs if e.get("type") == "tool_call"]
tr = [e for e in evs if e.get("type") == "tool_result"]
check("mastery TC1 mastery_status 合成节点", any((e.get("metadata") or {}).get("name") == "mastery_status" for e in tc), str(types_of(evs)))
check("mastery TC1 tool_result 先于 content", bool(tr) and tr[0].get("seq", 0) < (t.index("content") if "content" in t else 10**9), str(types_of(evs)))
check("mastery TC1 result+done", "result" in t and "done" in t, str(t[-4:]))

# ---- wrong-intake TC1 抽取→确认卡 ----
evs, code = stream("tutor/wrong-intake", "我错了这道题：3+5×2 我算成了 16，帮我记一下")
t = types_of(evs)
card = [e for e in evs if e.get("type") == "confirmation_card"]
check("wrong-intake TC1 confirmation_card", len(card) == 1, str(t))
if card:
    md = card[0].get("metadata") or {}
    check("wrong-intake TC1 卡含正解 13", "13" in str(md.get("correct_answer", "")), json.dumps(md, ensure_ascii=False)[:200])
    check("wrong-intake TC1 卡含误答 16", "16" in str(md.get("wrong_answer", "")), json.dumps(md, ensure_ascii=False)[:200])
sid = first_sess(evs)
check("wrong-intake TC1 done(未落库)", "done" in t and "error" not in t, str(t[-4:]))

# ---- wrong-intake TC2 确认落库 ----
evs2, _ = stream("tutor/wrong-intake", "确认", session_id=sid)
t2 = types_of(evs2)
tr2 = [e for e in evs2 if e.get("type") == "tool_result" and (e.get("metadata") or {}).get("name") == "wrong_question_save"]
check("wrong-intake TC2 save 工具事件", len(tr2) == 1, str(t2))
if tr2:
    ok = (json.loads(tr2[0].get("content") or "{}") or {}).get("ok")
    check("wrong-intake TC2 落库 ok=true", ok is True, tr2[0].get("content", "")[:120])
check("wrong-intake TC2 done ok", "done" in t2 and not any(e.get("type") == "error" for e in evs2), str(t2[-4:]))

# ---- wrong-intake TC3 信息不足追问 ----
evs3, _ = stream("tutor/wrong-intake", "帮我记一道错题")
t3 = types_of(evs3)
check("wrong-intake TC3 无确认卡", "confirmation_card" not in t3, str(t3))
check("wrong-intake TC3 done", "done" in t3, str(t3[-4:]))

print(f"\n汇总: PASS={PASS} FAIL={FAIL}")
sys.exit(1 if FAIL else 0)
