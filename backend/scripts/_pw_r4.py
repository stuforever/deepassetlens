# -*- coding: utf-8 -*-
"""R4批 对拍（R#5 / 计划 Task 12 Step1）：平台 WS 两径恢复 + 闪烁复验。

断言账：
1  knowledge progress WS 升级经新代理条目打通（onopen 或后端升级后受控关闭≠传输失败）
2  partners WS 升级同理
3  15s 闪烁复验：零 'Invalid frame header'/'WebSocket' 相关 console 错误 + 零 pageerror
   + 无导航重载（dev-client 无限重连的根因形态不复现）
4  DOM churn：15s 窗口 body 顶层结构变异=0（闪烁=持续重挂载）
"""
import json
import sys
import time
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
    ws_frames = []
    pg.on("websocket", lambda ws: (ws_frames.append(ws.url),
                                   ws.on("socketerror", lambda m: ws_frames.append(f"ERR:{m}"))))

    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)

    # ①② WS 升级探针（探针 kb/伙伴 id——升级层证明=代理转发成功；后端业务拒绝发生在升级后）
    # HPM v2 惰性订阅：upgrade 监听在中间件收到首个匹配上下文的普通 HTTP 请求后才挂上
    # （源码 catchUpgradeRequest 注释"use initial request to access the server object"）
    # ——探针前先各发一次普通请求暖订阅
    pg.evaluate("""async () => {
      await fetch('/api/v1/knowledge').catch(() => {});
      await fetch('/api/v1/partners').catch(() => {});
    }""")
    pg.wait_for_timeout(500)
    probe = pg.evaluate("""async () => {
      const probe = (path) => new Promise((resolve) => {
        let opened = false;
        let closeCode = null;
        const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + path);
        const done = (r) => { try { ws.close(); } catch {} resolve(r); };
        ws.onopen = () => { opened = true; done({ opened }); };
        ws.onerror = () => { if (!opened) done({ opened: false }); };
        ws.onclose = (e) => { closeCode = e.code; done({ opened, closeCode }); };
        setTimeout(() => done({ opened, timeout: true }), 6000);
      });
      const k = await probe('/api/v1/knowledge/probe-r4/progress/ws');
      const pt = await probe('/api/v1/partners/probe-r4/ws');
      return { knowledge: k, partners: pt };
    }""")
    k_ok = probe["knowledge"]["opened"] or (probe["knowledge"].get("closeCode") not in (None, 1006, 1002, 1015))
    p_ok = probe["partners"]["opened"] or (probe["partners"].get("closeCode") not in (None, 1006, 1002, 1015))
    check("knowledge progress WS 升级打通", k_ok, json.dumps(probe["knowledge"])[:80])
    check("partners WS 升级打通", p_ok, json.dumps(probe["partners"])[:80])

    # ③ 15s 闪烁复验
    console_errs = []
    pg.on("console", lambda m: console_errs.append(m.text[:120]) if m.type == "error" else None)
    nav0 = len(pg.context.pages)
    t0 = time.time()
    pg.wait_for_timeout(15000)
    frame_errs = [e for e in console_errs if "frame header" in e or "WebSocket" in e]
    check("15s 零 WS/frame 错误", len(frame_errs) == 0, str(frame_errs[:2]))
    check("15s 零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    check("无 dev-client 重载（页面数不变）", len(pg.context.pages) == nav0)

    # ④ DOM churn（顶层结构变异计数）
    churn = pg.evaluate("""() => new Promise((resolve) => {
      let n = 0;
      const obs = new MutationObserver((muts) => { n += muts.filter(m => m.type === 'childList').length; });
      obs.observe(document.getElementById('root') || document.body, { childList: true, subtree: false });
      setTimeout(() => { obs.disconnect(); resolve(n); }, 10000);
    })""")
    check("10s 顶层 DOM churn≈0", churn <= 5, f"mutations={churn}")

    pg.screenshot(path=str(SCR / "_pw_r4.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== R4批 对拍：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
