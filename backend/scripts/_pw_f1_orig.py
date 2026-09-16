# -*- coding: utf-8 -*-
"""⑤R F1 L4 基准：从用户在看的 30408 原版逐屏截图（对拍基准=用户所见）。"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:30408"
OUT = Path(__file__).resolve().parent / "dt_baseline" / "screens_orig_30408"

PAGES = [
    ("mother-questions", "/mother-questions"),
    ("mother-questions__new", "/mother-questions/new"),
    ("mother-questions__photo", "/mother-questions/photo"),
    ("mother-questions__photo-center", "/mother-questions/photo-center"),
    ("mother-questions__analysis", "/mother-questions/analysis"),
    ("mother-questions__review", "/mother-questions/review"),
    ("mother-questions__trash", "/mother-questions/trash"),
    ("book", "/book"),
    ("settings__curriculum", "/settings/curriculum"),
    ("settings__curriculum__textbooks", "/settings/curriculum/textbooks"),
    ("settings__curriculum__chapters", "/settings/curriculum/chapters"),
    ("settings__curriculum__knowledge-points", "/settings/curriculum/knowledge-points"),
]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for name, path in PAGES:
            try:
                page.goto(BASE + path, wait_until="networkidle", timeout=45000)
            except Exception as e:
                print(f"WAIT-TIMEOUT {name}: {str(e)[:80]}")
            time.sleep(2.5)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
            print(f"OK {name}")
        browser.close()

if __name__ == "__main__":
    main()
