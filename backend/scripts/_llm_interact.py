# -*- coding: utf-8 -*-
"""LLM 设置交互实测：选智谱→运行测试→保存草稿→应用，抓每步结果。"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SCR = Path(__file__).parent
BASE = "http://localhost:23000"


def snap(pg, label):
    toasts = pg.evaluate("""() => Array.from(document.querySelectorAll('.ant-message, .ant-notification, [class*=toast], [class*=Toast]'))
        .map(el => el.innerText.trim()).filter(Boolean)""")
    print(f"[{label}] toast: {toasts}", flush=True)


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    sys.path.insert(0, str(SCR))
    from _pw_login_util import login_page
    pg = login_page(b)
    pg.set_viewport_size({"width": 1920, "height": 1080})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)[:200]))

    pg.goto(BASE + "/settings/llm", timeout=60000, wait_until="domcontentloaded")
    pg.wait_for_timeout(6000)

    # 工具栏计数（疑似双渲染）
    tb = pg.evaluate("""() => Array.from(document.querySelectorAll('button')).filter(b => b.innerText.trim()==='保存草稿').length""")
    print("保存草稿按钮数:", tb, flush=True)

    # 1. 选中智谱 profile
    pg.get_by_text("Zhipu AI", exact=True).first.click()
    pg.wait_for_timeout(1500)
    pg.screenshot(path=str(SCR / "_llm_zhipu_selected.png"))
    # 读编辑器当前字段
    fields = pg.evaluate("""() => Array.from(document.querySelectorAll('input,textarea'))
        .map(el => ({ph: el.placeholder||'', val: (el.value||'').slice(0,60), type: el.type||''}))
        .filter(f => f.val || f.ph)""")
    print("智谱编辑器字段:", fields[:12], flush=True)

    # 2. 展开诊断 + 运行测试
    exp = pg.get_by_text("展开诊断")
    if exp.count():
        exp.first.click()
        pg.wait_for_timeout(800)
    run = pg.get_by_text("运行测试", exact=True)
    print("运行测试按钮数:", run.count(), flush=True)
    if run.count():
        run.first.click()
        ok = False
        for _ in range(90):
            pg.wait_for_timeout(1000)
            done = pg.evaluate("""() => {
                const t = document.body.innerText;
                return t.includes('pong') || t.includes('失败') || t.includes('错误') || t.includes('error') || t.includes('ERROR');
            }""")
            if done:
                break
        pg.wait_for_timeout(1500)
        diag = pg.evaluate("""() => {
            const els = Array.from(document.querySelectorAll('pre, code, [class*=diagnostic], [class*=Diag]'));
            return els.map(e => e.innerText.trim()).filter(t => t && t.length > 10).join('\\n---\\n').slice(0, 2500);
        }""")
        print("诊断输出:", diag[:2500], flush=True)
        snap(pg, "测试后")
        pg.screenshot(path=str(SCR / "_llm_zhipu_test.png"), full_page=True)

    # 3. 保存草稿 → 应用
    pg.get_by_text("保存草稿", exact=True).first.click()
    pg.wait_for_timeout(1500)
    snap(pg, "保存草稿后")
    pg.get_by_text("应用", exact=True).first.click()
    pg.wait_for_timeout(2500)
    snap(pg, "应用后")
    pg.screenshot(path=str(SCR / "_llm_zhipu_save.png"), full_page=True)

    # 4. 模型行 hover 找复制
    models = pg.evaluate("""() => Array.from(document.querySelectorAll('button,[role=button]'))
        .map(el => (el.innerText||el.getAttribute('aria-label')||'').trim())
        .filter(t => t.includes('复制') || t.toLowerCase().includes('copy'))""")
    print("复制类按钮:", models, flush=True)
    print("pageerror:", errors[:3], flush=True)
    b.close()
