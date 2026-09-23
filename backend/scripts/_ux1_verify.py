# -*- coding: utf-8 -*-
"""UX批① 验收探针：问数/私塾 × 门户发送/⌘K 四入口——全部单跳直达、零第二页签、零面板浮层。"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).parent))
BASE = "http://localhost:23000"
R = []


def check(name, ok, detail=""):
    R.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:170], flush=True)


def state(pg):
    return {
        "url": pg.url,
        "tabs": pg.locator("svg[data-icon='close']").count(),
        "panel": pg.locator("[data-testid='nav-panel']").is_visible(),
    }


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    from _pw_login_util import login_page
    pg = login_page(b)
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:100]))

    for expert, marker in (("wenshu", "问数"), ("sishu", "私塾")):
        # 入口 1：门户 Tab+发送
        pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
        pg.wait_for_timeout(5000)
        pg.locator(f"[data-testid='newchat-tabs'] >> text={marker}").first.click()
        pg.wait_for_timeout(400)
        ta = pg.locator("[data-testid='newchat-composer'] textarea").first
        ta.fill("统计用电客户总数")
        ta.press("Enter")
        pg.wait_for_timeout(2500)
        st = state(pg)
        check(f"门户发送 {marker} 单跳直达", f"/e/{expert}/chat" in st["url"] and st["tabs"] == 0 and not st["panel"],
              f"url={st['url'][:60]} tabs={st['tabs']} panel={st['panel']}")

    # 入口 2：⌘K
    for expert, label, marker in (("wenshu", "问数：新建对话", "问数"), ("sishu", "私塾：新建对话", "私塾")):
        pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
        pg.wait_for_timeout(4000)
        pg.keyboard.press("Control+k")
        pg.wait_for_timeout(500)
        pg.locator("[data-testid='cmdk-input']").fill(marker)
        pg.wait_for_timeout(500)
        first = pg.locator("[data-testid='cmdk-item-0']")
        got_label = (first.inner_text().strip().splitlines()[0] if first.count() else "NONE")
        pg.keyboard.press("Enter")
        pg.wait_for_timeout(2500)
        st = state(pg)
        # 批③ 按 path 去重后专家直达=页签项（label=数据探索对话/私塾先生对话，hint=专家俗称）
        ok_label = got_label in ("问数：新建对话", "数据探索对话") if expert == "wenshu" else got_label in ("私塾：新建对话", "私塾先生对话")
        check(f"⌘K {marker} 单跳直达", ok_label and f"/e/{expert}/chat" in st["url"] and st["tabs"] == 0 and not st["panel"],
              f"label={got_label} url={st['url'][:55]} tabs={st['tabs']} panel={st['panel']}")

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    b.close()

fails = [x for x, ok in R if not ok]
print(f"\n=== UX批① 四入口单跳：{len(R) - len(fails)}/{len(R)} PASS ===")
sys.exit(1 if fails else 0)
