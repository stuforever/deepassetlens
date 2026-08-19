"""
Smart Skill 执行流水线 —— _invoke_skill 与默认资产从 smart_skills.py 拆分（机械迁移，行为等价）

迁移内容：Step1 默认资产常量、_invoke_skill 单体执行链、_pick_script_assistant_llm。
路由仍留在 smart_skills.py，从此模块导入这两个函数。
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import json
import time
import re
import math
from datetime import datetime

from ..models.base import (
    SmartSkill,
    Concept,
    Entity,
    EntityRelation,
    LLMConnectionConfig,
    IntentSemanticAsset,
)
from .smart_apps import generate_smart_join_candidates, CONFIDENCE_THRESHOLD
from ..services.smart_planner import get_active_planner_config, call_openai_compatible_messages
from ..services.semantic_retrieval import (
    get_or_init_retrieval_config,
    rebuild_semantic_index,
    semantic_status,
    score_entities_semantic,
    hybrid_score,
    embed_texts,
    cosine_similarity,
)
from ..services.standard_semantic_service import query_standard_semantic_matches

# ============== Step1 默认资产（从 smart_skills.py 迁移） ==============
DEFAULT_STEP1_STOP_WORDS = [
    "我想",
    "按照",
    "查询",
    "请求",
    "信息",
    "帮助",
    "有没有",
    "是否",
    "请问",
    "一下",
    "帮我",
    "看看",
    "这个",
    "那个",
    "呢",
    "吗",
    "呀",
    "啊",
    "多少",
    "数量",
    "统计",
    "总和",
    "合计",
    "最大值",
    "最小值",
    "平均值",
]

DEFAULT_STEP1_DOMAIN_PHRASES = [
    "证件类型",
    "用电户",
    "数量",
    "电费",
    "结算时间",
    "计费结算",
    "电费金额",
    "缴费状态",
    "结算周期",
    "结算记录",
]

DEFAULT_STEP1_RULE_DICT = {
    "缴费信息": {"replace_with": ["缴费状态", "电费金额"], "type": "core_fields"},
    "电费信息": {"replace_with": ["电费金额", "缴费状态"], "type": "core_fields"},
    "本月": {"replace_with": ["结算时间=当前自然月"], "type": "filter"},
    "这个月": {"replace_with": ["结算时间=当前自然月"], "type": "filter"},
    "统计": {"replace_with": ["分组统计"], "type": "operation"},
    "用电户": {"replace_with": ["用电户"], "type": "entity"},
    "用户": {"replace_with": ["用电户"], "type": "entity"},
    "户号": {"replace_with": ["用电户"], "type": "entity"},
    "电费": {"replace_with": ["计费结算"], "type": "entity"},
    "账单": {"replace_with": ["计费结算"], "type": "entity"},
    "证件类型": {"replace_with": ["证件类型"], "type": "attribute"},
    "电费金额": {"replace_with": ["电费金额"], "type": "attribute"},
    "缴费状态": {"replace_with": ["缴费状态"], "type": "attribute"},
    "结算时间": {"replace_with": ["结算时间"], "type": "attribute"},
}

DEFAULT_STEP1_SYNONYM_MAP = {
    "用电户": ["用户", "客户", "户主", "我家", "户号"],
    "计费结算": ["电费", "账单", "结算", "算完", "算好了"],
    "结算完成": ["算完", "结算完成", "结算好了", "算好了"],
    "缴费状态": ["扣没扣", "交了吗", "扣款状态", "缴费情况", "是否缴费"],
    "本月": ["这个月", "本月", "当月"],
    "上月": ["上个月", "上月", "上期"],
}

DEFAULT_STEP1_INTENT_EXAMPLES = [
    {
        "user_query": "张三这个月电费交了吗？",
        "structured_intent": {
            "entities": [{"name": "张三", "std_name": "用电户", "type": "User"}],
            "relations": ["产生"],
            "attributes": ["缴费状态", "电费金额"],
            "filters": {"结算周期": "本月"},
            "constraints": [],
        },
    },
    {
        "user_query": "户号12345的结算记录在哪？",
        "structured_intent": {
            "entities": [{"name": "12345", "std_name": "用电户", "type": "User"}],
            "relations": ["产生"],
            "attributes": ["结算编号", "结算时间", "用电量"],
            "filters": {},
            "constraints": [],
        },
    },
    {
        "user_query": "李四家上个月电费多少钱？",
        "structured_intent": {
            "entities": [{"name": "李四", "std_name": "用电户", "type": "User"}],
            "relations": ["产生"],
            "attributes": ["电费金额"],
            "filters": {"结算周期": "上月"},
            "constraints": [],
        },
    },
]

# ============== _invoke_skill 执行链（从 smart_skills.py 迁移） ==============
def _invoke_skill(
    db: Session,
    skill: SmartSkill,
    step: Dict[str, Any],
    context: Dict[str, Any],
):
    payload = context.get("input_payload") or {}
    runtime = skill.runtime_config or {}
    step_config = step.get("config") if isinstance(step, dict) else {}
    merged_cfg = {}
    merged_cfg.update(runtime if isinstance(runtime, dict) else {})
    merged_cfg.update(step_config if isinstance(step_config, dict) else {})

    skill_code = (skill.skill_code or "").lower()
    action = str(merged_cfg.get("action") or "").lower()

    def _extract_match_tokens(text_value: str) -> List[str]:
        txt = (text_value or "").lower()
        raw_parts = re.split(r"[\s,;:()\-_/，。！？、]+", txt)
        parts = [p for p in raw_parts if p]
        zh_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", txt)
        tokens = set(parts)
        for chunk in zh_chunks:
            tokens.add(chunk)
            if len(chunk) > 2:
                for i in range(len(chunk) - 1):
                    tokens.add(chunk[i : i + 2])
        stop_words = {"分析", "数据", "信息", "需求", "情况", "这个", "我们", "为什么", "然后", "以及"}
        return [t for t in tokens if t and t not in stop_words]

    def _safe_float(v: Any) -> Optional[float]:
        try:
            return float(v)
        except Exception:
            return None

    def _parse_numeric_evidence(text_value: str) -> List[Dict[str, Any]]:
        txt = str(text_value or "")
        found = []
        for m in re.finditer(r"(-?\d+(?:\.\d+)?)\s*([a-zA-Z%℃度千伏MWkWh]*)", txt):
            num = _safe_float(m.group(1))
            if num is None:
                continue
            found.append({"value": num, "unit": m.group(2) or ""})
        return found

    def _concept_path(concept_map: Dict[str, Any], concept_id: str) -> List[str]:
        path = []
        cur = concept_map.get(str(concept_id))
        guard = 0
        while cur and guard < 20:
            path.append(cur.get("name") or "")
            pid = cur.get("parent_id")
            if not pid:
                break
            cur = concept_map.get(str(pid))
            guard += 1
        path.reverse()
        return [x for x in path if x]

    def _load_asset(asset_type: str, default_value: Any) -> Any:
        row = (
            db.query(IntentSemanticAsset)
            .filter(IntentSemanticAsset.asset_type == asset_type, IntentSemanticAsset.enabled == True)  # noqa: E712
            .order_by(IntentSemanticAsset.updated_at.desc())
            .first()
        )
        return (row.content if row and row.content is not None else default_value)

    def _step1_preprocess(intent_text: str) -> Dict[str, Any]:
        txt = str(intent_text or "").strip()
        # 规则：不做中文碎词分词，只提取完整关键词
        clean_query = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", "", txt)
        stop_words = [str(x) for x in _load_asset("stop_words", DEFAULT_STEP1_STOP_WORDS)]
        removed_stop_words: List[str] = []

        # 先移除停用词（长词优先）
        working = clean_query
        for sw in sorted(set(stop_words), key=len, reverse=True):
            if not sw:
                continue
            if sw in working:
                removed_stop_words.append(sw)
                working = working.replace(sw, "")

        synonym_map = _load_asset("synonym_map", DEFAULT_STEP1_SYNONYM_MAP) or {}
        asset_phrases = _load_asset("step1_domain_phrases", DEFAULT_STEP1_DOMAIN_PHRASES) or []
        phrase_candidates = list(asset_phrases)
        for canonical, syns in (synonym_map or {}).items():
            if canonical:
                phrase_candidates.append(str(canonical))
            for s in (syns or []):
                phrase_candidates.append(str(s))
        # 保留长度>=2的完整词，避免“件类/想按/询用”这类碎片
        phrase_candidates = [p for p in dict.fromkeys(phrase_candidates) if p and len(p) >= 2]

        # 在文本中匹配完整短语（按出现位置输出，禁止半截词）
        hits: List[Dict[str, Any]] = []
        for p in sorted(phrase_candidates, key=len, reverse=True):
            start = working.find(p)
            while start >= 0:
                hits.append({"term": p, "start": start, "end": start + len(p)})
                start = working.find(p, start + 1)
        hits.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))
        selected: List[Dict[str, Any]] = []
        used_ranges: List[tuple] = []
        for h in hits:
            overlap = any(not (h["end"] <= a or h["start"] >= b) for a, b in used_ranges)
            if overlap:
                continue
            selected.append(h)
            used_ranges.append((h["start"], h["end"]))
        core_tokens = []
        for h in selected:
            t = h["term"]
            if t not in core_tokens:
                core_tokens.append(t)

        # 补充数字实体（如户号12345）
        for m in re.finditer(r"\d{3,}", working):
            num = m.group(0)
            if num not in core_tokens:
                core_tokens.append(num)

        tokens = [x["term"] for x in hits] if hits else []
        clean_text = " ".join(core_tokens)
        return {
            "original_query": txt,
            "tokens": tokens,
            "core_tokens": core_tokens,
            "core_text": clean_text,
            "clean_text": clean_text,
            "removed_stop_words": list(dict.fromkeys(removed_stop_words)),
        }

    def _step1_llm_understand(intent_text: str, pre: Dict[str, Any]) -> Dict[str, Any]:
        # 使用豆包做“初步可计算意图理解”，失败时自动降级规则结果
        conn = _pick_script_assistant_llm(db)
        raw_query = str(intent_text or "").strip()

        def _fallback_understand(q: str) -> Dict[str, Any]:
            q2 = q or ""
            intent_type = "query"
            stat_method = None
            if any(x in q2 for x in ["数量", "多少", "几", "统计", "总数", "总量"]):
                intent_type = "stat"
                stat_method = "count"
            if any(x in q2 for x in ["按照", "按", "分组", "分类"]):
                if intent_type == "stat":
                    intent_type = "group_stat"
                else:
                    intent_type = "group_query"
            group_fields = []
            if "类型" in q2 and any(x in q2 for x in ["按照", "按", "分组", "分类"]):
                group_fields.append("类型")
            return {
                "intent_type": intent_type,
                "stat_object": "用电户" if "用电户" in q2 or "用户" in q2 else None,
                "stat_method": stat_method,
                "conditions": [],
                "group_fields": group_fields,
                "intent_summary": f"{'分组统计' if intent_type=='group_stat' else ('统计' if intent_type=='stat' else '查询')}请求",
            }

        if not conn:
            fb = _fallback_understand(raw_query)
            return {
                "used_llm": False,
                "intent_summary": fb.get("intent_summary") or f"查询{raw_query}",
                "structured_hint": fb,
            }
        system_prompt = (
            "你是电力数据语义理解器。请基于用户原始问句做意图理解，不要把词切碎。"
            "你需要识别 intent_type(query/stat/group_stat)、统计对象、统计方式、条件、分组字段。"
            "规则：'数量/多少' => stat_method=count；'按照...类型' => group_fields包含'类型'。"
            "请只输出JSON，不要解释。"
        )
        user_prompt = json.dumps(
            {
                "raw_query": raw_query,
                "output_schema": {
                    "intent_summary": "string",
                    "intent_type": "query|stat|group_stat",
                    "stat_object": "string",
                    "stat_method": "count|sum|max|min|avg|null",
                    "conditions": ["string"],
                    "group_fields": ["string"],
                    "entities": ["string"],
                    "attributes": ["string"],
                    "relations": ["string"],
                    "filters": {"key": "value"},
                    "constraints": ["string"],
                },
            },
            ensure_ascii=False,
        )
        try:
            resp = call_openai_compatible_messages(
                conn,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1,
                max_tokens=800,
            )
            content = ((((resp or {}).get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
            start = content.find("{")
            end = content.rfind("}")
            parsed = json.loads(content[start : end + 1]) if start >= 0 and end >= start else {}
            if not parsed.get("intent_type"):
                parsed.update(_fallback_understand(raw_query))
            return {
                "used_llm": True,
                "llm_provider": conn.provider,
                "llm_model_name": conn.model_name,
                "intent_summary": parsed.get("intent_summary") or f"查询{raw_query}",
                "structured_hint": parsed,
            }
        except Exception:
            fb = _fallback_understand(raw_query)
            return {
                "used_llm": False,
                "intent_summary": fb.get("intent_summary") or f"查询{raw_query}",
                "structured_hint": fb,
            }

    def _step1_vector_match(intent_text: str, pre: Dict[str, Any], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        token_list = [str(x) for x in (pre.get("core_tokens") or []) if str(x).strip()]
        if not token_list:
            core = str(pre.get("core_text") or intent_text or "").strip()
            token_list = [core] if core else []

        config = config or {}
        top_k_per_token = int(config.get("top_k_per_token", 8))
        only_top_entity_attr = bool(config.get("only_top_entity_attr", True))
        term_types = config.get("term_types", ["entity", "attribute"])

        entity_map = {str(e.id): (e.entity_name or e.entity_code or str(e.id)) for e in db.query(Entity).all()}
        per_token = []
        all_matches: List[Dict[str, Any]] = []
        entities: List[Dict[str, Any]] = []
        relations: List[Dict[str, Any]] = []
        attributes: List[Dict[str, Any]] = []

        for tk in token_list:
            m = query_standard_semantic_matches(
                db=db,
                query_text=tk,
                top_k=top_k_per_token,
                term_types=term_types,
                normalize_l2=True,
                bind_ontology=True,
                entity_scope="data",
            )
            all_matches.extend(m)
            top_entity = next((x for x in m if x.get("term_type") == "entity"), None)
            token_attrs = [x for x in m if x.get("term_type") == "attribute"]
            # 属性结果反推实体归属
            for a in token_attrs:
                bind = a.get("ontology_bind") or {}
                rid = str(bind.get("ref_id") or "")
                if rid and rid in entity_map:
                    a["owner_entity_id"] = rid
                    a["owner_entity_name"] = entity_map[rid]
            if top_entity:
                entities.append(top_entity)
            relations.extend([x for x in m if x.get("term_type") == "relation"][:2])
            attributes.extend(token_attrs[:3])
            per_token.append({"token": tk, "top_entity": top_entity, "matches": m})

        # 去重
        def _uniq(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            out = []
            seen = set()
            for r in rows:
                k = str(r.get("term_id") or "") + "|" + str(r.get("term_type") or "")
                if k in seen:
                    continue
                seen.add(k)
                out.append(r)
            return out
        entities = _uniq(entities)[:8]
        relations = _uniq(relations)[:8]
        attributes = _uniq(attributes)[:8]
        all_matches = sorted(_uniq(all_matches), key=lambda x: float(x.get("score") or 0), reverse=True)[:30]

        # 默认只返回得分最高的实体及属性
        top_entity = None
        top_attribute = None
        if only_top_entity_attr and all_matches:
            # 先找得分最高的实体
            entity_matches = [x for x in all_matches if x.get("term_type") == "entity"]
            if entity_matches:
                top_entity = entity_matches[0]
                # 找属于这个实体的得分最高的属性
                entity_id = top_entity.get("entity_id")
                attr_matches_for_entity = [
                    x for x in all_matches
                    if x.get("term_type") == "attribute" and x.get("entity_id") == entity_id
                ]
                if attr_matches_for_entity:
                    top_attribute = attr_matches_for_entity[0]

        return {
            "token_queries": per_token,
            "matches": all_matches,
            "entities": entities,
            "relations": relations,
            "attributes": attributes,
            "query_scope": {"entity_scope": "data", "term_types": term_types},
            "config": {"top_k_per_token": top_k_per_token, "only_top_entity_attr": only_top_entity_attr},
            "top_entity": top_entity,
            "top_attribute": top_attribute,
        }

    def _step1_synonym_match(pre: Dict[str, Any]) -> Dict[str, Any]:
        synonym_map = _load_asset("synonym_map", DEFAULT_STEP1_SYNONYM_MAP) or {}
        core = str(pre.get("core_text") or "")
        hit = []
        for canonical, syns in synonym_map.items():
            syn_list = [str(x) for x in (syns or [])]
            matched = [s for s in syn_list if s and s in core]
            if matched or (str(canonical) in core):
                hit.append({"canonical": str(canonical), "matched_terms": matched or [str(canonical)]})
        return {"matches": hit}

    def _step1_rule_dict_preprocess(intent_text: str) -> Dict[str, Any]:
        rule_dict = _load_asset("step1_rule_dict", DEFAULT_STEP1_RULE_DICT) or DEFAULT_STEP1_RULE_DICT
        raw_query = str(intent_text or "").strip()
        working_text = raw_query
        replacements = []
        replaced_tokens = []

        for src, rule in sorted(rule_dict.items(), key=lambda x: len(x[0]), reverse=True):
            if src in working_text:
                replacements.append({
                    "original": src,
                    "replaced_with": rule.get("replace_with", []),
                    "type": rule.get("type", "unknown"),
                })
                for t in rule.get("replace_with", []):
                    replaced_tokens.append(t)
                working_text = working_text.replace(src, " ")

        normalized_tokens = list(dict.fromkeys([t for t in replaced_tokens if len(t) >= 2]))
        short_sentence = " ".join(normalized_tokens)

        filters = {}
        group_by = None
        operation = "查询"
        for r in replacements:
            if r.get("type") == "filter" and "=" in "".join(r.get("replaced_with", [])):
                for t in r.get("replaced_with", []):
                    if "=" in t:
                        k, v = t.split("=", 1)
                        filters[k] = v
            if r.get("type") == "operation":
                operation = "".join(r.get("replaced_with", [operation]))
            if r.get("original") in ["证件类型"] and any(x in raw_query for x in ["按照", "按", "分组", "分类"]):
                group_by = "证件类型"

        return {
            "original_query": raw_query,
            "replacements": replacements,
            "normalized_tokens": normalized_tokens,
            "short_sentence": short_sentence,
            "filters": filters,
            "group_by": group_by,
            "operation": operation,
        }

    def _step1_attribute_belongs_validate(vector_match: Dict[str, Any]) -> Dict[str, Any]:
        entities_map = {str(e.id): e for e in db.query(Entity).all()}
        all_matches = vector_match.get("matches", [])
        validations = []
        all_passed = True

        for m in all_matches:
            term_type = m.get("term_type")
            if term_type != "attribute":
                continue
            attr_name = m.get("attribute_name")
            belongs_to_entity_id = m.get("entity_id")
            belongs_to_entity_name = m.get("entity_name")

            valid = False
            if belongs_to_entity_id and belongs_to_entity_id in entities_map:
                e = entities_map[belongs_to_entity_id]
                props = e.properties_schema if isinstance(e.properties_schema, list) else []
                for p in props:
                    plabel = str(p.get("label") or p.get("cnName") or "")
                    if plabel == attr_name:
                        valid = True
                        break
            validations.append({
                "attribute_name": attr_name,
                "belongs_to_entity_name": belongs_to_entity_name,
                "belongs_to_entity_id": belongs_to_entity_id,
                "passed": valid,
            })
            if not valid:
                all_passed = False

        return {
            "validations": validations,
            "all_passed": all_passed,
            "passed_count": len([v for v in validations if v.get("passed")]),
            "total_count": len(validations),
        }

    def _step1_llm_refine_fusion(
        intent_text: str,
        rule_preprocess: Dict[str, Any],
        vector_match: Dict[str, Any],
        attribute_validate: Dict[str, Any],
    ) -> Dict[str, Any]:
        conn = _pick_script_assistant_llm(db)

        entities_list = list(dict.fromkeys([
            x.get("entity_name")
            for x in vector_match.get("matches", [])
            if x.get("term_type") == "entity" and x.get("entity_name")
        ]))
        attributes_list = list(dict.fromkeys([
            x.get("attribute_name")
            for x in vector_match.get("matches", [])
            if x.get("term_type") == "attribute" and x.get("attribute_name")
        ]))
        filters = rule_preprocess.get("filters", {})
        group_by = rule_preprocess.get("group_by")
        operation = rule_preprocess.get("operation", "查询")

        relations_list = []
        entity_relations = db.query(EntityRelation).all()
        entity_name_map = {str(e.id): (e.entity_name or e.entity_code or str(e.id)) for e in db.query(Entity).all()}
        for r in entity_relations[:20]:
            src_name = entity_name_map.get(str(r.source_entity_id), "")
            tgt_name = entity_name_map.get(str(r.target_entity_id), "")
            if src_name and tgt_name and src_name in entities_list and tgt_name in entities_list:
                relations_list.append({
                    "source": src_name,
                    "target": tgt_name,
                    "type": r.relation_name or "产生",
                })

        fallback_structured = {
            "query_type": "DATA_ONLY",
            "risk_level": "LOW",
            "entities": entities_list,
            "relations": relations_list,
            "group_by": group_by,
            "filters": filters,
            "select_fields": attributes_list,
            "trace_id": f"trace_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
        }

        if not conn:
            return {
                "used_llm": False,
                "structured": fallback_structured,
            }

        system_prompt = (
            "你是电力数据结构化意图生成器。请仅做结构化输出，不要多余推理。"
            "输出格式严格为JSON，不要解释。"
        )
        user_prompt = json.dumps({
            "task": "generate_structured_intent",
            "context": {
                "entities": entities_list,
                "relations": relations_list,
                "attributes": attributes_list,
                "filters": filters,
                "group_by": group_by,
                "operation": operation,
            },
            "output_schema": {
                "query_type": "DATA_ONLY",
                "risk_level": "LOW|MEDIUM|HIGH",
                "entities": ["string"],
                "relations": [{"source": "string", "target": "string", "type": "string"}],
                "group_by": "string|null",
                "filters": {"key": "value"},
                "select_fields": ["string"],
                "trace_id": "string",
            },
        }, ensure_ascii=False)

        try:
            resp = call_openai_compatible_messages(
                conn,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.1,
                max_tokens=1200,
            )
            content = ((((resp or {}).get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
            start = content.find("{")
            end = content.rfind("}")
            parsed = json.loads(content[start : end + 1]) if start >= 0 and end >= start else fallback_structured
            if not parsed.get("entities"):
                parsed["entities"] = entities_list
            if not parsed.get("trace_id"):
                parsed["trace_id"] = f"trace_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            return {
                "used_llm": True,
                "llm_provider": conn.provider,
                "llm_model_name": conn.model_name,
                "structured": parsed,
            }
        except Exception:
            return {
                "used_llm": False,
                "structured": fallback_structured,
            }

    def _step1_dynamic_confidence_clarify(
        vector_match: Dict[str, Any],
        llm_refine: Dict[str, Any],
    ) -> Dict[str, Any]:
        all_matches = vector_match.get("matches", [])
        min_score = 1.0
        for m in all_matches:
            s = float(m.get("score", 0.0))
            if s < min_score:
                min_score = s
        if not all_matches:
            min_score = 0.0

        query_type = (llm_refine.get("structured") or {}).get("query_type", "DATA_ONLY")
        threshold = 0.5 if query_type == "DATA_ONLY" else 0.6
        need_clarify = min_score < threshold

        return {
            "query_type": query_type,
            "threshold": threshold,
            "min_score": round(min_score, 4),
            "need_clarify": need_clarify,
            "clarify_questions": ["请确认您要查询的对象是哪个实体？"] if need_clarify else [],
        }

    def _step1_example_match(intent_text: str, pre: Dict[str, Any]) -> Dict[str, Any]:
        examples = _load_asset("intent_examples", DEFAULT_STEP1_INTENT_EXAMPLES) or []
        if not examples:
            return {"best_example": None, "score": 0.0}
        query_text = pre.get("core_text") or intent_text
        texts = [query_text] + [str(x.get("user_query") or "") for x in examples]
        vecs = embed_texts(db, texts)
        if not vecs or len(vecs) != len(texts):
            return {"best_example": None, "score": 0.0}
        qv = vecs[0]
        scored = []
        for i, ex in enumerate(examples, start=1):
            score = (cosine_similarity(qv, vecs[i]) + 1) / 2
            scored.append({"example": ex, "score": float(score)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return {"best_example": scored[0]["example"], "score": scored[0]["score"], "top_examples": scored[:3]}

    def _compose_step1_structured_intent(
        intent_text: str,
        pre: Dict[str, Any],
        llm_understand: Dict[str, Any],
        vector_match: Dict[str, Any],
        synonym_match: Dict[str, Any],
        example_match: Dict[str, Any],
    ) -> Dict[str, Any]:
        llm_hint = llm_understand.get("structured_hint") or {}
        best_example = (example_match.get("best_example") or {}).get("structured_intent") or {}
        canonical_hits = [x.get("canonical") for x in (synonym_match.get("matches") or []) if x.get("canonical")]
        vector_top = vector_match.get("matches") or []

        std_entities = (llm_hint.get("entities") or [])
        if not std_entities:
            std_entities = [x.get("term") for x in vector_top if x.get("term_type") in ("entity", "canonical")][:3]
        entities_out = []
        for x in std_entities[:6]:
            entities_out.append({"name": str(x), "std_name": str(x), "type": "Entity"})
        if not entities_out and (best_example.get("entities") or []):
            entities_out = best_example.get("entities") or []

        attributes_out = list(dict.fromkeys((llm_hint.get("attributes") or []) + canonical_hits + (best_example.get("attributes") or [])))
        relations_out = list(dict.fromkeys((llm_hint.get("relations") or []) + (best_example.get("relations") or ["产生"])))
        filters_out = {}
        filters_out.update(best_example.get("filters") or {})
        filters_out.update(llm_hint.get("filters") or {})
        core_text = pre.get("core_text") or ""
        if ("这个月" in intent_text) or ("本月" in core_text):
            filters_out["结算周期"] = "本月"
        if ("上个月" in intent_text) or ("上月" in core_text):
            filters_out["结算周期"] = "上月"
        constraints_out = list(dict.fromkeys((llm_hint.get("constraints") or []) + (best_example.get("constraints") or [])))
        return {
            "entities": entities_out,
            "relations": relations_out,
            "attributes": attributes_out,
            "filters": filters_out,
            "constraints": constraints_out,
        }

    def _build_graph_context_for_llm(intent_text: str) -> Dict[str, Any]:
        concepts = db.query(Concept).all()
        entities = db.query(Entity).all()
        entity_relations = db.query(EntityRelation).all()
        tokens = _extract_match_tokens(str(intent_text))
        retrieval_cfg = get_or_init_retrieval_config(db)
        if semantic_status(db).get("embedding_rows", 0) == 0:
            rebuild_semantic_index(db)
        entity_sem_scores = score_entities_semantic(db, intent_text)

        def entity_hit_info(e: Entity) -> Dict[str, Any]:
            text_parts = [e.entity_name or "", e.entity_code or "", e.entity_en_name or ""]
            props = e.properties_schema if isinstance(e.properties_schema, list) else []
            field_hits = []
            for p in props[:30]:
                name = str(p.get("name") or "")
                label = str(p.get("label") or "")
                text_parts.append(name)
                text_parts.append(label)
                joined = f"{name} {label}".lower()
                hit_tokens = [t for t in tokens if t in joined]
                if hit_tokens:
                    field_hits.append(
                        {
                            "name": name,
                            "label": label,
                            "type": p.get("type"),
                            "hit_tokens": list(set(hit_tokens)),
                        }
                    )
            full = " ".join(text_parts).lower()
            entity_hit_tokens = list(set([t for t in tokens if t in full]))
            keyword_score = min(1.0, (len(entity_hit_tokens) + len(field_hits)) / 8.0)
            semantic_score = float(entity_sem_scores.get(str(e.id), 0.0))
            mixed_score = hybrid_score(keyword_score, semantic_score, retrieval_cfg)
            hit_score = mixed_score * 100
            return {
                "entity_hit_tokens": entity_hit_tokens,
                "field_hits": field_hits,
                "hit_score": hit_score,
                "keyword_score": keyword_score,
                "semantic_score": semantic_score,
                "mixed_score": mixed_score,
            }

        ranked_entities = sorted(entities, key=lambda x: entity_hit_info(x).get("hit_score", 0), reverse=True)
        top_entities = []
        for e in ranked_entities[:8]:
            hit_info = entity_hit_info(e)
            props = e.properties_schema if isinstance(e.properties_schema, list) else []
            physical_table_name = (e.entity_en_name or "").strip() or (e.entity_code or "").strip()
            top_entities.append(
                {
                    "node_id": str(e.id),
                    "entity_id": str(e.id),
                    "entity_code": e.entity_code,
                    "entity_cn_name": e.entity_name,
                    "entity_en_name": e.entity_en_name,
                    "landing_table_en_name": physical_table_name,
                    "physical_table_name": physical_table_name,
                    "table_name_rule": "physical_table_name = entity_en_name",
                    "hit_score": hit_info.get("hit_score", 0),
                    "keyword_score": hit_info.get("keyword_score", 0),
                    "semantic_score": hit_info.get("semantic_score", 0),
                    "mixed_score": hit_info.get("mixed_score", 0),
                    "entity_hit_tokens": hit_info.get("entity_hit_tokens", []),
                    "matched_fields": hit_info.get("field_hits", []),
                    "fields": [{"name": p.get("name"), "label": p.get("label"), "type": p.get("type")} for p in props[:15]],
                }
            )

        entity_table_map = {
            str(e.id): ((e.entity_en_name or "").strip() or (e.entity_code or "").strip())
            for e in entities
        }
        # 关系来源强约束：优先使用“实体关系维护”数据，不做无依据猜测
        table_relations_from_entities = []
        for r in entity_relations[:80]:
            src_table = entity_table_map.get(str(r.source_entity_id))
            tgt_table = entity_table_map.get(str(r.target_entity_id))
            relation_expr = (r.join_expr or "").strip() or None
            table_relations_from_entities.append(
                {
                    "main_table_en": src_table,
                    "related_table_en": tgt_table,
                    "relation_expr": relation_expr,
                    "source": "entity_relation_maintenance",
                    "relation_name": r.relation_name,
                    "direction": r.direction,
                    "cardinality": r.cardinality,
                }
            )
        return {
            "concepts": [{"id": str(c.id), "name": c.name, "level": c.level} for c in concepts[:30]],
            "context_rules": {
                "entity_table_name_rule": "每个实体对应表名=实体落地英文表名(entity_en_name / landing_table_en_name)",
                "must_use_entity_en_name_as_table": True,
                "relation_source_rule": "关系仅来源于实体关系维护，不基于未知表关系猜测",
            },
            "entities": top_entities,
            "entity_relations": [
                {
                    "source_entity_id": str(r.source_entity_id),
                    "target_entity_id": str(r.target_entity_id),
                    "source_entity_table": entity_table_map.get(str(r.source_entity_id)),
                    "target_entity_table": entity_table_map.get(str(r.target_entity_id)),
                    "relation_name": r.relation_name,
                    "direction": r.direction,
                    "cardinality": r.cardinality,
                    "join_expr": r.join_expr,
                    "description": r.description,
                    "source": "entity_relation_maintenance",
                }
                for r in entity_relations[:80]
            ],
            "table_relations": table_relations_from_entities,
        }

    # 首个可执行技能：智能联接推荐（复用原有阈值策略）
    if "join_recommend" in skill_code or action == "smart_join_recommend":
        intent = payload.get("intent") or context.get("intent")
        if not intent:
            raise HTTPException(status_code=400, detail="编排执行缺少intent参数")
        entity_id = payload.get("entity_id")
        top_k = int(payload.get("top_k") or merged_cfg.get("top_k") or 3)
        strategy_cfg = context.get("workflow_strategy") or {}
        single_table_policy = str(
            payload.get("single_table_policy")
            or merged_cfg.get("single_table_policy")
            or strategy_cfg.get("single_table_policy")
            or "auto"
        ).lower()
        result = generate_smart_join_candidates(
            db=db,
            intent=intent,
            entity_id=entity_id,
            top_k=top_k,
            single_table_policy=single_table_policy,
        )
        return {
            "type": "smart_join_recommend",
            "threshold": CONFIDENCE_THRESHOLD,
            "single_table_policy": single_table_policy,
            "result": result,
        }

    if action == "biz_requirement_understand":
        intent = payload.get("intent") or ""
        if not intent:
            raise HTTPException(status_code=400, detail="业务理解技能缺少intent参数")
        planner = get_active_planner_config(db)
        llm_resp = None
        llm_answer = ""
        graph_context = _build_graph_context_for_llm(intent)
        if planner and planner.llm_connection_id:
            conns = db.query(LLMConnectionConfig).all()
            conn = next((c for c in conns if str(c.id) == str(planner.llm_connection_id) and c.enabled), None)
            if conn:
                try:
                    llm_resp = call_openai_compatible_messages(
                        conn,
                        messages=[
                            {
                                "role": "system",
                                "content": (
                                    "你是数据业务分析师。请结合图谱上下文做任务规划："
                                    "1)先判断是否可单表完成；若可，优先单表SQL；"
                                    "2)否则给主联接方案。"
                                    "注意重点使用实体唯一编码(entity_code)、实体中文名称(entity_cn_name)、实体落地英文表名(entity_en_name/landing_table_en_name)以及字段信息。"
                                    "强规则：每个实体对应物理表名=实体落地英文表名(entity_en_name/landing_table_en_name)，关联关系中必须按该表名进行推理和SQL建议。"
                                    "输出：分析目标、关键实体、关键字段、单表/联接判断、建议SQL要点。"
                                ),
                            },
                            {
                                "role": "user",
                                "content": f"业务需求:\n{intent}\n\n本地图谱上下文(JSON):\n{json.dumps(graph_context, ensure_ascii=False)}",
                            },
                        ],
                    )
                    llm_answer = (
                        (((llm_resp or {}).get("choices") or [{}])[0].get("message") or {}).get("content")
                        or ""
                    )
                except Exception:
                    llm_resp = None
                    llm_answer = ""
        if not llm_answer:
            llm_answer = f"规则理解：需求为“{intent}”，建议先明确主题实体、关联实体、指标口径和时间范围。"
        return {
            "type": "biz_requirement_understand",
            "understanding": llm_answer,
            "used_llm": bool(llm_resp),
            "llm_provider": "doubao_or_configured_llm" if llm_resp else "rule_fallback",
            "llm_input_preview": {
                "intent": intent,
                "graph_context": graph_context,
            },
            "graph_context_hit": {
                "entity_count": len(graph_context.get("entities") or []),
                "entities": graph_context.get("entities") or [],
            },
        }

    if action == "graph_entity_field_locator":
        intent = payload.get("intent") or ""
        concepts = db.query(Concept).all()
        entities = db.query(Entity).all()
        relations = db.query(EntityRelation).all()
        concept_map = {str(c.id): c.name for c in concepts}
        tokens = _extract_match_tokens(str(intent))
        retrieval_cfg = get_or_init_retrieval_config(db)
        if semantic_status(db).get("embedding_rows", 0) == 0:
            rebuild_semantic_index(db)
        entity_sem_scores = score_entities_semantic(db, intent)

        def score_entity(e: Entity):
            text_parts = [e.entity_name or "", e.entity_code or "", e.entity_en_name or ""]
            props = e.properties_schema if isinstance(e.properties_schema, list) else []
            matched_fields = []
            for p in props:
                n = str(p.get("name") or "")
                l = str(p.get("label") or "")
                text_parts.append(n)
                text_parts.append(l)
                blob = f"{n} {l}".lower()
                hit_tokens = [t for t in tokens if t in blob]
                if hit_tokens:
                    matched_fields.append({"name": n, "label": l, "type": p.get("type"), "hit_tokens": list(set(hit_tokens))})
            full = " ".join(text_parts).lower()
            entity_hit_tokens = [t for t in tokens if t in full]
            keyword_score = min(1.0, (len(set(entity_hit_tokens)) + len(matched_fields)) / 8.0)
            semantic_score = float(entity_sem_scores.get(str(e.id), 0.0))
            mixed_score = hybrid_score(keyword_score, semantic_score, retrieval_cfg)
            score = mixed_score * 100
            return score, list(set(entity_hit_tokens)), matched_fields, keyword_score, semantic_score, mixed_score

        ranked = sorted(entities, key=lambda x: score_entity(x)[0], reverse=True)
        top_entities = []
        for e in ranked[:8]:
            score, entity_hit_tokens, matched_fields, keyword_score, semantic_score, mixed_score = score_entity(e)
            props = e.properties_schema if isinstance(e.properties_schema, list) else []
            physical_table_name = (e.entity_en_name or "").strip() or (e.entity_code or "").strip()
            top_entities.append(
                {
                    "node_id": str(e.id),
                    "entity_id": str(e.id),
                    "entity_code": e.entity_code,
                    "entity_cn_name": e.entity_name,
                    "entity_en_name": e.entity_en_name,
                    "landing_table_en_name": physical_table_name,
                    "physical_table_name": physical_table_name,
                    "hit_score": score,
                    "keyword_score": keyword_score,
                    "semantic_score": semantic_score,
                    "mixed_score": mixed_score,
                    "entity_hit_tokens": entity_hit_tokens,
                    "matched_fields": matched_fields,
                    "concept_name": concept_map.get(str(e.concept_id)),
                    "fields": [
                        {
                            "name": p.get("name"),
                            "label": p.get("label"),
                            "type": p.get("type"),
                        }
                        for p in props[:20]
                    ],
                }
            )

        relation_links = []
        entity_name_map = {str(e.id): e.entity_name for e in entities}
        entity_table_map = {
            str(e.id): ((e.entity_en_name or "").strip() or (e.entity_code or "").strip())
            for e in entities
        }
        for r in relations[:50]:
            relation_links.append(
                {
                    "source_entity": entity_name_map.get(str(r.source_entity_id), str(r.source_entity_id)),
                    "target_entity": entity_name_map.get(str(r.target_entity_id), str(r.target_entity_id)),
                    "source_table": entity_table_map.get(str(r.source_entity_id)),
                    "target_table": entity_table_map.get(str(r.target_entity_id)),
                    "relation_name": r.relation_name,
                    "direction": r.direction,
                    "cardinality": r.cardinality,
                    "join_expr": r.join_expr,
                    "source": "entity_relation_maintenance",
                }
            )

        table_links = [
            {
                "main_table_en": entity_table_map.get(str(r.source_entity_id)),
                "related_table_en": entity_table_map.get(str(r.target_entity_id)),
                "relation_expr": (r.join_expr or "").strip() or None,
                "relation_scope": "entity_relation",
                "source": "entity_relation_maintenance",
                "relation_name": r.relation_name,
                "direction": r.direction,
                "cardinality": r.cardinality,
            }
            for r in relations[:80]
        ]

        return {
            "type": "graph_entity_field_locator",
            "entities": top_entities,
            "entity_relations": relation_links,
            "table_relations": table_links,
            "hit_summary": [
                {
                    "entity_name": x.get("entity_cn_name"),
                    "entity_code": x.get("entity_code"),
                    "entity_en_name": x.get("entity_en_name"),
                    "landing_table_en_name": x.get("landing_table_en_name") or x.get("physical_table_name"),
                    "physical_table_name": x.get("physical_table_name"),
                    "hit_score": x.get("hit_score", 0),
                    "keyword_score": x.get("keyword_score", 0),
                    "semantic_score": x.get("semantic_score", 0),
                    "mixed_score": x.get("mixed_score", 0),
                    "entity_hit_tokens": x.get("entity_hit_tokens", []),
                    "matched_fields": x.get("matched_fields", []),
                }
                for x in top_entities
            ],
        }

    if action == "join_sql_recommend":
        intent = payload.get("intent") or ""
        entity_id = payload.get("entity_id")
        top_k = int(payload.get("top_k") or merged_cfg.get("top_k") or 3)
        strategy_cfg = context.get("workflow_strategy") or {}
        single_table_policy = str(
            payload.get("single_table_policy")
            or merged_cfg.get("single_table_policy")
            or strategy_cfg.get("single_table_policy")
            or "auto"
        ).lower()
        result = generate_smart_join_candidates(
            db=db,
            intent=intent,
            entity_id=entity_id,
            top_k=top_k,
            single_table_policy=single_table_policy,
        )
        return {
            "type": "join_sql_recommend",
            "threshold": CONFIDENCE_THRESHOLD,
            "single_table_policy": single_table_policy,
            "result": result,
        }

    if action == "join_sql_validate":
        last_output = context.get("last_output") or {}
        candidates = (((last_output or {}).get("result") or {}).get("candidates") or [])
        checks = []
        for c in candidates:
            checks.append(
                {
                    "candidate_id": c.get("candidate_id"),
                    "title": c.get("title"),
                    "can_execute_now": c.get("can_execute_now"),
                    "need_manual_review": c.get("need_manual_review"),
                    "reason_not_executable": c.get("reason_not_executable"),
                }
            )
        return {
            "type": "join_sql_validate",
            "checks": checks,
            "ok_count": len([x for x in checks if x.get("can_execute_now")]),
            "total": len(checks),
        }

    if action == "ontology_semantic_align":
        intent = str(payload.get("intent") or "")
        pre = _step1_preprocess(intent)
        llm_understand = _step1_llm_understand(intent, pre)
        vector_match = _step1_vector_match(intent, pre, {})
        synonym_match = _step1_synonym_match(pre)
        example_match = _step1_example_match(intent, pre)
        structured_intent = _compose_step1_structured_intent(intent, pre, llm_understand, vector_match, synonym_match, example_match)

        vector_top = vector_match.get("matches") or []
        aligned_terms = [
            {
                "entity_name": x.get("term"),
                "path": x.get("path") or [],
                "score": x.get("score"),
                "term_type": x.get("term_type"),
            }
            for x in vector_top[:8]
        ]
        confidence = max(
            float((vector_top[0].get("score") if vector_top else 0.0) or 0.0),
            float(example_match.get("score") or 0.0),
        )
        return {
            "type": "ontology_semantic_align",
            "intent": intent,
            "preprocess": pre,
            "llm_understand": llm_understand,
            "vector_match": {"top_matches": vector_top[:8]},
            "synonym_match": synonym_match,
            "example_match": {
                "score": example_match.get("score"),
                "best_user_query": ((example_match.get("best_example") or {}).get("user_query")),
                "top_examples": example_match.get("top_examples"),
            },
            "structured_intent": structured_intent,
            "aligned_terms": aligned_terms,
            "ontology_confidence": confidence,
            "low_confidence": confidence < 0.45,
            "used_llm": bool(llm_understand.get("used_llm")),
        }

    if action == "step1_preprocess":
        intent = str(payload.get("intent") or "")
        pre = _step1_preprocess(intent)
        return {
            "type": "step1_preprocess",
            "input": {"intent": intent},
            "process": {"method": "stop_words_filter + token_extract", "asset_type": "stop_words"},
            "output": pre,
        }

    if action == "step1_llm_understand":
        intent = str(payload.get("intent") or "")
        pre = payload.get("step1_preprocess_output") or _step1_preprocess(intent)
        llm_understand = _step1_llm_understand(intent, pre)
        return {
            "type": "step1_llm_understand",
            "input": {"intent": intent, "preprocess": pre},
            "process": {"method": "llm_intent_understand", "provider": llm_understand.get("llm_provider")},
            "output": llm_understand,
        }

    if action == "step1_vector_match":
        intent = str(payload.get("intent") or "")
        pre = payload.get("step1_preprocess_output") or _step1_preprocess(intent)
        config = payload.get("config") or {}
        output_count = int(config.get("output_count", 5))
        output_count = max(1, min(output_count, 100))
        
        vector_match = _step1_vector_match(intent, pre, config)
        
        simple_output = []
        seen_entity_ids = set()
        for m in vector_match.get("matches", []):
            entity_id = m.get("entity_id")
            if entity_id and entity_id not in seen_entity_ids:
                seen_entity_ids.add(entity_id)
                simple_output.append({
                    "entity_name": m.get("entity_name"),
                    "entity_id": entity_id,
                    "attribute_name": m.get("attribute_name"),
                    "attribute_category": m.get("attribute_category"),
                    "score": round(m.get("score", 0), 4)
                })
                if len(simple_output) >= output_count:
                    break
        
        return {
            "type": "step1_vector_match",
            "input": {"intent": intent, "preprocess": pre, "config": config},
            "process": {"method": "local_bge_embedding + cosine_similarity"},
            "output": {
                "simple": simple_output,
                "total_matches": len(vector_match.get("matches", [])),
                "output_count": len(simple_output)
            }
        }

    if action == "step1_synonym_match":
        intent = str(payload.get("intent") or "")
        pre = payload.get("step1_preprocess_output") or _step1_preprocess(intent)
        synonym_match = _step1_synonym_match(pre)
        return {
            "type": "step1_synonym_match",
            "input": {"intent": intent, "preprocess": pre},
            "process": {"method": "synonym_dictionary_match", "asset_type": "synonym_map"},
            "output": synonym_match,
        }

    if action == "step1_rule_dict_preprocess":
        intent = str(payload.get("intent") or "")
        rule_pre = _step1_rule_dict_preprocess(intent)
        return {
            "type": "step1_rule_dict_preprocess",
            "input": {"intent": intent},
            "process": {"method": "rule_dict_replace", "asset_type": "step1_rule_dict"},
            "output": rule_pre,
        }

    if action == "step1_attribute_belongs_validate":
        vector_match = payload.get("step1_vector_match_output") or {}
        validate = _step1_attribute_belongs_validate(vector_match)
        return {
            "type": "step1_attribute_belongs_validate",
            "input": {"vector_match": vector_match},
            "process": {"method": "attribute_belongs_to_validation"},
            "output": validate,
        }

    if action == "step1_llm_refine_fusion":
        intent = str(payload.get("intent") or "")
        rule_pre = payload.get("step1_rule_dict_preprocess_output") or _step1_rule_dict_preprocess(intent)
        vector_match = payload.get("step1_vector_match_output") or {}
        attribute_validate = payload.get("step1_attribute_belongs_validate_output") or _step1_attribute_belongs_validate(vector_match)
        refine = _step1_llm_refine_fusion(intent, rule_pre, vector_match, attribute_validate)
        return {
            "type": "step1_llm_refine_fusion",
            "input": {"intent": intent},
            "process": {"method": "llm_refine_fusion"},
            "output": refine,
        }

    if action == "step1_dynamic_confidence_clarify":
        vector_match = payload.get("step1_vector_match_output") or {}
        llm_refine = payload.get("step1_llm_refine_fusion_output") or {}
        clarify = _step1_dynamic_confidence_clarify(vector_match, llm_refine)
        return {
            "type": "step1_dynamic_confidence_clarify",
            "input": {"vector_match": vector_match, "llm_refine": llm_refine},
            "process": {"method": "dynamic_confidence_check"},
            "output": clarify,
        }

    if action == "step1_example_match":
        intent = str(payload.get("intent") or "")
        pre = payload.get("step1_preprocess_output") or _step1_preprocess(intent)
        llm_understand = payload.get("step1_llm_understand_output") or _step1_llm_understand(intent, pre)
        vector_match = payload.get("step1_vector_match_output") or _step1_vector_match(intent, pre)
        synonym_match = payload.get("step1_synonym_match_output") or _step1_synonym_match(pre)
        example_match = payload.get("step1_example_match_raw") or _step1_example_match(intent, pre)
        structured_intent = _compose_step1_structured_intent(intent, pre, llm_understand, vector_match, synonym_match, example_match)
        return {
            "type": "step1_example_match",
            "input": {"intent": intent, "preprocess": pre},
            "process": {"method": "few_shot_example_retrieval + intent_compose", "asset_type": "intent_examples"},
            "output": {
                "example_match": {
                    "score": example_match.get("score"),
                    "best_user_query": ((example_match.get("best_example") or {}).get("user_query")),
                    "top_examples": example_match.get("top_examples"),
                },
                "structured_intent": structured_intent,
            },
        }

    if action == "low_confidence_clarify":
        prev = context.get("last_output") or {}
        low = bool(prev.get("low_confidence"))
        top = (prev.get("aligned_terms") or [])[:3]
        suggestions = [x.get("entity_name") for x in top if x.get("entity_name")]
        questions = []
        if low:
            questions.append("请确认您要查询的对象是哪个实体？")
            if suggestions:
                questions.append(f"可选实体：{' / '.join(suggestions)}")
        return {
            "type": "low_confidence_clarify",
            "need_clarify": low,
            "clarify_questions": questions,
            "suggestions": suggestions,
        }

    if action == "graph_query_generate":
        intent = str(payload.get("intent") or "")
        entities = db.query(Entity).all()
        relations = db.query(EntityRelation).all()
        tokens = _extract_match_tokens(intent)
        entity_map = {str(e.id): e for e in entities}
        hit_entities = []
        for e in entities:
            blob = " ".join([e.entity_name or "", e.entity_code or "", e.entity_en_name or ""]).lower()
            hit = [t for t in tokens if t in blob]
            if hit:
                hit_entities.append((e, len(set(hit))))
        hit_entities.sort(key=lambda x: x[1], reverse=True)
        selected_relation = None
        for r in relations:
            src = entity_map.get(str(r.source_entity_id))
            tgt = entity_map.get(str(r.target_entity_id))
            src_hit = any(x[0].id == (src.id if src else None) for x in hit_entities)
            tgt_hit = any(x[0].id == (tgt.id if tgt else None) for x in hit_entities)
            if src_hit or tgt_hit:
                selected_relation = r
                break
        if not selected_relation and relations:
            selected_relation = relations[0]

        violations = []
        precheck_passed = True
        query_plan = None
        whitelist_edges = {
            (str(r.source_entity_id), str(r.target_entity_id), str(r.relation_name or ""))
            for r in relations
            if (r.join_expr or "").strip()
        }

        # 使用命中前2实体做白名单矩阵校验：若无直连，则不允许生成“直连关系”
        top2 = [x[0] for x in hit_entities[:2]]
        top2_ids = [str(x.id) for x in top2]
        two_hop_suggestion = None
        if len(top2_ids) >= 2:
            a, b = top2_ids[0], top2_ids[1]
            direct = any((x[0] == a and x[1] == b) or (x[0] == b and x[1] == a) for x in whitelist_edges)
            if not direct:
                for r1 in relations:
                    if str(r1.source_entity_id) != a:
                        continue
                    mid = str(r1.target_entity_id)
                    r2 = next((x for x in relations if str(x.source_entity_id) == mid and str(x.target_entity_id) == b), None)
                    if r2:
                        two_hop_suggestion = {
                            "path_entity_ids": [a, mid, b],
                            "path_relation_ids": [str(r1.id), str(r2.id)],
                        }
                        break

        if selected_relation:
            src = entity_map.get(str(selected_relation.source_entity_id))
            tgt = entity_map.get(str(selected_relation.target_entity_id))
            query_plan = {
                "source_entity_id": str(selected_relation.source_entity_id),
                "target_entity_id": str(selected_relation.target_entity_id),
                "source_entity_name": src.entity_name if src else None,
                "target_entity_name": tgt.entity_name if tgt else None,
                "relation_name": selected_relation.relation_name,
                "direction": selected_relation.direction,
                "cardinality": selected_relation.cardinality,
                "join_expr": selected_relation.join_expr,
            }
            # 关系合法性/本体规则预检查（生产加强版）
            if not (selected_relation.join_expr or "").strip():
                precheck_passed = False
                violations.append("关系缺少 join_expr，无法形成可靠图查询")
            edge_key = (
                str(selected_relation.source_entity_id),
                str(selected_relation.target_entity_id),
                str(selected_relation.relation_name or ""),
            )
            if edge_key not in whitelist_edges:
                precheck_passed = False
                violations.append("关系不在白名单矩阵中（需实体关系维护后方可使用）")
            if len(top2_ids) >= 2:
                a, b = top2_ids[0], top2_ids[1]
                if not (
                    (str(selected_relation.source_entity_id) == a and str(selected_relation.target_entity_id) == b)
                    or (str(selected_relation.source_entity_id) == b and str(selected_relation.target_entity_id) == a)
                ):
                    precheck_passed = False
                    violations.append("命中实体对未直连，禁止跨层误连；建议使用两跳路径")
        else:
            precheck_passed = False
            violations.append("未找到可用实体关系")

        return {
            "type": "graph_query_generate",
            "query_plan": query_plan,
            "rule_check_passed": precheck_passed,
            "violations": violations,
            "repaired_query": query_plan if precheck_passed else None,
            "relation_whitelist_check": {
                "whitelist_edge_count": len(whitelist_edges),
                "top_hit_entity_ids": top2_ids,
                "two_hop_suggestion": two_hop_suggestion,
            },
        }

    if action == "graph_query_execute":
        history = context.get("output_history") or {}
        gen_out = history.get("graph_query_generate") or context.get("last_output") or {}
        plan = gen_out.get("query_plan") or {}
        entities = db.query(Entity).all()
        entity_map = {str(e.id): e for e in entities}
        relations = db.query(EntityRelation).all()
        results = []
        retry_count = 0
        fallback_triggered = False
        empty_reason = None

        def _execute_by_plan(p: Dict[str, Any]) -> List[Dict[str, Any]]:
            if not p:
                return []
            sid = str(p.get("source_entity_id") or "")
            tid = str(p.get("target_entity_id") or "")
            rel_name = str(p.get("relation_name") or "")
            out = []
            for r in relations:
                if str(r.source_entity_id) == sid and str(r.target_entity_id) == tid and (not rel_name or r.relation_name == rel_name):
                    out.append(
                        {
                            "relation_id": str(r.id),
                            "source_entity_name": entity_map.get(str(r.source_entity_id)).entity_name if entity_map.get(str(r.source_entity_id)) else None,
                            "target_entity_name": entity_map.get(str(r.target_entity_id)).entity_name if entity_map.get(str(r.target_entity_id)) else None,
                            "relation_name": r.relation_name,
                            "join_expr": r.join_expr,
                        }
                    )
            return out

        results = _execute_by_plan(plan)
        if not results:
            fallback_triggered = True
            retry_count = 1
            empty_reason = "strict_plan_no_result"
            # 空结果回退：放宽为同名关系或任一有join_expr关系
            fallback = next((r for r in relations if (r.join_expr or "").strip()), None)
            if fallback:
                plan = {
                    "source_entity_id": str(fallback.source_entity_id),
                    "target_entity_id": str(fallback.target_entity_id),
                    "relation_name": fallback.relation_name,
                }
                results = _execute_by_plan(plan)
                if not results:
                    empty_reason = "fallback_no_result"

        return {
            "type": "graph_query_execute",
            "executed_query": plan,
            "results": results,
            "result_count": len(results),
            "fallback_triggered": fallback_triggered,
            "retry_count": retry_count,
            "empty_reason": empty_reason,
        }

    if action == "vector_hybrid_retrieve":
        intent = str(payload.get("intent") or "")
        retrieval_cfg = get_or_init_retrieval_config(db)
        if semantic_status(db).get("embedding_rows", 0) == 0:
            rebuild_semantic_index(db)
        sem_map = score_entities_semantic(db, intent)
        tokens = _extract_match_tokens(intent)
        entities = db.query(Entity).all()
        evidences = []
        for e in entities:
            kw_blob = " ".join([e.entity_name or "", e.entity_code or "", e.entity_en_name or ""]).lower()
            kw_hit = len([t for t in tokens if t in kw_blob])
            keyword_score = min(1.0, kw_hit / 6.0)
            vector_score = float(sem_map.get(str(e.id), 0.0))
            mixed_score = hybrid_score(keyword_score, vector_score, retrieval_cfg)
            evidences.append(
                {
                    "entity_id": str(e.id),
                    "entity_name": e.entity_name,
                    "entity_code": e.entity_code,
                    "keyword_score": keyword_score,
                    "vector_score": vector_score,
                    "mixed_score": mixed_score,
                }
            )
        evidences.sort(key=lambda x: x.get("mixed_score", 0), reverse=True)
        return {
            "type": "vector_hybrid_retrieve",
            "retrieval_meta": {
                "retrieval_mode": retrieval_cfg.get("retrieval_mode"),
                "keyword_weight": retrieval_cfg.get("keyword_weight"),
                "vector_weight": retrieval_cfg.get("vector_weight"),
                "rerank_enabled": retrieval_cfg.get("rerank_enabled"),
            },
            "evidences": evidences[:10],
        }

    if action == "llm_reasoning_answer":
        history = context.get("output_history") or {}
        exec_out = history.get("graph_query_execute") or {}
        retrieve_out = history.get("vector_hybrid_retrieve") or {}
        intent = str(payload.get("intent") or "")
        exec_results = exec_out.get("results") or []
        evidences = retrieve_out.get("evidences") or []
        top_ev = evidences[:3]
        comparisons = []
        nums = _parse_numeric_evidence(intent)
        if len(nums) >= 2:
            a = nums[0]
            b = nums[1]
            comparisons.append(
                {
                    "left": a.get("value"),
                    "operator": ">",
                    "right": b.get("value"),
                    "result": bool((a.get("value") or 0) > (b.get("value") or 0)),
                    "expression": f"{a.get('value')} > {b.get('value')}",
                }
            )
        answer = (
            f"已完成六步分析。需求“{intent}”"
            f"；图查询命中 {len(exec_results)} 条关系；"
            f"向量混合检索选出 {len(top_ev)} 条高相关证据。"
        )
        return {
            "type": "llm_reasoning_answer",
            "answer": answer,
            "explicit_comparisons": comparisons,
            "citations": top_ev,
            "graph_results": exec_results,
        }

    if action == "ontology_compliance_trace_check":
        history = context.get("output_history") or {}
        answer_out = history.get("llm_reasoning_answer") or context.get("last_output") or {}
        exec_out = history.get("graph_query_execute") or {}
        retrieve_out = history.get("vector_hybrid_retrieve") or {}
        citations = retrieve_out.get("evidences") or []
        graph_results = exec_out.get("results") or []
        answer = str(answer_out.get("answer") or "")
        unsupported = []
        fact_checks = []
        if citations:
            names = [str(x.get("entity_name") or "") for x in citations]
            hit_any_entity = any(n and n in answer for n in names)
            fact_checks.append(
                {
                    "check_type": "entity_citation_presence",
                    "passed": bool(hit_any_entity),
                    "evidence": names[:5],
                }
            )
            if names and not hit_any_entity:
                unsupported.append("答案未引用检索证据中的实体名称")

        # 关系事实一致性：答案中关系名必须来自Step3执行结果
        relation_names = [str(x.get("relation_name") or "") for x in graph_results if x.get("relation_name")]
        if relation_names:
            rel_hit = any(rn and rn in answer for rn in relation_names)
            fact_checks.append(
                {
                    "check_type": "relation_fact_consistency",
                    "passed": bool(rel_hit),
                    "evidence": relation_names[:5],
                }
            )
            if not rel_hit:
                unsupported.append("答案未体现图查询返回的关系事实")

        # 数值一致性：比较式中的数字必须与答案文本中数字一致出现
        comparisons = answer_out.get("explicit_comparisons") or []
        answer_nums = [x.get("value") for x in _parse_numeric_evidence(answer)]
        for idx, c in enumerate(comparisons):
            left = _safe_float(c.get("left"))
            right = _safe_float(c.get("right"))
            in_answer = False
            if left is not None and right is not None:
                in_answer = any(abs(float(x) - float(left)) < 1e-6 for x in answer_nums) and any(
                    abs(float(x) - float(right)) < 1e-6 for x in answer_nums
                )
            fact_checks.append(
                {
                    "check_type": "numeric_consistency",
                    "index": idx,
                    "expression": c.get("expression"),
                    "passed": bool(in_answer),
                    "evidence": {"answer_nums": answer_nums[:8]},
                }
            )
            if not in_answer:
                unsupported.append(f"比较式数字未在答案中显式体现: {c.get('expression')}")

        pass_count = len([x for x in fact_checks if x.get("passed")])
        total_count = len(fact_checks)
        pass_rate = (pass_count / total_count) if total_count > 0 else (1.0 if not unsupported else 0.5)
        return {
            "type": "ontology_compliance_trace_check",
            "final_answer": answer,
            "fact_consistency_pass_rate": pass_rate,
            "fact_checks": fact_checks,
            "unsupported_claims": unsupported,
            "citations": citations[:5],
            "final_passed": pass_rate >= 0.8,
        }

    kind = (skill.skill_kind or "").lower()
    if kind == "natural_language":
        desc = (skill.skill_content or "").strip()
        return {
            "type": "natural_language",
            "summary": desc or "自然语言技能已执行",
            "input": payload,
            "context": {"skill_code": skill.skill_code, "version": skill.version},
        }

    if kind == "descriptor":
        descriptor = skill.skill_descriptor or {}
        return {
            "type": "descriptor",
            "descriptor": descriptor,
            "input": payload,
        }

    if kind == "python":
        code = (skill.skill_content or "").strip()
        if not code:
            raise HTTPException(status_code=400, detail=f"Python技能缺少代码: {skill.skill_code}")
        safe_globals = {
            "__builtins__": {
                "len": len,
                "min": min,
                "max": max,
                "sum": sum,
                "str": str,
                "int": int,
                "float": float,
                "bool": bool,
                "dict": dict,
                "list": list,
                "print": print,
                "range": range,
                "enumerate": enumerate,
                "json": json,
            }
        }
        local_vars: Dict[str, Any] = {}
        exec(code, safe_globals, local_vars)
        if "run" in local_vars and callable(local_vars["run"]):
            out = local_vars["run"](payload, context)
        else:
            out = local_vars.get("output")
        return {"type": "python", "output": out}

    raise HTTPException(status_code=400, detail=f"暂不支持的技能调用: {skill.skill_code}")


def _pick_script_assistant_llm(db: Session) -> Optional[LLMConnectionConfig]:
    planner = get_active_planner_config(db)
    conns = db.query(LLMConnectionConfig).all()
    if planner and planner.llm_connection_id:
        hit = next((c for c in conns if str(c.id) == str(planner.llm_connection_id) and c.enabled), None)
        if hit:
            return hit
    # 兜底：优先豆包，再取任一可用连接
    doubao = next((c for c in conns if c.enabled and (c.provider or "").lower() == "volcengine_doubao"), None)
    if doubao:
        return doubao
    return next((c for c in conns if c.enabled), None)
