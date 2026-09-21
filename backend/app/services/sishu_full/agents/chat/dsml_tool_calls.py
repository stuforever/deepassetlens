"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import json
import re
from typing import Any

# A real DSML tool-call tag (not prose that merely mentions "tool_calls"): an
# opening ``<...invoke name="`` or any ``<...DSML...>`` tag. Used to decide
# whether the content channel is carrying tool-call markup.
DSML_SIGNAL_RE = re.compile(
    r"<[^>]*DSML[^>]*>|<[^>]*?invoke\s+name\s*=\s*\"",
    re.IGNORECASE,
)

_INVOKE_RE = re.compile(
    r"<[^>]*?invoke\s+name\s*=\s*\"(?P<name>[^\"]+)\"[^>]*>(?P<body>.*?)</[^>]*?invoke\s*>",
    re.IGNORECASE | re.DOTALL,
)
_PARAM_RE = re.compile(
    r"<[^>]*?parameter\s+name\s*=\s*\"(?P<pname>[^\"]+)\"(?P<attrs>[^>]*)>(?P<pval>.*?)</[^>]*?parameter\s*>",
    re.IGNORECASE | re.DOTALL,
)
# The ``<...tool_calls>`` open/close wrapper, stripped from the cleaned text once
# we have extracted the invokes inside it.
_TOOLCALLS_WRAP_RE = re.compile(r"</?[^>]*?tool_calls\s*>", re.IGNORECASE)


def _looks_like_string(attrs: str) -> bool:
    normalized = attrs.replace("'", '"')
    return 'string="true"' in normalized.lower()


def _coerce_param_value(raw: str, attrs: str) -> Any:
    if _looks_like_string(attrs):
        return raw
    # Unmarked scalars (numbers, bools, JSON objects/arrays) are parsed; on any
    # failure the raw string is kept verbatim.
    try:
        return json.loads(raw.strip())
    except Exception:
        return raw


def has_dsml_tool_calls(text: str | None) -> bool:
    """Cheap check for whether ``text`` carries DSML tool-call markup."""
    return bool(text) and bool(DSML_SIGNAL_RE.search(text))


def extract_dsml_tool_calls(text: str | None) -> tuple[list[dict[str, Any]], str]:
    """Parse DSML tool-call markup out of ``text``.

    Returns ``(tool_calls, cleaned_text)``. ``tool_calls`` is empty and
    ``cleaned_text is text`` when no well-formed invoke block is present, so the
    caller can treat "no calls" as "not a DSML round" and fall through
    unchanged.
    """
    if not has_dsml_tool_calls(text):
        return [], text or ""

    tool_calls: list[dict[str, Any]] = []
    spans: list[tuple[int, int]] = []
    for idx, match in enumerate(_INVOKE_RE.finditer(text)):
        name = match.group("name").strip()
        if not name:
            continue
        args: dict[str, Any] = {}
        for param in _PARAM_RE.finditer(match.group("body")):
            args[param.group("pname").strip()] = _coerce_param_value(
                param.group("pval"), param.group("attrs") or ""
            )
        tool_calls.append(
            {
                "id": f"dsml_{idx}",
                "name": name,
                "arguments": json.dumps(args, ensure_ascii=False),
            }
        )
        spans.append((match.start(), match.end()))

    if not tool_calls:
        return [], text

    cleaned = text
    for start, end in reversed(spans):
        cleaned = cleaned[:start] + cleaned[end:]
    cleaned = _TOOLCALLS_WRAP_RE.sub("", cleaned).strip()
    return tool_calls, cleaned


__all__ = ["extract_dsml_tool_calls", "has_dsml_tool_calls", "DSML_SIGNAL_RE"]
