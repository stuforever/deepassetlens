# -*- coding: utf-8 -*-
"""批③ 对拍：⌘K 命令面板——Ctrl+K 开/输入过滤/Enter 执行/portal 中文标签/Esc 关闭。

口径（2026-09-23，批③ Task3 同步）：
- Step 3.5 已落地：MENU_LABELS['portal']='专家门户'——本脚本断言改为中文标签（不再是裸键）。
- 僵尸项（矩阵/四区/图库）断言归 _pw_b3.py（Step 3 删僵尸后验证），此处不测。
- 同指 path 去重（批③ 审查Minor②，first-wins）后空查询默认仍 12 条
  （页面注册项 30 + 专家 3 + 动作 3，去重吸收后远超 slice(0,12) 上限）——以实为准记账。
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

SCR = Path(__file__).parent
BASE = "http://localhost:23000"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:170], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)  # 批③基线复验：auth 开启后须登录态
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:120]))

    pg.goto(BASE + "/", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)

    cmdk = pg.locator("[data-testid='cmdk']")
    inp = pg.locator("[data-testid='cmdk-input']")

    # ① Ctrl+K 开面板
    pg.keyboard.press("Control+k")
    cmdk.wait_for(state="visible", timeout=5000)
    check("Ctrl+K 开面板", cmdk.is_visible())
    check("输入框占位符", "搜索页面" in (inp.get_attribute("placeholder") or ""))

    # ② 空查询默认 12 条（同指 path 去重后仍远超 12，slice(0,12) 截断）
    n_default = pg.locator("[data-testid^='cmdk-item-']").count()
    check("默认 12 条", n_default == 12, f"count={n_default}")

    # ③ 输入过滤：'发布' → 首条 H5 发布管理（pages 先于 experts/actions 注册）
    inp.fill("发布")
    pg.wait_for_timeout(400)
    n_f = pg.locator("[data-testid^='cmdk-item-']").count()
    first_txt = pg.locator("[data-testid='cmdk-item-0']").inner_text()
    check("过滤后条目变少", 0 < n_f < n_default, f"{n_default}->{n_f}")
    check("首条=H5 发布管理", first_txt.strip() == "H5 发布管理", first_txt.strip()[:40])

    # ④ Enter 执行首条 → /h5-publish 且面板关闭
    pg.keyboard.press("Enter")
    pg.wait_for_timeout(1500)
    check("Enter 直达 /h5-publish", "/h5-publish" in pg.url, pg.url[:90])
    pg.wait_for_timeout(800)  # antd Modal 关闭动画后 is_hidden
    check("执行后面板关闭", cmdk.is_hidden())

    # ⑤ portal 项中文标签（Step 3.5 已落地——MENU_LABELS['portal']='专家门户'；
    #    查询词须用中文「门户」——label 已无 'portal' 子串，旧查询词永不匹配）
    pg.keyboard.press("Control+k")
    cmdk.wait_for(state="visible", timeout=5000)
    inp.fill("门户")
    pg.wait_for_timeout(400)
    p_txt = pg.locator("[data-testid='cmdk-item-0']").inner_text().strip()
    check("portal 项 label=专家门户（Step 3.5 已落地）", p_txt == "专家门户", f"label={p_txt[:40]}")

    # ⑥ Esc 关闭
    pg.keyboard.press("Escape")
    pg.wait_for_timeout(800)
    check("Esc 关闭面板", cmdk.is_hidden())

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    pg.screenshot(path=str(SCR / "_pw_cmdk.png"))
    b.close()

fails = [x for x in RESULTS if not x[1]]
print(f"\n=== cmdk 对拍：{len(RESULTS) - len(fails)}/{len(RESULTS)} PASS ===")
sys.exit(1 if fails else 0)
