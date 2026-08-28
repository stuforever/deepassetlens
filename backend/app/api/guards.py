"""guards.py - 安全控制中心 API（《安全控制中心实施设计》2.3）

端点：
  GET  /api/guards                      -> {items:[...], global_version}
  PATCH /api/guards/{guard_id}          -> 更新后 item（红级关闭缺理由 -> 400）
  POST  /api/guards/{guard_id}/probe    -> {verdict, blocked_reason|passed_reason, elapsed_ms}
  GET   /api/guards/events              -> 分页事件表（guard_id/range/page）
  POST  /api/guards/reset-defaults      -> {items:[...]}

权限：所有端点经 get_current_user；非 admin -> GET 可读、PATCH/probe/reset 403。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.services import guard_config, guard_probes

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/guards", tags=["guards"])


def _require_admin(request: Request) -> object:
    """非 admin -> 403（写操作统一入口）。"""
    user = get_current_user(request)
    if user is None or not user.is_admin():
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")
    return user


class GuardUpdateBody(BaseModel):
    enabled: Optional[bool] = None
    mode: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    confirm: bool = True
    close_reason: Optional[str] = None


def _stats(guard_id: str) -> Dict[str, Any]:
    """从 guard_events 聚合 24h/7d 拦截数与最近拦截时间。"""
    try:
        from app.models.base import GuardEvent
        db = guard_config._db()
        try:
            now = datetime.utcnow()
            h24 = db.query(GuardEvent).filter(
                GuardEvent.guard_id == guard_id,
                GuardEvent.ts >= now - timedelta(hours=24),
                GuardEvent.action == "block").count()
            h7d = db.query(GuardEvent).filter(
                GuardEvent.guard_id == guard_id,
                GuardEvent.ts >= now - timedelta(days=7),
                GuardEvent.action == "block").count()
            last = db.query(GuardEvent).filter(
                GuardEvent.guard_id == guard_id,
                GuardEvent.action == "block").order_by(GuardEvent.ts.desc()).first()
            return {"h24": h24, "h7d": h7d,
                    "last_block_at": last.ts.isoformat() if last and last.ts else None}
        finally:
            db.close()
    except Exception:
        return {"h24": 0, "h7d": 0, "last_block_at": None}


@router.get("")
def list_guards(request: Request):
    """读取全部策略（含统计）。所有登录用户可读。"""
    get_current_user(request)
    policies = guard_config.get_policies(force=True)
    items = [{**p, "stats": _stats(p["guard_id"])} for p in policies]
    return {"items": items, "global_version": guard_config.get_version()}


@router.patch("/{guard_id}")
def update_guard(guard_id: str, body: GuardUpdateBody, request: Request):
    """更新策略开关/模式/参数。红级关闭缺理由 -> 400。"""
    _require_admin(request)
    user = get_current_user(request)
    updated_by = user.sub if user and user.sub else "admin"
    try:
        row = guard_config.update_guard(
            guard_id, enabled=body.enabled, mode=body.mode, params=body.params,
            updated_by=updated_by, close_reason=body.close_reason, confirm=body.confirm)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"守卫 {guard_id} 不存在")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {**row, "stats": _stats(guard_id)}


@router.post("/{guard_id}/probe")
def probe_guard(guard_id: str, request: Request):
    """试探单：验证该控制当前是否真正生效。"""
    _require_admin(request)
    return guard_probes.run_probe(guard_id)


@router.get("/events")
def list_events(
    request: Request,
    guard_id: Optional[str] = Query(None),
    range_: str = Query("24h", alias="range"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """分页事件表（含 toggle/probe/block）。"""
    get_current_user(request)
    from app.models.base import GuardEvent
    db = guard_config._db()
    try:
        q = db.query(GuardEvent)
        if guard_id:
            q = q.filter(GuardEvent.guard_id == guard_id)
        hours = {"24h": 24, "7d": 168, "30d": 720}.get(range_, 24)
        q = q.filter(GuardEvent.ts >= datetime.utcnow() - timedelta(hours=hours))
        total = q.count()
        rows = q.order_by(GuardEvent.ts.desc()).offset((page - 1) * page_size).limit(page_size).all()
        items = [{
            "id": r.id, "guard_id": r.guard_id,
            "ts": r.ts.isoformat() if r.ts else None,
            "action": r.action, "question_digest": r.question_digest,
            "verdict": r.verdict, "detail": r.detail or {}, "updated_by": r.updated_by,
        } for r in rows]
        return {"items": items, "total": total, "page": page, "page_size": page_size}
    finally:
        db.close()


@router.post("/reset-defaults")
def reset_defaults(request: Request):
    """全部恢复基线。"""
    _require_admin(request)
    user = get_current_user(request)
    updated_by = user.sub if user and user.sub else "admin"
    items = guard_config.reset_defaults(updated_by=updated_by)
    return {"items": [{**p, "stats": _stats(p["guard_id"])} for p in items],
            "global_version": guard_config.get_version()}
