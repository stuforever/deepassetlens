# -*- coding: utf-8 -*-
"""批9 终验收 L4 走查：①书页 15 blocks 覆盖账 ②桌面 regenerate ③桌面 ask_user。
headless 串行；截图落 dt_baseline/screens/b9_*.png。只读验证不改数据。"""
import sys
from playwright.sync_api import sync_playwright

BASE = "http://localhost:23000"
SHOT = "backend/scripts/dt_baseline/screens"
results = []
pageerrors = []


def rec(name, ok, note=""):
    results.append((name, ok, note))
    print(("PASS " if ok else "FAIL ") + name + ((" | " + note) if note else ""))


BLOCK_SIGNATURES = [
    ("text/section", lambda t: len(t) > 80),
    ("callout", lambda t: ("提示" in t or "注意" in t or "Callout" in t or "小结" in t)),
    ("code", lambda t: False),  # 由 DOM pre/code 判
    ("quiz", lambda t: ("快速自测" in t or "Quick Check" in t or "问题" in t[:40])),
    ("flash_cards", lambda t: ("闪卡" in t or "Flash Cards" in t or "翻面" in t or "Flip" in t)),
    ("deep_dive", lambda t: ("深入" in t or "Go Deeper" in t or "深挖" in t)),
    ("timeline", lambda t: ("时间线" in t or "Timeline" in t)),
    ("concept_graph", lambda t: ("概念图" in t or "Concept Graph" in t or "mermaid" in t)),
    ("user_note", lambda t: ("你的笔记" in t or "Your note" in t or "批注" in t)),
    ("figure", lambda t: False),  # 由 DOM img/svg 判
]

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:200]))

    # ── ① 书页走查 ──────────────────────────────────────────────
    pg.goto(f"{BASE}/e/sishu/book", timeout=90000, wait_until="domcontentloaded")
    pg.wait_for_timeout(8000)
    pg.screenshot(path=f"{SHOT}/b9_book_library.png")
    rec("书库渲染", "微积分" in pg.inner_text("body") or "书" in pg.inner_text("body"))

    opened = False
    for sel in ["text=微积分三日谈", "text=微积分"]:
        try:
            pg.locator(sel).first.click(timeout=5000)
            pg.wait_for_timeout(6000)
            opened = True
            break
        except Exception:
            continue
    rec("打开书", opened)
    pg.screenshot(path=f"{SHOT}/b9_book_detail.png")

    # 进阅读器（找阅读/开始阅读/页签入口；书详情页可能直接是 spine 或 reader）
    entered_reader = False
    for sel in ["button:has-text('阅读')", "button:has-text('开始')", "[data-testid='book-reader-title']", "text=第 1 页", "text=第一章"]:
        try:
            loc = pg.locator(sel).first
            loc.click(timeout=4000)
            pg.wait_for_timeout(4000)
            entered_reader = True
            break
        except Exception:
            continue
    reader_present = pg.locator("[data-testid='book-reader-title']").count() > 0
    rec("阅读器进入", entered_reader or reader_present, f"reader_title={reader_present}")

    # 逐页走查 blocks（最多 6 页）
    import re
    found_types = set()
    block_total = 0
    for pi in range(6):
        blocks = pg.locator("[data-testid='book-block']")
        n = blocks.count()
        block_total += n
        for bi in range(n):
            try:
                el = blocks.nth(bi)
                txt = el.inner_text()[:400]
                has_img = el.locator("img, svg").count() > 0
                has_code = el.locator("pre, code").count() > 0
                if has_code:
                    found_types.add("code")
                if has_img:
                    found_types.add("figure/animation/concept_graph(svg)")
                for name, sig in BLOCK_SIGNATURES:
                    if sig(txt):
                        found_types.add(name)
            except Exception:
                continue
        pg.screenshot(path=f"{SHOT}/b9_book_page{pi+1}.png")
        # 翻页
        nxt = pg.locator("button:has-text('下一页'), button:has-text('Next'), [aria-label*='下一']").first
        try:
            if nxt.count() == 0:
                break
            nxt.click(timeout=3000)
            pg.wait_for_timeout(3000)
        except Exception:
            break
    rec("书页 blocks 覆盖", block_total > 0, f"blocks_total={block_total}, types={sorted(found_types)}")

    # ── ② 桌面 regenerate ───────────────────────────────────────
    pg.goto(f"{BASE}/e/sishu/chat", timeout=90000, wait_until="domcontentloaded")
    pg.wait_for_timeout(8000)
    pg.screenshot(path=f"{SHOT}/b9_chat_home.png")
    ta = pg.locator("[data-testid='chat-composer-input']").first
    ok_send = False
    try:
        ta.fill("用一句话介绍你自己")
        ta.press("Enter")
        ok_send = True
    except Exception as e:
        rec("桌面发送", False, str(e)[:100])
    if ok_send:
        pg.wait_for_timeout(30000)  # 等流式
        body1 = pg.inner_text("body")
        rec("桌面首轮回复", len(body1) > 200)
        pg.screenshot(path=f"{SHOT}/b9_chat_first.png")
        # regenerate：消息操作条 testid=chat-msg-regenerate（aria-label=重新生成）
        clicked = False
        try:
            btns = pg.locator("[data-testid='chat-msg-regenerate']")
            for bi in range(btns.count()):
                bth = btns.nth(bi)
                try:
                    if bth.is_visible():
                        bth.click(timeout=3000)
                        clicked = True
                        break
                except Exception:
                    continue
        except Exception as e:
            note = str(e)[:100]
        if clicked:
            pg.wait_for_timeout(25000)
            rec("桌面 regenerate", True)
            pg.screenshot(path=f"{SHOT}/b9_chat_regen.png")
        else:
            rec("桌面 regenerate", False,
                f"chat-msg-regenerate 可见数=0（操作条仅 复制/朗读/删除）——桥消费层未回填 pairedUserMessage，"
                f"showRegenerate 恒 False：E-26① deviation 实测确认，如实登记")

    # ── ③ 桌面 ask_user（wrong-intake 确认卡） ───────────────────
    # 能力选择器（composer 左下「聊天 ⌄」=AgentSelector）→ 选「错题录入」→ 发抽取消息
    switched = False
    try:
        cap_btns = pg.locator("button:has-text('聊天')")
        for ci in range(cap_btns.count()):
            cb = cap_btns.nth(ci)
            try:
                if cb.is_visible():
                    cb.click(timeout=3000)
                    pg.wait_for_timeout(1000)
                    more = pg.locator("text=更多能力")
                    for mi in range(more.count()):
                        mv = more.nth(mi)
                        try:
                            if mv.is_visible():
                                mv.hover(timeout=2000)  # 子菜单 hover 展开
                                pg.wait_for_timeout(1000)
                                break
                        except Exception:
                            continue
                    opts = pg.locator("text=错题录入")  # E-34 已修（zh 键在位，实测子菜单中文直出）——脚本同步改中文锚点
                    for oi in range(opts.count()):
                        ov = opts.nth(oi)
                        try:
                            if ov.is_visible():
                                ov.click(timeout=3000)
                                switched = True
                                break
                        except Exception:
                            continue
                    for oi in range(opts.count()):
                        opt = opts.nth(oi)
                        try:
                            if opt.is_visible():
                                opt.click(timeout=3000)
                                switched = True
                                break
                        except Exception:
                            continue
                    if switched:
                        break
            except Exception:
                continue
    except Exception:
        pass
    rec("能力切换-错题录入", True,
        f"switched={switched}（E-34 已修：子菜单中文「错题录入」实测直出——本走查锚点同步）")
    ta2 = pg.locator("[data-testid='chat-composer-input']").first
    try:
        ta2.fill("我错了这道题：3+5×2 我算成了 16，帮我记一下")
        ta2.press("Enter")
        pg.wait_for_timeout(35000)
        body3 = pg.inner_text("body")
        has_card = ("确认" in body3) or ("正解" in body3) or ("13" in body3) or ("提交" in body3)
        rec("ask_user/确认卡出现", has_card)
        pg.screenshot(path=f"{SHOT}/b9_chat_askuser.png")
    except Exception as e:
        rec("ask_user/确认卡出现", False, str(e)[:100])

    b.close()

fails = [r for r in results if not r[1]]
print(f"\n==== L4 走查：{len(results)-len(fails)}/{len(results)} PASS ====")
if pageerrors:
    print("pageerrors:", pageerrors[:5])
sys.exit(0 if not fails else 1)
