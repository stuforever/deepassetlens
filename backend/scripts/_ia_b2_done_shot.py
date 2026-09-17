# 引擎批2 2.5 完成态取证：assistant 气泡+已完成头+用量脚注
import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:300]))
        await page.goto("http://localhost:23000/e/tutor/chat", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)
        ta = page.locator("textarea:visible").first
        await ta.fill("用一句话说明什么是知识图谱")
        await ta.press("Enter")
        # 等停止键出现（流中标记）
        try:
            await page.wait_for_selector("button:has(svg):near(textarea:visible)", timeout=10000)
        except Exception:
            pass
        # 最长等 150s 到流结束（停止键消失）
        for i in range(100):
            await page.wait_for_timeout(1500)
            try:
                stop_visible = await page.locator("[data-chat-scroll-root] >> text=推理中").count()
            except Exception:
                stop_visible = 0
            body = await page.locator("body").inner_text()
            if "已完成" in body and "推理中" not in body:
                break
        await page.wait_for_timeout(1500)
        body = await page.locator("body").inner_text()
        print("已完成头:", "已完成" in body)
        print("用量脚注(tokens):", ("tokens" in body) or ("调用" in body) or ("$" in body))
        # assistant 气泡内容抽验
        bubbles = await page.locator("[data-turn-bubble]").count()
        print("turn-bubble 数:", bubbles)
        for e in errors[:4]:
            print("PAGEERROR:", e)
        if not errors:
            print("PAGEERROR: none")
        await page.screenshot(path="backend/scripts/_pw_b2_done.png")
        print("shot: _pw_b2_done.png")
        await browser.close()

asyncio.run(main())
