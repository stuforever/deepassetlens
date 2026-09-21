"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import json
import os
import time
from typing import Any


def _log_path() -> str:
    base: str | None = None
    try:
        from app.services.sishu_full.multi_user.paths import get_current_path_service

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
