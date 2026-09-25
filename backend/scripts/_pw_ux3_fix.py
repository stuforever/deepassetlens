# -*- coding: utf-8 -*-
"""UX3修 对拍：BUG1 门户卡→新会话欢迎页；BUG3 私塾风格收敛=问数同骨架；sishu 发送链路回归。

断言账：
B1a 首页门户卡在场（刷新后种子历史会话在 localStorage）
B1b 点问数卡 → /e/wenshu/chat（?new=1 已清）
B1c 历史消息未渲染（不再进历史对话）
B1d 问数色条=蓝 + 欢迎页主视觉在场
B3a 私塾色条=琥珀 #D97706（TutorHomeChat 页头色条）
B3b 功能还原·学情上下文右栏（sishu-trust-panel）
B3c 统计胶囊·待复习（today-panel）
B3e 统计胶囊·连续学习
B3f 建议卡（问数同款两列卡）
B3g 衬线旧欢迎题退场（风格收敛）
S1  sishu 发送走桥 POST /api/v2/skills/capability
S2  请求带 skill_code=sishu/*
S3  回复落定（停止生成退场）
零 pageerror
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(__file__).parent
BASE = "http://localhost:23000"
R = []


def check(name, ok, detail=""):
    R.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:200], flush=True)


SEED = json.dumps([{
    "id": "ux3fix-hist", "title": "历史会话UX3修", "expertId": "wenshu",
    "messages": [{"id": "m1", "role": "user", "text": "历史会话标记消息XYZABC", "payload": {}}],
    "confirmed": {}, "flags": {}, "thinkStream": [], "pendingCandidates": [],
    "finalTokens": [], "createdAt": 1700000000000,
}], ensure_ascii=False)

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(SCR))
    from _pw_login_util import login_page
    pg = login_page(b)
    pg.set_viewport_size({"width": 1920, "height": 1080})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)[:100]))

    # ---------- BUG1: 首页刷新 → 点问数 → 欢迎页而非历史对话 ----------
    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    pg.evaluate("(s) => localStorage.setItem('di_sessions_freeplan_v1', s)", SEED)
    pg.reload(timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    cards = pg.locator("[data-testid='portal-card-wenshu']")
    check("B1a 首页门户卡在场", cards.count() >= 1)
    if cards.count():
        cards.first.click()
        pg.wait_for_timeout(4000)
        url = pg.url
        check("B1b 落点 /e/wenshu/chat（?new=1 已清）", "/e/wenshu/chat" in url and "new=1" not in url, url[:90])
        hist = pg.locator("text=历史会话标记消息XYZABC")
        check("B1c 历史消息未渲染", hist.count() == 0, f"hits={hist.count()}")
        bar = pg.locator("[data-testid='space-color-bar']")
        if bar.count():
            bg = bar.first.evaluate("el => getComputedStyle(el).backgroundColor")
            check("B1d 问数色条=蓝", "37, 99, 235" in bg, bg)
        else:
            check("B1d 问数色条=蓝", False, "bar not found")
        welcome = pg.locator("text=数据资产探查")
        check("B1d 欢迎页主视觉在场", welcome.count() >= 1, f"hits={welcome.count()}")
        pg.screenshot(path=str(SCR / "_ux3fix_wenshu.png"))

    # ---------- BUG3: 私塾功能还原 + 风格收敛（TutorHomeChat 组件内做风格） ----------
    pg.goto(BASE + "/e/sishu/chat?new=1", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(7000)
    bar2 = pg.locator("[data-testid='space-color-bar']")
    if bar2.count():
        bg2 = bar2.first.evaluate("el => getComputedStyle(el).backgroundColor")
        check("B3a 私塾色条=琥珀#D97706", "217, 119, 6" in bg2, bg2)
    else:
        check("B3a 私塾色条=琥珀#D97706", False, "bar not found")
    trust = pg.locator("[data-testid='sishu-trust-panel']")
    check("B3b 功能还原·学情上下文右栏", trust.count() >= 1)
    check("B3c 统计胶囊·待复习", pg.locator("text=待复习").count() >= 1)
    check("B3e 统计胶囊·连续学习", pg.locator("[data-testid='sishu-capsule-连续学习']").count() >= 1)
    check("B3f 建议卡（问数同款）", pg.locator("[data-testid='sishu-suggest-0']").count() >= 1)
    serif = pg.locator("h1.font-serif")
    check("B3g 衬线旧欢迎题退场", serif.count() == 0, f"hits={serif.count()}")

    # ---------- sishu 发送链路（桥 POST /api/v2/skills/capability，skill_code=sishu/*）----------
    req_info = {}

    def on_req(req):
        if "skills/capability" in req.url:
            req_info["url"] = req.url
            try:
                req_info["body"] = req.post_data or ""
            except Exception:
                req_info["body"] = ""

    pg.on("request", on_req)
    ta = pg.locator("textarea").first
    if ta.count():
        ta.click()
        ta.fill("你好")
        ta.press("Enter")
        ok_req = False
        for _ in range(30):
            pg.wait_for_timeout(1000)
            if req_info.get("url"):
                ok_req = True
                break
        ok_resp = False
        for _ in range(150):
            pg.wait_for_timeout(1000)
            if pg.evaluate("() => !document.body.innerText.includes('停止生成')"):
                ok_resp = True
                break
        check("S1 sishu 发送走桥 capability 流", ok_req, str(req_info.get("url", ""))[:80])
        body = req_info.get("body", "")
        check("S2 请求带 skill_code=sishu/*", '"skill_code"' in body and "sishu" in body, body[:140].replace("\n", " "))
        check("S3 回复落定（停止生成退场）", ok_resp)
        pg.screenshot(path=str(SCR / "_ux3fix_sishu.png"))
    else:
        check("S1 sishu 发送链路", False, "textarea not found")
        check("S2 请求带 expert_id=sishu", False, "no request")
        check("S3 回复落定（loading 退场）", False, "no send")

    check("零 pageerror", len(errors) == 0, str(errors[:2]))
    b.close()

fails = [x for x, ok in R if not ok]
print(f"\n=== UX3修 对拍：{len(R) - len(fails)}/{len(R)} PASS ===")
sys.exit(1 if fails else 0)
