# -*- coding: utf-8 -*-
"""M04 单测：三组层级校验/master_activity 打点归一与实体对唯一/Excel 往返/source_mode 持久化/
清空重链/血缘占位登记态（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M04 spec §八验收标准锚定现有实现）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------------------------
# 验收标准映射（M04 spec §八，2026-09-08 测试补全）：
# §八.1 三组关系 CRUD 层级校验全绿（非法层级 400） → test_group_level_matrix +
#       test_group_same_entity_rejected（均本文件既有）；
#       master_activity 创建/编辑/导入三路强制打点+实体对唯一 →
#       test_master_activity_category_forced_three_paths +
#       test_master_activity_pair_uniqueness_create_edit_import（本次补，本文件）
# §八.2 Excel 导出→导入往返一致（复用同一套校验） → test_relation_excel_roundtrip_consistency +
#       test_import_excel_reuses_group_validation（本次补，本文件；隔离 SQLite 双库防误写真实
#       图谱数据，范式承 test_m03_concept.py::test_excel_roundtrip_consistency）
# §八.3 source_mode 三模式切换保存后就地生效 → test_source_mode_update_persists_three_modes
#       （本次补，本文件：后端锚定 EntityUpdate.source_mode 三值经 update_entity 持久化+读回）；
#       树不刷新不折叠/映射跳转 Tab 正确+实体过滤生效 → 前端 store 交互链路
#       （ModelTreeManager.tsx L484-548），pytest 不可达，e2e 域覆盖（批次末总验收），如实披露
# §八.4 跨页联动：关系高亮/建模定位/映射跳转三条链路 e2e 冒烟 → 前端链路，e2e 域覆盖；
#       已核 backend/tests 现无三条链路的专项证据（relationHighlight/modelingInitialKey/映射跳转
#       零命中），不装饰性引用，待批次末总验收 e2e 补齐，如实披露
# §八.5 清空重置 Popconfirm 后清空并重链/清理 modeling/initdata/rules 引用 →
#       test_clear_reset_relinks_modeling_initdata_rules（本次补，本文件：三表重链桥接锚定）+
#       test_m03_concept.py::test_clear_graph_data_cascades_links（清空级联清理，既有他文件）
# §八.6 血缘页呈现占位文案（禁改清单件，按登记态断言） →
#       test_lineage_page_placeholder_state（本次补，本文件）
# ---------------------------------------------------------------------------

import asyncio  # noqa: E402
import io  # noqa: E402
import uuid  # noqa: E402

import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from fastapi import HTTPException, UploadFile  # noqa: E402

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


def _sqlite_db():
    """独立内存 SQLite（M04 相关八表），供关系 CRUD/Excel 往返/重链测试——防误写真实图谱数据。"""
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


def _seed_pair(db):
    """种子隔离库：2 个 L2 主数据实体 + 2 个 L4 活动实体（独立概念，层级经 concept_map 推断）。"""
    from app.models.base import Concept, Entity
    c2a = Concept(name="m04t_l2a", level=2, area_index=91)
    c2b = Concept(name="m04t_l2b", level=2, area_index=92)
    c4a = Concept(name="m04t_l4a", level=4, area_index=91)
    c4b = Concept(name="m04t_l4b", level=4, area_index=92)
    db.add_all([c2a, c2b, c4a, c4b])
    db.flush()
    m1 = Entity(concept_id=c2a.id, entity_code="m04t_m1", entity_name="m04t主数据一",
                entity_en_name="m04t_m1", properties_schema=[], is_main_table=True)
    m2 = Entity(concept_id=c2b.id, entity_code="m04t_m2", entity_name="m04t主数据二",
                entity_en_name="m04t_m2", properties_schema=[], is_main_table=True)
    a1 = Entity(concept_id=c4a.id, entity_code="m04t_a1", entity_name="m04t活动一",
                entity_en_name="m04t_a1", properties_schema=[], is_main_table=False)
    a2 = Entity(concept_id=c4b.id, entity_code="m04t_a2", entity_name="m04t活动二",
                entity_en_name="m04t_a2", properties_schema=[], is_main_table=False)
    db.add_all([m1, m2, a1, a2])
    db.commit()
    return {"m1": m1, "m2": m2, "a1": a1, "a2": a2}


def _excel_bytes(rows, sheet="实体关系清单"):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name=sheet, index=False)
    buf.seek(0)
    return buf


def _import_rows(db, rows):
    """行字典 → 实体关系清单 xlsx → 走真实导入端点（三轨M3/6 起为同步 def——直呼）。"""
    from app.api.entity_relation_manage import import_entity_relations_excel
    buf = _excel_bytes(rows)
    return import_entity_relations_excel(
        file=UploadFile(file=buf, filename="m04t.xlsx"), db=db)


def _drain_stream(resp):
    """抽干 StreamingResponse body_iterator（导出端点同步签名+异步体）。"""
    async def _collect():
        chunks = []
        async for chunk in resp.body_iterator:
            chunks.append(chunk)
        return b"".join(chunks)
    return asyncio.run(_collect())


def _rel_snapshot(db):
    """关系面快照（类别/名称/实体对编码/方向/基数/关联说明，忽略 uuid）。"""
    from app.models.base import Entity, EntityRelation
    emap = {str(e.id): e for e in db.query(Entity).all()}
    return {
        (r.relation_category, r.relation_name,
         emap[str(r.source_entity_id)].entity_code, emap[str(r.target_entity_id)].entity_code,
         r.direction, r.cardinality, r.join_expr)
        for r in db.query(EntityRelation).all()
    }


# ---------------------------------------------------------------------------
# 任务 1：三组层级校验（§八.1 层级面，既有）
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
    uid = str(uuid.uuid4())
    assert _norm_uuid_str(uid, "id") == uid
    assert _clean_text("  a  ") == "a"
    assert _clean_text(None) is None


# ---------------------------------------------------------------------------
# §八.1 master_activity 创建/编辑/导入三路强制打点 + 实体对唯一
# ---------------------------------------------------------------------------

def test_master_activity_category_forced_three_paths():
    """master_activity 创建/编辑/导入三路都强制归一「打点维护」（spec §八.1/§三/§七.2 单一来源：
    create/edit/import 三处归一一致，与资产矩阵打点同语义）。
    变异锚点：三处归一（create L434-436/edit L479-481/import L616-618）任一删/改 →
    该路关系类别漂移为入参值（如「手工维护」）红。"""
    from app.api.entity_relation_manage import (
        RelationManagerUpsert, create_entity_relation_item, update_entity_relation_item,
    )
    from app.models.base import EntityRelation
    db = _sqlite_db()
    ent = _seed_pair(db)

    # 路 1 创建：入参类别「手工维护」→ 入库强制「打点维护」
    r1 = create_entity_relation_item(RelationManagerUpsert(
        relation_group="master_activity", source_entity_id=str(ent["m1"].id),
        target_entity_id=str(ent["a1"].id), relation_category="手工维护"), db=db)
    assert r1["code"] == 200
    row = db.query(EntityRelation).filter(EntityRelation.id == r1["data"]["id"]).first()
    assert row.relation_category == "打点维护"

    # 路 2 编辑：改成「手工维护」→ 仍归一「打点维护」
    update_entity_relation_item(r1["data"]["id"], RelationManagerUpsert(
        relation_group="master_activity", source_entity_id=str(ent["m1"].id),
        target_entity_id=str(ent["a1"].id), relation_category="手工维护",
        relation_name="m04t改名"), db=db)
    db.expire_all()
    row = db.query(EntityRelation).filter(EntityRelation.id == r1["data"]["id"]).first()
    assert row.relation_category == "打点维护"
    assert row.relation_name == "m04t改名"

    # 路 3 导入：Excel 行类别「手工维护」→ 入库强制「打点维护」
    res = _import_rows(db, [{
        "关系分组": "主数据-业务活动", "关系名称": "m04t导入打点",
        "源实体编码": "m04t_m2", "目标实体编码": "m04t_a2", "关系类别": "手工维护",
    }])
    assert res["code"] == 200 and res["data"]["created_count"] == 1, res
    row = db.query(EntityRelation).filter(EntityRelation.relation_name == "m04t导入打点").first()
    assert row is not None and row.relation_category == "打点维护"


def test_master_activity_pair_uniqueness_create_edit_import():
    """master_activity 实体对唯一（一对实体一条打点关系）：创建重复 400 中文提示/编辑撞对 400/
    导入重复行就地更新不重复建行；master_master 按实体对+关系名+类别去重（spec §八.1/§三）。
    变异锚点：唯一性查询（create L440-456/edit L485-503/import L620-640）删/漏自排除 →
    重复行入库红；导入不就地更新 → 同对双行红。"""
    from app.api.entity_relation_manage import (
        RelationManagerUpsert, create_entity_relation_item, update_entity_relation_item,
    )
    from app.models.base import EntityRelation
    db = _sqlite_db()
    ent = _seed_pair(db)

    def up(m, a, **kw):
        return RelationManagerUpsert(
            relation_group="master_activity", source_entity_id=str(ent[m].id),
            target_entity_id=str(ent[a].id), **kw)

    # 创建：同实体对第二次 → 400 中文提示
    create_entity_relation_item(up("m1", "a1"), db=db)
    with pytest.raises(HTTPException) as ei:
        create_entity_relation_item(up("m1", "a1"), db=db)
    assert ei.value.status_code == 400
    assert ei.value.detail == "该主数据-业务活动关系已存在，请直接编辑"

    # 编辑：把 m2→a2 改撞 m1→a1 → 400（唯一性排除自身后仍命中）
    r2 = create_entity_relation_item(up("m2", "a2"), db=db)
    with pytest.raises(HTTPException) as ei:
        update_entity_relation_item(r2["data"]["id"], up("m1", "a1"), db=db)
    assert ei.value.status_code == 400

    # 导入：同实体对两行 → created 1 + updated 1，库里该对仍一行
    res = _import_rows(db, [
        {"关系分组": "主数据-业务活动", "关系名称": "m04t_upsert",
         "源实体编码": "m04t_m1", "目标实体编码": "m04t_a2"},
        {"关系分组": "主数据-业务活动", "关系名称": "m04t_upsert",
         "源实体编码": "m04t_m1", "目标实体编码": "m04t_a2"},
    ])
    assert res["code"] == 200, res
    assert res["data"]["created_count"] == 1 and res["data"]["updated_count"] == 1, res
    pair_rows = db.query(EntityRelation).filter(
        EntityRelation.source_entity_id == str(ent["m1"].id),
        EntityRelation.target_entity_id == str(ent["a2"].id)).all()
    assert len(pair_rows) == 1

    # 对照组 master_master：实体对+关系名+类别去重——同名 400、改名可建
    def mm(name):
        return RelationManagerUpsert(
            relation_group="master_master", source_entity_id=str(ent["m1"].id),
            target_entity_id=str(ent["m2"].id), relation_name=name)

    create_entity_relation_item(mm("n1"), db=db)
    with pytest.raises(HTTPException) as ei:
        create_entity_relation_item(mm("n1"), db=db)
    assert ei.value.status_code == 400
    assert create_entity_relation_item(mm("n2"), db=db)["code"] == 200


# ---------------------------------------------------------------------------
# §八.2 Excel 导出→导入往返一致（复用同一套校验）
# ---------------------------------------------------------------------------

def test_relation_excel_roundtrip_consistency():
    """Excel 导出→（新库）导入 往返一致：三组各一条，类别/名称/实体对/方向/基数/关联说明全量对齐，
    关系名缺省 f"{源}关联{目标}" 随行保留（spec §八.2/§三——导入循环内复用组校验与唯一性判断）。
    隔离 SQLite 双库（导出库/导入库），防误写真实图谱数据。
    变异锚点：导出列漂移（中文列头=外部契约）→ 导入解析不出实体/组红；
    导入绕过组校验/唯一性 → 非法或重复行混入红；master_activity 打点归一缺失 → 类别漂移红。"""
    from app.api.entity_relation_manage import (
        RelationManagerUpsert, create_entity_relation_item, export_entity_relations_excel,
        import_entity_relations_excel,
    )
    db1 = _sqlite_db()
    ent1 = _seed_pair(db1)
    create_entity_relation_item(RelationManagerUpsert(
        relation_group="master_master", source_entity_id=str(ent1["m1"].id),
        target_entity_id=str(ent1["m2"].id)), db=db1)
    create_entity_relation_item(RelationManagerUpsert(
        relation_group="master_activity", source_entity_id=str(ent1["m1"].id),
        target_entity_id=str(ent1["a1"].id)), db=db1)
    create_entity_relation_item(RelationManagerUpsert(
        relation_group="activity_activity", source_entity_id=str(ent1["a1"].id),
        target_entity_id=str(ent1["a2"].id), relation_name="m04t活动串联"), db=db1)

    content = _drain_stream(export_entity_relations_excel(db=db1))
    assert content[:2] == b"PK"  # xlsx（zip 容器）

    # 全新库（同种子）导入：三行全建、零 skip
    db2 = _sqlite_db()
    _seed_pair(db2)
    res = import_entity_relations_excel(
        file=UploadFile(file=io.BytesIO(content), filename="entity_relations.xlsx"), db=db2)
    assert res["code"] == 200, res
    assert res["data"]["created_count"] == 3, res
    assert res["data"]["skipped_rows"] == [], res

    snap1, snap2 = _rel_snapshot(db1), _rel_snapshot(db2)
    assert snap1 == snap2, f"关系面往返漂移：{snap1 ^ snap2}"
    # master_activity 打点语义随往返保持；关系名缺省式随行保留
    ma = [t for t in snap2 if t[0] == "打点维护"]
    assert len(ma) == 1 and ma[0][1] == "m04t主数据一关联m04t活动一"
    assert any(t[1] == "m04t主数据一关联m04t主数据二" for t in snap2)


def test_import_excel_reuses_group_validation():
    """导入复用同一套校验：层级非法行/未知组行不入库且记入 skipped_rows，合法行正常入库
    （spec §八.2/§三——导入循环内 _validate_group_entities/L614 校验+L641-642 skip 记录）。
    变异锚点：导入循环删 _validate_group_entities 调用 → 非法层级行入库红；
    skip 记录删 → 非法行静默丢失红。"""
    from app.models.base import EntityRelation
    db = _sqlite_db()
    _seed_pair(db)
    res = _import_rows(db, [
        {"关系分组": "主数据-业务活动", "关系名称": "m04t_ok",
         "源实体编码": "m04t_m1", "目标实体编码": "m04t_a1"},
        # L4→L4 冒充「主数据-主数据」→ 层级校验拒绝
        {"关系分组": "主数据-主数据", "关系名称": "m04t_bad",
         "源实体编码": "m04t_a1", "目标实体编码": "m04t_a2"},
        # 未知分组标签 → Unsupported relation_group 拒绝
        {"关系分组": "未知分组", "关系名称": "m04t_unk",
         "源实体编码": "m04t_m1", "目标实体编码": "m04t_m2"},
    ])
    assert res["code"] == 200, res
    assert res["data"]["created_count"] == 1, res
    assert len(res["data"]["skipped_rows"]) == 2, res
    assert {r.relation_name for r in db.query(EntityRelation).all()} == {"m04t_ok"}


# ---------------------------------------------------------------------------
# §八.3 source_mode 三模式：保存后就地生效（后端锚点）
# ---------------------------------------------------------------------------

def test_source_mode_update_persists_three_modes():
    """source_mode 三模式（physical_table/sql_integration/api_integration）经 update_entity
    保存后就地生效：值持久化到实体行且随行读回，三模式配置面字段（integration_sql/doris_catalog/
    data_source_id）同路可写（spec §八.3/§四——前端走 entityApi.updateEntity(id, {source_mode})）。
    变异锚点：EntityUpdate.source_mode 字段删/update_entity 漏 setattr → 模式保存后丢失红；
    列默认值改 → 非 physical_table 起步红。"""
    from app.api.concept_entity import update_entity
    from app.models.base import Entity
    from app.schemas.concept import EntityUpdate
    for f in ("source_mode", "integration_sql", "doris_catalog", "data_source_id"):
        assert f in EntityUpdate.model_fields  # 三模式配置面契约
    db = _sqlite_db()
    _seed_pair(db)
    e = db.query(Entity).filter(Entity.entity_code == "m04t_m1").first()
    assert e.source_mode == "physical_table"  # M01 兼容迁移默认值
    for mode, extra in (("sql_integration", {"integration_sql": "select 1"}),
                        ("api_integration", {}),
                        ("physical_table", {"data_source_id": None})):
        res = update_entity(str(e.id), EntityUpdate(source_mode=mode, **extra), db=db)
        assert res.source_mode == mode  # 端点响应就地反映
        db.expire_all()
        e = db.query(Entity).filter(Entity.id == str(e.id)).first()
        assert e.source_mode == mode   # 保存后持久化读回
    assert e.integration_sql == "select 1"


# ---------------------------------------------------------------------------
# §八.5 清空重置：重链 modeling/initdata/rules 引用
# ---------------------------------------------------------------------------

def test_clear_reset_relinks_modeling_initdata_rules():
    """清空重置后按 entity_code 重链三表引用：EntityModeling/EntityInitData 直接按 entity_code
    回链新 uuid，无 entity_code 列的 EntityMappingRule 借 (旧uuid→code) 桥接重链；无法恢复者
    保留原值（spec §八.5/§六——concept_admin._relink_entity_dependencies 治理行为）。
    变异锚点：entity_code 回链删/借道桥接删 → modeling/initdata/rules 引用悬空红；
    不可恢复行误改 → 原值丢失红。"""
    from app.api.concept_admin import _relink_entity_dependencies
    from app.models.base import Concept, Entity, EntityInitData, EntityMappingRule, EntityModeling
    db = _sqlite_db()
    c2 = Concept(name="m04t_l2r", level=2, area_index=91)
    db.add(c2)
    db.flush()
    e_new = Entity(concept_id=c2.id, entity_code="m04t_relink", entity_name="m04t重链实体",
                   properties_schema=[])
    db.add(e_new)
    db.flush()
    old_uuid = str(uuid.uuid4())  # 清空重置前旧实体 id（已随清空消失）
    db.add_all([
        EntityModeling(entity_id=old_uuid, entity_code="m04t_relink", entity_name="m04t重链实体",
                       model_target="database", model_table_en="m04t_relink_tbl"),
        EntityInitData(entity_id=old_uuid, entity_code="m04t_relink", entity_name="m04t重链实体",
                       init_mode="sql", init_sql="insert into t values (1)"),
        EntityMappingRule(name="m04t_rule1", source_table_ids=["s1"], entity_ids=[old_uuid]),
        EntityMappingRule(name="m04t_rule2", source_table_ids=["s2"], entity_ids=[str(e_new.id)]),
        EntityMappingRule(name="m04t_rule3", source_table_ids=["s3"], entity_ids=[str(uuid.uuid4())]),
        EntityModeling(entity_id=str(uuid.uuid4()), entity_code="m04t_ghost", entity_name="幽灵行",
                       model_target="database", model_table_en="ghost_tbl"),
    ])
    db.commit()
    res = _relink_entity_dependencies(db)
    assert res == {"modeling": 1, "initdata": 1, "rules": 1}, res
    db.expire_all()
    m = db.query(EntityModeling).filter(EntityModeling.entity_code == "m04t_relink").first()
    x = db.query(EntityInitData).filter(EntityInitData.entity_code == "m04t_relink").first()
    r1 = db.query(EntityMappingRule).filter(EntityMappingRule.name == "m04t_rule1").first()
    r2 = db.query(EntityMappingRule).filter(EntityMappingRule.name == "m04t_rule2").first()
    r3 = db.query(EntityMappingRule).filter(EntityMappingRule.name == "m04t_rule3").first()
    ghost = db.query(EntityModeling).filter(EntityModeling.entity_code == "m04t_ghost").first()
    assert m.entity_id == str(e_new.id)  # modeling 按 entity_code 回链
    assert x.entity_id == str(e_new.id)  # initdata 按 entity_code 回链
    assert r1.entity_ids == [str(e_new.id)]  # rules 借道桥接重链
    assert r2.entity_ids == [str(e_new.id)]  # 有效 uuid 原样保留
    assert len(r3.entity_ids) == 1 and r3.entity_ids[0] != str(e_new.id)  # 无法恢复保留原值
    assert ghost.entity_id != str(e_new.id)  # 无匹配 code 者不动


# ---------------------------------------------------------------------------
# §八.6 血缘页：占位登记态（禁改清单件）
# ---------------------------------------------------------------------------

def test_lineage_page_placeholder_state():
    """血缘页=登记态占位（spec §二/§五/§八.6）：LineageManager.tsx 呈现「智能溯源」卡片+
    「待开发」Empty 占位、无任何数据请求逻辑——按登记态断言，不许测出「功能缺失」就实现它。
    变异锚点：占位页提前实现真实血缘（绕过设计管线）/占位文案漂移 → 登记态破坏红。"""
    p = Path(__file__).resolve().parents[2] / "frontend" / "src" / "pages" / "LineageManager.tsx"
    assert p.is_file(), f"血缘占位页缺失：{p}"
    text = p.read_text(encoding="utf-8")
    assert "智能溯源" in text
    assert "待开发" in text
    assert "Empty" in text
    low = text.lower()
    assert "useeffect" not in low and "axios" not in low and "fetch(" not in low  # 静态占位无请求
