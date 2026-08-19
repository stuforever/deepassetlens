"""下一步判断闸门中间件（v3.4 候选判断实时流）

把"为什么执行这一步"做成可见判定说明：模型须在发起工具调用的**同一轮** AIMessage
content 里写明【下一步判断】（已知/判断/因此），再带工具调用。本中间件拦截所有工具调用，
校验不通过则返回 ToolMessage 拒绝（不调 handler，原工具不执行），模型下一轮须补判后重发
--补判是一次新的模型输出与新的工具调用，产生**新的 tool_call_id**，旧调用绝不复用（审计链
清晰）。原工具绝不执行、不伪装重试成功。

两层校验：
- 理由闸门（全工具）：下一步判断存在（标记+已知/判断/因此）、因此行工具名与实际一致、一轮单工具。
- 范围闸门（仅 execute_sql）：声明了客户名集合时，SQL 的 cust_name 过滤 ⊆ 声明范围。

下一步判断格式（模型在 content 内、工具调用前写，标记必须在第一个非空白位置）：
    【下一步判断】
    已知: <来自用户要求、剧本规则或上一步真实结果>
    判断: <为什么当前需要这个工具>
    因此: 调用 <本轮工具名>。
    范围: <仅 execute_sql：客户名精确集合, 逗号分隔, 如 客户001,客户003; 无客户限定写 无>

v3.4：中间件在闸门通过/拒绝时通过 adispatch_custom_event 派发 decision_committed /
decision_rejected 事件，供 SSE 消费层推给前端。前端据此实现"候选判断实时流"。
"""
from __future__ import annotations

import re
from typing import Any, Awaitable, Callable, Optional

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import AIMessage, ToolMessage

from app.services.scope_checker import ScopeCheck, check_customer_scope

# dispatcher 签名: async (event_name: str, payload: dict, config: RunnableConfig | None) -> None
Dispatcher = Callable[[str, dict, Optional[Any]], Awaitable[None]]

# 受范围强校验的工具：全部 4 个数据读取工具（评审点4：不能只保护 execute_sql）。
# 理由校验（已知/判断/因此 + 真实工具名 + 一轮单工具）对所有工具生效；
# 范围强校验（客户名 ⊆ 可信范围）对全部数据工具，由 scope_adapters 按工具参数结构适配。
SCOPE_GATED_TOOLS = frozenset({"execute_sql", "execute_doris_sql", "execute_entity_api", "execute_api_sql"})
# 向后兼容别名
GATED_TOOLS = SCOPE_GATED_TOOLS

# 下一步判断标记：模型同轮 AIMessage.content 须以此标记开头（第一个非空白位置）
DECISION_MARKER = "【下一步判断】"

# 拒绝标记：拒绝 ToolMessage content 含此串，用于统计补判次数 + SSE 侧识别补判
REJECT_MARKER = "下一步判断闸门·拒绝"
# 范围拒绝子标记：范围校验失败专有，用于区分"理由拒绝"与"范围拒绝"--
# 范围补判预算只计范围拒绝，理由拒绝不侵蚀范围补判次数。
SCOPE_REJECT_SUBMARKER = "范围校验失败"

# 最多补判次数（走一次补判）；超过则阻断，不再放行也不再拒绝
MAX_REPAIRS = 1

# 字段提取：单行取值（模型按多行格式写；行内取值遇换行止）
_FIELD_KNOWN = re.compile(r"已知\s*[:：]\s*([^\n]*)")
_FIELD_JUDGE = re.compile(r"判断\s*[:：]\s*([^\n]*)")
_FIELD_THEREFORE = re.compile(r"因此\s*[:：]\s*([^\n]*)")
_FIELD_SCOPE = re.compile(r"范围\s*[:：]\s*([^\n]*)")
_SCOPE_SPLIT = re.compile(r"[,，、\s]+")
# "因此: 调用 execute_sql。" -> 提取工具名
_THEREFORE_TOOL = re.compile(r"调用\s*([A-Za-z_][\w\-]*)")

# 派发失败标记：committed/rejected 派发失败时 ToolMessage content 含此串
DISPATCH_FAIL_MARKER = "判定事件发送失败"


async def _default_dispatcher(event_name: str, payload: dict, config: Optional[Any]) -> None:
    """生产默认 dispatcher：通过 adispatch_custom_event 派发事件。

    在 agent 执行上下文内运行时，contextvar 自动提供 parent run id；
    显式传 config 作为双保险。
    """
    from langchain_core.callbacks import adispatch_custom_event
    await adispatch_custom_event(event_name, payload, config=config)


class DecisionGateMiddleware(AgentMiddleware[Any, Any, Any]):
    """下一步判断闸门中间件：全工具理由校验 + execute_sql 范围强校验。

    Args:
        scope_gated: 需额外范围校验的工具名集合；None 用默认 SCOPE_GATED_TOOLS(=execute_sql)。
        scope_checker: 范围校验函数 (sql, declared) -> ScopeCheck；默认 check_customer_scope。
        max_repairs: 范围校验最多补判次数；超过则阻断。
        reason_gated: True(默认)=全工具理由校验；False=完全关闸门(测试/灰度)。
        dispatcher: 可注入的事件派发函数；默认 _default_dispatcher(adispatch_custom_event)。
            单测传 spy/no-op，生产不传。签名: async (event_name, payload, config) -> None。
    """

    def __init__(
        self,
        scope_gated: frozenset[str] | None = None,
        scope_checker: Callable[[str, Any], ScopeCheck] | None = None,
        max_repairs: int = MAX_REPAIRS,
        reason_gated: bool = True,
        dispatcher: Optional[Dispatcher] = None,
    ) -> None:
        self._scope_gated = scope_gated if scope_gated is not None else SCOPE_GATED_TOOLS
        self._scope_checker = scope_checker or check_customer_scope
        self._max_repairs = max_repairs
        self._reason_gated = reason_gated
        self._dispatcher: Dispatcher = dispatcher or _default_dispatcher

    async def _dispatch(self, event_name: str, payload: dict, request) -> None:
        """派发自定义事件。config 从 request.runtime.config 取（双保险）。"""
        config = request.runtime.config if request.runtime else None
        await self._dispatcher(event_name, payload, config)

    async def awrap_tool_call(self, request, handler):
        # reason_gated=False -> 完全关闸门(测试/灰度)，但仍派发 committed（让前端看到过程）
        if not self._reason_gated:
            tool_name_nogate = request.tool_call.get("name", "")
            tc_id_nogate = request.tool_call.get("id")
            try:
                await self._dispatch("decision_committed", {
                    "tool_call_id": tc_id_nogate, "tool_name": tool_name_nogate,
                    "content": "闸门已关闭(reason_gated=False)",
                }, request)
            except Exception:
                pass  # 关闸门模式不因派发失败阻断
            return await handler(request)

        tool_name = request.tool_call.get("name", "")
        tc_id = request.tool_call.get("id")
        # 范围补判预算只计范围拒绝(含 SCOPE_REJECT_SUBMARKER)；理由拒绝不侵蚀范围补判次数
        scope_attempt = self._count_prior_rejections(request.state, scope_only=True) + 1
        reason_attempt = self._count_prior_rejections(request.state) + 1

        # ---- 理由闸门（全工具）----
        # 1) 定位发起本次 tool_call 的 AIMessage（按 tool_call_id）
        aimsg = self._get_current_aimessage(request)
        aimsg_content = getattr(aimsg, "content", "") if aimsg else ""

        def _reject_and_dispatch(reject_msg: str, reason: str) -> ToolMessage:
            """派发 decision_rejected 事件 + 返回拒绝 ToolMessage。

            rejected 派发失败不静默：记录异常，ToolMessage 带稳定标记，
            让模型知道"判定事件发送失败"（但工具仍不执行）。
            """
            try:
                import asyncio
                # _dispatch 是 async，但这里在 async 上下文，需要 await
                # 不能在同步闭包里 await，改为在外部处理
                pass
            except Exception:
                pass
            # 实际派发在下面 _do_reject 中
            return ToolMessage(content=reject_msg, tool_call_id=tc_id)

        # 2) 一轮单工具：该 AIMessage 不得含多个 tool_call（一条判定说明无法解释多个工具）
        tcs = getattr(aimsg, "tool_calls", None) or []

        # 3) 下一步判断存在性 + 格式校验
        decision = _parse_decision(aimsg_content) if aimsg is not None else None

        # 收集拒绝信息，统一在最后派发 rejected + return
        reject_reason = None
        reject_msg = None
        if aimsg is None:
            reject_reason = "未找到发起本次工具调用的 AIMessage"
            reject_msg = _reject_no_decision(reason_attempt, tool_name)
        elif len(tcs) > 1:
            reject_reason = "一轮多工具调用"
            reject_msg = _reject_multi_tool(reason_attempt)
        elif decision is None:
            reject_reason = f"content 未以 {DECISION_MARKER} 开头"
            reject_msg = _reject_no_decision(reason_attempt, tool_name)
        elif not decision.get("known") or not decision.get("judge") or not decision.get("therefore"):
            reject_reason = "下一步判断字段不全（已知/判断/因此）"
            reject_msg = _reject_incomplete(reason_attempt)
        else:
            # 4) "因此"行工具名与实际 tool_call 名一致
            _t_tool = _THEREFORE_TOOL.search(decision.get("therefore", ""))
            if not _t_tool or _t_tool.group(1) != tool_name:
                reject_reason = f"因此行工具名与实际不符(期望{tool_name})"
                reject_msg = _reject_tool_mismatch(reason_attempt, tool_name)
            else:
                # ---- 范围闸门（全部 scope_gated 数据工具，评审点4）----
                # 可信范围从 Agent state.last_scope 取（不从模型"范围"行取，防自洽绕过）
                if tool_name in self._scope_gated:
                    from app.services.scope_adapters import check_scope_for_tool
                    _trusted = _get_trusted_scope(request.state, request.runtime)
                    if _trusted:  # 有可信范围 -> 强校验 SQL/filters 是否在范围内
                        sc = check_scope_for_tool(tool_name, request.tool_call, _trusted)
                        if not sc.ok:
                            if scope_attempt > self._max_repairs:
                                reject_reason = "范围校验失败且超过补判上限"
                                reject_msg = _reject_block()
                            else:
                                reject_reason = f"范围校验失败: {sc.reason}"
                                reject_msg = _reject_scope(sc, scope_attempt)
                    else:
                        # 无可信范围（首轮或用户未指定）-> 要求模型必须声明范围（"范围:"行）
                        # "范围: 无"也算合法声明（表示无客户范围限制）
                        # 缺少"范围:"行 -> 格式不全，拒绝（防首轮无范围裸奔执行SQL）
                        if not _scope_line_present(aimsg_content):
                            reject_reason = "数据工具决策缺少范围声明（需含'范围:'行）"
                            reject_msg = _reject_missing_scope(reason_attempt, tool_name)

        # ---- 拒绝路径：派发 rejected + return ToolMessage（不调 handler）----
        if reject_msg is not None:
            try:
                await self._dispatch("decision_rejected", {
                    "tool_call_id": tc_id, "tool_name": tool_name,
                    "candidate_content": aimsg_content,
                    "attempt": reason_attempt, "reason": reject_reason,
                }, request)
            except Exception as e:
                # rejected 派发失败不静默：ToolMessage 带稳定标记
                import logging
                logging.getLogger(__name__).error(
                    "[DecisionGate] dispatch rejected failed: %s", e, exc_info=True)
                reject_msg = f"{DISPATCH_FAIL_MARKER}(rejected): {type(e).__name__}"
            return ToolMessage(content=reject_msg, tool_call_id=tc_id)

        # ---- 通过路径：派发 committed + 调 handler ----
        # v3.6: last_scope 在 middleware 内同步更新（评审点4：不从 SSE 路由 ensure_future 写，避免竞态）
        try:
            await self._dispatch("decision_committed", {
                "tool_call_id": tc_id, "tool_name": tool_name,
                "content": aimsg_content,
            }, request)
        except Exception as e:
            # committed 派发失败 -> 失败关闭：不执行工具（过程可见是强约束）
            import logging
            logging.getLogger(__name__).error(
                "[DecisionGate] dispatch committed failed: %s", e, exc_info=True)
            return ToolMessage(
                content=f"{DISPATCH_FAIL_MARKER}(committed): {type(e).__name__}。工具未执行。",
                tool_call_id=tc_id)

        # 从决策文本提取客户范围，同步写入 state.last_scope（不异步、不竞态）
        _update_last_scope(request.state, aimsg_content)

        return await handler(request)

    def _get_current_aimessage(self, request) -> Optional[AIMessage]:
        """定位发起本次 tool_call 的 AIMessage（按 tool_call_id）。

        awrap_tool_call 触发时，发起该 tool_call 的 AIMessage 已 append 到 state.messages
        （model node 先于 tool node）。找不到发起消息（异常）-> None（安全侧拒绝）。
        """
        messages = _get_messages(request.state)
        if not messages:
            return None
        tc_id = request.tool_call.get("id")
        for m in reversed(messages):
            if not isinstance(m, AIMessage):
                continue
            tcs = getattr(m, "tool_calls", None) or []
            if any(tc.get("id") == tc_id for tc in tcs):
                return m
        return None

    def _count_prior_rejections(self, state: Any, scope_only: bool = False) -> int:
        """统计 state.messages 里已有的拒绝 ToolMessage 数。

        拒绝 ToolMessage 的 content 含 REJECT_MARKER。补判产生新 tool_call_id，旧拒绝仍留在
        消息历史里，据此计次。

        Args:
            scope_only: True 时只统计范围拒绝(含 SCOPE_REJECT_SUBMARKER)，用于范围补判预算；
                False 统计全部拒绝，用于理由拒绝消息编号。
        """
        messages = _get_messages(state) or []
        n = 0
        for m in messages:
            if isinstance(m, ToolMessage):
                c = getattr(m, "content", "")
                if isinstance(c, str) and REJECT_MARKER in c:
                    if scope_only and SCOPE_REJECT_SUBMARKER not in c:
                        continue
                    n += 1
        return n


def _parse_decision(content: str) -> Optional[dict]:
    """从 AIMessage.content 解析【下一步判断】（标记 + 字段，多行格式）。

    标记必须在第一个非空白位置（与前端前缀状态机统一标准）。
    无标记/标记位置不对 -> None。有标记但缺字段 -> 对应字段缺失（范围缺失/为"无" -> []，跳过范围校验）。
    """
    if not content:
        return None
    stripped = content.lstrip()
    if not stripped.startswith(DECISION_MARKER):
        return None
    after = stripped[len(DECISION_MARKER):]
    decision: dict = {}
    m = _FIELD_KNOWN.search(after)
    if m:
        decision["known"] = m.group(1).strip()
    m = _FIELD_JUDGE.search(after)
    if m:
        decision["judge"] = m.group(1).strip()
    m = _FIELD_THEREFORE.search(after)
    if m:
        decision["therefore"] = m.group(1).strip()
    m = _FIELD_SCOPE.search(after)
    if m:
        raw = m.group(1).strip()
        if raw and raw != "无":
            decision["scope"] = [s for s in _SCOPE_SPLIT.split(raw) if s]
        else:
            decision["scope"] = []
    return decision


def _get_messages(state: Any):
    """从 agent state 取 messages（兼容 dict / BaseModel）。"""
    if state is None:
        return None
    if isinstance(state, dict):
        return state.get("messages")
    return getattr(state, "messages", None)


def _get_trusted_scope(state: Any, runtime=None):
    """从运行时上下文取可信范围 last_scope。

    F4: 优先从 runtime.context（context_schema 正式接入后的原生路径），
    fallback 到 state.last_scope（兼容旧路径，模型声明的范围仍写 state）。
    已删除 config["configurable"]["last_scope"] 旁路——scope 只走 runtime.context。

    last_scope 有两种来源（按 source 字段区分优先级）：
    - source="user_input"：data_intelligence 从用户原始输入提取的客户名，
      通过 context= 传入（不进 checkpoint），模型无权修改。
    - source="model_declared"：模型在决策文本"范围:"行声明的客户名，
      首轮无 user_input 来源时由 _update_last_scope 写入 state。

    Returns:
        dict{customer_names: [...], ordered: bool, source: str} 或 None（无可信范围）
    """
    # F4: 优先从 runtime.context 读（原生 context_schema 路径，不进 checkpoint）
    if runtime is not None:
        _ctx = getattr(runtime, "context", None)
        if isinstance(_ctx, dict):
            _ctx_scope = _ctx.get("last_scope")
            if _ctx_scope:
                return _ctx_scope
    # 兼容旧路径：从 state.last_scope 读（model_declared 来源）
    if state is None:
        return None
    if isinstance(state, dict):
        return state.get("last_scope")
    return getattr(state, "last_scope", None)


def _update_last_scope(state: Any, decision_content: str):
    """从决策文本提取客户范围，同步写入 state.last_scope。

    source 优先级：user_input（用户原始输入解析）不可被 model_declared 覆盖。
    模型只能在没有 user_input 范围时声明范围，声明后写入 source="model_declared"。
    格式: 范围: 客户001,客户003 或 范围: 无。
    """
    if not decision_content:
        return
    import re as _re
    _scope_match = _re.search(r'范围[:：]\s*(.+)', decision_content)
    if not _scope_match:
        return

    # user_input 来源的范围不可被模型覆盖（防自洽绕过）
    _existing = _get_trusted_scope(state)
    if _existing and _existing.get("source") == "user_input":
        return  # 用户指定的范围，模型无权修改

    _scope_raw = _scope_match.group(1).strip()
    if not _scope_raw or _scope_raw == "无":
        # 范围: 无 -> 清空旧范围（仅清 model_declared，不碰 user_input）
        if _existing and _existing.get("source") == "user_input":
            return  # 不清空用户指定的范围
        if isinstance(state, dict):
            state["last_scope"] = None
        else:
            try: setattr(state, "last_scope", None)
            except: pass
        return
    _customer_names = [c.strip() for c in _re.split(r'[,，、]', _scope_raw) if c.strip()]
    if not _customer_names:
        return
    _new_scope = {
        "customer_names": _customer_names,
        "ordered": True,
        "commitment": "exact_set",
        "source": "model_declared",
    }
    if isinstance(state, dict):
        state["last_scope"] = _new_scope
    else:
        try: setattr(state, "last_scope", _new_scope)
        except: pass


# ---- 拒绝提示（均含 REJECT_MARKER，供计次 + SSE 侧识别补判） ----

def _reject_no_decision(attempt: int, tool_name: str = "工具") -> str:
    return (
        f"{REJECT_MARKER}[第{attempt}次] 未发现同轮【下一步判断】。请在 {tool_name} 调用前用如下格式写"
        f"（与工具调用在同一轮 content 内）：\n"
        f"{DECISION_MARKER}\n已知: <来自用户要求、剧本规则或上一步真实结果>\n"
        f"判断: <为什么当前需要这个工具>\n因此: 调用 {tool_name}。\n"
        f"范围: <仅 execute_sql 需写：客户名精确集合, 逗号分隔, 如 客户001,客户003; 无客户限定写 无>\n"
        f"写完后, 同一轮重新发起 {tool_name}（会生成新的工具调用）。原工具未执行。"
    )


def _reject_incomplete(attempt: int) -> str:
    return (
        f"{REJECT_MARKER}[第{attempt}次] 【下一步判断】字段不全，须同时含 已知/判断/因此 三行。"
        f"请补全后重新发起 execute_sql。原工具未执行。"
    )


def _reject_tool_mismatch(attempt: int, real_tool: str) -> str:
    return (
        f"{REJECT_MARKER}[第{attempt}次] 【下一步判断】的「因此」行工具名与实际调用({real_tool})不一致。"
        f"请将「因此: 调用 {real_tool}。」修正后重新发起。原工具未执行。"
    )


def _reject_multi_tool(attempt: int) -> str:
    return (
        f"{REJECT_MARKER}[第{attempt}次] 一轮含多个工具调用，无法用一段判定说明分别解释。"
        f"请一条回复只调用一个工具，分多轮顺序执行；本轮重新只发起 execute_sql（含完整下一步判断）。"
        f"原工具未执行。"
    )


def _reject_scope(scope_check: ScopeCheck, attempt: int) -> str:
    return (
        f"{REJECT_MARKER}[第{attempt}次范围校验失败] {scope_check.reason}。"
        f"请修正 SQL 的 cust_name 过滤使其 ⊆ 下一步判断声明的范围, 或修正范围声明, "
        f"再重新发起 execute_sql。原工具未执行。"
    )


def _reject_block() -> str:
    return (
        f"{REJECT_MARKER}[二次校验仍失败·已阻断] 已超出补判次数上限。"
        f"不要再重试 execute_sql, 请基于已有信息直接回答用户, "
        f"或说明因校验不通过无法完成该查询。"
    )


def _scope_line_present(decision_content: str) -> bool:
    """检查决策文本是否包含"范围:"行（首轮无 last_scope 时要求模型必须声明范围）。"""
    if not decision_content:
        return False
    import re as _re
    return bool(_re.search(r'范围[:：]\s*\S', decision_content))


def _reject_missing_scope(attempt: int, tool_name: str) -> str:
    return (
        f"{REJECT_MARKER}[第{attempt}次] 数据工具 {tool_name} 的下一步判断缺少「范围」行。"
        f"请补写 范围: <客户名精确集合, 逗号分隔, 如 客户001,客户003; 无客户限定写 无> 后重新发起。"
        f"原工具未执行。"
    )
