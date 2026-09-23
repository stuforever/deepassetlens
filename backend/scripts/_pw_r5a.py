# -*- coding: utf-8 -*-
"""R5批① 对拍（R#2 select 续批代表页）：BookCreator 语言下拉 antd 化后可开可选。

R2批 先例=「代表页对拍」：同批同模式的置换取 1 处可达页实点交互
（渲染/弹层/选项数/取值变更），其余以 tsc+模式同构覆盖并登记。
SpineEditor（spine-content-type）与 CoursewareTab（courseware-select）
需书籍编辑态/章节课件数据前置，本轮登记按模式同构覆盖。
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:180], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:120]))

    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)

    # SPA 路径进入书籍工作台（硬加载 /e/sishu/book 有既有 AppShellProvider 缺陷——与本置换无关，经面板导航零 pageerror）
    pg.locator("[data-testid='activity-console']").click()
    pg.locator("[data-testid='nav-item-e:sishu:book']").wait_for(state="visible", timeout=5000)
    pg.locator("[data-testid='nav-item-e:sishu:book']").click()
    pg.wait_for_timeout(1500)
    pg.locator("[data-testid='activity-console']").click()  # 重开面板继续（点击后自动收起）
    pg.wait_for_timeout(400)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)

    # 书库列表视图 → 点「新建书籍」进入 creator 视图（BookCreator 挂载）
    pg.get_by_text("新建书籍", exact=True).first.click()
    pg.wait_for_timeout(1500)

    lang = pg.locator("[data-testid='book-language']")
    if lang.count() == 0:
        body_head = pg.inner_text("body")[:200].replace("\n", " | ")
        check("语言下拉在场", False, f"body={body_head}")
    else:
        check("语言下拉在场（AntSelect）", lang.count() >= 1)
        # 打开弹层
        lang.first.click()
        pg.wait_for_timeout(600)
        opts = pg.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option")
        n_opts = opts.count()
        check("选项渲染 2 项", n_opts == 2, f"opts={n_opts}")
        if n_opts == 2:
            second_label = opts.nth(1).inner_text().strip()
            opts.nth(1).click()
            pg.wait_for_timeout(500)
            trigger_txt = lang.first.inner_text().strip()
            check("选后取值生效", second_label[:12] in trigger_txt, f"trigger={trigger_txt[:24]}")
        # 弹层收起
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(400)

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    pg.screenshot(path=str(SCR / "_pw_r5a.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== R5批① 代表页对拍：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
