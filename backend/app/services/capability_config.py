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
import os
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
            "capability_id": p["capability_id"], "title": p["title"],
            # W-4a：seed_enabled=False 的能力项 fail-safe 也回代码基准=关（env=1 部署由环境变量兜底）
            "enabled": p.get("seed_enabled", True),
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
    """全局能力版本号（缓存键 #c 成分）。

    批13-W 修正：max(version) -> sum(version)。原 max 语义有缺陷——PATCH 非"当前最大行"
    （如 skills/subagents 早期推到 v13 后）时 max 不动 → 缓存键不变 → Agent 永不重建，
    白名单/决策门配置静默失效（W-1 e2e 实测暴露）。sum 对任意行 PATCH 必变化，满足
    「PATCH → version+1 → 缓存键变 → 重装配」的生效链定调。查库异常返回 0。
    """
    try:
        from app.models.base import CapabilityPolicy
        db = _db()
        try:
            v = db.query(CapabilityPolicy.version).all()
        finally:
            db.close()
        return sum([x[0] for x in v if x[0]]) or 0
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


# ============================================================
# 批13-W W-1：工具白名单打勾制（黑名单版 856c7ac 的语义反转，用户 2026-08-24 定调）
# 理由：黑名单对框架升级新增工具漏网（新名字不在名单上自动放行）；白名单天生免疫（没打勾即禁）。
# 机制零新增：装配侧仍喂 HarnessProfile(excluded_tools=...)，本层只做「allowed -> excluded」换算。
# ============================================================
# 白名单勾选域 = MCP 17 件（GENERIC_ALLOWED_TOOLS）+ task（13-Z 子代理，契约层动态裁决）。
# 装配换算公式：excluded = 红线 5 件 ∪ (勾选域 - allowed)。默认 allowed=全勾 -> excluded=红线 5 件
# =黑名单版现状（迁移零行为变化）。
def _w1_managed_universe() -> frozenset:
    try:
        from app.services.query_contract import GENERIC_ALLOWED_TOOLS
        return frozenset(GENERIC_ALLOWED_TOOLS) | {"task"}
    except Exception:
        return frozenset({"task"})


# 物理锁定三件（前端灰显不可取消；PATCH 校验强制保留）：read_file=技能渐进披露命脉，
# ls=文件浏览（域外恒允许，HarnessProfile 从不排除），task=子代理（13-Z 点火后命根子）。
W1_LOCKED_TOOLS: List[str] = ["read_file", "ls", "task"]
# 安全红线 5 件（HarnessProfile 硬排除，不在勾选域——白名单不可配置它们，物理不存在勾选框）
W1_REDLINE_EXCLUSIONS: List[str] = ["grep", "glob", "write_file", "edit_file", "execute"]
# 批13-J 旧名保留（黑名单版兼容引用：test/旧探针读到的默认值即红线 5 件）
DEFAULT_TOOL_EXCLUSIONS: List[str] = list(W1_REDLINE_EXCLUSIONS)
LOCKED_TOOL_EXCLUSIONS: List[str] = ["read_file", "ls"]


def w1_default_allowed() -> List[str]:
    """默认允许集 = 勾选域全勾（17 MCP + task）。fail-safe 基线与种子基线同源。"""
    return sorted(_w1_managed_universe())


# 批13-W W-4：DecisionGate 装卸与范围工具集的代码基准（管理页只能改当前值，基准钉死代码）
DECISION_GATE_SCOPE_DEFAULT = ["execute_sql", "execute_doris_sql", "execute_entity_api", "execute_api_sql"]


def get_decision_gate_config() -> Dict[str, Any]:
    """读决策门配置（W-4a 装卸 + W-4b 范围工具集）。

    enabled 语义（设计 §四迁移注意）：TUPU_DECISION_GATE=1 环境变量为启动兜底（恒开）；
    未设环境变量时以管理页为准（decision_gate.enabled，种子基准=False=关）；
    两者都未设=关。env=0 显式关闭不覆盖管理页开（登记：env 只表达兜底开，不表达强制关）。
    scope_tools：params 优先（PATCH 时 validate_params 已校验 ⊆ 勾选域且非空），缺省=代码常量。
    """
    env_raw = os.getenv("TUPU_DECISION_GATE", "")
    env_on = env_raw == "1"
    cfg_on = False
    scope = list(DECISION_GATE_SCOPE_DEFAULT)
    try:
        p = get_policy("decision_gate")
        if p:
            cfg_on = bool(p.get("enabled"))
            st = (p.get("params") or {}).get("scope_tools")
            if isinstance(st, list) and st and all(isinstance(t, str) and t for t in st):
                scope = [t for t in st if t in _w1_managed_universe()] or list(DECISION_GATE_SCOPE_DEFAULT)
    except Exception as e:
        logger.error(f"[DecisionGateConfig] 读配置失败，scope 用代码常量: {e}")
    return {"enabled": env_on or cfg_on, "scope_tools": scope, "env_fallback": env_raw}


def get_tool_allowance() -> Dict[str, List[str]]:
    """读白名单允许集（tool_availability.params.allowed）。

    返回 {"allowed": [...], "locked": [...]}。**fail-safe 语义反转登记**（设计 §五.3）：
    读配置异常/缺 params -> 返回默认允许集（勾选域全勾）——黑名单版读崩=默认排除 5 件，
    白名单版读崩=默认允许 18 件；两者都是「回到安全可用态」，字面语义相反。
    """
    allowed = w1_default_allowed()
    try:
        p = get_policy("tool_availability")
        if p and isinstance(p.get("params"), dict):
            a = p["params"].get("allowed")
            if isinstance(a, list) and all(isinstance(t, str) and t for t in a):
                universe = _w1_managed_universe()
                # 锁定件强制保留（即使 params 被绕过写入漏勾，运行时也恒允许）
                allowed = [t for t in a if t in universe] + [t for t in W1_LOCKED_TOOLS
                                                             if t in universe and t not in a]
    except Exception as _e:
        logger.error(f"[ToolAllowance] 读白名单失败，fail-safe 全勾: {_e}")
    return {"allowed": sorted(set(allowed)), "locked": list(W1_LOCKED_TOOLS)}


def get_tool_exclusions() -> Dict[str, List[str]]:
    """读工具排除清单（**白名单换算版**，接口形状与黑名单版一致——装配侧零改动）。

    换算公式（设计 §二.2）：excluded = 红线 5 件 ∪ (勾选域 - allowed)。
    默认全勾 -> excluded=红线 5 件（与黑名单版现状逐件一致=迁移零行为变化）；
    locked 恒在 allowed（get_tool_allowance 已强制），勾选域外红线件物理不可勾。
    """
    try:
        allowance = get_tool_allowance()["allowed"]
        _excluded = set(W1_REDLINE_EXCLUSIONS) | (_w1_managed_universe() - set(allowance))
    except Exception as _e:
        logger.error(f"[ToolExclusions] 白名单换算失败，fail-safe 用红线 5 件: {_e}")
        _excluded = set(W1_REDLINE_EXCLUSIONS)
    return {"excluded": sorted(_excluded), "locked": list(W1_LOCKED_TOOLS)}


def migrate_tool_exclusions_to_allowlist(db) -> int:
    """启动迁移（设计 §二.2）：params 含旧 excluded 键且无 allowed -> 换算写回。

    allowed = 勾选域 - excluded（锁定件强制保留）；写回删 excluded 加 allowed，
    version+1，记 migration 事件。返回迁移行数（0=无需迁移）。迁移后默认勾选集=现状允许集=零行为变化。
    """
    from ..models.base import CapabilityPolicy
    try:
        row = db.query(CapabilityPolicy).filter(
            CapabilityPolicy.capability_id == "tool_availability").first()
        if row is None:
            return 0
        params = dict(row.params or {})
        if "allowed" in params or "excluded" not in params:
            return 0  # 已是白名单语义或无配置——不迁移
        old_excluded = {t for t in params.get("excluded") or [] if isinstance(t, str)}
        universe = _w1_managed_universe()
        allowed = sorted(universe - old_excluded)
        # 锁定件强制保留
        allowed += [t for t in W1_LOCKED_TOOLS if t in universe and t not in allowed]
        params.pop("excluded", None)
        params["allowed"] = allowed
        row.params = params
        row.title = "工具白名单"
        row.version = (row.version or 1) + 1
        db.commit()
        record_event("tool_availability", "migration",
                     detail={"from": "excluded", "to": "allowed", "allowed_count": len(allowed),
                             "old_excluded": sorted(old_excluded)}, _sync=True)
        logger.info(f"[W1] 黑名单->白名单迁移完成: allowed {len(allowed)} 件（原 excluded {sorted(old_excluded)}）")
        return 1
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error(f"[W1] 迁移失败（保持旧配置不动）: {e}")
        return 0


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
        # 批13-W W-1：白名单语义——PATCH 的是 allowed（允许集），未知名 400（设计 §二.2）。
        a = params.get("allowed")
        if a is not None:
            if not isinstance(a, list) or not all(isinstance(t, str) and t for t in a):
                return "allowed 必须是工具名字符串数组"
            universe = _w1_managed_universe()
            # ls 是域外恒允许件（HarnessProfile 从不排除），PATCH 里出现不拒（幂等容忍）
            known = universe | {"ls"}
            unknown = [t for t in a if t not in known]
            if unknown:
                return f"未知工具名（不在注册表内）：{sorted(unknown)[:6]}"
            # 锁定件强制保留：取消 = Agent 残废（技能披露/子代理/文件浏览的命根子）
            locked_in_universe = [t for t in W1_LOCKED_TOOLS if t in universe]
            missing_locked = [t for t in locked_in_universe if t not in a]
            if missing_locked:
                return (f"物理锁定工具不可取消：{sorted(missing_locked)}"
                        f"（read_file/task 为技能渐进披露与子代理命脉）")
        # 旧 excluded 键不再接受 PATCH（防黑名单语义混写）：显式给 excluded 直接拒绝
        if params.get("excluded") is not None:
            return "excluded 已退役（W-1 白名单反转）——请改用 allowed（允许集打勾）"
    if capability_id == "rubric":
        # 批13-AB3：评分 mode 枚举校验——skill_prompt=自检段进系统提示词（默认，用户定调）；
        # middleware=独立评分模型路径保留（可切回）。非法值 PATCH -> 400 不落库。
        mode = params.get("mode")
        if mode is not None and mode not in ("skill_prompt", "middleware"):
            return "mode 非法（允许: skill_prompt / middleware）"
    if capability_id == "decision_gate":
        # 批13-W W-4b：范围校验工具集入 params——scope_tools 必须 ⊆ 勾选域且非空（防误传全部清空）。
        st = params.get("scope_tools")
        if st is not None:
            if not isinstance(st, list) or not all(isinstance(t, str) and t for t in st):
                return "scope_tools 必须是工具名字符串数组"
            unknown = [t for t in st if t not in _w1_managed_universe()]
            if unknown:
                return f"未知工具名（不在注册表内）：{sorted(unknown)[:6]}"
            if not st:
                return "scope_tools 不能为空（范围强校验需至少一件；要关闭请用 decision_gate 开关）"
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
                # W-4a：seed_enabled=False 的能力项（decision_gate）reset 回代码基准=关
                row.enabled = seed.get("seed_enabled", True)
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
