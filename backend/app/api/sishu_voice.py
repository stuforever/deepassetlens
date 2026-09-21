# -*- coding: utf-8 -*-
"""批11深水：voice 平台路由——vendor voice.py 1:1（tts/stt 全量 2 端点）。

底层走移植件 services/voice（synthesize_speech/transcribe_audio 批6已移植）+
compat h5 门禁（h5_user_guarded/user_context）。vendor voice 路由整行摘除
（SISHU 卸挂集扩 voice）。
"""
from __future__ import annotations

import io
import logging
import wave
from contextlib import nullcontext

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel, Field

from app.services.sishu.compat.h5 import h5_user_guarded
from app.services.sishu.compat.paths import user_context
from app.services.sishu.services.voice import (
    VoiceProviderError,
    synthesize_speech,
    transcribe_audio,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB, matching OpenAI's limit.
_DEFAULT_PCM_SAMPLE_RATE = 24_000
_DEFAULT_PCM_CHANNELS = 1
_PCM16_SAMPLE_WIDTH = 2


class TTSRequest(BaseModel):
    """Text-to-speech request body."""

    text: str = Field(..., min_length=1)
    voice: str | None = None
    format: str | None = None


def _h5_gate(u: str, code: str, x_access_code: str):
    """1:1 vendor voice.py _h5_gate（T2 u 门禁——带 u 校验访问码切用户上下文）。"""
    if not isinstance(u, str) or not u.strip():
        return nullcontext()
    return user_context(h5_user_guarded(u.strip(), code, x_access_code))


def _parse_pcm_content_type(content_type: str) -> tuple[int, int] | None:
    """1:1 vendor voice.py _parse_pcm_content_type。"""
    media_type, *params = (content_type or "").split(";")
    if media_type.strip().lower() not in {"audio/pcm", "audio/x-pcm", "audio/l16"}:
        return None
    sample_rate = _DEFAULT_PCM_SAMPLE_RATE
    channels = _DEFAULT_PCM_CHANNELS
    for item in params:
        key, sep, value = item.strip().partition("=")
        if not sep:
            continue
        key = key.strip().lower()
        value = value.strip().strip('"')
        try:
            parsed = int(value)
        except ValueError:
            continue
        if key in {"rate", "sample-rate", "samplerate"} and parsed > 0:
            sample_rate = parsed
        elif key in {"channels", "channel"} and parsed > 0:
            channels = parsed
    return sample_rate, channels


def _pcm16_to_wav(audio: bytes, *, sample_rate: int, channels: int) -> bytes:
    """Wrap provider PCM16 bytes in a WAV container browsers can play."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(_PCM16_SAMPLE_WIDTH)
        wav.setframerate(sample_rate)
        wav.writeframes(audio)
    return buffer.getvalue()


@router.post("/tts")
async def text_to_speech(
    payload: TTSRequest,
    u: str = Query("", description="H5 用户标识（?u=）；带 u 时校验访问码"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
) -> Response:
    """Synthesize ``text`` to audio using the active TTS provider."""
    with _h5_gate(u, code, x_access_code):
        try:
            audio, content_type = await synthesize_speech(
                payload.text,
                voice=payload.voice,
                response_format=payload.format,
            )
        except ValueError as exc:  # missing/invalid configuration
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except VoiceProviderError as exc:
            logger.warning("TTS provider error: %s", exc)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    pcm_info = _parse_pcm_content_type(content_type)
    if pcm_info:
        sample_rate, channels = pcm_info
        audio = _pcm16_to_wav(audio, sample_rate=sample_rate, channels=channels)
        content_type = "audio/wav"
    return Response(
        content=audio,
        media_type=content_type,
        headers={"Cache-Control": "no-store"},
    )


@router.post("/stt")
async def speech_to_text(
    file: UploadFile = File(...),
    language: str | None = Form(default=None),
    u: str = Query("", description="H5 用户标识（?u=）；带 u 时校验访问码"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
) -> dict[str, str]:
    """Transcribe an uploaded audio clip using the active STT provider."""
    with _h5_gate(u, code, x_access_code):
        audio = await file.read()
        if not audio:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty audio upload.")
        if len(audio) > _MAX_AUDIO_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Audio exceeds the 25 MB limit.",
            )
        try:
            text = await transcribe_audio(
                audio,
                filename=file.filename or "audio.webm",
                content_type=file.content_type or "application/octet-stream",
                language=language,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except VoiceProviderError as exc:
            logger.warning("STT provider error: %s", exc)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return {"text": text}
