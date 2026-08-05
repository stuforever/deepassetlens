from __future__ import annotations

import logging
import json
import time
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.base import Entity, SemanticEmbedding, StandardSemanticTerm
from app.services.tupu_qdrant_client import (
    QdrantClientError,
    TupuQdrantClient,
)

logger = logging.getLogger(__name__)

QDRANT_COLLECTION_STANDARD_TERMS = "tupu_standard_terms"

def get_standard_semantic_collection(model_name: Optional[str] = None) -> str:
    name = (model_name or "bge-large-zh-v1.5").strip().lower()
    safe = "".join(ch if ch.isalnum() else "_" for ch in name).strip("_")
    if safe in ("", "bge_large_zh_v1_5"):
        return QDRANT_COLLECTION_STANDARD_TERMS
    return f"{QDRANT_COLLECTION_STANDARD_TERMS}_{safe}"


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _l2_normalize(vec: List[float]) -> List[float]:
    norm = sum(float(x) * float(x) for x in vec) ** 0.5
    if norm <= 0:
        return vec
    return [float(x) / norm for x in vec]


def _norm_uuid(val: Any) -> Optional[str]:
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None
    if len(s) == 32:
        s = f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
    return s


def _entity_context(db: Session) -> tuple[Dict[str, Entity], Dict[str, Optional[str]], Dict[str, Dict[str, str]]]:
    entities_map = {str(e.id): e for e in db.query(Entity).all()}
    entity_id_to_en_name: Dict[str, Optional[str]] = {}
    entity_id_to_field_map: Dict[str, Dict[str, str]] = {}
    for e in entities_map.values():
        entity_id_to_en_name[str(e.id)] = e.entity_en_name or e.entity_code
        field_map: Dict[str, str] = {}
        props = e.properties_schema if isinstance(e.properties_schema, list) else []
        for p in props:
            if not isinstance(p, dict):
                continue
            cn = p.get("cnName") or p.get("label") or ""
            en = p.get("name") or ""
            if cn and en:
                field_map[cn] = en
        entity_id_to_field_map[str(e.id)] = field_map
    return entities_map, entity_id_to_en_name, entity_id_to_field_map


def build_standard_semantic_qdrant_point(
    t: StandardSemanticTerm,
    vec: List[float],
    *,
    entities_map: Optional[Dict[str, Entity]] = None,
    entity_id_to_en_name: Optional[Dict[str, Optional[str]]] = None,
    entity_id_to_field_map: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, Any]:
    vec = _l2_normalize([float(x) for x in vec])
    payload = t.text_payload if isinstance(t.text_payload, dict) else {}
    entities_map = entities_map or {}
    entity_id_to_en_name = entity_id_to_en_name or {}
    entity_id_to_field_map = entity_id_to_field_map or {}

    entity_id = None
    if t.term_type == "entity" and t.ontology_ref_type == "entity":
        entity_id = str(t.ontology_ref_id) if t.ontology_ref_id else None
    elif t.term_type == "attribute":
        entity_id = _safe_text(payload.get("entity_id")) or None
    entity_id_norm = _norm_uuid(entity_id)
    e_obj = entities_map.get(entity_id_norm) if entity_id_norm else None
    entity_en_name = payload.get("entity_en_name") or (entity_id_to_en_name.get(entity_id_norm) if entity_id_norm else None)
    attribute_name = (payload.get("attribute_name") if t.term_type == "attribute" else None) or t.term
    field_map = entity_id_to_field_map.get(entity_id_norm or "", {}) if entity_id_norm else {}
    attribute_en_name = field_map.get(attribute_name) or payload.get("attribute_en_name")

    point_payload: Dict[str, Any] = {
        "term_id": _norm_uuid(str(t.id)),
        "term": t.term,
        "term_type": t.term_type,
        "ontology_ref_type": t.ontology_ref_type,
        "doc_type": _safe_text(payload.get("doc_type")) or t.term_type,
        "scene": _safe_text(payload.get("scene")) or None,
        "display_text": _safe_text(payload.get("display_text")) or t.term,
        "vector_dim": len(vec),
        "entity_scope": "concept" if t.ontology_ref_type == "concept" else ("data" if t.ontology_ref_type == "entity" else None),
        "entity_id": entity_id_norm,
        "entity_name": (e_obj.entity_name or e_obj.entity_code if e_obj else payload.get("entity_name")),
        "entity_code": e_obj.entity_code if e_obj else None,
        "entity_en_name": entity_en_name,
        "attribute_id": payload.get("attribute_id") if t.term_type == "attribute" else None,
        "attribute_name": attribute_name if t.term_type == "attribute" else None,
        "attribute_en_name": attribute_en_name if t.term_type == "attribute" else None,
        "attribute_code": (payload.get("attribute_code") or attribute_en_name if t.term_type == "attribute" else None),
        "attribute_category": (payload.get("attribute_category") or "通用属性" if t.term_type == "attribute" else None),
        "search_texts": payload.get("search_texts") or [],
        "model_name": t.model_name,
    }
    return {
        "id": _norm_uuid(str(t.id)),
        "vector": vec,
        "payload": point_payload,
    }


def upsert_standard_semantic_vectors_to_qdrant(
    db: Session,
    terms: List[StandardSemanticTerm],
    vectors: List[List[float]],
    *,
    batch_size: int = 32,           # 默认从 256 降到 32 防 Qdrant 32MB 限制
    max_payload_bytes: int = 24 * 1024 * 1024,  # 24MB 安全阈值
    collection: str = QDRANT_COLLECTION_STANDARD_TERMS,
    recreate_on_dimension_mismatch: bool = False,
) -> Dict[str, Any]:
    started_at = time.time()
    if collection == QDRANT_COLLECTION_STANDARD_TERMS and terms:
        collection = get_standard_semantic_collection(terms[0].model_name)
    client = TupuQdrantClient()
    if not client.healthcheck():
        raise QdrantClientError("qdrant_unavailable")
    sample_vec = next((v for v in vectors if v), None)
    if not sample_vec:
        return {"ok": True, "upserted": 0, "skipped": len(terms), "vector_size": 0, "took_ms": 0}
    vector_size = len(sample_vec)
    try:
        client.ensure_collection(collection, vector_size=vector_size, distance="Cosine", recreate=False)
    except QdrantClientError:
        if not recreate_on_dimension_mismatch:
            raise
        client.ensure_collection(collection, vector_size=vector_size, distance="Cosine", recreate=True)

    entities_map, entity_id_to_en_name, entity_id_to_field_map = _entity_context(db)

    def _flush_if_needed(points, current_bytes, force=False):
        """按数量 + payload 大小拆批写入"""
        if not points:
            return 0, 0
        if force or len(points) >= batch_size or current_bytes >= max_payload_bytes:
            client.upsert_points(collection, points)
            return len(points), 0
        return 0, current_bytes

    points: List[Dict[str, Any]] = []
    batch_bytes = 0
    upserted = 0
    skipped = 0
    for term, vector in zip(terms, vectors):
        if not vector:
            skipped += 1
            continue
        pt = build_standard_semantic_qdrant_point(
            term,
            vector,
            entities_map=entities_map,
            entity_id_to_en_name=entity_id_to_en_name,
            entity_id_to_field_map=entity_id_to_field_map,
        )
        pt_size = len(json.dumps(pt, ensure_ascii=False).encode("utf-8"))
        points.append(pt)
        batch_bytes += pt_size
        flushed, batch_bytes = _flush_if_needed(points, batch_bytes)
        if flushed:
            upserted += flushed
            points.clear()

    # flush 剩余
    if points:
        flushed, _ = _flush_if_needed(points, batch_bytes, force=True)
        upserted += flushed
        points.clear()
    return {
        "ok": True,
        "upserted": upserted,
        "skipped": skipped,
        "vector_size": vector_size,
        "took_ms": int((time.time() - started_at) * 1000),
    }


def sync_standard_semantic_to_qdrant(
    db: Session,
    *,
    force: bool = False,
    batch_size: int = 256,
    collection: str = QDRANT_COLLECTION_STANDARD_TERMS,
) -> Dict[str, Any]:
    started_at = time.time()
    client = TupuQdrantClient()
    if not client.healthcheck():
        return {"ok": False, "error": "qdrant_unavailable"}

    terms = (
        db.query(StandardSemanticTerm)
        .filter(StandardSemanticTerm.vector_status == "ready", StandardSemanticTerm.enabled == True)
        .all()
    )
    term_ids = [str(t.id) for t in terms]
    if not term_ids:
        return {"ok": True, "synced": 0, "total": 0, "skipped": 0, "vector_size": 0, "took_ms": 0}

    info = client.collection_info(collection)
    qdrant_count = client.count_points(collection) if info else 0
    return {
        "ok": True,
        "synced": 0,
        "total": len(term_ids),
        "skipped": len(term_ids),
        "vector_size": 0,
        "qdrant_count": qdrant_count,
        "took_ms": int((time.time() - started_at) * 1000),
        "note": "qdrant_is_primary_revectorize_to_refresh",
    }


def query_standard_semantic_matches_qdrant(
    db: Session,
    query_text: str,
    *,
    top_k: int = 10,
    term_types: Optional[List[str]] = None,
    entity_scope: str = "data",
    collection: str = QDRANT_COLLECTION_STANDARD_TERMS,
) -> List[Dict[str, Any]]:
    from app.services.semantic_retrieval import embed_texts, get_or_init_retrieval_config

    started_at = time.time()
    if collection == QDRANT_COLLECTION_STANDARD_TERMS:
        cfg = get_or_init_retrieval_config(db)
        collection = get_standard_semantic_collection(cfg.get("vector_model_name"))
    client = TupuQdrantClient()
    if not client.healthcheck():
        logger.warning("Qdrant healthcheck failed")
        return []

    qv_list = embed_texts(db, [query_text])
    if not qv_list:
        return []
    qv = _l2_normalize([float(x) for x in qv_list[0]])

    filter_must: List[Dict[str, Any]] = []
    if term_types:
        filter_must.append({"key": "term_type", "match": {"any": list(term_types)}})
    scope = (entity_scope or "data").lower()
    if scope == "concept":
        filter_must.append({"key": "ontology_ref_type", "match": {"value": "concept"}})

    raw = client.search_points(
        collection=collection,
        vector=qv,
        top=int(top_k * 1.5) if top_k < 64 else top_k,
        with_payload=True,
        filter_must=filter_must or None,
    )

    rows: List[Dict[str, Any]] = []
    for hit in raw:
        payload = hit.get("payload") or {}
        if scope == "data":
            term_type = payload.get("term_type")
            ontology_ref_type = payload.get("ontology_ref_type")
            if term_type == "entity" and ontology_ref_type != "entity":
                continue
        sim = float(hit.get("score") or 0.0)
        sim_normalized = (sim + 1) / 2
        substring_bonus = 0.0
        attribute_name = payload.get("attribute_name")
        term = payload.get("term") or ""
        q = (query_text or "").strip()
        if payload.get("term_type") == "attribute" and attribute_name:
            if q == attribute_name or q in attribute_name or attribute_name in q:
                substring_bonus = 0.5
            elif q == term or q in term or term in q:
                substring_bonus = 0.3
            else:
                for text in payload.get("search_texts") or []:
                    s = str(text or "").strip()
                    if s and (q in s or s in q):
                        substring_bonus = max(substring_bonus, 0.2)
        row = {
            "term_id": payload.get("term_id"),
            "term": term,
            "term_type": payload.get("term_type"),
            "doc_type": payload.get("doc_type") or payload.get("term_type"),
            "scene": payload.get("scene"),
            "display_text": payload.get("display_text") or term,
            "score": float(min(sim_normalized + substring_bonus, 1.0)),
            "vector_sim": float(sim_normalized),
            "substring_bonus": substring_bonus,
            "vector_dim": payload.get("vector_dim"),
            "entity_scope": payload.get("entity_scope"),
            "entity_id": payload.get("entity_id"),
            "entity_name": payload.get("entity_name"),
            "entity_code": payload.get("entity_code"),
            "entity_en_name": payload.get("entity_en_name"),
            "attribute_id": payload.get("attribute_id"),
            "attribute_name": payload.get("attribute_name"),
            "attribute_en_name": payload.get("attribute_en_name"),
            "attribute_code": payload.get("attribute_code"),
            "attribute_category": payload.get("attribute_category"),
            "text_payload": payload,
        }
        rows.append(row)
    rows.sort(key=lambda r: -r["score"])
    rows = rows[:top_k]
    elapsed_ms = int((time.time() - started_at) * 1000)
    logger.info(
        "qdrant_search collection=%s top_k=%d returned=%d took=%dms",
        collection,
        top_k,
        len(rows),
        elapsed_ms,
    )
    return rows


__all__ = [
    "QDRANT_COLLECTION_STANDARD_TERMS",
    "build_standard_semantic_qdrant_point",
    "upsert_standard_semantic_vectors_to_qdrant",
    "sync_standard_semantic_to_qdrant",
    "query_standard_semantic_matches_qdrant",
]




