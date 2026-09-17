# -*- coding: utf-8 -*-
"""批5 UI 冒烟：/e/tutor/book 书页加载（书库态）+菜单「书籍」+无 pageerror。"""
import asyncio
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from playwright.async_api import async_playwright

BASE = "http://localhost:23000"
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f" :: {detail}"))


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1600, "height": 950})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:160]))
        await page.goto(f"{BASE}/e/tutor/book", wait_until="networkidle", timeout=120000)
        await page.wait_for_timeout(3000)
        body = await page.inner_text("body")
        check("book 页壳渲染", any(k in body for k in ["书籍", "Books", "书库", "创建"]), body[:160])
        check("book 菜单项", "书籍" in body, body[:160])
        await page.screenshot(path="scripts/_pw_b5_book_library.png")
        check("无 pageerror", not errors, str(errors[:2]))
        await browser.close()
    print(f"\n汇总: PASS={len(PASS)} FAIL={len(FAIL)}")
    sys.exit(1 if FAIL else 0)


asyncio.run(main())
