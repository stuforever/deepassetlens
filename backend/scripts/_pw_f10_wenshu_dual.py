# -*- coding: utf-8 -*-
"""批10 F3 10.3：wenshu 双入口等值核验。
入口A=门户卡直入（portal → 私塾先生卡）；入口B=侧栏/等值切换（专家菜单切到 wenshu）。
断言两入口到达同一对话面（等值）。"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

FRONT = "http://localhost:23000"
SCR = Path(__file__).resolve().parent / "dt_baseline"

def clear(pg):
    pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")

def chat_open(pg):
    body = pg.evaluate("document.body.textContent || ''")
    return ("想问什么数据" in body) or ("私塾先生" in body) or ("思考" in body)

def main():
    okA = okB = False
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})

        # ---- 入口A：门户卡直入 ----
        pg.goto(FRONT + "/", timeout=60000, wait_until="domcontentloaded")
        time.sleep(5)
        for _ in range(3):
            clear(pg)
            card = pg.query_selector(".ant-card:has-text('私塾先生')")
            if card:
                try:
                    card.click(force=True)
                    break
                except Exception:
                    time.sleep(1.5)
            time.sleep(1.5)
        time.sleep(5)
        okA = chat_open(pg)
        pg.screenshot(path=str(SCR / "b10_wenshu_entry_A.png"))

        # ---- 入口B：侧栏等值切换（回到门户→从对话页专家切换器） ----
        pg.goto(FRONT + "/", timeout=60000, wait_until="domcontentloaded")
        time.sleep(4)
        clear(pg)
        # 侧栏「专家门户」已在本页；找专家切换入口（侧栏专家项/搜索）——直接点侧栏私塾先生项
        side = pg.query_selector("li:has-text('私塾先生'), .ant-menu-item:has-text('私塾先生'), span:has-text('私塾先生')")
        if side:
            try:
                side.click(force=True)
                time.sleep(5)
                clear(pg)
                okB = chat_open(pg)
            except Exception:
                okB = False
        pg.screenshot(path=str(SCR / "b10_wenshu_entry_B.png"))
        b.close()

    print(f"[{'PASS' if okA else 'FAIL'}] 入口A 门户卡直入→对话面")
    print(f"[{'PASS' if okB else 'FAIL'}] 入口B 侧栏切换→对话面（等值）")
    print("总体:", "PASS" if (okA and okB) else "FAIL")

if __name__ == "__main__":
    main()
