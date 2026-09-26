# -*- coding: utf-8 -*-
"""笔记本记录摘要器（切换 R6/Wave2 平台化重写）。

vendor sishu/agents/notebook/summarize_agent.py 的平台重写：提示词资产自
agents/notebook/prompts/{zh,en}/summarize_agent.yaml **逐字内联**（改一字需标注），
LLM 链改走平台唯一入口 llm_client.get_chat_model（kg_llm_connection_configs）。
语义保持：summarize（聚合+清洗）与 stream_summary（逐块流式）两方法面不变，
供 sishu_learning/notebook 路由消费。
"""
from __future__ import annotations

import re
from typing import AsyncGenerator

_PROMPTS = {
    "zh": {
        "system": (
            "你是 DeepTutor 的 notebook summary agent。请把一条待保存内容提炼成简洁、可检索、\n"
            "面向未来复用的摘要。摘要必须突出主题、关键结论、适用场景和保存价值。\n"
            "只输出摘要正文，不要加标题、前缀或项目符号。"
        ),
        "user_template": (
            "记录类型：{record_type}\n"
            "类型提示：{record_hint}\n"
            "标题：{title}\n"
            "用户输入：\n{user_query}\n\n"
            "保存内容：\n{output}\n\n"
            "元数据：{metadata}\n\n"
            "请输出 80-180 字的中文摘要。要求：\n"
            "1. 优先概括知识主题与关键信息；\n"
            "2. 如果内容是草稿或中间过程，要说明当前完成度；\n"
            "3. 如果内容适合后续复用，要点明可复用角度。"
        ),
        "record_hints": {
            "chat": "一段完整聊天历史，重点提炼问题、结论与后续行动。",
            "tutorbot": "一段与 Partner（具名 AI 助手）的对话，重点提炼提出的问题、Partner 给出的结论与后续行动。",
            "guided_learning": "一段引导式学习记录，重点提炼学习主题、知识点结构与阶段性产出。",
            "co_writer": "一份用户在 Co-Writer 中撰写的 Markdown 草稿，重点提炼文档主题、结构骨架、当前完成度，以及后续值得回顾的部分。",
            "default": "请总结此记录中最值得复用的信息。",
        },
    },
    "en": {
        "system": (
            "You are DeepTutor's notebook summary agent. Compress a saved record into a\n"
            "concise, retrieval-friendly summary for future reuse. Focus on topic, key\n"
            "conclusions, use cases, and why this record matters. Output only the summary\n"
            "text with no heading or bullets."
        ),
        "user_template": (
            "Record type: {record_type}\n"
            "Type hint: {record_hint}\n"
            "Title: {title}\n"
            "User input:\n{user_query}\n\n"
            "Saved content:\n{output}\n\n"
            "Metadata: {metadata}\n\n"
            "Write an 80-180 word summary. Focus on the topic, key information, current\n"
            "completion state, and what makes this record useful for future reuse."
        ),
        "record_hints": {
            "chat": "A full chat transcript; focus on the question, conclusion, and next actions.",
            "tutorbot": "A conversation with a Partner (a named AI assistant); focus on what was asked, the Partner's conclusion, and any next actions.",
            "guided_learning": "A guided learning record; focus on topic, knowledge structure, and partial/final output.",
            "co_writer": "A Co-Writer markdown draft authored by the user; focus on the document's topic, structure, current completion state, and what makes it worth revisiting.",
            "default": "Summarize the most reusable information in this record.",
        },
    },
}

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)

_MAX_TOKENS = 300  # vendor get_token_limit_kwargs(model, 300) 同值


def clean_summary_text(text: str) -> str:
    """剥思考标签（vendor clean_thinking_tags 的平台最小面——<think> 块剥离）。"""
    return _THINK_RE.sub("", str(text or "")).strip()


def _clip(value: str, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n...[truncated]"


def _norm_lang(language: str) -> str:
    return "zh" if str(language or "en").lower().startswith("zh") else "en"


def _build_user_prompt(*, language: str, title: str, record_type: str,
                       user_query: str, output: str, metadata: dict) -> str:
    p = _PROMPTS[_norm_lang(language)]
    hint = p["record_hints"].get(record_type) or p["record_hints"]["default"]
    return p["user_template"].format(
        record_type=record_type,
        record_hint=hint,
        title=title or "(untitled)",
        user_query=_clip(user_query, 1200) or "(empty)",
        output=_clip(output, 6000) or "(empty)",
        metadata=_clip(str(metadata or {}), 1000) or "(none)",
    )


def _model():
    from app.services.llm_client import get_chat_model

    return get_chat_model(temperature=0.2, streaming=True).bind(max_tokens=_MAX_TOKENS)


def _messages(*, language: str, title: str, record_type: str,
              user_query: str, output: str, metadata: dict) -> list:
    from langchain_core.messages import HumanMessage, SystemMessage

    p = _PROMPTS[_norm_lang(language)]
    return [
        SystemMessage(content=p["system"]),
        HumanMessage(content=_build_user_prompt(
            language=language, title=title, record_type=record_type,
            user_query=user_query, output=output, metadata=metadata)),
    ]


async def summarize_record(*, title: str, record_type: str, user_query: str,
                           output: str, metadata: dict | None = None,
                           language: str = "en") -> str:
    """聚合摘要（对应 vendor NotebookSummarizeAgent.summarize）。"""
    try:
        resp = await _model().ainvoke(_messages(
            language=language, title=title, record_type=record_type,
            user_query=user_query, output=output, metadata=metadata or {}))
        return clean_summary_text(getattr(resp, "content", "") or "")
    except Exception:
        # 摘要失败不阻塞保存——回落为标题（与 vendor 失败语义等价的可用产物）
        return title or ""


async def stream_record_summary(*, title: str, record_type: str, user_query: str,
                                output: str, metadata: dict | None = None,
                                language: str = "en") -> AsyncGenerator[str, None]:
    """逐块流式摘要（对应 vendor NotebookSummarizeAgent.stream_summary）。"""
    model = _model()
    async for chunk in model.astream(_messages(
            language=language, title=title, record_type=record_type,
            user_query=user_query, output=output, metadata=metadata or {})):
        c = getattr(chunk, "content", "")
        if isinstance(c, str) and c:
            yield c
