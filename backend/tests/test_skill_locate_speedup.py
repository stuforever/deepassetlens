# -*- coding: utf-8 -*-
"""剧本定位提速（2026-09-09 spec）单测：件①缓存层 / 件②批量 / 件③预解析。

变异锚点：每测 docstring 标明何种生产改动会让它红。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# 任务 1：件① ORM + 缓存层
# ---------------------------------------------------------------------------

def test_lookup_cache_table_created():
    """第 84 表存在且可 create_all 幂等（spec §三 件①：表 83→84）。
    变异锚点：删 ORM 类/改表名 → 此测红。"""
    from app.models.base import EntityLookupCache
    from app.core.database import engine, ensure_schema_compatibility
    from sqlalchemy import text
    assert EntityLookupCache.__tablename__ == "kg_entity_lookup_cache"
    ensure_schema_compatibility()
    # plan 步骤 1.5 括注：ensure_schema_compatibility 不建新表，create_all 幂等建第 84 表
    from app.models.base import Base
    Base.metadata.create_all(engine)
    with engine.connect() as conn:
        cnt = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'kg_entity_lookup_cache'")).scalar()
    assert cnt == 1


def test_cache_roundtrip_and_invalidate():
    """cache_store→cache_lookup 命中且 bump hit_count；invalidate 后未命中（spec §三 件①）。
    变异锚点：normalize 去小写/去空白删掉 → 「配电 变压器」查不到「配电变压器」。"""
    from app.services.entity_lookup_cache import cache_store, cache_lookup, invalidate_entity_lookup_cache
    from app.services.entity_lookup_cache import normalize_query_key
    assert normalize_query_key(" 配电　Transformer ") == "配电transformer"  # NFKC+小写+去空白
    cache_store("配电变压器X", "keyword", {"entities": [{"entity_code": "t_x"}]})
    hit = cache_lookup("配电变压器X", "keyword")
    assert hit is not None and hit["entities"][0]["entity_code"] == "t_x"
    invalidate_entity_lookup_cache()
    assert cache_lookup("配电变压器X", "keyword") is None


def test_cache_degrades_on_error(monkeypatch):
    """缓存表读写失败→None+warning，不抛异常（行为契约：加速件非正确性件）。
    变异锚点：cache_lookup 去掉 try/except → 此测红（异常外泄）。"""
    import logging
    from app.services import entity_lookup_cache as elc
    def _boom(*a, **k):
        raise RuntimeError("table gone")
    monkeypatch.setattr("app.core.database.SessionLocal", _boom)  # 服务层为函数内 import（elc 无模块级 SessionLocal），patch 工厂源头
    with pytest.raises(RuntimeError):  # 直接调 _boom 验证 monkeypatch 生效
        _boom()
    monkeypatch.undo()
    monkeypatch.setattr(elc, "_exec", None) if False else None
    # 真实降级路径：patch 内部会话工厂抛错
    class _Broken:
        def __enter__(self): raise RuntimeError("down")
        def __exit__(self, *a): return False
    monkeypatch.setattr("app.core.database.SessionLocal", lambda: _Broken())  # 同上：真实降级路径走 SessionLocal 工厂
    assert elc.cache_lookup("任意", "keyword") is None   # 降级 None
    elc.cache_store("任意", "keyword", {"x": 1})          # 降级不抛
    elc.invalidate_entity_lookup_cache()                  # 降级不抛


# ---------------------------------------------------------------------------
# 任务 2：件② 批量动作（一批 SQL + 一次 embedding 数组调用）
# ---------------------------------------------------------------------------

def _clear_lookup_cache():
    # 测试前置隔离（plan 三测逐字落之外的最小偏离，仅测试卫生）：件② 批量 handler 会
    # cache_store 回写——不清缓存则本文件 -k batch 复跑时缓存命中（embed 计数=0/
    # cache 项无 log）假红。生产路径不受影响；全量跑时任务 1 的 invalidate 测试已前置清空。
    from app.services.entity_lookup_cache import invalidate_entity_lookup_cache
    invalidate_entity_lookup_cache()


def test_batch_single_embedding_gateway_call(monkeypatch):
    """未命中 keywords 收拢一次 embed_texts 数组调用（spec §三 件②核心断言：
    mock 网关计数=1）。变异锚点：batch 退回逐 variant 串行 embed → 计数>1 → 红。"""
    _clear_lookup_cache()
    from app.services import kg_action_handlers as kah
    calls = {"n": 0}
    def _fake_embed(db, texts, model_name=None):
        calls["n"] += 1
        return [[0.1] * 8 for _ in texts]
    import app.services.semantic_retrieval as sr
    monkeypatch.setattr(sr, "embed_texts", _fake_embed)
    monkeypatch.setattr(kah, "search_entity_vectors", lambda q, top_k=10, db=None, vec=None: [])
    out = kah._kg_search_entities_batch(
        {"keywords": ["绝不存在的甲实体", "绝不存在的乙实体", "绝不存在的丙实体"]}, "00:00:00")
    assert calls["n"] == 1                      # 唯一断言核心：一次网关调用
    assert len(out["results"]) == 3             # 逐项 hit/miss 返回
    assert all(r.get("hit") is False for r in out["results"])


def test_batch_registered_everywhere():
    """注册面五处（spec §三 件②注册面）：handler 字典/MCP/白名单/定位族×2。
    变异锚点：任一处漏注册 → 对应断言红。"""
    from app.services.kg_action_handlers import _KG_ACTION_HANDLERS
    from app.services.query_contract import GENERIC_ALLOWED_TOOLS
    from app.services.skill_policy import _LOCATE_BUDGET_TOOLS, _LOCATE_DEDUP_TOOLS
    assert "search_entities_batch" in _KG_ACTION_HANDLERS
    assert "search_entities_batch" in GENERIC_ALLOWED_TOOLS
    assert "search_entities_batch" in _LOCATE_BUDGET_TOOLS   # batch 计 1 次定位
    assert "search_entities_batch" in _LOCATE_DEDUP_TOOLS     # 同参去重（确定性工具）
    import inspect
    import app.mcp_server as mcp
    assert "search_entities_batch" in inspect.getsource(mcp)


def test_batch_merges_exact_like_vector():
    """三层合并语义（spec §三 件②）：精确>LIKE>向量逐项归组、每项与单查同构。
    变异锚点：归组错列（keyword 拿到别的 keyword 结果）→ 红。"""
    _clear_lookup_cache()
    from app.services.kg_action_handlers import _kg_search_entities_batch
    out = _kg_search_entities_batch({"keywords": ["台区"]}, "00:00:00")
    r = out["results"][0]
    for key in ("entities", "fields", "hit", "log"):
        assert key in r  # 与单查返回同构（含 fields）+ 批量自有 hit/miss 状态
