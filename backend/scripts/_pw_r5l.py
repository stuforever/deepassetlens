# -*- coding: utf-8 -*-
"""R5批⑫ 对拍（R#3 Drawer 三档对齐收尾）：对齐后抽屉宽度实测+横向溢出检测。

断言账：
1  映射分页/缓存抽屉 420→400（唯一收窄点）——宽实测 400±1 且内容无横向溢出
   （scrollWidth ≤ clientWidth——原「缩档溢出风险」的数值化验证）
2  金标新增抽屉 520→560（放宽向）——宽实测 560±1
3  零 pageerror
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


def drawer_metrics(pg):
    return pg.evaluate("""() => {
      const d = document.querySelector('.ant-drawer-content-wrapper:not([style*="display: none"])');
      if (!d) return null;
      const r = d.getBoundingClientRect();
      const body = d.querySelector('.ant-drawer-body');
      return {
        w: r.width,
        hOverflow: body ? body.scrollWidth > body.clientWidth + 1 : false,
        wOverflow: body ? body.scrollWidth : 0,
      };
    }""")


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:120]))

    # ① 映射页：分页/缓存配置抽屉（420→400 收窄点）
    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    pg.locator("[data-testid='activity-console']").click()
    pg.locator("[data-testid='nav-item-mapping']").click()
    pg.wait_for_timeout(2500)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)
    btn = pg.locator("button[title='分页/缓存配置']").first
    if btn.count() == 0:
        check("映射抽屉可开", False, "无端点行——登记（页面无数据时抽屉入口不存在）")
    else:
        btn.click()
        pg.wait_for_timeout(1200)
        m = drawer_metrics(pg)
        check("映射抽屉宽=400（sm 档）", m and abs(m["w"] - 400) <= 1, f"w={m and round(m['w'])}")
        check("映射抽屉无横向溢出", m and not m["hOverflow"], f"scrollW={m and m['wOverflow']}")

    # ② 金标页：新增金标抽屉（520→560 放宽点）
    pg.goto(BASE + "/golden-qa", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    add = pg.get_by_text("新增金标", exact=True).first
    add.click()
    pg.wait_for_timeout(1200)
    m2 = drawer_metrics(pg)
    check("金标抽屉宽=560（md 档）", m2 and abs(m2["w"] - 560) <= 1, f"w={m2 and round(m2['w'])}")

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    pg.screenshot(path=str(SCR / "_pw_r5l.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== R5批⑫（R#3）对拍：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
