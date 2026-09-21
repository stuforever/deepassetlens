"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from typing import Any


def _read_int(source: dict[str, Any], key: str, default: int) -> int:
    value = source.get(key)
    if isinstance(value, int) and value > 0:
        return value
    return default


def _read_bool(source: dict[str, Any], key: str, default: bool) -> bool:
    value = source.get(key)
    if isinstance(value, bool):
        return value
    return default


def build_question_runtime_config(
    *,
    base_config: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the runtime_config dict passed to :class:`QuestionPipeline`.

    The pipeline reads its knobs from ``runtime_config["exploring"]`` —
    everything else in ``base_config`` is currently ignored by question.
    """
    base = base_config if isinstance(base_config, dict) else {}
    capabilities = base.get("capabilities") if isinstance(base.get("capabilities"), dict) else {}
    question_root = (
        capabilities.get("deep_question")
        if isinstance(capabilities.get("deep_question"), dict)
        else {}
    )
    exploring_root = (
        question_root.get("exploring") if isinstance(question_root.get("exploring"), dict) else {}
    )
    summarizer_root = (
        exploring_root.get("tool_summarizer")
        if isinstance(exploring_root.get("tool_summarizer"), dict)
        else {}
    )

    exploring = {
        "max_iterations": _read_int(exploring_root, "max_iterations", 8),
        "tool_summarizer": {
            "enabled": _read_bool(summarizer_root, "enabled", True),
            "max_tokens": _read_int(summarizer_root, "max_tokens", 800),
        },
    }

    runtime_config = dict(base)
    runtime_config["exploring"] = exploring
    return runtime_config


__all__ = ["build_question_runtime_config"]
