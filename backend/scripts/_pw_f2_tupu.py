# -*- coding: utf-8 -*-
"""批9 F2 L4：tupu 23000 复刻屏截图（390x844 移动视口，与 _pw_f2_orig 同清单同口径）。"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:23000"
OUT = Path(__file__).resolve().parent / "dt_baseline" / "screens_tupu_f2"

PAGES = [
    ("h5", "/e/tutor/h5"),
    ("h5__chat", "/e/tutor/h5/chat"),
    ("h5__learn", "/e/tutor/h5/learn"),
    ("h5__learn__textbook", "/e/tutor/h5/learn/textbook"),
    ("h5__classroom", "/e/tutor/h5/classroom"),
    ("h5__review", "/e/tutor/h5/review"),
    ("h5__wrong", "/e/tutor/h5/wrong"),
    ("h5__wrongbook", "/e/tutor/h5/wrongbook"),
    ("h5__paths", "/e/tutor/h5/paths"),
    ("h5__report", "/e/tutor/h5/report"),
    ("h5__atlas", "/e/tutor/h5/atlas"),
    ("h5__me", "/e/tutor/h5/me"),
    ("h5__share", "/e/tutor/h5/share"),
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
            page.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
            print(f"OK {name}")
        browser.close()

if __name__ == "__main__":
    main()
