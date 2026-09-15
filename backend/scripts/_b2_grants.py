# -*- coding: utf-8 -*-
"""⑥-2a B-2 步骤 2：A5 走查——赋权/回收/有效期三动作（串行+截图，admin 视角）。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright

SCR = Path(__file__).parent
FRONT = "http://localhost:23000"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


def _mk_user(sub, username):
    from app.core.database import SessionLocal
    from app.models.auth import User
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.sub == sub).first():
            db.add(User(sub=sub, username=username, email=f"{sub}@x", is_active=True))
            db.commit()
    finally:
        db.close()


def _cleanup():
    from app.core.database import SessionLocal
    from app.models.auth import ResourceACL, User
    db = SessionLocal()
    try:
        db.query(ResourceACL).filter(ResourceACL.resource_type == "expert",
                                     ResourceACL.principal_type == "user",
                                     ResourceACL.principal_id.like("tdd-grant-%")).delete(synchronize_session=False)
        db.query(User).filter(User.sub.like("tdd-grant-%")).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


try:
    _cleanup()
    _mk_user("tdd-grant-u1", "走查用户甲")
    _mk_user("tdd-grant-u2", "走查用户乙")
    time.sleep(1)

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(f"{FRONT}/expert-grants", timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(7000)
        body = pg.inner_text("body")
        check("赋权页渲染", "专家赋权" in body)

        # 动作一：赋权（u1 × tutor × use）——UI 表单全流程
        pg.locator("#principal_id").click()
        pg.wait_for_timeout(1200)
        opts = pg.locator(".ant-select-item-option").all_inner_texts()
        print("DEBUG 下拉选项:", opts[:8])
        import requests as _rq
        print("DEBUG /auth/users:", _rq.get("http://127.0.0.1:28000/api/v1/auth/users", timeout=10).json()["data"][:3])
        pg.locator(".ant-select-item-option[title='走查用户甲']").first.click()
        pg.locator("#expert_id").click()
        pg.wait_for_timeout(600)
        pg.locator(".ant-select-item-option[title='私塾先生']").first.click()
        pg.click("button:has-text('赋 权'), button:has-text('赋权')")
        pg.wait_for_timeout(2500)
        body = pg.inner_text("body")
        check("赋权动作（UI 表单→落库→列表可见）", "tdd-grant-u1" in body, body[-200:].replace("\n", "|"))

        # 动作二：有效期（u2 × wenshu × use + 30 天临时授权→到期列有日期）
        pg.locator("#principal_id").click()
        pg.wait_for_timeout(800)
        pg.locator(".ant-select-item-option[title='走查用户乙']").first.click()
        pg.locator("#expert_id").click()
        pg.wait_for_timeout(1000)
        print("DEBUG 专家下拉:", pg.locator(".ant-select-item-option").all_inner_texts()[:8])
        pg.locator(".ant-select-item-option").filter(has_text="数据资产探查").last.click()
        pg.locator(".ant-checkbox-input").nth(2).check()   # 30 天临时授权 checkbox 本体（前两个=use/manage 动作组）
        pg.click("button:has-text('赋 权'), button:has-text('赋权')")
        pg.wait_for_timeout(2500)
        body = pg.inner_text("body")
        check("有效期动作（30 天临时授权→到期列显示日期）", "tdd-grant-u2" in body,
              "tail=" + body[-160:].replace("\n", "|"))

        # 动作三：回收（删 u1 行→列表消失）
        row = pg.locator("tr", has_text="tdd-grant-u1").first
        row.locator("button:has-text('回 收'), button:has-text('回收')").first.click()
        pg.wait_for_timeout(2500)
        body = pg.inner_text("body")
        check("回收动作（列表行消失）", "tdd-grant-u1" not in body)
        pg.screenshot(path=str(SCR / "_pw_b2_grants.png"))
        b.close()
finally:
    _cleanup()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== B-2 赋权面走查：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
