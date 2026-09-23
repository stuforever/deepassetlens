"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from app.services.sishu_full.services.generation_http import (
    GenerationProviderError,
    build_auth_headers,
    join_api_path,
    raise_for_provider,
)
from app.services.sishu_full.services.imagegen.base import BaseImagegenAdapter
from app.services.sishu_full.services.imagegen.config import ImagegenConfig

logger = logging.getLogger(__name__)


class ChatCompletionsImagegenAdapter(BaseImagegenAdapter):
    """POST ``{base}/chat/completions`` with image modalities; collect image bytes."""

    async def generate(
        self, prompt: str, config: ImagegenConfig, *, n: int = 1
    ) -> list[tuple[bytes, str]]:
        if not config.base_url:
            raise GenerationProviderError("No endpoint URL configured for image generation.")
        url = join_api_path(config.base_url, "chat/completions")
        headers = {
            "Content-Type": "application/json",
            **build_auth_headers(config.auth_style, config.api_key),
            **(config.extra_headers or {}),
        }
        payload: dict[str, Any] = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
        }

        logger.debug("imagegen(chat) url=%s model=%s", url, config.model)
        try:
            async with httpx.AsyncClient(timeout=config.request_timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
                raise_for_provider(resp, "Image generation")
                images = [
                    await self._materialize(client, src) for src in self._extract_sources(resp)
                ]
        except httpx.HTTPError as exc:
            raise GenerationProviderError(f"Image generation request error: {exc}") from exc
        if not images:
            raise GenerationProviderError(
                "Chat model returned no image. Check the model supports image output "
                "(its output modalities must include `image`)."
            )
        return images

    @staticmethod
    def _extract_sources(resp: httpx.Response) -> list[str]:
        """Pull image URLs / data URIs out of the assistant message."""
        data = resp.json()
        sources: list[str] = []
        choices = data.get("choices") if isinstance(data, dict) else None
        for choice in choices or []:
            message = (choice or {}).get("message") or {}
            for image in message.get("images") or []:
                if not isinstance(image, dict):
                    continue
                src = (image.get("image_url") or {}).get("url") or image.get("url")
                if isinstance(src, str) and src:
                    sources.append(src)
            # Fallback: some variants nest images in the content parts array.
            content = message.get("content")
            if isinstance(content, list):
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    src = (part.get("image_url") or {}).get("url") or part.get("url")
                    if isinstance(src, str) and src.startswith(("data:image", "http")):
                        sources.append(src)
        if not sources:
            raise GenerationProviderError("Image response had no image in the assistant message.")
        return sources

    async def _materialize(self, client: httpx.AsyncClient, src: str) -> tuple[bytes, str]:
        if src.startswith("data:"):
            header, _, encoded = src.partition(",")
            if not encoded:
                raise GenerationProviderError("Malformed image data URI.")
            content_type = header[5:].split(";", 1)[0].strip() or "image/png"
            return base64.b64decode(encoded), content_type
        # R5批㉑（清单安全）：SSRF 防线——仅 http(s)，拒绝环回/私网/链路本地/保留段
        # 字面 IP 与 localhost 系主机名（src 来自模型输出，prompt 用户可控可诱导）
        from urllib.parse import urlparse as _urlparse
        import ipaddress as _ip

        _u = _urlparse(src)
        if _u.scheme not in ("http", "https") or not _u.hostname:
            raise GenerationProviderError("仅允许 http(s) 图片 URL")
        try:
            _addr = _ip.ip_address(_u.hostname)
            if _addr.is_loopback or _addr.is_private or _addr.is_link_local or _addr.is_reserved:
                raise GenerationProviderError("拒绝指向内网/环回的图片 URL")
        except ValueError:
            _hn = _u.hostname.lower().rstrip(".")
            if _hn == "localhost" or _hn.endswith((".localhost", ".local", ".internal")):
                raise GenerationProviderError("拒绝指向内网的图片 URL")
        resp = await client.get(src)
        raise_for_provider(resp, "Image download")
        content_type = resp.headers.get("content-type") or "image/png"
        if not content_type.startswith("image/"):
            content_type = "image/png"
        return resp.content, content_type


__all__ = ["ChatCompletionsImagegenAdapter"]
