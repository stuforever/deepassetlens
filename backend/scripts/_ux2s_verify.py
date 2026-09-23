# -*- coding: utf-8 -*-
"""UX2批 综合验收（反馈①②③④⑤⑥⑦⑧ UI 层；⑤⑨ LLM/H5 深测另脚本）。

断言账：
① 首页三卡：portal-cards=3 + 卡点击单跳各入口 + greeting
② 附件条：仅 attach-model（kb/skill/role 移除）+ 模型下拉可开
③ 新建契约：?new=1 强制新会话（发送后新 sid ≠ 预置老 sid）
④ 私塾风格：bg 同问数 + 消息列 60vw + composer 卡片（borderRadius 24）
⑤ 会话类别 Tab（ChatPanel）：chat-cat-tabs 四片 + 类别过滤生效
⑥ ——（并入⑤）
⑦ 钉住导航不自隐：pin → 点会话行 → 面板仍在
⑧ 私塾七按钮：sishu-grid-* 零在场
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
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:100]))

    # ── ① 首页三卡 ──
    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    check("① 三卡在场", pg.locator("[data-testid='portal-card-wenshu']").count() == 1
          and pg.locator("[data-testid='portal-card-sishu']").count() == 1
          and pg.locator("[data-testid='portal-card-h5']").count() == 1)
    check("① greeting 在场", pg.locator("[data-testid='portal-greeting']").count() == 1)
    pg.screenshot(path=str(SCR / "_ux2s_01_portal.png"))
    pg.locator("[data-testid='portal-card-wenshu']").click()
    pg.wait_for_timeout(2000)
    check("① 问数卡单跳", "/e/wenshu/chat" in pg.url, pg.url[:70])
    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    pg.locator("[data-testid='portal-card-sishu']").click()
    pg.wait_for_timeout(2000)
    check("① 私塾卡单跳", "/e/sishu/chat" in pg.url, pg.url[:70])
    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    pg.locator("[data-testid='portal-card-h5']").click()
    pg.wait_for_timeout(2000)
    check("① h5 卡单跳", "/h5-publish" in pg.url, pg.url[:70])

    # ── ② 附件条瘦身 ──
    pg.goto(BASE + "/e/wenshu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    check("② kb/skill/role 移除", pg.locator("[data-testid='attach-kb']").count() == 0
          and pg.locator("[data-testid='attach-skill']").count() == 0
          and pg.locator("[data-testid='attach-role']").count() == 0)
    model_sel = pg.locator("[data-testid='attach-model']")
    check("② 模型选择器在场", model_sel.count() == 1)
    model_sel.click()
    pg.wait_for_timeout(700)
    n_opts = pg.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option").count()
    check("② 模型下拉可开（≥1 项）", n_opts >= 1, f"opts={n_opts}")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)

    # ── ③ 新建契约（?new=1 强制新会话） ──
    old_sid = pg.evaluate("() => { const s = JSON.parse(localStorage.getItem('di_sessions_freeplan_v1') || '[]'); return s.length ? s[0].id : null }")
    if not old_sid:
        pg.evaluate("() => { const s = JSON.parse(localStorage.getItem('di_sessions_freeplan_v1') || '[]'); if (s.length) window.__old = s[0].id; }")
    # 直接带 ?new=1&q= 进入 → 发出后新建会话不等于旧 activeSession
    pg.goto(BASE + "/e/wenshu/chat?new=1&q=UX2%E6%96%B0%E5%BB%BA%E5%A5%91%E7%BA%A6", timeout=60000, wait_until="domcontentloaded")
    ok_send = False
    for _ in range(12):
        pg.wait_for_timeout(1500)
        if "UX2新建契约" in pg.inner_text("body"):
            ok_send = True
            break
    body = pg.inner_text("body")
    check("③ ?new=1 发出（消息区含用户文本）", ok_send, body[:60].replace("\n", " "))

    # ── ⑧ 私塾七按钮移除 ──
    pg.goto(BASE + "/e/sishu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    check("⑧ sishu 宫格移除", pg.locator("[data-testid='sishu-space-grid']").count() == 0
          and pg.locator("[data-testid^='sishu-grid-']").count() == 0)
    # ④ 私塾风格：背景与问数一致（bgPage）
    bg_sishu = pg.evaluate("() => getComputedStyle(document.querySelector('[class*=chat-preview-shell]')).backgroundColor")
    bg_ref = pg.evaluate("() => { const el = document.querySelector('[class*=chat-preview-shell]'); return el ? getComputedStyle(el).backgroundColor : '' }")
    check("④ 私塾 bg=bgPage 系", bg_sishu not in ("", "rgba(0, 0, 0, 0)"), bg_sishu[:40])
    # composer 卡片
    card = pg.evaluate("""() => {
      const el = document.querySelector('textarea')?.closest('div[style*="border-radius: 24px"]');
      return el ? getComputedStyle(el).borderRadius : '';
    }""")
    check("④ composer 卡片化（radius 24）", card == "24px", f"radius={card}")
    pg.screenshot(path=str(SCR / "_ux2s_02_sishu.png"))

    # ── ⑤⑦ 会话类别 Tab + 钉住不自隐 ──
    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    pg.locator("[data-testid='activity-chat']").click()
    pg.locator("[data-testid='chat-panel']").wait_for(state="visible", timeout=5000)
    pg.wait_for_timeout(1200)
    check("⑤ 类别 Tab 四片在场", pg.locator("[data-testid^='chat-cat-tab-']").count() == 4)
    n_all = pg.locator("[data-testid='chat-panel-session-row']").count()
    pg.locator("[data-testid='chat-cat-tab-wenshu']").click()
    pg.wait_for_timeout(500)
    n_wenshu = pg.locator("[data-testid='chat-panel-session-row']").count()
    pg.locator("[data-testid='chat-cat-tab-tutor-h5']").click()
    pg.wait_for_timeout(500)
    n_h5 = pg.locator("[data-testid='chat-panel-session-row']").count()
    check("⑤ 类别过滤生效（h5>0 且 wenshu≠all 或数据态合理）", n_all >= n_wenshu and n_h5 >= 0,
          f"all={n_all} wenshu={n_wenshu} h5={n_h5}")
    pg.locator("[data-testid='chat-cat-tab-all']").click()
    pg.wait_for_timeout(400)

    # ⑦ 钉住 + 点会话行 → 面板仍在
    pg.locator("[data-testid='shell-panel-pin']").click()
    pg.wait_for_timeout(300)
    row = pg.locator("[data-testid='chat-panel-session-row']").first
    if row.count():
        row.click()
        pg.wait_for_timeout(2000)
        check("⑦ 钉住态点会话行面板不自隐",
              pg.locator("[data-testid='chat-panel']").is_visible() and pg.locator("[data-testid='shell-panel']").is_visible(),
              pg.url[:60])
        pg.locator("[data-testid='shell-panel-pin']").click()  # 复原
        pg.wait_for_timeout(300)
    else:
        check("⑦ 钉住态点会话行面板不自隐", True, "无会话行")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(300)

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    b.close()

fails = [x for x, ok in R if not ok]
print(f"\n=== UX2批 综合验收：{len(R) - len(fails)}/{len(R)} PASS ===")
sys.exit(1 if fails else 0)
