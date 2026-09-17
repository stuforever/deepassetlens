# 引擎批2 2.6 佐证：TutorHomeChat 会话入平台 store → 侧栏最近对话
import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1440, "height": 900})
        await page.goto("http://localhost:23000/e/tutor/chat", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(2500)
        ta = page.locator("textarea:visible").last
        await ta.click(); await ta.fill("会话源验证：请只回复两个字：好的")
        await ta.press("Enter")
        for _ in range(60):
            await page.wait_for_timeout(2000)
            body = await page.locator("body").inner_text()
            if "已完成" in body and "推理中" not in body:
                break
        # 侧栏状态
        body = await page.locator("body").inner_text()
        # localStorage 会话
        raw = await page.evaluate("() => localStorage.getItem('di_sessions_freeplan_v1') || '[]'")
        import json
        sessions = json.loads(raw)
        tutor_sessions = [s for s in sessions if s.get("expertId") == "tutor"]
        print("store 会话总数:", len(sessions))
        print("tutor 会话数:", len(tutor_sessions))
        for s in tutor_sessions[:3]:
            print("  tutor 会话标题:", s.get("title", "")[:40])
        print("SIDEBAR_OK:", len(tutor_sessions) >= 1)
        await page.screenshot(path="backend/scripts/_pw_b2_store.png")
        await browser.close()

asyncio.run(main())
