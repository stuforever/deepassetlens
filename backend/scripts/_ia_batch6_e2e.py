# -*- coding: utf-8 -*-
"""IA批6 e2e v2（确定性断言版）：AI写作+伙伴+桌面自主学习动线。
S1 菜单入口→AI写作列表 | S2 新建草稿→?doc= 动线 | S3 编辑页输入→自动保存
S4 自主学习页 | S5 菜单入口→伙伴列表 | S6 新建伙伴→向导首步
S7 伙伴详情（列表卡点击） | S8 /e/tutor/partners/:id 直访（参数路由匹配） |
"""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:23000"
HERE = Path(__file__).resolve().parent
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(("PASS " if ok else "FAIL ") + name + (" | " + str(detail) if detail else ""))


def shot(pg, name):
    pg.screenshot(path=str(HERE / f"_ia_b6_{name}.png"))


def click_menu(pg, group, item):
    pg.evaluate(
        "(g) => { const t = [...document.querySelectorAll('.dal-sider .ant-menu-submenu-title')]"
        ".find((e) => e.textContent.includes(g)); if (t) t.click(); }",
        group,
    )
    pg.wait_for_timeout(900)
    pg.evaluate(
        "(i) => { const els = [...document.querySelectorAll('.dal-sider .ant-menu-item')];"
        " const el = els.find((e) => e.textContent.includes(i));"
        " if (el) el.click(); }",
        item,
    )
    pg.wait_for_timeout(1200)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()

        # S1 菜单入口→AI写作列表
        pg.goto(BASE + "/", timeout=60000)
        pg.wait_for_timeout(3500)
        click_menu(pg, "私塾先生", "AI写作")
        ok = True
        try:
            pg.wait_for_url("**/e/tutor/co-writer", timeout=25000)
        except Exception:
            ok = False
        body = pg.locator("body").inner_text()
        check("S1 菜单入口→AI写作列表", ok and ("智能写作" in body), pg.url)
        shot(pg, "cowriter_list")

        # S2 新建草稿→参数路由动线（列表→编辑跳转语义，源 router.push(/co-writer/${id}) 等价）
        try:
            pg.get_by_text("新建草稿", exact=False).first.click(timeout=10000)
            pg.wait_for_url("**/e/tutor/co-writer/*", timeout=20000)
            check("S2 新建草稿→编辑动线", ("/e/tutor/co-writer/" in pg.url), pg.url)
        except Exception as e:
            check("S2 新建草稿→编辑动线", False, str(e)[:80])
        shot(pg, "cowriter_editor")

        # S3 编辑页输入→自动保存（1500ms 防抖）
        # 定位注意：KeepAlive 隐藏面板里也有 textarea（探查页聊天）——必须 :visible
        try:
            ta = pg.locator("textarea:visible").first
            ta.wait_for(state="visible", timeout=20000)
            ta.fill("# 批6 对拍验证\n\n自动保存语义逐字复刻。", timeout=15000)
            pg.wait_for_timeout(2600)
            body = pg.locator("body").inner_text()
            saved = ("已保存" in body) or ("正在保存" in body)
            check("S3 编辑→自动保存", saved, f"saved={saved}")
        except Exception as e:
            check("S3 编辑→自动保存", False, str(e)[:80])

        # S4 自主学习直访
        pg.goto(BASE + "/e/tutor/self-learning", timeout=60000)
        pg.wait_for_timeout(3500)
        body = pg.locator("body").inner_text()
        check("S4 自主学习页", ("自主学习" in body) and (("教材" in body) or ("选择一个章节" in body)), pg.url)
        shot(pg, "self_learning")

        # S5 菜单入口→伙伴列表
        pg.goto(BASE + "/", timeout=60000)
        pg.wait_for_timeout(3500)
        click_menu(pg, "私塾先生", "伙伴/推送")
        ok = True
        try:
            pg.wait_for_url("**/e/tutor/partners", timeout=25000)
        except Exception:
            ok = False
        body = pg.locator("body").inner_text()
        check("S5 菜单入口→伙伴列表", ok and ("伙伴" in body), pg.url)
        shot(pg, "partners_list")

        # S6 新建伙伴→向导首步（源入口为 <Link>/<a>——非 antd Button）
        try:
            pg.locator("a:has-text('新建伙伴')").first.click(timeout=15000)
            pg.wait_for_url("**/e/tutor/partners/new", timeout=20000)
            body = pg.locator("body").inner_text()
            check("S6 新建伙伴向导", ("伙伴" in body), pg.url)
        except Exception as e:
            check("S6 新建伙伴向导", False, str(e)[:80])
        shot(pg, "partners_new")

        # S7 伙伴详情（列表卡点击——小宝助理）
        pg.goto(BASE + "/e/tutor/partners", timeout=60000)
        pg.wait_for_timeout(3500)
        try:
            pg.locator("text=小宝助理").first.click(timeout=10000)
            pg.wait_for_timeout(3500)
            ok = ("/e/tutor/partners/" in pg.url) and (pg.url.rstrip("/") != BASE + "/e/tutor/partners")
            check("S7 伙伴详情（列表卡）", ok, pg.url)
        except Exception as e:
            check("S7 伙伴详情（列表卡）", False, str(e)[:80])
        shot(pg, "partners_detail")

        # S8 详情参数路由直访（:partnerId 段匹配）
        pg.goto(BASE + "/e/tutor/partners/partner-f5849d88", timeout=60000)
        pg.wait_for_timeout(3500)
        body = pg.locator("body").inner_text()
        check("S8 详情参数路由直访", ("小宝助理" in body) and ("聊天" in body or "配置" in body), pg.url)

        browser.close()

    ok_n = sum(1 for _, s, _ in RESULTS if s)
    print(f"== 批6 e2e 结果: {ok_n}/{len(RESULTS)} PASS ==")
    (HERE / "_ia_batch6_e2e_result.json").write_text(
        json.dumps([{"name": n, "ok": s, "detail": d} for n, s, d in RESULTS], ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return 0 if ok_n == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
