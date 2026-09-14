# -*- coding: utf-8 -*-
"""_pw_llmcaps.py - ③批2 A6：LLM 配置页能力徽标/筛选/表单开关 Playwright 走查+截图。"""
from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        pg.goto("http://localhost:23000/llm-config", timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(5000)
        body = pg.inner_text("body")
        checks = {
            "LLM配置页": "大模型连接" in body,
            "能力位列": "能力位" in body,
            "筛选下拉": pg.query_selector("input[placeholder='按能力筛选']") is not None,
        }
        for k, v in checks.items():
            print(f"[{'PASS' if v else 'FAIL'}] {k}")
        # 徽标渲染：deepseek官方（chat 默认规则 tool_call=true）→「工具」标签可见
        tags = pg.inner_text("body")
        checks2 = {
            "工具徽标": "工具" in tags,
        }
        for k, v in checks2.items():
            print(f"[{'PASS' if v else 'FAIL'}] {k}")
        pg.screenshot(path="scripts/_pw_a6_llmcaps.png", full_page=True)
        b.close()
        print("截图: scripts/_pw_a6_llmcaps.png")


if __name__ == "__main__":
    main()
