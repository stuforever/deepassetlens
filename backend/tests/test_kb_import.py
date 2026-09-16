# -*- coding: utf-8 -*-
"""⑤R B0（唯一交棒 批2.2）：④ 注册表导入面——教学域 KB 注册表导入④（数据分区 knowledge_bases→导入④）。

- 幂等 upsert：按 (name, type=connected, pointer_params.source) 定位——重复导入零重复；
- 一律 type=connected（R2 D6：删除只删注册行，外部索引零触碰）；
- rag_provider=`tutor_dt`（B0 新白名单值，仅导入面——create 既有白名单零触碰）；
- search 守卫：tutor 域 KB 检索走教学域原通道（vendor 栈），④不透传——422 诚实报错。
测试范式沿 test_kb_engines.py A4：真 MySQL 幂等造数（固定名清理）+直调端点函数。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402
from fastapi import HTTPException  # noqa: E402

ITEMS = [
    {"name": "math-textbook", "description": "Knowledge base: math-textbook", "status": "ready",
     "pointer_params": {"source": "tutor", "workspace": "T:\\ws", "kb_name": "math-textbook"}},
    {"name": "七年级语文上", "description": None, "status": "ready",
     "pointer_params": {"source": "tutor", "workspace": "T:\\ws", "kb_name": "七年级语文上"}},
]


def _cleanup():
    from app.core.database import SessionLocal
    from app.models.knowledge_base import KnowledgeBase
    db = SessionLocal()
    try:
        names = {i["name"] for i in ITEMS}
        for row in db.query(KnowledgeBase).filter(
                KnowledgeBase.type == "connected",
                KnowledgeBase.rag_provider == "tutor_dt").all():
            if (row.pointer_params or {}).get("kb_name") in names:
                db.delete(row)
        db.commit()
    finally:
        db.close()


def _payload():
    from app.api.knowledge_base import KBImport
    return KBImport(source="tutor", items=[KBImport.Item(**i) for i in ITEMS])


def test_import_upsert_idempotent_and_d6():
    """导入幂等（二轮零重复+updated 计数）+ connected 行 D6 语义。变异锚点：
    upsert 退化为 insert → 二轮 imported=2 红；漏 source 键 → 定位漂移红。"""
    _cleanup()
    from app.api import knowledge_base as kb_api
    from app.core.database import SessionLocal
    from app.models.knowledge_base import KnowledgeBase
    db = SessionLocal()
    try:
        my_names = [i["name"] for i in ITEMS]

        def _my_rows(q):
            return q.filter(KnowledgeBase.name.in_(my_names))

        out1 = kb_api.import_knowledge_bases(_payload(), db)
        assert out1["code"] == 200 and out1["data"]["imported"] == 2 and out1["data"]["updated"] == 0

        rows = _my_rows(db.query(KnowledgeBase).filter(
            KnowledgeBase.type == "connected", KnowledgeBase.rag_provider == "tutor_dt")).all()
        assert len(rows) == 2
        by_name = {r.name: r for r in rows}
        assert by_name["math-textbook"].status == "ready"
        assert by_name["math-textbook"].pointer_params["kb_name"] == "math-textbook"
        assert by_name["math-textbook"].pointer_params["source"] == "tutor"

        # 二轮：改 description/status → updated=2，行数不变（幂等）
        items2 = [dict(i, description="改过的描述") for i in ITEMS]
        items2[1]["status"] = "error"
        p2 = kb_api.KBImport(source="tutor", items=[kb_api.KBImport.Item(**i) for i in items2])
        out2 = kb_api.import_knowledge_bases(p2, db)
        assert out2["data"]["imported"] == 0 and out2["data"]["updated"] == 2
        rows2 = _my_rows(db.query(KnowledgeBase).filter(
            KnowledgeBase.type == "connected", KnowledgeBase.rag_provider == "tutor_dt")).all()
        assert len(rows2) == 2
        by_name2 = {r.name: r for r in rows2}
        assert by_name2["math-textbook"].description == "改过的描述"
        assert by_name2["七年级语文上"].status == "error"

        # D6：connected 删除只删注册行（delete 端点函数直调——外部索引零触碰语义）
        kb_api.delete_knowledge_base(by_name2["math-textbook"].id, db)
        remain = _my_rows(db.query(KnowledgeBase).filter(
            KnowledgeBase.type == "connected", KnowledgeBase.rag_provider == "tutor_dt")).all()
        assert len(remain) == 1 and remain[0].name == "七年级语文上"
    finally:
        db.close()
        _cleanup()


def test_import_validation_strict():
    """校验铁则：pointer_params 必填且含 source；name 非空；status 白名单。"""
    from app.api import knowledge_base as kb_api
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        I = kb_api.KBImport.Item
        with pytest.raises(HTTPException) as e1:
            kb_api.import_knowledge_bases(kb_api.KBImport(source="tutor", items=[
                I(name="x1", pointer_params={"workspace": "T:\\ws"})]), db)
        assert e1.value.status_code == 422 and "source" in e1.value.detail
        with pytest.raises(HTTPException) as e2:
            kb_api.import_knowledge_bases(kb_api.KBImport(source="tutor", items=[
                I(name="  ", pointer_params={"source": "tutor"})]), db)
        assert e2.value.status_code == 422
        with pytest.raises(HTTPException) as e3:
            kb_api.import_knowledge_bases(kb_api.KBImport(source="tutor", items=[
                I(name="x2", status="running", pointer_params={"source": "tutor"})]), db)
        assert e3.value.status_code == 422
    finally:
        db.close()


def test_search_guard_tutor_rows():
    """search 守卫：tutor_dt 行 → 422 诚实报错（走教学域原通道），不得误入 ES 族 502。
    变异锚点：撤守卫 → ConnectedESFamily 误命中 → 非 422 红。"""
    _cleanup()
    from app.api import knowledge_base as kb_api
    from app.core.database import SessionLocal
    from app.models.knowledge_base import KnowledgeBase
    db = SessionLocal()
    try:
        kb_api.import_knowledge_bases(_payload(), db)
        row = db.query(KnowledgeBase).filter(
            KnowledgeBase.type == "connected", KnowledgeBase.rag_provider == "tutor_dt",
            KnowledgeBase.name == "math-textbook").first()
        assert row is not None
        with pytest.raises(HTTPException) as e:
            kb_api.search_knowledge_base(row.id, kb_api.KBSearch(query="有理数"), db)
        assert e.value.status_code == 422 and "教学域" in e.value.detail
    finally:
        db.close()
        _cleanup()
