"""RecitationStore — attempts per-u JSON 留档存储（M25 三年级上批次 T10）。

规格 §4.5：每个用户在自己的 workspace 下以
``recitation/attempts.json`` 留档背诵/默写记录。路径由
``get_path_service().get_workspace_dir()`` 解析——当前用户上下文决定
workspace 根，per-u 隔离在路径级天然成立（照 ``mother_question.py``
L134 存储惯例同款）。

存取惯例（mother_questions 同款）：load → append → save，
``atomic_write_text`` 原子写 + 模块级锁；文件恒持最近
``MAX_ATTEMPTS`` 条（50 条截断，规格 §4.6 GET 历史上限）。
partial attempt（segmented=true 未完成态，§4.8）照常留档——
本层只做存储，不校验 per_segment 完整性。
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from deeptutor.services.file_io import atomic_write_text as _atomic_write_text
from deeptutor.services.path_service import get_path_service

__all__ = ["RecitationAttempt", "RecitationStore"]

# 文件级截断上限：每 u 只留最近 50 条（规格 §4.6：GET 历史「最近 50 条」）
MAX_ATTEMPTS = 50

# 模块级重入锁：并发 append 的 load-modify-save 互斥
# （照 mother_question._cas_lock 惯例，跨 store 实例生效）。
_lock = threading.RLock()


def _now() -> float:
    return time.time()


def _gen_id() -> str:
    return uuid.uuid4().hex


class RecitationAttempt(BaseModel):
    """单次背诵/默写留档记录 — schema = 规格 §4.5，一字段不多不少。"""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(default_factory=_gen_id)
    ts: float = Field(default_factory=_now)
    u: str                                   # 用户 slug（?u= 语义；与路径隔离两个独立层面）
    textbook_id: str
    chapter_id: str
    material_id: str
    material_title: str
    mode: Literal["recite", "dictation"]     # 背诵/默写
    input_mode: Literal["voice", "type"]     # 语音/打字
    segmented: bool = False                  # 逐段模式；partial attempt 亦为 True（§4.8 未完成态）
    total_score: float = 0.0
    per_segment: list[dict[str, Any]] = Field(default_factory=list)  # [{idx, score}]
    wrong_chars: list[str] = Field(default_factory=list)
    homophones: list[str] = Field(default_factory=list)


class RecitationStore:
    """JSON-backed store for recitation attempts.

    Layout under <workspace>/recitation/:
      attempts.json - list of RecitationAttempt（最近 MAX_ATTEMPTS 条）
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or (get_path_service().get_workspace_dir() / "recitation")
        self._root.mkdir(parents=True, exist_ok=True)
        self._path = self._root / "attempts.json"

    # ---------- 留档 ----------

    def record(
        self,
        *,
        u: str,
        textbook_id: str,
        chapter_id: str,
        material_id: str,
        material_title: str,
        mode: Literal["recite", "dictation"],
        input_mode: Literal["voice", "type"],
        segmented: bool = False,
        total_score: float = 0.0,
        per_segment: list[dict[str, Any]] | None = None,
        wrong_chars: list[str] | None = None,
        homophones: list[str] | None = None,
        ts: float | None = None,
    ) -> RecitationAttempt:
        """留档一次 attempt：append+save，文件截断至最近 MAX_ATTEMPTS 条。

        ``ts`` 缺省取当前时间；测试可显式传参钉死顺序。
        partial attempt（§4.8）：segmented=True 且 per_segment 不足全部
        段落时照常入库，本层不做完整性校验。
        ``mode``/``input_mode`` 用 Literal 静态化（T10 审查次要-1）——
        非法值在调用点即被类型检查拦截，运行时另有模型 ValidationError 兜底。
        """
        att = RecitationAttempt(
            u=u,
            textbook_id=textbook_id,
            chapter_id=chapter_id,
            material_id=material_id,
            material_title=material_title,
            mode=mode,
            input_mode=input_mode,
            segmented=segmented,
            total_score=total_score,
            per_segment=list(per_segment or []),
            wrong_chars=list(wrong_chars or []),
            homophones=list(homophones or []),
            ts=_now() if ts is None else ts,
        )
        with _lock:
            items = self._load()
            items.append(att)
            self._save(items[-MAX_ATTEMPTS:])
        return att

    def list_attempts(
        self,
        *,
        u: str | None = None,
        chapter_id: str | None = None,
    ) -> list[RecitationAttempt]:
        """历史记录：最近 MAX_ATTEMPTS 条倒序（最新在前）。

        ``u``/``chapter_id`` 给定时按记录字段过滤——文件本身已按
        当前用户 workspace 物理隔离，此处的 u 过滤是记录字段层面的
        第二道防线（两层面各自被测试钉死）。
        """
        items = self._load()
        if u is not None:
            items = [a for a in items if a.u == u]
        if chapter_id is not None:
            items = [a for a in items if a.chapter_id == chapter_id]
        items.sort(key=lambda a: a.ts, reverse=True)
        return items[:MAX_ATTEMPTS]

    # ---------- 内部 ----------

    def _load(self) -> list[RecitationAttempt]:
        if not self._path.exists():
            return []
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return [RecitationAttempt.model_validate(d) for d in data]

    def _save(self, items: list[RecitationAttempt]) -> None:
        text = json.dumps(
            [a.model_dump(mode="json") for a in items],
            ensure_ascii=False, indent=2,
        )
        _atomic_write_text(self._path, text)
