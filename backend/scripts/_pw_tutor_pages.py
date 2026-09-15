# -*- coding: utf-8 -*-
"""_pw_tutor_pages.py - 🔴-6（审查 2026-09-15）：tutor 四页干净走查重拍。

对 /e/tutor/{practice,review,wrong-book,progress} 逐页：
  1) 断言无编译覆盖层（"Compiled with problems" 文本 + #webpack-dev-server-client-overlay）
  2) 断言页面渲染锚（AppTabs 页签 label 入 body）
  3) 覆盖截图 scripts/_pw_tutor_{practice,review,wrongbook,progress}.png
前置：前端 23000 + 后端 28000 双活；tutor 卡 enabled=true（走查期临时启用，跑完还原）。
串行纪律：一次只跑一个 Playwright 实例（AGENTS.md 铁律）。
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

PAGES = [
    ("practice", "/e/tutor/practice", ["练习"]),
    ("review", "/e/tutor/review", ["复习"]),
    ("wrongbook", "/e/tutor/wrong-book", ["错题本"]),
    ("progress", "/e/tutor/progress", ["学情"]),
]

OUT = Path(__file__).parent


def main():
    fails = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        for shot, route, anchors in PAGES:
            pg.goto(f"http://localhost:23000{route}", timeout=45000, wait_until="domcontentloaded")
            pg.wait_for_timeout(5000)          # lazy chunk + 拉数
            body = ""
            try:
                body = pg.inner_text("body")
            except Exception:
                pass
            overlay = pg.query_selector("#webpack-dev-server-client-overlay")
            if overlay is not None or "Compiled with problems" in body:
                fails.append(f"{shot}: 编译错误覆盖层在屏")
                pg.screenshot(path=str(OUT / f"_pw_tutor_{shot}.png"))
                continue
            for a in anchors:
                if a not in body:
                    fails.append(f"{shot}: 渲染锚缺失「{a}」")
            pg.screenshot(path=str(OUT / f"_pw_tutor_{shot}.png"))
            print(f"OK {shot} -> _pw_tutor_{shot}.png")
        b.close()
    if fails:
        print("FAIL:")
        for f in fails:
            print(" -", f)
        return 1
    print("四页干净存照全部重拍完成（无编译覆盖层）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
