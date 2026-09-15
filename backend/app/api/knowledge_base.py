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


def _current_signature(db: Session, vector_size: int = None) -> Dict[str, Any]:
    """④（spec D8）：签名三因子（嵌入模型名/维度/分块参数）——对账基准。"""
    from app.services.llm_client import get_default_llm_connection
    conn = get_default_llm_connection("embedding")
    if vector_size is None:
        vector_size = _get_vector_size(db)
    return {
        "embed_model": (conn.model_name if conn else ""),
        "vector_size": vector_size,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
    }


# ---------- Schemas ----------

class KBCreate(BaseModel):
    name: str
    description: Optional[str] = None
    # ④批2：建库白名单（spec §七铁则）——type/rag_provider 白名单+indexed 的 pointer 必空
    type: str = "indexed"
    rag_provider: str = "qdrant"
    pointer_params: Optional[Dict[str, Any]] = None


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
    # ④批2：白名单铁则——type/rag_provider 枚举+indexed 的 pointer_params 必空
    kb_type = (payload.type or "indexed").strip().lower()
    provider = (payload.rag_provider or "qdrant").strip().lower()
    if kb_type not in ("indexed", "connected"):
        raise HTTPException(status_code=422, detail=f"type 白名单: indexed/connected（收到 {kb_type}）")
    if provider not in ("qdrant", "connected_es"):
        raise HTTPException(status_code=422, detail=f"rag_provider 白名单: qdrant/connected_es（收到 {provider}）")
    if kb_type == "connected" and provider != "connected_es":
        raise HTTPException(status_code=422, detail="connected 型当前仅支持 connected_es 指针族")
    if kb_type == "indexed" and payload.pointer_params:
        raise HTTPException(status_code=422, detail="indexed 型为自建索引，pointer_params 必须为空")

    kb_id = str(uuid.uuid4())
    collection = _collection_name(kb_id)
    kb = KnowledgeBase(
        id=kb_id,
        name=name,
        description=payload.description,
        collection_name=collection,
        storage_dir=kb_id,
        type=kb_type,
        rag_provider=provider,
        pointer_params=(payload.pointer_params or None) if kb_type == "connected" else None,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)

    if kb_type == "connected":
        # ④批2：指针型不建索引、不建磁盘目录（零复制零重建——D6）
        return {"code": 200, "data": _kb_to_dict(kb), "message": f"知识库「{name}」已创建（connected 指针型）"}

    # 建 Qdrant collection（探测维度）——indexed 专属
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
    # ④批2（D6 指针二分）：connected 只删注册行（collection/磁盘/文档零触碰——A3）；
    # indexed 级联照旧（m15 语义）。
    if (kb.type or "indexed") == "connected":
        db.delete(kb)
        db.commit()
        return {"code": 200, "message": "指针型知识库已删除（外部资源零触碰）"}
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
    # ④批2：指针型无摄入语义（后端 422 双保险——管理页入口对 connected 隐藏）
    if (kb.type or "indexed") == "connected":
        raise HTTPException(status_code=422, detail="指针型知识库不支持文档上传（不复制不重建）")

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

    # ④批3：checksum+解析缓存键（sha256 文件内容——同文件不重复解析）
    import hashlib as _hl
    _sha = _hl.sha256(contents).hexdigest()
    doc = KnowledgeDocument(
        id=doc_id,
        kb_id=kb_id,
        filename=filename,
        file_path=str(save_path),
        file_size=len(contents),
        status="pending",
        checksum=_sha,
        parse_cache_key=f"sha256:{_sha[:24]}",
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
    # ④批2：指针型无向量化工序
    if (kb.type or "indexed") == "connected":
        raise HTTPException(status_code=422, detail="指针型知识库无需向量化（检索实时透传外部源）")

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
        # 全量重建：先删 collection 再建（m15 语义不动——抽层不抽语义，A2 对拍钉死）
        client.delete_collection(kb.collection_name)
        client.ensure_collection(kb.collection_name, vector_size=vector_size, distance="Cosine")

        # ④批1：分块→嵌入→upsert 收编进 QdrantFamily（签名三因子快照同步落 KB/文档行，批 3 对账用）
        from app.services.kb_engines.qdrant_family import QdrantFamily
        sig = _current_signature(db, vector_size)
        kb.embedding_signature = sig
        fam = QdrantFamily(client=client, embed_fn=lambda batch: embed_texts(db, batch))
        total_vectors = 0
        for doc in docs:
            try:
                # ④批3：解析走 factory+cache（checksum 命中不重解析；md/txt 语义与 _read_text_file 等值）
                from app.services.parsing.cache import parse_cached
                _sha = doc.checksum or "no-checksum"
                text = parse_cached(Path(doc.file_path), _sha) if doc.checksum else _read_text_file(Path(doc.file_path))
                # ⑤批3（⑤d）：教材块结构面（两面一次编译）——内容特征触发（⑤d 修改点仅两项，
                # 不加 KB 配置列）：解析产物可编出结构块（quiz/flash_cards）或多章节（## ≥2）
                # 才视为教材落 blocks_json；普通单文本不落（笔记零感知）。
                try:
                    from app.services.parsing.factory import parse_book_text
                    _blocks = parse_book_text(text)
                    if sum(1 for b in _blocks if b["type"] != "text") >= 1 or len(_blocks) >= 2:
                        doc.blocks_json = _blocks
                except Exception as pe:   # 编块失败不阻嵌入面（教材=增强，检索面为主）
                    logger.warning("文档 %s 块编译失败（跳过块面）: %s", doc.filename, pe)
                counts = fam.add_documents(
                    {"id": kb.id, "embedding_signature": sig},
                    [{"doc_id": doc.id, "filename": doc.filename, "text": text}],
                )
                chunk_n = counts.get(doc.id, 0)
                doc.embedding_signature = sig
                if not chunk_n:
                    doc.status = "error"
                    doc.error_msg = "文件内容为空"
                    doc.chunk_count = 0
                    continue
                doc.chunk_count = chunk_n
                doc.status = "vectorized"
                doc.error_msg = None
                total_vectors += chunk_n
            except Exception as de:
                doc.status = "error"
                doc.error_msg = str(de)
                doc.embedding_signature = sig
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

    # ④批2：type 分路——connected→指针族透传（外部 ES）；indexed→Qdrant 相似检索
    if (kb.type or "indexed") == "connected":
        from app.services.kb_engines.connected_es import ConnectedESFamily
        params = dict(kb.pointer_params or {})
        fam = ConnectedESFamily(params)
        try:
            hits = fam.search({"id": kb.id}, query, top_k=top_k)
        except Exception as e:
            logger.warning("指针型检索失败: %s", e)
            raise HTTPException(status_code=502, detail=f"外部检索源不可用: {e}")
        matches = [
            {"score": float(h["score"] or 0), "text": h["text"],
             "filename": (h.get("payload") or {}).get("_index", ""), "chunk_idx": 0}
            for h in hits
        ]
        return {"code": 200, "data": {"query": query, "matches": matches, "count": len(matches)}}

    try:
        client = _get_client()
        if not client.healthcheck():
            raise RuntimeError("qdrant_unavailable")
        from app.services.semantic_retrieval import embed_texts
        # ④批1：检索走 QdrantFamily（m15 语义等值——score/text/filename/chunk_idx 出参不变）
        from app.services.kb_engines.qdrant_family import QdrantFamily
        fam = QdrantFamily(client=client, embed_fn=lambda batch: embed_texts(db, batch))
        hits = fam.search({"id": kb.id}, query, top_k=top_k)
        matches = [
            {
                "score": h["score"],
                "text": h["text"],
                "filename": (h.get("payload") or {}).get("filename", ""),
                "chunk_idx": (h.get("payload") or {}).get("chunk_idx", 0),
            }
            for h in hits
        ]
        return {"code": 200, "data": {"query": query, "matches": matches, "count": len(matches)}}
    except Exception as e:
        logger.warning("知识库检索失败: %s", e)
        raise HTTPException(status_code=500, detail=f"检索失败: {e}")


# ---------- ④批3：增量对账+重嵌（spec D8：重嵌永远手动） ----------

@router.post("/{kb_id}/reconcile")
def reconcile_knowledge_base(kb_id: str, db: Session = Depends(get_db)):
    """对账（spec D8）：文档行签名快照 vs KB 级签名（嵌入模型名/维度/分块参数三因子）→
    不一致标 stale；返回报告 {stale, failed, consistent, signature, checked_at}。
    永不自动重嵌（成本纪律）——重嵌走 reembed 按钮。幂等（重复对账结果稳定）。"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if (kb.type or "indexed") == "connected":
        raise HTTPException(status_code=422, detail="指针型知识库无对账语义（无自建索引）")
    sig = _current_signature(db)
    stale_list, failed_list, consistent = [], [], 0
    for doc in kb.documents:
        if doc.status == "error":
            failed_list.append(doc.filename)
        elif doc.status in ("vectorized", "stale"):
            # 🔴-3（审查 2026-09-15）：已嵌入文档按**签名失配**判定而非 status——
            # 修复报告幂等（原实现首轮 stale 第二轮 status!=vectorized 翻转 consistent）；
            # 签名已对齐的 stale 行态归位 vectorized（报告与行态一致）。
            if (doc.embedding_signature or {}) != (sig or {}):
                doc.status = "stale"
                stale_list.append(doc.filename)
            else:
                if doc.status == "stale":
                    doc.status = "vectorized"
                consistent += 1
        # pending 等中间态：不计入任何桶（原实现虚计 consistent）
    kb.status = "degraded" if (stale_list or failed_list) else kb.status
    db.commit()
    from datetime import datetime as _dt
    return {"code": 200, "data": {
        "kb": _kb_to_dict(kb, with_docs=True),
        "reconcile": {"stale": stale_list, "failed": failed_list,
                      "consistent": consistent, "signature": sig,
                      "checked_at": _dt.now().isoformat(timespec="seconds")},
    }}


@router.post("/{kb_id}/reembed")
def reembed_knowledge_base(kb_id: str, db: Session = Depends(get_db)):
    """重嵌（spec D8：永远手动）：stale 文档批→按当前签名全量重建该批向量→签名对齐→清洁。
    先删旧点再嵌（🔴-1，审查 2026-09-15）。未 reembed 时检索照常（旧索引不破坏——A4 断言）。"""
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.id == kb_id).first()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")
    if (kb.type or "indexed") == "connected":
        raise HTTPException(status_code=422, detail="指针型知识库无重嵌语义")
    sig = _current_signature(db)
    # I2（复审 2026-09-15）：候选集 = stale ∪（error 且签名失配）——error 不可重试会把
    # 一次故障变成永久缺口；签名失配的 error 文档保持重试资格（成功后归位 vectorized）。
    stale_docs = [d for d in kb.documents
                  if d.status == "stale"
                  or (d.status == "error" and (d.embedding_signature or {}) != (sig or {}))]
    if not stale_docs:
        return {"code": 200, "data": {"kb": _kb_to_dict(kb, with_docs=True),
                "reembed": {"reembedded": 0, "failed": [], "message": "无 stale 文档"}}}
    client = _get_client()
    if not client.healthcheck():
        raise HTTPException(status_code=502, detail="qdrant_unavailable")
    from app.services.semantic_retrieval import embed_texts
    from app.services.kb_engines.qdrant_family import QdrantFamily
    fam = QdrantFamily(client=client, embed_fn=lambda batch: embed_texts(db, batch))
    # C1（复审 2026-09-15）：维度预检——签名三因子含 vector_size（_current_signature 内部
    # 已探测新嵌入维度），而 collection 尺寸创建即固定、封装层显式拒绝不一致
    # （tupu_qdrant_client.py:81-85）。不预检则「删旧点成功→新维度 upsert 被拒→旧索引
    # 已丢」，🔴-1 的 fail-closed 反而把无害失败升级为丢索引。不一致=按 KB 级先重建
    # （等价 vectorize :344-345 语义），重建后逐文档删点自然为空操作。集合名统一走
    # _collection_name(kb.id)（fam 写入与 KB 创建列同源，I4 收敛口径）。
    _coll = _collection_name(kb.id)
    _info = client.collection_info(_coll) or {}
    _existing = (((( _info.get("config") or {}).get("params") or {}).get("vectors")) or {}).get("size") \
        or _info.get("vector_size")
    _want = int(sig.get("vector_size") or 0)
    if _want and _existing and int(_existing) != _want:
        client.delete_collection(_coll)
        client.ensure_collection(_coll, vector_size=_want, distance="Cosine")
        logger.warning("重嵌维度预检：%s 维度 %s→%s，已按新签名重建 collection",
                       _coll, _existing, _want)
    reembedded = 0
    failed: list = []   # I2（复审 2026-09-15）：失败清单进响应（前端明示，不再「成功：0 个文档」）
    for doc in stale_docs:
        try:
            from app.services.parsing.cache import parse_cached
            text = (parse_cached(Path(doc.file_path), doc.checksum)
                    if doc.checksum else _read_text_file(Path(doc.file_path)))
            try:
                # 🔴-1 + I4（复审 2026-09-15）：先删旧点再嵌——删除原语收编 fam.delete
                # （FilterSelector by payload.doc_id，与 add_documents 同一封装、同一集合名
                # 口径 _collection_name(kb.id)，消「DB 列 vs 推导名」双源与三份重复原语；
                # C1 预检重建后此处自然为空操作）。
                fam.delete({"id": kb.id}, doc_ids=[doc.id])
            except Exception as de0:
                # I2：删除失败保 stale（error_msg 记因）——标 error 会失去重试资格，把一次
                # 故障变成永久缺口；stale 文档旧点仍在（A4 语义），下次 reembed 可重试。
                doc.status = "stale"
                doc.error_msg = f"删旧向量失败（防新旧并存，fail-closed）: {de0}"
                failed.append({"id": doc.id, "filename": doc.filename, "error_msg": doc.error_msg})
                logger.warning("重嵌 %s 删旧失败: %s", doc.filename, de0)
                continue
            counts = fam.add_documents({"id": kb.id, "embedding_signature": sig},
                                       [{"doc_id": doc.id, "filename": doc.filename, "text": text}])
            doc.chunk_count = counts.get(doc.id, 0)
            doc.status = "vectorized"
            doc.embedding_signature = sig
            doc.error_msg = None
            reembedded += 1
        except Exception as de:
            doc.status = "error"
            doc.error_msg = str(de)
            failed.append({"id": doc.id, "filename": doc.filename, "error_msg": str(de)})
            logger.warning("重嵌 %s 失败: %s", doc.filename, de)
    # stale 文档旧点仍在 Qdrant（A4 语义：重嵌前检索照常）——向量计数应含其 chunk_count
    kb.vector_count = sum(d.chunk_count or 0 for d in kb.documents
                          if d.status in ("vectorized", "stale"))
    kb.status = "ready" if not [d for d in kb.documents if d.status in ("error", "stale")] else kb.status
    db.commit()
    return {"code": 200, "data": {"kb": _kb_to_dict(kb, with_docs=True),
            "reembed": {"reembedded": reembedded, "failed": failed, "signature": sig}}}


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
        # ④批1：新列出参（type/rag_provider/enabled/version/签名）
        "type": getattr(kb, "type", None) or "indexed",
        "rag_provider": getattr(kb, "rag_provider", None) or "qdrant",
        "enabled": bool(getattr(kb, "enabled", True)),
        "version": int(getattr(kb, "version", 1) or 1),
        "embedding_signature": getattr(kb, "embedding_signature", None),
        "created_at": kb.created_at.isoformat() if kb.created_at else None,
    }
    if with_docs:
        d["documents"] = [_doc_to_dict(doc) for doc in kb.documents]
    # ④批3：状态报告增强（签名一致性/stale+failed 清单/最后对账=文档行签名抽查）
    if with_docs:
        sig = getattr(kb, "embedding_signature", None)
        d["report"] = {
            "type": d.get("type"),
            "rag_provider": d.get("rag_provider"),
            "signature": sig,
            "stale_docs": [doc["filename"] for doc in d["documents"] if doc["status"] == "stale"],
            "failed_docs": [doc["filename"] for doc in d["documents"] if doc["status"] == "error"],
            "signature_consistent": all(
                (doc.get("embedding_signature") or None) == (sig or None)
                for doc in d["documents"] if doc["status"] == "vectorized"),
        }
        if d.get("type") == "connected":
            # 指针失联探测（HEAD 语义——轻量 GET）
            params = getattr(kb, "pointer_params", None) or {}
            try:
                import requests as _rq
                _r = _rq.get(f"{params.get('url', '')}", timeout=3)
                d["report"]["reachable"] = _r.status_code < 500
                d["report"]["checked_at"] = _r.headers.get("date")
            except Exception as _pe:
                d["report"]["reachable"] = False
                d["report"]["unreachable_reason"] = str(_pe)[:120]
    return d


def _doc_to_dict(doc: KnowledgeDocument) -> Dict[str, Any]:
    # ⑤批3（⑤d）：块概要一行（块数/类型分布——H5 消费预检；明细走 blocks_json 列不进列表）
    _blocks = getattr(doc, "blocks_json", None) or []
    _type_dist: Dict[str, int] = {}
    for _b in _blocks:
        _t = str(_b.get("type", "text"))
        _type_dist[_t] = _type_dist.get(_t, 0) + 1
    return {
        "id": doc.id,
        "kb_id": doc.kb_id,
        "filename": doc.filename,
        "file_size": doc.file_size,
        "chunk_count": doc.chunk_count,
        "status": doc.status,
        "error_msg": doc.error_msg,
        "checksum": getattr(doc, "checksum", None),          # ④批3：解析缓存键面
        "embedding_signature": getattr(doc, "embedding_signature", None),
        "block_summary": {"count": len(_blocks), "types": _type_dist} if _blocks else None,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
    }
