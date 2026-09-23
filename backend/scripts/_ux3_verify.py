# -*- coding: utf-8 -*-
"""UX批③ 验收探针（反馈⑥）：拍照→OCR→切题→缩略图渲染→入库 全链路 + 手动快录路径。

断言账：
1  母题库入口双钮（拍照中心/拍照录入）
2  上传整页图 → batch_recognize 200 → 逐题卡渲染（mq-pc-item-0）
3  缩略图 AuthedImg 实际加载（naturalWidth>0——blob 修复实证）
4  批量入库（mq-pc-save-all）→ 已保存态/POST 200
5  手动快录：拍照录入页字段+文件入口在场（≤3 步：传图→核对→保存）
6  零 pageerror
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(__file__).parent
BASE = "http://localhost:23000"
R = []


def check(name, ok, detail=""):
    R.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:170], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:100]))
    api = []
    pg.on("response", lambda r: api.append((r.status, r.url.rsplit('/', 1)[-1][:40]))
          if '/mother-questions' in r.url and r.request.method in ('POST', 'PUT') else None)

    # ① 母题库入口
    pg.goto(BASE + "/e/sishu/admin/mother-questions", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    check("① 母题库入口双钮", pg.locator("[data-testid='mq-photo-center-btn']").count() == 1
          and pg.locator("[data-testid='mq-photo-btn']").count() == 1)

    # ②③④ 拍照中心全链（带字测试图）
    pg.locator("[data-testid='mq-photo-center-btn']").click()
    pg.wait_for_timeout(3000)
    inp2 = pg.locator("input[type='file']").first
    check("② 文件入口在场", inp2.count() >= 1)
    inp2.set_input_files('backend/scripts/_ux_text_question.png')
    pg.wait_for_timeout(15000)
    item0 = pg.locator("[data-testid='mq-pc-item-0']")
    check("② 逐题卡渲染", item0.count() >= 1, f"items={pg.locator('[data-testid^=mq-pc-item-]').count()}")
    thumb = item0.locator("img").first
    if thumb.count():
        nw = thumb.evaluate("el => el.naturalWidth")
        check("③ 缩略图 AuthedImg 实际加载", nw > 0, f"naturalWidth={nw}")
    else:
        check("③ 缩略图 AuthedImg 实际加载", False, "无 img 元素")
    pg.screenshot(path=str(SCR / "_ux3_items.png"))

    # ④ 批量入库
    save = pg.locator("[data-testid='mq-pc-save-all']")
    if save.count():
        save.click()
        pg.wait_for_timeout(4000)
        saved = pg.locator("[data-saved='ok']").count()
        check("④ 批量入库成功", saved >= 1, f"saved={saved} api={api[-3:]}")
    else:
        check("④ 批量入库钮", False, "无 mq-pc-save-all")

    # ⑤ 手动快录（拍照录入页：传图→OCR 预填→核对保存 = ≤3 步）
    pg.goto(BASE + "/e/sishu/admin/mother-questions/photo", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    body = pg.inner_text("body")
    has_fields = ("题干" in body) or ("题目" in body) or ("答案" in body)
    has_file = pg.locator("input[type='file']").count() >= 1
    check("⑤ 手动快录路径（字段+传图入口在场）", has_fields and has_file, f"fields={has_fields} file={has_file}")
    pg.screenshot(path=str(SCR / "_ux3_manual.png"))

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    b.close()

fails = [x for x, ok in R if not ok]
print(f"\n=== UX批③ 对拍：{len(R) - len(fails)}/{len(R)} PASS ===")
sys.exit(1 if fails else 0)
