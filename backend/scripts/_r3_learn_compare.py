# -*- coding: utf-8 -*-
"""⑤R 前端活体对拍：自主学习屏（原仓 30408 vs tupu 23000，390x844 移动视口）。
抓双方关键字段文本+截图，输出 r3_learn_screens.json。"""
import io
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent / "dt_baseline"
PAIRS = [
    ("learn", "http://localhost:30408/h5/learn", "http://localhost:23000/e/tutor/h5/learn"),
    ("learn_textbook", "http://localhost:30408/h5/learn/textbook", "http://localhost:23000/e/tutor/h5/learn/textbook"),
]

FIELDS_LEARN = ["streak", "今日", "到期", "薄弱", "教材", "章节", "复习", "学习", "任务"]
FIELDS_TB = ["教材", "章节", "书", "继续", "学习"]


def grab(pg, url, tag, shot):
    pg.goto(url, timeout=60000, wait_until="domcontentloaded")
    time.sleep(6)
    pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")
    time.sleep(1)
    body = pg.evaluate("document.body.innerText || ''")
    pg.screenshot(path=str(shot))
    return body


def main():
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 390, "height": 844})
        for name, ourl, turl in PAIRS:
            ob = grab(pg, ourl, name, BASE / f"r3_{name}_orig.png")
            tb = grab(pg, turl, name, BASE / f"r3_{name}_tupu.png")
            fields = FIELDS_LEARN if name == "learn" else FIELDS_TB
            fa = {f: (f in ob) for f in fields}
            fb = {f: (f in tb) for f in fields}
            missing_in_tupu = [f for f in fields if fa[f] and not fb[f]]
            out.append({"screen": name, "orig_fields": fa, "tupu_fields": fb,
                        "missing_in_tupu": missing_in_tupu,
                        "orig_head": ob[:300], "tupu_head": tb[:300]})
            print(f"== {name} ==")
            print(f"  原仓字段在位: {[k for k, v in fa.items() if v]}")
            print(f"  tupu 字段在位: {[k for k, v in fb.items() if v]}")
            print(f"  tupu 缺失: {missing_in_tupu or '无'}")
        b.close()
    json.dump(out, io.open(BASE / "r3_learn_screens.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
