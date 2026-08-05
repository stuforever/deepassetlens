"""自定义知识库 API：RAG 检索增强

复用现有基础设施：
- TupuQdrantClient：每个 KB 一个 Qdrant collection
- semantic_retrieval.embed_texts：文本嵌入
- 文档原文存磁盘 backend/data/kb_documents/{kb_id}/

流程：
1. create：建 KB 元数据 + 建 Qdrant collection
2. upload：保存文件到磁盘（.txt/.md）
3. vectorize：读文件 -> 分块 -> embed -> upsert Qdrant
4. search：embed query -> search Qdrant -> 返回 top-k
"""
from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import SessionLocal, get_db
from ..models.knowledge_base import KnowledgeBase, KnowledgeDocument

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/knowledge-bases", tags=["自定义知识库"])

# 文档存储根目录（backend/data/kb_documents/）
KB_DOC_ROOT = Path(__file__).resolve().parent.parent.parent / "data" / "kb_documents"
ALLOWED_EXT = {".txt", ".md", ".markdown"}
CHUNK_SIZE = 500       # 每块字符数
CHUNK_OVERLAP = 50     # 块间重叠
EMB_BATCH = 32


# ---------- 工具函数 ----------

def _collection_name(kb_id: str) -> str:
    """Qdrant collection 名：kb_ 前缀 + id 去连字符"""
    return "kb_" + kb_id.replace("-", "")[:24]


def _kb_dir(kb_id: str) -> Path:
    d = KB_DOC_ROOT / kb_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _get_client():
    from app.services.tupu_qdrant_client import TupuQdrantClient
    return TupuQdrantClient()


def _get_vector_size(db: Session) -> int:
    from app.services.semantic_retrieval import embed_texts
    vec = embed_texts(db, ["维度探测"])
    return len(vec[0]) if vec and vec[0] else 1024


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """按字符分块（带重叠），过滤纯空白块"""
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = start + size
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = end - overlap
    return chunks


def _read_text_file(path: Path) -> str:
    """读取 txt/md 文件，自动尝试 utf-8 / gbk"""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


# ---------- Schemas ----------

class KBCreate(BaseModel):
    name: str
    description: Optional[str] = None


class KBSearch(BaseModel):
    query: str
    top_k: int = 5


# ---------- CRUD ----------

@router.get("")
def list_knowledge_bases(db: Session = Depends(get_db)):
    kbs = db.query(KnowledgeBase).order_by(KnowledgeBase.created_at.desc()).all()
    return {"code": 200, "data": [_kb_to_dict(kb) for kb in kbs]}


@router.get("/{kb_id}")
def get_knowledge_base(kb_id: str, db: Session = Depends(get_db)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    return {"code": 200, "data": _kb_to_dict(kb, with_docs=True)}


@router.post("")
def create_knowledge_base(payload: KBCreate, db: Session = Depends(get_db)):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="知识库名称不能为空")
    if db.query(KnowledgeBase).filter(KnowledgeBase.name == name).first():
        raise HTTPException(status_code=400, detail="知识库名称已存在")

    kb_id = str(uuid.uuid4())
    collection = _collection_name(kb_id)
    kb = KnowledgeBase(
        id=kb_id,
        name=name,
        description=payload.description,
        collection_name=collection,
        storage_dir=kb_id,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)

    # 建 Qdrant collection（探测维度）
    try:
        client = _get_client()
        if client.healthcheck():
            vector_size = _get_vector_size(db)
            client.ensure_collection(collection, vector_size=vector_size, distance="Cosine")
        else:
            kb.status = "error"
            kb.error_msg = "qdrant_unavailable"
            db.commit()
    except Exception as e:
        kb.status = "error"
        kb.error_msg = str(e)
        db.commit()
        logger.warning("建 Qdrant collection 失败: %s", e)

    _kb_dir(kb_id)  # 预建目录
    return {"code": 200, "data": _kb_to_dict(kb), "message": f"知识库「{name}」已创建"}


@router.delete("/{kb_id}")
def delete_knowledge_base(kb_id: str, db: Session = Depends(get_db)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    collection = kb.collection_name
    # 删 Qdrant collection
    try:
        client = _get_client()
        if client.healthcheck():
            client.delete_collection(collection)
    except Exception as e:
        logger.warning("删 Qdrant collection 失败: %s", e)
    # 删磁盘文件
    try:
        import shutil
        d = KB_DOC_ROOT / kb_id
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
    except Exception:
        pass
    db.delete(kb)
    db.commit()
    return {"code": 200, "message": "知识库已删除"}


# ---------- 文档上传/删除 ----------

@router.post("/{kb_id}/upload")
async def upload_document(kb_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    filename = file.filename or "untitled.txt"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail=f"仅支持 {', '.join(ALLOWED_EXT)} 文件")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="文件为空")

    # 存磁盘：{kb_id}/{uuid}_{原文件名}
    doc_id = str(uuid.uuid4())
    save_name = f"{doc_id}_{filename}"
    save_path = _kb_dir(kb_id) / save_name
    save_path.write_bytes(contents)

    doc = KnowledgeDocument(
        id=doc_id,
        kb_id=kb_id,
        filename=filename,
        file_path=str(save_path),
        file_size=len(contents),
        status="pending",
    )
    db.add(doc)
    kb.doc_count = (kb.doc_count or 0) + 1
    db.commit()
    db.refresh(doc)
    return {"code": 200, "data": _doc_to_dict(doc), "message": f"文档「{filename}」已上传"}


@router.delete("/{kb_id}/documents/{doc_id}")
def delete_document(kb_id: str, doc_id: str, db: Session = Depends(get_db)):
    doc = db.query(KnowledgeDocument).filter(
        KnowledgeDocument.id == doc_id,
        KnowledgeDocument.kb_id == kb_id,
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    # 删磁盘文件
    try:
        p = Path(doc.file_path)
        if p.exists():
            p.unlink()
    except Exception:
        pass
    # 删 Qdrant 中该文档的向量（按 payload.doc_id 过滤删除）
    try:
        client = _get_client()
        if kb and client.healthcheck():
            from qdrant_client import models
            client._client.delete(
                collection_name=kb.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[models.FieldCondition(key="doc_id", match=models.MatchValue(value=doc_id))]
                    )
                ),
            )
    except Exception as e:
        logger.warning("删文档向量失败: %s", e)

    db.delete(doc)
    if kb:
        kb.doc_count = max(0, (kb.doc_count or 1) - 1)
    db.commit()
    return {"code": 200, "message": "文档已删除"}


# ---------- 向量化 ----------

@router.post("/{kb_id}/vectorize")
def vectorize_knowledge_base(kb_id: str, db: Session = Depends(get_db)):
    """对 KB 下所有 pending / 全部文档重新向量化"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    docs = db.query(KnowledgeDocument).filter(KnowledgeDocument.kb_id == kb_id).all()
    if not docs:
        raise HTTPException(status_code=400, detail="知识库无文档，请先上传")

    kb.status = "processing"
    kb.error_msg = None
    db.commit()

    try:
        client = _get_client()
        if not client.healthcheck():
            raise RuntimeError("qdrant_unavailable")

        from app.services.semantic_retrieval import embed_texts
        vector_size = _get_vector_size(db)
        # 全量重建：先删 collection 再建
        client.delete_collection(kb.collection_name)
        client.ensure_collection(kb.collection_name, vector_size=vector_size, distance="Cosine")

        total_vectors = 0
        for doc in docs:
            try:
                text = _read_text_file(Path(doc.file_path))
                chunks = _chunk_text(text)
                if not chunks:
                    doc.status = "error"
                    doc.error_msg = "文件内容为空"
                    doc.chunk_count = 0
                    continue

                points: List[Dict[str, Any]] = []
                for i in range(0, len(chunks), EMB_BATCH):
                    batch = chunks[i:i + EMB_BATCH]
                    vectors = embed_texts(db, batch)
                    for j, vec in enumerate(vectors):
                        chunk_idx = i + j
                        points.append({
                            "id": str(uuid.uuid4()),
                            "vector": vec,
                            "payload": {
                                "doc_id": doc.id,
                                "filename": doc.filename,
                                "chunk_idx": chunk_idx,
                                "text": batch[j],
                            },
                        })
                # 分批 upsert
                UPSERT_BATCH = 64
                for k in range(0, len(points), UPSERT_BATCH):
                    client.upsert_points(kb.collection_name, points[k:k + UPSERT_BATCH])

                doc.chunk_count = len(chunks)
                doc.status = "vectorized"
                doc.error_msg = None
                total_vectors += len(chunks)
            except Exception as de:
                doc.status = "error"
                doc.error_msg = str(de)
                logger.warning("文档 %s 向量化失败: %s", doc.filename, de)

        kb.vector_count = total_vectors
        kb.status = "ready"
        db.commit()
        return {
            "code": 200,
            "data": {
                "vector_count": total_vectors,
                "doc_count": len(docs),
                "docs": [_doc_to_dict(d) for d in docs],
            },
            "message": f"向量化完成：{total_vectors} 个分块",
        }
    except Exception as e:
        kb.status = "error"
        kb.error_msg = str(e)
        db.commit()
        logger.exception("知识库向量化失败")
        raise HTTPException(status_code=500, detail=f"向量化失败: {e}")


# ---------- 检索测试 ----------

@router.post("/{kb_id}/search")
def search_knowledge_base(kb_id: str, payload: KBSearch, db: Session = Depends(get_db)):
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    query = (payload.query or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="查询文本不能为空")
    top_k = max(1, min(int(payload.top_k or 5), 50))

    try:
        client = _get_client()
        if not client.healthcheck():
            raise RuntimeError("qdrant_unavailable")
        from app.services.semantic_retrieval import embed_texts
        vectors = embed_texts(db, [query])
        if not vectors or not vectors[0]:
            raise RuntimeError("embedding 失败")
        hits = client.search_points(
            kb.collection_name,
            vectors[0],
            top=top_k,
            with_payload=True,
        )
        matches = [
            {
                "score": float(h.get("score", 0)),
                "text": (h.get("payload") or {}).get("text", ""),
                "filename": (h.get("payload") or {}).get("filename", ""),
                "chunk_idx": (h.get("payload") or {}).get("chunk_idx", 0),
            }
            for h in hits
        ]
        return {"code": 200, "data": {"query": query, "matches": matches, "count": len(matches)}}
    except Exception as e:
        logger.warning("知识库检索失败: %s", e)
        raise HTTPException(status_code=500, detail=f"检索失败: {e}")


# ---------- 序列化 ----------

def _kb_to_dict(kb: KnowledgeBase, with_docs: bool = False) -> Dict[str, Any]:
    d: Dict[str, Any] = {
        "id": kb.id,
        "name": kb.name,
        "description": kb.description,
        "collection_name": kb.collection_name,
        "doc_count": kb.doc_count,
        "vector_count": kb.vector_count,
        "status": kb.status,
        "error_msg": kb.error_msg,
        "created_at": kb.created_at.isoformat() if kb.created_at else None,
    }
    if with_docs:
        d["documents"] = [_doc_to_dict(doc) for doc in kb.documents]
    return d


def _doc_to_dict(doc: KnowledgeDocument) -> Dict[str, Any]:
    return {
        "id": doc.id,
        "kb_id": doc.kb_id,
        "filename": doc.filename,
        "file_size": doc.file_size,
        "chunk_count": doc.chunk_count,
        "status": doc.status,
        "error_msg": doc.error_msg,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }
