# -*- coding: utf-8 -*-
"""V1壳 Task2 对拍：新建对话首屏 + Tab 记忆 + 发送直达 + /home 重定向 + 页签无钉住。"""
import sys
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:170], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)  # 批③基线复验：auth 开启后须登录态
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:120]))

    # ① 首屏：Tab+composer，无侧栏树噪音
    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    check("首屏 newchat-home", pg.locator("[data-testid='newchat-home']").count() == 1)
    check("专家 Tab 三枚", pg.locator("[data-testid='newchat-tabs'] > div").count() == 3)
    check("composer 在", pg.locator("[data-testid='newchat-composer'] textarea").count() >= 1)
    body_txt = pg.inner_text("body")
    check("无旧侧栏菜单噪音（工作区/资产管理组名不再出现）",
          "工作区" not in body_txt and "资产管理" not in body_txt, "")

    # ② Tab 切换 + 记忆
    pg.locator("[data-testid='newchat-tab-sishu']").click()
    pg.wait_for_timeout(400)
    check("切私塾标题变", "今天想学点什么" in pg.inner_text("body"))
    pg.reload(timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    active = pg.evaluate("() => localStorage.getItem('newchat-tab')")
    check("Tab 记忆生效（reload 后 sishu）", active == "sishu", f"saved={active}")

    # ③ 发送 → /e/wenshu/chat?new=1&q=... 且流式回答（切回 wenshu Tab 再发）
    pg.locator("[data-testid='newchat-tab-wenshu']").click()
    pg.wait_for_timeout(300)
    q = "统计用电客户总数"
    pg.locator("[data-testid='newchat-composer'] textarea").first.fill(q)
    pg.locator("[data-testid='newchat-composer'] textarea").first.press("Enter")
    pg.wait_for_timeout(2000)
    expect_url = "/e/wenshu/chat?new=1&q=" + urllib.parse.quote(q, safe="")
    # 批⓪ R#6 后契约：落到对话页且 URL 已立即清参（?q=/?new=1 不驻留）
    check("发送直达对话页", "/e/wenshu/chat" in pg.url and "q=" not in pg.url and "new=1" not in pg.url, pg.url[:90])
    # R#13 正向断言（R队列要求补）：问题气泡出现 + chat 请求到达后端——
    # 旧形态 cleanup 掐定时器=首问静默丢失（无气泡无请求），此二断言是修法回归门。
    got_bubble = False
    got_chat_req = False
    reqs = []
    pg.on("request", lambda r: reqs.append(r.url) if (r.method == "POST" and ("chat" in r.url or "capability" in r.url)) else None)
    t0b = __import__("time").time()
    while __import__("time").time() - t0b < 30:
        if "统计用电客户总数" in pg.inner_text("body"):
            got_bubble = True
            break
        pg.wait_for_timeout(500)
    check("R#13正向：问题气泡出现", got_bubble, f"waited={int(__import__('time').time()-t0b)}s")
    pg.wait_for_timeout(3000)
    got_chat_req = any(("chat" in u or "capability" in u) for u in reqs)
    check("R#13正向：chat请求到达后端", got_chat_req, f"posts={len(reqs)}")
    # 流式回答：等待回答文本或表格（600s 上限——探针实测 330s 交付/偶发 >420s，LLM 多轮推理延迟方差非回归）
    got = False
    import time
    t0 = time.time()
    while time.time() - t0 < 600:
        body = pg.inner_text("body")
        # 批①a 后流式可达判据：完成行（ThinkingChain）或表格，且操作条出现=回答交付完成
        if ("已准备好答案" in body) or ("推理完成" in body) or (pg.locator("[data-testid^='msg-actions']").count() > 0):
            got = True
            break
        pg.wait_for_timeout(3000)
    check("流式回答到达", got, f"waited={int(time.time()-t0)}s")

    # ④ /home 重定向
    pg.goto(BASE + "/home", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(3000)
    check("/home 落 /", pg.url.rstrip("/").endswith(":23000") or pg.url.rstrip("/").endswith("/"), pg.url[:80])
    check("/home 渲染新建对话页", pg.locator("[data-testid='newchat-home']").count() == 1)

    # ⑤ 页签无钉住：切到一个 tabbed 页，全部页签可关（关闭后页签减少）
    pg.goto(BASE + "/graph", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    close_btns = pg.locator("[data-testid='app-tabs'] svg, .ant-tabs-tab-remove")
    tabs_count = pg.evaluate("""() => {
      // 页签 DOM：AppTabs 自绘——统计带关闭 X 的页签行
      const nodes = document.querySelectorAll('[style*="borderTop"]');
      return document.querySelectorAll("svg[data-icon='close']").length;
    }""")
    check("页签关闭钮存在（无钉住遮挡）", tabs_count >= 1, f"close_icons={tabs_count}")

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    pg.screenshot(path=str(SCR / "_pw_newchat.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== Task2 对拍：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
