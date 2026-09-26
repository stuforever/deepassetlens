# -*- coding: utf-8 -*-
"""EXEC 工具签名一致性测试（五维评估盯防点②，防 T8a NameError 类复发）。

钉两条：
1. EXEC_TOOLS 每件的 MCP 入参 schema 必含 confirm_token（T8a 曾出现函数体引用
   confirm_token 而签名缺失 → 每次 MCP 调用即 NameError 的潜伏 bug）；
2. READONLY_TOOLS 每件 schema 必不含 confirm_token（只读件无两段臂）。
"""
from __future__ import annotations

import asyncio

from app.mcp_server import mcp
from app.services.permission_vocab import EXEC_TOOLS, READONLY_TOOLS


def _schemas_by_name() -> dict:
    tools = asyncio.run(mcp.list_tools())
    return {t.name: t.inputSchema for t in tools}


def test_exec_tools_have_confirm_token_param():
    schemas = _schemas_by_name()
    for name in sorted(EXEC_TOOLS):
        props = (schemas.get(name) or {}).get("properties") or {}
        assert "confirm_token" in props, (
            f"EXEC 工具 {name} 缺 confirm_token 形参——两段臂签名损坏"
            "（同 T8a execute_entity_api 潜伏 NameError 类缺陷）")


def test_readonly_tools_have_no_confirm_token_param():
    schemas = _schemas_by_name()
    for name in sorted(READONLY_TOOLS):
        props = (schemas.get(name) or {}).get("properties") or {}
        assert "confirm_token" not in props, (
            f"只读工具 {name} 不应暴露 confirm_token（两段臂属 EXEC 语义）")
