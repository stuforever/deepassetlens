"""guard_config.py - 安全控制中心策略服务（《安全控制中心实施设计》2.2）

职责：
  - get_policies()：进程内 TTL 5s 缓存读库；查库异常 -> 返回 DEFAULT_ALL_ENABLED（fail-closed：
    配置坏了 = 全启用，绝不因读库失败而放行危险操作）。
  - get_version()：全局版本号（max(version)），审批轨重建 agent 单例的缓存键成分。
  - guard_enabled(guard_id, sub_id=None)：热生效判断（capability 内含 whitelist/absolute_tools/
    stop_when 三个内部检查共享开关，事件细分到内部 sub_id）。
  - update_guard()：PATCH 落地，红级关闭缺 close_reason -> ValueError；成功 version+1、写 toggle 事件。
  - reset_defaults()：全部恢复基线，version+1、写 reset 事件。
  - record_event()：写 guard_events（fire-and-forget，不阻塞主链路）。

热生效链路：PATCH -> version+1 -> TTL 5s 自然过期 -> 下一次读取读到新配置。
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CACHE_TTL = 5.0
_CACHE: Dict[str, Any] = {"data": None, "ts": 0.0}

# 基线（全启用、block 模式）；fail-closed 兜底 + reset 目标
DEFAULT_ALL_ENABLED: List[Dict[str, Any]] = [
    {"guard_id": "capability", "title": "能力控制", "enabled": True, "mode": "block",
     "risk_level": "red", "confirm_required": True, "version": 1},
    {"guard_id": "sql_safety", "title": "SQL 安全控制", "enabled": True, "mode": "block",
     "risk_level": "red", "confirm_required": True, "version": 1},
    {"guard_id": "template", "title": "模板控制", "enabled": True, "mode": "block",
     "risk_level": "yellow", "confirm_required": True, "version": 1},
    {"guard_id": "engine_lock", "title": "引擎控制", "enabled": True, "mode": "block",
     "risk_level": "yellow", "confirm_required": True, "version": 1},
    {"guard_id": "output", "title": "输出控制", "enabled": True, "mode": "block",
     "risk_level": "yellow", "confirm_required": True, "version": 1},
    {"guard_id": "approval_track", "title": "审批轨", "enabled": True, "mode": "block",
     "risk_level": "green", "confirm_required": False, "version": 1},
]
_BY_ID: Dict[str, Dict[str, Any]] = {p["guard_id"]: p for p in DEFAULT_ALL_ENABLED}


def _db():
    from app.core.database import SessionLocal
    return SessionLocal()


def _row_to_dict(row) -> Dict[str, Any]:
    return {
        "guard_id": row.guard_id, "title": row.title,
        "enabled": bool(row.enabled), "mode": row.mode or "block",
        "params": row.params or {}, "risk_level": row.risk_level or "yellow",
        "description": row.description or {}, "confirm_required": bool(row.confirm_required),
        "updated_by": row.updated_by, "updated_at": row.updated_at,
        "close_reason": row.close_reason, "version": row.version or 1,
    }


def get_policies(force: bool = False) -> List[Dict[str, Any]]:
    """读全部策略（TTL 5s 进程内缓存）。查库异常 -> 全启用基线（fail-closed）。"""
    now = time.time()
    if force or _CACHE["data"] is None or (now - _CACHE["ts"]) > _CACHE_TTL:
        try:
            from app.models.base import GuardPolicy
            db = _db()
            try:
                rows = db.query(GuardPolicy).all()
                data = [_row_to_dict(r) for r in rows] or list(DEFAULT_ALL_ENABLED)
            finally:
                db.close()
            _CACHE["data"] = data
            _CACHE["ts"] = now
            return data
        except Exception as e:
            logger.error(f"[GuardConfig] 读策略失败，fail-closed 返回全启用基线: {e}")
            _CACHE["data"] = list(DEFAULT_ALL_ENABLED)
            _CACHE["ts"] = now
            return list(DEFAULT_ALL_ENABLED)
    return _CACHE["data"]


def get_version() -> int:
    """全局配置版本号 = max(version)。查库异常返回 0（审批轨单例重建用）。"""
    try:
        from app.models.base import GuardPolicy
        db = _db()
        try:
            v = db.query(GuardPolicy.version).all()
        finally:
            db.close()
        return max([x[0] for x in v], default=0) or 0
    except Exception:
        return 0


def guard_enabled(guard_id: str, sub_id: Optional[str] = None) -> bool:
    """热生效判断：守卫是否启用。capability 内部检查经 sub_id 细分事件，开关共享。"""
    for p in get_policies():
        if p["guard_id"] == guard_id:
            return bool(p["enabled"])
    # 未知 guard_id -> 按启用处理（未知守卫不阻断既有安全检查）
    return True


def get_policy(guard_id: str) -> Optional[Dict[str, Any]]:
    for p in get_policies():
        if p["guard_id"] == guard_id:
            return p
    return None


def record_event(guard_id: str, action: str, *, verdict: Optional[str] = None,
                 question_digest: Optional[str] = None, detail: Optional[Dict[str, Any]] = None,
                 updated_by: Optional[str] = None, _sync: bool = False) -> None:
    """写 guard_events。默认 fire-and-forget（_sync=True 供测试/探针需要落库即查的场景）。"""
    def _do():
        try:
            from app.models.base import GuardEvent
            db = _db()
            try:
                db.add(GuardEvent(
                    guard_id=guard_id[:64], action=action[:16], verdict=verdict,
                    question_digest=(question_digest or "")[:200], detail=detail,
                    updated_by=updated_by,
                ))
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[GuardEvent] 写入失败(不阻塞主链路): {e}")

    if _sync:
        _do()
        return
    try:
        import threading
        threading.Thread(target=_do, daemon=True).start()
    except Exception:
        _do()


def update_guard(guard_id: str, *, enabled: Optional[bool] = None, mode: Optional[str] = None,
                 params: Optional[Dict[str, Any]] = None, updated_by: Optional[str] = None,
                 close_reason: Optional[str] = None, confirm: bool = True) -> Dict[str, Any]:
    """更新策略。红级关闭缺 close_reason -> ValueError（API 层转 400）。

    enabled=False 且 risk_level=red 且 confirm=False 且无 close_reason -> 拒绝（fail-closed 边界）。
    成功：version+1，写 toggle 事件，清缓存。
    """
    from app.models.base import GuardPolicy
    db = _db()
    try:
        row = db.query(GuardPolicy).filter(GuardPolicy.guard_id == guard_id).first()
        if row is None:
            raise KeyError(guard_id)
        going_off = enabled is False
        risk = row.risk_level or "yellow"
        if going_off and risk == "red":
            reason = (close_reason or "").strip()
            if len(reason) < 10:
                raise ValueError("需填写关闭理由（至少 10 字）")
            row.close_reason = reason[:500]
        if enabled is not None:
            row.enabled = enabled
        if mode is not None:
            row.mode = mode
        if params is not None:
            row.params = params
        row.updated_by = updated_by
        row.updated_at = func_now()
        row.version = (row.version or 1) + 1
        db.commit()
        db.refresh(row)
        out = _row_to_dict(row)
        # 写 toggle 事件（同步落库，保证 PATCH 返回后立即可查）
        record_event(guard_id, "toggle",
                     detail={"enabled": out["enabled"], "mode": out["mode"], "version": out["version"],
                             "close_reason": row.close_reason},
                     updated_by=updated_by, _sync=True)
        _CACHE["data"] = None
        return out
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def reset_defaults(updated_by: Optional[str] = None) -> List[Dict[str, Any]]:
    """全部恢复基线：enabled=True/mode=block/params=种子基线/close_reason 清空，version+1。"""
    from app.core.init_db import GUARD_POLICY_SEED
    from app.models.base import GuardPolicy
    db = _db()
    try:
        for seed in GUARD_POLICY_SEED:
            row = db.query(GuardPolicy).filter(GuardPolicy.guard_id == seed["guard_id"]).first()
            if row is None:
                row = GuardPolicy(guard_id=seed["guard_id"])
                db.add(row)
            row.title = seed["title"]
            row.enabled = True
            row.mode = "block"
            row.params = seed.get("params")
            row.risk_level = seed["risk_level"]
            row.description = seed.get("description")
            row.confirm_required = seed.get("confirm_required", True)
            row.close_reason = None
            row.updated_by = updated_by
            row.updated_at = func_now()
            row.version = (row.version or 1) + 1
        db.commit()
        rows = db.query(GuardPolicy).all()
        out = [_row_to_dict(r) for r in rows]
        record_event("all", "reset", detail={"guards": [r["guard_id"] for r in out]},
                     updated_by=updated_by, _sync=True)
        _CACHE["data"] = None
        return out
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def cleanup_old_events(days: int = 30) -> int:
    """清理 30 天前的 guard_events（启动时调用，防表膨胀）。"""
    try:
        from app.models.base import GuardEvent
        db = _db()
        try:
            from datetime import datetime, timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)
            n = db.query(GuardEvent).filter(GuardEvent.ts < cutoff).delete()
            db.commit()
            return n
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[GuardEvent] 清理失败: {e}")
        return 0


def func_now():
    from sqlalchemy.sql import func as _f
    return _f.now()
