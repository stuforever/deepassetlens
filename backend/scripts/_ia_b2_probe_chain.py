# 引擎批2 链路探查：二轮后 turn-key/气泡结构
import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://localhost:23000/e/tutor/chat", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2500)

        async def send(q):
            ta = page.locator("textarea:visible").last
            await ta.click(); await ta.fill(q); await ta.press("Enter")
            for _ in range(60):
                await page.wait_for_timeout(2000)
                body = await page.locator("body").inner_text()
                if body.count("已完成") >= (2 if q.startswith("我')") else 1):
                    return
                if "已完成" in body and "推理中" not in body:
                    return

        await send("我叫小明。请只回复两个字：好的")
        await page.wait_for_timeout(1500)
        await send("我叫什么名字？")
        await page.wait_for_timeout(1500)
        keys = await page.locator("[data-turn-key]").count()
        print("turn-key 数:", keys)
        bubbles = await page.locator("[data-turn-bubble]").count()
        print("bubble 数:", bubbles)
        col = page.locator("[data-chat-column]").first
        html = await col.inner_html()
        # 只打印 data-turn-key 序列与文本摘要
        import re
        for m in re.finditer(r'data-turn-key="([^"]+)"', html):
            print("turn:", m.group(1))
        texts = await page.locator("[data-turn-bubble] div.whitespace-pre-wrap, [data-turn-bubble] p").all_inner_texts()
        for t in texts[:6]:
            print("bubble文本:", t[:60])
        # 二轮回答文本
        body = await page.locator("body").inner_text()
        idx = body.find("我叫什么名字")
        print("二轮后文:", body[idx:idx+160].replace("\n", " | ") if idx >= 0 else "(未见问句)")
        await browser.close()

asyncio.run(main())
