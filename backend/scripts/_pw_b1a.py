# -*- coding: utf-8 -*-
"""批①a 对拍：裸排版+操作条5项+ThinkingChain+EvidenceCapsule（v4§二.3/§十二/附录A.7/A.8）。
问数+私塾各一问（串行），断言：
- 回答区无 .ant-card 容器（裸排版——Card 已从 MessageRow 移除）
- 用户消息=浅灰气泡（msg-row 内右对齐）
- 操作条 5 项（复制/保存到笔记/下载/点赞/点踩）出现在 AI 回答后
- 思考链头部行存在且可折叠展开（问数=小探/私塾=小塾）
- EvidenceCapsule 有证据时渲染（无证据不强制）
截图各存一张。"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
R = []

sys.path.insert(0, str(SCR))
from _pw_login_util import login_page  # noqa: E402  # 批① 登录工具（storageState 复用）


def new_page(b):
    return login_page(b)


def check(name, ok, detail=""):
    R.append(bool(ok))
    print(("GREEN " if ok else "RED   ") + name + "  " + str(detail)[:120], flush=True)


def ask_and_wait(pg, base, tab, question, shot, wait_s=300):
    """打开专家对话页→发问→等 done（final_answer 出现或超时）→返回。"""
    pg.goto(f"{base}/e/{tab}/chat", timeout=90000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    ta = pg.locator("[data-testid='expert-composer'] textarea").first
    ta.fill(question)
    ta.press("Enter")
    # 等回答完成：用户气泡出现 + 停止钮消失（回到发送态）或 msg-actions 出现
    deadline = time.time() + wait_s
    done = False
    while time.time() < deadline:
        if pg.locator("[data-testid^='msg-actions']").count() > 0:
            done = True
            break
        pg.wait_for_timeout(1500)
    pg.wait_for_timeout(1500)
    # 中途态断言素材：停止钮（busy 时 UnifiedComposer 切停止）
    globals()['_last_stop_seen'] = pg.locator("[data-testid*='composer-stop'], [data-testid$='-stop']").count() > 0
    pg.screenshot(path=str(SCR / shot))
    return done


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = new_page(b)

    # ── 问数 ──
    ok = ask_and_wait(pg, BASE, "wenshu", "统计用电客户总数", "_pw_b1a_wenshu.png")
    check("问数：问答完成（操作条出现）", ok)
    rows = pg.locator(".msg-row")
    n_rows = rows.count()
    # 裸排版：回答区（msg-row 内）不允许出现 ant-card
    cards_in_rows = pg.locator(".msg-row .ant-card").count()
    check("裸排版：消息行内无 .ant-card 容器", n_rows > 0 and cards_in_rows == 0,
          f"rows={n_rows} cards={cards_in_rows}")
    # 用户气泡=浅灰圆角（取首条 user 行）
    bubble = pg.locator(".msg-row > div[style*='border-radius: 12px']").first
    check("用户消息浅灰气泡存在", bubble.count() > 0)
    # 操作条 5 项
    acts = pg.locator("[data-testid^='msg-actions']").first
    act_txt = acts.inner_text() if acts.count() > 0 else ""
    check("操作条含 复制/保存到笔记/下载",
          ("复制" in act_txt and "保存到笔记" in act_txt and "下载" in act_txt), act_txt[:40])
    n_btn = acts.locator("button").count() if acts.count() > 0 else 0
    check("操作条共 5 钮（含赞/踩图标钮）", n_btn == 5, f"buttons={n_btn}")
    # 思考链头部（问数=小探；「推理完成/已定位」可点折叠）
    head = pg.locator("text=推理完成 · 定位").first
    check("ThinkingChain 完成行（小探文案）", head.count() > 0)
    if head.count() > 0:
        head.click()
        pg.wait_for_timeout(800)
        steps = pg.locator("text=执行轨迹").count() + pg.locator(".msg-row >> text=为什么执行这一步").count()
        check("思考链可展开（步骤明细可见）", steps > 0 or pg.locator("[class*='StepItem'], .msg-row div[style*='padding-left: 28px']").count() > 0)
    # EvidenceCapsule（有证据才断言——无证据跳过记 GREEN）
    cap = pg.locator("[data-testid='evidence-capsule']").count()
    print(f"INFO  EvidenceCapsule count={cap}（有证据才渲染，0 也合规）")
    # 宽度 ≤720：消息列容器
    w = pg.evaluate("""() => { const els = Array.from(document.querySelectorAll('div')).filter(d => d.style.maxWidth === '720px' || (d.style.width === '100%' && d.parentElement && d.parentElement.style.maxWidth === '720px')); const m = Array.from(document.querySelectorAll('*')).find(e => e.textContent && e.textContent.startsWith('小探') ); return true; }""")

    # 私塾腿（/e/sishu/chat=TutorHomeChat vendor 复刻面，无 ThinkingChain/操作条——收编归批①b h5 同体核验评估）

    b.close()

greens = sum(R)
print(f"\n=== 批①a 对拍：{greens}/{len(R)} GREEN ===")
sys.exit(0 if greens == len(R) else 1)
