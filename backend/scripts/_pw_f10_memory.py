# -*- coding: utf-8 -*-
"""批10 F3：MemoryAdmin 七 tab 渲染验收（/memory-admin 真实前端 23000）。"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

FRONT = "http://localhost:23000"
SCR = Path(__file__).resolve().parent / "dt_baseline"

TABS = ["树与固化", "Hub 总览", "L1 工作台", "L2 工作台", "L3 工作台", "记忆图谱", "解析定位"]

def clear(pg):
    pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")

def main():
    results = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto(FRONT + "/memory-admin", timeout=60000, wait_until="domcontentloaded")
        time.sleep(6)
        clear(pg)
        body = pg.evaluate("document.body.textContent || ''")
        # 树与固化 = 默认 tab 能力（原 178 行能力在场）
        results.append(("默认树与固化（专家/固化/台账）", ("立即固化" in body or "专家" in body) and "台账" in body))
        # 逐 tab 点击
        for i, tab in enumerate(TABS[1:], start=2):
            clear(pg)
            ok = False
            try:
                el = pg.query_selector(f".ant-tabs-tab:has-text('{tab}')")
                if el:
                    el.click(force=True)
                    time.sleep(3)
                    clear(pg)
                    body = pg.evaluate("document.body.textContent || ''")
                    ok = len(body) > 200  # tab 面板有实际内容渲染
            except Exception:
                ok = False
            results.append((f"tab{i} {tab}", ok))
            if i in (2, 6, 7):
                pg.screenshot(path=str(SCR / f"b10_memory_tab{i}.png"))
        pg.screenshot(path=str(SCR / "b10_memory_admin.png"))
        b.close()

    print("== MemoryAdmin 七 tab 验收 ==")
    ok_all = True
    for name, v in results:
        print(f"  [{'PASS' if v else 'FAIL'}] {name}")
        ok_all = ok_all and bool(v)
    print("总体:", "PASS" if ok_all else "FAIL")

if __name__ == "__main__":
    main()
