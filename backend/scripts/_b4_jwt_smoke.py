# -*- coding: utf-8 -*-
"""⑥-2a B-4 步骤 2：JWT 冒烟——真实 OIDC 全链（Authentik 表单→callback→token→fetchMe）。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright

SCR = Path(__file__).parent
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    # 1. 打开前端 → AuthGate 无 token → 跳 Authentik
    pg.goto("http://localhost:23000/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    check("跳转 Authentik 登录页", "9100" in pg.url or "authentik" in pg.url.lower() or pg.query_selector("input[name='username']") is not None, pg.url[:80])
    # 2. Authentik 表单登录（bootstrap 凭据）
    try:
        inputs = pg.locator("input").all()
        print("DEBUG inputs:", [(i.get_attribute("name"), i.get_attribute("type")) for i in inputs][:6])
        pg.fill("input[name='username']", "admin@deepassetlens.local")
        pg.locator("button[type='submit']").first.click()
        # 多阶段轮询：identification→password→(consent)→authorize→redirect（shadow DOM 内推进）
        for i in range(12):
            pg.wait_for_timeout(3000)
            if "23000" in pg.url:
                break
            try:
                btn = pg.locator("button[type='submit']")
                if btn.count() and btn.first.is_visible():
                    pw2 = pg.locator("input[name='password']")
                    if pw2.count() and pw2.first.is_visible() and not (pw2.first.input_value()):
                        pw2.first.fill("deepassetlens_admin")
                    btn.first.click()
            except Exception:
                pass
        print("DEBUG 多阶段后 URL:", pg.url[:100])
    except Exception as e:
        print("DEBUG 表单异常:", str(e)[:120])
        pg.screenshot(path=str(SCR / "_diag_b4_form.png"))
    # 3. 回跳 callback→token 交换→ready
    for _ in range(10):
        if "auth/callback" in pg.url or "23000" in pg.url:
            break
        pg.wait_for_timeout(2000)
    check("回跳 callback/前端", "23000" in pg.url, pg.url[:80])
    pg.wait_for_timeout(6000)
    # 4. fetchMe→用户名显示（非 anonymous）
    body = pg.inner_text("body")
    check("登录态用户显示（非 anonymous）", "akadmin" in body or "deepassetlens" in body.lower(), body[:120].replace("\n", "|"))
    # 5. token 已落 localStorage（AuthGate ready）
    has_token = pg.evaluate("() => Object.keys(localStorage).some(k => k.includes('token') || k.includes('auth'))")
    check("token 落 localStorage", bool(has_token))
    pg.screenshot(path=str(SCR / "_pw_b4_jwt.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== B-4 JWT 冒烟：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
