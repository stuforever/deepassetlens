# -*- coding: utf-8 -*-
"""M04 单测：三组层级校验/master_activity 打点归一/唯一性/关系名缺省（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M04 spec §八验收标准锚定现有实现）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from fastapi import HTTPException  # noqa: E402

from app.api.entity_relation_manage import (  # noqa: E402
    _clean_text,
    _norm_uuid_str,
    _validate_group_entities,
)


def _e(concept_id, name="e"):
    """实体桩（concept_id 决定层级，经 concept_map 推断）。"""
    from app.models.base import Entity
    return Entity(entity_name=name, concept_id=concept_id, id=concept_id)


def _cmap(level):
    """concept_map 桩：concept_id→level（每个实体独立 concept_id）。"""
    from app.models.base import Concept
    return {f"c{level}a": Concept(id=f"c{level}a", name=f"c{level}a", level=level),
            f"c{level}b": Concept(id=f"c{level}b", name=f"c{level}b", level=level)}


# ---------------------------------------------------------------------------
# 任务 1：三组层级校验
# ---------------------------------------------------------------------------

def test_group_level_matrix():
    """三组合法矩阵：master_master L2↔L2 / master_activity L2→L4 / activity_activity L4↔L4。
    变异锚点：层级校验删/改宽 → 非法层级数据入表。"""
    assert _validate_group_entities("master_master", _e("c2a"), _e("c2b"), _cmap(2)) is None
    assert _validate_group_entities("master_activity", _e("c2a"), _e("c4a"), _cmap(2) | _cmap(4)) is None
    assert _validate_group_entities("activity_activity", _e("c4a"), _e("c4b"), _cmap(4)) is None
    # 非法层级 → 400
    for group, s, t in [("master_master", 2, 4), ("master_activity", 4, 2),
                        ("activity_activity", 2, 4), ("master_master", 4, 4)]:
        with pytest.raises(HTTPException) as ei:
            _validate_group_entities(group, _e(f"c{s}a"), _e(f"c{t}a"), _cmap(s) | _cmap(t))
        assert ei.value.status_code == 400


def test_group_same_entity_rejected():
    """源=目标实体拒绝（spec 关系语义：不允许自环）。
    变异锚点：同 id 判定删 → 自环关系入表。"""
    with pytest.raises(HTTPException) as ei:
        _validate_group_entities("master_master", _e("c2"), _e("c2"), _cmap(2))
    assert ei.value.status_code == 400


def test_norm_uuid_str_and_clean_text():
    """ID 归一（合法 UUID 原样）+文本清理（spec 校验面辅助）。
    变异锚点：清理逻辑删 → 空串/None 入表。"""
    import uuid
    uid = str(uuid.uuid4())
    assert _norm_uuid_str(uid, "id") == uid
    assert _clean_text("  a  ") == "a"
    assert _clean_text(None) is None
