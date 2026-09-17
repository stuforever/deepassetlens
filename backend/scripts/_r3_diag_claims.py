# -*- coding: utf-8 -*-
"""截图式登录诊断（每阶段留证）。"""
import base64
import json
import sys
import time

import requests
sys.path.insert(0, "scripts")
from playwright.sync_api import sync_playwright
from _r3_perm_e2e import nav, FRONT  # noqa: E402

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    try:
        pg.evaluate("try { localStorage.clear(); sessionStorage.clear(); } catch {}")
    except Exception:
        pass
    nav(pg, FRONT + "/", 8)
    print("t0 url:", pg.url[:70])
    for k in range(6):
        pg.screenshot(path=f"scripts\\dt_baseline\\r3_d{k}.png")
        has_u = False
        for f in pg.frames:
            try:
                if f.locator("input[name='username']").count():
                    has_u = True
            except Exception:
                pass
        print(f"t{k} url={pg.url[:60]} has_username_input={has_u}")
        if "23000" in pg.url and "auth/callback" not in pg.url and k > 0 and not has_u:
            print("frontend reached (SSO direct?)")
            break
        time.sleep(3)
    # 若在 9100 且有输入：走一次键入
    hit = False
    for f in pg.frames:
        try:
            if f.locator("input[name='username']").count():
                hit = True
        except Exception:
            pass
    if hit:
        pg.mouse.click(720, 358)
        time.sleep(0.5)
        pg.keyboard.type("akadmin", delay=30)
        pg.keyboard.press("Enter")
        time.sleep(4)
        pg.screenshot(path=r"scripts\dt_baseline\r3_d7.png")
        print("after user:", pg.url[:70])
        pg.keyboard.type("deepassetlens_admin", delay=30)
        pg.keyboard.press("Enter")
        time.sleep(5)
        pg.screenshot(path=r"scripts\dt_baseline\r3_d8.png")
        print("after pw:", pg.url[:70])
    time.sleep(3)
    print("final:", pg.url[:70])
    tok = pg.evaluate("""() => {
        for (const k of Object.keys(localStorage)) {
            try { const v = JSON.parse(localStorage.getItem(k));
                  if (v && v.access_token) return v.access_token; } catch {}
        }
        return null; }""")
    print("token:", "GOT" if tok else "NONE")
    b.close()

if tok:
    import base64
    payload = tok.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))
    print("claims keys:", sorted(claims.keys()))
    print("groups:", claims.get("groups"))
    me = requests.get("http://127.0.0.1:28000/api/v1/auth/me",
                      headers={"Authorization": f"Bearer {tok}"}, timeout=15).json()
    print("me:", json.dumps(me.get("data", {}), ensure_ascii=False)[:220])
