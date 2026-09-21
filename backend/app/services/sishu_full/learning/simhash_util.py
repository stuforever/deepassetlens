"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""
from __future__ import annotations

from typing import Optional


def _tokenize(text: str) -> list[str]:
    """Chinese chars as single tokens, ASCII alnum lowercased."""
    tokens: list[str] = []
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            tokens.append(ch)
        elif ch.isalnum():
            tokens.append(ch.lower())
    return tokens


def _ngrams(tokens: list[str], n: int = 3) -> list[str]:
    if len(tokens) < n:
        return tokens or []
    return ["".join(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def _hash64(s: str) -> int:
    """Stable 64-bit hash (FNV-1a variant) for the pure-Python fallback."""
    h = 0xCBF29CE484222325
    for b in s.encode("utf-8"):
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return h


def _simhash_pure(features: list[str]) -> int:
    """Pure-Python simhash: weight each feature by 1, accumulate sign bits."""
    v = [0] * 64
    for f in features:
        h = _hash64(f)
        for i in range(64):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1
    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= 1 << i
    return fingerprint


def compute_simhash(title: str, text: str) -> Optional[int]:
    """Compute a 64-bit simhash from title + text. None if empty."""
    raw = f"{title or ''} {text or ''}".strip()
    if not raw:
        return None
    tokens = _tokenize(raw)
    if not tokens:
        return None
    features = _ngrams(tokens, 3)
    try:
        from simhash import Simhash  # type: ignore

        return Simhash(features).value
    except ImportError:
        return _simhash_pure(features)


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")
