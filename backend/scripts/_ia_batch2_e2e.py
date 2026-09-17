# -*- coding: utf-8 -*-
"""IA 件批2 2.4 验收 e2e（Playwright headless 串行）：
A 老会话归组：localStorage 注入无 expertId 旧会话 → 归数据探索组（裁定④）
B 三分组渲染：数据探索/私塾先生/私塾先生h5 组头齐全；当前路由组展开置顶
C tutor 组新建 → /e/tutor/chat 欢迎页
D h5 组 vendor 真操作：发消息建会话 → 组内出现 → 点击恢复(?session=) → 重命名 → 删除
auth=0 匿名直进。截图落 scripts/_ia_b2_*.png。"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:23000"
OUT = Path(__file__).parent
results = []
LEGACY_TITLE = "IA批2旧会话-无expertId"


def shot(page, name):
    page.screenshot(path=str(OUT / f"_ia_b2_{name}.png"))
    return f"_ia_b2_{name}.png"


def check(label, ok, detail=""):
    results.append((label, ok, detail))
    print(("PASS " if ok else "FAIL ") + label + (" | " + str(detail) if detail else ""))


LEGACY = [
    {
        "id": "free_legacy_ia2_1",
        "title": LEGACY_TITLE,
        "messages": [{"id": "m1", "role": "user", "text": "旧会话第一条"}],
        "confirmed": {}, "flags": {}, "thinkStream": [], "pendingCandidates": [],
        "lastResponse": None, "finalTokens": [], "createdAt": int(time.time() * 1000) - 86400000,
    }
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    # 预置 h5 身份：跳过「欢迎使用」浮层（h5-sheet-overlay 会拦截全部点击）
    ctx.add_init_script("try { localStorage.setItem('h5_recent_users', JSON.stringify(['小明'])); } catch (e) {}")

    # A+B：注入旧会话 → 门户 → 三组渲染 + 旧会话归数据探索组
    page = ctx.new_page()
    page.goto(f"{BASE}/", timeout=30000)
    page.evaluate("""(sessions) => localStorage.setItem('di_sessions_freeplan_v1', JSON.stringify(sessions))""", LEGACY)
    page.goto(f"{BASE}/e/wenshu/chat", timeout=30000)
    page.wait_for_timeout(4000)
    body = page.inner_text("body")
    shot(page, "groups_wenshu")
    check("A+B1 三组组头齐全", all(k in body for k in ("数据资产探查", "私塾先生h5")))
    check("A+B2 旧会话归数据探索组", LEGACY_TITLE in body)
    page.close()

    # B3 tutor 组新建按钮 → /e/tutor/chat
    page = ctx.new_page()
    page.goto(f"{BASE}/e/tutor-h5", timeout=30000)
    page.wait_for_timeout(3500)
    # 私塾先生组头旁的新建按钮（会话组顺序钉死：数据资产探查(0)/私塾先生(1)/私塾先生h5(2)；
    # has_text 子串会误命中「私塾先生h5」——改用索引）
    plus = page.locator(".dal-sider .anticon-plus").nth(1)
    plus.click(timeout=8000)
    page.wait_for_timeout(3000)
    check("B3 tutor 组新建→tutor chat 欢迎页", "/e/tutor/chat" in page.url, page.url)
    shot(page, "new_tutor")
    page.close()

    # D：h5 组 vendor 真操作（发消息→建会话→列表→恢复→改名→删除）
    page = ctx.new_page()
    page.goto(f"{BASE}/e/tutor-h5/chat", timeout=30000)
    page.wait_for_timeout(3500)
    page.on("dialog", lambda d: d.accept("IA批2改名会话"))
    # ① 发一条消息（真实 vendor 会话创建；文本带时间戳标记防跨跑串扰）
    MSG = f"帮我出两道圆柱体积的练习题 IA{int(time.time())}"
    tb = page.locator("textarea:visible").first
    tb.fill(MSG)
    page.keyboard.press("Enter")
    page.wait_for_timeout(8000)  # 会话落库（标题要等首轮回复完成才更新，行定位不用标题）
    shot(page, "h5_chat_sent")
    check("D0 消息回显在对话页", MSG in page.inner_text("body"))
    page.goto(f"{BASE}/e/tutor-h5", timeout=30000)  # 路径变化触发 AppSider 刷新 h5 组
    page.wait_for_timeout(2000)
    # 折叠组不渲染行 → DOM 中 .dal-session-row 全属展开的 tutor-h5 组；first=updated_at 最新
    try:
        page.wait_for_selector(".dal-session-row", timeout=15000)
    except Exception:
        pass
    n_rows = page.locator(".dal-session-row").count()
    shot(page, "h5_group_new_session")
    check("D1 h5 组出现 vendor 新会话", n_rows > 0, f"rows={n_rows}")
    # ② 点击恢复（?session= 深链）——最新行=刚建的会话
    row = page.locator(".dal-session-row").first
    row.click(timeout=8000)
    page.wait_for_timeout(6000)
    check("D2 点击恢复→/e/tutor-h5/chat?session=", "session=" in page.url, page.url)
    shot(page, "h5_restore")
    # ③ 重命名（dialog 已挂 accept→改名为「IA批2改名会话」；行定位用最新行，不用标题）
    page.goto(f"{BASE}/e/tutor-h5", timeout=30000)
    page.wait_for_timeout(3500)
    row = page.locator(".dal-session-row").first
    row.hover()
    row.locator(".anticon-edit").click(timeout=8000)
    page.wait_for_timeout(2000)
    body = page.inner_text("body")
    check("D3 重命名生效", "IA批2改名会话" in body)
    # ④ 删除（Popconfirm——点确认按钮）
    page.on("dialog", lambda d: d.accept())
    row2 = page.locator(".dal-session-row", has_text="IA批2改名会话").first
    row2.hover()
    row2.locator(".anticon-close").click(timeout=8000)
    page.wait_for_timeout(1200)
    confirm = page.locator(".ant-popconfirm-buttons button").last
    confirm.click(timeout=8000)
    page.wait_for_timeout(2500)
    body = page.inner_text("body")
    shot(page, "h5_after_delete")
    check("D4 删除生效", "IA批2改名会话" not in body)
    page.close()

    browser.close()

fails = [r for r in results if not r[1]]
print(f"\n== 批2 e2e 汇总: {len(results) - len(fails)}/{len(results)} PASS ==")
sys.exit(1 if fails else 0)
