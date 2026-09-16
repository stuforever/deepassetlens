"""轻量 LLM 调用成本 JSONL 日志（运营基建，审核建议 2）。

非对话 LLM 直调点（练习生成/变式生成/错因归因/explain/ai_solve）不经
capability 管线，UsageTracker 统计不到。本模块提供追加式 JSONL 日志：
每行 {ts, iso, endpoint, user, tokens_in, tokens_out, ok, latency_ms, error}，
供家长周报估算「本周 AI 消耗」、工程侧定位异常烧钱调用点（如某个孩子
狂点「生成新题」）。

文件落当前用户工作区 `workspace/logs/llm_calls.jsonl`（get_path_service
随上下文自动隔离：admin=全局 data/user/workspace，H5 用户=各自工作区）。
只追加、不读不聚合；任何异常静默吞掉，绝不影响业务主路径。
"""

from __future__ import annotations

import json
import os
import time
from typing import Any


def _log_path() -> str:
    base: str | None = None
    try:
        from deeptutor.multi_user.paths import get_current_path_service

        base = str(get_current_path_service().get_workspace_dir())
    except Exception:  # noqa: BLE001
        base = None
    if not base:
        base = os.path.join(os.getcwd(), "data", "user", "workspace")
    d = os.path.join(base, "logs")
    try:
        os.makedirs(d, exist_ok=True)
    except Exception:  # noqa: BLE001
        return ""
    return os.path.join(d, "llm_calls.jsonl")


def log_llm_call(
    endpoint: str,
    user: str = "",
    tokens_in: int = 0,
    tokens_out: int = 0,
    ok: bool = True,
    latency_ms: int = 0,
    error: str = "",
    **extra: Any,
) -> None:
    """追加一行调用日志。调用方在 LLM 返回后（成功或异常）各调一次。"""
    try:
        row: dict[str, Any] = {
            "ts": time.time(),
            "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
            "endpoint": endpoint,
            "user": user or "",
            "tokens_in": int(tokens_in or 0),
            "tokens_out": int(tokens_out or 0),
            "ok": bool(ok),
            "latency_ms": int(latency_ms or 0),
            "error": (error or "")[:200],
        }
        for k, v in extra.items():
            row[k] = v
        path = _log_path()
        if not path:
            return
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass  # 日志失败绝不影响业务
