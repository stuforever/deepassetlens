# -*- coding: utf-8 -*-
"""LLM 设置修复 e2e：工具栏单渲染 / 复制档→保存→应用→落库→删除→清场 / 模型名 trim。"""
import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(__file__).parent
BASE = "http://localhost:23000"
API = "http://localhost:28000/api/v1"
R = []


def check(name, ok, detail=""):
    R.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:220], flush=True)


def conn_names():
    with urllib.request.urlopen(f"{API}/llm-connections") as r:
        d = json.load(r)
    return {row["name"]: row for row in d["data"]}


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(SCR))
    from _pw_login_util import login_page
    pg = login_page(b)
    pg.set_viewport_size({"width": 1920, "height": 1080})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)[:150]))

    pg.goto(BASE + "/settings/llm", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)

    # ① 双工具栏修复
    n_save = pg.evaluate("() => Array.from(document.querySelectorAll('button')).filter(x => x.innerText.trim()==='保存草稿').length")
    check("T1 工具栏单渲染（保存草稿=1）", n_save == 1, f"count={n_save}")

    # ② 复制按钮在场
    dup_btn = pg.locator("[data-testid='service-duplicate-profile-llm']")
    check("T2 复制按钮在场", dup_btn.count() >= 1)

    # ③ 复制 4coding 档（选它→复制→草稿出现 副本）
    pg.get_by_text("4coding", exact=True).first.click()
    pg.wait_for_timeout(1200)
    dup_btn.click()
    pg.wait_for_timeout(1200)
    copy_in_draft = pg.get_by_text("4coding 副本", exact=True).count()
    check("T3 复制产生草稿档「4coding 副本」", copy_in_draft >= 1, f"hits={copy_in_draft}")

    # ④ 保存草稿点亮并可点
    save_btn = pg.locator("[data-testid='settings-save-btn']").first
    enabled = save_btn.is_enabled()
    check("T4 保存草稿已点亮", enabled)
    if enabled:
        save_btn.click()
        pg.wait_for_timeout(2500)

    # ⑤ 应用 → 落库
    apply_btn = pg.locator("[data-testid='settings-apply-btn']").first
    if apply_btn.count() and apply_btn.is_enabled():
        apply_btn.click()
        pg.wait_for_timeout(3000)
    names = conn_names()
    check("T5 副本已落库（连接行出现）", "4coding 副本" in names, str(list(names)[:8]))
    row = names.get("4coding 副本")
    check("T6 副本字段完整（base_url/model）", bool(row) and row["base_url"].startswith("https://ark.cn-beijing") and row["model_name"], (row or {}).get("model_name", ""))

    # ⑦ trim 实测：给副本模型名加尾随空格→保存→应用→读回应已 strip
    if row:
        model_input = pg.locator("input[placeholder='gpt-4o']").first
        model_input.fill("glm-5.3-flash ")
        pg.wait_for_timeout(400)
        pg.locator("[data-testid='settings-save-btn']").first.click()
        pg.wait_for_timeout(2500)
        pg.locator("[data-testid='settings-apply-btn']").first.click()
        pg.wait_for_timeout(3000)
        names2 = conn_names()
        val = (names2.get("4coding 副本") or {}).get("model_name", "")
        check("T7 模型名尾随空格已 trim", val == "glm-5.3-flash", repr(val))

        # ⑧ 清场：删副本→保存→应用→连接行消失
        pg.get_by_text("4coding 副本", exact=True).first.click()
        pg.wait_for_timeout(800)
        pg.locator("[data-testid='service-delete-profile-llm']").click()
        pg.wait_for_timeout(800)
        pg.locator("[data-testid='settings-save-btn']").first.click()
        pg.wait_for_timeout(2500)
        pg.locator("[data-testid='settings-apply-btn']").first.click()
        pg.wait_for_timeout(3000)
        names3 = conn_names()
        check("T8 删除副本后连接行清场", "4coding 副本" not in names3)

    # 用户两条连接仍在且未受扰
    final = conn_names()
    check("T9 智谱/DeepSeek 连接未受扰", "Zhipu AI" in final and "deepseek官方" in final)

    check("零 pageerror", len(errors) == 0, str(errors[:2]))
    pg.screenshot(path=str(SCR / "_llm_e2e.png"), full_page=True)
    b.close()

fails = [x for x, ok in R if not ok]
print(f"\n=== LLM 设置 e2e：{len(R) - len(fails)}/{len(R)} PASS ===")
sys.exit(1 if fails else 0)
