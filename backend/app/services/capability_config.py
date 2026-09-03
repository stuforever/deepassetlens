"""capability_config.py - 能力开关中心服务（《能力开关中心与subagents受限启用设计》批13-Q 三）

职责：
  - get_policies()：TTL 5s 缓存读库；查库异常 -> 返回 DEFAULT_ALL_ENABLED（fail-closed：配置坏了=全开=现状行为）。
  - get_version()：max(version)，装配类缓存键成分（version 变化 -> agent 重建）。
  - cap_enabled(capability_id) / get_policy(id)。
  - update_capability()：PATCH 落地；physical_blocked 一律 403（API 层）；🔴缺 close_reason -> ValueError；
    **params 前置校验**（validate_params：subagents 规格工具交集非空/schema 名合法），非法 -> ValueError（API 转 400 不落库）。
  - record_event()：写 capability_events（toggle/rebuild/probe/task_invoke/task_reject/spec_invalid/fallback）。
  - reset_defaults()：全部回基线（physical_blocked 项保持锁定），version+1。

两类生效路径：
  - 装配类（skills/filesystem_tools/.../subagents/permissions/debug）-> version+1 -> agent 缓存键失配重建；
  - 运行时类（store 读取）-> TTL 5s 缓存刷新，不重建。
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_CACHE_TTL = 5.0
_CACHE: Dict[str, Any] = {"data": None, "ts": 0.0}

# 合法 schema 名（response_format.params.schema）；"final" = 扁平最终交付 schema
RESPONSE_FORMAT_SCHEMAS = ("final",)

# 全局工具注册表（护栏3 白名单窄化 + PATCH 前置校验的静态依据）：
# MCP 受控工具（GENERIC_ALLOWED_TOOLS）+ 框架只读文件工具。
# 注意：write_file/edit_file/execute/grep/glob 属 HarnessProfile 排除清单（安全红线），
# 不入注册表——子代理规格引用它们会被护栏3 拒装配/窄化剔除。
def _global_tool_registry() -> frozenset:
    try:
        from app.services.query_contract import GENERIC_ALLOWED_TOOLS
        base = set(GENERIC_ALLOWED_TOOLS)
    except Exception:
        base = set()
    base |= {"read_file", "ls"}
    return frozenset(base)


def _seed_baseline() -> List[Dict[str, Any]]:
    from app.core.init_db import CAPABILITY_POLICY_SEED
    out = []
    for p in CAPABILITY_POLICY_SEED:
        out.append({
            "capability_id": p["capability_id"], "title": p["title"], "enabled": True,
            "params": p.get("params"), "risk_level": p.get("risk_level", "yellow"),
            "description": p.get("description"), "confirm_required": p.get("confirm_required", True),
            "physical_blocked": p.get("physical_blocked", False),
            "blocked_reason": p.get("blocked_reason"), "version": 1,
        })
    return out


DEFAULT_ALL_ENABLED: List[Dict[str, Any]] = _seed_baseline()


def _db():
    from app.core.database import SessionLocal
    return SessionLocal()


def _row_to_dict(row) -> Dict[str, Any]:
    return {
        "capability_id": row.capability_id, "title": row.title,
        "enabled": bool(row.enabled), "params": row.params or {},
        "risk_level": row.risk_level or "yellow", "description": row.description or {},
        "confirm_required": bool(row.confirm_required),
        "physical_blocked": bool(row.physical_blocked),
        "blocked_reason": row.blocked_reason,
        "updated_by": row.updated_by, "updated_at": row.updated_at,
        "close_reason": row.close_reason, "version": row.version or 1,
    }


def get_policies(force: bool = False) -> List[Dict[str, Any]]:
    """读全部能力策略（TTL 5s 进程内缓存）。查库异常 -> 全开基线（fail-closed=现状行为）。"""
    now = time.time()
    if force or _CACHE["data"] is None or (now - _CACHE["ts"]) > _CACHE_TTL:
        try:
            from app.models.base import CapabilityPolicy
            db = _db()
            try:
                rows = db.query(CapabilityPolicy).all()
                data = [_row_to_dict(r) for r in rows] or list(DEFAULT_ALL_ENABLED)
            finally:
                db.close()
            _CACHE["data"] = data
            _CACHE["ts"] = now
            return data
        except Exception as e:
            logger.error(f"[CapabilityConfig] 读策略失败，fail-closed 返回全开基线: {e}")
            _CACHE["data"] = list(DEFAULT_ALL_ENABLED)
            _CACHE["ts"] = now
            return list(DEFAULT_ALL_ENABLED)
    return _CACHE["data"]


def get_version() -> int:
    """全局能力版本号 = max(version)。查库异常返回 0。"""
    try:
        from app.models.base import CapabilityPolicy
        db = _db()
        try:
            v = db.query(CapabilityPolicy.version).all()
        finally:
            db.close()
        return max([x[0] for x in v], default=0) or 0
    except Exception:
        return 0


def cap_enabled(capability_id: str) -> bool:
    for p in get_policies():
        if p["capability_id"] == capability_id:
            return bool(p["enabled"])
    return True  # 未知能力按启用处理（不改变现状行为）


def get_policy(capability_id: str) -> Optional[Dict[str, Any]]:
    for p in get_policies():
        if p["capability_id"] == capability_id:
            return p
    return None


# 批13-J 收尾（问题二）：工具黑名单配置化——默认排除名单（安全红线，与 HarnessProfile 硬编码 5 件一致）
DEFAULT_TOOL_EXCLUSIONS: List[str] = ["grep", "glob", "write_file", "edit_file", "execute"]
# 物理锁定（前端灰显，不可恢复）：技能渐进披露靠 read_file/ls 活命
LOCKED_TOOL_EXCLUSIONS: List[str] = ["read_file", "ls"]


def get_tool_exclusions() -> Dict[str, List[str]]:
    """读工具黑名单配置（capability_policies.tool_availability.params，定稿能力项名）。

    返回 {"excluded": [...], "locked": [...]}。**fail-safe**：读配置异常/缺 params
    -> 返回默认 5 件（绝不因配置读崩变成"全放开"）。locked 恒为物理锁定件（不可改）。
    """
    excluded = list(DEFAULT_TOOL_EXCLUSIONS)
    try:
        p = get_policy("tool_availability")
        if p and isinstance(p.get("params"), dict):
            x = p["params"].get("excluded")
            if isinstance(x, list) and all(isinstance(t, str) and t for t in x):
                # 排除名单可配置（但 locked 件永远不可出现在 excluded——物理保护）
                excluded = [t for t in x if t not in LOCKED_TOOL_EXCLUSIONS]
    except Exception as _e:
        logger.error(f"[ToolExclusions] 读配置失败，fail-safe 用默认 5 件: {_e}")
    return {"excluded": excluded, "locked": list(LOCKED_TOOL_EXCLUSIONS)}


def validate_params(capability_id: str, params: Dict[str, Any]) -> Optional[str]:
    """PATCH 前置校验。返回 None=合法；返回字符串=拒绝原因（API 转 400 且不落库）。

    - subagents：specs 必为列表；每规格 name/description/prompt/tools 齐全；
      tools ∩ 全局注册表非空（护栏3：空交集拒装配）；max_concurrent 为正整数。
    - response_format：schema ∈ RESPONSE_FORMAT_SCHEMAS。
    - store：max_prefs 为正整数。
    """
    if capability_id == "subagents":
        specs = params.get("specs")
        if specs is None:
            return None  # 不更新 specs 时放行（params 可只改 max_concurrent）
        if not isinstance(specs, list):
            return "specs 必须是规格数组"
        registry = _global_tool_registry()
        for s in specs:
            if not isinstance(s, dict):
                return "每个规格必须是对象"
            for k in ("name", "description", "prompt", "tools"):
                if not s.get(k):
                    return f"规格缺少必填字段 {k}（name/description/prompt/tools）"
            if not isinstance(s["tools"], list) or not all(isinstance(t, str) for t in s["tools"]):
                return f"规格 {s['name']} 的 tools 必须是字符串数组"
            overlap = set(s["tools"]) & registry
            if not overlap:
                return (f"规格 {s['name']} 的工具集与全局工具注册表交集为空（护栏3：拒装配）——"
                        f"非法工具: {sorted(set(s['tools']) - registry)[:6]}")
        mc = params.get("max_concurrent", 2)
        if not isinstance(mc, int) or mc < 1 or mc > 8:
            return "max_concurrent 必须是 1-8 的整数"
    if capability_id == "response_format":
        schema = params.get("schema")
        if schema is not None and schema not in RESPONSE_FORMAT_SCHEMAS:
            return f"schema 非法（允许: {list(RESPONSE_FORMAT_SCHEMAS)}）"
    if capability_id == "store":
        mp = params.get("max_prefs")
        if mp is not None and (not isinstance(mp, int) or mp < 1 or mp > 50):
            return "max_prefs 必须是 1-50 的整数"
    if capability_id == "tool_availability":
        x = params.get("excluded")
        if x is not None:
            if not isinstance(x, list) or not all(isinstance(t, str) and t for t in x):
                return "excluded 必须是工具名字符串数组"
            registry = _global_tool_registry()
            known = registry | set(DEFAULT_TOOL_EXCLUSIONS) | set(LOCKED_TOOL_EXCLUSIONS)
            unknown = [t for t in x if t not in known]
            if unknown:
                return f"未知工具名（不在注册表内）：{sorted(unknown)[:6]}"
            locked = [t for t in x if t in LOCKED_TOOL_EXCLUSIONS]
            if locked:
                return f"物理锁定工具不可排除：{sorted(locked)}（read_file/ls 为技能渐进披露命脉）"
    if capability_id == "rubric":
        # 批13-AB3：评分 mode 枚举校验——skill_prompt=自检段进系统提示词（默认，用户定调）；
        # middleware=独立评分模型路径保留（可切回）。非法值 PATCH -> 400 不落库。
        mode = params.get("mode")
        if mode is not None and mode not in ("skill_prompt", "middleware"):
            return "mode 非法（允许: skill_prompt / middleware）"
    return None


def record_event(capability_id: str, action: str, *, detail: Optional[Dict[str, Any]] = None,
                 updated_by: Optional[str] = None, _sync: bool = False) -> None:
    """写 capability_events。默认 fire-and-forget（_sync=True 供探针/测试即时落库）。"""

    def _do():
        try:
            from app.models.base import CapabilityEvent
            db = _db()
            try:
                db.add(CapabilityEvent(
                    capability_id=capability_id[:64], action=action[:16],
                    detail=detail, updated_by=updated_by,
                ))
                db.commit()
            finally:
                db.close()
        except Exception as e:
            logger.warning(f"[CapabilityEvent] 写入失败(不阻塞主链路): {e}")

    if _sync:
        _do()
        return
    try:
        import threading
        threading.Thread(target=_do, daemon=True).start()
    except Exception:
        _do()


def update_capability(capability_id: str, *, enabled: Optional[bool] = None,
                      params: Optional[Dict[str, Any]] = None,
                      updated_by: Optional[str] = None,
                      close_reason: Optional[str] = None) -> Dict[str, Any]:
    """更新能力策略。physical_blocked -> ValueError（API 层转 403，双保险）；
    🔴 关闭缺理由（<10 字）-> ValueError（API 层转 400）；params 前置校验失败 -> ValueError（400）。
    成功：version+1、写 toggle 事件、清缓存。
    """
    from app.models.base import CapabilityPolicy
    db = _db()
    try:
        row = db.query(CapabilityPolicy).filter(CapabilityPolicy.capability_id == capability_id).first()
        if row is None:
            raise KeyError(capability_id)
        if row.physical_blocked:
            raise PermissionError(row.blocked_reason or "物理锁定能力不可变更")
        if enabled is False and (row.risk_level or "yellow") == "red":
            reason = (close_reason or "").strip()
            if len(reason) < 10:
                raise ValueError("需填写关闭理由（至少 10 字）")
            row.close_reason = reason[:500]
        if params is not None:
            _err = validate_params(capability_id, params)
            if _err:
                raise ValueError(_err)
            merged = dict(row.params or {})
            merged.update(params)
            row.params = merged
        if enabled is not None:
            row.enabled = enabled
        row.updated_by = updated_by
        from sqlalchemy.sql import func as _f
        row.updated_at = _f.now()
        row.version = (row.version or 1) + 1
        db.commit()
        db.refresh(row)
        out = _row_to_dict(row)
        record_event(capability_id, "toggle",
                     detail={"enabled": out["enabled"], "version": out["version"],
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
    """全部回基线：可切件 enabled=True/params=种子基线/close_reason 清空；灰显锁定项保持锁定；version+1。"""
    from app.core.init_db import CAPABILITY_POLICY_SEED
    from app.models.base import CapabilityPolicy
    db = _db()
    try:
        for seed in CAPABILITY_POLICY_SEED:
            row = db.query(CapabilityPolicy).filter(
                CapabilityPolicy.capability_id == seed["capability_id"]).first()
            if row is None:
                row = CapabilityPolicy(capability_id=seed["capability_id"])
                db.add(row)
            row.title = seed["title"]
            row.params = seed.get("params")
            row.risk_level = seed.get("risk_level", "yellow")
            row.description = seed.get("description")
            row.confirm_required = seed.get("confirm_required", True)
            row.physical_blocked = seed.get("physical_blocked", False)
            row.blocked_reason = seed.get("blocked_reason")
            row.updated_by = updated_by
            from sqlalchemy.sql import func as _f
            row.updated_at = _f.now()
            row.version = (row.version or 1) + 1
            if not seed.get("physical_blocked", False):
                row.enabled = True
                row.close_reason = None
        db.commit()
        rows = db.query(CapabilityPolicy).all()
        out = [_row_to_dict(r) for r in rows]
        record_event("all", "reset", detail={"capabilities": [r["capability_id"] for r in out]},
                     updated_by=updated_by, _sync=True)
        _CACHE["data"] = None
        return out
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def cleanup_old_events(days: int = 30) -> int:
    """清理 30 天前 capability_events（启动时调用）。"""
    try:
        from app.models.base import CapabilityEvent
        db = _db()
        try:
            from datetime import datetime, timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)
            n = db.query(CapabilityEvent).filter(CapabilityEvent.ts < cutoff).delete()
            db.commit()
            return n
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[CapabilityEvent] 清理失败: {e}")
        return 0
