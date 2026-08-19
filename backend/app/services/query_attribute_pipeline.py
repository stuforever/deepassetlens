"""
问属性 入口/校验/面板簇 -- 从 query_attribute_service.py 拆分（机械迁移，行为等价）

迁移内容：元数据入口（get_example_attribute_metadata/build_attribute_metadata_from_system）、
元数据摊平（_flatten_attribute_metadata）、结果校验（_validate_query_attribute_result）、
结果面板（_build_attribute_result_panels）、LLM 错误构造（_build_query_attribute_llm_error）。

对外仍由 query_attribute_service.py 显式 re-export，外部引用路径不变。
"""

import json
from collections import defaultdict
from copy import deepcopy
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from app.models.base import Concept, Entity, EntityRelation, StandardSemanticTerm
from app.services.query_entity_service import (
    _dedupe_keep_order,
    _extract_semantic_alias_terms,
    _safe_text,
)


from .query_attribute_catalog import (
    _build_attribute_catalog,
    _build_attribute_validation_catalog,
    _build_entity_brief,
    _build_example_attribute_metadata,
    _build_relation_brief,
    _build_scope_catalog,
)
from .query_attribute_support import (
    _build_sql_blueprint,
    _group_relations,
    _normalize_confidence,
    _pick_existing_relation,
    _sanitize_attribute_result,
)


def get_example_attribute_metadata() -> Dict[str, Any]:
    return _build_example_attribute_metadata()


def build_attribute_metadata_from_system(db: Session) -> Dict[str, Any]:
    concepts = db.query(Concept).all()
    entities = db.query(Entity).all()
    relations = db.query(EntityRelation).order_by(EntityRelation.created_at.desc()).all()
    semantic_terms = (
        db.query(StandardSemanticTerm)
        .filter(StandardSemanticTerm.enabled == True)  # noqa: E712
        .filter(StandardSemanticTerm.ontology_ref_type == "entity")
        .all()
    )

    concept_map: Dict[str, Concept] = {str(item.id): item for item in concepts}
    entity_map: Dict[str, Entity] = {str(item.id): item for item in entities}
    entity_alias_map: Dict[str, List[str]] = defaultdict(list)
    for term in semantic_terms:
        ref_id = _safe_text(term.ontology_ref_id)
        if ref_id and ref_id in entity_map:
            entity_alias_map[ref_id].extend(_extract_semantic_alias_terms(term))

    entity_catalog: List[Dict[str, Any]] = []
    entity_catalog_by_id: Dict[str, Dict[str, Any]] = {}
    for entity in sorted(
        entities,
        key=lambda item: (
            0 if item.is_main_table else 1,
            int(item.sort_order or 0),
            _safe_text(item.entity_name),
        ),
    ):
        brief = _build_entity_brief(entity=entity, concept_map=concept_map, entity_alias_map=entity_alias_map)
        if not brief:
            continue
        entity_catalog.append(brief)
        entity_catalog_by_id[_safe_text(brief.get("entity_id"))] = brief

    relation_catalog = [
        row
        for row in (
            _build_relation_brief(rel, entity_catalog_by_id)
            for rel in relations
        )
        if row
    ]
    scope_catalog = _build_scope_catalog(entity_catalog)
    attribute_catalog = _build_attribute_catalog(entity_catalog)
    attribute_validation_catalog = _build_attribute_validation_catalog(entity_catalog, db_entities_by_id=entity_map)
    return {
        "source": "system",
        "scope_catalog": scope_catalog,
        "entity_catalog": entity_catalog,
        "attribute_catalog": attribute_catalog,
        "relation_catalog": relation_catalog,
        "attribute_validation_catalog": attribute_validation_catalog,
        "_meta": {
            "source": "system",
            "master_domain_count": len([item for item in scope_catalog if item.get("scope_type") == "master"]),
            "master_entity_count": len([item for item in entity_catalog if item.get("entity_type") == "master"]),
            "activity_domain_count": len([item for item in scope_catalog if item.get("scope_type") == "activity"]),
            "activity_entity_count": len([item for item in entity_catalog if item.get("entity_type") == "activity"]),
            "relation_count": len(relation_catalog),
        },
    }




def _flatten_attribute_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    entity_by_name: Dict[str, Dict[str, Any]] = {}
    entity_name_by_norm: Dict[str, str] = {}
    attribute_index_by_entity: Dict[str, Dict[str, Dict[str, Any]]] = {}
    relation_catalog = metadata.get("relation_catalog") or []

    for entity in metadata.get("entity_catalog") or []:
        if not isinstance(entity, dict):
            continue
        entity_name = _safe_text(entity.get("entity_name"))
        if not entity_name:
            continue
        entity_by_name[entity_name] = entity
        entity_name_by_norm[entity_name.lower()] = entity_name
        attr_index: Dict[str, Dict[str, Any]] = {}
        for attr in metadata.get("attribute_validation_catalog") or []:
            if not isinstance(attr, dict):
                continue
            if _safe_text(attr.get("entity_name")) != entity_name:
                continue
            keys = [
                _safe_text(attr.get("field_cn")),
                _safe_text(attr.get("field_en")),
                *[_safe_text(item) for item in (attr.get("aliases") or [])],
            ]
            for key in keys:
                norm = key.lower()
                if norm and norm not in attr_index:
                    attr_index[norm] = attr
        attribute_index_by_entity[entity_name] = attr_index

    relation_pairs: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for rel in relation_catalog if isinstance(relation_catalog, list) else []:
        if not isinstance(rel, dict):
            continue
        source = _safe_text(rel.get("source_entity_name"))
        target = _safe_text(rel.get("target_entity_name"))
        if not source or not target:
            continue
        relation_pairs[(source, target)] = rel
        relation_pairs[(target, source)] = rel

    return {
        "entity_by_name": entity_by_name,
        "entity_name_by_norm": entity_name_by_norm,
        "attribute_index_by_entity": attribute_index_by_entity,
        "relation_pairs": relation_pairs,
        "relation_catalog": relation_catalog if isinstance(relation_catalog, list) else [],
    }



def _validate_query_attribute_result(parsed_result: Dict[str, Any], metadata: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    result = _sanitize_attribute_result(parsed_result)
    flatten = _flatten_attribute_metadata(metadata)
    logs: List[Dict[str, Any]] = [{"check": "json_fields", "ok": True, "result_snapshot": deepcopy(result)}]

    valid_master_entities: List[Dict[str, Any]] = []
    valid_activity_entities: List[Dict[str, Any]] = []
    selected_entity_names: List[str] = []

    for row in result.get("master_entities") or []:
        entity_name = _safe_text(row.get("entity_name"))
        entity = flatten["entity_by_name"].get(entity_name)
        if entity and entity.get("entity_type") == "master":
            merged = {
                **row,
                "l1": entity.get("l1"),
                "l2": entity.get("l2"),
                "is_main_table": bool(entity.get("is_main_table")),
            }
            valid_master_entities.append(merged)
            selected_entity_names.append(entity_name)
        else:
            logs.append({"check": "master_entity_lookup", "ok": False, "entity_name": entity_name})

    for row in result.get("activity_entities") or []:
        entity_name = _safe_text(row.get("entity_name"))
        entity = flatten["entity_by_name"].get(entity_name)
        if entity and entity.get("entity_type") == "activity":
            merged = {
                **row,
                "l3": entity.get("l3"),
                "l4": entity.get("l4"),
                "is_main_table": bool(entity.get("is_main_table")),
            }
            valid_activity_entities.append(merged)
            selected_entity_names.append(entity_name)
        else:
            logs.append({"check": "activity_entity_lookup", "ok": False, "entity_name": entity_name})

    valid_resolved_attributes: List[Dict[str, Any]] = []
    for row in result.get("resolved_attributes") or []:
        entity_name = _safe_text(row.get("entity_name"))
        entity = flatten["entity_by_name"].get(entity_name)
        if not entity:
            logs.append({"check": "attribute_entity_lookup", "ok": False, "entity_name": entity_name, "attribute": row.get("raw_name")})
            continue
        attr_index = flatten["attribute_index_by_entity"].get(entity_name) or {}
        candidate_keys = [
            _safe_text(row.get("field_cn")).lower(),
            _safe_text(row.get("field_en")).lower(),
            _safe_text(row.get("normalized_name")).lower(),
            _safe_text(row.get("raw_name")).lower(),
        ]
        matched_attr = next((attr_index.get(key) for key in candidate_keys if key and attr_index.get(key)), None)
        if not matched_attr:
            logs.append({"check": "attribute_lookup", "ok": False, "entity_name": entity_name, "attribute": row.get("raw_name")})
            continue
        normalized = {
            **row,
            "entity_type": entity.get("entity_type"),
            "field_cn": _safe_text(matched_attr.get("field_cn")) or row.get("field_cn"),
            "field_en": matched_attr.get("field_en") or row.get("field_en"),
            "is_main_table": bool(entity.get("is_main_table")),
            "confidence": _normalize_confidence(row.get("confidence") or result.get("confidence")),
        }
        valid_resolved_attributes.append(normalized)
        selected_entity_names.append(entity_name)
        if entity.get("entity_type") == "master" and entity_name not in [item.get("entity_name") for item in valid_master_entities]:
            valid_master_entities.append(
                {
                    "entity_name": entity_name,
                    "entity_type": "master",
                    "role": "related",
                    "reason": "由属性归属反推实体",
                    "l1": entity.get("l1"),
                    "l2": entity.get("l2"),
                    "is_main_table": bool(entity.get("is_main_table")),
                }
            )
        if entity.get("entity_type") == "activity" and entity_name not in [item.get("entity_name") for item in valid_activity_entities]:
            valid_activity_entities.append(
                {
                    "entity_name": entity_name,
                    "entity_type": "activity",
                    "role": "related",
                    "reason": "由属性归属反推实体",
                    "l3": entity.get("l3"),
                    "l4": entity.get("l4"),
                    "is_main_table": bool(entity.get("is_main_table")),
                }
            )

    valid_relations: List[Dict[str, Any]] = []
    for row in result.get("relations") or []:
        relation = _pick_existing_relation(row.get("source_entity_name"), row.get("target_entity_name"), flatten)
        if not relation:
            logs.append({"check": "relation_lookup", "ok": False, "source_entity_name": row.get("source_entity_name"), "target_entity_name": row.get("target_entity_name")})
            continue
        valid_relations.append(relation)

    selected_entity_names = _dedupe_keep_order(selected_entity_names)
    if not valid_relations and len(selected_entity_names) >= 2:
        selected_set = set(selected_entity_names)
        for rel in flatten["relation_catalog"]:
            source = _safe_text(rel.get("source_entity_name"))
            target = _safe_text(rel.get("target_entity_name"))
            if source in selected_set and target in selected_set:
                valid_relations.append(rel)
    valid_relations = _dedupe_keep_order([
        json.dumps(item, ensure_ascii=False, sort_keys=True) for item in valid_relations
    ])
    valid_relations = [json.loads(item) for item in valid_relations]

    result["master_entities"] = valid_master_entities
    result["activity_entities"] = valid_activity_entities
    result["resolved_attributes"] = valid_resolved_attributes
    result["relations"] = valid_relations

    if valid_master_entities:
        result["l1"] = result.get("l1") or valid_master_entities[0].get("l1")
        result["l2"] = result.get("l2") or valid_master_entities[0].get("l2")
    if valid_activity_entities:
        result["l3"] = result.get("l3") or valid_activity_entities[0].get("l3")
        result["l4"] = result.get("l4") or valid_activity_entities[0].get("l4")

    if valid_master_entities and valid_activity_entities:
        result["scope_type"] = "mixed"
    elif valid_activity_entities:
        result["scope_type"] = "activity_only"
    elif valid_master_entities:
        result["scope_type"] = "master_only"
    elif result.get("scope_type") not in {"master_only", "activity_only", "mixed"}:
        result["scope_type"] = None

    if not valid_resolved_attributes:
        result["confidence"] = "LOW"
        if not _safe_text(result.get("reason")):
            result["reason"] = "未能校核出可用的属性归属结果"
    relation_groups = _group_relations(result.get("relations") or [])
    result["sql_blueprint"] = _build_sql_blueprint(result, relation_groups)
    logs.append(
        {
            "check": "final_validation",
            "ok": len(valid_resolved_attributes) > 0,
            "master_entity_count": len(valid_master_entities),
            "activity_entity_count": len(valid_activity_entities),
            "resolved_attribute_count": len(valid_resolved_attributes),
            "relation_count": len(valid_relations),
        }
    )
    return result, logs


def _build_attribute_result_panels(final_result: Dict[str, Any]) -> Dict[str, Any]:
    relation_groups = _group_relations(final_result.get("relations") or [])
    return {
        "summary": {
            "scope_type": final_result.get("scope_type"),
            "l1": final_result.get("l1"),
            "l2": final_result.get("l2"),
            "l3": final_result.get("l3"),
            "l4": final_result.get("l4"),
            "confidence": final_result.get("confidence"),
            "reason": final_result.get("reason"),
        },
        "master_entities": final_result.get("master_entities") or [],
        "activity_entities": final_result.get("activity_entities") or [],
        "resolved_attributes": final_result.get("resolved_attributes") or [],
        "requested_attributes": final_result.get("requested_attributes") or [],
        "relation_groups": relation_groups,
        "sql_blueprint": final_result.get("sql_blueprint") or _build_sql_blueprint(final_result, relation_groups),
        "query_scope": final_result.get("scope_type") or "master_only",
    }


def _build_query_attribute_llm_error(reason: Any) -> Dict[str, Any]:
    reason_text = _safe_text(reason)
    if reason_text == "llm_connection_not_found":
        message = "未找到可用大模型连接，请在前台显式选择模型，或在规划器配置中设置默认 LLM。"
    elif reason_text.startswith("llm_parse_failed:"):
        message = "大模型已返回内容，但返回的不是合法 JSON，当前在 Step3 解析失败。请收紧上下文范围或加强 JSON 约束。"
    else:
        message = "大模型调用失败，请检查连接配置、模型服务状态或返回内容。"
    return {
        "type": "llm_error",
        "reason": reason_text,
        "message": message,
    }
