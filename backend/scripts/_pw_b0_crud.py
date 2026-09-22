# -*- coding: utf-8 -*-
"""批⓪ 补充对拍：ChatPanel 会话重命名/删除 全链路实拍（坑册：换壳批必须对拍会话 CRUD）。
- 重命名：hover → ⋯ → 重命名 → 内联 Input → Enter → 行标题更新
- 删除：hover → ⋯ → 删除 → Modal.confirm → 行消失
附带清理基线 C 残留的「新对话」测试会话。"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
ok_all = True


def check(name, ok, detail=""):
    global ok_all
    ok_all = ok_all and bool(ok)
    print(("GREEN " if ok else "RED   ") + name + "  " + str(detail)[:110], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1600, "height": 900})
    # 造平台会话：门户发一条消息（sendQuestion 即建会话；CRUD 后删除，自清理）
    pg.goto(BASE + "/", timeout=90000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    pg.locator("[data-testid='newchat-composer'] textarea").fill("批⓪CRUD临时问题")
    pg.locator("[data-testid='newchat-composer'] textarea").press("Enter")
    pg.wait_for_timeout(4000)  # 落 /e/wenshu/chat?q=... 自动发出 → 会话已建
    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    pg.locator("[data-testid='activity-chat']").click()
    pg.wait_for_timeout(1200)

    # ── 重命名（平台「批⓪CRUD临时问题」会话） ──
    row = pg.locator("[data-testid='chat-panel-session-row']").first  # 刚建的会话必最新=首行
    row.hover()
    pg.wait_for_timeout(400)
    row.locator("[data-testid='chat-panel-row-more']").click()
    pg.wait_for_timeout(600)
    pg.locator(".ant-dropdown-menu >> text=重命名").click()
    pg.wait_for_timeout(500)
    inp = pg.locator("[data-testid='chat-panel-rename-input']")
    renamed = False
    if inp.count() > 0:
        inp.fill("批⓪CRUD对拍会话")
        inp.press("Enter")
        pg.wait_for_timeout(1200)
        panel = pg.locator("[data-testid='chat-panel']").inner_text()
        renamed = "批⓪CRUD对拍会话" in panel
    check("会话重命名（内联编辑生效）", renamed)

    # ── 删除（重命名后的会话） ──
    row2 = pg.locator("[data-testid='chat-panel-session-row']").filter(has_text="批⓪CRUD对拍会话").first
    row2.hover()
    pg.wait_for_timeout(400)
    row2.locator("[data-testid='chat-panel-row-more']").click()
    pg.wait_for_timeout(600)
    pg.locator(".ant-dropdown-menu >> text=删除").click()
    pg.wait_for_timeout(600)
    # Modal.confirm（坑册：Modal 断言用状态而非 DOM 存在性）
    confirm_btn = pg.locator(".ant-modal-confirm-btns button.ant-btn-dangerous, .ant-modal-confirm-btns .ant-btn-primary").first
    deleted = False
    if confirm_btn.count() > 0:
        confirm_btn.click()
        pg.wait_for_timeout(1500)
        panel = pg.locator("[data-testid='chat-panel']").inner_text()
        deleted = "批⓪CRUD对拍会话" not in panel
    check("会话删除（确认后行消失）", deleted)

    pg.screenshot(path=str(SCR / "_pw_b0_crud.png"))
    b.close()

print("\n=== 批⓪ CRUD 对拍：%s ===" % ("全绿" if ok_all else "存在红项"))
sys.exit(0 if ok_all else 1)
