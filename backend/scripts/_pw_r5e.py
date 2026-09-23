# -*- coding: utf-8 -*-
"""R5批⑤ 对拍（复用批④ 页面流的新鲜运行——client-cache 归属校验改造后：ChatPanel 会话列表经 session-api withClientCache、伙伴列表经 knowledge/llm-options 缓存面）:
批④：partners-api json()/personas-api asJson 空体兜底 + session-api 401 门控。

实拍两条活路径：伙伴列表（partners-api json() 成功路径）、ChatPanel h5 会话行
（session-api listSessions 经 expectJson——auth=ON 下 runtimeAuthEnabled=true，
门控放行跳转逻辑不变；列表正常返回=非 401 主路径无回归）。
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:180], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:120]))

    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)

    # ① 伙伴/推送页（partners-api json() 主路径）
    pg.locator("[data-testid='activity-console']").click()
    pg.locator("[data-testid='nav-item-e:sishu:partners']").click()
    pg.wait_for_timeout(2500)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)
    body = pg.inner_text("body")
    check("伙伴页实拉数据", ("伙伴" in body), body[:60].replace("\n", " "))

    # ② ChatPanel h5 会话行（session-api listSessions 主路径）
    pg.locator("[data-testid='activity-chat']").click()
    pg.locator("[data-testid='chat-panel']").wait_for(state="visible", timeout=5000)
    pg.wait_for_timeout(1200)
    chat_txt = pg.locator("[data-testid='chat-panel']").inner_text()
    check(
        "ChatPanel 渲染（h5 会话经 expectJson）",
        "新建对话" in chat_txt and pg.locator("[data-testid='chat-panel-search']").count() == 1,
        chat_txt[:50].replace("\n", " "),
    )

    # 未被 401 误弹 /login
    check("未发生误跳 /login", "/login" not in pg.url, pg.url[:60])

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    pg.screenshot(path=str(SCR / "_pw_r5e.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== R5批⑤ 对拍：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
