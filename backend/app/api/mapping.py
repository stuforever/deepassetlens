from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.base import SourceTable, Entity, Concept, EntityMappingRule, SourceMasterTable, SourceBusinessTable, SourceReferenceTable
from ..schemas.mapping import SourceTableCreate, SourceTableResponse, EntityMappingCreate, EntityMappingResponse
from ..core.database import get_db
import json
import sqlalchemy
from sqlalchemy import create_engine, inspect
from pydantic import BaseModel
import re
import uuid

router = APIRouter()

def _norm_entity_key(v: Optional[str]) -> str:
    s = (v or "").strip()
    return re.sub(r"\s+", " ", s).lower()


def _entity_key_by_id(db: Session, entity_id: str) -> str:
    ent = db.query(Entity).filter(Entity.id == str(entity_id)).first()
    if not ent:
        raise HTTPException(status_code=400, detail="Entity not found")
    return _norm_entity_key(ent.entity_name) or _norm_entity_key(ent.entity_code) or str(ent.id)


def _find_conflict_rule_by_entity_key(db: Session, entity_key: str, exclude_rule_id: Optional[str] = None) -> Optional[EntityMappingRule]:
    rules = db.query(EntityMappingRule).all()
    entity_ids = set()
    for r in rules:
        if exclude_rule_id and str(r.id) == str(exclude_rule_id):
            continue
        for eid in (r.entity_ids or []):
            entity_ids.add(str(eid))

    ent_rows = db.query(Entity.id, Entity.entity_name, Entity.entity_code).filter(Entity.id.in_(list(entity_ids))).all() if entity_ids else []
    ent_key_map = {}
    for eid, name, code in ent_rows:
        ent_key_map[str(eid)] = _norm_entity_key(name) or _norm_entity_key(code) or str(eid)

    for r in rules:
        if exclude_rule_id and str(r.id) == str(exclude_rule_id):
            continue
        for eid in (r.entity_ids or []):
            if ent_key_map.get(str(eid), "") == entity_key:
                return r
    return None

class MappingRuleCreate(BaseModel):
    name: Optional[str] = None
    source_table_ids: List[str]
    entity_ids: List[str]
    field_mappings: Optional[dict] = None
    is_advanced_sql: Optional[bool] = False
    sql_content: Optional[str] = None


class MappingRuleUpdate(BaseModel):
    name: Optional[str] = None
    source_table_ids: Optional[List[str]] = None
    entity_ids: Optional[List[str]] = None
    field_mappings: Optional[dict] = None
    is_advanced_sql: Optional[bool] = None
    sql_content: Optional[str] = None


def _serialize_rule(rule: EntityMappingRule):
    return {
        "id": str(rule.id),
        "name": rule.name,
        "source_table_ids": rule.source_table_ids or [],
        "entity_ids": rule.entity_ids or [],
        "field_mappings": rule.field_mappings or {},
        "is_advanced_sql": bool(rule.is_advanced_sql),
        "sql_content": rule.sql_content,
        "created_at": str(rule.created_at) if rule.created_at else None,
    }


def _find_rule_by_id(db: Session, rule_id: str) -> Optional[EntityMappingRule]:
    rules = db.query(EntityMappingRule).all()
    return next((r for r in rules if str(r.id) == str(rule_id)), None)


def _extract_table_ids_from_rule(rule: EntityMappingRule, valid_table_ids: set):
    result = set()

    # 先保留 source_table_ids 中已合法的
    for sid in (rule.source_table_ids or []):
        sid_str = str(sid)
        if sid_str in valid_table_ids:
            result.add(sid_str)

    # 再从 field_mappings.source 中解析真实表ID
    mappings = rule.field_mappings or {}
    for _, value in mappings.items():
        source_values = []
        if isinstance(value, dict) and value.get("source") is not None:
            src = value.get("source")
            source_values = src if isinstance(src, list) else [src]
        elif isinstance(value, str):
            source_values = [value]
        elif isinstance(value, list):
            source_values = value

        for mv in source_values:
            if not isinstance(mv, str):
                continue
            for tid in valid_table_ids:
                if mv.startswith(f"{tid}_"):
                    result.add(tid)
                    break

    return list(result)


def _get_valid_source_table_ids(db: Session) -> set:
    valid_table_ids = set()
    for t in db.query(SourceMasterTable.id).all():
        valid_table_ids.add(str(t[0]))
    for t in db.query(SourceBusinessTable.id).all():
        valid_table_ids.add(str(t[0]))
    for t in db.query(SourceReferenceTable.id).all():
        valid_table_ids.add(str(t[0]))
    return valid_table_ids


def _extract_table_ids_from_field_mappings(field_mappings: dict, valid_table_ids: set) -> set:
    result = set()
    mappings = field_mappings or {}
    for _, value in mappings.items():
        source_values = []
        if isinstance(value, dict) and value.get("source") is not None:
            src = value.get("source")
            source_values = src if isinstance(src, list) else [src]
        elif isinstance(value, str):
            source_values = [value]
        elif isinstance(value, list):
            source_values = value

        for mv in source_values:
            if not isinstance(mv, str):
                continue
            for tid in valid_table_ids:
                if mv.startswith(f"{tid}_"):
                    result.add(tid)
                    break
    return result


def _validate_mapping_detail_unique_key(field_mappings: dict):
    seen = set()
    duplicates = set()
    mappings = field_mappings or {}
    for k in mappings.keys():
        if k == "__meta__":
            continue
        if "_" not in str(k):
            continue
        field_en = str(k).split("_", 1)[1].strip().lower()
        if not field_en:
            continue
        if field_en in seen:
            duplicates.add(field_en)
        else:
            seen.add(field_en)
    if duplicates:
        dup_list = "、".join(sorted(duplicates))
        raise HTTPException(status_code=409, detail=f"映射明细唯一主键冲突（映射规则+字段英文名）：{dup_list}")


def _validate_field_mappings_table_subset(field_mappings: dict, source_table_ids: List[str], valid_table_ids: set):
    used_ids = _extract_table_ids_from_field_mappings(field_mappings or {}, valid_table_ids)
    selected_ids = {str(x) for x in (source_table_ids or [])}
    missing = sorted([tid for tid in used_ids if tid not in selected_ids])
    if missing:
        raise HTTPException(status_code=400, detail=f"field_mappings 引用的来源表未被选择：{', '.join(missing)}")


def _to_uuid_or_none(v):
    if v is None or v == "":
        return None
    try:
        return uuid.UUID(str(v))
    except Exception:
        raise HTTPException(status_code=400, detail=f"非法UUID: {v}")


@router.post("/rules")
def create_mapping_rule(rule: MappingRuleCreate, db: Session = Depends(get_db)):
    payload = rule.dict()
    entity_ids = payload.get("entity_ids") or []
    if len(entity_ids) != 1:
        raise HTTPException(status_code=400, detail="entity_ids must contain exactly one entity")

    entity_key = _entity_key_by_id(db, str(entity_ids[0]))
    conflict = _find_conflict_rule_by_entity_key(db, entity_key)
    if conflict:
        raise HTTPException(status_code=409, detail=f"该目标实体已存在映射规则（rule_id={conflict.id}）")

    valid_table_ids = _get_valid_source_table_ids(db)
    field_mappings = payload.get("field_mappings") or {}
    _validate_mapping_detail_unique_key(field_mappings)
    _validate_field_mappings_table_subset(field_mappings, payload.get("source_table_ids") or [], valid_table_ids)

    db_rule = EntityMappingRule(**payload)
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return {"code": 200, "data": {"id": str(db_rule.id), "overwritten": False}}

@router.get("/rules")
def get_mapping_rules(entity_id: Optional[str] = Query(None, description="按实体ID过滤"), db: Session = Depends(get_db)):
    q = db.query(EntityMappingRule).order_by(EntityMappingRule.created_at.desc())
    if entity_id:
        # entity_ids 是 JSON 数组，Python 端过滤包含该 entity_id 的规则
        all_rules = q.all()
        rules = [r for r in all_rules if entity_id in (r.entity_ids or [])]
    else:
        rules = q.all()
    return {"code": 200, "data": [_serialize_rule(r) for r in rules]}


@router.get("/rules/{rule_id}")
def get_mapping_rule_detail(rule_id: str, db: Session = Depends(get_db)):
    db_rule = _find_rule_by_id(db, rule_id)
    if not db_rule:
        raise HTTPException(status_code=404, detail="Mapping rule not found")
    return {"code": 200, "data": _serialize_rule(db_rule)}


@router.put("/rules/{rule_id}")
def update_mapping_rule(rule_id: str, payload: MappingRuleUpdate, db: Session = Depends(get_db)):
    db_rule = _find_rule_by_id(db, rule_id)
    if not db_rule:
        raise HTTPException(status_code=404, detail="Mapping rule not found")

    data = payload.dict(exclude_unset=True)
    if "entity_ids" in data:
        entity_ids = data.get("entity_ids") or []
        if len(entity_ids) != 1:
            raise HTTPException(status_code=400, detail="entity_ids must contain exactly one entity")
        entity_key = _entity_key_by_id(db, str(entity_ids[0]))
        conflict = _find_conflict_rule_by_entity_key(db, entity_key, exclude_rule_id=str(db_rule.id))
        if conflict:
            raise HTTPException(status_code=409, detail=f"该目标实体已存在映射规则（rule_id={conflict.id}）")

    next_source_table_ids = data.get("source_table_ids", db_rule.source_table_ids or [])
    next_field_mappings = data.get("field_mappings", db_rule.field_mappings or {})
    valid_table_ids = _get_valid_source_table_ids(db)
    _validate_mapping_detail_unique_key(next_field_mappings)
    _validate_field_mappings_table_subset(next_field_mappings, next_source_table_ids, valid_table_ids)

    if "name" in data:
        db_rule.name = data["name"]
    if "source_table_ids" in data:
        db_rule.source_table_ids = data["source_table_ids"] or []
    if "entity_ids" in data:
        db_rule.entity_ids = data["entity_ids"] or []
    if "field_mappings" in data:
        db_rule.field_mappings = data["field_mappings"] or {}
    if "is_advanced_sql" in data:
        db_rule.is_advanced_sql = bool(data["is_advanced_sql"])
    if "sql_content" in data:
        db_rule.sql_content = data["sql_content"]

    db.commit()
    db.refresh(db_rule)
    return {"code": 200, "data": _serialize_rule(db_rule)}


@router.delete("/rules/{rule_id}")
def delete_mapping_rule(rule_id: str, db: Session = Depends(get_db)):
    db_rule = _find_rule_by_id(db, rule_id)
    if not db_rule:
        raise HTTPException(status_code=404, detail="Mapping rule not found")
    db.delete(db_rule)
    db.commit()
    return {"code": 200, "message": "deleted"}


@router.post("/sources", response_model=SourceTableResponse)
def register_source_table(source: SourceTableCreate, db: Session = Depends(get_db)):
    """注册外部源表并自动扫描字段元数据"""
    conn_info = source.connection_info
    
    # 尝试连接外部数据库并扫描字段
    # 支持 mysql, postgresql, oracle (需对应驱动)
    try:
        # 这里仅为逻辑演示，实际生产需根据不同库类型构建URL
        # db_url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db}"
        # 这里我们模拟一个元数据扫描结果
        mock_columns = [
            {"name": "CONS_NO", "type": "VARCHAR(32)", "comment": "用户编号"},
            {"name": "CONS_NAME", "type": "VARCHAR(256)", "comment": "用户名称"},
            {"name": "ELEC_ADDR", "type": "VARCHAR(512)", "comment": "用电地址"}
        ]
        
        db_source = SourceTable(
            table_name=source.table_name,
            schema_name=source.schema_name,
            connection_info=conn_info,
            column_metadata={"columns": mock_columns} # 扫描结果存入JSONB
        )
        db.add(db_source)
        db.commit()
        db.refresh(db_source)
        return db_source
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to scan source table: {str(e)}")

@router.get("/sources", response_model=List[SourceTableResponse])
def list_sources(db: Session = Depends(get_db)):
    return db.query(SourceTable).all()

@router.get("/lineage/{entity_id}")
def get_entity_lineage(entity_id: str, db: Session = Depends(get_db)):
    """获取实体的完整溯源路径：实体 -> 映射规则 -> 源表"""
    # 1. 获取实体信息
    entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # 2. 获取所属概念信息
    concept = db.query(Concept).filter(Concept.id == entity.concept_id).first()
    
    # 3. 从 EntityMappingRule 查找关联的映射
    all_rules = db.query(EntityMappingRule).all()
    matched_rules = []
    eid_norm = entity_id.replace('-', '') # 兼容 32 位和 36 位
    
    for r in all_rules:
        eids = r.entity_ids
        if isinstance(eids, str):
            try: eids = json.loads(eids)
            except: eids = []
        
        eids_norm = [str(x).replace('-', '') for x in (eids or [])]
        if eid_norm in eids_norm:
            matched_rules.append(r)
    
    lineage_results = []
    
    # 加载所有源表信息用于快速查找
    from ..models.base import SourceMasterTable, SourceBusinessTable, SourceReferenceTable
    all_master = {str(t.id): t for t in db.query(SourceMasterTable).all()}
    all_biz = {str(t.id): t for t in db.query(SourceBusinessTable).all()}
    all_ref = {str(t.id): t for t in db.query(SourceReferenceTable).all()}
    
    for rule in matched_rules:
        stids = rule.source_table_ids
        if isinstance(stids, str):
            try: stids = json.loads(stids)
            except: stids = []
            
        for stid in (stids or []):
            stid_str = str(stid)
            source = all_master.get(stid_str) or all_biz.get(stid_str) or all_ref.get(stid_str)
            
            lineage_results.append({
                "rule_id": str(rule.id),
                "rule_name": rule.name or "未命名规则",
                "mapping_logic": rule.field_mappings,
                "sql_fragment": rule.sql_content,
                "source_table": {
                    "id": stid_str,
                    "table_name": getattr(source, 'cnName', 'UNKNOWN'),
                    "en_name": getattr(source, 'enName', 'UNKNOWN'),
                    "sys_name": getattr(source, 'sysName', None),
                }
            })
    
    return {
        "entity": {
            "id": str(entity.id),
            "name": entity.entity_name,
            "code": entity.entity_code,
            "concept_path": f"{concept.name}" if concept else "Unknown"
        },
        "lineage": lineage_results
    }
