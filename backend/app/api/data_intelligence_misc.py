"""数据智能对话 API -- 路由预览/健康检查/技能治理杂项端点（自 data_intelligence.py 机械拆分，行为等价）

端点（router 自带 prefix="/api/data-intelligence"，与拆分前 data_intelligence.router 完全一致）：
  POST   /route/preview                              受控路由预览（RouteSimulator）
  GET    /health                                     健康检查
  GET    /skills/catalog                             Skill 目录快照（治理/审核）
  GET    /skills/metrics                             治理指标 + 审计轨迹快照
  POST   /skills/simulate-route                      Skill 工作台路由模拟
  DELETE /chat/freeplan/threads/{thread_id}/memory    清除会话 checkpoint 记忆
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-intelligence", tags=["data-intelligence"])


class RoutePreviewRequest(BaseModel):
    """受控路由预览：输入问句 + 可选连续上下文，返回确定性路由结果+契约。"""
    user_input: str
    last_skill: Optional[str] = None
    last_step: Optional[str] = None
    customer_names: List[str] = Field(default_factory=list)


@router.post("/route/preview")
def route_preview(req: RoutePreviewRequest) -> Dict[str, Any]:
    """受控 Skill 问答平台 v2：RouteSimulator 预览端点。

    前端不自行猜路由/契约，统一走后端 SkillRouter（与生产对话同一裁判）。
    """
    ctx: Dict[str, Any] = {}
    if req.last_skill:
        ctx["last_skill"] = req.last_skill
    if req.last_step:
        ctx["last_step"] = req.last_step
    if req.customer_names:
        ctx["last_scope"] = {
            "customer_names": list(req.customer_names),
            "ordered": True,
            "commitment": "exact_set",
            "source": "user_input",
        }
    try:
        from app.services.skill_router import route_user_input
        result = route_user_input(req.user_input, ctx)
        return {"ok": True, "route": result.to_dict()}
    except Exception as e:
        logger.error(f"[RoutePreview] 路由预览异常: {e}")
        return {"ok": False, "error": str(e)}


@router.get("/health")
def health() -> Dict[str, str]:
    """健康检查"""
    return {"status": "ok", "service": "data-intelligence"}


# ----------------------------------------------------------------------
# 批4 生产治理端点（运行观测台数据源 / 审核入口）
# ----------------------------------------------------------------------
@router.get("/skills/catalog")
def skills_catalog() -> Dict[str, Any]:
    """Skill 目录快照：启用/禁用/版本/哈希/告警（生产治理·审核用）。

    供运行观测台与上线审核查看当前 SKILL.md 唯一来源的解析状态；
    不参与路由逻辑（路由只认 SkillRouter）。
    """
    try:
        from app.services.skill_catalog import get_catalog
        cat = get_catalog()
        skills = []
        for md in sorted(cat._scenarios_dir.glob("*/SKILL.md")):
            name = md.parent.name
            loaded = cat.load_skill(name)
            if loaded is not None:
                skills.append({
                    "skill_id": loaded.name, "enabled": loaded.enabled,
                    "version": loaded.version, "priority": loaded.priority,
                    "sha256": loaded.sha256[:16], "steps": [s.id for s in loaded.steps],
                    "template_count": sum(len(s.templates) for s in loaded.steps),
                    "entity_alias_count": len(loaded.entity_aliases),
                    "multi_engine": bool(loaded.multi_engine),
                    "template_mode": loaded.template_mode,   # P0-2 治理可见：strict/extensible/generic
                    "forbid_markdown_detail_table": bool(loaded.output.get("forbid_markdown_detail_table", True)),
                })
            else:
                failed = cat._failed.get(name)
                skills.append({
                    "skill_id": name, "enabled": False, "version": None,
                    "priority": None, "sha256": None, "steps": [],
                    "template_count": 0, "entity_alias_count": 0,
                    "disabled_reason": failed or "解析失败已禁用",
                })
        return {
            "ok": True,
            "catalog": skills,
            "warnings": cat.warnings[-50:],
            "skills_root": str(cat._scenarios_dir),
        }
    except Exception as e:
        logger.error(f"[Governance] catalog 端点异常: {e}")
        return {"ok": False, "error": str(e)}


@router.get("/skills/metrics")
def skills_metrics() -> Dict[str, Any]:
    """治理指标 + 审计轨迹快照（进程内；运行观测台消费）。"""
    try:
        from app.services.skill_governance import get_governance
        snap = get_governance().snapshot()
        snap["ok"] = True
        return snap
    except Exception as e:
        logger.error(f"[Governance] metrics 端点异常: {e}")
        return {"ok": False, "error": str(e)}


@router.post("/skills/simulate-route")
def simulate_route(req: RoutePreviewRequest) -> Dict[str, Any]:
    """Skill 工作台路由模拟（设计 §7.3 端点名）：复用与生产一致的 SkillRouter。

    前端不镜像规则：模拟结果即生产判定结果。
    """
    return route_preview(req)


@router.delete("/chat/freeplan/threads/{thread_id}/memory")
async def clear_freeplan_memory(thread_id: str, request: Request):
    """清除自由问答会话的后端 checkpoint 记忆。
    前端清空/删除会话时调用，确保 Agent 不再记住已清空的内容。

    v3.6: 加会话所有权校验（评审 P0）：用当前用户 sub 构造 thread_id，
    确保只能清自己的会话，防跨用户清除。
    """
    from app.core.auth import get_current_user
    _current_user = get_current_user(request)
    _user_prefix = _current_user.sub if _current_user and _current_user.sub else "anonymous"
    # 专家地基①（spec §八）：三段键单点收口；①期清除端点固定 wenshu 域（misc 路由属问数页面，
    # 无 ChatRequest 上下文不可卡化——登记②期随端点卡化）
    from app.services.expert_paths import thread_id as _expert_thread_id
    _memory_thread_id = _expert_thread_id(_user_prefix, "wenshu", thread_id)
    try:
        from app.services.tupu_deepagent import _GLOBAL_CHECKPOINTER
        # Agent 尚未初始化 -> 无 checkpoint 可清，直接返回成功
        if _GLOBAL_CHECKPOINTER is None:
            return {"status": "ok", "thread_id": thread_id, "cleared": False, "note": "agent not initialized, nothing to clear"}
        try:
            await _GLOBAL_CHECKPOINTER.adelete_thread(_memory_thread_id)
            logger.info(f"[FreePlan] checkpoint 已清除: thread_id={_memory_thread_id}")
            return {"status": "ok", "thread_id": thread_id, "cleared": True}
        except Exception as e:
            logger.warning(f"[FreePlan] adelete_thread 失败({e}), 尝试逐条删除")
            # 降级：直接从 SQLite 删除该 thread_id 的 checkpoint 行
            try:
                import aiosqlite
                from app.services.tupu_deepagent import _CHECKPOINT_DB
                import aiosqlite as _aiosqlite
                async with _aiosqlite.connect(_CHECKPOINT_DB) as db:
                    await db.execute("DELETE FROM checkpoints WHERE thread_id = ?", (_memory_thread_id,))
                    await db.execute("DELETE FROM writes WHERE thread_id = ?", (_memory_thread_id,))
                    await db.commit()
                logger.info(f"[FreePlan] checkpoint 降级删除成功: thread_id={_memory_thread_id}")
                return {"status": "ok", "thread_id": thread_id, "cleared": True, "note": "deleted via raw SQL"}
            except Exception as e2:
                logger.error(f"[FreePlan] 降级删除也失败: {e2}")
                raise HTTPException(status_code=500, detail=f"清除记忆失败(降级删除也失败): {e2}")
    except Exception as e:
        logger.error(f"[FreePlan] 清除 checkpoint 失败: {e}")
        raise HTTPException(status_code=500, detail=f"清除记忆失败: {e}")
