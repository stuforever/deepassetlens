from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import hashlib
import json
import math
import base64
import io
import re
import sqlalchemy
from datetime import datetime
import uuid

from ..core.database import get_db
from ..models.base import (
    Concept,
    Entity,
    EntityRelation,
    IntentSemanticAsset,
    SemanticEmbedding,
    StandardSemanticTerm,
    StandardSemanticVectorTask,
    CommonStopWord,
)
from ..services.semantic_retrieval import embed_texts, get_or_init_retrieval_config, get_vector_model_registry
from ..services.standard_semantic_service import query_standard_semantic_matches

router = APIRouter()


DEFAULT_MODEL_CONFIG = {
    "model_name": "bge-large-zh-v1.5",
    "model_path": "",
    "dimension": 1024,
    "batch_size": 32,
    "use_gpu": False,
}


class ExtractGraphTermsRequest(BaseModel):
    reset_existing: bool = False
    extract_mode: str = "all"  # "all" or "attributes_only"


class VectorizeRequest(BaseModel):
    term_ids: Optional[List[str]] = None
    force_regenerate: Optional[bool] = False
    normalize_l2: Optional[bool] = True
    max_retries: Optional[int] = 2
    batch_size: Optional[int] = None
    model_name: Optional[str] = None


class QueryVectorRequest(BaseModel):
    query_text: str
    top_k: Optional[int] = 10
    term_types: Optional[List[str]] = None
    normalize_l2: Optional[bool] = True
    bind_ontology: Optional[bool] = True
    entity_scope: Optional[str] = "data"  # data | concept | all
    hybrid: Optional[bool] = True


class ExportVectorsRequest(BaseModel):
    format: str = "json"  # json | parquet | vector_store
    include_ontology_bind: Optional[bool] = True
    term_types: Optional[List[str]] = None
    entity_scope: Optional[str] = "data"  # data | concept | all


class ModelConfigUpdate(BaseModel):
    model_name: Optional[str] = None
    model_path: Optional[str] = None
    dimension: Optional[int] = None
    batch_size: Optional[int] = None
    use_gpu: Optional[bool] = None


def _hash_term(model_name: str, canonical_text: str) -> str:
    return hashlib.sha256(f"{model_name}\n{canonical_text}".encode("utf-8")).hexdigest()


def _get_model_config(db: Session) -> dict:
    cfg = get_or_init_retrieval_config(db)
    return {
        "model_name": cfg["vector_model_name"],
        "model_path": cfg.get("vector_model_path") or "",
        "dimension": cfg.get("vector_dimension") or DEFAULT_MODEL_CONFIG["dimension"],
        "batch_size": DEFAULT_MODEL_CONFIG["batch_size"],
        "use_gpu": DEFAULT_MODEL_CONFIG["use_gpu"],
        "provider": cfg.get("vector_provider") or "local",
        "available_models": get_vector_model_registry()["models"],
    }


@router.post("/standard-semantics/extract-from-graph")
def extract_graph_terms_api(payload: ExtractGraphTermsRequest, db: Session = Depends(get_db)):
    from ..services.standard_semantic_service import extract_graph_semantic_terms
    cfg = _get_model_config(db)
    try:
        result = extract_graph_semantic_terms(
            db,
            model_name=cfg["model_name"],
            reset_existing=payload.reset_existing,
            extract_mode=payload.extract_mode,
        )
        return {"code": 200, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/standard-semantics/vectorize")
def vectorize_terms_api(payload: VectorizeRequest, db: Session = Depends(get_db)):
    from ..services.standard_semantic_service import vectorize_terms
    cfg = _get_model_config(db)
    try:
        result = vectorize_terms(
            db,
            model_name=payload.model_name or cfg["model_name"],
            model_path=cfg.get("model_path"),
            term_ids=payload.term_ids,
            force_regenerate=payload.force_regenerate,
            normalize_l2=payload.normalize_l2,
            max_retries=payload.max_retries,
            batch_size=payload.batch_size or cfg.get("batch_size", 32),
            use_gpu=cfg.get("use_gpu", False),
        )
        return {"code": 200, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/standard-semantics/query")
def query_semantic_matches_api(payload: QueryVectorRequest, db: Session = Depends(get_db)):
    from ..services.standard_semantic_service import query_standard_semantic_matches
    cfg = _get_model_config(db)
    try:
        result = query_standard_semantic_matches(
            db,
            query_text=payload.query_text,
            top_k=payload.top_k,
            term_types=payload.term_types,
            normalize_l2=payload.normalize_l2,
            bind_ontology=payload.bind_ontology,
            entity_scope=payload.entity_scope,
            hybrid=payload.hybrid if payload.hybrid is not None else True,
        )
        return {"code": 200, "data": {"matches": result}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/standard-semantics/export")
def export_vectors_api(payload: ExportVectorsRequest, db: Session = Depends(get_db)):
    from ..services.standard_semantic_service import export_vectors
    cfg = _get_model_config(db)
    try:
        data = export_vectors(
            db,
            model_name=cfg["model_name"],
            format=payload.format,
            include_ontology_bind=payload.include_ontology_bind,
            term_types=payload.term_types,
            entity_scope=payload.entity_scope,
        )
        return {"code": 200, "data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/standard-semantics/model-config")
def get_model_config_api(db: Session = Depends(get_db)):
    cfg = _get_model_config(db)
    return {"code": 200, "data": cfg}


@router.get("/standard-semantics/vector-models")
def list_vector_models_api():
    return {"code": 200, "data": get_vector_model_registry()}


@router.put("/standard-semantics/model-config")
def update_model_config_api(payload: ModelConfigUpdate, db: Session = Depends(get_db)):
    from ..models.base import SmartPlannerConfig
    from ..services.semantic_retrieval import VECTOR_MODEL_REGISTRY, _resolve_local_model_path

    item = db.query(SmartPlannerConfig).order_by(SmartPlannerConfig.created_at.desc()).first()
    if not item:
        item = SmartPlannerConfig(planner_mode="rule", enabled=True)
        db.add(item)
    if payload.model_name:
        if payload.model_name not in VECTOR_MODEL_REGISTRY:
            raise HTTPException(status_code=400, detail=f"不支持的向量模型: {payload.model_name}")
        spec = VECTOR_MODEL_REGISTRY[payload.model_name]
        item.vector_model_name = payload.model_name
        item.vector_model_path = payload.model_path or (_resolve_local_model_path(payload.model_name) if spec.get("provider") == "local" else "")
    elif payload.model_path is not None:
        item.vector_model_path = payload.model_path
    db.commit()
    return {"code": 200, "data": _get_model_config(db), "message": "Model config updated"}


@router.get("/standard-semantics/terms")
def list_semantic_terms_api(
    term_type: Optional[str] = None,
    entity_scope: Optional[str] = None,
    keyword: Optional[str] = None,
    vector_status: Optional[str] = None,
    limit: int = 1000,
    db: Session = Depends(get_db),
):
    query = db.query(StandardSemanticTerm)
    if term_type:
        query = query.filter(StandardSemanticTerm.term_type == term_type)
    if entity_scope and entity_scope != "all":
        if entity_scope == "data":
            query = query.filter(StandardSemanticTerm.ontology_ref_type == "entity")
        elif entity_scope == "concept":
            query = query.filter(StandardSemanticTerm.ontology_ref_type == "concept")
        else:
            query = query.filter(StandardSemanticTerm.ontology_ref_type == entity_scope)
    if keyword:
        query = query.filter(StandardSemanticTerm.term.contains(keyword))
    if vector_status:
        query = query.filter(StandardSemanticTerm.vector_status == vector_status)
    items = query.order_by(StandardSemanticTerm.created_at.desc()).limit(limit).all()

    return {
        "code": 200,
        "data": [
            {
                "id": str(i.id),
                "term": i.term,
                "display_text": (i.text_payload or {}).get("display_text") if isinstance(i.text_payload, dict) else i.term,
                "term_type": i.term_type,
                "doc_type": (i.text_payload or {}).get("doc_type") if isinstance(i.text_payload, dict) else i.term_type,
                "scene": (i.text_payload or {}).get("scene") if isinstance(i.text_payload, dict) else None,
                "ontology_ref_type": i.ontology_ref_type,
                "ontology_ref_id": str(i.ontology_ref_id) if i.ontology_ref_id else None,
                "text_payload": i.text_payload,
                "search_text_preview": (
                    ((i.text_payload or {}).get("search_texts") or [])[:5]
                    if isinstance(i.text_payload, dict)
                    else []
                ),
                "vector_status": i.vector_status,
                "vector_dim": i.vector_dim,
                "last_error": i.last_error,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in items
        ],
    }


@router.delete("/standard-semantics/terms/{term_id}")
def delete_semantic_term_api(term_id: str, db: Session = Depends(get_db)):
    term = db.query(StandardSemanticTerm).filter(StandardSemanticTerm.id == term_id).first()
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")
    db.delete(term)
    db.commit()
    return {"code": 200, "data": {"message": "Deleted"}}


@router.post("/standard-semantics/vectorize-task")
def create_vectorize_task_api(db: Session = Depends(get_db)):
    task = StandardSemanticVectorTask(status="pending")
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"code": 200, "data": {"task_id": str(task.id), "status": task.status}}


@router.get("/standard-semantics/vector-tasks")
def list_vectorize_tasks_api(limit: int = 20, db: Session = Depends(get_db)):
    lim = max(1, min(limit or 20, 200))
    tasks = (
        db.query(StandardSemanticVectorTask)
        .order_by(StandardSemanticVectorTask.created_at.desc())
        .limit(lim)
        .all()
    )
    return {
        "code": 200,
        "data": [
            {
                "id": str(t.id),
                "task_code": t.task_code,
                "status": t.status,
                "total_count": t.total_count,
                "success_count": t.success_count,
                "failed_count": t.failed_count,
                "skipped_count": t.skipped_count,
                "progress": t.progress,
                "message": t.message,
                "task_logs": t.task_logs or [],
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in tasks
        ],
    }


@router.get("/standard-semantics/stop-words")
def list_stop_words_api(db: Session = Depends(get_db)):
    items = db.query(CommonStopWord).all()
    return {
        "code": 200,
        "data": [
            {
                "id": str(i.id),
                "word": i.word,
                "word_type": i.word_type,
                "priority": i.priority,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in items
        ],
    }


@router.post("/standard-semantics/stop-words")
def create_stop_word_api(payload: dict, db: Session = Depends(get_db)):
    word = payload.get("word")
    word_type = payload.get("word_type", "通用")
    priority = payload.get("priority", 0)
    if not word:
        raise HTTPException(status_code=400, detail="word is required")
    item = CommonStopWord(word=word, word_type=word_type, priority=priority)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": {"id": str(item.id), "word": item.word}}


@router.delete("/standard-semantics/stop-words/{item_id}")
def delete_stop_word_api(item_id: str, db: Session = Depends(get_db)):
    item = db.query(CommonStopWord).filter(CommonStopWord.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Not found")
    db.delete(item)
    db.commit()
    return {"code": 200, "data": {"message": "Deleted"}}


# ---- cypher templates ----
class CypherTemplateCreateRequest(BaseModel):
    template_name: str
    cypher_pattern: str
    description: Optional[str] = None


class GraphSchemaCreateRequest(BaseModel):
    field_name: str
    field_type: Optional[str] = None
    description: Optional[str] = None


@router.get("/nl2cypher/cypher-templates")
def list_cypher_templates_api(db: Session = Depends(get_db)):
    from ..services.semantic_manager_service import list_cypher_templates
    items = list_cypher_templates(db)
    return {"code": 200, "data": [{"id": str(i.id), "template_name": i.template_name, "cypher_pattern": i.cypher_pattern, "description": i.description} for i in items]}


@router.post("/nl2cypher/cypher-templates")
def create_cypher_template_api(payload: CypherTemplateCreateRequest, db: Session = Depends(get_db)):
    from ..services.semantic_manager_service import create_cypher_template
    item, exists = create_cypher_template(db, template_name=payload.template_name, cypher_pattern=payload.cypher_pattern, description=payload.description)
    if exists:
        return {"code": 409, "data": {"id": str(item.id), "message": "模板已存在"}}
    return {"code": 200, "data": {"id": str(item.id), "template_name": item.template_name}}


@router.delete("/nl2cypher/cypher-templates/{item_id}")
def delete_cypher_template_api(item_id: str, db: Session = Depends(get_db)):
    from ..services.semantic_manager_service import delete_cypher_template
    ok = delete_cypher_template(db, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="不存在")
    return {"code": 200, "data": {"message": "删除成功"}}


# ---- graph schema ----
@router.get("/nl2cypher/graph-schema")
def list_graph_schema_api(db: Session = Depends(get_db)):
    from ..services.semantic_manager_service import list_graph_schema
    items = list_graph_schema(db)
    return {"code": 200, "data": [{"id": str(i.id), "field_name": i.field_name, "field_type": i.field_type, "description": i.description} for i in items]}


@router.post("/nl2cypher/graph-schema")
def create_graph_schema_api(payload: GraphSchemaCreateRequest, db: Session = Depends(get_db)):
    from ..services.semantic_manager_service import create_graph_schema
    item, exists = create_graph_schema(db, field_name=payload.field_name, field_type=payload.field_type, description=payload.description)
    if exists:
        return {"code": 409, "data": {"id": str(item.id), "message": "字段已存在"}}
    return {"code": 200, "data": {"id": str(item.id), "field_name": item.field_name}}


@router.delete("/nl2cypher/graph-schema/{item_id}")
def delete_graph_schema_api(item_id: str, db: Session = Depends(get_db)):
    from ..services.semantic_manager_service import delete_graph_schema
    ok = delete_graph_schema(db, item_id)
    if not ok:
        raise HTTPException(status_code=404, detail="不存在")
    return {"code": 200, "data": {"message": "删除成功"}}


# ---- entity relations query ----
class EntityRelationsQueryRequest(BaseModel):
    entity_ids: List[str]


@router.post("/entity-relations/query")
def query_entity_relations_api(payload: EntityRelationsQueryRequest, db: Session = Depends(get_db)):
    entity_ids_str = payload.entity_ids or []
    if len(entity_ids_str) < 2:
        return {"code": 200, "data": {"entities": [], "relations": []}}

    try:
        entity_ids = []
        for s in entity_ids_str:
            s = s.strip()
            if len(s) == 32:
                s = f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
            uuid.UUID(s)
            entity_ids.append(s)
    except ValueError:
        return {"code": 400, "data": {"error": "Invalid entity_ids format"}}

    entities_map = {}
    entities_list = []
    for e in db.query(Entity).filter(Entity.id.in_(entity_ids)).all():
        eid = str(e.id)
        entity_dict = {
            "id": eid,
            "entity_name": e.entity_name or e.entity_code or eid,
            "entity_code": e.entity_code,
            "entity_en_name": e.entity_en_name,
            "properties_schema": e.properties_schema if isinstance(e.properties_schema, list) else [],
            "layer": getattr(e, 'layer', None),
            "layer_info": getattr(e, 'layer_info', None),
            "concept_id": str(e.concept_id) if e.concept_id else None,
        }
        entities_map[eid] = entity_dict
        entities_list.append(entity_dict)

    relations = []
    for rel in db.query(EntityRelation).filter(
        EntityRelation.source_entity_id.in_(entity_ids),
        EntityRelation.target_entity_id.in_(entity_ids)
    ).all():
        src_id = str(rel.source_entity_id)
        tgt_id = str(rel.target_entity_id)
        src_name = entities_map.get(src_id, {}).get("entity_name", src_id)
        tgt_name = entities_map.get(tgt_id, {}).get("entity_name", tgt_id)
        relations.append({
            "id": str(rel.id),
            "source": src_name,
            "source_id": src_id,
            "target": tgt_name,
            "target_id": tgt_id,
            "relation": rel.relation_name,
            "relation_name": rel.relation_name,
            "direction": rel.direction,
            "cardinality": rel.cardinality,
            "join_expr": rel.join_expr,
        })

    return {
        "code": 200,
        "data": {
            "entities": entities_list,
            "relations": relations,
        }
    }


class SqlExecuteRequest(BaseModel):
    sql: str
    params: Optional[list] = None
    limit: Optional[int] = 200
    data_source_id: Optional[str] = None  # None表示使用默认SQLite


def _execute_on_mysql(config: dict, sql: str, params: list, limit: int):
    import pymysql
    conn = pymysql.connect(
        host=config["host"],
        port=config["port"],
        database=config["database"],
        user=config["username"],
        password=config["password"],
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(sql, params or [])
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            data_rows = rows[:max(1, min(limit or 200, 500))]
            return {
                "columns": columns,
                "rows": data_rows,
                "row_count": len(data_rows),
            }
    finally:
        conn.close()


@router.post("/sql/execute")
def execute_sql_api(payload: SqlExecuteRequest, db: Session = Depends(get_db)):
    raw = (payload.sql or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="SQL不能为空")
    first_word = re.split(r"\s+", raw.lstrip(), maxsplit=1)[0].upper()
    if first_word != "SELECT":
        raise HTTPException(status_code=400, detail="仅允许执行 SELECT 查询")

    # 如果有指定数据源，用MySQL执行
    if payload.data_source_id:
        from ..models.base import DataSourceConfig
        ds = db.query(DataSourceConfig).filter(DataSourceConfig.id == payload.data_source_id).first()
        if not ds:
            raise HTTPException(status_code=404, detail="数据源不存在")
        if not ds.enabled:
            raise HTTPException(status_code=400, detail="数据源已禁用")
        try:
            result = _execute_on_mysql(
                {"host": ds.host, "port": ds.port, "database": ds.database, "username": ds.username, "password": ds.password},
                raw, payload.params or [], payload.limit or 200
            )
            return {"code": 200, "data": result}
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"MySQL执行错误: {e}")

    # 默认SQLite执行
    try:
        if isinstance(payload.params, list):
            raise HTTPException(
                status_code=400,
                detail="SQLite执行仅支持命名参数字典；当前收到数组参数，请选择MySQL数据源执行",
            )
        result = db.execute(sqlalchemy.text(raw), payload.params or {})
        rows = result.mappings().all()
        columns = list(result.keys()) if hasattr(result, "keys") else []
        data_rows = [dict(r) for r in rows[:max(1, min(payload.limit or 200, 500))]]
        return {
            "code": 200,
            "data": {
                "columns": [str(c) for c in columns],
                "rows": data_rows,
                "row_count": len(data_rows),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL执行错误: {e}")


def _norm_uuid(val):
    if not val:
        return val
    s = str(val).strip()
    if not s:
        return val
    if len(s) == 32:
        s = f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
    return s


class TraceabilityRequest(BaseModel):
    entity_ids: List[str]
    field_list: Optional[List[dict]] = None  # [{field_name, entity_id, attribute_name, entity_en_name, attribute_en_name}]


@router.post("/traceability/analyze")
def analyze_traceability(payload: TraceabilityRequest, db: Session = Depends(get_db)):
    from ..models.base import (
        EntityMappingRule, SourceTableRelation,
        SourceFieldImport
    )

    entity_ids = payload.entity_ids or []
    field_list = payload.field_list or []
    if not entity_ids:
        raise HTTPException(status_code=400, detail="entity_ids 不能为空")

    norm_ids = []
    for eid in entity_ids:
        try:
            s = str(eid).strip()
            if len(s) == 32:
                s = f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
            uuid.UUID(s)
            norm_ids.append(s)
        except ValueError:
            pass
    if not norm_ids:
        raise HTTPException(status_code=400, detail="entity_ids 格式不正确")

    entities = db.query(Entity).filter(Entity.id.in_(norm_ids)).all()
    entities_map = {str(e.id): e for e in entities}

    all_concepts = db.query(Concept).all()
    concept_map = {str(c.id): c for c in all_concepts}

    def build_concept_chain(concept_id: str) -> list:
        chain = []
        cid = _norm_uuid(concept_id)
        visited = set()
        while cid and cid not in visited:
            visited.add(cid)
            c = concept_map.get(cid)
            if not c:
                break
            chain.insert(0, {"id": cid, "name": c.name, "level": c.level})
            pid = str(c.parent_id) if c.parent_id else None
            cid = _norm_uuid(pid) if pid else None
        return chain

    # 2. 查找实体映射规则
    all_rules = db.query(EntityMappingRule).all()
    matched_rules = []
    query_eids_32 = [_norm_uuid(eid) for eid in entity_ids]

    for rule in all_rules:
        try:
            # 兼容处理 JSON 字段可能是字符串或列表/字典的情况
            rule_entity_ids = rule.entity_ids
            if isinstance(rule_entity_ids, str):
                rule_entity_ids = json.loads(rule_entity_ids)
            rule_entity_ids = rule_entity_ids or []
            
            rule_eids_32 = [_norm_uuid(eid) for eid in rule_entity_ids]
            if any(eid in query_eids_32 for eid in rule_eids_32):
                matched_rules.append(rule)
        except Exception as e:
            print(f"Error parsing rule entity_ids: {e}")
            pass

    # 3. 解析映射规则中的源表ID和字段映射
    # rule_field_mappings: {attr_key_32: [{source_table_id, source_field_en, is_pk, desc}]}
    rule_source_table_ids = set()
    rule_field_mappings = {}  
    
    for rule in matched_rules:
        try:
            stids = rule.source_table_ids
            if isinstance(stids, str):
                stids = json.loads(stids)
            stids = stids or []
            for stid in stids:
                rule_source_table_ids.add(_norm_uuid(stid))
            
            fms = rule.field_mappings
            if isinstance(fms, str):
                fms = json.loads(fms)
            fms = fms or {}
            
            for fk, fm_val in fms.items():
                # fk 格式: "entity_id_attr_name"
                parts = fk.split("_")
                if len(parts) >= 2:
                    attr_name_part = "_".join(parts[1:])
                    attr_key_32 = _norm_uuid(parts[0]) + "_" + attr_name_part
                else:
                    attr_key_32 = fk
                
                # MappingManager.tsx 存储的是数组 [ "tableId_fieldEn", ... ]
                # 兼容旧逻辑可能是字典 { "source": [...], "is_pk": ... }
                sources = []
                is_pk = False
                desc = ""
                
                if isinstance(fm_val, list):
                    sources = fm_val
                elif isinstance(fm_val, dict):
                    src = fm_val.get("source", [])
                    sources = src if isinstance(src, list) else [src]
                    is_pk = fm_val.get("is_pk", False)
                    desc = fm_val.get("desc", "")
                elif isinstance(fm_val, str):
                    sources = [fm_val]

                for src in sources:
                    if not isinstance(src, str): continue
                    src_parts = src.split("_")
                    if len(src_parts) >= 2:
                        src_table_id = _norm_uuid(src_parts[0])
                        src_field_en = "_".join(src_parts[1:])
                        
                        # 我们支持一个属性对应多个来源，这里先取列表
                        if attr_key_32 not in rule_field_mappings:
                            rule_field_mappings[attr_key_32] = []
                            
                        rule_field_mappings[attr_key_32].append({
                            "source_table_id": src_table_id,
                            "source_field_en": src_field_en,
                            "is_pk": is_pk,
                            "desc": desc,
                        })
                        rule_source_table_ids.add(src_table_id)
        except Exception as e:
            print(f"Error parsing rule field_mappings: {e}")
            pass

    # 4. 从 SourceMasterTable/Business/Reference 加载源表基本信息用于 ID -> enName 转换
    from ..models.base import SourceMasterTable, SourceBusinessTable, SourceReferenceTable
    all_source_tables_map = {}
    for t in db.query(SourceMasterTable).all(): all_source_tables_map[str(t.id)] = t
    for t in db.query(SourceBusinessTable).all(): all_source_tables_map[str(t.id)] = t
    for t in db.query(SourceReferenceTable).all(): all_source_tables_map[str(t.id)] = t

    # 5. 从 SourceFieldImport 加载源表和源字段信息
    all_source_fields = db.query(SourceFieldImport).all()
    # source_field_info: {table_en + "_" + field_en: {field_cn, data_type, pk_fk, sys_code, table_cn}}
    source_field_info = {}
    for sf in all_source_fields:
        ten = (sf.table_en or "").strip().lower()
        fen = (sf.field_en or "").strip().lower()
        if ten and fen:
            key = f"{ten}_{fen}"
            source_field_info[key] = {
                "field_cn": sf.field_cn,
                "field_en": sf.field_en,
                "data_type": sf.data_type or "",
                "pk_fk": sf.pk_fk or "",
                "sys_code": sf.sys_code or "",
                "table_en": sf.table_en,
                "table_cn": sf.table_cn,
            }

    # 6. 查找源表关系
    source_rels = db.query(SourceTableRelation).all()

    # 按 scope 分组
    l2_rels = [r for r in source_rels if (r.relation_scope or "").lower() in ("l2", "l2内部")]
    l4_rels = [r for r in source_rels if (r.relation_scope or "").lower() in ("l4", "l4活动")]

    # 7. 构建每个实体的溯源信息
    result = []
    for eid in entity_ids:
        eid_32 = _norm_uuid(eid)
        entity = entities_map.get(eid_32)
        if not entity:
            continue

        concept_chain = []
        if entity.concept_id:
            concept_chain = build_concept_chain(str(entity.concept_id))

        layer_info = {"level": None, "l1": None, "l2": None, "l3": None, "l4": None, "chain": concept_chain}
        for item in concept_chain:
            lv = item.get("level")
            if lv == 1: layer_info["l1"] = item.get("name")
            elif lv == 2: layer_info["l2"] = item.get("name"); layer_info["level"] = "L2"
            elif lv == 3: layer_info["l3"] = item.get("name"); layer_info["level"] = "L3"
            elif lv == 4: layer_info["l4"] = item.get("name"); layer_info["level"] = "L4"

        entity_result = {
            "entity_id": eid_32,
            "entity_name": entity.entity_name,
            "entity_en_name": entity.entity_en_name,
            "entity_code": entity.entity_code,
            "concept_id": _norm_uuid(str(entity.concept_id)) if entity.concept_id else None,
            "properties_schema": entity.properties_schema if isinstance(entity.properties_schema, list) else [],
            "layer_info": layer_info,
            "has_mapping_rule": len(matched_rules) > 0,
            "mapping_rule_count": len(matched_rules),
        }
        result.append(entity_result)

    # 8. 按输入的属性逐条构建溯源信息
    attribute_traces = []
    for field in field_list:
        field_name = field.get("field_name", "")
        entity_id = _norm_uuid(field.get("entity_id", ""))
        attribute_name = field.get("attribute_name", "") or field.get("attribute_en_name", "")
        entity_en_name = field.get("entity_en_name", "")
        attribute_en_name = field.get("attribute_en_name", "")
        entity_name = field.get("entity_name", "")

        entity = entities_map.get(entity_id)
        if not entity:
            continue

        # 查找属性在 properties_schema 中的定义
        prop_def = None
        for prop in (entity.properties_schema or []):
            if isinstance(prop, dict):
                if prop.get("name") == attribute_en_name or prop.get("cnName") == attribute_name:
                    prop_def = prop
                    break

        # 查找字段映射
        attr_key = f"{entity_id}_{attribute_en_name}"
        fms_list = rule_field_mappings.get(attr_key, [])
        
        # 溯源明细信息
        src_field = None
        source_table_en = ""
        source_table_cn = ""
        source_system = ""
        combined_src_field_en = ""
        
        if fms_list:
            all_src_field_ens = []
            for fm_item in fms_list:
                s_tid = fm_item.get("source_table_id")
                s_fen = fm_item.get("source_field_en")
                all_src_field_ens.append(s_fen)
                
                # 尝试定位源表英文名
                table_info = all_source_tables_map.get(s_tid)
                s_ten = table_info.enName if table_info else ""
                
                if s_ten and s_fen:
                    lookup_key = f"{s_ten.strip().lower()}_{s_fen.strip().lower()}"
                    info = source_field_info.get(lookup_key)
                    if info:
                        src_field = info
                        source_table_en = info.get("table_en")
                        source_table_cn = info.get("table_cn")
                        source_system = info.get("sys_code")
                        # 找到一个详细信息就够了
            
            combined_src_field_en = " | ".join(filter(None, all_src_field_ens))

        # 如果没找到映射规则，尝试按属性名全局匹配（兜底）
        if not src_field and attribute_en_name:
            for key, info in source_field_info.items():
                if info.get("field_en", "").lower() == attribute_en_name.lower():
                    src_field = info
                    source_table_en = info.get("table_en")
                    source_table_cn = info.get("table_cn")
                    source_system = info.get("sys_code")
                    combined_src_field_en = info.get("field_en")
                    break

        attribute_traces.append({
            "field_name": field_name,
            "attribute_name": attribute_name,
            "attribute_en_name": attribute_en_name,
            "entity_id": entity_id,
            "entity_name": entity_name or entity.entity_name,
            "entity_en_name": entity_en_name or entity.entity_en_name,
            "entity_code": entity.entity_code,
            "property_definition": prop_def,
            "is_primary_key": prop_def.get("isPrimaryKey", False) if prop_def else (fms_list[0].get("is_pk", False) if fms_list else False),
            "source_system": source_system,
            "source_table_cn": source_table_cn,
            "source_table_en": source_table_en,
            "source_field_cn": src_field.get("field_cn") if src_field else "",
            "source_field_en": combined_src_field_en,
            "source_field_type": src_field.get("data_type") if src_field else "",
            "source_field_pk_fk": src_field.get("pk_fk") if src_field else "",
            "has_source_mapping": src_field is not None or len(fms_list) > 0,
        })

    # 8. 实体间关联关系
    entity_rels = db.query(EntityRelation).filter(
        (EntityRelation.source_entity_id.in_(norm_ids)) | (EntityRelation.target_entity_id.in_(norm_ids))
    ).all()
    inter_entity_relations = []
    norm_entity_ids = {_norm_uuid(e) for e in entity_ids}
    for rel in entity_rels:
        src_id = str(rel.source_entity_id)
        tgt_id = str(rel.target_entity_id)
        if src_id not in norm_entity_ids or tgt_id not in norm_entity_ids:
            continue
        src = entities_map.get(src_id)
        tgt = entities_map.get(tgt_id)
        inter_entity_relations.append({
            "source_id": src_id,
            "source": src.entity_name if src else src_id,
            "source_en_name": src.entity_en_name if src else None,
            "target_id": tgt_id,
            "target": tgt.entity_name if tgt else tgt_id,
            "target_en_name": tgt.entity_en_name if tgt else None,
            "relation": rel.relation_name,
            "join_expr": rel.join_expr,
            "cardinality": rel.cardinality,
        })

    # 9. 来源表间关联关系
    table_relations_grouped = {
        "l2_internal": [],
        "l4_activity": [],
        "other": [],
    }
    for rel in source_rels:
        scope = (rel.relation_scope or "").lower()
        item = {
            "scope": rel.relation_scope,
            "l1": rel.l1,
            "l2": rel.l2,
            "l3": rel.l3,
            "l4": rel.l4,
            "main_table_cn": rel.main_table_cn,
            "main_table_en": rel.main_table_en,
            "related_table_cn": rel.related_table_cn,
            "related_table_en": rel.related_table_en,
            "relation_expr": rel.relation_expr,
            "relation_desc": rel.relation_desc,
            "relation_category": rel.relation_category,
        }
        if scope in ("l2", "l2内部"):
            table_relations_grouped["l2_internal"].append(item)
        elif scope in ("l4", "l4活动"):
            table_relations_grouped["l4_activity"].append(item)
        else:
            table_relations_grouped["other"].append(item)

    return {
        "code": 200,
        "data": {
            "entities": result,
            "inter_entity_relations": inter_entity_relations,
            "attribute_traces": attribute_traces,
            "table_relations_grouped": table_relations_grouped,
        }
    }

