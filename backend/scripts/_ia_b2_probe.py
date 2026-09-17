# -*- coding: utf-8 -*-
"""批2 e2e 探针：h5 chat 页 textarea 可见性盘点。"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script("try { localStorage.setItem('h5_recent_users', JSON.stringify(['小明'])); } catch (e) {}")
    pg = ctx.new_page()
    pg.goto("http://localhost:23000/e/tutor-h5/chat", timeout=30000)
    pg.wait_for_timeout(5000)
    n = pg.locator("textarea").count()
    print("textarea count:", n)
    for i in range(n):
        t = pg.locator("textarea").nth(i)
        ph = t.get_attribute("placeholder") or ""
        vis = t.is_visible()
        print(f"  [{i}] visible={vis} placeholder={ph[:40]!r}")
    pg.screenshot(path="scripts/_ia_b2_probe.png")
    b.close()
