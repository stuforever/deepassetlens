"""
问属性 service -- 机械拆分后的兼容门面（行为等价）

原实现已按簇拆分为两个兄弟模块：
- query_attribute_catalog.py：目录/元数据构建簇（原 L32-762）
- query_attribute_pipeline.py：入口/校验/面板簇（原 L765-1075）

本文件保留全部原顶层名字的显式 re-export；
外部 `from app.services.query_attribute_service import X` 与
`app.services.query_attribute_service.X` 属性访问均不变。
"""

from .query_attribute_catalog import (
    _build_attribute_catalog,
    _build_attribute_entity_catalog_from_query_entity_metadata,
    _build_attribute_prompt_metadata_from_query_entity_metadata,
    _build_attribute_relation_catalog_from_query_entity_metadata,
    _build_attribute_validation_catalog,
    _build_attribute_validation_metadata_from_query_entity_metadata,
    _build_entity_brief,
    _build_example_attribute_metadata,
    _build_relation_brief,
    _build_scope_catalog,
    _build_scope_path,
    _entity_role_to_attribute_entity_type,
    _extract_attribute_detail_rows,
    _extract_attribute_names,
    _extract_property_alias_terms,
    _recall_attribute_hits_from_validation_catalog,
    _resolve_entity_candidates_from_attribute_hits,
    _score_attribute_hit_from_catalog,
)
from .query_attribute_pipeline import (
    _build_attribute_result_panels,
    _build_query_attribute_llm_error,
    _flatten_attribute_metadata,
    _validate_query_attribute_result,
    build_attribute_metadata_from_system,
    get_example_attribute_metadata,
)

__all__ = [
    # 目录/元数据构建簇（query_attribute_catalog）
    "_extract_property_alias_terms",
    "_extract_attribute_detail_rows",
    "_extract_attribute_names",
    "_build_entity_brief",
    "_build_relation_brief",
    "_build_scope_catalog",
    "_build_attribute_catalog",
    "_build_attribute_validation_catalog",
    "_build_scope_path",
    "_entity_role_to_attribute_entity_type",
    "_build_attribute_entity_catalog_from_query_entity_metadata",
    "_build_attribute_relation_catalog_from_query_entity_metadata",
    "_build_attribute_prompt_metadata_from_query_entity_metadata",
    "_build_attribute_validation_metadata_from_query_entity_metadata",
    "_score_attribute_hit_from_catalog",
    "_recall_attribute_hits_from_validation_catalog",
    "_resolve_entity_candidates_from_attribute_hits",
    "_build_example_attribute_metadata",
    # 入口/校验/面板簇（query_attribute_pipeline）
    "get_example_attribute_metadata",
    "build_attribute_metadata_from_system",
    "_flatten_attribute_metadata",
    "_validate_query_attribute_result",
    "_build_attribute_result_panels",
    "_build_query_attribute_llm_error",
]
