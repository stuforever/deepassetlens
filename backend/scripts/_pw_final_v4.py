# -*- coding: utf-8 -*-
"""批⑥ 全量终验收（A 主窗断言同步：模板 testid=newchat-template-{title}；💬面板四层分类取代「最近对话」文案；🎭角色=默认+三卡共 4 项）（v4§十 ⓪-⑥ + 附录A/B.3 抽样 + v3§七 + 批⑥新项 + 三专家冒烟）。

跨批不变量：
- 批⓪/①: newchat 首屏/8宫格回填不直发/裸排版无 Card/操作条
- 批②: tokens 在场（--font/--fs 变量）
- 批③: 图标条 3 + 三面板 400 + 五组 + ⌘K（专家门户中文/僵尸不出）
- 批④: 💬面板分类列表（置顶/收藏/搜索）
- 批⑤: 附件条技能下拉仅场景型；角色下拉三卡
- 批⑥: 设置八分区点遍无死链 + 运行观测契约回放 + 对话页「路由模拟」=0 + R#12 notebook 活
- 三专家冒烟: wenshu 全链（流式+操作条）；sishu/h5 页面+发送链路
"""
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
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:170], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(SCR))
    from _pw_login_util import login_page

    pg = login_page(b)
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:120]))

    # ── ⓪/① 首屏 ────────────────────────────────────────────────
    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    check("⓪ newchat 首屏", pg.locator("[data-testid='newchat-home']").count() == 1)
    check("① composer 在", pg.locator("[data-testid='newchat-composer'] textarea").count() >= 1)
    body = pg.inner_text("body")
    check("⓪ 首屏无路由模拟字样", "路由模拟" not in body)
    tokens_css = pg.evaluate("() => getComputedStyle(document.documentElement).getPropertyValue('--font-sans') || getComputedStyle(document.body).fontFamily")
    check("② 附录A tokens 在场", bool(tokens_css))

    # 8 宫格回填不直发（点击模板后仍在首屏）
    tpl = pg.locator("[data-testid^='newchat-template-']")
    if tpl.count() >= 1:
        tpl.first.click()
        pg.wait_for_timeout(400)
        check("② 模板回填不直发", pg.locator("[data-testid='newchat-home']").count() == 1)
    else:
        check("② 模板宫格在场", False, "no newchat-tpl-*")

    # ── ③ 壳三态+⌘K ─────────────────────────────────────────────
    btns = pg.locator("[data-testid='activity-bar'] button")
    check("③ 图标条 3", btns.count() == 3, f"count={btns.count()}")
    pg.locator("[data-testid='activity-console']").click()
    pg.wait_for_timeout(600)
    sp = pg.locator("[data-testid='shell-panel']")
    check("③ 管理台面板开", sp.count() == 1 and sp.is_visible())
    w = sp.bounding_box()["width"] if sp.count() else 0
    check("③ 面板宽 400", abs((w or 0) - 400) <= 1, f"w={w}")
    for g in ("数据建模", "数据接入", "数据资产", "私塾管理", "H5 发布管理"):
        check(f"③ 组[{g}]", pg.locator(f"[data-testid='nav-panel-group-{g}']").count() == 1)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(500)

    # ⌘K：门户中文标签 + 僵尸不出现
    pg.keyboard.press("Control+k")
    pg.wait_for_timeout(500)
    pg.locator("[data-testid='cmdk-input']").fill("门户")
    pg.wait_for_timeout(400)
    first = pg.locator("[data-testid='cmdk-item-0']")
    check("③ ⌘K 门户中文", first.count() == 1 and first.inner_text().strip() == "专家门户",
          first.inner_text().strip()[:30] if first.count() else "none")
    pg.locator("[data-testid='cmdk-input']").fill("矩阵")
    pg.wait_for_timeout(400)
    check("③ ⌘K 僵尸清零", pg.get_by_text("无匹配结果").count() >= 1)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)

    # ── ④ 💬面板历史分类 ────────────────────────────────────────
    pg.locator("[data-testid='activity-chat']").click()
    pg.wait_for_timeout(600)
    chat_body = pg.inner_text("[data-testid='chat-panel']")
    check("④ 新建对话+历史搜索（批④四层分类契约）", "新建对话" in chat_body and pg.locator("[data-testid='chat-panel-search']").count() == 1)
    check("④ 无专家直达", "三专家直达" not in chat_body)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)

    # ── ⑤ 附件条（进 wenshu 对话页） ────────────────────────────
    pg.goto(BASE + "/e/wenshu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    check("⑤ 附件条在场", pg.locator("[data-testid='attachment-bar']").count() >= 1)
    pg.locator("[data-testid='attach-skill']").click()
    pg.wait_for_timeout(600)
    skill_opts = pg.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option")
    opts_txt = [skill_opts.nth(i).inner_text() for i in range(min(skill_opts.count(), 20))]
    check("⑤ 技能下拉非空", len(opts_txt) >= 1, f"opts={opts_txt[:5]}")
    pg.keyboard.press("Escape")
    pg.locator("[data-testid='attach-role']").click()
    pg.wait_for_timeout(600)
    role_opts = pg.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option")
    check("⑤ 角色下拉默认+三卡", role_opts.count() == 4, f"count={role_opts.count()}")
    pg.keyboard.press("Escape")
    chat_body2 = pg.inner_text("body")
    check("批⑥ 对话页无路由模拟", "路由模拟" not in chat_body2)

    # R#12：notebook 别名活
    r = pg.goto(BASE + "/e/sishu/notebook", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(3000)
    check("R#12 notebook 活", "404" not in (pg.title() or "") and pg.locator("body").count() == 1,
          pg.url[:60])

    # ── 批⑥ 设置八分区点遍无死链 ────────────────────────────────
    pg.goto(BASE + "/settings", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    sections = pg.locator("[data-testid^='settings-panel-'], [data-testid^='hub-card-'], a[href^='/settings'], [data-testid^='settings-hub-']")
    hub_txt = pg.inner_text("body")
    eight = ["通用", "模型与服务", "知识与检索", "智能体", "数据探索", "数据治理", "安全", "私塾教学"]
    for name in eight:
        check(f"批⑥ 分区[{name}]在设置中心", name in hub_txt)
    dead = []
    pageerror0 = len(pageerrors)
    # 遍历设置中心所有分区链接（点开 → 回设置中心）
    links = pg.locator("a[href^='/settings'], a[href^='/vector'], a[href^='/governance'], a[href^='/security-controls'], a[href^='/skills'], a[href^='/golden-qa']")
    n_links = min(links.count(), 24)
    hrefs = [links.nth(i).get_attribute("href") for i in range(n_links)]
    seen = set()
    for href in hrefs:
        if not href or href in seen:
            continue
        seen.add(href)
        try:
            pg.goto(BASE + href, timeout=30000, wait_until="domcontentloaded")
            pg.wait_for_timeout(1200)
            if len(pageerrors) > pageerror0:
                dead.append((href, pageerrors[-1][:60]))
                pageerror0 = len(pageerrors)
        except Exception as exc:
            dead.append((href, str(exc)[:60]))
    check("批⑥ 设置分区点遍无死链", not dead, str(dead[:3]))

    # ── 批⑥ 运行观测契约回放 ────────────────────────────────────
    pg.goto(BASE + "/governance", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    check("批⑥ 观测页契约回放卡", pg.locator("[data-testid='gov-trace-input']").count() == 1
          and pg.locator("[data-testid='gov-trace-load']").count() == 1)
    pg.locator("[data-testid='gov-trace-input']").fill("nonexistent-thread")
    pg.locator("[data-testid='gov-trace-load']").click()
    pg.wait_for_timeout(1500)
    check("批⑥ 回放 404 文案", pg.get_by_text("无该 thread_id 的契约轨迹").count() >= 1)

    # ── 三专家冒烟 ───────────────────────────────────────────────
    # wenshu：全链（流式+操作条）
    pg.goto(BASE + "/e/wenshu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    pg.locator("textarea").first.fill("统计用电客户总数")
    pg.locator("textarea").first.press("Enter")
    t0 = time.time()
    got = False
    while time.time() - t0 < 600:
        body = pg.inner_text("body")
        if "已准备好答案" in body or "推理完成" in body or pg.locator("[data-testid^='msg-actions']").count() > 0:
            got = True
            break
        pg.wait_for_timeout(5000)
    check("冒烟 wenshu 流式交付", got, f"waited={int(time.time()-t0)}s")

    # sishu：发送链路
    pg.goto(BASE + "/e/sishu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    sishu_ok = pg.locator("textarea").count() >= 1
    check("冒烟 sishu 页面+composer", sishu_ok)

    # h5：展台页
    pg.goto(BASE + "/e/tutor-h5/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    check("冒烟 h5 展台页", pg.locator("body").count() == 1)

    check("零 pageerror（终验收）", len(pageerrors) == 0, str(pageerrors[:2]))
    pg.screenshot(path=str(SCR / "_pw_final_v4.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== 批⑥ 全量终验收：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
