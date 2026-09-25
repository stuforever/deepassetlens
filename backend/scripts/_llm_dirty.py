# -*- coding: utf-8 -*-
"""判别：编辑字段 vs 复制档——哪种草稿改动能点亮保存按钮。"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(__file__).parent
BASE = "http://localhost:23000"


def status(pg):
    return pg.evaluate("""() => {
        const el = document.querySelector('[data-testid=settings-toolbar-status]');
        const btn = document.querySelector('[data-testid=settings-save-btn]');
        return { text: el ? el.innerText.trim() : null, disabled: btn ? btn.disabled : null };
    }""")


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(SCR))
    from _pw_login_util import login_page
    pg = login_page(b)
    pg.set_viewport_size({"width": 1920, "height": 1080})
    pg.goto(BASE + "/settings/llm", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)

    print("初始:", status(pg), flush=True)

    # A. 编辑 base_url 字段（加再删一个字符）
    pg.get_by_text("OpenAI", exact=True).first.click()
    pg.wait_for_timeout(1000)
    inp = pg.locator("input[placeholder='https://api.openai.com/v1']").first
    inp.fill(inp.input_value() + " ")
    pg.wait_for_timeout(600)
    print("字段编辑后:", status(pg), flush=True)
    inp.fill(inp.input_value().rstrip())
    pg.wait_for_timeout(600)
    print("字段还原后:", status(pg), flush=True)

    # B. 复制档
    pg.get_by_text("4coding", exact=True).first.click()
    pg.wait_for_timeout(1000)
    pg.locator("[data-testid='service-duplicate-profile-llm']").click()
    pg.wait_for_timeout(1200)
    st = status(pg)
    print("复制档后:", st, flush=True)
    pg.screenshot(path=str(SCR / "_llm_dirty.png"), full_page=True)
    b.close()
