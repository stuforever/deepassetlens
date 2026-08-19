"""数据智能对话 API -- 流式问答主端点（自 data_intelligence.py 机械拆分，行为等价）

POST /api/data-intelligence/chat/freeplan/stream
  - 入参：thread_id, user_input, user_selection（可选）
  - 出参：SSE 流式推送（think/token/final/recommend/sql_result/trace/done）

依赖说明：ChatRequest/_build_contract_system_message 仍定义于 data_intelligence.py；
skill_router、RunEventSink 等服务层依赖与拆分前一致，保持在函数体内就近 import。
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from .data_intelligence import ChatRequest, _build_contract_system_message
from .data_intelligence_support import (
    _KG_ACTION_LABELS, _get_session_lock, _extract_customer_names_from_input,
    _extract_recommendations, _build_final_delivery, _build_action_detail,
    _build_result_summary, _build_nonjson_result_summary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-intelligence", tags=["data-intelligence"])


@router.post("/chat/freeplan/stream")
def chat_freeplan_stream(req: ChatRequest, request: Request):
    """数据资产探查（ReAct 流式对话）。

    - ReAct 模式（create_deep_agent），边规划边思考
    - 全量加载 10 个任务级 SKILL.md 到虚拟文件系统
    - astream_events v2 推送
    """
    async def event_iter():
        try:
            aiter = None  # LangGraph 事件迭代器, finally 中 aclose 以响应客户端取消
            _evt_sink = None  # v3.1 关键事件持久化 sink; 提前置 None 防 early-exception 时 except/finally 引用未绑定变量
            _session_lock = None  # v3.5 会话执行锁, finally 中释放
            import asyncio as _asyncio
            from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

            # P1-1: 删除旧技能枚举+files注入（CompositeBackend+skills=["/skills/"] 已接管技能加载）
            # Agent 通过 FilesystemBackend 自主 read_file /skills/*/SKILL.md，无需每次请求手动注入

            # v3.5: 改用全局 Agent 单例（持久化 AsyncSqliteSaver，同 thread_id 跨请求恢复记忆）
            # 不再每请求新建 MemorySaver（旧实现无跨轮记忆）
            from app.services.tupu_deepagent import get_tupu_agent
            agent = await get_tupu_agent(connection_id=req.llm_connection_id or "")

            # v3.6: checkpoint 按真实用户隔离（评审 P0：固定 anonymous 前缀导致跨用户串记忆）
            # 鉴权关闭时 user.sub="anonymous"；启用后用真实 OIDC sub，实现用户级隔离
            from app.core.auth import get_current_user
            _current_user = get_current_user(request)
            _user_prefix = _current_user.sub if _current_user and _current_user.sub else "anonymous"
            _memory_thread_id = f"{_user_prefix}:{req.thread_id}"
            config = {"configurable": {"thread_id": _memory_thread_id, "checkpoint_ns": "freeplan"}, "recursion_limit": 80}

            # v3.5: 同一会话执行锁 -- 防止同 thread_id 并发请求导致 checkpoint 分叉覆盖
            _session_lock = _get_session_lock(_memory_thread_id)
            await _session_lock.acquire()

            # F4: scope 通过原生 context= 参数传递（不进 checkpoint，不混入消息历史）
            # P0-1: 从用户原始输入正则提取客户名，通过 context 传给中间件（source=user_input）
            # 模型无权覆盖此来源（_update_last_scope 遇到 source=user_input 时跳过）
            _user_scope = _extract_customer_names_from_input(req.user_input)
            _ctx = {}
            if _user_scope:
                _ctx["last_scope"] = {
                    "customer_names": _user_scope,
                    "ordered": True,
                    "commitment": "exact_set",
                    "source": "user_input",
                }

            # 跨轮 scope：从 checkpoint state 读上一轮 model_declared 范围
            # （user_input 来源不进 checkpoint，只在本轮 context 里存活）
            if not _ctx.get("last_scope"):
                try:
                    _prev_state = await agent.aget_state(config)
                    _prev_scope = (_prev_state.values or {}).get("last_scope") if _prev_state.values else None
                    if _prev_scope and _prev_scope.get("customer_names"):
                        _ctx["last_scope"] = _prev_scope
                except Exception:
                    pass

            # F4: 删除 SystemMessage 注入 scope（改为 runtime.context 原生路径）
            # 模型从 system_prompt 里知道要写"范围:"行，闸门从 context.last_scope 读可信范围

            # ===== 受控 Skill 问答平台 v2：确定性路由 -> 受控契约 -> 注入 =====
            # SkillRouter 是唯一执行裁判（不让模型猜命中什么）；SkillPolicyMiddleware
            # 从 runtime.context.contract 读契约硬校验；模型只按契约提示在允许范围内工作。
            from app.services.skill_router import route_user_input
            _conversation_ctx = {"thread_id": req.thread_id}
            if _ctx.get("last_scope"):
                _conversation_ctx["last_scope"] = _ctx["last_scope"]
                _conversation_ctx["last_skill"] = None  # 跨轮技能延续由 checkpoint state 提供
            try:
                _prev_state_skill = None
                _prev_state = await agent.aget_state(config)
                if _prev_state and _prev_state.values:
                    _prev_state_skill = (_prev_state.values or {}).get("last_skill")
                if _prev_state_skill:
                    _conversation_ctx["last_skill"] = _prev_state_skill
            except Exception:
                pass
            try:
                _route = route_user_input(req.user_input, _conversation_ctx)
            except Exception as _rte:
                logger.warning(f"[SkillRouter] 路由异常，降级为低权限通用契约: {_rte}")
                from app.services.query_contract import QueryContract
                _route = None
                _fallback_contract = QueryContract.generic(route_reason=f"路由异常降级: {_rte}")
            _contract = getattr(_route, "contract", None) if _route is not None else _fallback_contract

            # 契约注入 runtime.context（SkillPolicyMiddleware 读取的唯一边界）
            if _contract is not None:
                _ctx["contract"] = _contract
                # 每次请求只向模型提供受控工作流上下文（设计 §7.1）；G1: 尾部追加 top-3 已验证示例
                _contract_msg = _build_contract_system_message(_contract, question=req.user_input)
                input_messages = [SystemMessage(content=_contract_msg), HumanMessage(content=req.user_input)]
                logger.info(
                    f"[SkillRouter] route={_route.route_type if _route else 'fallback'} "
                    f"skill={_contract.skill_id} step={_contract.workflow_step} "
                    f"allowed={len(_contract.allowed_tools)} 契约注入成功"
                )
            else:
                input_messages = [HumanMessage(content=req.user_input)]

            # 评审 P1-5：路由成功后确定性写回 last_skill/last_step（跨轮受控上下文；
            # 新场景命中即覆盖；generic/降级清空以免连续上下文误延续）。
            try:
                if _route is not None and _route.route_type == "scenario" and _contract is not None:
                    _state_upd = {"last_skill": _contract.skill_id, "last_step": _contract.workflow_step}
                else:
                    _state_upd = {"last_skill": None, "last_step": None}
                await agent.aupdate_state(config, _state_upd)
            except Exception as _wbe:
                logger.warning(f"[SkillRouter] last_skill/last_step 写回 checkpoint 失败: {_wbe}")

            tool_results = {}
            think_stream = []
            final_sent_at = [0.0]
            llm_round = [0]  # LLM 推理轮次计数器（每轮 ReAct 循环 +1）
            step_counter = [0]  # 工具调用步骤序号(每次 on_tool_start +1), 前端按 step_id 区分同名步骤
            step_start_ts = {}  # step_id -> 开始时间戳, 算每步耗时
            _run_id_to_sid = {}  # ev.run_id -> step_id; on_tool_end 按 run_id 精确归属(替代 think_stream[-1], 修复并行工具/拒绝补判导致的误归属)
            # v3.4 候选判断实时流: round 状态隔离 + tool_call_id -> round_id 映射
            #   _round_states: model_run_id -> {accumulated, classifier, seq}  按轮隔离，on_chat_model_end 后清理
            #   _tcid_to_roundid: tool_call_id -> model_run_id  on_chat_model_end 设，on_custom_event 消费后删
            _round_states: dict[str, dict] = {}
            _tcid_to_roundid: dict[str, str] = {}
            # v3.2 下一步判断: tool_call_id 绑定链
            #   on_chat_model_end 设 _pending_tcid(单工具约束下唯一) -> on_tool_start 消费并记 _run_id_to_tcid
            #   -> on_tool_end 按 run_id 取 tool_call_id。前端按 tool_call_id 关联 decision↔tool(不按中文名)。
            _pending_tcid = [""]   # 本轮 tool_call_id(on_chat_model_end 设, on_tool_start 消费)
            _pending_tcname = [""]  # 本轮 tool_name(同上)
            _pending_reason = [""]  # 本轮"下一步判断"content(on_chat_model_end 设, on_tool_start 写入 think_stream.live_reason)
            _run_id_to_tcid = {}   # ev.run_id -> tool_call_id(on_tool_start 设, on_tool_end 用)
            _sid_to_tool_name = {}  # step_id -> tool_name(on_tool_start 设, data_result 兜底关联用)
            _data_result_sids = set()  # 已由 DataSummaryMiddleware 派发 data_result -> sql_result 的 step_id（防止 on_tool_end 再发截断版覆盖完整数据）
            # v3.1 步骤5: 关键事件持久化(flag-gated+容错); _consume_events 内 append, final/except 里 complete/fail, finally 里 close
            from app.services.run_event_sink import RunEventSink
            _evt_sink = RunEventSink(req.user_input)

            # v3.6 分段计时埋点：定位首响应延迟来源（6.73s 归因，评审要求先测量再归因）
            import time as _time
            _t0 = _time.time()
            _timing = {"first_event": None, "first_model_stream": None,
                       "first_tool_start": None, "first_decision": None,
                       "first_answer_token": None, "total": None}
            def _mark(key):
                if _timing[key] is None:
                    _timing[key] = round((_time.time() - _t0) * 1000)

            yield f"event: status\n"
            yield f"data: {json.dumps({'node': 'DeepAgent', 'phase': 'running', 'text': '小探正在运行中', 'routed_skill': 'free_plan'}, ensure_ascii=False)}\n\n"

            # 受控路由/契约事件（前端据此渲染 RouteCard/ScopeCard/DataAccessCard/ExecutionDecisionCard）
            if _contract is not None:
                yield f"event: route\n"
                yield f"data: {json.dumps((_route.to_dict() if _route is not None else {'route_type': 'fallback', 'contract': _contract.to_dict()}), ensure_ascii=False)}\n\n"
                yield f"event: contract\n"
                yield f"data: {json.dumps(_contract.to_dict(), ensure_ascii=False)}\n\n"

            # 复用 ReAct 路径的事件消费逻辑
            # F4: 通过原生 context= 传递 runtime.context（astream_events 的 **kwargs 会透传给底层）
            aiter = agent.astream_events(
                {"messages": input_messages},
                config=config,
                context=_ctx,
                version="v2",
            ).__aiter__()
            async def _consume_events():
                _task_deadline = _time.time() + 300  # 5分钟硬超时：超过即终止
                # v3.4: 不再用全局 _round_content_buf，完全按 round_id 隔离（_round_states 在外层定义）
                while True:
                    # 5分钟硬超时：超过即终止，aclose 杀掉 agent，不再烧 token
                    if _time.time() > _task_deadline:
                        yield f"event: think\n"
                        yield f"data: {json.dumps({'task': '超时终止', 'kind': 'skill', 'result_summary': '任务超过5分钟被终止', 'result_status': 'error'}, ensure_ascii=False)}\n\n"
                        break
                    try:
                        if final_sent_at[0] > 0:
                            remaining = (final_sent_at[0] + 3.0) - _time.time()
                            if remaining <= 0:
                                break
                            ev = await _asyncio.wait_for(aiter.__anext__(), timeout=remaining)
                        else:
                            ev = await aiter.__anext__()
                    except StopAsyncIteration:
                        break
                    except _asyncio.TimeoutError:
                        break
                    etype = ev.get("event", "")
                    name = ev.get("name", "")
                    data = ev.get("data", {})
                    _mark("first_event")

                    if etype == "on_chat_model_stream":
                        _mark("first_model_stream")
                        chunk = data.get("chunk")
                        if chunk is None:
                            continue
                        # v3.4 候选判断实时流：逐 token 推送，不再缓冲到 on_chat_model_end
                        # 前缀状态机：识别【下一步判断】开头 -> decision_draft；否则 -> answer_draft
                        content = getattr(chunk, "content", "")
                        if not (isinstance(content, str) and content):
                            continue
                        _rid = ev.get("run_id", "")
                        _rs = _round_states.setdefault(_rid, {"accumulated": "", "classifier": "detecting", "seq": 0})
                        _rs["accumulated"] += content
                        _rs["seq"] += 1
                        _marker = "【下一步判断】"
                        if _rs["classifier"] == "detecting":
                            _stripped = _rs["accumulated"].lstrip()
                            if _marker.startswith(_stripped) and len(_stripped) < len(_marker):
                                continue  # 仍是标记前缀，等待更多 token
                            if _stripped.startswith(_marker):
                                _rs["classifier"] = "decision"
                                # 首次冲刷：推完整累积内容（不丢前面的标记和文字）
                                yield f"event: think_token\n"
                                yield f"data: {json.dumps({'kind': 'decision_draft', 'round_id': _rid, 'delta': _rs['accumulated']}, ensure_ascii=False)}\n\n"
                                continue
                            else:
                                _rs["classifier"] = "answer"
                                _mark("first_answer_token")
                                yield f"event: think_token\n"
                                yield f"data: {json.dumps({'kind': 'answer_draft', 'round_id': _rid, 'delta': _rs['accumulated']}, ensure_ascii=False)}\n\n"
                                continue
                        # 已识别，只推增量
                        _kind = "decision_draft" if _rs["classifier"] == "decision" else "answer_draft"
                        yield f"event: think_token\n"
                        yield f"data: {json.dumps({'kind': _kind, 'round_id': _rid, 'delta': content}, ensure_ascii=False)}\n\n"
                        continue

                    if etype == "on_chat_model_end":
                        out = data.get("output")
                        _rid = ev.get("run_id", "")
                        # 取并清理 round 状态（完全以 round_states 为准，不用全局缓冲）
                        _rs = _round_states.pop(_rid, None)
                        _accumulated = _rs["accumulated"] if _rs else ""
                        if out is not None:
                            has_tc = bool(getattr(out, "tool_calls", None))
                            # 优先用 AIMessage.output.content，其次 round accumulated
                            c = getattr(out, "content", "") or _accumulated
                            if not has_tc:
                                # 最终答案：推 answer_committed（完整正文校准，防丢字）
                                if c and isinstance(c, str) and c.strip():
                                    tool_results["ai_reply"] = c
                                    yield f"event: think_token\n"
                                    yield f"data: {json.dumps({'kind': 'answer_committed', 'round_id': _rid, 'content': c}, ensure_ascii=False)}\n\n"
                                    if _evt_sink is not None:
                                        _evt_sink.append("answer.committed", {"round_id": _rid, "content_len": len(c), "content": c[:2000]})
                            # 有 tool_calls -> 存映射 tool_call_id -> round_id，等中间件 committed/rejected
                            if has_tc:
                                _tcs = getattr(out, "tool_calls", None) or []
                                for _tc in _tcs:
                                    _tc_id = _tc.get("id", "") if isinstance(_tc, dict) else getattr(_tc, "id", "")
                                    _tc_name = _tc.get("name", "") if isinstance(_tc, dict) else getattr(_tc, "name", "")
                                    _tc_args = _tc.get("args", {}) if isinstance(_tc, dict) else getattr(_tc, "args", {})
                                    # task 用对应工具中文名, 与 on_tool_start task_label 一致(前端兼容 task 匹配)
                                    if _tc_name == "kg_api" and isinstance(_tc_args, dict):
                                        _rtask = _KG_ACTION_LABELS.get(_tc_args.get("action", ""), _tc_args.get("action", ""))
                                    elif _tc_name == "read_file":
                                        _rtask = "读技能"
                                    elif _tc_name == "write_todos":
                                        _rtask = "任务规划"
                                    elif _tc_name in _KG_ACTION_LABELS:
                                        _rtask = _KG_ACTION_LABELS[_tc_name]
                                    else:
                                        _rtask = _tc_name
                                    # 存映射：中间件 on_custom_event 时用 tool_call_id 反查 round_id
                                    _tcid_to_roundid[_tc_id] = _rid
                                    # 仍设 _pending（兼容 on_tool_start 的 tool_call_id 绑定）
                                    _pending_tcid[0] = _tc_id
                                    _pending_tcname[0] = _tc_name
                                    _pending_reason[0] = c if (c and isinstance(c, str) and c.strip()) else ""
                                llm_round[0] += 1
                        continue

                    if etype == "on_tool_start":
                        _mark("first_tool_start")
                        task_label = name
                        inp = data.get("input", {})
                        action = inp.get("action", "") if (name == "kg_api" and isinstance(inp, dict)) else ""
                        # 判定 kind：write_todos=规划，其他=技能调用
                        if name == "write_todos":
                            _kind = "plan"
                            task_label = "任务规划"
                        else:
                            _kind = "skill"
                            if name == "kg_api" and isinstance(inp, dict):
                                task_label = _KG_ACTION_LABELS.get(action, action)
                            elif name == "read_file":
                                task_label = "读技能"
                            elif name in _KG_ACTION_LABELS:
                                # DeepAgent 直接暴露工具名(execute_sql/validate_safe_sql 等),
                                # 映射中文任务名以匹配 on_tool_end 的 last_task 分支(SQL执行/校验SQL)
                                task_label = _KG_ACTION_LABELS[name]
                        # 自然语言 detail（调用'XX'技能包的'XX'工具）
                        input_detail = _build_action_detail(name, action, inp if isinstance(inp, dict) else {})
                        # 中文参数摘要（不再暴露 action=xxx, params=xxx）
                        input_summary = ""
                        raw_params = ""
                        if name == "kg_api" and isinstance(inp, dict):
                            raw_params = inp.get("params", "")
                            input_summary = f"输入参数：{str(raw_params)[:200]}" if raw_params else ""
                        elif name == "write_todos":
                            todos = inp.get("todos", []) if isinstance(inp, dict) else []
                            input_summary = f"规划 {len(todos)} 步" if todos else ""
                        elif isinstance(inp, dict):
                            # DeepAgent 直接工具(execute_sql/validate_safe_sql 等), 整个输入 dict 即参数, 如 {'sql': '...'}
                            raw_params = inp
                            input_summary = f"输入参数：{str(inp)[:200]}"
                        # 提取完整 SQL(execute_sql/validate_safe_sql 时), 供前端展示与复制(不被200字符截断)
                        sql_full = ""
                        if name == "kg_api" and action == "execute_sql" and raw_params:
                            if isinstance(raw_params, dict):
                                sql_full = raw_params.get("sql", "")
                            elif isinstance(raw_params, str):
                                try:
                                    _rpj = json.loads(raw_params)
                                    sql_full = _rpj.get("sql", "") if isinstance(_rpj, dict) else ""
                                except Exception:
                                    try:
                                        import ast as _ast
                                        _rpj = _ast.literal_eval(raw_params)
                                        sql_full = _rpj.get("sql", "") if isinstance(_rpj, dict) else ""
                                    except Exception:
                                        sql_full = ""
                        elif name in ("execute_sql", "validate_safe_sql") and isinstance(raw_params, dict):
                            sql_full = raw_params.get("sql", "")
                        # 步骤序号 + 耗时起点(前端按 step_id 区分同名步骤, 防剧本多步 execute_sql 互相覆盖)
                        step_counter[0] += 1
                        _sid = step_counter[0]
                        _started_at_ms = int(_time.time() * 1000)
                        step_start_ts[_sid] = _time.time()
                        _run_id_to_sid[ev.get("run_id", "")] = _sid  # on_tool_end 按 run_id 精确归属(同 run_id 的 start/end 是同一次工具调用)
                        # v3.2: 绑定 tool_call_id(来自 on_chat_model_end 的 decision.committed), 前端按 id 关联 decision↔tool
                        _tcid = _pending_tcid[0]
                        if _tcid:
                            _run_id_to_tcid[ev.get("run_id", "")] = _tcid
                        _tool_name = action if (name == "kg_api" and action) else name
                        _sid_to_tool_name[_sid] = _tool_name  # data_result 兜底关联用
                        # R1: 检测是否为补判重试--同 tool_name 的最近 rejected 步骤，关联 step_id
                        # 让前端能展示"#4 校验SQL(失败) -> #5 校验SQL(修正后重试)"的因果关系
                        _retry_of_step = None
                        for _ts in reversed(think_stream):
                            if (_ts.get("tool_name") == _tool_name
                                    and _ts.get("phase") == "rejected"
                                    and not _ts.get("superseded")):
                                _retry_of_step = _ts.get("step_id")
                                _ts["superseded"] = True  # 标记被重试取代
                                break
                        logger.info(f"[STEP] sid={_sid} counter={step_counter[0]} name={name} action={action} run_id={ev.get('run_id','')[:8]} tcid={_tcid[:8]} sql_full_len={len(sql_full)} retry_of={_retry_of_step}")
                        _evt_sink.append("tool.started", {"tool_name": _tool_name, "action": action, "input_summary": input_summary, "sql_full": sql_full[:500], "retry_of_step": _retry_of_step}, step_id=str(_sid))
                        yield f"event: think\n"
                        yield f"data: {json.dumps({'task': task_label, 'kind': _kind, 'strategy': 'free_plan', 'action': input_detail, 'detail': input_detail, 'input_summary': input_summary, 'step_id': _sid, 'step_no': _sid, 'tool_name': _tool_name, 'tool_call_id': _tcid, 'sql_full': sql_full, 'result_status': 'running', 'phase': 'running', 'live_reason': _pending_reason[0], 'retry_of_step': _retry_of_step, 'started_at_ms': _started_at_ms}, ensure_ascii=False)}\n\n"
                        think_stream.append({"task": task_label, "kind": _kind, "strategy": "free_plan", "action": input_detail, "result_status": "running", "phase": "running", "detail": input_detail, "input_summary": input_summary, "step_id": _sid, "step_no": _sid, "tool_name": _tool_name, "tool_call_id": _tcid, "live_reason": _pending_reason[0], "sql_full": sql_full, "retry_of_step": _retry_of_step, "started_at_ms": _started_at_ms})
                        _pending_reason[0] = ""  # 消费, 避免串到下一轮
                        continue

                    if etype == "on_tool_end":
                        output = data.get("output")
                        out_str = ""
                        if output is not None:
                            if isinstance(output, str):
                                out_str = output
                            elif isinstance(output, dict):
                                out_str = json.dumps(output, ensure_ascii=False, default=str)
                            elif hasattr(output, "content"):
                                # content 可能是 dict/list（非 str），需用 json.dumps 而非 str()
                                if isinstance(output.content, str):
                                    out_str = output.content
                                elif isinstance(output.content, (dict, list)):
                                    out_str = json.dumps(output.content, ensure_ascii=False, default=str)
                                else:
                                    out_str = str(output.content)
                            else:
                                out_str = str(output)
                        parsed = None
                        if isinstance(out_str, str) and "{" in out_str:
                            import re as _re
                            brace_idx = out_str.find("{")
                            if brace_idx > 0:
                                out_str = out_str[brace_idx:]
                            json_match = _re.search(r'\{.*\}', out_str, _re.DOTALL)
                            if json_match:
                                try:
                                    parsed = json.loads(json_match.group(0))
                                except Exception:
                                    parsed = None
                                # JSON 解析失败时，尝试用 ast.literal_eval 处理 Python dict str（单引号）
                                if parsed is None:
                                    try:
                                        import ast as _ast
                                        parsed = _ast.literal_eval(json_match.group(0))
                                        # 转成标准 dict 后再 json.dumps 确保可序列化
                                        if isinstance(parsed, dict):
                                            parsed = json.loads(json.dumps(parsed, ensure_ascii=False, default=str))
                                    except Exception as _ast_err:
                                        logger.debug(f"[DEBUG ast.literal_eval failed] err={_ast_err} match_len={len(json_match.group(0))} match_tail={json_match.group(0)[-100:]}")
                                        parsed = None

                        # DeepAgent 工具返回统一为 {"type":"text","text":"<JSON字符串>"} 格式, 解析嵌套 text 字段取真实数据(columns/rows/safe 等)
                        if isinstance(parsed, dict) and isinstance(parsed.get("text"), str):
                            try:
                                _inner = json.loads(parsed["text"])
                                if isinstance(_inner, dict):
                                    parsed = _inner
                            except Exception:
                                pass

                        # 按 ev.run_id 精确归属(替代 think_stream[-1]): 并行工具调用/拒绝补判时,
                        # on_tool_end 触发时 think_stream[-1] 可能已是别的工具, 会把结果挂错步骤。
                        _sid = _run_id_to_sid.pop(ev.get("run_id", ""), None)  # pop: 一次性, 释放内存
                        _tcid = _run_id_to_tcid.pop(ev.get("run_id", ""), "")  # v3.2: tool_call_id(前端按 id 关联)
                        _item = None
                        if _sid is not None:
                            for _ts in think_stream:
                                if _ts.get("step_id") == _sid:
                                    _item = _ts
                                    break
                        last_task = (_item["task"] if _item else (think_stream[-1]["task"] if think_stream else name))
                        # 每步耗时(ms)
                        _duration_ms = None
                        if _sid is not None and _sid in step_start_ts:
                            _duration_ms = int((_time.time() - step_start_ts[_sid]) * 1000)

                        # v3.2: 闸门拒绝(下一步判断不通过)-> 该步标记补判中, 推 decision_rejected; 不当正常结果
                        _is_reject = isinstance(out_str, str) and "下一步判断闸门·拒绝" in out_str

                        # 调试日志：诊断 on_tool_end 解析情况
                        logger.debug(f"[DEBUG freeplan on_tool_end] name={name} last_task={last_task} sid={_sid} tcid={_tcid[:8]} dur={_duration_ms} reject={_is_reject} parsed_is_none={parsed is None} out_str[:200]={out_str[:200]}")

                        if _is_reject:
                            # 闸门拒绝: 只更新 think_stream（供 done 事件），不发 think 事件
                            # 前端可见性完全由 decision_rejected (custom event / Path B) 控制：
                            #   空 candidate_content = 格式拒绝 -> 前端删步骤（用户不可见）
                            #   非空 candidate_content = 范围拒绝 -> 前端显示详情
                            if _item is None and think_stream:
                                _item = think_stream[-1]
                            if _item is not None:
                                _item["result_status"] = "rejected"
                                _item["phase"] = "rejected"
                                _item["result_summary"] = "判定需补充信息·补判中"
                                if _duration_ms is not None:
                                    _item["duration_ms"] = _duration_ms
                            continue  # 跳过下方 parsed 处理 + think 事件 yield
                        if parsed:
                            tool_log = parsed.get("log", "") if isinstance(parsed, dict) else ""
                            if last_task == "校验L2":
                                tool_results["l2_name"] = parsed.get("l2_name", "")
                                tool_results["l2_id"] = parsed.get("l2_id", "")
                                yield f"event: trace\n"
                                yield f"data: {json.dumps({'node': '校验L2', 'status': 'locked' if parsed.get('valid') else 'needs_clarification', 'l2_name': parsed.get('l2_name', ''), 'detail': tool_log}, ensure_ascii=False)}\n\n"
                            elif last_task in ("SQL执行", "Doris跨对象SQL", "Doris整合") or name in ("execute_sql", "execute_doris_sql", "execute_entity_api", "execute_api_sql"):
                                # P0-fix: 所有数据查询工具（execute_sql/execute_doris_sql/execute_entity_api/execute_api_sql）
                                # 都要捕获 sql_result，不只 execute_sql（原 last_task=="SQL执行" 只覆盖 kg_api.action=execute_sql）
                                _sql_err = parsed.get("error") if isinstance(parsed, dict) else None
                                if _sql_err:
                                    tool_results["sql_executed"] = False
                                    tool_results["sql_error"] = _sql_err
                                    yield f"event: trace\n"
                                    yield f"data: {json.dumps({'node': last_task or name, 'status': 'error', 'error': _sql_err, 'detail': tool_log or _sql_err, 'step_id': _sid}, ensure_ascii=False)}\n\n"
                                else:
                                    tool_results["sql_executed"] = True
                                    tool_results["sql_result"] = parsed
                                    tool_results["assembled_sql"] = parsed.get("sql", "")
                                    yield f"event: trace\n"
                                    yield f"data: {json.dumps({'node': last_task or name, 'status': 'done', 'row_count': parsed.get('row_count', 0), 'detail': tool_log, 'step_id': _sid}, ensure_ascii=False)}\n\n"
                                    # 仅当 DataSummaryMiddleware 未派发 data_result（完整数据）时才在此发 sql_result。
                                    # 若已派发（_sid in _data_result_sids），此处 parsed 已被截断为前10行，再发会覆盖前端的完整数据。
                                    if _sid not in _data_result_sids:
                                        yield f"event: sql_result\n"
                                        yield f"data: {json.dumps({'columns': parsed.get('columns', []), 'rows': parsed.get('rows', []), 'row_count': parsed.get('row_count', 0), 'sql': parsed.get('sql', ''), 'step_id': _sid, 'step_no': _sid, 'returned_rows': len(parsed.get('rows', [])), 'is_preview': False, 'llm_is_preview': parsed.get('_truncated', False), 'llm_preview_row_count': parsed.get('llm_preview_row_count', parsed.get('preview_row_count', 0)), 'result_available_for_ui': True, 'data_snapshot_at': parsed.get('data_snapshot_at'), 'cache_sources': parsed.get('cache_sources')}, ensure_ascii=False, default=str)}\n\n"
                            else:
                                if tool_log:
                                    yield f"event: trace\n"
                                    yield f"data: {json.dumps({'node': last_task or name, 'status': 'done', 'detail': tool_log}, ensure_ascii=False)}\n\n"

                        # 按 _item(step_id 精确定位)更新结果; run_id 未命中时降级用 think_stream[-1](老逻辑兜底)
                        # 注: 拒绝步骤已在上方 continue 跳过, 不会到达此处
                        if _item is None and think_stream:
                            _item = think_stream[-1]
                        if _item is not None:
                            if parsed:
                                if isinstance(parsed, dict) and parsed.get("error"):
                                    _rs_status = "error"
                                else:
                                    _rs_status = "locked" if (parsed.get("safe", parsed.get("valid", True))) else "done"
                                result_summary = _build_result_summary(last_task, parsed)
                            else:
                                # 非 JSON 返回（如 read_file 返回技能文件内容）
                                _rs_status = "done"
                                result_summary = _build_nonjson_result_summary(last_task, name, out_str)
                            # phase: 执行终态（done/error），与 result_status(业务结果 locked/done/error) 分离
                            # locked 是业务结果（SQL安全校验通过），不兼任执行阶段
                            _phase = "error" if _rs_status == "error" else "done"
                            _item["result_status"] = _rs_status
                            _item["phase"] = _phase
                            if result_summary:
                                _item["result_summary"] = result_summary
                            if _duration_ms is not None:
                                _item["duration_ms"] = _duration_ms
                            # 推送 think 更新事件：带 phase/result_status/step_id/tool_call_id/duration_ms
                            _end_kind = _item.get("kind", "skill")
                            yield f"event: think\n"
                            yield f"data: {json.dumps({'task': last_task, 'kind': _end_kind, 'result_summary': result_summary, 'step_id': _sid, 'tool_call_id': _tcid, 'duration_ms': _duration_ms, 'result_status': _rs_status, 'phase': _phase}, ensure_ascii=False)}\n\n"
                            _evt_sink.append("tool.completed", {"task": last_task, "tool_name": name, "result_summary": (result_summary or "")[:500], "result_status": _rs_status, "duration_ms": _duration_ms}, step_id=str(_sid) if _sid is not None else None)
                            # v3.6: 推送 transition 事件（评审：每步有明确转场，前端可展示"为什么继续下一步"）
                            _trans_text = "执行成功，继续下一步" if _phase == "done" else "执行失败，需要修正"
                            yield f"event: transition\n"
                            yield f"data: {json.dumps({'step_id': _sid, 'tool_call_id': _tcid, 'task': last_task, 'from_phase': 'running', 'to_phase': _phase, 'result_summary': (result_summary or '')[:200], 'transition': _trans_text}, ensure_ascii=False)}\n\n"
                        continue

                    if etype == "on_custom_event":
                        # v3.4: 中间件派发的 decision_committed / decision_rejected 事件
                        _cname = ev.get("name", "")
                        _cdata = data if isinstance(data, dict) else {}
                        if _cname == "decision_committed":
                            _mark("first_decision")
                            _tcid = _cdata.get("tool_call_id", "")
                            # 用后即删：反查 round_id，避免长对话内存累积
                            _rid = _tcid_to_roundid.pop(_tcid, None)
                            _tcn = _cdata.get("tool_name", "")
                            _content = _cdata.get("content", "")
                            # v3.6: last_scope 已由 DecisionGateMiddleware 同步写入 state（不再在 SSE 路由异步写）
                            # task 中文名（与 on_tool_start 一致）
                            _rtask = _KG_ACTION_LABELS.get(_tcn, _tcn)
                            yield f"event: think_token\n"
                            yield f"data: {json.dumps({'kind': 'decision_committed', 'round_id': _rid, 'tool_call_id': _tcid, 'tool_name': _tcn, 'task': _rtask, 'content': _content}, ensure_ascii=False)}\n\n"
                            if _evt_sink is not None:
                                _evt_sink.append("decision.committed", {"round_id": _rid, "tool_call_id": _tcid, "tool_name": _tcn, "content_len": len(_content), "content": _content[:2000]})
                        elif _cname == "decision_rejected":
                            _tcid = _cdata.get("tool_call_id", "")
                            _rid = _tcid_to_roundid.pop(_tcid, None)
                            _tcn = _cdata.get("tool_name", "")
                            yield f"event: think_token\n"
                            yield f"data: {json.dumps({'kind': 'decision_rejected', 'round_id': _rid, 'tool_call_id': _tcid, 'tool_name': _tcn, 'candidate_content': _cdata.get('candidate_content', ''), 'attempt': _cdata.get('attempt', 0), 'reason': _cdata.get('reason', '')}, ensure_ascii=False)}\n\n"
                            if _evt_sink is not None:
                                _evt_sink.append("decision.rejected", {"round_id": _rid, "tool_call_id": _tcid, "tool_name": _tcn, "attempt": _cdata.get('attempt', 0), "reason": _cdata.get('reason', '')[:500]})
                        elif _cname == "data_result":
                            # 数据查询结果摘要中间件派发：完整数据推前端直出（不经 LLM 全量转手）
                            # 关联 step_id：优先按 run_id（on_tool_start 已映射），custom_event 异步延迟导致
                            # on_tool_end 可能已 pop，故兜底按 tool_name 找最近同名步骤（ReAct 串行无并行风险）
                            _ev_run_id = ev.get("run_id", "")
                            _d_sid = _run_id_to_sid.get(_ev_run_id)
                            _d_tool = _cdata.get("tool_name", "")
                            if _d_sid is None and _d_tool:
                                _d_sid = max((_s for _s, _tn in _sid_to_tool_name.items() if _tn == _d_tool), default=None)
                            if _d_sid is not None:
                                _data_result_sids.add(_d_sid)  # 标记：此 step_id 的完整数据已推送，on_tool_end 不再发截断版覆盖
                            _d_rows = _cdata.get("rows", [])
                            _d_rc = _cdata.get("row_count", 0)
                            yield f"event: sql_result\n"
                            yield f"data: {json.dumps({'columns': _cdata.get('columns', []), 'rows': _d_rows, 'row_count': _d_rc, 'sql': _cdata.get('sql', ''), 'returned_rows': _cdata.get('returned_rows', len(_d_rows)), 'preview_row_count': _cdata.get('preview_row_count', min(10, _d_rc)), 'is_preview': _cdata.get('is_preview', False), 'llm_is_preview': _cdata.get('llm_is_preview', False), 'llm_preview_row_count': _cdata.get('llm_preview_row_count', 0), 'result_available_for_ui': _cdata.get('result_available_for_ui', True), 'step_id': _d_sid, 'tool_name': _d_tool, 'data_snapshot_at': _cdata.get('data_snapshot_at'), 'cache_sources': _cdata.get('cache_sources')}, ensure_ascii=False, default=str)}\n\n"
                        elif _cname in ("engine.selected", "stop.reached", "policy.rejected",
                                       "template.bound", "template.drift", "correction.attempt"):
                            # 评审 P1-3：SkillPolicy 自定义事件动态推 SSE —— 运行中引擎确认/终止/
                            # 策略拒绝/模板绑定/漂移实时可见，前端按 run_id 合并更新当前契约（不等 done）。
                            # engine/stop 事件 payload 携带最新 contract.to_dict()（与 _ctx 同一对象）。
                            _cc = _cdata.get("contract") if isinstance(_cdata, dict) else None
                            if _cname in ("engine.selected", "stop.reached"):
                                _emit_ev = "contract_update"
                                _payload = {
                                    "kind": _cname,
                                    "tool_call_id": _cdata.get("tool_call_id", ""),
                                    "tool_name": _cdata.get("tool_name", ""),
                                    "reason": _cdata.get("reason", ""),
                                    "selected_engine": _cdata.get("selected_engine"),
                                    "multi_engine": _cdata.get("multi_engine", False),
                                    "completed_engines": _cdata.get("completed_engines"),
                                    "entity_engine_map": _cdata.get("entity_engine_map"),
                                    "contract": _cc,
                                }
                            elif _cname == "policy.rejected":
                                _emit_ev = "policy"
                                _payload = {
                                    "kind": "policy.rejected",
                                    "tool_call_id": _cdata.get("tool_call_id", ""),
                                    "tool_name": _cdata.get("tool_name", ""),
                                    "reason": _cdata.get("reason", ""),
                                    "attempt": _cdata.get("attempt", 0),
                                    "blocked": _cdata.get("blocked", False),
                                }
                            elif _cname == "correction.attempt":
                                # G2（融合设计 §4.3）：自纠错计数闸门实时可见（attempt/limit/stopped）
                                _emit_ev = "correction"
                                _payload = {
                                    "kind": "correction.attempt",
                                    "tool_call_id": _cdata.get("tool_call_id", ""),
                                    "tool_name": _cdata.get("tool_name", ""),
                                    "error_class": _cdata.get("error_class", ""),
                                    "attempt": _cdata.get("attempt", 0),
                                    "limit": _cdata.get("limit", 2),
                                    "stopped": _cdata.get("stopped", False),
                                    "reason": _cdata.get("reason", ""),
                                    "contract": _cc,
                                }
                            else:
                                _emit_ev = "template"
                                _payload = {
                                    "kind": _cname,
                                    "detail": _cdata.get("detail", "") or _cdata.get("reason", ""),
                                }
                            yield f"event: {_emit_ev}\n"
                            yield f"data: {json.dumps(_payload, ensure_ascii=False, default=str)}\n\n"
                            if _evt_sink is not None:
                                _evt_sink.append(_cname, {k: v for k, v in _payload.items() if k != "contract"})
                        elif isinstance(_cdata, dict) and _cdata.get("type") == "think_token":
                            # 兼容旧版自定义事件（llm_client 内 reasoning 推送）
                            yield f"event: think_token\n"
                            yield f"data: {json.dumps({'task': _cdata.get('task', '推理'), 'kind': 'decision', 'token': _cdata.get('token', '')}, ensure_ascii=False)}\n\n"
                        continue

                    # model/tools 节点的 on_chain_start/end 不再推送状态事件：
                    # DecisionGate 拒绝时 model 会空转重试（model执行中->model完成 但无 step 产出），
                    # 推送这些状态会让前端看到无意义的"空转"。进度改为只靠 skill step 事件 + decision 事件展示。
                    # if etype == "on_chain_start" and name in ("model", "tools"):
                    #     yield f"event: status\n"
                    #     yield f"data: {json.dumps({'node': name, 'phase': 'running', 'text': f'{name}执行中'}, ensure_ascii=False)}\n\n"
                    # elif etype == "on_chain_end" and name in ("model", "tools"):
                    #     yield f"event: status\n"
                    #     yield f"data: {json.dumps({'node': name, 'phase': 'done', 'text': f'{name}完成'}, ensure_ascii=False)}\n\n"

            consume_error: Optional[Exception] = None
            try:
                async for sse_chunk in _consume_events():
                    yield sse_chunk
            except Exception as e:
                import traceback as _tb
                _tb_str = _tb.format_exc()
                logger.warning(f"[FreePlan] astream_events 消费异常: {e}\n{_tb_str}")
                consume_error = e
                # aiosqlite 连接断开后线程不能重启(RuntimeError: threads can only be started once)
                # -> 重置 agent 单例，下次请求自动用新连接重建
                if "threads can only be started once" in str(e):
                    try:
                        from app.services.tupu_deepagent import reset_tupu_agent
                        await reset_tupu_agent()
                        logger.info("[FreePlan] 检测到 aiosqlite 连接断开，已重置 agent 单例")
                    except Exception as _re:
                        logger.warning(f"[FreePlan] 重置 agent 失败: {_re}")
            finally:
                # v3.6 推送分段计时（定位首响应延迟来源）
                _timing["total"] = round((_time.time() - _t0) * 1000)
                try:
                    yield f"event: timing\n"
                    yield f"data: {json.dumps(_timing, ensure_ascii=False)}\n\n"
                except Exception:
                    pass
                # 客户端断开(abort)时 GeneratorExit 在 yield sse_chunk 抛出(不被 except Exception 捕获),
                # 走到这里 aclose 关闭底层 LangGraph agent 迭代器, 取消后续 LLM/MCP/SQL 调用, 不再烧 token。
                # 正常结束时 aiter 已耗尽, aclose 是 no-op, 安全。
                try:
                    await aiter.aclose()
                except Exception:
                    pass
                # v3.5: 释放会话执行锁
                if _session_lock.locked():
                    _session_lock.release()

            # 消费异常时：已推送的中间步骤可能不全，直接发 error 事件终止，避免发空 done 让前端误以为成功
            if consume_error is not None:
                err_msg = str(consume_error) or repr(consume_error) or "DeepAgent 执行异常（LLM 调用失败或超时）"
                if _evt_sink is not None:
                    _evt_sink.fail(err_msg)
                yield f"event: error\n"
                yield f"data: {json.dumps({'error': err_msg}, ensure_ascii=False)}\n\n"
                return

            # final：优先从 state 取最后一条 AIMessage（最终回复），避免推中间步骤汇报
            final_answer = ""
            try:
                final_state = await _asyncio.wait_for(agent.aget_state(config), timeout=10)
                msgs = final_state.values.get("messages", []) if final_state.values else []
                for msg in reversed(msgs):
                    if msg.__class__.__name__ == "AIMessage" and not getattr(msg, "tool_calls", None):
                        c = msg.content if isinstance(msg.content, str) else str(msg.content)
                        if c and c.strip():
                            final_answer = c
                            break
            except Exception:
                pass
            # state 无最终回复时，用 on_chat_model_end 捕获的 ai_reply
            if not final_answer:
                final_answer = tool_results.get("ai_reply", "")

            # F5: 尝试从 state 取结构化最终答案（FinalDelivery，response_format 生效时）
            _structured = None
            try:
                _fs = await _asyncio.wait_for(agent.aget_state(config), timeout=5)
                _sv = _fs.values if _fs.values else {}
                _structured = _sv.get("structured_response") if isinstance(_sv, dict) else None
            except Exception:
                pass

            # 统一最终交付构建（A-E 确定性降级）。
            # 替换旧的"二次 LLM 四段式总结"兜底：不再根据 rows[:3] 让模型总结全量结果，
            # 不再生成"定位实体"等内部过程内容作为业务答案；无模型最终文本时用纯 Python 确定性交付。
            _delivery_result = _build_final_delivery(
                user_input=req.user_input,
                final_answer=final_answer,
                structured=_structured,
                sql_result=tool_results.get("sql_result"),
                sql_error=tool_results.get("sql_error", ""),
                sql_executed=tool_results.get("sql_executed", False),
                l2_name=tool_results.get("l2_name", ""),
                entity_name=tool_results.get("entity_name", ""),
            )
            final_answer = _delivery_result["final_answer"]
            final_delivery = _delivery_result["final_delivery"]
            _structured_degraded = _delivery_result["degraded"]  # true=GLM 未产出结构化，用文本/确定性交付
            if _structured_degraded and final_answer:
                logger.info("[FreePlan] response_format 降级：GLM 未产出结构化结果，使用文本/确定性交付")

            # 输出契约（设计 §8/§10）：完整数据已推前端查询结果表时，最终回答不得再输出
            # Markdown 明细表（SKILL.md 输出格式硬规则第2条）——确定性清洗 + 记录
            _output_scrubbed = False
            _output_check_reason = ""
            _sr_for_check = tool_results.get("sql_result")
            _has_ui_result = bool(_sr_for_check and isinstance(_sr_for_check, dict) and not _sr_for_check.get("error"))
            if _has_ui_result and final_answer:
                try:
                    from app.services.output_contract import validate_final_output, scrub_markdown_tables
                    # 输出契约旗标来自受控契约（skill 声明 forbid_markdown_detail_table）：
                    # 分布过载(true)剥离答案表格；跨源汇总类技能(false)保留答案呈现的表
                    _forbid_md = True
                    if _contract is not None:
                        _forbid_md = bool(_contract.forbid_markdown_detail_table)
                    _oc = validate_final_output(
                        final_answer, result_available_for_ui=True,
                        row_count=(_sr_for_check or {}).get("row_count"),
                        forbid_markdown_detail_table=_forbid_md,
                    )
                    _output_check_reason = _oc.reason
                    if not _oc.ok:
                        _scrubbed = scrub_markdown_tables(final_answer)
                        if _scrubbed != final_answer:
                            final_answer = _scrubbed
                            _output_scrubbed = True
                        logger.info(f"[OutputContract] 已清洗最终回答 Markdown 明细表: {_oc.reason}")
                        # 批4 治理：记录输出契约清洗审计
                        try:
                            from app.services.skill_governance import EVENT_OUTPUT_SCRUBBED, get_governance
                            get_governance().record_output(EVENT_OUTPUT_SCRUBBED, _oc.reason or "markdown_detail_table")
                        except Exception:
                            pass
                except Exception as _oce:
                    logger.warning(f"[OutputContract] 输出校验异常: {_oce}")

            if final_answer and final_answer.strip():
                import time as _t2
                final_sent_at[0] = _t2.time()
                yield f"event: final\n"
                yield f"data: {json.dumps({'answer': final_answer}, ensure_ascii=False)}\n\n"

            # 推送推荐问题（优先 final_delivery.recommendations，其次从 final_answer 提取，再默认兜底）
            recs = final_delivery.get("recommendations") or _extract_recommendations(final_answer)
            if not recs:
                recs = ["统计用电客户总数", "查客户的联系电话", "什么是变压器"]
            yield f"event: recommend\n"
            yield f"data: {json.dumps({'questions': [{'label': r, 'shortcut': r} for r in recs]}, ensure_ascii=False)}\n\n"

            # 构建 confirmed
            confirmed = {
                "L2": tool_results.get("l2_name", ""),
                "L2_id": tool_results.get("l2_id", ""),
                "L2X": tool_results.get("entity_code", ""),
                "L2X_name": tool_results.get("entity_name", ""),
                "attributes": tool_results.get("attributes", []),
                "assembled_sql": tool_results.get("assembled_sql", ""),
            }

            # SQL 执行结果（供前端渲染数据表格；附带完整性契约字段，前端不把预览当不完整）
            sql_result_data = None
            _sr = tool_results.get("sql_result")
            if _sr and isinstance(_sr, dict) and not _sr.get("error"):
                _rows = _sr.get("rows", [])
                _rc = _sr.get("row_count", 0) or len(_rows)
                sql_result_data = {
                    "columns": _sr.get("columns", []),
                    "rows": _rows,
                    "row_count": _rc,
                    "sql": tool_results.get("assembled_sql", ""),
                    "returned_rows": len(_rows),
                    "preview_row_count": min(10, _rc),
                    "is_preview": False,                    # 前端拿完整数据，一律 false
                    "llm_is_preview": _rc > 10,             # 模型是否只看前 10 行分析样本
                    "llm_preview_row_count": min(10, _rc),  # 模型样本行数
                    "result_available_for_ui": True,
                }

            # 推送 done
            final_response = {
                "thread_id": req.thread_id,
                "current_task": "DeepAgent",
                "goal": "free_plan",
                "routed_skill": "free_plan",
                "pending_clarification": None,
                "confirmed": confirmed,
                "completed_tasks": [t["task"] for t in think_stream],
                "flags": {
                    "chain_locked": bool(confirmed.get("L2")),
                    "entity_locked": bool(confirmed.get("L2X")),
                    "sql_executed": tool_results.get("sql_executed", False),
                    "output_scrubbed": _output_scrubbed,
                },
                "route": (_route.to_dict() if _route is not None else None),  # 受控路由结果（前端 RouteCard）
                "contract": _contract.to_dict() if _contract is not None else None,  # 受控契约（前端五卡）
                "output_contract_check": {"ok": not _output_scrubbed, "reason": _output_check_reason},
                "think_stream": think_stream,
                "final_answer": final_answer,
                "final_answer_structured": _structured,  # F5: 结构化输出（GLM 不兼容时为 None，降级手动）
                "response_format_degraded": _structured_degraded,  # F5: 降级标识（true=GLM 未产出结构化，用文本答案）
                "final_delivery": final_delivery,  # 统一最终交付协议（标题/摘要/发现/告警/推荐/row_count）
                "sql_result": sql_result_data,  # P1-4: 清理后的数据（排除 error 结果），删除重复键
                "recommendations": [{"label": r, "shortcut": r} for r in recs],
                "next_step_recommendation": None,
                "message_card": None,
            }
            yield f"event: done\n"
            yield f"data: {json.dumps(final_response, ensure_ascii=False, default=str)}\n\n"
            _evt_sink.complete({"final_answer": (final_answer or "")[:500], "completed_tasks": final_response.get("completed_tasks", []), "sql_executed": final_response.get("flags", {}).get("sql_executed", False)})

        except Exception as e:
            import traceback as _tb
            logger.error(f"[FreePlan] event_iter 异常: {e}\n{_tb.format_exc()}")
            if _evt_sink is not None:
                _evt_sink.fail(str(e) or repr(e) or "event_iter 异常")
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            # 客户端断开(abort)或异常时, 关闭 LangGraph 事件迭代器, 取消底层 agent task
            # (停止后续 LLM/MCP/SQL 调用, 不再烧 token; GeneratorExit 也会经此清理)
            if _evt_sink is not None:
                _evt_sink.close()
            if aiter is not None:
                try:
                    await aiter.aclose()
                except Exception:
                    pass
            # v3.5: 释放会话执行锁（兜底：inner finally 可能因 early-exception 未到达）
            if _session_lock is not None and _session_lock.locked():
                _session_lock.release()

    return StreamingResponse(event_iter(), media_type="text/event-stream")
