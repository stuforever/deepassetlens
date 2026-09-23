# -*- coding: utf-8 -*-
"""批① Playwright 登录工具（Authentik 表单流，Enter 提交法——shadow DOM 内 click 不可靠）。
用法：
    from _pw_login_util import login_page
    pg = login_page(b)          # 返回已登录页面（storageState 缓存复用）
凭据沿用 _v4_perm_e2e.py：akadmin / deepassetlens_admin。
"""
import sys
import time
from pathlib import Path

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
STATE = SCR / "_pw_state.json"

IDENT = "akadmin"
PASSWORD = "deepassetlens_admin"


def _authentik_login(pg):
    """裸 context 走完整 OIDC 表单流（Enter 提交）。成功返回 True。"""
    pg.goto(BASE + "/", timeout=90000, wait_until="domcontentloaded")
    for _ in range(15):
        if "9100" in pg.url[:60]:
            break
        pg.wait_for_timeout(2000)
    if "9100" not in pg.url[:60]:
        return False  # 未跳流（可能已登录）
    # identification 阶段
    u = pg.locator("input[name='uidField'], input[name='username']").first
    u.wait_for(state="visible", timeout=20000)
    u.click()
    u.fill(IDENT)
    pg.wait_for_timeout(400)
    u.press("Enter")
    # password 阶段
    pw = pg.locator("input[name='password']").first
    pw.wait_for(state="visible", timeout=20000)
    pw.click()
    pw.fill(PASSWORD)
    pg.wait_for_timeout(400)
    pw.press("Enter")
    # 等回到前端且 root 挂载
    for _ in range(20):
        pg.wait_for_timeout(2000)
        if pg.url.startswith(BASE) and pg.evaluate(
            "() => (document.getElementById('root')||{}).innerHTML?.length > 100"
        ):
            return True
    return False


def login_page(b, force_login=False):
    """返回已登录页面。storageState 存在且有效则复用；否则完整登录并存档。"""
    if not force_login and STATE.exists():
        ctx = b.new_context(viewport={"width": 1600, "height": 900}, storage_state=str(STATE))
        pg = ctx.new_page()
        pg.goto(BASE + "/", timeout=90000, wait_until="domcontentloaded")
        pg.wait_for_timeout(6000)
        if pg.evaluate("() => (document.getElementById('root')||{}).innerHTML?.length > 100"):
            return pg
        ctx.close()
    ctx = b.new_context(viewport={"width": 1600, "height": 900})
    pg = ctx.new_page()
    ok = _authentik_login(pg)
    if not ok:
        ctx.close()
        raise RuntimeError("Authentik 登录失败（akadmin）")
    ctx.storage_state(path=str(STATE))
    return pg
