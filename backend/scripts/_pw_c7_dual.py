# -*- coding: utf-8 -*-
"""⑤补补-7 步骤 1：A5 主战场剧本——双闭环（对话式 source=chat + 手动 source=manual）。

chat LLM 面只断非空（计划约束「断言结构化结果，LLM 只断非空」）；落库动线为确定性断言：
SOP 步骤 4 落库动作（wrong_question_add source=chat）→错题本可见→FSRS 卡→变式可出。
manual 通道走真实表单 UI 落库→列表可见。
"""
import sys
import json
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from playwright.sync_api import sync_playwright
from sqlalchemy import text

from app.services.learning.pg import _engine

SCR = Path(__file__).parent
BASE = "http://127.0.0.1:28000"
FRONT = "http://localhost:23000"
UID = "anonymous"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


def cleanup():
    with _engine.begin() as c:
        c.execute(text("DELETE FROM learning_review_records WHERE card_id LIKE 'wq-a7%' OR card_id='c-a7-mq'"))
        c.execute(text("DELETE FROM learning_wrong_questions WHERE user_id=:u"), {"u": UID})
        c.execute(text("DELETE FROM learning_review_cards WHERE user_id=:u"), {"u": UID})
        c.execute(text("DELETE FROM learning_mother_questions WHERE knowledge_point_id=:kp"),
                  {"kp": "kp:tdd隔离知识点"})


try:
    cleanup()
    requests.patch(f"{BASE}/api/experts/tutor", json={"enabled": True}, timeout=20)
    time.sleep(6)

    # ── chat 通道（LLM 面非空断言——真实 agent 流式端点）──
    try:
        r = requests.post(f"{BASE}/api/data-intelligence/chat/freeplan/stream",
                          json={"user_input": "我今天做鸡兔同笼的题做错了，题目是：笼子里鸡兔共10只共28条腿，我答了鸡6兔4。帮我记到错题本。",
                                "expert_id": "tutor"},
                          stream=True, timeout=90)
        first_chunk = next(r.iter_lines(), b"")
        check("chat LLM 流式响应非空", bool(first_chunk) and b"Not Found" not in first_chunk,
              f"head={first_chunk[:60]!r}")
        r.close()
    except Exception as e:
        check("chat LLM 流式响应非空", False, str(e)[:80])

    # SOP 步骤 4 落库动作（确定性断言——source=chat）
    from app.services.learning.learning_dao import wrong_question_add, wrong_question_query
    wq_chat = wrong_question_add(UID, "鸡兔同笼变式：共10只共28条腿",
                                 mother_question_id="mq-seed-0001",
                                 question={"stem": "鸡兔同笼", "options": [], "correct_answer": "鸡6兔4"},
                                 my_answer="鸡6兔4", error_type="technique", source="chat")
    rows = wrong_question_query(UID)
    row = next(r for r in rows if r["wq_id"] == wq_chat)
    check("chat 通道落库 source=chat", row.get("source") == "chat")

    # FSRS 卡生成（SOP：判分错误后 fsrs_review 建卡——确定性模拟）
    requests.post(f"{BASE}/api/tutor/review-submit",
                  json={"item_id": "mq-seed-0001", "rating": 2, "kind": "mother_question"}, timeout=20)
    with _engine.begin() as c:
        n = c.execute(text("SELECT count(*) AS n FROM learning_review_cards "
                           "WHERE user_id=:u AND kind='mother_question'"), {"u": UID}).mappings().first()
    check("FSRS 卡生成（kind=mother_question）", n["n"] >= 1, f"n={n['n']}")

    # 变式可出（practice 端点面可达——agent run 判分管线转发，LLM 非空）
    pr = requests.post(f"{BASE}/api/tutor/practice",
                       json={"user_input": "出三道有理数大小比较的基础题"}, timeout=90)
    check("变式可出（practice 面 200）", pr.status_code == 200, f"status={pr.status_code}")

    # ── manual 通道（真实表单 UI——diag 验证序列：卡 enabled 下直达 chat 页渲染正常）──
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(f"{FRONT}/e/tutor/chat", timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(6000)
        # 侧栏 tutor 子菜单默认收起——点 submenu title 展开→点错题本
        pg.locator(".ant-menu-submenu-title:has-text('私塾先生')").first.click(timeout=10000)
        pg.wait_for_timeout(1500)
        pg.locator("text=错题本").first.click(timeout=8000)
        pg.wait_for_timeout(4000)
        pg.click("button:has-text('录 入'), button:has-text('录入')")
        pg.wait_for_timeout(800)
        pg.fill("textarea[placeholder='完整题面']", "有理数大小比较：-3 与 -5 谁大")
        pg.fill("input[placeholder='如：B']", "-3")
        pg.fill("input[placeholder='当时填了什么']", "-5")
        pg.fill("input[placeholder='kp:…']", "kp:tdd隔离知识点")
        pg.fill("input[placeholder='如：有理数分类']", "有理数大小比较")
        pg.click("button:has-text('落 库'), button:has-text('落库')")
        pg.wait_for_timeout(2500)
        # 状态切到全部看两条（chat+manual）——Segmented 选项非 button
        pg.locator(".ant-segmented-item:has-text('全部')").first.click()
        pg.wait_for_timeout(2500)
        body = pg.inner_text("body")
        check("manual 通道 UI 落库（列表可见 source=manual Tag）", "手动" in body)
        check("chat 通道错题本可见（source=chat Tag）", "对话" in body)
        pg.screenshot(path=str(SCR / "_pw_c7_dual.png"))
        # 错因分析卡片在页
        check("错因分析卡片同屏", "错因分析" in body)
        b.close()
finally:
    requests.patch(f"{BASE}/api/experts/tutor",
                   json={"enabled": False, "close_reason": "补-7 走查毕还原（双闭环验收）"}, timeout=20)
    cleanup()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== 补-7 双闭环验收：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
