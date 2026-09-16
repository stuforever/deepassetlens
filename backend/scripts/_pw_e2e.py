# -*- coding: utf-8 -*-
"""_pw_e2e.py <问题> [截图名] - Playwright 前端 e2e：问数页输入→发送→等流式→提取结果表/结论
用法: python _pw_e2e.py "统计用电客户总数" smoke1
"""
import sys
import time
from playwright.sync_api import sync_playwright

Q = sys.argv[1] if len(sys.argv) > 1 else "统计用电客户总数"
SHOT = sys.argv[2] if len(sys.argv) > 2 else "e2e"

TIMEOUT_S = int(sys.argv[3]) if len(sys.argv) > 3 else 200

# 记忆插槽②批7：第 4 参专家（默认 wenshu——/e/{expert}/chat 入口）
EXPERT = sys.argv[4] if len(sys.argv) > 4 else "wenshu"

# ②补验 C 组：第 5 参用户（空=默认 anonymous；"admin"=点击 header 用户切换）
USER = sys.argv[5] if len(sys.argv) > 5 else ""

# ⑤R B2（用户指令 2026-09-16）：第 6 参 LLM 渠道（空=不动；"4coding"=点击 composer 渠道
# 选择器切到平台默认渠道——deepseek官方 402 余额不足时的切换路径）
CHANNEL = sys.argv[6] if len(sys.argv) > 6 else ""
CHANNEL_OLD = "deepseek官方"  # 当前选中渠道显示文本（切换锚点）


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        # 专家地基①（批5）：入口走 /e/{expert}/chat 专家对话页（批7 加专家参数）
        pg.goto(f"http://localhost:23000/e/{EXPERT}/chat", timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(4000)
        # ②补验 C1：用户切换（header 用户名文本点击）
        if USER:
            try:
                pg.click(f"text={USER}", timeout=6000)
                pg.wait_for_timeout(2000)
                print(f"USER: 已切换 {USER}")
            except Exception as e:
                print(f"WARN: 用户切换 {USER} 失败: {e}")
        # 输入（专家地基①批5：KeepAlive 下 pinned 页签同挂 ExpertChat——:visible 过滤隐藏 textarea）
        if CHANNEL:
            try:
                pg.click(f"text={CHANNEL_OLD}", timeout=6000)
                pg.wait_for_timeout(800)
                pg.click(f"text={CHANNEL}", timeout=6000)
                pg.wait_for_timeout(800)
                print(f"CHANNEL: 已切换 {CHANNEL}")
            except Exception as e:
                print(f"WARN: 渠道切换 {CHANNEL} 失败: {e}")
        ta = pg.query_selector("textarea.ant-input:visible")
        if not ta:
            print("FAIL: 找不到输入框")
            b.close(); return 1
        ta.fill(Q)
        pg.wait_for_timeout(300)
        # 发送：ant-btn-primary（图标按钮，可见态）或 Enter
        send = pg.query_selector("button.ant-btn-primary:visible")
        if send:
            send.click()
        else:
            ta.press("Enter")
        # 等待流式：监听网络空闲 + 轮询结果出现
        t0 = time.time()
        result_text = ""
        table_count = 0
        while time.time() - t0 < TIMEOUT_S:
            pg.wait_for_timeout(3000)
            try:
                body = pg.inner_text("body")
            except Exception:
                body = ""
            # 查询结果表（ant-table）
            try:
                tables = pg.query_selector_all(".ant-table")
                table_count = len(tables)
            except Exception:
                table_count = 0
            # 结论/回答区：找含"结论"/"回答"/"共 N"的关键文本
            keys = [ln for ln in body.splitlines() if any(k in ln for k in ("结论", "行", "查询结果", "未找到", "不存在", "用电户", "项目", "WBS", "客户"))]
            # 若出现 done 标记（如"重新提问"按钮或回答稳定）则退出
            if table_count > 0 and keys:
                result_text = body
                break
            # 简单终止：等待足够久且页面不再变化
            if time.time() - t0 > TIMEOUT_S * 0.9:
                result_text = body
                break
        elapsed = time.time() - t0
        pg.screenshot(path=f"scripts/_pw_{SHOT}.png", full_page=False)
        print(f"== 前端 e2e 完成 耗时{elapsed:.0f}s tables={table_count} ==")
        # 提取结果表
        try:
            for ti, tbl in enumerate(pg.query_selector_all(".ant-table")):
                try:
                    thead = [h.inner_text().strip() for h in tbl.query_selector_all("thead th") ]
                    rows = []
                    for tr in tbl.query_selector_all("tbody tr"):
                        cells = [c.inner_text().strip() for c in tr.query_selector_all("td")]
                        if cells:
                            rows.append(cells)
                    print(f"[表{ti}] 列={thead}")
                    for r in rows[:6]:
                        print("    ", [x[:20] for x in r])
                    print(f"    共{len(rows)}行(预览6)")
                except Exception as e:
                    print(f"[表{ti}] 解析失败 {e}")
        except Exception as e:
            print("表格解析失败:", e)
        # 提取结论/回答文本
        print("\n== 回答区关键文本 ==")
        for ln in [l for l in result_text.splitlines() if l.strip()][-40:]:
            print("  ", ln[:80])
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
