# -*- coding: utf-8 -*-
"""⑤R F1 L4 逐屏对拍取证：headless 打开 tupu 前端 /e/tutor/admin/* 逐页截图。
用法: python _pw_f1_l4.py  (串行逐页, 23000 前端)"""
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
BASE = "http://localhost:23000"
OUT = Path(__file__).resolve().parent / "dt_baseline" / "screens_tupu_f1"

PAGES = [
    ("mother-questions", "/e/tutor/admin/mother-questions"),
    ("mother-questions__new", "/e/tutor/admin/mother-questions/new"),
    ("mother-questions__photo", "/e/tutor/admin/mother-questions/photo"),
    ("mother-questions__photo-center", "/e/tutor/admin/mother-questions/photo-center"),
    ("mother-questions__analysis", "/e/tutor/admin/mother-questions/analysis"),
    ("mother-questions__review", "/e/tutor/admin/mother-questions/review"),
    ("mother-questions__trash", "/e/tutor/admin/mother-questions/trash"),
    ("book", "/e/tutor/admin/book"),
    ("settings__curriculum", "/e/tutor/admin/settings"),
]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for name, path in PAGES:
            page.goto(BASE + path, wait_until="networkidle", timeout=60000)
            time.sleep(2.5)
            # 移除 dev 遮罩（eslint 警告非阻塞——confirm 保原仓契约的等价替换）
            page.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")
            time.sleep(0.4)
            out = OUT / f"{name}.png"
            page.screenshot(path=str(out), full_page=False)
            print(f"OK {name} <- {path}")
        browser.close()

if __name__ == "__main__":
    main()
