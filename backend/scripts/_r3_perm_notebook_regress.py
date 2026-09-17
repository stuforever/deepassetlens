# -*- coding: utf-8 -*-
"""回归：student(use granted) 访问 /e/tutor/notebook——题库页在 auth=1+use 守卫下仍完整渲染。"""
import json
import math
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SCR = Path(__file__).resolve().parent
TOKF = SCR / "dt_baseline" / "tokens.json"
FRONT = "http://localhost:23000"


def nav(pg, url, wait_s=6):
    try:
        pg.goto(url, timeout=60000, wait_until="domcontentloaded")
    except Exception as e:
        if "interrupted by another navigation" in str(e):
            time.sleep(3)
            try:
                pg.goto(url, timeout=60000, wait_until="domcontentloaded")
            except Exception:
                pass
        else:
            raise
    time.sleep(wait_s)


tok = json.loads(TOKF.read_text(encoding="utf-8"))["student"]
payload = tok.split(".")[1]
payload += "=" * (-len(payload) % 4)
import base64  # noqa: E402
exp = json.loads(base64.urlsafe_b64decode(payload)).get("exp", math.floor(time.time()) + 300)
bundle = {"access_token": tok, "token_type": "bearer",
          "expires_in": max(60, exp - math.floor(time.time())),
          "obtained_at": math.floor(time.time()) - 5}

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(
        f"try {{ localStorage.setItem('tupu.oidc', JSON.stringify({json.dumps(bundle)})); }} catch {{}}")
    pg = ctx.new_page()
    nav(pg, FRONT + "/e/tutor/notebook", 6)
    body = pg.evaluate("document.body.innerText || ''")
    url = pg.url
    ok = "/e/tutor/notebook" in url and "题库" in body and "总计" in body
    print(f"{'PASS' if ok else 'FAIL'}  notebook use 守卫下可达且完整  url={url[:60]} "
          f"题库={'题库' in body} 总计={'总计' in body}")
    pg.screenshot(path=str(SCR / "dt_baseline" / "r3_perm_student_notebook.png"))
    b.close()
    sys.exit(0 if ok else 1)
