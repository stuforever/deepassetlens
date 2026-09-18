# -*- coding: utf-8 -*-
"""分步探针：/llm-config 点击 deepseek官方→应用 后页面状态全景。"""
import json
import urllib.request
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs, cons = [], []
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    pg.on("console", lambda m: cons.append(f"{m.type}:{m.text[:150]}") if m.type in ("error", "warning") else None)
    pg.goto("http://localhost:23000/llm-config", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(15000)
    LIST = '[data-testid="service-profile-list-llm"]'
    print("== 初始 LIST 文本 ==")
    print(pg.locator(LIST).inner_text().replace("\n", " | ")[:400])
    pg.locator(LIST).get_by_text("deepseek官方", exact=False).first.click()
    pg.wait_for_timeout(800)
    pg.get_by_role("button", name="应用").first.click()
    pg.wait_for_timeout(6000)
    print("== 应用后 LIST 文本 ==")
    try:
        print(pg.locator(LIST).inner_text().replace("\n", " | ")[:400])
    except Exception as e:
        print("LIST 不存在:", str(e)[:100])
    print("== 应用后 body 关键段 ==")
    body = pg.inner_text("body")
    print(body[:800].replace("\n", " | "))
    print("== pageerror ==", errs)
    print("== console err/warn ==")
    for c in cons[-10:]:
        print("  ", c)
    with urllib.request.urlopen("http://127.0.0.1:28000/api/v1/llm-connections", timeout=10) as r:
        rows = json.load(r)["data"]
    print("== DB ==")
    print([(x["name"], x["is_default"]) for x in rows])
    pg.screenshot(path="scripts/_pw_b8_probe_after_apply.png")
    b.close()
