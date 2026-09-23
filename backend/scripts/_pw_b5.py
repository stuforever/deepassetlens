# -*- coding: utf-8 -*-
"""批⑤ 对拍（计划 Task 9 Step 3 / v4§三·§四）：技能场景分型 + 问数角色接入。

断言账：
1  ⚡技能下拉只列场景技能（8 问数场景骨架在场；通用/私塾 deepagent 技能不出现）
2  🎭角色下拉三卡（默认分析师/业务白话型/技术 detail 型）
3  角色选择记忆（选业务白话型→reload→保持）
4  SkillManagerV2 场景分型筛选+卡片场景标签
5  业务白话型问答交付（流式回答到达——语气人工核=截图 _pw_b5.png）
6  零 pageerror
登记：追问 chips 联动场景推荐（§七C）需技能注册表推荐问法字段（后端二期），本轮豁免登记。
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
RESULTS = []

SCENARIO_NAMES = {"数据概览", "明细查询", "对比分析", "趋势占比", "异常排查", "血缘追溯", "指标解读", "客户巡访"}
FOREIGN_SAMPLES = ("私塾先生·出题", "私塾先生·解题", "定位", "关系查询")


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

    # ①② wenshu 附件条：技能/角色下拉
    pg.goto(BASE + "/e/wenshu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    skill_sel = pg.locator("[data-testid='attach-skill']")
    check("技能选择器在场", skill_sel.count() == 1)
    skill_sel.click()
    pg.wait_for_timeout(800)
    opts = pg.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option")
    labels = [opts.nth(i).inner_text().strip() for i in range(opts.count())]
    hit = SCENARIO_NAMES & set(labels)
    foreign = [f for f in FOREIGN_SAMPLES if any(f in x for x in labels)]
    check("技能下拉=8 场景骨架", len(hit) == 8, f"hit={sorted(hit)}/labels={labels[:6]}")
    check("通用/deepagent 技能不出现", len(foreign) == 0, f"foreign={foreign}")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)

    role_sel = pg.locator("[data-testid='attach-role']")
    check("角色选择器在场（wenshu）", role_sel.count() == 1)
    role_sel.click()
    pg.wait_for_timeout(800)
    r_opts = pg.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option")
    r_labels = [r_opts.nth(i).inner_text().strip() for i in range(r_opts.count())]
    check("角色三卡在场", any("默认" in x for x in r_labels) and any("业务白话型" in x for x in r_labels) and any("技术" in x for x in r_labels), str(r_labels))
    r_opts.nth(1).click() if "业务白话型" not in r_labels[0] else r_opts.nth(0).click()
    pg.wait_for_timeout(400)
    # 点中「业务白话型」（上一步若首个即业务白话型则已选）
    if not any("业务白话型" in x for x in [pg.locator("[data-testid='attach-role']").inner_text()]):
        role_sel.click()
        pg.wait_for_timeout(600)
        pg.locator(".ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item-option").filter(
            has_text="业务白话型").first.click()
        pg.wait_for_timeout(400)
    check("角色选后 chip=业务白话型", "业务白话型" in pg.locator("[data-testid='attach-role']").inner_text())

    # ③ reload 记忆
    pg.reload(timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    check("角色 reload 记忆", "业务白话型" in pg.locator("[data-testid='attach-role']").inner_text(),
          pg.locator("[data-testid='attach-role']").inner_text()[:30])
    role_ls = pg.evaluate("() => localStorage.getItem('attach:wenshu:role')")
    check("角色写 localStorage", role_ls == '"business_plain"' or "business_plain" in str(role_ls), str(role_ls))

    # ④ SkillManagerV2 场景分型
    pg.goto(BASE + "/skills", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    scen_tags = pg.locator(".ant-tag:has-text('场景')")
    check("管理页场景标签在场（≥8）", scen_tags.count() >= 8, f"tags={scen_tags.count()}")

    # ⑤ 业务白话型问答交付（语气人工核=截图）
    pg.goto(BASE + "/e/wenshu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    ta = pg.locator("textarea").first
    ta.fill("统计用电客户总数")
    ta.press("Enter")
    got = False
    t0 = time.time()
    while time.time() - t0 < 600:
        body = pg.inner_text("body")
        if ("已准备好答案" in body) or ("推理完成" in body) or (pg.locator("[data-testid^='msg-actions']").count() > 0):
            got = True
            break
        pg.wait_for_timeout(3000)
    check("业务白话型问答交付", got, f"waited={int(time.time()-t0)}s（语气人工核=截图）")

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    pg.screenshot(path=str(SCR / "_pw_b5.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== 批⑤ 对拍：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
