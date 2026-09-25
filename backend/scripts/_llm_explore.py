# -*- coding: utf-8 -*-
"""LLM 设置页探查：/settings/llm 真实 UI 结构 + 测试/保存/复制按钮定位。"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(__file__).parent
BASE = "http://localhost:23000"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(SCR))
    from _pw_login_util import login_page
    pg = login_page(b)
    pg.set_viewport_size({"width": 1920, "height": 1080})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)[:200]))
    console_errs = []
    pg.on("console", lambda m: console_errs.append(m.text[:200]) if m.type == "error" else None)

    pg.goto(BASE + "/settings/llm", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    pg.screenshot(path=str(SCR / "_llm_page.png"), full_page=True)
    text = pg.evaluate("() => document.body.innerText")
    print("=== PAGE TEXT (first 3000 chars) ===")
    print(text[:3000])
    print("=== BUTTONS ===")
    btns = pg.evaluate("""() => Array.from(document.querySelectorAll('button,[role=button]'))
        .map(el => (el.innerText || el.getAttribute('aria-label') || '').trim())
        .filter(t => t && t.length < 30)""")
    print(sorted(set(btns)))
    print("=== pageerror ===", errors[:3])
    print("=== console errors ===", console_errs[:5])
    b.close()
