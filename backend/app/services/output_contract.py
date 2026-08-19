"""output_contract.py - 最终输出校验（受控 Skill 问答平台 v2，设计 §8/§10 输出契约）

在后端运行时执行，防止：
- 结果重复：已推前端查询结果表后，最终回答又输出 Markdown 明细表；
- 无证据结论：结论超出 SQL 结果可支撑范围（v1 只做基础校验：是否引用 row_count/结果）。
v1 提供 validate + scrub 两个确定性函数，供 data_intelligence 最终交付阶段调用。
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Markdown 表格检测：| a | b | 行
_MD_TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)


@dataclass
class OutputCheck:
    ok: bool
    reason: str = ""
    detail_tables_found: int = 0
    scrubbed: bool = False


def count_markdown_tables(text: str) -> int:
    """统计最终回答中 Markdown 表格行数（| 分隔的连续块视为一张表）。"""
    if not text:
        return 0
    lines = [l for l in text.splitlines() if _MD_TABLE_LINE.match(l)]
    # 分隔行(|---|)也算；连续表格块按行粗计，足够 v1 判定"重复画表"
    return len(lines)


def validate_final_output(final_answer: str, *, result_available_for_ui: bool,
                          row_count: Any = None,
                          forbid_markdown_detail_table: bool = True) -> OutputCheck:
    """校验最终回答是否符合输出契约。

    - 技能声明 `output.forbid_markdown_detail_table=true` 且完整数据已推前端时，
      最终回答不应再画 Markdown 明细表（distribution-overload 硬规则第 2 条）；
    - 技能声明 `forbid_markdown_detail_table=false`（如 project-lifecycle-cost 跨源
      由答案呈现汇总表）时，不剥离其答案表格；
    - 有 row_count 时，回答应引用总数（仅提示性，不强制）。
    """
    n = count_markdown_tables(final_answer or "")
    if forbid_markdown_detail_table and result_available_for_ui and n > 0:
        return OutputCheck(
            ok=False, detail_tables_found=n,
            reason=f"完整数据已推前端查询结果表，最终回答不应再输出 Markdown 明细表（发现 {n} 行表格）。",
        )
    return OutputCheck(
        ok=True, detail_tables_found=n,
        reason=(f"输出契约通过（result_available_for_ui={result_available_for_ui}, "
                f"forbid_markdown_detail_table={forbid_markdown_detail_table}, 表格行={n}）"),
    )


def scrub_markdown_tables(final_answer: str) -> str:
    """从最终回答中移除 Markdown 表格块（前端已唯一展示完整数据），返回清洗后文本。"""
    if not final_answer:
        return final_answer
    lines = final_answer.splitlines()
    out: List[str] = []
    in_block = False
    for ln in lines:
        is_tbl = bool(_MD_TABLE_LINE.match(ln))
        if is_tbl:
            in_block = True
            continue
        if in_block:
            # 表格后第一个非空普通行 -> 加分隔注记
            if ln.strip():
                out.append("（完整明细见下方查询结果表）")
            in_block = False
        out.append(ln)
    return "\n".join(out)
