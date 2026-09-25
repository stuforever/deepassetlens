# -*- coding: utf-8 -*-
"""UX3修 对拍：BUG1 门户卡→新会话欢迎页；BUG3 私塾风格收敛=问数同骨架；sishu 发送链路回归。

断言账：
B1a 首页门户卡在场（刷新后种子历史会话在 localStorage）
B1b 点问数卡 → /e/wenshu/chat（?new=1 已清）
B1c 历史消息未渲染（不再进历史对话）
B1d 问数色条=蓝 + 欢迎页主视觉在场
B3a 私塾色条=琥珀 #D97706（ExpertChat slug-aware）
B3b 私塾功能宫格在场（sishu-space-grid）
B3c today-panel 统计胶囊（待复习）
B3d 旧 TutorHomeChat 欢迎语「下午好」退场
S1  sishu 发送走 freeplan stream
S2  请求带 expert_id=sishu
S3  回复落定（loading 退场）
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

    # ---------- BUG3: 私塾风格收敛 ----------
    pg.goto(BASE + "/e/sishu/chat?new=1", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(7000)
    bar2 = pg.locator("[data-testid='space-color-bar']")
    if bar2.count():
        bg2 = bar2.first.evaluate("el => getComputedStyle(el).backgroundColor")
        check("B3a 私塾色条=琥珀#D97706", "217, 119, 6" in bg2, bg2)
    else:
        check("B3a 私塾色条=琥珀#D97706", False, "bar not found")
    grid = pg.locator("[data-testid='sishu-space-grid']")
    check("B3b 私塾功能宫格在场", grid.count() >= 1)
    due = pg.locator("text=待复习")
    check("B3c today-panel 统计胶囊", due.count() >= 1, f"hits={due.count()}")
    old_title = pg.locator("text=下午好")
    check("B3d 旧 TutorHomeChat 欢迎语退场", old_title.count() == 0, f"hits={old_title.count()}")

    # ---------- sishu 发送链路（freeplan stream + expert_id=sishu）----------
    req_info = {}

    def on_req(req):
        if "chat/freeplan/stream" in req.url:
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
        for _ in range(120):
            pg.wait_for_timeout(1000)
            if pg.evaluate("() => !document.body.innerText.includes('正在思考...')"):
                ok_resp = True
                break
        check("S1 sishu 发送走 freeplan stream", ok_req, str(req_info.get("url", ""))[:80])
        body = req_info.get("body", "")
        check("S2 请求带 expert_id=sishu", "sishu" in body, body[:140].replace("\n", " "))
        check("S3 回复落定（loading 退场）", ok_resp)
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
