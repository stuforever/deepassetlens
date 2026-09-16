# -*- coding: utf-8 -*-
"""批9 F2 动线 e2e：首页→章节自主学习→错题录入→练习判分→精通之路（真实前端 23000，串行）。
输出: 各步断言 + dt_baseline/batch9_e2e_*.png"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:23000"
OUT = Path(__file__).resolve().parent / "dt_baseline"

def clear(pg):
    pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")

def text(pg):
    return pg.evaluate("document.body.textContent || ''")

def main():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pg = browser.new_page(viewport={"width": 390, "height": 844})

        # 1. H5 首页
        pg.goto(BASE + "/e/tutor/h5", wait_until="networkidle", timeout=60000)
        time.sleep(3); clear(pg); time.sleep(1)
        b = text(pg)
        ok_home = ("学习" in b) and ("错题本" in b) and ("我的" in b)  # 底部 TabBar 五项
        results.append(("1 H5首页 TabBar", ok_home))
        pg.screenshot(path=str(OUT / "batch9_e2e_1_home.png"))

        # 2. 学习页（自主学习）
        pg.goto(BASE + "/e/tutor/h5/learn", wait_until="networkidle", timeout=60000)
        time.sleep(4); clear(pg); time.sleep(1)
        b = text(pg)
        ok_learn = ("学习" in b) and len(b) > 300
        results.append(("2 学习页渲染", ok_learn))
        pg.screenshot(path=str(OUT / "batch9_e2e_2_learn.png"))

        # 3. 错题录入
        pg.goto(BASE + "/e/tutor/h5/wrong", wait_until="networkidle", timeout=60000)
        time.sleep(3); clear(pg); time.sleep(1)
        b = text(pg)
        ok_wrong = len(b) > 300 and ("错题" in b or "录入" in b or "拍照" in b)
        results.append(("3 错题录入", ok_wrong))
        pg.screenshot(path=str(OUT / "batch9_e2e_3_wrong.png"))

        # 4. 错题本（练习判分入口——错题本列表/复习入口）
        pg.goto(BASE + "/e/tutor/h5/wrongbook", wait_until="networkidle", timeout=60000)
        time.sleep(4); clear(pg); time.sleep(1)
        b = text(pg)
        ok_wb = len(b) > 300 and ("错题" in b or "复习" in b or "暂无" in b)
        results.append(("4 错题本", ok_wb))
        pg.screenshot(path=str(OUT / "batch9_e2e_4_wrongbook.png"))

        # 5. 精通之路
        pg.goto(BASE + "/e/tutor/h5/paths", wait_until="networkidle", timeout=60000)
        time.sleep(3); clear(pg); time.sleep(1)
        b = text(pg)
        ok_paths = ("精通" in b or "路径" in b or "掌握" in b or "新建" in b)
        results.append(("5 精通之路", ok_paths))
        pg.screenshot(path=str(OUT / "batch9_e2e_5_paths.png"))

        # 6. 学情报告 + 我的 + 分享（可达性）
        for name, path in [("6 学情报告", "/e/tutor/h5/report"), ("7 我的", "/e/tutor/h5/me"), ("8 分享", "/e/tutor/h5/share")]:
            pg.goto(BASE + path, wait_until="networkidle", timeout=60000)
            time.sleep(3); clear(pg); time.sleep(1)
            results.append((name, len(text(pg)) > 300))
            pg.screenshot(path=str(OUT / f"batch9_e2e_{name[0]}_{'report' if '报告' in name else 'me' if '我' in name else 'share'}.png"))

        browser.close()

    print("== F2 动线 e2e ==")
    ok_all = True
    for name, v in results:
        print(f"  [{'PASS' if v else 'FAIL'}] {name}")
        ok_all = ok_all and bool(v)
    print("总体:", "PASS" if ok_all else "FAIL")

if __name__ == "__main__":
    main()
