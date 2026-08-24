# -*- coding: utf-8 -*-
"""answer_renderer.py - 批9 模板直出答案渲染器（问五）

确定性模板填槽：row_count / 口径注释 / data_snapshot_at。不经过 LLM，
输出契约友好（generic 禁 Markdown 明细表 -> 多行结果只报行数，明细由前端结果表唯一展示）。
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, Optional

# 计数词剥离：从问题提取主体词（「统计用电客户总数」->「用电客户」）
_COUNT_WORD_RE = re.compile(r"(总数|数量|多少个|几个|多少|数目|统计|查询|一下|请问|请|系统里|系统中)")


def _subject_from_question(question: str) -> str:
    """从问题剥离计数词得到主体词；剥不出（空/过短）返回空串。"""
    t = _COUNT_WORD_RE.sub("", str(question or "").strip())
    t = re.sub(r"[的了吗呢？?。！!，,、\s]+$", "", t)
    if len(t) < 2:
        return ""
    return t


def render_template_answer(question: str, example_hit: Dict[str, Any],
                           sql_result: Dict[str, Any]) -> str:
    """模板填槽渲染直出答案。

    - 1 行 1 列标量（COUNT 类）：共 {value} {主体词}；
    - 多行：只报行数/列数（明细由前端查询结果表唯一展示）；
    - 尾部固定口径注释：来源示例 + 主表 + 数据截至（data_snapshot_at 或查询时刻）。
    """
    rows = (sql_result or {}).get("rows") or []
    row_count = int((sql_result or {}).get("row_count") or len(rows) or 0)
    cols = (sql_result or {}).get("columns") or []

    value_txt: Optional[str] = None
    if row_count == 1 and rows and isinstance(rows[0], (list, tuple)) and len(rows[0]) == 1:
        v = rows[0][0]
        value_txt = str(v)

    subject = _subject_from_question(question)
    lines: list = []
    if value_txt is not None:
        if subject:
            lines.append(f"共 **{value_txt}** 个{subject}。")
        else:
            lines.append(f"共 **{value_txt}** 条。")
    else:
        lines.append(f"查询完成：返回 {row_count} 行 × {len(cols)} 列，明细见下方查询结果表。")

    # 口径注释（scope）+ 数据截至
    try:
        from app.services.kg_action_handlers import _extract_main_table
        table = _extract_main_table(str((sql_result or {}).get("sql") or "")) or "已验证数据源"
    except Exception:
        table = "已验证数据源"
    snapshot = (sql_result or {}).get("data_snapshot_at")
    if not snapshot:
        snapshot = datetime.now().strftime("%Y-%m-%d %H:%M")
    ex_q = str((example_hit or {}).get("question_raw") or "").strip()
    scope = f"统计口径：{table}"
    if ex_q:
        scope += f"（命中已验证示例「{ex_q}」）"
    lines.append(f"> {scope}；数据截至 {snapshot}。")
    return "\n".join(lines)
