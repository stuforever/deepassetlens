"""capabilities.py - 能力开关中心 API（《能力开关中心与subagents受限启用设计》批13-Q 三）

端点（与 guards.py 同构）：
  GET  /api/capabilities                -> {items（含 stats），capability_version}
  PATCH /api/capabilities/{id}          -> 更新后 item（physical_blocked 403；🔴缺理由 400；非法 params 400）
  POST /api/capabilities/{id}/probe     -> 探针执行（写 events）
  GET  /api/capabilities/events         -> 分页（含 task_invoke 审计流）
  POST /api/capabilities/reset-defaults -> 全部回基线

权限：非 admin 只读，写操作 403。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.services import capability_config, capability_probes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/capabilities", tags=["capabilities"])


def _require_admin(request: Request):
    user = get_current_user(request)
    if user is None or not user.is_admin():
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")
    return user


class CapabilityUpdateBody(BaseModel):
    enabled: Optional[bool] = None
    params: Optional[Dict[str, Any]] = None
    confirm: bool = True
    close_reason: Optional[str] = None


def _stats(capability_id: str) -> Dict[str, Any]:
    """从 capability_events 聚合：探针通过率 / 最近 task_invoke 数 / 最近变更。"""
    try:
        from app.models.base import CapabilityEvent
        db = capability_config._db()
        try:
            now = datetime.utcnow()
            probes = db.query(CapabilityEvent).filter(
                CapabilityEvent.capability_id == capability_id,
                CapabilityEvent.action == "probe",
                CapabilityEvent.ts >= now - timedelta(days=7)).all()
            ok = sum(1 for e in probes if (e.detail or {}).get("verdict") == "probe_ok")
            total = len(probes)
            task_invokes = db.query(CapabilityEvent).filter(
                CapabilityEvent.capability_id == "subagents",
                CapabilityEvent.action == "task_invoke",
                CapabilityEvent.ts >= now - timedelta(days=7)).count()
            last_toggle = db.query(CapabilityEvent).filter(
                CapabilityEvent.capability_id == capability_id,
                CapabilityEvent.action.in_(["toggle", "rebuild", "reset"]),
                ).order_by(CapabilityEvent.ts.desc()).first()
            return {
                "probe_pass_rate": round(ok / total, 2) if total else None,
                "probe_total_7d": total,
                "task_invoke_7d": task_invokes,
                "last_change": last_toggle.ts.isoformat() if last_toggle and last_toggle.ts else None,
            }
        finally:
            db.close()
    except Exception:
        return {"probe_pass_rate": None, "probe_total_7d": 0, "task_invoke_7d": 0, "last_change": None}


@router.get("")
def list_capabilities(request: Request):
    """读取全部能力策略（含统计）。所有登录用户可读。"""
    get_current_user(request)
    policies = capability_config.get_policies(force=True)
    items = [{**p, "stats": _stats(p["capability_id"])} for p in policies]
    return {"items": items, "capability_version": capability_config.get_version()}


@router.patch("/{capability_id}")
def update_capability(capability_id: str, body: CapabilityUpdateBody, request: Request):
    """更新能力开关/参数。physical_blocked 一律 403；🔴缺理由 400；非法 params 400（不落库）。"""
    _require_admin(request)
    user = get_current_user(request)
    updated_by = user.sub if user and user.sub else "admin"
    try:
        row = capability_config.update_capability(
            capability_id, enabled=body.enabled, params=body.params,
            updated_by=updated_by, close_reason=body.close_reason)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"能力 {capability_id} 不存在")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=f"物理锁定能力不可变更: {e}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {**row, "stats": _stats(capability_id)}


@router.post("/{capability_id}/probe")
def probe_capability(capability_id: str, request: Request):
    """探针执行（装配断言/store roundtrip/subagents 越权与合规）。"""
    _require_admin(request)
    return capability_probes.run_probe(capability_id)


@router.get("/events")
def list_events(
    request: Request,
    capability_id: Optional[str] = Query(None),
    range_: str = Query("7d", alias="range"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """分页事件表（toggle/rebuild/probe/task_invoke/task_reject/spec_invalid/fallback）。"""
    get_current_user(request)
    from app.models.base import CapabilityEvent
    db = capability_config._db()
    try:
        q = db.query(CapabilityEvent)
        if capability_id:
            q = q.filter(CapabilityEvent.capability_id == capability_id)
        hours = {"24h": 24, "7d": 168, "30d": 720}.get(range_, 168)
        q = q.filter(CapabilityEvent.ts >= datetime.utcnow() - timedelta(hours=hours))
        total = q.count()
        rows = q.order_by(CapabilityEvent.ts.desc()).offset((page - 1) * page_size).limit(page_size).all()
        items = [{
            "id": r.id, "capability_id": r.capability_id,
            "ts": r.ts.isoformat() if r.ts else None,
            "action": r.action, "detail": r.detail or {}, "updated_by": r.updated_by,
        } for r in rows]
        return {"items": items, "total": total, "page": page, "page_size": page_size}
    finally:
        db.close()


@router.post("/reset-defaults")
def reset_defaults(request: Request):
    """全部回基线（灰显锁定项保持锁定）。"""
    _require_admin(request)
    user = get_current_user(request)
    updated_by = user.sub if user and user.sub else "admin"
    items = capability_config.reset_defaults(updated_by=updated_by)
    return {"items": [{**p, "stats": _stats(p["capability_id"])} for p in items],
            "capability_version": capability_config.get_version()}
