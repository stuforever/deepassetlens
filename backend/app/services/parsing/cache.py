# -*- coding: utf-8 -*-
"""④（spec D5）：解析结果内存缓存——checksum→文本；同一文件不重复解析（进程内 TTL 不设，
重启即失效=成本可接受，重解析幂等）。"""
import hashlib
import threading
from pathlib import Path
from typing import Dict

_LOCK = threading.Lock()
_CACHE: Dict[str, str] = {}


def file_checksum(path: Path) -> str:
    """sha256 文件内容（upload 端点写入 doc.checksum）。"""
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def parse_cached(path: Path, checksum: str) -> str:
    """checksum 命中→直接返回；未命中→解析并缓存。"""
    with _LOCK:
        if checksum in _CACHE:
            return _CACHE[checksum]
    from app.services.parsing.factory import parse_file
    text = parse_file(path)
    with _LOCK:
        _CACHE[checksum] = text
    return text
