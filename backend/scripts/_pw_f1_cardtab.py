# -*- coding: utf-8 -*-
"""截图「专家卡配置」tab。"""
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto("http://localhost:23000/e/tutor/admin/settings", wait_until="networkidle", timeout=60000)
    time.sleep(3)
    pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")
    pg.click('.ant-tabs-tab:has-text("专家卡配置")')
    time.sleep(2.5)
    pg.screenshot(path="scripts/dt_baseline/screens_tupu_f1/settings__expert-card.png")
    print("OK")
    b.close()
