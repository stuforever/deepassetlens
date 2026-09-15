# -*- coding: utf-8 -*-
"""附件四 A-3 步骤 3：后台四区 DOM 实录（四 Tab 断言+截图）。user 直打重定向断言=B-3 诚实账。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from playwright.sync_api import sync_playwright

SCR = Path(__file__).parent
BASE = "http://127.0.0.1:28000"
FRONT = "http://localhost:23000"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


try:
    requests.patch(f"{BASE}/api/experts/tutor", json={"enabled": True}, timeout=20)
    time.sleep(6)
    # 端点先验（admin 面）
    rp = requests.get(f"{BASE}/api/tutor-admin/progress", timeout=20)
    rs = requests.get(f"{BASE}/api/tutor-admin/schedule", timeout=20)
    check("progress 端点 200", rp.status_code == 200, f"status={rp.status_code}")
    check("schedule 端点 200（defaults.retention=0.9/w=19）",
          rs.status_code == 200 and rs.json()["data"]["defaults"]["desired_retention"] == 0.9
          and len(rs.json()["data"]["defaults"]["w"]) == 19)

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(f"{FRONT}/e/tutor/admin", timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(7000)
        body = pg.inner_text("body")
        check("后台页含四区卡", "后台四区" in body)
        for tab in ("题库", "学情看板", "教材", "复习调度"):
            try:
                pg.locator(f".ant-tabs-tab:has-text('{tab}')").first.click()
                pg.wait_for_timeout(2000)
                tb = pg.inner_text("body")
                check(f"区[{tab}] 渲染", tb.count(tab) >= 1)
                if tab == "学情看板":
                    check("学情看板有用户行/到期列", "复习卡" in tb and "当前到期" in tb)
                if tab == "复习调度":
                    check("调度生效值展示", "生效目标保持率" in tb and "90%" in tb)
            except Exception as e:
                check(f"区[{tab}] 渲染", False, str(e)[:60])
        pg.locator(".ant-tabs-tab:has-text('学情看板')").first.click()
        pg.wait_for_timeout(1500)
        pg.screenshot(path=str(SCR / "_pw_a3_zones.png"))
        b.close()
finally:
    requests.patch(f"{BASE}/api/experts/tutor",
                   json={"enabled": False, "close_reason": "A-3 走查毕还原（四区验收）"}, timeout=20)

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== A-3 四区验收：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
