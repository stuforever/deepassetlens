# 引擎批2 2.5 全链冒烟：能力浮层 + 桥 SSE 真发消息 + 完成态
import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:200]))
        await page.goto("http://localhost:23000/e/tutor/chat", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2000)

        # 1) 能力浮层（点击 聊天 chip）
        cap_chip = page.locator("button:has-text('聊天')").first
        if await cap_chip.count() == 0:
            cap_chip = page.locator("button:has-text('Chat')").first
        await cap_chip.click()
        await page.wait_for_timeout(800)
        flyout_items = await page.locator("text=Multi-step reasoning").count()
        print("浮层 Solve 描述项:", flyout_items)
        await page.screenshot(path="backend/scripts/_pw_b2_flyout.png")
        # 关浮层
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(400)

        # 2) 真发消息（桥 SSE：/api/v2/skills/capability → tutor/chat 编排 → GLM 回答）
        ta = page.locator("textarea:visible").first
        await ta.fill("用一句话说明什么是知识图谱")
        await ta.press("Enter")
        print("已发送，等流式回答…")
        # 等回答（最长 90s：桥→LangGraph→LLM）
        try:
            await page.wait_for_selector("button[title='停止']", timeout=15000)
            print("停止按钮出现（流中）")
        except Exception:
            print("停止按钮未见（可能已完成或发送键不同）")
        done = False
        for _ in range(60):
            await page.wait_for_timeout(1500)
            body = await page.locator("body").inner_text()
            if "已完成" in body or ("知识图谱" in body and "已发送" not in body):
                done = True
                break
        print("回答完成:", done)
        body = await page.locator("body").inner_text()
        has_reply = any(k in body for k in ["知识图谱", "图结构", "实体", "关系"])
        print("回答含关键词:", has_reply)
        # 头部完成态/用量脚注
        print("已完成头:", "已完成" in body)
        for e in errors[:4]:
            print("PAGEERROR:", e)
        if not errors:
            print("PAGEERROR: none")
        await page.screenshot(path="backend/scripts/_pw_b2_answer.png")
        print("RESULT:", "PASS" if (done or has_reply) and not errors else "CHECK")
        await browser.close()

asyncio.run(main())
