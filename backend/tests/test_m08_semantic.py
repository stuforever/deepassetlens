# -*- coding: utf-8 -*-
"""M08 单测：词条状态机列/双同义面区分/同义词组重复 400/字典检索（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M08 spec §八验收标准锚定现有实现）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.models.base import (  # noqa: E402
    CommonStopWord,
    StandardDict,
    StandardSemanticTerm,
    SynonymGroup,
)


# ---------------------------------------------------------------------------
# 任务 1：词条生命周期模型（spec §三）
# ---------------------------------------------------------------------------

def test_term_lifecycle_columns():
    """词条状态机列契约（spec §三：vector_status/retry_count/last_error/content_hash + 默认值）。
    变异锚点：content_hash 列删 → 变更检测断；source 默认非 graph_extract → 词条凭空手造。"""
    cols = {c.name for c in StandardSemanticTerm.__table__.columns}
    assert {"vector_status", "retry_count", "last_error", "content_hash",
            "canonical_text", "ontology_ref_type", "ontology_ref_id"} <= cols
    assert StandardSemanticTerm.__table__.c.source.default.arg == "graph_extract"
    assert StandardSemanticTerm.__table__.c.vector_status.default.arg == "pending"


def test_two_synonym_surfaces_distinct():
    """双同义面：SynonymGroup(standard_term+synonyms) ≠ StandardDict(non_standard→standard)。
    变异锚点：两表混用 → 检索改写与口径映射语义互污染。"""
    sg = {c.name for c in SynonymGroup.__table__.columns}
    sd = {c.name for c in StandardDict.__table__.columns}
    assert sg != sd
    assert "standard_term" in sg and "synonyms" in sg
    assert "non_standard" in sd and "standard" in sd


def test_stop_word_model():
    """停用词模型（spec §四：word/category/enabled）。
    变异锚点：category 列删 → 清洗分类断。"""
    cols = {c.name for c in CommonStopWord.__table__.columns}
    assert {"word", "category", "enabled"} <= cols


# ---------------------------------------------------------------------------
# 任务 4：同义词组重复 400（spec §八.3）
# ---------------------------------------------------------------------------

def test_synonym_duplicate_rejected():
    """重复 standard_term→400（spec §八.3；synonym.py L58-60）。
    变异锚点：重复校验删 → 同义词组数据漂移。"""
    from app.api.synonym import create_synonym
    from app.api.synonym import SynonymGroupCreate
    from app.core.database import SessionLocal
    from fastapi import HTTPException
    from app.models.base import SynonymGroup
    db = SessionLocal()
    try:
        db.query(SynonymGroup).filter(SynonymGroup.standard_term == "m08dup").delete()
        db.add(SynonymGroup(standard_term="m08dup", synonyms=["a"]))
        db.commit()
        try:
            create_synonym(SynonymGroupCreate(standard_term="m08dup", synonyms=["b"]), db=db)
            assert False, "应 400"
        except HTTPException as e:
            assert e.status_code == 400
    finally:
        db.query(SynonymGroup).filter(SynonymGroup.standard_term == "m08dup").delete()
        db.commit(); db.close()


def test_synonym_create_ok():
    """合法同义词组创建（spec §八.3）。
    变异锚点：创建路径断 → 检索改写资产无源。"""
    from app.api.synonym import SynonymGroupCreate, create_synonym
    from app.core.database import SessionLocal
    from app.models.base import SynonymGroup
    db = SessionLocal()
    try:
        db.query(SynonymGroup).filter(SynonymGroup.standard_term == "m08ok").delete()
        db.commit()
        res = create_synonym(SynonymGroupCreate(standard_term="m08ok", synonyms=["x", "y"]), db=db)
        assert isinstance(res, dict)
    finally:
        db.query(SynonymGroup).filter(SynonymGroup.standard_term == "m08ok").delete()
        db.commit(); db.close()
