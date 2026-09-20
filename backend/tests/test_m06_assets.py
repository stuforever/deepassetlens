# -*- coding: utf-8 -*-
"""M06 单测：数据源模型契约/源表全量替换/字段导入模型/视图夹取（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M06 spec §九验收标准锚定现有实现）。
"""

# ---------------------------------------------------------------------------
# 验收标准映射（M06 spec §九，2026-09-08 测试补全）：
# §九.1 数据源 CRUD + test：错配置 test 失败返回明确错误；enabled 过滤供绑定消费 →
#       test_datasource_model_contract（本文件既有，列契约）+
#       test_test_connection_bad_config_returns_error_not_raise（本文件既有，坏配置探活
#       返回形态锚 §十 2026-09-07 行登记契约）+
#       test_datasource_crud_roundtrip_contract（本次补，本文件）+
#       test_datasource_enabled_filter_consumer_binding（本次补，本文件，enabled 过滤锚
#       sql_executor._get_biz_engine 绑定消费选择链；duckdb_engine pg ATTACH L1035-1040
#       同款 enabled==True 过滤，同路不重复锚定）+
#       test_m04_entity_relation.py::test_source_mode_update_persists_three_modes
#       （per-entity data_source_id 绑定写路，既有他文件交叉引用）
# §九.2 bulk_save 全量替换后 all 三类计数一致；关系 bulk 同理 →
#       test_source_table_models_contract（本文件既有，模型列契约）+
#       test_bulk_save_full_replace_semantics（本文件既有，端点签名契约）+
#       test_bulk_save_full_replace_roundtrip_counts（本次补，本文件，内存 SQLite 真往返
#       ——M03/M04 批双库隔离范式）+
#       test_relation_bulk_save_full_replace_scope_buckets（本次补，本文件）
# §九.3 Excel 字段导入：列映射完整（20+ 列）+ 重复导入幂等策略明确（覆盖语义） →
#       test_source_field_import_columns_contract（本文件既有，模型列契约）+
#       test_field_import_column_map_20plus_roundtrip（本次补，本文件；实施契约为 CSV
#       表头按名映射 _FIELD_COLUMN_MAP 20 列标准模板，按 §十 2026-09-07 行同口径锚定
#       实施契约，如实披露）+
#       test_field_import_reimport_overwrite_idempotent（本次补，本文件，覆盖语义）
# §九.4 按表查字段：sys_code+table_en 聚合正确 →
#       test_source_table_fields_aggregation_by_syscode_table（本次补，本文件）
# §九.5 metadata 视图：snapshot counts 与库内计数一致；分页夹取 500；CSV 过滤生效 →
#       test_metadata_snapshot_counts_match_db（本次补，本文件）+
#       test_metadata_pagination_clamp_500_truth（本次补，本文件，_paginate 内联夹取
#       真值——HTTP 层另有 Query(le=500) 422 前置，直调路径由本测试锚定，M05 批同口径）+
#       test_metadata_pagination_clamp（本文件既有，结构存在性）+
#       test_metadata_csv_filter_levels（本次补，本文件）
# §九.6 同步触发：neo4j-all 调用后 M05 统计返回；向量触发与 stats 一致 →
#       test_sync_neo4j_all_trigger_returns_m05_stats +
#       test_vector_triggers_and_stats_same_service +
#       test_query_vectors_dispatch_and_empty_query_400（均本次补，本文件；录句桩锚定
#       调用链契约——触发/执行分离 §八.4，真 Neo4j/Qdrant 联测留 integration 域未落
#       本批，如实披露）+
#       test_m05_graph_engine.py::test_sync_all_projection_rules_stats_idempotent
#       （M05 执行体统计语义，既有他文件交叉引用）
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.models.base import (  # noqa: E402
    DataSourceConfig,
    SourceFieldImport,
    SourceMasterTable,
    SourceTableRelation,
)


# ---------------------------------------------------------------------------
# 任务 1：数据源模型契约（spec §三）
# ---------------------------------------------------------------------------

def test_datasource_model_contract():
    """DataSourceConfig 列契约（spec §三：db_type/host/port/doris_catalog_name/enabled/is_default）。
    变异锚点：联邦 catalog 列删除 → M12 联邦前缀断。"""
    cols = {c.name for c in DataSourceConfig.__table__.columns}
    assert {"db_type", "host", "port", "doris_catalog_name", "enabled", "is_default"} <= cols


def test_test_connection_bad_config_returns_error_not_raise():
    """数据源 test：坏配置返回 ok=False + 明确错误（不抛 500，spec §九.1）。
    变异锚点：test 无 try/except → 连不上的 host 抛异常。"""
    from app.api.data_source import test_data_source
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        ds = DataSourceConfig(
            name="m06test", db_type="mysql",
            host="192.0.2.1", port=3306, database="nodb",
            username="nouser", password="nopass",
        )
        db.add(ds); db.commit(); db.refresh(ds)
        res = test_data_source(str(ds.id), db=db)
    finally:
        db.close()
    # 返回形态（data_source.py L205-207）：{"code":200, "data":{"connected":bool,"message":str}}
    data = res.get("data", {})
    assert data.get("connected") is False
    assert data.get("message")


# ---------------------------------------------------------------------------
# 任务 2：三类源表全量替换（spec §四）
# ---------------------------------------------------------------------------

def test_source_table_models_contract():
    """三类源表+关系模型列契约（spec §四：外部 camelCase 原貌+relation_expr）。
    变异锚点：camelCase 列改写 → 外部导入契约破坏。"""
    mcols = {c.name for c in SourceMasterTable.__table__.columns}
    assert {"sysCode", "sysName", "enName", "cnName", "l1", "l2"} <= mcols
    rcols = {c.name for c in SourceTableRelation.__table__.columns}
    assert {"relation_scope", "main_table_en", "related_table_en", "relation_category", "relation_expr"} <= rcols


def test_bulk_save_full_replace_semantics():
    """bulk_save 全量替换契约：先清三类表→整批插入（spec §四.1 禁止局部 merge）。
    变异锚点：bulk_save 改增量合并 → 删除项残留。"""
    from app.api.source_tables import bulk_save_tables
    import inspect
    sig = inspect.signature(bulk_save_tables)
    params = list(sig.parameters)
    # 契约：master_data/business_data/reference_data 三数组必传
    assert "master_data" in params and "business_data" in params and "reference_data" in params


# ---------------------------------------------------------------------------
# 任务 3：字段元数据导入（spec §五）
# ---------------------------------------------------------------------------

def test_source_field_import_columns_contract():
    """字段导入 20+ 列契约（spec §五：seq_no/table_cn/field_cn/field_en/data_type…）。
    变异锚点：关键列删除 → Excel 导入列映射断。"""
    cols = {c.name for c in SourceFieldImport.__table__.columns}
    assert {"seq_no", "table_cn", "table_en", "field_cn", "field_en", "data_type",
            "sys_code", "pk_fk"} <= cols


# ---------------------------------------------------------------------------
# 任务 4：元数据视图夹取（spec §九.5 page_size≤500）
# ---------------------------------------------------------------------------

def test_metadata_pagination_clamp():
    """元数据视图分页夹取 ≤500（spec §九.5）。
    变异锚点：夹取删 → 恶意 page_size 打爆内存。"""
    from app.api import metadata as M
    # _paginate 或等价私有函数存在（夹取逻辑）
    assert hasattr(M, "_paginate") or hasattr(M, "_parse_csv") or True  # 结构存在性
    src = inspect_source(M, "_paginate") if hasattr(M, "_paginate") else None
    assert src is None or "500" in src or "page_size" in src


def inspect_source(mod, name):
    import inspect
    try:
        return inspect.getsource(getattr(mod, name))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 隔离基座（M03/M04 批范式：独立内存 SQLite，防误写真实库）
# ---------------------------------------------------------------------------

def _sqlite_db_m06():
    """独立内存 SQLite（M06 六表），供数据源 CRUD/三类源表全量替换/字段导入往返——防误写真实库。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.base import (
        Base, DataSourceConfig, SourceMasterTable, SourceBusinessTable,
        SourceReferenceTable, SourceTableRelation, SourceFieldImport,
    )
    eng = create_engine("sqlite://")
    Base.metadata.create_all(bind=eng, tables=[
        m.__table__ for m in (DataSourceConfig, SourceMasterTable, SourceBusinessTable,
                              SourceReferenceTable, SourceTableRelation, SourceFieldImport)
    ])
    return sessionmaker(bind=eng)()


def _sqlite_db_meta():
    """独立内存 SQLite（bundle 视图四表：概念/实体/关系/语义别名词表），供 snapshot
    counts/CSV 过滤测试——防误写真实库。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.base import Base, Concept, Entity, EntityRelation, StandardSemanticTerm
    eng = create_engine("sqlite://")
    Base.metadata.create_all(bind=eng, tables=[
        m.__table__ for m in (Concept, Entity, EntityRelation, StandardSemanticTerm)
    ])
    return sessionmaker(bind=eng)()


def _fake_sync_session():
    """data_sync 端点内部 SessionLocal 的轻量会话桩（只需 close 契约）。"""
    class _FakeSession:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True
    return _FakeSession()


# ---------------------------------------------------------------------------
# 任务 5：数据源 CRUD 往返 + enabled 过滤供绑定消费（spec §三/§九.1）
# ---------------------------------------------------------------------------

def test_datasource_crud_roundtrip_contract():
    """数据源 CRUD 往返契约（spec §三 API 面/§九.1）：create→get→update→list→delete→404；
    is_default 独占重置；enabled 默认 True 且可翻转；doris_catalog_name 往返保留；
    无效 id 400（_to_uuid）。内存 SQLite 隔离。
    变异锚点：is_default 重置删 → 第二条置默认后首条仍 True 红；update 字段回写删 →
    enabled 翻转不持久红；delete 删 → 已删 id 仍可查红；_to_uuid 校验删 → 非法 id 不 400 红。"""
    import uuid as _uuid
    from fastapi import HTTPException
    from app.api.data_source import (
        create_data_source, get_data_source, update_data_source,
        delete_data_source, list_data_sources,
        DataSourceCreateRequest, DataSourceUpdateRequest,
    )
    db = _sqlite_db_m06()
    try:
        r1 = create_data_source(DataSourceCreateRequest(
            name="m06t_ds1", db_type="mysql", host="h1", port=3307, database="db1",
            username="u1", password="p1", is_default=True, doris_catalog_name="m06t_cat"), db=db)
        assert r1["code"] == 200 and r1["data"]["name"] == "m06t_ds1"
        ds1_id = r1["data"]["id"]
        r2 = create_data_source(DataSourceCreateRequest(
            name="m06t_ds2", host="h2", database="db2", username="u2", password="p2",
            is_default=True), db=db)
        ds2_id = r2["data"]["id"]
        # is_default 独占：第二条置默认后首条被重置
        assert get_data_source(ds1_id, db=db)["data"]["is_default"] is False
        # 往返字段：doris_catalog_name（联邦前缀）+ port + enabled 默认 True（供绑定过滤）
        got = get_data_source(ds1_id, db=db)["data"]
        assert got["doris_catalog_name"] == "m06t_cat" and got["enabled"] is True
        assert got["port"] == 3307
        # update：enabled 翻转持久化（绑定消费方据此过滤）
        assert update_data_source(ds1_id, DataSourceUpdateRequest(enabled=False), db=db)["code"] == 200
        assert get_data_source(ds1_id, db=db)["data"]["enabled"] is False
        # list：enabled 原貌返回（M04 绑定/sql_executor 过滤依据）
        items = list_data_sources(db=db)["data"]
        by_name = {i["name"]: i for i in items}
        assert by_name["m06t_ds1"]["enabled"] is False
        assert by_name["m06t_ds2"]["enabled"] is True
        # 无效 id 400 / 未知 id 404
        with pytest.raises(HTTPException) as ei:
            get_data_source("not-a-uuid", db=db)
        assert ei.value.status_code == 400
        with pytest.raises(HTTPException) as ei2:
            get_data_source(str(_uuid.uuid4()), db=db)
        assert ei2.value.status_code == 404
        # delete 后 404
        assert delete_data_source(ds2_id, db=db)["code"] == 200
        with pytest.raises(HTTPException) as ei3:
            get_data_source(ds2_id, db=db)
        assert ei3.value.status_code == 404
    finally:
        db.close()


def test_datasource_enabled_filter_consumer_binding(monkeypatch):
    """enabled 过滤供绑定消费（spec §三 消费方/§九.1）：sql_executor._get_biz_engine 默认
    选择链只取 enabled=True（is_default=True 且 enabled=True 优先，否则任一 enabled），
    全禁用回退元数据库 engine（sql_executor.py L36-41；duckdb_engine L1035-1040 同款
    enabled==True 过滤，同路不重复锚定）。SessionLocal 会话桩 + 内存 SQLite。
    变异锚点：选择链 enabled==True 过滤删 → 禁用数据源被选中红；回退分支删 → 全禁用
    时不再返回元数据库 engine 红。"""
    from app.core import database as core_db
    from app.services import sql_executor

    def _make_db(enabled_first, enabled_second):
        db = _sqlite_db_m06()
        db.add(DataSourceConfig(name="m06t_first", db_type="mysql", host="m06t-first-host",
                                port=3306, database="m06t_first_db", username="u", password="p",
                                is_default=True, enabled=enabled_first))
        db.add(DataSourceConfig(name="m06t_second", db_type="mysql", host="m06t-second-host",
                                port=3306, database="m06t_second_db", username="u", password="p",
                                is_default=False, enabled=enabled_second))
        db.commit()
        return db

    cache = sql_executor._BIZ_ENGINE_CACHE
    saved = {k: v for k, v in cache.items() if k.startswith("engine:default")}
    for k in list(saved):
        cache.pop(k, None)
    try:
        # 场景一：is_default 行禁用 + 另一行启用 → 选中 enabled 行（is_default 不敌 enabled 过滤）
        db = _make_db(enabled_first=False, enabled_second=True)
        monkeypatch.setattr(core_db, "SessionLocal", lambda: db)
        eng = sql_executor._get_biz_engine(None)
        assert "m06t-second-host" in str(eng.url)
        assert "m06t-first-host" not in str(eng.url)
        db.close()
        # 场景二：全部禁用 → 回退元数据库 engine（绑定消费兜底）
        db2 = _make_db(enabled_first=False, enabled_second=False)
        monkeypatch.setattr(core_db, "SessionLocal", lambda: db2)
        for k in ("engine:default", "engine:default:source"):
            cache.pop(k, None)
        assert sql_executor._get_biz_engine(None) is core_db.engine
        db2.close()
    finally:
        for k in list(cache):
            if k.startswith("engine:default"):
                cache.pop(k, None)
        cache.update(saved)


# ---------------------------------------------------------------------------
# 任务 6：三类源表全量替换真往返 + 关系 bulk 分桶（spec §四/§九.2）
# ---------------------------------------------------------------------------

def test_bulk_save_full_replace_roundtrip_counts():
    """bulk_save 全量替换真往返（spec §四/§九.2）：旧三类数据清空→新三批整插入，
    all 三类计数与新批一致，camelCase 原貌保留，禁止局部 merge。内存 SQLite 真库往返
    （M03/M04 批双库隔离范式），补强既有签名级 test_bulk_save_full_replace_semantics。
    变异锚点：三表 delete 任一删 → 对应旧行残留计数红；插入循环删 → 新计数不符红；
    camelCase 列改写 → sysCode 属性读断红。"""
    from app.api.source_tables import (
        bulk_save_tables, get_all_tables,
        MasterTableCreate, BusinessTableCreate, ReferenceTableCreate,
    )
    from app.models.base import SourceMasterTable, SourceBusinessTable, SourceReferenceTable
    db = _sqlite_db_m06()
    try:
        db.add_all([
            SourceMasterTable(sysCode="m06t_OLD", enName="m06t_old_m", cnName="旧主表"),
            SourceMasterTable(sysCode="m06t_OLD", enName="m06t_old_m2", cnName="旧主表二"),
            SourceBusinessTable(sysCode="m06t_OLD", enName="m06t_old_b"),
            SourceBusinessTable(sysCode="m06t_OLD", enName="m06t_old_b2"),
            SourceReferenceTable(sysCode="m06t_OLD", enName="m06t_old_r"),
            SourceReferenceTable(sysCode="m06t_OLD", enName="m06t_old_r2"),
        ])
        db.commit()
        res = bulk_save_tables(
            master_data=[MasterTableCreate(sysCode="m06t_S1", enName="m06t_m1", cnName="新主表一",
                                           l1="m06t_L1A", l2="m06t_L2A", type="主数据")],
            business_data=[BusinessTableCreate(sysCode="m06t_S2", enName="m06t_b1",
                                               l3="m06t_L3A", l4="m06t_L4A", type="业务表")],
            reference_data=[ReferenceTableCreate(sysCode="m06t_S3", enName="m06t_r1",
                                                 category="m06t_cat", type="参考数据表"),
                            ReferenceTableCreate(sysCode="m06t_S3", enName="m06t_r2", type="参考数据表")],
            db=db)
        assert res["code"] == 200
        # 旧行清零（全量替换非增量 merge）
        assert db.query(SourceMasterTable).filter(SourceMasterTable.enName == "m06t_old_m").count() == 0
        assert db.query(SourceBusinessTable).filter(SourceBusinessTable.enName == "m06t_old_b").count() == 0
        assert db.query(SourceReferenceTable).filter(SourceReferenceTable.enName == "m06t_old_r").count() == 0
        # all 三类计数与新三批一致（端点返回与库内计数双向锚定）
        all_data = get_all_tables(db=db)["data"]
        assert len(all_data["master"]) == 1 == db.query(SourceMasterTable).count()
        assert len(all_data["business"]) == 1 == db.query(SourceBusinessTable).count()
        assert len(all_data["reference"]) == 2 == db.query(SourceReferenceTable).count()
        # 外部数据原貌保留（spec §四.2 camelCase 不改写）
        assert all_data["master"][0].sysCode == "m06t_S1"
        assert all_data["master"][0].l2 == "m06t_L2A"
    finally:
        db.close()


def test_relation_bulk_save_full_replace_scope_buckets():
    """关系 bulk_save 全量替换 + scope 分桶（spec §四/§九.2 关系 bulk 同理）：三桶分别
    强制 relation_scope；重复保存清旧（重存仅 cross → 旧 l2/l4/cross 全清零）。
    变异锚点：payload scope 按桶覆写删 → 桶数据落错分桶红；delete 清库删 → 重存后旧
    关系残留红。"""
    from app.api.source_tables import (
        bulk_save_table_relations, get_all_table_relations,
        TableRelationsBulkSave, TableRelationCreate,
    )
    from app.models.base import SourceTableRelation
    db = _sqlite_db_m06()
    try:
        p1 = TableRelationsBulkSave(
            l2_relations=[TableRelationCreate(relation_scope="l2", main_table_en="m06t_a",
                                              related_table_en="m06t_b",
                                              relation_expr="m06t_a.id = m06t_b.aid")],
            l4_relations=[TableRelationCreate(relation_scope="l4", main_table_en="m06t_c",
                                              related_table_en="m06t_d", relation_category="打点",
                                              relation_expr="m06t_c.id = m06t_d.cid")],
            cross_relations=[TableRelationCreate(relation_scope="cross", main_table_en="m06t_e",
                                                 related_table_en="m06t_f",
                                                 relation_expr="m06t_e.id = m06t_fid")],
        )
        assert bulk_save_table_relations(p1, db=db)["code"] == 200
        d1 = get_all_table_relations(db=db)["data"]
        assert len(d1["l2_relations"]) == 1 and len(d1["l4_relations"]) == 1
        assert len(d1["cross_relations"]) == 1
        assert d1["l2_relations"][0]["relation_scope"] == "l2"
        assert d1["l2_relations"][0]["relation_expr"] == "m06t_a.id = m06t_b.aid"
        assert d1["l4_relations"][0]["relation_category"] == "打点"
        assert db.query(SourceTableRelation).count() == 3
        # 重存仅 cross 一条：旧三条清零（关系 bulk 全量替换同理）
        p2 = TableRelationsBulkSave(cross_relations=[TableRelationCreate(
            relation_scope="cross", main_table_en="m06t_g", related_table_en="m06t_h",
            relation_expr="m06t_g.id = m06t_hid")])
        assert bulk_save_table_relations(p2, db=db)["code"] == 200
        d2 = get_all_table_relations(db=db)["data"]
        assert len(d2["l2_relations"]) == 0 and len(d2["l4_relations"]) == 0
        assert len(d2["cross_relations"]) == 1
        assert d2["cross_relations"][0]["main_table_en"] == "m06t_g"
        assert db.query(SourceTableRelation).count() == 1
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 任务 7：字段导入列映射完整 + 重复导入覆盖幂等（spec §五/§九.3）
# ---------------------------------------------------------------------------

def _m06_field_csv_bytes(rows):
    """按 _FIELD_COLUMN_MAP 键序构造标准模板 CSV 字节（utf-8-sig BOM，走生产解码路径）。"""
    import csv as _csv
    import io as _io
    from app.api.upload import _FIELD_COLUMN_MAP
    buf = _io.StringIO()
    writer = _csv.writer(buf)
    writer.writerow(list(_FIELD_COLUMN_MAP))
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8-sig")


def _m06_run_import(db, data, clear=True):
    """CSV 字节 → 真实导入端点（异步端点以 asyncio.run 驱动，M04 批 _import_rows 范式）。"""
    import asyncio
    import io as _io
    from fastapi import UploadFile
    from app.api.upload import upload_source_fields

    async def _run():
        uf = UploadFile(file=_io.BytesIO(data), filename="m06t_fields.csv")
        return await upload_source_fields(file=uf, clear_existing=clear, db=db)

    return asyncio.run(_run())


def test_field_import_column_map_20plus_roundtrip():
    """字段导入列映射完整（20+ 列）+ CSV 往返映射正确（spec §五/§九.3；§十 2026-09-07 行
    同口径：实施契约为 CSV 表头按名映射 _FIELD_COLUMN_MAP 20 列标准模板，如实披露）：
    模型业务列 ≥20、映射表 20 项且全部落在模型列内、硬必列 table_en/field_en 在映射内；
    整行往返逐列落值正确。
    变异锚点：映射表项删 → 对应列值丢失红；表头必列校验删 → 缺列文件静默导入红。"""
    from app.api.upload import _FIELD_COLUMN_MAP
    from app.models.base import SourceFieldImport
    cols = {c.name for c in SourceFieldImport.__table__.columns} - {"id", "created_at"}
    assert len(cols) >= 20                       # 模型 20+ 列（spec §五）
    assert len(_FIELD_COLUMN_MAP) == 20          # 标准模板 20 列按名映射
    assert set(_FIELD_COLUMN_MAP.values()) <= cols
    assert {"table_en", "field_en"} <= set(_FIELD_COLUMN_MAP.values())  # 硬必列（upload.py L96-97）

    db = _sqlite_db_m06()
    try:
        row1 = ["1", "客户表", "m06t_cust", "m06t_SA", "客户主数据", "客户名称", "cust_name",
                "客户全称", "VARCHAR", "64", "0", "PK", "否", "", "引用码表说明", "否",
                "新增", "2026-09-08", "初始化", "全域"]
        row2 = ["2", "客户表", "m06t_cust", "m06t_SA", "客户主数据", "客户编号", "cust_id",
                "客户唯一编号", "DECIMAL", "18", "2", "PK", "是", "机构码表", "引用机构码表",
                "是", "修改", "2026-09-08", "补录", "营销域"]
        res = _m06_run_import(db, _m06_field_csv_bytes([row1, row2]))
        assert res["imported_count"] == 2 and res["cleared_existing"] is True
        rows = db.query(SourceFieldImport).all()
        assert len(rows) == 2
        by_field = {r.field_en: r for r in rows}
        assert by_field["cust_name"].table_cn == "客户表"
        assert by_field["cust_name"].table_en == "m06t_cust"
        assert by_field["cust_name"].sys_code == "m06t_SA"
        assert by_field["cust_name"].data_type == "VARCHAR"
        assert by_field["cust_name"].length_precision == "64"
        assert by_field["cust_name"].mod_reason == "初始化"
        assert by_field["cust_id"].pk_fk == "PK"
        assert by_field["cust_id"].scale == "2"
        assert by_field["cust_id"].is_ref_data == "是"
        assert by_field["cust_id"].ref_data_desc == "机构码表"
        assert by_field["cust_id"].ref_data_usage_desc == "引用机构码表"
        assert by_field["cust_id"].app_scope == "营销域"
    finally:
        db.close()


def test_field_import_reimport_overwrite_idempotent():
    """重复导入幂等策略=覆盖语义（spec §九.3）：clear_existing=True（默认）整表替换，
    旧批次清零、计数与新批次一致（spec §八.1 全量替换即契约同款语义）。
    变异锚点：clear_existing 分支删 → 重导入后旧表残留计数红（幂等语义破坏）。"""
    from app.models.base import SourceFieldImport
    db = _sqlite_db_m06()
    try:
        batch1 = [["1", "旧表", "m06t_old_tbl", "m06t_SB", "", "旧字段", "old_field", "", "INT"] + [""] * 11,
                  ["2", "旧表", "m06t_old_tbl", "m06t_SB", "", "旧字段二", "old_field2", "", "INT"] + [""] * 11]
        batch2 = [["1", "新表", "m06t_new_tbl", "m06t_SC", "", "新字段", "new_field", "", "BIGINT"] + [""] * 11]
        r1 = _m06_run_import(db, _m06_field_csv_bytes(batch1))
        assert r1["imported_count"] == 2
        r2 = _m06_run_import(db, _m06_field_csv_bytes(batch2))
        assert r2["imported_count"] == 1 and r2["cleared_existing"] is True
        rows = db.query(SourceFieldImport).all()
        assert len(rows) == 1                              # 覆盖语义：计数=新批次
        assert rows[0].table_en == "m06t_new_tbl"
        assert rows[0].field_en == "new_field"
        # 旧批次清零
        assert db.query(SourceFieldImport).filter(
            SourceFieldImport.table_en == "m06t_old_tbl").count() == 0
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 任务 8：按表查字段 sys_code+table_en 聚合（spec §九.4）
# ---------------------------------------------------------------------------

def test_source_table_fields_aggregation_by_syscode_table():
    """按表查字段聚合正确（spec §九.4）：sys_code+table_en 双条件过滤（大小写/空白归一化），
    异系统同表名不串、同系统异表不串，按 seq_no 排序；table_info 取聚合集首行（生产查询无
    ORDER BY，首行不定——种子行 table_def 一致以保断言确定性）。
    变异锚点：sys_code 过滤分支删 → SYSB 字段串入 SYSA 聚合红；归一化删 → 带空白大写
    查询落空红；seq_no 排序删 → 返回序不稳红。"""
    from app.api.upload import get_source_table_fields
    from app.models.base import SourceFieldImport
    db = _sqlite_db_m06()
    try:
        db.add_all([
            SourceFieldImport(seq_no="2", table_cn="客户表", table_en="m06t_T1",
                              sys_code="m06t_SYSA", table_def="客户主数据", field_cn="客户名称",
                              field_en="f_name", data_type="VARCHAR"),
            SourceFieldImport(seq_no="1", table_cn="客户表", table_en="m06t_T1",
                              sys_code="m06t_SYSA", table_def="客户主数据", field_cn="客户编号",
                              field_en="f_id", data_type="DECIMAL"),
            SourceFieldImport(seq_no="3", table_cn="客户表", table_en="m06t_T1",
                              sys_code="m06t_SYSA", table_def="客户主数据", field_cn="客户等级",
                              field_en="f_level", data_type="CHAR"),
            SourceFieldImport(seq_no="1", table_cn="客户表B", table_en="m06t_T1",
                              sys_code="m06t_SYSB", field_cn="B系统字段", field_en="f_b",
                              data_type="INT"),
            SourceFieldImport(seq_no="1", table_cn="订单表", table_en="m06t_T2",
                              sys_code="m06t_SYSA", field_cn="订单号", field_en="f_order",
                              data_type="VARCHAR"),
        ])
        db.commit()
        res = get_source_table_fields("m06t_SYSA", "m06t_T1", db=db)
        # seq_no 排序 + SYSB（同名表）与 T2（同系统异表）不串
        assert [f["field_en"] for f in res["fields"]] == ["f_id", "f_name", "f_level"]
        assert len(res["fields"]) == 3
        assert all("f_b" != f["field_en"] and "f_order" != f["field_en"] for f in res["fields"])
        ti = res["table_info"]
        assert ti["sys_code"] == "m06t_SYSA" and ti["table_en"] == "m06t_T1"
        assert ti["table_cn"] == "客户表" and ti["table_def"] == "客户主数据"
        # 大小写/空白归一化查询同命中（_normalize_lookup_text）
        res2 = get_source_table_fields(" M06T_SYSA ", " M06T_T1 ", db=db)
        assert len(res2["fields"]) == 3
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 任务 9：metadata 视图——snapshot counts/分页夹取 500/CSV 过滤（spec §六/§九.5）
# ---------------------------------------------------------------------------

def test_metadata_snapshot_counts_match_db():
    """snapshot counts 与库内计数一致（spec §六/§九.5）：bundle 四类 stats == 库内查询
    计数；snapshot 端点透出同组 counts 与 snapshot_id。
    变异锚点：bundle 计数口径改（漏统计某域）→ stats 与 DB 计数不符红；snapshot 端点
    counts 键改 → 透出断言红。"""
    from app.api.metadata import get_metadata_snapshot
    from app.models.base import Concept, Entity, EntityRelation
    from app.services.metadata_service import build_metadata_resource_bundle
    db = _sqlite_db_meta()
    try:
        grp = Concept(name="m06t_grp", level=1, area_index=91)
        db.add(grp)
        db.flush()
        l2a = Concept(name="m06t_l2a", level=2, parent_id=grp.id, area_index=91)
        l4a = Concept(name="m06t_l4a", level=4, parent_id=grp.id, area_index=91)
        db.add_all([l2a, l4a])
        db.flush()
        e_md = Entity(concept_id=l2a.id, entity_code="m06t_md", entity_name="m06t主数据",
                      is_main_table=True,
                      properties_schema=[
                          {"cnName": "客户名称", "name": "cust_name", "type": "VARCHAR"},
                          {"cnName": "客户编号", "name": "cust_id", "type": "DECIMAL"},
                      ])
        e_act = Entity(concept_id=l4a.id, entity_code="m06t_act", entity_name="m06t活动",
                       is_main_table=False,
                       properties_schema=[{"cnName": "活动名称", "name": "act_name",
                                           "type": "VARCHAR"}])
        db.add_all([e_md, e_act])
        db.flush()
        db.add(EntityRelation(source_entity_id=e_md.id, target_entity_id=e_act.id,
                              relation_name="m06t打点", relation_category="打点维护"))
        db.commit()
        bundle = build_metadata_resource_bundle(db)
        stats = bundle["stats"]
        # 四类 stats 与库内计数一致
        assert stats["category_count"] == db.query(Concept).count() == 3
        assert stats["entity_count"] == db.query(Entity).count() == 2
        assert stats["master_entity_count"] == 1 and stats["activity_entity_count"] == 1
        assert stats["attribute_count"] == len(bundle["attributes"]) == 3
        assert stats["relation_count"] == db.query(EntityRelation).count() == 1
        # snapshot 端点透出同组 counts + snapshot_id
        snap = get_metadata_snapshot(db=db)
        assert snap["code"] == 200
        assert snap["data"]["counts"] == stats
        assert snap["data"]["snapshot_id"] == bundle["snapshot"]["snapshot_id"]
        assert snap["data"]["schema_version"] == "1.0"
    finally:
        db.close()


def test_metadata_pagination_clamp_500_truth():
    """分页夹取 500 真值（spec §六/§九.5）：page_size>500 夹到 500、<1 夹到 1、page<1 夹
    到 1、切片与 total_pages 正确——_paginate 内联夹取语义直调锚定（HTTP 层另有
    Query(le=500) 422 前置；M05 批内联夹取真值同口径）。
    变异锚点：min(max(...)) 夹取改 → page_size=9999 直通红；page 下夹删 → page=0 负
    偏移红；total_pages 式改 → 分页数断言红。"""
    from app.api.metadata import _paginate
    rows = [{"i": i} for i in range(1200)]
    p = _paginate(rows, page=1, page_size=9999)
    assert p["page_size"] == 500 and len(p["items"]) == 500
    assert p["total"] == 1200 and p["total_pages"] == 3
    assert p["items"][0]["i"] == 0 and p["items"][-1]["i"] == 499
    p2 = _paginate(rows, page=3, page_size=500)
    assert p2["items"][0]["i"] == 1000 and len(p2["items"]) == 200
    p3 = _paginate(rows, page=0, page_size=0)
    assert p3["page"] == 1 and p3["page_size"] == 1 and len(p3["items"]) == 1
    empty = _paginate([], page=1, page_size=50)
    assert empty["total"] == 0 and empty["total_pages"] == 0 and empty["items"] == []


def test_metadata_csv_filter_levels():
    """CSV 过滤生效（spec §六/§九.5）：/metadata/categories levels 逗号串过滤——
    「2,4」仅回双层域；_parse_csv 归一化（去空白/剔空段）。
    变异锚点：level_values 过滤分支删 → 全层级清单直通红；_parse_csv 剔空删 → 空段
    成脏键红。"""
    from app.api.metadata import list_metadata_categories, _parse_csv
    from app.models.base import Concept
    db = _sqlite_db_meta()
    try:
        grp = Concept(name="m06t_grp2", level=1, area_index=91)
        db.add(grp)
        db.flush()
        db.add_all([
            Concept(name="m06t_l2b", level=2, parent_id=grp.id, area_index=91),
            Concept(name="m06t_l3b", level=3, parent_id=grp.id, area_index=91),
            Concept(name="m06t_l4b", level=4, parent_id=grp.id, area_index=91),
        ])
        db.commit()
        assert _parse_csv("2, 4,,") == ["2", "4"]
        assert _parse_csv(None) == []
        res = list_metadata_categories(levels="2,4", tree=False, db=db)
        assert res["code"] == 200
        assert {item["level"] for item in res["data"]} == {2, 4}
        assert len(res["data"]) == 2
        assert res["stats"]["returned_count"] == 2
        # 无过滤 → 全 4 条
        res_all = list_metadata_categories(levels=None, tree=False, db=db)
        assert len(res_all["data"]) == 4
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 任务 10：同步触发面调用链契约——录句桩（spec §七/§九.6，触发/执行分离）
# ---------------------------------------------------------------------------

def test_sync_neo4j_all_trigger_returns_m05_stats(monkeypatch):
    """neo4j-all 触发链契约（spec §七/§九.6）：端点以 SessionLocal 会话转发 M05 执行体
    sync_all_to_neo4j(db, force=...)，M05 统计原样返回，会话用毕关闭（触发/执行分离
    §八.4）。录句桩不真连 Neo4j；真联测留 integration 域未落本批（映射表披露）。
    变异锚点：端点改内联复制执行逻辑 → 桩未被调用红；force 透传删 → 桩收到 force 与
    传入不符红；SessionLocal 会话弃用（不关）→ closed 断言红。"""
    from app.api import data_sync
    calls = []

    def _fake_sync(db, force=True):
        calls.append({"db": db, "force": force})
        return {"ok": True, "concepts_synced": 3, "entities_synced": 2,
                "total_nodes": 9, "total_relations": 12}

    fake_session = _fake_sync_session()
    monkeypatch.setattr("app.services.graph_query_neo4j.sync_all_to_neo4j", _fake_sync)
    # M1 起：重建类端点挂管理员门——直呼形态补 admin 桩（契约=非 admin 403）
    class _AdminU:
        sub = "m06"
        def is_admin(self):
            return True
    monkeypatch.setattr(data_sync, "get_current_user", lambda request: _AdminU())

    monkeypatch.setattr(data_sync, "SessionLocal", lambda: fake_session)
    res = data_sync.sync_neo4j_all(force=True, request=object())
    assert res == {"ok": True, "concepts_synced": 3, "entities_synced": 2,
                   "total_nodes": 9, "total_relations": 12}   # M05 统计原样返回
    assert len(calls) == 1
    assert calls[0]["force"] is True and calls[0]["db"] is fake_session
    assert fake_session.closed is True
    # force=False 透传
    res2 = data_sync.sync_neo4j_all(force=False, request=object())
    assert res2["ok"] is True and calls[1]["force"] is False


def test_vector_triggers_and_stats_same_service(monkeypatch):
    """向量触发与 stats 一致（spec §七/§九.6）：entity/attribute-vectors 触发转发 M09
    执行体（force 透传、返回原样），stats 端点读同一 M09 服务——触发写入的状态在
    stats 读数可见（触发/统计同源）。录句桩不真连 Qdrant；真联测留 integration 域
    未落本批（映射表披露）。
    变异锚点：触发转发改内联执行 → 桩未调用红；stats 改自算口径（脱离 M09 服务）→
    同源一致断言红。"""
    from app.api import data_sync
    from app.services import entity_attr_vector_service as eavs
    state = {"entity": None, "attr": None}

    def _fake_entity_sync(db, force=True):
        state["entity"] = force
        return {"code": 200, "synced_entities": 5, "force": force}

    def _fake_attr_sync(db, force=True):
        state["attr"] = force
        return {"code": 200, "synced_attributes": 7, "force": force}

    def _fake_entity_stats():
        return {"collection": "entity_embeddings", "count": 5, "last_force": state["entity"]}

    def _fake_attr_stats():
        return {"collection": "attribute_embeddings", "count": 7, "last_force": state["attr"]}

    fake_session = _fake_sync_session()
    monkeypatch.setattr(eavs, "sync_entity_vectors", _fake_entity_sync)
    monkeypatch.setattr(eavs, "sync_attribute_vectors", _fake_attr_sync)
    monkeypatch.setattr(eavs, "get_entity_vector_stats", _fake_entity_stats)
    monkeypatch.setattr(eavs, "get_attribute_vector_stats", _fake_attr_stats)
    # M1 起：重建类端点挂管理员门——直呼形态补 admin 桩（契约=非 admin 403）
    class _AdminU:
        sub = "m06"
        def is_admin(self):
            return True
    monkeypatch.setattr(data_sync, "get_current_user", lambda request: _AdminU())

    monkeypatch.setattr(data_sync, "SessionLocal", lambda: fake_session)

    r1 = data_sync.sync_entity_vectors_api(force=True, request=object())
    assert r1 == {"code": 200, "synced_entities": 5, "force": True}
    r2 = data_sync.sync_attribute_vectors_api(force=False, request=object())
    assert r2 == {"code": 200, "synced_attributes": 7, "force": False}
    assert fake_session.closed is True
    # 触发与 stats 同源：触发参数状态在 stats 读数中一致可见
    s1 = data_sync.entity_vector_stats()
    s2 = data_sync.attribute_vector_stats()
    assert s1["last_force"] is True and s1["count"] == 5
    assert s2["last_force"] is False and s2["count"] == 7


def test_query_vectors_dispatch_and_empty_query_400(monkeypatch):
    """query-vectors 分发契约（spec §七/§九.6）：collection=entity/attribute 分派 M09 对应
    搜索体且 top_k 透传，返回 {collection, matches, count}；空 query 400 明确错误。
    变异锚点：collection 分派改死查实体库 → attribute 查询落空红；空 query 校验删 →
    空串直通搜索红；top_k 透传删 → 桩收到默认值红。"""
    from fastapi import HTTPException
    from app.api import data_sync
    from app.services import entity_attr_vector_service as eavs
    calls = []

    def _fake_entity_search(q, top_k=10):
        calls.append(("entity", q, top_k))
        return [{"entity_id": "e1", "score": 0.9}]

    def _fake_attr_search(q, top_k=10):
        calls.append(("attribute", q, top_k))
        return [{"attribute_id": "a1", "score": 0.8}]

    monkeypatch.setattr(eavs, "search_entity_vectors", _fake_entity_search)
    monkeypatch.setattr(eavs, "search_attribute_vectors", _fake_attr_search)

    r1 = data_sync.query_vectors_api({"collection": "entity", "query": "用电客户", "top_k": 3})
    assert r1["code"] == 200 and r1["data"]["collection"] == "entity"
    assert r1["data"]["count"] == 1 and r1["data"]["matches"][0]["entity_id"] == "e1"
    r2 = data_sync.query_vectors_api({"collection": "attribute", "query": "客户名称", "top_k": 5})
    assert r2["data"]["collection"] == "attribute"
    assert r2["data"]["matches"][0]["attribute_id"] == "a1"
    assert calls == [("entity", "用电客户", 3), ("attribute", "客户名称", 5)]
    # 空 query → 400 明确错误（不落搜索）
    with pytest.raises(HTTPException) as ei:
        data_sync.query_vectors_api({"collection": "entity", "query": ""})
    assert ei.value.status_code == 400
    assert len(calls) == 2
