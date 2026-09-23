# -*- coding: utf-8 -*-
"""UX批⑨ H5 全页冒烟（移动 414×820）：14 页逐页加载——渲染/无错误页/零 pageerror + 首页底导航。

输出每页状态账；破图页（加载失败/pageerror）登记为修复项。
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(__file__).parent
BASE = "http://localhost:23000"
R = []

PAGES = [
    ("home", "/e/tutor-h5"),
    ("chat", "/e/tutor-h5/chat"),
    ("learn", "/e/tutor-h5/learn"),
    ("learn-textbook", "/e/tutor-h5/learn/textbook"),
    ("classroom", "/e/tutor-h5/classroom"),
    ("review", "/e/tutor-h5/review"),
    ("wrong", "/e/tutor-h5/wrong"),
    ("wrongbook", "/e/tutor-h5/wrongbook"),
    ("paths", "/e/tutor-h5/paths"),
    ("report", "/e/tutor-h5/report"),
    ("atlas", "/e/tutor-h5/atlas"),
    ("me", "/e/tutor-h5/me"),
    ("share", "/e/tutor-h5/share"),
    ("notebook", "/e/tutor-h5/notebook"),
]


def check(name, ok, detail=""):
    R.append((name, ok))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}"[:170], flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from _pw_login_util import login_page
    pg = login_page(b)
    pg.set_viewport_size({"width": 414, "height": 820})
    broken = []
    for key, path in PAGES:
        pageerrors = []
        pg.on("pageerror", lambda e: pageerrors.append(str(e)[:80]))
        try:
            pg.goto(BASE + path, timeout=45000, wait_until="domcontentloaded")
            pg.wait_for_timeout(4000)
        except Exception as exc:  # noqa: BLE001
            broken.append((key, f"goto:{str(exc)[:50]}"))
            check(f"h5[{key}] 加载", False, str(exc)[:60])
            continue
        body = pg.inner_text("body")[:200]
        failed = "页面加载失败" in body or "加载失败" in body[:80]
        ok = (not failed) and len(pageerrors) == 0
        if not ok:
            broken.append((key, f"failed={failed} errs={pageerrors[:1]}"))
        check(f"h5[{key}]", ok, f"failed={failed} errs={len(pageerrors)}")
        pg.screenshot(path=str(SCR / f"_ux9_{key}.png"))
    check(f"H5 破图页数=0（共 {len(PAGES)} 页）", len(broken) == 0, str(broken[:4]))
    b.close()

fails = [x for x, ok in R if not ok]
print(f"\n=== UX批⑨ H5 冒烟：{len(R) - len(fails)}/{len(R)} PASS ===")
sys.exit(1 if fails else 0)
