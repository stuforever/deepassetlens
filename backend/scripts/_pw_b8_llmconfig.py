# -*- coding: utf-8 -*-
"""批8 8.5(b) e2e 硬门：/llm-config 渲染③连接目录行（llmDirectory 适配器数据面）。

断言：
1. /llm-config 打开无崩（无 text: 应用错误/error boundary）；
2. 配置列表（aside）渲染出③ 5 行（profile 名=连接名）：4coding/火山 Endpoint·模型2/
   火山 Endpoint·模型3/deepseek官方/glm-embedding-default；
3. 默认档高亮=4coding（active_profile_id=is_default 行）；
4. 4coding 档 base_url 展示（ark.cn-beijing.volces.com/api/coding/v3）；
5. 模型 chip 显示 glm-5.3-flash；
6. 截图存照 scripts/dt_baseline/screens/b8_llmconfig.png。
"""
import sys
from playwright.sync_api import sync_playwright

EXPECT_PROFILES = ["4coding", "火山 Endpoint·模型2", "火山 Endpoint·模型3", "deepseek官方", "glm-embedding-default"]

failures = []

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto("http://localhost:23000/llm-config", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(12000)  # vendor settings + ③目录 + 渲染
    body = pg.inner_text("body")

    # 1 无崩
    if "应用错误" in body or "Error boundary" in body:
        failures.append("页面崩溃（错误边界文案在场）")

    # 2 ③行渲染
    for name in EXPECT_PROFILES:
        if name not in body:
            failures.append(f"③行未渲染: {name}")

    # 3 默认档=4coding（ServiceConfigEditor L473：激活行带 data-active 属性）
    active = pg.locator('[data-testid="service-profile-list-llm"] [data-active]').all_inner_texts()
    if not any("4coding" in t for t in active):
        failures.append("激活态未指向 4coding（data-active 行无 4coding 文本）")

    # 4/5 字段值
    if "ark.cn-beijing.volces.com" not in body:
        failures.append("4coding base_url 未展示")
    if "glm-5.3-flash" not in body:
        failures.append("模型 glm-5.3-flash 未展示")

    pg.screenshot(path="scripts/dt_baseline/screens/b8_llmconfig.png")

    if errors:
        failures.append(f"pageerror×{len(errors)}: {errors[:3]}")
    b.close()

if failures:
    print("B8 LLMCONFIG FAIL:")
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("B8 LLMCONFIG PASS: ③5行渲染+4coding默认档+base_url/模型字段+截图 b8_llmconfig.png")
