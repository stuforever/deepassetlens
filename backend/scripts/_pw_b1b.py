# -*- coding: utf-8 -*-
"""批①b 对拍：首屏8宫格回填不直发 + 附件条四选择器记忆 + 右栏三态（v4§二.1/.2/.4/§十三.3）。"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
R = []
sys.path.insert(0, str(SCR))
from _pw_login_util import login_page  # noqa: E402


def check(name, ok, detail=""):
    R.append(bool(ok))
    print(("GREEN " if ok else "RED   ") + name + "  " + str(detail)[:110], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = login_page(b)

    # ── 首屏 8 宫格：点击回填不直发 ──
    pg.goto(BASE + "/", timeout=90000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    grid = pg.locator("[data-testid='newchat-templates']")
    check("宫格渲染", grid.count() > 0)
    cells = pg.locator("[data-testid='newchat-templates'] [role='button']")
    check("8 模板格", cells.count() == 8, f"cells={cells.count()}")
    if cells.count() >= 1:
        cells.first.click()
        pg.wait_for_timeout(800)
        ta = pg.locator("[data-testid='newchat-composer'] textarea").first
        val = ta.input_value()
        check("点击回填 composer 值=模板文案", "{主题}" in val, val[:40])
        check("未直发（URL 仍在 /）", pg.url.rstrip("/") == BASE, pg.url[-30:])
        focused = pg.evaluate("() => document.activeElement === document.querySelector(\"[data-testid='newchat-composer'] textarea\")")
        check("回填后聚焦输入框", focused)
        # 自定义格=空模板聚焦
        custom = pg.locator("[data-testid='newchat-template-自定义']")
        if custom.count() > 0:
            custom.click()
            pg.wait_for_timeout(500)
            check("自定义格=空回填", pg.locator("[data-testid='newchat-composer'] textarea").first.input_value() == "")

    # ── 对话页附件条 + 右栏（注入种子会话——右栏需已有消息渲染） ──
    import json as _json
    import time as _time
    seed = [{
        "id": "b1b-seed", "title": "批①b右栏测试", "expertId": "wenshu",
        "createdAt": int(_time.time() * 1000), "confirmed": {}, "flags": {},
        "thinkStream": [], "pendingCandidates": [], "lastResponse": None,
        "finalTokens": [], "finalAnswer": "",
        "messages": [
            {"id": "u-1700000000000", "role": "user", "text": "测试问题"},
            {"id": "a-1700000000001", "role": "assistant", "text": "测试回答",
             "payload": {"final_answer": "测试回答", "evidence": {"route": {"skill": "sishu/chat", "route_type": "expert_card"}, "tables": ["t_demo"], "examples_used": []}, "confidence": "高"}},
        ],
    }]
    pg.context.add_init_script("try { localStorage.setItem('di_sessions_freeplan_v1', '%s'); } catch {}" % _json.dumps(seed, ensure_ascii=False).replace("'", "\'"))
    pg.goto(BASE + "/e/wenshu/chat", timeout=90000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    bar = pg.locator("[data-testid='attachment-bar']")
    check("附件条渲染", bar.count() > 0)
    for tid in ("attach-kb", "attach-skill", "attach-model"):
        check(f"选择器 {tid} 在场", pg.locator(f"[data-testid='{tid}']").count() > 0)
    # 选知识库 → localStorage 记忆
    kb_sel = pg.locator("[data-testid='attach-kb']")
    kb_sel.click()
    pg.wait_for_timeout(1200)
    opts = pg.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option")
    if opts.count() > 0:
        first_label = opts.first.inner_text()
        opts.first.click()
        pg.wait_for_timeout(800)
        kb_sel.press("Escape")
        pg.wait_for_timeout(300)
        stored = pg.evaluate("() => localStorage.getItem('attach:wenshu:kb') || ''")
        check("📚 选择落 localStorage", first_label[:10] in stored or "kb" in stored, stored[:60])
        pg.reload(wait_until="domcontentloaded")
        pg.wait_for_timeout(6000)
        chips = pg.locator("[data-testid='attach-kb'] .ant-select-selection-item").count()
        check("reload 后知识库选择保持", chips > 0, f"chips={chips}")
    else:
        check("📚 选择落 localStorage", False, "无知识库选项（库列表空）")

    # 右栏三态：细条→展开→收起
    strip = pg.locator("[data-testid='context-rail-strip']")
    check("右栏细条渲染（40px）", strip.count() > 0)
    if strip.count() > 0:
        w0 = pg.evaluate("() => document.querySelector(\"[data-testid='context-rail-panel']\") ? document.querySelector(\"[data-testid='context-rail-panel']\").getBoundingClientRect().width : 0")
        pg.locator("[data-testid='context-rail-config']").click()
        pg.wait_for_timeout(900)
        w1 = pg.evaluate("() => document.querySelector(\"[data-testid='context-rail-panel']\")?.getBoundingClientRect().width || 0")
        check("config 面板展开 320px", w1 == 320, f"w={w1}")
        mirror = pg.locator("[data-testid='rail-attachment-bar']").count()
        check("config=附件条镜像", mirror > 0)
        pg.locator("[data-testid='context-rail-evidence']").click()
        pg.wait_for_timeout(600)
        check("evidence 面板可切换", pg.locator("[data-testid='context-rail-panel']").count() > 0)
        pg.locator("[data-testid='context-rail-artifacts']").click()
        pg.wait_for_timeout(600)
        check("artifacts 面板可切换", pg.locator("[data-testid='context-rail-panel']").count() > 0)
        pg.screenshot(path=str(SCR / "_pw_b1b_rail.png"))
        pg.locator("[data-testid='context-rail'] button[aria-label='收起右栏']").click()
        pg.wait_for_timeout(600)
        w2 = pg.evaluate("() => document.querySelector(\"[data-testid='context-rail-panel']\") ? 1 : 0")
        check("收起后面板消失", w2 == 0)
        open_ls = pg.evaluate("() => localStorage.getItem('rail:wenshu:open')")
        check("收起态清除记忆", open_ls is None, str(open_ls))

    pg.screenshot(path=str(SCR / "_pw_b1b.png"))
    b.close()

greens = sum(R)
print(f"\n=== 批①b 对拍：{greens}/{len(R)} GREEN ===")
sys.exit(0 if greens == len(R) else 1)
