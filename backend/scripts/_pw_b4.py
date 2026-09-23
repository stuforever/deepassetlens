# -*- coding: utf-8 -*-
"""批④ 对拍（计划 Task 7 Step 3 / v4 §六）：ChatPanel 历史分类四层+搜索+查看全部。

断言账：
1  按专家分组（问数组含标记会话；今天/本周/更早三时间桶在场）
2  搜索过滤（唯一子串→1 行；乱串→无匹配）
3  置顶即时生效（⋯菜单→置顶→📌组在场+localStorage）+ reload 后保持
4  收藏即时生效（填充001→⭐组在场+localStorage）
5  >30 条截断（可见 30 行+「查看全部」按钮）→ 点击破截（行数>30）
6  零 pageerror 收尾 + 截图

种子：localStorage 注入 33 条平台会话（di_sessions_freeplan_v1；1 标记+32 填充零 padded）——
Playwright 每次全新 context，跑完即弃无清理负担、零 LLM 负载。
"""
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
RESULTS = []
MARKER = "批④置顶收藏验证会话XYZQ"
FILLER = "批④填充会话{:03d}"
NOW = int(time.time() * 1000)
DAY = 86_400_000


def seed_sessions() -> list:
    out = [{
        "id": "b4_seed_marker", "title": MARKER, "expertId": "wenshu",
        "messages": [{"role": "user", "content": "hi"}],
        "confirmed": {}, "flags": {}, "thinkStream": [], "pendingCandidates": [],
        "finalTokens": [], "createdAt": NOW,
    }]
    for i in range(1, 33):
        # 1=1h前(今天) 2-10=2~6天前(本周) 11-32=10~41天前(更早)
        age = DAY // 24 if i == 1 else (i * 0.6 * DAY if i <= 10 else (i + 3) * DAY)
        out.append({
            "id": f"b4_seed_{i:03d}", "title": FILLER.format(i), "expertId": "wenshu",
            "messages": [{"role": "user", "content": "hi"}],
            "confirmed": {}, "flags": {}, "thinkStream": [], "pendingCandidates": [],
            "finalTokens": [], "createdAt": int(NOW - age),
        })
    return out


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:180], flush=True)


def open_chat(pg):
    pg.locator("[data-testid='activity-chat']").click()
    pg.locator("[data-testid='chat-panel']").wait_for(state="visible", timeout=5000)
    pg.wait_for_timeout(600)


def row_menu_click(pg, row, label):
    row.hover()
    pg.wait_for_timeout(400)
    row.locator("[data-testid='chat-panel-row-more']").click()
    pg.wait_for_timeout(500)
    pg.get_by_role("menuitem", name=label, exact=True).click()
    pg.wait_for_timeout(500)


def row_in_layer(pg, needle: str, layer_testid: str):
    """结构判定：needle 行沿祖先向上找，任一祖先容器的直接子节点里含 layer_testid 分组标题。

    组件契约：分组 testid 挂在标题 div 上，行是标题的兄弟节点——置顶层无中间包裹、
    专家层隔一层时间桶容器，故向上多走几层（上限 6）按容器判定。
    返回 True/False/NO_ROW。
    """
    return pg.evaluate(
        """([needle, testid]) => {
          const rows = [...document.querySelectorAll('[data-testid="chat-panel-session-row"]')];
          const row = rows.find(r => r.innerText.includes(needle));
          if (!row) return 'NO_ROW';
          let el = row;
          for (let i = 0; i < 6 && el; i++) {
            el = el.parentElement;
            if (!el) break;
            if ([...el.children].some(c => c.getAttribute && c.getAttribute('data-testid') === testid)) return true;
          }
          return false;
        }""",
        [needle, layer_testid],
    )


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)  # auth=ON 登录态
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:120]))

    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    pg.evaluate("(s) => localStorage.setItem('di_sessions_freeplan_v1', s)", json.dumps(seed_sessions(), ensure_ascii=False))
    pg.reload(timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)

    # ① 按专家分组 + 时间桶
    open_chat(pg)
    wenshu_group = pg.locator("[data-testid='hist-group-expert-wenshu']")
    check("问数组在场", wenshu_group.count() == 1)
    check("标记会话在问数组", row_in_layer(pg, MARKER, "hist-group-expert-wenshu") is True)
    for bk in ("today", "week", "earlier"):
        check(f"时间桶[{bk}]在场", pg.locator(f"[data-testid='hist-bucket-wenshu-{bk}']").count() >= 1)

    # ② 搜索过滤
    inp = pg.locator("[data-testid='chat-panel-search']")
    inp.fill("XYZQ")
    pg.wait_for_timeout(500)
    n_hit = pg.locator("[data-testid='chat-panel-session-row']").count()
    check("搜索唯一命中", n_hit == 1 and MARKER in pg.locator("[data-testid='chat-panel-session-row']").first.inner_text(), f"rows={n_hit}")
    inp.fill("绝不存在的会话ZZZ")
    pg.wait_for_timeout(500)
    check("搜索空态提示", "无匹配会话" in pg.locator("[data-testid='chat-panel']").inner_text())
    inp.fill("")
    pg.wait_for_timeout(500)

    # ③ 置顶即时生效 + reload 保持
    marker_row = pg.locator("[data-testid='chat-panel-session-row']").filter(has_text=MARKER).first
    row_menu_click(pg, marker_row, "置顶")
    pinned_group = pg.locator("[data-testid='hist-group-pinned']")
    check("置顶即时生效（📌层含标记）", pinned_group.count() == 1 and row_in_layer(pg, MARKER, "hist-group-pinned") is True)
    pin_ls = pg.evaluate("() => localStorage.getItem('hist:pinned')")
    check("置顶写 localStorage", pin_ls and "b4_seed_marker" in pin_ls, str(pin_ls)[:60])
    pg.reload(timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    open_chat(pg)
    pinned_group = pg.locator("[data-testid='hist-group-pinned']")
    check("reload 后置顶保持", pinned_group.count() == 1 and row_in_layer(pg, MARKER, "hist-group-pinned") is True)

    # ④ 收藏即时生效（填充001——注意置顶行不进收藏层，用另一条）
    inp = pg.locator("[data-testid='chat-panel-search']")
    inp.fill("批④填充会话001")
    pg.wait_for_timeout(500)
    f1_row = pg.locator("[data-testid='chat-panel-session-row']").filter(has_text=FILLER.format(1)).first
    row_menu_click(pg, f1_row, "收藏")
    inp.fill("")
    pg.wait_for_timeout(500)
    fav_group = pg.locator("[data-testid='hist-group-fav']")
    check("收藏即时生效（⭐层含填充001）", fav_group.count() == 1 and row_in_layer(pg, FILLER.format(1), "hist-group-fav") is True)
    fav_ls = pg.evaluate("() => localStorage.getItem('hist:fav')")
    check("收藏写 localStorage", fav_ls and "b4_seed_001" in fav_ls, str(fav_ls)[:60])

    # ⑤ >30 截断 → 查看全部
    n_rows = pg.locator("[data-testid='chat-panel-session-row']").count()
    expand_btn = pg.locator("[data-testid='hist-expand']")
    check("30 条截断生效", n_rows == 30, f"rows={n_rows}")
    check("查看全部按钮在场", expand_btn.count() == 1, expand_btn.inner_text()[:40] if expand_btn.count() else "")
    expand_btn.click()
    pg.wait_for_timeout(600)
    n_all = pg.locator("[data-testid='chat-panel-session-row']").count()
    check("破截后行数>30", n_all > 30, f"rows={n_all}")

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    pg.screenshot(path=str(SCR / "_pw_b4.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== 批④ 对拍：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
