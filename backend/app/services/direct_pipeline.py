# -*- coding: utf-8 -*-
"""direct_pipeline.py - 批9 模板直出管道 v1（问五）

高频题 0 LLM 轮：sim≥0.95 且 count 类且无动态条件 -> 绕过 Agent 直接执行验证 SQL + 模板填槽，2~4s。

分层（与批2-C 共存）：
  - sim≥0.95 且无动态条件 -> 本管道直通（0 轮）；
  - sim 0.90~0.95 或带条件 -> 批2-C 首选计划（Agent 内 1-2 轮）；
  - 其余 -> 常规 Agent。

安全边界诚实声明（设计已登记的有意取舍）：直通绕过 SkillPolicy/Agent 循环——
安全由「来源可信」（验证 SQL 单源：status=enabled 的已验证示例）+ validate_safe_sql
（SELECT-only/强制 LIMIT）+ 模板白名单渲染承接；执行报错自动回退完整 Agent 路径。
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 直通相似度阈值（比首选计划 0.90 更严；环境变量可调）
DIRECT_PIPELINE_SIM = float(os.getenv("TUPU_DIRECT_PIPELINE_SIM", "0.95"))


class DirectPipelineError(Exception):
    """直通执行失败（校验未过/引擎报错）；调用方据此回退完整 Agent 路径。"""


def evaluate_direct_eligibility(contract: Any, question: str) -> Optional[Dict[str, Any]]:
    """路由后、Agent 前的直通判定（纯规则，静默不满足返回 None）。

    条件（设计 §2.5；批13-C 切源 golden_hits；批16-A 路由门放开 scenario）：
    route_type∈(generic, scenario) 且 golden_hits 最高分 ≥0.95
    且 intent_classifier=count 类 且 无动态条件（日期/编号/比较词）
    且 金标 sql 非空（命中行本就来自 enabled 且有 SQL 单源——DB 层过滤 + Qdrant payload 过滤）。
    安全链四件套不变：来源可信/validate_safe_sql（SELECT-only+强制 LIMIT）/模板白名单渲染/失败回退 Agent。
    """
    # 批16-A：路由门 generic-only → {generic, scenario}（scene COUNT 题收敛主改动，spec §五.2）
    if contract is None or getattr(contract, "route_type", "") not in ("generic", "scenario"):
        return None
    if getattr(contract, "clarify_required", False):
        return None
    hits = (getattr(contract, "_runtime", {}) or {}).get("golden_hits") or []
    if not hits:
        return None
    top = max(hits, key=lambda h: h.get("score") or 0)
    sim = float(top.get("score") or 0)
    if sim < DIRECT_PIPELINE_SIM:
        return None
    sql = str(top.get("sql") or "").strip()
    if not sql:
        return None
    from app.services.intent_classifier import is_count_intent, has_dynamic_condition
    if not is_count_intent(question):
        return None
    if has_dynamic_condition(question):
        return None
    engine = (top.get("engine") or "doris").strip() or "doris"
    if engine not in ("doris", "physical"):  # api_integration 等不直通（需实体 API 编排）
        return None
    return {"hit": top, "engine": engine, "sql": sql, "score": sim}


def run_direct_pipeline(plan: Dict[str, Any], question: str,
                        thread_id: str = "") -> Dict[str, Any]:
    """直通执行：validate_safe_sql 安全闸 -> 引擎执行 -> 查询日志 -> bump 命中 -> 模板渲染。

    同步实现（dispatch_kg_action 为同步）；调用方在事件循环里用 asyncio.to_thread 包装。
    失败抛 DirectPipelineError（回退 Agent），其余异常原样上抛同样触发回退。
    """
    from app.services.kg_action_handlers import dispatch_kg_action

    sql = plan["sql"]
    t0 = time.time()
    # ① 显式安全闸（与 Agent 路径同一校验器：SELECT-only/强制 LIMIT/危险函数拦截）
    chk = dispatch_kg_action("validate_safe_sql", {"sql": sql})
    if not isinstance(chk, dict) or not chk.get("safe", False):
        raise DirectPipelineError(str((chk or {}).get("reason") or (chk or {}).get("error") or "SQL 安全校验未通过"))
    # ② 引擎执行（engine 定执行工具）
    tool = "execute_doris_sql" if plan["engine"] == "doris" else "execute_sql"
    res = dispatch_kg_action(tool, {"entity_code": "", "sql": sql, "filters": {}})
    if not isinstance(res, dict) or res.get("error"):
        raise DirectPipelineError(str((res or {}).get("error") or "执行失败"))
    duration_ms = int((time.time() - t0) * 1000)
    # ③ 查询日志（direct_pipeline 标记，看板口径）
    try:
        from app.services.engine_query_log import record_query_log
        record_query_log(
            engine="doris" if tool == "execute_doris_sql" else "sql",
            sql=str(res.get("sql") or sql), rows_returned=int(res.get("row_count") or 0),
            duration_ms=duration_ms, status="ok",
            run_id=(f"direct:{thread_id}" if thread_id else "direct")[:64],
            direct_pipeline=True,
        )
    except Exception as _le:
        logger.warning(f"[DirectPipeline] 查询日志失败（忽略）: {_le}")
    # ④ 命中计数（批13-C：bump 金标 hit_count；👍 已改纯观测——直通不新增示例/金标）
    try:
        from app.core.database import SessionLocal
        from app.services.golden_qa_service import bump_golden_hit
        _db = SessionLocal()
        try:
            bump_golden_hit(_db, [str(plan["hit"].get("id"))])
        finally:
            _db.close()
    except Exception as _he:
        logger.warning(f"[DirectPipeline] 命中计数失败（忽略）: {_he}")
    # ⑤ 模板填槽渲染（确定性，0 LLM）
    from app.services.answer_renderer import render_template_answer
    answer = render_template_answer(question, plan["hit"], res)
    return {"answer": answer, "result": res, "plan": plan, "tool": tool, "duration_ms": duration_ms}
