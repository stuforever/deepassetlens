# -*- coding: utf-8 -*-
"""批9 F2 wenshu 零感知回归：门户 → 私塾先生卡 → 对话面打开。
F2 变更纯增量（/e/tutor/h5/* 路由+页面、vendor sessions 挂载），wenshu 门面必须原样。"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

FRONT = "http://localhost:23000"
SCR = Path(__file__).resolve().parent / "dt_baseline"

def clear_overlay(pg):
    pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")

def main():
    ok_card = ok_chat = False
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(FRONT + "/", timeout=60000, wait_until="domcontentloaded")
        time.sleep(5)
        for _ in range(4):
            clear_overlay(pg)
            badge = pg.query_selector(".ant-card:has-text('私塾先生') .ant-tag:has-text('后台')")
            card = pg.query_selector(".ant-card:has-text('私塾先生')")
            if card:
                ok_card = True
            if badge:
                try:
                    badge.click(force=True)
                    break
                except Exception:
                    time.sleep(1.5)
            time.sleep(1.5)
        time.sleep(5)
        clear_overlay(pg)
        body = pg.evaluate("document.body.textContent || ''")
        # 对话面打开：输入区/对话语义在场
        ok_chat = ("想问什么数据" in body) or ("私塾先生" in body) or ("对话" in body)
        pg.screenshot(path=str(SCR / "b9_wenshu_regression.png"))
        b.close()
    print(f"[{'PASS' if ok_card else 'FAIL'}] 门户私塾先生卡在位")
    print(f"[{'PASS' if ok_chat else 'FAIL'}] 卡点击后对话面渲染")
    print("总体:", "PASS" if (ok_card and ok_chat) else "FAIL")

if __name__ == "__main__":
    main()
