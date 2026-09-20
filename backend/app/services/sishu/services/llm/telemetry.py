# -*- coding: utf-8 -*-
# [sishu port] v4批6 机械复制自 vendor deeptutor/services/llm/telemetry.py（1:1 语义，仅 import 改写）。
# 批16 vendor 物理删除后的存活拷贝；上游修订需回灌本件（复刻纪律）。
"""
LLM Telemetry
=============

Basic telemetry tracking for LLM calls.
"""

from collections.abc import Awaitable, Callable
import functools
import logging
from typing import TypeVar

logger = logging.getLogger(__name__)


T = TypeVar("T")


def track_llm_call(
    provider_name: str,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator to track LLM calls for telemetry.

    Args:
        provider_name: Name of the provider being called

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger.debug("LLM call to %s: %s", provider_name, func.__name__)
            try:
                result = await func(*args, **kwargs)
                logger.debug("LLM call to %s completed successfully", provider_name)
                return result
            except Exception as e:
                logger.warning("LLM call to %s failed: %s", provider_name, e)
                raise

        return wrapper

    return decorator
