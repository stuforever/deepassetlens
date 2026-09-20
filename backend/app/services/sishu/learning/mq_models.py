# -*- coding: utf-8 -*-
# [sishu port] v4批6 机械复制自 vendor deeptutor/learning/mother_question.py L45-122（模型块逐字）。
# 批16 vendor 物理删除后的存活拷贝；独立成件以断 mq_store ↔ mother_question 环。
# 本件为特制件（脚本 _v4_port_batch6.py 播种自 scripts/sishu_port_special/）。
"""Mother question (母题) + variant (变式题) data models.

Migrated from ragflow/wrong_question_api.py to DeepTutor's learning layer.
A mother question is a canonical problem archetype (e.g. 鸡兔同笼) that:
  - links to a DeepTutor KnowledgePoint via knowledge_point_id (reuses mastery + scheduler)
  - has many variants (变式题) for spaced-repetition practice
  - can be turned into a Book (course) with animation/quiz/flash_cards blocks
"""
from __future__ import annotations

import time
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _now() -> float:
    return time.time()


def _gen_id() -> str:
    return uuid.uuid4().hex


class MotherQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    subject: str = "math"
    grade: str | None = None                # 一年级...六年级
    category: str | None = None             # 应用题/计算/几何/统计/综合
    archetype_code: str | None = None       # 内部编码 MQ_CHICKEN_RABBIT
    question_text: str
    standard_answer: str | None = None
    wrong_answer: str | None = None          # 学生错误答案（你的答案）
    detailed_analysis: str | None = None     # 详细解析（文本形式，区别于 solution_steps 列表）
    note: str | None = None                  # 学生笔记
    solution_steps: list[dict[str, Any]] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    difficulty: int = 3                     # 1-5
    knowledge_point_id: str | None = None   # 挂 DeepTutor KnowledgePoint
    textbook_id: str | None = None
    chapter_id: str | None = None
    cover_image_url: str | None = None
    photo_url: str | None = None              # 题目图（原题截图 / 拍照切题小图）
    wrong_answer_image_url: str | None = None  # 错误答案截图
    source_image_url: str | None = None       # 拍照整页原图 URL
    crop_box: list[int] | None = None         # 切题裁剪框 [x1,y1,x2,y2]
    ocr_text: str | None = None               # OCR 识别的原始文本
    has_checkmark: bool | None = None         # 红笔标记（是否有 ✓，None=未检测）
    tags: list[str] = Field(default_factory=list)  # 自由标签
    assets: list[dict[str, Any]] = Field(default_factory=list)  # 多图资产 [{url,type,ocr_text,create_time}]
    simhash: int | None = None
    variant_count: int = 0
    video_count: int = 0
    status: str = "active"                  # active/deleted
    deleted_time: float | None = None       # 软删除时间（回收站排序用）
    mastery_status: str = "not_mastered"    # not_mastered/reviewing/mastered
    wrong_reason: str | None = None        # 错因（错误模式分析用）
    wrong_advice: str | None = None        # 错因改进建议（P2-B LLM 归因输出）
    related_lecture_doc_ids: list[str] = Field(default_factory=list)  # 关联讲义文档ID
    correct_transferred_at: float | None = None  # 转正确题时间（None=未转）
    create_time: float = Field(default_factory=_now)
    update_time: float = Field(default_factory=_now)
    created_at: str = ""  # ISO 时间戳（P2-A 周聚合用；旧数据缺省 "" 向后兼容）


class QuestionVariant(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    mother_id: str
    question_text: str
    answer: str | None = None
    solution_steps: list[dict[str, Any]] = Field(default_factory=list)
    difficulty: int = 3
    variant_type: str | None = None         # 数值变式/情境变式/逆向变式/综合变式
    source: str = "manual"                  # manual/llm_gen/ocr_import
    simhash: int | None = None
    status: str = "active"
    create_time: float = Field(default_factory=_now)
    update_time: float = Field(default_factory=_now)


class Attempt(BaseModel):
    """单次答题记录 (移植自 ragflow WrongQuestionAttempt)."""
    model_config = ConfigDict(extra="ignore")

    id: str
    mother_id: str
    variant_id: str | None = None
    is_correct: bool
    user_answer: str | None = None          # 学生作答
    source: str = "manual"                  # manual/review/photo
    time_spent: float | None = None         # 作答耗时（秒）
    rating: int | None = None              # FSRS 评分 1-4（如使用 FSRS）
    create_time: float = Field(default_factory=_now)


__all__ = [
    "MotherQuestion",
    "QuestionVariant",
    "Attempt",
    "_gen_id",
    "_now",
]
