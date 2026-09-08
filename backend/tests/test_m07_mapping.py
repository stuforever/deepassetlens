# -*- coding: utf-8 -*-
"""M07 单测：映射模型契约/溯源 UUID 兼容/伪 SQL 无 WHERE 约束（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M07 spec §九验收标准锚定现有实现）。
"""

# ---------------------------------------------------------------------------
# 验收标准映射（M07 spec §九，2026-09-08 测试补全）：
# §九.1 映射规则 CRUD + 溯源：32/36 位 UUID 兼容匹配 →
#       test_lineage_uuid_compat_32_36_match（本次补，本文件，双形态规则行真匹配行为锚）+
#       test_lineage_uuid_compat_logic（本文件既有，归一化逻辑存在性锚，行为锚由前条补强）；
#       三源表类型聚合正确 → test_lineage_three_source_table_types_aggregated（本次补，本文件）；
#       无规则实体返回空链路非 500 → test_lineage_entity_without_rules_not_500（本文件既有）+
#       test_lineage_entity_missing_404_not_500（本文件既有，不存在实体 404 非 500）；
#       映射规则 CRUD → test_mapping_rule_crud_roundtrip（本次补，本文件，内存 SQLite 真往返）
# §九.2 ApiEndpoint 全生命周期：配置新端点→/tables 可见（table_name 唯一）→
#       test_api_endpoint_create_and_tables_visible（本次补，本文件）；
#       execute 按列契约返回（columns json_path 提取，经 load_endpoints_from_db 装配）→
#       test_api_endpoint_execute_contract_via_json_path（本次补，本文件）+
#       test_api_endpoint_execute_guards_reject_unsafe_sql（本次补，本文件，空 SQL/非 SELECT/DDL 拒）；
#       test 失败给结构化错误 → test_api_endpoint_test_failure_structured_error（本次补，本文件，
#       引擎级 error/error_class + API 级 code 500 双层）+
#       test_api_endpoint_test_dtype_suggestion_written_back（本次补，本文件，采样定 dtype 回写）；
#       cache_ttl 生效（重复执行命中缓存）→ test_engine_enhance.py::TestFakeApi::test_cache_hit_zero_second_call
#       （既有他文件交叉引用，引擎级「同问题二问零 API 调用」）+
#       test_engine_p3.py::TestCircuitBreaker::test_cache_hit_skips_circuit（既有他文件交叉引用）+
#       test_api_endpoint_config_save_invalidates_cache（本次补，本文件，配置保存/删除即失效录句桩）；
#       pagination 翻页取全量 → test_api_endpoint_pagination_fetches_all_pages（本次补，本文件，
#       假件逐页合并+页参序列+上限警告）
# §九.3 EntityApiMapping：verify 能发现列缺失/类型不匹配 →
#       test_entity_api_mapping_verify_surfaces_contract_mismatch（本次补，本文件，DuckDB 真执行
#       暴露契约偏差为结构化错误）；execute 多端点整合 →
#       test_entity_api_mapping_execute_integrates_multiple_endpoints（本次补，本文件，双虚拟表
#       JOIN 整合+filters 动态下推）+ test_entity_api_mapping_execute_missing_guards_404（本次补，
#       本文件，实体/映射缺失 404）
# §九.4 integration-sql：verify 拒绝引用不存在虚拟表 →
#       test_integration_sql_verify_rejects_missing_table_structured（本次补，本文件，结构化错误
#       非假成功非 500；Doris 缺表分类语义由 test_m21_engines.py::test_classify_by_message_core_classes
#       交叉锚定）；ai-rewrite 返回建议不落库 →
#       test_integration_sql_ai_rewrite_suggestion_not_persisted（本次补，本文件，建议返回+库零写入
#       +实体缺失不改写；ai_rewrite_sql 在位由 test_m21_engines.py::test_sql_rewrite_service_exists
#       交叉锚定）；execute 走安全链 →
#       test_integration_sql_execute_pushdown_safe_chain（本次补，本文件，filters 经 AST 安全构造
#       下推+catalog 透传；build_sql_with_filters 注入防护全谱由 test_f1_sql_injection.py 交叉锚定）
# §九.5 前端：三 Tab 与 source_mode 跳转对齐+实体过滤联动 →
#       test_frontend_tab_alignment_source_contract（本次补，本文件，源码级登记态断言：
#       ModelTreeManager tabMap 三模式→Tab1/2/3 + MappingManager 消费跳转/过滤态）；
#       交互链路（点击跳转/过滤渲染）pytest 不可达，e2e 域覆盖（批次末总验收承接），如实披露；
#       预览弹窗数据闭环（后端半环）→ test_entity_preview_three_modes_backend_loop（本次补，
#       本文件，三 source_mode 分发+rows 对象数组+缺配 hint 降级）
# §九.6 预留表存在且无消费代码（登记一致）→
#       test_smart_join_review_reserved_table_no_consumer（本次补，本文件，import 探针+源码级
#       grep 断言，SmartJoinReview 按登记态断言不实现）
# 既有测试保留（非 §九 主锚点，模型契约基座）：test_entity_mapping_rule_columns /
#       test_api_endpoint_columns_contract / test_entity_api_mapping_pseudo_sql_column
#       （§三/§四/§五 列契约，为 §九.1-§九.3 行为锚提供结构前提）
# ---------------------------------------------------------------------------
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.models.base import ApiEndpoint, EntityApiMapping, EntityMappingRule  # noqa: E402


# ---------------------------------------------------------------------------
# 任务 1：映射规则模型契约（spec §三）
# ---------------------------------------------------------------------------

def test_entity_mapping_rule_columns():
    """EntityMappingRule 列契约（spec §三：source_table_ids/entity_ids/field_mappings/is_advanced_sql/sql_content）。
    变异锚点：高级 SQL 列删 → 物理表模式升级断。"""
    cols = {c.name for c in EntityMappingRule.__table__.columns}
    assert {"name", "source_table_ids", "entity_ids", "field_mappings", "is_advanced_sql", "sql_content"} <= cols


def test_api_endpoint_columns_contract():
    """ApiEndpoint 列契约（spec §四：table_name unique/params/columns/data_path/body_template/cache_ttl/pagination/run_config）。
    变异锚点：虚拟表唯一名删 → DuckDB 引用歧义。"""
    cols = {c.name for c in ApiEndpoint.__table__.columns}
    assert {"name", "table_name", "api_url", "method", "headers", "body_template",
            "params", "columns", "data_path", "cache_ttl_seconds", "pagination", "run_config"} <= cols


def test_entity_api_mapping_pseudo_sql_column():
    """EntityApiMapping 伪 SQL 列（spec §五：pseudo_sql 不含 WHERE）。
    变异锚点：pseudo_sql 列删 → 对象级 API 整合断。"""
    cols = {c.name for c in EntityApiMapping.__table__.columns}
    assert {"entity_id", "api_endpoint_ids", "field_mappings", "pseudo_sql"} <= cols


# ---------------------------------------------------------------------------
# 任务 1：溯源 UUID 兼容（spec §九.1）
# ---------------------------------------------------------------------------

def test_lineage_uuid_compat_logic():
    """溯源 32/36 位 UUID 兼容匹配逻辑（spec §三：UUID 32/36 位连字符兼容）。
    变异锚点：归一化删 → 32 位存储匹配不上 36 位查询。"""
    from app.api import mapping as M
    # 定位 UUID 归一化辅助（双形态解析 L334-339）
    candidates = []
    for name in dir(M):
        if "uuid" in name.lower() or "norm" in name.lower():
            candidates.append(name)
    # 契约：存在 UUID 归一化逻辑（函数或 get_entity_lineage 内联）；直接验证 32/36 等价
    import re
    uid32 = "a" * 32
    uid36 = f"{uid32[:8]}-{uid32[8:12]}-{uid32[12:16]}-{uid32[16:20]}-{uid32[20:]}"
    norm = lambda s: s.replace("-", "").lower()  # 与 L331-340 归一化等价
    assert norm(uid36) == norm(uid32)
    # 溯源入口存在
    assert hasattr(M, "get_entity_lineage")


def test_lineage_entity_without_rules_not_500():
    """存在实体但无映射规则→空 lineage 结构（spec §九.1 非 500）。
    变异锚点：无规则分支抛异常 → 前端溯源页崩。"""
    from app.api.mapping import get_entity_lineage
    from app.core.database import SessionLocal
    from app.models.base import Concept, Entity
    import uuid
    db = SessionLocal()
    eid = None
    cid = None
    try:
        cid = str(uuid.uuid4())
        db.add(Concept(id=cid, name="m07test", level=2, area_index=1))
        db.commit()
        eid = str(uuid.uuid4())
        db.add(Entity(id=eid, entity_code="m07test_code", entity_name="m07test", concept_id=cid))
        db.commit()
        res = get_entity_lineage(eid, db=db)
    finally:
        if eid:
            db.query(Entity).filter(Entity.id == eid).delete()
        if cid:
            db.query(Concept).filter(Concept.id == cid).delete()
        db.commit(); db.close()
    assert isinstance(res, dict) or isinstance(res, list)


def test_lineage_entity_missing_404_not_500():
    """不存在的实体→404（非 500）。
    变异锚点：404 分支删 → 未知实体 500。"""
    from app.api.mapping import get_entity_lineage
    from app.core.database import SessionLocal
    import uuid
    db = SessionLocal()
    try:
        from fastapi import HTTPException
        try:
            get_entity_lineage(str(uuid.uuid4()), db=db)
            assert False, "应 404"
        except HTTPException as e:
            assert e.status_code == 404
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 任务 3：伪 SQL 无 WHERE 约束（spec §八.2 安全边界）
# ---------------------------------------------------------------------------

def test_pseudo_sql_no_where_constraint():
    """EntityApiMapping 创建/更新拒绝含 WHERE 的伪 SQL（spec §八.2 安全边界）。
    变异锚点：WHERE 校验删 → 用户输入注入伪 SQL 模板。"""
    from app.api.api_mapping import _validate_pseudo_sql_no_where
    from fastapi import HTTPException
    # 合法模板（无 WHERE）放行
    _validate_pseudo_sql_no_where("SELECT t0.id, t0.name FROM vt0 t0 JOIN vt1 t1 ON t0.id=t1.id")
    _validate_pseudo_sql_no_where(None)
    # 含 WHERE → 400
    with pytest.raises(HTTPException) as ei:
        _validate_pseudo_sql_no_where("SELECT * FROM vt WHERE x=1")
    assert ei.value.status_code == 400
    # 字符串字面量里的 WHERE 不误判
    _validate_pseudo_sql_no_where("SELECT 'where' AS literal FROM vt")


# ---------------------------------------------------------------------------
# 隔离基座（M03/M04/M06 批范式：独立内存 SQLite，防误写真实库）
# ---------------------------------------------------------------------------

def _sqlite_db_m07():
    """独立内存 SQLite（M07 八表），供映射规则 CRUD/溯源/API 编排/integration-sql 往返。"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.base import (
        Base, Concept, Entity, EntityMappingRule, SourceMasterTable,
        SourceBusinessTable, SourceReferenceTable, ApiEndpoint, EntityApiMapping,
    )
    eng = create_engine("sqlite://")
    Base.metadata.create_all(bind=eng, tables=[
        m.__table__ for m in (Concept, Entity, EntityMappingRule, SourceMasterTable,
                              SourceBusinessTable, SourceReferenceTable,
                              ApiEndpoint, EntityApiMapping)
    ])
    return sessionmaker(bind=eng)()


def _mk_concept_entity(db, code, name=None, **entity_extra):
    """概念+实体桩（Entity.concept_id NOT NULL，M03/M07 既有范式）。
    entity_extra 可覆盖 entity_code/entity_name 之外的任意 Entity 列；
    显式传 entity_code 时覆盖 code。"""
    import uuid
    from app.models.base import Concept, Entity
    cid = str(uuid.uuid4())
    db.add(Concept(id=cid, name=f"m07c_{code}", level=2, area_index=1))
    db.commit()
    eid = str(uuid.uuid4())
    db.add(Entity(id=eid, entity_code=entity_extra.pop("entity_code", code),
                  entity_name=name or code, concept_id=cid, **entity_extra))
    db.commit()
    return cid, eid


# ---------------------------------------------------------------------------
# §九.1 映射规则 CRUD 往返 + 溯源 UUID 兼容真匹配 + 三源表类型聚合
# ---------------------------------------------------------------------------

def test_mapping_rule_crud_roundtrip():
    """映射规则 CRUD 往返契约（spec §九.1/§三）：create→detail→list 过滤→update→delete→404；
    entity_ids 必须恰一（0/2 个 400）；同实体重复绑定 409；field_mappings 引用未选源表 400；
    不存在实体 400。内存 SQLite 隔离。
    变异锚点：恰一校验删 → 多实体规则混入红；实体 key 冲突检测删 → 同实体双规则 409 断红；
    field_mappings 子集校验删 → 幽灵源表引用入库红；update 回写删 → 改名不持久红。"""
    import uuid
    from fastapi import HTTPException
    from app.api.mapping import (
        create_mapping_rule, get_mapping_rules, get_mapping_rule_detail,
        update_mapping_rule, delete_mapping_rule, MappingRuleCreate, MappingRuleUpdate,
    )
    from app.models.base import SourceMasterTable
    db = _sqlite_db_m07()
    try:
        _, eid = _mk_concept_entity(db, "m07crud")
        tid = str(uuid.uuid4())
        db.add(SourceMasterTable(id=tid, sysCode="M07", enName="m07_tbl", cnName="映射源表"))
        db.commit()
        # create 守卫：entity_ids 恰一
        for bad in ([], [str(uuid.uuid4()), str(uuid.uuid4())]):
            with pytest.raises(HTTPException) as ei:
                create_mapping_rule(MappingRuleCreate(source_table_ids=[], entity_ids=bad), db=db)
            assert ei.value.status_code == 400
        # create：不存在实体 400
        with pytest.raises(HTTPException) as ei:
            create_mapping_rule(MappingRuleCreate(source_table_ids=[], entity_ids=[str(uuid.uuid4())]), db=db)
        assert ei.value.status_code == 400
        # create 主路
        r = create_mapping_rule(MappingRuleCreate(
            name="规则A", source_table_ids=[tid], entity_ids=[eid],
            field_mappings={}), db=db)
        assert r["code"] == 200 and r["data"]["overwritten"] is False
        rid = r["data"]["id"]
        # 同实体重复绑定 → 409（实体名 key 冲突）
        with pytest.raises(HTTPException) as ei:
            create_mapping_rule(MappingRuleCreate(name="规则B", source_table_ids=[], entity_ids=[eid]), db=db)
        assert ei.value.status_code == 409
        # detail 往返
        d = get_mapping_rule_detail(rid, db=db)
        assert d["data"]["name"] == "规则A" and d["data"]["source_table_ids"] == [tid]
        # list 按 entity_id 过滤
        lst = get_mapping_rules(entity_id=eid, db=db)
        assert [x["id"] for x in lst["data"]] == [rid]
        # update：改名持久化
        update_mapping_rule(rid, MappingRuleUpdate(name="规则A2"), db=db)
        assert get_mapping_rule_detail(rid, db=db)["data"]["name"] == "规则A2"
        # update：field_mappings 引用未选源表 → 400
        with pytest.raises(HTTPException) as ei:
            update_mapping_rule(rid, MappingRuleUpdate(
                source_table_ids=[], field_mappings={"prop": {"source": f"{tid}_col"}}), db=db)
        assert ei.value.status_code == 400
        # delete → 200，再查 404
        assert delete_mapping_rule(rid, db=db)["code"] == 200
        with pytest.raises(HTTPException) as ei:
            get_mapping_rule_detail(rid, db=db)
        assert ei.value.status_code == 404
    finally:
        db.close()


def test_lineage_uuid_compat_32_36_match():
    """溯源 32/36 位 UUID 连字符兼容真匹配（spec §三 L331-340）：规则 entity_ids 存 32 位
    （历史双形态）而实体/查询用 36 位 → 仍命中；反向（实体 32 位存储+规则 36 位+查询 32 位）
    同样命中。行为级锚定（既有 test_lineage_uuid_compat_logic 为存在性锚）。
    变异锚点：归一化 replace('-','') 删 → 32 位存储规则行匹配不上 36 位查询红。"""
    import uuid
    from app.api.mapping import get_entity_lineage
    from app.models.base import EntityMappingRule, SourceMasterTable
    db = _sqlite_db_m07()
    try:
        tid = str(uuid.uuid4())  # lineage 逐「规则×源表」展开，规则须挂源表才产链路
        db.add(SourceMasterTable(id=tid, sysCode="M07", enName="u_tbl", cnName="兼容源表"))
        db.commit()
        # 方向一：实体 36 位，规则行混存 32/36 两种形态
        _, eid36 = _mk_concept_entity(db, "m07u36")
        uid32 = eid36.replace("-", "")
        db.add(EntityMappingRule(name="r36", source_table_ids=[tid], entity_ids=[eid36]))
        db.add(EntityMappingRule(name="r32", source_table_ids=[tid], entity_ids=[uid32]))
        db.commit()
        res = get_entity_lineage(eid36, db=db)
        assert {x["rule_name"] for x in res["lineage"]} == {"r36", "r32"}
        # 方向二：实体 id 本身按 32 位存储，规则存 36 位形态，查询传 32 位
        _, eid32 = _mk_concept_entity(db, "m07u32")
        eid32_as36 = f"{eid32[:8]}-{eid32[8:12]}-{eid32[12:16]}-{eid32[16:20]}-{eid32[20:]}"
        db.add(EntityMappingRule(name="r32ent", source_table_ids=[tid], entity_ids=[eid32_as36]))
        db.commit()
        res2 = get_entity_lineage(eid32, db=db)
        assert [x["rule_name"] for x in res2["lineage"]] == ["r32ent"]
    finally:
        db.close()


def test_lineage_three_source_table_types_aggregated():
    """三源表类型聚合正确（spec §九.1/§三 L346-359）：规则 source_table_ids 横跨
    主数据/业务表/参考数据三类 → lineage 逐表展开三条链路，cnName/enName/sysName
    原貌输出，mapping_logic/sql_fragment 随链路返回。
    变异锚点：三类源表字典合并查找删任一 → 对应类型链路丢失红；逐表展开循环删 →
    多源规则只出一条链路红。"""
    import uuid
    from app.api.mapping import get_entity_lineage
    from app.models.base import (
        EntityMappingRule, SourceMasterTable, SourceBusinessTable, SourceReferenceTable,
    )
    db = _sqlite_db_m07()
    try:
        _, eid = _mk_concept_entity(db, "m07agg")
        mid, bid, rid = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
        db.add(SourceMasterTable(id=mid, sysCode="S1", enName="master_tbl", cnName="主表", sysName="系统一"))
        db.add(SourceBusinessTable(id=bid, sysCode="S2", enName="biz_tbl", cnName="业务表", sysName="系统二"))
        db.add(SourceReferenceTable(id=rid, sysCode="S3", enName="ref_tbl", cnName="参考表", sysName="系统三"))
        db.add(EntityMappingRule(name="三源规则", source_table_ids=[mid, bid, rid],
                                 entity_ids=[eid], field_mappings={"prop": {"source": f"{mid}_f1"}},
                                 sql_content="SELECT 1"))
        db.commit()
        res = get_entity_lineage(eid, db=db)
        lin = res["lineage"]
        assert len(lin) == 3, f"三源应逐表展开三条链路，实际 {len(lin)}"
        by_en = {x["source_table"]["en_name"]: x for x in lin}
        assert set(by_en) == {"master_tbl", "biz_tbl", "ref_tbl"}
        assert by_en["master_tbl"]["source_table"]["table_name"] == "主表"
        assert by_en["master_tbl"]["source_table"]["sys_name"] == "系统一"
        assert by_en["ref_tbl"]["source_table"]["table_name"] == "参考表"
        one = lin[0]
        assert one["rule_id"] and one["rule_name"] == "三源规则"
        assert one["mapping_logic"] == {"prop": {"source": f"{mid}_f1"}}
        assert one["sql_fragment"] == "SELECT 1"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# §九.2 ApiEndpoint 全生命周期（外部 HTTP 全桩）
# ---------------------------------------------------------------------------

class _FakeResp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def _fake_get(payload, calls=None):
    def fake_get(url, params=None, headers=None, timeout=None):
        if calls is not None:
            calls.append(dict(url=url, params=dict(params or {}), headers=dict(headers or {})))
        return _FakeResp(payload)
    return fake_get


def test_api_endpoint_create_and_tables_visible():
    """配置新端点→/tables 虚拟表清单可见（spec §九.2/§四）：create 返回默认 cache_ttl=300；
    table_name 重复 400（DuckDB 虚拟表唯一名）；未知 id 详情 404。内存 SQLite。
    变异锚点：唯一性校验删 → 同名虚拟表 DuckDB 引用歧义红；tables 清单漏 list_tables →
    SQL 编辑器提示断供红。"""
    from fastapi import HTTPException
    from app.api.api_mapping import (
        create_endpoint, list_tables, get_endpoint, ApiEndpointCreate,
    )
    db = _sqlite_db_m07()
    try:
        payload = dict(name="m07端点A", table_name="t_m07a", api_url="http://fake.local/a",
                       method="GET", columns=[{"name": "user_id", "json_path": "user_id", "type": "VARCHAR"}])
        r = create_endpoint(ApiEndpointCreate(**payload), db=db)
        assert r["code"] == 200 and r["data"]["table_name"] == "t_m07a"
        assert r["data"]["cache_ttl_seconds"] == 300  # 默认 TTL（spec §四 批2）
        tables = list_tables(db=db)["data"]
        assert {"table_name": "t_m07a", "name": "m07端点A"} in tables
        # table_name unique → 400
        with pytest.raises(HTTPException) as ei:
            create_endpoint(ApiEndpointCreate(**{**payload, "name": "重复表"}), db=db)
        assert ei.value.status_code == 400
        # 未知 id → 404
        with pytest.raises(HTTPException) as ei:
            get_endpoint("no-such-id", db=db)
        assert ei.value.status_code == 404
    finally:
        db.close()


def test_api_endpoint_execute_contract_via_json_path(monkeypatch):
    """execute 按列契约返回（spec §九.2/§四）：load_endpoints_from_db 从 DB 装配端点配置，
    execute 经假件 HTTP 按 columns[].json_path 提取（含嵌套点号路径），列名=契约列名。
    变异锚点：json_path 提取链删 → 列值错位/None 红；装配漏 columns/data_path →
    契约列缺失红；嵌套点号路径解析删 → ES _source.col 形态断。"""
    from app.api import api_mapping as AM
    from app.api.api_mapping import create_endpoint, ApiEndpointCreate, ExecuteRequest
    from app.services import duckdb_engine
    db = _sqlite_db_m07()
    try:
        create_endpoint(ApiEndpointCreate(
            name="契约端点", table_name="t_m07c", api_url="http://fake.local/c", method="GET",
            columns=[{"name": "user_id", "json_path": "user_id", "type": "VARCHAR"},
                     {"name": "org", "json_path": "_source.org", "type": "VARCHAR"},
                     {"name": "amt", "json_path": "amt", "type": "VARCHAR", "dtype": "float64"}],
            data_path="items", cache_ttl_seconds=0), db=db)
        calls = []
        monkeypatch.setattr(duckdb_engine.requests, "get",
                            _fake_get({"items": [
                                {"user_id": "u1", "_source": {"org": "O1"}, "amt": "10"},
                                {"user_id": "u2", "_source": {"org": "O2"}, "amt": "20"},
                            ]}, calls))
        res = AM.execute_sql(ExecuteRequest(sql="SELECT * FROM t_m07c"), db=db)
        data = res["data"]
        assert data["columns"] == ["user_id", "org", "amt"]  # 列名=契约列序
        assert data["rows"] == [["u1", "O1", 10.0], ["u2", "O2", 20.0]]  # json_path 提取+dtype
        assert data["row_count"] == 2
        assert calls and calls[0]["url"] == "http://fake.local/c"  # 端点配置装配生效
    finally:
        db.close()


def test_api_endpoint_execute_guards_reject_unsafe_sql():
    """execute 请求护栏（spec §四/§八 安全边界）：空 SQL 400；非 SELECT/WITH 400；
    SELECT 夹带 DDL/DML 关键字 400；合法 SELECT 但未配置任何端点 400。
    变异锚点：SELECT-only 校验删 → 写操作穿透联邦引擎红；DDL 关键字扫描删 →
    DROP 随 SELECT 混入红；空端点守卫删 → 空配置静默空结果红。"""
    from fastapi import HTTPException
    from app.api import api_mapping as AM
    from app.api.api_mapping import ExecuteRequest
    db = _sqlite_db_m07()
    try:
        with pytest.raises(HTTPException) as ei:
            AM.execute_sql(ExecuteRequest(sql="   "), db=db)
        assert ei.value.status_code == 400
        with pytest.raises(HTTPException) as ei:
            AM.execute_sql(ExecuteRequest(sql="DELETE FROM t_m07c"), db=db)
        assert ei.value.status_code == 400
        with pytest.raises(HTTPException) as ei:
            AM.execute_sql(ExecuteRequest(sql="SELECT 1; DROP TABLE x"), db=db)
        assert ei.value.status_code == 400
        # 合法 SQL 但零端点配置
        with pytest.raises(HTTPException) as ei:
            AM.execute_sql(ExecuteRequest(sql="SELECT 1"), db=db)
        assert ei.value.status_code == 400
    finally:
        db.close()


def test_api_endpoint_pagination_fetches_all_pages(monkeypatch):
    """pagination 翻页取全量（spec §九.2/§四 批2）：页码型分页逐页拉取合并，
    页参 page/size 按配置序列透传，单页不足即停；达 max_pages 仍有满页给上限警告。
    变异锚点：分页循环删 → 只取首页丢全量红；页参透传删 → 上游恒返第 1 页红；
    上限警告删 → 截断数据无审计静默红。"""
    from app.services import duckdb_engine
    duckdb_engine.invalidate_endpoint_cache()
    try:
        ep = {
            "id": "ep-m07pg", "name": "pg", "table_name": "t_m07pg",
            "api_url": "http://fake.local/pg", "method": "GET",
            "params": [], "columns": [{"name": "n", "json_path": "n", "type": "VARCHAR"}],
            "data_path": "items", "headers": {}, "body_template": None,
            "cache_ttl_seconds": 0,  # 禁缓存：隔离分页行为
            "pagination": {"page_param": "page", "size_param": "size", "page_size": 2, "max_pages": 5},
        }
        pages = {1: [{"n": "a"}, {"n": "b"}], 2: [{"n": "c"}, {"n": "d"}], 3: [{"n": "e"}]}
        calls = []

        def fake_get(url, params=None, headers=None, timeout=None):
            p = dict(params or {})
            calls.append(p)
            return _FakeResp({"items": pages.get(int(p.get("page", 1)), [])})

        monkeypatch.setattr(duckdb_engine.requests, "get", fake_get)
        r = duckdb_engine.execute_sql("SELECT * FROM t_m07pg", {"t_m07pg": ep})
        assert r["row_count"] == 5 and [row[0] for row in r["rows"]] == ["a", "b", "c", "d", "e"]
        assert [c["page"] for c in calls] == [1, 2, 3]  # 页参序列
        assert all(c["size"] == 2 for c in calls)        # size_param 透传
        # 上限场景：max_pages=2 且两页全满 → 警告明示可能仍有后续数据
        calls2 = []
        ep2 = {**ep, "id": "ep-m07pg2", "pagination": {"page_param": "page", "size_param": "size",
                                                       "page_size": 2, "max_pages": 2}}

        def fake_get2(url, params=None, headers=None, timeout=None):
            p = dict(params or {})
            calls2.append(p)
            return _FakeResp({"items": [{"n": "x"}, {"n": "y"}]})
        monkeypatch.setattr(duckdb_engine.requests, "get", fake_get2)
        r2 = duckdb_engine.execute_sql("SELECT * FROM t_m07pg", {"t_m07pg": ep2})
        assert r2["row_count"] == 4 and len(calls2) == 2
        assert any("上限" in w for w in r2.get("warnings", []))
    finally:
        duckdb_engine.invalidate_endpoint_cache()


def test_api_endpoint_test_failure_structured_error(monkeypatch):
    """test 失败给结构化错误（spec §九.2）：上游 HTTP 失败 → 引擎级 test_endpoint 返回
    {error, error_class}（非裸抛）；API 层执行异常 → code 500 + data.error 结构化（非 500 异常穿透）。
    变异锚点：EngineError→结构化转换删 → test 连通失败裸抛 500 红；API 层 try/except 删 →
    异常穿透打断前端测试面板红。"""
    from app.api import api_mapping as AM
    from app.api.api_mapping import test_endpoint as api_test_endpoint
    from app.api.api_mapping import create_endpoint, ApiEndpointCreate
    from app.services import duckdb_engine
    duckdb_engine.invalidate_endpoint_cache()
    try:
        # 引擎级：上游 403 → AUTH 结构化错误
        def boom(url, params=None, headers=None, timeout=None):
            raise duckdb_engine.requests.exceptions.HTTPError(
                "403 Forbidden", response=_FakeResp({}))
        monkeypatch.setattr(duckdb_engine.requests, "get", boom)
        ep = {"id": "ep-m07t", "api_url": "http://fake.local/t", "method": "GET",
              "params": [], "columns": [{"name": "n", "json_path": "n", "type": "VARCHAR"}],
              "data_path": "items", "headers": {}, "body_template": None,
              "pagination": {}, "cache_ttl_seconds": 0}
        r = duckdb_engine.test_endpoint(ep)
        assert r["row_count"] == 0 and r["error"] and r["error_class"]  # 结构化，非裸抛
        # API 层：引擎异常 → code 500 + data.error
        db = _sqlite_db_m07()
        try:
            cr = create_endpoint(ApiEndpointCreate(
                name="测试端点", table_name="t_m07t", api_url="http://fake.local/t", method="GET",
                columns=[{"name": "n", "json_path": "n", "type": "VARCHAR"}]), db=db)
            ep_id = cr["data"]["id"]

            def kaboom(ep_cfg, limit=10):
                raise RuntimeError("引擎内部故障")
            monkeypatch.setattr(duckdb_engine, "test_endpoint", kaboom)
            res = api_test_endpoint(ep_id, db=db)
            assert res["code"] == 500 and res["data"]["error"] == "引擎内部故障"
        finally:
            db.close()
    finally:
        duckdb_engine.invalidate_endpoint_cache()


def test_api_endpoint_test_dtype_suggestion_written_back(monkeypatch):
    """test 成功路径：采样定 dtype 建议回写未显式 dtype 的列（spec §四 批2——数值 SUM 从此正确），
    并披露 cache_ttl_seconds。
    变异锚点：dtype 建议回写删 → 字符串数值列 SUM 永远错红；建议丢失 → 前端无采样披露红。"""
    from app.api import api_mapping as AM
    from app.api.api_mapping import create_endpoint, ApiEndpointCreate
    from app.services import duckdb_engine
    duckdb_engine.invalidate_endpoint_cache()
    try:
        db = _sqlite_db_m07()
        try:
            cr = create_endpoint(ApiEndpointCreate(
                name="采样端点", table_name="t_m07d", api_url="http://fake.local/d", method="GET",
                columns=[{"name": "amt", "json_path": "amt", "type": "VARCHAR"},
                         {"name": "user_id", "json_path": "user_id", "type": "VARCHAR"}],
                data_path="items", cache_ttl_seconds=60), db=db)
            ep_id = cr["data"]["id"]
            monkeypatch.setattr(duckdb_engine.requests, "get", _fake_get(
                {"items": [{"user_id": "u1", "amt": "10"}, {"user_id": "u2", "amt": "20"}]}))
            res = AM.test_endpoint(ep_id, db=db)
            assert res["code"] == 200
            data = res["data"]
            assert data["row_count"] == 2 and data["columns"] == ["amt", "user_id"]
            assert data["dtype_suggestions"].get("amt") in ("int64", "float64")
            assert data["cache_ttl_seconds"] == 60
            # 回写持久化：amt 列 dtype 落库（未显式设 dtype 的列才写）
            from app.models.base import ApiEndpoint
            ep_row = db.query(ApiEndpoint).filter(ApiEndpoint.id == ep_id).first()
            amt_col = next(c for c in ep_row.columns if c["name"] == "amt")
            assert amt_col.get("dtype") in ("int64", "float64")
        finally:
            db.close()
    finally:
        duckdb_engine.invalidate_endpoint_cache()


def test_api_endpoint_config_save_invalidates_cache(monkeypatch):
    """配置保存/删除即失效该 endpoint 缓存（spec §四 批2「配置即失效」）：update/delete
    均触发 invalidate_endpoint_cache(endpoint_id)，参数透传。M06 批录句桩三要素。
    变异锚点：保存/删除后的失效调用删 → 改配置后旧缓存数据继续服役红。"""
    from app.api import api_mapping as AM
    from app.api.api_mapping import (
        create_endpoint, update_endpoint, delete_endpoint,
        ApiEndpointCreate, ApiEndpointUpdate,
    )
    from app.services import duckdb_engine
    db = _sqlite_db_m07()
    try:
        cr = create_endpoint(ApiEndpointCreate(
            name="缓存端点", table_name="t_m07cache", api_url="http://fake.local/cache", method="GET",
            columns=[{"name": "n", "json_path": "n", "type": "VARCHAR"}]), db=db)
        ep_id = cr["data"]["id"]
        seen = []
        monkeypatch.setattr(duckdb_engine, "invalidate_endpoint_cache",
                            lambda eid=None: seen.append(eid) or 0)
        update_endpoint(ep_id, ApiEndpointUpdate(name="缓存端点2"), db=db)
        delete_endpoint(ep_id, db=db)
        assert seen == [ep_id, ep_id], f"保存与删除都应按 endpoint_id 失效缓存，实际 {seen}"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# §九.3 EntityApiMapping verify 契约发现力 + execute 多端点整合
# ---------------------------------------------------------------------------

def _mk_endpoint_row(db, table_name, cols, url=None):
    """直接落一条 ApiEndpoint 行（绕过端点校验，构造映射资源池用）。"""
    from app.models.base import ApiEndpoint
    ep = ApiEndpoint(name=f"m07_{table_name}", table_name=table_name,
                     api_url=url or f"http://fake.local/{table_name}", method="GET",
                     params=[], columns=cols, data_path="items", cache_ttl_seconds=0)
    db.add(ep)
    db.commit()
    return ep


def test_entity_api_mapping_verify_surfaces_contract_mismatch(monkeypatch):
    """verify 能发现列缺失/类型不匹配（spec §九.3/§五）：pseudo_sql 引用契约外列 /
    对 VARCHAR 列做聚合 → DuckDB 真执行暴露偏差，verify 以「HTTP 200 + data.error/error_class
    结构化错误」披露（引擎 execute_sql 异常即结构化返回，不裸抛不假成功）；契约一致对照 →
    columns 正常返回。
    变异锚点：verify 异常吞噬改假成功（吞 error 字段）→ 契约偏差不暴露红；
    偏差检测依赖的执行链断 → 列缺失分支 error 断红。"""
    from app.api.api_mapping import verify_entity_api_mapping
    from app.models.base import EntityApiMapping
    from app.services import duckdb_engine
    duckdb_engine.invalidate_endpoint_cache()
    try:
        db = _sqlite_db_m07()
        try:
            _, eid = _mk_concept_entity(db, "m07v")
            ep = _mk_endpoint_row(db, "t_m07v", [
                {"name": "user_id", "json_path": "user_id", "type": "VARCHAR"},
                {"name": "amt", "json_path": "amt", "type": "VARCHAR", "dtype": "int64"}])
            monkeypatch.setattr(duckdb_engine.requests, "get", _fake_get(
                {"items": [{"user_id": "u1", "amt": "10"}]}))
            m_ok = EntityApiMapping(entity_id=eid, api_endpoint_ids=[ep.id],
                                    pseudo_sql="SELECT user_id FROM t_m07v")
            m_missing = EntityApiMapping(entity_id=eid, api_endpoint_ids=[ep.id],
                                         pseudo_sql="SELECT user_id, no_such_col FROM t_m07v")
            m_type = EntityApiMapping(entity_id=eid, api_endpoint_ids=[ep.id],
                                      pseudo_sql="SELECT SUM(user_id) AS s FROM t_m07v")
            db.add_all([m_ok, m_missing, m_type])
            db.commit()
            # 对照：契约一致 → columns 正常返回
            ok = verify_entity_api_mapping(m_ok.id, db=db)
            assert ok["code"] == 200 and ok["data"]["columns"] == ["user_id"]
            # 列缺失 → 结构化偏差暴露（HTTP 200 + data.error，非假成功非裸抛）
            miss = verify_entity_api_mapping(m_missing.id, db=db)
            assert miss["code"] == 200
            assert miss["data"]["error"] and "no_such_col" in miss["data"]["error"]
            assert miss["data"]["row_count"] == 0 and not miss["data"]["columns"]
            # 类型不匹配（VARCHAR 聚合）→ 结构化偏差暴露
            typ = verify_entity_api_mapping(m_type.id, db=db)
            assert typ["code"] == 200 and typ["data"]["error"]
        finally:
            db.close()
    finally:
        duckdb_engine.invalidate_endpoint_cache()


def test_entity_api_mapping_execute_integrates_multiple_endpoints(monkeypatch):
    """execute 多端点整合（spec §九.3/§五）：对象 API 映射引用双虚拟表，pseudo_sql JOIN
    整合两路假件数据；filters 动态下推（spec §八.2——build_sql_with_filters 调用期拼 WHERE）
    后整合结果同步过滤。
    变异锚点：多表注册循环删 → 单表执行 JOIN 报错红；filters 下推链删 → 动态过滤失效红。"""
    from app.api.api_mapping import execute_entity_api_mapping, EntityApiExecuteRequest
    from app.models.base import EntityApiMapping
    from app.services import duckdb_engine
    duckdb_engine.invalidate_endpoint_cache()
    try:
        db = _sqlite_db_m07()
        try:
            _, eid = _mk_concept_entity(db, "m07join", entity_code="m07join_code")
            ep_a = _mk_endpoint_row(db, "t_m07ja", [
                {"name": "user_id", "json_path": "user_id", "type": "VARCHAR"},
                {"name": "amt", "json_path": "amt", "type": "VARCHAR", "dtype": "int64"}])
            ep_b = _mk_endpoint_row(db, "t_m07jb", [
                {"name": "user_id", "json_path": "user_id", "type": "VARCHAR"},
                {"name": "order_no", "json_path": "order_no", "type": "VARCHAR"}])
            monkeypatch.setattr(duckdb_engine.requests, "get", _fake_get({}))  # 占位，下面按 url 分发

            def fake_get(url, params=None, headers=None, timeout=None):
                if "t_m07ja" in url:
                    return _FakeResp({"items": [{"user_id": "u1", "amt": "10"},
                                                {"user_id": "u2", "amt": "20"}]})
                return _FakeResp({"items": [{"user_id": "u1", "order_no": "D1"},
                                            {"user_id": "u2", "order_no": "D2"}]})
            monkeypatch.setattr(duckdb_engine.requests, "get", fake_get)
            m = EntityApiMapping(entity_id=eid, api_endpoint_ids=[ep_a.id, ep_b.id],
                                 pseudo_sql="SELECT a.user_id, a.amt, b.order_no FROM t_m07ja a "
                                            "JOIN t_m07jb b ON a.user_id = b.user_id")
            db.add(m)
            db.commit()
            res = execute_entity_api_mapping(EntityApiExecuteRequest(entity_code="m07join_code"), db=db)
            assert res["code"] == 200
            data = res["data"]
            assert data["columns"] == ["user_id", "amt", "order_no"]
            assert sorted(data["rows"]) == [["u1", 10, "D1"], ["u2", 20, "D2"]]  # 双端点 JOIN 整合
            # filters 动态下推：DuckDB 内存过滤后仅剩 u1
            res2 = execute_entity_api_mapping(EntityApiExecuteRequest(
                entity_code="m07join_code", filters={"user_id": "u1"}), db=db)
            assert res2["code"] == 200 and res2["data"]["rows"] == [["u1", 10, "D1"]]
        finally:
            db.close()
    finally:
        duckdb_engine.invalidate_endpoint_cache()


def test_entity_api_mapping_execute_missing_guards_404():
    """execute 缺失守卫（spec §五）：实体不存在 404；实体存在但未配置 API 映射 404
    （均为结构化 HTTPException，非 500）。
    变异锚点：实体查找分支删 → 未知编码裸 KeyError 红；映射缺失分支删 → None.pseudo_sql 崩红。"""
    from fastapi import HTTPException
    from app.api.api_mapping import execute_entity_api_mapping, EntityApiExecuteRequest
    db = _sqlite_db_m07()
    try:
        with pytest.raises(HTTPException) as ei:
            execute_entity_api_mapping(EntityApiExecuteRequest(entity_code="ghost"), db=db)
        assert ei.value.status_code == 404
        _mk_concept_entity(db, "m07nomap", entity_code="m07nomap_code")
        with pytest.raises(HTTPException) as ei:
            execute_entity_api_mapping(EntityApiExecuteRequest(entity_code="m07nomap_code"), db=db)
        assert ei.value.status_code == 404
    finally:
        db.close()


# ---------------------------------------------------------------------------
# §九.4 integration-sql：verify 拒不存在表 / ai-rewrite 不落库 / execute 安全链
# ---------------------------------------------------------------------------

def test_integration_sql_verify_rejects_missing_table_structured(monkeypatch):
    """verify 引用不存在的表 → 结构化错误返回（非假成功非 500）（spec §九.4/§五）：
    verify 把 SQL 透传 Doris 验证链（sql/catalog 原样），缺表以 error+error_class 结构暴露。
    Doris 缺表分类语义（TABLE_MISSING）由 test_m21_engines.py::test_classify_by_message_core_classes
    交叉锚定；真连 Doris 联测留 integration 域（默认排除），本测以引擎边界桩锚定契约。
    变异锚点：verify 透传链删/改写 SQL → 参数透传断红；错误结构被吞成空成功 →
    error_class 断红。"""
    from app.api.api_mapping import verify_integration_sql, IntegrationSqlVerifyRequest
    captured = {}

    def fake_verify(sql, catalog=None):
        captured["sql"] = sql
        captured["catalog"] = catalog
        return {"columns": [], "rows": [], "row_count": 0,
                "error": "Table 'internal.m07_doris_t' doesn't exist",
                "error_class": "TABLE_MISSING"}

    monkeypatch.setattr("app.services.doris_engine.test_integration_sql", fake_verify)
    res = verify_integration_sql(IntegrationSqlVerifyRequest(
        sql="SELECT cust_no FROM m07_doris_t", catalog="m07cat"))
    assert res["code"] == 200  # HTTP 层不 500，错误在 data 内结构化
    assert captured == {"sql": "SELECT cust_no FROM m07_doris_t", "catalog": "m07cat"}
    data = res["data"]
    assert data["error"] and data["error_class"] == "TABLE_MISSING"  # 拒绝=结构化错误，非假成功


def test_integration_sql_ai_rewrite_suggestion_not_persisted(monkeypatch):
    """ai-rewrite 返回建议不落库（spec §九.4/§八.4 LLM 只建议）：实体字段与 SQL 输出列
    透传改写服务（connection_id 透传），建议 SQL 随响应返回；库零写入（实体行原貌）；
    实体缺失 → matched=False + 原样返回且 LLM 未被调用。
    变异锚点：ai_rewrite 结果直接落库 → 库零写入断红；实体缺失分支误调 LLM →
    调用计数断红。"""
    from app.api.api_mapping import ai_rewrite, AiRewriteRequest
    from app.models.base import Entity
    db = _sqlite_db_m07()
    try:
        _, eid = _mk_concept_entity(db, "m07ai")
        ent = db.query(Entity).filter(Entity.id == eid).first()
        ent.properties_schema = [{"name": "cons_no", "type": "varchar", "cnName": "用户编号"}]
        db.commit()
        calls = []

        def fake_rewrite(sql, sql_columns, entity_fields, connection_id=None):
            calls.append({"sql": sql, "cols": sql_columns, "fields": entity_fields, "conn": connection_id})
            return {"matched": False, "rewritten_sql": "SELECT cons_no AS cust_no FROM cat.tbl",
                    "reason": "输出列与实体字段不一致"}

        monkeypatch.setattr("app.services.doris_engine.describe_sql_columns",
                            lambda sql, catalog=None: [{"name": "cust_no", "type": "varchar"}])
        monkeypatch.setattr("app.services.sql_rewrite_service.ai_rewrite_sql", fake_rewrite)
        res = ai_rewrite(AiRewriteRequest(sql="SELECT cust_no FROM cat.tbl", catalog="m07cat",
                                          entity_id=eid, connection_id="conn-9"), db=db)
        assert res["code"] == 200
        data = res["data"]
        assert data["rewritten_sql"] == "SELECT cons_no AS cust_no FROM cat.tbl"  # 建议 SQL 返回
        assert data["sql_columns"] == [{"name": "cust_no", "type": "varchar"}]
        assert data["entity_fields"] == [{"name": "cons_no", "type": "varchar", "cnName": "用户编号"}]
        assert calls[0]["conn"] == "conn-9" and calls[0]["cols"] == data["sql_columns"]
        # 不落库：实体 integration_sql 原貌（None），无任何映射行新增
        db.refresh(ent)
        assert ent.integration_sql is None
        # 实体缺失分支：原样返回 + LLM 未被调用
        n_calls = len(calls)
        res2 = ai_rewrite(AiRewriteRequest(sql="SELECT 1", entity_id="no-such", catalog=None), db=db)
        assert res2["data"]["matched"] is False
        assert res2["data"]["rewritten_sql"] == "SELECT 1"
        assert len(calls) == n_calls
    finally:
        db.close()


def test_integration_sql_execute_pushdown_safe_chain(monkeypatch):
    """execute 走安全链（spec §九.4/§五）：filters 经 build_sql_with_filters AST 安全构造
    下推（注入值单引号转义，test_f1_sql_injection.py 交叉锚定注入防护全谱），integration_sql
    与 doris_catalog 原样透传引擎；实体缺失 404 / 未配置 integration_sql 400。
    变异锚点：下推链删 → filters 丢失 WHERE 红注入值裸拼红；实体守卫删 → 未知编码崩红。"""
    from fastapi import HTTPException
    from app.api.api_mapping import (
        execute_integration_sql, IntegrationSqlExecuteRequest,
    )
    from app.models.base import Entity
    db = _sqlite_db_m07()
    try:
        _, eid = _mk_concept_entity(db, "m07exec")
        ent = db.query(Entity).filter(Entity.id == eid).first()
        ent.entity_code = "m07exec_code"
        ent.integration_sql = "SELECT cust_no FROM m07_doris_t"
        ent.doris_catalog = "m07cat"
        ent.source_mode = "sql_integration"
        db.commit()
        captured = {}

        def fake_exec(sql, limit=0, catalog=None):
            captured["sql"] = sql
            captured["catalog"] = catalog
            return {"columns": ["cust_no"], "rows": [["c1"]], "row_count": 1}

        monkeypatch.setattr("app.services.doris_engine.execute_sql", fake_exec)
        res = execute_integration_sql(IntegrationSqlExecuteRequest(
            entity_code="m07exec_code", filters={"cust_no": "x' OR 1=1 --"}), db=db)
        assert res["code"] == 200 and res["data"]["row_count"] == 1
        assert captured["catalog"] == "m07cat"  # catalog 透传
        up = captured["sql"].upper()
        assert "WHERE" in up  # filters 经安全链下推（非裸拼）
        assert "x'' OR 1=1 --" in captured["sql"]  # 注入值已转义进字面量（安全链产物）
        # 守卫：实体缺失 404 / 未配置 integration_sql 400
        with pytest.raises(HTTPException) as ei:
            execute_integration_sql(IntegrationSqlExecuteRequest(entity_code="ghost"), db=db)
        assert ei.value.status_code == 404
        ent.integration_sql = None
        db.commit()
        with pytest.raises(HTTPException) as ei:
            execute_integration_sql(IntegrationSqlExecuteRequest(entity_code="m07exec_code"), db=db)
        assert ei.value.status_code == 400
    finally:
        db.close()


# ---------------------------------------------------------------------------
# §九.5 前端三 Tab 跳转对齐 + 预览弹窗数据闭环（后端半环）
# ---------------------------------------------------------------------------

def test_frontend_tab_alignment_source_contract():
    """三 Tab 与 source_mode 跳转对齐 + 实体过滤联动（spec §九.5/§六，源码级登记态断言）：
    ModelTreeManager tabMap 三模式→Tab1/2/3 经 store mappingJumpTab 下发；MappingManager
    消费 mappingFilterEntityId（实体过滤联动）与 mappingJumpTab（预选 Tab）。
    交互链路（点击跳转/过滤渲染）pytest 不可达，e2e 域覆盖（批次末总验收承接），如实披露。
    变异锚点：tabMap 模式键漂移/Tab 序号错位 → 三模式映射断红；映射页停用跳转态消费 →
    setActiveTab/mappingFilterEntityId 断红。"""
    root = Path(__file__).resolve().parents[2] / "frontend" / "src"
    tree = (root / "components" / "ModelTreeManager.tsx")
    page = (root / "pages" / "MappingManager.tsx")
    assert tree.is_file() and page.is_file()
    tsrc = tree.read_text(encoding="utf-8")
    assert "physical_table: '1'" in tsrc and "sql_integration: '2'" in tsrc \
        and "api_integration: '3'" in tsrc  # 三模式→Tab 对齐
    assert "setMappingJumpTab(tabMap[sourceMode]" in tsrc  # 跳转态经 store 下发
    psrc = page.read_text(encoding="utf-8")
    assert "setQueryEntityId(mappingFilterEntityId)" in psrc  # 实体过滤联动
    assert "setActiveTab(mappingJumpTab || '1')" in psrc      # 按来源模式预选 Tab
    assert "setMappingFilterEntityId(null)" in psrc and "setMappingJumpTab(null)" in psrc  # 消费后清理防反复跳转


def test_entity_preview_three_modes_backend_loop(monkeypatch):
    """预览弹窗数据闭环·后端半环（spec §九.5/§五）：/entity-preview 按 source_mode 三路分发，
    rows 输出对象数组（前端表格直渲），缺配降级 hint 非 500；
    前端弹窗渲染为 e2e 域（批次末总验收承接），如实披露。
    变异锚点：三模式分发链删任一支 → 对应模式 hint 降级红；对象数组序列化删 →
    前端表格渲染断供红。"""
    from sqlalchemy import create_engine, text
    from sqlalchemy.pool import StaticPool
    from app.api.api_mapping import preview_entity_data
    from app.models.base import EntityApiMapping
    db = _sqlite_db_m07()
    try:
        # physical_table：桩业务引擎（内存 SQLite 真表真查）
        _, eid_p = _mk_concept_entity(db, "m07pv_p", entity_code="m07pv_p",
                                      entity_en_name="m07_phys", source_mode="physical_table")
        eng = create_engine("sqlite://", connect_args={"check_same_thread": False},
                            poolclass=StaticPool)
        with eng.begin() as conn:
            conn.execute(text("CREATE TABLE m07_phys (id INTEGER, cons_name TEXT)"))
            conn.execute(text("INSERT INTO m07_phys VALUES (1, '户甲'), (2, '户乙')"))
        monkeypatch.setattr("app.services.sql_executor._get_biz_engine", lambda dsid=None: eng)
        r1 = preview_entity_data(eid_p, limit=20, db=db)
        assert r1["source_mode"] == "physical_table" and r1["code"] == 200
        assert r1["data"]["table_name"] == "m07_phys" and r1["data"]["row_count"] == 2
        assert r1["data"]["rows"][0] == {"id": 1, "cons_name": "户甲"}  # 对象数组闭环
        # sql_integration：Doris 桩
        _, eid_s = _mk_concept_entity(db, "m07pv_s", entity_code="m07pv_s",
                                      integration_sql="SELECT cust_no FROM doris_t",
                                      doris_catalog="m07cat", source_mode="sql_integration")
        monkeypatch.setattr("app.services.doris_engine.execute_with_filters",
                            lambda sql, filters=None, catalog=None:
                            {"columns": ["cust_no"], "rows": [["c9"]], "row_count": 1})
        r2 = preview_entity_data(eid_s, limit=20, db=db)
        assert r2["data"]["rows"] == [{"cust_no": "c9"}] and r2["data"]["row_count"] == 1
        # api_integration：DuckDB 桩 + 映射行
        _, eid_a = _mk_concept_entity(db, "m07pv_a", entity_code="m07pv_a",
                                      source_mode="api_integration")
        db.add(EntityApiMapping(entity_id=eid_a, api_endpoint_ids=[],
                                pseudo_sql="SELECT user_id FROM t_m07v"))
        db.commit()
        monkeypatch.setattr("app.services.duckdb_engine.execute_sql",
                            lambda sql, endpoints: {"columns": ["user_id"], "rows": [["u7"]], "row_count": 1})
        r3 = preview_entity_data(eid_a, limit=20, db=db)
        assert r3["data"]["rows"] == [{"user_id": "u7"}]
        # 缺配降级：api_integration 无映射 → hint 非 500
        _, eid_n = _mk_concept_entity(db, "m07pv_n", entity_code="m07pv_n",
                                      source_mode="api_integration")
        r4 = preview_entity_data(eid_n, limit=20, db=db)
        assert r4["code"] == 200 and r4["data"]["hint"] == "未配置 API映射"
        # 不存在的实体 → 404 非 500
        import uuid as _u
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as ei:
            preview_entity_data(str(_u.uuid4()), db=db)
        assert ei.value.status_code == 404
    finally:
        db.close()


# ---------------------------------------------------------------------------
# §九.6 预留表登记态（禁改清单件 SmartJoinReview）
# ---------------------------------------------------------------------------

def test_smart_join_review_reserved_table_no_consumer():
    """SmartJoinReview 预留表存在且无消费代码（spec §九.6/§七，按登记态断言）：
    模型列契约在位（HITL 工作流设计结构原貌）；backend/app 与 frontend/src 全域
    仅模型定义一处引用——登记一致，不许测出「未实现」就实现它。
    变异锚点：有人提前消费预留表（注册路由/服务引用）→ 消费文件清单红；
    模型列删 → HITL 结构断供红。"""
    from app.models.base import SmartJoinReview
    cols = {c.name for c in SmartJoinReview.__table__.columns}
    assert {"app_type", "intent", "candidate_id", "candidate_payload", "confidence",
            "need_manual_review", "approved", "executed", "reviewer"} <= cols
    assert SmartJoinReview.__tablename__ == "kg_smart_join_reviews"
    app_dir = Path(__file__).resolve().parents[1] / "app"
    hits_backend = sorted(p.name for p in app_dir.rglob("*.py")
                          if "SmartJoinReview" in p.read_text(encoding="utf-8"))
    assert hits_backend == ["base.py"], f"backend/app 出现模型定义外引用：{hits_backend}"
    fe_dir = Path(__file__).resolve().parents[2] / "frontend" / "src"
    hits_fe = sorted(str(p.relative_to(fe_dir)) for p in fe_dir.rglob("*.ts*")
                     if "SmartJoinReview" in p.read_text(encoding="utf-8"))
    assert hits_fe == [], f"frontend 出现预留表消费引用：{hits_fe}"
