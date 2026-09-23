# -*- coding: utf-8 -*-
"""UX批⑤ chat 问答式错题录入 E2E：真图+错题录入能力→抽取/追问→确认卡→落库。

断言账：
1 错题录入能力项在场  2 附件上传+发送  3 OCR 注入（编排日志）→ 确认卡出现（或追问轮内出现）
4 点确认 → 落库回执（已入库 ✓ / POST mother-questions 2xx）  5 零 pageerror
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
    "题干就用图片里红笔标记的那道，我的答案写在图上了",
    "学科数学，章节一元一次方程",
    "我的错误答案是 x=5，正确答案是 x=2，错因：移项没变号",
    "信息齐全，请出确认卡",
    "确认",
]


def agent_idle(pg) -> bool:
    body = pg.inner_text("body")
    busy = ("正在思考", "正在理解", "正在生成", "AI 正在", "推理中", "AI 正在讲解")
    return not any(m in body for m in busy)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:100]))
    api = []
    pg.on("response", lambda r: api.append((r.status, r.url.rsplit('/', 1)[-1][:36]))
          if '/mother-questions' in r.url and r.request.method == 'POST' else None)

    pg.goto(BASE + "/e/sishu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(8000)

    # ① 选择「错题录入」能力：composer 左下当前能力钮 → 弹层 → 错题录入
    # 欢迎层会拦截指针命中——JS 直点（onClick 处理器照常触发）
    pg.evaluate("""() => {
      const btn = [...document.querySelectorAll('button')].find(b => /聊天|Chat|对话/.test(b.innerText || ''));
      if (btn) btn.click();
    }""")
    pg.wait_for_timeout(700)
    opened = pg.evaluate("""() => {
      const el = [...document.querySelectorAll('div,button')].find(e => (e.innerText || '').trim() === '错题录入');
      if (el) { el.click(); return true; }
      return false;
    }""")
    check("① 错题录入能力项点击", opened)
    pg.wait_for_timeout(800)

    # ② 上传真图
    pg.locator("input[type='file']").first.set_input_files(IMG)
    pg.wait_for_timeout(3000)
    check("② 附件预览在场", pg.locator("[data-testid='chat-attachment-preview']").count() >= 1)

    # ③ 发送
    ta = pg.locator("textarea").first
    ta.fill("帮我录入这张错题")
    pg.locator("[data-testid='chat-send']").click()
    print("已发送（错题录入能力+真图）", flush=True)

    # ④ 多轮：等确认卡 / 追问回复
    confirmed = False
    card_seen = False
    for turn in range(6):
        t0 = time.time()
        while time.time() - t0 < 240:
            if agent_idle(pg):
                break
            pg.wait_for_timeout(5000)
        pg.wait_for_timeout(2500)
        card = pg.locator("[data-testid='wrong-intake-confirmation']")
        if card.count() >= 1:
            card_seen = True
            check(f"轮{turn + 1} 错题确认卡出现", True)
            pg.screenshot(path=str(SCR / f"_ux5e_confirm_t{turn + 1}.png"))
            card.locator("[data-testid='wrong-intake-confirm-btn']").click()
            pg.wait_for_timeout(5000)
            after = pg.inner_text("body")
            ok_save = ("已入库" in after[-400:]) or any(s in (200, 201) for s, _ in api[-3:])
            check("④ 确认后落库回执", ok_save, f"api={api[-3:]} tail={after[-120:].replace(chr(10), ' ')}")
            confirmed = True
            break
        # 无卡：读末条 agent 文本（转录）后按话术回复
        body_tail = pg.inner_text("body")[-400:]
        print(f"轮{turn + 1} BODY尾: {body_tail.replace(chr(10), ' | ')[-260:]}", flush=True)
        reply = REPLIES[min(turn, len(REPLIES) - 1)]
        ta2 = pg.locator("textarea").first
        if ta2.count() == 0:
            break
        ta2.fill(reply)
        send = pg.locator("[data-testid='chat-send']")
        if send.count() and not send.is_disabled():
            send.click()
        else:
            ta2.press("Enter")
        print(f"轮{turn + 1} 已回复: {reply}", flush=True)
    if not confirmed:
        check("错题确认卡+落库", card_seen, "未达确认（转录人工核）")
    pg.screenshot(path=str(SCR / "_ux5e_final.png"))

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    b.close()

fails = [x for x, ok in R if not ok]
print(f"\n=== UX批⑤ chat E2E：{len(R) - len(fails)}/{len(R)} PASS ===")
sys.exit(1 if fails else 0)
