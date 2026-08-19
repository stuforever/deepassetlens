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


def _build_contract_system_message(contract, question: str = "") -> str:
    """按契约构造每次请求注入的 SystemMessage（设计 §7.1：只向模型提供受控上下文）。

    模型只在契约允许范围内做判断；契约本身由代码路由+SkillPolicy 强制执行。
    G1（融合设计 §4.1）：question 非空时尾部追加 top-3 已验证示例（Qdrant 不可用/无命中
    静默跳过，不阻断问答）；命中写入 contract._runtime["example_hits"] 并累计 hit_count。
    """
    scope = contract.scope or {}
    customers = scope.get("customer_names") or []
    scope_txt = ("; ".join(customers) if customers else "无客户名限定")
    if scope.get("commitment") == "exact_set":
        scope_txt += f"（精确集合，{scope.get('source', 'user_input')}）"
    lines = [
        "你当前处于受控工作流。以下契约由代码强制执行（SkillPolicyMiddleware），你无权改写：",
        f"- 场景/步骤：{contract.skill_id} / {contract.workflow_step}",
        f"- 允许工具：{', '.join(contract.allowed_tools)}",
        f"- 禁止工具：{', '.join(contract.forbidden_tools) or '无'}",
        f"- 本次允许的 SQL 模板：{', '.join(contract.template_ids) or '未声明（仅只读查询）'}",
        f"- 范围：客户名 {scope_txt}",
        f"- 数据引擎：{contract.selected_engine or '尚未确认 —— 先调用 batch_entity_source_mode 确认数据源模式，再执行数据查询；引擎一经锁定只允许对应工具，禁止切换重查'}",
        f"- 终止条件：{'；'.join(contract.stop_when) or '拿到查询结果即停止'}",
        f"- 输出模式：{contract.output_mode} —— 完整明细由前端查询结果表唯一展示，最终回答禁止输出 Markdown 明细表，只写结论/发现/风险/建议",
    ]
    base = "\n".join(lines)
    if question:
        try:
            from app.services.qa_example_service import build_examples_payload, bump_hit_count
            from app.core.database import SessionLocal
            _db = SessionLocal()
            try:
                _payload = build_examples_payload(_db, question)
            finally:
                _db.close()
            if _payload["block"]:
                base += _payload["block"]
                try:
                    contract._runtime["example_hits"] = _payload["hits"]
                except Exception:
                    pass
                try:
                    _db2 = SessionLocal()
                    try:
                        bump_hit_count(_db2, [str(h["id"]) for h in _payload["hits"]])
                    finally:
                        _db2.close()
                except Exception:
                    pass
        except Exception as _e:
            logger.warning(f"[QA示例库] 示例注入失败（静默跳过）: {_e}")
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
