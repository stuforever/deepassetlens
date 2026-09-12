# -*- coding: utf-8 -*-
"""件 A（2026-09-12 极速模式 spec §三）：一键极速/安全预设 + 切换后预热。

组合表硬编码为常量（两档固定，YAGNI 不做自定义组合 UI）——turbo=六站关
（decision_gate/模板/输出/引擎锁/审批轨/工具白名单守卫），sql_safety 与
locate_budget 保留开（只读保护与死循环防护非权限类，两档都显式置开=确定性不变量）；
safe=全站开。实现走既有 guard_config.update_guard / capability_config.update_capability
更新链：逐站调用但版本连续 bump、中间无用户请求 → 实际只重建一次。

签名适配（实况最小适配，2026-09-12 任务 3 落地实测）：
guard_config.update_guard 有 confirm 形参，capability_config.update_capability 没有
——confirm 仅传守卫链，能力链不传（plan 代码块原样会对 capability 抛 TypeError）。
"""
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

PRESET_STATIONS: Dict[str, Dict[str, Dict[str, bool]]] = {
    "turbo": {
        "guards": {"template": False, "output": False, "engine_lock": False,
                   "approval_track": False, "capability": False, "sql_safety": True},
        "capabilities": {"decision_gate": False, "locate_budget": True},
    },
    "safe": {
        "guards": {"template": True, "output": True, "engine_lock": True,
                   "approval_track": True, "capability": True, "sql_safety": True},
        "capabilities": {"decision_gate": True, "locate_budget": True},
    },
}


def apply_preset(mode: str, updated_by: str = "admin") -> Dict[str, Any]:
    """应用预设。幂等（目标态已一致跳过，少 bump 少重建）；逐站失败重试一次，
    仍败分站如实上报（spec §五）。非法 mode -> ValueError（端点层转 400）。"""
    from app.services import guard_config, capability_config
    preset = PRESET_STATIONS.get(mode)
    if preset is None:
        raise ValueError(f"未知模式: {mode}（允许: turbo | safe）")
    stations: list = []

    def _one(kind: str, cur_on, setter, sid: str, target: bool, confirm_kw: dict) -> None:
        for attempt in (1, 2):                       # 逐站幂等重试一次
            try:
                if cur_on(sid) == target:
                    stations.append({"kind": kind, "id": sid, "ok": True, "changed": False})
                    return
                if target is False:                 # 红/黄级关闭统一带理由（update 链校验 ≥10 字）
                    setter(sid, enabled=False, updated_by=updated_by,
                           close_reason=f"预设 {mode} 一键切换（spec 2026-09-12 极速模式）", **confirm_kw)
                else:
                    setter(sid, enabled=True, updated_by=updated_by, **confirm_kw)
                stations.append({"kind": kind, "id": sid, "ok": True, "changed": True})
                return
            except Exception as e:
                if attempt == 2:
                    stations.append({"kind": kind, "id": sid, "ok": False, "error": str(e)})

    for sid, target in preset["guards"].items():
        _one("guard", guard_config.guard_enabled, guard_config.update_guard, sid, target,
             {"confirm": True})                     # update_guard 实测有 confirm 形参
    for cid, target in preset["capabilities"].items():
        _one("capability", capability_config.cap_enabled, capability_config.update_capability, cid, target,
             {})                                    # update_capability 实测无 confirm 形参（最小适配）
    return {"mode": mode, "stations": stations, "all_ok": all(s["ok"] for s in stations)}


async def warmup_default_agent() -> None:
    """切换后预热（复用 main.py L205-215 启动预热模式）：sleep 1.5s → get_tupu_agent("")。
    失败静默（首问按原逻辑重建）。诚实边界：只覆盖默认连接——非默认连接首问仍背
    2~5s 重建（登记接受）。"""
    import asyncio
    import time as _t
    try:
        await asyncio.sleep(1.5)
        from app.services.tupu_deepagent import get_tupu_agent
        _t0 = _t.time()
        await get_tupu_agent("")
        logger.info(f"[preset-warmup] 默认连接 Agent 预热完成 ({(_t.time() - _t0) * 1000:.0f}ms)")
    except Exception as e:
        logger.warning(f"[preset-warmup] 预热失败（首问按原逻辑重建）: {e}")


def schedule_warmup() -> None:
    """在事件循环内挂后台预热任务（guards.py preset 端点调用；创建失败静默）。"""
    try:
        import asyncio
        asyncio.create_task(warmup_default_agent())
    except Exception as e:
        logger.warning(f"[preset] 预热任务创建失败: {e}")
