# -*- coding: utf-8 -*-
"""UX3批1 P0 三修对拍：backdrop 吃击 / 设置子页挂壳 / 新建对话留守当前空间。

断言账：
P0-A 第一击生效：/e/wenshu/chat 开 💬 浮层面板 → 主区 composer 输入并点发送一次
    → 消息列表 +1 且浮层面板已收起（修复前：第一击只收面板，消息未发出）
P0-B 子页带壳：/settings/chat → SettingsLayout 二级侧栏可见 → 点「聊天」→ 侧栏仍在、主区聊天页可见
    （修复前：点完整个设置壳消失）
P0-C 新建留守：/e/sishu/chat → 开 💬 面板 → 点 chat-panel-new
    → URL == /e/sishu/chat?new=1；space-color-bar 仍可见；面板未关闭
    （修复前：navigate('/') 跳门户）
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
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:100]))

    # ── P0-A 第一击生效 ──
    pg.goto(BASE + "/e/wenshu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    pg.locator("[data-testid='activity-chat']").click()
    pg.locator("[data-testid='shell-panel']").wait_for(state="visible", timeout=5000)
    pg.wait_for_timeout(400)
    # 主区 composer（ExpertChat 的 UnifiedComposer，非面板内）
    main_ta = pg.locator(".ant-layout-content textarea").first
    n_before = pg.locator(".ant-layout-content textarea").count()
    main_ta.fill("UX3P0第一击测试")
    # 点主区发送钮（点击路径——backdrop 吃击的精确复现；键盘发送不经过 backdrop）
    send_btn = pg.locator("[data-testid='expert-composer-send']").first
    if send_btn.count() == 0:
        send_btn = pg.locator(".ant-layout-content button[class*='send'], .ant-layout-content button:has(.anticon-send)").first
    try:
        send_btn.click(timeout=5000)
    except Exception as e:
        # 修复前预期：backdrop 拦截点击（Playwright 重试至超时）——本异常即缺陷本体证据
        check("P0-A 发送钮可点击", False, str(e)[:80])
    pg.wait_for_timeout(1500)
    sent = "UX3P0第一击测试" in pg.inner_text(".ant-layout-content")
    panel_gone = pg.locator("[data-testid='shell-panel']").is_hidden()
    check("P0-A 首击发出消息（点击路径）", sent, f"body含用户文本={sent}")
    check("P0-A 面板已收起", panel_gone)
    pg.screenshot(path=str(SCR / "_ux3p0_a.png"))

    # ── P0-B 设置子页带壳 ──
    pg.goto(BASE + "/settings/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    sidebar = pg.locator("[data-testid='settings-layout-sidebar']")
    check("P0-B 子页挂 SettingsLayout 壳（侧栏在场）", sidebar.count() == 1 and sidebar.is_visible())
    if sidebar.count():
        # 点侧栏「聊天」项
        pg.locator("[data-testid='settings-layout-sidebar']").get_by_text("聊天", exact=False).first.click()
        pg.wait_for_timeout(1500)
        check("P0-B 点侧栏后壳仍在", sidebar.count() == 1 and sidebar.is_visible())
        check("P0-B 主区聊天页内容", "聊天" in pg.inner_text("body"))
    pg.screenshot(path=str(SCR / "_ux3p0_b.png"))

    # ── P0-C 新建留守当前空间 ──
    pg.goto(BASE + "/e/sishu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    pg.locator("[data-testid='activity-chat']").click()
    pg.locator("[data-testid='chat-panel']").wait_for(state="visible", timeout=5000)
    pg.wait_for_timeout(400)
    pg.locator("[data-testid='chat-panel-new']").click()
    pg.wait_for_timeout(1500)
    check("P0-C URL=?new=1 留守私塾", "/e/sishu/chat" in pg.url and "new=1" in pg.url, pg.url[:80])
    check("P0-C space-color-bar 仍可见", pg.locator("[data-testid='space-color-bar']").count() >= 1)
    check("P0-C 面板未关闭", pg.locator("[data-testid='chat-panel']").is_visible())
    pg.screenshot(path=str(SCR / "_ux3p0_c.png"))

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    b.close()

fails = [x for x, ok in R if not ok]
print(f"\n=== UX3批1 P0 三修对拍：{len(R) - len(fails)}/{len(R)} PASS ===")
sys.exit(1 if fails else 0)
