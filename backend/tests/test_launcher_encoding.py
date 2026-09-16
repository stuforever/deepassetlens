# -*- coding: utf-8 -*-
"""启动器 stdout 编码硬化回归——96 题前端实测「病理性卡顿」根因护航。

根因（2026-09-16 实录）：GBK 控制台/管道下，langgraph 状态流内部 print 撞不可编码
字符（『』\\u27e6、−\\u2212 等）→ UnicodeEncodeError → 流式中断 → 前端永久停在
「正在理解问题」。启动器必须在解释器内把标准流固化为 UTF-8（errors=replace），
不得依赖启动方自觉设置 PYTHONUTF8=1。
"""
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def test_启动器硬化_GBK流遇不可编码字符不炸():
    """子进程模拟裸 GBK 环境（无 PYTHONUTF8）——『』− 打印必须存活。"""
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    env["PYTHONIOENCODING"] = "gbk"          # 强制子进程 std 流为 GBK（模拟 GBK 控制台/管道）
    code = "import __start_8000; print('『』−', end='')"
    r = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(BACKEND), env=env, capture_output=True, timeout=300,
    )
    out = r.stdout.decode("utf-8", "replace")
    assert r.returncode == 0, f"启动器硬化缺失/未生效，GBK 流炸: {r.stderr.decode('utf-8', 'replace')[-500:]}"
    assert "『』−" in out, f"输出非 UTF-8 或字符被吞: {out[-200:]!r}"
