# -*- coding: utf-8 -*-
# [sishu port] v4批6 机械复制自 vendor deeptutor/services/llm/registry.py（1:1 语义，仅 import 改写）。
# 批16 vendor 物理删除后的存活拷贝；上游修订需回灌本件（复刻纪律）。
"""
LLM Provider Registry
====================

Simple provider registration system for LLM providers.
"""

from collections.abc import Callable

# Global registry for LLM providers
_provider_registry: dict[str, type] = {}


def register_provider(name: str) -> Callable[[type], type]:
    """
    Decorator to register an LLM provider class.

    Args:
        name: Name to register the provider under

    Returns:
        Decorator function
    """

    def decorator(cls: type) -> type:
        if name in _provider_registry:
            raise ValueError(f"Provider '{name}' is already registered")
        _provider_registry[name] = cls
        setattr(cls, "__provider_name__", name)
        return cls

    return decorator


def get_provider_class(name: str) -> type:
    """
    Get a registered provider class by name.

    Args:
        name: Provider name

    Returns:
        Provider class

    Raises:
        KeyError: If provider is not registered
    """
    return _provider_registry[name]


def list_providers() -> list[str]:
    """
    List all registered provider names.

    Returns:
        List of provider names
    """
    return list(_provider_registry.keys())


def is_provider_registered(name: str) -> bool:
    """
    Check if a provider is registered.

    Args:
        name: Provider name

    Returns:
        True if registered, False otherwise
    """
    return name in _provider_registry
