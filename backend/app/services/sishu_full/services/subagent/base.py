"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from app.services.sishu_full.services.subagent.config import BackendConfig
from app.services.sishu_full.services.subagent.types import ConsultResult, DetectResult, SubagentEvent

# Called once per native event as it streams in. Backends must await it so
# backpressure (e.g. a slow WebSocket consumer) is respected.
OnEvent = Callable[[SubagentEvent], Awaitable[None]]


class SubagentBackend(ABC):
    """Drive one subagent (a local CLI, or one of the user's partners)."""

    kind: str
    display_name: str
    cli_command: str
    # Local-CLI backends (Claude Code, Codex) are detected on this machine and
    # offered in the connect-CLI modal. Non-CLI backends (a Partner) are
    # connected from their own list, so they sit out machine detection.
    local_cli: bool = True

    @abstractmethod
    async def detect(self) -> DetectResult:
        """Report whether this CLI is installed and usable on this machine."""

    @abstractmethod
    async def consult(
        self,
        question: str,
        *,
        on_event: OnEvent,
        cwd: str | None = None,
        session_id: str | None = None,
        config: BackendConfig | None = None,
        images: list[str] | None = None,
        partner_id: str | None = None,
    ) -> ConsultResult:
        """Put one question to the subagent and stream every native event.

        ``session_id`` resumes the backend's prior session for this turn (so the
        subagent keeps context across DeepTutor's successive questions); the
        returned :class:`ConsultResult` carries the session id to thread into the
        next consult. ``images`` are local file paths the user forwarded with the
        question (Codex attaches them with ``-i``; Claude Code is pointed at them
        for its Read tool). ``partner_id`` names the bound partner for the partner
        backend (the CLI backends ignore it). Waits unconditionally for the
        subagent to finish — only its own exit (clean or error) ends the consult.
        """


__all__ = ["OnEvent", "SubagentBackend"]
