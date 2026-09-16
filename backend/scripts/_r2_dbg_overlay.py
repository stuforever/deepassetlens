# -*- coding: utf-8 -*-
import time
from playwright.sync_api import sync_playwright

errors = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.on("console", lambda m: errors.append(f"[{m.type}] {m.text[:300]}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: errors.append(f"[pageerror] {str(e)[:400]}"))
    pg.goto("http://localhost:23000/e/wenshu/chat", timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(7000)
    ov = pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.contentDocument?.body?.innerText || ''")
    print("== overlay 内容 ==")
    print(ov[:1500] if ov else "(无 overlay)")
    print("== console errors ==")
    for e in errors[:12]:
        print(" ", e)
    b.close()
