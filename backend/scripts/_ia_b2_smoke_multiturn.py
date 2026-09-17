# 引擎批2 TC1b 多轮（全防护版：失败即取证）
import asyncio, sys, io, traceback
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:300]))
        try:
            await page.goto("http://localhost:23000/e/tutor/chat", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(2500)

            async def send_and_wait(q: str, max_s: int = 120):
                tas = page.locator("textarea:visible")
                n = await tas.count()
                print(f"  [send] 可见textarea={n}")
                ta = tas.last
                await ta.click()
                await ta.fill(q)
                await ta.press("Enter")
                for _ in range(max_s // 2):
                    await page.wait_for_timeout(2000)
                    body = await page.locator("body").inner_text()
                    if "已完成" in body:
                        return body
                return await page.locator("body").inner_text()

            b1 = await send_and_wait("我叫小明，请记住。请只回复：好的")
            print("第一轮完成:", "已完成" in b1)
            await page.wait_for_timeout(1500)
            b2 = await send_and_wait("我叫什么名字？")
            # 等"推理中"消失（真正流结束）
            for _ in range(60):
                await page.wait_for_timeout(2000)
                body2 = await page.locator("body").inner_text()
                if "推理中" not in body2:
                    break
            b2 = body2
            print("第二轮完成:", "已完成" in b2)
            tail = b2.split("我叫什么名字")[-1] if "我叫什么名字" in b2 else b2
            print("记忆召回(小明):", "小明" in tail)
            bubbles = await page.locator("[data-turn-bubble]").count()
            print("turn-bubble 数(应>=4):", bubbles)
        except Exception as e:
            print("EXC:", str(e)[:200])
            await page.screenshot(path="backend/scripts/_pw_b2_mt_fail.png")
        finally:
            print("PAGEERROR:", errors[:4] if errors else "none")
            try:
                await page.screenshot(path="backend/scripts/_pw_b2_mt_end.png")
            except Exception:
                pass
            await browser.close()

asyncio.run(main())
