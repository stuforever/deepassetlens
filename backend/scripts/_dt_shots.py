# -*- coding: utf-8 -*-
"""批1 1.4：原仓逐屏截图底册——headless 串行，一屏一文件（含全部子页面）。

用法：python _dt_shots.py 3   （只拍前 3 屏探针）；不带参=全量静态 75 屏。"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright  # noqa: E402

BASE = Path(__file__).resolve().parent / "dt_baseline"
SCR = BASE / "screens"
SCR.mkdir(parents=True, exist_ok=True)
WEB = "http://localhost:3782"

ROUTES = [
    "/", "/admin/users", "/login", "/register",
    "/agents", "/knowledge", "/notebook", "/profile",
    "/memory", "/memory/graph", "/memory/l1", "/memory/l2", "/memory/l3", "/memory/resolve",
    "/settings", "/settings/agents", "/settings/agents/claude-code", "/settings/agents/codex",
    "/settings/agents/gemini", "/settings/agents/kimi", "/settings/agents/mimo", "/settings/agents/opencode",
    "/settings/appearance", "/settings/attachments", "/settings/capabilities", "/settings/chat",
    "/settings/curriculum", "/settings/curriculum/chapters", "/settings/curriculum/knowledge-points",
    "/settings/curriculum/textbooks", "/settings/document-parsing", "/settings/embedding", "/settings/image",
    "/settings/llm", "/settings/mcp", "/settings/memory", "/settings/mineru", "/settings/models",
    "/settings/network", "/settings/search", "/settings/status", "/settings/stt", "/settings/tools",
    "/settings/tts", "/settings/video",
    "/space", "/space/chat-history", "/space/cli-apps", "/space/learning", "/space/mcp",
    "/space/notebooks", "/space/personas", "/space/questions", "/space/skills",
    "/book", "/co-writer", "/home", "/mother-questions", "/mother-questions/analysis",
    "/mother-questions/new", "/mother-questions/photo", "/mother-questions/photo-center",
    "/mother-questions/review", "/mother-questions/trash", "/partners", "/partners/new",
    "/playground", "/self-learning",
    "/h5", "/h5/atlas", "/h5/chat", "/h5/classroom", "/h5/learn", "/h5/learn/textbook", "/h5/me",
    "/h5/paths", "/h5/report", "/h5/review", "/h5/share", "/h5/wrong", "/h5/wrongbook",
]
(SCR / "_routes.json").write_text(
    json.dumps(ROUTES, ensure_ascii=False, indent=1), encoding="utf-8") if False else None

limit = int(sys.argv[1]) if len(sys.argv) > 1 else len(ROUTES)
prefix = sys.argv[2] if len(sys.argv) > 2 else ""
if prefix:
    ROUTES = [r for r in ROUTES if r == prefix or r.startswith(prefix + "/") or (prefix == "/" and r == "/")]
results = []
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    for r in ROUTES[:limit]:
        fname = (r.strip("/").replace("/", "__") or "root") + ".png"
        try:
            pg.goto(WEB + r, timeout=45000, wait_until="domcontentloaded")
            pg.wait_for_timeout(3500)
            pg.screenshot(path=str(SCR / fname), full_page=False)
            body = pg.inner_text("body")[:120].replace("\n", "|")
            url = pg.url
            results.append((r, "OK", url[-40:], body[:80]))
            print(f"OK   {r}  -> {url[:60]}  {body[:60]}", flush=True)
        except Exception as e:
            results.append((r, "FAIL", "", str(e)[:80]))
            print(f"FAIL {r}  {str(e)[:80]}", flush=True)
        time.sleep(0.3)
    b.close()
ok = sum(1 for x in results if x[1] == "OK")
print(f"\n=== 逐屏探针/截图：{ok}/{len(results)} ===")
