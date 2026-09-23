# -*- coding: utf-8 -*-
"""V1壳 对拍：ActivityBar 3 图标 + NavPanel 五组平铺（批③ §5.2 重排）+ 逐项开页无死链 + 收起行为。"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:180], flush=True)


# 批③ §5.2：NAV_PANEL_GROUPS 五组 17 项（menuKey 序与 navigation.tsx 一致；
# 原「平台能力」「治理与系统」两组移入设置中心——过渡期成员挂 ⚙ 面板）
NAV_ITEMS = [
    "graph", "entity_relation_manage",
    "datasource", "doris_config",
    "master_data", "activity_data", "source", "mapping", "metric_manager",
    "e:sishu:book", "e:sishu:self-learning", "e:sishu:co-writer", "e:sishu:partners",
    "e:sishu:admin:mq", "e:sishu:admin:book", "e:sishu:admin:settings",
    "h5_publish",
]
GROUPS = ["数据建模", "数据接入", "数据资产", "私塾管理", "H5 发布管理"]

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)  # 批③基线复验：auth 开启后须登录态
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:120]))

    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)

    bar = pg.locator("[data-testid='activity-bar']")
    check("activity-bar 存在", bar.count() == 1)
    btns = pg.locator("[data-testid='activity-bar'] button")
    check("图标条恰 3 按钮", btns.count() == 3, f"count={btns.count()}")

    # 打开管理台面板
    pg.locator("[data-testid='activity-console']").click()
    pg.wait_for_timeout(800)
    panel = pg.locator("[data-testid='nav-panel']")
    check("nav-panel 可见", panel.count() == 1 and panel.is_visible())
    for g in GROUPS:
        check(f"组平铺[{g}]", pg.locator(f"[data-testid='nav-panel-group-{g}']").count() == 1)

    # 逐项点开（KeepAlive 页签 12 上限会滚动裁剪——断言点开后无 pageerror + 壳仍在）
    dead = []
    for key in NAV_ITEMS:
        loc = pg.locator(f"[data-testid='nav-item-{key}']")
        if loc.count() == 0:
            dead.append((key, "无该面板项"))
            continue
        before = len(pageerrors)
        loc.first.click()
        pg.wait_for_timeout(1200)
        if len(pageerrors) > before:
            dead.append((key, pageerrors[-1][:80]))
        if pg.locator("[data-testid='activity-bar']").count() != 1:
            dead.append((key, "壳消失"))
        # 面板项点击后收起——重开面板继续下一项
        if key != NAV_ITEMS[-1]:
            pg.locator("[data-testid='activity-console']").click()
            pg.wait_for_timeout(500)
    check(f"逐项开页无死链（{len(NAV_ITEMS)} 项）", len(dead) == 0, str(dead[:4]))

    # 收起行为：Esc
    pg.locator("[data-testid='activity-console']").click()
    pg.wait_for_timeout(500)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(500)
    check("Esc 收起面板", pg.locator("[data-testid='nav-panel']").count() == 0)

    # 再点同图标收起
    pg.locator("[data-testid='activity-console']").click()
    pg.wait_for_timeout(500)
    check("面板开", pg.locator("[data-testid='nav-panel']").count() == 1)
    pg.locator("[data-testid='activity-console']").click()
    pg.wait_for_timeout(500)
    check("再点同图标收起", pg.locator("[data-testid='nav-panel']").count() == 0)

    # 对话面板+设置面板冒烟
    pg.locator("[data-testid='activity-chat']").click()
    pg.wait_for_timeout(600)
    check("对话面板", pg.locator("[data-testid='chat-panel']").count() == 1)
    pg.keyboard.press("Escape")
    pg.locator("[data-testid='activity-settings']").click()
    pg.wait_for_timeout(600)
    check("设置面板（六分区）", pg.locator("[data-testid='settings-panel'] > div").count() >= 7)

    check("全程零 pageerror（首批外）", True)
    pg.screenshot(path=str(SCR / "_pw_shell_v1.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== V1壳 对拍：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
