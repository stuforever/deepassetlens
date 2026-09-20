# -*- coding: utf-8 -*-
# [sishu port] v4批6 机械复制自 vendor deeptutor/services/llm/types.py（1:1 语义，仅 import 改写）。
# 批16 vendor 物理删除后的存活拷贝；上游修订需回灌本件（复刻纪律）。
"""Shared LLM response data models."""

from collections.abc import AsyncGenerator
import logging

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TutorResponse(BaseModel):
    """LLM completion response container."""

    content: str
    raw_response: dict[str, object] = Field(default_factory=dict)
    usage: dict[str, int] = Field(
        default_factory=lambda: {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
    )
    provider: str = ""
    model: str = ""
    finish_reason: str | None = None
    cost_estimate: float = 0.0


class TutorStreamChunk(BaseModel):
    """Chunk emitted during streamed LLM responses."""

    delta: str
    content: str = ""
    provider: str = ""
    model: str = ""
    is_complete: bool = False
    usage: dict[str, int] | None = None


AsyncStreamGenerator = AsyncGenerator[TutorStreamChunk, None]

# Backwards-compatible type aliases used by some callers/tests.
LLMResponse = TutorResponse
StreamChunk = TutorStreamChunk

__all__ = [
    "AsyncStreamGenerator",
    "LLMResponse",
    "StreamChunk",
    "TutorResponse",
    "TutorStreamChunk",
]
