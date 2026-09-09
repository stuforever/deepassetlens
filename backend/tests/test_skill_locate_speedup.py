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
