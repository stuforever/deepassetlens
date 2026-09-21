"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import asyncio

from app.services.sishu_full.services.subagent.base import SubagentBackend
from app.services.sishu_full.services.subagent.claude_code import ClaudeCodeBackend
from app.services.sishu_full.services.subagent.codex import CodexBackend
from app.services.sishu_full.services.subagent.gemini import GeminiBackend
from app.services.sishu_full.services.subagent.kimi import KimiBackend
from app.services.sishu_full.services.subagent.opencode_family import MimoBackend, OpencodeBackend
from app.services.sishu_full.services.subagent.partner import PartnerBackend
from app.services.sishu_full.services.subagent.types import DetectResult

_BACKENDS: dict[str, SubagentBackend] = {
    backend.kind: backend
    for backend in (
        ClaudeCodeBackend(),
        CodexBackend(),
        GeminiBackend(),
        KimiBackend(),
        OpencodeBackend(),
        MimoBackend(),
        PartnerBackend(),
    )
}


def list_backend_kinds() -> list[str]:
    """Every connectable backend kind (CLIs + partner)."""
    return list(_BACKENDS.keys())


def get_backend(kind: str) -> SubagentBackend | None:
    return _BACKENDS.get(str(kind or "").strip())


def _cli_backends() -> list[SubagentBackend]:
    return [b for b in _BACKENDS.values() if getattr(b, "local_cli", True)]


async def detect_all() -> list[DetectResult]:
    """Probe each local-CLI backend for installability on this machine.

    Non-CLI backends (the partner backend) are skipped — they aren't installed,
    they're connected from their own list — so this only ever returns the CLIs
    the connect-CLI modal offers.
    """
    cli = _cli_backends()
    results = await asyncio.gather(
        *(backend.detect() for backend in cli),
        return_exceptions=True,
    )
    detections: list[DetectResult] = []
    for backend, result in zip(cli, results, strict=True):
        if isinstance(result, DetectResult):
            detections.append(result)
        else:
            detections.append(
                DetectResult(
                    kind=backend.kind,
                    display_name=backend.display_name,
                    available=False,
                    detail=str(result),
                )
            )
    return detections


__all__ = ["list_backend_kinds", "get_backend", "detect_all"]
