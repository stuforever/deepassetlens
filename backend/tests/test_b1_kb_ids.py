# -*- coding: utf-8 -*-
"""B1（v4§八）契约测试：ChatRequest.kb_ids 检索过滤 + kb 列表名称。

先红后绿（TDD）——实现前运行应 ImportError/AttributeError 失败：
- 选 1 库只查该库
- None/空 = 全库不过滤
- 不存在 id → 跳过不报错（空结果）
- ChatRequest 接受 kb_ids（None 默认）
- kb 列表出参含 name（禁裸 UUID）
服务层单测：直接构造 ORM 行（MySQL 真库固定 id），QdrantFamily 打桩确定性返回。
"""
import pytest


@pytest.fixture()
def two_kbs():
    """固定 id 两个知识库（真库，跑完清理）。"""
    from app.models.knowledge_base import KnowledgeBase
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        for kid in ("kb-b1-a", "kb-b1-b"):
            db.query(KnowledgeBase).filter_by(id=kid).delete()
        db.commit()
        db.add(KnowledgeBase(id="kb-b1-a", name="B1测试库A", collection_name="kb_b1_a",
                             storage_dir="kb-b1-a", type="indexed", rag_provider="qdrant"))
        db.add(KnowledgeBase(id="kb-b1-b", name="B1测试库B", collection_name="kb_b1_b",
                             storage_dir="kb-b1-b", type="indexed", rag_provider="qdrant"))
        db.commit()
        yield ["kb-b1-a", "kb-b1-b"]
    finally:
        for kid in ("kb-b1-a", "kb-b1-b"):
            db.query(KnowledgeBase).filter_by(id=kid).delete()
        db.commit()
        db.close()


@pytest.fixture()
def stub_qdrant(monkeypatch):
    """QdrantFamily 打桩：search 按 kb_ref['id'] 返回确定性命中。"""
    class _StubFam:
        def __init__(self, *a, **k):
            pass

        def search(self, kb_ref, query, top_k=6):
            return [{"text": f"hit::{kb_ref['id']}::{query}", "score": 0.9,
                     "payload": {"filename": "f.md", "chunk_idx": 0}}]
    monkeypatch.setattr("app.services.kb_engines.qdrant_family.QdrantFamily", _StubFam)


def test_single_kb_only_queries_selected(two_kbs, stub_qdrant):
    """选 1 库 → 只返回该库命中块。"""
    from app.services.kb_query import kb_search_filtered
    out = kb_search_filtered("测试问题", ["kb-b1-a"], top_k=6)
    assert len(out) == 1
    assert out[0]["kb_id"] == "kb-b1-a"
    assert out[0]["kb_name"] == "B1测试库A"
    assert out[0]["matches"][0]["text"] == "hit::kb-b1-a::测试问题"


def test_none_means_all_kbs(two_kbs, stub_qdrant):
    """None = 全库不过滤（夹具两库都必须命中；真库可能有其他库=超集即可）。"""
    from app.services.kb_query import kb_search_filtered
    out = kb_search_filtered("测试问题", None, top_k=6)
    ids = {r["kb_id"] for r in out}
    assert {"kb-b1-a", "kb-b1-b"} <= ids
    out2 = kb_search_filtered("测试问题", [], top_k=6)
    assert {"kb-b1-a", "kb-b1-b"} <= {r["kb_id"] for r in out2}


def test_missing_kb_id_skipped_no_error(two_kbs, stub_qdrant):
    """不存在的 id → 跳过不报错（只回存在的库）。"""
    from app.services.kb_query import kb_search_filtered
    out = kb_search_filtered("测试问题", ["kb-b1-a", "kb-nonexistent-xyz"], top_k=6)
    assert [r["kb_id"] for r in out] == ["kb-b1-a"]


def test_chat_request_accepts_kb_ids():
    """ChatRequest.kb_ids 默认 None、可传列表（None/空=不过滤语义由检索层承担）。"""
    from app.api.data_intelligence import ChatRequest
    req = ChatRequest(user_input="q")
    assert req.kb_ids is None
    req2 = ChatRequest(user_input="q", kb_ids=["kb-b1-a"])
    assert req2.kb_ids == ["kb-b1-a"]


def test_kb_list_dict_contains_name(two_kbs):
    """知识库列表出参含 name（禁裸 UUID——v4§八）。"""
    from app.api.knowledge_base import _kb_to_dict
    from app.models.knowledge_base import KnowledgeBase
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        kb = db.query(KnowledgeBase).filter_by(id="kb-b1-a").first()
        d = _kb_to_dict(kb)
        assert d["id"] == "kb-b1-a"
        assert d["name"] == "B1测试库A"
    finally:
        db.close()


def test_freeplan_prep_injects_kb_blocks(two_kbs, stub_qdrant, monkeypatch):
    """freeplan prep：req.kb_ids 非空 → HumanMessage 前置 KB 检索块；None → 不注入。"""
    import asyncio
    from types import SimpleNamespace
    from app.api.freeplan.prep import run_prep

    class _FakeAgent:
        async def aget_state(self, config):
            return SimpleNamespace(values={})

        async def aupdate_state(self, config, patch):
            return None

    req = SimpleNamespace(
        thread_id="t-b1", user_input="测试问题", expert_id="wenshu",
        llm_connection_id=None, kb_ids=["kb-b1-a"],
    )
    # 路由降级路径（router 异常→fallback contract）不影响注入断言
    prep = asyncio.run(run_prep(req=req, agent=_FakeAgent(), memory_thread_id="t-b1",
                                prep_timing={}))
    human = [m for m in prep.input_messages if type(m).__name__ == "HumanMessage"]
    assert human, "必须存在 HumanMessage"
    content = human[0].content if isinstance(human[0].content, str) else str(human[0].content)
    assert "hit::kb-b1-a::" in content
    assert "B1测试库A" in content

    req_none = SimpleNamespace(
        thread_id="t-b1", user_input="测试问题", expert_id="wenshu",
        llm_connection_id=None, kb_ids=None,
    )
    prep2 = asyncio.run(run_prep(req=req_none, agent=_FakeAgent(), memory_thread_id="t-b1",
                                 prep_timing={}))
    human2 = [m for m in prep2.input_messages if type(m).__name__ == "HumanMessage"]
    content2 = human2[0].content if isinstance(human2[0].content, str) else str(human2[0].content)
    assert "hit::kb-b1-a::" not in content2
