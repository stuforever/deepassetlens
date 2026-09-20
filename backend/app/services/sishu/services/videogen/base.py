# -*- coding: utf-8 -*-
# [sishu port] v4批6 机械复制自 vendor deeptutor/services/videogen/base.py（1:1 语义，仅 import 改写）。
# 批16 vendor 物理删除后的存活拷贝；上游修订需回灌本件（复刻纪律）。
"""Base abstraction for video-generation adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from app.services.sishu.services.videogen.config import VideogenConfig

# Optional async progress callback invoked during long renders. Receives a short
# human-readable status line (the tool layer forwards it to the chat stream).
ProgressFn = Callable[[str], Awaitable[None]]


class BaseVideogenAdapter(ABC):
    """Abstract text-to-video adapter (task lifecycle: submit → poll → download)."""

    @abstractmethod
    async def submit_task(self, prompt: str, config: VideogenConfig) -> str:
        """Submit a generation task and return its provider task id.

        Used both by :meth:`generate` and by the Settings "Test connection"
        probe, which validates endpoint + auth + model without waiting for the
        (slow, billable) render to finish.
        """

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        config: VideogenConfig,
        *,
        progress: ProgressFn | None = None,
    ) -> tuple[bytes, str]:
        """Generate one video for ``prompt``.

        Returns ``(video_bytes, content_type)`` — content type is best-effort,
        e.g. ``video/mp4``.
        """


__all__ = ["BaseVideogenAdapter", "ProgressFn"]
