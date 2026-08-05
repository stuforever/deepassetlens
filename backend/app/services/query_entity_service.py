import json
import re
import unicodedata
from collections import defaultdict
from copy import deepcopy
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.base import Concept, Entity, EntityRelation, LLMConnectionConfig, StandardSemanticTerm
from app.services.llm_client import call_openai_compatible_chat, get_active_planner_config


KEY_ATTRIBUTE_HINTS = [
    "编号",
    "编码",
    "名称",
    "证件",
    "地址",
    "类型",
    "状态",
    "流水",
    "申请",
    "记录",
    "工单",
    "单号",
]

BIZ_OBJECT_PATTERNS = [
    r"(工单号[:：]?\s*[A-Za-z0-9_-]+)",
    r"(申请单[:：]?\s*[A-Za-z0-9_-]+)",
    r"(单号[:：]?\s*[A-Za-z0-9_-]+)",
    r"(记录[:：]?\s*[A-Za-z0-9_-]+)",
    r"(这笔)",
    r"(该笔)",
]

ALLOWED_CLARIFICATION_SLOT_CODES = {"target_l2", "target_l2x", "target_l4x", "generic"}

def _safe_text(text: Any) -> str:
    return str(text or "").strip()


def normalize_text(text: Any) -> str:
    raw = unicodedata.normalize("NFKC", str(text or "")).strip().lower()
    raw = re.sub(r"\s+", "", raw)
    raw = re.sub(r"[，,。.!！？?；;：:（）()\[\]【】'\"“”‘’/\\\-]+", "", raw)
    return raw


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        value = _safe_text(item)
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _split_alias_text(text: Any) -> List[str]:
    raw = _safe_text(text)
    if not raw:
        return []
    parts = re.split(r"[,，、/|；;\n\r\t]+", raw)
    return [part.strip() for part in parts if part and part.strip()]


def _strip_markdown_code_fence(text: str) -> str:
    cleaned = _safe_text(text).replace("\ufeff", "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json|python|javascript|js)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _extract_first_balanced_json_object(text: str) -> str:
    raw = _safe_text(text)
    start = raw.find("{")
    if start < 0:
        return raw
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(raw)):
        ch = raw[index]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw[start : index + 1]
    end = raw.rfind("}")
    return raw[start : end + 1] if end >= start else raw[start:]


def _cleanup_json_candidate(text: str) -> str:
    cleaned = _safe_text(text).replace("\ufeff", "")
    cleaned = re.sub(r"^json\s*", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r",(\s*[}\]])", r"\1", cleaned)
    cleaned = re.sub(r'([}\]0-9"eEl])\s*\n(\s*")', r'\1,\n\2', cleaned)
    return cleaned.strip()


def _parse_llm_json_payload(content: Any, empty_result_factory: Optional[Callable[[], Dict[str, Any]]] = None) -> Tuple[Optional[Dict[str, Any]], str, Optional[str]]:
    raw_text = _safe_text(content)
    if not raw_text:
        return (empty_result_factory() if empty_result_factory is not None else {}), "", None

    candidates: List[str] = []

    def _push(candidate: str) -> None:
        value = _safe_text(candidate)
        if value and value not in candidates:
            candidates.append(value)

    fence_stripped = _strip_markdown_code_fence(raw_text)
    balanced = _extract_first_balanced_json_object(fence_stripped)
    _push(raw_text)
    _push(fence_stripped)
    _push(balanced)
    _push(_cleanup_json_candidate(fence_stripped))
    _push(_cleanup_json_candidate(balanced))

    last_error: Optional[json.JSONDecodeError] = None
    last_candidate = candidates[-1] if candidates else raw_text
    for candidate in candidates:
        last_candidate = candidate
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed, candidate, None
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
    reason = f"llm_parse_failed:{last_error}" if last_error is not None else "llm_parse_failed:invalid_json_payload"
    return None, last_candidate, reason


def _extract_semantic_alias_terms(term_row: StandardSemanticTerm) -> List[str]:
    term_type = _safe_text(term_row.term_type).lower()
    if term_type not in {"alias", "synonym", "entity_alias", "entity_synonym", "nickname"}:
        return []
    alias_terms: List[str] = []
    alias_terms.extend(_split_alias_text(term_row.term))
    alias_terms.extend(_split_alias_text(term_row.canonical_text))
    payload = term_row.text_payload or {}
    if isinstance(payload, dict):
        for key in ["aliases", "synonyms", "variants"]:
            value = payload.get(key)
            if isinstance(value, list):
                for item in value:
                    alias_terms.extend(_split_alias_text(item))
            else:
                alias_terms.extend(_split_alias_text(value))
    cleaned: List[str] = []
    for alias in _dedupe_keep_order(alias_terms):
        if len(alias) > 40:
            continue
        if "的" in alias or "：" in alias or ":" in alias:
            continue
        cleaned.append(alias)
    return cleaned


def _extract_entity_explanation_alias_terms(entity: Entity) -> List[str]:
    alias_terms: List[str] = []
    alias_terms.extend(_split_alias_text(getattr(entity, "entity_explanation", None)))
    cleaned: List[str] = []
    for alias in _dedupe_keep_order(alias_terms):
        if len(alias) > 40:
            continue
        if "的" in alias or "：" in alias or ":" in alias:
            continue
        cleaned.append(alias)
    return cleaned


def _prop_cn_name(prop: Dict[str, Any]) -> str:
    return _safe_text(
        prop.get("cnName")
        or prop.get("label")
        or prop.get("display_name")
        or prop.get("name_zh")
        or prop.get("attribute_name")
    )


def _prop_en_name(prop: Dict[str, Any]) -> str:
    return _safe_text(prop.get("name") or prop.get("field_name") or prop.get("attribute_en_name") or prop.get("attr_code"))


def _extract_key_attributes(entity: Entity) -> List[str]:
    props = entity.properties_schema if isinstance(entity.properties_schema, list) else []
    explicit: List[str] = []
    safe: List[str] = []
    for prop in props:
        if not isinstance(prop, dict):
            continue
        label = _prop_cn_name(prop) or _prop_en_name(prop)
        if not label:
            continue
        if any(
            bool(prop.get(flag))
            for flag in [
                "enable_query_entity",
                "is_alias_key",
                "is_key_attribute",
                "key_attribute",
                "keyword",
                "is_primary_key",
                "isPrimaryKey",
            ]
        ):
            explicit.append(label)
            continue
        if any(hint in label for hint in KEY_ATTRIBUTE_HINTS):
            safe.append(label)
    return _dedupe_keep_order(explicit + safe)[:5]


def _entity_basic_payload(entity: Entity, aliases: List[str]) -> Dict[str, Any]:
    return {
        "id": str(entity.id),
        "name": _safe_text(entity.entity_name),
        "entity_code": _safe_text(entity.entity_code),
        "entity_en_name": _safe_text(entity.entity_en_name),
        "aliases": aliases,
        "is_main_table": bool(entity.is_main_table),
    }


def _match_terms(query_norm: str, terms: List[str]) -> List[str]:
    matched: List[str] = []
    for term in terms:
        term_norm = normalize_text(term)
        if term_norm and term_norm in query_norm:
            matched.append(term)
    return _dedupe_keep_order(matched)


def _match_term_specs(query_norm: str, term_specs: List[Tuple[str, str]]) -> List[Dict[str, str]]:
    matched: List[Dict[str, str]] = []
    seen = set()
    for source_type, term in term_specs:
        value = _safe_text(term)
        term_norm = normalize_text(value)
        key = (source_type, value)
        if not term_norm or key in seen:
            continue
        if term_norm in query_norm:
            seen.add(key)
            matched.append(
                {
                    "source_type": source_type,
                    "matched_text": value,
                    "normalized_text": term_norm,
                }
            )
    return matched


def _drop_generic_terms(term_specs: List[Tuple[str, str]], generic_terms: List[str]) -> List[Tuple[str, str]]:
    generic_norms = {normalize_text(term) for term in generic_terms if normalize_text(term)}
    filtered: List[Tuple[str, str]] = []
    for source_type, term in term_specs:
        term_norm = normalize_text(term)
        if term_norm and term_norm in generic_norms:
            continue
        filtered.append((source_type, term))
    return filtered


def _extract_biz_object_hints(user_query: str) -> List[str]:
    hints: List[str] = []
    for pattern in BIZ_OBJECT_PATTERNS:
        for item in re.findall(pattern, _safe_text(user_query), flags=re.IGNORECASE):
            if isinstance(item, tuple):
                hints.extend([_safe_text(x) for x in item if _safe_text(x)])
            else:
                hints.append(_safe_text(item))
    return _dedupe_keep_order(hints)


def build_query_entity_metadata_diagnostics_from_system(db: Session) -> Dict[str, Any]:
    concepts = db.query(Concept).all()
    entities = db.query(Entity).all()
    relations = db.query(EntityRelation).order_by(EntityRelation.created_at.desc()).all()
    semantic_terms = (
        db.query(StandardSemanticTerm)
        .filter(StandardSemanticTerm.enabled == True)  # noqa: E712
        .filter(StandardSemanticTerm.ontology_ref_type == "entity")
        .all()
    )

    concept_map: Dict[str, Concept] = {str(c.id): c for c in concepts}
    entity_map: Dict[str, Entity] = {str(e.id): e for e in entities}
    entity_alias_map: Dict[str, List[str]] = defaultdict(list)

    for term in semantic_terms:
        ref_id = _safe_text(term.ontology_ref_id)
        if ref_id and ref_id in entity_map:
            entity_alias_map[ref_id].extend(_extract_semantic_alias_terms(term))

    domain_catalog: List[Dict[str, Any]] = []
    domain_by_concept_id: Dict[str, Dict[str, Any]] = {}
    l2_entities_by_id: Dict[str, Dict[str, Any]] = {}
    l4_entities_by_id: Dict[str, Dict[str, Any]] = {}
    entity_role_map: Dict[str, Dict[str, Any]] = {}

    level2_concepts = [c for c in concepts if c.level == 2]
    for concept in sorted(level2_concepts, key=lambda x: (int(x.sort_order or 0), _safe_text(x.name))):
        parent = concept_map.get(str(concept.parent_id)) if concept.parent_id else None
        domain = {
            "domain_id": str(concept.id),
            "l1": _safe_text(parent.name if parent else ""),
            "l2": _safe_text(concept.name),
            "primary_entity": None,
            "secondary_entities": [],
            "related_activity_entities": [],
        }
        domain_catalog.append(domain)
        domain_by_concept_id[str(concept.id)] = domain

    for entity in sorted(entities, key=lambda x: (0 if x.is_main_table else 1, int(x.sort_order or 0), _safe_text(x.entity_name))):
        concept = concept_map.get(str(entity.concept_id))
        if not concept:
            continue
        aliases = _dedupe_keep_order(
            _extract_entity_explanation_alias_terms(entity) + entity_alias_map.get(str(entity.id), [])
        )
        basic = _entity_basic_payload(entity, aliases=aliases)
        if concept.level == 2:
            domain = domain_by_concept_id.get(str(concept.id))
            if not domain:
                continue
            parent = concept_map.get(str(concept.parent_id)) if concept.parent_id else None
            basic["l1"] = _safe_text(parent.name if parent else "")
            basic["l2"] = _safe_text(concept.name)
            if entity.is_main_table and domain.get("primary_entity") is None:
                domain["primary_entity"] = basic
                entity_role_map[str(entity.id)] = {
                    "role": "primary_entity",
                    "l1": basic["l1"],
                    "l2": basic["l2"],
                    "entity_name": basic["name"],
                }
            else:
                domain["secondary_entities"].append(basic)
                entity_role_map[str(entity.id)] = {
                    "role": "secondary_entity",
                    "l1": basic["l1"],
                    "l2": basic["l2"],
                    "entity_name": basic["name"],
                }
            l2_entities_by_id[str(entity.id)] = basic
        elif concept.level == 4:
            parent = concept_map.get(str(concept.parent_id)) if concept.parent_id else None
            basic["l3"] = _safe_text(parent.name if parent else "")
            basic["l4"] = _safe_text(concept.name)
            l4_entities_by_id[str(entity.id)] = basic
            entity_role_map[str(entity.id)] = {
                "role": "l4x",
                "l3": basic["l3"],
                "l4": basic["l4"],
                "entity_name": basic["name"],
            }

    relation_catalog: List[Dict[str, Any]] = []
    binding_map: Dict[str, str] = {}
    binding_conflicts: List[Dict[str, Any]] = []
    related_activity_by_primary: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    unbound_l4x_ids = set(l4_entities_by_id.keys())

    def _add_binding(l4x_id: str, primary_id: str, rel: EntityRelation):
        if l4x_id in binding_map and binding_map[l4x_id] != primary_id:
            binding_conflicts.append(
                {
                    "l4x_id": l4x_id,
                    "l4x_name": _safe_text((l4_entities_by_id.get(l4x_id) or {}).get("name")),
                    "existing_l2x_id": binding_map[l4x_id],
                    "existing_l2x_name": _safe_text((l2_entities_by_id.get(binding_map[l4x_id]) or {}).get("name")),
                    "conflict_l2x_id": primary_id,
                    "conflict_l2x_name": _safe_text((l2_entities_by_id.get(primary_id) or {}).get("name")),
                    "relation_id": str(rel.id),
                }
            )
            return
        binding_map[l4x_id] = primary_id
        unbound_l4x_ids.discard(l4x_id)

    for rel in relations:
        source_id = _safe_text(rel.source_entity_id)
        target_id = _safe_text(rel.target_entity_id)
        source_role = entity_role_map.get(source_id, {})
        target_role = entity_role_map.get(target_id, {})
        relation_row = {
            "id": str(rel.id),
            "source_entity_id": source_id,
            "source_entity_name": _safe_text(source_role.get("entity_name") or (entity_map.get(source_id).entity_name if entity_map.get(source_id) else "")),
            "source_entity_role": _safe_text(source_role.get("role")),
            "source_l1": _safe_text(source_role.get("l1")),
            "source_l2": _safe_text(source_role.get("l2")),
            "source_l3": _safe_text(source_role.get("l3")),
            "source_l4": _safe_text(source_role.get("l4")),
            "target_entity_id": target_id,
            "target_entity_name": _safe_text(target_role.get("entity_name") or (entity_map.get(target_id).entity_name if entity_map.get(target_id) else "")),
            "target_entity_role": _safe_text(target_role.get("role")),
            "target_l1": _safe_text(target_role.get("l1")),
            "target_l2": _safe_text(target_role.get("l2")),
            "target_l3": _safe_text(target_role.get("l3")),
            "target_l4": _safe_text(target_role.get("l4")),
            "relation_name": _safe_text(rel.relation_name),
            "relation_category": _safe_text(rel.relation_category),
            "direction": _safe_text(rel.direction),
            "cardinality": _safe_text(rel.cardinality),
            "source_field_name": _safe_text(rel.source_field_name),
            "target_field_name": _safe_text(rel.target_field_name),
            "join_expr": _safe_text(rel.join_expr),
            "description": _safe_text(rel.description),
            "remark": _safe_text(rel.remark),
        }
        relation_catalog.append(relation_row)

        if source_role.get("role") == "primary_entity" and target_role.get("role") == "l4x":
            _add_binding(target_id, source_id, rel)
        elif source_role.get("role") == "l4x" and target_role.get("role") == "primary_entity":
            _add_binding(source_id, target_id, rel)

    for l4x_id, primary_id in binding_map.items():
        l4x_row = deepcopy(l4_entities_by_id.get(l4x_id) or {})
        if not l4x_row:
            continue
        l4x_row["binding_primary_entity_id"] = primary_id
        related_activity_by_primary[primary_id].append(
            {
                "id": l4x_row.get("id"),
                "l3": l4x_row.get("l3"),
                "l4": l4x_row.get("l4"),
                "name": l4x_row.get("name"),
                "aliases": l4x_row.get("aliases") or [],
                "binding_primary_entity_id": primary_id,
            }
        )

    for domain in domain_catalog:
        primary = domain.get("primary_entity") or {}
        primary_id = _safe_text(primary.get("id"))
        domain["related_activity_entities"] = sorted(
            related_activity_by_primary.get(primary_id, []),
            key=lambda x: (normalize_text(x.get("l3")), normalize_text(x.get("l4")), normalize_text(x.get("name"))),
        )

    unbound_activity_entities = [
        {
            "id": l4x_id,
            "l3": _safe_text((l4_entities_by_id.get(l4x_id) or {}).get("l3")),
            "l4": _safe_text((l4_entities_by_id.get(l4x_id) or {}).get("l4")),
            "name": _safe_text((l4_entities_by_id.get(l4x_id) or {}).get("name")),
        }
        for l4x_id in sorted(unbound_l4x_ids)
    ]

    return {
        "source": "system",
        "binding_conflicts": binding_conflicts,
        "unbound_activity_entities": unbound_activity_entities,
        "_meta": {
            "source": "system",
            "binding_conflict_count": len(binding_conflicts),
            "unbound_activity_entity_count": len(unbound_activity_entities),
        },
    }


def build_metadata_from_system(db: Session) -> Dict[str, Any]:
    concepts = db.query(Concept).all()
    entities = db.query(Entity).all()
    relations = db.query(EntityRelation).order_by(EntityRelation.created_at.desc()).all()
    semantic_terms = (
        db.query(StandardSemanticTerm)
        .filter(StandardSemanticTerm.enabled == True)  # noqa: E712
        .filter(StandardSemanticTerm.ontology_ref_type == "entity")
        .all()
    )

    concept_map: Dict[str, Concept] = {str(c.id): c for c in concepts}
    entity_map: Dict[str, Entity] = {str(e.id): e for e in entities}
    entity_alias_map: Dict[str, List[str]] = defaultdict(list)

    for term in semantic_terms:
        ref_id = _safe_text(term.ontology_ref_id)
        if ref_id and ref_id in entity_map:
            entity_alias_map[ref_id].extend(_extract_semantic_alias_terms(term))

    domain_catalog: List[Dict[str, Any]] = []
    domain_by_concept_id: Dict[str, Dict[str, Any]] = {}
    entity_context_by_id: Dict[str, Dict[str, Any]] = {}
    activity_entity_by_id: Dict[str, Dict[str, Any]] = {}

    level2_concepts = [c for c in concepts if c.level == 2]
    for concept in sorted(level2_concepts, key=lambda x: (int(x.sort_order or 0), _safe_text(x.name))):
        parent = concept_map.get(str(concept.parent_id)) if concept.parent_id else None
        domain = {
            "domain_id": str(concept.id),
            "l1": _safe_text(parent.name if parent else ""),
            "l2": _safe_text(concept.name),
            "primary_entity": None,
            "secondary_entities": [],
            "related_activity_entities": [],
        }
        domain_catalog.append(domain)
        domain_by_concept_id[str(concept.id)] = domain

    for entity in sorted(entities, key=lambda x: (0 if x.is_main_table else 1, int(x.sort_order or 0), _safe_text(x.entity_name))):
        concept = concept_map.get(str(entity.concept_id))
        if not concept:
            continue
        aliases = _dedupe_keep_order(
            _extract_entity_explanation_alias_terms(entity) + entity_alias_map.get(str(entity.id), [])
        )
        basic = _entity_basic_payload(entity, aliases=aliases)
        if concept.level == 2:
            domain = domain_by_concept_id.get(str(concept.id))
            if not domain:
                continue
            parent = concept_map.get(str(concept.parent_id)) if concept.parent_id else None
            basic["l1"] = _safe_text(parent.name if parent else "")
            basic["l2"] = _safe_text(concept.name)
            basic["entity_type"] = "master"
            if entity.is_main_table and domain.get("primary_entity") is None:
                domain["primary_entity"] = basic
            else:
                domain["secondary_entities"].append(basic)
            entity_context_by_id[str(entity.id)] = basic
        elif concept.level == 4:
            parent = concept_map.get(str(concept.parent_id)) if concept.parent_id else None
            basic["l3"] = _safe_text(parent.name if parent else "")
            basic["l4"] = _safe_text(concept.name)
            basic["entity_type"] = "activity"
            activity_entity_by_id[str(entity.id)] = basic

    binding_map: Dict[str, str] = {}
    for rel in relations:
        source_id = _safe_text(rel.source_entity_id)
        target_id = _safe_text(rel.target_entity_id)
        source = entity_context_by_id.get(source_id)
        target = activity_entity_by_id.get(target_id)
        if source and target and bool(source.get("is_main_table")):
            binding_map[target_id] = source_id
            continue
        source_activity = activity_entity_by_id.get(source_id)
        target_master = entity_context_by_id.get(target_id)
        if source_activity and target_master and bool(target_master.get("is_main_table")):
            binding_map[source_id] = target_id

    for activity_id, primary_id in binding_map.items():
        activity = activity_entity_by_id.get(activity_id)
        primary = entity_context_by_id.get(primary_id)
        if not activity or not primary:
            continue
        domain = domain_by_concept_id.get(
            next(
                (
                    concept_id
                    for concept_id, item in domain_by_concept_id.items()
                    if _safe_text((item.get("primary_entity") or {}).get("id")) == primary_id
                    or any(_safe_text(row.get("id")) == primary_id for row in item.get("secondary_entities") or [])
                ),
                "",
            )
        )
        if not domain:
            continue
        domain["related_activity_entities"].append(
            {
                "id": activity.get("id"),
                "l3": activity.get("l3"),
                "l4": activity.get("l4"),
                "name": activity.get("name"),
                "aliases": activity.get("aliases") or [],
                "binding_primary_entity_id": primary_id,
            }
        )

    for domain in domain_catalog:
        domain["secondary_entities"] = sorted(
            domain.get("secondary_entities") or [],
            key=lambda x: normalize_text(x.get("name")),
        )
        domain["related_activity_entities"] = sorted(
            domain.get("related_activity_entities") or [],
            key=lambda x: (normalize_text(x.get("l3")), normalize_text(x.get("l4")), normalize_text(x.get("name"))),
        )

    relation_catalog: List[Dict[str, Any]] = []
    for rel in relations:
        source_id = _safe_text(rel.source_entity_id)
        target_id = _safe_text(rel.target_entity_id)
        source_master = entity_context_by_id.get(source_id)
        source_activity = activity_entity_by_id.get(source_id)
        target_master = entity_context_by_id.get(target_id)
        target_activity = activity_entity_by_id.get(target_id)
        source_row = source_master or source_activity or {}
        target_row = target_master or target_activity or {}
        relation_catalog.append(
            {
                "id": str(rel.id),
                "source_entity_id": source_id,
                "source_entity_name": _safe_text(source_row.get("name") or (entity_map.get(source_id).entity_name if entity_map.get(source_id) else "")),
                "source_entity_type": _safe_text(source_row.get("entity_type")) or ("master" if source_master else "activity" if source_activity else None),
                "source_l1": _safe_text(source_row.get("l1")),
                "source_l2": _safe_text(source_row.get("l2")),
                "source_l3": _safe_text(source_row.get("l3")),
                "source_l4": _safe_text(source_row.get("l4")),
                "target_entity_id": target_id,
                "target_entity_name": _safe_text(target_row.get("name") or (entity_map.get(target_id).entity_name if entity_map.get(target_id) else "")),
                "target_entity_type": _safe_text(target_row.get("entity_type")) or ("master" if target_master else "activity" if target_activity else None),
                "target_l1": _safe_text(target_row.get("l1")),
                "target_l2": _safe_text(target_row.get("l2")),
                "target_l3": _safe_text(target_row.get("l3")),
                "target_l4": _safe_text(target_row.get("l4")),
                "relation_name": _safe_text(rel.relation_name),
                "direction": _safe_text(rel.direction),
                "cardinality": _safe_text(rel.cardinality),
                "source_field_name": _safe_text(rel.source_field_name),
                "target_field_name": _safe_text(rel.target_field_name),
                "join_expr": _safe_text(rel.join_expr),
            }
        )

    primary_entity_count = sum(1 for domain in domain_catalog if domain.get("primary_entity"))
    secondary_entity_count = sum(len(domain.get("secondary_entities") or []) for domain in domain_catalog)
    activity_entity_count = sum(len(domain.get("related_activity_entities") or []) for domain in domain_catalog)

    return {
        "source": "system",
        "domain_catalog": domain_catalog,
        "relation_catalog": relation_catalog,
        "_meta": {
            "source": "system",
            "domain_count": len(domain_catalog),
            "primary_entity_count": primary_entity_count,
            "secondary_entity_count": secondary_entity_count,
            "activity_entity_count": activity_entity_count,
            "relation_count": len(relation_catalog),
        },
    }


def _flatten_query_entity_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    l2x_by_name: Dict[str, Dict[str, Any]] = {}
    l2x_by_id: Dict[str, Dict[str, Any]] = {}
    l4x_by_name: Dict[str, Dict[str, Any]] = {}
    l4x_by_id: Dict[str, Dict[str, Any]] = {}
    l4x_binding_by_name: Dict[str, Dict[str, Any]] = {}
    l2_label_to_primary: Dict[str, Dict[str, Any]] = {}
    for domain in metadata.get("domain_catalog") or []:
        primary = deepcopy(domain.get("primary_entity") or {})
        if primary:
            primary["l1"] = _safe_text(domain.get("l1"))
            primary["l2"] = _safe_text(domain.get("l2"))
            primary["entity_role"] = "primary_entity"
            l2x_by_name[_safe_text(primary.get("name"))] = primary
            l2x_by_id[_safe_text(primary.get("id"))] = primary
            l2_label_to_primary[_safe_text(domain.get("l2"))] = primary
        for secondary in domain.get("secondary_entities") or []:
            row = deepcopy(secondary)
            row["l1"] = _safe_text(domain.get("l1"))
            row["l2"] = _safe_text(domain.get("l2"))
            row["entity_role"] = "secondary_entity"
            l2x_by_name[_safe_text(row.get("name"))] = row
            l2x_by_id[_safe_text(row.get("id"))] = row
        for activity in domain.get("related_activity_entities") or []:
            row = deepcopy(activity)
            row["l1"] = _safe_text(domain.get("l1"))
            row["l2"] = _safe_text(domain.get("l2"))
            row["l4x"] = _safe_text(row.get("name"))
            l4x_by_name[_safe_text(row.get("name"))] = row
            l4x_by_id[_safe_text(row.get("id"))] = row
            l4x_binding_by_name[_safe_text(row.get("name"))] = {
                "l1": _safe_text(domain.get("l1")),
                "l2": _safe_text(domain.get("l2")),
                "l2x": _safe_text(primary.get("name")),
                "l2x_id": _safe_text(primary.get("id")),
                "l3": _safe_text(row.get("l3")),
                "l4": _safe_text(row.get("l4")),
                "l4x": _safe_text(row.get("name")),
            }
    return {
        "l2x_by_name": l2x_by_name,
        "l2x_by_id": l2x_by_id,
        "l4x_by_name": l4x_by_name,
        "l4x_by_id": l4x_by_id,
        "l4x_binding_by_name": l4x_binding_by_name,
        "l2_label_to_primary": l2_label_to_primary,
    }


def get_query_llm_connection(db: Optional[Session], llm_connection_id: Optional[str]) -> Optional[LLMConnectionConfig]:
    if db is None:
        return None
    all_conns = db.query(LLMConnectionConfig).all()
    if llm_connection_id:
        return next((x for x in all_conns if str(x.id) == str(llm_connection_id) and x.enabled), None)
    planner = get_active_planner_config(db)
    if planner and planner.enabled and planner.llm_connection_id:
        return next((x for x in all_conns if str(x.id) == str(planner.llm_connection_id) and x.enabled), None)
    return None


def _make_empty_result(reason: str) -> Dict[str, Any]:
    return {
        "l1": None,
        "l2": None,
        "l2x": None,
        "l3": None,
        "l4": None,
        "l4x": None,
        "biz_object": None,
        "master_entity_names": [],
        "activity_entity_names": [],
        "confidence": "LOW",
        "reason": reason,
    }


def _invoke_query_llm(
    db: Optional[Session],
    user_query: str,
    metadata: Optional[Dict[str, Any]] = None,
    system_prompt: Optional[str] = None,
    user_prompt: Optional[str] = None,
    llm_connection: Optional[LLMConnectionConfig] = None,
    llm_runner: Optional[Callable[..., Any]] = None,
) -> Dict[str, Any]:
    metadata = metadata or {}
    system_prompt = _safe_text(system_prompt) or None
    user_prompt = _safe_text(user_prompt) or None

    if llm_runner is not None:
        raw = llm_runner(
            user_query=user_query,
            metadata=metadata,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        content = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
        if isinstance(raw, dict):
            parsed = raw
        else:
            parsed, content, parse_reason = _parse_llm_json_payload(raw)
            if parse_reason:
                return {
                    "used": False,
                    "runner_type": "custom_runner",
                    "reason": parse_reason,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "raw": raw,
                    "content": content,
                    "parsed": None,
                }
        return {
            "used": True,
            "runner_type": "custom_runner",
            "reason": "ok",
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "raw": raw,
            "content": content,
            "parsed": parsed,
        }

    conn = llm_connection
    if conn:
        try:
            raw = call_openai_compatible_chat(conn, system_prompt, user_prompt)
            content = (
                (((raw or {}).get("choices") or [{}])[0].get("message") or {}).get("content")
                or ""
            ).strip()
            parsed, content, parse_reason = _parse_llm_json_payload(
                content,
                empty_result_factory=lambda: _make_empty_result("大模型未返回有效JSON"),
            )
            if parse_reason:
                return {
                    "used": False,
                    "runner_type": "llm_connection",
                    "reason": parse_reason,
                    "connection_name": conn.name,
                    "model_name": conn.model_name,
                    "system_prompt": system_prompt,
                    "user_prompt": user_prompt,
                    "raw": raw,
                    "content": content,
                    "parsed": None,
                }
            return {
                "used": True,
                "runner_type": "llm_connection",
                "reason": "ok",
                "connection_name": conn.name,
                "model_name": conn.model_name,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "raw": raw,
                "content": content,
                "parsed": parsed,
            }
        except Exception as exc:
            return {
                "used": False,
                "runner_type": "llm_connection",
                "reason": f"llm_call_failed:{exc}",
                "connection_name": conn.name,
                "model_name": conn.model_name,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "raw": None,
                "content": "",
                "parsed": None,
            }

    return {
        "used": False,
        "runner_type": "llm_connection",
        "reason": "llm_connection_not_found",
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "raw": None,
        "content": "",
        "parsed": None,
    }


def _sanitize_result(data: Any) -> Dict[str, Any]:
    base = _make_empty_result("未匹配到任何业务实体")
    if not isinstance(data, dict):
        return base
    result = deepcopy(base)
    for key in ["l1", "l2", "l2x", "l3", "l4", "l4x", "biz_object", "confidence", "reason"]:
        value = data.get(key)
        if key in {"confidence", "reason"}:
            result[key] = _safe_text(value) or result[key]
        else:
            text = _safe_text(value)
            result[key] = text if text else None
    result["master_entity_names"] = _dedupe_keep_order(
        [_safe_text(item) for item in (data.get("master_entity_names") or []) if _safe_text(item)]
    )
    result["activity_entity_names"] = _dedupe_keep_order(
        [_safe_text(item) for item in (data.get("activity_entity_names") or []) if _safe_text(item)]
    )
    if result["confidence"] not in {"HIGH", "MEDIUM", "LOW"}:
        result["confidence"] = "LOW"
    return result


def _extract_llm_clarification(data: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(data, dict):
        return None
    decision = _safe_text(data.get("decision")).lower()
    if decision != "clarify":
        return None
    question = _safe_text(data.get("clarification_question"))
    if not question:
        return None
    slot_code = _safe_text(data.get("clarification_slot_code")) or "generic"
    if slot_code not in ALLOWED_CLARIFICATION_SLOT_CODES:
        slot_code = "generic"
    raw_options = data.get("clarification_options") or []
    options: List[Dict[str, Any]] = []
    seen = set()
    for item in raw_options if isinstance(raw_options, list) else []:
        if isinstance(item, dict):
            label = _safe_text(item.get("label") or item.get("value"))
            value = _safe_text(item.get("value") or item.get("label"))
            description = _safe_text(item.get("description"))
        else:
            label = _safe_text(item)
            value = label
            description = ""
        key = (label, value)
        if not label or not value or key in seen:
            continue
        seen.add(key)
        options.append(
            {
                "label": label,
                "value": value,
                "description": description,
            }
        )
    manual_allowed = data.get("clarification_manual_allowed")
    multi_select = bool(data.get("clarification_multi_select"))
    if len(options) < 2:
        multi_select = False
    return {
        "slot_code": slot_code,
        "question": question,
        "hint": _safe_text(data.get("clarification_hint")) or None,
        "options": options[:5],
        "multi_select": multi_select,
        "manual_allowed": True if manual_allowed is None else bool(manual_allowed),
        "reason": _safe_text(data.get("reason")) or "当前信息不足，需要继续澄清。",
        "confidence": _safe_text(data.get("confidence")) or "LOW",
    }


def _validate_result(parsed_result: Dict[str, Any], metadata: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    steps: List[Dict[str, Any]] = []
    result = _sanitize_result(parsed_result)
    flatten = _flatten_query_entity_metadata(metadata)
    steps.append({"check": "json_fields", "ok": True, "result_snapshot": deepcopy(result)})

    if not any(result.get(key) for key in ["l1", "l2", "l2x", "l3", "l4", "l4x", "biz_object"]):
        result["confidence"] = "LOW"
        if not _safe_text(result.get("reason")):
            result["reason"] = "未匹配到任何业务实体"
        steps.append({"check": "empty_result", "ok": True, "reason": result["reason"]})
        return result, steps

    if result.get("l4x"):
        binding = flatten["l4x_binding_by_name"].get(_safe_text(result["l4x"]))
        if not binding:
            error_result = _make_empty_result("业务活动实体未配置唯一主数据归属，请先完善关系")
            steps.append({"check": "l4x_binding", "ok": False, "reason": error_result["reason"]})
            return error_result, steps
        if not result.get("l2x"):
            result["l1"] = binding["l1"]
            result["l2"] = binding["l2"]
            result["l2x"] = binding["l2x"]
            steps.append({"check": "backfill_l2x", "ok": True, "bound_primary_entity": binding["l2x"]})
        elif _safe_text(result["l2x"]) != _safe_text(binding["l2x"]):
            error_result = {
                "l1": result.get("l1") or binding["l1"],
                "l2": result.get("l2") or binding["l2"],
                "l2x": result.get("l2x"),
                "l3": None,
                "l4": None,
                "l4x": None,
                "biz_object": result.get("biz_object"),
                "confidence": "LOW",
                "reason": "主数据对象上未发生该业务，请建立关系后再问",
            }
            steps.append(
                {
                    "check": "l2x_l4x_relation",
                    "ok": False,
                    "expected_primary_entity": binding["l2x"],
                    "returned_l2x": result.get("l2x"),
                }
            )
            return error_result, steps
        result["l1"] = binding["l1"]
        result["l2"] = binding["l2"]
        result["l2x"] = binding["l2x"]
        result["l3"] = binding["l3"]
        result["l4"] = binding["l4"]
        steps.append({"check": "l4x_binding", "ok": True, "bound_primary_entity": binding["l2x"]})
        return result, steps

    if result.get("l2") and not result.get("l2x"):
        primary = flatten["l2_label_to_primary"].get(_safe_text(result["l2"]))
        if primary:
            result["l1"] = result.get("l1") or primary.get("l1")
            result["l2x"] = primary.get("name")
            steps.append({"check": "default_primary_entity", "ok": True, "l2x": primary.get("name")})

    if result.get("l2x"):
        l2x_row = flatten["l2x_by_name"].get(_safe_text(result["l2x"]))
        if l2x_row:
            result["l1"] = result.get("l1") or l2x_row.get("l1")
            result["l2"] = result.get("l2") or l2x_row.get("l2")
            steps.append({"check": "l2x_lookup", "ok": True, "entity_role": l2x_row.get("entity_role")})
        else:
            steps.append({"check": "l2x_lookup", "ok": False, "returned_l2x": result.get("l2x")})

    result["l3"] = None
    result["l4"] = None
    result["l4x"] = None
    return result, steps


def _infer_match_confidence(matched_sources: List[Dict[str, Any]]) -> str:
    source_types = {_safe_text(item.get("source_type")) for item in matched_sources or []}
    if source_types & {"实体名", "业务活动实体名"}:
        return "HIGH"
    if source_types & {"别名", "业务活动别名"}:
        return "MEDIUM"
    if len(source_types) >= 2:
        return "MEDIUM"
    return "LOW"


def _format_match_reason(matched_sources: List[Dict[str, Any]]) -> str:
    if not matched_sources:
        return "-"
    return "、".join(
        [
            f'{_safe_text(item.get("source_type"))}:{_safe_text(item.get("matched_text"))}'
            for item in matched_sources
            if _safe_text(item.get("matched_text"))
        ]
    ) or "-"


def _append_unique_rows(rows: List[Dict[str, Any]], incoming: Dict[str, Any], key: str = "id"):
    incoming_key = _safe_text(incoming.get(key))
    if incoming_key and any(_safe_text(row.get(key)) == incoming_key for row in rows):
        return
    if not incoming_key:
        name_key = _safe_text(incoming.get("l2x") or incoming.get("l4x"))
        if name_key and any(_safe_text(row.get("l2x") or row.get("l4x")) == name_key for row in rows):
            return
    rows.append(incoming)


def _build_result_panels(final_result: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    flatten = _flatten_query_entity_metadata(metadata)
    master_rows: List[Dict[str, Any]] = []
    activity_rows: List[Dict[str, Any]] = []
    llm_master_entities = final_result.get("master_entity_names") or []
    llm_activity_entities = final_result.get("activity_entity_names") or []

    def add_primary_for_domain(l2_value: str, reason: str, confidence: str = "MEDIUM"):
        primary = flatten["l2_label_to_primary"].get(_safe_text(l2_value)) or {}
        if not primary:
            return
        _append_unique_rows(
            master_rows,
            {
                "id": _safe_text(primary.get("id")),
                "l1": _safe_text(primary.get("l1")),
                "l2": _safe_text(primary.get("l2")),
                "l2x": _safe_text(primary.get("name")),
                "is_main_table": bool(primary.get("is_main_table")),
                "confidence": confidence,
                "match_reason": reason,
            },
        )

    for entity_name in llm_master_entities:
        l2x_row = flatten["l2x_by_name"].get(_safe_text(entity_name)) or {}
        if not l2x_row:
            continue
        _append_unique_rows(
            master_rows,
            {
                "id": _safe_text(l2x_row.get("id")),
                "l1": _safe_text(l2x_row.get("l1")),
                "l2": _safe_text(l2x_row.get("l2")),
                "l2x": _safe_text(l2x_row.get("name")),
                "is_main_table": bool(l2x_row.get("is_main_table")),
                "confidence": _safe_text(final_result.get("confidence")) or "MEDIUM",
                "match_reason": f'大模型枚举：{_safe_text(final_result.get("reason")) or _safe_text(entity_name)}',
            },
        )
        if not bool(l2x_row.get("is_main_table")):
            add_primary_for_domain(
                _safe_text(l2x_row.get("l2")),
                f'主数据主表补全：大模型枚举实体“{_safe_text(l2x_row.get("name"))}”属于 {_safe_text(l2x_row.get("l2"))}',
                confidence=_safe_text(final_result.get("confidence")) or "MEDIUM",
            )

    for entity_name in llm_activity_entities:
        l4x_row = flatten["l4x_by_name"].get(_safe_text(entity_name)) or {}
        if not l4x_row:
            continue
        _append_unique_rows(
            activity_rows,
            {
                "id": _safe_text(l4x_row.get("id")),
                "l3": _safe_text(l4x_row.get("l3")),
                "l4": _safe_text(l4x_row.get("l4")),
                "l4x": _safe_text(l4x_row.get("l4x")),
                "confidence": _safe_text(final_result.get("confidence")) or "MEDIUM",
                "match_reason": f'大模型枚举：{_safe_text(final_result.get("reason")) or _safe_text(entity_name)}',
            },
        )

    if final_result.get("l2x"):
        l2x_row = flatten["l2x_by_name"].get(_safe_text(final_result.get("l2x"))) or {}
        _append_unique_rows(
            master_rows,
            {
                "id": _safe_text(l2x_row.get("id")),
                "l1": _safe_text(final_result.get("l1") or l2x_row.get("l1")),
                "l2": _safe_text(final_result.get("l2") or l2x_row.get("l2")),
                "l2x": _safe_text(final_result.get("l2x")),
                "is_main_table": bool(l2x_row.get("is_main_table")),
                "confidence": _safe_text(final_result.get("confidence")) or "LOW",
                "match_reason": _safe_text(final_result.get("reason")) or "-",
            },
        )
        if not final_result.get("l4x") and not bool(l2x_row.get("is_main_table")):
            add_primary_for_domain(
                _safe_text(final_result.get("l2") or l2x_row.get("l2")),
                f'主数据主表补全：最终判定实体“{_safe_text(final_result.get("l2x"))}”属于 {_safe_text(final_result.get("l2") or l2x_row.get("l2"))}',
                confidence=_safe_text(final_result.get("confidence")) or "MEDIUM",
            )

    if not master_rows and final_result.get("l2") and not final_result.get("l4x"):
        add_primary_for_domain(
            _safe_text(final_result.get("l2")),
            f'主数据主表补全：{_safe_text(final_result.get("reason")) or _safe_text(final_result.get("l2"))}',
            confidence=_safe_text(final_result.get("confidence")) or "MEDIUM",
        )

    if final_result.get("l4x"):
        l4x_row = flatten["l4x_by_name"].get(_safe_text(final_result.get("l4x"))) or {}
        _append_unique_rows(
            activity_rows,
            {
                "id": _safe_text(l4x_row.get("id")),
                "l3": _safe_text(final_result.get("l3") or l4x_row.get("l3")),
                "l4": _safe_text(final_result.get("l4") or l4x_row.get("l4")),
                "l4x": _safe_text(final_result.get("l4x")),
                "confidence": _safe_text(final_result.get("confidence")) or "LOW",
                "match_reason": _safe_text(final_result.get("reason")) or "-",
            },
        )

    master_rows = sorted(
        master_rows,
        key=lambda row: (
            0 if row.get("is_main_table") else 1,
            {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(_safe_text(row.get("confidence")), 3),
            normalize_text(row.get("l2x")),
        ),
    )
    activity_rows = sorted(
        activity_rows,
        key=lambda row: (
            {"HIGH": 0, "MEDIUM": 1, "LOW": 2}.get(_safe_text(row.get("confidence")), 3),
            normalize_text(row.get("l3")),
            normalize_text(row.get("l4")),
            normalize_text(row.get("l4x")),
        ),
    )

    master_ids = {_safe_text(row.get("id")) for row in master_rows if _safe_text(row.get("id"))}
    activity_ids = {_safe_text(row.get("id")) for row in activity_rows if _safe_text(row.get("id"))}
    relation_groups = {
        "master_to_master": [],
        "activity_to_activity": [],
        "master_to_activity": [],
    }
    for relation in metadata.get("relation_catalog") or []:
        source_id = _safe_text(relation.get("source_entity_id"))
        target_id = _safe_text(relation.get("target_entity_id"))
        if source_id in master_ids and target_id in master_ids:
            relation_groups["master_to_master"].append(relation)
        elif source_id in activity_ids and target_id in activity_ids:
            relation_groups["activity_to_activity"].append(relation)
        elif (source_id in master_ids and target_id in activity_ids) or (source_id in activity_ids and target_id in master_ids):
            relation_groups["master_to_activity"].append(relation)

    return {
        "summary": {
            "confidence": _safe_text(final_result.get("confidence")) or "LOW",
            "reason": _safe_text(final_result.get("reason")) or "-",
            "biz_object": _safe_text(final_result.get("biz_object")) or None,
            "l1": final_result.get("l1"),
            "l2": final_result.get("l2"),
            "l2x": final_result.get("l2x"),
            "l3": final_result.get("l3"),
            "l4": final_result.get("l4"),
            "l4x": final_result.get("l4x"),
        },
        "master_entities": master_rows,
        "activity_entities": activity_rows,
        "relation_groups": relation_groups,
        "query_scope": "master_only" if not final_result.get("l4x") else "master_activity",
    }
