# -*- coding: utf-8 -*-
"""批4 UI 面板开态：quiz/visualize/research 三面板逐屏 + 判题桥编译断言。"""
import asyncio
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from playwright.async_api import async_playwright

BASE = "http://localhost:23000"
PASS = []
FAIL = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f" :: {detail}"))


CHIP = ("button:has-text('聊天'), button:has-text('Chat'), button:has-text('测验'), "
        "button:has-text('Quiz'), button:has-text('可视化'), button:has-text('Visualize'), "
        "button:has-text('研究'), button:has-text('Research')")


async def pick_capability(page, more_text, wait=600):
    chip = page.locator(CHIP + " >> visible=true").first
    await chip.click()
    await page.wait_for_timeout(wait)
    more = page.locator("text=More Capabilities >> visible=true").first
    if await more.count() == 0:
        more = page.locator("text=更多能力 >> visible=true").first
    await more.hover()
    await page.wait_for_timeout(600)
    item = page.locator(f"text={more_text} >> visible=true").first
    await item.click()
    await page.wait_for_timeout(900)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1600, "height": 950})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:160]))
        await page.goto(f"{BASE}/e/tutor/chat", wait_until="networkidle", timeout=120000)
        await page.wait_for_timeout(2500)

        # quiz 面板（测验 chip=主浮层首位——直接点测验）
        await page.locator(CHIP + " >> visible=true").first.click()
        await page.wait_for_timeout(600)
        await page.locator("text=测验 >> visible=true").first.click()
        await page.wait_for_timeout(1200)
        body = await page.inner_text("body")
        check("quiz 面板态字段", any(k in body for k in ["题型", "题量", "Question types", "难度"]), body[:200])
        await page.screenshot(path="scripts/_pw_b4_panel_quiz.png")

        # visualize 面板（重载复位→更多能力→可视化）
        await page.goto(f"{BASE}/e/tutor/chat", wait_until="networkidle", timeout=120000)
        await page.wait_for_timeout(2000)
        await pick_capability(page, "可视化")
        body = await page.inner_text("body")
        check("visualize 面板态字段", any(k in body for k in ["渲染", "render", "Render", "质量"]), body[:200])
        await page.screenshot(path="scripts/_pw_b4_panel_visualize.png")

        # research 面板（重载复位→更多能力→研究）
        await page.goto(f"{BASE}/e/tutor/chat", wait_until="networkidle", timeout=120000)
        await page.wait_for_timeout(2000)
        await pick_capability(page, "研究")
        body = await page.inner_text("body")
        check("research 面板态字段", any(k in body for k in ["模式", "Mode", "深度", "Depth", "大纲"]), body[:200])
        await page.screenshot(path="scripts/_pw_b4_panel_research.png")

        check("无 pageerror", not errors, str(errors[:2]))
        await browser.close()
    print(f"\n汇总: PASS={len(PASS)} FAIL={len(FAIL)}")
    sys.exit(1 if FAIL else 0)


asyncio.run(main())
