# -*- coding: utf-8 -*-
"""⑤补补-4 步骤 1：mastery_path 核心模型迁移（DeepTutor learning/models.py 字段语义保持）。

- LearningModule：学习模块=章节内知识点组合（id/name/order/pass_threshold/knowledge_points）；
- LearningStage：mastery path 循环六态（diagnostic→explain→feynman_check→practice→
  error_diagnosis→review）——tupu 侧当前消费 learn/practice/review 三态，全枚举保留语义。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LearningStage(str, Enum):
    """DeepTutor LearningStage 全枚举（字段语义保持——消费面按需取值）。"""

    DIAGNOSTIC = "diagnostic"
    EXPLAIN = "explain"
    FEYNMAN_CHECK = "feynman_check"
    PRACTICE = "practice"
    ERROR_DIAGNOSIS = "error_diagnosis"
    REVIEW = "review"


@dataclass
class LearningModule:
    """DeepTutor LearningModule 平移（pydantic→dataclass，字段名/缺省值不变）。"""

    id: str
    name: str
    order: int = 0
    pass_threshold: float = 0.7
    knowledge_points: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "order": self.order,
            "pass_threshold": self.pass_threshold, "knowledge_points": self.knowledge_points,
        }


__all__ = ["LearningModule", "LearningStage"]
