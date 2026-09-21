"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from typing import Any


def assistant_message_with_tool_calls(
    content: str,
    tool_calls: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the assistant message that precedes tool result messages."""
    return {
        "role": "assistant",
        "content": content or None,
        "tool_calls": [
            {
                "id": tool_call["id"],
                "type": "function",
                "function": {
                    "name": tool_call["name"],
                    "arguments": tool_call.get("arguments") or "{}",
                },
            }
            for tool_call in tool_calls
        ],
    }


__all__ = ["assistant_message_with_tool_calls"]
