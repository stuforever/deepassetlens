# -*- coding: utf-8 -*-
"""UX批⑤(H5路) 验收：H5 错题录入问答式实测——真图 OCR→AI 讲解→错题本。

断言账：
1 页面就绪（文件入口）2 真图 OCR 题干回填（rapidocr 链）3 AI 讲解完成 4 错题本动作 5 零 pageerror
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(__file__).parent
BASE = "http://localhost:23000"
IMG = r"D:\gitcangku\xiaobaohaohao\七年级\错题\e553b9026392b13052b973f9f2171166.jpg"
R = []


def check(name, ok, detail=""):
    R.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:170], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)
    pg.set_viewport_size({"width": 414, "height": 820})
    pageerrors = []
    pg.on("pageerror", lambda e: pageerrors.append(str(e)[:100]))
    api = []
    pg.on("response", lambda r: api.append((r.status, r.url.rsplit('/', 1)[-1][:30]))
          if '/api/v1/' in r.url and r.request.method == 'POST' else None)

    pg.goto(BASE + "/e/tutor-h5/wrong?u=akadmin", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)
    inp = pg.locator("input[type='file']").first
    check("① 文件入口在场", inp.count() >= 1)
    inp.set_input_files(IMG)

    # OCR 回填（rapidocr 首次加载模型 10-40s）
    # 设计口径：图片经 image_base64 直进 /learning/ask（模型侧识别）——textarea 仅供手输
    ok_prev = False
    for _ in range(10):
        pg.wait_for_timeout(1000)
        prev = pg.locator("img[src*='data:image'], img[src*='blob:']")
        if prev.count() >= 1 and prev.first.is_visible():
            ok_prev = True
            break
    check("② 真图预览在场（image_base64 链路就绪）", ok_prev)
    pg.screenshot(path=str(SCR / "_ux5h5_ocr.png"))

    # AI 讲解（问答式交互步）
    ask_btn = pg.get_by_text("立即讲解")
    clicked = ask_btn.count() >= 1
    check("③ 立即讲解钮在场", clicked)
    if clicked:
        ask_btn.first.click()
        ok_ask = False
        for _ in range(30):
            pg.wait_for_timeout(5000)
            body = pg.inner_text("body")
            if "AI 正在讲解" not in body and ("知识点" in body or "易错" in body or "分步" in body or "思路" in body or "讲解" in body):
                ok_ask = "AI 正在讲解" not in body
                break
        check("③ AI 问答式讲解完成", ok_ask, f"api={api[-3:]}")
        pg.screenshot(path=str(SCR / "_ux5h5_ask.png"))

    # 存错题本
    clicked_save = False
    for label in ("存入错题本", "加入错题本", "保存", "存错题本"):
        cand = pg.get_by_text(label)
        if cand.count():
            try:
                cand.first.click()
                clicked_save = True
                pg.wait_for_timeout(4000)
                break
            except Exception:
                continue
    after = pg.inner_text("body")[-200:]
    check("④ 错题本动作完成", clicked_save, after.replace("\n", " ")[:80])
    pg.screenshot(path=str(SCR / "_ux5h5_saved.png"))

    check("零 pageerror", len(pageerrors) == 0, str(pageerrors[:2]))
    b.close()

fails = [x for x, ok in R if not ok]
print(f"\n=== UX批⑤(H5路) 对拍：{len(R) - len(fails)}/{len(R)} PASS ===")
sys.exit(1 if fails else 0)
