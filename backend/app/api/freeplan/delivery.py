# -*- coding: utf-8 -*-
"""freeplan/delivery.py - 收尾段纯函数（批13-D Step1，从 stream 单体提取，行为零变化）。

覆盖（原 data_intelligence_stream.chat_freeplan_stream 收尾段 L995-1212）：
  extract_final_answer_from_state  从 checkpoint state 取最终 AIMessage 文本
  apply_output_contract            输出契约校验 + Markdown 明细表 scrub（治理留痕）
  build_sql_result_payload         前端数据表格载荷（完整性契约字段）
  build_confirmed                  L2/L2X/SQL 确认块
  build_evidence                   M3 证据链聚合 + 置信度三级
  build_recommendations            推荐问题（final_delivery > final_answer 提取 > 默认兜底）
  build_done_payload               done 帧载荷
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DEFAULT_RECS = ["统计用电客户总数", "查客户的联系电话", "什么是变压器"]


def extract_final_answer_from_state(msgs: List[Any]) -> str:
    """从 state messages 取最后一条非工具 AIMessage（最终回复）；无则空串。"""
    try:
        for msg in reversed(msgs):
            if msg.__class__.__name__ == "AIMessage" and not getattr(msg, "tool_calls", None):
                c = msg.content if isinstance(msg.content, str) else str(msg.content)
                if c and c.strip():
                    return c
    except Exception:
        pass
    return ""


def apply_output_contract(final_answer: str, sql_result: Any, forbid_md: bool = True) -> Dict[str, Any]:
    """输出契约校验：完整数据已推前端表时剥离最终回答的 Markdown 明细表。

    返回 {answer, reason, scrubbed}：scrubbed=True 表示发生过清洗（治理留痕）。
    """
    out = {"answer": final_answer, "reason": "", "scrubbed": False}
    _has_ui_result = bool(sql_result and isinstance(sql_result, dict) and not sql_result.get("error"))
    if not (_has_ui_result and final_answer):
        return out
    try:
        from app.services.output_contract import validate_final_output, scrub_markdown_tables
        _oc = validate_final_output(
            final_answer, result_available_for_ui=True,
            row_count=(sql_result or {}).get("row_count"),
            forbid_markdown_detail_table=forbid_md,
        )
        out["reason"] = _oc.reason
        if not _oc.ok:
            _scrubbed = scrub_markdown_tables(final_answer)
            if _scrubbed != final_answer:
                out["answer"] = _scrubbed
                out["scrubbed"] = True
            logger.info(f"[OutputContract] 已清洗最终回答 Markdown 明细表: {_oc.reason}")
            try:
                from app.services.skill_governance import EVENT_OUTPUT_SCRUBBED, get_governance
                get_governance().record_output(EVENT_OUTPUT_SCRUBBED, _oc.reason or "markdown_detail_table")
            except Exception:
                pass
    except Exception as _oce:
        logger.warning(f"[OutputContract] 输出校验异常: {_oce}")
    return out


def build_sql_result_payload(sr: Any, assembled_sql: str) -> Optional[Dict[str, Any]]:
    """SQL 执行结果 -> 前端数据表格载荷（含完整性契约字段，前端不把预览当不完整）。"""
    if not (sr and isinstance(sr, dict) and not sr.get("error")):
        return None
    _rows = sr.get("rows", [])
    _rc = sr.get("row_count", 0) or len(_rows)
    return {
        "columns": sr.get("columns", []),
        "rows": _rows,
        "row_count": _rc,
        "sql": assembled_sql or "",
        "returned_rows": len(_rows),
        "preview_row_count": min(10, _rc),
        "is_preview": False,                    # 前端拿完整数据，一律 false
        "llm_is_preview": _rc > 10,             # 模型是否只看前 10 行分析样本
        "llm_preview_row_count": min(10, _rc),  # 模型样本行数
        "result_available_for_ui": True,
    }


def build_confirmed(tool_results: Dict[str, Any]) -> Dict[str, Any]:
    """L2/L2X/attributes/assembled_sql 确认块（前端 DataAccessCard 关联展示）。"""
    return {
        "L2": tool_results.get("l2_name", ""),
        "L2_id": tool_results.get("l2_id", ""),
        "L2X": tool_results.get("entity_code", ""),
        "L2X_name": tool_results.get("entity_name", ""),
        "attributes": tool_results.get("attributes", []),
        "assembled_sql": tool_results.get("assembled_sql", ""),
    }


def _extract_main_table(sql_txt: str) -> str:
    try:
        from app.services.kg_action_handlers import _extract_main_table
        return _extract_main_table(sql_txt) or ""
    except Exception:
        return ""


def build_evidence(contract: Any, tool_results: Dict[str, Any], final_answer: str,
                   golden_hits: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """M3 G7 证据链聚合 + 置信度三级（高/中/低）。

    高=rubric satisfied|skipped_clean_aggregate 且 verification 无 warning；
    低=corrections>0 或 rubric 失败/超限/grader错，或零执行但答案含数字（S1 b）；
    中=无 rubric（scenario）或 verification 有 warning。
    """
    _ev_route = {
        "skill": contract.skill_id if contract is not None else "__generic__",
        "route_type": contract.route_type if contract is not None else "generic",
    }
    _ev_tables: List[str] = []
    _ev_verification: Dict[str, Any] = {}
    _sr_ev = tool_results.get("sql_result")
    if isinstance(_sr_ev, dict):
        _ev_verification = _sr_ev.get("verification") or {}
        _ev_sql_txt = str(tool_results.get("assembled_sql") or _sr_ev.get("sql") or "")
        if _ev_sql_txt:
            _t = _extract_main_table(_ev_sql_txt)
            if _t:
                _ev_tables = [_t]
    _ev_examples: List[Dict[str, Any]] = []
    for _h in (golden_hits or []):
        if isinstance(_h, dict):
            _ev_examples.append({"q": _h.get("question_raw") or _h.get("question") or "",
                                 "sim": _h.get("score")})
    _ev_rubric = {
        "status": contract._runtime.get("rubric_status") if contract is not None else None,
        "iterations": int((contract._runtime.get("rubric_iterations") or 0)) if contract is not None else 0,
    }
    _ev_corrections = int((contract._runtime.get("corrections") or 0)) if contract is not None else 0
    _ev_confidence = "中"
    _rs = _ev_rubric["status"]
    if _ev_corrections > 0 or _rs in ("failed", "max_iterations_reached", "grader_error"):
        _ev_confidence = "低"
    elif (_rs in ("satisfied", "skipped_clean_aggregate")
          and not _ev_verification.get("warnings")):
        _ev_confidence = "高"
    # S1（b）：零执行但回答含数字 -> 无数据支撑告警（前端置信度判低 + 黄条提示）
    _ev_missing_data = False
    if not tool_results.get("sql_executed", False) and (final_answer or ""):
        if any(_ch.isdigit() for _ch in final_answer):
            _ev_missing_data = True
            _ev_confidence = "低"
    return {
        "evidence": {
            "route": _ev_route, "tables": _ev_tables, "examples_used": _ev_examples,
            "verification": _ev_verification, "rubric": _ev_rubric, "corrections": _ev_corrections,
            "missing_data_support": _ev_missing_data,
        },
        "confidence": _ev_confidence,
        "rubric": _ev_rubric,
    }


def build_recommendations(final_delivery: Any, final_answer: str) -> List[str]:
    """推荐问题（优先 final_delivery.recommendations，其次 final_answer 提取，再默认兜底）。"""
    recs = []
    try:
        if isinstance(final_delivery, dict) and final_delivery.get("recommendations"):
            recs = final_delivery["recommendations"]
    except Exception:
        recs = []
    if not recs:
        try:
            from .data_intelligence_support import _extract_recommendations
            recs = _extract_recommendations(final_answer)
        except Exception:
            recs = []
    if not recs:
        recs = list(_DEFAULT_RECS)
    return recs


def build_done_payload(*, thread_id: str, confirmed: Dict[str, Any], think_stream: List[Any],
                       tool_results: Dict[str, Any], route: Any, contract: Any,
                       final_answer: str, structured: Any, structured_degraded: bool,
                       final_delivery: Any, sql_result_data: Any, recs: List[str],
                       evidence: Dict[str, Any], confidence: str,
                       timing: Dict[str, Any], output_scrubbed: bool,
                       output_check_reason: str) -> Dict[str, Any]:
    """done 帧载荷构建（键序与拆分前一致）。"""
    return {
        "thread_id": thread_id,
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
            "output_scrubbed": output_scrubbed,
        },
        "route": (route.to_dict() if route is not None else None),
        "contract": contract.to_dict() if contract is not None else None,
        "output_contract_check": {"ok": not output_scrubbed, "reason": output_check_reason},
        "think_stream": think_stream,
        "final_answer": final_answer,
        "final_answer_structured": structured,
        "response_format_degraded": structured_degraded,
        "final_delivery": final_delivery,
        "sql_result": sql_result_data,
        "recommendations": [{"label": r, "shortcut": r} for r in recs],
        "next_step_recommendation": None,
        "message_card": None,
        "evidence": evidence,
        "confidence": confidence,
        "timing": dict(timing),
    }
