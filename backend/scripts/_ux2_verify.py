# -*- coding: utf-8 -*-
"""UX批② 对拍（反馈③④⑤）：对话域响应式列宽 + 面板可拖拽。

断言账：
1  反馈③ 1920×1080 留白：内容容器 ≥60% 视口（左右各 ≤1/5）
2  反馈③ 小屏回落：1280 视口内容宽 ≥720（下限不挤）
3  反馈④ 浮层拖宽：resizer 拖 100px → 面板宽 500 + localStorage 落库
4  反馈④ reload 记忆：重开面板仍 500
5  反馈④ 上限钳制：拖到 700 → 钳 640
6  反馈④ 钉住态拖宽：pinned 拖后主区让位随宽联动（content 宽差=宽差）
7  零 pageerror
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


def panel_w(pg):
    return pg.locator("[data-testid='shell-panel']").bounding_box()["width"]


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:100]))

    # 反馈③ 1920 留白
    pg.set_viewport_size({"width": 1920, "height": 1080})
    pg.goto(BASE + "/e/wenshu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    w = pg.evaluate("""() => {
      const ta = document.querySelector('textarea');
      let el = ta && ta.closest('div[style*="max-width"]');
      if (!el) el = ta && ta.parentElement;
      while (el && el.getBoundingClientRect().width < 720) el = el.parentElement;
      return el ? el.getBoundingClientRect().width : 0;
    }""")
    blank = (1920 - w) / 2
    check("反馈③ 1920 内容≥60%（留白≤1/5）", w >= 1920 * 0.6 - 2 and blank <= 1920 / 5 + 1, f"content={w:.0f} blank={blank:.0f}")
    pg.screenshot(path=str(SCR / "_ux2_1920.png"))

    # 反馈③ 1280 下限
    pg.set_viewport_size({"width": 1280, "height": 800})
    pg.wait_for_timeout(800)
    w2 = pg.evaluate("""() => {
      const ta = document.querySelector('textarea');
      let el = ta && ta.closest('div[style*="max-width"]');
      if (!el) el = ta && ta.parentElement;
      while (el && el.getBoundingClientRect().width < 700) el = el.parentElement;
      return el ? el.getBoundingClientRect().width : 0;
    }""")
    check("反馈③ 1280 内容 ≥720 下限", w2 >= 718, f"content={w2:.0f}")

    # 反馈④ 拖宽（浮层 console 面板）
    pg.set_viewport_size({"width": 1920, "height": 1080})
    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    pg.evaluate("() => localStorage.removeItem('shell:width:console')")
    pg.locator("[data-testid='activity-console']").click()
    pg.locator("[data-testid='shell-panel']").wait_for(state="visible", timeout=5000)
    pg.wait_for_timeout(400)
    w0 = panel_w(pg)
    check("④ 初始宽 400", abs(w0 - 400) <= 1, f"w={w0:.0f}")
    box = pg.locator("[data-testid='shell-panel']").bounding_box()
    sx = box["x"] + box["width"] - 2
    sy = box["y"] + 300
    pg.mouse.move(sx, sy)
    pg.mouse.down()
    pg.mouse.move(sx + 100, sy, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(400)
    w1 = panel_w(pg)
    check("④ 拖拽 +100 → 500", abs(w1 - 500) <= 3, f"w={w1:.0f}")
    ls_w = pg.evaluate("() => localStorage.getItem('shell:width:console')")
    check("④ 松手落库 localStorage（±2px 鼠标精度）", ls_w and abs(int(ls_w) - 500) <= 3, f"v={ls_w}")

    # 反馈④ reload 记忆
    pg.reload(timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    pg.locator("[data-testid='activity-console']").click()
    pg.locator("[data-testid='shell-panel']").wait_for(state="visible", timeout=5000)
    pg.wait_for_timeout(400)
    w2b = panel_w(pg)
    check("④ reload 仍 500", abs(w2b - 500) <= 3, f"w={w2b:.0f}")

    # 反馈④ 上限钳制
    box = pg.locator("[data-testid='shell-panel']").bounding_box()
    sx = box["x"] + box["width"] - 2
    pg.mouse.move(sx, box["y"] + 300)
    pg.mouse.down()
    pg.mouse.move(sx + 300, box["y"] + 300, steps=8)
    pg.mouse.up()
    pg.wait_for_timeout(400)
    w3 = panel_w(pg)
    check("④ 拖 700 钳 640", abs(w3 - 640) <= 3, f"w={w3:.0f}")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)

    # 反馈④ 钉住态拖宽联动（主区让位=宽差）
    pg.locator("[data-testid='activity-console']").click()
    pg.wait_for_timeout(400)
    pg.locator("[data-testid='shell-panel-pin']").click()
    pg.wait_for_timeout(400)
    cw0 = pg.evaluate("() => document.querySelector('.ant-layout-content').getBoundingClientRect().width")
    box = pg.locator("[data-testid='shell-panel']").bounding_box()
    sx = box["x"] + box["width"] - 2
    pg.mouse.move(sx, box["y"] + 300)
    pg.mouse.down()
    pg.mouse.move(sx - 100, box["y"] + 300, steps=6)
    pg.mouse.up()
    pg.wait_for_timeout(400)
    cw1 = pg.evaluate("() => document.querySelector('.ant-layout-content').getBoundingClientRect().width")
    check("④ 钉住拖宽主区联动（面板 -100 → content +100）", abs((cw1 - cw0) - 100) <= 4, f"dcw={cw1 - cw0:.0f}")
    pg.locator("[data-testid='shell-panel-pin']").click()
    pg.wait_for_timeout(300)
    pg.keyboard.press("Escape")

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    b.close()

fails = [x for x, ok in R if not ok]
print(f"\n=== UX批② 对拍：{len(R) - len(fails)}/{len(R)} PASS ===")
sys.exit(1 if fails else 0)
