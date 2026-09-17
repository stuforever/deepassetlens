# -*- coding: utf-8 -*-
"""⑤R 学习流对拍：输入名字→开始学习→仪表盘字段对比（原仓 vs tupu）。"""
import io
import json
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent / "dt_baseline"
FIELDS = ["streak", "连续", "今日任务", "到期", "薄弱", "掌握", "复习", "任务", "开始学习", "进度", "知识点"]


def enter(pg, url, shot):
    pg.goto(url, timeout=60000, wait_until="domcontentloaded")
    time.sleep(6)
    pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")
    body = pg.evaluate("document.body.innerText || ''")
    # 欢迎层：输名字→开始学习
    inp = pg.query_selector("input[placeholder*='我叫']") or pg.query_selector("input")
    if inp and "欢迎使用" in body:
        inp.fill("对拍员")
        time.sleep(0.6)
        btn = pg.query_selector("button:has-text('开始学习')")
        if btn:
            btn.click()
            time.sleep(5)
            pg.evaluate("document.getElementById('webpack-dev-server-client-overlay')?.remove()")
            time.sleep(1)
    body2 = pg.evaluate("document.body.innerText || ''")
    pg.screenshot(path=str(shot))
    return body2


def main():
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 390, "height": 844})
        for side, url, shot in [
            ("orig", "http://localhost:30408/h5/learn", BASE / "r3_learnflow_orig.png"),
            ("tupu", "http://localhost:23000/e/tutor/h5/learn", BASE / "r3_learnflow_tupu.png"),
        ]:
            body = enter(pg, url, shot)
            fa = {f: (f in body) for f in FIELDS}
            out.append({"side": side, "fields": fa, "head": body[:500]})
            print(f"== {side} == 在位字段: {[k for k, v in fa.items() if v]}")
            print("  head:", body[:180].replace(chr(10), "|"))
        b.close()
    same = out[0]["fields"] == out[1]["fields"]
    json.dump(out, io.open(BASE / "r3_learnflow.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("仪表盘字段一致性:", "一致" if same else "有差异")


if __name__ == "__main__":
    main()
