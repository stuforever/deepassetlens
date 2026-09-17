# -*- coding: utf-8 -*-
"""⑤R 权限三态验证（免登录：注入缓存 token）。
API 面：me×3 / grant(acadmin→student tutor use) / check 三态 / wenshu viewer 种子。
前端三态（token 注入 localStorage['tupu.oidc']）：
  student+use → 门户见 tutor 卡+功能页可达+后台被拦；
  student2    → 门户无卡+直连被拦；
  akadmin     → 后台可达。
前置：dt_baseline/tokens.json 已由 _r3_capture_token.py 抓好三账号 token。"""
import base64
import json
import math
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

SCR = Path(__file__).resolve().parent
TOKF = SCR / "dt_baseline" / "tokens.json"
RESULTS = []
FRONT = "http://localhost:23000"
BACK = "http://127.0.0.1:28000"


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


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


def bundle(tok: str) -> dict:
    payload = tok.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))
    exp = claims.get("exp", math.floor(time.time()) + 300)
    return {"access_token": tok, "token_type": "bearer",
            "expires_in": max(60, exp - math.floor(time.time())),
            "obtained_at": math.floor(time.time()) - 5}


def h(tok):
    return {"Authorization": f"Bearer {tok}"}


def main():
    tokens = json.loads(TOKF.read_text(encoding="utf-8"))
    st, ad, s2 = tokens["student"], tokens["akadmin"], tokens["student2"]

    # fixture 复位：清掉上一轮遗留的 student-tutor-user grant（保证 grant前=False 可复验）
    import pymysql
    _sub = json.loads((lambda p: base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))(
        st.split(".")[1]))
    conn = pymysql.connect(host="localhost", port=33066, user="root",
                           password="root", database="tupu")
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM auth_resource_acl WHERE resource_type='expert' AND resource_id='tutor' "
        "AND principal_type='user' AND principal_id=%s", (_sub["sub"],))
    conn.commit()
    print(f"fixture reset: deleted {cur.rowcount} stale grant row(s)", flush=True)
    conn.close()

    # ================= API 面 =================
    print("== API 面 ==", flush=True)
    me1 = requests.get(BACK + "/api/v1/auth/me", headers=h(st), timeout=15).json()
    check("student me=username+viewer",
          me1.get("data", {}).get("username") == "student"
          and "viewer" in (me1.get("data", {}).get("roles") or []),
          str(me1.get("data", {}).get("roles")))
    me2 = requests.get(BACK + "/api/v1/auth/me", headers=h(ad), timeout=15).json()
    check("akadmin me=admin", "admin" in (me2.get("data", {}).get("roles") or []),
          str(me2.get("data", {}).get("roles")))
    me3 = requests.get(BACK + "/api/v1/auth/me", headers=h(s2), timeout=15).json()
    check("student2 me=username+viewer",
          me3.get("data", {}).get("username") == "student2"
          and "viewer" in (me3.get("data", {}).get("roles") or []),
          str(me3.get("data", {}).get("roles")))

    c0 = requests.get(BACK + "/api/v1/auth/check",
                      params={"resource_type": "expert", "resource_id": "tutor", "action": "use"},
                      headers=h(st), timeout=15).json()
    check("grant前 student tutor use=False", c0.get("data", {}).get("allowed") is False)

    g = requests.post(BACK + "/api/v1/auth/grant", headers=h(ad), timeout=15,
                      json={"resource_type": "expert", "resource_id": "tutor",
                            "principal_type": "user", "principal_id": me1["data"]["sub"],
                            "actions": ["use"]})
    gj = g.json()
    check("admin grant student tutor use", gj.get("code") == 200, str(gj)[:90])

    c1 = requests.get(BACK + "/api/v1/auth/check",
                      params={"resource_type": "expert", "resource_id": "tutor", "action": "use"},
                      headers=h(st), timeout=15).json()
    check("grant后 student tutor use=True", c1.get("data", {}).get("allowed") is True)
    c2 = requests.get(BACK + "/api/v1/auth/check",
                      params={"resource_type": "expert", "resource_id": "tutor", "action": "manage"},
                      headers=h(st), timeout=15).json()
    check("student tutor manage=False（仅 use）", c2.get("data", {}).get("allowed") is False)
    c3 = requests.get(BACK + "/api/v1/auth/check",
                      params={"resource_type": "expert", "resource_id": "tutor", "action": "use"},
                      headers=h(s2), timeout=15).json()
    check("student2 tutor use=False（无 grant）", c3.get("data", {}).get("allowed") is False)
    c4 = requests.get(BACK + "/api/v1/auth/check",
                      params={"resource_type": "expert", "resource_id": "wenshu", "action": "use"},
                      headers=h(s2), timeout=15).json()
    check("wenshu viewer 种子仍可用", c4.get("data", {}).get("allowed") is True)

    # 匿名访问受保护面（无 token）
    r_anon = requests.get(BACK + "/api/v1/experts", timeout=15)
    check("匿名 /api/experts 401", r_anon.status_code == 401, str(r_anon.status_code))
    r_dev = requests.post(BACK + "/api/v1/auth/dev-login", timeout=15)
    check("dev-login 自证锚点 403", r_dev.status_code == 403, str(r_dev.status_code))

    # ================= 前端三态（token 注入） =================
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)

        def new_pg(tok):
            ctx = b.new_context(viewport={"width": 1440, "height": 900})
            ctx.add_init_script(
                f"try {{ localStorage.setItem('tupu.oidc', JSON.stringify({json.dumps(bundle(tok))})); }} catch {{}}")
            return ctx.new_page()

        # ---- student（use 已 grant）：门户见卡+功能页可达+后台被拦 ----
        print("== student 三态 ==", flush=True)
        pg = new_pg(st)
        nav(pg, FRONT + "/", 6)
        body = pg.evaluate("document.body.innerText || ''")
        check("student 门户见 tutor 卡", "私塾先生" in body, body[:70].replace("\n", "|"))
        nav(pg, FRONT + "/e/tutor/h5", 6)
        body2 = pg.evaluate("document.body.innerText || ''")
        url2 = pg.url
        check("student 功能页可达",
              "/e/tutor/h5" in url2 and ("学习" in body2 or "课件" in body2),
              url2[:60])
        pg.screenshot(path=str(SCR / "dt_baseline" / "r3_perm_student_learn.png"))
        nav(pg, FRONT + "/e/tutor/admin/mother-questions", 6)
        time.sleep(3)  # 守卫异步 check→重定向收尾（防瞬时渲染采样）
        body3 = pg.evaluate("document.body.innerText || ''")
        url3 = pg.url
        check("student 后台被拦（重定向离台或无管理内容）",
              "/e/tutor/admin" not in url3 or "母题库管理" not in body3,
              f"{url3[:55]} {'有管理内容' if '母题库管理' in body3 else '无管理内容'}")
        pg.screenshot(path=str(SCR / "dt_baseline" / "r3_perm_student_admguard.png"))

        # ---- student2（无 grant）：门户无卡+直连被拦 ----
        print("== student2 无 grant ==", flush=True)
        pg2 = new_pg(s2)
        nav(pg2, FRONT + "/", 6)
        body4 = pg2.evaluate("document.body.innerText || ''")
        check("student2 门户无 tutor 卡", "私塾先生" not in body4, body4[:60].replace("\n", "|"))
        nav(pg2, FRONT + "/e/tutor/h5", 6)
        time.sleep(3)  # use 守卫异步 check→重定向收尾
        body5 = pg2.evaluate("document.body.innerText || ''")
        url5 = pg2.url
        check("student2 直连功能页被拦（重定向离台或无学习内容）",
              "/e/tutor/h5" not in url5 or ("课件" not in body5 and "闯关" not in body5),
              f"{url5[:55]} {'有学习内容' if ('课件' in body5 or '闯关' in body5) else '无学习内容'}")
        pg2.screenshot(path=str(SCR / "dt_baseline" / "r3_perm_student2_guard.png"))
        # wenshu 共存：student2 仍可用 wenshu chat
        nav(pg2, FRONT + "/e/wenshu/chat", 6)
        body6 = pg2.evaluate("document.body.innerText || ''")
        check("student2 wenshu chat 可用（共存不串）",
              "wenshu" in pg2.url and ("提问" in body6 or "对话" in body6 or "发送" in body6),
              pg2.url[:60])

        # ---- akadmin：后台可达 ----
        print("== akadmin 后台 ==", flush=True)
        pg3 = new_pg(ad)
        nav(pg3, FRONT + "/e/tutor/admin/mother-questions", 6)
        body7 = pg3.evaluate("document.body.innerText || ''")
        check("akadmin 后台可达", "母题" in body7, pg3.url[:60])
        pg3.screenshot(path=str(SCR / "dt_baseline" / "r3_perm_admin_adm.png"))

        b.close()

    fails = [x for x in RESULTS if not x[1]]
    print(f"\n=== 权限三态验证：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
