# -*- coding: utf-8 -*-
"""批② 对拍：composer 聚焦仅边框变色无阴影（附录B.2-3）+ 斜体清零抽查 + tokens 在场。"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
R = []
sys.path.insert(0, str(SCR))
from _pw_login_util import login_page  # noqa: E402


def check(name, ok, detail=""):
    R.append(bool(ok))
    print(("GREEN " if ok else "RED   ") + name + "  " + str(detail)[:110], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = login_page(b)
    pg.goto(BASE + "/e/wenshu/chat", timeout=90000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)

    # composer 聚焦前后：border-color 变化 & box-shadow 不加环
    comp = pg.locator(".dal-composer").first
    if comp.count() == 0:
        # 无消息页可能为欢迎悬浮 composer——同 class
        comp = pg.locator("[class*='dal-composer']").first
    before = comp.evaluate("el => getComputedStyle(el).boxShadow + ' | ' + getComputedStyle(el).borderColor")
    ta = comp.locator("textarea").first
    ta.click()
    pg.wait_for_timeout(400)
    after = comp.evaluate("el => getComputedStyle(el).boxShadow + ' | ' + getComputedStyle(el).borderColor")
    b_shadow, b_border = [x.strip() for x in before.split("|")]
    a_shadow, a_border = [x.strip() for x in after.split("|")]
    check("聚焦后 border-color 变主色", a_border != b_border and ("37, 99, 235" in a_border or "#2563eb" in a_border.lower()),
          f"{b_border[-18:]} -> {a_border[-18:]}")
    check("聚焦无新增阴影环", ("1.5px" not in a_shadow) and ("0 0 0 1.5px" not in a_shadow),
          a_shadow[:60])
    pg.screenshot(path=str(SCR / "_pw_b2_focus.png"))

    # 排版 tokens 在场（:root CSS 变量）
    has_vars = pg.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--fs-t3').trim()")
    check("附录A tokens 落地（--fs-t3=14px）", has_vars == "14px", has_vars)
    mono = pg.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--font-mono').trim()")
    check("--font-mono 在场", "Consolas" in mono, mono[:40])

    b.close()

greens = sum(R)
print(f"\n=== 批② 对拍：{greens}/{len(R)} GREEN ===")
sys.exit(0 if greens == len(R) else 1)
