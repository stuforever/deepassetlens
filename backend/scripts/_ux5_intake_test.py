# -*- coding: utf-8 -*-
"""UX批⑤ 验收（反馈⑥续/反馈⑦）：问答式错题录入全流程实测——真图（七年级/错题）。

流程：sishu 对话页 → 附件上传真错题照片 → 发「帮我录入这张错题」→ 多轮交互（agent 问/我答）
→ 等待 wrong-intake-confirmation 卡 → 点「确认并保存」→ 断言入库成功。
验收口径：确认卡出现+确认后成功（AI 问答轮次内容人工核=截图 _ux5_turns.png）。
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(__file__).parent
BASE = "http://localhost:23000"
IMG = r"D:\gitcangku\xiaobaohaohao\七年级\错题\e553b9026392b13052b973f9f2171166.jpg"
R = []


def check(name, ok, detail=""):
    R.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:170], flush=True)


REPLIES = [
    "帮我录入这张错题",
    "图片我上传了，请识别红色标记的那道题",
    "题目是：解方程 2x+3=7，求 x",
    "我的错误答案是 x=5，正确答案是 x=2，错在移项没变号",
    "学科：数学，章节：一元一次方程",
    "信息齐全了，请录入错题本",
    "确认无误，录入吧",
]


def agent_idle(pg) -> bool:
    """Agent 回复完成判据：发送钮不再 streaming/无「正在」字样（宽松）。"""
    body = pg.inner_text("body")
    busy_markers = ("正在思考", "正在理解", "正在生成", "流式传输中")
    return not any(m in body for m in busy_markers)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:100]))
    api = []
    pg.on("response", lambda r: api.append((r.status, r.url.rsplit('/', 1)[-1][:36]))
          if ('wrong' in r.url.lower() or 'mother' in r.url or 'notebook' in r.url) and r.request.method == 'POST' else None)

    pg.goto(BASE + "/e/sishu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(7000)

    # 上传真图
    inp = pg.locator("input[type='file']").first
    check("附件入口在场", inp.count() >= 1)
    inp.set_input_files(IMG)
    pg.wait_for_timeout(3000)
    check("附件预览在场", pg.locator("[data-testid='chat-attachment-preview']").count() >= 1)

    # 发送首条
    ta = pg.locator("textarea").first
    ta.fill(REPLIES[0])
    pg.locator("[data-testid='chat-send']").click()
    print("已发送首条+图片", flush=True)

    # 多轮交互：最多 7 轮，每轮等 agent 空闲后读确认卡/回复
    confirmed = False
    for turn in range(7):
        t0 = time.time()
        while time.time() - t0 < 240:
            if agent_idle(pg):
                break
            pg.wait_for_timeout(5000)
        pg.wait_for_timeout(2000)
        try:
            last_msg = pg.evaluate("""() => {
              const bubbles = [...document.querySelectorAll('[class*=message], [class*=bubble], [data-testid*=assistant]')];
              const el = bubbles[bubbles.length - 1];
              return el ? el.innerText.slice(0, 220) : '';
            }""")
            print(f"轮{turn + 1} AGENT说: {last_msg[:180]}", flush=True)
        except Exception:
            pass
        body = pg.inner_text("body")
        # 确认卡出现？
        card = pg.locator("[data-testid='wrong-intake-confirmation']")
        if card.count() >= 1:
            check(f"轮{turn + 1} 错题确认卡出现", True)
            pg.screenshot(path=str(SCR / f"_ux5_confirm_t{turn + 1}.png"))
            card.locator("[data-testid='wrong-intake-confirm-btn']").click()
            pg.wait_for_timeout(4000)
            after = pg.inner_text("body")
            confirmed = ("已" in after[-300:]) or any(s == 200 or s == 201 for s, _ in api[-3:])
            check("确认后入库成功", confirmed, f"api={api[-3:]}")
            break
        # 回复一轮（轮换话术）
        reply = REPLIES[min(turn + 1, len(REPLIES) - 1)]
        ta2 = pg.locator("textarea").first
        if ta2.count() == 0:
            check(f"轮{turn + 1} 输入框消失", False, body[:80].replace("\n", " "))
            break
        ta2.fill(reply)
        send = pg.locator("[data-testid='chat-send']")
        if send.count() and not send.is_disabled():
            send.click()
        else:
            ta2.press("Enter")
        print(f"轮{turn + 1} 已回复: {reply}", flush=True)
        pg.screenshot(path=str(SCR / f"_ux5_turns.png"))
    else:
        check("错题确认卡出现", False, "7 轮内未出现（对话内容人工核=截图）")

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    b.close()

fails = [x for x, ok in R if not ok]
print(f"\n=== UX批⑤ 问答式错题录入实测：{len(R) - len(fails)}/{len(R)} PASS ===")
sys.exit(1 if fails else 0)
