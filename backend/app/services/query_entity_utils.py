"""
问实体 通用工具 —— 从 query_entity_service.py 拆分（机械迁移，行为等价）

迁移内容：KEY_ATTRIBUTE_HINTS/BIZ_OBJECT_PATTERNS 常量与 18 个通用工具函数
（文本规整/JSON 解析/别名提取/术语匹配等）。query_entity_service.py 通过
re-export 保持对 query_attribute_support 的 _safe_text/_dedupe_keep_order 导入兼容。
"""

import json
import re
import unicodedata
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.models.base import Entity, StandardSemanticTerm

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



# ============== 通用工具函数（原 query_entity_service L40-294） ==============
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
