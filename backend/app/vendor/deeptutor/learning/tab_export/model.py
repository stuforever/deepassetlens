"""ExportDoc 统一文档模型（规格 §3.1）。

结构：ExportDoc(title, meta[{label, value}], sections[Section])；
Section(heading, paragraphs, list_items, table{headers, rows}, 
questions[{ask, options, answer, why}])。全部为普通 dataclass/dict，
不绑定任何渲染器——PDF（reportlab）与 DOCX（python-docx）各自消费。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["ExportDoc", "Section", "empty_doc", "format_answer"]


def format_answer(answer: Any) -> str | None:
    """题目答案 → 展示文本；无可展示答案返回 None（双渲染器共用）。

    审查 R1-建议1：填空/简答题（options 为空）的 answer 常为 str 或
    候选 list——旧守卫 ``answer is not None and options`` 把它们全部
    拦掉，家长版缺答案（判例 3 对填空子集不达）。规则：
    - int → 选择题选项字母（0-7）或原值；
    - 非空 str → 原文（去首尾空白）；
    - list → 非空元素以「 / 」连接（多候选/多空）；
    - 其余（None/空串/空表/bool）→ None。
    """
    if isinstance(answer, bool):
        return None
    if isinstance(answer, int):
        return "ABCDEFGH"[answer] if 0 <= answer < 8 else str(answer)
    if isinstance(answer, str):
        cleaned = answer.strip()
        return cleaned or None
    if isinstance(answer, (list, tuple)):
        parts = [str(a).strip() for a in answer if str(a).strip()]
        return " / ".join(parts) or None
    return None


@dataclass
class Section:
    """一个 tab 内的节：标题 + 四种内容形态（可任意组合）。"""

    heading: str = ""
    paragraphs: list[str] = field(default_factory=list)
    list_items: list[str] = field(default_factory=list)
    # 规格形态 {"headers": [...], "rows": [[...], ...]}；None = 无表格
    table: dict[str, Any] | None = None
    # 题目块 {"ask": str, "options": [str], "answer": int|None, "why": str}
    questions: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ExportDoc:
    """统一文档：标题 + meta 键值行 + 节列表。"""

    title: str = ""
    meta: list[dict[str, str]] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)


def empty_doc(title: str) -> ExportDoc:
    """空数据提示页：单节单段「本章节暂无该内容」（T15 步骤 3）。"""
    return ExportDoc(
        title=title,
        meta=[],
        sections=[Section(heading="", paragraphs=["本章节暂无该内容"])],
    )
