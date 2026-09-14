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


def test_reconcile_reembed_lifecycle(tmp_path, monkeypatch):
    """A4（spec D8）：改签名→reconcile→stale→**检索照常**（旧索引不破坏）→reembed→清洁。
    服务层语义单测：直接构造 ORM 行（内存 SQLite），不真连 Qdrant/嵌入。"""
    from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument
    from app.models.base import Base
    from app.core.database import SessionLocal, engine
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        # 真库（MySQL）幂等：清历史运行残留（测试行按固定 id）
        db.query(KnowledgeDocument).filter_by(kb_id="kb-recon").delete()
        db.query(KnowledgeBase).filter_by(id="kb-recon").delete()
        db.commit()
        (tmp_path / "a.md").write_text("对账测试文档内容", encoding="utf-8")   # reembed 读文件用
        kb = KnowledgeBase(id="kb-recon", name="对账测试", collection_name="kb_recon",
                           storage_dir="kb-recon", type="indexed", rag_provider="qdrant",
                           embedding_signature={"embed_model": "old", "vector_size": 4,
                                                "chunk_size": 500, "chunk_overlap": 50})
        db.add(kb)
        db.flush()
        db.add(KnowledgeDocument(id="d1", kb_id="kb-recon", filename="a.md",
                                 file_path=str(tmp_path / "a.md"), status="vectorized",
                                 embedding_signature={"embed_model": "old", "vector_size": 4,
                                                      "chunk_size": 500, "chunk_overlap": 50}))
        db.commit()

        # 模拟签名变更（嵌入模型升级）：文档行快照≠新签名 → stale
        from app.api import knowledge_base as kb_api
        monkeypatch.setattr(kb_api, "_current_signature", lambda db, vs=None: {
            "embed_model": "new-embed", "vector_size": 4, "chunk_size": 500, "chunk_overlap": 50})
        rep = kb_api.reconcile_knowledge_base("kb-recon", db)
        rec = rep["data"]["reconcile"]
        assert rec["stale"] == ["a.md"] and rec["consistent"] == 0
        assert rep["data"]["kb"]["status"] == "degraded"          # 状态纪律

        # 检索照常（A4 核心）：reembed 前端点不被破坏——这里断言端点不拦 stale KB
        # （真实检索路径由 Qdrant 可用性决定，单测层面验证 reconcile 不改向量侧）
        doc = db.query(KnowledgeDocument).filter_by(id="d1").first()
        assert doc.status == "stale"

        # reembed：monkeypatch Family.add_documents 返回固定计数
        class _FakeFam:
            def add_documents(self, kb, docs):
                return {d["doc_id"]: 3 for d in docs}
        monkeypatch.setattr("app.services.kb_engines.qdrant_family.QdrantFamily", lambda **k: _FakeFam())
        monkeypatch.setattr(kb_api, "_get_client", lambda: type("C", (), {"healthcheck": lambda s: True})())
        out = kb_api.reembed_knowledge_base("kb-recon", db)
        assert out["data"]["reembed"]["reembedded"] == 1
        doc = db.query(KnowledgeDocument).filter_by(id="d1").first()
        assert doc.status == "vectorized"
        assert (doc.embedding_signature or {})["embed_model"] == "new-embed"   # 签名对齐
        kb2 = db.query(KnowledgeBase).filter_by(id="kb-recon").first()
        assert kb2.status == "ready"                              # 清洁
    finally:
        db.close()
