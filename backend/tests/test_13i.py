# -*- coding: utf-8 -*-
"""批13-I C4 LLM 前缀缓存观测落库 单测。

- contextvar 桥：_log_cache_usage 探测到缓存字段 -> set -> get_last_llm_cache 可读
- record_query_log 落库附列（cache_hit_tokens/cache_miss_tokens）
- 未透传网关：不 set -> 落库 NULL（降级 TTFT 基线，设计允许）
"""
import json
from types import SimpleNamespace

import pytest

from app.services import llm_client


def test_桥默认None():
    """未发生 LLM 调用时读桥返回 None（execute 落库 NULL 语义）。"""
    old = dict(llm_client._LAST_LLM_CACHE)
    try:
        llm_client._LAST_LLM_CACHE["cache_hit_tokens"] = None
        llm_client._LAST_LLM_CACHE["cache_miss_tokens"] = None
        assert llm_client.get_last_llm_cache() is None
    finally:
        llm_client._LAST_LLM_CACHE.update(old)


def test_探测到缓存字段set桥():
    """_log_cache_usage 收到 cache_hit_tokens -> 观测单值可读（hit/miss 两值）。"""
    old = dict(llm_client._LAST_LLM_CACHE)
    try:
        llm_client._log_cache_usage(
            {"cache_hit_tokens": 8192, "cache_miss_tokens": 2341, "prompt_tokens": 10533},
            conn_name="test")
        v = llm_client.get_last_llm_cache()
        assert v == {"cache_hit_tokens": 8192, "cache_miss_tokens": 2341}
    finally:
        llm_client._LAST_LLM_CACHE.update(old)


def test_未透传不set桥():
    """无缓存字段（网关不透传）-> 不写观测单值（降级 TTFT 观测）。"""
    old = dict(llm_client._LAST_LLM_CACHE)
    try:
        llm_client._LAST_LLM_CACHE["cache_hit_tokens"] = None
        llm_client._LAST_LLM_CACHE["cache_miss_tokens"] = None
        llm_client._log_cache_usage({"total_tokens": 100}, conn_name="test")
        assert llm_client.get_last_llm_cache() is None
    finally:
        llm_client._LAST_LLM_CACHE.update(old)


def test_record_query_log附列(monkeypatch):
    """record_query_log 从观测单值读缓存态附到 EngineQueryLog 行。"""
    from app.services import engine_query_log as eql
    old = dict(llm_client._LAST_LLM_CACHE)
    try:
        llm_client._log_cache_usage(
            {"cache_hit_tokens": 4096, "cache_miss_tokens": 512}, conn_name="test")
        captured = {}

        class _FakeDB:
            def add(self, obj):
                captured["obj"] = obj

            def commit(self):
                captured["committed"] = True

            def close(self):
                pass

        class _FakeSL:
            def __call__(self):
                return _FakeDB()

        import app.core.database as dbmod
        monkeypatch.setattr(dbmod, "SessionLocal", _FakeSL(), raising=False)
        # engine_query_log 内部 from app.core.database import SessionLocal（函数内导入，monkeypatch 生效）
        eql.record_query_log(engine="doris", sql="SELECT 1", rows_returned=1, run_id="r13i")
        obj = captured.get("obj")
        assert obj is not None and captured.get("committed")
        assert obj.cache_hit_tokens == 4096
        assert obj.cache_miss_tokens == 512
        assert obj.run_id == "r13i"
    finally:
        llm_client._LAST_LLM_CACHE.update(old)
