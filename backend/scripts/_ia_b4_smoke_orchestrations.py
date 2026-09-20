# -*- coding: utf-8 -*-
"""引擎批4 编排冒烟：quiz TC1-3 / visualize TC1 / research TC1（SSE 直连桥，串行）。"""
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import requests

BASE = "http://127.0.0.1:28000/api/v2/skills/capability"
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


def stream(skill, message, config=None, kbs=None):
    body = {"skill_code": skill, "message": message, "tools": [], "knowledge_bases": kbs or [],
            "attachments": [], "history_references": [], "config": config or {}}
    r = requests.post(BASE, json=body, stream=True, timeout=600)
    events = []
    for raw in r.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data:"):
            continue
        try:
            events.append(json.loads(raw[5:].strip()))
        except Exception:
            continue
    return events


def types_of(evs):
    return [e.get("type") for e in evs]


# ---- quiz TC1 出题 ----
evs = stream("sishu/quiz", "出两道数据资产选择题", {"question_types": ["multiple_choice"], "questionCount": 2})
t = types_of(evs)
cards = [e for e in evs if e.get("type") == "question_card"]
check("quiz TC1 题卡×2", len(cards) == 2, str(t))
check("quiz TC1 自检 pass", all((c.get("metadata") or {}).get("self_check") == "pass" for c in cards), "")
res = [e for e in evs if e.get("type") == "result"]
check("quiz TC1 result count=2", res and (res[0].get("metadata") or {}).get("count") == 2, str(t[-4:]))

# ---- quiz TC2 判题 ----
evs = stream("sishu/quiz", "判断我的作答", {
    "action": "judge", "language": "zh",
    "question": "3+5×2 等于多少？", "question_type": "fill_blank",
    "options": None, "correct_answer": "13", "explanation": "先乘后加",
    "user_answer": "16", "user_answer_images": []})
t = types_of(evs)
judge_txt = "".join(e.get("content", "") for e in evs if e.get("type") == "content")
check("quiz TC2 judge 段", "stage_start" in t and "judge" in [e.get("stage") for e in evs], str(t[:8]))
check("quiz TC2 判分语义", any(k in judge_txt for k in ["错误", "不正确", "误", "16 != 13", "正确答案", "❌", "✗"]), judge_txt[-120:])
check("quiz TC2 result(action=judge)", any(e.get("type") == "result" and (e.get("metadata") or {}).get("action") == "judge" for e in evs), str(t[-4:]))

# ---- quiz TC3 mimic 负例 ----
evs = stream("sishu/quiz", "仿制这份试卷", {"action": "mimic"})
t = types_of(evs)
check("quiz TC3 无PDF error", "error" in t and "PDF" in "".join(e.get("content", "") for e in evs if e.get("type") == "error"), str(t))

# ---- visualize TC1 svg ----
evs = stream("sishu/visualize", "画正弦函数曲线示意", {"render_mode": "svg", "quality": "standard"})
t = types_of(evs)
arts = [e for e in evs if e.get("type") == "artifact"]
svg_art = [a for a in arts if "<svg" in str((a.get("metadata") or {}).get("content", ""))]
check("visualize TC1 artifact svg", len(svg_art) == 1, f"arts={len(arts)} types={t[:6]}")
check("visualize TC1 done ok", "done" in t and not any(e.get("type") == "error" for e in evs), str(t[-4:]))

# ---- research TC1 全链 ----
evs = stream("sishu/research", "数据资产管理的研究现状", {"mode": "report", "depth": "standard"})
t = types_of(evs)
outline = [e for e in evs if e.get("type") == "outline"]
prog = [e for e in evs if e.get("type") == "progress"]
check("research TC1 outline≥2节", outline and len((outline[0].get("metadata") or {}).get("sections", [])) >= 2, str(t[:8]))
check("research TC1 progress 连续", len(prog) >= 2, f"progress={len(prog)}")
res = [e for e in evs if e.get("type") == "result"]
check("research TC1 result 报告", bool(res) and len(res[0].get("content", "")) > 100, str(t[-4:]))

print(f"\n汇总: PASS={PASS} FAIL={FAIL}")
sys.exit(1 if FAIL else 0)
