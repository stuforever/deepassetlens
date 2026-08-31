"""数据智能对话 API（FastAPI 路由）

基于 DeepAgents 框架（LLM + kg_api 工具 + SKILL.md 文件驱动），提供：
  POST /api/data-intelligence/chat/freeplan/stream
    - 入参：thread_id, user_input, user_selection（可选）
    - 出参：SSE 流式推送（think/token/final/recommend/sql_result/trace/done）
  GET /api/data-intelligence/health
    - 健康检查
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


from .data_intelligence_support import (
    _ACTION_TOOL_MAP, _SKILL_CODE_CN, _SESSION_LOCKS, _SESSION_LOCK_MAX, _KG_ACTION_LABELS,
    _get_session_lock, _extract_customer_names_from_input, _extract_recommendations,
    _safe_error_summary, _empty_result_text, _build_final_delivery,
    _build_action_detail, _infer_decision_task, _build_result_summary,
    _build_nonjson_result_summary,
)


class UserSelection(BaseModel):
    label: Optional[str] = None
    value: Optional[str] = None
    name: Optional[str] = None
    code: Optional[str] = None
    level: Optional[str] = None
    entity_code: Optional[str] = None
    attribute_code: Optional[str] = None
    is_main_table: Optional[bool] = None


class ChatRequest(BaseModel):
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_input: str
    user_selection: List[UserSelection] = Field(default_factory=list)
    format: str = Field(default="default", description="响应格式：default | card")
    llm_connection_id: Optional[str] = Field(default=None, description="指定 LLM 连接 ID（不传则用默认）")
    mode: str = Field(default="free_plan", description="对话模式：free_plan")


class ChatResponse(BaseModel):
    thread_id: str
    current_task: str
    goal: Optional[str] = None
    pending_clarification: Optional[Dict[str, Any]] = None
    confirmed: Dict[str, Any] = Field(default_factory=dict)
    completed_tasks: List[str] = Field(default_factory=list)
    flags: Dict[str, bool] = Field(default_factory=dict)
    trace: List[Dict[str, Any]] = Field(default_factory=list)
    think_stream: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_next: List[Dict[str, str]] = Field(default_factory=list)
    next_step_recommendation: Optional[Dict[str, Any]] = None
    message_card: Optional[Dict[str, Any]] = None


# 批5-C1：契约文案模板常量——DeepSeek 服务端前缀缓存命中前提=前缀逐字节一致；
# 固定骨架全部走这里（同场景逐字节一致），变化内容（示例块/首选计划/实体提示/指引）
# 一律 append 在消息尾部，不打碎前缀。
_CONTRACT_HEADER = "你当前处于受控工作流。以下契约由代码强制执行（SkillPolicyMiddleware），你无权改写："
_CONTRACT_ENGINE_UNCONFIRMED = ("尚未确认 —— 先调用 batch_entity_source_mode 确认数据源模式，"
                                "再执行数据查询；引擎一经锁定只允许对应工具，禁止切换重查")
_CONTRACT_STOP_DEFAULT = "拿到查询结果即停止"
_CONTRACT_OUTPUT_SUFFIX = (" —— 完整明细由前端查询结果表唯一展示，最终回答禁止输出 Markdown 明细表，"
                           "只写结论/发现/风险/建议")


def _build_contract_system_message(contract, question: str = "", precomputed_bundle: dict | None = None) -> str:
    """按契约构造每次请求注入的 SystemMessage（设计 §7.1：只向模型提供受控上下文）。

    模型只在契约允许范围内做判断；契约本身由代码路由+SkillPolicy 强制执行。
    G1（融合设计 §4.1；批13-C 金标锚定）：question 非空时尾部追加 top-3 金标锚定
    静默跳过，不阻断问答）；命中写入 contract._runtime["golden_hits"] 并累计 hit_count。
    批13-N5：precomputed_bundle 非空时直接使用流层后台预取的检索结果，跳过内部同步检索
    （检索已与锁/状态读取/路由并行）；None 时维持原行为内部检索。
    """
    scope = contract.scope or {}
    customers = scope.get("customer_names") or []
    scope_txt = ("; ".join(customers) if customers else "无客户名限定")
    if scope.get("commitment") == "exact_set":
        scope_txt += f"（精确集合，{scope.get('source', 'user_input')}）"
    lines = [
        _CONTRACT_HEADER,
        f"- 场景/步骤：{contract.skill_id} / {contract.workflow_step}",
        f"- 允许工具：{', '.join(contract.allowed_tools)}",
        f"- 禁止工具：{', '.join(contract.forbidden_tools) or '无'}",
        f"- 本次允许的 SQL 模板：{', '.join(contract.template_ids) or '未声明（仅只读查询）'}",
        f"- 范围：客户名 {scope_txt}",
        f"- 数据引擎：{contract.selected_engine or _CONTRACT_ENGINE_UNCONFIRMED}",
        f"- 终止条件：{'；'.join(contract.stop_when) or _CONTRACT_STOP_DEFAULT}",
        f"- 输出模式：{contract.output_mode}{_CONTRACT_OUTPUT_SUFFIX}",
    ]
    base = "\n".join(lines)
    # S1（L1）：聚合分布意图 -> 追加受控指令（路由层标记，结构层要求聚合视图）
    agg = getattr(contract, "aggregate_intent", None)
    if agg:
        _dim = f"（维度列提示：{agg.get('dimension_hint')}）" if agg.get("dimension_hint") else ""
        base += (
            f"\n- 本问题要求聚合分布/占比视图{_dim}：必须返回 GROUP BY 维度列 + COUNT/SUM 的聚合结果，"
            "禁止返回明细全表；如需维度枚举值先 sample_column_values。"
        )
    # S2（金标扩容）：歧义提问 -> 收缩工具集为空 + 指令输出澄清问题（禁止任何数据查询）
    if getattr(contract, "clarify_required", False):
        base += (
            "\n- 本问题意图不明确（未指明关心的维度/指标）。本步骤不允许调用任何工具、禁止执行任何数据查询。"
            "请直接用一句话向用户澄清：询问其想了解的具体维度或指标（如电压等级、容量、重要性等级等），不要作答数据结论。"
        )
    if question:
        try:
            # 批13-C：金标锚定检索单入口（qa_example_service 运行时退役，题库移除）
            # 一次 embedding 双集合（金标+实体）并搜 + E2 短窗缓存
            # （同问题 60s 内二次提问 0 远程检索；直通判定/自评豁免共享同一份 golden_hits）
            # 批13-N5：流层后台预取的 bundle 优先（检索已与编排并行，此处零等待收割）
            if precomputed_bundle is not None:
                _bundle = precomputed_bundle
            else:
                from app.services.golden_qa_service import retrieve_golden_bundle
                from app.core.database import SessionLocal
                _db = SessionLocal()
                try:
                    _bundle = retrieve_golden_bundle(_db, question)
                finally:
                    _db.close()
            from app.services.golden_qa_service import bump_golden_hit
            if _bundle["golden_block"]:
                base += _bundle["golden_block"]
                try:
                    contract._runtime["golden_hits"] = _bundle["golden_hits"]
                except Exception:
                    pass
                # 首选计划（L1 层）：高分金标直接执行已验证 SQL（5 轮 → 2 轮核心杠杆）。
                # 阈值比展示(0.75)/rubric 直通(0.85)更严（默认 0.90，环境变量 TUPU_DIRECT_PLAN_SIM 可调）；
                # 金标 SQL 仍过 validate_sql（SELECT-only/强制 LIMIT）与 SkillPolicy 全链路，写错表有纠错兜底。
                _DIRECT_PLAN_SIM = float(os.getenv("TUPU_DIRECT_PLAN_SIM", "0.90"))
                if _bundle["golden_hits"]:
                    _top = max(_bundle["golden_hits"], key=lambda h: h.get("score") or 0)
                    if (_top.get("score") or 0) >= _DIRECT_PLAN_SIM and _top.get("sql"):
                        _eng = _top.get("engine") or "doris"
                        # 首选计划锚定：锁定引擎（金标 SQL 已验证，默认 Doris 联邦），
                        # 模型只能 execute_doris_sql 直接执行，跳过 batch_entity_source_mode 确认轮（省 ~10s）。
                        # 若执行报 TABLE_MISSING/列名错误，纠错循环会触发回退。
                        try:
                            if _eng in ("doris", "duckdb", "physical"):
                                contract.lock_engine(_eng, f"首选计划金标锚定（相似度 {_top['score']:.2f}）")
                        except Exception:
                            pass
                        base += (
                            f"\n首选计划（已验证金标，相似度 {_top['score']:.2f}）：直接执行以下 SQL 作答，"
                            f"跳过实体定位与读技能步骤；数据引擎已锁定为 {_eng}，"
                            f"用 execute_doris_sql 直接执行（金标 SQL 已通过回归验证；若报 TABLE_MISSING/列名错误，"
                            f"再 batch_entity_source_mode 确认源模式后重试，仍失败则回退常规定位流程 search_entities）。\n"
                            f"SQL：{_top['sql']}"
                        )
                try:
                    _db2 = SessionLocal()
                    try:
                        bump_golden_hit(_db2, [str(h["id"]) for h in _bundle["golden_hits"]])
                    finally:
                        _db2.close()
                except Exception:
                    pass
            if _bundle["entity_hint_block"]:
                base += _bundle["entity_hint_block"]
        except Exception as _e:
            logger.warning(f"[金标锚定] 注入失败（静默跳过）: {_e}")
        # 批2-E 指引预载：规则意图分类注入 sql-query 写法指引（省 read_file 技能轮）
        try:
            from app.services.query_contract import build_guidance_block
            _guidance = build_guidance_block(question)
            if _guidance:
                base += _guidance
        except Exception as _eg:
            logger.warning(f"[指引预载] 注入失败（静默跳过）: {_eg}")
    return base


# ---------------------------------------------------------------------------
# 机械拆分（行为等价）：端点实现移至兄弟模块，本模块保留模型/助手并聚合路由。
#   - data_intelligence_stream.py : POST /chat/freeplan/stream（流式问答主函数）
#   - data_intelligence_misc.py   : route/preview、health、skills/*、DELETE memory
# 两个子 router 自带 prefix="/api/data-intelligence"（与拆分前本模块 router 的
# prefix 完全一致），include_router 合并后的最终路径与拆分前逐条相同；
# 下方 re-export 保持 `from app.api.data_intelligence import X` 对外符号不变（tests 依赖）。
# ---------------------------------------------------------------------------
from .data_intelligence_stream import (  # noqa: F401 -- re-export
    router as _stream_router,
    chat_freeplan_stream,
)
from .data_intelligence_misc import (  # noqa: F401 -- re-export
    router as _misc_router,
    RoutePreviewRequest,
    route_preview,
    health,
    skills_catalog,
    skills_metrics,
    simulate_route,
    clear_freeplan_memory,
)

router.include_router(_stream_router)
router.include_router(_misc_router)
