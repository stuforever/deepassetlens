# -*- coding: utf-8 -*-
"""UX3批3 对拍：右栏拖宽+Tooltip+历史不自关。

断言账：
R1 ContextRail 展开面板可拖宽（拖左缘 → 宽变化）
R2 拖宽后 reload 记忆（rail:width localStorage）
R3 细条图标 Tooltip 在场
零 pageerror
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(__file__).parent
BASE = "http://localhost:23000"
R = []


def check(name, ok, detail=""):
    R.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:170], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)
    pg.set_viewport_size({"width": 1920, "height": 1080})
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:100]))

    pg.goto(BASE + "/e/wenshu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    # 注入种子会话让 hasMessages=true → ContextRail 渲染
    pg.evaluate("""() => {
      const seed = [{ id: 'ux3-seed', title: 'UX3测试', expertId: 'wenshu', messages: [{ role: 'user', text: 'test', id: 'm1' }], confirmed: {}, flags: {}, thinkStream: [], pendingCandidates: [], finalTokens: [], createdAt: Date.now() }];
      localStorage.setItem('di_sessions_freeplan_v1', JSON.stringify(seed));
    }""")
    pg.reload(timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)

    # 展开右栏（点击细条图标）
    icon = pg.locator("[data-testid='context-rail-icon-evidence']").first
    if icon.count() == 0:
        icon = pg.locator("[data-testid='context-rail-strip'] button").first
    icon.click()
    pg.wait_for_timeout(1000)

    panel = pg.locator("[data-testid='context-rail-panel']")
    if panel.count() == 0:
        check("右栏面板展开", False, "panel not found")
    else:
        w0 = panel.bounding_box()["width"]
        check("R1a 右栏面板展开", w0 >= 280, f"w={w0:.0f}")

        # 拖左缘 +100
        box = panel.bounding_box()
        sx = box["x"] - 2
        sy = box["y"] + 300
        pg.mouse.move(sx, sy)
        pg.mouse.down()
        pg.mouse.move(sx - 100, sy, steps=8)
        pg.mouse.up()
        pg.wait_for_timeout(500)
        w1 = panel.bounding_box()["width"]
        check("R1b 拖宽 +100 → 面板变宽", w1 > w0 + 50, f"w0={w0:.0f} w1={w1:.0f}")

        # reload 记忆
        pg.reload(timeout=60000, wait_until="domcontentloaded")
        pg.wait_for_timeout(6000)
        icon = pg.locator("[data-testid='context-rail-icon-evidence']").first
        if icon.count():
            icon.click()
            pg.wait_for_timeout(1000)
        panel2 = pg.locator("[data-testid='context-rail-panel']")
        if panel2.count():
            w2 = panel2.bounding_box()["width"]
            check("R2 reload 宽保持", abs(w2 - w1) <= 5, f"w2={w2:.0f} w1={w1:.0f}")
        else:
            check("R2 reload 宽保持", False, "panel not found after reload")

        # R3 Tooltip
        strip_btn = pg.locator("[data-testid='context-rail-strip'] button").first
        strip_btn.hover()
        pg.wait_for_timeout(800)
        tt = pg.locator(".ant-tooltip:not(.ant-tooltip-hidden)")
        check("R3 Tooltip 在场", tt.count() >= 1)

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    pg.screenshot(path=str(SCR / "_ux3_rail.png"))
    b.close()

fails = [x for x, ok in R if not ok]
print(f"\n=== UX3批3 对拍：{len(R) - len(fails)}/{len(R)} PASS ===")
sys.exit(1 if fails else 0)
