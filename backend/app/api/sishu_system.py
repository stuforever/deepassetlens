# -*- coding: utf-8 -*-
"""批11深水：system 平台路由——前端消费面（vendor system.py 1:1 语义，底层走移植件）。

承接：GET /api/v1/system/status（SettingsHub 系统状态页消费）。
vendor system.py 五端点中余四端点（runtime-topology/test-llm/test-embeddings/
test-search）前端零消费，vendor 同前缀续服务（台账登记）。
本件挂载在 vendor 同前缀之前（main.py 注册顺序恒优先）；无参数路由，零遮挡。
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

from app.services.sishu.compat.context import get_current_user
from app.services.sishu.services.config import resolve_search_runtime_config
from app.services.sishu.services.embedding import get_embedding_config
from app.services.sishu.services.llm import get_llm_config

router = APIRouter()


@router.get("/status")
async def get_system_status():
    """1:1 vendor system.py get_system_status（学习域移植服务栈）。"""
    result = {
        "backend": {"status": "online", "timestamp": datetime.now().isoformat()},
        "llm": {"status": "unknown", "model": None, "testable": True},
        "embeddings": {"status": "unknown", "model": None, "testable": True},
        "search": {"status": "optional", "provider": None, "testable": True},
    }

    result["backend"]["status"] = "online"

    try:
        llm_config = get_llm_config()
        result["llm"]["model"] = llm_config.model
        result["llm"]["status"] = "configured"
    except ValueError as e:
        result["llm"]["status"] = "not_configured"
        result["llm"]["error"] = str(e)
    except Exception as e:
        result["llm"]["status"] = "error"
        result["llm"]["error"] = str(e)

    try:
        embedding_config = get_embedding_config()
        result["embeddings"]["model"] = embedding_config.model
        result["embeddings"]["status"] = "configured"
    except ValueError as e:
        result["embeddings"]["status"] = "not_configured"
        result["embeddings"]["error"] = str(e)
    except Exception as e:
        result["embeddings"]["status"] = "error"
        result["embeddings"]["error"] = str(e)

    try:
        search_config = resolve_search_runtime_config()
        if search_config.requested_provider:
            result["search"]["provider"] = search_config.provider
            if search_config.unsupported_provider:
                result["search"]["status"] = "unsupported"
                result["search"]["error"] = (
                    f"{search_config.requested_provider} is deprecated/unsupported. "
                    "Switch to brave/tavily/jina/searxng/duckduckgo/perplexity."
                )
            elif search_config.deprecated_provider:
                result["search"]["status"] = "deprecated"
                result["search"]["error"] = (
                    f"{search_config.requested_provider} is deprecated. "
                    "Switch to brave/tavily/jina/searxng/duckduckgo/perplexity."
                )
            elif search_config.missing_credentials:
                result["search"]["status"] = "not_configured"
                result["search"]["error"] = (
                    f"{search_config.requested_provider} requires api_key. "
                    "Set profile.api_key in Settings > Catalog."
                )
            elif search_config.provider == "none":
                result["search"]["status"] = "disabled"
                result["search"]["testable"] = False
            else:
                result["search"]["status"] = "configured"
                if search_config.fallback_reason:
                    result["search"]["status"] = "fallback"
                    result["search"]["error"] = search_config.fallback_reason
    except Exception as e:
        result["search"]["status"] = "error"
        result["search"]["error"] = str(e)

    if not get_current_user().is_admin:
        for section in ("llm", "embeddings"):
            result[section].pop("model", None)
        result["search"].pop("provider", None)

    return result
