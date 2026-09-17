# -*- coding: utf-8 -*-
"""探针：S13 菜单点击设置中心后的页面态。"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    pg.goto("http://localhost:23000/", timeout=60000)
    pg.wait_for_timeout(4000)
    items = pg.evaluate(
        "() => [...document.querySelectorAll('.dal-sider .ant-menu-item')].map((e) => e.textContent.trim())"
    )
    print("menu items:", items)
    clicked = pg.evaluate(
        "() => { const els = [...document.querySelectorAll('.dal-sider .ant-menu-item')];"
        " const el = els.find((e) => e.textContent.includes('设置中心'));"
        " if (el) { el.click(); return true; } return false; }"
    )
    print("clicked:", clicked)
    pg.wait_for_timeout(6000)
    print("url:", pg.url)
    body = pg.inner_text("body")[:400]
    print("body head:", body.replace("\n", " | ")[:380])
    pg.screenshot(path="scripts/_ia_b5_menu_probe.png")
    b.close()
