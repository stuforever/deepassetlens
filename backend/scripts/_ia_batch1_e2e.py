# -*- coding: utf-8 -*-
"""IA 件批1 1.5 验收 e2e（Playwright headless 串行）：
A 门户三卡可见（wenshu/tutor/tutor-h5）
B 三空间 chat 可达（/e/wenshu/chat、/e/tutor/chat、/e/tutor-h5/chat 开屏）
C 旧 URL 别名 4 条命中（/e/tutor/h5/learn、/e/tutor/h5、/e/tutor/notebook、/e/tutor/h5/paths/xxx 含参→书路径）
auth=0（计划 §二常态），匿名直进。截图落 scripts/_ia_b1_*.png。"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:23000"
OUT = Path(__file__).parent
results = []


def shot(page, name):
    page.screenshot(path=str(OUT / f"_ia_b1_{name}.png"))
    return f"_ia_b1_{name}.png"


def check(label, ok, detail=""):
    results.append((label, ok, detail))
    print(("PASS " if ok else "FAIL ") + label + (" | " + detail if detail else ""))


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})

    # A 门户三卡
    page = ctx.new_page()
    page.goto(f"{BASE}/", timeout=30000)
    page.wait_for_timeout(4000)
    body = page.inner_text("body")
    shot(page, "portal")
    check("A1 门户卡-数据资产探查", "数据资产探查" in body)
    check("A2 门户卡-私塾先生", "私塾先生" in body)
    check("A3 门户卡-私塾先生h5", "私塾先生h5" in body)
    page.close()

    # B 三空间 chat
    for slug, marker in (("wenshu", "想问什么数据"), ("tutor", ""), ("tutor-h5", "")):
        pg = ctx.new_page()
        pg.goto(f"{BASE}/e/{slug}/chat", timeout=30000)
        pg.wait_for_timeout(3500)
        txt = pg.inner_text("body")
        dead = ("无法显示" in txt) or ("此页面不可用" in txt) or ("ERR_" in txt)
        check(f"B {slug} chat 可达", not dead and len(txt) > 80, f"len={len(txt)}")
        shot(pg, f"chat_{slug}")
        pg.close()

    # C 旧 URL 别名 4 条
    # C1 /e/tutor/h5/learn → 学习页（H5Shell 底部导航 + 学习内容）
    pg = ctx.new_page()
    pg.goto(f"{BASE}/e/tutor/h5/learn", timeout=30000)
    pg.wait_for_timeout(3500)
    txt = pg.inner_text("body")
    check("C1 旧URL /e/tutor/h5/learn 命中学习页", ("学习" in txt and "首页" in txt and "错题本" in txt) and "404" not in txt)
    shot(pg, "alias_learn")
    pg.close()
    # C2 /e/tutor/h5 → 首页
    pg = ctx.new_page()
    pg.goto(f"{BASE}/e/tutor/h5", timeout=30000)
    pg.wait_for_timeout(3500)
    txt = pg.inner_text("body")
    check("C2 旧URL /e/tutor/h5 命中h5首页", ("首页" in txt and "错题本" in txt and "我的" in txt) and "404" not in txt)
    shot(pg, "alias_home")
    pg.close()
    # C3 /e/tutor/notebook → 笔记本
    pg = ctx.new_page()
    pg.goto(f"{BASE}/e/tutor/notebook", timeout=30000)
    pg.wait_for_timeout(3500)
    txt = pg.inner_text("body")
    check("C3 旧URL /e/tutor/notebook 命中笔记本", ("笔记本" in txt or "题库" in txt) and "404" not in txt)
    shot(pg, "alias_notebook")
    pg.close()
    # C4 含参 /e/tutor/h5/paths/xxx → 书路径页签（页面开屏即算命中——无书时也有空态/报错文案而非 404 路由）
    pg = ctx.new_page()
    pg.goto(f"{BASE}/e/tutor/h5/paths/seed-book-1", timeout=30000)
    pg.wait_for_timeout(3500)
    txt = pg.inner_text("body")
    check("C4 含参旧URL /e/tutor/h5/paths/xxx 命中书路径路由", ("精通之路" in txt or "返回" in txt or "书路径" in txt or "欢迎使用" in txt) and "404" not in txt)
    shot(pg, "alias_pathbook")
    pg.close()

    browser.close()

fails = [r for r in results if not r[1]]
print(f"\n== 批1 e2e 汇总: {len(results) - len(fails)}/{len(results)} PASS ==")
sys.exit(1 if fails else 0)
