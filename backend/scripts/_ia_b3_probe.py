# -*- coding: utf-8 -*-
"""批3 探针：dump 侧栏菜单结构。"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_context(viewport={"width": 1440, "height": 900}).new_page()
    msgs = []
    pg.on("console", lambda m: msgs.append(f"{m.type}: {m.text[:160]}"))
    pg.on("pageerror", lambda e: msgs.append(f"PAGEERROR: {str(e)[:200]}"))
    pg.goto("http://localhost:23000/", timeout=60000)
    pg.wait_for_timeout(9000)
    print("== .dal-sider 存在:", pg.locator(".dal-sider").count())
    print("== ant-menu 存在:", pg.locator(".ant-menu").count())
    print("== submenu-title 文本:")
    for t in pg.locator(".ant-menu-submenu-title").all_inner_texts()[:20]:
        print("  -", t)
    print("== console/errors:")
    for m in msgs[-12:]:
        print("  ", m)
    pg.screenshot(path="scripts/_ia_b3_probe_dump.png")
    b.close()
