from math import ceil
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.metadata_service import (
    build_metadata_resource_bundle,
    build_query_entity_metadata_diagnostics_view,
    build_query_attribute_metadata_view,
    build_query_entity_metadata_view,
)
from app.services.query_entity_service import _safe_text

router = APIRouter()


class MetadataViewRequest(BaseModel):
    compact: bool = Field(default=False, description="是否紧凑返回")
    include_stats: bool = Field(default=True, description="是否附带统计摘要")


def _parse_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _paginate(rows: List[Dict[str, Any]], page: int, page_size: int) -> Dict[str, Any]:
    total = len(rows)
    page = max(page, 1)
    page_size = min(max(page_size, 1), 500)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": ceil(total / page_size) if total else 0,
        "items": rows[start:end],
    }


@router.get("/metadata/snapshot")
def get_metadata_snapshot(db: Session = Depends(get_db)):
    bundle = build_metadata_resource_bundle(db)
    return {
        "code": 200,
        "data": {
            **bundle["snapshot"],
            "counts": bundle["stats"],
        },
    }


@router.get("/metadata/categories")
def list_metadata_categories(
    levels: Optional[str] = Query(default=None, description="逗号分隔的层级列表，例如 1,2,3,4"),
    tree: bool = Query(default=False, description="是否返回树结构"),
    db: Session = Depends(get_db),
):
    bundle = build_metadata_resource_bundle(db)
    rows = bundle["categories"]
    level_values = {int(item) for item in _parse_csv(levels) if item.isdigit()}
    if level_values:
        rows = [item for item in rows if int(item.get("level") or 0) in level_values]
    if tree:
        node_map: Dict[str, Dict[str, Any]] = {}
        roots: List[Dict[str, Any]] = []
        for item in rows:
            node_map[item["category_id"]] = {**item, "children": []}
        for item in node_map.values():
            parent_id = item.get("parent_id")
            parent = node_map.get(parent_id) if parent_id else None
            if parent is None:
                roots.append(item)
            else:
                parent["children"].append(item)
        data: Any = roots
    else:
        data = rows
    return {
        "code": 200,
        "snapshot": bundle["snapshot"],
        "data": data,
        "stats": {
            "returned_count": len(rows),
            **bundle["stats"],
        },
    }


@router.get("/metadata/entities")
def list_metadata_entities(
    keyword: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None, description="master/activity"),
    is_main_table: Optional[bool] = Query(default=None),
    category_ids: Optional[str] = Query(default=None, description="逗号分隔的分类ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    bundle = build_metadata_resource_bundle(db)
    rows = bundle["entities"]
    keyword_text = _safe_text(keyword).lower()
    category_id_set = set(_parse_csv(category_ids))
    if keyword_text:
        rows = [
            item
            for item in rows
            if keyword_text in _safe_text(item.get("entity_name")).lower()
            or keyword_text in _safe_text(item.get("entity_code")).lower()
            or keyword_text in _safe_text(item.get("entity_en_name")).lower()
            or any(keyword_text in _safe_text(alias).lower() for alias in item.get("aliases") or [])
        ]
    entity_type_text = _safe_text(entity_type).lower()
    if entity_type_text in {"master", "activity"}:
        rows = [item for item in rows if _safe_text(item.get("entity_type")).lower() == entity_type_text]
    if is_main_table is not None:
        rows = [item for item in rows if bool(item.get("is_main_table")) is is_main_table]
    if category_id_set:
        rows = [item for item in rows if _safe_text(item.get("category_id")) in category_id_set]
    page_result = _paginate(rows, page, page_size)
    return {
        "code": 200,
        "snapshot": bundle["snapshot"],
        "filters": {
            "keyword": keyword,
            "entity_type": entity_type_text or None,
            "is_main_table": is_main_table,
            "category_ids": sorted(category_id_set),
        },
        "page": {k: page_result[k] for k in ["page", "page_size", "total", "total_pages"]},
        "data": page_result["items"],
    }


@router.get("/metadata/attributes")
def list_metadata_attributes(
    keyword: Optional[str] = Query(default=None),
    entity_ids: Optional[str] = Query(default=None, description="逗号分隔的实体ID"),
    entity_type: Optional[str] = Query(default=None, description="master/activity"),
    queryable_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    bundle = build_metadata_resource_bundle(db)
    rows = bundle["attributes"]
    keyword_text = _safe_text(keyword).lower()
    entity_id_set = set(_parse_csv(entity_ids))
    if keyword_text:
        rows = [
            item
            for item in rows
            if keyword_text in _safe_text(item.get("field_name_cn")).lower()
            or keyword_text in _safe_text(item.get("field_name_en")).lower()
            or keyword_text in _safe_text(item.get("entity_name")).lower()
            or any(keyword_text in _safe_text(alias).lower() for alias in item.get("aliases") or [])
        ]
    if entity_id_set:
        rows = [item for item in rows if _safe_text(item.get("entity_id")) in entity_id_set]
    entity_type_text = _safe_text(entity_type).lower()
    if entity_type_text in {"master", "activity"}:
        rows = [item for item in rows if _safe_text(item.get("entity_type")).lower() == entity_type_text]
    if queryable_only:
        rows = [item for item in rows if bool(item.get("is_queryable"))]
    page_result = _paginate(rows, page, page_size)
    return {
        "code": 200,
        "snapshot": bundle["snapshot"],
        "filters": {
            "keyword": keyword,
            "entity_ids": sorted(entity_id_set),
            "entity_type": entity_type_text or None,
            "queryable_only": queryable_only,
        },
        "page": {k: page_result[k] for k in ["page", "page_size", "total", "total_pages"]},
        "data": page_result["items"],
    }


@router.get("/metadata/relations")
def list_metadata_relations(
    entity_ids: Optional[str] = Query(default=None, description="逗号分隔的实体ID，命中 source/target 任一侧"),
    source_entity_ids: Optional[str] = Query(default=None),
    target_entity_ids: Optional[str] = Query(default=None),
    keyword: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    bundle = build_metadata_resource_bundle(db)
    rows = bundle["relations"]
    entity_id_set = set(_parse_csv(entity_ids))
    source_id_set = set(_parse_csv(source_entity_ids))
    target_id_set = set(_parse_csv(target_entity_ids))
    keyword_text = _safe_text(keyword).lower()
    if entity_id_set:
        rows = [
            item
            for item in rows
            if _safe_text(item.get("source_entity_id")) in entity_id_set
            or _safe_text(item.get("target_entity_id")) in entity_id_set
        ]
    if source_id_set:
        rows = [item for item in rows if _safe_text(item.get("source_entity_id")) in source_id_set]
    if target_id_set:
        rows = [item for item in rows if _safe_text(item.get("target_entity_id")) in target_id_set]
    if keyword_text:
        rows = [
            item
            for item in rows
            if keyword_text in _safe_text(item.get("relation_name")).lower()
            or keyword_text in _safe_text(item.get("source_entity_name")).lower()
            or keyword_text in _safe_text(item.get("target_entity_name")).lower()
        ]
    page_result = _paginate(rows, page, page_size)
    return {
        "code": 200,
        "snapshot": bundle["snapshot"],
        "filters": {
            "entity_ids": sorted(entity_id_set),
            "source_entity_ids": sorted(source_id_set),
            "target_entity_ids": sorted(target_id_set),
            "keyword": keyword,
        },
        "page": {k: page_result[k] for k in ["page", "page_size", "total", "total_pages"]},
        "data": page_result["items"],
    }


@router.post("/metadata/views/query-entity")
def get_query_entity_metadata_view(payload: MetadataViewRequest, db: Session = Depends(get_db)):
    view = build_query_entity_metadata_view(db)
    data = view["data"]
    if payload.compact:
        data = {
            "domain_catalog": data.get("domain_catalog") or [],
            "relation_catalog": data.get("relation_catalog") or [],
            "_meta": data.get("_meta") or {},
        }
    response = {
        "code": 200,
        "view_code": view["view_code"],
        "data": data,
    }
    if payload.include_stats:
        response["stats"] = view["stats"]
    return response


@router.get("/metadata/diagnostics/query-entity")
def get_query_entity_metadata_diagnostics(db: Session = Depends(get_db)):
    view = build_query_entity_metadata_diagnostics_view(db)
    return {
        "code": 200,
        "view_code": view["view_code"],
        "data": view["data"],
        "stats": view["stats"],
    }


@router.post("/metadata/views/query-attribute")
def get_query_attribute_metadata_view(payload: MetadataViewRequest, db: Session = Depends(get_db)):
    view = build_query_attribute_metadata_view(db)
    data = view["data"]
    if payload.compact:
        data = {
            "scope_catalog": data.get("scope_catalog") or [],
            "entity_catalog": data.get("entity_catalog") or [],
            "attribute_catalog": data.get("attribute_catalog") or [],
            "relation_catalog": data.get("relation_catalog") or [],
            "attribute_validation_catalog": data.get("attribute_validation_catalog") or [],
        }
    response = {
        "code": 200,
        "view_code": view["view_code"],
        "data": data,
    }
    if payload.include_stats:
        response["stats"] = view["stats"]
    return response
