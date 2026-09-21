"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from abc import ABC, abstractmethod
import logging
from typing import Any

from app.services.sishu_full.services.config import resolve_search_runtime_config

from .types import WebSearchResponse

# Legacy name retained for provider metadata only.
SEARCH_API_KEY_ENV = "SEARCH_API_KEY"


class BaseSearchProvider(ABC):
    """Abstract base class for search providers.

    Providers use the active Search profile from Settings > Catalog.
    Each provider has its own BASE_URL defined as a class constant.
    """

    name: str = "base"
    display_name: str = "Base Provider"
    description: str = ""
    requires_api_key: bool = True
    supports_answer: bool = False  # Whether provider generates LLM answers
    BASE_URL: str = ""  # Each provider defines its own endpoint
    API_KEY_ENV_VARS: tuple[str, ...] = (SEARCH_API_KEY_ENV,)

    def __init__(self, api_key: str | None = None, **kwargs: Any) -> None:
        """
        Initialize the provider.

        Args:
            api_key: API key for the provider. If not provided, use the active Search profile.
            **kwargs: Additional configuration options.
        """
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key or self._get_api_key()
        self.config = kwargs
        self.proxy = kwargs.get("proxy")

    def _get_api_key(self) -> str:
        """Get API key from the active search profile."""
        key = ""
        resolved = resolve_search_runtime_config()
        if resolved.provider == self.name or resolved.requested_provider == self.name:
            key = resolved.api_key
        if self.requires_api_key and not key:
            raise ValueError(f"{self.name} requires an api_key in Settings > Catalog > Search.")
        return key

    @abstractmethod
    def search(self, query: str, **kwargs: Any) -> WebSearchResponse:
        """
        Execute search and return standardized response.

        Args:
            query: The search query.
            **kwargs: Provider-specific options.

        Returns:
            WebSearchResponse: Standardized search response.
        """
        pass

    def is_available(self) -> bool:
        """
        Check if provider is available (dependencies installed, API key set).

        Returns:
            bool: True if provider is available, False otherwise.
        """
        try:
            if self.requires_api_key:
                key = self.api_key or resolve_search_runtime_config().api_key
                if not key:
                    return False
            return True
        except (ValueError, ImportError):
            return False


__all__ = ["BaseSearchProvider", "SEARCH_API_KEY_ENV"]
