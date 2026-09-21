"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.sishu_full.services.config.runtime_settings import (
    DOCUMENT_PARSING_ENGINE_MARKITDOWN,
    load_document_parsing_settings,
)


@dataclass(frozen=True)
class MarkItDownConfig:
    # Reserved: when True, use DeepTutor's VLM to caption images during
    # conversion. Wiring is deferred; the field keeps the signature/UI stable.
    enable_llm_image_description: bool = False


def resolve_markitdown_config() -> MarkItDownConfig:
    slice_ = (
        load_document_parsing_settings()
        .get("engines", {})
        .get(DOCUMENT_PARSING_ENGINE_MARKITDOWN, {})
    )
    return MarkItDownConfig(
        enable_llm_image_description=bool(slice_.get("enable_llm_image_description", False)),
    )


__all__ = ["MarkItDownConfig", "resolve_markitdown_config"]
