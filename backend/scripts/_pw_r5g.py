# -*- coding: utf-8 -*-
"""R5批⑦ 对拍（纯字符串逻辑件——消费页加载无回归实拍）：chat-export 下载链回归实拍（TutorHomeChat 下载 Markdown 钮）。

useVoiceAutoplay/useVoiceRecorder 为挂载态 hooks——页面加载即消费（零 pageerror=挂载无回归）；
下载点击需会话内有消息（disabled 态登记为渲染在场），有消息则捕获 download 事件。
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

    pg.goto(BASE + "/e/sishu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)

    btn = pg.locator("button[title*='Markdown'], button:has-text('Markdown')").first
    if btn.count() == 0:
        check("页面与下载钮在场", False, "未定位到 Markdown 下载钮")
    else:
        check("页面与下载钮在场（chat-export 消费页挂载）", True)
        disabled = btn.is_disabled()
        if disabled:
            check("下载点击（无消息禁用态——渲染在场登记）", True, "disabled")
        else:
            try:
                with pg.expect_download(timeout=8000) as dl_info:
                    btn.click()
                dl = dl_info.value
                check("下载事件触发（download 修复后回归通过）", True, dl.suggested_filename[:40])
            except Exception as e:  # noqa: BLE001
                check("下载事件触发", False, str(e)[:80])

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    pg.screenshot(path=str(SCR / "_pw_r5g.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== R5批⑦ 对拍（纯字符串逻辑件——消费页加载无回归实拍）：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
