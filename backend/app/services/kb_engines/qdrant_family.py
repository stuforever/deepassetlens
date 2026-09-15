# -*- coding: utf-8 -*-
"""④（spec D4/D8）：indexed 族——现 m15 vectorize/search 流程的协议化封装（抽层不抽语义，
A2 对拍钉死）。原语 _chunk_text/_collection_name/_read_text_file/embed_texts 全部沿用
api/knowledge_base.py 既有实现（本模块只 import 不复制）。"""
import uuid
from typing import Any, Callable, Dict, List, Optional

logger = __import__("logging").getLogger(__name__)


class QdrantFamily:
    """indexed 族：每 KB 一个 collection（kb_ 前缀去连字符，_collection_name 语义）。
    add_documents=分块→embed 批嵌→upsert（payload 带 doc_id/filename/chunk_idx/text/signature）；
    search=embed query→top-k；delete=collection 删或 filter 删。
    分块参数（size/overlap）从 kb['embedding_signature'] 读——签名变了走 reconcile 通道。"""

    def __init__(self, client: Any = None, embed_fn: Optional[Callable[[List[str]], List[List[float]]]] = None):
        # client=注入（测试桩）；缺省走 m15 _get_client()。embed_fn=注入（db 无关形态）；
        # 缺省走 m15 embed_texts(db, texts)——端点侧传入 db 偏函数。
        self._client = client
        self._embed_fn = embed_fn

    # ---- 原语桥接（延迟 import 防 API 层循环依赖） ----

    def _client_or_default(self):
        if self._client is None:
            from app.api.knowledge_base import _get_client
            self._client = _get_client()
        return self._client

    def _embed(self, batch: List[str]) -> List[List[float]]:
        if self._embed_fn is not None:
            return self._embed_fn(batch)
        from app.services.semantic_retrieval import embed_texts
        from app.core.database import SessionLocal
        db = SessionLocal()
        try:
            return embed_texts(db, batch)
        finally:
            db.close()

    def _chunk(self, text: str, sig: Dict[str, Any]) -> List[str]:
        from app.api.knowledge_base import _chunk_text
        return _chunk_text(text,
                           size=int(sig.get("chunk_size", 500) or 500),
                           overlap=int(sig.get("chunk_overlap", 50) or 50))

    def _collection(self, kb: Dict[str, Any]) -> str:
        from app.api.knowledge_base import _collection_name
        return _collection_name(kb["id"])

    # ---- 协议四方法 ----

    def initialize(self, kb: Dict[str, Any]) -> None:
        """确保 collection 存在（维度=当前嵌入探测语义，沿 _get_vector_size）。"""
        from app.api.knowledge_base import _get_vector_size
        from app.core.database import SessionLocal
        client = self._client_or_default()
        if not client.healthcheck():
            raise RuntimeError("qdrant_unavailable")
        db = SessionLocal()
        try:
            client.ensure_collection(self._collection(kb), vector_size=_get_vector_size(db), distance="Cosine")
        finally:
            db.close()

    def add_documents(self, kb: Dict[str, Any], docs: List[Dict[str, Any]]) -> Dict[str, int]:
        """docs=[{doc_id, filename, text}] → {doc_id: chunk_count}。
        m15 vectorize 端点体的协议化：payload/doc_id/filename/chunk_idx/text/signature
        与 EMB_BATCH 分批语义逐项等值（A2 对拍锚点）。"""
        sig = kb.get("embedding_signature") or {"chunk_size": 500, "chunk_overlap": 50}
        client = self._client_or_default()
        EMB_BATCH, UPSERT_BATCH = 32, 64
        out: Dict[str, int] = {}
        for doc in docs:
            chunks = self._chunk(doc["text"], sig)
            if not chunks:
                out[doc["doc_id"]] = 0
                continue
            points: List[Dict[str, Any]] = []
            for i in range(0, len(chunks), EMB_BATCH):
                batch = chunks[i:i + EMB_BATCH]
                vectors = self._embed(batch)
                for j, vec in enumerate(vectors):
                    chunk_idx = i + j
                    points.append({
                        "id": str(uuid.uuid4()),
                        "vector": vec,
                        "payload": {
                            "doc_id": doc["doc_id"],
                            "filename": doc["filename"],
                            "chunk_idx": chunk_idx,
                            "text": batch[j],
                            "signature": sig,
                        },
                    })
            for k in range(0, len(points), UPSERT_BATCH):
                client.upsert_points(self._collection(kb), points[k:k + UPSERT_BATCH])
            out[doc["doc_id"]] = len(chunks)
        return out

    def search(self, kb: Dict[str, Any], query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        """embed query→top-k（m15 search 端点语义：[{text, score, payload}]）。"""
        client = self._client_or_default()
        vectors = self._embed([query])
        if not vectors or not vectors[0]:
            raise RuntimeError("embedding 失败")
        hits = client.search_points(self._collection(kb), vectors[0], top=top_k, with_payload=True)
        return [
            {
                "score": float(h.get("score", 0)),
                "text": (h.get("payload") or {}).get("text", ""),
                "payload": h.get("payload") or {},
            }
            for h in hits
        ]

    def delete(self, kb: Dict[str, Any], doc_ids: Optional[List[str]] = None) -> None:
        """doc_ids=None 删整库（collection 删除=m15 DELETE 语义）；否则按 payload.doc_id
        FilterSelector 原语删（🔴-2，审查 2026-09-15：废弃「scroll 重读-过滤-重写」路径——
        scroll 万点封顶/异常即 delete_collection 全清/维度硬编码 1024 三雷同拆；
        qdrant-client 原生 filter delete，无新依赖）。"""
        client = self._client_or_default()
        name = self._collection(kb)
        if doc_ids is None:
            client.delete_collection(name)
            return
        from qdrant_client import models as _qmodels
        client._client.delete(
            collection_name=name,
            points_selector=_qmodels.FilterSelector(
                filter=_qmodels.Filter(
                    must=[_qmodels.FieldCondition(key="doc_id",
                                                  match=_qmodels.MatchAny(any=list(doc_ids)))]
                )
            ),
        )
