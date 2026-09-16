# -*- coding: utf-8 -*-
"""⑤R B2：composer 渠道选择器 DOM 探针——定位 4coding 切换的真实可点元素。"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto("http://localhost:23000/e/wenshu/chat", timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(5000)
    for kw in ("deepseek", "4coding", "官方"):
        els = pg.query_selector_all(f"text={kw}")
        print(f"[{kw}] 匹配 {len(els)} 个:")
        for i, e in enumerate(els[:6]):
            try:
                tag = e.evaluate("el => el.tagName + '.' + el.className")
                vis = e.is_visible()
                txt = e.inner_text()[:40].replace("\n", "|")
                print(f"  {i}: visible={vis} {tag} :: {txt}")
            except Exception as ex:
                print(f"  {i}: err {ex}")
    # composer 区域结构
    comp = pg.query_selector("textarea.ant-input:visible")
    print("textarea:", bool(comp))
    if comp:
        # 向上找 composer 容器内的可点文本
        sibs = comp.evaluate("""el => {
            let c = el; for (let i=0;i<6 && c.parentElement;i++) c = c.parentElement;
            return c.innerText.slice(0, 300);
        }""")
        print("composer 区文本:", sibs.replace("\n", " | ")[:300])
    b.close()
