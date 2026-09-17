# -*- coding: utf-8 -*-
"""一次性登录某账号→token 存 dt_baseline/tokens.json。
用法: python _r3_capture_token.py <student|akadmin|student2>
每账号独立进程跑一次（避免同进程连续登录触发节流/会话竞争）。
逻辑=已验证的 _r3_diag_claims 步骤（等待流框出现→坐标点击→键盘输入→等 token）。"""
import base64
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SCR = Path(__file__).resolve().parent
TOKF = SCR / "dt_baseline" / "tokens.json"
FRONT = "http://localhost:23000"
ACCOUNTS = {
    "student": ("student", "Tupu_student_2026"),
    "akadmin": ("akadmin", "deepassetlens_admin"),
    "student2": ("student2", "Tupu_student_2026"),
}


def main():
    acct = sys.argv[1]
    ident, password = ACCOUNTS[acct]
    tok = None
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()
        try:
            pg.goto(FRONT + "/", timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            if "interrupted" not in str(e):
                raise
        time.sleep(8)
        print("start:", pg.url[:70], flush=True)
        for step in range(8):
            pg.screenshot(path=str(SCR / "dt_baseline" / f"r3_cap_{acct}_{step}.png"))
            # 逐个可见输入探测（导航中 evaluate 会炸——重试）
            state = None
            for _ in range(3):
                try:
                    state = pg.evaluate("""() => {
                        const out = [];
                        const scan = (root) => root.querySelectorAll('input').forEach(i => {
                            const r = i.getBoundingClientRect();
                            out.push({name: i.name, vis: r.width > 0 && r.height > 0, val: i.value.length});
                        });
                        scan(document);
                        return {url: location.href.slice(0, 60), inputs: out.slice(0, 6)};
                    }""")
                    break
                except Exception:
                    time.sleep(2)
            if not state:
                time.sleep(2)
                continue
            print(f"step{step}:", state["url"], state["inputs"], flush=True)
            if "23000" in state["url"] and step > 0:
                break
            acted = False
            # 在流页（iframe 或主帧）上找 username/password 输入用坐标法输入
            if any(i["name"] == "username" and i["vis"] and i["val"] == 0 for i in state["inputs"]) \
                    or "9100" in pg.url or state["url"].startswith("http://localhost:9100"):
                # 流在 iframe：坐标点击可见卡位
                pg.mouse.click(720, 358)
                time.sleep(0.5)
                pg.keyboard.type(ident, delay=30)
                time.sleep(0.4)
                pg.keyboard.press("Enter")
                time.sleep(4)
                pg.keyboard.type(password, delay=30)
                time.sleep(0.4)
                pg.keyboard.press("Enter")
                acted = True
            if not acted:
                time.sleep(3)
        # 等回前端+token
        for _ in range(15):
            if FRONT in pg.url and "9100" not in pg.url:
                time.sleep(3)
                tok = pg.evaluate("""() => {
                    try { const v = JSON.parse(localStorage.getItem('tupu.oidc'));
                          return v && v.access_token ? v.access_token : null; } catch { return null; }
                }""")
                if tok:
                    break
            time.sleep(2)
        pg.screenshot(path=str(SCR / "dt_baseline" / f"r3_cap_{acct}_final.png"))
        b.close()
    if not tok:
        print(f"{acct}: LOGIN FAILED (final={pg.url[:60]})")
        sys.exit(1)
    data = json.loads(TOKF.read_text(encoding="utf-8")) if TOKF.exists() else {}
    data[acct] = tok
    TOKF.write_text(json.dumps(data), encoding="utf-8")
    payload = tok.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))
    print(f"{acct}: OK sub={claims.get('sub', '')[:16]} groups={claims.get('groups')}")


if __name__ == "__main__":
    main()
