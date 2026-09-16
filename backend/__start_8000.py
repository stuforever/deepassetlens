"""tupu 后端启动器——铁律端口 28000（勿改其他端口）。

2026-09-16 编码硬化（96 题前端实测「病理性卡顿」根因）：GBK 控制台/管道下，
langgraph 状态流内部 print 撞不可编码字符（『』\\u27e6、−\\u2212 等）→
UnicodeEncodeError → 流式中断 → 前端永久停在「正在理解问题」。
PYTHONUTF8=1 依赖启动方自觉，此处在解释器内把标准流固化为 UTF-8 且
errors=replace（永不因字符崩流）——无论以何种方式启动均免疫。
"""
import sys

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass  # 非 TextIOWrapper（已重定向/测试替身）等场景尽力而为

import uvicorn

from app.main import app

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=28000, workers=1, log_level="info")
