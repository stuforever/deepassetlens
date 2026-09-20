# -*- coding: utf-8 -*-
"""v4批5 5.1：平台建书引擎——PG sishu_book_* 单轨（E-25 收口：vendor BookEngine 清零）。

帧契约（前端零改）：yield {"ws_event": {...}} / {"ws_result": {...}}——
ws_event=vendor BookStream.book_event 同型（PROGRESS 通道 content=kind，
metadata={kind, **data}；kind ∈ proposal_ready/spine_ready/page_planned/
block_ready/block_error/page_compiled）；ws_result=vendor WS handler 同款形状。
LLM=complete(parts) 注入（编排层闭包 _agent_text——agent 循环唯一引擎，§2.1）。
产物=PG upsert（sishu_books/sishu_book_spines/sishu_book_pages/sishu_book_blocks/
sishu_book_progress/sishu_book_logs）。"""
import json
import time
import uuid
from typing import Any, AsyncGenerator, Callable

from sqlalchemy import text

from .pg import engine


def _now() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


_BOOK_PROPOSAL_DIRECTIVE = (
    "[book-create]\n你是建书规划器。根据用户意图与素材产出书籍提案，只输出 JSON：\n"
    '{"title": "...", "description": "...", "scope": "...", "target_level": "introductory|intermediate|advanced",'
    ' "estimated_chapters": N, "rationale": "..."}\n')
_BOOK_SPINE_DIRECTIVE = (
    "[book-spine]\n你是书籍骨架设计师。依据提案产出全书章节骨架，只输出 JSON：\n"
    '{"chapters": [{"id": "ch_x1", "title": "...", "learning_objectives": ["..."],'
    ' "content_type": "theory", "summary": "...", "order": 0}]}'
    "\n章节顺序即学习顺序；id 用 ch_ 前缀自拟且唯一。\n")
_BOOK_PAGE_PLAN_DIRECTIVE = (
    "[book-page-plan]\n你是页面规划器。为该章产出单页计划，只输出 JSON：\n"
    '{"title": "...", "learning_objectives": ["..."], "content_type": "theory"}\n')
_BOOK_PAGE_COMPILE_DIRECTIVE = (
    "[book-compile]\n你是书籍页编译器。按页计划与章节摘要产出该页块序列，只输出 JSON：\n"
    '{"blocks": [{"type": "text|section|callout|quiz|code|figure|timeline|flash_cards|deep_dive|concept_graph|user_note|placeholder",'
    ' "title": "...", "payload": {"text": "..."} 或 {"items": [...]} 等按类型自洽}]}\n'
    "text/section 块 payload={\"text\": \"markdown 正文\"}；quiz 块 payload={\"question\":...,\"options\":[...],\"answer\":...,\"explanation\":...}；"
    "每页 4-8 个块，正文用中文。\n")
_BOOK_BLOCK_REGEN_DIRECTIVE = (
    "[book-block-regen]\n你是块再生成器。按块类型与原内容重生成该块，只输出 JSON：\n"
    '{"type": "...", "title": "...", "payload": {...}}\n')


def _extract_json(raw: str) -> dict:
    t = raw[raw.find("{"):]
    obj, _ = json.JSONDecoder().raw_decode(t)
    return obj


def _frame(kind: str, data: dict, stage: str) -> dict:
    return {"ws_event": {"type": "progress", "source": "book", "stage": stage,
                          "content": kind, "metadata": {"kind": kind, **data}}}


async def _load_book(book_id: str) -> dict | None:
    with engine.connect() as c:
        row = c.execute(text(
            "SELECT book_id, title, description, language, status, manifest, created_at, updated_at "
            "FROM sishu_books WHERE book_id=:b"), {"b": book_id}).fetchone()
    if not row:
        return None
    manifest = row[5] or {}
    return {"id": row[0], "title": row[1], "description": row[2] or "",
            "status": row[4], "proposal": manifest.get("proposal"),
            "knowledge_bases": manifest.get("knowledge_bases") or [],
            "language": row[3], "page_count": manifest.get("page_count", 0),
            "created_at": row[6].timestamp() if row[6] else _now(),
            "updated_at": row[7].timestamp() if row[7] else _now()}


async def _save_book(book: dict) -> None:
    manifest = {"proposal": book.get("proposal"),
                "knowledge_bases": book.get("knowledge_bases") or [],
                "page_count": book.get("page_count", 0)}
    with engine.begin() as c:
        c.execute(text("""
            INSERT INTO sishu_books (book_id, title, description, language, status, manifest, created_at, updated_at)
            VALUES (:b, :t, :d, :l, :s, CAST(:m AS JSONB), COALESCE(:ca, now()), now())
            ON CONFLICT (book_id) DO UPDATE SET title=:t, description=:d, language=:l,
              status=:s, manifest=CAST(:m AS JSONB), updated_at=now()"""),
            {"b": book["id"], "t": book.get("title", ""), "d": book.get("description", ""),
             "l": book.get("language", "zh"), "s": book.get("status", ""),
             "m": json.dumps(manifest, ensure_ascii=False),
             "ca": None})


async def _save_spine(book_id: str, spine: dict) -> None:
    with engine.begin() as c:
        c.execute(text("""
            INSERT INTO sishu_book_spines (book_id, spine, updated_at)
            VALUES (:b, CAST(:s AS JSONB), now())
            ON CONFLICT (book_id) DO UPDATE SET spine=CAST(:s AS JSONB), updated_at=now()"""),
            {"b": book_id, "s": json.dumps(spine, ensure_ascii=False)})


async def _load_spine(book_id: str) -> dict | None:
    with engine.connect() as c:
        row = c.execute(text("SELECT spine FROM sishu_book_spines WHERE book_id=:b"),
                        {"b": book_id}).fetchone()
    return row[0] if row else None


def _page_dict(book_id: str, chapter: dict, plan: dict, blocks: list[dict], order: int) -> dict:
    return {"id": _new_id("pg"), "book_id": book_id, "chapter_id": chapter.get("id", ""),
            "title": plan.get("title") or chapter.get("title", ""),
            "learning_objectives": plan.get("learning_objectives") or [],
            "content_type": plan.get("content_type") or "theory",
            "status": "compiled", "order": order, "blocks": blocks,
            "links": [], "parent_page_id": "", "error": ""}


async def _save_page(book_id: str, page: dict) -> None:
    with engine.begin() as c:
        c.execute(text("""
            INSERT INTO sishu_book_pages (page_id, book_id, page_no, title, payload, created_at, updated_at)
            VALUES (:p, :b, :n, :t, CAST(:pl AS JSONB), now(), now())
            ON CONFLICT (page_id) DO UPDATE SET title=:t, payload=CAST(:pl AS JSONB), updated_at=now()"""),
            {"p": page["id"], "b": book_id, "n": page.get("order", 0),
             "t": page.get("title", ""), "pl": json.dumps(page, ensure_ascii=False)})
        for blk in page.get("blocks", []):
            c.execute(text("""
                INSERT INTO sishu_book_blocks (block_id, page_id, block_type, payload, created_at, updated_at)
                VALUES (:i, :p, :t, CAST(:pl AS JSONB), now(), now())
                ON CONFLICT (block_id) DO UPDATE SET block_type=:t, payload=CAST(:pl AS JSONB), updated_at=now()"""),
                {"i": blk.get("id") or _new_id("blk"), "p": page["id"],
                 "t": blk.get("type", "text"), "pl": json.dumps(blk, ensure_ascii=False)})


async def _save_progress(book_id: str, data: dict) -> None:
    with engine.begin() as c:
        c.execute(text("""
            INSERT INTO sishu_book_progress (book_id, payload, updated_at)
            VALUES (:b, CAST(:p AS JSONB), now())
            ON CONFLICT (book_id) DO UPDATE SET payload=CAST(:p AS JSONB), updated_at=now()"""),
            {"b": book_id, "p": json.dumps(data, ensure_ascii=False)})


async def _log(book_id: str, content: str) -> None:
    with engine.begin() as c:
        c.execute(text("INSERT INTO sishu_book_logs (book_id, content, created_at) VALUES (:b, :c, now())"),
                  {"b": book_id, "c": content[:2000]})


async def book_op(req, session_id: str, turn_id: str, op: str, cfg: dict,
                  complete: Callable) -> AsyncGenerator[dict, None]:
    """平台建书 op 通道。complete(parts)->str = agent 循环闭包（编排层注入）。"""
    if op == "create":
        async for fr in _op_create(req, session_id, turn_id, cfg, complete):
            yield fr
    elif op == "confirm_proposal":
        async for fr in _op_confirm_proposal(session_id, turn_id, cfg, complete):
            yield fr
    elif op == "confirm_spine":
        async for fr in _op_confirm_spine(session_id, turn_id, cfg, complete):
            yield fr
    elif op == "compile_page":
        async for fr in _op_compile_page(session_id, turn_id, cfg, complete):
            yield fr
    elif op == "regenerate_block":
        async for fr in _op_regenerate_block(session_id, turn_id, cfg, complete):
            yield fr
    else:
        raise ValueError(f"Unknown book op: {op}")


async def _op_create(req, session_id, turn_id, cfg, complete):
    raw = await complete([_BOOK_PROPOSAL_DIRECTIVE,
                          f"[用户意图]\n{cfg.get('user_intent') or ''}\n",
                          f"[语言] {cfg.get('language') or 'zh'}\n",
                          f"[会话选段]\n{json.dumps(cfg.get('chat_selections') or [], ensure_ascii=False)[:2000]}\n",
                          f"[知识库]\n{json.dumps(cfg.get('knowledge_bases') or [], ensure_ascii=False)[:1000]}"])
    proposal = _extract_json(raw)
    book_id = _new_id("bk")
    book = {"id": book_id, "title": proposal.get("title", ""), "description": proposal.get("description", ""),
            "status": "proposal_ready", "proposal": proposal,
            "knowledge_bases": cfg.get("knowledge_bases") or [],
            "language": str(cfg.get("language") or "zh"), "page_count": 0,
            "created_at": _now(), "updated_at": _now()}
    await _save_book(book)
    await _log(book_id, f"create: {book['title']}")
    await _save_progress(book_id, {"op": "create", "at": _now()})
    yield _frame("proposal_ready", {"book": book, "proposal": proposal}, "ideation")
    yield {"ws_result": {"type": "create_result", "book": book, "proposal": proposal}}


async def _op_confirm_proposal(session_id, turn_id, cfg, complete):
    book_id = str(cfg.get("book_id") or "")
    book = await _load_book(book_id)
    if not book:
        raise ValueError(f"book 不存在: {book_id}")
    raw = await complete([_BOOK_SPINE_DIRECTIVE,
                          f"[提案]\n{json.dumps(cfg.get('proposal') or book.get('proposal') or {}, ensure_ascii=False)[:3000]}"])
    spine_raw = _extract_json(raw)
    chapters = []
    for i, ch in enumerate(spine_raw.get("chapters") or []):
        chapters.append({"id": ch.get("id") or _new_id("ch"), "title": ch.get("title", ""),
                         "learning_objectives": ch.get("learning_objectives") or [],
                         "content_type": ch.get("content_type") or "theory",
                         "prerequisites": [], "page_ids": [],
                         "summary": ch.get("summary", ""), "order": i})
    spine = {"book_id": book_id, "chapters": chapters, "version": 1, "updated_at": _now()}
    book["status"] = "spine_ready"
    book["updated_at"] = _now()
    await _save_spine(book_id, spine)
    await _save_book(book)
    await _log(book_id, f"confirm_proposal: {len(chapters)} chapters")
    yield _frame("spine_ready", {"book": book, "spine": spine}, "spine")
    yield {"ws_result": {"type": "confirm_proposal_result", "book": book, "spine": spine}}


async def _op_confirm_spine(session_id, turn_id, cfg, complete):
    book_id = str(cfg.get("book_id") or "")
    book = await _load_book(book_id)
    if not book:
        raise ValueError(f"book 不存在: {book_id}")
    spine = cfg.get("spine") or await _load_spine(book_id)
    chapters = [c for c in (spine or {}).get("chapters", []) if isinstance(c, dict)]
    auto_compile = bool(cfg.get("auto_compile", True))
    pages: list[dict] = []
    for ci, ch in enumerate(chapters):
        plan_raw = await complete([_BOOK_PAGE_PLAN_DIRECTIVE,
                                   f"[章节]\n{json.dumps(ch, ensure_ascii=False)[:1500]}"])
        try:
            plan = _extract_json(plan_raw)
        except Exception:
            plan = {"title": ch.get("title", ""), "learning_objectives": ch.get("learning_objectives") or []}
        yield _frame("page_planned", {"book_id": book_id, "chapter_id": ch.get("id", ""),
                                      "title": plan.get("title", "")}, "page_plan")
        if not auto_compile:
            # vendor 语义对齐：auto_compile=False 仍落 pending 页记录（编译面后续 compile_page）
            page = _page_dict(book_id, ch, plan, [], ci)
            page["status"] = "pending"
            await _save_page(book_id, page)
            pages.append(page)
            continue
        yield _frame("page_planned", {"book_id": book_id, "chapter_id": ch.get("id", ""),
                                      "phase": "compiling", "title": plan.get("title", "")}, "compilation")
        blocks: list[dict] = []
        try:
            comp_raw = await complete([_BOOK_PAGE_COMPILE_DIRECTIVE,
                                       f"[章节]\n{json.dumps(ch, ensure_ascii=False)[:1500]}\n",
                                       f"[页计划]\n{json.dumps(plan, ensure_ascii=False)[:800]}"])
            comp = _extract_json(comp_raw)
            for bi, b in enumerate(comp.get("blocks") or []):
                if isinstance(b, dict) and b.get("type"):
                    blocks.append({"id": _new_id("blk"), "type": b["type"], "status": "done",
                                   "title": b.get("title", ""), "params": {},
                                   "payload": b.get("payload") or {}, "order": bi})
        except Exception as e:
            yield _frame("block_error", {"book_id": book_id, "chapter_id": ch.get("id", ""),
                                         "error": str(e)[:300]}, "block")
        page = _page_dict(book_id, ch, plan, blocks, ci)
        await _save_page(book_id, page)
        for blk in blocks:
            yield _frame("block_ready", {"book_id": book_id, "page_id": page["id"],
                                         "block_id": blk["id"], "block_type": blk["type"]}, "block")
        yield _frame("page_compiled", {"book_id": book_id, "page_id": page["id"],
                                       "chapter_id": ch.get("id", ""), "blocks": len(blocks)}, "compilation")
        pages.append(page)
    book["status"] = "compiled"
    book["page_count"] = len(pages)
    book["updated_at"] = _now()
    await _save_book(book)
    await _save_progress(book_id, {"op": "confirm_spine", "pages": len(pages), "at": _now()})
    await _log(book_id, f"confirm_spine: {len(pages)} pages compiled")
    yield {"ws_result": {"type": "confirm_spine_result", "pages": pages}}


async def _op_compile_page(session_id, turn_id, cfg, complete):
    book_id = str(cfg.get("book_id") or "")
    book = await _load_book(book_id)
    if not book:
        raise ValueError(f"book 不存在: {book_id}")
    page_id = str(cfg.get("page_id") or "")
    spine = await _load_spine(book_id)
    # 既有页（confirm_spine auto_compile=False 落的 pending 页）→ 回读定位章节
    with engine.connect() as c:
        prow = c.execute(text("SELECT payload FROM sishu_book_pages WHERE page_id=:p AND book_id=:b"),
                         {"p": page_id, "b": book_id}).fetchone()
    pending = prow[0] if prow else None
    chapter = {}
    want_ch = (pending or {}).get("chapter_id") or str(cfg.get("chapter_id") or "")
    for ch in (spine or {}).get("chapters", []):
        if ch.get("id") == want_ch:
            chapter = ch
            break
    plan = {"title": (pending or {}).get("title") or chapter.get("title", "") or f"Page {want_ch}",
            "learning_objectives": (pending or {}).get("learning_objectives") or chapter.get("learning_objectives") or []}
    comp_raw = await complete([_BOOK_PAGE_COMPILE_DIRECTIVE,
                               f"[章节]\n{json.dumps(chapter, ensure_ascii=False)[:1500]}\n",
                               f"[页计划]\n{json.dumps(plan, ensure_ascii=False)[:800]}",
                               f"[force 重编译]\n{bool(cfg.get('force', False))}"])
    comp = _extract_json(comp_raw)
    blocks = []
    for bi, b in enumerate(comp.get("blocks") or []):
        if isinstance(b, dict) and b.get("type"):
            blocks.append({"id": _new_id("blk"), "type": b["type"], "status": "done",
                           "title": b.get("title", ""), "params": {},
                           "payload": b.get("payload") or {}, "order": bi})
    page = _page_dict(book_id, chapter, plan, blocks, int((pending or {}).get("order") or chapter.get("order", 0) or 0))
    page["id"] = page_id or page["id"]
    page["chapter_id"] = want_ch
    await _save_page(book_id, page)
    for blk in blocks:
        yield _frame("block_ready", {"book_id": book_id, "page_id": page["id"],
                                     "block_id": blk["id"], "block_type": blk["type"]}, "block")
    yield _frame("page_compiled", {"book_id": book_id, "page_id": page["id"],
                                   "chapter_id": page.get("chapter_id", ""), "blocks": len(blocks)}, "compilation")
    yield {"ws_result": {"type": "compile_page_result", "page": page}}


async def _op_regenerate_block(session_id, turn_id, cfg, complete):
    book_id = str(cfg.get("book_id") or "")
    page_id = str(cfg.get("page_id") or "")
    block_id = str(cfg.get("block_id") or "")
    with engine.connect() as c:
        row = c.execute(text("SELECT payload FROM sishu_book_blocks WHERE block_id=:i"),
                        {"i": block_id}).fetchone()
    if not row:
        raise ValueError(f"block 不存在: {block_id}")
    old_block = row[0] or {}
    params_override = cfg.get("params_override") or {}
    reg_raw = await complete([_BOOK_BLOCK_REGEN_DIRECTIVE,
                              f"[原块]\n{json.dumps(old_block, ensure_ascii=False)[:1500]}\n",
                              f"[参数覆盖]\n{json.dumps(params_override, ensure_ascii=False)[:500]}"])
    reg = _extract_json(reg_raw)
    block = {**old_block, "type": reg.get("type") or old_block.get("type", "text"),
             "title": reg.get("title") or old_block.get("title", ""),
             "payload": reg.get("payload") or old_block.get("payload", {}), "status": "done"}
    with engine.begin() as c:
        c.execute(text("UPDATE sishu_book_blocks SET payload=CAST(:pl AS JSONB), updated_at=now() WHERE block_id=:i"),
                  {"pl": json.dumps(block, ensure_ascii=False), "i": block_id})
    yield _frame("block_ready", {"book_id": book_id, "page_id": page_id,
                                 "block_id": block_id, "block_type": block["type"]}, "block")
    yield {"ws_result": {"type": "regenerate_block_result", "block": block}}
