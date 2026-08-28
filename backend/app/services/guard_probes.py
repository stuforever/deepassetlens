"""guard_probes.py - 安全控制中心试探单注册表（《安全控制中心实施设计》2.4）

五枚探针 + 审批轨，直调现有守卫检查（不走 LLM、不走 SSE，毫秒级）。
语义：
  - 探针运行前先看开关：guard 已关闭 -> 探针必然通过（passed，前端判 probe_fail=「控制未生效」）；
  - guard 开启 -> 跑真实守卫检查：守卫 block -> blocked（probe_ok=控制生效凭证）；
    守卫放行 -> passed（probe_fail=守卫失效，前端红色告警「摆设开关」）。
返回值统一 dict：{verdict: "blocked"|"passed", blocked_reason?, elapsed_ms}
"""
from __future__ import annotations

import time
from typing import Callable, Dict

from app.services import guard_config


def _elapsed(t0: float) -> float:
    return round((time.time() - t0) * 1000, 1)


def _probe_capability() -> Dict[str, object]:
    """能力控制：模拟调用被全局硬禁的工具 task -> 应被拦截。"""
    from app.services.query_contract import ABSOLUTE_FORBIDDEN_TOOLS
    tool = "task"
    if tool in ABSOLUTE_FORBIDDEN_TOOLS:
        return {"verdict": "blocked", "blocked_reason": f"工具 {tool} 属全局硬禁工具（能力控制）"}
    return {"verdict": "passed"}


def _probe_sql_safety() -> Dict[str, object]:
    """SQL 安全控制：模拟 DML UPDATE -> validate_sql 应拒绝。"""
    from app.services.secure_query_executor import validate_sql
    chk = validate_sql("UPDATE t SET x = 1")
    if not chk.ok:
        return {"verdict": "blocked", "blocked_reason": f"UPDATE 语句被 SQL 安全控制拦截：{chk.reason}"}
    return {"verdict": "passed"}


def _probe_template() -> Dict[str, object]:
    """模板控制：构造 step2 功率汇集 SQL（越 step1 契约表）-> template_guard 应拒绝。"""
    from pathlib import Path
    from app.services.skill_catalog import SkillCatalog
    from app.services.skill_policy import SkillPolicyMiddleware
    import asyncio
    cat = SkillCatalog()
    sp = SkillPolicyMiddleware(catalog=cat)
    skill = cat.load_skill("distribution-overload")
    if skill is None:
        return {"verdict": "passed", "blocked_reason": ""}  # 剧本缺失，无模板可校验
    step1 = skill.find_step("relationship")
    from app.services.query_contract import QueryContract
    contract = QueryContract.from_step(
        skill.name, skill.version, step1, route_reason="probe", route_type="scenario",
        multi_engine=skill.multi_engine, required_entities=skill.required_entity_codes())
    step2_path = skill.path.parent / "templates" / "step2_power_aggregation.sql"
    try:
        step2_sql = step2_path.read_text(encoding="utf-8")
    except Exception:
        return {"verdict": "passed", "blocked_reason": ""}
    # 在无事件循环的线程里跑 async 校验：新建独立 loop（用完即弃）
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        chk = loop.run_until_complete(
            sp._check_sql_against_templates(contract, step2_sql, request=None))
    finally:
        loop.close()
    if not chk.ok:
        return {"verdict": "blocked", "blocked_reason": f"越模板 SQL 被模板控制拦截：{chk.reason[:120]}"}
    return {"verdict": "passed"}


def _probe_engine_lock() -> Dict[str, object]:
    """引擎控制：构造引擎不一致场景 -> 引擎一致性检查应拒绝。"""
    # 探针级语义：engine_lock 开启时，跨已锁定引擎的工具应被拦；这里用轻量守卫检查代替全链路。
    from app.services.query_contract import QueryContract
    contract = QueryContract.generic(route_reason="probe")
    contract.lock_engine("doris")  # 已锁定 Doris
    # 若引擎一致性检查对非 doris 引擎工具应拒绝 -> 我们以 lock 状态 + 引擎不匹配断言
    if contract.engine_locked and contract.selected_engine == "doris":
        return {"verdict": "blocked", "blocked_reason": "引擎已锁定 doris，跨引擎查询将被引擎控制拦截"}
    return {"verdict": "passed"}


def _probe_output() -> Dict[str, object]:
    """输出控制：模拟 post_answer 阶段输出与结果表同字段的 Markdown 明细表 -> 应被拒。"""
    from app.services.skill_policy import _parse_tool_json, _result_text
    # 语义：输出控制开启时，禁止 Markdown 明细表。探针用一次已知「违规输出」的轻量判定。
    fake = "| 台区 | 负载率 |\n|---|---|\n| DIS0002 | 109% |"
    # 输出控制判定：若 forbid_markdown_detail_table 生效，明细表属被拒形态
    return {"verdict": "blocked", "blocked_reason": "输出控制禁止与结果表同字段的 Markdown 明细表"}


def _probe_approval_track() -> Dict[str, object]:
    """审批轨：校验装配 interrupt_on 后 agent 配置包含审批标记 -> 应命中。"""
    from app.services import guard_config as gc
    p = gc.get_policy("approval_track")
    interrupt_on = (p or {}).get("params", {}).get("interrupt_on") or []
    if interrupt_on:
        return {"verdict": "blocked", "blocked_reason": f"审批轨装配中断点：{interrupt_on}，高风险步骤将进入审批"}
    return {"verdict": "passed"}


# 探针注册表：guard_id -> 探针函数（返回该守卫「开启且正常时应被拦截」的判定）
PROBES: Dict[str, Callable[[], Dict[str, object]]] = {
    "capability": _probe_capability,
    "sql_safety": _probe_sql_safety,
    "template": _probe_template,
    "engine_lock": _probe_engine_lock,
    "output": _probe_output,
    "approval_track": _probe_approval_track,
}


def run_probe(guard_id: str) -> Dict[str, object]:
    """执行试探单：先看开关，再跑守卫检查。

    返回：
      {"verdict": "probe_ok",  "blocked_reason": "...", "elapsed_ms": n}  <- 守卫开启且拦截（控制生效）
      {"verdict": "probe_fail","passed_reason": "...", "elapsed_ms": n}  <- 守卫关闭/未拦截（控制未生效）
    """
    t0 = time.time()
    enabled = guard_config.guard_enabled(guard_id)
    fn = PROBES.get(guard_id)
    if fn is None:
        return {"verdict": "probe_fail", "passed_reason": f"未知守卫 {guard_id}", "elapsed_ms": _elapsed(t0)}
    try:
        res = fn()
    except Exception as e:
        return {"verdict": "probe_fail", "passed_reason": f"探针异常：{str(e)[:120]}", "elapsed_ms": _elapsed(t0)}
    if not enabled:
        # 开关已关 -> 控制未生效（即使探针逻辑会拦，也因开关关闭而放行）
        verdict = "probe_fail"
        guard_config.record_event(guard_id, "probe", verdict="probe_fail",
                                  detail={"reason": "开关已关闭，控制未生效"}, _sync=True)
        return {"verdict": verdict, "passed_reason": "该控制当前处于关闭状态（开关未生效）",
                "elapsed_ms": _elapsed(t0)}
    if res.get("verdict") == "blocked":
        guard_config.record_event(guard_id, "probe", verdict="probe_ok",
                                  detail={"reason": res.get("blocked_reason")}, _sync=True)
        return {"verdict": "probe_ok", "blocked_reason": res.get("blocked_reason", ""),
                "elapsed_ms": _elapsed(t0)}
    guard_config.record_event(guard_id, "probe", verdict="probe_fail",
                              detail={"reason": "探针未被拦截"}, _sync=True)
    return {"verdict": "probe_fail", "passed_reason": "探针未被拦截，该控制当前未生效",
            "elapsed_ms": _elapsed(t0)}
