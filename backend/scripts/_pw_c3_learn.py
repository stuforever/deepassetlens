# -*- coding: utf-8 -*-
"""⑤补补-3 步骤 4：A3 验收——章节浏览→精讲→今日任务→去练习动线（串行+截图）。"""
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from playwright.sync_api import sync_playwright
from sqlalchemy import text

from app.services.learning.pg import _engine

SCR = Path(__file__).parent
BASE = "http://127.0.0.1:28000"
UID = "anonymous"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


def make_weak_data():
    """造薄弱数据：一张久未复习低稳定 kp 卡→今日任务=due 1 条+weak 出题 1 条。"""
    now = datetime.now(timezone.utc)
    with _engine.begin() as c:
        c.execute(text(
            "INSERT INTO learning_review_cards (card_id, kind, item_id, user_id, stability, "
            "difficulty, reps, lapses, due, last_review) VALUES "
            "('c-learn-1','knowledge_point','kp:有理数',:uid,2.0,6.0,2,1,"
            ":due,:lr) ON CONFLICT (card_id) DO UPDATE SET due=:due, last_review=:lr, stability=2.0"),
            {"uid": UID, "due": now - timedelta(hours=1), "lr": now - timedelta(days=8)})


def cleanup():
    with _engine.begin() as c:
        c.execute(text("DELETE FROM learning_review_records WHERE card_id='c-learn-1'"))
        c.execute(text("DELETE FROM learning_review_cards WHERE card_id='c-learn-1'"))


try:
    requests.patch(f"{BASE}/api/experts/tutor", json={"enabled": True}, timeout=20)
    time.sleep(6)                                     # 卡缓存失效窗口
    make_weak_data()
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto("http://localhost:23000/e/tutor/learn", timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(6000)
        body = pg.inner_text("body")
        # ① 章节浏览（图谱树→1.1 章在列）
        check("章节浏览（1.1_正数和负数在列）", "1.1_正数和负数" in body)
        # ② 知识点精讲（点击 kp 行展开）
        kp_loc = pg.locator("text=有理数").first
        if kp_loc.count() > 0 or pg.query_selector("text=有理数"):
            kp_loc.click()
            pg.wait_for_timeout(1200)
            body2 = pg.inner_text("body")
            check("知识点精讲展开（explanation 属性可读）", "整数与分数统称有理数" in body2)
        else:
            check("知识点精讲展开（explanation 属性可读）", False, "kp 行未找到")
        # ③ 今日任务（due 到期 1 条）
        check("今日任务（到期复习项在列）", "到期复习" in body or "到期复习" in pg.inner_text("body"))
        pg.screenshot(path=str(SCR / "_pw_c3_learn.png"))
        # ④ 去练习动线（练习页「开始练习」按钮+知识点输入框 placeholder 在）
        go = pg.query_selector("button:has-text('去练习')")
        if go:
            go.click()
            pg.wait_for_timeout(3000)
            check("去练习动线（练习页可达）",
                  pg.query_selector("button:has-text('开始练习')") is not None
                  and pg.query_selector("input[placeholder*='知识点']") is not None)
            pg.screenshot(path=str(SCR / "_pw_c3_practice_nav.png"))
        else:
            check("去练习动线（练习页可达）", False, "按钮未找到")
        b.close()
finally:
    requests.patch(f"{BASE}/api/experts/tutor",
                   json={"enabled": False, "close_reason": "补-3 走查毕还原（自主学习页验收）"}, timeout=20)
    cleanup()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== 补-3 A3 验收汇总：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
