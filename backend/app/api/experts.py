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
    # 记忆插槽②批1：形状放宽 Any——①期列表 与 ②{slots, legacy_paths} 对象两形状并存（spec §四），
    # 合法性由 _validate_card_fields 的 normalize+五规则校验裁定（pydantic 不预拦）。
    memory: Any = []
    knowledge_sources: List[str] = ["ontology_graph"]
    llm_connection_id: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    ui_config: Optional[Dict[str, Any]] = None
    # 附件四 A-1：卡级 suggestions（≤5 条×≤120 字）+params（键白名单 {"fsrs"}）
    suggestions: Optional[List[str]] = None
    params: Optional[Dict[str, Any]] = None


class ExpertPatchBody(BaseModel):
    name: Optional[str] = None
    tagline: Optional[str] = None
    system_prompt: Optional[str] = None
    tools: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    # 记忆插槽②批1：同 POST——两形状并存，五规则校验在 _validate_card_fields。
    memory: Optional[Any] = None
    knowledge_sources: Optional[List[str]] = None
    llm_connection_id: Optional[str] = None
    icon: Optional[str] = None
    description: Optional[str] = None
    ui_config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    close_reason: Optional[str] = None
    confirm: bool = True
    # 附件四 A-1：同 POST——suggestions/params（校验在 _validate_card_fields）
    suggestions: Optional[List[str]] = None
    params: Optional[Dict[str, Any]] = None


def _validate_card_fields(body: Dict[str, Any]) -> None:
    """spec §六 POST 校验：slug 格式/tools ⊆ 活注册表/skills 路径存在/知识源白名单/
    system_prompt 非空/entry_kind 白名单。"""
    # ⑤批3（⑤c 诚实账①回补源头）：卡 tools 校验用真实注册全集（GENERIC_ALLOWED_TOOLS，
    # 含教学族）——_mcp_tool_registry() 是 wenshu tools **推导面**（剔除教学族的零感知
    # 语义），不是校验面；批 2 一函数两用导致 tutor 卡九件必 422（洞在批 2，不在本批打补丁）。
    # E-101：⑤R R1 后教学族从 GENERIC 分家为 TUTOR_TOOLS 冻结名单（sishu 代理 twin 执行面），
    # 校验全集须并回 TUTOR_TOOLS——否则 sishu 卡 11 件全 422，卡编辑 API 整体锁死。
    from app.services.query_contract import GENERIC_ALLOWED_TOOLS, TUTOR_TOOLS
    from pathlib import Path
    reg = set(GENERIC_ALLOWED_TOOLS) | set(TUTOR_TOOLS)
    slug = body.get("expert_id") or ""
    if not _SLUG_RE.match(slug):
        raise ValueError(f"expert_id 非法（小写字母数字连字符）: {slug}")
    if not (body.get("system_prompt") or "").strip():
        raise ValueError("system_prompt 不能为空")
    if body.get("entry_kind") not in _ENTRY_KINDS:
        raise ValueError(f"entry_kind 白名单外（①期仅 chat）: {body.get('entry_kind')}")
    for t in body.get("tools") or []:
        if t not in reg:
            raise ValueError(f"tools 越界（不在活注册表）: {t}")
    # 路径存在性：声明路径对 data/ 解析（"/skills/"→data/skills；"/skills/scenarios/"→data/skills/scenarios；
    # "/memory/AGENTS.md"→data/memory/AGENTS.md）——计划原稿的 (data/skills/首段) 解析与 /skills/ 根路径
    # 自相矛盾（会解析成 data/skills/skills），按 spec §六「路径存在」意图修正（登记于账本）。
    _data = Path(__file__).resolve().parent.parent.parent / "data"
    for s in body.get("skills") or []:
        rel = str(s).strip("/")
        if not rel or not (_data / rel).exists():
            raise ValueError(f"声明路径不存在: {s}")
    # 记忆插槽②批1：memory 两形状并存——归一（ValueError→422）+slots 五规则+legacy 逐条存在性
    # （RAW_MD 槽文件由 agent_edit 创建，不做存在性校验）。
    if body.get("memory") is not None:
        from app.services.memory_slots import normalize_memory_field, validate_slots
        _mem = normalize_memory_field(body.get("memory"))
        validate_slots(_mem.get("slots"))
        for s in _mem.get("legacy_paths") or []:
            rel = str(s).strip("/")
            if not rel or not (_data / rel).exists():
                raise ValueError(f"声明路径不存在: {s}")
    for k in body.get("knowledge_sources") or []:
        if k in _KNOWLEDGE_WHITELIST:
            continue        # ④批4（spec D9）：白名单扩展 kb:{id}——id 须真实存在（存在性校验=白名单纪律）
        if str(k).startswith("kb:"):
            from app.models.knowledge_base import KnowledgeBase
            from app.core.database import SessionLocal as _SL
            _kid = str(k)[3:]
            _s = _SL()
            try:
                _exists = _s.query(KnowledgeBase).filter(KnowledgeBase.id == _kid).first()
            finally:
                _s.close()
            if not _exists:
                raise ValueError(f"knowledge_sources 声明的知识库不存在: {k}")
            continue
        raise ValueError(f"knowledge_sources 白名单外（ontology_graph 或 kb:{{id}}）: {k}")
    # 附件四 A-1：卡级 suggestions/params 白名单（≤5 条×≤120 字非空；params 键 ⊆ {"fsrs"}，
    # fsrs 子键 ⊆ {desired_retention, w}——A-3 调度面消费；缺省 None=零行为差）。
    _sugg = body.get("suggestions")
    if _sugg is not None:
        if not isinstance(_sugg, list) or len(_sugg) > 5:
            raise ValueError("suggestions 须为列表且不超过 5 条")
        for s in _sugg:
            if not isinstance(s, str) or not s.strip() or len(s) > 120:
                raise ValueError("suggestions 每条须为非空字符串且不超过 120 字")
    _params = body.get("params")
    if _params is not None:
        if not isinstance(_params, dict):
            raise ValueError("params 须为对象")
        _unk = set(_params) - {"fsrs"}
        if _unk:
            raise ValueError(f"params 键白名单外: {sorted(_unk)}")
        _fsrs = _params.get("fsrs")
        if _fsrs is not None:
            if not isinstance(_fsrs, dict):
                raise ValueError("params.fsrs 须为对象")
            _sub_unk = set(_fsrs) - {"desired_retention", "w"}
            if _sub_unk:
                raise ValueError(f"params.fsrs 子键白名单外: {sorted(_sub_unk)}")


@router.get("")
def list_experts(request: Request, enabled: Optional[bool] = Query(None)):
    get_current_user(request)
    from app.services import expert_config
    from app.services.expert_auth import filter_visible_experts   # ⑥-2a 执法点①
    rows = expert_config._load_rows(force=True)
    if enabled is True:
        rows = [r for r in rows if r["enabled"]]
    rows = filter_visible_experts(request, rows)
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
                             description=body.description, ui_config=body.ui_config,
                             suggestions=body.suggestions, params=body.params, version=1))
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
       fields.get("system_prompt") is not None or \
       fields.get("suggestions") is not None or fields.get("params") is not None:
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
