# -*- coding: utf-8 -*-
"""⑤批1（存储边界 DAO 化）：learner_profile tupu 侧实现——批 1 给纯函数+空画像缺省
（build_learner_profile 的 PG 读取面批 2 随九工具落），算法件 import 不断链。"""
from __future__ import annotations

import re
from typing import Any


def _strip_chapter_prefix(name: str) -> str:
    """`1.1_正数和负数` -> `正数和负数` (drop leading `n.n_`).——DeepTutor 纯函数搬运。"""
    return re.sub(r"^\d+(\.\d+)*_", "", name or "").strip()


def build_learner_profile(user_id: str = "default") -> Any:
    """tupu 侧画像构建（批 1 缺省=空画像：weak/strong/due 全空——select_exercises
    对空画像全部 normal，语义与 DeepTutor 无数据路径一致）。批 2 接 PG 读取面。"""
    uid = user_id

    class _EmptyProfile:
        kp_mastery: dict = {}
        weak_points: list = []
        strong_points: list = []
        due_reviews: list = []

    p = _EmptyProfile()
    p.user_id = uid
    return p


__all__ = ["_strip_chapter_prefix", "build_learner_profile"]
