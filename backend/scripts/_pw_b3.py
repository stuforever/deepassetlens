# -*- coding: utf-8 -*-
"""批③ 对拍（计划 Task 6 Step 5 / v4 §十三·§5.1）：ShellPanel 三态 + 400 统一 + 五组重排 + 删专家直达 + ⌘K 僵尸清零。

断言账：
1  三图标常驻（activity-bar 恰 3 钮）
2  三面板等宽 400（chat/console/settings 各开一次，bounding_box 实测）
3  浮层不挤主区（.ant-layout-content 宽度：关闭基准 == 浮层打开，±1px）
4  钉住让位 400 + localStorage 记忆（console：钉住后主区=基准-400；reload 后再开直接钉住态）
5  五组组账（五组名在场；平台能力/治理与系统不在场）
6  五组 17 项逐项点开无死链（壳在 + pageerror 零增量）
7  无专家直达（chat-panel 含新建对话/最近对话，不含三专家直达）
8  ⚙过渡期 9 项（settings-panel-navitem-skills 在场且点击导航 /skills）
9  ⌘K 僵尸清零（搜矩阵/四区/图库=无匹配结果；搜门户=专家门户中文标签）
10 零 pageerror 收尾 + 截图
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
RESULTS = []

NAV_ITEMS = [
    "graph", "entity_relation_manage",
    "datasource", "doris_config",
    "master_data", "activity_data", "source", "mapping", "metric_manager",
    "e:sishu:book", "e:sishu:self-learning", "e:sishu:co-writer", "e:sishu:partners",
    "e:sishu:admin:mq", "e:sishu:admin:book", "e:sishu:admin:settings",
    "h5_publish",
]
GROUPS5 = ["数据建模", "数据接入", "数据资产", "私塾管理", "H5 发布管理"]
GROUPS_GONE = ["平台能力", "治理与系统"]


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:180], flush=True)


def content_width(pg) -> int:
    return pg.locator(".ant-layout-content").first.bounding_box()["width"]


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)  # auth=ON 登录态
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:120]))

    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)

    # 幂等卫生：清三枚钉住键，保证基准态=全部浮层
    pg.evaluate("() => ['chat','console','settings'].forEach(k => localStorage.removeItem('shell:pinned:' + k))")
    pg.reload(timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)

    shell = pg.locator("[data-testid='shell-panel']")
    content0 = content_width(pg)
    check(f"主区基准宽实测", content0 > 800, f"base={content0:.0f}")

    # ① 三图标常驻
    btns = pg.locator("[data-testid='activity-bar'] button")
    check("activity-bar 恰 3 钮", btns.count() == 3, f"count={btns.count()}")

    # ②③ 三面板等宽 400 + 浮层不挤主区
    for panel in ("chat", "console", "settings"):
        pg.locator(f"[data-testid='activity-{panel}']").click()
        shell.wait_for(state="visible", timeout=5000)
        pg.wait_for_timeout(500)
        w = shell.bounding_box()["width"]
        check(f"[{panel}] 面板宽=400", abs(w - 400) <= 1, f"w={w:.0f}")
        inner = pg.locator(f"[data-testid='{ {'chat':'chat-panel','console':'nav-panel','settings':'settings-panel'}[panel] }']")
        check(f"[{panel}] 内容 testid 在场", inner.count() == 1 and inner.is_visible())
        cw = content_width(pg)
        check(f"[{panel}] 浮层主区宽不变", abs(cw - content0) <= 1, f"open={cw:.0f} base={content0:.0f}")
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(500)
        check(f"[{panel}] Esc 收起", shell.is_hidden())

    # ④ 钉住：console 钉住 → 主区让位 400 → localStorage → reload 后直接钉住态
    pg.locator("[data-testid='activity-console']").click()
    shell.wait_for(state="visible", timeout=5000)
    pg.wait_for_timeout(400)
    pg.locator("[data-testid='shell-panel-pin']").click()
    pg.wait_for_timeout(500)
    cw_pinned = content_width(pg)
    check("钉住后主区让位 400", abs(cw_pinned - (content0 - 400)) <= 1, f"pinned={cw_pinned:.0f} expect={content0 - 400:.0f}")
    pin_flag = pg.evaluate("() => localStorage.getItem('shell:pinned:console')")
    check("钉住态写 localStorage", pin_flag == "1", f"v={pin_flag}")
    pg.reload(timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    pg.locator("[data-testid='activity-console']").click()
    shell.wait_for(state="visible", timeout=5000)
    pg.wait_for_timeout(500)
    cw_re = content_width(pg)
    check("reload 后再开直接钉住态", abs(cw_re - (content0 - 400)) <= 1, f"reopen={cw_re:.0f}")
    pg.locator("[data-testid='shell-panel-pin']").click()  # 复原：取消钉住
    pg.wait_for_timeout(500)
    pin_flag2 = pg.evaluate("() => localStorage.getItem('shell:pinned:console')")
    cw_un = content_width(pg)
    check("取消钉住复原（浮层+键归0）", pin_flag2 == "0" and abs(cw_un - content0) <= 1, f"v={pin_flag2} w={cw_un:.0f}")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)

    # ⑤ 管理台五组组账
    pg.locator("[data-testid='activity-console']").click()
    shell.wait_for(state="visible", timeout=5000)
    for g in GROUPS5:
        check(f"组在场[{g}]", pg.locator(f"[data-testid='nav-panel-group-{g}']").count() == 1)
    for g in GROUPS_GONE:
        check(f"组已移出[{g}]", pg.locator(f"[data-testid='nav-panel-group-{g}']").count() == 0)

    # ⑥ 五组 17 项逐项点开无死链（reopen 竞态容错：探测可见+重试点击——
    #    nav 点击 onClose 未落定时再次点击会被 toggle 吞掉；KeepAlive 重挂载会让
    #    wait_for 反复失效，故用 200ms 轮询替代一次性 wait_for）
    def shell_open() -> bool:
        try:
            loc = pg.locator("[data-testid='shell-panel']")
            return loc.count() == 1 and loc.is_visible()
        except Exception:
            return False

    def reopen_console() -> bool:
        for _ in range(3):
            if shell_open():
                return True
            pg.locator("[data-testid='activity-console']").click()
            t0 = time.time()
            while time.time() - t0 < 4:
                if shell_open():
                    return True
                pg.wait_for_timeout(200)
            pg.wait_for_timeout(300)
        return False

    dead = []
    for key in NAV_ITEMS:
        if not reopen_console():
            dead.append((key, "面板未开"))
            continue
        loc = pg.locator(f"[data-testid='nav-item-{key}']")
        if loc.count() == 0:
            dead.append((key, "无该面板项"))
            continue
        before = len(pageerrors)
        loc.first.click()
        pg.wait_for_timeout(1200)
        if len(pageerrors) > before:
            dead.append((key, pageerrors[-1][:80]))
        if pg.locator("[data-testid='activity-bar']").count() != 1:
            dead.append((key, "壳消失"))
    check(f"五组逐项开页无死链（{len(NAV_ITEMS)} 项）", len(dead) == 0, str(dead[:4]))

    # ⑦ 无专家直达
    pg.locator("[data-testid='activity-chat']").click()
    shell.wait_for(state="visible", timeout=5000)
    pg.wait_for_timeout(400)
    chat_txt = pg.locator("[data-testid='chat-panel']").inner_text()
    check("chat-panel 无专家直达", "三专家直达" not in chat_txt and "专家直达" not in chat_txt)
    check("chat-panel 保留新建对话/最近对话", "新建对话" in chat_txt and "最近对话" in chat_txt)
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(400)

    # ⑧ ⚙过渡期 9 项（抽 skills 实点导航）
    pg.locator("[data-testid='activity-settings']").click()
    shell.wait_for(state="visible", timeout=5000)
    pg.wait_for_timeout(400)
    t_first = pg.locator("[data-testid='settings-panel-navitem-skills']")
    check("⚙过渡期项在场（skills）", t_first.count() == 1)
    t_first.click()
    pg.wait_for_timeout(1200)
    check("⚙过渡期项导航 /skills", "/skills" in pg.url, pg.url[:90])

    # ⑨ ⌘K 僵尸清零 + 门户中文标签
    pg.keyboard.press("Control+k")
    cmdk = pg.locator("[data-testid='cmdk']")
    cmdk.wait_for(state="visible", timeout=5000)
    inp = pg.locator("[data-testid='cmdk-input']")
    for kw in ("矩阵", "四区", "图库"):
        inp.fill(kw)
        pg.wait_for_timeout(400)
        no_match = pg.locator("[data-testid='cmdk']").inner_text()
        check(f"⌘K 搜[{kw}]无僵尸项", "无匹配结果" in no_match, f"items={pg.locator('[data-testid^=cmdk-item-]').count()}")
    inp.fill("门户")
    pg.wait_for_timeout(400)
    p_txt = pg.locator("[data-testid='cmdk-item-0']").inner_text().strip()
    check("⌘K 搜[门户]出中文标签", p_txt == "专家门户", f"label={p_txt[:30]}")
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(600)

    # ⑩ 收尾
    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    pg.screenshot(path=str(SCR / "_pw_b3.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== 批③ 对拍：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
