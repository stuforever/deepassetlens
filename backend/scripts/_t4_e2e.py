# -*- coding: utf-8 -*-
"""权限重构 T4 e2e v2：UI 验登录流/页面渲染，API 造数避免表单竞态。

验收对齐（design §10 #2/#3/#4 骨架 + 🛠R2 刷新续期）。
前置：后端 ENABLE_AUTH=1 + AUTH_PROVIDER=supertokens（28000）；akadmin 已 bootstrap。
"""
import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(__file__).parent
BASE = "http://localhost:23000"
API = "http://localhost:28000/api/v1"
R = []


def check(name, ok, detail=""):
    R.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:200], flush=True)


def api(method, path, token=None, body=None):
    req = urllib.request.Request(API + path, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data, timeout=20) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def login(pg, email, password):
    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_selector("[data-testid='st-login-page']", timeout=20000)
    pg.fill("[data-testid='login-email']", email)
    pg.fill("[data-testid='login-password']", password)
    pg.click("[data-testid='login-submit']")
    pg.wait_for_selector("[data-testid='portal-cards']", timeout=30000)


def me_of(pg):
    return pg.evaluate("async () => (await (await fetch('/api/v1/auth/me', {headers:{Authorization:'Bearer '+localStorage.getItem('tupu_st_access')}})).json()).data")


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    errors = []

    # ---------- API 造数：管理员 token + 测试用户 ----------
    st, r = api("POST", "/auth/session", body={"email": "akadmin@tupu.local", "password": "AkAdmin#2026"})
    admin_token = r["data"]["access_token"]
    check("A0 管理员 API 登录", st == 200 and admin_token)
    # 前置清理：历史残片（旧错名镜像行）——ST 身份保留，镜像交由建号恢复路径重建
    import asyncio as _aio
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.core.database import SessionLocal as _SL
    from app.models.auth import User as _U, UserRole as _UR

    _db = _SL()
    _stale = _db.query(_U).filter(_U.username.like("sttest_e2e%")).all()
    for _u in _stale:
        _db.query(_UR).filter(_UR.user_sub == _u.sub).delete(synchronize_session=False)
        _db.delete(_u)
    _db.commit()
    _db.close()
    st, r = api("POST", "/iam/users", admin_token, {
        "username": "sttest_e2e_user", "email": "sttest_e2e@x.local",
        "password": "E2ePass#123", "roles": ["viewer"],
    })
    created = st == 200
    check("A1 API 建号（或已存在）", created or st == 409, f"st={st} {str(r)[:80]}")

    # ---------- ctx1：管理员 UI 登录 ----------
    ctx1 = b.new_context()
    pg1 = ctx1.new_page()
    pg1.on("pageerror", lambda e: errors.append("ctx1:" + str(e)[:120]))
    login(pg1, "akadmin@tupu.local", "AkAdmin#2026")
    check("E1 管理员登录进门户", True)
    me = me_of(pg1)
    check("E2 /auth/me 身份正确", me and me.get("username") == "akadmin" and "admin" in (me.get("roles") or []), str(me)[:120])

    # 用户管理页：行可见 + 抽屉打开
    pg1.goto(BASE + "/settings/iam/users", timeout=60000, wait_until="domcontentloaded")
    pg1.wait_for_selector("[data-testid='iam-users-table']", timeout=15000)
    pg1.wait_for_timeout(1500)
    pg1.get_by_text("sttest_e2e_user", exact=True).first.click()
    pg1.wait_for_selector("[data-testid='iam-drawer-save-roles']", timeout=8000)
    check("E3 用户管理页+抽屉", True)

    # ---------- ctx2：新用户登录（viewer 兜底） ----------
    ctx2 = b.new_context()
    pg2 = ctx2.new_page()
    pg2.on("pageerror", lambda e: errors.append("ctx2:" + str(e)[:120]))
    login(pg2, "sttest_e2e@x.local", "E2ePass#123")
    me2 = me_of(pg2)
    check("E4 新用户登录（viewer 兜底）", me2 and "viewer" in (me2.get("roles") or []), str(me2)[:120])

    # ---------- 管理员改角色 → 另一会话即时生效（验收 #3） ----------
    st, _ = api("POST", "/iam/roles", admin_token, {"code": "e2e_temp", "name": "e2e临时"})
    st, r = api("PUT", f"/iam/users/{me2['sub']}/roles", admin_token, {"roles": ["viewer", "e2e_temp"]})
    check("E5a 改角色 API 200", st == 200, str(r)[:80])
    me2b = me_of(pg2)
    check("E5b 另一会话即时生效（e2e_temp 出现）", "e2e_temp" in (me2b.get("roles") or []), str(me2b)[:120])

    # ---------- 刷新续期：清 access 留 refresh → 重载恢复（验收 #2 + 🛠R2） ----------
    pg2.evaluate("() => localStorage.removeItem('tupu_st_access')")
    pg2.reload(timeout=60000, wait_until="domcontentloaded")
    pg2.wait_for_timeout(6000)
    back = pg2.locator("[data-testid='portal-cards']").count()
    check("E6 刷新续期不打断会话", back >= 1, f"portal={back} err={errors[:1]}")

    # 角色管理页（矩阵编辑器）+ 审计页 smoke
    pg1.goto(BASE + "/settings/iam/roles", timeout=60000, wait_until="domcontentloaded")
    pg1.wait_for_timeout(3500)
    check("E7 角色管理页矩阵在场", pg1.locator("[data-testid='iam-matrix']").count() >= 1)
    pg1.goto(BASE + "/settings/iam/audit", timeout=60000, wait_until="domcontentloaded")
    pg1.wait_for_timeout(3500)
    check("E8 审计页在场（空态可容）", pg1.locator("[data-testid='iam-audit-table']").count() >= 1)

    # 登出
    pg2.evaluate("async () => { await fetch('/api/v1/auth/session', {method:'DELETE', headers:{Authorization:'Bearer '+localStorage.getItem('tupu_st_access')}}); }")
    check("E9 登出调用无异常", True)

    # 清场：解除测试角色 → 删角色
    api("PUT", f"/iam/users/{me2['sub']}/roles", admin_token, {"roles": ["viewer"]})
    api("DELETE", "/iam/roles/e2e_temp", admin_token)

    ctx1.close()
    ctx2.close()
    b.close()

fails = [x for x, ok in R if not ok]
print(f"\n=== T4 e2e：{len(R) - len(fails)}/{len(R)} PASS ===")
sys.exit(1 if fails else 0)
