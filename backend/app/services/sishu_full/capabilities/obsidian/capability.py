"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from importlib import resources
from typing import Any

from app.services.sishu_full.capabilities.obsidian.binding import obsidian_vault_refs, vault_for_turn
from app.services.sishu_full.capabilities.obsidian.tools import OBSIDIAN_TOOL_NAMES
from app.services.sishu_full.capabilities.protocol import KnowledgeCapability, PromptBlock
from app.services.sishu_full.core.context import UnifiedContext


class ObsidianCapability(KnowledgeCapability):
    """Turn-scoped integration for a connected Obsidian vault."""

    name = "obsidian"
    owned_tools = OBSIDIAN_TOOL_NAMES

    def is_active(self, context: UnifiedContext) -> bool:
        return vault_for_turn(context) is not None

    def owned_kbs(self, context: UnifiedContext) -> set[str]:
        # The selected vault KB(s) are read/authored through the Obsidian tools,
        # never through rag — exclude them so co-selected LlamaIndex KBs keep
        # their rag surface (issue #650).
        return obsidian_vault_refs(context)

    def system_block(
        self,
        context: UnifiedContext,
        *,
        language: str,
        prompts: dict[str, Any],
    ) -> PromptBlock | None:
        binding = vault_for_turn(context)
        if binding is None:
            return None
        override = _prompt_text(prompts, ("obsidian", "system"))
        content = override or _load_system_prompt(language)
        return PromptBlock("obsidian", content.replace("{vault_name}", binding["name"]))

    def augment_kwargs(
        self,
        tool_name: str,
        kwargs: dict[str, Any],
        context: UnifiedContext,
    ) -> dict[str, Any]:
        if tool_name not in OBSIDIAN_TOOL_NAMES:
            return kwargs
        binding = vault_for_turn(context)
        if binding is None:
            return kwargs
        # Server-owned: overwrite any model-supplied value so the path can't be
        # forged to read/write outside the connected vault.
        updated = dict(kwargs)
        updated["_vault_path"] = binding["path"]
        return updated

    def pre_loop_seed(self, context: UnifiedContext) -> str:
        _ = context
        return ""


def _prompt_text(prompts: dict[str, Any], path: tuple[str, ...]) -> str:
    value: Any = prompts
    for key in path:
        if not isinstance(value, dict):
            return ""
        value = value.get(key)
    return value if isinstance(value, str) and value else ""


def _load_system_prompt(language: str) -> str:
    lang = "zh" if language.lower().startswith("zh") else "en"
    prompt = resources.files(__package__).joinpath("prompts", lang, "system.md")
    return prompt.read_text(encoding="utf-8").strip()


__all__ = ["ObsidianCapability"]
