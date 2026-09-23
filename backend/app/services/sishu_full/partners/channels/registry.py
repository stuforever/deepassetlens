"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from app.services.sishu_full.partners.channels.base import BaseChannel

_INTERNAL = frozenset({"base", "manager", "registry"})


def discover_channel_names() -> list[str]:
    """Return all built-in channel module names by scanning the package (zero imports)."""
    import app.services.sishu_full.partners.channels as pkg

    return [
        name
        for _, name, ispkg in pkgutil.iter_modules(pkg.__path__)
        if name not in _INTERNAL and not ispkg
    ]


def load_channel_class(module_name: str) -> type[BaseChannel]:
    """Import *module_name* and return the first BaseChannel subclass found."""
    from app.services.sishu_full.partners.channels.base import BaseChannel as _Base

    mod = importlib.import_module(f"app.services.sishu_full.partners.channels.{module_name}")
    for attr in dir(mod):
        obj = getattr(mod, attr)
        if isinstance(obj, type) and issubclass(obj, _Base) and obj is not _Base:
            return obj
    raise ImportError(f"No BaseChannel subclass in deeptutor.partners.channels.{module_name}")


def discover_plugins() -> dict[str, type[BaseChannel]]:
    """Discover external channel plugins registered via entry_points."""
    from importlib.metadata import entry_points

    plugins: dict[str, type[BaseChannel]] = {}
    # Minor（R3批）：组名回退 deeptutor.partners.channels——与平台侧 sishu 副本
    # （app/services/sishu/partners/channels/registry.py）一致，同一插件双栈只注册一次。
    for ep in entry_points(group="deeptutor.partners.channels"):
        try:
            cls = ep.load()
            plugins[ep.name] = cls
        except Exception as e:
            logger.warning("Failed to load channel plugin '{}': {}", ep.name, e)
    return plugins


def discover_all() -> dict[str, type[BaseChannel]]:
    """Return all channels: built-in (pkgutil) merged with external (entry_points).

    Built-in channels take priority — an external plugin cannot shadow a built-in name.
    """
    channels, _errors = discover_all_with_errors()
    return channels


def discover_all_with_errors() -> tuple[dict[str, type[BaseChannel]], dict[str, str]]:
    """Like :func:`discover_all`, but also report channels that failed to load.

    Returns ``(channels, errors)`` where ``errors`` maps each unloadable
    built-in channel name to its import error message (typically a missing
    optional dependency). Surfacing these keeps "why is X missing from the
    UI?" diagnosable instead of silently dropping the channel.
    """
    builtin: dict[str, type[BaseChannel]] = {}
    errors: dict[str, str] = {}
    for modname in discover_channel_names():
        try:
            builtin[modname] = load_channel_class(modname)
        except ImportError as e:
            errors[modname] = str(e)
            logger.debug("Skipping built-in channel '{}': {}", modname, e)

    external = discover_plugins()
    shadowed = set(external) & set(builtin)
    if shadowed:
        logger.warning("Plugin(s) shadowed by built-in channels (ignored): {}", shadowed)

    return {**external, **builtin}, errors
