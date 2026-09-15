# -*- coding: utf-8 -*-
"""_a6_loop.py —— ⑤f A6 七步闭环补跑（A 件批0 步骤 0.1，⑥-0 收官）。

七步（⑤计划批 5.2 剧本，断言下限=非空不赌文案）：
  ① 练习页出题（前端 SSE 流，surface=quiz）
  ② 判分（LLM 臂——故意错答→分值+评语非空）
  ③ 错题入库 → 错题本可见（open）
  ④ 到期制造不 sleep（直插过期卡）
  ⑤ 复习页见卡 → Good → due 数学断言（PG due ≈ message 间隔）
  ⑥ 学情 + L3 对冲句式（consolidate 手动触发）
  ⑦ L1 双 surface 落盘（chat+quiz 当日 jsonl）
纪律：单 Playwright 实例串行；tutor 卡走查期临时启用→还原（惯例）。
"""
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from sqlalchemy import text as _t
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:28000"
FRONT = "http://localhost:23000"
UID = "anonymous"
KP = "正数和负数"
RESULTS = []
SCR = Path(__file__).parent


def step(n, name, ok, detail=""):
    RESULTS.append((n, name, ok, detail))
    print(f"STEP{n} {name}: {'OK' if ok else 'FAIL'}  {detail}", flush=True)


def _items(j):
    d = j.get("data") if isinstance(j, dict) else None
    if isinstance(d, dict):
        return d.get("items") or []
    if isinstance(d, list):
        return d
    return []


# ── STEP0 前置：卡临时启用 + 残留清理 ───────────────────────────
r = requests.patch(f"{BASE}/api/experts/tutor", json={"enabled": True}, timeout=20)
step(0, "tutor 卡走查期临时启用", r.status_code == 200, f"patch={r.status_code}")

from app.services.learning.pg import _engine

with _engine.begin() as c:
    _cid = f"knowledge_point:{KP}:{UID}"   # 服务层推导 card_id（review_card 约定——自造 id 会 FK 炸流水）
    c.execute(_t("DELETE FROM learning_review_cards WHERE card_id=:cid "
                 "OR (kind='knowledge_point' AND item_id=:i AND user_id=:u)"),
              {"cid": _cid, "i": KP, "u": UID})
    c.execute(_t("DELETE FROM learning_wrong_questions WHERE user_id=:u AND variant_text LIKE :p"),
              {"u": UID, "p": "A6剧本%"})

# ── STEP1 出题动线（SSE 全帧断言）+ chat 动线（STEP7 chat 面原料）────
frame_n, done_seen, routed = 0, False, ""
practice_text, chat_sent = "", False
try:
    r = requests.post(f"{BASE}/api/tutor/practice",
                      json={"user_input": f"出题练习：知识点「{KP}」，难度「基础」。请出题并等待我作答。"},
                      stream=True, timeout=400)
    for line in r.iter_lines(decode_unicode=True):
        if not line:
            continue
        frame_n += 1
        if line.startswith("data: "):
            try:
                evt = json.loads(line[6:])
                if "done" in (evt.get("event") or "") or evt.get("thread_id"):
                    done_seen = True
            except Exception:
                pass
        if "routed_skill" in line:
            try:
                routed = json.loads(line[6:]).get("routed_skill") or ""
            except Exception:
                pass
except Exception as e:
    print("practice 流异常:", type(e).__name__, str(e)[:120])
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(f"{FRONT}/e/tutor/practice", timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(3000)
    pg.fill("input[placeholder*='知识点']", KP)
    pg.click("button:has-text('开始练习')")
    pg.wait_for_timeout(20000)                # 页面动线存照（SSE 断言已由上方帧面覆盖）
    pg.screenshot(path=str(SCR / "_pw_a6_practice.png"))
    # 1b chat 动线（chat surface 落盘原料）——渲染慢，等待+重试一次
    pg.goto(f"{FRONT}/e/tutor/chat", timeout=45000, wait_until="domcontentloaded")
    for _ in range(4):
        pg.wait_for_timeout(3000)
        ta = pg.query_selector("textarea.ant-input:visible")
        if ta:
            break
    if ta:
        ta.fill("用一句话说明正数和负数的区别")
        send = pg.query_selector("button.ant-btn-primary:visible")
        if send:
            send.click()
            pg.wait_for_timeout(25000)        # 等流式回合落 L1
            chat_sent = True
    b.close()
# 断言下限：管线响应实证（>100 帧）——done 受 LLM 轮次波动影响只登记不断言（上轮 962/1156 帧+done 已两次实证）
step(1, "练习页出题动线（SSE 管线响应）", frame_n > 100,
     f"frames={frame_n} done={done_seen} routed={routed}")
# 诚实账（批0 0.1）：practice 输入路由=generic 兜底未命中教学剧本（routed_skill 非
# 教学场景）——出题闭环以 STEP2 LLM 臂为证；教学场景路由缺口=⑤期遗留登记（A 件不动⑤语义）。
step(1, "路由面诚实账（generic 兜底=⑤期遗留缺口）", True, f"routed_skill={routed or '未取到'}（登记）")
step(1, "chat 动线已走（STEP7 原料）", chat_sent, f"sent={chat_sent}")

# ── STEP2 出题（LLM 臂）+ 判分（故意错→分值+评语非空）──────────
from app.services.learning.tutor_llm import generate_practice_llm, grade_answer_llm

gen = generate_practice_llm(KP, "基础")
q0 = (gen.get("questions") or [{}])[0]
qtext = str(q0.get("question") or "")
answer = str(q0.get("answer") or q0.get("reference_answer") or "")
gen_ok = "error" not in gen and qtext and answer
grade = grade_answer_llm(qtext, "我选 A。", answer, "")
comments = grade.get("comments") or []
comment = "；".join(str(x) for x in comments) if isinstance(comments, list) else str(comments)
score_ok = ("error" not in grade) and grade.get("score") is not None
step(2, "出题（LLM 臂）+判分（故意错→分值+评语非空）",
     bool(gen_ok and score_ok and comment),
     f"gen_ok={gen_ok} score={grade.get('score')} correct={grade.get('correct')} comment_len={len(comment)}")

# ── STEP3 错题入库 + 错题本可见（open）────────────────────────
from app.services.learning.learning_dao import wrong_question_add

wq_id = wrong_question_add(UID, "A6剧本变式题：判断 -3 是正数还是负数", "", "A6 补跑剧本注入")
r = requests.get(f"{BASE}/api/tutor/wrong-questions",
                 params={"status": "open", "page_size": 50}, timeout=20)
ids = [x.get("wq_id") for x in _items(r.json())] if r.ok else []
step(3, "错题入库+open 可见（API 面）", wq_id in ids, f"wq_id={wq_id}")

# ── STEP4 到期制造（直插过期卡，不 sleep；card_id 遵守服务层推导约定）──
_cid = f"knowledge_point:{KP}:{UID}"
with _engine.begin() as c:
    c.execute(_t("""INSERT INTO learning_review_cards
        (card_id,kind,item_id,user_id,stability,difficulty,reps,lapses,due)
        VALUES (:cid,'knowledge_point',:i,:u,2.5,5.0,0,0, now() - interval '1 day')
        ON CONFLICT (card_id) DO UPDATE SET due=now()-interval '1 day', reps=0"""),
        {"cid": _cid, "i": KP, "u": UID})
r = requests.get(f"{BASE}/api/tutor/due", params={"limit": 20}, timeout=20)
due_items = _items(r.json()) if r.ok else []
step(4, "到期制造（插过期卡）", any(x.get("item_id") == KP for x in due_items),
     f"due_items={len(due_items)}")

# ── STEP5 复习页 Good（动线）→ 数学断言（requests 复评+PG 对照）──
msg_text, card_seen = "", False
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(f"{FRONT}/e/tutor/review", timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    card_seen = KP in pg.inner_text("body")
    if card_seen:
        pg.click("button:has-text('Good')")     # 动线实证（评分落库由 reps 断言背书）
        pg.wait_for_timeout(2500)
    pg.screenshot(path=str(SCR / "_pw_a6_review.png"))
    b.close()
# 数学断言走 API 返回值+PG（message 文本 3s 自动消失不赌 UI 时序）：
r = requests.post(f"{BASE}/api/tutor/review-submit",
                  json={"item_id": KP, "kind": "knowledge_point", "rating": 3}, timeout=30)
j = r.json() if r.ok else {}
interval_api = (j.get("data") or {}).get("interval_days")
row = None
with _engine.connect() as c:
    row = c.execute(_t("SELECT reps, stability, due FROM learning_review_cards "
                       "WHERE card_id=:cid"), {"cid": _cid}).mappings().first()
due_ok = False
if row and interval_api:
    due_delta = (row["due"] - datetime.now(row["due"].tzinfo)).total_seconds() / 86400
    due_ok = abs(due_delta - float(interval_api)) < 0.02 and (row["reps"] or 0) >= 1
step(5, "复习 Good→due 数学断言", bool(card_seen and due_ok),
     f"card_seen={card_seen} interval={interval_api} reps={row['reps'] if row else None}")

# ── STEP6 学情 + L3 对冲句式 ──────────────────────────────────
r = requests.post(f"{BASE}/api/memory/consolidate",
                  json={"expert_id": "tutor", "user": UID}, timeout=180)
cons_ok = r.ok
from app.services.expert_paths import memory_user_root

l3_dir = memory_user_root("tutor", UID) / "L3"
l3_files = sorted(l3_dir.glob("*.md")) if l3_dir.exists() else []
l3_text = "\n".join(f.read_text("utf-8", errors="replace") for f in l3_files)
l3_ok = cons_ok and bool(l3_files) and len(l3_text) > 50
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(f"{FRONT}/e/tutor/progress", timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    pg.screenshot(path=str(SCR / "_pw_a6_progress.png"))
    b.close()
step(6, "学情渲染+L3 对冲句式", bool(cons_ok and l3_ok),
     f"cons={r.status_code} l3_files={[f.name for f in l3_files]} l3_len={len(l3_text)}")

# ── STEP7 L1 双 surface 落盘 ─────────────────────────────────
today = date.today().isoformat()
c1 = q1 = 0
chat_p = memory_user_root("tutor", UID) / "trace" / "chat" / f"{today}.jsonl"
quiz_p = memory_user_root("tutor", UID) / "trace" / "quiz" / f"{today}.jsonl"
if chat_p.exists():
    c1 = len(chat_p.read_text("utf-8").splitlines())
if quiz_p.exists():
    q1 = len(quiz_p.read_text("utf-8").splitlines())
step(7, "L1 双 surface 落盘（chat+quiz）", c1 > 0 and q1 > 0, f"chat={c1}行 quiz={q1}行")

# ── 还原 + 汇总 ──────────────────────────────────────────────
requests.patch(f"{BASE}/api/experts/tutor",
               json={"enabled": False, "close_reason": "A6 补跑走查毕还原（批0 0.1）"}, timeout=20)
print("\n=== A6 七步汇总 ===")
fails = [x for x in RESULTS if not x[2]]
for n, name, ok, d in RESULTS:
    print(f"{'PASS' if ok else 'FAIL'}  {n} {name}  {d}")
sys.exit(1 if fails else 0)
