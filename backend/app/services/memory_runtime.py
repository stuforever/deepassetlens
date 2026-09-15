# -*- coding: utf-8 -*-
"""记忆插槽②（spec §六）：ContextVar 机关——「同装配、不同人」。

Agent 缓存无用户维度（也不该有），但记忆树 per-user：本 ContextVar 携带
{expert_id, user, session_id, turn_id}，endpoint 在算完 memory_thread_id 处 set、
请求结束 reset；L1 中间件与 MemoryTreeBackend/f 因子**调用时读它**。
异常路径防御（spec §十一）：缺省 wenshu/anonymous（与现状默认一致）。
"""
from contextvars import ContextVar
from typing import Optional

_memory_runtime: ContextVar[Optional[dict]] = ContextVar("tupu_memory_runtime", default=None)


def set_runtime(expert_id: str, user: str, session_id: str = "", turn_id: str = "") -> dict:
    rt = {"expert_id": expert_id, "user": user, "session_id": session_id, "turn_id": turn_id}
    _memory_runtime.set(rt)
    return rt


def update_turn_id(turn_id: str) -> None:
    """run_id 就绪后原位补 turn_id（dict 值可变——set 两次也行，取简）。"""
    rt = _memory_runtime.get()
    if rt is not None:
        rt["turn_id"] = turn_id


def update_runtime(patch: dict) -> None:
    """⑤b（spec §三）：请求级补丁（surface 路由等）——原位合并，缺键不动。"""
    rt = _memory_runtime.get()
    if rt is not None:
        rt.update(patch)


def current() -> dict:
    rt = _memory_runtime.get()
    if rt is None:   # 异常路径缺省（spec §十一）
        return {"expert_id": "wenshu", "user": "anonymous", "session_id": "", "turn_id": ""}
    return rt


def current_user() -> str:
    return current()["user"]


def current_user_strict() -> str:
    """🔴-4（审查 2026-09-15）fail-closed：runtime 未置位即抛——绝不静默落 anonymous
    共享桶（跨用户泄漏面）。教学工具（HTTP MCP 面+进程内 twin）一律走本解析；
    current() 的 wenshu/anonymous 缺省兜底只服务无用户维度的既有只读面（spec §十一）。"""
    rt = _memory_runtime.get()
    if rt is None:
        raise RuntimeError("memory_runtime 未置位：教学工具拒绝执行（fail-closed，🔴-4）")
    return rt["user"]


def reset() -> None:
    _memory_runtime.set(None)
