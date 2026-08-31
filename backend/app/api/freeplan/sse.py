# -*- coding: utf-8 -*-
"""freeplan/sse.py - SSE 帧工具（批13-D，纯函数，无副作用）。

所有 SSE 帧统一经 sse_frames/sse_event 生成，保证字节一致：
  帧 = f"event: {name}\n" + f"data: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"
与拆分前 stream 单体内联 yield 逐字节相同（行为零变化）。
"""
from __future__ import annotations

import json
from typing import Any, Iterable


def sse_frames(name: str, data: Any, default=str) -> Iterable[str]:
    """生成 SSE 帧（两行：event + data），供 `yield from` 消费，保持字节一致。"""
    yield f"event: {name}\n"
    yield f"data: {json.dumps(data, ensure_ascii=False, default=default)}\n\n"


def sse_line(name: str, data: Any, default=str) -> str:
    """拼接为单个帧字符串（用于需要单串的场景，如日志/测试断言）。"""
    return "".join(sse_frames(name, data, default=default))
