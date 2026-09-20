# -*- coding: utf-8 -*-
# [sishu port] v4批6 机械复制自 vendor deeptutor/services/imagegen/base.py（1:1 语义，仅 import 改写）。
# 批16 vendor 物理删除后的存活拷贝；上游修订需回灌本件（复刻纪律）。
"""Base abstraction for image-generation adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.sishu.services.imagegen.config import ImagegenConfig


class BaseImagegenAdapter(ABC):
    """Abstract text-to-image adapter."""

    @abstractmethod
    async def generate(
        self, prompt: str, config: ImagegenConfig, *, n: int = 1
    ) -> list[tuple[bytes, str]]:
        """Generate ``n`` images for ``prompt``.

        Returns a list of ``(image_bytes, content_type)`` — content type is
        best-effort, e.g. ``image/png``.
        """


__all__ = ["BaseImagegenAdapter"]
