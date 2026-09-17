# -*- coding: utf-8 -*-
"""逐阶段驱动 Authentik 登录流，每步截图+DOM 状态。"""
import time
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto("http://localhost:23000/", timeout=60000, wait_until="domcontentloaded")
    time.sleep(8)
    print("start URL:", pg.url[:100])
    for step in range(8):
        pg.screenshot(path=f"scripts\\dt_baseline\\r3_step{step}.png")
        # 逐个可见输入探测（用 evaluate 深入 shadow DOM 拿真实可见性）
        state = pg.evaluate("""() => {
            const out = [];
            const scan = (root, tag) => {
                root.querySelectorAll('input').forEach(i => {
                    const r = i.getBoundingClientRect();
                    out.push({tag, name: i.name, type: i.type, vis: r.width > 0 && r.height > 0, val: i.value.slice(0,12)});
                });
            };
            scan(document, 'top');
            document.querySelectorAll('iframe, embed').forEach(f => { try { scan(f.contentDocument, 'frame'); } catch {} });
            const btns = [];
            document.querySelectorAll('button, input[type=submit]').forEach(bt => {
                const r = bt.getBoundingClientRect();
                if (r.width > 0) btns.push((bt.textContent || bt.value || '').trim().slice(0, 20));
            });
            return {url: location.href.slice(0, 90), inputs: out.slice(0, 8), buttons: btns.slice(0, 5)};
        }""")
        print(f"step{step}:", state)
        # 决策：填什么点什么
        acted = False
        for i in state["inputs"]:
            if i["vis"] and i["name"] == "username" and not i["val"]:
                pg.evaluate("""() => {
                    const i = [...document.querySelectorAll('input')].find(x => x.name==='username' && x.getBoundingClientRect().width>0);
                    const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    s.call(i, 'admin@deepassetlens.local');
                    i.dispatchEvent(new Event('input', {bubbles: true}));
                }""")
                time.sleep(0.8)
                pg.evaluate("""() => {
                    const b = [...document.querySelectorAll('button')].find(x => x.getBoundingClientRect().width>0 && /log in|continue|submit/i.test(x.textContent));
                    if (b) b.click();
                }""")
                acted = True
                break
            if i["vis"] and i["name"] == "password" and not i["val"]:
                pg.evaluate("""() => {
                    const i = [...document.querySelectorAll('input')].find(x => x.name==='password' && x.getBoundingClientRect().width>0);
                    const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    s.call(i, 'deepassetlens_admin');
                    i.dispatchEvent(new Event('input', {bubbles: true}));
                }""")
                time.sleep(0.8)
                pg.evaluate("""() => {
                    const b = [...document.querySelectorAll('button')].find(x => x.getBoundingClientRect().width>0 && /log in|continue|submit/i.test(x.textContent));
                    if (b) b.click();
                }""")
                acted = True
                break
        if not acted and state["buttons"]:
            pg.evaluate("""() => {
                const b = [...document.querySelectorAll('button')].find(x => x.getBoundingClientRect().width>0 && /continue|log in|submit/i.test(x.textContent));
                if (b) b.click();
            }""")
        time.sleep(4)
        if "23000" in pg.url:
            print("DONE back at frontend")
            break
    print("final:", pg.url[:100])
    b.close()
