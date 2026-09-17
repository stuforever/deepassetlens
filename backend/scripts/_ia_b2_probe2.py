# -*- coding: utf-8 -*-
"""批2 探针2：h5 chat 发送链路诊断（网络+console+screenshot）。"""
import time

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script("try { localStorage.setItem('h5_recent_users', JSON.stringify(['小明'])); } catch (e) {}")
    pg = ctx.new_page()
    reqs = []
    pg.on("response", lambda r: reqs.append((r.status, r.url[:110])) if "/api/" in r.url else None)
    errs = []
    pg.on("console", lambda m: errs.append(m.text[:160]) if m.type == "error" else None)
    pg.goto("http://localhost:23000/e/tutor-h5/chat", timeout=30000)
    pg.wait_for_timeout(5000)
    tb = pg.locator("textarea:visible").first
    tb.fill("帮我出两道圆柱体积的练习题 IAprobe")
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(10000)
    print("== /api responses (last 12) ==")
    for s, u in reqs[-12:]:
        print(" ", s, u)
    print("== console errors (last 6) ==")
    for e in errs[-6:]:
        print(" ", e)
    pg.screenshot(path="scripts/_ia_b2_probe2.png")
    b.close()
