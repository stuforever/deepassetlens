# -*- coding: utf-8 -*-
"""三轨M13(批7) 7.1：book REST CRUD PG 实现——vendor book.py 端点面 1:1（同路径同形状）。

数据源=PG sishu_books/sishu_book_spines/sishu_book_pages/sishu_book_blocks/sishu_book_progress/
sishu_book_logs/sishu_book_inputs（批5 book_gen 同族表——读面直 SQL，写操作仍走
book_gen 编排/SSE，本件只承接读+删+健康+refresh-fingerprints 等非生成面）。
执法=require_expert 全挂（v4_acl_map：book 域=use——SISHU_ROUTER_DEPS 统一注入）。
"""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

from app.services.sishu_data.pg import engine

router = APIRouter()


def _rows(sql: str, params: dict | None = None):
    with engine.connect() as c:
        return c.execute(text(sql), params or {}).mappings().all()


def _one(sql: str, params: dict | None = None):
    rows = _rows(sql, params)
    return rows[0] if rows else None


@router.get("/health")
def book_health():
    return {"ok": True, "engine": "pg"}


@router.get("/books")
def list_books():
    rows = _rows("SELECT book_id, title, manifest, status, created_at, updated_at FROM sishu_books ORDER BY updated_at DESC")
    return {"books": [
        {
            "id": r["book_id"],
            "title": r["title"],
            "status": r["status"] or "unknown",
            "metadata": r["manifest"] or {},
            "page_count": (r["manifest"] or {}).get("page_count", 0),
            "chapter_count": (r["manifest"] or {}).get("chapter_count", 0),
            "created_at": str(r["created_at"]) if r["created_at"] else None,
            "updated_at": str(r["updated_at"]) if r["updated_at"] else None,
        }
        for r in rows
    ]}


@router.get("/books/{book_id}")
def get_book(book_id: str):
    r = _one("SELECT book_id, title, manifest, status, created_at, updated_at FROM sishu_books WHERE book_id=:b", {"b": book_id})
    if not r:
        raise HTTPException(404, "book 不存在")
    pages = _rows("SELECT page_id FROM sishu_book_pages WHERE book_id=:b", {"b": book_id})
    spine = _one("SELECT spine FROM sishu_book_spines WHERE book_id=:b", {"b": book_id})
    manifest = r["manifest"] or {}
    chapters = ((spine or {}).get("spine") or {}).get("chapters") or []
    return {
        "book": {
            "id": r["book_id"], "title": r["title"], "status": r["status"] or "unknown",
            "metadata": manifest,
            "page_count": len(pages),
            "chapter_count": manifest.get("chapter_count", len(chapters)),
            "created_at": str(r["created_at"]) if r["created_at"] else None,
            "updated_at": str(r["updated_at"]) if r["updated_at"] else None,
        },
        "spine": (spine or {}).get("spine") or {},
        "pages": [{"id": p["page_id"]} for p in pages],
    }


@router.get("/books/{book_id}/spine")
def get_spine(book_id: str):
    r = _one("SELECT spine FROM sishu_book_spines WHERE book_id=:b", {"b": book_id})
    if not r:
        raise HTTPException(404, "spine 不存在")
    return r["spine"] or {}


@router.get("/books/{book_id}/pages/{page_id}")
def get_page(book_id: str, page_id: str):
    r = _one("SELECT payload FROM sishu_book_pages WHERE book_id=:b AND page_id=:p",
             {"b": book_id, "p": page_id})
    if not r:
        raise HTTPException(404, "page 不存在")
    blocks = _rows("SELECT payload FROM sishu_book_blocks WHERE page_id=:p ORDER BY created_at",
                   {"p": page_id})
    page = dict(r["payload"] or {})
    page["blocks"] = [b["payload"] for b in blocks]
    return page


@router.delete("/books/{book_id}")
def delete_book(book_id: str):
    with engine.begin() as c:
        n = c.execute(text("DELETE FROM sishu_books WHERE book_id=:b"), {"b": book_id}).rowcount
    if not n:
        raise HTTPException(404, "book 不存在")
    return {"deleted": True}  # 子表 FK ON DELETE CASCADE 随主行清理


@router.get("/books/{book_id}/health")
def book_health_detail(book_id: str):
    r = _one("SELECT status FROM sishu_books WHERE book_id=:b", {"b": book_id})
    if not r:
        raise HTTPException(404, "book 不存在")
    return {"ok": True, "status": r["status"]}


@router.post("/books/{book_id}/refresh-fingerprints")
def refresh_fingerprints(book_id: str):
    r = _one("SELECT manifest FROM sishu_books WHERE book_id=:b", {"b": book_id})
    if not r:
        raise HTTPException(404, "book 不存在")
    manifest = r["manifest"] or {}
    manifest["kb_fingerprints"] = manifest.get("kb_fingerprints") or {}
    manifest["stale_page_ids"] = []
    with engine.begin() as c:
        c.execute(text("UPDATE sishu_books SET manifest=CAST(:m AS JSONB), updated_at=now() WHERE book_id=:b"),
                  {"m": json.dumps(manifest, ensure_ascii=False), "b": book_id})
    return {"ok": True, "refreshed": 0}
