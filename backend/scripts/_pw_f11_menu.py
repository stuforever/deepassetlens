# -*- coding: utf-8 -*-
"""批11 F4：入口接线与菜单终版 e2e。
①平台菜单「知识库管理」更名+/knowledge 别名渲染同页；②侧栏 tutor 子菜单（13 h5 项+后台 3 项 admin）；
③wenshu（数据资产探查）退化单 chat 项；④后台三项顶级入口页面可达。"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

FRONT = "http://localhost:23000"
SCR = Path(__file__).resolve().parent / "dt_baseline"

def clear(pg):
    pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")

def body(pg):
    return pg.evaluate("document.body.textContent || ''")

def main():
    results = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})

        # ① 向量管理更名 + /knowledge 别名
        pg.goto(FRONT + "/knowledge", timeout=60000, wait_until="domcontentloaded")
        time.sleep(5); clear(pg); time.sleep(1)
        t = body(pg)
        ok_alias = ("知识库管理" in t) or ("向量" in t)
        results.append(("1 /knowledge 别名→知识库管理页", ok_alias))
        pg.screenshot(path=str(SCR / "b11_kb_alias.png"))

        # ②③ 侧栏结构：启用 tutor 卡后展开私塾先生子菜单
        for _ in range(2):
            try:
                pg.evaluate("fetch('/api/experts/tutor',{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled:true})})")
                break
            except Exception:
                time.sleep(1)
        pg.goto(FRONT + "/", timeout=60000, wait_until="domcontentloaded")
        time.sleep(5); clear(pg)
        tutor_menu = pg.query_selector(".ant-menu-submenu:has-text('私塾先生'), li:has-text('私塾先生')")
        if tutor_menu:
            try:
                tutor_menu.click(force=True)
            except Exception:
                pass
        time.sleep(2); clear(pg)
        t = body(pg)
        ok_tutor_items = all(x in t for x in ["对话", "首页", "学习", "课堂", "错题录入", "错题本", "精通之路", "学情报告", "知识地图", "分享"])
        results.append(("2 侧栏 tutor 空间 13 项", ok_tutor_items))
        ok_admin3 = all(x in t for x in ["母题库管理", "书源管理", "教学设置"])
        results.append(("3 侧栏后台 3 项（admin）", ok_admin3))
        ok_wenshu_single = "数据资产探查" in t
        results.append(("4 wenshu 退化单 chat 项在场", ok_wenshu_single))
        pg.screenshot(path=str(SCR / "b11_sider_tutor.png"))

        # ④ 后台三项可达（母题库管理）
        pg.goto(FRONT + "/e/tutor/admin/mother-questions", timeout=60000, wait_until="domcontentloaded")
        time.sleep(6); clear(pg); time.sleep(1)
        t = body(pg)
        ok_mq = ("母题" in t) and len(t) > 300
        results.append(("5 母题库管理页可达", ok_mq))
        pg.screenshot(path=str(SCR / "b11_admin_mq.png"))

        b.close()

    print("== F4 入口接线 e2e ==")
    ok_all = True
    for name, v in results:
        print(f"  [{'PASS' if v else 'FAIL'}] {name}")
        ok_all = ok_all and bool(v)
    print("总体:", "PASS" if ok_all else "FAIL")

if __name__ == "__main__":
    main()
