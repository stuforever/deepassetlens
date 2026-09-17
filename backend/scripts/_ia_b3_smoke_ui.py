# -*- coding: utf-8 -*-
"""引擎批3 全链冒烟（Playwright 真实前端，串行）：
TC1 工具页 4 件置灰「未接入」；TC2 solve 能力解题；TC3 wrong-intake 抽取→确认卡→确认落库；
TC4 导出 Markdown 下载；TC5 活动面板开合。截图落 scripts/_pw_b3_*.png。"""
import asyncio
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from playwright.async_api import async_playwright

BASE = "http://localhost:23000"
PASS = []
FAIL = []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(f"{name} :: {detail}" if not cond else name)
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f" :: {detail}"))


async def wait_done(page, timeout_ms=240000):
    """等完成锚：已完成出现且推理中消失（批2 语义——只等消失会在工具阶段误判）。"""
    await page.wait_for_function(
        "() => document.body.innerText.includes('已完成') && !document.body.innerText.includes('推理中')",
        timeout=timeout_ms, polling=1500)
    await page.wait_for_timeout(2000)


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1600, "height": 950})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:160]))

        # ---- TC1 工具页 4 件置灰「未接入」 ----
        await page.goto(f"{BASE}/settings/tools", wait_until="networkidle", timeout=90000)
        await page.wait_for_timeout(2500)
        for tool in ["geogebra_analysis", "paper_search", "imagegen", "videogen"]:
            row = page.locator(f"[data-testid=tools-tool-{tool}]")
            check(f"TC1 {tool} 行在场", await row.count() == 1)
            badge = row.locator("text=未接入").first
            check(f"TC1 {tool} 未接入徽标", await badge.count() >= 1)
        # web_search 可开关不置灰
        ws = page.locator("[data-testid=tools-toggle-web_search]")
        check("TC1 web_search 开关在场且可点", await ws.count() == 1 and await ws.is_disabled() is False)
        await page.screenshot(path="scripts/_pw_b3_tools.png")

        # ---- TC2 solve 解题 ----
        await page.goto(f"{BASE}/e/tutor/chat", wait_until="networkidle", timeout=90000)
        await page.wait_for_timeout(2000)
        # 能力浮层 → 更多能力（嵌套浮层）→ 深度解题
        await page.locator("button:has-text('聊天')").first.click()
        await page.wait_for_timeout(600)
        more = page.locator("text=More Capabilities >> visible=true").first
        if await more.count() == 0:
            more = page.locator("text=更多能力 >> visible=true").first
        await more.hover()
        await page.wait_for_timeout(700)
        solve_item = page.locator("text=多步推理与问题求解 >> visible=true").first
        if await solve_item.count() == 0:
            solve_item = page.locator("text=Multi-step reasoning >> visible=true").first
        await solve_item.click()
        await page.wait_for_timeout(800)
        ta = page.locator("textarea:visible").first
        await ta.fill("解方程 2x+3=11，给出 x")
        await ta.press("Enter")
        await page.wait_for_timeout(4000)
        await wait_done(page)
        body = await page.inner_text("body")
        check("TC2 solve 答含 x=4", ("x = 4" in body) or ("x=4" in body.replace(" ", "")), body[-120:])
        await page.screenshot(path="scripts/_pw_b3_solve.png")

        # ---- TC3 wrong-intake 抽取→确认卡→确认落库 ----
        await page.goto(f"{BASE}/e/tutor/chat", wait_until="networkidle", timeout=90000)
        await page.wait_for_timeout(2000)
        # 激活 chip 跟随当前能力（重载后默认=聊天）
        cap_chip = page.locator("button:has-text('聊天') >> visible=true").first
        if await cap_chip.count() == 0:
            cap_chip = page.locator("button:has-text('Chat') >> visible=true").first
        await cap_chip.click()
        await page.wait_for_timeout(600)
        more = page.locator("text=More Capabilities >> visible=true").first
        if await more.count() == 0:
            more = page.locator("text=更多能力 >> visible=true").first
        await more.hover()
        await page.wait_for_timeout(700)
        wi_item = page.locator("text=错题 >> visible=true").first
        if await wi_item.count() == 0:
            wi_item = page.locator("text=Wrong >> visible=true").first
        await wi_item.click()
        await page.wait_for_timeout(800)
        ta = page.locator("textarea:visible").first
        await ta.fill("我错了这道题：3+5×2 我算成了 16，帮我记一下")
        await ta.press("Enter")
        # 等确认卡（超时诊断：截屏+正文尾部）
        card = page.locator("[data-testid=wrong-intake-confirmation]")
        try:
            await card.wait_for(state="visible", timeout=240000)
        except Exception:
            await page.screenshot(path="scripts/_pw_b3_card_timeout.png")
            b = await page.inner_text("body")
            print("CARD-TIMEOUT body尾400:", b[-400:].replace("\n", " | "))
            raise
        check("TC3 确认卡在场", await card.count() == 1)
        card_text = await card.inner_text()
        check("TC3 卡含正解 13", "13" in card_text, card_text[:160])
        check("TC3 卡含误答 16", "16" in card_text, card_text[:160])
        await page.screenshot(path="scripts/_pw_b3_card.png")
        await page.locator("[data-testid=wrong-intake-confirm-btn]").click()
        await wait_done(page)
        await page.wait_for_timeout(1500)
        body = await page.inner_text("body")
        check("TC3 落库回执在场", ("已入库" in body) or ("错题本" in body), body[-160:])
        await page.screenshot(path="scripts/_pw_b3_saved.png")

        # ---- TC4 导出 Markdown ----
        async with page.expect_download(timeout=30000) as dl_info:
            await page.locator("button:has-text('Download'), button:has-text('下载')").first.click()
        dl = await dl_info.value
        check("TC4 下载触发", dl.suggested_filename.endswith(".md"), dl.suggested_filename)

        # ---- TC5 活动面板 ----
        act_btn = page.locator("button:has-text('Activity'), button:has-text('活动')").first
        await act_btn.click()
        await page.wait_for_timeout(1200)
        await page.screenshot(path="scripts/_pw_b3_activity.png")
        check("TC5 活动面板无 pageerror", not errors, str(errors[:2]))

        await browser.close()

    print(f"\n汇总: PASS={len(PASS)} FAIL={len(FAIL)}")
    sys.exit(1 if FAIL else 0)


asyncio.run(main())
