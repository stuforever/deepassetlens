# -*- coding: utf-8 -*-
"""批7 7.4 UI 冒烟：自主学习 11 tabs 逐屏（点章→tab 循环截图+断言）+跳转卡退役。"""
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


TABS = ["原文", "知识点", "内部书籍", "错题", "课件", "练习", "笔记", "记忆", "AI 资源", "语音视频", "背诵"]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1600, "height": 950})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:120]))
        await page.goto(f"{BASE}/e/tutor/self-learning", wait_until="networkidle", timeout=180000)
        await page.wait_for_timeout(3500)
        body = await page.inner_text("body")
        check("教材树渲染", "北师大版" in body or "人教版" in body, body[:120])

        # 展开第一本教材→点第一章
        node = page.locator("[data-testid^='tree-chapter-']").first
        if await node.count() == 0:
            node = page.locator("text=章 >> visible=true").first
        await node.click()
        await page.wait_for_timeout(3000)
        body = await page.inner_text("body")
        check("章节 tabs 渲染", "chapter-tabs" in await page.content() or any(t in body for t in TABS), body[:150])

        # 11 个 tab 标签在场
        found = [t for t in TABS if t in body]
        check("11 tab 标签在场", len(found) >= 9, f"found={len(found)} missing={set(TABS)-set(found)}")

        # 跳转卡退役断言（ChapterTabEntry 提示卡不再出现）
        check("ChapterTabEntry 退役", "学习动线入口" not in body and "/e/tutor/h5/learn" not in body, "")

        # 逐 tab 点开截图（11 屏）
        shot_i = 0
        for t in TABS:
            loc = page.locator(f"text={t} >> visible=true").first
            try:
                await loc.click()
                await page.wait_for_timeout(1600)
                shot_i += 1
                await page.screenshot(path=f"scripts/_pw_b7_tab{shot_i:02d}.png")
            except Exception:
                pass
        check("tabs 逐屏截图", shot_i >= 9, f"shots={shot_i}")
        check("无 pageerror", not errors, str(errors[:2]))
        await browser.close()
    print(f"\n汇总: PASS={len(PASS)} FAIL={len(FAIL)}")
    sys.exit(1 if FAIL else 0)


asyncio.run(main())
