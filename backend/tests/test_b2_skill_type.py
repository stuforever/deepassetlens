# -*- coding: utf-8 -*-
"""B2（v4§三）契约测试：技能注册表 type 分型（scenario|general）。

先红后绿（TDD）——实现前运行应 ImportError/AttributeError 失败：
- Skill.type 列（NULL=存量未分型；skill_type=框架类型 python/sql/claude… 与本列正交）
- init_db 幂等补列（照 _ensure_expert_card_columns 范式）
- create 读写 type / update 改型 / SkillService.list_skills type 过滤
- 列表出参含 type 字段
- 请求模型校验：type ∈ {scenario, general, None}，非法值 pydantic 拒收
"""
import uuid

import pytest


@pytest.fixture()
def tmp_skill_code():
    """真库建一个技能的 skill_code，跑完清理（B1 范式）。"""
    from app.core.database import SessionLocal
    from app.models.skill import Skill
    code = f"b2type_{uuid.uuid4().hex[:8]}"
    yield code
    db = SessionLocal()
    try:
        for row in db.query(Skill).filter(Skill.skill_code == code).all():
            db.delete(row)
        db.commit()
    finally:
        db.close()


def test_skill_model_has_type_column():
    from app.models.skill import Skill
    assert hasattr(Skill, "type")


def test_ensure_skill_type_column_idempotent():
    from app.core.database import SessionLocal
    from app.core.init_db import _ensure_skill_type_column
    from sqlalchemy import text
    db = SessionLocal()
    try:
        _ensure_skill_type_column(db)
        _ensure_skill_type_column(db)  # 幂等：二跑不炸
        n = db.execute(text(
            "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE "
            "TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'skills' AND COLUMN_NAME = 'type'"
        )).scalar()
        assert n == 1
    finally:
        db.close()


def test_create_with_type_scenario_roundtrip(tmp_skill_code):
    from app.core.database import SessionLocal
    from app.models.skill import Skill
    from app.services.skill_manager import SkillService
    db = SessionLocal()
    try:
        skill = SkillService.create_skill(db, {
            "skill_code": tmp_skill_code, "name": "B2分型测试", "type": "scenario"})
        db.refresh(skill)
        assert skill.type == "scenario"
    finally:
        db.close()


def test_create_without_type_is_none(tmp_skill_code):
    from app.core.database import SessionLocal
    from app.services.skill_manager import SkillService
    db = SessionLocal()
    try:
        skill = SkillService.create_skill(db, {"skill_code": tmp_skill_code, "name": "B2分型缺省"})
        db.refresh(skill)
        assert skill.type is None
    finally:
        db.close()


def test_update_type(tmp_skill_code):
    from app.core.database import SessionLocal
    from app.services.skill_manager import SkillService
    db = SessionLocal()
    try:
        skill = SkillService.create_skill(db, {"skill_code": tmp_skill_code, "name": "B2改型"})
        out = SkillService.update_skill(db, skill.skill_id, {"type": "general"})
        db.refresh(out)
        assert out.type == "general"
    finally:
        db.close()


def test_list_filter_by_type(tmp_skill_code):
    from app.core.database import SessionLocal
    from app.services.skill_manager import SkillService
    db = SessionLocal()
    code_b = f"{tmp_skill_code}_b"
    try:
        SkillService.create_skill(db, {"skill_code": tmp_skill_code, "name": "B2场景", "type": "scenario"})
        SkillService.create_skill(db, {"skill_code": code_b, "name": "B2通用", "type": "general"})
        rows = SkillService.list_skills(db, type="scenario", limit=500)
        codes = {r.skill_code for r in rows}
        assert tmp_skill_code in codes
        assert code_b not in codes
    finally:
        from app.models.skill import Skill as _S
        for c in (code_b,):
            for row in db.query(_S).filter(_S.skill_code == c).all():
                db.delete(row)
        db.commit()
        db.close()


def test_list_response_includes_type(tmp_skill_code):
    from app.core.database import SessionLocal
    from app.api.v2_skills_crud import list_skills
    from app.services.skill_manager import SkillService
    db = SessionLocal()
    try:
        SkillService.create_skill(db, {"skill_code": tmp_skill_code, "name": "B2出参", "type": "scenario"})
        resp = list_skills(status=None, skill_type=None, type="scenario", skip=0, limit=500, db=db)
        item = next(i for i in resp.data if i["skill_code"] == tmp_skill_code)
        assert item["type"] == "scenario"
    finally:
        db.close()


def test_request_model_type_validation():
    from pydantic import ValidationError
    from app.api.skill_v2_support import SkillCreateRequest, SkillUpdateRequest
    assert SkillCreateRequest(name="x").type is None
    assert SkillCreateRequest(name="x", type="scenario").type == "scenario"
    assert SkillUpdateRequest(type="general").type == "general"
    with pytest.raises(ValidationError):
        SkillCreateRequest(name="x", type="weird")
    with pytest.raises(ValidationError):
        SkillUpdateRequest(type="weird")
