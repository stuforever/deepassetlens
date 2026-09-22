# -*- coding: utf-8 -*-
"""批⓪ 红色基线：v4§九 四功能缺失（会话删除/重命名/停止生成/消息真删）
+ 审查 S4 回归 R#6（?q= 刷新重发）/R#8（深链落错视图）/R#9（h5 会话排序沉底）/R#12（notebook 旧链 404）。
修完后复跑应全绿（红→绿对拍底）。"""
import sys
import time
import urllib.parse
from pathlib import Path

from playwright.sync_api import sync_playwright

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
R = []


def check(name, ok, detail=""):
    """基线模式：ok=True 表示「现状符合目标态」。基线期预期多数 FAIL（红）。"""
    R.append(ok)
    print(("GREEN " if ok else "RED   ") + name + "  " + str(detail)[:130], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1600, "height": 900})

    # ── A. ChatPanel 会话删除/重命名（v4§九：hover ⋯ 菜单缺失） ──
    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    pg.locator("[data-testid='activity-chat']").click()
    pg.wait_for_timeout(1000)
    rows = pg.locator("[data-testid='chat-panel'] [style*='cursor'] >> nth=0")
    # 会话行 hover 后找 ⋯/删除/重命名操作件
    row_count = pg.locator("[data-testid='chat-panel'] >> text=分钟前").count() \
        + pg.locator("[data-testid='chat-panel'] >> text=天前").count() \
        + pg.locator("[data-testid='chat-panel'] >> text=刚刚").count()
    has_rows = row_count > 0
    if has_rows:
        try:
            first_row = pg.locator("[data-testid='chat-panel-session-row']").first
            first_row.hover(timeout=3000)
            pg.wait_for_timeout(500)
            more = pg.locator("[data-testid='chat-panel-row-more']").first
            if more.count() > 0:
                more.click(timeout=2000)
                pg.wait_for_timeout(700)
        except Exception:
            pass
        menu_txt = ""
        try:
            menu_txt = pg.locator(".ant-dropdown-menu").first.inner_text(timeout=2000)
        except Exception:
            pass
        has_actions = ("重命名" in menu_txt) and ("删除" in menu_txt)
        pg.keyboard.press("Escape")
    else:
        has_actions = False
    check("A 会话面板项有删除/重命名操作（hover ⋯）", has_rows and has_actions,
          f"rows={row_count} actions={has_actions}")

    # ── B. ExpertChat 停止生成（isBusy → 停止钮） ──
    pg.goto(BASE + "/e/wenshu/chat", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    ta = pg.locator("textarea:visible").first
    if ta.count() == 0:
        ta = pg.locator("textarea").first
    ta.fill("统计用电客户总数")
    ta.press("Enter")
    pg.wait_for_timeout(2500)  # 流式已启动（正在思考/stop 应可见）
    stop_visible = pg.locator("button:has-text('停止'), [data-testid*='stop'], .ant-btn:has-text('■')").count() > 0
    check("B busy 时 composer 出现停止钮", stop_visible)
    # 等流式结束（后续用例复用页面），或直接进下一段
    pg.wait_for_timeout(3000)

    # ── C. R#6 ?q= 刷新重发 ──
    q = "9+9等于几"
    pg.goto(BASE + "/?new=1", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    nta = pg.locator("[data-testid='newchat-composer'] textarea").first
    nta.fill(q)
    nta.press("Enter")
    pg.wait_for_timeout(2500)  # 落 /e/wenshu/chat?new=1&q=...
    on_chat = "/e/wenshu/chat" in pg.url
    count_before = pg.evaluate(
        """(q) => Array.from(document.querySelectorAll('*')).filter(el =>
            el.children.length === 0 && el.textContent.trim() === q).length""",
        q,
    )
    pg.reload(timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)  # auto-send 窗口（600ms）+ 用户消息渲染
    count_after = pg.evaluate(
        """(q) => Array.from(document.querySelectorAll('*')).filter(el =>
            el.children.length === 0 && el.textContent.trim() === q).length""",
        q,
    )
    resent = on_chat and count_after > count_before
    check("C R#6 刷新后不重发（同问题用户消息数不增）", on_chat and not resent,
          f"chat={on_chat} before={count_before} after={count_after}")

    # ── D. R#8 深链落正确视图（SPA 重入：GraphManager 已挂载，仅 search 变化） ──
    pg.goto(BASE + "/graph", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    pg.evaluate("() => { window.history.pushState({}, '', '/graph?view=matrix'); window.dispatchEvent(new PopStateEvent('popstate')); }")
    pg.wait_for_timeout(3500)
    url_ok = "/graph?view=matrix" in pg.url
    active_tab = ""
    try:
        active_tab = pg.locator("[data-testid='graph-view-tabs'] .ant-tabs-tab-active").inner_text()
    except Exception:
        pass
    check("D R#8 深链 SPA 重入落 /graph?view=matrix 且激活=资产矩阵", url_ok and "矩阵" in active_tab,
          f"url_ok={url_ok} active={active_tab}")

    # ── E. R#9 ChatPanel 排序归一（最新 h5 会话应排最前；raw-ts 秒/毫秒混排则 h5 沉底） ──
    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    # 造数：PATCH 同 title 触摸最新 h5 会话（updated_at=now()）→ 它成为全局最新会话
    touched = pg.evaluate(
        """async () => {
        const raw = localStorage.getItem('tupu.oidc');
        let h = {};
        if (raw) { const t = JSON.parse(raw); h = { Authorization: t.token_type + ' ' + t.access_token }; }
        const lr = await fetch('/api/v1/sessions?limit=50&offset=0', { headers: h });
        if (!lr.ok) return { err: 'list-' + lr.status };
        const lj = await lr.json();
        const rows = lj.sessions || [];
        if (!rows.length) return { err: 'no-h5-sessions' };
        const top = rows[0];
        const sid = top.session_id || top.id;
        const pr = await fetch('/api/v1/sessions/' + sid, {
            method: 'PATCH',
            headers: Object.assign({ 'Content-Type': 'application/json' }, h),
            body: JSON.stringify({ title: top.title }),
        });
        return pr.ok ? { title: top.title } : { err: 'patch-' + pr.status };
    }"""
    )
    pg.locator("[data-testid='activity-chat']").click()
    pg.wait_for_timeout(1500)
    panel_txt = pg.locator("[data-testid='chat-panel']").inner_text()
    rows_meta = pg.evaluate(
        """() => {
        const panel = document.querySelector("[data-testid='chat-panel']");
        if (!panel) return [];
        const out = [];
        panel.querySelectorAll('div').forEach(d => {
          if (d.style.cursor !== 'pointer') return;
          const spans = d.querySelectorAll('span');
          if (!spans.length) return;
          const dot = spans[0];
          const t = (d.innerText || '').replace(/\\n/g, '|').trim();
          if (t && t.length > 2 && t.length < 80 && dot.style.borderRadius.indexOf('99') >= 0) {
            out.push([t, dot.style.background]);
          }
        });
        return out.slice(0, 8);
    }"""
    )
    import re as _re
    def _mins(txt):
        m = _re.search(r"刚刚", txt)
        if m:
            return 0
        m = _re.search(r"(\d+)\s*秒前", txt)
        if m:
            return 0
        m = _re.search(r"(\d+)\s*分钟前", txt)
        if m:
            return int(m.group(1))
        m = _re.search(r"(\d+)\s*小时前", txt)
        if m:
            return int(m.group(1)) * 60
        m = _re.search(r"(\d+)\s*天前", txt)
        if m:
            return int(m.group(1)) * 1440
        return None
    rows_t = []
    for line in panel_txt.splitlines():
        line = line.strip()
        if not line:
            continue
        mv = _mins(line)
        if mv is not None:
            rows_t.append((mv, line[:26]))
    mins_seq = [x[0] for x in rows_t]
    sorted_ok = (len(mins_seq) >= 2 and
                 all(a <= b for a, b in zip(mins_seq, mins_seq[1:]))) or len(mins_seq) < 2
    # 主断言：刚触摸的 h5 会话（全局最新）必须排第一行；且面板存在 h5(cyan) 行
    cyan_rows = [i for i, (t, c) in enumerate(rows_meta) if "8, 145" in c or "8,145" in c]
    touched_title = touched.get("title") if isinstance(touched, dict) else None
    first_is_h5 = bool(cyan_rows) and cyan_rows[0] == 0
    check("E R#9 会话按真实时间排序（新者在前）", sorted_ok and first_is_h5,
          f"touched={str(touched)[:40]} rows_meta={rows_meta[:4]}")

    # ── F. R#12 notebook 旧链 ──
    pg.goto(BASE + "/e/sishu/notebook", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    body = pg.inner_text("body")
    alive = "页面加载失败" not in body and "专家门户" not in body and ("笔记本" in body or "题库" in body or "笔记" in body)
    check("F R#12 /e/sishu/notebook 活（非 portal 回落）", alive, body[:60].replace("\n", "|"))

    pg.screenshot(path=str(SCR / "_pw_b0_before.png"))
    b.close()

greens = sum(R)
print(f"\n=== 批⓪ 基线：{greens}/{len(R)} GREEN（基线期红=待修缺陷实证）===")
sys.exit(0)  # 基线脚本恒 0（红是预期产物）
