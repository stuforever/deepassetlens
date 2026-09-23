# -*- coding: utf-8 -*-
"""批⑤ 种子：问数 8 场景技能骨架（v4§3.2）——经 /api/v2/skills 契约格式（与技能管理页表单同源）。

幂等：按 skill_code 存在即跳过。创建后逐个发布（published——技能下拉只列已发布场景技能）。
契约骨架=描述承载模板牢笼（数据面/输出形态/禁止项）；明细契约由技能版本文件后续迭代。
运行：python backend/scripts/_seed_scenario_skills.py
"""
import json
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = "http://127.0.0.1:28000"

SKILLS = [
    ("scenarios/wenshu-data-overview", "数据概览", "场景契约：输入=时间范围（可选）；输出=KPI 卡（总数/新增/占比）+趋势图；模板牢笼=只允许聚合口径，禁明细行罗列。"),
    ("scenarios/wenshu-detail-query", "明细查询", "场景契约：输入=筛选条件（字段+值）；输出=明细表+命中计数+可导出；模板牢笼=SELECT 指定列+WHERE+LIMIT，禁聚合改写。"),
    ("scenarios/wenshu-compare", "对比分析", "场景契约：输入=两对象或两时段；输出=对比表+差值/差率+结论行；模板牢笼=两列对齐结构，禁混合口径。"),
    ("scenarios/wenshu-trend", "趋势占比", "场景契约：输入=时间粒度（日/周/月）；输出=趋势序列+占比构成；模板牢笼=时间连续聚合，禁跨粒度混算。"),
    ("scenarios/wenshu-anomaly", "异常排查", "场景契约：输入=指标+阈值；输出=异常清单+定位维度+建议下钻；模板牢笼=先定位后归因，禁无依据断言。"),
    ("scenarios/wenshu-lineage", "血缘追溯", "场景契约：输入=表或字段名；输出=上下游链路（层级）+影响面；模板牢笼=仅基于图谱/血缘关系，禁猜测补充。"),
    ("scenarios/wenshu-metric-explain", "指标解读", "场景契约：输入=指标名；输出=口径定义+数据来源+近期趋势；模板牢笼=口径优先，禁跳过定义直接给数。"),
    ("scenarios/wenshu-customer-visit", "客户巡访", "场景契约：输入=客户清单/区域；输出=巡访要点卡（基础信息+近期动态+关注项）；模板牢笼=只汇总既有记录，禁编造走访结论。"),
]


def get_token() -> str:
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        from _pw_login_util import login_page
        pg = login_page(b)
        tok = pg.evaluate("() => JSON.parse(localStorage.getItem('tupu.oidc')).access_token")
        b.close()
        return tok


def call(method: str, path: str, token: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def main() -> None:
    tok = get_token()
    existing = call("GET", "/api/v2/skills?limit=500", tok).get("data") or []
    have = {s.get("skill_code") for s in existing}
    created, skipped = [], []
    for code, name, desc in SKILLS:
        if code in have:
            skipped.append(code)
            continue
        r = call("POST", "/api/v2/skills", tok, {
            "name": name,
            "skill_code": code,
            "description": desc,
            "skill_type": "claude",
            "type": "scenario",
        })
        sid = (r.get("data") or {}).get("skill_id")
        call("POST", f"/api/v2/skills/{sid}/publish", tok)
        created.append(code)
    print(f"created={len(created)} skipped={len(skipped)}")
    for c in created:
        print("  +", c)
    for c in skipped:
        print("  =", c)


if __name__ == "__main__":
    main()
