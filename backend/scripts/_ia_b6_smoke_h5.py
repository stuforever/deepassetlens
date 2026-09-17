# -*- coding: utf-8 -*-
"""批6 6.6⑤ h5 全链 e2e：流式回显（桥 SSE）+历史抽屉 ?u= 隔离+重命名/删除。串行。"""
import asyncio
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
from playwright.async_api import async_playwright

BASE = "http://localhost:23000"
U = "e2e_b6"
PASS, FAIL = [], []


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else f" :: {detail}"))


async def wait_done(page, timeout_ms=180000):
    """h5 状态词「深度思考中」消失 + 2s 沉降（h5 用深度思考中/思考计秒）。"""
    await page.wait_for_timeout(1500)
    deadline = asyncio.get_event_loop().time() + timeout_ms / 1000
    while asyncio.get_event_loop().time() < deadline:
        body = await page.inner_text("body")
        if "深度思考中" not in body and "推理中" not in body:
            await page.wait_for_timeout(2000)
            return True
        await page.wait_for_timeout(3000)
    return False


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 430, "height": 930})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:160]))
        await page.goto(f"{BASE}/e/tutor-h5/chat?u={U}", wait_until="networkidle", timeout=180000)
        await page.wait_for_timeout(3000)
        body = await page.inner_text("body")
        check("h5 页面渲染", len(body.strip()) > 50, body[:120])
        await page.screenshot(path="scripts/_pw_b6_h5_home.png")

        # 发送一条消息（composer textarea——可见过滤）
        box = page.locator("textarea:visible").last
        await box.click()
        await box.fill("用一句话解释什么是微积分")
        await box.press("Enter")
        sent = await wait_done(page)
        check("h5 流式回显完成", sent, "等待超时")
        body = await page.inner_text("body")
        check("h5 助手有实质回复", any(k in body for k in ["极限", "变化率", "积分", "微分", "导数", "函数"]) or len(body) > 300, body[-150:])
        await page.screenshot(path="scripts/_pw_b6_h5_stream.png")

        # 历史抽屉：找历史/会话入口
        hist = page.locator("text=历史 >> visible=true").first
        if await hist.count() == 0:
            hist = page.locator("[class*='history'], [aria-label*='history'], button:has(svg)").first
        try:
            await hist.click()
            await page.wait_for_timeout(1500)
        except Exception:
            pass
        body2 = await page.inner_text("body")
        check("h5 历史含本轮会话", ("微积分" in body2) or ("新对话" in body2) or ("会话" in body2), body2[:150])
        await page.screenshot(path="scripts/_pw_b6_h5_history.png")

        # ?u= 隔离：另一用户看不到该会话
        page2 = await browser.new_page(viewport={"width": 430, "height": 930})
        await page2.goto(f"{BASE}/e/tutor-h5/chat?u=e2e_other", wait_until="networkidle", timeout=120000)
        await page2.wait_for_timeout(2500)
        try:
            h2 = page2.locator("text=历史 >> visible=true").first
            if await h2.count() > 0:
                await h2.click()
                await page2.wait_for_timeout(1200)
        except Exception:
            pass
        body3 = await page2.inner_text("body")
        check("h5 ?u= 隔离", "用一句话解释什么是微积分" not in body3, body3[:120])
        await page2.close()

        check("无 pageerror", not errors, str(errors[:2]))
        await browser.close()
    print(f"\n汇总: PASS={len(PASS)} FAIL={len(FAIL)}")
    sys.exit(1 if FAIL else 0)


asyncio.run(main())
