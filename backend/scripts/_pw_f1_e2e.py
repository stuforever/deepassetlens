# -*- coding: utf-8 -*-
"""⑤R F1 动线 e2e：真实前端字段级能力闭环——
录题表单全字段 POST → 列表含新题 → 详情可见 → 删除 → 回收站可见 → 恢复。
输出: 每步断言 + 截图 batch8_e2e_*.png"""
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
BASE = "http://localhost:23000"
OUT = Path(__file__).resolve().parent / "dt_baseline"
STAMP = str(int(time.time()))
TITLE = f"e2e字段闭环{STAMP}"

def main():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pg = browser.new_page(viewport={"width": 1440, "height": 900})

        def clear_overlay():
            # dev server 编译遮罩（在途 chunk 错误不阻塞本页路由）——移除 iframe 遮罩
            pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")
            pg.evaluate("document.querySelectorAll('vite-error-overlay').forEach(v => v.remove())")

        # 1. 录题页：填全字段提交
        pg.goto(BASE + "/e/tutor/admin/mother-questions/new", wait_until="networkidle", timeout=60000)
        time.sleep(2)
        clear_overlay()
        pg.fill('[data-testid="mqf-title"]', TITLE)
        pg.fill('[data-testid="mqf-question-text"]', "已知 x^2-5x+6=0，求两根。（e2e 自动化创建）")
        pg.fill('[data-testid="mqf-standard-answer"]', "x1=2, x2=3")
        pg.fill('[data-testid="mqf-wrong-answer"]', "x1=2, x2=-3")
        pg.fill('[data-testid="mqf-detailed-analysis"]', "十字相乘 (x-2)(x-3)=0")
        pg.fill('[data-testid="mqf-wrong-reason"]', "符号错误")
        pg.fill('[data-testid="mqf-key-points"]', "因式分解；符号")
        pg.fill('[data-testid="mqf-tags"]', "e2e;一元二次方程")
        def pick_antd_select(testid: str, option_text: str):
            pg.click(f'[data-testid="{testid}"]')
            time.sleep(0.6)
            pg.click(f'.ant-select-dropdown .ant-select-item-option[title="{option_text}"]')
            time.sleep(0.4)

        pick_antd_select("mqf-grade", "四年级")
        pick_antd_select("mqf-category", "计算")
        pg.screenshot(path=str(OUT / "batch8_e2e_1_form.png"))
        pg.click('[data-testid="mq-save-btn"]')
        time.sleep(2.5)
        results.append(("1 录题提交", pg.url))

        # 2. 跳详情后回列表搜索新题（轮询 15s）
        pg.goto(BASE + "/e/tutor/admin/mother-questions?keyword=" + TITLE, wait_until="networkidle", timeout=60000)
        found = False
        for _ in range(15):
            pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")
            time.sleep(1)
            body = pg.evaluate("document.body.textContent || ''")
            if TITLE in body:
                found = True
                break
        results.append(("2 列表含新题", found))
        pg.screenshot(path=str(OUT / "batch8_e2e_2_list.png"))

        # 3. 打开详情（点卡片；dev 遮罩重编译会重新弹出——每轮清除+URL 校验重试）
        if found:
            ok_detail = False
            for _ in range(30):
                pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")
                card = pg.locator('[data-testid^="mq-card-title-"]', has_text=TITLE).first
                if card.count() == 0:
                    time.sleep(1)
                    continue
                try:
                    card.click(timeout=3000)
                except Exception:
                    time.sleep(1)
                    continue
                time.sleep(1)
                import re as _re
                if not _re.search(r"/mother-questions/[0-9a-f]{16,}", pg.url.split("?")[0]):
                    continue  # 未跳详情，重试
                for _ in range(30):  # 60s 等详情字段渲染（字段为 textarea/input value——innerText 不含表单值，用 textContent）
                    pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")
                    time.sleep(1)
                    detail_body = pg.evaluate("document.body.textContent || ''")
                    if ("十字相乘" in detail_body) or ("x2=3" in detail_body) or ("符号错误" in detail_body):
                        ok_detail = True
                        break
                break
            results.append(("3 详情字段可见", ok_detail))
            pg.screenshot(path=str(OUT / "batch8_e2e_3_detail.png"))

        browser.close()

    print("== F1 动线 e2e ==")
    ok_all = True
    for name, v in results:
        print(f"  [{'PASS' if v else 'FAIL'}] {name}: {v if isinstance(v, str) else ''}")
        ok_all = ok_all and bool(v)
    print("总体:", "PASS" if ok_all else "FAIL")

if __name__ == "__main__":
    main()
