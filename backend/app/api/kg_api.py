"""知识图谱 API - 把图谱查询函数开放成 HTTP 端点，供 kg_api @tool 调用。

安全：数据库连接只在后端，LLM 通过 kg_api @tool 发 HTTP 请求，看不到连接串。
复用：前端/外部系统也能调这些 API。
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/kg", tags=["kg-api"])


# ---------------------------------------------------------------------------
# 请求模型
# ---------------------------------------------------------------------------

class ValidateL2Request(BaseModel):
    l2_name: str
    l2_id: str = ""


class ValidateAttrsRequest(BaseModel):
    entity_code: str
    attributes: List[Dict[str, Any]] = []


class ValidateSafeSqlRequest(BaseModel):
    sql: str


class ExecuteSqlRequest(BaseModel):
    sql: str


# ---------------------------------------------------------------------------
# 端点
# ---------------------------------------------------------------------------

@router.get("/fetch_l1_l2_tree")
def fetch_l1_l2_tree():
    """获取 L1-L2 业务域层级树"""
    from app.services.skill_injections import build_fetch_l1_l2_tree
    fn = build_fetch_l1_l2_tree()
    if not fn:
        raise HTTPException(500, "L1-L2 树查询函数不可用")
    return fn()


@router.post("/validate_l2")
def validate_l2(req: ValidateL2Request):
    """校验 L2 的 l2_id，按 l2_name 反查真实 UUID"""
    from app.core.database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        rows = db.execute(text("SELECT id, name FROM kg_concepts WHERE level = 2")).fetchall()
        name_to_id = {}
        id_to_name = {}
        for r in rows:
            rid = str(r[0])
            rname = (r[1] or "").strip()
            if rid:
                id_to_name[rid] = rname
            if rname and rname not in name_to_id:
                name_to_id[rname] = rid
    finally:
        db.close()

    l2_name = (req.l2_name or "").strip()
    l2_id_raw = (req.l2_id or "").strip()

    if l2_id_raw and l2_id_raw in id_to_name:
        if not l2_name:
            l2_name = id_to_name[l2_id_raw]
        return {"l2_name": l2_name, "l2_id": l2_id_raw, "id_fixed": False, "valid": True}

    if l2_name and l2_name in name_to_id:
        real_id = name_to_id[l2_name]
        if real_id:
            return {"l2_name": l2_name, "l2_id": real_id, "id_fixed": True, "valid": True}

    return {"l2_name": l2_name, "l2_id": l2_id_raw, "id_fixed": False, "valid": False}


@router.get("/fetch_subgraph/{l2_id}")
def fetch_subgraph(l2_id: str):
    """获取 L2 子图（L2X 实体+属性、跨链 L3/L4->L4X）"""
    from app.services.skill_injections import build_fetch_subgraph_by_l2
    fn = build_fetch_subgraph_by_l2()
    if not fn:
        raise HTTPException(500, "子图查询函数不可用")
    return fn(l2_id)


@router.post("/validate_attributes")
def validate_attributes(req: ValidateAttrsRequest):
    """校验属性 code，按 attribute_name 回填真实 code"""
    from app.core.database import SessionLocal
    from sqlalchemy import text
    import json

    db = SessionLocal()
    try:
        row = db.execute(text(
            "SELECT properties_schema FROM kg_entities WHERE entity_code = :code LIMIT 1"
        ), {"code": req.entity_code}).fetchone()
    finally:
        db.close()

    if not row:
        return {"entity_code": req.entity_code, "attributes": req.attributes, "fixed_count": 0}

    # 解析 properties_schema
    props = row[0]
    if isinstance(props, str):
        try:
            props = json.loads(props)
        except Exception:
            props = []
    real_attrs = []
    if isinstance(props, list):
        for p in props:
            if isinstance(p, dict):
                code = p.get("code") or p.get("attribute_code") or p.get("field") or ""
                name = p.get("name") or p.get("attribute_name") or p.get("cnName") or p.get("label") or ""
                if code or name:
                    real_attrs.append({"attribute_code": str(code), "attribute_name": str(name)})

    real_by_code = {a["attribute_code"].lower(): a for a in real_attrs if a.get("attribute_code")}
    real_by_name = {a["attribute_name"]: a for a in real_attrs if a.get("attribute_name")}

    validated = []
    fixed = 0
    for la in (req.attributes or []):
        llm_code = str(la.get("attribute_code") or "").strip()
        llm_name = str(la.get("attribute_name") or "").strip()
        matched = None
        if llm_code and llm_code.lower() in real_by_code:
            matched = real_by_code[llm_code.lower()]
        elif llm_name and llm_name in real_by_name:
            matched = real_by_name[llm_name]
        elif llm_name:
            for rname, ra in real_by_name.items():
                if llm_name in rname or rname in llm_name:
                    matched = ra
                    break
        if matched:
            validated.append({
                "attribute_code": matched["attribute_code"],
                "attribute_name": matched["attribute_name"],
            })
            if llm_code and llm_code.lower() != matched["attribute_code"].lower():
                fixed += 1
        else:
            validated.append(la)
    return {"entity_code": req.entity_code, "attributes": validated, "fixed_count": fixed}


@router.get("/fetch_join_expr/{source_entity}/{target_entity}")
def fetch_join_expr(source_entity: str, target_entity: str):
    """查两个实体表之间的 JOIN 关联字段"""
    from app.services.skill_runnable import _build_fetch_join_expr_fn
    fn = _build_fetch_join_expr_fn()
    if not fn:
        # fallback
        return {"join_on": f"{source_entity}.cust_id = {target_entity}.cust_id", "source_entity": source_entity, "target_entity": target_entity}
    join_on = fn(source_entity, target_entity)
    if not join_on:
        join_on = f"{source_entity}.cust_id = {target_entity}.cust_id"
    return {"join_on": join_on, "source_entity": source_entity, "target_entity": target_entity}


@router.post("/validate_safe_sql")
def validate_safe_sql(req: ValidateSafeSqlRequest):
    """校验 SQL 安全性（只允许 SELECT/WITH）

    使用 word boundary 正则匹配禁止关键词，避免字段名误杀：
    - 旧逻辑：`if "DROP" in sql` → `SELECT drop_date FROM t` 被误杀
    - 新逻辑：`re.search(r"\\bDROP\\b", sql)` → 只匹配独立关键词
    """
    import re as _re
    sql_raw = (req.sql or "").strip()
    if not sql_raw:
        return {"safe": False, "sql": req.sql, "reason": "SQL 为空"}
    sql = sql_raw.upper()
    if not sql.startswith("SELECT") and not sql.startswith("WITH"):
        return {"safe": False, "sql": req.sql, "reason": "必须以 SELECT 或 WITH 开头"}
    # 检测多语句（分号后跟非空内容）—— 防止 SQL 注入
    # 注意：分号在字符串字面量里是合法的，简单检测可能误杀，但安全优先
    if ";" in sql_raw.rstrip(";"):
        # 去掉末尾单个分号后如果还有分号，说明是多语句
        stripped = sql_raw.rstrip().rstrip(";")
        if ";" in stripped:
            return {"safe": False, "sql": req.sql, "reason": "禁止多语句（含分号）"}
    # word boundary 匹配禁止关键词，避免字段名如 drop_date/update_log 被误杀
    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE", "MERGE", "CALL", "EXEC", "EXECUTE"]
    for kw in forbidden:
        if _re.search(rf"\b{kw}\b", sql):
            return {"safe": False, "sql": req.sql, "reason": f"禁止包含关键词 {kw}"}
    return {"safe": True, "sql": req.sql, "reason": "通过"}


@router.post("/execute_sql")
def execute_sql(req: ExecuteSqlRequest):
    """执行 SELECT SQL 并返回结果"""
    from app.services.sql_executor import _build_execute_query_fn
    exec_fn = _build_execute_query_fn()
    if not exec_fn:
        raise HTTPException(500, "SQL 执行函数不可用")
    result = exec_fn(req.sql)
    return result


# ---------------------------------------------------------------------------
# NL2API: 数据源模式查询
# ---------------------------------------------------------------------------

@router.get("/entity_source_mode/{entity_code}")
def get_entity_source_mode(entity_code: str):
    """返回实体的 source_mode + 通用 API 映射信息

    让 LLM 知道该实体该走 SQL 路径(sql_integration)还是 API 映射路径(api_integration)。
    """
    from app.core.database import SessionLocal
    from app.models.base import Entity, EntityApiMapping, DataSourceConfig

    db = SessionLocal()
    try:
        ent = db.query(Entity).filter(Entity.entity_code == entity_code).first()
        if not ent:
            return {"entity_code": entity_code, "source_mode": "physical_table"}
        source_mode = ent.source_mode or "physical_table"
        entity_en_name = ent.entity_en_name or ""
        has_integration_sql = bool(ent.integration_sql)
        # 实体级 catalog（execute_doris_sql 执行前 SWITCH 用）+ integration_sql 摘要（让 LLM 知道 SQL 已现成，无需自拼）
        doris_catalog = ent.doris_catalog or None
        integration_sql_preview = (ent.integration_sql or "").strip()[:200]
        has_api_mapping = db.query(EntityApiMapping).filter(EntityApiMapping.entity_id == ent.id).first() is not None
        # per-entity 数据源绑定（physical_table 模式用）
        data_source_id = str(ent.data_source_id) if ent.data_source_id else None
        data_source_name = None
        doris_catalog_name = None
        if data_source_id:
            ds = db.query(DataSourceConfig).filter(DataSourceConfig.id == data_source_id).first()
            if ds:
                data_source_name = ds.name
                doris_catalog_name = ds.doris_catalog_name
    finally:
        db.close()

    return {
        "entity_code": entity_code,
        "source_mode": source_mode,
        "entity_en_name": entity_en_name,
        "has_integration_sql": has_integration_sql,
        "has_api_mapping": has_api_mapping,
        "data_source_id": data_source_id,
        "data_source_name": data_source_name,
        "doris_catalog_name": doris_catalog_name,
        # 实体级 catalog（sql_integration 执行前 SWITCH；为 None 时 SQL 须用 3 段命名 catalog.db.table）
        "doris_catalog": doris_catalog,
        # integration_sql 摘要：sql_integration 模式下 SQL 已在平台配好，传 entity_code 即用，无需自拼
        "integration_sql_preview": integration_sql_preview,
    }

