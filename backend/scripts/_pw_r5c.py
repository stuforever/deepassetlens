# -*- coding: utf-8 -*-
"""R5批③ 对拍：book-api 修复实拍——书库列表经 request()（headers 合并新序）实拉数据。

book-api.request() 新展开序（...init 前置）下书库列表照常拉取=合并序无回归；
requestOverBridge 的 apiFetch 换装经同文件 import 链随 tsc 校验（生成动作需
书籍数据前置，登记：apiFetch 为全仓统一封装，行为面=credentials+401 门控）。
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:180], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:120]))

    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)

    # SPA 进书籍工作台（AppShellProvider 已由 R5批① 修复）
    pg.locator("[data-testid='activity-console']").click()
    pg.locator("[data-testid='nav-item-e:sishu:book']").click()
    pg.wait_for_timeout(2500)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)

    body = pg.inner_text("body")
    check("书库列表实拉数据（request() 新合并序）", ("书籍总数" in body or "我的书库" in body), body[:60].replace("\n", " "))
    n = pg.locator("text=/共 \\d+ 本/").count()
    check("书架计数行在场", n >= 1, f"count={n}")

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    pg.screenshot(path=str(SCR / "_pw_r5c.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== R5批③ 对拍：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
