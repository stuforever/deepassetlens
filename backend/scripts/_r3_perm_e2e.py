# -*- coding: utf-8 -*-
"""⑤R 权限全链 e2e（auth=1）：默认账号登录→grant 分配→三态实测（串行）。
A student(无 grant)→门户无 tutor 卡+check false；B admin 分配 use→check true+门户见卡+
功能页可达+后台拦；C akadmin(admin)→后台可达；D student2 无 grant 直连被拦；
E wenshu viewer 种子兼容。
登录法=坐标+键盘真实输入（新版 authentik UI 表单在 shadow DOM 渲染、DOM input 为
-2000 屏外镜像，locator fill 不可达可见层）。
每个登录用全新 browser context（SSO cookie 隔离——否则 authorize 复用上一账号
会话静默发错身份 token，B 段曾拿 student token 调 grant 报 auth.write 拒绝）。"""
import base64
import json
import sys
import time
from pathlib import Path

import requests
from playwright.sync_api import sync_playwright

SCR = Path(__file__).resolve().parent / "dt_baseline"
RESULTS = []
FRONT = "http://localhost:23000"
BACK = "http://127.0.0.1:28000"


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


def jwt_sub(token: str) -> str:
    try:
        p = token.split(".")[1]
        p += "=" * (-len(p) % 4)
        return json.loads(base64.urlsafe_b64decode(p)).get("sub", "")
    except Exception:
        return ""


def nav(pg, url, wait_s=6):
    """容错 goto：被 in-flight 登录跳转打断→等 3s 重试一次。"""
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


def login(b, ident, password, _tries=2):
    """独立 context 内走 Authentik 表单流（SSO cookie 隔离）。返回 (page, token)。
    失败重试：旧 context 保留不关（避免返回已关 page），浏览器退出时统一回收。"""
    pg = None
    for attempt in range(_tries):
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()
        tok = _login_once(pg, ident, password)
        if tok:
            return pg, tok
        print(f"  [login retry {attempt + 1}] {ident}", flush=True)
    return pg, None


def _login_once(pg, ident, password):
    try:
        pg.evaluate("try { localStorage.clear(); sessionStorage.clear(); } catch {}")
    except Exception:
        pass
    nav(pg, FRONT + "/", 8)
    # 等流页出现（主帧或子帧有 username input）或已在 9100
    for _ in range(10):
        hit = False
        for f in pg.frames:
            try:
                if f.locator("input[name='username']").count():
                    hit = True
                    break
            except Exception:
                pass
        if hit or "9100" in pg.url:
            break
        time.sleep(2)
    # 阶段1: 用户名
    pg.mouse.click(720, 358)
    time.sleep(0.5)
    pg.keyboard.type(ident, delay=30)
    time.sleep(0.4)
    pg.keyboard.press("Enter")
    time.sleep(4)
    # 阶段2: 密码（卡片自动聚焦）
    pg.keyboard.type(password, delay=30)
    time.sleep(0.4)
    pg.keyboard.press("Enter")
    # 等回前端+token
    tok = None
    for _ in range(15):
        if FRONT in pg.url and "9100" not in pg.url:
            time.sleep(3)
            tok = pg.evaluate("""() => {
                for (const k of Object.keys(localStorage)) {
                    try { const v = JSON.parse(localStorage.getItem(k));
                          if (v && v.access_token) return v.access_token; } catch {}
                }
                return null; }""")
            if tok:
                break
        time.sleep(2)
    # 等 callback 收尾
    for _ in range(10):
        if "auth/callback" not in pg.url:
            break
        time.sleep(1.5)
    time.sleep(2)
    return tok


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)

        # ---- A: student 首登（自动开户）+ grant 前态 ----
        print("== A student 首登 ==", flush=True)
        pg, st_tok = login(b, "student", "Tupu_student_2026")
        check("student 表单流登录", bool(st_tok), (pg.url if pg else "")[:60])
        st_sub = jwt_sub(st_tok) if st_tok else ""
        check("student JWT sub 解析", bool(st_sub), st_sub[:20])
        me = requests.get(BACK + "/api/v1/auth/me",
                          headers={"Authorization": f"Bearer {st_tok}"}, timeout=15).json()
        check("student 自动开户(me)", me.get("data", {}).get("username") == "student",
              str(me.get("data", {}).get("roles")))
        chk = requests.get(BACK + "/api/v1/auth/check",
                           params={"resource_type": "expert", "resource_id": "tutor", "action": "use"},
                           headers={"Authorization": f"Bearer {st_tok}"}, timeout=15).json()
        check("grant 前 check tutor use=False", chk.get("data", {}).get("allowed") is False)
        nav(pg, FRONT + "/", 5)
        body = pg.evaluate("document.body.innerText || ''")
        check("grant 前门户无 tutor 卡", "私塾先生" not in body, body[:70].replace("\n", "|"))

        # ---- B: akadmin 登录→grant student use ----
        print("== B admin 分配 ==", flush=True)
        pg2, ad_tok = login(b, "akadmin", "deepassetlens_admin")
        check("akadmin 表单流登录", bool(ad_tok), (pg2.url if pg2 else "")[:60])
        ad_me = requests.get(BACK + "/api/v1/auth/me",
                             headers={"Authorization": f"Bearer {ad_tok}"}, timeout=15).json()
        check("akadmin 角色=admin", "admin" in (ad_me.get("data", {}).get("roles") or []),
              str(ad_me.get("data", {}).get("roles")))
        g = requests.post(BACK + "/api/v1/auth/grant",
                          headers={"Authorization": f"Bearer {ad_tok}"},
                          json={"resource_type": "expert", "resource_id": "tutor",
                                "principal_type": "user", "principal_id": st_sub,
                                "actions": ["use"]}, timeout=15).json()
        check("grant student tutor use", g.get("code") == 200, str(g)[:90])

        # ---- C: student 再验（API 面+前端三态） ----
        print("== C student 三态 ==", flush=True)
        chk2 = requests.get(BACK + "/api/v1/auth/check",
                            params={"resource_type": "expert", "resource_id": "tutor", "action": "use"},
                            headers={"Authorization": f"Bearer {st_tok}"}, timeout=15).json()
        check("grant 后 check tutor use=True", chk2.get("data", {}).get("allowed") is True)
        chk3 = requests.get(BACK + "/api/v1/auth/check",
                            params={"resource_type": "expert", "resource_id": "tutor", "action": "manage"},
                            headers={"Authorization": f"Bearer {st_tok}"}, timeout=15).json()
        check("student manage 仍=False（仅 use）", chk3.get("data", {}).get("allowed") is False)

        pg3, st_tok2 = login(b, "student", "Tupu_student_2026")
        check("student 重登录", bool(st_tok2), (pg3.url if pg3 else "")[:60])
        nav(pg3, FRONT + "/", 5)
        body2 = pg3.evaluate("document.body.innerText || ''")
        check("grant 后门户见 tutor 卡", "私塾先生" in body2, body2[:70].replace("\n", "|"))
        nav(pg3, FRONT + "/e/tutor/h5", 5)
        body3 = pg3.evaluate("document.body.innerText || ''")
        url3 = pg3.url
        check("student 功能页可达(tutor 卡守卫放行)",
              "/e/tutor/h5" in url3 and "学习" in body3, url3[:60])
        nav(pg3, FRONT + "/e/tutor/admin/mother-questions", 5)
        body_adm = pg3.evaluate("document.body.innerText || ''")
        check("student 后台被守卫拦(非母题库管理内容)",
              "母题库管理" not in body_adm, pg3.url[:60])
        pg3.screenshot(path=str(SCR / "r3_perm_student_admin_guard.png"))

        # ---- D: akadmin 前端后台可达 ----
        print("== D admin 后台 ==", flush=True)
        pg4, ad_tok2 = login(b, "akadmin", "deepassetlens_admin")
        check("akadmin 重登录", bool(ad_tok2), (pg4.url if pg4 else "")[:60])
        nav(pg4, FRONT + "/e/tutor/admin/mother-questions", 6)
        body4 = pg4.evaluate("document.body.innerText || ''")
        check("admin 后台可达", "母题" in body4, pg4.url[:60])
        pg4.screenshot(path=str(SCR / "r3_perm_admin_admin.png"))

        # ---- E: student2（无 grant）直连被拦 ----
        print("== E student2 无 grant ==", flush=True)
        pg5, s2_tok = login(b, "student2", "Tupu_student_2026")
        check("student2 登录", bool(s2_tok), (pg5.url if pg5 else "")[:60])
        nav(pg5, FRONT + "/", 5)
        body5 = pg5.evaluate("document.body.innerText || ''")
        check("student2 门户无 tutor 卡", "私塾先生" not in body5, body5[:60].replace("\n", "|"))
        nav(pg5, FRONT + "/e/tutor/h5", 5)
        body6 = pg5.evaluate("document.body.innerText || ''")
        check("student2 直连功能页被拦(不可见 tutor 页内容)",
              "课件" not in body6 and "闯关" not in body6, pg5.url[:60])
        pg5.screenshot(path=str(SCR / "r3_perm_student2_guard.png"))

        # ---- F: wenshu 兼容（viewer 种子） ----
        chk4 = requests.get(BACK + "/api/v1/auth/check",
                            params={"resource_type": "expert", "resource_id": "wenshu", "action": "use"},
                            headers={"Authorization": f"Bearer {s2_tok}"}, timeout=15).json()
        check("wenshu viewer 种子仍可用", chk4.get("data", {}).get("allowed") is True)

        b.close()

    fails = [x for x in RESULTS if not x[1]]
    print(f"\n=== 权限全链 e2e：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
