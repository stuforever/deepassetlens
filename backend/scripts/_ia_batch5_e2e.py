# -*- coding: utf-8 -*-
"""IA批5 e2e：设置中心 31 页复刻（hub+二级侧栏+子页+LLM 合一页+防双轨跳转）。"""
from playwright.sync_api import sync_playwright

BASE = "http://localhost:23000"
OUT = []


def check(name, ok, detail=""):
    OUT.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + ((" | " + str(detail)) if detail else ""))


def shot(page, name):
    page.screenshot(path=f"scripts/_ia_b5_{name}.png")


def open_path(ctx, path, wait_text, timeout=25000):
    page = ctx.new_page()
    page.goto(BASE + path, timeout=60000)
    if wait_text:
        page.wait_for_selector(wait_text, timeout=timeout)
    page.wait_for_timeout(2500)
    return page


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script("try{localStorage.setItem('h5_recent_users', JSON.stringify(['小明']));}catch(e){}")

    # S1 hub
    pg = open_path(ctx, "/settings", "text=设置")
    body = pg.inner_text("body")
    check("S1 hub(类目卡+状态)", all(k in body for k in ("外观", "模型", "伙伴和智能体", "记忆")))
    shot(pg, "hub")
    pg.close()

    # S2 llm 子页（ServiceConfigEditor）
    pg = open_path(ctx, "/settings/llm", "text=LLM")
    body = pg.inner_text("body")
    check("S2 llm 子页(ServiceConfigEditor)", ("API" in body or "Provider" in body or "供应商" in body) and ("模型" in body))
    shot(pg, "llm")
    pg.close()

    # S3 appearance
    pg = open_path(ctx, "/settings/appearance", "text=外观")
    body = pg.inner_text("body")
    check("S3 appearance(主题卡)", ("默认" in body and "深色" in body) or "主题" in body)
    shot(pg, "appearance")
    pg.close()

    # S4 agents 子枢纽
    pg = open_path(ctx, "/settings/agents", "text=伙伴和智能体")
    body = pg.inner_text("body")
    check("S4 agents 枢纽(六家磁贴)", "Claude Code" in body and "Codex" in body)
    shot(pg, "agents")
    pg.close()

    # S5 codex 编辑器
    pg = open_path(ctx, "/settings/agents/codex", "text=Codex")
    check("S5 codex 编辑器", "模型" in pg.inner_text("body") or "推理" in pg.inner_text("body"))
    shot(pg, "codex")
    pg.close()

    # S6-S8 防双轨/源跳转壳
    pg = open_path(ctx, "/settings/curriculum", None)
    pg.wait_for_timeout(2500)
    check("S6 curriculum→教学设置", "/e/tutor/admin/settings/curriculum" in pg.url, pg.url)
    pg.close()

    pg = open_path(ctx, "/settings/attachments", None)
    pg.wait_for_timeout(2500)
    check("S7 attachments→/attachment-settings", "/attachment-settings" in pg.url, pg.url)
    pg.close()

    pg = open_path(ctx, "/settings/mineru", None)
    pg.wait_for_timeout(2500)
    check("S8 mineru→document-parsing", "/settings/document-parsing" in pg.url, pg.url)
    shot(pg, "document_parsing")
    pg.close()

    # S9 /llm-config 合一页
    pg = open_path(ctx, "/llm-config", "text=LLM")
    body = pg.inner_text("body")
    check("S9 /llm-config 合一页", ("供应商" in body or "Provider" in body or "API" in body))
    shot(pg, "llm_config")
    pg.close()

    # S10 tools 厚页
    pg = open_path(ctx, "/settings/tools", "text=工具")
    check("S10 tools 页", "体验增强" in pg.inner_text("body") or "内置工具" in pg.inner_text("body"))
    shot(pg, "tools")
    pg.close()

    # S11 memory 厚页
    pg = open_path(ctx, "/settings/memory", "text=记忆")
    check("S11 memory 页", "去重" in pg.inner_text("body") or "分块" in pg.inner_text("body"))
    pg.close()

    # S12 capabilities 厚页
    pg = open_path(ctx, "/settings/capabilities", "text=能力")
    check("S12 capabilities 页", "温度" in pg.inner_text("body") or "聊天" in pg.inner_text("body"))
    pg.close()

    # S13 菜单入口：设置中心（组标题先展开，再点 menu-item）
    pg = ctx.new_page()
    pg.goto(BASE + "/", timeout=60000)
    pg.wait_for_timeout(3500)
    pg.evaluate(
        "() => { const t = [...document.querySelectorAll('.dal-sider .ant-menu-submenu-title')]"
        ".find((e) => e.textContent.includes('设置中心')); if (t) t.click(); }"
    )
    pg.wait_for_timeout(900)
    pg.evaluate(
        "() => { const els = [...document.querySelectorAll('.dal-sider .ant-menu-item')];"
        " const el = els.find((e) => e.textContent.includes('设置中心'));"
        " if (el) el.click(); }"
    )
    pg.wait_for_timeout(1000)
    pg.wait_for_selector("text=外观", timeout=25000)
    check("S13 菜单入口→设置中心", "/settings" in pg.url, pg.url)
    shot(pg, "menu_entry")
    pg.close()

    # S14 hub 二级侧栏（设置专属）
    pg = open_path(ctx, "/settings", "text=外观")
    body = pg.inner_text("body")
    check("S14 二级侧栏(通用/服务/Agent)", ("通用" in body and "服务" in body))
    pg.close()

    b.close()

fails = [o for o in OUT if not o[1]]
print(f"\n== 批5 e2e 结果: {len(OUT) - len(fails)}/{len(OUT)} PASS ==")
for f in fails:
    print("FAILED:", f[0], f[2])
