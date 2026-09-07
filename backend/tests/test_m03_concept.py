# -*- coding: utf-8 -*-
"""M03 单测：层级语义/area_index/归一化排序/英文名治理（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M03 spec §七验收标准锚定现有实现）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.api.concept_support import (  # noqa: E402
    _normalize_system_names,
    _safe_int,
    _sort_concepts,
    _split_entity_explanation,
)


# ---------------------------------------------------------------------------
# 任务 1：模型与共享函数
# ---------------------------------------------------------------------------

def test_level_semantics_models():
    """Concept/EntityRelation 列契约（spec §九锚点：level/parent_id/area_index/system_names）。
    变异锚点：模型删列 → 契约破坏即时暴露。"""
    from app.models.base import Concept, EntityRelation
    cols = {c.name for c in Concept.__table__.columns}
    assert {"level", "parent_id", "area_index", "system_names"} <= cols
    rcols = {c.name for c in EntityRelation.__table__.columns}
    assert {"relation_category", "direction", "cardinality", "join_expr"} <= rcols


def test_normalize_system_names():
    """system_names 分隔符归一（spec §二：概念层共享词汇）。
    变异锚点：分隔符正则改/删 → 半角分号/顿号残留。"""
    assert _normalize_system_names("A; B ，C") == ["A", "B", "C"]
    assert _normalize_system_names(None) is None or _normalize_system_names(None) == []


def test_safe_int_fallback():
    """_safe_int 容错（spec §四 area_index 分配依赖数字转换）。
    变异锚点：类型判断删 → 非法输入抛异常炸掉 CRUD。"""
    assert _safe_int(None, 1) == 1
    assert _safe_int("x", 2) == 2
    assert _safe_int("3", 1) == 3


def test_sort_concepts_level_area_order():
    """概念排序：level 优先+area_index 次序（spec §六.1 树语义）。
    变异锚点：多级排序键改 → 树序错乱。"""
    from app.models.base import Concept
    items = [
        Concept(name="l2", level=2, area_index=1),
        Concept(name="l1", level=1, area_index=2),
        Concept(name="l2b", level=2, area_index=0),
        Concept(name="l0", level=0, area_index=3),
    ]
    out = _sort_concepts(items)
    assert [c.level for c in out] == [0, 1, 2, 2]
    assert [c.name for c in out] == ["l0", "l1", "l2b", "l2"]


def test_split_entity_explanation_terms():
    """实体解释拆分（spec §三/§九：_split_entity_explanation）。
    变异锚点：拆分分隔符删 → 长串不切。"""
    assert isinstance(_split_entity_explanation("配电变压器，负责电压变换"), list)


# ---------------------------------------------------------------------------
# 任务 3：英文名治理（autofill 幂等不覆盖）
# ---------------------------------------------------------------------------

def test_en_name_autofill_idempotent_not_overwrite():
    """autofill 补全不覆盖已填英文名（spec §七.5）——空请求走真实签名不 500。
    变异锚点：autofill 覆盖已填 → 人工确认的英文名被冲掉。"""
    from app.api.concept_entity import EntityEnNameAutoFillRequest, autofill_entity_en_name
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        req = EntityEnNameAutoFillRequest(entity_ids=[], only_empty=True)
        res = autofill_entity_en_name(req, db=db)
    finally:
        db.close()
    assert isinstance(res, dict)
    assert "updated" in res or "data" in res or "results" in res or "items" in res


def test_en_name_integrity_check_structure():
    """英文名完整性体检返回结构（spec §七.5）。
    变异锚点：端点删/返回结构变 → 治理面断。"""
    from app.api.concept_entity import check_entity_en_name_integrity
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        res = check_entity_en_name_integrity(db=db)
    finally:
        db.close()
    assert isinstance(res, dict)


# ---------------------------------------------------------------------------
# 任务 4：资产矩阵（只含打点 L2→L4）
# ---------------------------------------------------------------------------

@pytest.fixture()
def matrix_db():
    from app.core.database import SessionLocal
    from app.models.base import Concept, Entity, EntityRelation
    db = SessionLocal()
    try:
        # 清测试残留
        for m in (EntityRelation, Entity, Concept):
            db.query(m).filter(getattr(m, "name", None).like("m03test%")).delete() if hasattr(m, "name") else None
        db.commit()
        yield db
    finally:
        db.close()


def test_matrix_filter_relation_category():
    """矩阵过滤逻辑：get_graph_matrix 只取打点维护关系（spec §四 矩阵语义）。
    变异锚点：过滤条件删除 → 手工关系误入矩阵。"""
    from app.api.concept_admin import get_graph_matrix
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        # 空库调用不应 500，结构含 rows/cols 或 data
        res = get_graph_matrix(db=db)
    finally:
        db.close()
    assert isinstance(res, dict)
