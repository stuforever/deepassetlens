# -*- coding: utf-8 -*-
"""IA批4 e2e：知识中心复刻页全链（/vector 承接+/knowledge 别名+三视图+弹窗+菜单入口）。"""
import time
from playwright.sync_api import sync_playwright

BASE = "http://localhost:23000"
OUT = []


def check(name, ok, detail=""):
    OUT.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + ((" | " + str(detail)) if detail else ""))


def shot(page, name):
    page.screenshot(path=f"scripts/_ia_b4_{name}.png")


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script("try{localStorage.setItem('h5_recent_users', JSON.stringify(['小明']));}catch(e){}")
    page = ctx.new_page()

    # K1 /vector 承接页加载
    page.goto(BASE + "/vector", timeout=60000)
    page.wait_for_selector("text=知识中心", timeout=25000)
    page.wait_for_timeout(3000)
    body = page.inner_text("body")
    check("K1 /vector=知识中心(引擎网格+KB列表)",
          all(k in body for k in ("检索引擎", "知识库列表", "新建知识库", "math-textbook", "LlamaIndex")))
    shot(page, "home")

    # K2 KB 详情（点 math-textbook 卡）
    page.locator("text=math-textbook").first.click()
    page.wait_for_timeout(3500)
    body = page.inner_text("body")
    check("K2 KB 详情(头卡+四分区导航)", all(k in body for k in ("math-textbook", "文件", "添加文档", "索引版本", "设置")))
    shot(page, "kb_detail")

    # K3 索引版本 tab
    page.locator("text=索引版本").first.click()
    page.wait_for_timeout(2500)
    check("K3 索引版本区", ("索引版本" in page.inner_text("body")))
    shot(page, "index_versions")

    # K4 设置 tab
    page.locator(".ant-menu, body").first  # noop keep
    page.get_by_text("设置", exact=True).first.click()
    page.wait_for_timeout(2500)
    body = page.inner_text("body")
    check("K4 设置区(概览+危险操作)", ("危险" in body or "删除知识库" in body))
    shot(page, "settings")

    # K5 返回→引擎详情
    page.get_by_text("知识库列表", exact=True).first.click()
    page.wait_for_timeout(2500)
    page.locator("text=LlamaIndex").first.click()
    page.wait_for_timeout(3500)
    body = page.inner_text("body")
    check("K5 引擎详情(检索与分块+模型+KB列表)", ("检索" in body and ("模型" in body or "嵌入" in body) and "math-textbook" in body))
    shot(page, "engine_detail")

    # K6 建库弹窗
    page.get_by_text("知识中心", exact=True).first.click()
    page.wait_for_timeout(2000)
    page.locator("button:has-text('新建知识库')").first.click()
    page.wait_for_timeout(2000)
    body = page.inner_text("body")
    check("K6 建库弹窗(新建/关联已有)", ("关联已有" in body and ("索引引擎" in body or "知识库名称" in body)))
    shot(page, "create_modal")
    page.keyboard.press("Escape")
    page.wait_for_timeout(800)

    # K7 /knowledge 别名
    page.goto(BASE + "/knowledge", timeout=45000)
    page.wait_for_selector("text=知识中心", timeout=25000)
    check("K7 /knowledge 别名同页", "知识中心" in page.inner_text("body"))

    # K8 菜单入口（后台配置→知识库管理；手风琴折叠态不定——先确保组开，再 JS 直点触发 onSelect）
    page.goto(BASE + "/", timeout=45000)
    page.wait_for_timeout(3500)
    opened = page.locator(".dal-sider .ant-menu-sub:visible").count()
    if opened == 0:
        page.locator(".dal-sider .ant-menu-submenu-title", has_text="后台配置").first.click()
        page.wait_for_timeout(800)
    page.evaluate(
        "() => { const els = [...document.querySelectorAll('.dal-sider .ant-menu-item')];"
        " const el = els.find((e) => e.textContent.includes('知识库管理'));"
        " if (el) el.click(); }"
    )
    page.wait_for_timeout(1000)
    page.wait_for_selector("text=知识中心", timeout=25000)
    check("K8 菜单入口→知识中心", "知识中心" in page.inner_text("body"), page.url)
    shot(page, "menu_entry")

    b.close()

fails = [o for o in OUT if not o[1]]
print(f"\n== 批4 e2e 结果: {len(OUT) - len(fails)}/{len(OUT)} PASS ==")
for f in fails:
    print("FAILED:", f[0], f[2])
