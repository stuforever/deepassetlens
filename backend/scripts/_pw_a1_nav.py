# -*- coding: utf-8 -*-
"""A-1 步骤 5：导航接线 Playwright 验收（admin 态三断言+动线）。

auth=0 基线（anonymous=admin）——admin 态可验；user 态断言（无后台入口）延 B-3 登录
动线批（auth=1 时补验，诚实账）。tutor 卡走查期临时启用→还原（批0 惯例）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:28000"
FRONT = "http://localhost:23000"
SCR = Path(__file__).parent
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


# 走查期临时启用 tutor
requests.patch(f"{BASE}/api/experts/tutor", json={"enabled": True}, timeout=20)

try:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})

        # 断言1：侧栏 tutor 子菜单（对话+四页+后台——admin 态）
        pg.goto(f"{FRONT}/", timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(5000)
        # 展开专家组（点 tutor 父项）——先看父项在不在
        tutor_parent = pg.query_selector(".ant-menu-submenu:has-text('教学专家'), li:has-text('tutor')")
        body = pg.inner_text("body")
        # tutor 卡名（中文名「教学专家」还是别的？拿卡名）
        card_name = requests.get(f"{BASE}/api/experts/tutor", timeout=20).json()
        card_name = (card_name.get("data", card_name) or {}).get("name") or "tutor"
        check("侧栏含 tutor 卡项", card_name in body, f"卡名={card_name}")
        # 点击 tutor 父项展开子菜单
        parent_li = pg.query_selector(f"li.ant-menu-submenu:has-text('{card_name}')")
        if parent_li:
            parent_li.click()
            pg.wait_for_timeout(1200)
        sub = pg.inner_text("body")
        for label in ("对话", "练习", "复习", "错题本", "学情", "后台"):
            check(f"侧栏子项[{label}]", label in sub)
        pg.screenshot(path=str(SCR / "_pw_a1_sider_admin.png"))

        # 断言2：wenshu 等值分支（admin 态=对话+后台，无功能页 chips）
        wenshu_name = "数据资产探查"
        w_li = pg.query_selector(f"li.ant-menu-submenu:has-text('{wenshu_name}')")
        if w_li:
            w_li.click()
            pg.wait_for_timeout(1200)
            w_text = pg.inner_text(f"li.ant-menu-submenu:has-text('{wenshu_name}')")
            ok = ("对话" in w_text) and ("后台" in w_text) and ("练习" not in w_text)
            check("wenshu 等值分支（对话+后台/无功能页）", ok, w_text.replace("\n", "|")[:90])
        else:
            check("wenshu 等值分支", False, "父项未找到")
        pg.screenshot(path=str(SCR / "_pw_a1_sider_wenshu.png"))

        # 断言3：门户 tutor 卡 chips+suggestions+点击预填动线
        pg.goto(f"{FRONT}/", timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(5000)
        body = pg.inner_text("body")
        for label in ("练习", "复习", "错题本", "学情", "后台"):
            check(f"门户 chips[{label}]", label in body)
        check("门户 suggestions[出三道几何练习]", "出三道几何练习" in body)
        pg.screenshot(path=str(SCR / "_pw_a1_portal.png"))
        # 点 suggestion→预填
        sugg = pg.query_selector("text=出三道几何练习")
        if sugg:
            sugg.click()
            pg.wait_for_timeout(4000)
            # 预填断言：composer 输入框（按 placeholder 定位——页面存在多个 textarea）
            ta = pg.query_selector("textarea[placeholder*='想问'], textarea[placeholder*='问什么']")
            if not ta:
                tas = pg.query_selector_all("textarea.ant-input:visible")
                ta = tas[-1] if tas else None
            val = ta.input_value() if ta else ""
            check("建议点击→chat 预填", val == "出三道几何练习", f"input={val!r}")
            pg.screenshot(path=str(SCR / "_pw_a1_prefill.png"))
        else:
            check("建议点击→chat 预填", False, "建议元素未找到")

        # 断言4：admin 页可达（后台角标/侧栏后台项→/e/tutor/admin 渲染）
        pg.goto(f"{FRONT}/e/tutor/admin", timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(4000)
        admin_body = pg.inner_text("body")
        check("后台页渲染（卡总览）", ("tutor 后台" in admin_body) and ("专家卡" in admin_body))
        pg.screenshot(path=str(SCR / "_pw_a1_admin_page.png"))
        b.close()
finally:
    # 还原（惯例）
    requests.patch(f"{BASE}/api/experts/tutor",
                   json={"enabled": False, "close_reason": "A-1 走查毕还原（导航接线验收）"}, timeout=20)

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== A-1 验收汇总：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
