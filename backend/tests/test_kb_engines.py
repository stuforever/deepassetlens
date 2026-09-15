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
            def delete(self, kb, doc_ids=None):
                pass   # I4：删点原语收编 fam.delete（成功=无操作）

            def add_documents(self, kb, docs):
                return {d["doc_id"]: 3 for d in docs}
        monkeypatch.setattr("app.services.kb_engines.qdrant_family.QdrantFamily", lambda **k: _FakeFam())

        class _FakeGateClient:
            def healthcheck(self):
                return True

            def collection_info(self, name):
                return None   # C1 预检面：无既有 collection → 不触发重建
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
                           embedding_signature={"embed_model": "new-embed"}, status="degraded")
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
        kb1 = db.query(KnowledgeBase).filter_by(id="kb-recon-pos").first()
        assert kb1.status == "ready"            # I3：归位后收回 degraded（不粘滞）
        r2 = kb_api.reconcile_knowledge_base("kb-recon-pos", db)["data"]["reconcile"]
        assert r2["consistent"] == 1 and r2["stale"] == []   # 幂等
        assert db.query(KnowledgeBase).filter_by(id="kb-recon-pos").first().status == "ready"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# 🔴-1（审查 2026-09-15）：reembed 先按 doc_id 删旧点再嵌（防新旧并存/维度冲突）
# ---------------------------------------------------------------------------

def _mk_reembed_fixture(db, tmp_path, kb_id, doc_id, kb_sig=None, doc_sig=None):
    """A4 同款造数：stale 文档（真 MySQL，固定 id，先清残留）。"""
    from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument
    from app.api.knowledge_base import _collection_name
    db.query(KnowledgeDocument).filter_by(kb_id=kb_id).delete()
    db.query(KnowledgeBase).filter_by(id=kb_id).delete()
    db.commit()
    (tmp_path / "a.md").write_text("重嵌删旧测试", encoding="utf-8")
    # 集合名列与生产同源（_collection_name，I4/C1 口径收敛——不再用 replace 偶然推导）
    kb = KnowledgeBase(id=kb_id, name="重嵌删旧", collection_name=_collection_name(kb_id),
                       storage_dir=kb_id, type="indexed", rag_provider="qdrant",
                       embedding_signature=kb_sig or {"embed_model": "new-embed"})
    db.add(kb)
    db.flush()
    db.add(KnowledgeDocument(id=doc_id, kb_id=kb_id, filename="a.md",
                             file_path=str(tmp_path / "a.md"), status="stale", chunk_count=3,
                             embedding_signature=doc_sig or {"embed_model": "old"}))
    db.commit()


def test_reembed_dimension_change_rebuilds_collection(tmp_path, monkeypatch):
    """C1（复审 2026-09-15）：跨维度重嵌必须先按新签名 KB 级重建 collection——否则
    删旧点成功→新维度 upsert 被 Qdrant 拒（ensure_collection 显式拒绝尺寸不一致）→
    旧索引已丢=「失败即丢索引」回归面，且与 spec D8「维度变更→reembed→报告清洁」相悖。
    场景：collection 维度=旧(4) / 当前签名维度=新(8)。断言：①ensure_collection 以新
    维度调用（重建）；②文档终态 vectorized+签名对齐；③reembedded 计数正确。
    变异锚点：去掉维度预检即红（ensure 不被调用）。"""
    from app.api.knowledge_base import _collection_name
    from app.models.knowledge_base import KnowledgeDocument
    from app.models.base import Base
    from app.core.database import SessionLocal, engine
    from app.api import knowledge_base as kb_api
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        _mk_reembed_fixture(
            db, tmp_path, "kb-reemb3", "d1r3",
            kb_sig={"embed_model": "new-embed", "vector_size": 8,
                    "chunk_size": 500, "chunk_overlap": 50},
            doc_sig={"embed_model": "old", "vector_size": 4})
        ops, adds = [], []

        class _FakeClient:
            def healthcheck(self):
                return True

            def collection_info(self, name):
                return {"config": {"params": {"vectors": {"size": 4}}}}   # 旧维度

            def delete_collection(self, name):
                ops.append(("del_coll", name))

            def ensure_collection(self, name, vector_size=1024, distance="Cosine", recreate=False):
                ops.append(("ensure", name, vector_size))

        class _FakeFam:
            def __init__(self, client=None, embed_fn=None):
                pass

            def delete(self, kb, doc_ids=None):
                ops.append(("del_points", doc_ids))   # I4：原语收编 fam.delete

            def add_documents(self, kb, docs):
                adds.append(docs)
                return {d["doc_id"]: 2 for d in docs}

        monkeypatch.setattr("app.services.kb_engines.qdrant_family.QdrantFamily", _FakeFam)
        monkeypatch.setattr(kb_api, "_get_client", lambda: _FakeClient())
        monkeypatch.setattr(kb_api, "_current_signature", lambda db, vs=None: {
            "embed_model": "new-embed", "vector_size": 8,
            "chunk_size": 500, "chunk_overlap": 50})
        out = kb_api.reembed_knowledge_base("kb-reemb3", db)
        assert out["data"]["reembed"]["reembedded"] == 1
        # ① KB 级重建：删 collection+按新签名 ensure（集合名与 fam 写入口径同源）
        assert ("del_coll", _collection_name("kb-reemb3")) in ops, f"未重建 collection: {ops}"
        assert ("ensure", _collection_name("kb-reemb3"), 8) in ops, f"ensure 未按新维度: {ops}"
        # ② 文档终态
        doc = db.query(KnowledgeDocument).filter_by(id="d1r3").first()
        assert doc.status == "vectorized"
        assert (doc.embedding_signature or {}).get("vector_size") == 8
        # ③ 计数
        assert adds and adds[0][0]["doc_id"] == "d1r3"
    finally:
        db.close()


def test_reembed_dimension_change_reembeds_all_docs(tmp_path, monkeypatch):
    """C2（勾验撤回条款 2026-09-15）：混合候选+维度变更——重建清空整库后必须**全量**
    重嵌（等价 vectorize 语义）。场景：A=vectorized 旧签名（不在常规候选集）+ B=stale，
    维度变更 4→8 → 断言 A 亦被重嵌归位。变异锚点：候选集不随重建扩 → A 的旧向量已被
    整库清空却不再生（静默丢索引：status 仍 vectorized、检索查不到）→ 本测红。"""
    from app.api.knowledge_base import _collection_name
    from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument
    from app.models.base import Base
    from app.core.database import SessionLocal, engine
    from app.api import knowledge_base as kb_api
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        db.query(KnowledgeDocument).filter_by(kb_id="kb-reemb4").delete()
        db.query(KnowledgeBase).filter_by(id="kb-reemb4").delete()
        db.commit()
        (tmp_path / "a.md").write_text("混合候选甲", encoding="utf-8")
        (tmp_path / "b.md").write_text("混合候选乙", encoding="utf-8")
        db.add(KnowledgeBase(id="kb-reemb4", name="混合候选", collection_name=_collection_name("kb-reemb4"),
                             storage_dir="kb-reemb4", type="indexed", rag_provider="qdrant",
                             embedding_signature={"embed_model": "old", "vector_size": 4}))
        db.flush()
        db.add(KnowledgeDocument(id="d1ra", kb_id="kb-reemb4", filename="a.md",
                                 file_path=str(tmp_path / "a.md"), status="vectorized", chunk_count=3,
                                 embedding_signature={"embed_model": "old", "vector_size": 4}))
        db.add(KnowledgeDocument(id="d1rb", kb_id="kb-reemb4", filename="b.md",
                                 file_path=str(tmp_path / "b.md"), status="stale", chunk_count=2,
                                 embedding_signature={"embed_model": "old", "vector_size": 4}))
        db.commit()
        adds = []

        class _FakeClient:
            def healthcheck(self):
                return True

            def collection_info(self, name):
                return {"config": {"params": {"vectors": {"size": 4}}}}   # 旧维度 → 触发重建

            def delete_collection(self, name):
                pass

            def ensure_collection(self, name, vector_size=1024, distance="Cosine", recreate=False):
                pass

        class _FakeFam:
            def __init__(self, client=None, embed_fn=None):
                pass

            def delete(self, kb, doc_ids=None):
                pass

            def add_documents(self, kb, docs):
                adds.extend(d["doc_id"] for d in docs)
                return {d["doc_id"]: 2 for d in docs}

        monkeypatch.setattr("app.services.kb_engines.qdrant_family.QdrantFamily", _FakeFam)
        monkeypatch.setattr(kb_api, "_get_client", lambda: _FakeClient())
        monkeypatch.setattr(kb_api, "_current_signature", lambda db, vs=None: {
            "embed_model": "new-embed", "vector_size": 8,
            "chunk_size": 500, "chunk_overlap": 50})
        out = kb_api.reembed_knowledge_base("kb-reemb4", db)
        # C2：重建路径全量重嵌——A（vectorized 旧签名、不在常规候选集）也必须重嵌归位
        assert out["data"]["reembed"]["reembedded"] == 2
        assert set(adds) == {"d1ra", "d1rb"}, f"重嵌集漂移: {adds}"
        a = db.query(KnowledgeDocument).filter_by(id="d1ra").first()
        assert a.status == "vectorized" and (a.embedding_signature or {}).get("vector_size") == 8
        b = db.query(KnowledgeDocument).filter_by(id="d1rb").first()
        assert b.status == "vectorized"
    finally:
        db.close()


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

        class _FakeClient:
            def healthcheck(self):
                return True

            def collection_info(self, name):
                return None   # C1 预检面：无既有 collection → 不触发重建

        class _FakeFam:
            def __init__(self, client=None, embed_fn=None):
                pass

            def delete(self, kb, doc_ids=None):
                # I4：删除原语收编 fam.delete——记录 (kb_dict, doc_ids)
                seq.append(("delete", kb, doc_ids))

            def add_documents(self, kb, docs):
                seq.append(("add", [d["doc_id"] for d in docs]))
                return {d["doc_id"]: 2 for d in docs}

        monkeypatch.setattr("app.services.kb_engines.qdrant_family.QdrantFamily", _FakeFam)
        monkeypatch.setattr(kb_api, "_get_client", lambda: _FakeClient())
        out = kb_api.reembed_knowledge_base("kb-reemb", db)
        assert out["data"]["reembed"]["reembedded"] == 1
        kinds = [s[0] for s in seq]
        assert kinds == ["delete", "add"], f"调用序漂移: {seq}"       # 先删后嵌
        # I4：删点走 fam.delete（同一封装/同一集合名口径）——kb id 与 doc_ids 逐项对上
        _dkb, _ddocs = seq[0][1], seq[0][2]
        assert _dkb.get("id") == "kb-reemb"
        assert _ddocs == ["d1r"]
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

        class _FakeClient:
            def healthcheck(self):
                return True

            def collection_info(self, name):
                return None   # C1 预检面：无既有 collection → 不触发重建

        adds = []

        class _FakeFam:
            _boom = True   # 类属性开关（reembed 每次新建实例，实例属性会被重置）

            def __init__(self, client=None, embed_fn=None):
                pass

            def delete(self, kb, doc_ids=None):
                # I2：删点走 fam.delete——失败模拟在原语层（fail-closed 语义不变）
                if _FakeFam._boom:
                    raise RuntimeError("qdrant down")

            def add_documents(self, kb, docs):
                adds.append(docs)
                return {d["doc_id"]: 2 for d in docs}

        monkeypatch.setattr("app.services.kb_engines.qdrant_family.QdrantFamily", _FakeFam)
        monkeypatch.setattr(kb_api, "_get_client", lambda: _FakeClient())
        out = kb_api.reembed_knowledge_base("kb-reemb2", db)
        assert out["data"]["reembed"]["reembedded"] == 0
        assert adds == []                                        # 未继续 add
        failed = out["data"]["reembed"]["failed"]
        assert [f["id"] for f in failed] == ["d1r2"]             # I2：失败清单进响应
        doc = db.query(KnowledgeDocument).filter_by(id="d1r2").first()
        assert doc.status == "stale"                             # I2：保 stale（可重试）
        assert "删旧向量失败" in (doc.error_msg or "")

        # I2 重试性：删除恢复后第二次 reembed 同文档再次入候选并成功归位
        _FakeFam._boom = False
        out2 = kb_api.reembed_knowledge_base("kb-reemb2", db)
        assert out2["data"]["reembed"]["reembedded"] == 1
        assert out2["data"]["reembed"]["failed"] == []
        doc2 = db.query(KnowledgeDocument).filter_by(id="d1r2").first()
        assert doc2.status == "vectorized" and doc2.error_msg is None
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
        from qdrant_client.models import UpdateResult, UpdateStatus
        from app.api.knowledge_base import _collection_name
        from app.services.kb_engines.qdrant_family import QdrantFamily
        calls = []

        class _FakeRaw:
            def delete(self, **kw):
                calls.append(kw)
                return UpdateResult(operation_id=1, status=UpdateStatus.COMPLETED)

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

    def test_delete_acknowledged_not_confirmed_fail_closed(self):
        """I1（复审 2026-09-15）：显式 wait=True + 返回值校验——ACKNOWLEDGED（受理未落盘）
        必须 fail-closed，fail-closed 不能只认异常不认返回值（靠库默认值撑不住契约）。
        变异锚点：去掉 status 校验或丢掉 wait=True 即红。"""
        from qdrant_client.models import UpdateResult, UpdateStatus
        from app.services.kb_engines.qdrant_family import QdrantFamily
        kw_seen = {}

        class _FakeRaw:
            def delete(self, **kw):
                kw_seen.update(kw)
                return UpdateResult(operation_id=2, status=UpdateStatus.ACKNOWLEDGED)

        class _FakeClient:
            _client = _FakeRaw()

        fam = QdrantFamily(client=_FakeClient(), embed_fn=lambda batch: [[0.0]] * len(batch))
        with pytest.raises(RuntimeError, match="未确认完成"):
            fam.delete({"id": "kb-i1"}, doc_ids=["x"])
        assert kw_seen.get("wait") is True          # 显式等待进原语参数


# ---------------------------------------------------------------------------
# T3（复审 2026-09-15）：端点级 smoke——reconcile/reembed 404/422/502 三分支
# （子 router 挂最小 FastAPI=m02 判例，规避全 app lifespan；TestClient 不抛服务器异常）
# ---------------------------------------------------------------------------

def test_reconcile_reembed_endpoint_smoke(tmp_path, monkeypatch):
    """端点级三分支：404 不存在 / 422 指针型无重嵌语义 / 502 qdrant 不可用。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.api import knowledge_base as kb_api
    from app.api.knowledge_base import router as kb_router
    from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument
    from app.models.base import Base
    from app.core.database import SessionLocal, engine

    app = FastAPI()
    app.include_router(kb_router)
    client = TestClient(app, raise_server_exceptions=False)

    # 404：reconcile/reembed 打不存在的 KB
    assert client.post("/api/v1/knowledge-bases/nope/reconcile").status_code == 404
    assert client.post("/api/v1/knowledge-bases/nope/reembed").status_code == 404

    # 422/502：造 connected 型 KB（reembed 拒绝）+ 真实 KB（qdrant 不可用 → 502）
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        db.query(KnowledgeBase).filter_by(id="kb-smoke-conn").delete()
        db.query(KnowledgeBase).filter_by(id="kb-smoke-idx").delete()
        db.commit()
        db.add(KnowledgeBase(id="kb-smoke-conn", name="指针型", collection_name="kb_smokeconn",
                             storage_dir="kb-smoke-conn", type="connected", rag_provider="qdrant"))
        db.add(KnowledgeBase(id="kb-smoke-idx", name="自建型", collection_name="kb_smokeidx",
                             storage_dir="kb-smoke-idx", type="indexed", rag_provider="qdrant"))
        db.flush()
        db.add(KnowledgeDocument(id="d-smoke-s", kb_id="kb-smoke-idx", filename="s.md",
                                 file_path=str(tmp_path / "s.md"), status="stale", chunk_count=1))
        db.commit()

        r = client.post("/api/v1/knowledge-bases/kb-smoke-conn/reembed")
        assert r.status_code == 422 and "指针型" in r.json()["detail"]
        r = client.post("/api/v1/knowledge-bases/kb-smoke-conn/reconcile")
        assert r.status_code == 422 and "指针型" in r.json()["detail"]

        monkeypatch.setattr(kb_api, "_get_client", lambda: type("_Down", (), {
            "healthcheck": lambda self: False})())
        r = client.post("/api/v1/knowledge-bases/kb-smoke-idx/reembed")
        assert r.status_code == 502 and "qdrant_unavailable" in r.json()["detail"]
    finally:
        db.query(KnowledgeDocument).filter_by(kb_id="kb-smoke-idx").delete()
        db.query(KnowledgeBase).filter_by(id="kb-smoke-conn").delete()
        db.query(KnowledgeBase).filter_by(id="kb-smoke-idx").delete()
        db.commit()
        db.close()
