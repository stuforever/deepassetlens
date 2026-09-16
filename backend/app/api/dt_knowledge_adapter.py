# -*- coding: utf-8 -*-
"""⑤R 契约适配层（唯一交棒 批3.2）：/api/v1/knowledge/* 原形状 → ④挂接。

分工（B0 三分类 + B1 实测修正登记）：
- 形状保真：41 路径由 vendor knowledge 路由 1:1 提供（list/configs 携带 index_versions
  机制态——③管理器自有 kb_config 存储，照搬不重设计）；
- ④挂接（本模块）：注册表镜像导入④（B0 import 面，幂等）+ tutor 卡 knowledge_sources
  挂接 kb:{④id}（平台消费面：④页/① mcp_server D9 检索入口）；
- 数据分区：knowledge_bases/parse_cache → vendor workspace data/（manager 自有存储照搬），
  注册表行 → ④ kg_knowledge_base（connected/tutor_dt 指针语义）。
"""
import json
import logging
from pathlib import Path

from app.core.database import SessionLocal
from app.models.base import ExpertProfile
from app.models.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


def vendor_kb_config_path() -> Path:
    from app.vendor.deeptutor.runtime.home import get_runtime_data_root

    return get_runtime_data_root() / "knowledge_bases" / "kb_config.json"


def sync_registry_to_kb4() -> dict:
    """vendor kb_config 注册表 → ④ import 面幂等导入（重复调用零重复）。"""
    from app.api.knowledge_base import KBImport, import_knowledge_bases

    cfg_path = vendor_kb_config_path()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    kbs = cfg.get("knowledge_bases", {})
    ws = str(cfg_path.parent)
    items = [
        KBImport.Item(
            name=name,
            description=info.get("description"),
            status=info.get("status") or "ready",
            pointer_params={"source": "tutor", "workspace": ws, "kb_name": name},
        )
        for name, info in kbs.items()
    ]
    db = SessionLocal()
    try:
        out = import_knowledge_bases(KBImport(source="tutor", items=items), db)
        return out["data"]
    finally:
        db.close()


def attach_tutor_knowledge_sources() -> list:
    """tutor 卡 knowledge_sources 挂接：kb:{④id}（tutor_dt 行）。

    重建式语义（E1 实测修正）：非 kb: 项（ontology_graph 等白名单源）保留原序；
    kb: 引用以 ④ 现行 tutor_dt 行为准重建——外部窗口删行后旧引用成僵尸
    （422 knowledge_sources 声明的知识库不存在），merge 保留会固化僵尸。"""
    db = SessionLocal()
    try:
        rows = db.query(KnowledgeBase).filter(
            KnowledgeBase.type == "connected",
            KnowledgeBase.rag_provider == "tutor_dt").all()
        kb_refs = [f"kb:{r.id}" for r in rows]
        card = db.query(ExpertProfile).filter(ExpertProfile.expert_id == "tutor").first()
        if card is None:
            logger.warning("tutor 专家卡不存在——挂接跳过（cards 初始化后重跑）")
            return []
        existing = list(card.knowledge_sources or [])
        kept = [k for k in existing if not k.startswith("kb:")]
        merged = kept + kb_refs
        if merged != existing:
            card.knowledge_sources = merged
            db.commit()
            logger.info("tutor 卡 knowledge_sources 挂接重建：kept=%d +kb=%d", len(kept), len(kb_refs))
        return merged
    finally:
        db.close()
