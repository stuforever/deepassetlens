# -*- coding: utf-8 -*-
"""书籍上下文 PG 版（切换 R6-b）——vendor sishu_full/book/context.py 的平台重写。

数据源=平台建书引擎产物（sishu_books/sishu_book_spines/sishu_book_pages/
sishu_book_blocks，sishu_data.book_gen 单轨 PG）；签名与返回（BookContextResult：
text/references/warnings）与 vendor 版 1:1，序列化文本格式对齐（## Page:/###
Block:/Learning objectives），消费方（source_inventory/turn_runtime 的书引用
上下文注入）零感知换芯。提示词纪律不涉本件（纯数据序列化）。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

from sqlalchemy import text

from app.services.sishu_data.pg import engine

DEFAULT_MAX_CONTEXT_CHARS = 32_000
DEFAULT_MAX_PAGE_CHARS = 12_000
DEFAULT_MAX_BLOCK_CHARS = 4_000

_THINK_RE = re.compile(r"<think\b[^>]*>.*?</think>", re.IGNORECASE | re.DOTALL)


@dataclass(frozen=True)
class NormalizedBookReference:
    """One selected book with the page ids that should be sent to chat."""

    book_id: str
    page_ids: List[str]

    def model_dump(self) -> Dict[str, Any]:
        return {"book_id": self.book_id, "page_ids": list(self.page_ids)}


@dataclass
class BookContextResult:
    """Serialized book context plus non-fatal issues encountered while loading."""

    text: str = ""
    references: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def normalize_book_references(value: Any) -> List[NormalizedBookReference]:
    """Validate and de-duplicate the public ``book_references`` payload."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    refs: List[NormalizedBookReference] = []
    seen_books: set = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        book_id = str(item.get("book_id") or "").strip()
        raw_page_ids = item.get("page_ids") or []
        if not book_id or not isinstance(raw_page_ids, Sequence) \
                or isinstance(raw_page_ids, (str, bytes, bytearray)):
            continue
        page_ids: List[str] = []
        seen_pages: set = set()
        for raw_page_id in raw_page_ids:
            page_id = str(raw_page_id or "").strip()
            if not page_id or page_id in seen_pages:
                continue
            seen_pages.add(page_id)
            page_ids.append(page_id)
        if book_id in seen_books:
            existing = next((r for r in refs if r.book_id == book_id), None)
            if existing is not None:
                for page_id in page_ids:
                    if page_id not in existing.page_ids:
                        existing.page_ids.append(page_id)
            continue
        seen_books.add(book_id)
        refs.append(NormalizedBookReference(book_id=book_id, page_ids=page_ids))
    return refs


def _clean(value: Any) -> str:
    text_ = str(value or "")
    text_ = _THINK_RE.sub("", text_)
    text_ = text_.replace("</think>", "").replace("<think>", "")
    text_ = re.sub(r"\n{3,}", "\n\n", text_)
    return text_.strip()


def _clip(value: Any, limit: int) -> str:
    text_ = _clean(value)
    if limit <= 0 or len(text_) <= limit:
        return text_
    head = max(0, limit - 40)
    return text_[:head].rstrip() + "\n...[truncated]"


def _load_book_row(c, book_id: str):
    return c.execute(text(
        "SELECT book_id, title, description, language FROM sishu_books WHERE book_id=:b"),
        {"b": book_id}).mappings().first()


def _load_spine(c, book_id: str) -> Dict[str, Any]:
    row = c.execute(text("SELECT spine FROM sishu_book_spines WHERE book_id=:b"),
                    {"b": book_id}).mappings().first()
    spine = (row or {}).get("spine")
    chapters = {}
    if isinstance(spine, dict):
        for ch in spine.get("chapters") or []:
            if isinstance(ch, dict) and ch.get("id"):
                chapters[str(ch["id"])] = ch
    return chapters


def _load_page(c, book_id: str, page_id: str):
    return c.execute(text(
        "SELECT page_id, title, payload FROM sishu_book_pages "
        "WHERE book_id=:b AND (page_id=:p OR payload->>'id'=:p)"),
        {"b": book_id, "p": page_id}).mappings().first()


def _load_blocks(c, page_id: str) -> List[Dict[str, Any]]:
    rows = c.execute(text(
        "SELECT block_type, payload FROM sishu_book_blocks WHERE page_id=:p "
        "ORDER BY COALESCE((payload->>'order')::int, 0)"), {"p": page_id}).mappings().all()
    out = []
    for r in rows:
        payload = r["payload"] if isinstance(r["payload"], dict) else {}
        out.append({"type": str(r["block_type"] or payload.get("type") or ""),
                    "status": str(payload.get("status") or ""),
                    "title": payload.get("title") or "",
                    "payload": payload.get("payload") if isinstance(payload.get("payload"), dict) else payload})
    return out


def _serialize_book_header(book_row) -> str:
    lines = [f"# Book: {_clean(book_row['title']) or book_row['book_id']}"]
    if book_row["description"]:
        lines.append(f"Description: {_clip(_clean(book_row['description']), 800)}")
    if book_row["language"]:
        lines.append(f"Language: {_clean(book_row['language'])}")
    return "\n".join(lines)


def _join_text_fields(payload: Dict[str, Any], keys: Sequence[str]) -> str:
    return "\n".join(t for k in keys if (t := _clean(payload.get(k))))


def _serialize_block(block: Dict[str, Any], *, block_char_limit: int) -> str:
    btype = _clean(block.get("type"))
    status = _clean(block.get("status"))
    if status == "hidden":
        return ""
    heading = f"### Block: {_clean(block.get('title')) or btype}"
    if btype:
        heading += f" ({btype})"
    payload = block.get("payload") or {}
    if status and status != "ready":
        details = [heading, f"Status: {status}"]
        if payload.get("error"):
            details.append(f"Error: {_clip(payload.get('error'), 500)}")
        return "\n".join(details)
    # 主文提取（常用类型的主文本位；其余走安全摘要）
    main = _join_text_fields(payload, ("content", "body", "text", "markdown", "intro"))
    if not main and btype == "quiz":
        main = _join_text_fields(payload, ("topic", "question", "explanation"))
    if not main:
        parts = [_join_text_fields(payload, ("description", "summary", "caption", "label"))]
        for k in ("code",):
            if v := _clean(payload.get(k)):
                parts.append(f"Code:\n{_clip(v, 1200)}")
        key_points = payload.get("key_points")
        if isinstance(key_points, list):
            parts.extend(f"- {_clean(x)}" for x in key_points[:8] if _clean(x))
        main = "\n".join(p for p in parts if p)
    if not main:
        return ""
    return _clip(f"{heading}\n{main}", block_char_limit)


def _serialize_page(*, page_row, chapter: Dict[str, Any] | None, block_texts: List[str],
                    page_char_limit: int) -> str:
    payload = page_row["payload"] if isinstance(page_row["payload"], dict) else {}
    lines = [f"## Page: {_clean(page_row['title']) or page_row['page_id']}"]
    chapter_title = _clean(chapter.get("title")) if chapter else ""
    if chapter_title:
        lines.append(f"Chapter: {chapter_title}")
    if chapter and chapter.get("summary"):
        lines.append(f"Chapter summary: {_clip(chapter.get('summary'), 1200)}")
    objectives = payload.get("learning_objectives") or (chapter or {}).get("learning_objectives") or []
    if isinstance(objectives, list) and objectives:
        lines.append("Learning objectives:")
        lines.extend(f"- {_clip(obj, 300)}" for obj in objectives if _clean(obj))
    if payload.get("status"):
        lines.append(f"Page status: {_clean(payload.get('status'))}")
    if block_texts:
        lines.append("Page content:")
        lines.extend(block_texts)
    if payload.get("error"):
        lines.append(f"Page error: {_clip(payload.get('error'), 600)}")
    return _clip("\n".join(lines), page_char_limit)


def build_book_context(
    book_references: Any,
    *,
    max_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
    page_char_limit: int = DEFAULT_MAX_PAGE_CHARS,
    block_char_limit: int = DEFAULT_MAX_BLOCK_CHARS,
) -> BookContextResult:
    """Load selected book pages (PG 平台书) and serialize them into compact LLM context."""
    refs = normalize_book_references(book_references)
    if not refs:
        return BookContextResult()
    warnings: List[str] = []
    sections: List[str] = []
    with engine.connect() as c:
        for ref in refs:
            book_row = _load_book_row(c, ref.book_id)
            if book_row is None:
                warnings.append(f"book_not_found:{ref.book_id}")
                continue
            chapters = _load_spine(c, ref.book_id)
            page_sections: List[str] = []
            for page_id in ref.page_ids:
                page_row = _load_page(c, ref.book_id, page_id)
                if page_row is None:
                    warnings.append(f"page_not_found:{ref.book_id}:{page_id}")
                    continue
                payload = page_row["payload"] if isinstance(page_row["payload"], dict) else {}
                chapter = chapters.get(str(payload.get("chapter_id") or ""))
                inline_blocks = payload.get("blocks") if isinstance(payload.get("blocks"), list) else []
                block_texts: List[str] = []
                if inline_blocks:
                    block_texts = [
                        s for b in inline_blocks
                        if isinstance(b, dict)
                        and (s := _serialize_block(
                            {"type": b.get("type") or "", "status": b.get("status") or "",
                             "title": b.get("title") or "",
                             "payload": b.get("payload") if isinstance(b.get("payload"), dict) else b},
                            block_char_limit=block_char_limit))
                    ]
                else:
                    # 页 payload 无内联块（生成中/换轨页）——从 sishu_book_blocks 表取
                    block_texts = [
                        s for b in _load_blocks(c, page_row["page_id"])
                        if (s := _serialize_block(b, block_char_limit=block_char_limit))
                    ]
                    if not block_texts:
                        warnings.append(f"page_empty:{ref.book_id}:{page_id}")
                page_text = _serialize_page(
                    page_row=page_row, chapter=chapter, block_texts=block_texts,
                    page_char_limit=page_char_limit)
                if page_text:
                    page_sections.append(page_text)
            if page_sections:
                sections.append(_serialize_book_header(book_row) + "\n\n" + "\n\n".join(page_sections))
    body = _clip("\n\n---\n\n".join(sections), max_chars)
    return BookContextResult(text=body, references=[r.model_dump() for r in refs], warnings=warnings)
