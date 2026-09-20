"""
概念/实体 通用工具与解释建议 —— 从 concept.py 拆分（机械迁移，行为等价）

迁移内容：EntityExplanationSuggestRequest 模型、解释拆分/建议构建、UUID 规整、
矩阵关系名、排序、实体-概念链接同步等纯函数与常量。路由仍留在 concept.py。
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import re
import uuid

from ..models.base import (
    Concept, Entity, EntityRelation, EntityConceptLink,
    ConceptRelation, EntityModeling, EntityInitData, EntityMappingRule,
)

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
        u = uuid.UUID(s)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid {field_name} format")
    return str(u)  # 三轨M3（:172 顺手修）：返回规范形式（小写+连字符），花括号/urn/大写归一


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
    added = set()
    for cid in unique_cids:
        cid_norm = _norm_uuid_str(cid, "concept_id")
        if cid_norm:
            added.add(cid_norm)
            db.add(EntityConceptLink(entity_id=entity_id, concept_id=cid_norm))
    db.flush()
    # 三轨M3/4：清理幸存旧链接——mode 区间外未被删除、且不属于新集合的残链
    survivors = db.query(EntityConceptLink).filter(
        EntityConceptLink.entity_id == entity_id).all()
    for lk in survivors:
        cid_str = str(lk.concept_id)
        if cid_str not in added:
            db.query(EntityConceptLink).filter(EntityConceptLink.id == lk.id).delete(synchronize_session=False)
    db.flush()
