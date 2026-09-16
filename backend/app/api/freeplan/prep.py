# -*- coding: utf-8 -*-
"""freeplan/prep.py - 受控 Skill 问答准备段（批13-D Step2，从 stream 单体提取，行为零变化）。

覆盖（原 data_intelligence_stream.chat_freeplan_stream 的 prep 段）：
  scope/跨轮上下文构建 -> checkpoint 一次性读取 -> 确定性路由 -> 金标后台预取 ->
  追问改写（仅 generic 路径）-> 契约注入 runtime.context + 金标收割 -> rubric 分档 ->
  input_messages 组装 -> last_skill/last_step 写回。

run_prep 为 async 顺序逻辑，产出 PrepResult 供后续（直通判定/事件消费/收尾）使用。
"""
from __future__ import annotations

import asyncio
import logging
import time
import types
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PrepResult:
    """prep 段产出（后续段消费的全部契约）。"""
    config: Dict[str, Any]
    route: Any
    contract: Any
    effective_question: str
    input_messages: List[Any]
    ctx: Dict[str, Any]
    followup_rewritten: Optional[str] = None
    precomputed_bundle: Any = None


async def run_prep(*, req: Any, agent: Any, memory_thread_id: str,
                   prep_timing: Dict[str, int]) -> PrepResult:
    """准备段编排（行为与原 stream 内联逐行等价）。"""
    from app.core.auth import get_current_user  # noqa: F401  # 仅保持 import 语义

    # 跨轮 scope / context 构建（F4: scope 通过原生 context= 传递，不进 checkpoint）
    from ..data_intelligence_support import _extract_customer_names_from_input
    _user_scope = _extract_customer_names_from_input(req.user_input)
    _ctx: Dict[str, Any] = {}
    if _user_scope:
        _ctx["last_scope"] = {
            "customer_names": _user_scope,
            "ordered": True,
            "commitment": "exact_set",
            "source": "user_input",
        }

    # ===== 批13-N3：checkpoint 一次性读取（config 用无 checkpoint_ns 形式）=====
    _state_config_once = {"configurable": {"thread_id": memory_thread_id}, "recursion_limit": 80}
    _shared_state_values: dict = {}
    try:
        _t_state = time.time()
        _state_once = await agent.aget_state(_state_config_once)
        prep_timing["state_ms"] = round((time.time() - _t_state) * 1000)
        _shared_state_values = (_state_once.values or {}) if _state_once else {}
    except Exception:
        prep_timing["state_ms"] = round((time.time() - _t_state) * 1000) if "_t_state" in dir() else -1
    # 写回/流式执行沿用原带 checkpoint_ns 的 config（行为不变；读取统一走上面的无 ns 形式）
    config = {"configurable": {"thread_id": memory_thread_id, "checkpoint_ns": "freeplan"}, "recursion_limit": 80}

    # 跨轮 scope：从共享状态读上一轮 model_declared 范围
    if not _ctx.get("last_scope"):
        _prev_scope = _shared_state_values.get("last_scope")
        if _prev_scope and _prev_scope.get("customer_names"):
            _ctx["last_scope"] = _prev_scope

    # ===== 受控 Skill 问答平台 v2：确定性路由 -> 受控契约 -> 注入 =====
    from app.services.skill_router import route_user_input
    _conversation_ctx = {"thread_id": req.thread_id}
    if _ctx.get("last_scope"):
        _conversation_ctx["last_scope"] = _ctx["last_scope"]
        _conversation_ctx["last_skill"] = None  # 跨轮技能延续由 checkpoint state 提供
    _prev_state_skill = _shared_state_values.get("last_skill")
    if _prev_state_skill:
        _conversation_ctx["last_skill"] = _prev_state_skill

    # ===== 批13-N5：金标向量检索后台化（不阻塞编排主链）=====
    _retrieval_task = None
    if req.user_input:
        def _prefetch_bundle():
            from app.services.golden_qa_service import retrieve_golden_bundle as _rcb
            from app.core.database import SessionLocal as _SL
            _db = _SL()
            try:
                return _rcb(_db, req.user_input)
            finally:
                _db.close()
        try:
            _retrieval_task = asyncio.create_task(asyncio.to_thread(_prefetch_bundle))
        except Exception:
            _retrieval_task = None

    try:
        _t_route = time.time()
        # ⑤R E1 接线：非 wenshu 专家按卡 tools 面路由（专家卡面契约）——原仓语义=教学
        # 代理带自身工具自由对话，无 wenshu 场景路由层。wenshu 卡维持原路由不变。
        _card_tools = None
        if getattr(req, "expert_id", "") and req.expert_id != "wenshu":
            try:
                from app.services import expert_config as _ec_route
                _route_card = _ec_route.get_card(req.expert_id)
                if _route_card and _route_card.get("tools"):
                    _card_tools = list(_route_card["tools"])
            except Exception as _ece:
                logger.warning(f"[E1 卡面路由] 卡读取失败（降级 wenshu 路由）: {_ece}")
        if _card_tools:
            from app.services.query_contract import QueryContract
            from app.services.skill_router import RouteResult, PRIORITY_GENERIC
            _route = RouteResult(
                route_type="expert_card", skill_id=f"expert:{req.expert_id}",
                workflow_step="chat",
                matched_rules=[f"expert_card: {req.expert_id} 卡面路由"],
                route_reason="专家卡面路由（⑤R E1：卡 tools 面=契约面，不走 wenshu 场景剧本）",
                fallback_level="none",
                contract=QueryContract.for_expert_card(
                    expert_id=req.expert_id, tools=_card_tools),
                priority=PRIORITY_GENERIC,
            )
            prep_timing["route_ms"] = round((time.time() - _t_route) * 1000)
        else:
            _route = route_user_input(req.user_input, _conversation_ctx)
            prep_timing["route_ms"] = round((time.time() - _t_route) * 1000)
    except Exception as _rte:
        logger.warning(f"[SkillRouter] 路由异常，降级为低权限通用契约: {_rte}")
        from app.services.query_contract import QueryContract
        _route = None
        _fallback_contract = QueryContract.generic(route_reason=f"路由异常降级: {_rte}")
    _contract = getattr(_route, "contract", None) if _route is not None else _fallback_contract

    # S5（HITL v2）：free_plan generic 路径开启人审（scenario 保持自动降级）
    if (_contract is not None and _route is not None and _route.route_type == "generic"):
        try:
            _contract.hitl_enabled = True
        except Exception:
            pass

    # ===== S3b（G9）追问改写（仅 generic 路由确认后才改写）=====
    _followup_rewritten = None
    _fu_t0 = time.time()
    _is_generic_route = (_route is not None and _route.route_type == "generic")
    if _is_generic_route and _contract is not None:
        try:
            from app.services.followup_rewrite import (
                is_followup_question, history_text_from_state, rewrite_followup_question,
                _REWRITE_HISTORY_TAIL, _REWRITE_HISTORY_PER_LINE, _REWRITE_TIMEOUT,
            )
            _has_history = bool(_shared_state_values.get("messages"))
            if _has_history and is_followup_question(req.user_input, _has_history):
                _hist_state_like = types.SimpleNamespace(values=_shared_state_values)
                _history_text = history_text_from_state(
                    _hist_state_like, tail=_REWRITE_HISTORY_TAIL, per_line=_REWRITE_HISTORY_PER_LINE)
                # 硬性封顶（TUPU_REWRITE_TIMEOUT，默认 8s）
                _followup_rewritten = await asyncio.wait_for(
                    asyncio.to_thread(
                        rewrite_followup_question, req.user_input, _history_text, req.llm_connection_id or ""
                    ),
                    timeout=_REWRITE_TIMEOUT,
                ) or None
                if _followup_rewritten:
                    logger.info(f"[FollowupRewrite] {req.user_input!r} -> {_followup_rewritten!r}")
        except Exception as _frw:
            logger.warning(f"[FollowupRewrite] 追问改写流程异常，回退原问题: {_frw}")
            _followup_rewritten = None
    prep_timing["rewrite_ms"] = round((time.time() - _fu_t0) * 1000)

    # S3b 边界：scenario 模式不改写（问题结构化强）
    _effective_question = req.user_input
    if (_followup_rewritten and _is_generic_route and _contract is not None):
        _effective_question = _followup_rewritten
        # 改写后的完整问题可能带聚合触发词——补挂 aggregate_intent 使 L2 结果层硬校验生效
        try:
            from app.services.skill_router import SkillRouter
            _agg2 = SkillRouter.detect_aggregate_intent(_effective_question)
            if _agg2 and not getattr(_contract, "aggregate_intent", None):
                _contract.aggregate_intent = _agg2
        except Exception:
            pass
    elif _followup_rewritten:
        logger.info(f"[FollowupRewrite] 非 generic 路径丢弃改写，用原问题")

    # 契约注入 runtime.context（SkillPolicyMiddleware 读取的唯一边界）
    _precomputed_bundle = None
    if _contract is not None:
        _ctx["contract"] = _contract
        # 批13-N5：收割后台检索结果
        if _retrieval_task is not None:
            try:
                _t_ret = time.time()
                _precomputed_bundle = await _retrieval_task
                prep_timing["retrieval_ms"] = round((time.time() - _t_ret) * 1000)
            except Exception as _rt_err:
                logger.warning(f"[PrepTiming] 金标检索后台任务失败（降级不带锚定）: {_rt_err}")
                prep_timing["retrieval_ms"] = -1
        # 每次请求只向模型提供受控工作流上下文；批13-C: 尾部追加 top-3 金标锚定
        from ..data_intelligence import _build_contract_system_message
        from langchain_core.messages import HumanMessage, SystemMessage
        _contract_msg = _build_contract_system_message(
            _contract, question=_effective_question, precomputed_bundle=_precomputed_bundle)
        # 批13-C：金标注入完成后按锚定强度分档（高分金标锚定跳过 rubric 自评）
        try:
            from app.services.query_contract import apply_rubric_tier
            apply_rubric_tier(_contract)
        except Exception as _rbe:
            logger.warning(f"[RubricTier] 分档失败(不影响执行): {_rbe}")
        input_messages = [SystemMessage(content=_contract_msg), HumanMessage(content=_effective_question)]
        logger.info(
            f"[SkillRouter] route={_route.route_type if _route else 'fallback'} "
            f"skill={_contract.skill_id} step={_contract.workflow_step} "
            f"allowed={len(_contract.allowed_tools)} 契约注入成功"
        )
    else:
        input_messages = [HumanMessage(content=_effective_question)]

    # 评审 P1-5：路由成功后确定性写回 last_skill/last_step
    try:
        if _route is not None and _route.route_type == "scenario" and _contract is not None:
            _state_upd = {"last_skill": _contract.skill_id, "last_step": _contract.workflow_step}
        else:
            _state_upd = {"last_skill": None, "last_step": None}
        await agent.aupdate_state(config, _state_upd)
    except Exception as _wbe:
        logger.warning(f"[SkillRouter] last_skill/last_step 写回 checkpoint 失败: {_wbe}")

    return PrepResult(
        config=config,
        route=_route,
        contract=_contract,
        effective_question=_effective_question,
        input_messages=input_messages,
        ctx=_ctx,
        followup_rewritten=_followup_rewritten,
        precomputed_bundle=_precomputed_bundle,
    )
