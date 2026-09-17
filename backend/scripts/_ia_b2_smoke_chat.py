# 引擎批2 2.5 冒烟：/e/tutor/chat 渲染态（headless）
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
        await page.wait_for_timeout(2500)
        # 欢迎语/头按钮/composer 存在性
        checks = {}
        checks["标题或欢迎语"] = await page.locator("h1").count()
        checks["下载按钮"] = await page.locator("button[title='下载 Markdown']").count()
        checks["活动按钮"] = await page.locator("button[title='活动']").count()
        checks["保存到笔记本"] = await page.locator("button[title='保存到笔记本']").count()
        checks["composer_textarea"] = await page.locator("textarea").count()
        checks["能力菜单按钮"] = await page.locator("button:has-text('Chat')").count()
        body_text = await page.locator("body").inner_text()
        checks["页面非空白"] = 1 if len(body_text.strip()) > 50 else 0
        print("==== 检查项 ====")
        ok = True
        for k, v in checks.items():
            mark = "PASS" if v and v > 0 else "FAIL"
            if mark == "FAIL":
                ok = False
            print(f"{mark} {k}: {v}")
        print("==== 页面错误 ====")
        for e in errors[:5]:
            print("PAGEERROR:", e)
        if not errors:
            print("PAGEERROR: none")
        await page.screenshot(path="backend/scripts/_pw_b2_tutor_chat.png")
        print("shot: backend/scripts/_pw_b2_tutor_chat.png")
        print("SMOKE:", "PASS" if ok and not errors else "CHECK")
        await browser.close()

asyncio.run(main())
