# -*- coding: utf-8 -*-
"""三轨M17(批10 深水)：knowledge 平台路由——KB 管理核心面（vendor knowledge.py 端点
子集承接，底层走移植件 KnowledgeBaseManager）。

vendor knowledge.py 2901 行 49 端点——本件承接前端最高频消费的 8 端点读面+
创建/删除写面；上传/进度 WS/RAG 管线配置等低频面暂由 vendor 保留挂载续服务（E-85）。
本件挂载在 vendor 同前缀之前（main.py 注册顺序恒优先）。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.services.sishu_data.pg import engine

router = APIRouter()


def _kbm():
    from app.services.sishu.knowledge.manager import KnowledgeBaseManager
    from app.services.sishu.compat.runtime.home import get_runtime_home
    base = get_runtime_home() / "data" / "knowledge_bases"
    base.mkdir(parents=True, exist_ok=True)
    return KnowledgeBaseManager(base_dir=str(base))


@router.get("/list")
def list_kbs():
    """KB 列表（前端 knowledge-api.ts listKnowledgeBases 消费）。"""
    kbm = _kbm()
    names = kbm.list_knowledge_bases()
    items = []
    for name in names:
        entry = kbm.get_kb_entry(name) or {}
        items.append({
            "name": name,
            "description": entry.get("description"),
            "status": entry.get("status") or "ready",
            "is_default": entry.get("is_default", False),
            "kb_type": entry.get("kb_type") or "local",
            "doc_count": len(entry.get("documents", {})),
            "provider": entry.get("provider") or entry.get("rag_provider"),
        })
    return items


@router.get("/rag-providers")
def list_rag_providers():
    from app.services.sishu.services.rag.factory import KNOWN_PROVIDERS, DEFAULT_PROVIDER
    return [{"value": p, "label": p, "is_default": p == DEFAULT_PROVIDER}
            for p in sorted(KNOWN_PROVIDERS)]


class KBCreate(BaseModel):
    name: str
    description: str = ""
    set_default: bool = False


@router.post("/create")
def create_kb(body: KBCreate):
    kbm = _kbm()
    existing = kbm.get_kb_entry(body.name)
    if existing:
        raise HTTPException(409, f"知识库 {body.name} 已存在")
    kbm.register_knowledge_base(body.name, body.description, body.set_default)
    return {"ok": True, "name": body.name}


@router.get("/default/{name}")
def set_default_kb(name: str):
    kbm = _kbm()
    entry = kbm.get_kb_entry(name)
    if not entry:
        raise HTTPException(404, f"知识库 {name} 不存在")
    # 清除其他 default
    cfg = kbm._load_config()
    for k, v in cfg.get("knowledge_bases", {}).items():
        v["is_default"] = (k == name)
    # C-修复：_save_config 落盘的是 self.config——必须把变更后的 cfg 回写，
    # 否则 is_default 翻转被静默丢弃
    kbm.config = cfg
    kbm._save_config()
    return {"ok": True, "default": name}


@router.delete("/{name}")
def delete_kb(name: str):
    kbm = _kbm()
    entry = kbm.get_kb_entry(name)
    if not entry:
        raise HTTPException(404, f"知识库 {name} 不存在")
    cfg = kbm._load_config()
    cfg.get("knowledge_bases", {}).pop(name, None)
    if cfg.get("defaults", {}).get("default_kb") == name:
        cfg["defaults"]["default_kb"] = None
    # C-修复：同 set_default_kb——变更回写 self.config 后再落盘
    kbm.config = cfg
    kbm._save_config()
    return {"ok": True, "deleted": name}


# 注意：不承接 vendor GET /{name} 单段参数路由——平台同径先注册会把 vendor
# 静态单段端点（/health /configs /probe-folder /connect-folder…41 低频面）全部
# 遮挡成 404（E-91 实测）。前端零消费单段 GET（knowledge-api.ts 全为 /{name}/files
# 双段与静态径），裁剪保 vendor 低频面续服务。DELETE /{name} 前端消费且 vendor
# 无同径静态 DELETE，保留 1:1。
