"""技能沙箱全局注入工厂

为 _invoke_skill 本地直连模式提供：
  - build_llm_client()                  → 兼容 openai-compatible chat 的 LLM 客户端
  - build_vector_recall_fn()            → Qdrant entity_embeddings 向量召回
  - build_attribute_vector_search_fn()  → Qdrant attribute_embeddings 向量检索
  - build_fetch_all_l1_l3()             → Neo4j 查全量 L1/L3
  - build_fetch_l2_l4_by_parent()       → Neo4j 查 L2/L4 子分类
  - build_fetch_entities_by_parent()    → Neo4j 查 L2X/L4X 实体
  - build_fetch_entity_attributes()     → MySQL 查实体属性(properties_schema)

设计原则：
  - 委托 graph_query_neo4j / entity_attr_vector_service，不重复逻辑
  - 依赖缺失时返回 None（技能走兜底分支，不崩）
"""
from __future__ import annotations

import os
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


def build_llm_client() -> Optional[Any]:
    """[DEPRECATED] 构造旧版 LLM 客户端。请用 build_llm_chat_model() 替代。

    保留是因为 legacy 图（boss_router/agent_run_runtime/query_entity_service）还在引用。
    问数流程和 DeepAgent 已改用 build_llm_chat_model()（langchain ChatOpenAI）。
    """
    base_url = api_key = model = None

    # 1) 优先从数据库读默认 chat LLM 连接
    try:
        from app.core.database import SessionLocal
        from app.models.base import LLMConnectionConfig
        _db = SessionLocal()
        try:
            conn = (
                _db.query(LLMConnectionConfig)
                .filter(LLMConnectionConfig.enabled == True)
                .filter(LLMConnectionConfig.capability == "chat")
                .order_by(LLMConnectionConfig.is_default.desc())
                .first()
            )
            if conn:
                base_url = conn.base_url or conn.api_base
                api_key = conn.api_key
                model = conn.model_name
                logger.info(f"[skill_injections] LLM 从数据库加载: model={model}, base_url={base_url}")
        finally:
            _db.close()
    except Exception as e:
        logger.debug(f"[skill_injections] 从数据库读 LLM 失败: {e}")

    # 2) fallback 环境变量
    if not base_url:
        base_url = os.getenv("TUPU_LLM_BASE_URL") or os.getenv("LLM_BASE_URL")
    if not api_key:
        api_key = os.getenv("TUPU_LLM_API_KEY") or os.getenv("LLM_API_KEY")
    if not model:
        model = os.getenv("TUPU_LLM_MODEL") or os.getenv("LLM_MODEL", "gpt-4o-mini")

    if not base_url or not api_key:
        logger.info("[skill_injections] LLM 未配置，技能走兜底")
        return None

    try:
        from langchain_openai import ChatOpenAI
    except ImportError:
        logger.warning("[skill_injections] langchain-openai 未安装")
        return None

    timeout = int(os.getenv("TUPU_LLM_TIMEOUT", "120"))
    chat = ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url.rstrip("/"),
        temperature=0.1,
        timeout=timeout,
    )

    class _LLMClient:
        def __init__(self, chat_model: ChatOpenAI):
            self._chat = chat_model

        def call_openai_compatible_chat(self, system_prompt: str, user_prompt: str,
                                         temperature: float = 0.1) -> str:
            from langchain_core.messages import SystemMessage, HumanMessage
            self._chat.temperature = temperature
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt or ""),
            ]
            resp = self._chat.invoke(messages)
            return resp.content if isinstance(resp.content, str) else str(resp.content)

        def stream_openai_compatible_chat(self, system_prompt: str, user_prompt: str,
                                          temperature: float = 0.1):
            """langchain ChatOpenAI.stream() 生成器，逐 token yield（供流式推理展示）。"""
            from langchain_core.messages import SystemMessage, HumanMessage
            self._chat.temperature = temperature
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt or ""),
            ]
            for chunk in self._chat.stream(messages):
                token = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                if token:
                    yield token

        def __call__(self, system_prompt: str, user_prompt: str) -> str:
            return self.call_openai_compatible_chat(system_prompt, user_prompt, 0.1)

    return _LLMClient(chat)


def build_llm_chat_model() -> Optional[Any]:
    """构造原始 ChatOpenAI 模型（供 .stream() token 级流式使用）。

    统一走 llm_client.get_chat_model（读数据库 timeout_seconds，全局超时一致）。
    保留返回 None 的兜底语义以兼容旧调用方。
    """
    try:
        from app.services.llm_client import get_chat_model
        return get_chat_model(temperature=0.3, streaming=True)
    except Exception as e:
        logger.debug(f"[skill_injections] build_llm_chat_model 失败: {e}")
        return None


def build_vector_recall_fn() -> Optional[Callable[[str, int], List[Dict[str, Any]]]]:
    """构造实体向量召回函数（Qdrant entity_embeddings collection）。

    返回函数签名：(query: str, top_k: int = 8) -> List[Dict]
    每项格式：{code, name, level, chain_type, score}
    """
    try:
        from app.services.entity_attr_vector_service import search_entity_vectors
    except ImportError as e:
        logger.info(f"[skill_injections] 实体向量依赖缺失: {e}")
        return None

    def _recall(query: str, top_k: int = 8) -> List[Dict[str, Any]]:
        return search_entity_vectors(query, top_k=top_k)

    return _recall


def build_attribute_vector_search_fn() -> Optional[Callable]:
    """构造属性向量检索函数（Qdrant attribute_embeddings collection）。

    返回函数签名：(query: str, top_k: int = 10, index: str = "all_fields") -> List[Dict]
    每项格式：{entity_code, entity_name, attribute_code, attribute_name, score}
    """
    try:
        from app.services.entity_attr_vector_service import search_attribute_vectors
    except ImportError as e:
        logger.info(f"[skill_injections] 属性向量依赖缺失: {e}")
        return None

    def _search(query: str, top_k: int = 10, index: str = "all_fields") -> List[Dict[str, Any]]:
        return search_attribute_vectors(query, top_k=top_k)

    return _search


def build_fetch_all_l1_l3() -> Optional[Callable[[], List[Dict[str, Any]]]]:
    """从 MySQL 查全量 L1/L3 列表（kg_concepts 表 level 1/3）。"""
    try:
        from app.models.base import Concept, SessionLocal
    except ImportError as e:
        logger.info(f"[skill_injections] MySQL/ORM 缺失: {e}")
        return None

    def _fetch() -> List[Dict[str, Any]]:
        try:
            db = SessionLocal()
            try:
                rows = db.query(Concept).filter(Concept.level.in_([1, 3])).order_by(Concept.level, Concept.sort_order).all()
                out = []
                for c in rows:
                    lvl = "L1" if c.level == 1 else "L3"
                    ct = "MD" if c.level == 1 else "BZ"
                    out.append({
                        "code": f"{lvl}-{str(c.id)}",
                        "name": c.name or "",
                        "level": lvl,
                        "chain_type": ct,
                        "concept_id": str(c.id),
                    })
                return out
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[skill_injections] 查 L1/L3 失败: {e}")
            return []

    return _fetch


def build_fetch_l2_l4_by_parent() -> Optional[Callable[[str], List[Dict[str, Any]]]]:
    """从 MySQL 查 L2/L4 子分类（kg_concepts 表，按 parent concept_id）。"""
    try:
        from app.models.base import Concept, SessionLocal
    except ImportError as e:
        logger.info(f"[skill_injections] MySQL/ORM 缺失: {e}")
        return None

    def _fetch(parent_code: str) -> List[Dict[str, Any]]:
        if not parent_code:
            return []
        parent_id = parent_code.split("-", 1)[-1] if "-" in parent_code else parent_code
        try:
            db = SessionLocal()
            try:
                rows = db.query(Concept).filter(Concept.parent_id == parent_id).order_by(Concept.sort_order).all()
                out = []
                for c in rows:
                    if c.level not in (2, 4):
                        continue
                    lvl = "L2" if c.level == 2 else "L4"
                    ct = "MD" if c.level == 2 else "BZ"
                    out.append({
                        "code": f"{lvl}-{str(c.id)}",
                        "name": c.name or "",
                        "level": lvl,
                        "chain_type": ct,
                        "concept_id": str(c.id),
                    })
                return out
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[skill_injections] 查 L2/L4 失败: {e}")
            return []

    return _fetch


def build_fetch_entities_by_parent() -> Optional[Callable[[str], List[Dict[str, Any]]]]:
    """从 MySQL 查 L2X/L4X 实体（kg_entities 表，按 concept_id）。"""
    try:
        from app.models.base import Entity, SessionLocal
    except ImportError as e:
        logger.info(f"[skill_injections] MySQL/ORM 缺失: {e}")
        return None

    def _fetch(parent_code: str) -> List[Dict[str, Any]]:
        if not parent_code:
            return []
        parent_id = parent_code.split("-", 1)[-1] if "-" in parent_code else parent_code
        try:
            db = SessionLocal()
            try:
                rows = db.query(Entity).filter(Entity.concept_id == parent_id).order_by(Entity.sort_order).all()
                out = []
                for e in rows:
                    out.append({
                        "code": e.entity_code or "",
                        "entity_code": e.entity_code or "",
                        "name": e.entity_name or "",
                        "entity_name": e.entity_name or "",
                        "level": "L2X",
                        "chain_type": "MD",
                        "entity_id": str(e.id),
                        "entity_en_name": e.entity_en_name or "",
                        "is_main_table": bool(e.is_main_table),
                        "data_layer": e.data_layer or "",
                    })
                return out
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[skill_injections] 查 L2X/L4X 失败: {e}")
            return []

    return _fetch


def build_fetch_l1_l2_tree() -> Optional[Callable[[], Dict[str, Any]]]:
    """构造 L1-L2 层级树查询函数（kg_concepts 表，level=1/2）。

    返回函数签名：() -> Dict
    结构：{l1_list: [{l1_id, l1_name, l2_list: [{l2_id, l2_name}]}]}
    """
    try:
        from app.models.base import Concept, SessionLocal
    except ImportError as e:
        logger.info(f"[skill_injections] MySQL/ORM 缺失: {e}")
        return None

    def _fetch() -> Dict[str, Any]:
        try:
            db = SessionLocal()
            try:
                l1_rows = db.query(Concept).filter(Concept.level == 1).order_by(Concept.sort_order).all()
                l2_rows = db.query(Concept).filter(Concept.level == 2).order_by(Concept.sort_order).all()
                l1_list = []
                for l1 in l1_rows:
                    l2_list = [
                        {"l2_id": str(l2.id), "l2_name": l2.name or ""}
                        for l2 in l2_rows if str(l2.parent_id) == str(l1.id)
                    ]
                    l1_list.append({
                        "l1_id": str(l1.id),
                        "l1_name": l1.name or "",
                        "l2_list": l2_list,
                    })
                return {"l1_list": l1_list}
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[skill_injections] 查 L1-L2 树失败: {e}")
            return {"l1_list": []}

    return _fetch


def build_fetch_subgraph_by_l2() -> Optional[Callable[[str], Dict[str, Any]]]:
    """构造以 L2 为起点的子图查询函数。

    子图包含：
      - L2 本身
      - L2X 实体（Entity.concept_id = L2.id）+ 每个实体的全部属性
      - 跨链关系（ConceptRelation source/target = L2.id）→ L3/L4 → L4X 实体 + 属性

    返回函数签名：(l2_id: str) -> Dict
    """
    try:
        from app.models.base import Concept, ConceptRelation, Entity, SessionLocal
    except ImportError as e:
        logger.info(f"[skill_injections] MySQL/ORM 缺失: {e}")
        return None

    def _parse_attrs(props) -> List[Dict[str, Any]]:
        if not isinstance(props, list):
            return []
        out = []
        for p in props:
            if not isinstance(p, dict):
                continue
            attr_name = str(
                p.get("cnName") or p.get("label") or p.get("display_name")
                or p.get("name_zh") or p.get("attribute_name") or p.get("name") or ""
            ).strip()
            if not attr_name:
                continue
            out.append({
                "attribute_code": str(
                    p.get("name") or p.get("field_name")
                    or p.get("attribute_en_name") or p.get("attr_code") or ""
                ),
                "attribute_name": attr_name,
                "data_type": str(p.get("dataType") or p.get("data_type") or ""),
            })
        return out

    def _fetch(l2_id: str) -> Dict[str, Any]:
        if not l2_id:
            return {"l2_name": "", "l2x_entities": [], "cross_chain": []}
        try:
            db = SessionLocal()
            try:
                l2 = db.query(Concept).filter(Concept.id == l2_id).first()
                l2_name = l2.name if l2 else ""

                # L2X 实体 + 属性
                l2x_rows = db.query(Entity).filter(Entity.concept_id == l2_id).order_by(Entity.is_main_table.desc()).all()
                l2x_entities = []
                for e in l2x_rows:
                    l2x_entities.append({
                        "entity_code": e.entity_code or "",
                        "entity_name": e.entity_name or "",
                        "entity_en_name": e.entity_en_name or "",
                        "is_main_table": bool(e.is_main_table),
                        "attributes": _parse_attrs(e.properties_schema),
                    })

                # 跨链关系 → L3/L4 → L4X
                rels = db.query(ConceptRelation).filter(
                    (ConceptRelation.source_concept_id == l2_id)
                    | (ConceptRelation.target_concept_id == l2_id)
                ).all()
                cross_chain = []
                seen_concept_ids = set()
                for r in rels:
                    other_id = r.target_concept_id if r.source_concept_id == l2_id else r.source_concept_id
                    if other_id in seen_concept_ids:
                        continue
                    seen_concept_ids.add(other_id)
                    other = db.query(Concept).filter(Concept.id == other_id).first()
                    if not other or other.level not in (3, 4):
                        continue
                    l4x_rows = db.query(Entity).filter(Entity.concept_id == other_id).all()
                    l4x_entities = []
                    for e in l4x_rows:
                        l4x_entities.append({
                            "entity_code": e.entity_code or "",
                            "entity_name": e.entity_name or "",
                            "entity_en_name": e.entity_en_name or "",
                            "is_main_table": bool(e.is_main_table),
                            "attributes": _parse_attrs(e.properties_schema),
                        })
                    cross_chain.append({
                        "level": f"L{other.level}",
                        "name": other.name or "",
                        "relation_type": r.relation_type or "",
                        "l4x_entities": l4x_entities,
                    })

                return {
                    "l2_id": l2_id,
                    "l2_name": l2_name,
                    "l2x_entities": l2x_entities,
                    "cross_chain": cross_chain,
                }
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[skill_injections] 查 L2 子图失败: {e}")
            return {"l2_name": "", "l2x_entities": [], "cross_chain": []}

    return _fetch


def build_fetch_entity_attributes() -> Optional[Callable[[str], List[Dict[str, Any]]]]:
    """构造从 MySQL 查实体属性的函数（按 entity_code，读 properties_schema）。"""
    try:
        from app.models.base import Entity, SessionLocal
    except ImportError as e:
        logger.info(f"[skill_injections] MySQL/ORM 缺失: {e}")
        return None

    def _fetch(entity_code: str) -> List[Dict[str, Any]]:
        if not entity_code:
            return []
        try:
            db = SessionLocal()
            try:
                ent = db.query(Entity).filter(Entity.entity_code == entity_code).first()
                if not ent:
                    return []
                props = ent.properties_schema if isinstance(ent.properties_schema, list) else []
                out = []
                for p in props:
                    if not isinstance(p, dict):
                        continue
                    attr_name = str(
                        p.get("cnName") or p.get("label") or p.get("display_name")
                        or p.get("name_zh") or p.get("attribute_name") or p.get("name") or ""
                    ).strip()
                    if not attr_name:
                        continue
                    out.append({
                        "attribute_code": str(
                            p.get("name") or p.get("field_name")
                            or p.get("attribute_en_name") or p.get("attr_code") or ""
                        ),
                        "attribute_name": attr_name,
                        "attribute_type_cn": str(p.get("dataType") or p.get("data_type") or ""),
                        "attribute_category": str(p.get("category") or ""),
                    })
                return out
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[skill_injections] 查实体属性失败: {e}")
            return []

    return _fetch


def build_search_knowledge() -> Optional[Callable[[str], List[Dict[str, Any]]]]:
    """构造知识图谱关键词检索函数（知识问答用）。

    从 kg_concepts（L1-L4）+ kg_entities 两张表按名称/描述做 LIKE 检索，
    返回 [{type, name, level, description, attributes}]。
    """
    try:
        from app.models.base import Concept, Entity, SessionLocal
    except ImportError as e:
        logger.info(f"[skill_injections] MySQL/ORM 缺失: {e}")
        return None

    def _extract_keywords(query: str) -> List[str]:
        """从中文问句提取关键词（去停用词子串）"""
        if not query:
            return []
        import re as _re
        stop_words = ["有哪些", "有什么", "是什么", "什么是", "请问", "一下", "告诉我",
                      "子类", "分类", "类别", "类型", "包括", "包含", "哪些", "什么",
                      "怎么", "怎样", "如何", "都", "的", "了", "是", "有", "在",
                      "和", "与", "及", "或", "吗", "呢", "请", "帮", "帮我"]
        cleaned = _re.sub(r"[，。？?！!、,；;：:]+", " ", query).strip()
        for sw in stop_words:
            cleaned = cleaned.replace(sw, " ")
        tokens = [t for t in cleaned.split() if len(t) >= 1]
        if not tokens:
            cleaned2 = _re.sub(r"[，。？?！!、,；;：:\s]+", "", query).strip()
            if cleaned2:
                tokens = [cleaned2]
        return tokens

    def _search(query: str) -> List[Dict[str, Any]]:
        if not query or len(query.strip()) < 1:
            return []
        keywords = _extract_keywords(query)
        if not keywords:
            return []
        out: List[Dict[str, Any]] = []
        seen_ids = set()
        try:
            db = SessionLocal()
            try:
                from sqlalchemy import or_
                # 构建多关键词 OR 检索
                for kw in keywords:
                    kw_pat = f"%{kw}%"
                    # 1. 检索 concepts
                    concepts = (
                        db.query(Concept)
                        .filter(
                            or_(
                                Concept.name.like(kw_pat),
                                Concept.description.like(kw_pat),
                            )
                        )
                        .order_by(Concept.level.asc())
                        .limit(15)
                        .all()
                    )
                    for c in concepts:
                        if c.id in seen_ids:
                            continue
                        seen_ids.add(c.id)
                        out.append({
                            "type": "concept",
                            "name": c.name or "",
                            "level": f"L{c.level}" if c.level else "",
                            "description": (c.description or "")[:300],
                            "attributes": [],
                        })

                    # 2. 检索 entities
                    entities = (
                        db.query(Entity)
                        .filter(
                            or_(
                                Entity.entity_name.like(kw_pat),
                                Entity.entity_code.like(kw_pat),
                                Entity.entity_explanation.like(kw_pat),
                            )
                        )
                        .limit(10)
                        .all()
                    )
                    for e in entities:
                        if e.id in seen_ids:
                            continue
                        seen_ids.add(e.id)
                        props = e.properties_schema if isinstance(e.properties_schema, list) else []
                        attrs = []
                        for p in props[:15]:
                            if not isinstance(p, dict):
                                continue
                            aname = str(
                                p.get("cnName") or p.get("label") or p.get("display_name")
                                or p.get("name_zh") or p.get("attribute_name") or p.get("name") or ""
                            ).strip()
                            if aname:
                                attrs.append({"name": aname})
                        out.append({
                            "type": "entity",
                            "name": e.entity_name or e.entity_code or "",
                            "level": "",
                            "description": (e.entity_explanation or e.description or "")[:300],
                            "attributes": attrs,
                        })
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[skill_injections] 知识检索失败: {e}")
            return []
        return out[:25]

    return _search
