# -*- coding: utf-8 -*-
"""⑤补补-4 步骤 3：A4 验收——三色状态断言（造三态数据各一：灰未学/蓝学习中/绿已精通）。"""
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from playwright.sync_api import sync_playwright
from sqlalchemy import text

from scripts import seed_tutor_curriculum as seed
from app.services.learning.pg import _engine

SCR = Path(__file__).parent
BASE = "http://127.0.0.1:28000"
UID = "anonymous"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


def make_three_states():
    """三态数据：kp:正数与负数=高 retention 绿；kp:有理数=低 stability 久未复习蓝；无卡 kp=灰。"""
    now = datetime.now(timezone.utc)
    with _engine.begin() as c:
        c.execute(text(
            "INSERT INTO learning_review_cards (card_id, kind, item_id, user_id, stability, "
            "difficulty, reps, lapses, due, last_review) VALUES "
            "('c-path-g','knowledge_point','kp:正数与负数',:uid,80.0,4.0,6,0,:due,:lr) "
            "ON CONFLICT (card_id) DO UPDATE SET stability=80.0, last_review=:lr"),
            {"uid": UID, "due": now + timedelta(days=30), "lr": now - timedelta(days=1)})
        c.execute(text(
            "INSERT INTO learning_review_cards (card_id, kind, item_id, user_id, stability, "
            "difficulty, reps, lapses, due, last_review) VALUES "
            "('c-path-b','knowledge_point','kp:有理数',:uid,2.0,6.0,2,1,:due,:lr) "
            "ON CONFLICT (card_id) DO UPDATE SET stability=2.0, last_review=:lr"),
            {"uid": UID, "due": now - timedelta(hours=1), "lr": now - timedelta(days=8)})


def cleanup():
    with _engine.begin() as c:
        c.execute(text("DELETE FROM learning_review_records WHERE card_id LIKE 'c-path-%'"))
        c.execute(text("DELETE FROM learning_review_cards WHERE card_id LIKE 'c-path-%'"))


try:
    seed.main()                                       # 种子可重放（并行清库自愈）
    cleanup()
    make_three_states()
    requests.patch(f"{BASE}/api/experts/tutor", json={"enabled": True}, timeout=20)
    time.sleep(6)                                     # 卡缓存失效窗口
    # API 层三色断言
    d = requests.get(f"{BASE}/api/tutor/path", timeout=20).json().get("data") or {}
    colors = {}
    for m in d.get("modules") or []:
        for kp in m.get("kps") or []:
            colors[kp["code"]] = kp["color"]
    check("绿已精通（高 retention≥0.7）", colors.get("kp:正数与负数") == "green",
          f"got={colors.get('kp:正数与负数')}")
    check("蓝学习中（低 retention<0.7）", colors.get("kp:有理数") == "blue",
          f"got={colors.get('kp:有理数')}")
    check("灰未学（无卡）", "无卡 kp" not in " ".join(colors.keys()) and len(colors) >= 2,
          f"cards={colors}")

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto("http://localhost:23000/e/tutor/path", timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(6000)
        body = pg.inner_text("body")
        check("路线图渲染（模块卡+色阶图例）", "已精通" in body and "学习中" in body and "未学" in body)
        pg.screenshot(path=str(SCR / "_pw_c4_path.png"))
        b.close()
finally:
    requests.patch(f"{BASE}/api/experts/tutor",
                   json={"enabled": False, "close_reason": "补-4 走查毕还原（精通之路验收）"}, timeout=20)
    cleanup()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== 补-4 A4 验收汇总：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
