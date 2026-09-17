# -*- coding: utf-8 -*-
"""IA批4 4.1 补拍：DT 原仓 30408 知识中心子区块态逐屏（zh-CN 桌面视口）。录完即停。"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:30408"
OUT = Path(__file__).resolve().parent / "dt_baseline" / "screens"
OUT.mkdir(parents=True, exist_ok=True)


def shot(page, name):
    page.screenshot(path=str(OUT / f"knowledge__{name}.png"))
    print(f"OK knowledge__{name}")


def click_first(page, locators, wait=1800):
    """依序尝试一组定位器，点中第一个可见的。"""
    for loc in locators:
        try:
            el = page.locator(loc).first
            el.wait_for(state="visible", timeout=2500)
            el.click()
            page.wait_for_timeout(wait)
            return True
        except Exception:
            continue
    return False


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        page = ctx.new_page()
        page.goto(BASE + "/knowledge", wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)
        shot(page, "home")

        # 建库弹窗
        if click_first(page, ["button:has-text('新建')", "button:has-text('New')", "[role=button]:has-text('新建')"]):
            shot(page, "create_modal")
            page.keyboard.press("Escape")
            page.wait_for_timeout(800)

        # 引擎详情（引擎卡：LlamaIndex 等）
        if click_first(page, ["text=LlamaIndex", "text=GraphRAG", "[class*=engine]"]):
            page.wait_for_timeout(1500)
            shot(page, "engine_detail")
            if click_first(page, ["button:has-text('返回')", "button:has-text('Back')", "button:has-text('←')", "[aria-label*='back' i]"]):
                pass
            page.goto(BASE + "/knowledge", wait_until="networkidle", timeout=45000)
            page.wait_for_timeout(3000)

        # KB 详情（第一张知识库卡）
        if click_first(page, ["text=math-textbook", "text=七年级数学上", "text=三年级语文上", "[class*=kb-card]", "[class*=card]"]):
            page.wait_for_timeout(2500)
            shot(page, "kb_detail")
            # 文档列表态
            shot(page, "documents")
            # 索引版本区
            if click_first(page, ["text=索引版本", "text=Index Versions", "text=版本"], wait=1500):
                shot(page, "index_versions")
            # 更新历史
            if click_first(page, ["text=更新历史", "text=History", "text=历史"], wait=1500):
                shot(page, "update_history")
            # 文件 tab + 文件预览
            if click_first(page, ["text=文件", "text=Files"], wait=1800):
                shot(page, "files_tab")
                if click_first(page, [".cursor-pointer:has-text('.pdf')", "text=.md", "text=.txt", "[class*=file-row] >> nth=1"], wait=2500):
                    shot(page, "file_preview")
            # 返回
            click_first(page, ["button:has-text('返回')", "button:has-text('Back')"])

        # 页索引设置弹窗（建库弹窗内「配置」入口）
        if click_first(page, ["button:has-text('新建')", "button:has-text('New')"]):
            if click_first(page, ["button:has-text('配置')", "button:has-text('Configure')", "text=页索引", "text=PageIndex"], wait=2000):
                shot(page, "pageindex_modal")
        browser.close()


if __name__ == "__main__":
    main()
