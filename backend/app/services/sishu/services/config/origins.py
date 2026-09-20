# -*- coding: utf-8 -*-
# [sishu port] v4批6 机械复制自 vendor deeptutor/services/config/origins.py（1:1 语义，仅 import 改写）。
# 批16 vendor 物理删除后的存活拷贝；上游修订需回灌本件（复刻纪律）。
from __future__ import annotations

import re
from typing import Any, Iterable
from urllib.parse import urlparse

_ORIGIN_SEPARATORS = re.compile(r"[,;\n]+")


def _raw_origin_items(value: Any) -> Iterable[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for item in value:
            items.extend(_raw_origin_items(item))
        return items
    return _ORIGIN_SEPARATORS.split(str(value))


def normalize_origin(value: Any) -> str:
    """Normalize a browser Origin value for CORS allowlists.

    Operators often paste values as ``host:port`` or separate multiple origins
    with semicolons. Browsers always send an Origin as ``scheme://host[:port]``.
    This helper makes common deployment input tolerant while keeping the output
    as exact origins for Starlette's CORSMiddleware.
    """

    origin = str(value or "").strip().rstrip("/")
    if not origin:
        return ""
    if origin in {"*", "null"}:
        return origin
    if "://" not in origin:
        origin = f"http://{origin}"

    try:
        parsed = urlparse(origin)
    except ValueError:
        return origin
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return origin


def normalize_origins(value: Any) -> list[str]:
    origins: list[str] = []
    seen: set[str] = set()
    for raw in _raw_origin_items(value):
        origin = normalize_origin(raw)
        if origin and origin not in seen:
            origins.append(origin)
            seen.add(origin)
    return origins
