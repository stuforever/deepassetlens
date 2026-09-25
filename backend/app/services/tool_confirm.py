# -*- coding: utf-8 -*-
"""EXEC 确认层 confirm_token 服务（权限体系重构 T8a，design §8.4 两段臂时序）。

confirm_token = HMAC_SHA256(TUPU_INTERNAL_TOKEN, tool|canonical_args|user|ts) + "." + ts
- 绑定四元组：换工具/换参数/换用户/过期（±300s）任一变化即校验失败（重放防护）；
- 密钥=TUPU_INTERNAL_TOKEN 同值复用（design §8.2 不另设第二把，仅存 .env.infra）；
- 预检臂①签发、执行臂②校验；双审计由调用方落（①=approval、②=allow/deny）。
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Tuple

_MAX_AGE_SECONDS = 300  # design §8.2：±300s 新鲜度窗口


def _key() -> bytes:
    return (os.environ.get("TUPU_INTERNAL_TOKEN") or "tupu-dev-internal").encode("utf-8")


def _canonical_args(args: Dict[str, Any]) -> str:
    return json.dumps(args or {}, sort_keys=True, ensure_ascii=False, default=str)


def issue(tool: str, args: Dict[str, Any], user: str) -> str:
    """预检臂①：签发绑定 (tool, args, user, ts) 的确认令牌。"""
    ts = int(time.time())
    body = f"{tool}|{_canonical_args(args)}|{user}|{ts}"
    sig = hmac.new(_key(), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{sig}.{ts}"


def verify(tool: str, args: Dict[str, Any], user: str, token: str,
           now: float | None = None) -> Tuple[bool, str]:
    """执行臂②：校验令牌（四元组绑定 + ±300s 新鲜度）。返回 (ok, 失败原因)。"""
    if not token or "." not in token:
        return False, "缺少 confirm_token（两段臂：须先经预检臂①）"
    sig, ts_s = token.rsplit(".", 1)
    try:
        ts = int(ts_s)
    except ValueError:
        return False, "confirm_token 格式非法"
    now = time.time() if now is None else now
    if abs(now - ts) > _MAX_AGE_SECONDS:
        return False, "confirm_token 已过期（±300s 窗口）——请重新发起预检"
    body = f"{tool}|{_canonical_args(args)}|{user}|{ts}"
    expect = hmac.new(_key(), body.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expect):
        return False, "confirm_token 校验失败（工具/参数/用户不匹配或遭伪造）"
    return True, ""
