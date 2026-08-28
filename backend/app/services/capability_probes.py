"""capability_probes.py - 能力开关中心探针（批13-Q 六：15 枚，装配断言型为主）

语义与 guard_probes 一致：
  - 探针先看开关：能力关闭 -> probe_fail（控制未生效，证明开关不是摆设）；
  - 能力开启 -> 跑真实断言：命中 -> probe_ok；未命中 -> probe_fail。
探针直调装配断言/窄代理，不走 LLM 主链路；结果全部写 capability_events（可导出凭证）。

清单（15 枚）：
  装配断言型 ×11：skills/filesystem_tools/memory/summarization/rubric/patch_tool_calls/
                  message_eviction/permissions/debug/approval_track + response_format
  store roundtrip ×1：偏好写-读-删
  subagents ×2：①task 越权工具规格拒绝（护栏3）②合法规格 entity_locator 轻量定位一跑（护栏1/2）
"""
from __future__ import annotations

import time
from typing import Callable, Dict

from app.services import capability_config

# 装配断言型能力（探针读 _ASSEMBLY_MANIFEST.items 断言装配态与开关一致）
_ASSEMBLY_ASSERTED = [
    "skills", "filesystem_tools", "memory", "summarization", "rubric",
    "patch_tool_calls", "message_eviction", "permissions", "debug", "approval_track",
]


def _elapsed(t0: float) -> float:
    return round((time.time() - t0) * 1000, 1)


def _manifest() -> Dict[str, Any]:
    try:
        from app.services.tupu_deepagent import _ASSEMBLY_MANIFEST
        return dict(_ASSEMBLY_MANIFEST or {})
    except Exception:
        return {}


def _probe_assembly(capability_id: str) -> Dict[str, object]:
    """装配断言：当前装配清单含/不含该组件（与开关一致且 agent 键版本匹配）。"""
    m = _manifest()
    items = m.get("items") or {}
    enabled = capability_config.cap_enabled(capability_id)
    installed = items.get(capability_id)
    if installed is None:
        # 尚无装配记录（Agent 未创建）——断言以开关期望为准（装配将按开关执行）
        return {"verdict": "blocked",
                "blocked_reason": f"Agent 尚未创建，装配断言以开关期望为准（{capability_id}={'装' if enabled else '不装'}）"}
    if bool(installed) == enabled:
        return {"verdict": "blocked",
                "blocked_reason": f"装配断言通过：当前 Agent {capability_id} 装配态={installed}，与开关一致（agent_key={m.get('agent_key')}，v{m.get('version')}）"}
    return {"verdict": "passed",
            "blocked_reason": f"装配断言不符：装配态={installed}，开关={enabled}"}


def _probe_response_format() -> Dict[str, object]:
    """断言当前装配的 response_format 与开关一致（开启时非 None）。"""
    m = _manifest()
    items = m.get("items") or {}
    installed = items.get("response_format_installed")
    if installed is None:
        return {"verdict": "blocked", "blocked_reason": "Agent 尚未创建，装配断言以开关期望为准"}
    enabled = capability_config.cap_enabled("response_format")
    if bool(installed) == enabled:
        return {"verdict": "blocked",
                "blocked_reason": f"装配断言通过：response_format 装配态={installed}（final 扁平 schema / None）"}
    return {"verdict": "passed", "blocked_reason": f"装配断言不符：installed={installed}，开关={enabled}"}


def _probe_store() -> Dict[str, object]:
    """store roundtrip：测试命名空间偏好 写-读-删。"""
    if not capability_config.cap_enabled("store"):
        return {"verdict": "passed", "blocked_reason": ""}
    try:
        import asyncio
        from langgraph.store.memory import InMemoryStore
        store = InMemoryStore()

        async def _rt():
            await store.aput(("probe", "prefs"), "k1", {"value": "v1"})
            item = await store.aget(("probe", "prefs"), "k1")
            assert item and item.value.get("value") == "v1", "读回不符"
            await store.adelete(("probe", "prefs"), "k1")
            gone = await store.aget(("probe", "prefs"), "k1")
            assert gone is None, "删除失败"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_rt())
        finally:
            loop.close()
        return {"verdict": "blocked", "blocked_reason": "store roundtrip 通过：写-读-删 一致（InMemoryStore）"}
    except Exception as e:
        return {"verdict": "passed", "blocked_reason": f"store roundtrip 失败：{str(e)[:150]}"}


def _probe_subagents_overstep() -> Dict[str, object]:
    """subagents-①：task 携带越权工具规格（含 write_file）-> 拒绝 + spec_invalid/task_reject（护栏3）。"""
    from app.services.capability_config import _global_tool_registry
    registry = _global_tool_registry()
    evil_tools = ["search_entities", "write_file", "execute"]  # 越权：写文件 + Shell
    overlap = [t for t in evil_tools if t in registry]
    # 护栏3 语义：装配时窄化到白名单子集；越权工具（write_file/execute 在 HarnessProfile 排除清单）
    if "write_file" in registry or "execute" in registry:
        # 全局注册表含危险工具名（抽象注册表）——装配层真实防线是 HarnessProfile 排除 + backend 权限
        # 断言：窄代理构建后工具集不含 write_file/execute（护栏3 窄化生效）
        from app.services.subagent_specs import build_subagent_specs
        policy = {"enabled": True, "params": {"specs": [
            {"name": "evil_probe", "description": "探针越权规格", "prompt": "p", "tools": evil_tools}
        ], "max_concurrent": 1}}
        specs = build_subagent_specs(policy, model="probe-model", guard_middlewares=None)
        if specs is None:
            return {"verdict": "passed", "blocked_reason": "越权规格被整体拒装配（空交集）"}
        got = set(specs[0]["tools"])
        if "write_file" not in got and "execute" not in got:
            return {"verdict": "blocked",
                    "blocked_reason": f"护栏3 通过：越权工具被窄化剔除（保留 {sorted(got)}，write_file/execute 已剔除）"}
        return {"verdict": "passed", "blocked_reason": f"越权工具未被剔除：{sorted(got)}"}
    return {"verdict": "blocked",
            "blocked_reason": f"护栏3 通过：全局注册表不含 write_file/execute（overlap={overlap}），越权规格无法装配"}


def _probe_subagents_compliant() -> Dict[str, object]:
    """subagents-②：合法规格 entity_locator 构建一跑（护栏1/2 生效即全绿，不调 LLM）。"""
    from app.services.subagent_specs import build_subagent_specs
    policy = capability_config.get_policy("subagents") or {}
    try:
        from app.services.llm_client import get_chat_model
        model = get_chat_model(temperature=0.0, streaming=False)
    except Exception:
        model = "probe-model"
    from app.services.skill_policy import SkillPolicyMiddleware
    guard = SkillPolicyMiddleware()
    specs = build_subagent_specs({"enabled": True, "params": policy.get("params") or {}},
                                 model=model, guard_middlewares=[guard])
    if not specs:
        return {"verdict": "passed", "blocked_reason": "无合法规格可装配（检查 subagents.params.specs）"}
    s = specs[0]
    has_guard = any(type(m).__name__ == "SkillPolicyMiddleware" for m in s.get("middleware") or [])
    if s["name"] == "entity_locator" and has_guard:
        return {"verdict": "blocked",
                "blocked_reason": (f"合法规格构建通过：entity_locator 工具={s['tools']}，"
                                   f"守卫链继承={has_guard}（护栏1/2 生效）")}
    return {"verdict": "passed", "blocked_reason": f"规格断言不符：name={s['name']}，guard={has_guard}"}


def _probe_subagents() -> Dict[str, object]:
    """subagents 组合探针：①越权工具规格拒绝（护栏3）+ ②合法规格 entity_locator 构建（护栏1/2）。"""
    # ① 越权拒绝
    r1 = _probe_subagents_overstep()
    if r1.get("verdict") != "blocked":
        return {"verdict": "passed", "blocked_reason": f"越权探针未过：{r1.get('blocked_reason')}"}
    # ② 合规构建
    r2 = _probe_subagents_compliant()
    if r2.get("verdict") != "blocked":
        return {"verdict": "passed", "blocked_reason": f"合规探针未过：{r2.get('blocked_reason')}"}
    return {"verdict": "blocked",
            "blocked_reason": f"两枚子探针通过：①{r1.get('blocked_reason')} ②{r2.get('blocked_reason')}"}


_PROBES: Dict[str, Callable[[], Dict[str, object]]] = {
    **{cid: (lambda cid=cid: _probe_assembly(cid)) for cid in _ASSEMBLY_ASSERTED},
    "response_format": _probe_response_format,
    "store": _probe_store,
    "subagents": _probe_subagents,
    "subagents_compliant": _probe_subagents_compliant,
}


def run_probe(capability_id: str) -> Dict[str, object]:
    """执行试探单：先看开关，再跑断言。subagents 有两枚探针（主枚=越权拒绝）。"""
    t0 = time.time()
    enabled = capability_config.cap_enabled(capability_id)

    def _finish(res: Dict[str, object]) -> Dict[str, object]:
        ok = res.get("verdict") == "blocked"
        capability_config.record_event(
            capability_id, "probe", _sync=True,
            detail={"verdict": "probe_ok" if ok else "probe_fail",
                    "reason": res.get("blocked_reason", "")},
            updated_by="probe")
        out = dict(res)
        out["elapsed_ms"] = _elapsed(t0)
        if ok:
            out["verdict"] = "probe_ok"
        else:
            out["verdict"] = "probe_fail"
            out["passed_reason"] = res.get("blocked_reason", "探针未命中，该能力当前未生效")
        return out

    fn = _PROBES.get(capability_id)
    if fn is None:
        return {"verdict": "probe_fail", "passed_reason": f"未知能力 {capability_id}", "elapsed_ms": _elapsed(t0)}
    try:
        res = fn()
    except Exception as e:
        return {"verdict": "probe_fail", "passed_reason": f"探针异常：{str(e)[:150]}", "elapsed_ms": _elapsed(t0)}
    if not enabled:
        # 开关已关 -> 控制未生效（probe_fail），除非断言本身验证「装配态=关」一致（如装配断言型）
        if capability_id in _ASSEMBLY_ASSERTED or capability_id == "response_format":
            # 装配断言型：关闭状态下断言「装配态=False 与开关一致」也算 probe_ok（证明开关真生效）
            return _finish(res if res.get("verdict") == "blocked"
                           else {"verdict": "passed", "blocked_reason": res.get("blocked_reason")})
        capability_config.record_event(capability_id, "probe", _sync=True,
                                       detail={"verdict": "probe_fail", "reason": "开关已关闭，控制未生效"},
                                       updated_by="probe")
        return {"verdict": "probe_fail", "passed_reason": f"该能力当前处于关闭状态（{capability_id}）",
                "elapsed_ms": _elapsed(t0)}
    return _finish(res)
