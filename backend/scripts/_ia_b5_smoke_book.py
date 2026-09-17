# -*- coding: utf-8 -*-
"""引擎批5 L6 冒烟：book-generate create/compile_page（SSE 桥，串行）。"""
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


def stream(config):
    body = {"skill_code": "tutor/book-generate", "message": str(config.get("type") or "create"),
            "tools": [], "knowledge_bases": [], "attachments": [], "history_references": [],
            "config": config}
    r = requests.post(BASE, json=body, stream=True, timeout=900)
    events = []
    for raw in r.iter_lines(decode_unicode=True):
        if not raw or not raw.startswith("data:"):
            continue
        try:
            events.append(json.loads(raw[5:].strip()))
        except Exception:
            continue
    return events


def ws_result(evs):
    for e in evs:
        if e.get("type") == "result":
            return (e.get("metadata") or {}).get("ws_result")
    return None


def ws_events(evs):
    return [e["metadata"]["ws_event"] for e in evs
            if e.get("type") == "progress" and (e.get("metadata") or {}).get("ws_event")]


# ---- TC1 create ----
evs = stream({"type": "create", "user_intent": "一本 3 页的微积分入门小书：极限、导数、积分", "language": "zh"})
res = ws_result(evs)
check("book TC1 create_result", bool(res) and res.get("type") == "create_result", str(evs[-3:]))
book = (res or {}).get("book") or {}
proposal = (res or {}).get("proposal") or {}
book_id = book.get("id") or ""
check("book TC1 book+proposal", bool(book_id) and bool(proposal), f"book_id={book_id!r}")
check("book TC1 ws_event 流", len(ws_events(evs)) >= 1, str(len(ws_events(evs))))

# ---- TC2 confirm_proposal + confirm_spine + compile_page ----
if book_id:
    evs = stream({"type": "confirm_proposal", "book_id": book_id})
    res2 = ws_result(evs)
    spine = (res2 or {}).get("spine") or {}
    check("book TC2 confirm_proposal", bool(spine), str(evs[-3:]))
    chapters = spine.get("chapters") or spine.get("pages") or []
    evs = stream({"type": "confirm_spine", "book_id": book_id, "auto_compile": False})
    res3 = ws_result(evs)
    pages = (res3 or {}).get("pages") or []
    check("book TC2 confirm_spine pages", isinstance(pages, list) and len(pages) >= 1, str(len(pages)))
    if pages:
        pid = pages[0].get("id") or ""
        evs = stream({"type": "compile_page", "book_id": book_id, "page_id": pid})
        res4 = ws_result(evs)
        blocks = ((res4 or {}).get("page") or {}).get("blocks") or []
        check("book TC2 compile_page blocks", len(blocks) >= 1, str(len(blocks)))
    else:
        check("book TC2 compile_page blocks", False, "无页可编译")
else:
    check("book TC2 confirm_proposal", False, "无 book_id")
    check("book TC2 confirm_spine pages", False, "无 book_id")
    check("book TC2 compile_page blocks", False, "无 book_id")

print(f"\n汇总: PASS={PASS} FAIL={FAIL}")
sys.exit(1 if FAIL else 0)
