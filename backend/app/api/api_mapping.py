# -*- coding: utf-8 -*-
"""多源API映射 HTTP 接口

提供端点：
- GET    /api-endpoints              列表(可按 entity_id 过滤)
- POST   /api-endpoints              新增
- GET    /api-endpoints/{id}         详情
- PUT    /api-endpoints/{id}         修改
- DELETE /api-endpoints/{id}         删除
- POST   /api-endpoints/{id}/test    单端点测试(无参,返前N行)
- POST   /api-endpoints/execute      执行联邦SQL {sql} -> {columns,rows,row_count}
- GET    /api-endpoints/tables       列出已注册虚拟表名(SQL编辑器提示)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.base import ApiEndpoint, EntityApiMapping
from app.services import duckdb_engine

router = APIRouter()


# --------------------------------------------------------------------------- #
# 请求体
# --------------------------------------------------------------------------- #

class ApiEndpointCreate(BaseModel):
    name: str
    table_name: str
    entity_id: Optional[str] = None
    api_url: str
    method: str = "POST"
    params: Optional[List[Dict[str, Any]]] = None    # [{"name","column","map_to"}]
    columns: List[Dict[str, Any]]                    # [{"name","json_path","type"}]
    data_path: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    description: Optional[str] = None


class ApiEndpointUpdate(BaseModel):
    name: Optional[str] = None
    table_name: Optional[str] = None
    entity_id: Optional[str] = None
    api_url: Optional[str] = None
    method: Optional[str] = None
    params: Optional[List[Dict[str, Any]]] = None
    columns: Optional[List[Dict[str, Any]]] = None
    data_path: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    description: Optional[str] = None


class ExecuteRequest(BaseModel):
    sql: str


# --------------------------------------------------------------------------- #
# 序列化
# --------------------------------------------------------------------------- #

def _serialize(ep: ApiEndpoint) -> Dict[str, Any]:
    return {
        "id": ep.id, "name": ep.name, "table_name": ep.table_name,
        "entity_id": ep.entity_id, "api_url": ep.api_url, "method": ep.method,
        "params": ep.params or [], "columns": ep.columns or [],
        "data_path": ep.data_path, "headers": ep.headers or {},
        "description": ep.description, "created_at": ep.created_at.isoformat() if ep.created_at else None,
    }


# --------------------------------------------------------------------------- #
# CRUD
# --------------------------------------------------------------------------- #

@router.get("/api-endpoints")
def list_endpoints(entity_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(ApiEndpoint)
    if entity_id:
        q = q.filter(ApiEndpoint.entity_id == entity_id)
    items = q.order_by(ApiEndpoint.created_at.desc()).all()
    return {"code": 200, "data": [_serialize(e) for e in items], "count": len(items)}


@router.post("/api-endpoints")
def create_endpoint(payload: ApiEndpointCreate, db: Session = Depends(get_db)):
    # table_name 唯一性校验
    if db.query(ApiEndpoint).filter(ApiEndpoint.table_name == payload.table_name).first():
        raise HTTPException(status_code=400, detail=f"表名 {payload.table_name} 已存在")
    ep = ApiEndpoint(
        name=payload.name, table_name=payload.table_name, entity_id=payload.entity_id,
        api_url=payload.api_url, method=payload.method, params=payload.params,
        columns=payload.columns, data_path=payload.data_path, headers=payload.headers,
        description=payload.description,
    )
    db.add(ep)
    db.commit()
    db.refresh(ep)
    return {"code": 200, "data": _serialize(ep)}


@router.get("/api-endpoints/tables")
def list_tables(db: Session = Depends(get_db)):
    """列出已配置的虚拟表名（供 SQL 编辑器提示，必须在 {ep_id} 路由前避免被匹配）"""
    items = db.query(ApiEndpoint.table_name, ApiEndpoint.name).order_by(ApiEndpoint.table_name).all()
    return {"code": 200, "data": [{"table_name": t, "name": n} for t, n in items]}


@router.post("/api-endpoints/execute")
def execute_sql(payload: ExecuteRequest, db: Session = Depends(get_db)):
    """执行多源API联邦SQL，WHERE/JOIN条件自动下推到API参数（固定路径，必须在 {ep_id} 路由前）"""
    sql = (payload.sql or "").strip()
    if not sql:
        raise HTTPException(status_code=400, detail="SQL不能为空")
    low = sql.lower()
    if not (low.startswith("select") or low.startswith("with")):
        raise HTTPException(status_code=400, detail="只允许 SELECT/WITH 查询")
    if any(kw in low for kw in ["insert ", "update ", "delete ", "drop ", "alter ", "create "]):
        raise HTTPException(status_code=400, detail="禁止 DDL/DML")
    endpoints = duckdb_engine.load_endpoints_from_db(db)
    if not endpoints:
        raise HTTPException(status_code=400, detail="尚未配置任何API端点")
    try:
        result = duckdb_engine.execute_sql(sql, endpoints)
        return {"code": 200, "data": result}
    except Exception as e:
        return {"code": 500, "data": {"error": str(e), "columns": [], "rows": [], "row_count": 0}}


@router.get("/api-endpoints/{ep_id}")
def get_endpoint(ep_id: str, db: Session = Depends(get_db)):
    ep = db.query(ApiEndpoint).filter(ApiEndpoint.id == ep_id).first()
    if not ep:
        raise HTTPException(status_code=404, detail="端点不存在")
    return {"code": 200, "data": _serialize(ep)}


@router.put("/api-endpoints/{ep_id}")
def update_endpoint(ep_id: str, payload: ApiEndpointUpdate, db: Session = Depends(get_db)):
    ep = db.query(ApiEndpoint).filter(ApiEndpoint.id == ep_id).first()
    if not ep:
        raise HTTPException(status_code=404, detail="端点不存在")
    data = payload.dict(exclude_unset=True)
    # table_name 唯一性校验
    if "table_name" in data and data["table_name"] != ep.table_name:
        if db.query(ApiEndpoint).filter(ApiEndpoint.table_name == data["table_name"]).first():
            raise HTTPException(status_code=400, detail=f"表名 {data['table_name']} 已存在")
    for k, v in data.items():
        setattr(ep, k, v)
    db.commit()
    db.refresh(ep)
    return {"code": 200, "data": _serialize(ep)}


@router.delete("/api-endpoints/{ep_id}")
def delete_endpoint(ep_id: str, db: Session = Depends(get_db)):
    ep = db.query(ApiEndpoint).filter(ApiEndpoint.id == ep_id).first()
    if not ep:
        raise HTTPException(status_code=404, detail="端点不存在")
    db.delete(ep)
    db.commit()
    return {"code": 200, "data": {"deleted": ep_id}}


# --------------------------------------------------------------------------- #
# 测试 + 执行
# --------------------------------------------------------------------------- #

@router.post("/api-endpoints/{ep_id}/test")
def test_endpoint(ep_id: str, db: Session = Depends(get_db)):
    ep = db.query(ApiEndpoint).filter(ApiEndpoint.id == ep_id).first()
    if not ep:
        raise HTTPException(status_code=404, detail="端点不存在")
    try:
        result = duckdb_engine.test_endpoint(_serialize(ep))
        return {"code": 200, "data": result}
    except Exception as e:
        return {"code": 500, "data": {"error": str(e)}}


# --------------------------------------------------------------------------- #
# 对象API映射（EntityApiMapping，对象层面整合多源API）
# --------------------------------------------------------------------------- #

class EntityApiMappingCreate(BaseModel):
    name: Optional[str] = None
    entity_id: str
    api_endpoint_ids: List[str]
    field_mappings: Optional[dict] = None
    pseudo_sql: str
    description: Optional[str] = None


class EntityApiMappingUpdate(BaseModel):
    name: Optional[str] = None
    entity_id: Optional[str] = None
    api_endpoint_ids: Optional[List[str]] = None
    field_mappings: Optional[dict] = None
    pseudo_sql: Optional[str] = None
    description: Optional[str] = None


class EntityApiExecuteRequest(BaseModel):
    entity_code: str
    filters: Optional[Dict[str, Any]] = None


def _serialize_mapping(m: EntityApiMapping) -> Dict[str, Any]:
    return {
        "id": m.id, "name": m.name, "entity_id": m.entity_id,
        "api_endpoint_ids": m.api_endpoint_ids or [],
        "field_mappings": m.field_mappings or {}, "pseudo_sql": m.pseudo_sql,
        "description": m.description,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("/entity-api-mappings")
def list_entity_api_mappings(entity_id: Optional[str] = Query(None), db: Session = Depends(get_db)):
    q = db.query(EntityApiMapping)
    if entity_id:
        q = q.filter(EntityApiMapping.entity_id == entity_id)
    items = q.order_by(EntityApiMapping.created_at.desc()).all()
    return {"code": 200, "data": [_serialize_mapping(m) for m in items], "count": len(items)}


@router.post("/entity-api-mappings")
def create_entity_api_mapping(payload: EntityApiMappingCreate, db: Session = Depends(get_db)):
    existing = db.query(EntityApiMapping).filter(EntityApiMapping.entity_id == payload.entity_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="该对象已存在API映射，请编辑而非新增")
    m = EntityApiMapping(
        name=payload.name, entity_id=payload.entity_id, api_endpoint_ids=payload.api_endpoint_ids,
        field_mappings=payload.field_mappings, pseudo_sql=payload.pseudo_sql, description=payload.description,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return {"code": 200, "data": _serialize_mapping(m)}


@router.post("/entity-api-mappings/execute")
def execute_entity_api_mapping(payload: EntityApiExecuteRequest, db: Session = Depends(get_db)):
    """执行对象API映射（带 filters 下推，LLM 用）。固定路径，在 {m_id} 路由前。"""
    from app.models.base import Entity
    ent = db.query(Entity).filter(Entity.entity_code == payload.entity_code).first()
    if not ent:
        raise HTTPException(status_code=404, detail=f"对象 {payload.entity_code} 不存在")
    m = db.query(EntityApiMapping).filter(EntityApiMapping.entity_id == ent.id).first()
    if not m:
        raise HTTPException(status_code=404, detail=f"对象 {payload.entity_code} 未配置API映射")
    sql = duckdb_engine.build_sql_with_filters(m.pseudo_sql, payload.filters or {})
    endpoints = duckdb_engine.load_endpoints_from_db(db)
    try:
        result = duckdb_engine.execute_sql(sql, endpoints)
        return {"code": 200, "data": result}
    except Exception as e:
        return {"code": 500, "data": {"error": str(e), "columns": [], "rows": [], "row_count": 0}}


@router.get("/entity-api-mappings/{m_id}")
def get_entity_api_mapping(m_id: str, db: Session = Depends(get_db)):
    m = db.query(EntityApiMapping).filter(EntityApiMapping.id == m_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="对象API映射不存在")
    return {"code": 200, "data": _serialize_mapping(m)}


@router.put("/entity-api-mappings/{m_id}")
def update_entity_api_mapping(m_id: str, payload: EntityApiMappingUpdate, db: Session = Depends(get_db)):
    m = db.query(EntityApiMapping).filter(EntityApiMapping.id == m_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="对象API映射不存在")
    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return {"code": 200, "data": _serialize_mapping(m)}


@router.delete("/entity-api-mappings/{m_id}")
def delete_entity_api_mapping(m_id: str, db: Session = Depends(get_db)):
    m = db.query(EntityApiMapping).filter(EntityApiMapping.id == m_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="对象API映射不存在")
    db.delete(m)
    db.commit()
    return {"code": 200, "data": {"deleted": m_id}}


@router.post("/entity-api-mappings/{m_id}/verify")
def verify_entity_api_mapping(m_id: str, db: Session = Depends(get_db)):
    """验证 pseudo_sql 执行（无 filters）"""
    m = db.query(EntityApiMapping).filter(EntityApiMapping.id == m_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="对象API映射不存在")
    endpoints = duckdb_engine.load_endpoints_from_db(db)
    try:
        result = duckdb_engine.execute_sql(m.pseudo_sql, endpoints)
        return {"code": 200, "data": result}
    except Exception as e:
        return {"code": 500, "data": {"error": str(e), "columns": [], "rows": [], "row_count": 0}}


# --------------------------------------------------------------------------- #
# integration_sql 执行（sql_integration 模式，Doris 引擎）
# --------------------------------------------------------------------------- #

class IntegrationSqlVerifyRequest(BaseModel):
    sql: str
    catalog: Optional[str] = None


class IntegrationSqlExecuteRequest(BaseModel):
    entity_code: str
    filters: Optional[Dict[str, Any]] = None


@router.post("/integration-sql/verify")
def verify_integration_sql(payload: IntegrationSqlVerifyRequest):
    """验证 integration_sql 执行（Doris 引擎，限100行）"""
    from app.services.doris_engine import test_integration_sql
    result = test_integration_sql(payload.sql, payload.catalog)
    return {"code": 200, "data": result}


class AiRewriteRequest(BaseModel):
    sql: str
    catalog: Optional[str] = None
    entity_id: str
    connection_id: Optional[str] = None


@router.post("/integration-sql/ai-rewrite")
def ai_rewrite(payload: AiRewriteRequest, db: Session = Depends(get_db)):
    """AI 校验 SQL 输出字段与实体字段是否匹配，不匹配则改写

    流程：执行 SQL 取输出列(名+类型) -> 取实体 properties_schema -> 调 LLM 校验改写
    可通过 connection_id 指定用哪个 LLM 连接（让用户选模型），不传则用默认 chat 连接
    """
    from app.models.base import Entity
    from app.services.doris_engine import describe_sql_columns
    from app.services.sql_rewrite_service import ai_rewrite_sql

    entity = db.query(Entity).filter(Entity.id == payload.entity_id).first()
    if not entity:
        return {"code": 200, "data": {"matched": False, "error": f"实体 {payload.entity_id} 不存在", "rewritten_sql": payload.sql}}
    entity_fields = [
        {"name": f.get("name"), "type": f.get("type"), "cnName": f.get("cnName")}
        for f in (entity.properties_schema or [])
    ]
    sql_columns = describe_sql_columns(payload.sql, payload.catalog)
    if not sql_columns:
        return {"code": 200, "data": {
            "matched": False,
            "error": "SQL 执行失败，无法获取输出列（检查 SQL 语法与 Catalog）",
            "rewritten_sql": payload.sql,
            "sql_columns": [],
            "entity_fields": entity_fields,
        }}
    result = ai_rewrite_sql(payload.sql, sql_columns, entity_fields, payload.connection_id)
    result["sql_columns"] = sql_columns
    result["entity_fields"] = entity_fields
    return {"code": 200, "data": result}


@router.post("/integration-sql/execute")
def execute_integration_sql(payload: IntegrationSqlExecuteRequest, db: Session = Depends(get_db)):
    """执行对象的 integration_sql（带 filters 下推，Doris 引擎）"""
    from app.models.base import Entity
    from app.services.doris_engine import execute_with_filters
    ent = db.query(Entity).filter(Entity.entity_code == payload.entity_code).first()
    if not ent:
        raise HTTPException(status_code=404, detail=f"对象 {payload.entity_code} 不存在")
    if not ent.integration_sql:
        raise HTTPException(status_code=400, detail=f"对象 {payload.entity_code} 未配置 integration_sql")
    result = execute_with_filters(ent.integration_sql, payload.filters, ent.doris_catalog)
    return {"code": 200, "data": result}


# --------------------------------------------------------------------------- #
# 统一对象取数接口（第一阶段，按 source_mode 分发三引擎）
# --------------------------------------------------------------------------- #

class EntityDataRequest(BaseModel):
    filters: Optional[Dict[str, Any]] = None


@router.post("/entity-data/{entity_code}")
def get_entity_data(entity_code: str, payload: EntityDataRequest, db: Session = Depends(get_db)):
    """统一对象取数接口（第一阶段，按 source_mode 分发三引擎）

    - physical_table  -> MySQL 直接查 entity_en_name
    - sql_integration -> Doris 执行 integration_sql（build_sql_with_filters 下推）
    - api_integration -> DuckDB 执行 pseudo_sql（build_sql_with_filters 下推）
    """
    from app.models.base import Entity, EntityApiMapping
    from sqlalchemy import text
    from app.services.doris_engine import execute_with_filters as doris_exec
    from app.services.duckdb_engine import execute_sql as duckdb_exec, load_endpoints_from_db, build_sql_with_filters

    ent = db.query(Entity).filter(Entity.entity_code == entity_code).first()
    if not ent:
        raise HTTPException(status_code=404, detail=f"对象 {entity_code} 不存在")
    source_mode = ent.source_mode or "physical_table"
    filters = payload.filters or {}

    if source_mode == "physical_table":
        # PostgreSQL: SELECT * FROM "entity_en_name" WHERE filters LIMIT 500
        # 实体业务数据已迁 PG，走业务引擎（DataSourceConfig 默认源，db_type=postgresql）
        from app.services.sql_executor import _get_biz_engine
        table = ent.entity_en_name or entity_code
        sql = f'SELECT * FROM "{table}"'
        if filters:
            where = " AND ".join(f'"{k}"=\'{v}\'' for k, v in filters.items())
            sql += f" WHERE {where}"
        sql += " LIMIT 500"
        try:
            _eng = _get_biz_engine()
            with _eng.connect() as _conn:
                rows = _conn.execute(text(sql)).mappings().all()
            columns = list(rows[0].keys()) if rows else []
            result = {"columns": columns, "rows": [[(v.isoformat() if hasattr(v, 'isoformat') else v) for v in r.values()] for r in rows], "row_count": len(rows)}
        except Exception as e:
            result = {"columns": [], "rows": [], "row_count": 0, "error": str(e)}

    elif source_mode == "sql_integration":
        # Doris: integration_sql + filters 下推
        if not ent.integration_sql:
            raise HTTPException(status_code=400, detail=f"对象 {entity_code} 未配置 integration_sql")
        result = doris_exec(ent.integration_sql, filters, ent.doris_catalog)

    elif source_mode == "api_integration":
        # DuckDB: pseudo_sql + filters 下推
        m = db.query(EntityApiMapping).filter(EntityApiMapping.entity_id == ent.id).first()
        if not m:
            raise HTTPException(status_code=400, detail=f"对象 {entity_code} 未配置 API映射")
        sql = build_sql_with_filters(m.pseudo_sql, filters)
        endpoints = load_endpoints_from_db(db)
        result = duckdb_exec(sql, endpoints)

    else:
        raise HTTPException(status_code=400, detail=f"未知 source_mode: {source_mode}")

    return {"code": 200, "data": result, "source_mode": source_mode}


@router.get("/entity-preview/{entity_id}")
def preview_entity_data(entity_id: str, limit: int = 20, db: Session = Depends(get_db)):
    """实体数据预览（前端 EntityDetailCard / ModelTreeManager 统一消费）

    按 source_mode 路由数据源：
      - physical_table  -> PostgreSQL（业务引擎，实体业务数据已迁 PG）
      - api_integration  -> DuckDB + ApiEndpoint（PS 模块走 ES _search API）
      - sql_integration  -> Doris（integration_sql）
    返回 {rows:[对象], table_name, row_count, hint?}，rows 为对象数组便于前端表格渲染。
    """
    from app.models.base import Entity, EntityApiMapping
    from sqlalchemy import text
    from app.services.sql_executor import _get_biz_engine
    from app.services.doris_engine import execute_with_filters as doris_exec
    from app.services.duckdb_engine import execute_sql as duckdb_exec, load_endpoints_from_db, build_sql_with_filters

    ent = db.query(Entity).filter(Entity.id == entity_id).first()
    if not ent:
        raise HTTPException(status_code=404, detail=f"实体 {entity_id} 不存在")
    source_mode = ent.source_mode or "physical_table"
    table = ent.entity_en_name or ent.entity_code
    out: dict = {"rows": [], "table_name": table, "row_count": 0, "hint": None}

    def _ser(v):
        if hasattr(v, "isoformat"):
            return v.isoformat()
        return v

    try:
        if source_mode == "physical_table":
            # PostgreSQL: SELECT * FROM "table" LIMIT n
            sql = f'SELECT * FROM "{table}" LIMIT {limit}'
            eng = _get_biz_engine()
            with eng.connect() as conn:
                rows = conn.execute(text(sql)).mappings().all()
            obj_rows = [{k: _ser(v) for k, v in r.items()} for r in rows]
            out["rows"] = obj_rows
            out["row_count"] = len(obj_rows)
            if not obj_rows:
                out["hint"] = "该表无数据"

        elif source_mode == "api_integration":
            # DuckDB + ApiEndpoint（PS 模块 -> ES _search）
            m = db.query(EntityApiMapping).filter(EntityApiMapping.entity_id == ent.id).first()
            if not m:
                out["hint"] = "未配置 API映射"
            else:
                sql = build_sql_with_filters(m.pseudo_sql, {})
                endpoints = load_endpoints_from_db(db)
                result = duckdb_exec(sql, endpoints)
                cols = result.get("columns", [])
                rows2d = result.get("rows", [])
                obj_rows = [dict(zip(cols, [_ser(v) for v in r])) for r in rows2d[:limit]]
                out["rows"] = obj_rows
                out["row_count"] = len(obj_rows)
                if not obj_rows:
                    out["hint"] = "API 无数据"

        elif source_mode == "sql_integration":
            # Doris: integration_sql
            if not ent.integration_sql:
                out["hint"] = "未配置 integration_sql"
            else:
                result = doris_exec(ent.integration_sql, {}, ent.doris_catalog)
                cols = result.get("columns", [])
                rows2d = result.get("rows", [])
                obj_rows = [dict(zip(cols, [_ser(v) for v in r])) for r in rows2d[:limit]]
                out["rows"] = obj_rows
                out["row_count"] = len(obj_rows)
        else:
            out["hint"] = f"未知 source_mode: {source_mode}"
    except Exception as e:
        out["hint"] = f"预览失败: {e}"

    return {"code": 200, "data": out, "source_mode": source_mode}
