# -*- coding: utf-8 -*-
"""三轨M4（批3.5 热修）：research 双份 result 修复回归。

_agent_text 消费面：content 帧已 1:1 流出全文时，result 帧不得重复并入——
否则 research outline 相位 json.loads 切片横跨双份 JSON 命中 "Extra data" 必炸。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest


class _FakeReq:
    def __init__(self):
        self.skill_code = "sishu/research"
        self.message = "主题"
        self.knowledge_bases = []
        self.tools = []
        self.config = {}
        self._user_prefix = "anonymous"


def _stub_stream(monkeypatch, frames):
    import app.api.dt_agent_orchestrations as dao

    async def _fake_stream(req, session_id, turn_id, parts, **kw):
        for f in frames:
            yield f

    monkeypatch.setattr(dao, "_agent_stream", _fake_stream)


def test_agent_text_no_double_result(monkeypatch):
    """content 帧全文 + result 帧全文 → 返回单份（修复前=双份拼接）。"""
    import app.api.dt_agent_orchestrations as dao
    full = "这是研究大纲的完整JSON文本"
    _stub_stream(monkeypatch, [
        {"type": "content", "content": full[:10]},
        {"type": "content", "content": full[10:20]},
        {"type": "content", "content": full[20:]},
        {"type": "result", "content": full},
    ])
    out = asyncio_run(dao._agent_text(_FakeReq(), "s1", "t1", ["p"]))
    assert out == full, f"双份 result 未去重: {out[:60]}..."


def test_agent_text_result_only_kept(monkeypatch):
    """无 content 帧（纯 result 流）→ result 内容保留。"""
    import app.api.dt_agent_orchestrations as dao
    _stub_stream(monkeypatch, [{"type": "result", "content": "纯result文本"}])
    out = asyncio_run(dao._agent_text(_FakeReq(), "s1", "t1", ["p"]))
    assert out == "纯result文本"


def test_agent_text_empty_result_no_junk(monkeypatch):
    """空 result 帧 → 不注入垃圾。"""
    import app.api.dt_agent_orchestrations as dao
    _stub_stream(monkeypatch, [
        {"type": "content", "content": "正文"},
        {"type": "result", "content": ""},
    ])
    out = asyncio_run(dao._agent_text(_FakeReq(), "s1", "t1", ["p"]))
    assert out == "正文"


def test_research_outline_phase_survives(monkeypatch):
    """research outline 相位端到端：双份 JSON 修复后 json.loads 切片可解析。"""
    import json as _json
    import app.api.dt_agent_orchestrations as dao
    outline_obj = {"sections": [{"title": "一、背景", "points": ["a"]},
                                {"title": "二、现状", "points": ["b"]}]}
    single = _json.dumps(outline_obj, ensure_ascii=False)
    # 生产者实况：content 帧=流式分片（此处单帧模拟），result 帧=final_content=同一全文
    _stub_stream(monkeypatch, [
        {"type": "content", "content": single},
        {"type": "result", "content": single},
    ])
    raw = asyncio_run(dao._agent_text(_FakeReq(), "s1", "t1", ["p"]))
    assert raw == single, f"outline_raw 仍为双份: {raw[:80]}"
    parsed = _json.loads(raw)  # 修复前 raw=双份拼接 → "Extra data" 必炸
    assert parsed == outline_obj


def asyncio_run(coro):
    import asyncio
    return asyncio.run(coro)
