from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from ..models.base import Concept, Entity, EntityRelation, EntityConceptLink, ConceptRelation, EntityModeling, EntityInitData, EntityMappingRule
import pandas as pd
import io
import json
from ..schemas.concept import (
    ConceptCreate,
    ConceptResponse,
    ConceptUpdate,
    EntityCreate,
    EntityResponse,
    EntityUpdate,
    EntityRelationCreate,
    EntityRelationUpdate,
    EntityRelationResponse,
)
from ..core.database import get_db
from pydantic import BaseModel
import uuid
import re

router = APIRouter()

ENTITY_EXPLANATION_SPLIT_RE = re.compile(r"[,，、/|；;\n\r\t]+")
ENTITY_EXPLANATION_SUFFIXES = [
    "信息明细实体",
    "信息实体",
    "明细实体",
    "档案实体",
    "业务实体",
    "数据实体",
    "实体",
    "信息明细表",
    "明细表",
    "信息表",
    "档案表",
    "数据表",
    "主数据表",
    "主表",
    "信息明细",
    "明细",
    "档案",
    "信息",
    "资料",
    "数据",
    "表",
]
QUERY_ENTITY_PROPERTY_HINTS = ["编号", "编码", "名称", "证件", "地址", "类型", "状态", "单号", "申请", "记录"]


class EntityExplanationSuggestRequest(BaseModel):
    entity_name: Optional[str] = None
    concept_name: Optional[str] = None
    parent_concept_name: Optional[str] = None
    description: Optional[str] = None
    entity_explanation: Optional[str] = None
    properties_schema: Optional[List[Dict[str, Any]]] = None


def _split_entity_explanation(value: Any) -> List[str]:
    if value is None:
        return []
    raw_items = value if isinstance(value, list) else ENTITY_EXPLANATION_SPLIT_RE.split(str(value))
    result: List[str] = []
    seen = set()
    for item in raw_items:
        text = str(item or "").strip()
        if not text or text.lower() == "nan" or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _expand_entity_explanation_terms(term: str) -> List[str]:
    cleaned = re.sub(r"[（(].*?[)）]", "", str(term or "")).strip()
    if not cleaned:
        return []
    queue = [cleaned]
    result: List[str] = []
    seen = set()
    while queue:
        current = queue.pop(0).strip()
        if not current or current in seen:
            continue
        seen.add(current)
        result.append(current)
        for suffix in ENTITY_EXPLANATION_SUFFIXES:
            if current.endswith(suffix) and len(current) > len(suffix) + 1:
                queue.append(current[: -len(suffix)].strip())
    return result


def _get_property_label(prop: Dict[str, Any]) -> str:
    return str(
        prop.get("cnName")
        or prop.get("label")
        or prop.get("display_name")
        or prop.get("name_zh")
        or prop.get("name")
        or prop.get("field_name")
        or ""
    ).strip()


def _extract_property_keyword_options(properties_schema: Any) -> List[str]:
    props = properties_schema if isinstance(properties_schema, list) else []
    prioritized: List[str] = []
    others: List[str] = []
    for prop in props:
        if not isinstance(prop, dict):
            continue
        label = _get_property_label(prop)
        if not label:
            continue
        if any(
            bool(prop.get(flag))
            for flag in ["enable_query_entity", "is_alias_key", "is_key_attribute", "key_attribute", "keyword", "isPrimaryKey", "is_primary_key"]
        ) or any(hint in label for hint in QUERY_ENTITY_PROPERTY_HINTS):
            prioritized.append(label)
        else:
            others.append(label)
    return _split_entity_explanation(prioritized + others)


def _build_entity_explanation_suggestions(payload: EntityExplanationSuggestRequest) -> Dict[str, Any]:
    seeds: List[str] = []
    reasons: List[str] = []
    seed_pairs = [
        ("实体名称", payload.entity_name),
        ("所属分类", payload.concept_name),
        ("上级分类", payload.parent_concept_name),
    ]
    for source, raw_value in seed_pairs:
        parts = _split_entity_explanation(raw_value)
        if not parts:
            continue
        seeds.extend(parts)
        reasons.append(f"来自{source}")

    description_parts = [
        item
        for item in _split_entity_explanation(payload.description)
        if 1 < len(item) <= 20 and not any(ch in item for ch in [":", "：", "，", ",", "。"])
    ]
    if description_parts:
        seeds.extend(description_parts[:3])
        reasons.append("来自描述")

    existing_parts = _split_entity_explanation(payload.entity_explanation)
    if existing_parts:
        seeds.extend(existing_parts)
        reasons.append("合并当前已录入解释")

    suggestions: List[str] = []
    for seed in seeds:
        suggestions.extend(_expand_entity_explanation_terms(seed))

    field_keyword_options = _extract_property_keyword_options(payload.properties_schema)
    recommended_field_keywords = field_keyword_options[:12]
    return {
        "suggestions": _split_entity_explanation(suggestions)[:20],
        "field_keyword_options": field_keyword_options,
        "recommended_field_keywords": recommended_field_keywords,
        "reason_summary": "；".join(reasons) if reasons else "基于实体名称、分类和描述自动提取",
    }

def _norm_uuid_str(v: Optional[str], field_name: str = "id") -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    if len(s) == 32 and re.fullmatch(r"[0-9a-fA-F]{32}", s):
        s = f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
    try:
        uuid.UUID(s)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} format")
    return s


def _build_matrix_relation_name(master_entity: Optional[Entity], activity_entity: Optional[Entity]) -> str:
    if master_entity and activity_entity:
        return f"{master_entity.entity_name}主数据实体打点到{activity_entity.entity_name}活动实体"
    return "打点维护关系"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or str(value).strip() == "" or str(value).strip().lower() == "nan":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_system_names(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    raw_items = value if isinstance(value, list) else re.split(r"[,，、;\n\r]+", str(value))
    result: List[str] = []
    seen = set()
    for item in raw_items:
        text = str(item).strip()
        if not text or text.lower() == "nan" or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result or None


def _sort_concepts(items: List[Concept]) -> List[Concept]:
    return sorted(
        items,
        key=lambda item: (
            item.level or 0,
            item.area_index or 0,
            item.sort_order or 0,
            item.name or "",
        ),
    )


def _sort_entities(items: List[Entity]) -> List[Entity]:
    return sorted(
        items,
        key=lambda item: (
            item.sort_order or 0,
            item.entity_name or "",
            item.entity_code or "",
        ),
    )


def _update_entity_concept_links(db: Session, entity_id: str, concept_ids: List[str], mode: Optional[str] = None):
    """更新实体的多概念关联，支持模式隔离"""
    # 1. 确定要清理的关联范围
    query = db.query(EntityConceptLink).filter(EntityConceptLink.entity_id == entity_id)
    
    if mode == 'master':
        # 仅清理关联到 L1/L2 的链接
        target_concept_ids = [str(c.id) for c in db.query(Concept.id).filter(Concept.level.in_([1, 2])).all()]
        query = query.filter(EntityConceptLink.concept_id.in_(target_concept_ids))
    elif mode == 'activity':
        # 仅清理关联到 L0/L3/L4 的链接
        target_concept_ids = [str(c.id) for c in db.query(Concept.id).filter(Concept.level.in_([0, 3, 4])).all()]
        query = query.filter(EntityConceptLink.concept_id.in_(target_concept_ids))
    
    query.delete(synchronize_session=False)
    
    # 2. 建立新关联（去重）
    unique_cids = list(set(concept_ids or []))
    for cid in unique_cids:
        cid_norm = _norm_uuid_str(cid, "concept_id")
        if cid_norm:
            db.add(EntityConceptLink(entity_id=entity_id, concept_id=cid_norm))
    db.flush()


class EntityEnNameAutoFillRequest(BaseModel):
    only_empty: bool = True

@router.post("/sync-hierarchy")
def sync_hierarchy_to_neo4j():
    """一键同步业务链层级到 Neo4j

    包含：
      - ROOT_MD / ROOT_BZ 链根节点
      - L1/L2/L2X/L3/L4/L4X 全部 Category 节点
      - HAS_PARENT 父子关系
      - BELONGS_TO_CHAIN 链归属关系
      - RELATES_TO 跨链关系（含传递闭包派生）
      - RELATED_BY 反向关系（图谱可视化用）

    数据源：backend/data/business_chain_spec.yaml
    """
    try:
        import yaml
        from pathlib import Path
        from ..services.graph_query_neo4j import _get_driver

        spec_path = Path(__file__).parent.parent.parent / "data" / "business_chain_spec.yaml"
        if not spec_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"业务链 spec 不存在: {spec_path}",
            )

        spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))

        driver = _get_driver()
        with driver.session() as s:
            # 1. 清旧 L4/L4X
            s.run("MATCH (n) WHERE n.level IN ['L4', 'L4X'] DETACH DELETE n").consume()

            # 2. 链根
            s.run("""
                MERGE (r:ChainRoot:Category {code: 'ROOT_MD'})
                SET r.name = '主数据链根', r.level = 'ROOT', r.chain_type = 'MD'
            """).consume()
            s.run("""
                MERGE (r:ChainRoot:Category {code: 'ROOT_BZ'})
                SET r.name = '业务链根', r.level = 'ROOT', r.chain_type = 'BZ'
            """).consume()

            # 3. L1/L2/L2X → ROOT_MD, L3 → ROOT_BZ
            s.run("""
                MATCH (n:Category) WHERE n.level IN ['L1', 'L2', 'L2X']
                MATCH (r:ChainRoot {code: 'ROOT_MD'})
                MERGE (n)-[:BELONGS_TO_CHAIN]->(r)
            """).consume()
            s.run("""
                MATCH (n:Category) WHERE n.level = 'L3'
                MATCH (r:ChainRoot {code: 'ROOT_BZ'})
                MERGE (n)-[:BELONGS_TO_CHAIN]->(r)
            """).consume()

            # 4. L4 + HAS_PARENT → L3
            l4_count = 0
            for l3_code, l3_spec in spec.items():
                for l4 in l3_spec.get("L4", []):
                    s.run("""
                        MERGE (n:Category:Entity {code: $code})
                        SET n.level = 'L4',
                            n.name = $name,
                            n.chain_type = 'BZ',
                            n.entity_type = 'category'
                    """, code=l4["code"], name=l4["name"])
                    s.run("""
                        MATCH (l4:Category {code: $l4}), (l3:Category {code: $l3})
                        MERGE (l4)-[:HAS_PARENT]->(l3)
                    """, l4=l4["code"], l3=l3_code)
                    l4_count += 1

            # 5. L4X + HAS_PARENT → L4 + RELATES_TO → L2X
            l4x_count = 0
            rel_count = 0
            for l3_code, l3_spec in spec.items():
                for l4x in l3_spec.get("L4X", []):
                    s.run("""
                        MERGE (n:Category:Entity {code: $code})
                        SET n.level = 'L4X',
                            n.name = $name,
                            n.chain_type = 'BZ',
                            n.entity_type = 'leaf'
                    """, code=l4x["code"], name=l4x["name"])
                    s.run("""
                        MATCH (l4x:Category {code: $l4x}), (l4:Category {code: $l4})
                        MERGE (l4x)-[:HAS_PARENT]->(l4)
                    """, l4x=l4x["code"], l4=l4x["parent"])
                    l4x_count += 1

                    if l4x.get("relates_to"):
                        s.run("""
                            MATCH (l4x:Category {code: $l4x}), (l2x:Category {code: $l2x})
                            MERGE (l4x)-[r:RELATES_TO]->(l2x)
                            SET r.created_at = timestamp(),
                                r.relation_category = 'cross_chain'
                        """, l4x=l4x["code"], l2x=l4x["relates_to"])
                        rel_count += 1

            # 6. 传递闭包
            closure_count = s.run("""
                MATCH (l4x:Category)-[:RELATES_TO]->(l2x:Category)
                MATCH (l4x)-[:HAS_PARENT*1..2]->(l4:Category)
                MATCH (l2x)-[:HAS_PARENT*1..2]->(l2:Category)
                WHERE l4.level IN ['L4', 'L3'] AND l2.level IN ['L2', 'L1']
                MERGE (l4)-[r2:RELATES_TO]->(l2)
                ON CREATE SET r2.derived_from = 'transitive_closure',
                              r2.relation_category = 'cross_chain_derived'
                RETURN count(r2) AS cnt
            """).single()["cnt"]

            # 7. 反向
            back_count = s.run("""
                MATCH (a)-[r:RELATES_TO]->(b)
                MERGE (b)-[r2:RELATED_BY]->(a)
                ON CREATE SET r2.derived_from = 'reverse'
                RETURN count(r2) AS cnt
            """).single()["cnt"]

        return {
            "message": "Successfully synced business chain hierarchy to Neo4j",
            "l4_count": l4_count,
            "l4x_count": l4x_count,
            "cross_chain_relations": rel_count,
            "transitive_closure_count": closure_count,
            "reverse_relations": back_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"层级同步失败: {e}") from e


@router.post("/sync")
def sync_to_neo4j(db: Session = Depends(get_db)):
    """一键同步 Postgres 元数据到 Neo4j"""
    try:
        from ..services.graph_sync import Neo4jSyncService
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Neo4j sync dependency is not installed",
        ) from exc

    sync_service = Neo4jSyncService()
    try:
        # 1. 同步所有概念
        concepts = db.query(Concept).all()
        for c in concepts:
            sync_service.sync_concept(
                concept_id=str(c.id),
                name=c.name,
                level=c.level,
                parent_id=str(c.parent_id) if c.parent_id else None
            )
        
        # 2. 同步所有实体
        entities = db.query(Entity).all()
        for e in entities:
            sync_service.sync_entity(
                entity_id=str(e.id),
                name=e.entity_name,
                concept_id=str(e.concept_id)
            )
        
        return {"message": "Successfully synced to Neo4j", "concepts_count": len(concepts), "entities_count": len(entities)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")
    finally:
        sync_service.close()

@router.get("/graph/data")
def get_graph_data(db: Session = Depends(get_db)):
    """从本地关系型数据库生成图谱数据，概念间不再自动补边，仅展示实体关系"""
    try:
        nodes = []
        edges = []
        
        # 仅获取 level > 0 的概念（过滤业务域分类节点）
        concepts = _sort_concepts(db.query(Concept).filter(Concept.level > 0).all())
        concept_map = {str(c.id): c for c in concepts}
        
        for c in concepts:
            node_data = {
                "id": str(c.id),
                "name": c.name,  # 为了兼容 RightPanel 内部逻辑
                "label": c.name,
                "type": "concept",
                "level": c.level,
                "description": c.description,
                "system_names": c.system_names or [],
            }
            
            if c.level in [2, 4]:
                # 通过中间表查询关联的所有实体
                entity_links_for_c = db.query(EntityConceptLink).filter(EntityConceptLink.concept_id == c.id).all()
                entity_ids_for_c = [link.entity_id for link in entity_links_for_c]
                entities_for_c = db.query(Entity).filter(Entity.id.in_(entity_ids_for_c)).all() if entity_ids_for_c else []
                
                node_data["entities"] = [
                    {
                        "id": str(e.id), 
                        "concept_id": str(e.concept_id),
                        "entity_code": e.entity_code, 
                        "entity_name": e.entity_name,
                        "entity_explanation": e.entity_explanation,
                        "sort_order": e.sort_order or 0,
                        "description": e.description,
                        "is_main_table": e.is_main_table,
                        "data_layer": e.data_layer,
                        "landing_table_en_name": e.entity_en_name,
                        "properties_schema": e.properties_schema
                    }
                    for e in _sort_entities(entities_for_c)
                ]
                
            nodes.append(node_data)
            
        # 只显示在 kg_entity_concept_links 里有挂载的主数据(L2)/业务活动(L4)实体
        # 与主数据建模页面一致，避免展示 concept_id 关联但未挂载的 seed 实体，level 兜底排除 data_entity
        _linked_entity_ids = [link.entity_id for link in db.query(EntityConceptLink).all()]
        _ma_cids = {c.id for c in concepts if c.level in (2, 4)}
        entities = _sort_entities(
            db.query(Entity).filter(
                Entity.id.in_(_linked_entity_ids),
                Entity.concept_id.in_(_ma_cids)
            ).all()
        ) if _linked_entity_ids and _ma_cids else []
        for e in entities:
            e_id_str = str(e.id)
            entity_category = "data_entity"
            if e.concept_id and str(e.concept_id) in concept_map:
                entity_concept = concept_map[str(e.concept_id)]
                if entity_concept.level == 2:
                    entity_category = "master_entity"
                elif entity_concept.level == 4:
                    entity_category = "activity_entity"
            nodes.append({
                "id": e_id_str,
                "label": e.entity_name,
                "type": "entity",
                "entity_category": entity_category,
                "concept_id": str(e.concept_id),
                "entity_id": e_id_str,
                "entity_name": e.entity_name,
                "entity_code": e.entity_code,
                "entity_en_name": e.entity_en_name,
                "entity_explanation": e.entity_explanation,
                "description": e.description,
                "is_main_table": e.is_main_table,
                "data_layer": e.data_layer,
                "sort_order": e.sort_order or 0,
                "source_mode": e.source_mode or "physical_table",
                "integration_sql": e.integration_sql,
                "doris_catalog": e.doris_catalog,
                "data_source_id": str(e.data_source_id) if e.data_source_id else None,
                "landing_table_en_name": e.entity_en_name,
                "properties_schema": e.properties_schema,
                "concept_ids": [str(l.concept_id) for l in db.query(EntityConceptLink).filter(EntityConceptLink.entity_id == e.id).all()]
            })
            
            # 实体与概念的关联边：只用 kg_entity_concept_links（与主数据建模一致，不用 concept_id）
            links = db.query(EntityConceptLink).filter(EntityConceptLink.entity_id == e.id).all()
            for link in links:
                edges.append({
                    "id": f"ec-link-{e_id_str}-{link.concept_id}",
                    "source": e_id_str,
                    "target": str(link.concept_id),
                    "label": "所属",
                    "edge_type": "concept_entity_link",
                })
            
        entity_relations = db.query(EntityRelation).all()
        for rel in entity_relations:
            edge_type = "entity_generation" if (rel.relation_category or "") == "打点维护" else "entity_relation"
            edges.append({
                "id": f"er-{rel.id}",
                "source": str(rel.source_entity_id),
                "target": str(rel.target_entity_id),
                "label": "生成" if edge_type == "entity_generation" else (rel.relation_name or "实体关系"),
                "edge_type": edge_type,
                "relation_name": rel.relation_name,
                "relation_category": rel.relation_category or "手工维护",
                "direction": rel.direction or "forward",
                "cardinality": rel.cardinality or "N:N",
                "source_field_name": rel.source_field_name,
                "target_field_name": rel.target_field_name,
                "join_expr": rel.join_expr,
                "description": rel.description,
                "remark": rel.remark,
            })
        
        # 概念间层级关系（L2->L1, L4->L3 主数据/业务活动建模）
        for c in concepts:
            if c.parent_id and str(c.parent_id) in concept_map:
                parent = concept_map[str(c.parent_id)]
                child_lv = {1:'L1',2:'L2',3:'L3',4:'L4'}.get(c.level,'')
                parent_lv = {1:'L1',2:'L2',3:'L3',4:'L4'}.get(parent.level,'')
                edges.append({
                    "id": f"cp-{c.id}-{c.parent_id}",
                    "source": str(c.id),
                    "target": str(c.parent_id),
                    "label": "层级",
                    "edge_type": "concept_hierarchy",
                    "child_level": child_lv,
                    "parent_level": parent_lv,
                })
        
        # 跨链关系已清除（用户要求：关系只查维护的关系，不展示初始化/跨链）

        return {"nodes": nodes, "edges": edges}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate graph data: {str(e)}")


@router.get("/graph/subgraph-by-l1/{l1_id}")
def get_subgraph_by_l1(
    l1_id: str,
    db: Session = Depends(get_db),
):
    """按 L1 行业域过滤子图：返回该 L1 下的 L2、实体、关系

    用途：力导向图按 L1 顶点过滤（如选"客户"展示客户域子图）。

    Args:
        l1_id: L1 概念节点 ID

    Return:
        {nodes: [...], edges: [...], meta: {l1_id, l1_name, ...}}
    """
    try:
        l1 = db.query(Concept).filter(Concept.id == l1_id, Concept.level == 1).first()
        if not l1:
            raise HTTPException(status_code=404, detail=f"L1 不存在: {l1_id}")

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        node_ids = set()

        # L1 节点
        nodes.append({
            "id": str(l1.id), "name": l1.name, "label": l1.name,
            "type": "concept", "level": 1, "description": l1.description,
        })
        node_ids.add(str(l1.id))

        # L2 节点（parent_id = L1）
        l2_list = db.query(Concept).filter(Concept.parent_id == l1.id, Concept.level == 2).all()
        l2_ids = [str(c.id) for c in l2_list]
        for c in l2_list:
            nodes.append({
                "id": str(c.id), "name": c.name, "label": c.name,
                "type": "concept", "level": 2, "description": c.description,
            })
            node_ids.add(str(c.id))
            # L2 → L1 层级边
            edges.append({
                "id": f"cp-{c.id}-{l1.id}",
                "source": str(c.id), "target": str(l1.id),
                "label": "层级", "edge_type": "concept_hierarchy",
                "child_level": "L2", "parent_level": "L1",
            })

        # 实体节点（concept_id in L2_ids）
        entities = db.query(Entity).filter(Entity.concept_id.in_(l2_ids)).all() if l2_ids else []
        # 多对多挂载（EntityConceptLink）
        link_concept_ids = set(l2_ids)
        extra_links = db.query(EntityConceptLink).filter(EntityConceptLink.concept_id.in_(link_concept_ids)).all() if link_concept_ids else []
        extra_entity_ids = {str(l.entity_id) for l in extra_links}
        if extra_entity_ids:
            extra_entities = db.query(Entity).filter(Entity.id.in_(list(extra_entity_ids))).all()
            # 合并去重
            existing = {str(e.id) for e in entities}
            for e in extra_entities:
                if str(e.id) not in existing:
                    entities.append(e)

        entity_id_set = {str(e.id) for e in entities}

        for e in entities:
            entity_category = "data_entity"
            if e.concept_id and str(e.concept_id) in {str(c.id) for c in l2_list}:
                entity_category = "master_entity"
            nodes.append({
                "id": str(e.id), "label": e.entity_name, "type": "entity",
                "entity_category": entity_category,
                "concept_id": str(e.concept_id) if e.concept_id else None,
                "entity_id": str(e.id),
                "entity_name": e.entity_name,
                "entity_code": e.entity_code, "entity_en_name": e.entity_en_name,
                "entity_explanation": e.entity_explanation,
                "description": e.description,
                "is_main_table": e.is_main_table,
                "data_layer": e.data_layer,
                "source_mode": e.source_mode or "physical_table",
                "integration_sql": e.integration_sql,
                "doris_catalog": e.doris_catalog,
                "data_source_id": str(e.data_source_id) if e.data_source_id else None,
                "landing_table_en_name": e.entity_en_name,
                "properties_schema": e.properties_schema,
            })
            node_ids.add(str(e.id))
            # 实体 -> L2 所属边
            if e.concept_id and str(e.concept_id) in node_ids:
                edges.append({
                    "id": f"ec-{e.id}-{e.concept_id}",
                    "source": str(e.id), "target": str(e.concept_id),
                    "label": "所属", "edge_type": "concept_entity_link",
                })

        # === 通过实体关系查业务活动树（L0->L3->L4->L4实体）===
        # 概念体系是两套独立树：主数据(L1->L2->L2实体) + 业务活动(L0->L3->L4->L4实体)
        # 两套树通过实体关系（L2实体->L4实体，含打点维护+手工维护）连接
        if entity_id_set:
            # 查所有 source 在集合内的关系，按 target 实体的 concept level=4 过滤
            all_src_rels = db.query(EntityRelation).filter(
                EntityRelation.source_entity_id.in_(list(entity_id_set)),
            ).all()
            # 收集 target 实体并查其 concept level
            tgt_ids = {str(r.target_entity_id) for r in all_src_rels}
            l4_entity_ids = set()
            matrix_rels = []
            if tgt_ids:
                tgt_entities = db.query(Entity).filter(Entity.id.in_(list(tgt_ids))).all()
                tgt_concept_ids = {str(e.concept_id) for e in tgt_entities if e.concept_id}
                tgt_concepts = {str(c.id): c for c in db.query(Concept).filter(
                    Concept.id.in_(list(tgt_concept_ids))
                ).all()} if tgt_concept_ids else {}
                for e in tgt_entities:
                    c = tgt_concepts.get(str(e.concept_id))
                    if c and c.level == 4:
                        l4_entity_ids.add(str(e.id))
                # 筛选指向 L4 实体的关系
                l4_entity_id_strs = l4_entity_ids
                matrix_rels = [r for r in all_src_rels if str(r.target_entity_id) in l4_entity_id_strs]

            if l4_entity_ids:
                l4_entities = db.query(Entity).filter(Entity.id.in_(list(l4_entity_ids))).all()
                # L4 概念
                l4_concept_ids = {str(e.concept_id) for e in l4_entities if e.concept_id}
                l4_concepts = db.query(Concept).filter(
                    Concept.id.in_(list(l4_concept_ids)), Concept.level == 4
                ).all() if l4_concept_ids else []
                # L3 概念
                l3_concept_ids = {str(c.parent_id) for c in l4_concepts if c.parent_id}
                l3_concepts = db.query(Concept).filter(
                    Concept.id.in_(list(l3_concept_ids)), Concept.level == 3
                ).all() if l3_concept_ids else []
                # L0 业务域
                l0_concept_ids = {str(c.parent_id) for c in l3_concepts if c.parent_id}
                l0_concepts = db.query(Concept).filter(
                    Concept.id.in_(list(l0_concept_ids)), Concept.level == 0
                ).all() if l0_concept_ids else []

                # L0 业务域节点
                for c in l0_concepts:
                    if str(c.id) not in node_ids:
                        nodes.append({
                            "id": str(c.id), "name": c.name, "label": c.name,
                            "type": "concept", "level": 0, "description": c.description,
                        })
                        node_ids.add(str(c.id))
                # L3 节点 + L3->L0 层级边
                for c in l3_concepts:
                    if str(c.id) not in node_ids:
                        nodes.append({
                            "id": str(c.id), "name": c.name, "label": c.name,
                            "type": "concept", "level": 3, "description": c.description,
                        })
                        node_ids.add(str(c.id))
                    if str(c.parent_id) in node_ids:
                        edges.append({
                            "id": f"cp-{c.id}-{c.parent_id}",
                            "source": str(c.id), "target": str(c.parent_id),
                            "label": "层级", "edge_type": "concept_hierarchy",
                            "child_level": "L3", "parent_level": "L0",
                        })
                # L4 节点 + L4->L3 层级边
                for c in l4_concepts:
                    if str(c.id) not in node_ids:
                        nodes.append({
                            "id": str(c.id), "name": c.name, "label": c.name,
                            "type": "concept", "level": 4, "description": c.description,
                        })
                        node_ids.add(str(c.id))
                    if str(c.parent_id) in node_ids:
                        edges.append({
                            "id": f"cp-{c.id}-{c.parent_id}",
                            "source": str(c.id), "target": str(c.parent_id),
                            "label": "层级", "edge_type": "concept_hierarchy",
                            "child_level": "L4", "parent_level": "L3",
                        })
                # L4 实体节点 + 实体->L4概念边
                for e in l4_entities:
                    if str(e.id) not in node_ids:
                        nodes.append({
                            "id": str(e.id), "label": e.entity_name, "type": "entity",
                            "entity_category": "activity_entity",
                            "concept_id": str(e.concept_id) if e.concept_id else None,
                            "entity_id": str(e.id),
                            "entity_name": e.entity_name,
                            "entity_code": e.entity_code, "entity_en_name": e.entity_en_name,
                            "entity_explanation": e.entity_explanation,
                            "description": e.description,
                            "is_main_table": e.is_main_table,
                            "data_layer": e.data_layer,
                            "source_mode": e.source_mode or "physical_table",
                            "integration_sql": e.integration_sql,
                            "doris_catalog": e.doris_catalog,
                            "data_source_id": str(e.data_source_id) if e.data_source_id else None,
                            "landing_table_en_name": e.entity_en_name,
                            "properties_schema": e.properties_schema,
                        })
                        node_ids.add(str(e.id))
                        entity_id_set.add(str(e.id))
                    if e.concept_id and str(e.concept_id) in node_ids:
                        edges.append({
                            "id": f"ec-{e.id}-{e.concept_id}",
                            "source": str(e.id), "target": str(e.concept_id),
                            "label": "所属", "edge_type": "concept_entity_link",
                        })
                # 打点关系边（L2实体 -> L4实体）
                for r in matrix_rels:
                    if str(r.target_entity_id) in node_ids:
                        edges.append({
                            "id": f"er-{r.id}",
                            "source": str(r.source_entity_id), "target": str(r.target_entity_id),
                            "label": r.relation_name or "生成",
                            "edge_type": "entity_generation",
                            "relation_name": r.relation_name,
                            "relation_category": r.relation_category or "打点维护",
                            "direction": r.direction or "forward",
                            "cardinality": r.cardinality or "N:N",
                            "source_field_name": r.source_field_name,
                            "target_field_name": r.target_field_name,
                            "join_expr": r.join_expr,
                            "description": r.description,
                            "remark": r.remark,
                        })

        # 实体间关系（两端都在当前实体集合内）
        if entity_id_set:
            rels = db.query(EntityRelation).filter(
                EntityRelation.source_entity_id.in_(list(entity_id_set)),
                EntityRelation.target_entity_id.in_(list(entity_id_set)),
            ).all()
            for rel in rels:
                edge_type = "entity_generation" if (rel.relation_category or "") == "打点维护" else "entity_relation"
                edges.append({
                    "id": f"er-{rel.id}",
                    "source": str(rel.source_entity_id), "target": str(rel.target_entity_id),
                    "label": "生成" if edge_type == "entity_generation" else (rel.relation_name or "实体关系"),
                    "edge_type": edge_type,
                    "relation_name": rel.relation_name,
                    "relation_category": rel.relation_category or "手工维护",
                    "direction": rel.direction or "forward",
                    "cardinality": rel.cardinality or "N:N",
                    "source_field_name": rel.source_field_name,
                    "target_field_name": rel.target_field_name,
                    "join_expr": rel.join_expr,
                    "description": rel.description,
                    "remark": rel.remark,
                })

        return {
            "nodes": nodes, "edges": edges,
            "meta": {
                "l1_id": str(l1.id), "l1_name": l1.name,
                "node_count": len(nodes), "edge_count": len(edges),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 L1 子图失败: {str(e)}")


@router.get("/graph/neo4j-data")
def get_neo4j_graph_data():
    """从 Neo4j 图数据库生成力导图数据

    节点：Category（L1/L2/L3/L4 + L2X/L4X 实体）
    边：
      - HAS_PARENT（L2->L1, L4->L3, L2X->L2, L4X->L4）
      - RELATED_BY（L2->L3 跨链抽象）
      - RELATES_TO（L2X->L4X 打点维护）
    """
    try:
        from app.services.graph_query_neo4j import _get_driver
        driver = _get_driver()
        nodes = []
        edges = []
        node_ids = set()

        with driver.session() as s:
            # 1. 查所有 Category 节点（只取有效层级，过滤脏数据）
            valid_levels = ["L1", "L2", "L3", "L4", "L2X", "L4X"]
            rows = s.run("""
                MATCH (c:Category)
                WHERE c.level IN $validLevels
                RETURN c.code AS code, c.name AS name, c.level AS level,
                       c.concept_id AS concept_id, c.description AS description
                ORDER BY c.level, c.code
            """, validLevels=valid_levels).data()

            for r in rows:
                code = r.get("code") or ""
                level = r.get("level") or ""
                name = r.get("name") or code
                # 根据层级推断类型
                if level in ("L1", "L2", "L3", "L4"):
                    ntype = "concept"
                else:
                    ntype = "entity"
                # 标准化层级标签
                level_num = {"L1": 1, "L2": 2, "L3": 3, "L4": 4}.get(level, 0)
                nodes.append({
                    "id": code,
                    "label": f"{level} {name}" if level else name,
                    "name": name,
                    "type": ntype,
                    "level": level_num,
                    "level_label": level,
                    "code": code,
                    "concept_id": r.get("concept_id"),
                    "description": r.get("description") or "",
                })
                node_ids.add(code)

            # 2. 查 HAS_PARENT 边（层级关系）
            rows = s.run("""
                MATCH (a:Category)-[:HAS_PARENT]->(b:Category)
                RETURN a.code AS src, b.code AS tgt, a.level AS src_lv, b.level AS tgt_lv
            """).data()
            for r in rows:
                src, tgt = r.get("src"), r.get("tgt")
                if src in node_ids and tgt in node_ids:
                    edges.append({
                        "id": f"hp-{src}-{tgt}",
                        "source": src,
                        "target": tgt,
                        "label": "层级",
                        "edge_type": "concept_hierarchy",
                        "child_level": r.get("src_lv"),
                        "parent_level": r.get("tgt_lv"),
                    })

            # 3. 查 RELATED_BY 边（L2-L3 跨链抽象）
            rows = s.run("""
                MATCH (a:Category)-[r:RELATED_BY]->(b:Category)
                RETURN a.code AS src, b.code AS tgt,
                       r.rel_type AS rel_type, r.derived_from AS derived_from
            """).data()
            for r in rows:
                src, tgt = r.get("src"), r.get("tgt")
                if src in node_ids and tgt in node_ids:
                    edges.append({
                        "id": f"cc-{src}-{tgt}",
                        "source": src,
                        "target": tgt,
                        "label": "跨链",
                        "edge_type": "concept_cross_chain",
                        "relation_name": "跨链抽象",
                        "derived_from": r.get("derived_from") or "",
                    })

            # 4. 查 RELATES_TO 边（L2X-L4X 打点维护）
            rows = s.run("""
                MATCH (a:Category)-[r:RELATES_TO]->(b:Category)
                RETURN a.code AS src, b.code AS tgt, r.relation_name AS rname
            """).data()
            for r in rows:
                src, tgt = r.get("src"), r.get("tgt")
                if src in node_ids and tgt in node_ids:
                    edges.append({
                        "id": f"rt-{src}-{tgt}",
                        "source": src,
                        "target": tgt,
                        "label": r.get("rname") or "打点维护",
                        "edge_type": "entity_generation",
                    })

        return {"nodes": nodes, "edges": edges, "source": "neo4j"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Neo4j graph data: {str(e)}")


@router.post("/concepts", response_model=ConceptResponse)
def create_concept(concept: ConceptCreate, db: Session = Depends(get_db)):
    # 最新层级约束：业务域(level=0)无 parent；L1 无 parent；L2->L1；L3->业务域；L4->L3
    parent_level_map = {
        0: None,
        1: None,
        2: 1,
        3: 0,
        4: 3,
    }
    expected_parent_level = parent_level_map.get(concept.level)
    if expected_parent_level is None:
        if concept.parent_id is not None:
            raise HTTPException(status_code=400, detail=f"Level {concept.level} concept should not have parent_id")
    else:
        if concept.parent_id is None:
            raise HTTPException(status_code=400, detail=f"L{concept.level} concept must have parent_id")
        parent_id = _norm_uuid_str(concept.parent_id, "parent_id")
        parent = db.query(Concept).filter(Concept.id == parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="Parent concept not found")
        if parent.level != expected_parent_level:
            expected_label = "业务域" if expected_parent_level == 0 else f"L{expected_parent_level}"
            raise HTTPException(status_code=400, detail=f"L{concept.level} parent must be {expected_label}")

    data = concept.dict()
    if data.get("parent_id") is not None:
        data["parent_id"] = _norm_uuid_str(data.get("parent_id"), "parent_id")
    data["system_names"] = _normalize_system_names(data.get("system_names")) if concept.level == 3 else None
    if not data.get("area_index"):
        if concept.level in [0, 1]:
            # 根下新增顶层节点默认同序递增
            max_area = db.query(Concept).filter(Concept.level == concept.level).count()
            data["area_index"] = max_area + 1
        else:
            parent = db.query(Concept).filter(Concept.id == data.get("parent_id")).first()
            data["area_index"] = parent.area_index if parent else 1
    if data.get("sort_order") is None:
        sibling_query = db.query(func.max(Concept.sort_order)).filter(
            Concept.level == concept.level,
            Concept.parent_id == data.get("parent_id"),
        )
        data["sort_order"] = (sibling_query.scalar() or 0) + 1

    db_concept = Concept(**data)
    db.add(db_concept)
    db.commit()
    db.refresh(db_concept)
    return db_concept


@router.put("/concepts/{concept_id}", response_model=ConceptResponse)
def update_concept(concept_id: str, payload: ConceptUpdate, db: Session = Depends(get_db)):
    concept_id = _norm_uuid_str(concept_id, "concept_id") or concept_id
    db_concept = db.query(Concept).filter(Concept.id == concept_id).first()
    if not db_concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    update_data = payload.dict(exclude_unset=True)
    if "system_names" in update_data:
        update_data["system_names"] = _normalize_system_names(update_data.get("system_names")) if db_concept.level == 3 else None
    for k, v in update_data.items():
        setattr(db_concept, k, v)
    db.commit()
    db.refresh(db_concept)
    return db_concept


@router.delete("/concepts/{concept_id}")
def delete_concept(concept_id: str, db: Session = Depends(get_db)):
    concept_id = _norm_uuid_str(concept_id, "concept_id") or concept_id
    db_concept = db.query(Concept).filter(Concept.id == concept_id).first()
    if not db_concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    child_count = db.query(Concept).filter(Concept.parent_id == concept_id).count()
    if child_count > 0:
        raise HTTPException(status_code=400, detail="当前概念下存在子概念，禁止删除")

    entity_count = db.query(Entity).filter(Entity.concept_id == concept_id).count()
    if entity_count > 0:
        raise HTTPException(status_code=400, detail="当前概念下存在数据实体，禁止删除")

    db.delete(db_concept)
    db.commit()
    return {"code": 200, "message": "deleted"}

@router.get("/concepts", response_model=List[dict])
def get_concepts(level: Optional[int] = None, include_level_zero: bool = False, db: Session = Depends(get_db)):
    query = db.query(Concept)
    if level is not None:
        query = query.filter(Concept.level == level)
    
    concepts = _sort_concepts(query.all())
    concept_map = {str(c.id): c for c in concepts}
    
    # 获取所有实体（只查主数据L2和业务活动L4，排除 data_entity）
    _ma_cids = [c.id for c in concepts if c.level in (2, 4)]
    entities = _sort_entities(
        db.query(Entity).filter(Entity.concept_id.in_(_ma_cids)).all()
    ) if _ma_cids else []

    # 获取多对多挂载关系 (物理挂载)
    entity_concept_links = db.query(EntityConceptLink).all()
    concept_entities_map = {}
    for link in entity_concept_links:
        cid = str(link.concept_id)
        if cid not in concept_entities_map: concept_entities_map[cid] = []
        concept_entities_map[cid].append(str(link.entity_id))

    # 获取打点维护关系（统一从实体关系表读取）
    matrix_links = db.query(EntityRelation).filter(EntityRelation.relation_category == "打点维护").all()
    # 建立映射: source_entity_id (L2实体) -> [target_entity_id (L4实体)]
    l2_to_l4_map = {}
    for link in matrix_links:
        sid = str(link.source_entity_id)
        if sid not in l2_to_l4_map:
            l2_to_l4_map[sid] = []
        l2_to_l4_map[sid].append(str(link.target_entity_id))

    # 跨链关系已清除（用户要求：关系只查维护的关系，不展示初始化/跨链）
    cross_chain_map = {}

    result = []
    for c in concepts:
        # 默认不返回业务域(Level 0)，仅在显式请求时返回
        if c.level == 0 and level is None and not include_level_zero:
            continue
        
        concept_dict = {
            "id": str(c.id),
            "name": c.name,
            "level": c.level,
            "parent_id": str(c.parent_id) if c.parent_id else None,
            "area_index": c.area_index,
            "sort_order": c.sort_order or 0,
            "description": c.description,
            "system_names": c.system_names or [],
        }
        
        # 获取该概念下的实体列表
        linked_eids = concept_entities_map.get(str(c.id), [])
        c_entities = _sort_entities([e for e in entities if str(e.id) in linked_eids])
        
        concept_dict["entities"] = []
        
        # L2 概念附加跨链关系（L2->L3）
        if c.level == 2 and str(c.id) in cross_chain_map:
            concept_dict["cross_chain_relations"] = cross_chain_map[str(c.id)]
        else:
            concept_dict["cross_chain_relations"] = []
        
        for e in c_entities:
            e_data = {
                "id": str(e.id),
                "entity_code": e.entity_code,
                "entity_name": e.entity_name,
                "entity_en_name": e.entity_en_name,
                "entity_explanation": e.entity_explanation,
                "sort_order": e.sort_order or 0,
                "description": e.description,
                "is_main_table": e.is_main_table,
                "source_mode": e.source_mode or "physical_table",
                "integration_sql": e.integration_sql,
                "doris_catalog": e.doris_catalog,
                "data_source_id": str(e.data_source_id) if e.data_source_id else None,
                "properties_schema": e.properties_schema,
            }
            
            # --- 关键逻辑：如果该实体是 L2 实体，且有打点关系，则动态生成子树 ---
            if c.level == 2 and str(e.id) in l2_to_l4_map:
                l4_eids = l2_to_l4_map[str(e.id)]
                # 找到这些 L4 实体及其上层 L3, Domain
                sub_l4_entities = _sort_entities([ent for ent in entities if str(ent.id) in l4_eids])
                
                # 按 L3 分组构建子树
                l3_nodes = {}
                for l4e in sub_l4_entities:
                    l4_concept = concept_map.get(str(l4e.concept_id))
                    if not l4_concept or l4_concept.level != 4: continue
                    
                    l3_concept = concept_map.get(str(l4_concept.parent_id))
                    if not l3_concept or l3_concept.level != 3: continue
                    
                    l3_id = str(l3_concept.id)
                    if l3_id not in l3_nodes:
                        l3_nodes[l3_id] = {
                            "id": l3_id,
                            "name": l3_concept.name,
                            "level": 3,
                            "sort_order": l3_concept.sort_order or 0,
                            "children": {},
                        }
                    
                    l4_id = str(l4_concept.id)
                    if l4_id not in l3_nodes[l3_id]["children"]:
                        l3_nodes[l3_id]["children"][l4_id] = {
                            "id": l4_id,
                            "name": l4_concept.name,
                            "level": 4,
                            "sort_order": l4_concept.sort_order or 0,
                            "entities": [],
                        }
                    
                    l3_nodes[l3_id]["children"][l4_id]["entities"].append({
                        "id": str(l4e.id),
                        "name": l4e.entity_name,
                        "code": l4e.entity_code,
                        "sort_order": l4e.sort_order or 0,
                    })
                
                # 转化为前端树结构
                e_data["dynamic_children"] = sorted(
                    list(l3_nodes.values()),
                    key=lambda item: (item.get("sort_order", 0), item.get("name", "")),
                )
                for l3 in e_data["dynamic_children"]:
                    l3["children"] = sorted(
                        list(l3["children"].values()),
                        key=lambda item: (item.get("sort_order", 0), item.get("name", "")),
                    )
                    for l4 in l3["children"]:
                        l4["entities"] = sorted(
                            l4["entities"],
                            key=lambda item: (item.get("sort_order", 0), item.get("name", "")),
                        )

            concept_dict["entities"].append(e_data)
            
        result.append(concept_dict)
    return result

@router.get("/entities", response_model=dict)
def list_entities(db: Session = Depends(get_db)):
    entities = _sort_entities(db.query(Entity).all())
    return {
        "code": 200,
        "message": "success",
        "data": {
            "items": [
                {
                    "id": str(e.id),
                    "concept_id": str(e.concept_id),
                    "entity_code": e.entity_code,
                    "entity_name": e.entity_name,
                    "entity_en_name": e.entity_en_name,
                    "entity_explanation": e.entity_explanation,
                    "sort_order": e.sort_order or 0,
                    "description": e.description,
                    "is_main_table": e.is_main_table,
                    "source_mode": e.source_mode or "physical_table",
                    "integration_sql": e.integration_sql,
                    "doris_catalog": e.doris_catalog,
                    "data_source_id": str(e.data_source_id) if e.data_source_id else None,
                    "data_layer": e.data_layer,
                    "properties_schema": e.properties_schema,
                    "concept_ids": [str(l.concept_id) for l in db.query(EntityConceptLink).filter(EntityConceptLink.entity_id == e.id).all()]
                }
                for e in entities
            ],
            "total": len(entities)
        }
    }


@router.post("/entities/explanation-suggestions", response_model=dict)
def suggest_entity_explanations(payload: EntityExplanationSuggestRequest):
    return {
        "code": 200,
        "message": "success",
        "data": _build_entity_explanation_suggestions(payload),
    }


@router.post("/entities", response_model=EntityResponse)
def create_entity(entity: EntityCreate, db: Session = Depends(get_db)):
    concept_id = _norm_uuid_str(entity.concept_id, "concept_id")
    concept = db.query(Concept).filter(Concept.id == concept_id).first()
    if not concept or concept.level not in [2, 4]:
        raise HTTPException(status_code=400, detail="Only L2 and L4 concepts can have entities")
    
    payload = entity.dict(exclude={'concept_ids'})
    payload["concept_id"] = concept_id
    if payload.get("sort_order") is None:
        payload["sort_order"] = (db.query(func.max(Entity.sort_order)).filter(Entity.concept_id == concept_id).scalar() or 0) + 1
    db_entity = Entity(**payload)
    db.add(db_entity)
    db.flush()
    
    # 更新多概念关联
    mode = 'master' if concept.level == 2 else 'activity'
    cids = list(set([concept_id] + (entity.concept_ids or [])))
    _update_entity_concept_links(db, db_entity.id, cids, mode=mode)
    
    db.commit()
    db.refresh(db_entity)
    # 填充 concept_ids 用于响应
    res = EntityResponse.from_orm(db_entity)
    res.concept_ids = [str(l.concept_id) for l in db.query(EntityConceptLink).filter(EntityConceptLink.entity_id == db_entity.id).all()]
    return res


def _suggest_entity_en_name(entity: Entity) -> str:
    base = (entity.entity_en_name or "").strip()
    if base:
        return base
    code = (entity.entity_code or "").strip().lower()
    if code:
        code = re.sub(r"[^a-z0-9_]+", "_", code)
        code = re.sub(r"_+", "_", code).strip("_")
        if code:
            return code
    return f"entity_{str(entity.id).replace('-', '')[:8]}"


@router.get("/entities/en-name-integrity-check")
def check_entity_en_name_integrity(db: Session = Depends(get_db)):
    entities = db.query(Entity).all()
    missing = [e for e in entities if not (e.entity_en_name or "").strip()]
    rows = [
        {
            "id": str(e.id),
            "concept_id": str(e.concept_id),
            "entity_code": e.entity_code,
            "entity_name": e.entity_name,
            "entity_en_name": e.entity_en_name,
            "landing_table_en_name": e.entity_en_name,
            "suggested_entity_en_name": _suggest_entity_en_name(e),
            "suggested_landing_table_en_name": _suggest_entity_en_name(e),
        }
        for e in missing
    ]
    return {
        "code": 200,
        "data": {
            "total": len(entities),
            "missing_count": len(missing),
            "missing_entities": rows,
        },
    }


@router.post("/entities/en-name-autofill")
def autofill_entity_en_name(payload: EntityEnNameAutoFillRequest, db: Session = Depends(get_db)):
    entities = db.query(Entity).all()
    updated = []
    for e in entities:
        is_empty = not (e.entity_en_name or "").strip()
        if payload.only_empty and not is_empty:
            continue
        suggested = _suggest_entity_en_name(e)
        if not suggested:
            continue
        if (e.entity_en_name or "").strip() == suggested:
            continue
        e.entity_en_name = suggested
        updated.append(
            {
                "id": str(e.id),
                "entity_code": e.entity_code,
                "entity_name": e.entity_name,
                "entity_en_name": e.entity_en_name,
            }
        )

    db.commit()
    return {"code": 200, "data": {"updated_count": len(updated), "updated_entities": updated}}

@router.put("/entities/{entity_id}", response_model=EntityResponse)
def update_entity(entity_id: str, entity_update: EntityUpdate, db: Session = Depends(get_db)):
    entity_id = _norm_uuid_str(entity_id, "entity_id") or entity_id
    db_entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not db_entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    update_data = entity_update.dict(exclude_unset=True, exclude={'concept_ids'})
    for key, value in update_data.items():
        setattr(db_entity, key, value)
        
    if entity_update.concept_ids is not None:
        # 强制更新多概念关联
        mode = 'master' if db_entity.concept_id and db_entity.concept_id in [str(c.id) for c in db.query(Concept.id).filter(Concept.level.in_([1, 2])).all()] else 'activity'
        cids = list(set(entity_update.concept_ids))
        # 确保当前的父级 concept_id 也在关联列表中
        if db_entity.concept_id and db_entity.concept_id not in cids:
            cids.append(db_entity.concept_id)
        _update_entity_concept_links(db, entity_id, cids, mode=mode)
    elif "concept_id" in update_data:
        # 如果只改了父级，确保父级在关联中
        mode = 'master' if db_entity.concept_id and db_entity.concept_id in [str(c.id) for c in db.query(Concept.id).filter(Concept.level.in_([1, 2])).all()] else 'activity'
        links = db.query(EntityConceptLink).filter(EntityConceptLink.entity_id == entity_id).all()
        curr_cids = [str(l.concept_id) for l in links]
        if str(db_entity.concept_id) not in curr_cids:
            curr_cids.append(str(db_entity.concept_id))
            _update_entity_concept_links(db, entity_id, curr_cids, mode=mode)

    db.commit()
    db.refresh(db_entity)
    res = EntityResponse.from_orm(db_entity)
    res.concept_ids = [str(l.concept_id) for l in db.query(EntityConceptLink).filter(EntityConceptLink.entity_id == db_entity.id).all()]
    return res

@router.delete("/entities/{entity_id}")
def delete_entity(entity_id: str, db: Session = Depends(get_db)):
    entity_id = _norm_uuid_str(entity_id, "entity_id") or entity_id
    db_entity = db.query(Entity).filter(Entity.id == entity_id).first()
    if not db_entity:
        raise HTTPException(status_code=404, detail="Entity not found")
    
    # 级联删除相关关系
    db.query(EntityRelation).filter(
        (EntityRelation.source_entity_id == entity_id) | (EntityRelation.target_entity_id == entity_id)
    ).delete()
    
    # 级联删除概念关联
    db.query(EntityConceptLink).filter(EntityConceptLink.entity_id == entity_id).delete()

    db.delete(db_entity)
    db.commit()
    return {"message": "Entity deleted successfully"}

@router.get("/entity-relations", response_model=List[EntityRelationResponse])
def get_entity_relations(entity_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(EntityRelation)
    if entity_id:
        entity_id = _norm_uuid_str(entity_id, "entity_id") or entity_id
        query = query.filter(
            (EntityRelation.source_entity_id == entity_id) | (EntityRelation.target_entity_id == entity_id)
        )
    return query.all()

@router.post("/entity-relations", response_model=EntityRelationResponse)
def create_entity_relation(relation: EntityRelationCreate, db: Session = Depends(get_db)):
    db_relation = EntityRelation(**relation.dict())
    db.add(db_relation)
    db.commit()
    db.refresh(db_relation)
    return db_relation


@router.put("/entity-relations/{relation_id}", response_model=EntityRelationResponse)
def update_entity_relation(relation_id: str, payload: EntityRelationUpdate, db: Session = Depends(get_db)):
    relation_id = _norm_uuid_str(relation_id, "relation_id") or relation_id
    db_relation = db.query(EntityRelation).filter(EntityRelation.id == relation_id).first()
    if not db_relation:
        raise HTTPException(status_code=404, detail="Relation not found")

    data = payload.dict(exclude_unset=True)
    for k, v in data.items():
        setattr(db_relation, k, v)
    db.commit()
    db.refresh(db_relation)
    return db_relation

@router.delete("/entity-relations/{relation_id}")
def delete_entity_relation(relation_id: str, db: Session = Depends(get_db)):
    relation_id = _norm_uuid_str(relation_id, "relation_id") or relation_id
    db_relation = db.query(EntityRelation).filter(EntityRelation.id == relation_id).first()
    if not db_relation:
        raise HTTPException(status_code=404, detail="Relation not found")
    
    db.delete(db_relation)
    db.commit()
    return {"message": "Relation deleted successfully"}


@router.get("/graph/matrix")
def get_graph_matrix(db: Session = Depends(get_db)):
    """获取资产矩阵数据：左侧 业务域/L3/L4 及其下属实体，顶部 L1/L2 及其下属实体"""
    try:
        # 1. 获取所有概念，按层级分类
        concepts = _sort_concepts(db.query(Concept).all())
        concept_map = {str(c.id): c for c in concepts}
        # 业务域定义为 level=0（不在图谱展示，仅用于矩阵分类）
        domains = [c for c in concepts if c.level == 0]
        l1_l2 = [c for c in concepts if c.level in [1, 2]]
        l3_l4 = [c for c in concepts if c.level in [3, 4]]
        
        # 2. 获取有挂载的实体（与主数据建模页面一致，只用 kg_entity_concept_links 里挂载的）
        _linked_entity_ids = [link.entity_id for link in db.query(EntityConceptLink).all()]
        entities = _sort_entities(
            db.query(Entity).filter(Entity.id.in_(_linked_entity_ids)).all()
        ) if _linked_entity_ids else []
        entity_map = {str(e.id): e for e in entities}
        
        # 获取打点维护关系：统一从实体关系表读取
        matrix_links = db.query(EntityRelation).filter(EntityRelation.relation_category == "打点维护").all()
        link_map = {}
        link_detail_map = {}
        for link in matrix_links:
            source_entity = entity_map.get(str(link.source_entity_id))
            target_entity = entity_map.get(str(link.target_entity_id))
            source_concept = concept_map.get(str(source_entity.concept_id)) if source_entity else None
            target_concept = concept_map.get(str(target_entity.concept_id)) if target_entity else None
            if not source_entity or not target_entity or not source_concept or not target_concept:
                continue
            if source_concept.level != 2 or target_concept.level != 4:
                continue
            sid = str(target_entity.id)
            tid = str(source_entity.id)
            if sid not in link_map:
                link_map[sid] = []
            link_map[sid].append(tid)
            if sid not in link_detail_map:
                link_detail_map[sid] = {}
            link_detail_map[sid][tid] = {
                "id": str(link.id),
                "relation_name": link.relation_name,
                "relation_category": "打点维护",
                "direction": link.direction or "forward",
                "cardinality": link.cardinality or "N:N",
                "join_expr": link.join_expr,
                "description": link.description,
                "source_field_name": link.source_field_name,
                "target_field_name": link.target_field_name,
                "remark": link.remark,
            }

        # 构建实体所属主要概念 map: {concept_id: [entity, ...]}
        concept_entities_map = {}
        for e in entities:
            cid = str(e.concept_id)
            if cid not in concept_entities_map:
                concept_entities_map[cid] = []
            concept_entities_map[cid].append(e)
            
        # 3. 构造响应结构
        return {
            "code": 200,
            "data": {
                "columns": [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "level": c.level,
                        "parent_id": str(c.parent_id) if c.parent_id else None,
                        "sort_order": c.sort_order or 0,
                        "entities": [
                            {
                                "id": str(e.id),
                                "name": e.entity_name,
                                "code": e.entity_code,
                                "en_name": e.entity_en_name,
                                "is_main_table": e.is_main_table,
                                "sort_order": e.sort_order or 0,
                            } for e in _sort_entities(concept_entities_map.get(str(c.id), []))
                        ] if c.level == 2 else []
                    } for c in l1_l2
                ],
                "domains": [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "level": c.level,
                        "parent_id": str(c.parent_id) if c.parent_id else None,
                        "sort_order": c.sort_order or 0,
                    } for c in domains
                ],
                "rows": [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "level": c.level,
                        "parent_id": str(c.parent_id) if c.parent_id else None,
                        "sort_order": c.sort_order or 0,
                        "entities": [
                            {
                                "id": str(e.id),
                                "name": e.entity_name,
                                "code": e.entity_code,
                                "en_name": e.entity_en_name,
                                "sort_order": e.sort_order or 0,
                                "linked_entity_ids": link_map.get(str(e.id), []),
                                "linked_entity_map": link_detail_map.get(str(e.id), {})
                            } for e in _sort_entities([item for item in entities if str(item.concept_id) == str(c.id)])
                        ]
                    } for c in l3_l4
                ]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate matrix data: {str(e)}")


@router.post("/entities/{entity_id}/matrix/toggle")
def toggle_entity_matrix_link(entity_id: str, target_entity_id: str, db: Session = Depends(get_db)):
    """在矩阵中切换业务实体(L4)与主数据实体(L2)的打点关联"""
    activity_id = _norm_uuid_str(entity_id, "entity_id")
    master_id = _norm_uuid_str(target_entity_id, "target_entity_id")
    activity_entity = db.query(Entity).filter(Entity.id == activity_id).first()
    master_entity = db.query(Entity).filter(Entity.id == master_id).first()
    if not activity_entity or not master_entity:
        raise HTTPException(status_code=404, detail="Entity not found")

    existing = db.query(EntityRelation).filter(
        EntityRelation.source_entity_id == master_id,
        EntityRelation.target_entity_id == activity_id,
        EntityRelation.relation_category == "打点维护",
    ).first()

    if existing:
        db.delete(existing)
        action = "unlinked"
        link_id = str(existing.id)
    else:
        new_link = EntityRelation(
            id=str(uuid.uuid4()),
            source_entity_id=master_id,
            target_entity_id=activity_id,
            relation_name=_build_matrix_relation_name(master_entity, activity_entity),
            relation_category="打点维护",
            direction="forward",
            cardinality="N:N",
            join_expr=None,
            description="由资产矩阵打点自动生成的实体关系",
            remark="由资产矩阵打点自动生成的实体关系",
        )
        db.add(new_link)
        action = "linked"
        link_id = str(new_link.id)
        
    db.commit()
    return {"code": 200, "message": "success", "action": action, "link_id": link_id}



@router.get("/export/excel")
def export_graph_to_excel(mode: Optional[str] = None, db: Session = Depends(get_db)):
    """导出图谱结构数据；指定模式时仅导出当前模式的分类、实体、属性。"""
    try:
        concept_columns = ["ID", "概念名称", "层级", "父级名称", "业务域索引", "顺序", "描述", "所属系统"]
        entity_columns = ["ID", "所属概念", "顺序", "实体编码", "实体名称", "实体英文名", "解释(别名同义词)", "描述", "是否主表", "数据层级"]
        property_columns = ["实体名称", "实体编码", "属性名(EN)", "属性名(CN)", "类型", "是否主键", "描述"]
        relation_columns = [
            "关系类别", "关系名称",
            "源实体", "源实体编码", "源实体所属分类",
            "目标实体", "目标实体编码", "目标实体所属分类",
            "方向", "基数", "关联条件", "描述"
        ]

        # 1. 概念清单
        query_concepts = db.query(Concept)
        if mode == 'master':
            query_concepts = query_concepts.filter(Concept.level.in_([1, 2]))
        elif mode == 'activity':
            query_concepts = query_concepts.filter(Concept.level.in_([0, 3, 4]))
        
        concepts = _sort_concepts(query_concepts.all())
        concept_map = {str(c.id): c for c in concepts}
        # 建立全量 map 用于找父级名称（即使父级不在导出范围内，也能显示名称）
        full_concept_map = {str(c.id): c for c in db.query(Concept).all()}
        
        concepts_df = pd.DataFrame([{
            "ID": str(c.id),
            "概念名称": c.name,
            "层级": c.level,
            "父级名称": full_concept_map.get(str(c.parent_id)).name if c.parent_id and full_concept_map.get(str(c.parent_id)) else "",
            "业务域索引": c.area_index,
            "顺序": c.sort_order or 0,
            "描述": c.description,
            "所属系统": "、".join(c.system_names or []) if c.level == 3 else "",
        } for c in concepts], columns=concept_columns)

        # 2. 实体清单
        concept_ids = [c.id for c in concepts]
        query_entities = db.query(Entity)
        if mode:
            query_entities = query_entities.filter(Entity.concept_id.in_(concept_ids))
        
        entities = _sort_entities(query_entities.all())
        entity_map = {str(e.id): e for e in entities}
        entities_df = pd.DataFrame([{
            "ID": str(e.id),
            "所属概念": concept_map.get(str(e.concept_id)).name if concept_map.get(str(e.concept_id)) else "",
            "顺序": e.sort_order or 0,
            "实体编码": e.entity_code,
            "实体名称": e.entity_name,
            "实体英文名": e.entity_en_name,
            "解释(别名同义词)": e.entity_explanation,
            "描述": e.description,
            "是否主表": "是" if e.is_main_table else "否",
            "数据层级": e.data_layer
        } for e in entities], columns=entity_columns)

        # 3. 实体属性
        props_data = []
        for e in entities:
            props = e.properties_schema if isinstance(e.properties_schema, list) else []
            for p in props:
                props_data.append({
                    "实体名称": e.entity_name,
                    "实体编码": e.entity_code,
                    "属性名(EN)": p.get("name"),
                    "属性名(CN)": p.get("cnName"),
                    "类型": p.get("type"),
                    "是否主键": "是" if p.get("isPrimaryKey") else "否",
                    "描述": p.get("description")
                })
        props_df = pd.DataFrame(props_data, columns=property_columns)

        # 写入 Excel 缓冲区
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            concepts_df.to_excel(writer, sheet_name='概念清单', index=False)
            entities_df.to_excel(writer, sheet_name='实体清单', index=False)
            props_df.to_excel(writer, sheet_name='实体属性', index=False)
            if not mode:
                relation_rows = []
                full_entity_map = {str(e.id): e for e in db.query(Entity).all()}
                relations = db.query(EntityRelation).all()
                for r in relations:
                    source_entity = full_entity_map.get(str(r.source_entity_id))
                    target_entity = full_entity_map.get(str(r.target_entity_id))
                    source_concept = full_concept_map.get(str(source_entity.concept_id)) if source_entity else None
                    target_concept = full_concept_map.get(str(target_entity.concept_id)) if target_entity else None
                    relation_rows.append({
                        "关系类别": r.relation_category or "手工维护",
                        "关系名称": r.relation_name,
                        "源实体": source_entity.entity_name if source_entity else "",
                        "源实体编码": source_entity.entity_code if source_entity else "",
                        "源实体所属分类": source_concept.name if source_concept else "",
                        "目标实体": target_entity.entity_name if target_entity else "",
                        "目标实体编码": target_entity.entity_code if target_entity else "",
                        "目标实体所属分类": target_concept.name if target_concept else "",
                        "方向": r.direction,
                        "基数": r.cardinality,
                        "关联条件": r.join_expr,
                        "描述": r.description
                    })
                relations_df = pd.DataFrame(relation_rows, columns=relation_columns)
                relations_df.to_excel(writer, sheet_name='实体关系', index=False)
        
        output.seek(0)
        
        filename = "graph_metadata.xlsx"
        if mode == 'master': filename = "master_data_metadata.xlsx"
        elif mode == 'activity': filename = "business_activity_metadata.xlsx"
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


def _clear_graph_data(db: Session, mode: Optional[str] = None) -> Dict[str, int]:
    """清空图谱结构数据。指定 mode 时仅清空当前模式（master=L1/L2, activity=L0/L3/L4），否则清全部。
    MySQL InnoDB 外键为 RESTRICT，必须子先父后删除；概念自引用按层级深度优先（深层先删）。
    返回已删除的 concept/entity 计数。
    """
    if mode == 'master':
        levels = [1, 2]
    elif mode == 'activity':
        levels = [0, 3, 4]
    else:
        levels = None  # 全部

    # 范围内的概念 id
    if levels is not None:
        scope_concept_ids = [r[0] for r in db.query(Concept.id).filter(Concept.level.in_(levels)).all()]
    else:
        scope_concept_ids = None

    # 范围内的实体 id（实体所属概念在范围内）
    if scope_concept_ids is not None:
        scope_entity_ids = (
            [r[0] for r in db.query(Entity.id).filter(Entity.concept_id.in_(scope_concept_ids)).all()]
            if scope_concept_ids else []
        )
    else:
        scope_entity_ids = None

    # 1) 删实体相关子表（关系/概念关联）-> 再删实体
    if scope_entity_ids is not None:
        if scope_entity_ids:
            db.query(EntityRelation).filter(
                or_(EntityRelation.source_entity_id.in_(scope_entity_ids),
                    EntityRelation.target_entity_id.in_(scope_entity_ids))
            ).delete(synchronize_session=False)
            db.query(EntityConceptLink).filter(EntityConceptLink.entity_id.in_(scope_entity_ids)).delete(synchronize_session=False)
            db.query(Entity).filter(Entity.id.in_(scope_entity_ids)).delete(synchronize_session=False)
    else:
        db.query(EntityRelation).delete(synchronize_session=False)
        db.query(EntityConceptLink).delete(synchronize_session=False)
        db.query(Entity).delete(synchronize_session=False)

    # 2) 删概念：先清残留指向这些概念的链接/概念关系，再按层级深度优先删概念（满足自引用父外键）
    deleted_concepts = 0
    if scope_concept_ids is not None:
        if scope_concept_ids:
            db.query(EntityConceptLink).filter(EntityConceptLink.concept_id.in_(scope_concept_ids)).delete(synchronize_session=False)
            db.query(ConceptRelation).filter(
                or_(ConceptRelation.source_concept_id.in_(scope_concept_ids),
                    ConceptRelation.target_concept_id.in_(scope_concept_ids))
            ).delete(synchronize_session=False)
            # 深层优先：4→3→2→1→0，保证删父节点前子节点已删
            level_order = [lv for lv in [4, 3, 2, 1, 0] if lv in (levels or [0, 1, 2, 3, 4])]
            for lv in level_order:
                deleted_concepts += db.query(Concept).filter(
                    Concept.level == lv, Concept.id.in_(scope_concept_ids)
                ).delete(synchronize_session=False)
    else:
        db.query(EntityConceptLink).delete(synchronize_session=False)
        db.query(ConceptRelation).delete(synchronize_session=False)
        level_order = [4, 3, 2, 1, 0]
        for lv in level_order:
            deleted_concepts += db.query(Concept).filter(Concept.level == lv).delete(synchronize_session=False)

    db.commit()
    deleted_entities = len(scope_entity_ids) if scope_entity_ids is not None else 'all'
    return {"concepts": deleted_concepts, "entities": deleted_entities}


def _relink_entity_dependencies(db: Session) -> Dict[str, int]:
    """实体按 entity_code 重新生成（clear+import 导致 uuid 变更）后，按 entity_code 重链
    EntityModeling / EntityInitData 的 entity_id，以及 EntityMappingRule.entity_ids。
    EntityMappingRule 无 entity_code 列，借 EntityModeling/EntityInitData 的 (旧entity_id, entity_code) 桥接。
    """
    code_to_id = {e.entity_code: str(e.id) for e in db.query(Entity).all()}
    # 旧 uuid -> entity_code 桥（来自仍带着旧 entity_id 的建模/初始化行）
    old_uuid_to_code: Dict[str, str] = {}
    for m in db.query(EntityModeling).all():
        if m.entity_id and m.entity_code:
            old_uuid_to_code.setdefault(str(m.entity_id), m.entity_code)
    for x in db.query(EntityInitData).all():
        if x.entity_id and x.entity_code:
            old_uuid_to_code.setdefault(str(x.entity_id), x.entity_code)

    rel_modeling = rel_initdata = rel_rules = 0
    # 1) EntityModeling：按 entity_code 重链 entity_id
    for m in db.query(EntityModeling).all():
        nid = code_to_id.get(m.entity_code)
        if nid and str(m.entity_id) != nid:
            m.entity_id = nid
            rel_modeling += 1
    # 2) EntityInitData
    for x in db.query(EntityInitData).all():
        nid = code_to_id.get(x.entity_code)
        if nid and str(x.entity_id) != nid:
            x.entity_id = nid
            rel_initdata += 1
    # 3) EntityMappingRule：entity_ids 旧 uuid 数组 -> code -> 新 uuid
    for r in db.query(EntityMappingRule).all():
        new_ids: list = []
        changed = False
        for eid in (r.entity_ids or []):
            seid = str(eid)
            if seid in code_to_id:           # 已是有效 uuid
                new_ids.append(seid)
            else:
                code = old_uuid_to_code.get(seid)
                if code and code in code_to_id:
                    new_ids.append(code_to_id[code]); changed = True
                else:
                    new_ids.append(seid)     # 无法恢复，保留原值
        if changed:
            r.entity_ids = new_ids
            rel_rules += 1
    db.commit()
    return {"modeling": rel_modeling, "initdata": rel_initdata, "rules": rel_rules}


@router.post("/concepts/clear")
def clear_graph_data(mode: Optional[str] = None, db: Session = Depends(get_db)):
    """清空图谱结构数据（按 mode 限定范围）。供“重置模板/清空数据”按钮调用。"""
    try:
        result = _clear_graph_data(db, mode)
        scope = {'master': '主数据', 'activity': '业务活动'}.get(mode, '全部')
        return {"code": 200, "message": f"已清空【{scope}】数据：概念 {result['concepts']}、实体 {result['entities']}"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"清空失败: {str(e)}")


@router.post("/import/excel")
async def import_graph_from_excel(mode: Optional[str] = None, clear: bool = False, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """导入图谱结构数据；指定模式时仅影响当前模式的分类、实体、属性。
    clear=True 时先清空当前模式数据再导入（清空重导入）。
    """
    try:
        if clear:
            _clear_graph_data(db, mode)
        contents = await file.read()
        excel_data = pd.read_excel(io.BytesIO(contents), sheet_name=None)
        # 导入计数（供前端反馈，避免"0 行也显示成功"的静默失败）
        counts = {"concepts": 0, "entities": 0, "entities_skipped": 0, "attributes": 0, "relations": 0}

        parent_level_map = {
            0: None,
            1: None,
            2: 1,
            3: 0,
            4: 3,
        }

        # 1. 导入概念
        if '概念清单' in excel_data:
            df = excel_data['概念清单']
            # 按层级排序，确保父节点先处理
            df = df.sort_values(by='层级')
            for _, row in df.iterrows():
                name = str(row['概念名称']).strip()
                level = int(row['层级'])
                
                # 模式过滤
                if mode == 'master' and level not in [1, 2]: continue
                if mode == 'activity' and level not in [0, 3, 4]: continue
                counts["concepts"] += 1

                parent_name = str(row.get('父级名称', '')).strip()
                
                parent_id = None
                if parent_name and parent_name != 'nan':
                    expected_parent_level = parent_level_map.get(level)
                    if expected_parent_level is not None:
                        parent = db.query(Concept).filter(Concept.name == parent_name, Concept.level == expected_parent_level).first()
                        if parent:
                            parent_id = parent.id
                
                existing = db.query(Concept).filter(Concept.name == name, Concept.level == level).first()
                if existing:
                    existing.parent_id = parent_id
                    existing.area_index = _safe_int(row.get('业务域索引', 1), 1)
                    existing.sort_order = _safe_int(row.get('顺序', 0), 0)
                    existing.description = str(row.get('描述', '')) if row.get('描述') != 'nan' else None
                    existing.system_names = _normalize_system_names(row.get('所属系统')) if level == 3 else None
                else:
                    new_concept = Concept(
                        name=name,
                        level=level,
                        parent_id=parent_id,
                        area_index=_safe_int(row.get('业务域索引', 1), 1),
                        sort_order=_safe_int(row.get('顺序', 0), 0),
                        description=str(row.get('描述', '')) if row.get('描述') != 'nan' else None,
                        system_names=_normalize_system_names(row.get('所属系统')) if level == 3 else None,
                    )
                    db.add(new_concept)
                    db.flush()  # autoflush=False：显式刷新，使后续 L2/L4 的父级查找能查到本轮新建的父概念
            db.commit()

        # 2. 导入实体
        if '实体清单' in excel_data:
            df = excel_data['实体清单']
            imported_entity_ids = []
            for _, row in df.iterrows():
                concept_name = str(row['所属概念']).strip()
                code = str(row['实体编码']).strip()
                name = str(row['实体名称']).strip()
                
                # 按 mode 优先查对应层级的概念（避免重名概念查到错误层级）
                # activity 模式查 L0/L3/L4，master 模式查 L1/L2，无 mode 查全部
                if mode == 'activity':
                    concept = db.query(Concept).filter(
                        Concept.name == concept_name, Concept.level.in_([0, 3, 4])
                    ).first()
                elif mode == 'master':
                    concept = db.query(Concept).filter(
                        Concept.name == concept_name, Concept.level.in_([1, 2])
                    ).first()
                else:
                    concept = db.query(Concept).filter(Concept.name == concept_name).first()
                if not concept:
                    counts["entities_skipped"] += 1
                    continue
                counts["entities"] += 1

                existing = db.query(Entity).filter(Entity.entity_code == code).first()
                if existing:
                    existing.concept_id = concept.id
                    existing.entity_name = name
                    existing.entity_en_name = str(row.get('实体英文名', '')) if row.get('实体英文名') != 'nan' else None
                    existing.entity_explanation = str(row.get('解释(别名同义词)', '')) if row.get('解释(别名同义词)') != 'nan' else None
                    existing.sort_order = _safe_int(row.get('顺序', 0), 0)
                    existing.description = str(row.get('描述', '')) if row.get('描述') != 'nan' else None
                    existing.is_main_table = (str(row.get('是否主表', '')) == '是')
                    existing.data_layer = str(row.get('数据层级', '')) if row.get('数据层级') != 'nan' else None
                    imported_entity_ids.append(str(existing.id))
                else:
                    new_entity = Entity(
                        concept_id=concept.id,
                        entity_code=code,
                        entity_name=name,
                        entity_en_name=str(row.get('实体英文名', '')) if row.get('实体英文名') != 'nan' else None,
                        entity_explanation=str(row.get('解释(别名同义词)', '')) if row.get('解释(别名同义词)') != 'nan' else None,
                        sort_order=_safe_int(row.get('顺序', 0), 0),
                        description=str(row.get('描述', '')) if row.get('描述') != 'nan' else None,
                        is_main_table=(str(row.get('是否主表', '')) == '是'),
                        data_layer=str(row.get('数据层级', '')) if row.get('数据层级') != 'nan' else None,
                        properties_schema=[]
                    )
                    db.add(new_entity)
                    db.flush()
                    imported_entity_ids.append(str(new_entity.id))
            db.flush()
            for entity_id in imported_entity_ids:
                entity = db.query(Entity).filter(Entity.id == entity_id).first()
                if entity:
                    _update_entity_concept_links(db, str(entity.id), [str(entity.concept_id)], mode=mode)
            db.commit()

        # 3. 导入实体属性
        if '实体属性' in excel_data:
            df = excel_data['实体属性']
            # 按实体编码分组处理
            for code, group in df.groupby('实体编码'):
                entity = db.query(Entity).filter(Entity.entity_code == str(code).strip()).first()
                if not entity:
                    continue

                new_props = []
                for _, row in group.iterrows():
                    new_props.append({
                        "name": str(row['属性名(EN)']).strip(),
                        "cnName": str(row['属性名(CN)']).strip(),
                        "type": str(row.get('类型', 'string')).strip(),
                        "isPrimaryKey": (str(row.get('是否主键', '')) == '是'),
                        "description": str(row.get('描述', '')) if row.get('描述') != 'nan' else ""
                    })
                entity.properties_schema = new_props
                counts["attributes"] += len(new_props)
            db.commit()

        # 4. 导入实体关系
        # 模式导入下不处理关系，避免跨主数据/业务活动互相污染。
        # 关系导入后续走独立功能。
        if not mode and '实体关系' in excel_data:
            df = excel_data['实体关系']
            for _, row in df.iterrows():
                relation_category = str(row.get('关系类别', '手工维护')).strip() if row.get('关系类别') != 'nan' else "手工维护"
                rel_name = str(row['关系名称']).strip()
                source_name = str(row['源实体']).strip()
                target_name = str(row['目标实体']).strip()
                
                source = db.query(Entity).filter(Entity.entity_name == source_name).first()
                target = db.query(Entity).filter(Entity.entity_name == target_name).first()
                
                if not source or not target:
                    continue
                
                # 模式过滤（仅当源实体属于当前模式的概念时导入）
                source_concept = db.query(Concept).filter(Concept.id == source.concept_id).first()
                if mode == 'master' and source_concept.level not in [1, 2]: continue
                if mode == 'activity' and source_concept.level not in [0, 3, 4]: continue

                existing = db.query(EntityRelation).filter(
                    EntityRelation.source_entity_id == source.id,
                    EntityRelation.target_entity_id == target.id,
                    EntityRelation.relation_name == rel_name,
                    EntityRelation.relation_category == relation_category,
                ).first()
                
                rel_data = {
                    "source_entity_id": source.id,
                    "target_entity_id": target.id,
                    "relation_name": rel_name,
                    "relation_category": relation_category,
                    "direction": str(row.get('方向', 'forward')).strip(),
                    "cardinality": str(row.get('基数', 'N:N')).strip(),
                    "join_expr": str(row.get('关联条件', '')) if row.get('关联条件') != 'nan' else None,
                    "description": str(row.get('描述', '')) if row.get('描述') != 'nan' else None,
                    "remark": str(row.get('描述', '')) if row.get('描述') != 'nan' else None,
                }
                
                if existing:
                    for k, v in rel_data.items():
                        setattr(existing, k, v)
                else:
                    db.add(EntityRelation(**rel_data))
                counts["relations"] += 1
            db.commit()

        # clear+import 会重建实体（uuid 变更），按 entity_code 重链建模表/初始化数据/映射规则，避免断链
        if clear:
            _relink_entity_dependencies(db)

        total = counts["concepts"] + counts["entities"] + counts["attributes"] + counts["relations"]
        # 模式不匹配判定：文件里有实体但全部找不到所属概念（概念/实体均为 0）
        mode_mismatch = counts["entities"] == 0 and counts["entities_skipped"] > 0
        if mode_mismatch:
            msg = f"未导入任何概念/实体（跳过 {counts['entities_skipped']} 个）：文件与当前页面模式不匹配，请在对应页面（主数据/业务活动）导入"
            status = "warning"
        elif total == 0:
            msg = "未导入任何数据：请检查文件与当前页面模式是否匹配（主数据/业务活动）"
            status = "warning"
        else:
            skipped = f"，跳过 {counts['entities_skipped']} 个无所属概念的实体" if counts["entities_skipped"] else ""
            msg = f"导入成功：概念 {counts['concepts']}、实体 {counts['entities']}、属性 {counts['attributes']}、关系 {counts['relations']}{skipped}"
            status = "success"
        return {"code": 200, "message": msg, "counts": counts, "total": total, "status": status}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
