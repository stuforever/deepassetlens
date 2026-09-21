"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import io
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.sishu_full.learning.tab_export.model import ExportDoc, Section, format_answer

__all__ = ["render_pdf"]

_CID_FONT = "STSong-Light"


def _ensure_cid_font() -> None:
    """幂等注册内置 CID 中文字体（重复注册会抛错，先查再注册）。"""
    try:
        pdfmetrics.getFont(_CID_FONT)
    except Exception:  # noqa: BLE001 — 未注册时 getFont 抛 KeyError
        pdfmetrics.registerFont(UnicodeCIDFont(_CID_FONT))


def _styles() -> dict[str, ParagraphStyle]:
    base = dict(fontName=_CID_FONT, textColor="#1a1a1a")
    return {
        "title": ParagraphStyle("doc-title", fontSize=16, leading=22, spaceAfter=4, **base),
        "meta": ParagraphStyle("doc-meta", fontSize=9, leading=13, textColor="#555555", fontName=_CID_FONT),
        "heading": ParagraphStyle("sec-heading", fontSize=12.5, leading=17, spaceBefore=10, spaceAfter=4, **base),
        "body": ParagraphStyle("doc-body", fontSize=10.5, leading=15.5, spaceAfter=3, **base),
        "list": ParagraphStyle("doc-list", fontSize=10.5, leading=15.5, **base),
        "qask": ParagraphStyle("doc-qask", fontSize=10.5, leading=15.5, spaceBefore=5, **base),
        "qwhy": ParagraphStyle("doc-qwhy", fontSize=9.5, leading=13.5, textColor="#666666", fontName=_CID_FONT),
    }


def _table_flow(table: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list:
    headers = [str(h) for h in table.get("headers") or []]
    rows = [[str(c) for c in (r or [])] for r in table.get("rows") or []]
    if not headers and not rows:
        return []
    data = [headers] + rows if headers else rows
    flow_table = Table(data, colWidths=None, hAlign="LEFT")
    style = [
        ("GRID", (0, 0), (-1, -1), 0.5, "#bbbbbb"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if headers:
        style.append(("BACKGROUND", (0, 0), (-1, 0), "#efefef"))
    flow_table.setStyle(TableStyle(style))
    return [flow_table, Spacer(1, 3 * mm)]


def _section_flow(section: Section, styles: dict[str, ParagraphStyle]) -> list:
    flows: list = []
    if section.heading:
        flows.append(Paragraph(section.heading, styles["heading"]))
    for text in section.paragraphs:
        flows.append(Paragraph(str(text), styles["body"]))
    if section.list_items:
        flows.append(ListFlowable(
            [ListItem(Paragraph(str(item), styles["list"]), leftIndent=16) for item in section.list_items],
            bulletType="bullet", start="•",
        ))
        flows.append(Spacer(1, 2 * mm))
    if section.table:
        flows.extend(_table_flow(section.table, styles))
    for i, q in enumerate(section.questions or [], start=1):
        ask = str(q.get("ask", ""))
        flows.append(Paragraph(f"{i}. {ask}", styles["qask"]))
        options = q.get("options") or []
        for j, opt in enumerate(options):
            flows.append(Paragraph(f"{'ABCDEFGH'[j] if j < 8 else j}. {opt}", styles["list"]))
        # 审查 R1-建议1：填空/简答题（无 options）也渲染答案——
        # format_answer 统一处理 int/str/list，无可展示答案返回 None
        answer_label = format_answer(q.get("answer"))
        if answer_label is not None:
            flows.append(Paragraph(f"答案：{answer_label}", styles["list"]))
        why = q.get("why")
        if why:
            flows.append(Paragraph(f"解析：{why}", styles["qwhy"]))
    return flows


def render_pdf(doc: ExportDoc) -> bytes:
    """ExportDoc → PDF 字节流（b"%PDF-" 文件头）。"""
    _ensure_cid_font()
    styles = _styles()
    buf = io.BytesIO()
    pdf_doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=16 * mm, bottomMargin=16 * mm,
        title=doc.title or "DeepTutor Export",
    )
    flows: list = []
    if doc.title:
        flows.append(Paragraph(doc.title, styles["title"]))
    for m in doc.meta or []:
        flows.append(Paragraph(f"{m.get('label', '')}：{m.get('value', '')}", styles["meta"]))
    if doc.title or doc.meta:
        flows.append(Spacer(1, 3 * mm))
    for section in doc.sections or []:
        flows.extend(_section_flow(section, styles))
        flows.append(Spacer(1, 2 * mm))
    pdf_doc.build(flows or [Paragraph("", styles["body"])])
    return buf.getvalue()
