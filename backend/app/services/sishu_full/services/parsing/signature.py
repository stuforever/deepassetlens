"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping


@dataclass(frozen=True)
class ParserSignature:
    """``(engine, engine_version, output-affecting params)`` identity.

    ``params`` is a sorted tuple of ``(key, value)`` strings so the hash is
    order-independent. Each engine decides which of its config knobs actually
    affect the output bytes and folds only those in via :meth:`build`
    (e.g. MinerU includes ``mode``/``model_version``/``language`` but never
    ``api_token`` or ``local_cli_path``).
    """

    engine: str
    engine_version: str
    params: tuple[tuple[str, str], ...]

    def hash(self) -> str:
        """Short hex digest used as the cache signature dir name."""
        payload = {
            "engine": self.engine,
            "engine_version": self.engine_version,
            "params": [list(item) for item in self.params],
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]

    @classmethod
    def build(
        cls, engine: str, engine_version: str, params: Mapping[str, object]
    ) -> "ParserSignature":
        items = tuple(sorted((str(k), str(v)) for k, v in params.items()))
        return cls(engine=engine, engine_version=engine_version or "", params=items)


__all__ = ["ParserSignature"]
