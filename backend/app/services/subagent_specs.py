"""subagent_specs.py - subagents 受限启用：委派规格构建 + 四护栏（《能力开关中心与subagents受限启用设计》批13-Q 五）

四护栏实现位置：
  护栏1 task 复合条件（契约 allow_subagents AND caps.subagents.enabled）→ skill_policy._precheck（运行时）；
  护栏2 子代理继承守卫 → 本模块：声明式规格显式携带 SkillPolicyMiddleware（deepagents 0.7.7
       声明式 SubAgent 不自动继承父 middleware——graph.py 只继承覆盖默认槽位的件，守卫链必须显式传入）；
  护栏3 工具白名单窄化 → 本模块：specs.tools ∩ 全局工具注册表，空交集拒装配 + spec_invalid 事件；
  护栏4 全程审计 → skill_policy（task_invoke/task_reject）+ capability_events。

降级语义：subagents 关闭或护栏拒绝 -> build_subagent_specs 返回 None -> 回退串行定位（委派是加速器不是依赖项）。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def build_subagent_specs(sub_policy: Dict[str, Any], model, guard_middlewares: Optional[List[Any]] = None,
                         parent_tools: Optional[List[Any]] = None):
    """按 caps.subagents 构建 create_deep_agent 的 subagents 参数。

    Args:
        sub_policy: capability_config.get_policy("subagents") 的 dict（params.specs/max_concurrent）。
        model: 父代理的 chat model（子代理规格必须显式指定 model，deepagents _compile_spec 强校验）。
        guard_middlewares: 传入子代理的守卫链实例（护栏2）——与父代理同栈的 SkillPolicyMiddleware 等。
        parent_tools: 父代理的真实工具对象列表（MCP BaseTool）。规格 tools 按名字映射到这些对象
            （deepagents SubAgent.tools 只接受 BaseTool/Callable/dict，不接受字符串）；
            None 时保留字符串清单（仅供探针/校验做名字级断言，不可用于真实装配）。

    Returns:
        List[dict]（deepagents SubAgent TypedDict 兼容）或 None（subagents 关闭/全部规格被护栏拒绝）。
    """
    if not sub_policy or not sub_policy.get("enabled"):
        return None
    params = sub_policy.get("params") or {}
    specs = params.get("specs") or []
    max_concurrent = int(params.get("max_concurrent") or 2)
    from app.services.capability_config import _global_tool_registry
    registry = _global_tool_registry()
    tools_by_name = {}
    if parent_tools:
        for t in parent_tools:
            name = getattr(t, "name", None)
            if name:
                tools_by_name[name] = t

    from app.services.capability_config import record_event
    out: List[Dict[str, Any]] = []
    for s in specs:
        name = str(s.get("name") or "")
        tools = [t for t in (s.get("tools") or []) if isinstance(t, str)]
        overlap = [t for t in tools if t in registry]
        if not overlap:
            # 护栏3：空交集 -> 拒装配 + spec_invalid 事件
            record_event("subagents", "spec_invalid",
                         detail={"spec_name": name, "reason": "工具集与全局注册表交集为空",
                                 "tools": tools}, updated_by="assembly")
            logger.warning(f"[SubAgentSpecs] 规格 {name} 拒装配（工具交集为空: {tools}）")
            continue
        prompt = str(s.get("prompt") or "")
        if max_concurrent > 1:
            prompt += f"\n（并发约束：最多 {max_concurrent} 个委派并行，超出时串行分批。）"
        spec: Dict[str, Any] = {
            "name": name,
            "description": str(s.get("description") or ""),
            "system_prompt": prompt,
            "model": model,
        }
        if parent_tools:
            # 真实装配：映射到父代理的 BaseTool 对象（护栏3 窄化=交集内且真实存在）
            real = [tools_by_name[t] for t in overlap if t in tools_by_name]
            if not real:
                record_event("subagents", "spec_invalid",
                             detail={"spec_name": name, "reason": "交集工具在父代理工具面中不存在",
                                     "tools": overlap}, updated_by="assembly")
                logger.warning(f"[SubAgentSpecs] 规格 {name} 拒装配（工具不在父代理工具面: {overlap}）")
                continue
            spec["tools"] = real
        else:
            spec["tools"] = overlap  # 名字级清单（探针/校验断言用）
        if guard_middlewares:
            # 护栏2：子代理继承守卫（显式传入，共享契约校验 -> 子代理工具调用产生 guard_events）
            spec["middleware"] = list(guard_middlewares)
        out.append(spec)
    if not out:
        return None
    return out
