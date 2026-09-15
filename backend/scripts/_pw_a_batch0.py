# -*- coding: utf-8 -*-
"""A 批0 步骤 0.3：门户+侧栏专家区暗路由现状存照。"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

SCR = Path(__file__).parent
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto("http://localhost:23000/", timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    pg.screenshot(path=str(SCR / "_pw_a_batch0_portal.png"))
    body = pg.inner_text("body")
    print("门户含专家区?", ("专家" in body), "| 含 wenshu 卡?", ("wenshu" in body.lower()), "| 含 tutor 卡?", ("tutor" in body.lower()))
    pg.goto("http://localhost:23000/e/tutor", timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    pg.screenshot(path=str(SCR / "_pw_a_batch0_tutor_dark.png"))
    b.close()
print("存照: _pw_a_batch0_portal.png / _pw_a_batch0_tutor_dark.png")
