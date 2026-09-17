# -*- coding: utf-8 -*-
"""IA批4 探针：/vector 知识中心承接页渲染验证。"""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script("try{localStorage.setItem('h5_recent_users', JSON.stringify(['小明']));}catch(e){}")
    pg = ctx.new_page()
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)[:200]))
    pg.goto("http://localhost:23000/vector", timeout=60000)
    pg.wait_for_timeout(9000)
    body = pg.inner_text("body")
    print("知识中心:", "知识中心" in body, "| 检索引擎:", "检索引擎" in body, "| 知识库列表:", "知识库列表" in body, "| 新建知识库:", "新建知识库" in body)
    print("math-textbook 卡:", "math-textbook" in body, "| LlamaIndex:", "LlamaIndex" in body)
    print("pageerrors:", errs[:3])
    pg.screenshot(path="scripts/_ia_b4_vector.png")
    b.close()
