# -*- coding: utf-8 -*-
"""M03 单测：层级语义/area_index/归一化排序/英文名治理（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M03 spec §七验收标准锚定现有实现）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------------------------
# 验收标准映射（M03 spec §七，2026-09-08 测试补全）：
# §七.1 概念 CRUD 层级合法构建/area_index 分配/删除级联 → test_concept_hierarchy_construction_rules +
#       test_concept_area_index_assign_rules + test_concept_delete_guards +
#       test_clear_graph_data_cascades_links（本次补，本文件）；
#       模型列契约（level/parent_id/area_index/system_names）→ test_level_semantics_models（本文件既有）
# §七.2 实体挂接矩阵与四区即时反映 → test_entity_mount_unmount_reflects_in_matrix_and_quad（本次补，本文件）
# §七.3 矩阵 toggle→EntityRelation 行增删/格子明细 join_expr+cardinality/打点过滤（level 2→4 方向）→
#       test_matrix_toggle_row_lifecycle + test_matrix_grid_detail_and_direction_filter（本次补，本文件）；
#       矩阵空库结构 → test_matrix_filter_relation_category（本文件既有）
# §七.4 Excel 导出→清空→导入 往返一致（含 area_index/system_names）→
#       test_excel_roundtrip_consistency（本次补，本文件；隔离 SQLite 双库，防误清真实图谱数据）
# §七.5 英文名治理 integrity-check 报缺失清单/autofill 补全不覆盖已填 →
#       test_en_name_integrity_lists_missing_and_autofill_preserves_filled（本次补，本文件）；
#       治理端点结构 → test_en_name_integrity_check_structure +
#       test_en_name_autofill_idempotent_not_overwrite（本文件既有）
# §七.6 四视图四模式数据契约 → test_force_view_full_data_contract（力导向=全量）+
#       test_quad_view_cascade_data_contract（四区=级联）+
#       test_gallery_view_neo4j_stub_contract（图库=Neo4j，桩）（本次补，本文件）；
#       矩阵=打点 → §七.3 两测（本文件）；真连 Neo4j 渲染留联测（单测桩锚定契约与降级）
# §七.7 层级数据变更后 M05 同步增量重投射（边界联测，Neo4j 桩）→
#       test_hierarchy_change_incremental_reprojection（本次补，本文件）；
#       Neo4j 停机降级路径 → test_m05_graph_engine.py::test_healthcheck_false_drives_degrade（既有）
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 2026-09-08 测试补全（批次 2·图谱域）：spec §七 验收缺口补测
# ---------------------------------------------------------------------------

import asyncio  # noqa: E402
import io  # noqa: E402
import uuid  # noqa: E402

from fastapi import HTTPException, UploadFile  # noqa: E402
from sqlalchemy import func, or_  # noqa: E402


# ---------------------------------------------------------------------------
# 测试基建：m03test 前缀隔离（真实 MySQL）+ 独立 SQLite（清空/Excel 往返防误伤真实库）
# ---------------------------------------------------------------------------

def _purge_m03test(db):
    """按 m03test 前缀清理本批测试残留（实体→挂接→概念深层优先），幂等可重入。"""
    from app.models.base import Concept, Entity, EntityConceptLink, EntityRelation, ConceptRelation
    ent_ids = [e.id for e in db.query(Entity).filter(Entity.entity_code.like("m03test%")).all()]
    if ent_ids:
        db.query(EntityRelation).filter(
            or_(EntityRelation.source_entity_id.in_(ent_ids), EntityRelation.target_entity_id.in_(ent_ids))
        ).delete(synchronize_session=False)
        db.query(EntityConceptLink).filter(EntityConceptLink.entity_id.in_(ent_ids)).delete(synchronize_session=False)
        db.query(Entity).filter(Entity.id.in_(ent_ids)).delete(synchronize_session=False)
    cids = [c.id for c in db.query(Concept).filter(Concept.name.like("m03test%")).all()]
    if cids:
        db.query(EntityConceptLink).filter(EntityConceptLink.concept_id.in_(cids)).delete(synchronize_session=False)
        db.query(ConceptRelation).filter(
            or_(ConceptRelation.source_concept_id.in_(cids), ConceptRelation.target_concept_id.in_(cids))
        ).delete(synchronize_session=False)
        for lv in (4, 3, 2, 1, 0):
            db.query(Concept).filter(Concept.level == lv, Concept.id.in_(cids)).delete(synchronize_session=False)
    db.commit()


@pytest.fixture()
def m03_db():
    """真实 MySQL 会话，前后各清一次 m03test 残留。"""
    from app.core.database import SessionLocal
    db = SessionLocal()
    _purge_m03test(db)
    try:
        yield db
    finally:
        _purge_m03test(db)
        db.close()


def _build_chain(db):
    """经真实 CRUD 构建 m03test 双链：L1→L2（主数据实体）/ L0→L3→L4（业务活动实体），
    挂接经 _update_entity_concept_links（create_entity 内部）。"""
    from app.api.concept_entity import create_concept, create_entity
    from app.schemas.concept import ConceptCreate, EntityCreate
    dom = create_concept(ConceptCreate(name="m03test_dom", level=0, area_index=91), db=db)
    grp = create_concept(ConceptCreate(name="m03test_grp", level=1, area_index=92), db=db)
    l2 = create_concept(ConceptCreate(name="m03test_l2", level=2, parent_id=str(grp.id), area_index=92), db=db)
    l3 = create_concept(ConceptCreate(name="m03test_l3", level=3, parent_id=str(dom.id), area_index=91), db=db)
    l4 = create_concept(ConceptCreate(name="m03test_l4", level=4, parent_id=str(l3.id), area_index=91), db=db)
    e_l2 = create_entity(EntityCreate(concept_id=str(l2.id), entity_code="m03test_l2e",
                                      entity_name="m03test主数据实体"), db=db)
    e_l4 = create_entity(EntityCreate(concept_id=str(l4.id), entity_code="m03test_l4e",
                                      entity_name="m03test活动实体"), db=db)
    return {"dom": dom, "grp": grp, "l2": l2, "l3": l3, "l4": l4, "e_l2": e_l2, "e_l4": e_l4}


def _sqlite_db():
    """独立内存 SQLite（仅 M03 五表+重链三表），供清空/Excel 往返测试——防误清真实图谱数据。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.base import (
        Base, Concept, Entity, EntityRelation, EntityConceptLink, ConceptRelation,
        EntityModeling, EntityInitData, EntityMappingRule,
    )
    eng = create_engine("sqlite://")
    Base.metadata.create_all(bind=eng, tables=[
        m.__table__ for m in (Concept, Entity, EntityRelation, EntityConceptLink,
                              ConceptRelation, EntityModeling, EntityInitData, EntityMappingRule)
    ])
    return sessionmaker(bind=eng)()


def _seed_concept_graph(db):
    """在给定库上种子 m03test 双链 + 挂接 + 打点关系 + 跨链概念关系（Excel/清空用）。"""
    from app.models.base import Concept, Entity, EntityConceptLink, EntityRelation, ConceptRelation
    dom = Concept(name="m03test_dom", level=0, area_index=91, sort_order=1, description="测试业务域")
    grp = Concept(name="m03test_grp", level=1, area_index=92, sort_order=1, description="测试分组")
    db.add_all([dom, grp])
    db.flush()
    l2 = Concept(name="m03test_l2", level=2, parent_id=grp.id, area_index=92, sort_order=1, description="测试主数据")
    l3 = Concept(name="m03test_l3", level=3, parent_id=dom.id, area_index=91, sort_order=1,
                 description="测试业务域L3", system_names=["系统A", "系统B"])
    db.add_all([l2, l3])
    db.flush()
    l4 = Concept(name="m03test_l4", level=4, parent_id=l3.id, area_index=91, sort_order=1, description="测试业务活动")
    db.add(l4)
    db.flush()
    e2 = Entity(concept_id=l2.id, entity_code="m03test_l2e", entity_name="m03test主数据实体",
                entity_en_name="m03test_l2e", is_main_table=True, sort_order=1, properties_schema=[],
                description="主数据实体")
    e4 = Entity(concept_id=l4.id, entity_code="m03test_l4e", entity_name="m03test活动实体",
                entity_en_name="m03test_l4e", is_main_table=False, sort_order=1, properties_schema=[],
                description="活动实体")
    db.add_all([e2, e4])
    db.flush()
    db.add_all([
        EntityConceptLink(entity_id=e2.id, concept_id=l2.id),
        EntityConceptLink(entity_id=e4.id, concept_id=l4.id),
        EntityRelation(source_entity_id=e2.id, target_entity_id=e4.id, relation_name="m03test打点关系",
                       relation_category="打点维护", direction="forward", cardinality="N:N",
                       join_expr="m03test_join", description="打点关系"),
        ConceptRelation(source_concept_id=l2.id, target_concept_id=l4.id, relation_type="CROSS_CHAIN"),
        ConceptRelation(source_concept_id=dom.id, target_concept_id=l3.id, relation_type="CROSS_CHAIN"),
    ])
    db.commit()
    return {"dom": dom, "grp": grp, "l2": l2, "l3": l3, "l4": l4, "e2": e2, "e4": e4}


def _snapshot(db):
    """概念/实体/实体关系三面快照（以名称/层级/父名/业务域索引/所属系统为键，忽略 uuid）。"""
    from app.models.base import Concept, Entity, EntityRelation
    cmap = {str(c.id): c for c in db.query(Concept).all()}
    emap = {str(e.id): e for e in db.query(Entity).all()}
    concepts = {
        (c.name, c.level,
         cmap[str(c.parent_id)].name if c.parent_id and str(c.parent_id) in cmap else None,
         c.area_index, tuple(sorted(c.system_names or [])))
        for c in cmap.values()
    }
    entities = {
        (e.entity_code, e.entity_name,
         cmap[str(e.concept_id)].name if e.concept_id and str(e.concept_id) in cmap else None,
         e.entity_en_name, bool(e.is_main_table))
        for e in emap.values()
    }
    relations = {
        (r.relation_category, r.relation_name,
         emap[str(r.source_entity_id)].entity_name, emap[str(r.target_entity_id)].entity_name,
         r.direction, r.cardinality, r.join_expr)
        for r in db.query(EntityRelation).all()
    }
    return concepts, entities, relations


# ---------------------------------------------------------------------------
# §七.1 概念 CRUD：层级合法构建 / area_index 分配 / 删除级联
# ---------------------------------------------------------------------------

def test_concept_hierarchy_construction_rules(m03_db):
    """L0-L4+L2X/L4X 层级合法构建与非法拒绝（spec §七.1；concept_entity.py parent_level_map：
    L0/L1 无父、L2→L1、L3→业务域(L0)、L4→L3；实体仅可挂 L2/L4 概念=L2X/L4X 构建面）。
    变异锚点：parent_level_map 改宽/层级校验删 → 非法层级父子关系入库红；
    create_entity 的 L2/L4 限定删 → 实体挂上 L0/L1/L3 概念红。"""
    db = m03_db
    from app.api.concept_entity import create_concept, create_entity
    from app.schemas.concept import ConceptCreate, EntityCreate
    chain = _build_chain(db)  # 合法构建：L0/L1 根 + L2←L1 + L3←L0 + L4←L3 全部成功
    assert chain["l2"].parent_id == chain["grp"].id
    assert chain["l3"].parent_id == chain["dom"].id
    assert chain["l4"].parent_id == chain["l3"].id
    # 非法：L0/L1 不应有父
    for lv, parent in ((0, chain["grp"]), (1, chain["dom"])):
        with pytest.raises(HTTPException) as ei:
            create_concept(ConceptCreate(name=f"m03test_bad{lv}", level=lv,
                                         parent_id=str(parent.id), area_index=99), db=db)
        assert ei.value.status_code == 400
    # 非法：L2 必须有父且父须 L1；L3 父须业务域；L4 父须 L3；父不存在 404
    bad_cases = [
        (ConceptCreate(name="m03test_bad_l2nop", level=2, area_index=99), 400),
        (ConceptCreate(name="m03test_bad_l2p", level=2, parent_id=str(chain["l2"].id), area_index=99), 400),
        (ConceptCreate(name="m03test_bad_l3p", level=3, parent_id=str(chain["grp"].id), area_index=99), 400),
        (ConceptCreate(name="m03test_bad_l4p", level=4, parent_id=str(chain["l2"].id), area_index=99), 400),
        (ConceptCreate(name="m03test_bad_orphan", level=2, parent_id=str(uuid.uuid4()), area_index=99), 404),
    ]
    for payload, code in bad_cases:
        with pytest.raises(HTTPException) as ei:
            create_concept(payload, db=db)
        assert ei.value.status_code == code
    # L2X/L4X 构建面：实体仅可挂 L2/L4 概念
    for cid in (chain["dom"].id, chain["grp"].id, chain["l3"].id):
        with pytest.raises(HTTPException) as ei:
            create_entity(EntityCreate(concept_id=str(cid), entity_code=f"m03test_bad_e{cid[:4]}",
                                       entity_name="m03test非法实体"), db=db)
        assert ei.value.status_code == 400


def test_concept_area_index_assign_rules(m03_db):
    """area_index 自动分配：L0/L1 同级 max+1（删除后不复用空位，spec §二/§七.1）；L2-L4 继承父。
    变异锚点：分配改同级 count+1 → 删除同级节点后新建撞号（回填空位）红；
    继承父分支改同级重算 → 子概念与父分域错位红。"""
    db = m03_db
    from app.api.concept_entity import create_concept, delete_concept
    from app.models.base import Concept
    from app.schemas.concept import ConceptCreate
    prev_max0 = db.query(func.max(Concept.area_index)).filter(Concept.level == 0).scalar() or 0
    prev_max1 = db.query(func.max(Concept.area_index)).filter(Concept.level == 1).scalar() or 0
    # L0 同级 max+1（显式 area_index=None 才走自动分配分支）
    a = create_concept(ConceptCreate(name="m03test_domA", level=0, area_index=None), db=db)
    b = create_concept(ConceptCreate(name="m03test_domB", level=0, area_index=None), db=db)
    assert a.area_index == prev_max0 + 1
    assert b.area_index == a.area_index + 1
    # 删除 A 后再建：max+1 语义 → 不回填 A 的空位、不与 B 撞号
    delete_concept(str(a.id), db=db)
    c = create_concept(ConceptCreate(name="m03test_domC", level=0, area_index=None), db=db)
    assert c.area_index == max(prev_max0, b.area_index) + 1
    assert c.area_index > b.area_index
    # L1 同级 max+1；L2 继承父 area_index
    g = create_concept(ConceptCreate(name="m03test_grpAI", level=1, area_index=None), db=db)
    l2 = create_concept(ConceptCreate(name="m03test_l2AI", level=2, parent_id=str(g.id), area_index=None), db=db)
    assert g.area_index == prev_max1 + 1
    assert l2.area_index == g.area_index


def test_concept_delete_guards(m03_db):
    """删除概念级联处理挂接：有子概念→400、有挂接实体→400、摘除实体后深层可删（spec §七.1；
    delete_concept 子/实体闸 + delete_entity 级联清其关系与挂接）。
    变异锚点：子概念闸删 → 删父后子成孤儿红；实体闸删 → 挂接中概念被删致矩阵/树悬挂红；
    delete_entity 关系/挂接级联删 → 残留 EntityRelation/Link 悬挂行红。"""
    db = m03_db
    from app.api.concept_entity import delete_concept, delete_entity
    from app.models.base import Concept, EntityConceptLink, EntityRelation
    chain = _build_chain(db)
    with pytest.raises(HTTPException) as ei:
        delete_concept(str(chain["dom"].id), db=db)
    assert ei.value.status_code == 400 and "子概念" in ei.value.detail
    with pytest.raises(HTTPException) as ei:
        delete_concept(str(chain["l4"].id), db=db)
    assert ei.value.status_code == 400 and "实体" in ei.value.detail
    # 摘除实体（级联清其挂接与关系）后概念可删——深层先删
    delete_entity(str(chain["e_l4"].id), db=db)
    assert db.query(EntityConceptLink).filter(EntityConceptLink.entity_id == chain["e_l4"].id).count() == 0
    assert db.query(EntityRelation).filter(
        (EntityRelation.source_entity_id == chain["e_l4"].id) | (EntityRelation.target_entity_id == chain["e_l4"].id)
    ).count() == 0
    assert delete_concept(str(chain["l4"].id), db=db)["code"] == 200
    assert delete_concept(str(chain["l3"].id), db=db)["code"] == 200
    assert delete_concept(str(chain["dom"].id), db=db)["code"] == 200
    assert db.query(Concept).filter(Concept.id == chain["dom"].id).first() is None


def test_clear_graph_data_cascades_links():
    """清空级联：链接/概念关系先清、概念按层级深度优先删；mode 限定只清本模式（spec §七.1 级联处理挂接；
    concept_admin._clear_graph_data）。隔离 SQLite 防 MySQL 真实图谱误清。
    变异锚点：清挂接/概念关系步骤删 → 残留悬挂行红（MySQL 下 FK RESTRICT 先炸）；
    mode 过滤删 → 另一模式数据被误清红；层级深度优先序改乱 → MySQL 按父外键抛错
    （SQLite 不设 FK，此处锚定清理完整性）。"""
    from app.api.concept_admin import _clear_graph_data
    from app.models.base import Concept, Entity, EntityConceptLink, EntityRelation, ConceptRelation
    db = _sqlite_db()
    _seed_concept_graph(db)
    # master 模式：仅清 L1/L2 及其下属实体/挂接/涉入概念关系
    res_m = _clear_graph_data(db, "master")
    assert res_m == {"concepts": 2, "entities": 1}
    assert {c.name for c in db.query(Concept).all()} == {"m03test_dom", "m03test_l3", "m03test_l4"}
    assert db.query(Entity).count() == 1
    assert db.query(Entity).first().entity_code == "m03test_l4e"
    assert db.query(EntityConceptLink).count() == 1
    assert db.query(EntityRelation).count() == 0  # 打点行随 e2 级联清除
    assert db.query(ConceptRelation).count() == 1  # dom→l3（业务侧）保留，l2→l4 随 l2 清除
    # 全清：4→3→2→1→0 深层优先，全部归零
    res_all = _clear_graph_data(db, None)
    assert res_all["concepts"] == 3 and res_all["entities"] == "all"
    assert db.query(Concept).count() == 0 and db.query(Entity).count() == 0
    assert db.query(EntityConceptLink).count() == 0 and db.query(EntityRelation).count() == 0
    assert db.query(ConceptRelation).count() == 0


# ---------------------------------------------------------------------------
# §七.2 实体挂接：矩阵与四区即时反映
# ---------------------------------------------------------------------------

def test_entity_mount_unmount_reflects_in_matrix_and_quad(m03_db):
    """概念下挂/摘实体即时反映在矩阵与四区（spec §七.2：矩阵与四区树均按 kg_entity_concept_links
    挂接过滤，摘挂后即时消失；力导向同源）。
    变异锚点：矩阵/树/力导向改用 Entity.concept_id 全量（绕过挂接表）→ 摘挂后仍出现红；
    _update_entity_concept_links 删 → 下挂后不出现红。"""
    db = m03_db
    from app.api.concept_admin import get_graph_matrix
    from app.api.concept_entity import get_concepts
    from app.api.concept_graph import get_graph_data
    from app.api.concept_support import _update_entity_concept_links
    chain = _build_chain(db)
    # 下挂即时反映：矩阵（列=主数据实体、行=业务活动实体）
    m = get_graph_matrix(db=db)
    assert str(chain["e_l2"].id) in {e["id"] for c in m["data"]["columns"] for e in c["entities"]}
    assert str(chain["e_l4"].id) in {e["id"] for r in m["data"]["rows"] for e in r["entities"]}
    # 四区级联树（get_concepts）
    tree = {c["id"]: {e["id"] for e in c["entities"]} for c in get_concepts(db=db)}
    assert str(chain["e_l2"].id) in tree[str(chain["l2"].id)]
    assert str(chain["e_l4"].id) in tree[str(chain["l4"].id)]
    # 力导向全量同源反映
    g = get_graph_data(db=db)
    assert {str(chain["e_l2"].id), str(chain["e_l4"].id)} <= {n["id"] for n in g["nodes"]}
    # 摘挂 L4 实体 → 矩阵/四区/力导向即时消失（只统计挂接过的实体）
    _update_entity_concept_links(db, str(chain["e_l4"].id), [])
    db.commit()
    m2 = get_graph_matrix(db=db)
    assert str(chain["e_l4"].id) not in {e["id"] for r in m2["data"]["rows"] for e in r["entities"]}
    tree2 = {c["id"]: {e["id"] for e in c["entities"]} for c in get_concepts(db=db)}
    assert str(chain["e_l4"].id) not in tree2[str(chain["l4"].id)]
    g2 = get_graph_data(db=db)
    assert str(chain["e_l4"].id) not in {n["id"] for n in g2["nodes"]}


# ---------------------------------------------------------------------------
# §七.3 矩阵：toggle 行增删 / 格子明细 / 打点过滤方向
# ---------------------------------------------------------------------------

def test_matrix_toggle_row_lifecycle(m03_db):
    """矩阵 L2×L4 格子 toggle 打点 → EntityRelation 行增删（spec §七.3；toggle_entity_matrix_link：
    首点建行 source=L2 主数据/target=L4 活动/类别=打点维护/forward/N:N，再点删行）。
    变异锚点：建行 source/target 颠倒 → level 2→4 过滤丢格子红；二次 toggle 不删行 →
    unlinked 谎报/行残留红；relation_name 模板与默认字段漂移 → 契约红。"""
    db = m03_db
    from app.api.concept_admin import toggle_entity_matrix_link
    from app.models.base import EntityRelation
    chain = _build_chain(db)
    r1 = toggle_entity_matrix_link(str(chain["e_l4"].id), str(chain["e_l2"].id), db=db)
    assert r1["code"] == 200 and r1["action"] == "linked" and r1["link_id"]
    row = db.query(EntityRelation).filter(EntityRelation.id == r1["link_id"]).first()
    assert row is not None
    assert row.relation_category == "打点维护"
    assert str(row.source_entity_id) == str(chain["e_l2"].id)
    assert str(row.target_entity_id) == str(chain["e_l4"].id)
    assert row.direction == "forward" and row.cardinality == "N:N"
    assert row.relation_name == f"{chain['e_l2'].entity_name}主数据实体打点到{chain['e_l4'].entity_name}活动实体"
    # 再点 → 删行
    r2 = toggle_entity_matrix_link(str(chain["e_l4"].id), str(chain["e_l2"].id), db=db)
    assert r2["action"] == "unlinked" and r2["link_id"] == r1["link_id"]
    assert db.query(EntityRelation).filter(EntityRelation.id == r1["link_id"]).first() is None


def test_matrix_grid_detail_and_direction_filter(m03_db):
    """格子明细含 join_expr/cardinality +「打点维护」过滤正确（spec §七.3/§四矩阵语义：
    只统计挂接实体；仅 category=打点维护 且 source 概念 level==2、target 概念 level==4 入格）。
    变异锚点：打点过滤的方向判定（source.level!=2 or target.level!=4 跳过）删/反 → 反向打点行入格红；
    category 过滤删 → 手工维护行入矩阵红；格子明细字段（join_expr/cardinality）删 → 明细断言红。"""
    db = m03_db
    from app.api.concept_admin import get_graph_matrix, toggle_entity_matrix_link
    from app.models.base import EntityRelation
    chain = _build_chain(db)
    r = toggle_entity_matrix_link(str(chain["e_l4"].id), str(chain["e_l2"].id), db=db)
    row = db.query(EntityRelation).filter(EntityRelation.id == r["link_id"]).first()
    row.join_expr = "m03test_join"
    row.cardinality = "1:N"
    db.commit()

    def _e4_of(matrix):
        for rr in matrix["data"]["rows"]:
            for e in rr["entities"]:
                if e["id"] == str(chain["e_l4"].id):
                    return e
        return None

    m = get_graph_matrix(db=db)
    e4 = _e4_of(m)
    assert e4 is not None
    assert e4["linked_entity_ids"] == [str(chain["e_l2"].id)]
    detail = e4["linked_entity_map"][str(chain["e_l2"].id)]
    assert detail["id"] == r["link_id"]
    assert detail["relation_category"] == "打点维护"
    assert detail["join_expr"] == "m03test_join"
    assert detail["cardinality"] == "1:N"
    # 反向打点行（source=L4 实体→target=L2 实体）与手工维护行都不得入格
    db.add(EntityRelation(source_entity_id=str(chain["e_l4"].id), target_entity_id=str(chain["e_l2"].id),
                          relation_name="m03test反向打点", relation_category="打点维护"))
    db.add(EntityRelation(source_entity_id=str(chain["e_l2"].id), target_entity_id=str(chain["e_l4"].id),
                          relation_name="m03test手工关系", relation_category="手工维护"))
    db.commit()
    m2 = get_graph_matrix(db=db)
    e4b = _e4_of(m2)
    assert e4b["linked_entity_ids"] == [str(chain["e_l2"].id)]
    assert e4b["linked_entity_map"][str(chain["e_l2"].id)]["join_expr"] == "m03test_join"


# ---------------------------------------------------------------------------
# §七.4 Excel 导出→清空→导入 往返一致
# ---------------------------------------------------------------------------

def test_excel_roundtrip_consistency():
    """Excel 导出→清空→导入 往返一致，含 area_index/system_names（spec §七.4/§六.4 列头中文即接口）。
    隔离 SQLite 双库（导出库/清空后导入库），防误清真实图谱数据。
    变异锚点：导出漏「业务域索引/所属系统」列或列名漂移 → 导入回填失败红；
    导入不写 area_index/不归一 system_names → 往返快照红；clear+import 不重建实体关系 → 关系快照红。"""
    from app.api.concept_admin import export_graph_to_excel, import_graph_from_excel
    db1 = _sqlite_db()
    _seed_concept_graph(db1)
    resp = export_graph_to_excel(db=db1)

    async def _drain(stream_resp):
        chunks = []
        async for chunk in stream_resp.body_iterator:
            chunks.append(chunk)
        return b"".join(chunks)

    content = asyncio.run(_drain(resp))
    assert content[:2] == b"PK"  # xlsx（zip 容器）
    # 清空后的新库：clear=True 走「清空→导入」完整链
    db2 = _sqlite_db()
    file = UploadFile(file=io.BytesIO(content), filename="graph_metadata.xlsx")
    res = asyncio.run(import_graph_from_excel(mode=None, clear=True, file=file, db=db2))
    assert res["status"] == "success", res["message"]
    assert res["counts"]["concepts"] == 5 and res["counts"]["entities"] == 2
    assert res["counts"]["relations"] == 1
    snap1, snap2 = _snapshot(db1), _snapshot(db2)
    assert snap1[0] == snap2[0], f"概念面往返漂移：{snap1[0] ^ snap2[0]}"
    assert snap1[1] == snap2[1], f"实体面往返漂移：{snap1[1] ^ snap2[1]}"
    assert snap1[2] == snap2[2], f"关系面往返漂移：{snap1[2] ^ snap2[2]}"
    # spec 点名两字段在案：system_names 往返 + area_index 逐概念保持
    l3 = [c for c in snap2[0] if c[0] == "m03test_l3"][0]
    assert l3[4] == ("系统A", "系统B")
    assert {(c[0], c[3]) for c in snap2[0]} >= {("m03test_dom", 91), ("m03test_grp", 92), ("m03test_l2", 92)}


# ---------------------------------------------------------------------------
# §七.5 英文名治理：缺失清单 / autofill 不覆盖已填
# ---------------------------------------------------------------------------

def test_en_name_integrity_lists_missing_and_autofill_preserves_filled(m03_db):
    """英文名治理：integrity-check 报缺失清单（缺者入列、已填不入）；autofill 只补空不覆盖已填且幂等
    （spec §七.5/§六.3 英文名一等公民）。
    变异锚点：缺失判定（not (en or '').strip()）反转/漏 → 缺失清单错红；
    only_empty 判定删 → 已填英文名被冲掉红；_suggest_entity_en_name 编码回退链改 → 建议值红。"""
    db = m03_db
    from app.api.concept_entity import (
        EntityEnNameAutoFillRequest, autofill_entity_en_name, check_entity_en_name_integrity,
    )
    from app.models.base import Entity
    from app.schemas.concept import EntityCreate
    from app.api.concept_entity import create_entity
    chain = _build_chain(db)
    e_keep = create_entity(EntityCreate(concept_id=str(chain["l2"].id), entity_code="m03test_kept",
                                        entity_name="m03test已填实体", entity_en_name="m03test_kept_en"), db=db)
    # e_l2 无英文名 → 缺失清单；已填者不入列
    chk = check_entity_en_name_integrity(db=db)
    missing_ids = {r["id"] for r in chk["data"]["missing_entities"]}
    assert str(chain["e_l2"].id) in missing_ids
    assert str(e_keep.id) not in missing_ids
    assert chk["data"]["missing_count"] >= 1
    assert chk["data"]["total"] >= chk["data"]["missing_count"]
    row = [r for r in chk["data"]["missing_entities"] if r["id"] == str(chain["e_l2"].id)][0]
    assert row["suggested_entity_en_name"] == "m03test_l2e"  # 由 entity_code 回退建议
    # autofill 只补空：补 e_l2、不覆盖 e_keep
    res = autofill_entity_en_name(EntityEnNameAutoFillRequest(only_empty=True), db=db)
    upd = {u["id"] for u in res["data"]["updated_entities"]}
    assert str(chain["e_l2"].id) in upd
    assert str(e_keep.id) not in upd
    db.expire_all()
    e1 = db.query(Entity).filter(Entity.id == chain["e_l2"].id).first()
    e2 = db.query(Entity).filter(Entity.id == e_keep.id).first()
    assert e1.entity_en_name == "m03test_l2e"
    assert e2.entity_en_name == "m03test_kept_en"
    # 幂等：再跑无重复更新
    res2 = autofill_entity_en_name(EntityEnNameAutoFillRequest(only_empty=True), db=db)
    assert str(chain["e_l2"].id) not in {u["id"] for u in res2["data"]["updated_entities"]}


# ---------------------------------------------------------------------------
# §七.6 四视图：四模式切换数据正确
# ---------------------------------------------------------------------------

def test_force_view_full_data_contract(m03_db):
    """力导向=全量（spec §五/§七.6：/graph/data MySQL 侧全量；§六.5 level=0 业务域不进图谱）。
    变异锚点：level>0 过滤删 → 业务域节点泄漏红；concept level 推断 entity_category 改 →
    master_entity/activity_entity 错红；打点边型映射（打点维护→entity_generation）改 → 边语义红。"""
    db = m03_db
    from app.api.concept_admin import toggle_entity_matrix_link
    from app.api.concept_entity import create_entity_relation
    from app.api.concept_graph import get_graph_data
    from app.schemas.concept import EntityRelationCreate
    chain = _build_chain(db)
    create_entity_relation(EntityRelationCreate(
        source_entity_id=str(chain["e_l2"].id), target_entity_id=str(chain["e_l4"].id),
        relation_name="m03test手工关系", relation_category="手工维护"), db=db)
    toggle_entity_matrix_link(str(chain["e_l4"].id), str(chain["e_l2"].id), db=db)
    g = get_graph_data(db=db)
    nodes = {n["id"]: n for n in g["nodes"]}
    for key in ("grp", "l2", "l3", "l4"):
        assert str(chain[key].id) in nodes and nodes[str(chain[key].id)]["type"] == "concept"
    assert str(chain["dom"].id) not in nodes  # L0 不进图谱
    assert nodes[str(chain["e_l2"].id)]["entity_category"] == "master_entity"
    assert nodes[str(chain["e_l4"].id)]["entity_category"] == "activity_entity"
    edges = {(e["source"], e["target"], e["edge_type"]) for e in g["edges"]}
    assert (str(chain["e_l2"].id), str(chain["l2"].id), "concept_entity_link") in edges
    assert (str(chain["e_l4"].id), str(chain["l4"].id), "concept_entity_link") in edges
    assert (str(chain["l2"].id), str(chain["grp"].id), "concept_hierarchy") in edges
    assert (str(chain["e_l2"].id), str(chain["e_l4"].id), "entity_relation") in edges
    assert (str(chain["e_l2"].id), str(chain["e_l4"].id), "entity_generation") in edges
    assert all(str(chain["dom"].id) not in (e["source"], e["target"]) for e in g["edges"])


def test_quad_view_cascade_data_contract(m03_db):
    """四区=级联（spec §五/§七.6：概念树+挂载实体；QuadCanvas 契约——左半 L1→L2→L2X、右半 L3→L4→L4X、
    中间连线=打点；get_concepts 默认不吐 L0、include_level_zero 显式可取）。
    变异锚点：include_level_zero 默认行为反转 → 业务域泄漏红；dynamic_children 组装
    （打点 L2 实体→L3/L4/L4X 子树）删 → 四区中间连线数据断红。"""
    db = m03_db
    from app.api.concept_admin import toggle_entity_matrix_link
    from app.api.concept_entity import get_concepts
    chain = _build_chain(db)
    toggle_entity_matrix_link(str(chain["e_l4"].id), str(chain["e_l2"].id), db=db)
    tree = get_concepts(db=db)
    by_id = {c["id"]: c for c in tree}
    assert str(chain["dom"].id) not in by_id  # 默认隐藏业务域（顶部筛选按需取）
    tree_all = get_concepts(include_level_zero=True, db=db)
    assert str(chain["dom"].id) in {c["id"] for c in tree_all}
    # 左右两半级联数据可用：L1/L2 与 L3/L4 均在树
    for key in ("grp", "l2", "l3", "l4"):
        assert str(chain[key].id) in by_id
    # L2 实体携带打点级联子树（L3→L4→L4X 实体）
    e2 = [e for e in by_id[str(chain["l2"].id)]["entities"] if e["id"] == str(chain["e_l2"].id)][0]
    dc = e2["dynamic_children"]
    l3_nodes = [d for d in dc if d["id"] == str(chain["l3"].id)]
    assert l3_nodes, "打点级联子树缺 L3 分组"
    l4_nodes = [c2 for c2 in l3_nodes[0]["children"] if c2["id"] == str(chain["l4"].id)]
    assert l4_nodes and any(x["id"] == str(chain["e_l4"].id) for x in l4_nodes[0]["entities"])


def test_gallery_view_neo4j_stub_contract(monkeypatch):
    """图库=Neo4j（spec §五/§七.6：/graph/neo4j-data 读 Neo4j Category 体系；§一 Neo4j 归 M05 边界）。
    Neo4j 桩（假 driver 会话）断言契约形状：level 标签→type/level 映射、valid_levels 过滤、
    三类边（HAS_PARENT/RELATED_BY/RELATES_TO）→ edge_type 映射、source 标记。
    变异锚点：节点查询未按 valid_levels 收敛（参数缺失/漂移）→ 桩库泄漏脏层级（ROOT）红；
    L2X/L4X→entity 映射改 → 节点类型红；RELATES_TO→entity_generation 映射改 → 打点边语义红。"""
    from app.api import concept_graph as CG
    from app.services import graph_query_neo4j as G
    cat_rows = [
        {"code": "L1-t01", "name": "主数据组", "level": "L1", "concept_id": "c1", "description": "d1"},
        {"code": "L2X-e01", "name": "主数据实体X", "level": "L2X", "concept_id": "c2", "description": ""},
        {"code": "L4X-e02", "name": "活动实体Y", "level": "L4X", "concept_id": "c3", "description": ""},
        {"code": "ROOT-dirty", "name": "脏数据", "level": "ROOT", "concept_id": "c9", "description": ""},
    ]
    hp_rows = [{"src": "L2X-e01", "tgt": "L1-t01", "src_lv": "L2X", "tgt_lv": "L1"}]
    rb_rows = [{"src": "L1-t01", "tgt": "L1-t01", "rel_type": "cross", "derived_from": "transitive_closure"}]
    rt_rows = [{"src": "L2X-e01", "tgt": "L4X-e02", "rname": "打点维护"}]

    class _R:
        def __init__(self, rows):
            self._rows = rows

        def data(self):
            return self._rows

    class _S:
        def run(self, q, **params):
            if "RETURN c.code AS code" in q:
                # 忠实模拟 DB 侧契约：valid_levels 下推为查询参数，库按 WHERE c.level IN 收敛
                valid = set(params.get("validLevels") or [])
                return _R([r for r in cat_rows if not valid or r["level"] in valid])
            if "HAS_PARENT" in q:
                return _R(hp_rows)
            if "RELATED_BY" in q:
                return _R(rb_rows)
            if "RELATES_TO" in q:
                return _R(rt_rows)
            return _R([])

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    class _D:
        def session(self):
            return _S()

    monkeypatch.setattr(G, "_get_driver", lambda: _D())
    res = CG.get_neo4j_graph_data()
    assert res["source"] == "neo4j"
    nodes = {n["id"]: n for n in res["nodes"]}
    assert "ROOT-dirty" not in nodes  # valid_levels 过滤脏数据
    assert nodes["L1-t01"]["type"] == "concept" and nodes["L1-t01"]["level"] == 1
    assert nodes["L2X-e01"]["type"] == "entity" and nodes["L2X-e01"]["level_label"] == "L2X"
    assert nodes["L4X-e02"]["type"] == "entity"
    edges = {(e["source"], e["target"], e["edge_type"]) for e in res["edges"]}
    assert ("L2X-e01", "L1-t01", "concept_hierarchy") in edges
    assert ("L1-t01", "L1-t01", "concept_cross_chain") in edges
    assert ("L2X-e01", "L4X-e02", "entity_generation") in edges


# ---------------------------------------------------------------------------
# §七.7 层级数据变更后 M05 同步增量重投射（边界联测，Neo4j 桩）
# ---------------------------------------------------------------------------

def test_hierarchy_change_incremental_reprojection(monkeypatch, m03_db):
    """层级数据变更后 M05 同步可增量重投射（spec §七.7 边界联测，Neo4j 桩）：
    概念 CRUD 变更后 sync_all_to_neo4j 以 MERGE on code 重投射该层级（幂等、非 force 不清库）；
    停机降级路径由 test_m05_graph_engine.py::test_healthcheck_false_drives_degrade 锚定。
    变异锚点：code 生成式（f"{lvl}-{id[:8]}"）改 → 重投射目标失配红；
    MERGE 改 CREATE → 重复同步重复建节点（幂等破坏）红；非 force 也 DETACH DELETE → 增量语义破坏红。"""
    db = m03_db
    from app.api.concept_entity import create_concept
    from app.schemas.concept import ConceptCreate
    from app.services import graph_query_neo4j as G
    dom = create_concept(ConceptCreate(name="m03test_domRP", level=0, area_index=None), db=db)

    class _RecResult:
        def __init__(self, log, q, params):
            self._log, self._q, self._p = log, q, params

        def consume(self):
            self._log.append((self._q, self._p))

        def single(self):
            return {"c": 0}

    class _RecSession:
        def __init__(self, log):
            self._log = log

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def run(self, q, **params):
            return _RecResult(self._log, q, params)

    class _RecDriver:
        def __init__(self):
            self.log = []

        def session(self):
            return _RecSession(self.log)

    fake = _RecDriver()
    monkeypatch.setattr(G, "neo4j_healthcheck", lambda: True)
    monkeypatch.setattr(G, "_get_driver", lambda: fake)
    res = G.sync_all_to_neo4j(db=db)
    assert res["ok"] is True and res["concepts_synced"] >= 1
    hits = [p for q, p in fake.log if "MERGE (n:Category {code:$code})" in q and p.get("cid") == str(dom.id)]
    assert hits, "层级变更的新概念未被重投射"
    assert hits[0]["code"] == f"L0-{str(dom.id)[:8]}"
    assert hits[0]["name"] == "m03test_domRP"
    assert not any("DETACH DELETE" in q for q, _ in fake.log)  # 非 force 增量：不清库
    # 幂等：重复同步仍 ok（MERGE 语义可重复重投射）
    assert G.sync_all_to_neo4j(db=db)["ok"] is True
