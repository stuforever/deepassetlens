# -*- coding: utf-8 -*-
"""R5批② 对拍（R#2 select 续批代表页）：ServiceConfigEditor provider 下拉 antd 化实拍。

只开不选——provider onChange 带 previousLabel 级联副作用（profile 改名/base_url/
默认模型链），冒烟断言渲染+弹层+选项数即止，不动 profile 状态。
CowriterEditor×3 / PartnerConfigure / schema-form 置换按同模式（onFocus/onBlur
契约逐字保留）以 tsc+批① 实点先例覆盖，登记。
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

    # SPA 进设置中心 LLM 分区（ServiceConfigEditor 挂载域）
    pg.locator("[data-testid='activity-settings']").click()
    pg.wait_for_timeout(800)
    pg.locator("[data-testid='settings-panel-navitem-llmconfig']").click()
    pg.wait_for_timeout(2500)
    check("落到 /settings/llm", "/settings/llm" in pg.url, pg.url[:90])

    prov = pg.locator("[data-testid^='service-provider-select-']")
    n_prov = prov.count()
    check("provider 下拉在场（≥1）", n_prov >= 1, f"count={n_prov}")
    if n_prov >= 1:
        cls = (prov.first.get_attribute("class") or "")
        check("antd Select 形态", "ant-select" in cls, cls[:60])
        prov.first.click()
        pg.wait_for_timeout(700)
        opts = pg.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option")
        check("弹层选项 ≥2", opts.count() >= 2, f"opts={opts.count()}")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(400)

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    pg.screenshot(path=str(SCR / "_pw_r5b.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== R5批② 代表页对拍：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
