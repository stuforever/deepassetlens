"""
问属性 目录/元数据构建簇 -- 从 query_attribute_service.py 拆分（机械迁移，行为等价）

迁移内容：属性别名/明细提取簇（_extract_property_alias_terms/_extract_attribute_detail_rows/
_extract_attribute_names）、实体/关系 brief 簇（_build_entity_brief/_build_relation_brief）、
目录构建簇（_build_scope_catalog/_build_attribute_catalog/_build_attribute_validation_catalog/
_build_scope_path/_entity_role_to_attribute_entity_type）、query_entity_metadata 派生簇
（_build_attribute_entity_catalog_from_query_entity_metadata/
_build_attribute_relation_catalog_from_query_entity_metadata/
_build_attribute_prompt_metadata_from_query_entity_metadata/
_build_attribute_validation_metadata_from_query_entity_metadata）、召回/打分簇
（_score_attribute_hit_from_catalog/_recall_attribute_hits_from_validation_catalog/
_resolve_entity_candidates_from_attribute_hits）、示例元数据（_build_example_attribute_metadata）。

对外仍由 query_attribute_service.py 显式 re-export，外部引用路径不变。
"""

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.models.base import Concept, Entity, EntityRelation
from app.services.query_entity_service import (
    _dedupe_keep_order,
    _extract_entity_explanation_alias_terms,
    _prop_cn_name,
    _prop_en_name,
    _safe_text,
    _split_alias_text,
)


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
