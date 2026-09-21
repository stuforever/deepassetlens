"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import logging
from pathlib import Path

TEXTBOOK_KB_PREFIX = "textbook-"

logger = logging.getLogger(__name__)


def _configured_names() -> list[str]:
    """settings/textbook_kbs.json -> auto_ground_kbs 名单（缺省空）。"""
    from app.services.sishu_full.multi_user.paths import get_current_path_service

    p = Path(get_current_path_service().get_settings_dir()) / "textbook_kbs.json"
    try:
        import json

        data = json.loads(p.read_text(encoding="utf-8"))
        items = data.get("auto_ground_kbs") or []
        return [str(x) for x in items if str(x).strip()]
    except Exception:
        return []


def _has_ready_index(name: str) -> bool:
    """该教材库是否有与当前 embedding 配置签名匹配的就绪索引。

    fail-open 原则：未配 embedding（无从判定）或任何异常都返回 True——
    静默失去接地比错科检索噪声更伤。失配返回 False 并由调用方记 warning。
    """
    from app.services.sishu_full.services.rag.embedding_signature import (
        signature_from_embedding_config,
    )
    from app.services.sishu_full.services.rag.index_versioning import find_matching_version

    try:
        signature = signature_from_embedding_config()
        if signature is None:
            return True
        from app.services.sishu_full.multi_user.knowledge_access import resolve_kb

        resource = resolve_kb(name, require_write=False)
        kb_dir = resource.base_dir / resource.name
        return find_matching_version(kb_dir, signature) is not None
    except Exception:
        logger.warning(
            "textbook KB %r readiness check failed; keeping it grounded "
            "(fail-open). Consider POST /api/v1/knowledge/%s/reindex if "
            "retrieval misbehaves.", name, name,
        )
        return True


def auto_textbook_kbs() -> list[str]:
    """当前用户可见的教材知识库名单（未显式选 KB 时的自动接地集）。

    - admin：自己工作区的全部 textbook-* / 名单库
    - H5 用户：自己的 + 管理员授予且可用的同类库
    """
    from app.services.sishu_full.multi_user.knowledge_access import list_visible_knowledge_bases

    configured = set(_configured_names())
    names: list[str] = []
    for item in list_visible_knowledge_bases():
        name = str(item.get("name") or "")
        if not (name.startswith(TEXTBOOK_KB_PREFIX) or name in configured):
            continue
        if item.get("available") is False:
            continue
        if not _has_ready_index(name):
            logger.warning(
                "textbook KB %r has no index matching the active embedding "
                "signature; skipping auto-ground (reindex to restore): "
                "POST /api/v1/knowledge/%s/reindex", name, name,
            )
            continue
        if name not in names:
            names.append(name)
    return names


__all__ = ["TEXTBOOK_KB_PREFIX", "auto_textbook_kbs"]
