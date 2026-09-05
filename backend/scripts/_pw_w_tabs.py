# -*- coding: utf-8 -*-
"""批13-W 十步 Tab 管理页 e2e（Playwright headless，AGENTS.md 铁律）。

流程：
  1. 开 /security-controls → 断言十步 Tab 结构（Tab0/守卫/步1-10）
  2. Tab0 manifest 总览渲染（四 mode/勾选域标签）
  3. 步7 打开 tool_availability 参数 → 打勾清单渲染（锁定件灰显）
  4. 只读教学页渲染（步2/3/8）
用法：python _pw_w_tabs.py <截图名>
"""
import asyncio
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from playwright.async_api import async_playwright  # noqa: E402

SHOT = sys.argv[1] if len(sys.argv) > 1 else "wtabs"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 2400 宽防 antd Tabs 折叠（12 个 Tab 在窄视口收进「更多」下拉，click 失效）
        page = await browser.new_page(viewport={"width": 2400, "height": 1000})
        await page.goto("http://localhost:23000/security-controls", wait_until="domcontentloaded")
        await page.wait_for_timeout(4500)

        report = {}

        # 1. Tab 结构断言
        body = await page.inner_text("body")
        tab_names = ["全局 · 缓存与版本", "守卫（运行期）", "步1", "步2", "步3", "步4",
                     "步5", "步6", "步7", "步8/9", "步10"]
        report["tabs_found"] = {t: (t in body) for t in tab_names}
        report["tabs_all_ok"] = all(report["tabs_found"].values())

        # 2. Tab0 内容
        report["tab0_cache_key"] = "缓存键四成分" in body
        report["tab0_mode"] = "backend_mode" in body or "装配 manifest 总览" in body

        # 截图 Tab0
        await page.screenshot(path=f"scripts/_pw_{SHOT}_tab0.png")

        # 3. 步7 → tool_availability 参数（打勾清单）
        await page.click("text=步7 · 筛与拼")
        await page.wait_for_timeout(1200)
        body7 = await page.inner_text("body")
        report["step7_toolcard"] = "工具白名单" in body7
        # 打开参数抽屉：两个卡（tool_availability/decision_gate）各一参数钮，逐个试开打勾清单
        btns = page.locator("button:has-text('参数')")
        n = await btns.count()
        report["step7_param_btns"] = n
        saw_allowlist = saw_scopegate = saw_locked_disabled = False
        checkbox_total = 0
        for bi in range(min(n, 2)):
            await btns.nth(bi).click()
            await page.wait_for_timeout(1600)
            bodyd = await page.inner_text("body")
            if "白名单打勾制" in bodyd:
                saw_allowlist = True
                saw_locked_disabled = (await page.locator(".ant-checkbox-disabled").count()) > 0
                checkbox_total = await page.locator(".ant-checkbox-wrapper").count()
            if "范围强校验工具集" in bodyd:
                saw_scopegate = True
            await page.screenshot(path=f"scripts/_pw_{SHOT}_step7_drawer{bi}.png")
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(700)
        report["checklist_allowlist_open"] = saw_allowlist
        report["checklist_scopegate_open"] = saw_scopegate
        report["locked_disabled"] = saw_locked_disabled
        report["universe_tags_19"] = checkbox_total >= 19

        # 4. 教学页
        await page.click("text=步2 · 体检")
        await page.wait_for_timeout(900)
        body2 = await page.inner_text("body")
        report["teach2"] = "保护名单" in body2 and "本步不可配置原因" in body2

        await page.screenshot(path=f"scripts/_pw_{SHOT}_final.png")
        await browser.close()

        print("== 十步 Tab e2e 报告 ==")
        print(json.dumps(report, ensure_ascii=False, indent=1))
        ok = (report["tabs_all_ok"] and report["tab0_cache_key"] and report["step7_toolcard"]
              and report.get("checklist_allowlist_open") and report.get("checklist_scopegate_open")
              and report.get("locked_disabled") and report.get("universe_tags_19")
              and report.get("teach2"))
        print(f"VERDICT: {'PASS' if ok else 'FAIL'}")


asyncio.run(main())
