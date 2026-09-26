# -*- coding: utf-8 -*-
"""书籍上下文 PG 版测试（R6-b）：同签名换芯——normalize/序列化/warning 路径。"""
from __future__ import annotations

from app.services.sishu_data.book_context import (
    build_book_context,
    normalize_book_references,
)


def test_normalize_refs_dedupe():
    refs = normalize_book_references([
        {"book_id": "bk_1", "page_ids": ["p1", "p1", "p2"]},
        {"book_id": "bk_1", "page_ids": ["p3"]},
        {"book_id": "", "page_ids": ["x"]},
        "junk",
    ])
    assert len(refs) == 1
    assert refs[0].book_id == "bk_1"
    assert refs[0].page_ids == ["p1", "p2", "p3"]


def test_build_context_real_book_roundtrip():
    """真实平台书（PG 31 册）取一册两页序列化——格式与 vendor 对齐。"""
    from sqlalchemy import text
    from app.services.sishu_data.pg import engine
    with engine.connect() as c:
        row = c.execute(text(
            "SELECT b.book_id, p.page_id FROM sishu_books b "
            "JOIN sishu_book_pages p ON p.book_id=b.book_id LIMIT 1")).mappings().first()
    if not row:
        return  # 空库环境跳过
    result = build_book_context([{"book_id": row["book_id"], "page_ids": [row["page_id"]]}])
    assert result.references == [{"book_id": row["book_id"], "page_ids": [row["page_id"]]}]
    assert "## Page:" in result.text or result.warnings


def test_build_context_missing_book_warning():
    result = build_book_context([{"book_id": "bk_nonexistent_xyz", "page_ids": ["p"]}])
    assert result.text == ""
    assert result.warnings == ["book_not_found:bk_nonexistent_xyz"]
    assert result.references  # 引用回显保持
