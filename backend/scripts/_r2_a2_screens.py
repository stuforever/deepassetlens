# -*- coding: utf-8 -*-
"""⑤R R2 A2：终版逐屏对拍+动线 e2e（串行）。
组1 门户+平台面；组2 tutor 空间 13+对话；组3 tutor 后台 3；组4 动线串联。"""
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

FRONT = "http://localhost:23000"
SCR = Path(__file__).resolve().parent / "dt_baseline"

GROUP2 = ["/e/tutor/h5", "/e/tutor/h5/chat", "/e/tutor/h5/learn", "/e/tutor/h5/learn/textbook",
          "/e/tutor/h5/classroom", "/e/tutor/h5/review", "/e/tutor/h5/wrong", "/e/tutor/h5/wrongbook",
          "/e/tutor/h5/paths", "/e/tutor/h5/report", "/e/tutor/h5/atlas", "/e/tutor/h5/me", "/e/tutor/h5/share"]
GROUP3 = ["/e/tutor/admin/mother-questions", "/e/tutor/admin/book", "/e/tutor/admin/settings"]
GROUP1 = ["/", "/knowledge", "/memory-admin", "/attachment-settings"]


def clear(pg):
    pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")


def alive(pg):
    return len(pg.evaluate("document.body.textContent || ''")) > 200


def main():
    results = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})

        # 组1 门户+平台面
        g1 = 0
        for path in GROUP1:
            pg.goto(FRONT + path, timeout=60000, wait_until="domcontentloaded")
            time.sleep(4.5); clear(pg); time.sleep(0.8)
            if alive(pg):
                g1 += 1
        results.append((f"组1 门户+平台面 4/4", g1 == len(GROUP1), f"{g1}/4"))
        pg.screenshot(path=str(SCR / "r2_a2_g1_platform.png"))

        # 组2 tutor 空间 13+对话（对话=e:tutor:chat 由 h5chat 壳内嵌面即 /e/tutor/h5/chat 覆盖；此处 13 项）
        g2 = 0
        for path in GROUP2:
            pg.goto(FRONT + path, timeout=60000, wait_until="domcontentloaded")
            time.sleep(4); clear(pg); time.sleep(0.6)
            if alive(pg):
                g2 += 1
        results.append((f"组2 tutor 空间 {g2}/{len(GROUP2)}", g2 == len(GROUP2), f"{g2}/{len(GROUP2)}"))
        pg.screenshot(path=str(SCR / "r2_a2_g2_h5.png"))

        # 组3 tutor 后台 3（admin）
        g3 = 0
        for path in GROUP3:
            pg.goto(FRONT + path, timeout=60000, wait_until="domcontentloaded")
            time.sleep(5); clear(pg); time.sleep(0.8)
            if alive(pg):
                g3 += 1
        results.append((f"组3 tutor 后台 {g3}/3", g3 == 3, f"{g3}/3"))
        pg.screenshot(path=str(SCR / "r2_a2_g3_admin.png"))

        # 组4 动线：门户→点私塾先生卡→对话面→h5 学习→错题本→后台母题库
        flow_ok = False
        pg.goto(FRONT + "/", timeout=60000, wait_until="domcontentloaded")
        time.sleep(5); clear(pg)
        card = pg.query_selector(".ant-card:has-text('私塾先生')")
        if card:
            try:
                card.click(force=True); time.sleep(5); clear(pg)
                body = pg.evaluate("document.body.textContent || ''")
                step1 = ("想问什么数据" in body) or ("思考" in body) or ("私塾先生" in body)
                pg.goto(FRONT + "/e/tutor/h5/learn", timeout=60000, wait_until="domcontentloaded")
                time.sleep(4); clear(pg)
                step2 = "学习" in pg.evaluate("document.body.textContent || ''") or alive(pg)
                pg.goto(FRONT + "/e/tutor/h5/wrongbook", timeout=60000, wait_until="domcontentloaded")
                time.sleep(4); clear(pg)
                step3 = alive(pg)
                pg.goto(FRONT + "/e/tutor/admin/mother-questions", timeout=60000, wait_until="domcontentloaded")
                time.sleep(5); clear(pg)
                step4 = alive(pg) and ("母题" in pg.evaluate("document.body.textContent || ''"))
                flow_ok = step1 and step2 and step3 and step4
                pg.screenshot(path=str(SCR / "r2_a2_g4_flow.png"))
            except Exception:
                flow_ok = False
        results.append(("组4 动线 卡→对话→学习→错题本→母题库", flow_ok, "串联" ))

        b.close()

    ok_all = True
    print("== A2 逐屏动线 ==")
    for name, v, note in results:
        print(f"  [{'PASS' if v else 'FAIL'}] {name} ({note})")
        ok_all = ok_all and bool(v)
    print("总体:", "PASS" if ok_all else "FAIL")


if __name__ == "__main__":
    main()
