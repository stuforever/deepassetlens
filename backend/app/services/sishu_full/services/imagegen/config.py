"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.sishu_full.services.generation_http import AUTH_BEARER


@dataclass(slots=True)
class ImagegenConfig:
    """Resolved text-to-image configuration for one generation call."""

    model: str
    provider_name: str = "openai"
    adapter: str = "openai_compat"
    auth_style: str = AUTH_BEARER
    api_key: str = ""
    base_url: str = ""
    api_version: str | None = None
    extra_headers: dict[str, str] = field(default_factory=dict)
    # Provider/model-specific generation knobs. Empty → omit from the request
    # and let the provider use its default.
    size: str = ""  # e.g. "1024x1024"
    quality: str = ""  # e.g. "standard" | "hd"
    style: str = ""  # e.g. "natural" | "vivid"
    response_format: str = ""  # "" | "url" | "b64_json"
    # Image generation is slow; allow generous wall-clock per request.
    request_timeout: int = 120


__all__ = ["ImagegenConfig"]
