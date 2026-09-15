# -*- coding: utf-8 -*-
"""⑤补补-2 步骤 4：A2 验收——欢迎语动态数实录（tutor chat 欢迎页）。"""
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


def make_due_and_streak():
    """造数据：一张到期 kp 卡+今日 record（streak=1/due≥1→欢迎语条件满足）。"""
    now = datetime.now(timezone.utc)
    with _engine.begin() as c:
        c.execute(text(
            "INSERT INTO learning_review_cards (card_id, kind, item_id, user_id, stability, "
            "difficulty, reps, lapses, due, last_review) VALUES "
            "('c-welcome-1','knowledge_point','kp:正数与负数',:uid,5.0,5.0,3,0,"
            ":due,:lr) ON CONFLICT (card_id) DO UPDATE SET due=:due, last_review=:lr, stability=5.0"),
            {"uid": UID, "due": now - timedelta(hours=2), "lr": now - timedelta(days=1)})
        c.execute(text(
            "INSERT INTO learning_review_records (card_id, user_id, rating, scheduled_interval, reviewed_at) "
            "VALUES ('c-welcome-1',:uid,3,1.0,:at)"),
            {"uid": UID, "at": now - timedelta(minutes=30)})


def cleanup():
    with _engine.begin() as c:
        c.execute(text("DELETE FROM learning_review_records WHERE card_id='c-welcome-1' OR user_id=:u"),
                  {"u": UID})
        c.execute(text("DELETE FROM learning_review_cards WHERE card_id='c-welcome-1'"))


try:
    cleanup()
    make_due_and_streak()
    requests.patch(f"{BASE}/api/experts/tutor", json={"enabled": True}, timeout=20)
    # API 直读（断言画像聚合与造数一致——必须在卡 enabled 后，_require_tutor_enabled 是守卫语义）
    pr = requests.get(f"{BASE}/api/tutor/profile", timeout=20).json().get("data") or {}
    check("profile API 聚合（streak/due）", pr.get("streak_days") == 1 and (pr.get("due_count") or 0) >= 1,
          f"streak={pr.get('streak_days')} due={pr.get('due_count')}")
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto("http://localhost:23000/e/tutor/chat", timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(6000)
        body = pg.inner_text("body")
        check("欢迎语含动态数（N 题待复习）", "题待复习" in body and "连续学习" in body)
        pg.screenshot(path=str(SCR / "_pw_c2_welcome.png"))
        b.close()
finally:
    requests.patch(f"{BASE}/api/experts/tutor",
                   json={"enabled": False, "close_reason": "补-2 走查毕还原（欢迎语验收）"}, timeout=20)
    cleanup()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== 补-2 A2 验收汇总：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
