# -*- coding: utf-8 -*-
"""UX批① 复现探针：门户点问数/私塾 → 全程 URL 时序+页签数+面板态实拍。"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent))
BASE = "http://localhost:23000"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    from _pw_login_util import login_page
    pg = login_page(b)
    navs = []
    pg.on("framenavigated", lambda f: navs.append(f.url[:90]) if f == f.page.main_frame and f.url != "about:blank" else None)

    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    print("T0 URL:", pg.url[:80])
    print("T0 tabs(closable):", pg.locator(".ant-tabs-tab-remove, svg[data-icon='close']").count())
    print("T0 nav-panel visible:", pg.locator("[data-testid='nav-panel']").is_visible())

    # 点问数 Tab（已默认激活）→ composer 发送
    ta = pg.locator("[data-testid='newchat-composer'] textarea").first
    ta.fill("统计用电客户总数")
    ta.press("Enter")
    for i in range(12):
        pg.wait_for_timeout(700)
        print(f"T+{(i+1)*0.7:.1f}s URL:", pg.url[:90],
              "| tabs:", pg.locator("svg[data-icon='close']").count(),
              "| navpanel:", pg.locator("[data-testid='nav-panel']").is_visible())
        if "/e/wenshu/chat" in pg.url and i >= 5:
            break
    print("NAV-SEQ:", navs[-6:])
    print("APP-TABS-LABELS:", pg.evaluate("() => [...document.querySelectorAll('.ant-tabs-tab')].map(t => t.innerText.slice(0, 20))"))
    pg.screenshot(path=str(Path(__file__).parent / "_ux_repro.png"))
    b.close()
