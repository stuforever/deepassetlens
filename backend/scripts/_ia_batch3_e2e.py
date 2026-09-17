# -*- coding: utf-8 -*-
"""IA批3 e2e：菜单七组重构 + 下拉 bug 三根因修复复测 + 权限显隐 + menuKey 抽查。
运行：python scripts/_ia_batch3_e2e.py（headless 串行；前置：前端 23000 / 后端 28000）"""
import time
from playwright.sync_api import sync_playwright

BASE = "http://localhost:23000"
OUT = []
SHOTS = []


def check(name, ok, detail=""):
    OUT.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + ((" | " + str(detail)) if detail else ""))


def shot(page, name):
    p = f"scripts/_ia_b3_{name}.png"
    page.screenshot(path=p)
    SHOTS.append(p)


def group_labels(page):
    return page.locator(".dal-sider .ant-menu-submenu-title").all_inner_texts()


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    # 批2 经验：预置 h5 欢迎门跳过标记（h5-sheet-overlay 挡点击）
    ctx.add_init_script(
        "try{localStorage.setItem('h5_recent_users', JSON.stringify(['小明']));}catch(e){}"
    )
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    # ── E1 七组静态渲染 ──
    page.goto(BASE + "/", timeout=45000)
    page.wait_for_timeout(4500)
    labels = "\n".join(group_labels(page))
    item_labels = "\n".join(page.locator(".dal-sider .ant-menu-item").all_inner_texts())
    # wenshu 组名=卡名实时取（数据资产探查）；门户为顶层 menu-item（非 submenu-title）
    check("E1 七组齐全(门户+6组)",
          all(k in labels for k in ("数据资产探查", "私塾先生", "私塾先生h5", "技能配置", "后台配置", "设置中心")) and ("专家门户" in item_labels),
          " | ".join(group_labels(page)))
    shot(page, "groups")

    # ── E2 数据探索组展开+平台页跳转 ──
    page.locator(".dal-sider .ant-menu-submenu-title", has_text="数据资产探查").first.click()
    page.wait_for_timeout(800)
    sub = "\n".join(page.locator(".dal-sider .ant-menu-sub").first.all_inner_texts())
    check("E2a wenshu 组 13 项", all(k in sub for k in ("对话", "图谱管理", "四区建模", "资产矩阵", "图库", "实体关系", "主数据", "活动数据", "来源表管理", "映射管理", "数据源", "指标管理", "Doris 配置")), sub[:120])
    page.locator(".dal-sider .ant-menu-sub .ant-menu-item", has_text="图谱管理").first.click()
    page.wait_for_timeout(3500)
    check("E2b 图谱管理跳转/graph", "/graph" in page.url, page.url)
    shot(page, "graph_tab")

    # ── E3 根因1 复测：e: 键路由→所属组自动展开+项高亮 ──
    page.goto(BASE + "/e/tutor-h5/learn", timeout=30000)
    page.wait_for_timeout(4500)
    # 私塾先生h5 组必须处于展开态（子菜单可见）
    h5_group = page.locator(".dal-sider .ant-menu-submenu", has_text="私塾先生h5").first
    h5_expanded = h5_group.locator(".ant-menu-sub").count() > 0
    sel = page.locator(".dal-sider .ant-menu-item-selected").all_inner_texts()
    check("E3 根因1: e:tutor-h5 键→h5 组展开+项选中", h5_expanded and any("自主学习" in s for s in sel), f"expanded={h5_expanded} selected={sel}")
    shot(page, "rootcause1_h5")

    # ── E4 根因3 复测：旧 localStorage 值不串组 ──
    page.evaluate("localStorage.setItem('dal_sider_open_keys', JSON.stringify(['graph_modeling']));localStorage.setItem('dal_sider_open_keys_v2', JSON.stringify(['graph_modeling']));")
    page.goto(BASE + "/e/tutor-h5/learn", timeout=30000)
    page.wait_for_timeout(4500)
    h5_group = page.locator(".dal-sider .ant-menu-submenu", has_text="私塾先生h5").first
    h5_expanded = h5_group.locator(".ant-menu-sub").count() > 0
    check("E4 根因3: 旧 openKeys 残留不串组", h5_expanded, f"expanded={h5_expanded}")

    # ── E5 根因2 复测：卡 API 断网→组不消失（静态名回退） ──
    page2 = ctx.new_page()
    page2.route("**/api/experts**", lambda r: r.abort())
    page2.goto(BASE + "/", timeout=45000)
    page2.wait_for_timeout(5000)
    labels2 = "\n".join(page2.locator(".dal-sider .ant-menu-submenu-title").all_inner_texts())
    check("E5 根因2: 卡拉取失败组仍在(静态名)",
          all(k in labels2 for k in ("数据探索专家", "私塾先生h5", "技能配置", "后台配置")),
          " | ".join(page2.locator(".dal-sider .ant-menu-submenu-title").all_inner_texts()))
    shot(page2, "rootcause2_fallback")
    page2.close()

    # ── E6 menuKey 抽查：平台三键 KeepAlive 页签不丢 ──
    page.goto(BASE + "/metrics", timeout=30000)
    page.wait_for_timeout(3500)
    tabs = page.locator(".dal-tabs .ant-tabs-tab").all_inner_texts() if page.locator(".dal-tabs").count() else page.locator("[class*=tab]").all_inner_texts()
    body = page.inner_text("body")
    check("E6a metric_manager 键=指标管理页签", "指标管理" in body)
    page.goto(BASE + "/llm-config", timeout=30000)
    page.wait_for_timeout(3000)
    check("E6b llmconfig 键=LLM 配置页签", "LLM" in page.inner_text("body"))

    # ── E7 权限显隐（auth=0 匿名=admin 全见）──
    page.goto(BASE + "/", timeout=30000)
    page.wait_for_timeout(3500)
    # 展开私塾先生组→管理三项+伙伴/推送应可见（作用域=该 submenu 容器内的 sub）
    page.locator(".dal-sider .ant-menu-submenu-title", has_text="私塾先生").first.click()
    page.wait_for_timeout(800)
    sub_tutor = "\n".join(
        page.locator(".dal-sider .ant-menu-submenu", has_text="私塾先生").first
        .locator(".ant-menu-sub").last.all_inner_texts()
    )
    check("E7 auth=0 全见(管理三项+伙伴/推送)",
          all(k in sub_tutor for k in ("母题库管理", "书源管理", "教学设置", "伙伴/推送")),
          sub_tutor[:120])
    shot(page, "acl_admin_all")

    # ── E8 技能三键过滤 ──
    page.goto(BASE + "/skills?expert=wenshu", timeout=30000)
    page.wait_for_timeout(4000)
    check("E8a ?expert=wenshu→场景技能列表", "project-lifecycle-cost" in page.inner_text("body") or "lifecycle" in page.inner_text("body"))
    page.goto(BASE + "/skills?expert=tutor", timeout=30000)
    page.wait_for_timeout(4000)
    check("E8b ?expert=tutor→诚实空态", ("暂无" in page.inner_text("body")) or (page.locator(".ant-empty").count() > 0))
    shot(page, "skills_tutor_empty")

    b.close()

fails = [o for o in OUT if not o[1]]
print(f"\n== 批3 e2e 结果: {len(OUT) - len(fails)}/{len(OUT)} PASS ==")
for f in fails:
    print("FAILED:", f[0], f[2])
