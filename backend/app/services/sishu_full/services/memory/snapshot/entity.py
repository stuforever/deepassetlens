"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass
class Entity:
    id: str
    label: str
    ts: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    fingerprint: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


ChangeKind = Literal["added", "modified", "removed"]


@dataclass
class ChangeEntry:
    ts: str
    kind: ChangeKind
    entity_id: str
    label: str
    prev_fingerprint: str | None = None
    new_fingerprint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
