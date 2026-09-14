# -*- coding: utf-8 -*-
"""④文档知识库（spec R2）单测：协议层/收编等值/指针二分/对账。变异锚点见各 docstring。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


def test_engine_protocol_four_methods():
    """四方法协议（spec D4）：RuntimeCheckable+hasattr 容忍部分实现。
    变异锚点：协议缺任一方法签名 → 红。"""
    from app.services.kb_engines.base import RAGPipeline
    for m in ("initialize", "add_documents", "search", "delete"):
        assert hasattr(RAGPipeline, m)


def test_qdrant_family_parity(tmp_path, monkeypatch):
    """A2 收编等值：qdrant 族 add/search 与 _chunk_text+embed_texts 原语义对拍
    （分块数/payload 字段/collection 命名一致）。变异锚点：收编改分块/嵌入语义 → 红。"""
    from app.services.kb_engines.qdrant_family import QdrantFamily
    from app.api.knowledge_base import _chunk_text, _collection_name

    upserts, searches = [], []

    class _FakeClient:
        """按 TupuQdrantClient 真实接口形状的桩：ensure_collection/upsert_points/search_points。"""

        def ensure_collection(self, name, vector_size=1024, distance="Cosine"):
            pass

        def upsert_points(self, name, points):
            upserts.append((name, list(points)))

        def search_points(self, name, vector, top=5, with_payload=True):
            pts = upserts[-1][1][:top] if upserts else []
            return [{"score": 0.9, "payload": p["payload"]} for p in pts]

    fam = QdrantFamily(client=_FakeClient(),
                       embed_fn=lambda batch: [[0.1, 0.2, 0.3, 0.4] for _ in batch])
    kb = {"id": "945fa9d0-1d15-4ac1-baf9-a2539cab9311",
          "embedding_signature": {"chunk_size": 500, "chunk_overlap": 50}}
    text = "x" * 1200
    counts = fam.add_documents(kb, [{"doc_id": "d1", "filename": "a.md", "text": text}])
    # 原语义对拍①：分块数与 _chunk_text 同参数一致
    chunks = _chunk_text(text, size=500, overlap=50)
    assert counts == {"d1": len(chunks)}
    # 原语义对拍②：collection 命名与 _collection_name 一致
    assert upserts and upserts[0][0] == _collection_name(kb["id"])
    # 原语义对拍③：payload 键与 m15 vectorize 端点一致（doc_id/filename/chunk_idx/text）+signature
    payload = upserts[0][1][0]["payload"]
    assert payload["doc_id"] == "d1" and payload["filename"] == "a.md"
    assert "chunk_idx" in payload and "text" in payload and "signature" in payload
    # search 命中形状
    hits = fam.search(kb, "q", top_k=2)
    assert hits and set(hits[0].keys()) == {"text", "score", "payload"}


def test_connected_delete_zero_touch():
    """A3 指针二分：connected 删除→透传客户端零 delete 调用（断言调用清单）。"""
    calls = []

    class _SpyES:
        def search(self, *a, **k):
            calls.append(("search", a))
            return {"hits": {"hits": []}}

    from app.services.kb_engines.connected_es import ConnectedESFamily
    fam = ConnectedESFamily({"url": "http://es:9200", "index": "demo", "client": _SpyES()})
    fam.delete("kb-x")                       # 指针删除=显式 no-op
    assert [c for c in calls if c[0] != "search"] == []      # 零删除/零写入
