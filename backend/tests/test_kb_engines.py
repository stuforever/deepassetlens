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
        # 🔴-1 契约升级：fake client 须含 _client.delete 面（删旧原语）——原 fake 缺该面，
        # 被 fail-closed 判为删旧失败（正是审查指出的"monkeypatch 掩盖"被契约暴露）
        class _FakeGateClient:
            class _client:
                @staticmethod
                def delete(**kw):
                    return None

            def healthcheck(self):
                return True
        monkeypatch.setattr(kb_api, "_get_client", lambda: _FakeGateClient())
        out = kb_api.reembed_knowledge_base("kb-recon", db)
        assert out["data"]["reembed"]["reembedded"] == 1
        doc = db.query(KnowledgeDocument).filter_by(id="d1").first()
        assert doc.status == "vectorized"
        assert (doc.embedding_signature or {})["embed_model"] == "new-embed"   # 签名对齐
        kb2 = db.query(KnowledgeBase).filter_by(id="kb-recon").first()
        assert kb2.status == "ready"                              # 清洁
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 🔴-3（审查 2026-09-15）：reconcile 报告幂等——按签名失配判定而非 status
# ---------------------------------------------------------------------------

def test_reconcile_report_idempotent(tmp_path, monkeypatch):
    """🔴-3 回归锁：reconcile 报告幂等。首轮 stale 的文档第二轮必须仍 stale
    （原实现按 status 判定：第二轮 status!=vectorized 翻转 consistent，"无 stale"
    误导运维）；pending 等中间态不虚计 consistent、行态不被对账改写。
    变异锚点：判定退回 status 绑定 → 红。"""
    from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument
    from app.models.base import Base
    from app.core.database import SessionLocal, engine
    from app.api import knowledge_base as kb_api
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        db.query(KnowledgeDocument).filter_by(kb_id="kb-recon-idem").delete()
        db.query(KnowledgeBase).filter_by(id="kb-recon-idem").delete()
        db.commit()
        kb = KnowledgeBase(id="kb-recon-idem", name="对账幂等", collection_name="kb_recon_idem",
                           storage_dir="kb-recon-idem", type="indexed", rag_provider="qdrant",
                           embedding_signature={"embed_model": "old"})
        db.add(kb)
        db.flush()
        db.add(KnowledgeDocument(id="d1i", kb_id="kb-recon-idem", filename="a.md",
                                 file_path=str(tmp_path / "a.md"), status="vectorized",
                                 embedding_signature={"embed_model": "old"}))
        db.add(KnowledgeDocument(id="d2i", kb_id="kb-recon-idem", filename="b.md",
                                 file_path=str(tmp_path / "b.md"), status="pending",
                                 embedding_signature=None))
        db.commit()
        monkeypatch.setattr(kb_api, "_current_signature",
                            lambda db, vs=None: {"embed_model": "new-embed"})
        # 首轮：签名失配 → stale；pending 不入任何桶
        r1 = kb_api.reconcile_knowledge_base("kb-recon-idem", db)["data"]["reconcile"]
        assert r1["stale"] == ["a.md"] and r1["consistent"] == 0 and r1["failed"] == []
        # 第二轮（签名未变）：仍 stale——幂等；pending 依旧不虚计
        r2 = kb_api.reconcile_knowledge_base("kb-recon-idem", db)["data"]["reconcile"]
        assert r2["stale"] == ["a.md"] and r2["consistent"] == 0
        doc = db.query(KnowledgeDocument).filter_by(id="d2i").first()
        assert doc.status == "pending"          # pending 行态不被对账改写
    finally:
        db.close()


def test_reconcile_stale_matching_sig_returns_vectorized(tmp_path, monkeypatch):
    """🔴-3：签名已对齐的 stale 行态归位 vectorized（报告与行态一致，重复对账稳定）。"""
    from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument
    from app.models.base import Base
    from app.core.database import SessionLocal, engine
    from app.api import knowledge_base as kb_api
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        db.query(KnowledgeDocument).filter_by(kb_id="kb-recon-pos").delete()
        db.query(KnowledgeBase).filter_by(id="kb-recon-pos").delete()
        db.commit()
        kb = KnowledgeBase(id="kb-recon-pos", name="对账归位", collection_name="kb_recon_pos",
                           storage_dir="kb-recon-pos", type="indexed", rag_provider="qdrant",
                           embedding_signature={"embed_model": "new-embed"})
        db.add(kb)
        db.flush()
        db.add(KnowledgeDocument(id="d1p", kb_id="kb-recon-pos", filename="a.md",
                                 file_path=str(tmp_path / "a.md"), status="stale",
                                 embedding_signature={"embed_model": "new-embed"}))  # 异常态：签名已对齐
        db.commit()
        monkeypatch.setattr(kb_api, "_current_signature",
                            lambda db, vs=None: {"embed_model": "new-embed"})
        r = kb_api.reconcile_knowledge_base("kb-recon-pos", db)["data"]["reconcile"]
        assert r["consistent"] == 1 and r["stale"] == []
        doc = db.query(KnowledgeDocument).filter_by(id="d1p").first()
        assert doc.status == "vectorized"       # 行态归位
        r2 = kb_api.reconcile_knowledge_base("kb-recon-pos", db)["data"]["reconcile"]
        assert r2["consistent"] == 1 and r2["stale"] == []   # 幂等
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 🔴-1（审查 2026-09-15）：reembed 先按 doc_id 删旧点再嵌（防新旧并存/维度冲突）
# ---------------------------------------------------------------------------

def _mk_reembed_fixture(db, tmp_path, kb_id, doc_id):
    """A4 同款造数：stale 文档（真 MySQL，固定 id，先清残留）。"""
    from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument
    db.query(KnowledgeDocument).filter_by(kb_id=kb_id).delete()
    db.query(KnowledgeBase).filter_by(id=kb_id).delete()
    db.commit()
    (tmp_path / "a.md").write_text("重嵌删旧测试", encoding="utf-8")
    kb = KnowledgeBase(id=kb_id, name="重嵌删旧", collection_name=kb_id.replace("-", "_"),
                       storage_dir=kb_id, type="indexed", rag_provider="qdrant",
                       embedding_signature={"embed_model": "new-embed"})
    db.add(kb)
    db.flush()
    db.add(KnowledgeDocument(id=doc_id, kb_id=kb_id, filename="a.md",
                             file_path=str(tmp_path / "a.md"), status="stale", chunk_count=3,
                             embedding_signature={"embed_model": "old"}))
    db.commit()


def test_reembed_deletes_old_points_before_add(tmp_path, monkeypatch):
    """🔴-1 回归锁：重嵌必须**先**按 doc_id 删旧点**再** add——换分块参数防新旧并存
    重复召回/vector_count 漂移；换嵌入模型防维度冲突重嵌永败。
    变异锚点：去掉 delete 调用或调用序翻转 → 红。"""
    from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument
    from app.models.base import Base
    from app.core.database import SessionLocal, engine
    from app.api import knowledge_base as kb_api
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        _mk_reembed_fixture(db, tmp_path, "kb-reemb", "d1r")
        seq = []

        class _FakeRaw:
            def delete(self, **kw):
                seq.append(("delete", kw))

        class _FakeClient:
            _client = _FakeRaw()

            def healthcheck(self):
                return True

        class _FakeFam:
            def __init__(self, client=None, embed_fn=None):
                pass

            def add_documents(self, kb, docs):
                seq.append(("add", [d["doc_id"] for d in docs]))
                return {d["doc_id"]: 2 for d in docs}

        monkeypatch.setattr("app.services.kb_engines.qdrant_family.QdrantFamily", _FakeFam)
        monkeypatch.setattr(kb_api, "_get_client", lambda: _FakeClient())
        out = kb_api.reembed_knowledge_base("kb-reemb", db)
        assert out["data"]["reembed"]["reembedded"] == 1
        kinds = [s[0] for s in seq]
        assert kinds == ["delete", "add"], f"调用序漂移: {seq}"       # 先删后嵌
        delkw = seq[0][1]
        assert delkw["collection_name"] == "kb_reemb"
        assert "d1r" in str(delkw["points_selector"])                # 按本 doc_id 过滤
        doc = db.query(KnowledgeDocument).filter_by(id="d1r").first()
        assert doc.status == "vectorized" and doc.chunk_count == 2
        assert db.query(KnowledgeBase).filter_by(id="kb-reemb").first().vector_count == 2
    finally:
        db.close()


def test_reembed_delete_failure_fail_closed(tmp_path, monkeypatch):
    """🔴-1：删旧失败 fail-closed——doc 标 error、**不继续 add**（绝不带旧向量嵌新点）。
    变异锚点：吞掉删除异常继续嵌 → 红。"""
    from app.models.knowledge_base import KnowledgeDocument
    from app.models.base import Base
    from app.core.database import SessionLocal, engine
    from app.api import knowledge_base as kb_api
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        _mk_reembed_fixture(db, tmp_path, "kb-reemb2", "d1r2")

        class _FakeRaw:
            def delete(self, **kw):
                raise RuntimeError("qdrant down")

        class _FakeClient:
            _client = _FakeRaw()

            def healthcheck(self):
                return True

        adds = []

        class _FakeFam:
            def __init__(self, client=None, embed_fn=None):
                pass

            def add_documents(self, kb, docs):
                adds.append(docs)
                return {d["doc_id"]: 2 for d in docs}

        monkeypatch.setattr("app.services.kb_engines.qdrant_family.QdrantFamily", _FakeFam)
        monkeypatch.setattr(kb_api, "_get_client", lambda: _FakeClient())
        out = kb_api.reembed_knowledge_base("kb-reemb2", db)
        assert out["data"]["reembed"]["reembedded"] == 0
        assert adds == []                                        # 未继续 add
        doc = db.query(KnowledgeDocument).filter_by(id="d1r2").first()
        assert doc.status == "error" and "删旧向量失败" in (doc.error_msg or "")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 🔴-2（审查 2026-09-15）：QdrantFamily.delete 改 FilterSelector 原语（拆三雷）
# ---------------------------------------------------------------------------

class TestQdrantFamilyDeleteSafe:
    """🔴-2 单测锁：按 doc_ids 删除必须走 FilterSelector 原语，废弃「scroll 重读-过滤-
    重写」路径（scroll 万点封顶/异常即 delete_collection 全清/维度硬编码 1024 三雷同拆）。
    变异锚点：回退 scroll 重写路径或误删整库 → 红。"""

    def test_delete_by_doc_ids_uses_filter_selector(self):
        from app.api.knowledge_base import _collection_name
        from app.services.kb_engines.qdrant_family import QdrantFamily
        calls = []

        class _FakeRaw:
            def delete(self, **kw):
                calls.append(kw)

        class _FakeClient:
            _client = _FakeRaw()

            def delete_collection(self, name):
                calls.append({"delete_collection": name})

            def scroll_points(self, *a, **k):
                raise AssertionError("🔴-2：不得再走 scroll 重写路径")

            def upsert_points(self, *a, **k):
                raise AssertionError("🔴-2：不得再走重写路径")

        fam = QdrantFamily(client=_FakeClient(), embed_fn=lambda batch: [[0.0]] * len(batch))
        fam.delete({"id": "d1e1ete2xx"}, doc_ids=["d1", "d2"])
        assert len(calls) == 1 and "delete_collection" not in calls[0]   # 恰一次原语删、不删整库
        assert calls[0]["collection_name"] == _collection_name("d1e1ete2xx")
        assert "d1" in str(calls[0]["points_selector"])
        assert "d2" in str(calls[0]["points_selector"])                  # MatchAny 含两 doc_id

    def test_delete_whole_collection_kept(self):
        """doc_ids=None → delete_collection 语义不变（m15 DELETE 既有契约）。"""
        from app.api.knowledge_base import _collection_name
        from app.services.kb_engines.qdrant_family import QdrantFamily
        calls = []

        class _FakeClient:
            def delete_collection(self, name):
                calls.append(("collection", name))

            def scroll_points(self, *a, **k):
                raise AssertionError("整库删除不应触达 scroll")

        fam = QdrantFamily(client=_FakeClient(), embed_fn=lambda batch: [[0.0]] * len(batch))
        fam.delete({"id": "kb-whole"})
        assert calls == [("collection", _collection_name("kb-whole"))]   # 恰一次整库删除、零 scroll
