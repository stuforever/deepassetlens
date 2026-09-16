# -*- coding: utf-8 -*-
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto("http://localhost:23000/e/wenshu/chat", timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")
    btn = pg.query_selector("button.ant-btn-primary:visible")
    print("btn found:", bool(btn))
    if btn:
        print("btn disabled:", btn.is_disabled(), "visible:", btn.is_visible())
        print("btn box:", btn.bounding_box())
        print("btn html:", (btn.evaluate("e => e.outerHTML") or "")[:220])
    pg.screenshot(path=r"scripts\dt_baseline\r2_a5_debug_chat.png")
    b.close()
