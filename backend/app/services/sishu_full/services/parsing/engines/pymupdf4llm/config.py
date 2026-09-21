"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.sishu_full.services.config.runtime_settings import (
    DOCUMENT_PARSING_ENGINE_PYMUPDF4LLM,
    load_document_parsing_settings,
)


@dataclass(frozen=True)
class PyMuPDF4LLMConfig:
    # Extract embedded images + rendered vector graphics into the images/ dir.
    write_images: bool = True
    # Output format for extracted images ("png" | "jpg" | "jpeg" | "webp").
    image_format: str = "png"
    # Render resolution (DPI) for extracted images.
    image_dpi: int = 150


def resolve_pymupdf4llm_config() -> PyMuPDF4LLMConfig:
    slice_ = (
        load_document_parsing_settings()
        .get("engines", {})
        .get(DOCUMENT_PARSING_ENGINE_PYMUPDF4LLM, {})
    )
    return PyMuPDF4LLMConfig(
        write_images=bool(slice_.get("write_images", True)),
        image_format=str(slice_.get("image_format") or "png"),
        image_dpi=int(slice_.get("image_dpi") or 150),
    )


__all__ = ["PyMuPDF4LLMConfig", "resolve_pymupdf4llm_config"]
