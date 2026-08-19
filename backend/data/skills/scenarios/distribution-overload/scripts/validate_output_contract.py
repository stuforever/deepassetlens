#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""validate_output_contract.py — 最终回答输出契约校验脚本（单表改造配套）。

检查最终回答文本是否符合产品输出契约：
  1. 不含 GFM Markdown 明细表（`| 列 |` 表头 + `|---|` 分隔行的表格）——原始明细只由前端查询结果表唯一展示；
  2. 无"全部/所有 X"类无证据全量结论：
     - 只对 row_count 允许全量结论（如"共 101 条"）；
     - 行内字段结论（单路供电/状态正常/10kV 等）必须带"样本显示/样本内"限定词；
     - "全部正常 / 全部单路供电 / 所有 X 均 Y"类结论必须由 SQL 显式聚合统计（COUNT/GROUP BY/聚合/统计）提供证据。

用法：
    python validate_output_contract.py < final_answer.txt      # 从 stdin 读
    python validate_output_contract.py --file final_answer.md  # 从文件读
退出码：0=通过，1=未通过。

此脚本为可执行校验工具（可挂 CI/手工验收），不参与 Agent 运行时。
"""
from __future__ import annotations

import re
import sys

# 1) GFM 表格检测：`|` 开头行 + 紧随其后的 `|---|` 分隔行（支持多列 / `:---:` 对齐）
_GFM_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
_GFM_SEP_RE = re.compile(r"^\s*\|?\s*(:?-+:?\s*\|?\s*)+\s*$")
# 2) 全量结论模式（行内字段级别的"全部/所有/均"结论）。
#    分两类状态词：强状态词（形容词性，紧跟"全部/所有"）与全部状态词（用于"全部 X 均为 Y"结构）。
#    "全部用电户/全部台区"这类名词短语不是结论，不得误报。
_STATE_WORDS_STRONG = "正常|在运|单路|多路|达标|异常|在用|绿色|在线|离线"
_STATE_WORDS_ALL = "正常|在运|单路|多路|用电|低压|高压|中压|售电|在用|达标|异常|绿色|在线|离线"
_FULL_CONCL_PATTERNS = [
    # 全部/所有/每个 + 强状态词（形容词紧跟，如"全部正常""所有台区单路"）
    re.compile(r"(?:全部|所有|每个|任一)\s*(?:" + _STATE_WORDS_STRONG + r")"),
    # 全部/所有 + 名词短语 + 均为/都是/均/都 + 任意状态词（如"全部台区均为单路""所有客户都正常"）
    re.compile(r"(?:全部|所有|每个|任一)\s*\S{0,10}\s*(?:均为|都是|均|都)\s*(?:" + _STATE_WORDS_ALL + r")"),
    # 名词 + 均/都为 + 状态词（如"客户状态均正常"，无"全部/所有"前缀也视为全量断言）
    re.compile(r"\S{0,10}(?:均|都)\s*(?:为|是)?\s*(?:" + _STATE_WORDS_ALL + r")"),
]
# 限定词：行内字段结论带"样本"限定才允许
_QUALIFIER_RE = re.compile(r"样本显示|样本内|样本中|前\s*\d+\s*行样本")
# 聚合统计证据：全量结论必须有 SQL 聚合依据
_EVIDENCE_RE = re.compile(r"COUNT\s*\(|GROUP\s+BY|聚合|统计|汇总")


def _strip_gfm_table(text: str) -> tuple[str, bool]:
    """去掉 GFM 表格行（表头+分隔+数据行）。返回 (剩余文本, 是否发现表格)。"""
    lines = text.splitlines()
    kept: list[str] = []
    in_table = False
    found_table = False
    for i, line in enumerate(lines):
        if _GFM_TABLE_RE.match(line):
            # 下一行是分隔行 -> 确认进入表格
            if i + 1 < len(lines) and _GFM_SEP_RE.match(lines[i + 1].strip()):
                in_table = True
                found_table = True
                continue
            if in_table:
                found_table = True
                continue
        else:
            in_table = False
        kept.append(line)
    return "\n".join(kept), found_table


def validate(text: str) -> list[str]:
    """校验最终回答文本，返回问题列表（空列表=通过）。"""
    problems: list[str] = []

    stripped, has_table = _strip_gfm_table(text)
    if has_table:
        problems.append("发现 GFM Markdown 明细表（原始明细应只由前端查询结果表唯一展示）")

    for lineno, line in enumerate(stripped.splitlines(), 1):
        # 汇总本行所有模式命中的全量结论，去子串重复，保留最长匹配
        matches = []
        for pat in _FULL_CONCL_PATTERNS:
            for m in pat.finditer(line):
                matches.append(m.group(0).strip())
        unique: list[str] = []
        for g in matches:
            if not any(g in u for u in unique):
                unique.append(g)
        for g in unique:
            m_start = line.find(g)
            # 取匹配词所在语句片段判断是否带限定/证据
            segment = line[max(0, m_start - 20): m_start + len(g) + 20]
            if _QUALIFIER_RE.search(segment) or _EVIDENCE_RE.search(segment):
                continue
            problems.append(
                f"第 {lineno} 行：无证据全量结论「{g}」"
                f"（行内字段只能说'样本显示'；'全部 X'类结论需 SQL 聚合统计证据）"
            )
    return problems


def main(argv: list[str]) -> int:
    text = ""
    if "--file" in argv:
        idx = argv.index("--file")
        if idx + 1 >= len(argv):
            print("用法：--file <path> 或从 stdin 传入文本", file=sys.stderr)
            return 2
        with open(argv[idx + 1], encoding="utf-8") as f:
            text = f.read()
    else:
        text = sys.stdin.read()

    problems = validate(text)
    if problems:
        print("输出契约校验未通过：")
        for p in problems:
            print("  ✗", p)
        return 1
    print("输出契约校验通过：无 GFM 明细表、无无证据全量结论。")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
