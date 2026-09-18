# -*- coding: utf-8 -*-
"""批8 8.1 写入链路受控往返 + 8.5(c) 快照 diff 硬门（v2）。

前置：scripts/dt_baseline/b8_llm_connections_before.json = 批次前原始快照（5 行，
default=4coding，名='4coding'/'火山 Endpoint·模型2'/...）。

流程（headless 串行，真实 UI 操作，全部在 /llm-config）：
1. 点「deepseek官方」→ 应用 → 断言 default 翻到 deepseek官方（③写入链路生效）；
2. 点「4coding」→ 应用 → 还原；
3. 终态断言：
   a. default=4coding 且唯一；
   b. 连接名还原为原始名（E-28 修正：保存不重写既有名）；
   c. 功能字段（base_url/api_key/model_name/temperature/max_tokens/
      timeout_seconds/enabled/capabilities/provider/capability）与原始快照零差异；
      允许差异仅 extra_config（溯源键 source=llm-config/profile_key 等元数据）。
"""
import json
import os
import sys
import urllib.request
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:28000/api/v1/llm-connections"
PRISTINE = os.path.join(os.path.dirname(__file__), "dt_baseline", "b8_llm_connections_before.json")
FUNC_FIELDS = ["name", "base_url", "api_key", "model_name", "enabled",
               "temperature", "max_tokens", "timeout_seconds",
               "provider", "capability", "capabilities"]


def snapshot():
    with urllib.request.urlopen(BASE, timeout=10) as r:
        return json.load(r)["data"]


def default_row(rows):
    d = [r for r in rows if r["is_default"]]
    return d[0] if d else None


failures = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://localhost:23000/llm-config", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(15000)

    LIST = '[data-testid="service-profile-list-llm"]'
    # 步骤1：点非激活档「火山 Endpoint·模型3」→ 应用（default 翻转，③写入链路生效证明；
    # 注意不能点当前已激活档——draft 不变会跳过③写入）
    pg.locator(LIST).get_by_text("火山 Endpoint·模型3", exact=False).first.click()
    pg.wait_for_timeout(800)
    pg.get_by_role("button", name="应用").first.click()
    pg.wait_for_timeout(4000)
    mid_default = default_row(snapshot())
    if not mid_default or mid_default["name"] != "火山 Endpoint·模型3":
        failures.append(f"步骤1后 default={mid_default and mid_default['name']!r}（期望 火山 Endpoint·模型3）——③写入链路未生效")

    # 步骤2：4coding → 应用（还原；宽松匹配兼容历史脏名 '4coding·glm-5.3-flash'——
    # 新适配器保存时按 connNameFor 约定还原为 '4coding'）
    pg.locator(LIST).get_by_text("4coding", exact=False).first.click()
    pg.wait_for_timeout(800)
    pg.get_by_role("button", name="应用").first.click()
    pg.wait_for_timeout(4000)

    if errs:
        failures.append(f"pageerror×{len(errs)}: {errs[:3]}")
    b.close()

after = snapshot()
pristine = json.load(open(PRISTINE, encoding="utf-8"))["data"]
pm = {r["id"]: r for r in pristine}
am = {r["id"]: r for r in after}

# a. default=4coding 唯一
d = default_row(after)
if not d or d["name"] != "4coding":
    failures.append(f"终态 default 异常: {d and d['name']!r}")
if sum(1 for r in after if r["is_default"]) != 1:
    failures.append("default 不唯一")

# b+c. 行集一致 + 功能字段与原始快照零差异
if set(pm) != set(am):
    failures.append(f"行集漂移: only-before={set(pm)-set(am)} only-after={set(am)-set(pm)}")
for i in set(pm) & set(am):
    for k in FUNC_FIELDS:
        if (pm[i].get(k) or None) != (am[i].get(k) or None):
            failures.append(f"功能字段漂移 id={i} {k}: {pm[i].get(k)!r} -> {am[i].get(k)!r}")

if failures:
    print("B8 LLM SAVE ROUNDTRIP FAIL:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("B8 LLM SAVE ROUNDTRIP PASS: default 翻转生效→还原；名/功能字段与批次前快照零差异")
