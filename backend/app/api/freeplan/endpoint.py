# -*- coding: utf-8 -*-
"""freeplan/endpoint.py - freeplan 流端点（批13-D Step3：从 data_intelligence_stream 迁入）

- chat_freeplan_stream：POST /chat/freeplan/stream 主编排器（函数体字节原样迁入，行为零变化）
- resume_hitl：S5（HITL v2）人审恢复端点
- 路由仍由 data_intelligence_stream.py 挂载（URL 不变，SSE 序列字节一致）
"""
from __future__ import annotations

import json
import logging
import os
from typing import Optional

from fastapi import Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel as _PydanticBaseModel

from ..data_intelligence import ChatRequest
from ..data_intelligence_support import (
    _KG_ACTION_LABELS, _get_session_lock, _extract_customer_names_from_input,
    _build_final_delivery, _build_action_detail,
    _build_result_summary, _build_nonjson_result_summary,
)
from .sse import sse_frames
from .delivery import (
    extract_final_answer_from_state, apply_output_contract, build_sql_result_payload,
    build_confirmed, build_evidence, build_recommendations, build_done_payload,
)

logger = logging.getLogger(__name__)


def chat_freeplan_stream(req: ChatRequest, request: Request):
    """数据资产探查（ReAct 流式对话）。

    - ReAct 模式（create_deep_agent），边规划边思考
    - 全量加载 10 个任务级 SKILL.md 到虚拟文件系统
    - astream_events v2 推送
    """
    async def event_iter():
        try:
            # 批13-N2：首个可见反馈提到编排第一行——此前首个 yield 排在全部准备之后
            # （三次重复 aget_state + 可能 8s 改写 + 同步检索），浏览器首字节前零反馈
            # （《首响应延迟解剖》W3）。status 先发，用户即时看到「小探正在运行中」。
            yield f"event: status\n"
            yield f"data: {json.dumps({'node': 'DeepAgent', 'phase': 'running', 'text': '小探正在运行中', 'routed_skill': 'free_plan'}, ensure_ascii=False)}\n\n"

            # 批13-N 配套：prep 细分计时（lock/state/rewrite/route/retrieval/update 各段 ms 入日志，
            # 与 v3.6 分段计时埋点互补；修完有数可证）
            import time as _time
            _t0 = _time.time()
            _prep_timing: dict = {}

            aiter = None  # LangGraph 事件迭代器, finally 中 aclose 以响应客户端取消
            _evt_sink = None  # v3.1 关键事件持久化 sink; 提前置 None 防 early-exception 时 except/finally 引用未绑定变量
            _session_lock = None  # v3.5 会话执行锁, finally 中释放
            import asyncio as _asyncio
            from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

            # P1-1: 删除旧技能枚举+files注入（CompositeBackend+skills=["/skills/"] 已接管技能加载）
            # Agent 通过 FilesystemBackend 自主 read_file /skills/*/SKILL.md，无需每次请求手动注入

            # v3.5: 改用全局 Agent 单例（持久化 AsyncSqliteSaver，同 thread_id 跨请求恢复记忆）
            # 不再每请求新建 MemorySaver（旧实现无跨轮记忆）
            # 专家地基①（spec §五/§十）：入口拦截先于装配——未知专家/已关停在装配前拒绝（SSE error）。
            from app.services import expert_config as _expert_cfg
            try:
                _expert_cfg.get_card(req.expert_id)
            except KeyError:
                raise RuntimeError(f"未知专家: {req.expert_id}")
            _expert_card = _expert_cfg.get_card(req.expert_id)
            if not _expert_card.get("enabled", False):
                raise RuntimeError(f"专家已关停: {req.expert_id}")
            from app.services.tupu_deepagent import get_tupu_agent
            agent = await get_tupu_agent(connection_id=req.llm_connection_id or "", expert_id=req.expert_id)

            # v3.6: checkpoint 按真实用户隔离（评审 P0：固定 anonymous 前缀导致跨用户串记忆）
            # 鉴权关闭时 user.sub="anonymous"；启用后用真实 OIDC sub，实现用户级隔离
            from app.core.auth import get_current_user
            _current_user = get_current_user(request)
            _user_prefix = _current_user.sub if _current_user and _current_user.sub else "anonymous"
            # 专家地基①（spec §八）：三段键单点收口——{user}:{expert}:{thread}（expert_paths 唯一构造处）
            from app.services.expert_paths import thread_id as _expert_thread_id
            _memory_thread_id = _expert_thread_id(_user_prefix, req.expert_id, req.thread_id)

            # v3.5: 同一会话执行锁 -- 防止同 thread_id 并发请求导致 checkpoint 分叉覆盖
            _session_lock = _get_session_lock(_memory_thread_id)
            _t_lock = _time.time()
            await _session_lock.acquire()
            _prep_timing["lock_ms"] = round((_time.time() - _t_lock) * 1000)

            # ===== 批13-D Step2：prep 段提取（freeplan.prep.run_prep，行为零变化）=====
            from .prep import run_prep
            _prep = await run_prep(
                req=req, agent=agent, memory_thread_id=_memory_thread_id, prep_timing=_prep_timing)
            # 局部别名保持后续段变量名不变（后续引用零改动）
            config = _prep.config
            # 批14-B 通道②（设计 §2.2）：请求期 config 级 callbacks 挂缓存观测采集器——
            # langgraph 标准传播（config callbacks 到达图内 chat model run 的 on_llm_end），
            # 零装配耦合（不动 Agent 单例），回滚=关 env TUPU_LLM_CACHE_OBS。
            try:
                if os.getenv("TUPU_LLM_CACHE_OBS") == "1":
                    from app.services.llm_client import _CACHE_COLLECTOR as _cc14b
                    _cbs = config.setdefault("callbacks", [])
                    if _cc14b not in _cbs:
                        _cbs.append(_cc14b)
            except Exception as _cache_obs_e:
                logger.warning(f"[14-B] 缓存观测挂载失败（不影响主链路）: {_cache_obs_e}")
            _route = _prep.route
            _contract = _prep.contract
            _effective_question = _prep.effective_question
            input_messages = _prep.input_messages
            _ctx = _prep.ctx
            _followup_rewritten = _prep.followup_rewritten

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
            # 批13-AB4：_data_result_sids 防覆盖集已删（DataSummaryMiddleware 退役，sql_result 统一 on_tool_end 派发）
            # v3.1 步骤5: 关键事件持久化(flag-gated+容错); _consume_events 内 append, final/except 里 complete/fail, finally 里 close
            from app.services.run_event_sink import RunEventSink
            _evt_sink = RunEventSink(req.user_input, expert_id=req.expert_id)  # 专家地基①：观测带专家维度

            # v3.6 分段计时埋点：流式段五段计时（_t0 已在批13-N2 提前到生成器第一行，
            # 使 total/first_event 覆盖 prep 段）
            _timing = {"first_event": None, "first_model_stream": None,
                       "first_tool_start": None, "first_decision": None,
                       "first_answer_token": None, "total": None}
            def _mark(key):
                if _timing[key] is None:
                    _timing[key] = round((_time.time() - _t0) * 1000)

            # 批13-N 配套：prep 细分计时入结构化日志（lock/state/rewrite/route/retrieval/update）
            try:
                logger.info(f"[PrepTiming] {json.dumps(_prep_timing, ensure_ascii=False)} total_prep_ms={round((_time.time() - _t0) * 1000)}")
            except Exception:
                pass

            # S3b（G9）：追问改写透明性 —— 前端最终答案上方渲染「理解为：xxx」（可点击展开原文对照）
            if _followup_rewritten and _effective_question == _followup_rewritten:
                yield f"event: followup.rewrite\n"
                yield f"data: {json.dumps({'original': req.user_input, 'rewritten': _followup_rewritten}, ensure_ascii=False)}\n\n"

            # 受控路由/契约事件（前端据此渲染 RouteCard/ScopeCard/DataAccessCard/ExecutionDecisionCard）
            if _contract is not None:
                yield f"event: route\n"
                yield f"data: {json.dumps((_route.to_dict() if _route is not None else {'route_type': 'fallback', 'contract': _contract.to_dict()}), ensure_ascii=False)}\n\n"
                yield f"event: contract\n"
                yield f"data: {json.dumps(_contract.to_dict(), ensure_ascii=False)}\n\n"
                # S2（金标扩容）：歧义提问 -> 路由层标记澄清，SSE 透出澄清事件（eval 澄清口径判定依据）
                if getattr(_contract, "clarify_required", False):
                    yield f"event: route.clarification\n"
                    yield f"data: {json.dumps({'node': '澄清', 'clarify_required': True, 'question': req.user_input}, ensure_ascii=False)}\n\n"

            # 复用 ReAct 路径的事件消费逻辑
            # F4: 通过原生 context= 传递 runtime.context（astream_events 的 **kwargs 会透传给底层）
            # M3 DA-2：generic 契约带 rubric -> 激活 RubricMiddleware（scenario 为 None 不传，保持不激活）
            _inv_state: dict = {"messages": input_messages}
            if _contract is not None and _contract.rubric:
                _inv_state["rubric"] = _contract.rubric
            # M3：on_evaluation 回调 -> 当前请求 sink/契约（contextvar 同任务上下文可见）
            from app.services.tupu_deepagent import _RUBRIC_HOOK_CTX
            _rubric_hook_token = _RUBRIC_HOOK_CTX.set({"sink": _evt_sink, "contract": _contract})

            # ===== 批9 模板直出管道 v1：路由后 Agent 前判定（问五）=====
            # sim≥0.95 且 count 类且无动态条件 -> 绕过 Agent 直接执行验证 SQL（0 LLM 轮，目标 2~4s）；
            # 执行报错自动回退完整 Agent 路径（用户无感，只是变慢）；与批2-C 首选计划分层共存。
            # 批16-A：外门与 evaluate_direct_eligibility 内门同步放开 scenario（实施发现第二道门：
            # plan 原记「一处条件」漏计此处——e2e 暴露，COUNT 场景题曾仍走 Agent 工作流）。
            if _contract is not None and getattr(_route, "route_type", "") in ("generic", "scenario"):
                _dp_plan = None
                try:
                    from app.services.direct_pipeline import evaluate_direct_eligibility
                    _dp_plan = evaluate_direct_eligibility(_contract, _effective_question)
                except Exception as _dpe:
                    logger.warning(f"[DirectPipeline] 直通判定异常（走Agent）: {_dpe}")
                if _dp_plan is not None:
                    _mark("first_tool_start")
                    _dp = None
                    try:
                        import asyncio as _dp_asyncio
                        from app.services.direct_pipeline import run_direct_pipeline
                        _dp = await _dp_asyncio.to_thread(
                            run_direct_pipeline, _dp_plan, _effective_question, str(req.thread_id or ""))
                    except Exception as _dre:
                        logger.warning(f"[DirectPipeline] 直通执行失败，回退 Agent: {_dre}")
                        try:
                            from app.services.skill_governance import get_governance
                            get_governance().record_policy(
                                "direct_pipeline.fallback", "_direct_", "_direct_", str(_dre)[:300])
                        except Exception:
                            pass
                    if _dp is not None:
                        # ---- SSE 直出（事件序列与 Agent 路径一致，前端零改动）----
                        _dp_res = _dp["result"]
                        _dp_rows = _dp_res.get("rows") or []
                        _dp_rc = int(_dp_res.get("row_count") or len(_dp_rows) or 0)
                        _dp_cols = _dp_res.get("columns") or []
                        _dp_sql = str(_dp_res.get("sql") or _dp_plan["sql"])
                        _dp_answer = str(_dp["answer"] or "")
                        _dp_summary = (f"命中已验证示例（相似度 {_dp_plan['score']:.2f}），"
                                       f"直接执行验证 SQL：返回 {_dp_rc} 行")
                        yield f"event: think\n"
                        yield f"data: {json.dumps({'task': '模板直出执行', 'kind': 'skill', 'step_id': 1, 'tool_call_id': '', 'duration_ms': _dp['duration_ms'], 'result_summary': _dp_summary, 'result_status': 'locked', 'phase': 'done'}, ensure_ascii=False)}\n\n"
                        try:
                            _evt_sink.append("tool.completed", {"task": "模板直出执行", "tool_name": _dp["tool"], "result_summary": _dp_summary, "result_status": "locked", "duration_ms": _dp["duration_ms"]}, step_id="1")
                        except Exception:
                            pass
                        _mark("first_answer_token")
                        yield f"event: sql_result\n"
                        yield f"data: {json.dumps({'columns': _dp_cols, 'rows': _dp_rows, 'row_count': _dp_rc, 'sql': _dp_sql, 'returned_rows': len(_dp_rows), 'preview_row_count': min(10, _dp_rc), 'is_preview': False, 'llm_is_preview': _dp_rc > 10, 'llm_preview_row_count': min(10, _dp_rc), 'result_available_for_ui': True, 'step_id': 1, 'data_snapshot_at': _dp_res.get('data_snapshot_at'), 'cache_sources': _dp_res.get('cache_sources')}, ensure_ascii=False, default=str)}\n\n"
                        if _dp_answer.strip():
                            import time as _dp_t
                            final_sent_at[0] = _dp_t.time()
                            yield f"event: final\n"
                            yield f"data: {json.dumps({'answer': _dp_answer}, ensure_ascii=False)}\n\n"
                        _dp_recs = ["统计用电客户总数", "查客户的联系电话", "什么是变压器"]
                        yield f"event: recommend\n"
                        yield f"data: {json.dumps({'questions': [{'label': r, 'shortcut': r} for r in _dp_recs]}, ensure_ascii=False)}\n\n"
                        # 会话历史写回 checkpoint（直通未走 agent 消息循环，保追问上下文连续性）
                        try:
                            from langchain_core.messages import AIMessage as _dp_AIM
                            await agent.aupdate_state(config, {"messages": [
                                HumanMessage(content=_effective_question), _dp_AIM(content=_dp_answer)]})
                        except Exception as _upe:
                            logger.warning(f"[DirectPipeline] 会话历史写回失败（忽略）: {_upe}")
                        _dp_think = [{"task": "模板直出执行", "kind": "skill", "step_id": 1,
                                      "phase": "done", "result_status": "locked",
                                      "result_summary": _dp_summary, "duration_ms": _dp["duration_ms"]}]
                        _dp_tables = []
                        try:
                            from app.services.kg_action_handlers import _extract_main_table as _dp_emt
                            _t_dp = _dp_emt(_dp_sql)
                            if _t_dp:
                                _dp_tables = [_t_dp]
                        except Exception:
                            pass
                        _dp_evidence = {
                            "route": {"skill": "__generic__", "route_type": "generic"},
                            "tables": _dp_tables,
                            "examples_used": [{"q": _dp_plan["hit"].get("question_raw") or "", "sim": _dp_plan["score"]}],
                            "verification": _dp_res.get("verification") or {},
                            "rubric": {"status": None, "iterations": 0},
                            "corrections": 0,
                            "missing_data_support": False,
                            "direct_pipeline": True,  # 批9：确定性来源标识
                        }
                        try:
                            from app.services.skill_governance import get_governance as _dp_gov
                            _dp_gov().record_policy(
                                "direct_pipeline.executed", "_direct_", "_direct_",
                                f"sim={_dp_plan['score']:.2f} rows={_dp_rc} engine={_dp_plan['engine']}")
                        except Exception:
                            pass
                        _timing["total"] = round((_time.time() - _t0) * 1000)
                        _timing["rubric_ms"] = 0  # 直通无 grader
                        _dp_response = {
                            "thread_id": req.thread_id,
                            "current_task": "DeepAgent",
                            "goal": "free_plan",
                            "routed_skill": "free_plan",
                            "pending_clarification": None,
                            "confirmed": {"assembled_sql": _dp_sql},
                            "completed_tasks": ["模板直出执行"],
                            "flags": {"chain_locked": False, "entity_locked": False,
                                      "sql_executed": True, "output_scrubbed": False,
                                      "direct_pipeline": True},
                            "route": (_route.to_dict() if _route is not None else None),
                            "contract": _contract.to_dict() if _contract is not None else None,
                            "output_contract_check": {"ok": True, "reason": ""},
                            "think_stream": _dp_think,
                            "final_answer": _dp_answer,
                            "final_answer_structured": None,
                            "response_format_degraded": False,
                            "final_delivery": None,
                            "sql_result": {
                                "columns": _dp_cols, "rows": _dp_rows, "row_count": _dp_rc,
                                "sql": _dp_sql, "returned_rows": len(_dp_rows),
                                "preview_row_count": min(10, _dp_rc), "is_preview": False,
                                "llm_is_preview": _dp_rc > 10, "llm_preview_row_count": min(10, _dp_rc),
                                "result_available_for_ui": True,
                            },
                            "recommendations": [{"label": r, "shortcut": r} for r in _dp_recs],
                            "next_step_recommendation": None,
                            "message_card": None,
                            "evidence": _dp_evidence,
                            "confidence": "高",  # 确定性来源（验证 SQL 单源 + 安全校验通过）
                            "timing": dict(_timing),
                        }
                        yield f"event: done\n"
                        yield f"data: {json.dumps(_dp_response, ensure_ascii=False, default=str)}\n\n"
                        try:
                            yield f"event: timing\n"
                            yield f"data: {json.dumps(_timing, ensure_ascii=False)}\n\n"
                        except Exception:
                            pass
                        _evt_sink.complete({"final_answer": _dp_answer[:500], "completed_tasks": ["模板直出执行"], "sql_executed": True})
                        logger.info(f"[DirectPipeline] 直通完成: sim={_dp_plan['score']:.2f} rows={_dp_rc} total={_timing['total']}ms")
                        return

            aiter = agent.astream_events(
                _inv_state,
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
                        # deepagents 工具循环的"任务笔记"固定标题（模型每次调工具前输出，内部产物，不应作为回答上屏）
                        _TOOL_NOTE_MARKERS = ("## SESSION INTENT", "## SUMMARY", "## ARTIFACTS", "## NEXT STEPS")
                        if _rs["classifier"] == "detecting":
                            _stripped = _rs["accumulated"].lstrip()
                            if _marker.startswith(_stripped) and len(_stripped) < len(_marker):
                                continue  # 仍是标记前缀，等待更多 token
                            # 任务笔记标题前缀等待（如 "## S"、"## SE"）：前缀阶段不完整，
                            # 不满足 startswith 完整标记，会落入 else 误判为 answer —— 须等待更多 token 再定
                            if any(m.startswith(_stripped) and len(_stripped) < len(m) for m in _TOOL_NOTE_MARKERS):
                                continue
                            if _stripped.startswith(_marker):
                                _rs["classifier"] = "decision"
                                # 首次冲刷：推完整累积内容（不丢前面的标记和文字）
                                yield f"event: think_token\n"
                                yield f"data: {json.dumps({'kind': 'decision_draft', 'round_id': _rid, 'delta': _rs['accumulated']}, ensure_ascii=False)}\n\n"
                                continue
                            elif any(_stripped.startswith(m) for m in _TOOL_NOTE_MARKERS):
                                # 工具任务笔记（SESSION INTENT 等）：内部中间产物，丢弃不推 answer_draft，
                                # 避免污染前端"答案生成"流（用户要求内部工作流文本不上屏）
                                _rs["classifier"] = "notes"
                                continue
                            else:
                                _rs["classifier"] = "answer"
                                _mark("first_answer_token")
                                yield f"event: think_token\n"
                                yield f"data: {json.dumps({'kind': 'answer_draft', 'round_id': _rid, 'delta': _rs['accumulated']}, ensure_ascii=False)}\n\n"
                                continue
                        # 已识别，只推增量（notes 类不推任何 think_token）
                        if _rs["classifier"] == "notes":
                            continue
                        _kind = "decision_draft" if _rs["classifier"] == "decision" else "answer_draft"
                        yield f"event: think_token\n"
                        yield f"data: {json.dumps({'kind': _kind, 'round_id': _rid, 'delta': content}, ensure_ascii=False)}\n\n"
                        continue

                    if etype == "on_chat_model_end":
                        out = data.get("output")
                        _rid = ev.get("run_id", "")
                        # 批13-I C4 缓存观测改走 llm_client callback（on_llm_end LLMResult 完整
                        # usage）——事件流的 out 对象 usage 细节被裁剪（itd=None/tu={} 实测），
                        # 此处不再探测（2026-09-04 三落点实测后定案）。
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
                                    # 批13-AB4：DataSummaryMiddleware 退役 -> sql_result 统一在此派发。
                                    # parsed 带 result_ref（工具端 _with_result_ref 已全量存 query_result_store）：
                                    # 取全量派发（is_preview=false 完整数据，字段与原 data_result 帧逐字段一致）；
                                    # 未命中（TTL 过期/极端内存淘汰）降级发模型侧截断版保底（前端少行数但不空窗）；
                                    # 无 result_ref（非 AB4 工具/异常路径）按原兜底发 parsed 本身。
                                    _ref = parsed.get("result_ref") if isinstance(parsed, dict) else None
                                    if _ref:
                                        from app.services import query_result_store as _qrs
                                        _full = _qrs.get(_ref)
                                        if _full is not None:
                                            _payload = {"columns": _full.get("columns", []), "rows": _full.get("rows", []),
                                                        "columns_cn": _full.get("columns_cn") or [],  # 表头中英双显（2026-09-12）
                                                        "row_count": _full.get("row_count", 0), "sql": _full.get("sql", ""),
                                                        "returned_rows": len(_full.get("rows", [])),
                                                        "preview_row_count": min(10, _full.get("row_count", 0)),
                                                        "is_preview": False,
                                                        "llm_is_preview": bool(parsed.get("llm_is_preview")),
                                                        "llm_preview_row_count": parsed.get("llm_preview_row_count", 10),
                                                        "result_available_for_ui": True,
                                                        "step_id": _sid, "tool_name": name,
                                                        "data_snapshot_at": _full.get("data_snapshot_at"),
                                                        "cache_sources": _full.get("cache_sources")}
                                            yield f"event: sql_result\n"
                                            yield f"data: {json.dumps(_payload, ensure_ascii=False, default=str)}\n\n"
                                        else:
                                            logger.warning(f"[SSE] result_ref 未命中降级截断版: tool={name} ref={str(_ref)[:8]} sid={_sid}")
                                            yield f"event: sql_result\n"
                                            yield f"data: {json.dumps({'columns': parsed.get('columns', []), 'rows': parsed.get('rows', []), 'columns_cn': parsed.get('columns_cn') or [], 'row_count': parsed.get('row_count', 0), 'sql': parsed.get('sql', ''), 'returned_rows': len(parsed.get('rows', [])), 'is_preview': False, 'llm_is_preview': True, 'llm_preview_row_count': parsed.get('llm_preview_row_count', 10), 'result_available_for_ui': True, 'step_id': _sid, 'tool_name': name, 'data_snapshot_at': parsed.get('data_snapshot_at'), 'cache_sources': parsed.get('cache_sources')}, ensure_ascii=False, default=str)}\n\n"
                                    else:
                                        yield f"event: sql_result\n"
                                        yield f"data: {json.dumps({'columns': parsed.get('columns', []), 'rows': parsed.get('rows', []), 'columns_cn': parsed.get('columns_cn') or [], 'row_count': parsed.get('row_count', 0), 'sql': parsed.get('sql', ''), 'step_id': _sid, 'step_no': _sid, 'returned_rows': len(parsed.get('rows', [])), 'is_preview': False, 'llm_is_preview': parsed.get('_truncated', False), 'llm_preview_row_count': parsed.get('llm_preview_row_count', parsed.get('preview_row_count', 0)), 'result_available_for_ui': True, 'data_snapshot_at': parsed.get('data_snapshot_at'), 'cache_sources': parsed.get('cache_sources')}, ensure_ascii=False, default=str)}\n\n"
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
                        # 批13-AB4：data_result 自定义事件分支已删——DataSummaryMiddleware 退役后
                        # 无人派发 data_result；sql_result 统一由 on_tool_end 按 result_ref 派发。
                        elif _cname in ("engine.selected", "stop.reached", "policy.rejected",
                                       "template.bound", "template.drift", "correction.attempt",
                                       "policy.interrupt"):
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
                            elif _cname == "policy.interrupt":
                                # S5（HITL v2）：人审请求实时透出（interrupt_id/reason/proposal）——
                                # 前端据此渲染「批准/拒绝」横条，批准/拒绝后调 resume 端点恢复同 thread。
                                _emit_ev = "policy"
                                _payload = {
                                    "kind": "policy.interrupt",
                                    "interrupt_id": _cdata.get("interrupt_id", ""),
                                    "tool_name": _cdata.get("tool_name", ""),
                                    "error_class": _cdata.get("error_class", ""),
                                    "reason": _cdata.get("reason", ""),
                                    "proposal": _cdata.get("proposal", ""),
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
                # 批3-F：自评段耗时（粗粒度）——首答案 token 到 done 的段落，主要为 rubric grader 调用；
                # 未激活 rubric（示例锚定直通）时该段≈收尾开销。
                _t_first_ans = _timing.get("first_answer_token") or 0
                _timing["rubric_ms"] = max(0, _timing["total"] - _t_first_ans) if _t_first_ans else 0
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
                for _f in sse_frames("error", {"error": err_msg}):
                    yield _f
                return

            # final：优先从 state 取最后一条 AIMessage（最终回复），避免推中间步骤汇报（批13-D 提取）
            # 批13-N3 收尾合并：final 答案 + F5 结构化响应共用一次 aget_state（原两次独立读）
            final_answer = ""
            _structured = None
            try:
                final_state = await _asyncio.wait_for(agent.aget_state(config), timeout=10)
                _sv = final_state.values if final_state.values else {}
                msgs = _sv.get("messages", []) if isinstance(_sv, dict) else []
                final_answer = extract_final_answer_from_state(msgs)
                _structured = _sv.get("structured_response") if isinstance(_sv, dict) else None
            except Exception:
                pass
            # state 无最终回复时，用 on_chat_model_end 捕获的 ai_reply
            if not final_answer:
                final_answer = tool_results.get("ai_reply", "")

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
            # Markdown 明细表（SKILL.md 输出格式硬规则第2条）——确定性清洗 + 记录（批13-D 提取）
            _output_scrubbed = False
            _output_check_reason = ""
            _sr_for_check = tool_results.get("sql_result")
            if final_answer:
                _forbid_md = True
                if _contract is not None:
                    _forbid_md = bool(_contract.forbid_markdown_detail_table)
                _oc_res = apply_output_contract(final_answer, _sr_for_check, forbid_md=_forbid_md)
                final_answer = _oc_res["answer"]
                _output_check_reason = _oc_res["reason"]
                _output_scrubbed = _oc_res["scrubbed"]

            if final_answer and final_answer.strip():
                import time as _t2
                final_sent_at[0] = _t2.time()
                for _f in sse_frames("final", {"answer": final_answer}):
                    yield _f

            # 推送推荐问题（优先 final_delivery.recommendations，其次从 final_answer 提取，再默认兜底）
            recs = build_recommendations(final_delivery, final_answer)
            for _f in sse_frames("recommend", {"questions": [{"label": r, "shortcut": r} for r in recs]}):
                yield _f

            # 构建 confirmed + SQL 结果载荷（批13-D 提取）
            confirmed = build_confirmed(tool_results)
            sql_result_data = build_sql_result_payload(tool_results.get("sql_result"),
                                                       tool_results.get("assembled_sql", ""))

            # M3（融合设计 §5.1/§5.3）：证据链聚合 + 置信度三级（答案头部小徽标；批13-D 提取）
            _ev = build_evidence(
                _contract, tool_results, final_answer,
                (_contract._runtime.get("golden_hits") or []) if _contract is not None else None,
            )
            _evidence = _ev["evidence"]
            _ev_confidence = _ev["confidence"]
            _ev_verification = _evidence["verification"]
            _ev_rubric = _ev["rubric"]
            # SSE：query_verified（G4 验证结论） + rubric（DA-2 自评状态），均带置信度
            if _ev_verification:
                for _f in sse_frames("query_verified", {
                    "verification": _ev_verification, "confidence": _ev_confidence, "thread_id": req.thread_id,
                }):
                    yield _f
            if _ev_rubric.get("status"):
                for _f in sse_frames("rubric", {
                    "status": _ev_rubric["status"], "iterations": _ev_rubric["iterations"],
                    "feedback_summary": (_contract._runtime.get('rubric_explanation') or '') if _contract is not None else '',
                    "confidence": _ev_confidence,
                }):
                    yield _f

            # 推送 done（批13-D 提取）
            final_response = build_done_payload(
                thread_id=req.thread_id, confirmed=confirmed, think_stream=think_stream,
                tool_results=tool_results, route=_route, contract=_contract,
                final_answer=final_answer, structured=_structured,
                structured_degraded=_structured_degraded, final_delivery=final_delivery,
                sql_result_data=sql_result_data, recs=recs,
                evidence=_evidence, confidence=_ev_confidence, timing=dict(_timing),
                output_scrubbed=_output_scrubbed, output_check_reason=_output_check_reason,
            )
            for _f in sse_frames("done", final_response, default=str):
                yield _f
            _evt_sink.complete({"final_answer": (final_answer or "")[:500], "completed_tasks": final_response.get("completed_tasks", []), "sql_executed": final_response.get("flags", {}).get("sql_executed", False)})

        except Exception as e:
            import traceback as _tb
            logger.error(f"[FreePlan] event_iter 异常: {e}\n{_tb.format_exc()}")
            if _evt_sink is not None:
                _evt_sink.fail(str(e) or repr(e) or "event_iter 异常")
            for _f in sse_frames("error", {"error": str(e)}):
                yield _f
        finally:
            # 客户端断开(abort)或异常时, 关闭 LangGraph 事件迭代器, 取消底层 agent task
            # (停止后续 LLM/MCP/SQL 调用, 不再烧 token; GeneratorExit 也会经此清理)
            # M3：重置 rubric on_evaluation 桥（防跨请求串扰）
            try:
                _RUBRIC_HOOK_CTX.reset(_rubric_hook_token)
            except Exception:
                pass
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


# ---------------------------------------------------------------------------


from pydantic import BaseModel as _PydanticBaseModel


class HITLResumeRequest(_PydanticBaseModel):
    """人审恢复请求：interrupt_id（SSE policy.interrupt 事件携带）+ approve 决定。"""
    interrupt_id: str
    approve: bool
    thread_id: str = ""  # 仅日志/观测用；解析按 interrupt_id


async def resume_hitl(body: HITLResumeRequest):
    """批准/拒绝待审中断，恢复同 thread 的 agent 续跑。

    会话锁注：**不得**获取会话锁——被中断的流仍持有该锁（agent 在 policy 中断处 await），
    此处再获取即死锁（S5 验收③）。仅按 interrupt_id 解析 Future，天然幂等。
    """
    from app.services.skill_policy import resolve_hitl_interrupt
    ok = resolve_hitl_interrupt(body.interrupt_id, body.approve)
    if not ok:
        logger.info(f"[HITL] resume 未命中（可能已超时/已处理）: interrupt={body.interrupt_id} approve={body.approve} thread={body.thread_id}")
        return {"code": 404, "message": "中断不存在或已处理（可能已超时）"}
    logger.info(f"[HITL] resume 命中: interrupt={body.interrupt_id} approve={body.approve} thread={body.thread_id}")
    return {"code": 200, "data": {"interrupt_id": body.interrupt_id, "approved": body.approve}}
