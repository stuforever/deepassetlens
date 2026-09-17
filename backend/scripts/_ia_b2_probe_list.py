# 引擎批2 探查：消息列表为何空白
import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:300]))
        console = []
        page.on("console", lambda m: console.append(m.text[:200]) if m.type == "error" else None)
        await page.goto("http://localhost:23000/e/tutor/chat", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)
        ta = page.locator("textarea:visible").first
        await ta.fill("你好，请只回复两个字：好的")
        await ta.press("Enter")
        await page.wait_for_timeout(20000)
        # 消息面 DOM 计数
        counts = {}
        counts["data-turn-key"] = await page.locator("[data-turn-key]").count()
        counts["data-chat-column"] = await page.locator("[data-chat-column]").count()
        counts["data-chat-scroll-root"] = await page.locator("[data-chat-scroll-root]").count()
        col_html = ""
        if counts["data-chat-column"]:
            col = page.locator("[data-chat-column]").first
            col_html = (await col.inner_html())[:600]
        scroll_html = ""
        if counts["data-chat-scroll-root"]:
            sr = page.locator("[data-chat-scroll-root]").first
            scroll_html = (await sr.inner_html())[:600]
        print("==== 计数 ====")
        for k, v in counts.items():
            print(f"{k}: {v}")
        print("==== chat-column html 头 600 ====")
        print(col_html or "(空)")
        print("==== scroll-root html 头 600 ====")
        print(scroll_html or "(空)")
        print("==== pageerror ====")
        for e in errors[:4]:
            print("PE:", e)
        if not errors:
            print("none")
        print("==== console error ====")
        for c in console[:6]:
            print("CE:", c)
        if not console:
            print("none")
        await browser.close()

asyncio.run(main())
