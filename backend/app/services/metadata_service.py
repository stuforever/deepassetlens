import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.base import Concept, Entity, EntityRelation, StandardSemanticTerm
from app.services.query_attribute_service import (
    _build_entity_brief,
    _build_relation_brief,
    _extract_attribute_detail_rows,
    build_attribute_metadata_from_system,
)
from app.services.query_entity_service import (
    _extract_semantic_alias_terms,
    _safe_text,
    build_query_entity_metadata_diagnostics_from_system,
    build_metadata_from_system,
)

SCHEMA_VERSION = "1.0"


def _isoformat(value: Any) -> Optional[str]:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return None


def _concept_path(concept: Concept, concept_map: Dict[str, Concept]) -> Dict[str, List[str]]:
    path_ids: List[str] = []
    path_names: List[str] = []
    current: Optional[Concept] = concept
    guard = 0
    while current is not None and guard < 8:
        path_ids.append(str(current.id))
        path_names.append(_safe_text(current.name))
        current = concept_map.get(str(current.parent_id)) if current.parent_id else None
        guard += 1
    path_ids.reverse()
    path_names.reverse()
    return {"path_ids": path_ids, "path_names": path_names}


def _category_kind(level: int) -> str:
    if level == 2:
        return "master_domain"
    if level == 4:
        return "activity_domain"
    return "group"


def _make_snapshot(concepts: List[Concept], entities: List[Entity], relations: List[EntityRelation], stats: Dict[str, Any]) -> Dict[str, Any]:
    latest_at: Optional[datetime] = None
    for item in list(concepts) + list(entities) + list(relations):
        created_at = getattr(item, "created_at", None)
        if isinstance(created_at, datetime) and (latest_at is None or created_at > latest_at):
            latest_at = created_at
    hash_payload = {
        "concept_ids": sorted(str(item.id) for item in concepts),
        "entity_ids": sorted(str(item.id) for item in entities),
        "relation_ids": sorted(str(item.id) for item in relations),
        "stats": stats,
    }
    digest = hashlib.sha1(json.dumps(hash_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return {
        "snapshot_id": f"meta_{digest[:16]}",
        "schema_version": SCHEMA_VERSION,
        "generated_at": _isoformat(latest_at) or datetime.now(timezone.utc).isoformat(),
        "hash": digest,
    }


def build_metadata_resource_bundle(db: Session) -> Dict[str, Any]:
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
    children_by_parent: Dict[str, List[Concept]] = defaultdict(list)
    for concept in concepts:
        if concept.parent_id:
            children_by_parent[str(concept.parent_id)].append(concept)

    entity_map: Dict[str, Entity] = {str(item.id): item for item in entities}
    entity_alias_map: Dict[str, List[str]] = defaultdict(list)
    for term in semantic_terms:
        ref_id = _safe_text(term.ontology_ref_id)
        if ref_id and ref_id in entity_map:
            entity_alias_map[ref_id].extend(_extract_semantic_alias_terms(term))

    direct_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"entity_count": 0, "master_entity_count": 0, "activity_entity_count": 0})
    entity_resources: List[Dict[str, Any]] = []
    entity_resources_by_id: Dict[str, Dict[str, Any]] = {}
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
        concept = concept_map.get(str(entity.concept_id))
        if concept is None:
            continue
        parent = concept_map.get(str(concept.parent_id)) if concept.parent_id else None
        path_info = _concept_path(concept, concept_map)
        row = {
            **brief,
            "category_id": str(concept.id),
            "category_name": _safe_text(concept.name),
            "parent_category_id": str(parent.id) if parent else None,
            "parent_category_name": _safe_text(parent.name if parent else None) or None,
            "category_level": int(concept.level),
            "category_path_ids": path_info["path_ids"],
            "category_path_names": path_info["path_names"],
            "data_layer": _safe_text(entity.data_layer) or None,
            "description": _safe_text(entity.description) or None,
        }
        entity_resources.append(row)
        entity_resources_by_id[_safe_text(row.get("entity_id"))] = row
        counts = direct_counts[str(concept.id)]
        counts["entity_count"] += 1
        if row.get("entity_type") == "master":
            counts["master_entity_count"] += 1
        elif row.get("entity_type") == "activity":
            counts["activity_entity_count"] += 1

    aggregate_cache: Dict[str, Dict[str, int]] = {}

    def _aggregate_category_counts(concept_id: str) -> Dict[str, int]:
        if concept_id in aggregate_cache:
            return aggregate_cache[concept_id]
        total = dict(direct_counts.get(concept_id) or {"entity_count": 0, "master_entity_count": 0, "activity_entity_count": 0})
        for child in children_by_parent.get(concept_id, []):
            child_total = _aggregate_category_counts(str(child.id))
            total["entity_count"] += child_total["entity_count"]
            total["master_entity_count"] += child_total["master_entity_count"]
            total["activity_entity_count"] += child_total["activity_entity_count"]
        aggregate_cache[concept_id] = total
        return total

    category_resources: List[Dict[str, Any]] = []
    for concept in sorted(concepts, key=lambda item: (int(item.level or 0), int(item.sort_order or 0), _safe_text(item.name))):
        parent = concept_map.get(str(concept.parent_id)) if concept.parent_id else None
        path_info = _concept_path(concept, concept_map)
        counts = _aggregate_category_counts(str(concept.id))
        category_resources.append(
            {
                "category_id": str(concept.id),
                "category_name": _safe_text(concept.name),
                "level": int(concept.level or 0),
                "kind": _category_kind(int(concept.level or 0)),
                "parent_id": str(parent.id) if parent else None,
                "parent_name": _safe_text(parent.name if parent else None) or None,
                "path_ids": path_info["path_ids"],
                "path_names": path_info["path_names"],
                "description": _safe_text(concept.description) or None,
                "system_names": concept.system_names if isinstance(concept.system_names, list) else [],
                "sort_order": int(concept.sort_order or 0),
                "child_category_count": len(children_by_parent.get(str(concept.id), [])),
                **counts,
            }
        )

    attribute_resources: List[Dict[str, Any]] = []
    for entity in entities:
        entity_id = str(entity.id)
        entity_row = entity_resources_by_id.get(entity_id)
        if entity_row is None:
            continue
        for detail in _extract_attribute_detail_rows(entity, limit=10000):
            field_cn = _safe_text(detail.get("field_cn"))
            field_en = _safe_text(detail.get("field_en"))
            if not field_cn and not field_en:
                continue
            attribute_key = field_en or field_cn
            attribute_resources.append(
                {
                    "attribute_id": f"{entity_id}#{attribute_key}",
                    "entity_id": entity_id,
                    "entity_name": entity_row.get("entity_name"),
                    "entity_type": entity_row.get("entity_type"),
                    "category_id": entity_row.get("category_id"),
                    "category_name": entity_row.get("category_name"),
                    "parent_category_id": entity_row.get("parent_category_id"),
                    "parent_category_name": entity_row.get("parent_category_name"),
                    "field_name_cn": field_cn or None,
                    "field_name_en": field_en or None,
                    "aliases": detail.get("aliases") or [],
                    "data_type": _safe_text(detail.get("data_type")) or None,
                    "is_primary_key": bool(detail.get("is_primary_key")),
                    "is_required": bool(detail.get("is_required")),
                    "is_queryable": bool(detail.get("enable_query")),
                    "is_main_table": bool(entity_row.get("is_main_table")),
                    "sort_order": int(detail.get("sort_order") or 0),
                }
            )

    relation_resources: List[Dict[str, Any]] = []
    for rel in relations:
        row = _build_relation_brief(rel, entity_resources_by_id)
        if not row:
            continue
        source_entity = entity_resources_by_id.get(_safe_text(row.get("source_entity_id"))) or {}
        target_entity = entity_resources_by_id.get(_safe_text(row.get("target_entity_id"))) or {}
        relation_resources.append(
            {
                **row,
                "source_category_id": source_entity.get("category_id"),
                "source_category_name": source_entity.get("category_name"),
                "target_category_id": target_entity.get("category_id"),
                "target_category_name": target_entity.get("category_name"),
            }
        )

    stats = {
        "category_count": len(category_resources),
        "entity_count": len(entity_resources),
        "master_entity_count": len([item for item in entity_resources if item.get("entity_type") == "master"]),
        "activity_entity_count": len([item for item in entity_resources if item.get("entity_type") == "activity"]),
        "attribute_count": len(attribute_resources),
        "relation_count": len(relation_resources),
    }
    snapshot = _make_snapshot(concepts, entities, relations, stats)
    return {
        "snapshot": snapshot,
        "stats": stats,
        "categories": category_resources,
        "entities": entity_resources,
        "attributes": attribute_resources,
        "relations": relation_resources,
    }


def build_query_entity_metadata_view(db: Session) -> Dict[str, Any]:
    payload = build_metadata_from_system(db)
    return {
        "view_code": "query-entity",
        "data": payload,
        "stats": payload.get("_meta") or {},
    }


def build_query_attribute_metadata_view(db: Session) -> Dict[str, Any]:
    payload = build_attribute_metadata_from_system(db)
    return {
        "view_code": "query-attribute",
        "data": payload,
        "stats": payload.get("_meta") or {},
    }


def build_query_entity_metadata_diagnostics_view(db: Session) -> Dict[str, Any]:
    payload = build_query_entity_metadata_diagnostics_from_system(db)
    return {
        "view_code": "query-entity-diagnostics",
        "data": payload,
        "stats": payload.get("_meta") or {},
    }
