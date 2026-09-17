# -*- coding: utf-8 -*-
"""IA批6 补拍 v2：原仓 co-writer 编辑页 + 伙伴详情页。"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:30408"
OUT = Path(__file__).resolve().parent / "dt_baseline" / "screens"


def click_doc_card(page):
    """co-writer 列表：优先点已有文档链接；无则点新建按钮建一篇再进编辑。"""
    link = page.locator("a[href^='/co-writer/']:not([href$='/new'])")
    if link.count() > 0:
        link.first.click(timeout=8000)
        return
    for text in ("新建", "新文档", "创建", "New", "Start", "开始写"):
        btn = page.get_by_text(text, exact=False).first
        if btn.count() > 0:
            btn.click(timeout=5000)
            page.wait_for_timeout(2500)
            return
    raise RuntimeError("no doc card / new button found")


def click_partner_card(page):
    """partners 列表：卡为 div onClick——按伙伴名文本点击（排除侧栏/按钮误中）。"""
    link = page.locator("a[href^='/partners/']:not([href$='/new'])")
    if link.count() > 0:
        link.first.click(timeout=8000)
        return
    name = page.locator("main, body").locator("text=小宝助理").first
    if name.count() > 0:
        name.click(timeout=8000)
        return
    card = page.locator("[class*='cursor-pointer']").first
    if card.count() > 0:
        card.click(timeout=8000)
        return
    raise RuntimeError("no partner card found")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN").new_page()

        page.goto(BASE + "/co-writer", wait_until="networkidle", timeout=40000)
        time.sleep(2)
        page.screenshot(path=str(OUT / "co-writer.png"))
        print("OK co-writer list")
        try:
            click_doc_card(page)
            page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(2.5)
            page.screenshot(path=str(OUT / "co-writer__docId.png"))
            print("OK co-writer__docId", page.url)
        except Exception as e:
            print("co-writer edit SKIP:", str(e)[:90])

        page.goto(BASE + "/partners", wait_until="networkidle", timeout=40000)
        time.sleep(2)
        page.screenshot(path=str(OUT / "partners.png"))
        print("OK partners list")
        try:
            click_partner_card(page)
            page.wait_for_load_state("networkidle", timeout=30000)
            time.sleep(2.5)
            page.screenshot(path=str(OUT / "partners__partnerId.png"))
            print("OK partners__partnerId", page.url)
        except Exception as e:
            print("partners detail SKIP:", str(e)[:90])

        browser.close()


if __name__ == "__main__":
    main()
