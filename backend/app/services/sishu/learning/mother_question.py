# -*- coding: utf-8 -*-
# [sishu port] v4批6 特制件：vendor deeptutor/learning/mother_question.py 的模型块+存储换芯。
# 模型=逐字复制（mq_models.py 再导出）；MotherQuestionStore 文件存储→PG 单轨
# （app.services.sishu_data.mq_store.MotherQuestionStorePG——方法面 vendor 语义 1:1，
#  用户作用域经 multi_user context 上下文变量，?u= 隔离语义不变）。
# 本件为特制件（脚本 _v4_port_batch6.py 播种自 scripts/sishu_port_special/）。
"""Mother question (母题) + variant (变式题) data models and store.

Migrated from ragflow/wrong_question_api.py to DeepTutor's learning layer.
A mother question is a canonical problem archetype (e.g. 鸡兔同笼) that:
  - links to a DeepTutor KnowledgePoint via knowledge_point_id (reuses mastery + scheduler)
  - has many variants (变式题) for spaced-repetition practice
  - can be turned into a Book (course) with animation/quiz/flash_cards blocks

v4批6：存储层换 PG 单轨（协议 E v2——批6 6.2 迁移 184+6+27 行入 sishu_mq_* 表）。
"""
from __future__ import annotations

from app.services.sishu.learning.mq_models import (  # noqa: F401
    Attempt,
    MotherQuestion,
    QuestionVariant,
    _gen_id,
    _now,
)
from app.services.sishu_data.mq_store import MotherQuestionStorePG as MotherQuestionStore

__all__ = [
    "MotherQuestion",
    "QuestionVariant",
    "Attempt",
    "MotherQuestionStore",
    "_gen_id",
    "_now",
]
