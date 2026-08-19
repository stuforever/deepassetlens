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
    join_on = fn(source_entity, target_entity) if fn else ""
    # P0 安全修复：缺失可信 JOIN 配置时明确失败，禁止默认编造 cust_id 关联键（数据正确性高风险）
    if not join_on:
        return {"error": f"未配置实体「{source_entity}」与「{target_entity}」的可信关联关系，不能执行跨表查询。请先在映射管理配置 JOIN ON 表达式。",
                "join_on": "", "source_entity": source_entity, "target_entity": target_entity}
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
    """执行 SELECT SQL 并返回结果（P0-2：统一经 secure_query_executor 校验，不可绕过）"""
    from app.services.secure_query_executor import validate_sql
    _chk = validate_sql(req.sql)
    if not _chk.ok:
        raise HTTPException(403, f"SQL安全校验未通过: {_chk.reason}")
    from app.services.sql_executor import _build_execute_query_fn
    exec_fn = _build_execute_query_fn()
    if not exec_fn:
        raise HTTPException(500, "SQL 执行函数不可用")
    result = exec_fn(_chk.sql)
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


@router.post("/batch_entity_source_mode")
def batch_entity_source_mode(payload: dict):
    """批量返回多实体的 source_mode + 路由建议。
    入参: {"entity_codes": ["vw_transformer", "cms20_dist_sta", ...]}
    出参: {
      "items": [{entity_code, source_mode, ...}, ...],
      "recommended_engine": "physical_table|doris_federated|api_integration",
      "recommended_tool": "execute_sql|execute_doris_sql|execute_entity_api",
      "has_api_integration": bool, "has_catalog": bool,
    }
    路由优先级（铁律）：
      - 任一 api_integration -> execute_entity_api（DuckDB 联邦）
      - 有 doris_catalog 的表（无 api）-> execute_doris_sql（Doris 联邦，三段命名 pg_tupu.public.表名）
      - 未绑 catalog 的物理表 -> execute_sql（物理直连）
    """
    from app.core.database import SessionLocal
    from app.models.base import Entity, EntityApiMapping, DataSourceConfig

    codes = payload.get("entity_codes") or []
    if not isinstance(codes, list) or not codes:
        return {"items": [], "recommended_engine": "physical_table", "recommended_tool": "execute_sql"}

    db = SessionLocal()
    try:
        from sqlalchemy import or_
        # 同时按 entity_code、entity_en_name（物理表名）、entity_name（中文名）匹配
        # 场景剧本用 ⟦中文名⟧ 解析后为物理表名，entity_code 是语义代码，entity_name 是中文
        ents = db.query(Entity).filter(
            or_(Entity.entity_code.in_(codes), Entity.entity_en_name.in_(codes), Entity.entity_name.in_(codes))
        ).all()
        # 构建双索引：entity_code 和 entity_en_name 都映射到实体
        ent_map = {}
        for e in ents:
            ent_map[e.entity_code] = e
            if e.entity_en_name:
                ent_map[e.entity_en_name] = e
        # 批量查 API 映射 + 数据源，减少 N+1 查询
        api_map_ids = {e.id for e in ents if e.id}
        has_api_set = set()
        if api_map_ids:
            api_rows = db.query(EntityApiMapping.entity_id).filter(EntityApiMapping.entity_id.in_(api_map_ids)).all()
            has_api_set = {r[0] for r in api_rows}
        ds_ids = {str(e.data_source_id) for e in ents if e.data_source_id}
        ds_map = {}
        if ds_ids:
            ds_rows = db.query(DataSourceConfig).filter(DataSourceConfig.id.in_(ds_ids)).all()
            ds_map = {str(d.id): d for d in ds_rows}
    finally:
        db.close()

    items = []
    has_api = False
    has_catalog = False  # 有 doris_catalog 的表（physical_table + sql_integration 绑了 catalog）
    for code in codes:
        ent = ent_map.get(code)
        if not ent:
            items.append({"entity_code": code, "source_mode": "physical_table"})
            continue
        sm = ent.source_mode or "physical_table"
        # view 等同于 physical_table（视图走 execute_sql 直连）
        if sm == "view":
            sm = "physical_table"
        if sm == "api_integration":
            has_api = True
        if ent.doris_catalog:
            has_catalog = True
        ds = ds_map.get(str(ent.data_source_id)) if ent.data_source_id else None
        items.append({
            "entity_code": code,
            "source_mode": sm,
            "has_integration_sql": bool(ent.integration_sql),
            "has_api_mapping": ent.id in has_api_set,
            "data_source_id": str(ent.data_source_id) if ent.data_source_id else None,
            "data_source_name": ds.name if ds else None,
            "doris_catalog_name": ds.doris_catalog_name if ds else None,
            "doris_catalog": ent.doris_catalog or None,
            # P5：可用预聚合加速器提示（命中加速器覆盖表时给出，供代理选择）
            "available_accelerators": _available_accelerators(ent),
        })

    # 路由决策：
    # - 多表含 api_integration -> execute_api_sql（DuckDB 跨源联邦，API 虚拟表 + 物理表 JOIN）
    # - 单表 api_integration -> execute_entity_api（DuckDB 单对象 API）
    # - 有 doris_catalog 的表 -> execute_doris_sql（Doris 联邦三段命名）
    # - 未绑 catalog 的物理表 -> execute_sql（物理直连）
    if has_api:
        if len(codes) > 1:
            recommended = ("api_federated", "execute_api_sql")
        else:
            recommended = ("api_integration", "execute_entity_api")
    elif has_catalog:
        recommended = ("doris_federated", "execute_doris_sql")
    else:
        recommended = ("physical_table", "execute_sql")

    return {
        "items": items,
        "recommended_engine": recommended[0],
        "recommended_tool": recommended[1],
        "has_api_integration": has_api,
        "has_catalog": has_catalog,
        # 批3：附加引擎健康快照（懒探测+60s缓存，供前端健康徽标/故障提示）
        "engine_health": _engine_health_snapshot(),
    }


def _engine_health_snapshot() -> dict:
    """引擎健康快照（best-effort，探测失败不影响路由）。"""
    try:
        from app.services import engine_health
        return engine_health.snapshot()
    except Exception:
        return {}


def _available_accelerators(ent) -> list:
    """P5：该实体可用预聚合加速器（按实体物理表名/entity_code 匹配 source_tables）。"""
    try:
        from app.services.engine_accelerator import list_accelerators
        candidates = {ent.entity_en_name, ent.entity_code}
        accs = list_accelerators(enabled_only=True)
        hits = []
        for a in accs:
            if any(c and c in (a.get("source_tables") or []) for c in candidates if c):
                hits.append({"name": a["name"], "target_table": f"{a['target_db']}.{a['target_table']}",
                             "agg_expr": a.get("agg_expr"), "data_as_of": a.get("last_refresh_at")})
        return hits
    except Exception:
        return []

