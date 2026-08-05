from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
import uuid
import hashlib
import math
import json

from ..models.base import (
    StandardSemanticTerm, SemanticEmbedding, Entity,
    EntityRelation, StandardSemanticVectorTask,
)
from .semantic_retrieval import embed_texts, cosine_similarity, _hash_text


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set()
    rows: List[str] = []
    for item in items:
        text = _safe_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        rows.append(text)
    return rows


def _split_alias_text(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        rows: List[str] = []
        for item in value:
            rows.extend(_split_alias_text(item))
        return rows
    text = _safe_text(value)
    if not text:
        return []
    for sep in ["|", ",", "，", ";", "；", "/", "、", "\n", "\t"]:
        text = text.replace(sep, "|")
    return [item.strip() for item in text.split("|") if item.strip()]


def _extract_property_alias_terms(prop: Dict[str, Any]) -> List[str]:
    alias_terms: List[str] = []
    for key in ["aliases", "alias", "synonyms", "variants", "keywords", "keyword", "explanation", "description"]:
        alias_terms.extend(_split_alias_text(prop.get(key)))
    return _dedupe_keep_order([item for item in alias_terms if len(item) <= 40])


def l2_normalize(vec: List[float]) -> List[float]:
    norm = sum(float(x) * float(x) for x in vec) ** 0.5
    if norm <= 0:
        return vec
    return [float(x) / norm for x in vec]


def _extract_entity_attributes(entities: List[Entity]) -> List[Dict[str, Any]]:
    attrs: List[Dict[str, Any]] = []
    seen = set()
    for e in entities:
        props = e.properties_schema if isinstance(e.properties_schema, list) else []
        for p in props:
            if not isinstance(p, dict):
                continue
            attr_name = str(
                p.get("cnName")
                or p.get("label")
                or p.get("display_name")
                or p.get("name_zh")
                or p.get("attribute_name")
                or p.get("name")
                or ""
            ).strip()
            attr_en_name = str(
                p.get("name")
                or p.get("field_name")
                or p.get("attribute_en_name")
                or p.get("attr_code")
                or ""
            ).strip()
            if not attr_name:
                continue
            uniq = (str(e.id), attr_name, attr_en_name)
            if uniq in seen:
                continue
            seen.add(uniq)
            attrs.append(
                {
                    "attribute_id": p.get("id") or p.get("attribute_id"),
                    "attribute_name": attr_name,
                    "attribute_en_name": attr_en_name,
                    "attribute_code": attr_en_name,
                    "entity_id": str(e.id),
                    "entity_name": e.entity_name or "",
                    "entity_en_name": e.entity_en_name or e.entity_code or "",
                }
            )
    return attrs


def _semantic_term_key(term: str, term_type: str, payload: Optional[Dict[str, Any]] = None) -> tuple[str, str]:
    payload = payload if isinstance(payload, dict) else {}
    if term_type == "attribute":
        doc_id = str(payload.get("doc_id") or "").strip()
        if doc_id:
            return (f"attribute::{doc_id}", term_type)
    return (term, term_type)


def extract_graph_semantic_terms(
    db: Session,
    model_name: str = "bge-large-zh-v1.5",
    reset_existing: bool = False,
    extract_mode: str = "all",  # "all" | "attributes_only" | "entities_only"
) -> Dict[str, Any]:
    extract_mode = (extract_mode or "all").strip().lower()
    if extract_mode not in ("all", "attributes_only", "entities_only"):
        extract_mode = "all"

    entities = db.query(Entity).all()
    attributes = _extract_entity_attributes(entities)
    relations = db.query(EntityRelation).all()

    if reset_existing:
        db.query(SemanticEmbedding).filter(SemanticEmbedding.object_type == "standard_term").delete()
        db.query(StandardSemanticTerm).delete()

    existing_terms = {
        _semantic_term_key(
            t.term,
            t.term_type,
            t.text_payload if isinstance(t.text_payload, dict) else None,
        ): t
        for t in db.query(StandardSemanticTerm).all()
    }
    created = 0
    updated = 0
    removed = 0

    legacy_attribute_terms = [
        t
        for t in db.query(StandardSemanticTerm).filter(
            StandardSemanticTerm.source == "graph_extract",
            StandardSemanticTerm.term_type == "attribute",
        ).all()
        if (not isinstance(t.text_payload, dict)) or (not str((t.text_payload or {}).get("doc_id") or "").strip()) or ("的" in str(t.term or ""))
    ]
    legacy_attr_ids = [str(t.id) for t in legacy_attribute_terms]
    if legacy_attr_ids:
        db.query(SemanticEmbedding).filter(
            SemanticEmbedding.object_type == "standard_term",
            SemanticEmbedding.object_id.in_(legacy_attr_ids),
        ).delete(synchronize_session=False)
        db.query(StandardSemanticTerm).filter(
            StandardSemanticTerm.id.in_(legacy_attr_ids)
        ).delete(synchronize_session=False)
        removed += len(legacy_attr_ids)
        db.flush()
        existing_terms = {
            _semantic_term_key(
                t.term,
                t.term_type,
                t.text_payload if isinstance(t.text_payload, dict) else None,
            ): t
            for t in db.query(StandardSemanticTerm).all()
        }

    if extract_mode == "attributes_only":
        # 仅属性模式下，清理图谱提炼产生的实体/关系词，避免历史数据继续展示为“仍提炼实体/关系”
        stale_terms = db.query(StandardSemanticTerm).filter(
            StandardSemanticTerm.source == "graph_extract",
            StandardSemanticTerm.term_type.in_(["entity", "relation"]),
        ).all()
        stale_ids = [str(t.id) for t in stale_terms]
        if stale_ids:
            db.query(SemanticEmbedding).filter(
                SemanticEmbedding.object_type == "standard_term",
                SemanticEmbedding.object_id.in_(stale_ids),
            ).delete(synchronize_session=False)
            removed = len(stale_ids)
            db.query(StandardSemanticTerm).filter(
                StandardSemanticTerm.id.in_(stale_ids)
            ).delete(synchronize_session=False)
            db.flush()
            existing_terms = {
                _semantic_term_key(
                    t.term,
                    t.term_type,
                    t.text_payload if isinstance(t.text_payload, dict) else None,
                ): t
                for t in db.query(StandardSemanticTerm).all()
            }

    if extract_mode in ("all", "entities_only"):
        for e in entities:
            term_text = e.entity_name or e.entity_code
            if not term_text:
                continue
            key = _semantic_term_key(term_text, "entity")
            ref_type = "entity"
            ref_id = str(e.id)
            payload = {
                "entity_id": str(e.id),
                "entity_name": e.entity_name,
                "entity_en_name": e.entity_en_name or e.entity_code,
                "entity_code": e.entity_code,
            }
            existing = existing_terms.get(key)
            if existing:
                existing.ontology_ref_type = ref_type
                existing.ontology_ref_id = ref_id
                existing.text_payload = payload
                updated += 1
            else:
                t = StandardSemanticTerm(
                    term=term_text,
                    term_type="entity",
                    source="graph_extract",
                    ontology_ref_type=ref_type,
                    ontology_ref_id=ref_id,
                    canonical_text=term_text,
                    text_payload=payload,
                    vector_status="pending",
                )
                db.add(t)
                created += 1

    for a in attributes:
        entity_name = a.get("entity_name") or ""
        attr_name = a.get("attribute_name") or ""
        if not attr_name:
            continue
        entity_en_name = a.get("entity_en_name") or ""
        attr_en_name = a.get("attribute_en_name") or ""
        term_text = attr_name
        ent_id = a.get("entity_id")
        ent = next((e for e in entities if str(e.id) == str(ent_id)), None) if ent_id else None
        aliases: List[str] = []
        if ent is not None:
            for prop in (ent.properties_schema or []):
                if not isinstance(prop, dict):
                    continue
                prop_cn = str(
                    prop.get("cnName")
                    or prop.get("label")
                    or prop.get("display_name")
                    or prop.get("name_zh")
                    or prop.get("attribute_name")
                    or prop.get("name")
                    or ""
                ).strip()
                if prop_cn != attr_name:
                    continue
                aliases = _extract_property_alias_terms(prop)
                break
        search_texts = _dedupe_keep_order(
            [
                attr_name,
                attr_en_name,
                *aliases,
                f"{entity_name} {attr_name}" if entity_name else "",
                f"{entity_en_name} {attr_en_name}" if entity_en_name and attr_en_name else "",
            ]
        )
        payload = {
            "doc_type": "attribute",
            "scene": "query_attribute",
            "doc_id": f"{ent_id or 'unknown'}#{attr_en_name or attr_name}",
            "display_text": attr_name,
            "search_texts": [item for item in search_texts if item],
            "attribute_id": str(a.get("attribute_id")) if a.get("attribute_id") else None,
            "attribute_name": attr_name,
            "attribute_en_name": attr_en_name,
            "attribute_code": a.get("attribute_code") or attr_en_name,
            "entity_name": entity_name,
            "entity_en_name": entity_en_name,
            "attribute_category": "通用属性",
            "aliases": aliases,
        }
        key = _semantic_term_key(term_text, "attribute", payload)
        if ent:
            payload["entity_id"] = str(ent.id)
            payload["entity_en_name"] = ent.entity_en_name or ent.entity_code
        existing = existing_terms.get(key)
        if existing:
            existing.term = term_text
            existing.canonical_text = " | ".join([item for item in search_texts if item])
            existing.text_payload = payload
            existing.ontology_ref_type = "entity"
            if ent:
                existing.ontology_ref_id = str(ent.id)
            updated += 1
        else:
            t = StandardSemanticTerm(
                term=term_text,
                term_type="attribute",
                source="graph_extract",
                ontology_ref_type="entity" if ent else None,
                ontology_ref_id=str(ent.id) if ent else None,
                canonical_text=" | ".join([item for item in search_texts if item]),
                text_payload=payload,
                vector_status="pending",
            )
            db.add(t)
            created += 1

    if extract_mode == "all":
        for r in relations:
            term_text = r.relation_name or ""
            if not term_text:
                continue
            key = _semantic_term_key(term_text, "relation")
            existing = existing_terms.get(key)
            if not existing:
                t = StandardSemanticTerm(
                    term=term_text,
                    term_type="relation",
                    source="graph_extract",
                    canonical_text=term_text,
                    vector_status="pending",
                )
                db.add(t)
                created += 1

    db.commit()
    total = db.query(StandardSemanticTerm).count()
    return {"created": created, "updated": updated, "removed": removed, "total": total}


def vectorize_terms(
    db: Session,
    model_name: str = "bge-large-zh-v1.5",
    model_path: Optional[str] = None,
    term_ids: Optional[List[str]] = None,
    force_regenerate: bool = False,
    normalize_l2: bool = True,
    max_retries: int = 2,
    batch_size: int = 32,
    use_gpu: bool = False,
) -> Dict[str, Any]:
    q = db.query(StandardSemanticTerm).filter(StandardSemanticTerm.enabled == True)  # noqa: E712
    if term_ids:
        q = q.filter(StandardSemanticTerm.id.in_(term_ids))
    if not force_regenerate:
        q = q.filter(StandardSemanticTerm.vector_status != "ready")
    terms = q.all()
    if not terms:
        return {"total": 0, "success": 0, "failed": 0, "skipped": 0, "status": "no_pending_terms"}

    from ..services.semantic_retrieval import get_or_init_retrieval_config
    cfg = get_or_init_retrieval_config(db)
    actual_model_name = model_name or cfg.get("vector_model_name", "bge-large-zh-v1.5")

    texts = []
    for t in terms:
        if t.canonical_text:
            texts.append(t.canonical_text)
        elif t.term:
            texts.append(t.term)
        else:
            texts.append("")

    vectors = embed_texts(db, texts, actual_model_name)

    success_count = 0
    failed_count = 0
    skipped_count = 0
    qdrant_terms: List[StandardSemanticTerm] = []
    qdrant_vectors: List[List[float]] = []

    for t, vec in zip(terms, vectors):
        if not vec or len(vec) == 0:
            t.vector_status = "failed"
            t.last_error = "Empty embedding"
            failed_count += 1
            continue
        try:
            if normalize_l2:
                vec = l2_normalize(vec)
            content = t.canonical_text or t.term or ""
            h = _hash_text(actual_model_name, content)
            existing = db.query(SemanticEmbedding).filter(
                SemanticEmbedding.object_type == "standard_term",
                SemanticEmbedding.object_id == str(t.id),
            ).first()
            if existing:
                existing.text_content = content
                existing.embedding = []
                existing.model_name = actual_model_name
                existing.content_hash = h
            else:
                emb = SemanticEmbedding(
                    object_type="standard_term",
                    object_id=str(t.id),
                    text_content=content,
                    embedding=[],
                    model_name=actual_model_name,
                    content_hash=h,
                )
                db.add(emb)
            t.last_error = None
            t.model_name = actual_model_name
            t.vector_dim = len(vec)
            qdrant_terms.append(t)
            qdrant_vectors.append(vec)
        except Exception as e:
            t.vector_status = "failed"
            t.last_error = str(e)[:500]
            failed_count += 1

    qdrant_result: Dict[str, Any] = {}
    if qdrant_terms:
        try:
            db.flush()
            from ..services.standard_semantic_qdrant import upsert_standard_semantic_vectors_to_qdrant
            qdrant_result = upsert_standard_semantic_vectors_to_qdrant(
                db,
                qdrant_terms,
                qdrant_vectors,
                batch_size=batch_size,
                recreate_on_dimension_mismatch=force_regenerate,
            )
            qdrant_ok_ids = {str(t.id) for t in qdrant_terms}
            for t in qdrant_terms:
                if str(t.id) in qdrant_ok_ids:
                    t.vector_status = "ready"
                    success_count += 1
        except Exception as e:
            err = str(e)[:500]
            for t in qdrant_terms:
                t.vector_status = "failed"
                t.last_error = err
            failed_count += len(qdrant_terms)
            qdrant_result = {"ok": False, "error": err}

    db.commit()
    total = len(terms)
    progress = success_count / total if total > 0 else 0.0

    task = StandardSemanticVectorTask(
        task_code=f"vec_{uuid.uuid4().hex[:8]}",
        status="done" if failed_count == 0 else ("partial" if success_count > 0 else "failed"),
        total_count=total,
        success_count=success_count,
        failed_count=failed_count,
        skipped_count=skipped_count,
        progress=progress,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "task_code": task.task_code,
        "status": task.status,
        "total": total,
        "success": success_count,
        "success_count": success_count,
        "failed": failed_count,
        "failed_count": failed_count,
        "skipped": skipped_count,
        "skipped_count": skipped_count,
        "progress": progress,
        "qdrant": qdrant_result,
        "storage": "qdrant_only_vector_mysql_metadata",
        "message": f"向量化完成：成功{success_count}，失败{failed_count}，跳过{skipped_count}，向量已写入Qdrant，MySQL仅保留元数据",
    }


def export_vectors(
    db: Session,
    model_name: str = "bge-large-zh-v1.5",
    format: str = "json",
    include_ontology_bind: bool = True,
    term_types: Optional[List[str]] = None,
    entity_scope: str = "data",
) -> Dict[str, Any]:
    q = db.query(StandardSemanticTerm).filter(
        StandardSemanticTerm.vector_status == "ready",
        StandardSemanticTerm.enabled == True,  # noqa: E712
    )
    if term_types:
        q = q.filter(StandardSemanticTerm.term_type.in_(term_types))
    if entity_scope and entity_scope != "all":
        if entity_scope == "data":
            q = q.filter(StandardSemanticTerm.ontology_ref_type == "entity")
        elif entity_scope == "concept":
            q = q.filter(StandardSemanticTerm.ontology_ref_type == "concept")
    terms = q.all()
    if not terms:
        return {"rows": [], "total": 0}

    from app.services.standard_semantic_qdrant import QDRANT_COLLECTION_STANDARD_TERMS
    from app.services.tupu_qdrant_client import TupuQdrantClient

    client = TupuQdrantClient()
    qdrant_points = client.get_points(
        QDRANT_COLLECTION_STANDARD_TERMS,
        [str(t.id) for t in terms],
        with_payload=True,
        with_vectors=True,
    )
    qdrant_map = {str(p.get("id")): p for p in qdrant_points}

    rows = []
    for t in terms:
        point = qdrant_map.get(str(t.id))
        vec = point.get("vector") if point else None
        if not isinstance(vec, list):
            continue
        payload = point.get("payload") or {}
        row = {
            "term_id": str(t.id),
            "term": t.term,
            "term_type": t.term_type,
            "canonical_text": t.canonical_text,
            "vector": [float(x) for x in vec],
            "vector_dim": len(vec),
            "model_name": payload.get("model_name") or t.model_name or model_name,
        }
        if include_ontology_bind:
            row["ontology_ref_type"] = t.ontology_ref_type
            row["ontology_ref_id"] = str(t.ontology_ref_id) if t.ontology_ref_id else None
            row["text_payload"] = t.text_payload
        rows.append(row)

    if format == "parquet":
        import base64
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
            table = pa.table({
                "term_id": [r["term_id"] for r in rows],
                "term": [r["term"] for r in rows],
                "term_type": [r["term_type"] for r in rows],
                "vector": [json.dumps(r["vector"]) for r in rows],
                "model_name": [r["model_name"] for r in rows],
            })
            import io
            buf = io.BytesIO()
            pq.write_table(table, buf)
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            return {"file_base64": b64, "file_name": "standard_semantic_vectors.parquet", "total": len(rows)}
        except ImportError:
            pass

    return {"rows": rows, "total": len(rows)}


def query_standard_semantic_matches(
    db: Session,
    query_text: str,
    top_k: int = 10,
    term_types: Optional[List[str]] = None,
    normalize_l2: bool = True,
    bind_ontology: bool = True,
    entity_scope: str = "data",
    logs: Optional[List[Dict[str, Any]]] = None,
    hybrid: bool = False,
) -> List[Dict[str, Any]]:
    try:
        if hybrid:
            from app.services.hybrid_retrieval import hybrid_search, tokenize_query
            tokens = tokenize_query(query_text)
            if logs is not None:
                logs.append({"level": "info", "message": f"hybrid_search tokens={tokens}"})
            rows = hybrid_search(
                db,
                query_text,
                top_k=top_k,
                term_types=term_types,
                entity_scope=entity_scope,
            )
            if logs is not None:
                logs.append({"level": "info", "message": f"hybrid_search returned {len(rows)} rows"})
            return rows
        from app.services.standard_semantic_qdrant import query_standard_semantic_matches_qdrant
        rows = query_standard_semantic_matches_qdrant(
            db,
            query_text,
            top_k=top_k,
            term_types=term_types,
            entity_scope=entity_scope,
        )
        if logs is not None:
            logs.append({"level": "info", "message": f"qdrant_backend hit, returned {len(rows)} rows"})
        return rows
    except Exception as exc:
        if logs is not None:
            logs.append({"level": "error", "message": f"qdrant_backend failed: {exc}"})
        return []
