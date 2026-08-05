"""实体名 / 属性 向量化服务

两个独立 Qdrant collection:
  - entity_embeddings    ← kg_entities.entity_name
  - attribute_embeddings ← kg_entities.properties_schema 提炼

设计要点:
  - 复用 semantic_retrieval.embed_texts 做 embedding
  - 复用 tupu_qdrant_client.TupuQdrantClient 做 Qdrant 读写 (HTTP)
  - payload 结构与 skill_injections 查询端对齐
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ENTITY_COLLECTION = "entity_embeddings"
ATTRIBUTE_COLLECTION = "attribute_embeddings"


def _get_client():
    from app.services.tupu_qdrant_client import TupuQdrantClient
    return TupuQdrantClient()


def _get_vector_size(db: Session) -> int:
    """探测向量维度（用一句短文本试跑一次 embedding）"""
    from app.services.semantic_retrieval import embed_texts
    vec = embed_texts(db, ["维度探测"])
    return len(vec[0]) if vec and vec[0] else 1024


def _ensure_collection(client, collection: str, vector_size: int):
    info = client.collection_info(collection)
    if info is None:
        client.ensure_collection(collection, vector_size=vector_size, distance="Cosine")


def sync_entity_vectors(db: Session, *, force: bool = False) -> Dict[str, Any]:
    """实体名向量化 → entity_embeddings collection"""
    started_at = time.time()
    from app.models.base import Concept, Entity

    try:
        client = _get_client()
        if not client.healthcheck():
            return {"ok": False, "error": "qdrant_unavailable"}
    except Exception as e:
        return {"ok": False, "error": f"qdrant_client_error: {e}"}

    vector_size = _get_vector_size(db)
    if force:
        client.delete_collection(ENTITY_COLLECTION)
    _ensure_collection(client, ENTITY_COLLECTION, vector_size)

    concepts = db.query(Concept).all()
    concept_dict = {str(c.id): c for c in concepts}
    level_map = {1: "L1", 2: "L2", 3: "L3", 4: "L4"}

    entities = db.query(Entity).all()
    texts: List[str] = []
    payloads: List[Dict[str, Any]] = []
    for e in entities:
        concept = concept_dict.get(str(e.concept_id))
        if not concept:
            continue
        parent_lvl = level_map.get(concept.level, "")
        if parent_lvl == "L2":
            ent_lvl, ct = "L2X", "MD"
            l1_name, l2_name = concept.name, concept.name
        elif parent_lvl == "L4":
            ent_lvl, ct = "L4X", "BZ"
            l1_name, l2_name = "", concept.name
        else:
            continue
        text = e.entity_name or e.entity_code or ""
        if not text:
            continue
        texts.append(text)
        payloads.append({
            "entity_id": str(e.id),
            "entity_code": e.entity_code or "",
            "entity_name": e.entity_name or "",
            "entity_en_name": e.entity_en_name or "",
            "level": ent_lvl,
            "chain_type": ct,
            "l1": l1_name or "",
            "l2": l2_name or "",
            "is_main_table": bool(e.is_main_table),
            "data_layer": e.data_layer or "",
        })

    if not texts:
        return {"ok": True, "synced": 0, "note": "no_entities"}

    from app.services.semantic_retrieval import embed_texts
    emb_batch = 32
    vectors = []
    for i in range(0, len(texts), emb_batch):
        vectors.extend(embed_texts(db, texts[i:i + emb_batch]))
    if not vectors or len(vectors) != len(texts):
        return {"ok": False, "error": "embedding_mismatch"}

    points = []
    for i, (vec, payload) in enumerate(zip(vectors, payloads)):
        points.append({
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, payload["entity_code"] or str(i))),
            "vector": [float(x) for x in vec],
            "payload": payload,
        })

    batch_size = 64
    for i in range(0, len(points), batch_size):
        client.upsert_points(ENTITY_COLLECTION, points[i:i + batch_size])

    return {
        "ok": True,
        "synced": len(points),
        "vector_size": vector_size,
        "collection": ENTITY_COLLECTION,
        "took_ms": int((time.time() - started_at) * 1000),
    }


def sync_attribute_vectors(db: Session, *, force: bool = False) -> Dict[str, Any]:
    """属性向量化 → attribute_embeddings collection"""
    started_at = time.time()
    from app.models.base import Concept, Entity

    try:
        client = _get_client()
        if not client.healthcheck():
            return {"ok": False, "error": "qdrant_unavailable"}
    except Exception as e:
        return {"ok": False, "error": f"qdrant_client_error: {e}"}

    vector_size = _get_vector_size(db)
    if force:
        client.delete_collection(ATTRIBUTE_COLLECTION)
    _ensure_collection(client, ATTRIBUTE_COLLECTION, vector_size)

    concepts = db.query(Concept).all()
    concept_dict = {str(c.id): c for c in concepts}

    entities = db.query(Entity).all()
    texts: List[str] = []
    payloads: List[Dict[str, Any]] = []
    for e in entities:
        concept = concept_dict.get(str(e.concept_id))
        if not concept:
            continue
        props = e.properties_schema if isinstance(e.properties_schema, list) else []
        for p in props:
            if not isinstance(p, dict):
                continue
            attr_name = str(
                p.get("cnName") or p.get("label") or p.get("display_name")
                or p.get("name_zh") or p.get("attribute_name") or p.get("name") or ""
            ).strip()
            if not attr_name:
                continue
            attr_en = str(
                p.get("name") or p.get("field_name") or p.get("attribute_en_name")
                or p.get("attr_code") or ""
            ).strip()
            texts.append(attr_name)
            payloads.append({
                "attribute_id": str(p.get("id") or p.get("attribute_id") or ""),
                "attribute_name": attr_name,
                "attribute_en_name": attr_en,
                "attribute_code": attr_en,
                "entity_id": str(e.id),
                "entity_code": e.entity_code or "",
                "entity_name": e.entity_name or "",
                "entity_en_name": e.entity_en_name or "",
                "data_type": str(p.get("dataType") or p.get("data_type") or ""),
            })

    if not texts:
        return {"ok": True, "synced": 0, "note": "no_attributes"}

    from app.services.semantic_retrieval import embed_texts
    vectors = []
    emb_batch = 32
    for i in range(0, len(texts), emb_batch):
        vectors.extend(embed_texts(db, texts[i:i + emb_batch]))
    if not vectors or len(vectors) != len(texts):
        return {"ok": False, "error": "embedding_mismatch"}

    points = []
    for i, (vec, payload) in enumerate(zip(vectors, payloads)):
        uid = f"{payload['entity_code']}:{payload['attribute_code'] or i}"
        points.append({
            "id": str(uuid.uuid5(uuid.NAMESPACE_URL, uid)),
            "vector": [float(x) for x in vec],
            "payload": payload,
        })

    batch_size = 64
    for i in range(0, len(points), batch_size):
        client.upsert_points(ATTRIBUTE_COLLECTION, points[i:i + batch_size])

    return {
        "ok": True,
        "synced": len(points),
        "vector_size": vector_size,
        "collection": ATTRIBUTE_COLLECTION,
        "took_ms": int((time.time() - started_at) * 1000),
    }


def get_entity_vector_stats() -> Dict[str, Any]:
    """实体向量统计"""
    try:
        client = _get_client()
        info = client.collection_info(ENTITY_COLLECTION)
        if info is None:
            return {"exists": False, "count": 0}
        count = client.count_points(ENTITY_COLLECTION)
        return {"exists": True, "count": count}
    except Exception as e:
        return {"exists": False, "count": 0, "error": str(e)}


def get_attribute_vector_stats() -> Dict[str, Any]:
    """属性向量统计"""
    try:
        client = _get_client()
        info = client.collection_info(ATTRIBUTE_COLLECTION)
        if info is None:
            return {"exists": False, "count": 0}
        count = client.count_points(ATTRIBUTE_COLLECTION)
        return {"exists": True, "count": count}
    except Exception as e:
        return {"exists": False, "count": 0, "error": str(e)}


def search_entity_vectors(query: str, top_k: int = 15, db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """实体向量检索（供 skill_injections 注入）"""
    if not query:
        return []
    try:
        client = _get_client()
        info = client.collection_info(ENTITY_COLLECTION)
        if info is None:
            return []
        if db is None:
            from app.core.database import SessionLocal
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        try:
            from app.services.semantic_retrieval import embed_texts
            vectors = embed_texts(db, [query])
            if not vectors or not vectors[0]:
                return []
            hits = client.search_points(ENTITY_COLLECTION, vectors[0], top=top_k, with_payload=True)
            out = []
            for h in hits:
                p = (h.get("payload") or {}) if isinstance(h, dict) else getattr(h, "payload", {}) or {}
                score = float((h.get("score") if isinstance(h, dict) else getattr(h, "score", None)) or 0.0)
                out.append({
                    "code": p.get("entity_code") or "",
                    "name": p.get("entity_name") or "",
                    "level": p.get("level") or "",
                    "chain_type": p.get("chain_type") or "",
                    "entity_id": p.get("entity_id") or "",
                    "is_main_table": p.get("is_main_table", False),
                    "score": score,
                })
            return out
        finally:
            if should_close:
                db.close()
    except Exception as e:
        logger.warning("[entity_attr_vector] search_entity_vectors failed: %s", e)
        return []


def search_attribute_vectors(query: str, top_k: int = 15, db: Optional[Session] = None) -> List[Dict[str, Any]]:
    """属性向量检索（供 skill_injections 注入）"""
    if not query:
        return []
    try:
        client = _get_client()
        info = client.collection_info(ATTRIBUTE_COLLECTION)
        if info is None:
            return []
        if db is None:
            from app.core.database import SessionLocal
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
        try:
            from app.services.semantic_retrieval import embed_texts
            vectors = embed_texts(db, [query])
            if not vectors or not vectors[0]:
                return []
            hits = client.search_points(ATTRIBUTE_COLLECTION, vectors[0], top=top_k, with_payload=True)
            out = []
            for h in hits:
                p = (h.get("payload") or {}) if isinstance(h, dict) else getattr(h, "payload", {}) or {}
                score = float((h.get("score") if isinstance(h, dict) else getattr(h, "score", None)) or 0.0)
                out.append({
                    "entity_code": p.get("entity_code") or "",
                    "entity_name": p.get("entity_name") or "",
                    "attribute_code": p.get("attribute_code") or p.get("attribute_en_name") or "",
                    "attribute_name": p.get("attribute_name") or "",
                    "data_type": p.get("data_type") or "",
                    "entity_id": p.get("entity_id") or "",
                    "score": score,
                })
            return out
        finally:
            if should_close:
                db.close()
    except Exception as e:
        logger.warning("[entity_attr_vector] search_attribute_vectors failed: %s", e)
        return []


__all__ = [
    "ENTITY_COLLECTION",
    "ATTRIBUTE_COLLECTION",
    "sync_entity_vectors",
    "sync_attribute_vectors",
    "get_entity_vector_stats",
    "get_attribute_vector_stats",
    "search_entity_vectors",
    "search_attribute_vectors",
]
