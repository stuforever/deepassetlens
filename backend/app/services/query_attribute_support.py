"""
问属性 结果净化 + SQL 蓝图构建 —— 从 query_attribute_service.py 拆分（机械迁移，行为等价）

迁移内容：澄清槽位白名单常量、结果净化簇（_sanitize_*/_normalize_confidence/澄清解析）、
SQL 蓝图簇（_build_sql_blueprint/_build_sql_text/_group_relations/_quote_sql_identifier/_pick_existing_relation）。
"""

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from app.services.query_entity_service import _dedupe_keep_order, _safe_text

ALLOWED_ATTRIBUTE_CLARIFICATION_SLOT_CODES = {
    "target_l2",
    "target_l2x",
    "target_l4x",
    "attribute_scope",
    "attribute_disambiguation",
    "generic",
}


# ============== 结果净化簇（原 query_attribute_service L833-1002） ==============
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



# ============== SQL 蓝图簇（原 query_attribute_service L1055-1206） ==============
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
            # R5批⑱（清单安全）：join_expr 来自 LLM 产出的关系数据，_safe_text 只净文本
            # 不净语义——白名单格式校验（仅「`标识符` = `标识符`」可 AND 连接），
            # 不合格式拒绝该 JOIN（fail-closed，宁少不注入）。
            import re as _re

            if not _re.fullmatch(
                    r"\s*`[^`]+`(?:\.`[^`]+`)*\s*=\s*`[^`]+`(?:\.`[^`]+`)*"
                    r"(?:\s+AND\s+`[^`]+`(?:\.`[^`]+`)*\s*=\s*`[^`]+`(?:\.`[^`]+`)*)*\s*",
                    join_expr):
                continue
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

