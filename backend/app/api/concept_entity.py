"""概念/实体/关系 CRUD 端点 -- 从 concept.py 拆分（机械迁移，行为等价）

迁移内容：/concepts* CRUD、/entities* 端点（含英文名补全）、
/entity-relations* CRUD，以及 EntityEnNameAutoFillRequest 模型与
_suggest_entity_en_name 助手。由 concept.py 聚合挂载，对外路由路径不变。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import List, Optional
from ..models.base import Concept, Entity, EntityRelation, EntityConceptLink
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
import re

from .concept_support import (
    EntityExplanationSuggestRequest,
    _build_entity_explanation_suggestions,
    _norm_uuid_str, _normalize_system_names,
    _sort_concepts, _sort_entities, _update_entity_concept_links,
)

router = APIRouter()


class EntityEnNameAutoFillRequest(BaseModel):
    only_empty: bool = True


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
            # 根下新增顶层节点默认同序递增（spec §二/§七.1：同级 max+1——删除后不复用空位，防撞号）
            max_area = db.query(func.max(Concept.area_index)).filter(
                Concept.level == concept.level
            ).scalar()
            data["area_index"] = (max_area or 0) + 1
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
    # 三轨M3/1：concept_id 与 create 对齐——归一化+必须指向存在的 L2/L4 概念
    if update_data.get("concept_id") is not None:
        _cid = _norm_uuid_str(str(update_data["concept_id"]), "concept_id")
        _parent = db.query(Concept).filter(Concept.id == _cid).first() if _cid else None
        if not _parent or _parent.level not in [2, 4]:
            raise HTTPException(status_code=400, detail="concept_id 必须指向存在的 L2/L4 概念")
        update_data["concept_id"] = _cid
    for key, value in update_data.items():
        setattr(db_entity, key, value)

    def _mode_of(concept_id: str) -> str:
        _c = db.query(Concept).filter(Concept.id == concept_id).first()
        return 'master' if _c and _c.level == 2 else 'activity'

    if entity_update.concept_ids is not None:
        # 强制更新多概念关联（mode 以父概念层级判定——L2=master，与 create 一致）
        if not db_entity.concept_id:
            raise HTTPException(status_code=400, detail="实体缺少父级概念，无法更新挂载")
        mode = _mode_of(str(db_entity.concept_id))
        cids = list(set(entity_update.concept_ids))
        # 确保当前的父级 concept_id 也在关联列表中
        if db_entity.concept_id and db_entity.concept_id not in cids:
            cids.append(db_entity.concept_id)
        _update_entity_concept_links(db, entity_id, cids, mode=mode)
    elif "concept_id" in update_data:
        # 如果只改了父级，确保父级在关联中
        mode = _mode_of(str(db_entity.concept_id))
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
