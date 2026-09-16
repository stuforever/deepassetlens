"""Mother question (母题库) API router.

Migrated from ragflow/wrong_question_api.py. Mounted at /api/v1/mother-questions.
Reuses DeepTutor's KnowledgePoint (via knowledge_point_id) for mastery + review,
but does NOT migrate RAGFlow-dependent features (RAG explain / similar / lecture
sync / vector incremental sync) — DeepTutor's own knowledge/ RAG covers those.
"""
from __future__ import annotations

from typing import Any

import json
from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Body,
    UploadFile,
    File as FastFile,
    Header,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from deeptutor.learning.mother_question import (
    MotherQuestion,
    MotherQuestionStore,
    QuestionVariant,
    Attempt,
    _gen_id,
    _now,
)

router = APIRouter()


def _store() -> MotherQuestionStore:
    # Fresh store per request, mirroring mastery_path.get_learning_service().
    return MotherQuestionStore()


def _h5_ctx(u: str, code: str = "", x_access_code: str = ""):
    """上下文管理器：u 非空时切到 H5 用户（错题本 data-class 隔离）。

    u 可能是 Query(...) 默认对象（直接调用测试时）或空串 —— 均回退 admin。
    R1-c：带 u 时经 h5_user_guarded 统一校验访问码（?code= / X-Access-Code）。
    """
    from contextlib import nullcontext

    from deeptutor.multi_user.h5 import h5_user_guarded
    from deeptutor.multi_user.paths import user_context

    if not isinstance(u, str) or not u.strip():
        return nullcontext()
    return user_context(h5_user_guarded(u, code, x_access_code))


# --------------------------------------------------------------------------- #
# Request schemas                                                              #
# --------------------------------------------------------------------------- #

class CreateMotherRequest(BaseModel):
    title: str = Field(min_length=1)
    question_text: str = Field(min_length=1)
    subject: str = "math"
    grade: str | None = None
    category: str | None = None
    archetype_code: str | None = None
    standard_answer: str | None = None
    wrong_answer: str | None = None
    detailed_analysis: str | None = None
    note: str | None = None
    solution_steps: list[dict[str, Any]] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    difficulty: int = 3
    knowledge_point_id: str | None = None
    textbook_id: str | None = None
    chapter_id: str | None = None
    cover_image_url: str | None = None
    photo_url: str | None = None
    wrong_answer_image_url: str | None = None
    source_image_url: str | None = None
    crop_box: list[int] | None = None
    ocr_text: str | None = None
    has_checkmark: bool | None = None
    tags: list[str] = Field(default_factory=list)
    assets: list[dict[str, Any]] = Field(default_factory=list)
    wrong_reason: str | None = None
    related_lecture_doc_ids: list[str] = Field(default_factory=list)
    force: bool = False  # 跳过查重短路


class UpdateMotherRequest(BaseModel):
    title: str | None = None
    question_text: str | None = None
    subject: str | None = None
    grade: str | None = None
    category: str | None = None
    archetype_code: str | None = None
    standard_answer: str | None = None
    wrong_answer: str | None = None
    detailed_analysis: str | None = None
    note: str | None = None
    solution_steps: list[dict[str, Any]] | None = None
    key_points: list[str] | None = None
    difficulty: int | None = None
    knowledge_point_id: str | None = None
    textbook_id: str | None = None
    chapter_id: str | None = None
    cover_image_url: str | None = None
    photo_url: str | None = None
    wrong_answer_image_url: str | None = None
    source_image_url: str | None = None
    crop_box: list[int] | None = None
    ocr_text: str | None = None
    has_checkmark: bool | None = None
    tags: list[str] | None = None
    assets: list[dict[str, Any]] | None = None
    wrong_reason: str | None = None
    related_lecture_doc_ids: list[str] | None = None
    status: str | None = None


class CreateVariantRequest(BaseModel):
    question_text: str
    answer: str | None = None
    solution_steps: list[dict[str, Any]] = Field(default_factory=list)
    difficulty: int = 3
    variant_type: str | None = None
    source: str = "manual"


class UpdateVariantRequest(BaseModel):
    question_text: str | None = None
    answer: str | None = None
    solution_steps: list[dict[str, Any]] | None = None
    difficulty: int | None = None
    variant_type: str | None = None
    source: str | None = None
    status: str | None = None


class ReviewSubmitRequest(BaseModel):
    """Validated payload for both FSRS and legacy binary reviews."""

    rating: int | None = Field(default=None, ge=1, le=4)
    is_correct: bool | None = None
    variant_id: str | None = None
    user_answer: str | None = None
    time_spent: float | None = Field(default=None, ge=0)


# --------------------------------------------------------------------------- #
# Mother question CRUD                                                         #
# --------------------------------------------------------------------------- #

@router.get("")
async def list_mother_questions(
    subject: str | None = None,
    grade: str | None = None,
    category: str | None = None,
    knowledge_point_id: str | None = None,
    textbook_id: str | None = None,
    chapter_id: str | None = None,
    tag: str | None = None,
    difficulty_min: int | None = None,
    difficulty_max: int | None = None,
    keyword: str | None = None,
    status: str = "active",
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    sort_by: str = Query("create_time"),
    sort_order: str = Query("desc"),
    # W（第八篇）：统一错题本 ?u= 隔离——create 已隔离，list 补齐（否则用户存了题看不到）
    u: str = Query("", description="H5 用户标识（?u=）：错题本 data-class 隔离"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    with _h5_ctx(u, code, x_access_code):
        store = _store()
        items, total = store.list_mothers(
            subject=subject, grade=grade, category=category,
            knowledge_point_id=knowledge_point_id,
            textbook_id=textbook_id, chapter_id=chapter_id, tag=tag,
            difficulty_min=difficulty_min, difficulty_max=difficulty_max,
            keyword=keyword, status=status, start_date=start_date, end_date=end_date,
            sort_by=sort_by, sort_order=sort_order,
            page=page, page_size=page_size,
        )
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [m.model_dump(mode="json") for m in items],
        }


@router.post("", status_code=201)
async def create_mother_question(
    body: CreateMotherRequest,
    u: str = Query("", description="H5 用户标识（?u=）：错题本 data-class 隔离"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    with _h5_ctx(u, code, x_access_code):
        return await _create_mother_question_inner(body)


async def _create_mother_question_inner(body: CreateMotherRequest):
    if not body.title or not body.question_text:
        raise HTTPException(400, "title 和 question_text 必填")
    # 创建时查重短路（除非 force=True）
    if not body.force:
        from deeptutor.learning.simhash_util import compute_simhash, hamming_distance
        new_hash = compute_simhash(body.title, body.question_text)
        store = _store()
        for existing in store.list_all_mothers():
            eh = existing.simhash
            if eh is None:
                eh = compute_simhash(existing.title, existing.question_text)
            if new_hash is not None and eh is not None and hamming_distance(new_hash, eh) <= 4:
                raise HTTPException(
                    409,
                    f"查重短路：与现有母题「{existing.title}」相似（汉明距离≤4）。设 force=true 跳过。",
                )
    else:
        new_hash = None
    m = MotherQuestion(
        id=_gen_id(),
        title=body.title,
        question_text=body.question_text,
        subject=body.subject,
        grade=body.grade,
        category=body.category,
        archetype_code=body.archetype_code,
        standard_answer=body.standard_answer,
        wrong_answer=body.wrong_answer,
        detailed_analysis=body.detailed_analysis,
        note=body.note,
        solution_steps=body.solution_steps,
        key_points=body.key_points,
        difficulty=body.difficulty,
        knowledge_point_id=body.knowledge_point_id,
        textbook_id=body.textbook_id,
        chapter_id=body.chapter_id,
        cover_image_url=body.cover_image_url,
        photo_url=body.photo_url,
        wrong_answer_image_url=body.wrong_answer_image_url,
        source_image_url=body.source_image_url,
        crop_box=body.crop_box,
        ocr_text=body.ocr_text,
        has_checkmark=body.has_checkmark,
        tags=body.tags,
        assets=body.assets,
        wrong_reason=body.wrong_reason,
        related_lecture_doc_ids=body.related_lecture_doc_ids,
        simhash=new_hash,
    )
    _store().create_mother(m)
    # W5（第八篇 M16-C）：create 端点补发 mother_created 事件（周报四源分布统计）。
    # 与 _auto_capture_mother（src:practice）对齐；真实来源从 tags 的 src:* 提取。
    try:
        from deeptutor.learning.learner_profile import emit_learning_event

        _src_tags = [t for t in (body.tags or []) if str(t).startswith("src:")]
        _src = _src_tags[0].split(":", 1)[1] if _src_tags else "manual"
        emit_learning_event(
            kind="mother_created",
            payload={
                "mid": m.id,
                "title": m.title,
                "kp_id": m.knowledge_point_id or "",
                "chapter_id": m.chapter_id or "",
                "source": _src,
            },
        )
    except Exception:  # noqa: BLE001
        import logging as _logging

        _logging.getLogger(__name__).warning("emit mother_created failed", exc_info=True)
    return m.model_dump(mode="json")


@router.get("/dict")
async def get_dictionary():
    """字典 API：返回教材列表 + 章节列表 + 知识点树 + 标签，供前端下拉用。
    必须定义在 /{mid} 之前，否则 'dict' 会被当作 mid 拦截。"""
    from deeptutor.learning.curriculum import CurriculumStore
    cs = CurriculumStore()
    textbooks = cs.list_textbooks()
    chapters = cs.list_chapters()
    kps = cs.list_kps()
    tags = _store().list_all_tags()
    return {
        "textbooks": [{"id": t.id, "name": t.name, "grade": t.grade, "subject": t.subject, "version": getattr(t, "version", None)} for t in textbooks],
        "chapters": [{"id": c.id, "name": c.name, "textbook_id": c.textbook_id, "parent_id": c.parent_id} for c in chapters],
        "knowledge_points": [{"id": k.id, "name": k.name, "parent_id": k.parent_id, "subject": k.subject} for k in kps],
        "tags": tags,
        "subjects": ["math", "chinese", "english", "physics", "chemistry", "biology", "history", "geography", "politics", "other"],
    }


# 静态路径必须在 /{mid} 之前定义，否则被当作 mid 拦截
@router.get("/trash")
async def list_trash_static(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    u: str = Query("", description="H5 用户标识（?u=）：错题本 data-class 隔离"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """回收站列表（仅 status=deleted）."""
    with _h5_ctx(u, code, x_access_code):
        items, total = _store().list_trash(page=page, page_size=page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [m.model_dump(mode="json") for m in items],
    }


@router.get("/tags")
async def list_tags_static():
    """列出所有标签."""
    return {"items": _store().list_all_tags()}


@router.get("/correct-questions")
async def list_correct_questions(limit: int = Query(100, ge=1, le=500)):
    """正确题库列表（已转正确题的母题）."""
    items = _store().list_correct(limit=limit)
    return {
        "total": len(items),
        "items": [m.model_dump(mode="json") for m in items],
    }


@router.get("/analysis/by-subject")
async def by_subject_stats_static():
    """按科目聚合统计."""
    items = _store().list_all_mothers()
    agg: dict[str, dict] = {}
    for m in items:
        s = m.subject or "other"
        if s not in agg:
            agg[s] = {"subject": s, "count": 0, "mastered": 0, "reviewing": 0, "avg_difficulty": 0}
        agg[s]["count"] += 1
        if m.mastery_status == "mastered":
            agg[s]["mastered"] += 1
        elif m.mastery_status == "reviewing":
            agg[s]["reviewing"] += 1
        agg[s]["avg_difficulty"] += m.difficulty
    for s in agg:
        agg[s]["avg_difficulty"] = round(agg[s]["avg_difficulty"] / agg[s]["count"], 2) if agg[s]["count"] else 0
    items_out = sorted(agg.values(), key=lambda x: x["count"], reverse=True)
    return {"items": items_out, "total_subjects": len(items_out)}


@router.get("/analysis/retention")
async def retention_analysis_static(
    u: str = Query(""),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """整体保留率分析."""
    from deeptutor.learning.fsrs import retrievability, format_card
    import time

    with _h5_ctx(u, code, x_access_code):
        store = _store()
        rs = store._load_rs()
        items = store.list_all_mothers()
        now = time.time()
        card_list = []
        total_retention = 0.0
        reviewed_count = 0
        for m in items:
            st = rs.get(m.id)
            if st and st.get("stability") is not None:
                r = retrievability(st, now)
                card_list.append({
                    "id": m.id, "title": m.title,
                    "retention": round(r * 100, 1),
                    "stability": st.get("stability", 0),
                    "difficulty": st.get("difficulty", 0),
                    "reps": st.get("reps", 0),
                    "lapses": st.get("lapses", 0),
                    "due": st.get("due"),
                    "state": format_card(st)["state"],
                })
                total_retention += r
                reviewed_count += 1
        card_list.sort(key=lambda x: x["retention"])
        avg_retention = round(total_retention / reviewed_count * 100, 1) if reviewed_count else 0
        buckets = {"<20%": 0, "20-40%": 0, "40-60%": 0, "60-80%": 0, "80-100%": 0}
        for c in card_list:
            r = c["retention"]
            if r < 20:
                buckets["<20%"] += 1
            elif r < 40:
                buckets["20-40%"] += 1
            elif r < 60:
                buckets["40-60%"] += 1
            elif r < 80:
                buckets["60-80%"] += 1
            else:
                buckets["80-100%"] += 1
        return {
            "avg_retention": avg_retention,
            "reviewed_count": reviewed_count,
            "total_count": len(items),
            "distribution": buckets,
            "lowest_retention": card_list[:10],
        }


@router.get("/{mid}")
async def get_mother_question(mid: str):
    store = _store()
    m = store.get_mother(mid)
    if not m:
        raise HTTPException(404, "母题不存在")
    out = m.model_dump(mode="json")
    out["variants"] = [v.model_dump(mode="json") for v in store.list_variants(mid)]
    return out


@router.patch("/{mid}")
async def update_mother_question(
    mid: str,
    body: UpdateMotherRequest,
    u: str = Query("", description="H5 用户标识（?u=）：错题本 data-class 隔离"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    with _h5_ctx(u, code, x_access_code):
        patch = body.model_dump(exclude_unset=True)
        if not patch:
            raise HTTPException(400, "空更新")
        store = _store()
        current = store.get_mother(mid)
        if not current:
            raise HTTPException(404, "母题不存在")
        if "title" in patch or "question_text" in patch:
            from deeptutor.learning.simhash_util import compute_simhash
            patch["simhash"] = compute_simhash(
                patch.get("title", current.title),
                patch.get("question_text", current.question_text),
            )
        m = store.update_mother(mid, patch)
        if not m:
            raise HTTPException(404, "母题不存在")
        return m.model_dump(mode="json")


@router.delete("/{mid}")
async def delete_mother_question(
    mid: str,
    hard: bool = False,
    u: str = Query("", description="H5 用户标识（?u=）：错题本 data-class 隔离"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    with _h5_ctx(u, code, x_access_code):
        ok = _store().delete_mother(mid, hard=hard)
    if not ok:
        raise HTTPException(404, "母题不存在")
    return {"deleted": True, "mode": "hard" if hard else "soft"}


# --------------------------------------------------------------------------- #
# Note (笔记) – 轻量保存，不走完整 UpdateMotherRequest                          #
# --------------------------------------------------------------------------- #

@router.patch("/{mid}/note")
async def update_note(mid: str, body: dict = Body(...)):
    """保存学生笔记."""
    note = (body.get("note") or "").strip()
    m = _store().update_mother(mid, {"note": note})
    if not m:
        raise HTTPException(404, "母题不存在")
    return {"note": m.note}


# --------------------------------------------------------------------------- #
# 转正确题 / 相似错题 / 关联讲义                                              #
# --------------------------------------------------------------------------- #

@router.post("/{mid}/transfer-to-correct")
async def transfer_to_correct(mid: str):
    """转正确题：标记为已掌握并转入正确题库."""
    import time as _time
    m = _store().update_mother(mid, {
        "mastery_status": "mastered",
        "correct_transferred_at": _time.time(),
    })
    if not m:
        raise HTTPException(404, "母题不存在")
    return {"transferred": True, "correct_transferred_at": m.correct_transferred_at}


@router.post("/{mid}/similar")
async def find_similar(mid: str, top_k: int = Query(5, ge=1, le=20)):
    """相似错题：用 simhash 查找相似母题."""
    m = _store().get_mother(mid)
    if not m:
        raise HTTPException(404, "母题不存在")
    if m.simhash is None:
        # 如果没有 simhash，现场计算
        from deeptutor.learning.simhash_util import compute_simhash
        sh = compute_simhash(m.title, m.question_text)
        _store().update_mother(mid, {"simhash": sh})
        m = _store().get_mother(mid)
    similar = _store().find_similar(mid, top_k=top_k)
    return {"items": similar, "count": len(similar), "engine": "simhash"}


@router.post("/{mid}/lectures/{doc_id}")
async def link_lecture(mid: str, doc_id: str):
    """关联讲义：添加讲义文档ID到关联列表."""
    m = _store().get_mother(mid)
    if not m:
        raise HTTPException(404, "母题不存在")
    ids = list(m.related_lecture_doc_ids or [])
    if doc_id not in ids:
        ids.append(doc_id)
        _store().update_mother(mid, {"related_lecture_doc_ids": ids})
    return {"linked": True, "related_lecture_doc_ids": ids}


@router.delete("/{mid}/lectures/{doc_id}")
async def unlink_lecture(mid: str, doc_id: str):
    """取消关联讲义."""
    m = _store().get_mother(mid)
    if not m:
        raise HTTPException(404, "母题不存在")
    ids = [d for d in (m.related_lecture_doc_ids or []) if d != doc_id]
    _store().update_mother(mid, {"related_lecture_doc_ids": ids})
    return {"unlinked": True, "related_lecture_doc_ids": ids}


# --------------------------------------------------------------------------- #
# Variants                                                                     #
# --------------------------------------------------------------------------- #

@router.get("/{mid}/variants")
async def list_variants(mid: str, status: str = "active"):
    store = _store()
    if not store.get_mother(mid):
        raise HTTPException(404, "母题不存在")
    items = store.list_variants(mid, status=status)
    return {"items": [v.model_dump(mode="json") for v in items]}


@router.post("/{mid}/variants", status_code=201)
async def create_variant(mid: str, body: CreateVariantRequest):
    store = _store()
    if not store.get_mother(mid):
        raise HTTPException(404, "母题不存在")
    v = QuestionVariant(
        id=_gen_id(),
        mother_id=mid,
        question_text=body.question_text,
        answer=body.answer,
        solution_steps=body.solution_steps,
        difficulty=body.difficulty,
        variant_type=body.variant_type,
        source=body.source,
    )
    store.create_variant(v)
    return v.model_dump(mode="json")


@router.patch("/variants/{vid}")
async def update_variant(vid: str, body: UpdateVariantRequest):
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(400, "空更新")
    v = _store().update_variant(vid, patch)
    if not v:
        raise HTTPException(404, "变式题不存在")
    return v.model_dump(mode="json")


@router.delete("/variants/{vid}")
async def delete_variant(vid: str, hard: bool = False):
    ok = _store().delete_variant(vid, hard=hard)
    if not ok:
        raise HTTPException(404, "变式题不存在")
    return {"deleted": True, "mode": "hard" if hard else "soft"}


# --------------------------------------------------------------------------- #
# 补齐: 母题统计 / 上下文 / LLM生成变式 / 批量识别 / 批量预览 / 批量保存   #
# --------------------------------------------------------------------------- #

@router.get("/{mid}/stats")
async def mother_question_stats(mid: str):
    """单题维度统计: 变式题数/复习次数/正确率/保留率/资产数."""
    store = _store()
    m = store.get_mother(mid)
    if not m:
        raise HTTPException(404, "母题不存在")
    variants = store.list_variants(mid)
    attempts = store.list_attempts(mid, limit=500)
    att_total = len(attempts)
    correct = sum(1 for a in attempts if a.get("is_correct"))
    retention = store.get_retention(mid)
    rs = store.get_review_state(mid)
    return {
        "variant_count": len(variants),
        "asset_count": len(m.assets or []),
        "attempt_count": att_total,
        "accuracy": round(correct / att_total, 4) if att_total else None,
        "retention": round(retention, 4) if retention is not None else None,
        "review_reps": rs.get("reps", 0) if rs else 0,
        "review_lapses": rs.get("lapses", 0) if rs else 0,
        "mastery_status": m.mastery_status,
        "difficulty": m.difficulty,
    }


@router.get("/{mid}/context")
async def mother_question_context(mid: str):
    """获取母题完整上下文: 母题 + 教材 + 章节 + 知识点."""
    store = _store()
    m = store.get_mother(mid)
    if not m:
        raise HTTPException(404, "母题不存在")
    out = m.model_dump(mode="json")
    out["textbook"] = None
    out["chapter"] = None
    out["knowledge_point"] = None
    try:
        from deeptutor.learning.curriculum import CurriculumStore
        cs = CurriculumStore()
        if m.textbook_id:
            for tb in cs.list_textbooks():
                if tb.id == m.textbook_id:
                    out["textbook"] = tb.model_dump(mode="json")
                    break
        if m.chapter_id:
            for ch in cs.list_chapters():
                if ch.id == m.chapter_id:
                    out["chapter"] = ch.model_dump(mode="json")
                    break
        if m.knowledge_point_id:
            for kp in cs.list_kps():
                if kp.id == m.knowledge_point_id:
                    out["knowledge_point"] = kp.model_dump(mode="json")
                    break
    except Exception:
        pass
    return out


_GEN_VARIANTS_PROMPT = """你是一位资深数学教师。请根据给定的母题（含错因归因），生成变式题。
要求：
- 生成 2-3 道变式题，保持核心知识点不变，变换数值/情境/问法
- 每道变式题包含: question_text(题干), answer(答案), difficulty(1-5), variant_type(数值变式/情境变式/逆向变式/综合变式)
- 若提供错因，请按错因定向出题（E1 错因→出题闭环）：
  · 错因=计算错误 -> 优先数值变式（同方法改数，多练运算步骤）
  · 错因=审题 -> 优先情境变式（换生活情境，训练读题抓关键信息）
  · 错因=方法错误 -> 优先方法迁移变式（换方法路径求解）
  · 错因=知识点缺失 -> 优先基础铺垫变式（降低难度回到核心概念）
  · 错因=粗心/未归因 -> 正常综合变式
- 只返回 JSON 数组，不要 markdown
- 示例: [{"question_text":"...","answer":"...","difficulty":3,"variant_type":"数值变式"}]"""


@router.post("/{mid}/generate_variants")
async def generate_variants(mid: str, payload: dict = Body(...)):
    """LLM 自动生成变式题."""
    import urllib.request as _ur

    store = _store()
    m = store.get_mother(mid)
    if not m:
        raise HTTPException(404, "母题不存在")
    count = min(int(payload.get("count", 3)), 5)

    try:
        from deeptutor.services.llm.config import get_llm_config
        cfg = get_llm_config()
        if not cfg.api_key or cfg.api_key == "sk-placeholder":
            raise HTTPException(503, "LLM key 未配置")
        user_msg = (
            f"母题标题: {m.title}\n"
            f"题干: {m.question_text}\n"
            f"标准答案: {m.standard_answer or '无'}\n"
            f"难度: {m.difficulty}/5\n"
            f"知识点: {', '.join(m.key_points) if m.key_points else '无'}\n"
            f"错因: {m.wrong_reason or '未归因'}\n"
            f"请生成 {count} 道变式题。"
        )
        body = json.dumps({
            "model": cfg.model,
            "messages": [
                {"role": "system", "content": _GEN_VARIANTS_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": 2000, "temperature": 0.7,
        }).encode("utf-8")
        req = _ur.Request(cfg.base_url + "/chat/completions", data=body,
                          headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg.api_key}, method="POST")
        import time as _t
        from deeptutor.learning.llm_cost_log import log_llm_call
        _t0 = _t.time()
        resp = _ur.urlopen(req, timeout=60)
        data = json.loads(resp.read())
        content = data["choices"][0]["message"].get("content", "")
        _usage = data.get("usage") or {}
        log_llm_call("generate_variants", user=str(payload.get("u", "") or ""),
                     tokens_in=_usage.get("prompt_tokens", 0), tokens_out=_usage.get("completion_tokens", 0),
                     ok=True, latency_ms=int((_t.time() - _t0) * 1000), mid=mid)
        import re as _re
        match = _re.search(r'\[.*\]', content, _re.DOTALL)
        if not match:
            raise HTTPException(500, "LLM 返回格式异常")
        items = json.loads(match.group())
    except HTTPException:
        raise
    except Exception as e:
        from deeptutor.learning.llm_cost_log import log_llm_call as _ll
        _ll("generate_variants", user=str(payload.get("u", "") or ""), ok=False, error=str(e)[:120], mid=mid)
        raise HTTPException(500, f"LLM 调用失败: {e}")

    created = []
    for item in items[:count]:
        v = QuestionVariant(
            id=_gen_id(), mother_id=mid,
            question_text=item.get("question_text", ""),
            answer=item.get("answer"),
            difficulty=int(item.get("difficulty", 3)),
            variant_type=item.get("variant_type", "综合变式"),
            source="llm_gen",
        )
        store.create_variant(v)
        created.append(v.model_dump(mode="json"))
    return {"generated": len(created), "items": created}


# --------------------------------------------------------------------------- #
# P2-B: 错因 LLM 自动归因（与既有 recognize_text 的六类枚举对齐）             #
# --------------------------------------------------------------------------- #

_ATTRIBUTE_REASONS = ("粗心", "审题", "知识点缺失", "计算错误", "方法错误", "其他")

_ATTRIBUTE_PROMPT = """你是数学错因分析专家。根据题目、标准答案和学生错误作答，判断错因类别。
只能从以下六类中选一个：粗心/审题/知识点缺失/计算错误/方法错误/其他。
只输出 JSON：{"wrong_reason":"...","confidence":0-1,"advice":"一句话改进建议(20字内)"}"""


def _attribute_one(store, m, force: bool = False, u: str = "") -> dict:
    """对单个母题做 LLM 归因并持久化；返回归因结果 dict。"""
    import re as _re
    import urllib.request as _ur

    if m.wrong_reason and not force:
        return {"wrong_reason": m.wrong_reason, "advice": m.wrong_advice or "", "cached": True}

    # 最近一次错误作答（attempts 倒序找 is_correct=False）
    last_wrong = ""
    for a in store.list_attempts(m.id, limit=50):
        if a.get("is_correct") is False:
            last_wrong = str(a.get("user_answer") or "")
            break

    from deeptutor.services.llm.config import get_llm_config
    cfg = get_llm_config()
    if not cfg.api_key or cfg.api_key == "sk-placeholder":
        raise HTTPException(503, "LLM key 未配置")

    user = (
        f"题干: {m.question_text}\n"
        f"标准答案: {m.standard_answer or '未记录'}\n"
        f"学生作答: {last_wrong or '未记录'}"
    )
    body = json.dumps({
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": _ATTRIBUTE_PROMPT},
            {"role": "user", "content": user},
        ],
        "max_tokens": 300, "temperature": 0.2,
    }).encode("utf-8")
    req = _ur.Request(
        cfg.base_url + "/chat/completions", data=body,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg.api_key},
        method="POST",
    )
    import time as _t
    from deeptutor.learning.llm_cost_log import log_llm_call
    _t0 = _t.time()
    try:
        resp = _ur.urlopen(req, timeout=60)
        data = json.loads(resp.read())
        content = data["choices"][0]["message"].get("content", "")
        _usage = data.get("usage") or {}
        log_llm_call("attribute", user=u, tokens_in=_usage.get("prompt_tokens", 0),
                     tokens_out=_usage.get("completion_tokens", 0), ok=True,
                     latency_ms=int((_t.time() - _t0) * 1000), mid=m.id)
    except Exception as e:  # noqa: BLE001
        from deeptutor.learning.llm_cost_log import log_llm_call as _ll
        _ll("attribute", user=u, ok=False, latency_ms=int((_t.time() - _t0) * 1000), error=str(e)[:120], mid=m.id)
        raise
    match = _re.search(r"\{.*\}", content, _re.DOTALL)
    if not match:
        raise HTTPException(500, "LLM 返回格式异常")
    r = json.loads(match.group())
    reason = str(r.get("wrong_reason", "")).strip()
    if reason not in _ATTRIBUTE_REASONS:
        reason = "其他"  # 兜底，保证落入六枚举
    advice = str(r.get("advice", ""))
    store.update_mother(m.id, {"wrong_reason": reason, "wrong_advice": advice})
    return {
        "wrong_reason": reason,
        "advice": advice,
        "confidence": r.get("confidence"),
        "cached": False,
    }


@router.post("/{mid}/attribute")
async def attribute_wrong_reason(
    mid: str,
    payload: dict = Body(default={}),
    u: str = Query("", description="H5 用户标识（?u=）"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """P2-B：LLM 自动归因单题错因（六枚举，与 error-patterns 图表对齐）。"""
    with _h5_ctx(u, code, x_access_code):
        store = _store()
        m = store.get_mother(mid)
        if not m:
            raise HTTPException(404, "母题不存在")
        try:
            return _attribute_one(store, m, force=bool(payload.get("force")), u=u)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"LLM 调用失败: {e}")


@router.post("/attribute-batch")
async def attribute_batch(
    payload: dict = Body(default={}),
    u: str = Query("", description="H5 用户标识（?u=）"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """P2-B：对 wrong_reason 为空的母题批量归因（串行，单个失败跳过）。"""
    with _h5_ctx(u, code, x_access_code):
        store = _store()
        limit = min(int(payload.get("limit", 10)), 50)
        items, _total = store.list_mothers(page_size=500)
        pending = [m for m in items if m.status == "active" and not m.wrong_reason][:limit]
        attributed = 0
        for m in pending:
            try:
                _attribute_one(store, m, u=u)
                attributed += 1
            except HTTPException:
                continue
            except Exception:  # noqa: BLE001
                continue
        return {"attributed": attributed, "pending": len(pending)}


# --------------------------------------------------------------------------- #
# P2-C1: 认领（admin 复制母题给目标 H5 用户）                                  #
# --------------------------------------------------------------------------- #

@router.post("/claim")
async def claim_mothers(
    payload: dict = Body(default={}),
    u: str = Query("", description="H5 用户标识；认领仅限 admin（u 缺省）"),
):
    """P2-C1：把 admin 工作区的母题（及变式）复制给目标 H5 用户。

    仅 admin 上下文（u 缺省）可调，否则 403——孩子不能自己认领。
    按 title+question_text 判重；复制结果打 claimed:<原id> tag。
    """
    from deeptutor.multi_user.h5 import h5_slug, h5_user
    from deeptutor.multi_user.paths import user_context

    if u:
        raise HTTPException(403, "认领仅管理员可操作")

    target_u = str(payload.get("target_u", "")).strip()
    if not target_u:
        raise HTTPException(400, "target_u 必填")
    mids = payload.get("mids") or []
    all_m = bool(payload.get("all", False))
    include_variants = bool(payload.get("include_variants", True))

    src = _store()  # admin 上下文
    candidates = src.list_all_mothers()
    if not all_m:
        want = set(mids)
        candidates = [m for m in candidates if m.id in want]
    if not candidates:
        raise HTTPException(404, "未找到可认领的母题")

    claimed = 0
    skipped_dup = 0
    with user_context(h5_user(h5_slug(target_u))):
        dst = _store()
        existing = dst.list_all_mothers()
        exist_keys = {(m.title or "", m.question_text or "") for m in existing}
        for m in candidates:
            key = (m.title or "", m.question_text or "")
            if key in exist_keys:
                skipped_dup += 1
                continue
            m2 = m.model_copy(update={
                "id": _gen_id(),
                "tags": [*(m.tags or []), f"claimed:{m.id}"],
            })
            dst.create_mother(m2)
            if include_variants:
                for v in src.list_variants(m.id):
                    dst.create_variant(
                        v.model_copy(update={"id": _gen_id(), "mother_id": m2.id})
                    )
            claimed += 1

    return {"claimed": claimed, "skipped_dup": skipped_dup, "target_u": target_u}


@router.post("/batch_recognize")
async def batch_recognize(files: list[UploadFile] = FastFile(...)):
    """批量识别多张图片 (每张图独立 OCR)."""
    from deeptutor.learning.image_pipeline import ocr_image
    results = []
    for f in files:
        raw = await f.read()
        try:
            r = ocr_image(raw)
            results.append({"filename": f.filename, "text": r.get("text", ""), "ok": True})
        except Exception as e:
            results.append({"filename": f.filename, "text": "", "ok": False, "error": str(e)})
    return {"items": results, "total": len(results)}


@router.post("/batch_preview")
async def batch_preview(payload: dict = Body(...)):
    """批量预览: 对已识别的多题列表做查重预览 (不入库).

    入参: {items: [{title, question_text}, ...]}
    出参: {items: [{title, question_text, duplicate: bool, duplicates: [...]}]}
    """
    from deeptutor.learning.simhash_util import compute_simhash
    store = _store()
    items = payload.get("items", [])
    out = []
    for item in items:
        title = item.get("title", "")
        qt = item.get("question_text", "")
        sh = compute_simhash(title, qt)
        dups = store.find_duplicates(sh, threshold=4)
        out.append({
            "title": title,
            "question_text": qt,
            "simhash": sh,
            "duplicate": len(dups) > 0,
            "duplicates": dups,
        })
    return {"items": out, "total": len(out)}


@router.post("/batch_save_corrected")
async def batch_save_corrected(payload: dict = Body(...)):
    """批量保存(含二次校正): 将用户校正后的多题批量入库.

    入参: {items: [{title, question_text, subject, ...}], force: bool}
    出参: {saved: N, items: [...], duplicates: [...]}
    """
    store = _store()
    items = payload.get("items", [])
    force = payload.get("force", False)
    saved = []
    dup_list = []
    for item in items:
        title = item.get("title", "")
        qt = item.get("question_text", "")
        if not title or not qt:
            continue
        if not force:
            from deeptutor.learning.simhash_util import compute_simhash
            sh = compute_simhash(title, qt)
            dups = store.find_duplicates(sh, threshold=4)
            if dups:
                dup_list.append({"title": title, "duplicates": dups})
                continue
        m = MotherQuestion(
            id=_gen_id(), title=title, question_text=qt,
            subject=item.get("subject", "math"),
            standard_answer=item.get("standard_answer"),
            difficulty=item.get("difficulty", 3),
            wrong_reason=item.get("wrong_reason"),
        )
        store.create_mother(m)
        saved.append(m.model_dump(mode="json"))
    return {"saved": len(saved), "items": saved, "duplicates": dup_list}


# --------------------------------------------------------------------------- #
# simhash 查重 (ticket 02)                                                     #
# --------------------------------------------------------------------------- #

class CheckDuplicateRequest(BaseModel):
    title: str
    question_text: str
    threshold: int = 4


@router.post("/check_duplicate")
async def check_duplicate(body: CheckDuplicateRequest):
    from deeptutor.learning.simhash_util import compute_simhash
    sh = compute_simhash(body.title, body.question_text)
    dups = _store().find_duplicates(sh, threshold=body.threshold)
    return {"simhash": sh, "duplicates": dups, "count": len(dups)}


@router.post("/{mid}/recompute_simhash")
async def recompute_simhash(mid: str):
    from deeptutor.learning.simhash_util import compute_simhash
    m = _store().get_mother(mid)
    if not m:
        raise HTTPException(404, "母题不存在")
    sh = compute_simhash(m.title, m.question_text)
    _store().update_mother(mid, {"simhash": sh})
    return {"id": mid, "simhash": sh}


# --------------------------------------------------------------------------- #
# 知识点聚合 (ticket 03)                                                       #
# --------------------------------------------------------------------------- #

@router.get("/by-knowledge-point/summary")
async def by_knowledge_point():
    """每知识点的母题数 + 变式题数聚合."""
    store = _store()
    mothers = store.list_all_mothers()
    variants = store._load_vq()
    vq_by_mother: dict[str, int] = {}
    for v in variants:
        if v.status == "active":
            vq_by_mother[v.mother_id] = vq_by_mother.get(v.mother_id, 0) + 1
    agg: dict[str, dict] = {}
    for m in mothers:
        kp = m.knowledge_point_id or "(未挂载)"
        if kp not in agg:
            agg[kp] = {"knowledge_point_id": kp, "mother_count": 0, "variant_count": 0}
        agg[kp]["mother_count"] += 1
        agg[kp]["variant_count"] += vq_by_mother.get(m.id, 0)
    items = sorted(agg.values(), key=lambda x: x["mother_count"], reverse=True)
    return {"items": items, "total_kps": len(items)}


# --------------------------------------------------------------------------- #
# 分析 (ticket 08) - 适配母题模型，内存聚合                                     #
# --------------------------------------------------------------------------- #

@router.get("/analysis/comprehensive-stats")
async def comprehensive_stats(
    u: str = Query("", description="H5 用户标识（?u=）：错题本 data-class 隔离"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    with _h5_ctx(u, code, x_access_code):
        items = _store().list_all_mothers()
    by_grade: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_difficulty: dict[int, int] = {}
    by_status: dict[str, int] = {}
    for m in items:
        by_grade[m.grade or "(未设)"] = by_grade.get(m.grade or "(未设)", 0) + 1
        by_category[m.category or "(未设)"] = by_category.get(m.category or "(未设)", 0) + 1
        by_difficulty[m.difficulty] = by_difficulty.get(m.difficulty, 0) + 1
        sk = m.mastery_status or "not_mastered"
        by_status[sk] = by_status.get(sk, 0) + 1
    avg_diff = sum(m.difficulty for m in items) / len(items) if items else 0
    return {
        "total": len(items),
        "by_grade": by_grade,
        "by_category": by_category,
        "by_difficulty": by_difficulty,
        "by_status": by_status,
        "avg_difficulty": round(avg_diff, 2),
    }


@router.get("/analysis/weak-points")
async def weak_points(
    subject: str | None = None,
    u: str = Query(""),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """母题数最多的知识点 = 薄弱点(积累多说明需要重点复习)."""
    with _h5_ctx(u, code, x_access_code):
        items = _store().list_all_mothers()
        if subject:
            items = [m for m in items if m.subject == subject]
        agg: dict[str, int] = {}
        for m in items:
            if m.knowledge_point_id:
                agg[m.knowledge_point_id] = agg.get(m.knowledge_point_id, 0) + 1
        items_out = sorted(
            [{"knowledge_point_id": k, "mother_count": v} for k, v in agg.items()],
            key=lambda x: x["mother_count"], reverse=True,
        )[:10]
        return {"weak_points": items_out, "summary": f"共 {len(items_out)} 个薄弱知识点"}


@router.get("/analysis/trends")
async def trends(
    days: int = 30,
    u: str = Query(""),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    import time
    with _h5_ctx(u, code, x_access_code):
        cutoff = time.time() - days * 86400
        items = [m for m in _store().list_all_mothers() if m.create_time >= cutoff]
        daily: dict[str, int] = {}
        for m in items:
            d = time.strftime("%Y-%m-%d", time.localtime(m.create_time))
            daily[d] = daily.get(d, 0) + 1
        trends_list = [{"date": d, "count": c} for d, c in sorted(daily.items())]
        return {"trends": trends_list, "days": days}


@router.get("/analysis/error-patterns")
async def error_patterns(
    subject: str | None = None,
    u: str = Query(""),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """错误模式分析（按 wrong_reason 聚合）."""
    with _h5_ctx(u, code, x_access_code):
        items = _store().list_all_mothers()
        if subject:
            items = [m for m in items if m.subject == subject]
        agg: dict[str, int] = {}
        for m in items:
            if m.wrong_reason:
                agg[m.wrong_reason] = agg.get(m.wrong_reason, 0) + 1
        patterns = sorted([{"reason": k, "count": v} for k, v in agg.items()], key=lambda x: x["count"], reverse=True)
        return {"patterns": patterns}


# --------------------------------------------------------------------------- #
# docx 导出 (ticket 06) - 移植自 ragflow python-docx 逻辑                       #
# --------------------------------------------------------------------------- #

@router.post("/export")
async def export_docx(
    payload: dict = Body(...),
    u: str = Query("", description="H5 用户标识（?u=）：错题本 data-class 隔离"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """导出母题为 DOCX，对齐原系统能力."""
    from io import BytesIO
    from urllib.parse import quote

    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor, Inches
    from fastapi.responses import StreamingResponse

    # ---- 参数解析（对齐原系统） ----
    with _h5_ctx(u, code, x_access_code):
        ids = payload.get("ids") or []
    subject = payload.get("subject", "")
    min_diff = int(payload.get("min_difficulty", 1))
    max_diff = int(payload.get("max_difficulty", 5))
    limit = int(payload.get("limit", 50))
    with_answer = bool(payload.get("with_answer", True))
    with_image = bool(payload.get("with_image", True))
    with_wrong_image = bool(payload.get("with_wrong_image", False))
    title = payload.get("title") or ""
    date_start = (payload.get("date_start") or "").strip()
    date_end = (payload.get("date_end") or "").strip()

    # ---- 查询题目 ----
    with _h5_ctx(u, code, x_access_code):
        store = _store()
        all_mq = store.list_all_mothers()

    # 过滤
    filtered = []
    for m in all_mq:
        if ids and m.id not in ids:
            continue
        if not ids:
            if subject and m.subject != subject:
                continue
            if m.difficulty < min_diff or m.difficulty > max_diff:
                continue
            if date_start:
                try:
                    ds = float(date_start) if date_start.replace(".", "").isdigit() else None
                    if ds and m.create_time < ds:
                        continue
                except Exception:
                    pass
            if date_end:
                try:
                    de = float(date_end) if date_end.replace(".", "").isdigit() else None
                    if de and m.create_time > de:
                        continue
                except Exception:
                    pass
        filtered.append(m)

    # 排序：创建时间倒序 -> 科目 -> 难度
    filtered.sort(key=lambda x: (-x.create_time, x.subject, x.difficulty))
    items = filtered[:limit]

    if not items:
        raise HTTPException(404, "无符合条件的母题")

    SUBJECT_CN = {
        "chinese": "语文", "math": "数学", "english": "英语",
        "physics": "物理", "chemistry": "化学", "biology": "生物",
        "history": "历史", "geography": "地理", "politics": "政治",
        "other": "其他",
    }

    # ---- 生成 DOCX ----
    doc = Document()

    if not title:
        sub_cn = SUBJECT_CN.get(subject, "综合") if subject else "综合"
        from datetime import datetime
        title = f"错题组卷 - {sub_cn} - {datetime.now().strftime('%Y%m%d')}"
    h = doc.add_heading(title, level=0)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 统计信息：题数 + 平均难度 + 难度分布 + 版本标注
    avg_diff = sum(m.difficulty for m in items) / len(items)
    diff_counts = {}
    for m in items:
        diff_counts[m.difficulty] = diff_counts.get(m.difficulty, 0) + 1
    diff_summary = " ".join(f"{'★'*d}={diff_counts.get(d, 0)}题" for d in sorted(diff_counts.keys()))

    info_para = doc.add_paragraph()
    info_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    info_run = info_para.add_run(
        f"共 {len(items)} 题  |  平均难度 {avg_diff:.1f}  |  {diff_summary}  |  "
        f"{'教师版（含答案解析）' if with_answer else '学生练习版'}"
    )
    info_run.font.size = Pt(10)
    info_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    doc.add_paragraph()

    from deeptutor.learning.image_pipeline import resolve_url_to_path

    def _try_get_image_path(url):
        """解析 URL 到本地文件路径，返回 path 或 None."""
        if not url:
            return None
        path = resolve_url_to_path(url)
        if path and path.exists():
            try:
                from PIL import Image as _PIL
                _PIL.open(path).verify()
                return path
            except Exception:
                return None
        return None

    def _set_table_no_border(table):
        """去除表格边框."""
        from docx.oxml.ns import qn
        tbl = table._tbl
        for cell in tbl.iter(qn("w:tc")):
            tcPr = cell.find(qn("w:tcPr"))
            if tcPr is None:
                tcPr = cell.makeelement(qn("w:tcPr"), {})
                cell.insert(0, tcPr)
            borders = tcPr.find(qn("w:tcBorders"))
            if borders is None:
                borders = tcPr.makeelement(qn("w:tcBorders"), {})
                tcPr.append(borders)
            for edge in ("top", "left", "bottom", "right"):
                el = borders.find(qn(f"w:{edge}"))
                if el is None:
                    el = borders.makeelement(qn(f"w:{edge}"), {})
                    borders.append(el)
                el.set(qn("w:val"), "nil")

    for i, m in enumerate(items, start=1):
        stars = "★" * m.difficulty
        sub_cn = SUBJECT_CN.get(m.subject, m.subject)

        # 题号 + 科目 + 标题 + 难度
        t_para = doc.add_paragraph()
        t_run = t_para.add_run(f"{i}. [{sub_cn}] {m.title or '未命名题目'}  ")
        t_run.font.bold = True
        t_run.font.size = Pt(12)
        stars_run = t_para.add_run(f"难度：{stars}")
        stars_run.font.color.rgb = RGBColor(0xff, 0x99, 0x00)
        stars_run.font.size = Pt(10)
        t_para.paragraph_format.space_after = Pt(8)

        # 题干 + 图片布局（图左文右表格）
        img_path = _try_get_image_path(m.photo_url) if with_image else None
        if img_path and m.question_text:
            table = doc.add_table(rows=1, cols=2)
            _set_table_no_border(table)
            table.autofit = False
            left_cell = table.cell(0, 0)
            left_cell.width = Inches(2.8)
            left_para = left_cell.paragraphs[0]
            left_run = left_para.add_run()
            try:
                left_run.add_picture(str(img_path), width=Inches(2.6))
            except Exception:
                pass
            right_cell = table.cell(0, 1)
            right_cell.width = Inches(3.6)
            right_para = right_cell.paragraphs[0]
            right_run = right_para.add_run(m.question_text)
            right_run.font.size = Pt(11)
        elif img_path:
            try:
                doc.add_picture(str(img_path), width=Inches(4.5))
                doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            except Exception:
                pass
        elif m.question_text:
            ot_para = doc.add_paragraph(m.question_text)
            ot_para.paragraph_format.left_indent = Inches(0.25)

        if with_answer:
            # 【你的答案】（红色）
            if m.wrong_answer:
                p = doc.add_paragraph()
                r1 = p.add_run("【你的答案】")
                r1.font.bold = True
                r1.font.color.rgb = RGBColor(0xc0, 0x39, 0x2b)
                p.add_run(str(m.wrong_answer))
            # 错误答案截图（单独控制）
            if with_wrong_image and m.wrong_answer_image_url:
                wrong_img = _try_get_image_path(m.wrong_answer_image_url)
                if wrong_img:
                    try:
                        doc.add_picture(str(wrong_img), width=Inches(2.5))
                        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.LEFT
                        doc.paragraphs[-1].paragraph_format.left_indent = Inches(0.25)
                    except Exception:
                        pass
            # 【正确答案】（绿色）
            if m.standard_answer:
                p = doc.add_paragraph()
                r1 = p.add_run("【正确答案】")
                r1.font.bold = True
                r1.font.color.rgb = RGBColor(0x27, 0xae, 0x60)
                p.add_run(str(m.standard_answer))
            # 【错误原因】
            if m.wrong_reason:
                p = doc.add_paragraph()
                r1 = p.add_run("【错误原因】")
                r1.font.bold = True
                p.add_run(str(m.wrong_reason))
            # 【解析】（优先用详细解析，其次用解题步骤）
            if m.detailed_analysis:
                p = doc.add_paragraph()
                r1 = p.add_run("【解析】")
                r1.font.bold = True
                p.add_run(str(m.detailed_analysis))
            elif m.solution_steps:
                p = doc.add_paragraph()
                p.add_run("【解析】").font.bold = True
                for step in m.solution_steps:
                    doc.add_paragraph(
                        f"  {step.get('step', '')}. {step.get('text', '')}",
                    )
            # 【要点】
            if m.key_points:
                kp = doc.add_paragraph()
                kp.add_run("【要点】").font.bold = True
                kp.add_run("；".join(m.key_points))
        else:
            # 学生练习版：留答题空行
            ans_para = doc.add_paragraph()
            ans_para.add_run("答：").font.bold = True
            ans_para.add_run("_" * 60)
            doc.add_paragraph("_" * 70)
            doc.add_paragraph("_" * 70)

        # 题间间距
        sep = doc.add_paragraph()
        sep.paragraph_format.space_before = Pt(14)
        sep.paragraph_format.space_after = Pt(14)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)

    filename_safe = title.replace(" ", "_").replace("/", "_")
    filename = f"{filename_safe}.docx"
    filename_encoded = quote(filename)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename={filename_encoded}; filename*=UTF-8''{filename_encoded}"
        },
    )


# --------------------------------------------------------------------------- #
# 复习 (ticket 04 完整版) - 接 DeepTutor SpacedRepetitionScheduler             #
# --------------------------------------------------------------------------- #

@router.get("/reviews/due")
async def reviews_due(
    max_items: int = Query(20, ge=1, le=200),
    u: str = Query("", description="H5 用户标识（?u=）"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    with _h5_ctx(u, code, x_access_code):
        items = _store().list_due(max_items=max_items)
        return {"items": [m.model_dump(mode="json") for m in items], "count": len(items)}


@router.get("/reviews/due_count")
async def reviews_due_count(
    u: str = Query("", description="H5 用户标识（?u=）"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    with _h5_ctx(u, code, x_access_code):
        return {"due_count": _store().due_count()}


@router.get("/reviews/plan")
async def reviews_plan(
    max_items: int = Query(20, ge=1, le=200),
    u: str = Query("", description="H5 用户标识（?u=）"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    with _h5_ctx(u, code, x_access_code):
        return await _reviews_plan_inner(max_items)


async def _reviews_plan_inner(max_items: int):
    store = _store()
    due = store.list_due(max_items=max_items)
    plan = []
    for m in due:
        st = store.get_review_state(m.id)
        # 兼容 FSRS 卡片和旧格式 scheduler 状态
        if st and st.get("stability") is not None:
            next_at = st.get("due")
            interval = st.get("stability", 0)
            retention = store.get_retention(m.id)
        else:
            next_at = st.get("next_review_at") if st else None
            interval = st.get("interval_index", 0) if st else 0
            retention = 0
        plan.append({
            "id": m.id, "title": m.title, "difficulty": m.difficulty,
            "grade": m.grade, "category": m.category, "subject": m.subject,
            "mastery_status": m.mastery_status,
            "next_review_at": next_at,
            "interval_index": interval,
            "retention": round(retention, 1),
        })
    return {"plan": plan, "count": len(plan)}


@router.get("/{mid}/review/next")
async def review_next(
    mid: str,
    u: str = Query("", description="H5 用户标识（?u=）"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """取一道变式题作复习（随机）."""
    import random

    with _h5_ctx(u, code, x_access_code):
        store = _store()
        if not store.get_mother(mid):
            raise HTTPException(404, "母题不存在")
        variants = store.list_variants(mid)
        if not variants:
            raise HTTPException(404, "该母题暂无变式题")
        v = random.choice(variants)
        return {
            "variant_id": v.id,
            "question_text": v.question_text,
            "difficulty": v.difficulty,
            "variant_type": v.variant_type,
        }


@router.post("/{mid}/review/submit")
async def review_submit(
    mid: str,
    body: ReviewSubmitRequest,
    u: str = Query("", description="H5 用户标识（?u=）"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """提交复习结果 -> 更新 FSRS/scheduler 状态 + 记 attempt + log.

    支持两种模式:
      - FSRS: {rating: 1-4, variant_id?, user_answer?, time_spent?}
      - Legacy: {is_correct: bool, variant_id?}
    """
    import time

    with _h5_ctx(u, code, x_access_code):
        store = _store()
        m = store.get_mother(mid)
        if not m:
            raise HTTPException(404, "母题不存在")
        rating = body.rating
        variant_id = body.variant_id
        user_answer = body.user_answer
        time_spent = body.time_spent

        if rating is not None:
            # FSRS 模式
            from deeptutor.learning.fsrs import rating_to_bool
            is_correct = rating_to_bool(rating)
            new_state = store.upsert_review_fsrs(mid, rating)
            # 记 attempt
            att = Attempt(
                id=_gen_id(), mother_id=mid, variant_id=variant_id,
                is_correct=is_correct, user_answer=user_answer,
                source="review", time_spent=time_spent, rating=rating,
            )
            store.create_attempt(att)
        else:
            # Legacy binary 模式
            if body.is_correct is None:
                raise HTTPException(400, "rating 或 is_correct 必须提供一个")
            is_correct = body.is_correct
            new_state = store.upsert_review_state(mid, is_correct)
            att = Attempt(
                id=_gen_id(), mother_id=mid, variant_id=variant_id,
                is_correct=is_correct, user_answer=user_answer,
                source="review", time_spent=time_spent,
            )
            store.create_attempt(att)

        # 记 review_log (向后兼容)，通过 store 保证并发追加不会覆盖彼此。
        total_reviews = store.append_review_log({
            "mother_id": mid,
            "variant_id": variant_id,
            "is_correct": is_correct,
            "rating": rating,
            "time": time.time(),
        })

        # 返回 FSRS 格式化卡片 + 保留率
        from deeptutor.learning.fsrs import format_card
        card_summary = format_card(new_state) if new_state.get("stability") is not None else None
        retention = store.get_retention(mid)
        m = store.get_mother(mid)

        # P2-A 事件：完成一次复习 → review_completed（周增量统计用）
        try:
            from deeptutor.learning.learner_profile import emit_learning_event

            emit_learning_event(
                kind="review_completed",
                payload={"mid": mid, "is_correct": is_correct},
            )
        except Exception:  # noqa: BLE001
            import logging as _logging

            _logging.getLogger(__name__).warning("emit review_completed failed", exc_info=True)

        # M16-D（第八篇核实缺口 1）：复习成果刷新学习画像——否则 mastery 辅导
        # 开局 read_memory 读到的是上次练习时点的旧薄弱点（复习掌握的题还躺着）。
        try:
            from deeptutor.learning.learner_profile import (
                write_learning_l2_md,
                write_learning_profile_md,
            )

            write_learning_profile_md()
            write_learning_l2_md()
        except Exception:  # noqa: BLE001
            import logging as _logging

            _logging.getLogger(__name__).warning("review profile refresh failed", exc_info=True)

        return {
            "recorded": True,
            "total_reviews": total_reviews,
            "new_state": new_state,
            "card": card_summary,
            "retention": round(retention, 1),
            "mastery_status": m.mastery_status if m else None,
        }


@router.get("/{mid}/review/state")
async def review_state(
    mid: str,
    u: str = Query("", description="H5 用户标识（?u=）"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """查复习调度状态 (FSRS card / interval_index / next_review_at)."""
    from deeptutor.learning.fsrs import format_card

    with _h5_ctx(u, code, x_access_code):
        store = _store()
        if not store.get_mother(mid):
            raise HTTPException(404, "母题不存在")
        st = store.get_review_state(mid)
        card_summary = format_card(st) if st and st.get("stability") is not None else None
        retention = store.get_retention(mid)
        return {
            "state": st,
            "card": card_summary,
            "retention": round(retention, 1),
            "mastery_status": store.get_mother(mid).mastery_status,
        }


@router.get("/{mid}/review/history")
async def review_history(mid: str):
    """复习历史."""
    store = _store()
    if not store.get_mother(mid):
        raise HTTPException(404, "母题不存在")
    items = store.list_review_log(mother_id=mid)
    correct = sum(1 for x in items if x.get("is_correct"))
    return {
        "items": items,
        "total": len(items),
        "correct": correct,
        "accuracy": round(correct / len(items), 2) if items else 0,
    }


# --------------------------------------------------------------------------- #
# 正错题转换 (ticket 缺口4) - mastery_status 切换                              #
# --------------------------------------------------------------------------- #

@router.post("/{mid}/transfer-to-mastered")
async def transfer_to_mastered(
    mid: str,
    u: str = Query("", description="H5 用户标识（?u=）"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header("", alias="X-Access-Code"),
):
    # WQ4（M24）：H5 状态转移需用户作用域（错题本 data-class 隔离）
    with _h5_ctx(u, code, x_access_code):
        m = _store().update_mother(mid, {"mastery_status": "mastered"})
        if not m:
            raise HTTPException(404, "母题不存在")
        return {"id": mid, "mastery_status": "mastered"}


@router.post("/{mid}/transfer-to-active")
async def transfer_to_active(
    mid: str,
    u: str = Query("", description="H5 用户标识（?u=）"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header("", alias="X-Access-Code"),
):
    # WQ4（M24）：H5 状态转移需用户作用域
    with _h5_ctx(u, code, x_access_code):
        m = _store().update_mother(mid, {"mastery_status": "not_mastered"})
        if not m:
            raise HTTPException(404, "母题不存在")
        return {"id": mid, "mastery_status": "not_mastered"}


# --------------------------------------------------------------------------- #
# 复活项: RAG 讲解 + 相似题 (用 DeepTutor LLM + simhash)                       #
# --------------------------------------------------------------------------- #

@router.post("/{mid}/explain")
async def explain(
    mid: str,
    u: str = Query("", description="H5 用户标识（?u=）"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """RAG 讲题: 先 try RAG 检索知识库, 再 LLM 讲解. KB 空/embedding 未配则降级纯 LLM."""
    with _h5_ctx(u, code, x_access_code):
        return await _explain_inner(mid)


async def _explain_inner(mid: str):
    import urllib.request as _ur
    m = _store().get_mother(mid)
    if not m:
        raise HTTPException(404, "母题不存在")

    # 1. 尝试 RAG 检索（KB 存在 + embedding 配了才成功）
    rag_context = ""
    rag_used = False
    try:
        from deeptutor.services.rag.service import RAGService
        from deeptutor.services.path_service import get_path_service
        kb_base = str(get_path_service().get_workspace_dir() / "knowledge_bases")
        rag = RAGService(kb_base_dir=kb_base, provider="llamaindex")
        result = await rag.search(query=(m.title + " " + m.question_text), kb_name="math-textbook")
        rag_context = str(result.get("text", "") or result.get("answer", "") or "")[:1500]
        rag_used = bool(rag_context)
    except Exception:
        pass  # KB 不存在或 embedding 未配，降级纯 LLM

    # 2. LLM 讲解（带或不带 rag_context）
    try:
        from deeptutor.services.llm.config import get_llm_config
        cfg = get_llm_config()
        if not cfg.api_key or cfg.api_key == "sk-placeholder":
            return {"explain": m.standard_answer or "（无自带答案）", "rag_used": rag_used, "fallback": True, "msg": "LLM key 未配置"}
        nl = chr(10)
        prompt = ("你是小学数学老师，请详细讲解这道题的解题思路和步骤。" + nl + nl
                  + "题目：" + m.title + nl + m.question_text + nl
                  + "参考答案：" + (m.standard_answer or "") + nl)
        if rag_used:
            prompt += nl + "参考资料（从知识库检索）：" + nl + rag_context + nl
        prompt += nl + "请给出通俗易懂的讲解，包含关键步骤和易错点。"
        body = json.dumps({"model": cfg.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 4000}).encode("utf-8")
        req = _ur.Request(cfg.base_url + "/chat/completions", data=body,
                          headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg.api_key}, method="POST")
        import time as _t
        from deeptutor.learning.llm_cost_log import log_llm_call
        _t0 = _t.time()
        resp = _ur.urlopen(req, timeout=60)
        data = json.loads(resp.read())
        msg = data["choices"][0]["message"]
        _usage = data.get("usage") or {}
        log_llm_call("explain", tokens_in=_usage.get("prompt_tokens", 0),
                     tokens_out=_usage.get("completion_tokens", 0), ok=True,
                     latency_ms=int((_t.time() - _t0) * 1000), mid=mid, rag_used=rag_used)
        # Reasoning models (GLM-5.2, DeepSeek-R1, etc.) put the chain-of-thought in
        # `reasoning_content` and the final answer in `content`. When token budget
        # runs out mid-reasoning, `content` is empty - fall back to reasoning.
        explain_text = msg.get("content") or msg.get("reasoning_content") or ""
        return {"explain": explain_text, "rag_used": rag_used, "rag_context_len": len(rag_context), "fallback": False}
    except Exception as e:
        from deeptutor.learning.llm_cost_log import log_llm_call as _ll
        _ll("explain", ok=False, error=str(e)[:120], mid=mid)
        return {"explain": m.standard_answer or "（无自带答案）", "rag_used": rag_used, "fallback": True, "msg": "LLM 调用失败: " + str(e)}


# --------------------------------------------------------------------------- #
# 图片能力: 上传 / OCR / 识别 / 拍照切题 (ticket 05-08)                       #
# --------------------------------------------------------------------------- #

@router.post("/upload_image")
async def upload_image(file: UploadFile = FastFile(...)):
    """上传单张图片，返回公开可访问 URL。

    用于题目截图、错误答案截图等。存本地 <workspace>/mother_questions/images/。
    """
    from deeptutor.learning.image_pipeline import save_upload
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "空文件")
    ext = (file.filename or "photo.jpg").rsplit(".", 1)[-1]
    url = save_upload(raw, ext=ext, subdir="single_q")
    return {"url": url}


@router.post("/ocr-upload")
async def ocr_upload(file: UploadFile = FastFile(...)):
    """上传图片 -> OCR 识别 -> 返回文字。

    供拍照录入页使用。OCR 引擎未安装时返回 503 降级提示。
    """
    from deeptutor.learning.image_pipeline import ocr_image, save_upload, make_thumbnail
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "空文件")
    ext = (file.filename or "photo.jpg").rsplit(".", 1)[-1]
    # 保存原图
    url = save_upload(raw, ext=ext, subdir="originals")
    thumbnail = make_thumbnail(raw)
    # OCR
    try:
        result = ocr_image(raw)
        return {
            "text": result["text"],
            "lines": result["lines"],
            "line_count": len(result["lines"]),
            "photo_url": url,
            "thumbnail": thumbnail,
        }
    except Exception as e:
        # OCR 引擎未安装或识别失败，降级返回原图 URL + 空文字
        return JSONResponse(
            status_code=503,
            content={
                "text": "",
                "lines": [],
                "line_count": 0,
                "photo_url": url,
                "thumbnail": thumbnail,
                "msg": f"OCR 识别失败（{type(e).__name__}: {e}），请手动输入题干",
            },
        )


@router.post("/recognize")
async def recognize(file: UploadFile = FastFile(...)):
    """拍照单题识别: 图片 -> OCR -> LLM 抽结构化字段。

    返回 {title, question_text, standard_answer, key_points, photo_url, ocr_text}。
    LLM 不可用时降级返回 OCR 文本供手动编辑。
    """
    from deeptutor.learning.image_pipeline import ocr_image, save_upload
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "空文件")
    ext = (file.filename or "photo.jpg").rsplit(".", 1)[-1]
    url = save_upload(raw, ext=ext, subdir="single_q")
    # 1. OCR
    try:
        ocr_result = ocr_image(raw)
        ocr_text = ocr_result["text"]
    except Exception as e:
        return {"photo_url": url, "ocr_text": "", "msg": f"OCR 失败: {e}", "fields": {}}
    if not ocr_text.strip():
        return {"photo_url": url, "ocr_text": "", "msg": "OCR 未识别到文字", "fields": {}}
    # 2. LLM 抽字段
    try:
        from deeptutor.services.llm.config import get_llm_config
        import urllib.request as _ur
        cfg = get_llm_config()
        if not cfg.api_key or cfg.api_key == "sk-placeholder":
            return {"photo_url": url, "ocr_text": ocr_text, "fields": {}, "msg": "LLM key 未配置，返回 OCR 原文供手动编辑"}
        nl = chr(10)
        prompt = ("你是小学数学题目解析助手。请从以下 OCR 文本中提取题目信息，返回 JSON。" + nl + nl
                  + "OCR 文本：" + nl + ocr_text + nl + nl
                  + '返回格式: {"title": "题目标题(简短)", "question_text": "完整题目", "standard_answer": "标准答案(如有)", "key_points": ["知识点1", "知识点2"]}' + nl
                  + "只返回 JSON，不要其他文字。")
        body = json.dumps({"model": cfg.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2000}).encode("utf-8")
        req = _ur.Request(cfg.base_url + "/chat/completions", data=body,
                          headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg.api_key}, method="POST")
        resp = _ur.urlopen(req, timeout=60)
        data = json.loads(resp.read())
        msg = data["choices"][0]["message"]
        content = msg.get("content") or msg.get("reasoning_content") or ""
        # 从 LLM 回复中提取 JSON
        import re as _re
        json_match = _re.search(r'\{[^{}]*\}', content, _re.DOTALL)
        fields = {}
        if json_match:
            try:
                fields = json.loads(json_match.group())
            except Exception:
                pass
        return {"photo_url": url, "ocr_text": ocr_text, "fields": fields, "fallback": False}
    except Exception as e:
        return {"photo_url": url, "ocr_text": ocr_text, "fields": {}, "fallback": True, "msg": f"LLM 抽字段失败: {e}"}


@router.post("/batch_recognize_all")
async def batch_recognize_all(file: UploadFile = FastFile(...)):
    """拍照整页 -> 切多题 -> 每题返回 {qno, text, bbox, thumbnail, crop_url, source_image_url}。

    供拍照中心使用：用户预览校正后逐题入库。
    """
    from deeptutor.learning.image_pipeline import split_questions, save_upload, detect_red_strokes
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "空文件")
    ext = (file.filename or "photo.jpg").rsplit(".", 1)[-1]
    source_url = save_upload(raw, ext=ext, subdir="originals")
    # 切题
    try:
        questions = split_questions(raw)
    except Exception as e:
        raise HTTPException(500, f"切题失败: {e}")
    # 红笔检测（整页）
    try:
        has_checkmark = detect_red_strokes(raw)
    except Exception:
        has_checkmark = None
    return {
        "source_image_url": source_url,
        "question_count": len(questions),
        "questions": questions,
        "has_checkmark": has_checkmark,
    }


@router.post("/detect_red_mark")
async def detect_red_mark(file: UploadFile = FastFile(...)):
    """检测图片中是否有红笔标记（✓ 判对错）。"""
    from deeptutor.learning.image_pipeline import detect_red_strokes
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "空文件")
    try:
        has_red = detect_red_strokes(raw)
        return {"has_checkmark": has_red}
    except Exception as e:
        raise HTTPException(500, f"红笔检测失败: {e}")


# --------------------------------------------------------------------------- #
# 补齐功能: 批量查重 / 字典API / 知识点seed / LLM建树 / 自动建章节 / 教材导入  #
# --------------------------------------------------------------------------- #

@router.post("/batch_check_duplicate")
async def batch_check_duplicate(payload: dict = Body(...)):
    """批量查重：入参 {items: [{title, question_text}, ...]}，返回每项的重复情况。"""
    from deeptutor.learning.simhash_util import compute_simhash, hamming_distance
    items_in = payload.get("items", [])
    if not items_in:
        return {"results": []}
    store = _store()
    all_mq = store.list_all_mothers()
    existing_hashes = [(m, m.simhash or compute_simhash(m.title, m.question_text)) for m in all_mq]
    results = []
    for item in items_in:
        title = item.get("title", "")
        text = item.get("question_text", "")
        new_hash = compute_simhash(title, text)
        dups = []
        for m, eh in existing_hashes:
            dist = hamming_distance(new_hash, eh)
            if dist <= 4:
                dups.append({"id": m.id, "title": m.title, "distance": dist})
        results.append({"title": title, "duplicates": dups, "is_duplicate": len(dups) > 0})
    return {"results": results}


@router.post("/knowledge-points/seed")
async def seed_knowledge_points():
    """预置小学数学知识点体系（1-6 年级核心知识点）。"""
    from deeptutor.learning.curriculum import CurriculumStore, KnowledgePoint
    cs = CurriculumStore()
    existing = {k.name for k in cs.list_kps()}
    seeds = [
        # 一年级
        ("一年级", "10以内数的认识"), ("一年级", "20以内加减法"), ("一年级", "认识图形"),
        ("一年级", "100以内数的认识"), ("一年级", "认识人民币"),
        # 二年级
        ("二年级", "表内乘法"), ("二年级", "表内除法"), ("二年级", "长度单位"),
        ("二年级", "角的认识"), ("二年级", "观察物体"),
        # 三年级
        ("三年级", "多位数乘一位数"), ("三年级", "分数初步认识"), ("三年级", "长方形正方形周长"),
        ("三年级", "面积"), ("三年级", "年月日"),
        # 四年级
        ("四年级", "三位数乘两位数"), ("四年级", "除数是两位数的除法"), ("四年级", "角的度量"),
        ("四年级", "平行四边形和梯形"), ("四年级", "条形统计图"),
        # 五年级
        ("五年级", "小数乘法"), ("五年级", "小数除法"), ("五年级", "多边形面积"),
        ("五年级", "简易方程"), ("五年级", "因数与倍数"),
        # 六年级
        ("六年级", "分数乘除法"), ("六年级", "圆"), ("六年级", "百分数"),
        ("六年级", "圆柱与圆锥"), ("六年级", "比例"), ("六年级", "统计与概率"),
    ]
    created = []
    for grade, name in seeds:
        if name in existing:
            continue
        kp = KnowledgePoint(id=_gen_id(), name=name, parent_id=None, subject="math", description=f"{grade}知识点")
        cs.create_kp(kp)
        created.append(name)
    return {"seeded": len(created), "created": created, "total": len(seeds)}


@router.post("/knowledge-points/auto-build")
async def auto_build_knowledge_tree():
    """LLM 分析现有母题，自动提取并建立知识点树。"""
    from deeptutor.learning.curriculum import CurriculumStore, KnowledgePoint
    store = _store()
    all_mq = store.list_all_mothers()[:50]  # 取最近50题分析
    if not all_mq:
        raise HTTPException(400, "无母题可分析")
    try:
        from deeptutor.services.llm.config import get_llm_config
        import urllib.request as _ur
        cfg = get_llm_config()
        if not cfg.api_key or cfg.api_key == "sk-placeholder":
            raise HTTPException(503, "LLM key 未配置")
        nl = chr(10)
        titles = nl.join(f"- {m.title}: {m.question_text[:60]}" for m in all_mq)
        prompt = ("分析以下小学数学题目，提取知识点并按年级分组。返回 JSON 数组：" + nl + nl
                  + titles + nl + nl
                  + '格式: [{"grade":"六年级","name":"圆柱体积","description":"..."}]' + nl
                  + "只返回 JSON 数组，不要其他文字。")
        body = json.dumps({"model": cfg.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 3000}).encode("utf-8")
        req = _ur.Request(cfg.base_url + "/chat/completions", data=body,
                          headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg.api_key}, method="POST")
        resp = _ur.urlopen(req, timeout=60)
        data = json.loads(resp.read())
        msg = data["choices"][0]["message"]
        content = msg.get("content") or msg.get("reasoning_content") or ""
        import re as _re
        # 提取 JSON 数组
        match = _re.search(r'\[.*\]', content, _re.DOTALL)
        if not match:
            raise HTTPException(500, "LLM 返回无法解析")
        kps_data = json.loads(match.group())
        cs = CurriculumStore()
        existing = {k.name for k in cs.list_kps()}
        created = []
        for kp_data in kps_data:
            name = kp_data.get("name", "").strip()
            if not name or name in existing:
                continue
            kp = KnowledgePoint(
                id=_gen_id(), name=name, parent_id=None, subject="math",
                description=kp_data.get("description", kp_data.get("grade", "")),
            )
            cs.create_kp(kp)
            existing.add(name)
            created.append(name)
        return {"created": created, "count": len(created)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"LLM 自动建树失败: {e}")


@router.post("/chapters/auto-build/{textbook_id}")
async def auto_build_chapters(textbook_id: str):
    """从教材标题自动生成章节结构（LLM 生成标准章节名）。"""
    from deeptutor.learning.curriculum import CurriculumStore, Chapter
    cs = CurriculumStore()
    tbs = cs.list_textbooks()
    tb = next((t for t in tbs if t.id == textbook_id), None)
    if not tb:
        raise HTTPException(404, "教材不存在")
    # 根据年级生成标准章节
    grade = tb.grade or "六年级"
    standard_chapters = {
        "六年级": ["一、负数", "二、百分数（二）", "三、圆柱与圆锥", "四、比例", "五、数学广角", "六、整理和复习"],
        "五年级": ["一、小数乘法", "二、位置", "三、小数除法", "四、可能性", "五、简易方程", "六、多边形的面积"],
        "四年级": ["一、大数的认识", "二、公顷和平方千米", "三、角的度量", "四、三位数乘两位数", "五、平行四边形和梯形"],
    }
    names = standard_chapters.get(grade, standard_chapters["六年级"])
    existing = cs.list_chapters(textbook_id)
    existing_names = {c.name for c in existing}
    created = []
    for i, name in enumerate(names):
        if name in existing_names:
            continue
        ch = Chapter(id=_gen_id(), textbook_id=textbook_id, name=name, parent_id=None, order=i + 1)
        cs.create_chapter(ch)
        created.append(name)
    return {"textbook_id": textbook_id, "created": created, "count": len(created)}


@router.post("/textbooks/{textbook_id}/import")
async def import_textbook(textbook_id: str, file: UploadFile = FastFile(...)):
    """教材导入：上传 PDF -> 拆页渲染 -> 每页存为图片 + OCR 文本。

    复用 image_pipeline 的 PIL + RapidOCR，不依赖 RAGFlow。
    """
    from deeptutor.learning.curriculum import CurriculumStore, TextbookPage
    from deeptutor.learning.image_pipeline import save_upload, ocr_image
    cs = CurriculumStore()
    tbs = cs.list_textbooks()
    tb = next((t for t in tbs if t.id == textbook_id), None)
    if not tb:
        raise HTTPException(404, "教材不存在")
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "空文件")
    # PDF 拆页
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise HTTPException(503, "PyMuPDF 未安装，无法拆页")
    pages = []
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        for page_num in range(min(doc.page_count, 100)):  # 限制最多100页
            page = doc[page_num]
            # 渲染为图片
            pix = page.get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            url = save_upload(img_bytes, ext="png", subdir=f"textbooks/{textbook_id}")
            # OCR
            ocr_text = ""
            try:
                ocr_result = ocr_image(img_bytes)
                ocr_text = ocr_result["text"]
            except Exception:
                pass
            page_record = TextbookPage(
                id=_gen_id(),
                textbook_id=textbook_id,
                page_num=page_num + 1,
                image_url=url,
                ocr_text=ocr_text[:500],
            )
            cs.add_page(page_record)
            pages.append(page_record.model_dump(mode="json"))
        doc.close()
    except Exception as e:
        raise HTTPException(500, f"PDF 拆页失败: {e}")
    return {"textbook_id": textbook_id, "pages": pages, "page_count": len(pages)}


# --------------------------------------------------------------------------- #
# P0-1: AI 智能填充 (recognize_text) - 移植自 ragflow wrong_question_api.py     #
# --------------------------------------------------------------------------- #

_RECOGNIZE_TEXT_PROMPT = """你是一个错题结构化助手。学生会给你一段错题相关的文字（可能来自拍照 OCR 或手输），请你抽取并以 JSON 输出。
要求字段：
- title: 一句话标题（不超过 30 字）
- subject: 学科（math/chinese/english/physics/chemistry/biology/history/geography/politics/other）
- category: 题型（应用题/计算/几何/统计/综合）
- question_text: 完整题目原文（保留关键数字和符号）
- standard_answer: 正确答案（如有）
- solution_steps: 解题步骤数组 [{step: 1, text: "..."}]
- key_points: 核心知识点数组 ["知识点1", "知识点2"]
- wrong_reason: 错误原因（粗心/审题/知识点缺失/计算错误/方法错误/其他）
- difficulty: 难度 1-5
约束：
- 只返回 JSON，不要 markdown
- 解析控制在 100 字以内
- 缺失字段返回空字符串或空数组"""


@router.post("/recognize_text")
async def recognize_text(
    payload: dict = Body(...),
    u: str = Query("", description="H5 用户标识（?u=）：错题本 data-class 隔离"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header("", alias="X-Access-Code"),
):
    """AI 智能填充：从文字/OCR文本中抽取结构化字段。

    入参: {text, image_url?, subject?, wrong_answer?, title?}
    出参: {fields: {title, question_text, standard_answer, ...}, raw?, msg?}
    LLM 不可用时降级返回原文。

    WQ1（M24）：带 u 时经 h5_user_guarded 统一校验访问码（?code= / X-Access-Code）。
    recognize_text 为纯 LLM 调用、无 per-user 存储，仅需闸门校验。
    """
    from deeptutor.multi_user.h5 import h5_user_guarded

    h5_user_guarded(u, code, x_access_code)

    import urllib.request as _ur
    import re as _re

    text = (payload.get("text") or "").strip()
    image_url = (payload.get("image_url") or "").strip()
    subject_hint = (payload.get("subject") or "").strip()
    existing_wrong_answer = (payload.get("wrong_answer") or "").strip()
    existing_title = (payload.get("title") or "").strip()

    # 拼装上下文
    parts = []
    if existing_title:
        parts.append(f"【已知标题】{existing_title}")
    if text:
        parts.append(f"【题目原文/描述】{text}")
    if image_url:
        # 尝试 OCR 补充（短超时，失败跳过）
        try:
            from deeptutor.learning.image_pipeline import resolve_url_to_path, ocr_image
            path = resolve_url_to_path(image_url)
            if path and path.exists():
                raw = path.read_bytes()
                ocr_result = ocr_image(raw)
                ocr_text = ocr_result.get("text", "")
                if ocr_text:
                    parts.append(f"【图片OCR文字】{ocr_text}")
        except Exception:
            pass
    if existing_wrong_answer:
        parts.append(f"【学生的错误答案】{existing_wrong_answer}")
    if subject_hint:
        parts.append(f"【学科提示】{subject_hint}")
    if not parts:
        raise HTTPException(400, "至少需要提供 text 或 image_url 之一")

    full_context = "\n".join(parts)
    user_msg = "请基于以下信息抽取并补全错题字段。已知字段请保留，缺失字段请推理填充。\n\n" + full_context

    try:
        from deeptutor.services.llm.config import get_llm_config
        cfg = get_llm_config()
        if not cfg.api_key or cfg.api_key == "sk-placeholder":
            return {"fields": {}, "msg": "LLM key 未配置，请手动填写"}
        body = json.dumps({
            "model": cfg.model,
            "messages": [
                {"role": "system", "content": _RECOGNIZE_TEXT_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": 3000, "temperature": 0.3,
        }).encode("utf-8")
        req = _ur.Request(cfg.base_url + "/chat/completions", data=body,
                          headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg.api_key}, method="POST")
        resp = _ur.urlopen(req, timeout=120)
        data = json.loads(resp.read())
        msg = data["choices"][0]["message"]
        content = msg.get("content") or msg.get("reasoning_content") or ""
        # 提取 JSON
        fields = None
        for i, ch in enumerate(content):
            if ch != "{":
                continue
            try:
                obj, _ = json.JSONDecoder().raw_decode(content, i)
                fields = obj
                break
            except json.JSONDecodeError:
                continue
        # JSON 截断修复
        if fields is None:
            first = content.find("{")
            if first >= 0:
                frag = content[first:]
                frag += "}" * max(0, frag.count("{") - frag.count("}"))
                frag += "]" * max(0, frag.count("[") - frag.count("]"))
                try:
                    fields = json.loads(frag)
                except json.JSONDecodeError:
                    pass
        if fields is None:
            return {"fields": {}, "raw": content[:500], "msg": "模型未返回有效 JSON"}
        return {"fields": fields, "fallback": False}
    except Exception as e:
        return {"fields": {}, "fallback": True, "msg": f"LLM 调用失败: {e}"}


# --------------------------------------------------------------------------- #
# P1-5: AI 解题流式 (SSE streaming) - 移植自 ragflow ai_solve                   #
# --------------------------------------------------------------------------- #

@router.post("/{mid}/ai_solve")
async def ai_solve(mid: str):
    """AI 解题（SSE 流式返回）.

    返回 text/plain stream，逐块输出解题过程。
    """
    from fastapi.responses import StreamingResponse

    m = _store().get_mother(mid)
    if not m:
        raise HTTPException(404, "母题不存在")

    prompt = (
        f"你是资深老师，请分析这道题：\n\n"
        f"【题目】{m.title}\n{m.question_text}\n"
        f"【参考答案】{m.standard_answer or '未填写'}\n\n"
        f"请直接给出：\n"
        f"1. 解题思路（一句话）\n"
        f"2. 详细解题步骤\n"
        f"3. 核心知识点\n"
        f"4. 易错点提示\n\n"
        f"严格要求：\n- 只输出中文\n- 不要输出思考过程\n- 总字数不超过 600 字"
    )

    async def stream():
        import time as _t
        from deeptutor.learning.llm_cost_log import log_llm_call
        _t0 = _t.time()
        _tok = 0
        try:
            from deeptutor.services.llm.config import get_llm_config
            import urllib.request as _ur
            cfg = get_llm_config()
            if not cfg.api_key or cfg.api_key == "sk-placeholder":
                yield "LLM key 未配置，无法使用 AI 解题。"
                return
            body = json.dumps({
                "model": cfg.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800, "temperature": 0.3, "stream": True,
            }).encode("utf-8")
            req = _ur.Request(cfg.base_url + "/chat/completions", data=body,
                              headers={"Content-Type": "application/json", "Authorization": "Bearer " + cfg.api_key}, method="POST")
            resp = _ur.urlopen(req, timeout=60)
            for line in resp:
                line = line.decode("utf-8", errors="replace").strip()
                if not line or not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    if chunk.get("usage"):
                        _tok = chunk["usage"].get("total_tokens", _tok)
                    delta = chunk["choices"][0].get("delta", {})
                    text = delta.get("content") or delta.get("reasoning_content") or ""
                    if text:
                        yield text
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
            log_llm_call("ai_solve", ok=True, tokens_out=_tok,
                         latency_ms=int((_t.time() - _t0) * 1000), mid=mid)
        except Exception as e:
            log_llm_call("ai_solve", ok=False, latency_ms=int((_t.time() - _t0) * 1000),
                         error=str(e)[:120], mid=mid)
            yield f"\n[AI 解题出错: {e}]"

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")


# --------------------------------------------------------------------------- #
# P0-3: 软删除/恢复 + 回收站                                                   #
# --------------------------------------------------------------------------- #

@router.post("/{mid}/restore")
async def restore_mother(
    mid: str,
    u: str = Query("", description="H5 用户标识（?u=）：错题本 data-class 隔离"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """从回收站恢复母题."""
    with _h5_ctx(u, code, x_access_code):
        ok = _store().restore_mother(mid)
    if not ok:
        raise HTTPException(404, "母题不存在或未在回收站中")
    return {"restored": True, "id": mid}


# --------------------------------------------------------------------------- #
# P1-7: 标签实体 CRUD                                                          #
# --------------------------------------------------------------------------- #

class CreateTagRequest(BaseModel):
    name: str
    color: str | None = None


@router.post("/tags", status_code=201)
async def create_tag(body: CreateTagRequest):
    tag = _store().create_tag(body.name, body.color)
    return tag


@router.delete("/tags/{name}")
async def delete_tag(name: str):
    _store().delete_tag(name)
    return {"deleted": True, "name": name}


# --------------------------------------------------------------------------- #
# P1-8: 答题记录 attempts                                                      #
# --------------------------------------------------------------------------- #

class CreateAttemptRequest(BaseModel):
    mother_id: str | None = None  # 从路径参数获取，body 中可选
    variant_id: str | None = None
    is_correct: bool
    user_answer: str | None = None
    source: str = "manual"
    time_spent: float | None = None
    rating: int | None = None


@router.get("/{mid}/attempts")
async def list_attempts(
    mid: str,
    limit: int = Query(100, ge=1, le=500),
    u: str = Query("", description="H5 用户标识（?u=）：错题本 data-class 隔离"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """列出某母题的答题记录."""
    with _h5_ctx(u, code, x_access_code):
        if not _store().get_mother(mid):
            raise HTTPException(404, "母题不存在")
        items = _store().list_attempts(mother_id=mid, limit=limit)
        correct = sum(1 for a in items if a.get("is_correct"))
        return {
            "items": items,
            "total": len(items),
            "correct": correct,
            "accuracy": round(correct / len(items), 2) if items else 0,
        }


@router.post("/{mid}/attempts", status_code=201)
async def create_attempt(mid: str, body: CreateAttemptRequest):
    """手动添加答题记录."""
    if not _store().get_mother(mid):
        raise HTTPException(404, "母题不存在")
    a = Attempt(
        id=_gen_id(), mother_id=mid, variant_id=body.variant_id,
        is_correct=body.is_correct, user_answer=body.user_answer,
        source=body.source, time_spent=body.time_spent, rating=body.rating,
    )
    _store().create_attempt(a)
    return a.model_dump(mode="json")


@router.delete("/attempts/{aid}")
async def delete_attempt(aid: str):
    ok = _store().delete_attempt(aid)
    if not ok:
        raise HTTPException(404, "答题记录不存在")
    return {"deleted": True}


# --------------------------------------------------------------------------- #
# P1-9: 多图资产系统                                                           #
# --------------------------------------------------------------------------- #

class AddAssetRequest(BaseModel):
    url: str
    asset_type: str = "photo"           # photo/wrong_answer/source/other
    ocr_text: str | None = None


@router.get("/{mid}/assets")
async def list_assets(mid: str):
    m = _store().get_mother(mid)
    if not m:
        raise HTTPException(404, "母题不存在")
    return {"items": m.assets or [], "total": len(m.assets or [])}


@router.post("/{mid}/assets", status_code=201)
async def add_asset(mid: str, body: AddAssetRequest):
    if not _store().get_mother(mid):
        raise HTTPException(404, "母题不存在")
    asset = {"url": body.url, "type": body.asset_type, "ocr_text": body.ocr_text, "create_time": _now()}
    _store().add_asset(mid, asset)
    return asset


@router.delete("/{mid}/assets")
async def remove_asset(mid: str, url: str = Query(...)):
    ok = _store().remove_asset(mid, url)
    if not ok:
        raise HTTPException(404, "资产不存在")
    return {"deleted": True}
