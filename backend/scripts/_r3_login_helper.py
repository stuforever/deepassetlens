# -*- coding: utf-8 -*-
"""Authentik 表单流登录助手（locator 穿透 shadow DOM，逐阶段）。
用法：from _r3_login_helper import form_login；token = form_login(pg, ident, password)"""
import time


def form_login(pg, ident: str, password: str, front: str = "http://localhost:23000"):
    """返回 access_token 或 None。pg 需为新 context（无登录态）。"""
    pg.evaluate("try { localStorage.clear(); sessionStorage.clear(); } catch {}")
    pg.goto(front + "/", timeout=60000, wait_until="domcontentloaded")
    # 等跳到 authentik 流
    for _ in range(10):
        if "9100" in pg.url or "authentik" in pg.url.lower():
            break
        time.sleep(1.5)
    # 阶段循环：每轮只处理一个可见未填字段，等流推进
    token = None
    for stage in range(16):
        if front.split("//")[1].split("/")[0] in pg.url and "auth" not in pg.url:
            # 回到前端（可能 callback 已换 token）
            pass
        # username 阶段
        u = pg.locator("input[name='username']").first
        if u.is_visible(timeout=1000):
            try:
                v = u.input_value()
            except Exception:
                v = ""
            if not v:
                u.fill(ident)
                time.sleep(0.6)
                _click_submit(pg)
                time.sleep(2.5)
                continue
        # password 阶段
        pw = pg.locator("input[name='password']").first
        if pw.is_visible(timeout=1000):
            try:
                v = pw.input_value()
            except Exception:
                v = ""
            if not v:
                pw.fill(password)
                time.sleep(0.6)
                _click_submit(pg)
                time.sleep(2.5)
                continue
        # 其他 submit 按钮（consent/continue）
        _click_submit(pg)
        time.sleep(2.5)
        if front in pg.url:
            break
    # 等 token 落 localStorage
    for _ in range(10):
        if front in pg.url:
            tok = pg.evaluate("""() => {
                for (const k of Object.keys(localStorage)) {
                    try { const v = JSON.parse(localStorage.getItem(k));
                          if (v && v.access_token) return v.access_token; } catch {}
                }
                return null; }""")
            if tok:
                return tok
        time.sleep(2)
    return None


def _click_submit(pg):
    for sel in ["button:has-text('Log in')", "button:has-text('Continue')",
                "button[type='submit']", "input[type='submit']"]:
        try:
            loc = pg.locator(sel).first
            if loc.is_visible(timeout=800):
                loc.click()
                return True
        except Exception:
            continue
    return False
