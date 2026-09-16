"""Microsoft Edge read-aloud TTS adapter — free, keyless, China-reachable.

Uses the ``edge-tts`` package, which speaks the same online speech service as
the Edge browser's read-aloud feature. No API key and no ``base_url`` are
required: the adapter ignores ``config.api_key`` / ``config.base_url`` and only
honours ``config.voice`` (a neural voice name such as
``zh-CN-XiaoxiaoNeural``) and ``config.speed`` (an OpenAI-style rate factor,
1.0 = normal).

This exists for public H5 deployments hosted in mainland China, where phone
browsers frequently lack a Chinese ``speechSynthesis`` voice and the configured
TTS providers (OpenAI/OpenRouter) are unreachable. The service itself is
reached through Microsoft's global CDN, which is reachable from mainland
datacenters.
"""

from __future__ import annotations

import asyncio
import logging

from deeptutor.services.voice.base import (
    BaseTTSAdapter,
    VoiceProviderError,
    strip_markdown_for_speech,
)
from deeptutor.services.voice.config import TTSConfig

logger = logging.getLogger(__name__)

_DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"


def _rate_percent(speed: float | None) -> str:
    """Translate an OpenAI-style speed factor (1.0 = normal) into edge-tts' rate."""
    if not speed or speed <= 0:
        return ""
    pct = round((float(speed) - 1.0) * 100)
    if pct == 0:
        return ""
    return f"{pct:+d}%"


class EdgeTTSAdapter(BaseTTSAdapter):
    """Synthesize speech via Microsoft Edge's free online TTS service."""

    async def synthesize(self, text: str, config: TTSConfig) -> tuple[bytes, str]:
        try:
            import edge_tts  # lazy: keeps the base install usable without it
        except ImportError as exc:  # pragma: no cover - guarded by requirements
            raise VoiceProviderError(
                "edge-tts package is not installed; add it to requirements and rebuild."
            ) from exc

        prose = strip_markdown_for_speech(text, max_chars=config.max_input_chars)
        if not prose:
            raise VoiceProviderError("TTS input is empty after markdown stripping.")

        voice = (config.voice or _DEFAULT_VOICE).strip() or _DEFAULT_VOICE
        # edge-tts 7.x rejects rate="" — only pass it when a shift applies.
        rate = _rate_percent(config.speed)
        communicate = (
            edge_tts.Communicate(prose, voice, rate=rate) if rate else edge_tts.Communicate(prose, voice)
        )

        async def _collect() -> bytes:
            chunks: list[bytes] = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    chunks.append(chunk["data"])
            return b"".join(chunks)

        try:
            audio = await asyncio.wait_for(_collect(), timeout=config.request_timeout or 60)
        except asyncio.TimeoutError as exc:
            raise VoiceProviderError(
                f"edge-tts timed out after {config.request_timeout or 60}s."
            ) from exc
        except Exception as exc:
            raise VoiceProviderError(f"edge-tts request error: {exc}") from exc

        if not audio:
            raise VoiceProviderError("edge-tts returned empty audio.")
        logger.debug("edge-tts synthesized voice=%s chars=%d bytes=%d", voice, len(prose), len(audio))
        return audio, "audio/mpeg"


__all__ = ["EdgeTTSAdapter"]
