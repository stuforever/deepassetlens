"""数据同步 API：Neo4j 全量重建 + 实体/属性向量化"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..core.database import SessionLocal, get_db

router = APIRouter(prefix="/api/v1/sync", tags=["数据同步"])


@router.post("/neo4j-all")
def sync_neo4j_all(force: bool = Query(True)):
    """全量同步 MySQL -> Neo4j（单一 Category+ChainRoot 体系）"""
    from ..services.graph_query_neo4j import sync_all_to_neo4j
    db = SessionLocal()
    try:
        return sync_all_to_neo4j(db, force=force)
    finally:
        db.close()


@router.post("/neo4j-wipe")
def wipe_neo4j():
    """清空 Neo4j 全库"""
    from ..services.graph_query_neo4j import wipe_neo4j
    return wipe_neo4j()


@router.post("/entity-vectors")
def sync_entity_vectors_api(force: bool = Query(True)):
    """实体名向量化 -> entity_embeddings collection（force=true 全量重建, force=false 增量同步）"""
    from ..services.entity_attr_vector_service import sync_entity_vectors
    db = SessionLocal()
    try:
        return sync_entity_vectors(db, force=force)
    finally:
        db.close()


@router.post("/attribute-vectors")
def sync_attribute_vectors_api(force: bool = Query(True)):
    """属性向量化 -> attribute_embeddings collection（force=true 全量重建, force=false 增量同步）"""
    from ..services.entity_attr_vector_service import sync_attribute_vectors
    db = SessionLocal()
    try:
        return sync_attribute_vectors(db, force=force)
    finally:
        db.close()


@router.get("/entity-vector-stats")
def entity_vector_stats():
    from ..services.entity_attr_vector_service import get_entity_vector_stats
    return get_entity_vector_stats()


@router.get("/attribute-vector-stats")
def attribute_vector_stats():
    from ..services.entity_attr_vector_service import get_attribute_vector_stats
    return get_attribute_vector_stats()


@router.post("/query-vectors")
def query_vectors_api(payload: dict):
    """向量查询测试：按 collection 下拉选择，分开查实体库/属性库

    body: { "collection": "entity" | "attribute", "query": str, "top_k": int = 10 }
    """
    from ..services.entity_attr_vector_service import search_entity_vectors, search_attribute_vectors
    collection = (payload or {}).get("collection", "entity")
    query = (payload or {}).get("query", "")
    top_k = int((payload or {}).get("top_k", 10))
    if not query:
        raise HTTPException(status_code=400, detail="query 不能为空")
    if collection == "attribute":
        hits = search_attribute_vectors(query, top_k=top_k)
    else:
        hits = search_entity_vectors(query, top_k=top_k)
    return {"code": 200, "data": {"collection": collection, "matches": hits, "count": len(hits)}}
