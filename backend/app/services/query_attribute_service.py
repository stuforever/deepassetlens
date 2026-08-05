import json
from collections import defaultdict
from copy import deepcopy
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.base import Concept, Entity, EntityRelation, StandardSemanticTerm
from app.services.query_entity_service import (
    _dedupe_keep_order,
    _extract_entity_explanation_alias_terms,
    _extract_semantic_alias_terms,
    _invoke_query_llm,
    _prop_cn_name,
    _prop_en_name,
    _safe_text,
    _split_alias_text,
)

ALLOWED_ATTRIBUTE_CLARIFICATION_SLOT_CODES = {
    "target_l2",
    "target_l2x",
    "target_l4x",
    "attribute_scope",
    "attribute_disambiguation",
    "generic",
}


def _extract_property_alias_terms(prop: Dict[str, Any]) -> List[str]:
    alias_terms: List[str] = []
    for key in ["aliases", "alias", "synonyms", "variants", "keywords", "keyword", "explanation", "description"]:
        value = prop.get(key)
        if isinstance(value, list):
            for item in value:
                alias_terms.extend(_split_alias_text(item))
        else:
            alias_terms.extend(_split_alias_text(value))
    cleaned: List[str] = []
    for alias in _dedupe_keep_order(alias_terms):
        if len(alias) > 40:
            continue
        cleaned.append(alias)
    return cleaned


def _extract_attribute_detail_rows(entity: Entity, limit: int = 20) -> List[Dict[str, Any]]:
    props = entity.properties_schema if isinstance(entity.properties_schema, list) else []
    rows: List[Dict[str, Any]] = []
    for index, prop in enumerate(props):
        if not isinstance(prop, dict):
            continue
        field_cn = _prop_cn_name(prop)
        field_en = _prop_en_name(prop)
        if not field_cn and not field_en:
            continue
        rows.append(
            {
                "field_cn": field_cn or field_en,
                "field_en": field_en or None,
                "aliases": _extract_property_alias_terms(prop),
                "data_type": _safe_text(prop.get("type") or prop.get("data_type") or prop.get("field_type")) or None,
                "is_primary_key": bool(prop.get("is_primary_key") or prop.get("isPrimaryKey")),
                "is_required": bool(prop.get("required") or prop.get("is_required")),
                "enable_query": bool(prop.get("enable_query_entity") or prop.get("enable_query_attribute")),
                "sort_order": int(prop.get("sort_order") or index),
            }
        )
    rows.sort(
        key=lambda item: (
            0 if item.get("is_primary_key") else 1,
            0 if item.get("enable_query") else 1,
            int(item.get("sort_order") or 0),
            _safe_text(item.get("field_cn")),
        )
    )
    return rows[:limit]


def _extract_attribute_names(entity: Entity, limit: int = 20) -> List[str]:
    detail_rows = _extract_attribute_detail_rows(entity, limit=limit)
    return [item.get("field_cn") for item in detail_rows if _safe_text(item.get("field_cn"))]


def _build_entity_brief(
    *,
    entity: Entity,
    concept_map: Dict[str, Concept],
    entity_alias_map: Dict[str, List[str]],
) -> Optional[Dict[str, Any]]:
    concept = concept_map.get(str(entity.concept_id))
    if not concept:
        return None
    if concept.level not in {2, 4}:
        return None
    parent = concept_map.get(str(concept.parent_id)) if concept.parent_id else None
    aliases = _dedupe_keep_order(
        _extract_entity_explanation_alias_terms(entity) + entity_alias_map.get(str(entity.id), [])
    )
    attribute_names = _extract_attribute_names(entity)
    data = {
        "entity_id": str(entity.id),
        "entity_name": _safe_text(entity.entity_name),
        "entity_code": _safe_text(entity.entity_code),
        "entity_en_name": _safe_text(entity.entity_en_name),
        "entity_explanation": _safe_text(getattr(entity, "entity_explanation", None)),
        "entity_type": "master" if concept.level == 2 else "activity",
        "l1": _safe_text(parent.name) if concept.level == 2 and parent else None,
        "l2": _safe_text(concept.name) if concept.level == 2 else None,
        "l3": _safe_text(parent.name) if concept.level == 4 and parent else None,
        "l4": _safe_text(concept.name) if concept.level == 4 else None,
        "is_main_table": bool(entity.is_main_table),
        "aliases": aliases,
        "attribute_count": len(attribute_names),
        "attribute_names": attribute_names,
        "sort_order": int(entity.sort_order or 0),
    }
    return data


def _build_relation_brief(
    rel: EntityRelation,
    entity_briefs_by_id: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    source = entity_briefs_by_id.get(_safe_text(rel.source_entity_id))
    target = entity_briefs_by_id.get(_safe_text(rel.target_entity_id))
    if not source or not target:
        return None
    return {
        "id": str(rel.id),
        "relation_name": _safe_text(rel.relation_name),
        "relation_category": _safe_text(rel.relation_category),
        "source_entity_id": source.get("entity_id"),
        "source_entity_name": source.get("entity_name"),
        "source_entity_type": source.get("entity_type"),
        "source_l1": source.get("l1"),
        "source_l2": source.get("l2"),
        "source_l3": source.get("l3"),
        "source_l4": source.get("l4"),
        "target_entity_id": target.get("entity_id"),
        "target_entity_name": target.get("entity_name"),
        "target_entity_type": target.get("entity_type"),
        "target_l1": target.get("l1"),
        "target_l2": target.get("l2"),
        "target_l3": target.get("l3"),
        "target_l4": target.get("l4"),
        "direction": _safe_text(rel.direction),
        "cardinality": _safe_text(rel.cardinality),
        "source_field_name": _safe_text(rel.source_field_name),
        "target_field_name": _safe_text(rel.target_field_name),
        "join_expr": _safe_text(rel.join_expr),
        "description": _safe_text(rel.description),
        "remark": _safe_text(rel.remark),
    }


def _build_scope_catalog(entity_catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for item in entity_catalog:
        entity_type = _safe_text(item.get("entity_type"))
        if entity_type == "master":
            key = ("master", _safe_text(item.get("l1")), _safe_text(item.get("l2")))
        else:
            key = ("activity", _safe_text(item.get("l3")), _safe_text(item.get("l4")))
        grouped[key].append(item)
    rows: List[Dict[str, Any]] = []
    for key, items in sorted(grouped.items(), key=lambda item: item[0]):
        scope_type, major_scope, minor_scope = key
        rows.append(
            {
                "scope_type": scope_type,
                "major_scope": major_scope or None,
                "minor_scope": minor_scope or None,
                "entity_count": len(items),
                "entity_names": [row.get("entity_name") for row in items if _safe_text(row.get("entity_name"))],
            }
        )
    return rows


def _build_attribute_catalog(entity_catalog: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for entity in entity_catalog:
        for field_cn in entity.get("attribute_names") or []:
            field_cn_text = _safe_text(field_cn)
            if not field_cn_text:
                continue
            rows.append(
                {
                    "entity_id": entity.get("entity_id"),
                    "entity_name": entity.get("entity_name"),
                    "entity_type": entity.get("entity_type"),
                    "l1": entity.get("l1"),
                    "l2": entity.get("l2"),
                    "l3": entity.get("l3"),
                    "l4": entity.get("l4"),
                    "is_main_table": bool(entity.get("is_main_table")),
                    "field_cn": field_cn_text,
                }
            )
    return rows


def _build_attribute_validation_catalog(entity_catalog: List[Dict[str, Any]], db_entities_by_id: Optional[Dict[str, Entity]] = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for entity in entity_catalog:
        entity_id = _safe_text(entity.get("entity_id"))
        db_entity = (db_entities_by_id or {}).get(entity_id) if entity_id else None
        detail_rows = _extract_attribute_detail_rows(db_entity, limit=200) if db_entity is not None else []
        if not detail_rows and isinstance(entity.get("attribute_names"), list):
            detail_rows = [{"field_cn": _safe_text(name)} for name in entity.get("attribute_names") or [] if _safe_text(name)]
        for attr in detail_rows:
            field_cn = _safe_text(attr.get("field_cn"))
            if not field_cn:
                continue
            rows.append(
                {
                    "entity_id": entity.get("entity_id"),
                    "entity_name": entity.get("entity_name"),
                    "entity_type": entity.get("entity_type"),
                    "field_cn": field_cn,
                    "field_en": _safe_text(attr.get("field_en")) or None,
                    "aliases": attr.get("aliases") or [],
                    "is_main_table": bool(entity.get("is_main_table")),
                }
            )
    return rows


def _build_scope_path(row: Dict[str, Any]) -> Optional[str]:
    entity_type = _safe_text(row.get("entity_type"))
    if entity_type == "master":
        parts = [_safe_text(row.get("l1")), _safe_text(row.get("l2"))]
    else:
        parts = [_safe_text(row.get("l3")), _safe_text(row.get("l4"))]
    values = [item for item in parts if item]
    return " / ".join(values) if values else None


def _entity_role_to_attribute_entity_type(role: Any) -> Optional[str]:
    role_text = _safe_text(role)
    if role_text.startswith("l2x"):
        return "master"
    if role_text == "l4x":
        return "activity"
    return None


def _build_attribute_entity_catalog_from_query_entity_metadata(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen_ids: set = set()

    def _append(row: Dict[str, Any]) -> None:
        entity_id = _safe_text(row.get("entity_id"))
        dedupe_key = entity_id or _safe_text(row.get("entity_name"))
        if not dedupe_key or dedupe_key in seen_ids:
            return
        seen_ids.add(dedupe_key)
        rows.append(row)

    for domain in metadata.get("domain_catalog") or []:
        if not isinstance(domain, dict):
            continue
        l1 = _safe_text(domain.get("l1")) or None
        l2 = _safe_text(domain.get("l2")) or None
        primary = domain.get("primary_entity") or {}
        if isinstance(primary, dict) and _safe_text(primary.get("name")):
            _append(
                {
                    "entity_id": _safe_text(primary.get("id")) or None,
                    "entity_name": _safe_text(primary.get("name")),
                    "entity_code": _safe_text(primary.get("entity_code")) or None,
                    "entity_en_name": _safe_text(primary.get("entity_en_name")) or None,
                    "entity_explanation": _safe_text(primary.get("entity_explanation")) or None,
                    "entity_type": "master",
                    "l1": l1,
                    "l2": l2,
                    "l3": None,
                    "l4": None,
                    "is_main_table": bool(primary.get("is_main_table")),
                    "aliases": primary.get("aliases") or [],
                    "attribute_names": [],
                    "sort_order": 0,
                }
            )
        for item in domain.get("secondary_entities") or []:
            if not isinstance(item, dict) or not _safe_text(item.get("name")):
                continue
            _append(
                {
                    "entity_id": _safe_text(item.get("id")) or None,
                    "entity_name": _safe_text(item.get("name")),
                    "entity_code": _safe_text(item.get("entity_code")) or None,
                    "entity_en_name": _safe_text(item.get("entity_en_name")) or None,
                    "entity_explanation": _safe_text(item.get("entity_explanation")) or None,
                    "entity_type": "master",
                    "l1": l1,
                    "l2": l2,
                    "l3": None,
                    "l4": None,
                    "is_main_table": bool(item.get("is_main_table")),
                    "aliases": item.get("aliases") or [],
                    "attribute_names": [],
                    "sort_order": 0,
                }
            )
        for item in domain.get("related_activity_entities") or []:
            if not isinstance(item, dict):
                continue
            entity_name = _safe_text(item.get("name"))
            if not entity_name:
                continue
            _append(
                {
                    "entity_id": _safe_text(item.get("id")) or None,
                    "entity_name": entity_name,
                    "entity_code": _safe_text(item.get("entity_code")) or None,
                    "entity_en_name": _safe_text(item.get("entity_en_name")) or None,
                    "entity_explanation": _safe_text(item.get("entity_explanation")) or None,
                    "entity_type": "activity",
                    "l1": None,
                    "l2": None,
                    "l3": _safe_text(item.get("l3")) or None,
                    "l4": _safe_text(item.get("l4")) or None,
                    "is_main_table": False,
                    "aliases": item.get("aliases") or [],
                    "attribute_names": [],
                    "sort_order": 0,
                }
            )

    rows.sort(
        key=lambda item: (
            0 if item.get("entity_type") == "master" else 1,
            0 if item.get("is_main_table") else 1,
            int(item.get("sort_order") or 0),
            _safe_text(item.get("entity_name")),
        )
    )
    return rows


def _build_attribute_relation_catalog_from_query_entity_metadata(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen: set = set()
    for item in metadata.get("relation_catalog") or []:
        if not isinstance(item, dict):
            continue
        relation_id = _safe_text(item.get("id"))
        source_entity_name = _safe_text(item.get("source_entity_name"))
        target_entity_name = _safe_text(item.get("target_entity_name"))
        if not source_entity_name or not target_entity_name:
            continue
        key = relation_id or (
            source_entity_name,
            target_entity_name,
            _safe_text(item.get("relation_name")),
        )
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "id": relation_id or None,
                "relation_name": _safe_text(item.get("relation_name")) or None,
                "relation_category": _safe_text(item.get("relation_category")) or None,
                "source_entity_id": _safe_text(item.get("source_entity_id")) or None,
                "source_entity_name": source_entity_name,
                "source_entity_type": _safe_text(item.get("source_entity_type")) or _entity_role_to_attribute_entity_type(item.get("source_entity_role")),
                "source_l1": _safe_text(item.get("source_l1")) or None,
                "source_l2": _safe_text(item.get("source_l2")) or None,
                "source_l3": _safe_text(item.get("source_l3")) or None,
                "source_l4": _safe_text(item.get("source_l4")) or None,
                "target_entity_id": _safe_text(item.get("target_entity_id")) or None,
                "target_entity_name": target_entity_name,
                "target_entity_type": _safe_text(item.get("target_entity_type")) or _entity_role_to_attribute_entity_type(item.get("target_entity_role")),
                "target_l1": _safe_text(item.get("target_l1")) or None,
                "target_l2": _safe_text(item.get("target_l2")) or None,
                "target_l3": _safe_text(item.get("target_l3")) or None,
                "target_l4": _safe_text(item.get("target_l4")) or None,
                "direction": _safe_text(item.get("direction")) or None,
                "cardinality": _safe_text(item.get("cardinality")) or None,
                "source_field_name": _safe_text(item.get("source_field_name")) or None,
                "target_field_name": _safe_text(item.get("target_field_name")) or None,
                "join_expr": _safe_text(item.get("join_expr")) or None,
                "description": _safe_text(item.get("description")) or None,
                "remark": _safe_text(item.get("remark")) or None,
            }
        )
    return rows


def _build_attribute_prompt_metadata_from_query_entity_metadata(
    metadata: Dict[str, Any],
    attribute_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    entity_catalog = _build_attribute_entity_catalog_from_query_entity_metadata(metadata)
    relation_catalog = _build_attribute_relation_catalog_from_query_entity_metadata(metadata)
    attribute_rows = attribute_rows or []
    attribute_names_by_entity: Dict[str, List[str]] = defaultdict(list)
    for row in attribute_rows:
        if not isinstance(row, dict):
            continue
        entity_name = _safe_text(row.get("entity_name"))
        field_cn = _safe_text(row.get("field_cn"))
        if entity_name and field_cn:
            attribute_names_by_entity[entity_name].append(field_cn)

    entity_rows: List[Dict[str, Any]] = []
    for item in entity_catalog:
        entity_name = _safe_text(item.get("entity_name"))
        entity_rows.append(
            {
                "entity_id": item.get("entity_id"),
                "entity_name": entity_name,
                "entity_type": item.get("entity_type"),
                "scope_path": _build_scope_path(item),
                "is_main_table": bool(item.get("is_main_table")),
                "attribute_names": _dedupe_keep_order(attribute_names_by_entity.get(entity_name) or []),
            }
        )
    return {
        "entity_rows": entity_rows,
        "relation_rows": relation_catalog,
        "attribute_rows": attribute_rows,
    }


def _build_attribute_validation_metadata_from_query_entity_metadata(
    metadata: Dict[str, Any],
    attribute_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    entity_catalog = _build_attribute_entity_catalog_from_query_entity_metadata(metadata)
    relation_catalog = _build_attribute_relation_catalog_from_query_entity_metadata(metadata)
    validation_rows: List[Dict[str, Any]] = []
    for row in attribute_rows or []:
        if not isinstance(row, dict):
            continue
        field_cn = _safe_text(row.get("field_cn"))
        entity_name = _safe_text(row.get("entity_name"))
        if not field_cn or not entity_name:
            continue
        validation_rows.append(
            {
                "entity_id": row.get("entity_id"),
                "entity_name": entity_name,
                "entity_type": _safe_text(row.get("entity_type")) or None,
                "field_cn": field_cn,
                "field_en": _safe_text(row.get("field_en")) or None,
                "aliases": row.get("aliases") or [],
                "is_main_table": bool(row.get("is_main_table")),
            }
        )
    return {
        "entity_catalog": entity_catalog,
        "relation_catalog": relation_catalog,
        "attribute_validation_catalog": validation_rows,
    }


def _score_attribute_hit_from_catalog(query_norm: str, row: Dict[str, Any]) -> float:
    candidates = [
        _safe_text(row.get("field_cn")),
        _safe_text(row.get("field_en")),
        *[_safe_text(item) for item in (row.get("aliases") or [])],
    ]
    score = 0.0
    for text in candidates:
        norm = text.lower()
        if not norm:
            continue
        if norm == query_norm:
            score = max(score, 1.0)
        elif norm and norm in query_norm:
            score = max(score, 0.9)
        elif query_norm and query_norm in norm:
            score = max(score, 0.75)
    return score


def _recall_attribute_hits_from_validation_catalog(
    user_query: str,
    validation_catalog: List[Dict[str, Any]],
    *,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    query_norm = _safe_text(user_query).lower()
    rows: List[Dict[str, Any]] = []
    for item in validation_catalog or []:
        if not isinstance(item, dict):
            continue
        score = _score_attribute_hit_from_catalog(query_norm, item)
        if score <= 0:
            continue
        rows.append(
            {
                "attribute_doc_id": f"{_safe_text(item.get('entity_id'))}#{_safe_text(item.get('field_en') or item.get('field_cn'))}",
                "entity_id": item.get("entity_id"),
                "entity_name": item.get("entity_name"),
                "attribute_name": item.get("field_cn"),
                "field_cn": item.get("field_cn"),
                "field_en": item.get("field_en"),
                "aliases": item.get("aliases") or [],
                "score": round(score, 4),
                "doc_type": "attribute",
                "scene": "query_attribute",
            }
        )
    rows.sort(key=lambda item: (-float(item.get("score") or 0.0), _safe_text(item.get("attribute_name"))))
    return rows[: max(1, min(limit, 100))]


def _resolve_entity_candidates_from_attribute_hits(
    attribute_hits: List[Dict[str, Any]],
    *,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    grouped: Dict[str, Dict[str, Any]] = {}
    for index, row in enumerate(attribute_hits):
        entity_id = _safe_text(row.get("entity_id"))
        entity_name = _safe_text(row.get("entity_name"))
        key = entity_id or entity_name
        if not key:
            continue
        bucket = grouped.setdefault(
            key,
            {
                "entity_id": entity_id or None,
                "entity_name": entity_name or None,
                "score": 0.0,
                "hit_count": 0,
                "top_attribute_names": [],
                "_rank_bonus": 0.0,
            },
        )
        score = float(row.get("score") or 0.0)
        bucket["score"] = max(float(bucket.get("score") or 0.0), score)
        bucket["hit_count"] = int(bucket.get("hit_count") or 0) + 1
        if _safe_text(row.get("attribute_name")):
            bucket["top_attribute_names"].append(_safe_text(row.get("attribute_name")))
        bucket["_rank_bonus"] += max(0.0, 0.1 - index * 0.005)

    candidates: List[Dict[str, Any]] = []
    for item in grouped.values():
        merged_score = float(item.get("score") or 0.0) + float(item.get("_rank_bonus") or 0.0) + min(0.2, int(item.get("hit_count") or 0) * 0.03)
        candidates.append(
            {
                "entity_id": item.get("entity_id"),
                "entity_name": item.get("entity_name"),
                "score": round(min(1.0, merged_score), 4),
                "hit_count": int(item.get("hit_count") or 0),
                "top_attribute_names": _dedupe_keep_order(item.get("top_attribute_names") or [])[:5],
            }
        )
    candidates.sort(key=lambda item: (-float(item.get("score") or 0.0), _safe_text(item.get("entity_name"))))
    return candidates[: max(1, min(limit, 50))]


def _build_example_attribute_metadata() -> Dict[str, Any]:
    entity_catalog = [
        {
            "entity_id": "attr_customer_main",
            "entity_name": "用电客户信息",
            "entity_code": "E_CUSTOMER_MAIN",
            "entity_en_name": "power_customer_main",
            "entity_explanation": "用电客户主表",
            "entity_type": "master",
            "l1": "客户",
            "l2": "用电客户",
            "l3": None,
            "l4": None,
            "is_main_table": True,
            "aliases": ["用电客户", "客户档案"],
            "attribute_count": 4,
            "attribute_names": ["用电客户标识", "行业分类", "重要性等级", "客户名称"],
            "sort_order": 0,
        },
        {
            "entity_id": "attr_customer_contact",
            "entity_name": "客户联系电话信息",
            "entity_code": "E_CUSTOMER_CONTACT",
            "entity_en_name": "power_customer_contact",
            "entity_explanation": "客户联系电话从表",
            "entity_type": "master",
            "l1": "客户",
            "l2": "用电客户",
            "l3": None,
            "l4": None,
            "is_main_table": False,
            "aliases": ["联系电话", "客户电话"],
            "attribute_count": 2,
            "attribute_names": ["联系电话", "联系电话类型"],
            "sort_order": 1,
        },
        {
            "entity_id": "attr_customer_cert",
            "entity_name": "客户证件信息",
            "entity_code": "E_CUSTOMER_CERT",
            "entity_en_name": "power_customer_cert",
            "entity_explanation": "客户证件从表",
            "entity_type": "master",
            "l1": "客户",
            "l2": "用电客户",
            "l3": None,
            "l4": None,
            "is_main_table": False,
            "aliases": ["证件信息", "客户证件"],
            "attribute_count": 2,
            "attribute_names": ["证件类型", "证件编号"],
            "sort_order": 2,
        },
        {
            "entity_id": "attr_meter_main",
            "entity_name": "计量点信息",
            "entity_code": "E_METER_POINT_MAIN",
            "entity_en_name": "meter_point_main",
            "entity_explanation": "计量点主表",
            "entity_type": "master",
            "l1": "设备",
            "l2": "计量点",
            "l3": None,
            "l4": None,
            "is_main_table": True,
            "aliases": ["计量点", "安装点"],
            "attribute_count": 3,
            "attribute_names": ["安装点编号", "设备标识", "综合倍率"],
            "sort_order": 0,
        },
        {
            "entity_id": "attr_meter_read",
            "entity_name": "计量点抄表记录",
            "entity_code": "E_METER_READ",
            "entity_en_name": "meter_read_record",
            "entity_explanation": "计量点抄表活动记录",
            "entity_type": "activity",
            "l1": None,
            "l2": None,
            "l3": "计量管理",
            "l4": "抄表信息",
            "is_main_table": False,
            "aliases": ["抄表信息", "抄表记录"],
            "attribute_count": 3,
            "attribute_names": ["本次实际抄表日期", "本次抄见示数", "抄见位数"],
            "sort_order": 0,
        },
    ]
    relation_catalog = [
        {
            "id": "attr_rel_customer_contact",
            "relation_name": "客户与联系电话",
            "relation_category": "手工维护",
            "source_entity_id": "attr_customer_main",
            "source_entity_name": "用电客户信息",
            "source_entity_type": "master",
            "source_l1": "客户",
            "source_l2": "用电客户",
            "source_l3": None,
            "source_l4": None,
            "target_entity_id": "attr_customer_contact",
            "target_entity_name": "客户联系电话信息",
            "target_entity_type": "master",
            "target_l1": "客户",
            "target_l2": "用电客户",
            "target_l3": None,
            "target_l4": None,
            "direction": "forward",
            "cardinality": "1:N",
            "source_field_name": "customer_id",
            "target_field_name": "customer_id",
            "join_expr": "customer.customer_id = contact.customer_id",
            "description": "客户与联系电话从表关系",
            "remark": "",
        },
        {
            "id": "attr_rel_customer_cert",
            "relation_name": "客户与证件",
            "relation_category": "手工维护",
            "source_entity_id": "attr_customer_main",
            "source_entity_name": "用电客户信息",
            "source_entity_type": "master",
            "source_l1": "客户",
            "source_l2": "用电客户",
            "source_l3": None,
            "source_l4": None,
            "target_entity_id": "attr_customer_cert",
            "target_entity_name": "客户证件信息",
            "target_entity_type": "master",
            "target_l1": "客户",
            "target_l2": "用电客户",
            "target_l3": None,
            "target_l4": None,
            "direction": "forward",
            "cardinality": "1:N",
            "source_field_name": "customer_id",
            "target_field_name": "customer_id",
            "join_expr": "customer.customer_id = cert.customer_id",
            "description": "客户与证件从表关系",
            "remark": "",
        },
        {
            "id": "attr_rel_meter_read",
            "relation_name": "计量点与抄表记录",
            "relation_category": "手工维护",
            "source_entity_id": "attr_meter_main",
            "source_entity_name": "计量点信息",
            "source_entity_type": "master",
            "source_l1": "设备",
            "source_l2": "计量点",
            "source_l3": None,
            "source_l4": None,
            "target_entity_id": "attr_meter_read",
            "target_entity_name": "计量点抄表记录",
            "target_entity_type": "activity",
            "target_l1": None,
            "target_l2": None,
            "target_l3": "计量管理",
            "target_l4": "抄表信息",
            "direction": "forward",
            "cardinality": "1:N",
            "source_field_name": "meter_point_id",
            "target_field_name": "meter_point_id",
            "join_expr": "meter_point.meter_point_id = meter_read.meter_point_id",
            "description": "计量点与抄表记录关系",
            "remark": "",
        },
    ]
    scope_catalog = _build_scope_catalog(entity_catalog)
    attribute_catalog = _build_attribute_catalog(entity_catalog)
    attribute_validation_catalog = [
        {"entity_id": "attr_customer_main", "entity_name": "用电客户信息", "entity_type": "master", "field_cn": "用电客户标识", "field_en": "customer_id", "aliases": [], "is_main_table": True},
        {"entity_id": "attr_customer_main", "entity_name": "用电客户信息", "entity_type": "master", "field_cn": "行业分类", "field_en": "industry_category", "aliases": [], "is_main_table": True},
        {"entity_id": "attr_customer_main", "entity_name": "用电客户信息", "entity_type": "master", "field_cn": "重要性等级", "field_en": "importance_level", "aliases": [], "is_main_table": True},
        {"entity_id": "attr_customer_main", "entity_name": "用电客户信息", "entity_type": "master", "field_cn": "客户名称", "field_en": "customer_name", "aliases": [], "is_main_table": True},
        {"entity_id": "attr_customer_contact", "entity_name": "客户联系电话信息", "entity_type": "master", "field_cn": "联系电话", "field_en": "contact_phone", "aliases": [], "is_main_table": False},
        {"entity_id": "attr_customer_contact", "entity_name": "客户联系电话信息", "entity_type": "master", "field_cn": "联系电话类型", "field_en": "contact_type", "aliases": [], "is_main_table": False},
        {"entity_id": "attr_customer_cert", "entity_name": "客户证件信息", "entity_type": "master", "field_cn": "证件类型", "field_en": "cert_type", "aliases": [], "is_main_table": False},
        {"entity_id": "attr_customer_cert", "entity_name": "客户证件信息", "entity_type": "master", "field_cn": "证件编号", "field_en": "cert_no", "aliases": [], "is_main_table": False},
        {"entity_id": "attr_meter_main", "entity_name": "计量点信息", "entity_type": "master", "field_cn": "安装点编号", "field_en": "install_point_no", "aliases": [], "is_main_table": True},
        {"entity_id": "attr_meter_main", "entity_name": "计量点信息", "entity_type": "master", "field_cn": "设备标识", "field_en": "device_id", "aliases": [], "is_main_table": True},
        {"entity_id": "attr_meter_main", "entity_name": "计量点信息", "entity_type": "master", "field_cn": "综合倍率", "field_en": "composite_ratio", "aliases": [], "is_main_table": True},
        {"entity_id": "attr_meter_read", "entity_name": "计量点抄表记录", "entity_type": "activity", "field_cn": "本次实际抄表日期", "field_en": "actual_read_date", "aliases": [], "is_main_table": False},
        {"entity_id": "attr_meter_read", "entity_name": "计量点抄表记录", "entity_type": "activity", "field_cn": "本次抄见示数", "field_en": "current_read_value", "aliases": [], "is_main_table": False},
        {"entity_id": "attr_meter_read", "entity_name": "计量点抄表记录", "entity_type": "activity", "field_cn": "抄见位数", "field_en": "read_digits", "aliases": [], "is_main_table": False},
    ]
    return {
        "source": "example",
        "scope_catalog": scope_catalog,
        "entity_catalog": entity_catalog,
        "attribute_catalog": attribute_catalog,
        "relation_catalog": relation_catalog,
        "attribute_validation_catalog": attribute_validation_catalog,
        "_meta": {
            "source": "example",
            "master_domain_count": len([item for item in scope_catalog if item.get("scope_type") == "master"]),
            "master_entity_count": len([item for item in entity_catalog if item.get("entity_type") == "master"]),
            "activity_domain_count": len([item for item in scope_catalog if item.get("scope_type") == "activity"]),
            "activity_entity_count": len([item for item in entity_catalog if item.get("entity_type") == "activity"]),
            "relation_count": 3,
        },
    }


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




def _make_empty_attribute_result(reason: str) -> Dict[str, Any]:
    return {
        "scope_type": None,
        "l1": None,
        "l2": None,
        "l3": None,
        "l4": None,
        "master_entities": [],
        "activity_entities": [],
        "requested_attributes": [],
        "resolved_attributes": [],
        "relations": [],
        "confidence": "LOW",
        "reason": reason,
    }


def _normalize_confidence(value: Any) -> str:
    text = _safe_text(value).upper()
    return text if text in {"HIGH", "MEDIUM", "LOW"} else "LOW"


def _extract_attribute_llm_clarification(data: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(data, dict):
        return None
    decision = _safe_text(data.get("decision")).lower()
    if decision != "clarify":
        return None
    question = _safe_text(data.get("clarification_question"))
    if not question:
        return None
    slot_code = _safe_text(data.get("clarification_slot_code")) or "generic"
    if slot_code not in ALLOWED_ATTRIBUTE_CLARIFICATION_SLOT_CODES:
        slot_code = "generic"
    options: List[Dict[str, Any]] = []
    for item in data.get("clarification_options") or []:
        if not isinstance(item, dict):
            continue
        label = _safe_text(item.get("label") or item.get("value"))
        value = _safe_text(item.get("value") or item.get("label"))
        if not label or not value:
            continue
        options.append(
            {
                "label": label,
                "value": value,
                "description": _safe_text(item.get("description")) or None,
            }
        )
    multi_select = bool(data.get("clarification_multi_select"))
    manual_allowed = data.get("clarification_manual_allowed")
    return {
        "slot_code": slot_code,
        "question": question,
        "hint": _safe_text(data.get("clarification_hint")) or None,
        "options": options[:5],
        "multi_select": multi_select,
        "manual_allowed": True if manual_allowed is None else bool(manual_allowed),
        "reason": _safe_text(data.get("reason")) or "当前属性归属信息不足，需要继续澄清。",
        "confidence": _normalize_confidence(data.get("confidence")),
    }


def _sanitize_entity_rows(rows: Any, entity_type: str) -> List[Dict[str, Any]]:
    sanitized: List[Dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        entity_name = _safe_text(row.get("entity_name"))
        if not entity_name:
            continue
        sanitized.append(
            {
                "entity_name": entity_name,
                "entity_type": entity_type,
                "role": _safe_text(row.get("role")) or ("activity" if entity_type == "activity" else "main"),
                "reason": _safe_text(row.get("reason")),
            }
        )
    return sanitized


def _sanitize_requested_attributes(rows: Any) -> List[Dict[str, Any]]:
    sanitized: List[Dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict):
            raw_name = _safe_text(row.get("raw_name") or row.get("normalized_name"))
            normalized_name = _safe_text(row.get("normalized_name") or row.get("raw_name"))
        else:
            raw_name = _safe_text(row)
            normalized_name = raw_name
        if not raw_name and not normalized_name:
            continue
        sanitized.append(
            {
                "raw_name": raw_name or normalized_name,
                "normalized_name": normalized_name or raw_name,
            }
        )
    return sanitized


def _sanitize_resolved_attributes(rows: Any) -> List[Dict[str, Any]]:
    sanitized: List[Dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        raw_name = _safe_text(row.get("raw_name") or row.get("normalized_name") or row.get("field_cn"))
        entity_name = _safe_text(row.get("entity_name"))
        field_cn = _safe_text(row.get("field_cn") or row.get("normalized_name") or raw_name)
        if not raw_name or not entity_name or not field_cn:
            continue
        sanitized.append(
            {
                "raw_name": raw_name,
                "normalized_name": _safe_text(row.get("normalized_name")) or field_cn,
                "entity_type": _safe_text(row.get("entity_type")) or None,
                "entity_name": entity_name,
                "field_cn": field_cn,
                "field_en": _safe_text(row.get("field_en")) or None,
                "is_main_table": bool(row.get("is_main_table")),
                "access_mode": _safe_text(row.get("access_mode")) or "direct",
                "source_entity_name": _safe_text(row.get("source_entity_name")) or None,
                "relation_hint": _safe_text(row.get("relation_hint") or row.get("relation_name")) or None,
                "confidence": _normalize_confidence(row.get("confidence")),
                "reason": _safe_text(row.get("reason")),
            }
        )
    return sanitized


def _sanitize_relations(rows: Any) -> List[Dict[str, Any]]:
    sanitized: List[Dict[str, Any]] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        source_entity_name = _safe_text(row.get("source_entity_name"))
        target_entity_name = _safe_text(row.get("target_entity_name"))
        if not source_entity_name or not target_entity_name:
            continue
        sanitized.append(
            {
                "source_entity_name": source_entity_name,
                "target_entity_name": target_entity_name,
                "relation_name": _safe_text(row.get("relation_name")) or None,
                "join_expr": _safe_text(row.get("join_expr")) or None,
            }
        )
    return sanitized


def _sanitize_attribute_result(data: Any) -> Dict[str, Any]:
    base = _make_empty_attribute_result("未识别到可用的问属性结果")
    if not isinstance(data, dict):
        return base
    result = deepcopy(base)
    result["scope_type"] = _safe_text(data.get("scope_type")) or None
    result["l1"] = _safe_text(data.get("l1")) or None
    result["l2"] = _safe_text(data.get("l2")) or None
    result["l3"] = _safe_text(data.get("l3")) or None
    result["l4"] = _safe_text(data.get("l4")) or None
    result["master_entities"] = _sanitize_entity_rows(data.get("master_entities"), "master")
    result["activity_entities"] = _sanitize_entity_rows(data.get("activity_entities"), "activity")
    result["requested_attributes"] = _sanitize_requested_attributes(data.get("requested_attributes"))
    result["resolved_attributes"] = _sanitize_resolved_attributes(data.get("resolved_attributes"))
    result["relations"] = _sanitize_relations(data.get("relations"))
    result["confidence"] = _normalize_confidence(data.get("confidence"))
    result["reason"] = _safe_text(data.get("reason")) or result["reason"]
    return result


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


def _pick_existing_relation(
    source_entity_name: str,
    target_entity_name: str,
    flatten: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    return flatten["relation_pairs"].get((_safe_text(source_entity_name), _safe_text(target_entity_name)))


def _group_relations(relations: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped = {
        "master_to_master": [],
        "activity_to_activity": [],
        "master_to_activity": [],
    }
    for rel in relations:
        source_type = _safe_text(rel.get("source_entity_type"))
        target_type = _safe_text(rel.get("target_entity_type"))
        if source_type == "master" and target_type == "master":
            grouped["master_to_master"].append(rel)
        elif source_type == "activity" and target_type == "activity":
            grouped["activity_to_activity"].append(rel)
        else:
            grouped["master_to_activity"].append(rel)
    return grouped


def _quote_sql_identifier(value: Any) -> str:
    text = _safe_text(value)
    if not text:
        return ""
    return f"`{text.replace('`', '``')}`"


def _build_sql_text(blueprint: Dict[str, Any]) -> str:
    if not isinstance(blueprint, dict) or not blueprint.get("sql_ready"):
        return ""
    anchor_entity = _safe_text(blueprint.get("anchor_entity"))
    select_fields = blueprint.get("select_fields") or []
    join_relations = blueprint.get("join_relations") or []
    if not anchor_entity or not select_fields:
        return ""

    select_lines: List[str] = []
    for row in select_fields:
        entity_name = _safe_text(row.get("entity_name")) or anchor_entity
        field_name = _safe_text(row.get("field_en")) or _safe_text(row.get("field_cn"))
        field_alias = _safe_text(row.get("field_cn")) or field_name
        if not field_name:
            continue
        select_lines.append(
            f"  {_quote_sql_identifier(entity_name)}.{_quote_sql_identifier(field_name)} AS {_quote_sql_identifier(field_alias)}"
        )
    if not select_lines:
        return ""

    sql_lines: List[str] = [
        "SELECT",
        ",\n".join(select_lines),
        f"FROM {_quote_sql_identifier(anchor_entity)}",
    ]

    seen_joins = set()
    for rel in join_relations:
        source_entity_name = _safe_text(rel.get("source_entity_name"))
        target_entity_name = _safe_text(rel.get("target_entity_name"))
        join_expr = _safe_text(rel.get("join_expr"))
        if not target_entity_name:
            continue
        join_key = (source_entity_name, target_entity_name, join_expr)
        if join_key in seen_joins:
            continue
        seen_joins.add(join_key)
        join_line = f"LEFT JOIN {_quote_sql_identifier(target_entity_name)}"
        if join_expr:
            join_line += f"\n  ON {join_expr}"
        sql_lines.append(join_line)

    sql_lines[-1] = f"{sql_lines[-1]};"
    return "\n".join(sql_lines)


def _build_sql_blueprint(final_result: Dict[str, Any], relation_groups: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
    master_entities = final_result.get("master_entities") or []
    activity_entities = final_result.get("activity_entities") or []
    resolved_attributes = final_result.get("resolved_attributes") or []
    anchor_entity = next(
        (
            item.get("entity_name")
            for item in master_entities
            if item.get("is_main_table") and _safe_text(item.get("entity_name"))
        ),
        None,
    ) or next(
        (item.get("entity_name") for item in master_entities if _safe_text(item.get("entity_name"))),
        None,
    ) or next(
        (item.get("entity_name") for item in activity_entities if _safe_text(item.get("entity_name"))),
        None,
    )
    select_fields = [
        {
            "entity_name": _safe_text(row.get("entity_name")),
            "entity_type": _safe_text(row.get("entity_type")) or None,
            "field_cn": _safe_text(row.get("field_cn")),
            "field_en": _safe_text(row.get("field_en")) or None,
            "is_main_table": bool(row.get("is_main_table")),
            "access_mode": _safe_text(row.get("access_mode")) or "direct",
            "source_entity_name": _safe_text(row.get("source_entity_name")) or None,
            "relation_hint": _safe_text(row.get("relation_hint")) or None,
        }
        for row in resolved_attributes
        if _safe_text(row.get("entity_name")) and _safe_text(row.get("field_cn"))
    ]
    join_relations = [
        {
            "source_entity_name": _safe_text(rel.get("source_entity_name")),
            "target_entity_name": _safe_text(rel.get("target_entity_name")),
            "join_expr": _safe_text(rel.get("join_expr")) or None,
            "relation_name": _safe_text(rel.get("relation_name")) or None,
        }
        for rel in (
            (relation_groups.get("master_to_master") or [])
            + (relation_groups.get("activity_to_activity") or [])
            + (relation_groups.get("master_to_activity") or [])
        )
        if _safe_text(rel.get("source_entity_name")) and _safe_text(rel.get("target_entity_name"))
    ]
    blueprint = {
        "scope_type": final_result.get("scope_type"),
        "anchor_entity": anchor_entity,
        "involved_entities": _dedupe_keep_order(
            [
                *[_safe_text(item.get("entity_name")) for item in master_entities],
                *[_safe_text(item.get("entity_name")) for item in activity_entities],
            ]
        ),
        "select_fields": select_fields,
        "join_relations": join_relations,
        "unresolved_attributes": [
            item
            for item in (final_result.get("requested_attributes") or [])
            if _safe_text(item.get("normalized_name") or item.get("raw_name"))
            not in {
                _safe_text(row.get("normalized_name") or row.get("raw_name"))
                for row in resolved_attributes
            }
        ],
        "sql_ready": bool(anchor_entity and select_fields),
    }
    blueprint["sql_text"] = _build_sql_text(blueprint)
    return blueprint


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
