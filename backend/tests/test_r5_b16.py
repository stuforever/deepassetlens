# -*- coding: utf-8 -*-
"""R5批⑯（清单安全）契约测试。

- practice_generator._cache_path：chapter_id 净化（穿越拒绝）
- （R5：vendor api/main 与 question 锚定测试随删除面移除）
变异锚点：净化/包装/收口任一删除 → 对应测红。
"""
import inspect

import pytest

from app.services.sishu_full.learning import practice_generator as pg


def test_cache_path_sanitized():
    assert pg._cache_path("ch-1").name == "ch-1.json"
    assert pg._cache_path("第3章_要点").name == "第3章_要点.json"
    for bad in ("../evil", "a/b", "a:b", "", None, "x" * 200):
        with pytest.raises(ValueError):
            pg._cache_path(bad)
