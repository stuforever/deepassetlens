# -*- coding: utf-8 -*-
"""experts.py - 专家卡管理 API（专家地基①，spec §六；模式照抄 guards.py）。

端点：GET /api/experts（?enabled=true 门户过滤）/ GET /{expert_id} / POST（建卡）
      PATCH /{expert_id}（version+1）/ POST /{expert_id}/probe / GET /events。
①期无 DELETE（只关不删）。鉴权：登录用户可读，写/探针 admin。
"""
from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.core.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/experts", tags=["experts"])

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_ENTRY_KINDS = {"chat"}
_KNOWLEDGE_WHITELIST = {"ontology_graph"}


def _require_admin(request: Request) -> object:
    user = get_current_user(request)
    if user is None or not user.is_admin():
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")
    return user


class ExpertCardBody(BaseModel):
    name: str
    tagline: Optional[str] = None
    entry_kind: str = "chat"
    system_prompt: str
    tools: List[str] = []
    skills: List[str] = []
    memory: List[str] = []
    knowledge_sources: List[str] = ["ontology_graph"]
    llm_connection_id: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    ui_config: Optional[Dict[str, Any]] = None


class ExpertPatchBody(BaseModel):
    name: Optional[str] = None
    tagline: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    memory: Optional[List[str]] = None
    knowledge_sources: Optional[List[str]] = None
    llm_connection_id: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    ui_config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    close_reason: Optional[str] = None
    confirm: bool = True


def _validate_card_fields(body: Dict[str, Any]) -> None:
    """spec §六 POST 校验：slug 格式/tools ⊆ 活注册表/skills 路径存在/知识源白名单/
    system_prompt 非空/entry_kind 白名单。"""
    from app.services.expert_config import _mcp_tool_registry
    from pathlib import Path
    slug = body.get("expert_id") or ""
    if not _SLUG_RE.match(slug):
        raise ValueError(f"expert_id 非法（小写字母数字连字符）: {slug}")
    if not (body.get("system_prompt") or "").strip():
        raise ValueError("system_prompt 不能为空")
    if body.get("entry_kind") not in _ENTRY_KINDS:
        raise ValueError(f"entry_kind 白名单外（①期仅 chat）: {body.get('entry_kind')}")
    reg = set(_mcp_tool_registry())
    for t in body.get("tools") or []:
        if t not in reg:
            raise ValueError(f"tools 越界（不在活注册表）: {t}")
    # 路径存在性：声明路径对 data/ 解析（"/skills/"→data/skills；"/skills/scenarios/"→data/skills/scenarios；
    # "/memory/AGENTS.md"→data/memory/AGENTS.md）——计划原稿的 (data/skills/首段) 解析与 /skills/ 根路径
    # 自相矛盾（会解析成 data/skills/skills），按 spec §六「路径存在」意图修正（登记于账本）。
    _data = Path(__file__).resolve().parent.parent.parent / "data"
    for s in (body.get("skills") or []) + (body.get("memory") or []):
        rel = str(s).strip("/")
        if not rel or not (_data / rel).exists():
            raise ValueError(f"声明路径不存在: {s}")
    for k in body.get("knowledge_sources") or []:
        if k not in _KNOWLEDGE_WHITELIST:
            raise ValueError(f"knowledge_sources 白名单外（①期仅 ontology_graph）: {k}")


@router.get("")
def list_experts(request: Request, enabled: Optional[bool] = Query(None)):
    get_current_user(request)
    from app.services import expert_config
    rows = expert_config._load_rows(force=True)
    if enabled is True:
        rows = [r for r in rows if r["enabled"]]
    return {"items": rows, "global_version": expert_config.get_version()}


@router.get("/events")
def list_events(request: Request, expert_id: Optional[str] = Query(None), page: int = Query(1, ge=1),
                page_size: int = Query(20, ge=1, le=100)):
    get_current_user(request)
    from app.models.base import ExpertEvent
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        q = db.query(ExpertEvent).order_by(ExpertEvent.ts.desc())
        if expert_id:
            q = q.filter(ExpertEvent.expert_id == expert_id)
        total = q.count()
        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        return {"items": [{"expert_id": r.expert_id, "ts": r.ts.isoformat() if r.ts else None,
                           "action": r.action, "detail": r.detail, "updated_by": r.updated_by}
                          for r in rows], "total": total}
    finally:
        db.close()


@router.get("/{expert_id}")
def get_expert(expert_id: str, request: Request):
    get_current_user(request)
    from app.services import expert_config
    try:
        return expert_config.get_card(expert_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"专家 {expert_id} 不存在")


@router.post("")
def create_expert(request: Request, expert_id: str = Query(..., alias="id"), body: ExpertCardBody = ...):
    """建卡（spec §六）：校验失败 → 422；slug 冲突 → 409。
    query 用 alias="id"（?id=echo）——对齐前端 expertsApi.create 的 /experts?id= 调用形。"""
    _require_admin(request)
    fields = body.model_dump()
    fields["expert_id"] = expert_id
    try:
        _validate_card_fields(fields)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    from app.models.base import ExpertProfile
    from app.core.database import SessionLocal
    from app.services import expert_config
    db = SessionLocal()
    try:
        if db.query(ExpertProfile).filter(ExpertProfile.expert_id == expert_id).first():
            raise HTTPException(status_code=409, detail=f"专家已存在: {expert_id}")
        db.add(ExpertProfile(expert_id=expert_id, name=body.name, tagline=body.tagline,
                             enabled=True, entry_kind=body.entry_kind,
                             system_prompt=body.system_prompt, tools=body.tools,
                             skills=body.skills, memory=body.memory,
                             knowledge_sources=body.knowledge_sources,
                             llm_connection_id=body.llm_connection_id, icon=body.icon,
                             description=body.description, ui_config=body.ui_config, version=1))
        db.commit()
    finally:
        db.close()
    expert_config._CACHE["rows"] = None
    expert_config.record_event(expert_id, "created", detail={"via": "api"}, updated_by="admin")
    return expert_config.get_card(expert_id)


@router.patch("/{expert_id}")
def patch_expert(expert_id: str, body: ExpertPatchBody, request: Request):
    """改卡→version+1（下一问新 Agent）；enabled=false 红级必须 close_reason（spec §六）。"""
    _require_admin(request)
    user = get_current_user(request)
    updated_by = user.sub if user and user.sub else "admin"
    fields = {k: v for k, v in body.model_dump().items()
              if v is not None and k not in ("confirm", "close_reason")}
    if fields.get("tools") is not None or fields.get("skills") is not None or \
       fields.get("memory") is not None or fields.get("knowledge_sources") is not None or \
       fields.get("system_prompt") is not None:
        from app.services import expert_config as ec
        try:
            merged = {**ec.get_card(expert_id), **fields}
        except KeyError:
            raise HTTPException(status_code=404, detail=f"专家 {expert_id} 不存在")
        merged["expert_id"] = expert_id
        try:
            _validate_card_fields(merged)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    from app.services import expert_config
    try:
        return expert_config.update_card(expert_id, updated_by=updated_by,
                                          close_reason=body.close_reason, **fields)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"专家 {expert_id} 不存在")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{expert_id}/probe")
def probe_expert(expert_id: str, request: Request):
    """D3 探针：卡声明 vs _ASSEMBLY_MANIFEST 实际装配对照。"""
    _require_admin(request)
    from app.services import expert_config
    from app.services.tupu_deepagent import _ASSEMBLY_MANIFEST
    try:
        card = expert_config.get_card(expert_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"专家 {expert_id} 不存在")
    m = _ASSEMBLY_MANIFEST or {}
    _mi = m.get("items") or {}  # 批2 落位：expert_id/card_version 在 manifest items 内（计划原稿读顶层为矛盾处，登记账本）
    checks = {
        "manifest_expert_match": _mi.get("expert_id") == expert_id,
        "manifest_card_version_match": _mi.get("card_version") == card.get("version"),
        "tools_declared_subset_registry": set(card.get("tools") or []) <= set(m.get("tool_universe") or card.get("tools") or []),
    }
    ok = all(checks.values())
    expert_config.record_event(expert_id, "probe",
                               detail={"checks": checks, "verdict": "probe_ok" if ok else "probe_fail"},
                               updated_by="admin")
    return {"expert_id": expert_id, "verdict": "probe_ok" if ok else "probe_fail", "checks": checks}
