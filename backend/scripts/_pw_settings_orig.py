# -*- coding: utf-8 -*-
"""IA批5 补拍：DT 原仓 30408 设置中心 31 页逐屏（zh-CN 桌面视口）。"""
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:30408"
OUT = Path(__file__).resolve().parent / "dt_baseline" / "screens"
OUT.mkdir(parents=True, exist_ok=True)

PAGES = [
    ("settings", "/settings"),
    ("settings-agents", "/settings/agents"),
    ("settings-agents-claude-code", "/settings/agents/claude-code"),
    ("settings-agents-codex", "/settings/agents/codex"),
    ("settings-agents-gemini", "/settings/agents/gemini"),
    ("settings-agents-kimi", "/settings/agents/kimi"),
    ("settings-agents-mimo", "/settings/agents/mimo"),
    ("settings-agents-opencode", "/settings/agents/opencode"),
    ("settings-appearance", "/settings/appearance"),
    ("settings-attachments", "/settings/attachments"),
    ("settings-capabilities", "/settings/capabilities"),
    ("settings-chat", "/settings/chat"),
    ("settings-curriculum", "/settings/curriculum"),
    ("settings-curriculum-chapters", "/settings/curriculum/chapters"),
    ("settings-curriculum-knowledge-points", "/settings/curriculum/knowledge-points"),
    ("settings-curriculum-textbooks", "/settings/curriculum/textbooks"),
    ("settings-document-parsing", "/settings/document-parsing"),
    ("settings-embedding", "/settings/embedding"),
    ("settings-image", "/settings/image"),
    ("settings-llm", "/settings/llm"),
    ("settings-mcp", "/settings/mcp"),
    ("settings-memory", "/settings/memory"),
    ("settings-mineru", "/settings/mineru"),
    ("settings-models", "/settings/models"),
    ("settings-network", "/settings/network"),
    ("settings-search", "/settings/search"),
    ("settings-status", "/settings/status"),
    ("settings-stt", "/settings/stt"),
    ("settings-tools", "/settings/tools"),
    ("settings-tts", "/settings/tts"),
    ("settings-video", "/settings/video"),
]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN").new_page()
        for name, path in PAGES:
            try:
                page.goto(BASE + path, wait_until="networkidle", timeout=40000)
            except Exception:
                print(f"WAIT-TIMEOUT {name}")
            time.sleep(2.0)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
            print(f"OK {name}")
        browser.close()


if __name__ == "__main__":
    main()
