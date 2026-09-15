# -*- coding: utf-8 -*-
"""A-2 步骤 2：卡配置面 Playwright 验收（编辑闭环/版本+1/校验上屏）。

user 不可达断言：auth=0 下 user 角色不可模拟——RequireAdmin 代码在位+admin 正常通过，
user 态断言延 B-3（诚实账）。
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


def card_version():
    d = requests.get(f"{BASE}/api/experts/tutor", timeout=20).json()
    return (d.get("data", d) or {}).get("version")


v0 = card_version()
requests.patch(f"{BASE}/api/experts/tutor", json={"enabled": True}, timeout=20)

try:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        # 真实动线：门户 → wenshu 卡「后台」角标点击进入（goto 直达冷加载的 tab 竞态=
        # 存量 KeepAlive 架构直达刷新边界，A-1 前已存在，登记后续批统一收敛）
        pg.goto(f"{FRONT}/", timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(5000)
        # tutor 卡（私塾先生）内的后台角标（卡顺序不稳定——限定卡容器）
        badge = pg.query_selector(".ant-card:has-text('私塾先生') .ant-tag:has-text('后台')")
        if badge:
            badge.click()
            pg.wait_for_timeout(4000)
        body = pg.inner_text("body")
        check("编辑面渲染（表单/总览）", ("专家卡配置（编辑面）" in body) and ("槽配置" in body))
        check("工具选项=活注册表", "活注册表" in body)
        pg.screenshot(path=str(SCR / "_pw_a2_admin_edit.png"))

        # 编辑闭环：suggestions 第一行改文→保存→版本+1→重载后值在
        sugg_changed = False
        first_input = pg.query_selector("input[maxlength='120']")
        if first_input:
            first_input.fill("出三道几何练习（A-2 改）")
            pg.wait_for_timeout(300)
            save = pg.query_selector("button:has-text('保存卡配置')")
            if save:
                save.click()
                pg.wait_for_timeout(3000)
                v1 = card_version()
                check("保存→卡版本+1", isinstance(v1, int) and v1 > v0, f"v0={v0} v1={v1}")
                # 重载后值在（编辑闭环=改→校验→生效）——AntD 两字按钮插空格（「重 载」）
                pg.click("button:has-text('重 载'), button:has-text('重载')")
                pg.wait_for_timeout(2000)
                v2 = pg.input_value("input[maxlength='120']")
                check("编辑生效（改后值回显）", v2 == "出三道几何练习（A-2 改）", f"input={v2!r}")
                sugg_changed = True
        if not sugg_changed:
            check("保存→卡版本+1", False, "编辑元素未找到")

        # 校验上屏：enabled 关闭→短理由→warning 上屏（①红级校验前端预检）
        sw = pg.query_selector(".ant-switch")
        if sw:
            sw.click()
            pg.wait_for_timeout(800)
            ta = pg.query_selector("textarea[placeholder*='关停理由']")
            if ta:
                ta.fill("太短")
            ok_btn = pg.query_selector("button:has-text('确认关停')")
            if ok_btn:
                ok_btn.click()
                pg.wait_for_timeout(800)
                msg = pg.inner_text("body")
                check("非法值被拦上屏（理由<10 字 warning）", "至少 10 字" in msg)
        # 确保卡仍启用（供后续批走查）——直接 API 置位
        requests.patch(f"{BASE}/api/experts/tutor", json={"enabled": True}, timeout=20)
        pg.screenshot(path=str(SCR / "_pw_a2_validate.png"))
        b.close()
finally:
    requests.patch(f"{BASE}/api/experts/tutor",
                   json={"enabled": False, "close_reason": "A-2 走查毕还原（卡配置面验收）"}, timeout=20)

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== A-2 验收汇总：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
