"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

# Re-export from services layer
from app.services.sishu_full.services.search import (
    PROVIDER_TEMPLATES,
    SEARCH_API_KEY_ENV,
    AnswerConsolidator,
    BaseSearchProvider,
    Citation,
    SearchProvider,
    SearchResult,
    WebSearchResponse,
    get_available_providers,
    get_current_config,
    get_default_provider,
    get_provider,
    get_providers_info,
    list_providers,
    web_search,
)

__all__ = [
    # Main function
    "web_search",
    "get_current_config",
    # Provider management
    "get_provider",
    "list_providers",
    "get_available_providers",
    "get_default_provider",
    "get_providers_info",
    # Types
    "WebSearchResponse",
    "Citation",
    "SearchResult",
    # Consolidation
    "AnswerConsolidator",
    "PROVIDER_TEMPLATES",
    # Base class
    "BaseSearchProvider",
    "SearchProvider",
    "SEARCH_API_KEY_ENV",
]
