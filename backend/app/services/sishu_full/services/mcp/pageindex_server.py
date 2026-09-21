"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from app.services.sishu_full.services.mcp.config import MCPConfig, MCPServerConfig

PAGEINDEX_SERVER_NAME = "pageindex"


def builtin_pageindex_server() -> MCPServerConfig | None:
    """The injected server entry, or ``None`` when no API key is configured."""
    from app.services.sishu_full.services.rag.pipelines.pageindex.config import get_pageindex_config

    try:
        cfg = get_pageindex_config()
    except Exception:
        return None
    return MCPServerConfig(
        type="streamableHttp",
        url=cfg.api_base_url.rstrip("/") + "/mcp",
        headers={"Authorization": f"Bearer {cfg.api_key}"},
        tool_timeout=120,
        # remove_document is the one api-proxy tool DeepTutor blocks: an agent
        # deleting a cloud doc would silently orphan the doc_ids in the local
        # KB manifest. Everything else the server advertises passes through.
        disabled_tools=["remove_document"],
    )


def with_builtin_servers(config: MCPConfig) -> MCPConfig:
    """Overlay code-injected servers onto *config*; user entries win."""
    if PAGEINDEX_SERVER_NAME in config.servers:
        return config
    entry = builtin_pageindex_server()
    if entry is None:
        return config
    return MCPConfig(servers={**config.servers, PAGEINDEX_SERVER_NAME: entry})


__all__ = ["PAGEINDEX_SERVER_NAME", "builtin_pageindex_server", "with_builtin_servers"]
