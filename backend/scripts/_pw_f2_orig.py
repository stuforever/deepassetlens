# -*- coding: utf-8 -*-
"""批9 F2 L4 基准：30408 原版 h5 组逐屏截图（移动视口 390x844——h5 形态）。"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:30408"
OUT = Path(__file__).resolve().parent / "dt_baseline" / "screens_orig_30408_h5"

PAGES = [
    ("h5", "/h5"),
    ("h5__chat", "/h5/chat"),
    ("h5__learn", "/h5/learn"),
    ("h5__learn__textbook", "/h5/learn/textbook"),
    ("h5__classroom", "/h5/classroom"),
    ("h5__review", "/h5/review"),
    ("h5__wrong", "/h5/wrong"),
    ("h5__wrongbook", "/h5/wrongbook"),
    ("h5__paths", "/h5/paths"),
    ("h5__report", "/h5/report"),
    ("h5__atlas", "/h5/atlas"),
    ("h5__me", "/h5/me"),
    ("h5__share", "/h5/share"),
]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        for name, path in PAGES:
            try:
                page.goto(BASE + path, wait_until="networkidle", timeout=45000)
            except Exception:
                print(f"WAIT-TIMEOUT {name}")
            time.sleep(2.5)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
            print(f"OK {name}")
        browser.close()

if __name__ == "__main__":
    main()
