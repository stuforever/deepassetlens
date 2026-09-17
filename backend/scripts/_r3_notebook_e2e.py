# -*- coding: utf-8 -*-
"""⑤R R3 笔记本页 e2e：/e/tutor/notebook 渲染+分类管理+筛选交互（串行）。"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SCR = Path(__file__).resolve().parent / "dt_baseline"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}", flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})

    # 1. 页面可达+渲染
    pg.goto("http://localhost:23000/e/tutor/notebook", timeout=60000, wait_until="domcontentloaded")
    time.sleep(6)
    pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")
    time.sleep(1)
    body = pg.evaluate("document.body.innerText || ''")
    check("笔记本页可达", "题库" in body and "跨会话回顾和整理测验题目" in body, body[:80].replace("\n", "|"))

    # 2. 空态/列表结构
    has_empty = "暂无题目" in body
    has_list = "总计" in body
    check("空态或列表结构在位", has_empty or has_list, f"empty={has_empty} list={has_list}")

    # 3. 三态筛选 chips
    chips = all(k in body for k in ("全部", "已收藏", "仅错题"))
    check("三态筛选 chips", chips)

    # 4. 分类管理：展开→新建→重命名→清理
    pg.click("text=管理分类")
    time.sleep(2.0)
    pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")
    time.sleep(0.8)
    # placeholder 属性不入 innerText——以输入框存在性判面板展开
    cat_input = pg.query_selector("input[placeholder='新分类名称...']")
    check("分类管理面板展开", cat_input is not None and cat_input.is_visible())
    ts = str(int(time.time()))[-6:]
    cat_name = f"对拍分类{ts}"
    pg.fill("input[placeholder='新分类名称...']", cat_name)
    pg.press("input[placeholder='新分类名称...']", "Enter")
    time.sleep(1.5)
    body3 = pg.evaluate("document.body.innerText || ''")
    check("分类新建成功", cat_name in body3, cat_name)
    pg.screenshot(path=str(SCR / "r3_notebook_page.png"))

    # 5. API 侧验证分类真落库
    import requests
    cats = requests.get("http://127.0.0.1:28000/api/v1/question-notebook/categories", timeout=15).json()
    hit = any(c.get("name") == cat_name for c in cats)
    check("分类 API 落库验证", hit, f"{len(cats)} 分类")
    new_id = next((c["id"] for c in cats if c.get("name") == cat_name), None)

    # 6. 分类 chip 出现在筛选栏
    body4 = pg.evaluate("document.body.innerText || ''")
    check("分类 chip 进筛选栏", cat_name in body4)

    # 7. 清理（删除分类——面板内删除按钮）
    if new_id:
        requests.delete(f"http://127.0.0.1:28000/api/v1/question-notebook/categories/{new_id}", timeout=15)
    cats2 = requests.get("http://127.0.0.1:28000/api/v1/question-notebook/categories", timeout=15).json()
    check("分类删除 API 通路", not any(c.get("id") == new_id for c in cats2) if new_id else True)

    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== 笔记本页 e2e：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
