# -*- coding: utf-8 -*-
"""笔记本摘要器平台化测试（R6/Wave2）：提示词逐字保留+LLM 链走平台+语义面不变。"""
from __future__ import annotations

import asyncio

from app.services.learning import notebook_summarizer as ns


def test_prompts_verbatim_zh_en():
    """提示词逐字保留（vendor yaml 搬入）：system 首句/模板槽位/record_hints 键集。"""
    assert "notebook summary agent" in ns._PROMPTS["zh"]["system"]
    assert "80-180 字的中文摘要" in ns._PROMPTS["zh"]["user_template"]
    assert "80-180 word summary" in ns._PROMPTS["en"]["user_template"]
    for lang in ("zh", "en"):
        assert {"chat", "tutorbot", "guided_learning", "co_writer", "default"} <= set(
            ns._PROMPTS[lang]["record_hints"])


def test_build_user_prompt_slots():
    p = ns._build_user_prompt(language="zh", title="向量检索", record_type="chat",
                              user_query="q" * 2000, output="o", metadata={"k": 1})
    assert "记录类型：chat" in p
    assert "一段完整聊天历史" in p
    assert "向量检索" in p
    assert "[truncated]" in p  # 超长裁剪生效


def test_clean_summary_text():
    assert ns.clean_summary_text("<think>chain</think>正文") == "正文"
    assert ns.clean_summary_text("  带空格  ") == "带空格"


def test_summarize_record_uses_platform_llm(monkeypatch):
    """LLM 链=平台 get_chat_model（kg_llm_connection_configs 单源），非 vendor 链。"""
    calls = {}

    class _Resp:
        content = "<think>x</think>主题：混合检索。结论：可用。"

    class _M:
        async def ainvoke(self, messages):
            calls["n"] = calls.get("n", 0) + 1
            assert any("notebook summary agent" in getattr(m, "content", "") for m in messages)
            return _Resp()

    monkeypatch.setattr(ns, "_model", lambda: _M())
    out = asyncio.run(ns.summarize_record(
        title="t", record_type="chat", user_query="q", output="o", language="zh"))
    assert out == "主题：混合检索。结论：可用。"  # 思考标签已剥
    assert calls["n"] == 1


def test_stream_record_summary_yields_chunks(monkeypatch):
    class _C:
        def __init__(self, c):
            self.content = c

    class _M:
        def astream(self, messages):
            async def _g():
                yield _C("第一")
                yield _C("第二")
                yield _C(None)
            return _g()

    monkeypatch.setattr(ns, "_model", lambda: _M())

    async def flow():
        return [c async for c in ns.stream_record_summary(
            title="t", record_type="chat", user_query="q", output="o")]

    assert asyncio.run(flow()) == ["第一", "第二"]
