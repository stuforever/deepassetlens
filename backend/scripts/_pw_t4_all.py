# -*- coding: utf-8 -*-
"""四题回归 e2e（Playwright 串行，AGENTS.md 铁律）：每题独立判定 tables>0，汇总 PASS/FAIL。

题目：查所有项目成本 / 查项目WBS / 查配电变压器重过载 / 查客户全量信息
用法：python _pw_t4_all.py
"""
import asyncio
import io
import json
import sys
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from playwright.async_api import async_playwright  # noqa: E402

QUESTIONS = [
    ("查所有项目成本", "t4r_cost", 150),
    ("查项目WBS", "t4r_wbs", 150),
    ("查配电变压器重过载", "t4r_overload", 220),
    ("查客户全量信息", "t4r_cust", 150),
]


async def ask(page, question, shot, timeout_s):
    await page.goto("http://localhost:23000/", wait_until="domcontentloaded")
    await page.wait_for_timeout(3500)
    ta = page.locator("textarea.ant-input").first
    await ta.wait_for(state="visible", timeout=20000)
    await ta.fill(question)
    await page.locator("button.ant-btn-primary").first.click()
    t0 = time.time()
    tables = 0
    while time.time() - t0 < timeout_s:
        tables = await page.locator(".ant-table").count()
        if tables > 0:
            break
        await page.wait_for_timeout(3000)
    await page.wait_for_timeout(2500)  # 等最终渲染稳定
    tables = await page.locator(".ant-table").count()
    # 抓表格首行数据与回答摘要
    first_cells = []
    try:
        tds = page.locator(".ant-table tbody tr").first.locator("td")
        n = min(await tds.count(), 4)
        first_cells = [(await tds.nth(i).inner_text()).strip()[:28] for i in range(n)]
    except Exception:
        pass
    await page.screenshot(path=f"scripts/_pw_{shot}.png")
    return {"tables": tables, "secs": round(time.time() - t0), "first_cells": first_cells}


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        report = {}
        for q, shot, tmo in QUESTIONS:
            # 每题独立 context（新 sessionStorage=新 thread）——否则 goto 恢复上一题对话，
            # 旧表格秒出造成 tables>0 假 PASS（首版实测后三题 3s 假阳）
            context = await browser.new_context(viewport={"width": 1440, "height": 900})
            page = await context.new_page()
            print(f"\n>>> {q} （上限 {tmo}s）", flush=True)
            r = await ask(page, q, shot, tmo)
            r["pass"] = r["tables"] > 0
            report[q] = r
            print(f"    tables={r['tables']} 耗时={r['secs']}s PASS={r['pass']} 首行={r['first_cells']}", flush=True)
            await context.close()
        await browser.close()
        print("\n== 四题回归汇总 ==")
        print(json.dumps(report, ensure_ascii=False, indent=1))
        ok = all(r["pass"] for r in report.values())
        print(f"VERDICT: {'PASS' if ok else 'FAIL'}")


asyncio.run(main())
