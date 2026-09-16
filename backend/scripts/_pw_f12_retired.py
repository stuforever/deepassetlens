# -*- coding: utf-8 -*-
"""批12 R1：先行版退役路由动线——/e/tutor/practice 等已不在路由表，落 * 兜底=专家门户。"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

FRONT = "http://localhost:23000"
SCR = Path(__file__).resolve().parent / "dt_baseline"

def clear(pg):
    pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")

def main():
    ok_all = True
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        for path, name in [("/e/tutor/practice", "practice"), ("/e/tutor/admin", "admin")]:
            pg.goto(FRONT + path, timeout=60000, wait_until="domcontentloaded")
            time.sleep(5); clear(pg); time.sleep(1)
            body = pg.evaluate("document.body.textContent || ''")
            # 兜底=专家门户（先行版练习页/旧后台骨架不再渲染）
            ok = "专家门户" in body
            print(f"  [{'PASS' if ok else 'FAIL'}] /e/tutor/{name} → 兜底专家门户")
            ok_all = ok_all and ok
        pg.screenshot(path=str(SCR / "b12_retired_fallback.png"))
        b.close()
    print("总体:", "PASS" if ok_all else "FAIL")

if __name__ == "__main__":
    main()
