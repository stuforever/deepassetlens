"""Self-directed Learning API router.

Provides a chapter-centric aggregation endpoint that collects counts and
summaries from mother-questions, curriculum, books, and notebook modules,
so the frontend tabbed UI can show an overview without making 5 separate calls.
"""

from __future__ import annotations

import logging
import re
from datetime import date
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Header, Response
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/chapter/{chapter_id}")
def chapter_overview(
    chapter_id: str,
    u: str = Query("", description="H5 用户标识（?u=），缺省=admin"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header("", alias="X-Access-Code"),
):
    """Return an aggregated overview of all content linked to a curriculum chapter.

    Includes:
    - chapter info (name, textbook, parent, children, kp_ids)
    - wrong question count + 3 recent items (u 感知：带 ?u= 时读该用户错题）
    - knowledge point details (resolved from kp_ids)
    - related books (matched by title keyword)
    - notebook entry count (keyword-matched)
    - mastery progress (u 感知：带 ?u= 时读该用户精通之路）
    """
    from deeptutor.learning.curriculum import CurriculumStore
    from deeptutor.multi_user.h5 import h5_user_guarded

    # R1-c：访问码守卫必须在 try 之外——401/400 不能被 best-effort 吞掉
    #（对照本文件 resources 端点的同一不变量）。u 缺省 -> admin（桌面不受约束）。
    _h5_user = h5_user_guarded(u, code, x_access_code)

    cs = CurriculumStore()

    # 1. Find the chapter across all textbooks
    all_chapters = cs.list_chapters("")
    chapter = None
    for c in all_chapters:
        if c.id == chapter_id:
            chapter = c
            break
    if not chapter:
        return {"error": "chapter not found", "chapter_id": chapter_id}

    # Resolve textbook
    textbooks = cs.list_textbooks("")
    textbook = next((t for t in textbooks if t.id == chapter.textbook_id), None)

    # Children chapters
    children = [c for c in all_chapters if c.parent_id == chapter_id]

    # 2. Knowledge points linked via kp_ids
    kps: list = []
    kp_map: dict = {}
    if chapter.kp_ids:
        all_kps = cs.list_kps((textbook.subject if textbook else "math"))
        kp_map = {k.id: k for k in all_kps}
        kps = [kp_map[kid] for kid in chapter.kp_ids if kid in kp_map]
        # 有效难度：分类节点继承子节点最大难度（与知识树一致），未标为 0
        def _eff_diff(k) -> int:
            if k.difficulty:
                return k.difficulty
            kids = [c for c in all_kps if c.parent_id == k.id]
            if kids:
                return max((_eff_diff(c) or 0) for c in kids)
            return 0
        _eff_map = {k.id: _eff_diff(k) for k in all_kps}
        # 按难度易→难排序（未标难度排最后）
        kps.sort(key=lambda k: (_eff_map.get(k.id, 0), k.name))

    def _kp_path(k) -> str:
        """祖先分类链，如：阅读 → 现代文阅读."""
        names: list[str] = []
        seen: set = set()
        cur = k
        while cur and cur.parent_id in kp_map and cur.parent_id not in seen:
            seen.add(cur.id)
            cur = kp_map[cur.parent_id]
            names.append(cur.name)
        return " → ".join(reversed(names))

    def _kp_payload(k) -> dict:
        """完整知识点载荷：含 总结/讲解/实例/公式/图形 与 相关关系（带名称）+ 祖先链."""
        related = []
        for r in (k.related or []):
            rid = r.get("kp_id")
            target = kp_map.get(rid)
            related.append({
                "kp_id": rid,
                "relation": r.get("relation"),
                "name": target.name if target else "",
            })
        return {
            "id": k.id,
            "name": k.name,
            "subject": k.subject,
            "grade": k.grade,
            "difficulty": k.difficulty,
            "path": _kp_path(k),
            "description": k.description,
            "explanation": k.explanation,
            "examples": k.examples or [],
            "formula": k.formula,
            "figure": k.figure,
            "related": related,
        }

    # 3. Wrong questions (mother questions) for this chapter
    # F2（M14-B）：u 感知——带 ?u= 时在该用户工作区读错题，避免串 admin 数据
    wrong_count = 0
    recent_wrong: list = []
    try:
        from deeptutor.learning.mother_question import MotherQuestionStore
        from deeptutor.multi_user.paths import user_context

        with user_context(_h5_user):
            store = MotherQuestionStore()
            all_mq = store.list_all_mothers()
            chapter_mq = [m for m in all_mq if m.chapter_id == chapter_id and not m.deleted_time]
            wrong_count = len(chapter_mq)
            recent_wrong = [
                {"id": m.id, "title": m.title, "difficulty": m.difficulty, "mastery_status": m.mastery_status}
                for m in chapter_mq[:5]
            ]
    except Exception:
        pass

    # 4. Related books (match by chapter name keyword in book title)
    related_books: list = []
    try:
        from deeptutor.services.path_service import get_path_service
        import json
        from pathlib import Path

        books_dir = get_path_service().get_workspace_dir() / "books"
        if books_dir.exists():
            for book_dir in books_dir.iterdir():
                manifest = book_dir / "manifest.json"
                if manifest.exists():
                    try:
                        data = json.loads(manifest.read_text(encoding="utf-8"))
                        title = data.get("title", "")
                        # Match if chapter name appears in book title, or book title in chapter name
                        if chapter.name in title or title in chapter.name or chapter.textbook_id == data.get("textbook_id"):
                            related_books.append({
                                "id": data.get("id", book_dir.name),
                                "title": title,
                                "status": data.get("status", "unknown"),
                                "page_count": data.get("page_count", 0),
                                "chapter_count": data.get("chapter_count", 0),
                            })
                    except Exception:
                        pass
    except Exception:
        pass

    # 5. Mastery progress (if a book is linked)
    # F2（M14-B）：u 感知——带 ?u= 时读该用户精通之路（learning_progress）
    mastery_progress = None
    try:
        import json
        from pathlib import Path
        from deeptutor.services.path_service import get_path_service
        from deeptutor.multi_user.paths import user_context

        with user_context(_h5_user):
            progress_dir = get_path_service().get_workspace_dir() / "learning_progress"
            if progress_dir.exists():
                for pf in progress_dir.glob("*.json"):
                    try:
                        data = json.loads(pf.read_text(encoding="utf-8"))
                        modules = data.get("modules", [])
                        # Check if any module name matches chapter name
                        matched = [m for m in modules if chapter.name in m.get("name", "")]
                        if matched:
                            mastery_progress = {
                                "book_id": pf.stem,
                                "total_modules": len(modules),
                                "matched_modules": len(matched),
                                "completed": sum(1 for m in modules if m.get("status") == "completed"),
                            }
                            break
                    except Exception:
                        pass
    except Exception:
        pass

    return {
        "chapter": {
            "id": chapter.id,
            "name": chapter.name,
            "textbook_id": chapter.textbook_id,
            "parent_id": chapter.parent_id,
            "order": chapter.order,
            "page_start": chapter.page_start,
            "page_end": chapter.page_end,
            "kp_ids": chapter.kp_ids,
        },
        "textbook": {
            "id": textbook.id if textbook else None,
            "name": textbook.name if textbook else "",
            "subject": textbook.subject if textbook else "",
            "grade": textbook.grade if textbook else "",
        },
        "children": [{"id": c.id, "name": c.name, "order": c.order} for c in children],
        "knowledge_points": [_kp_payload(k) for k in kps],
        "wrong_questions": {
            "count": wrong_count,
            "recent": recent_wrong,
        },
        "related_books": related_books,
        "mastery_progress": mastery_progress,
    }


@router.get("/textbooks")
def textbooks_with_chapters():
    """Convenience endpoint: all textbooks with their chapter trees in one call."""
    from deeptutor.learning.curriculum import CurriculumStore

    cs = CurriculumStore()
    return cs.textbook_tree()


# Subject -> knowledge base name mapping. A missing KB just means the
# generated book relies on textbook-page anchors + block-level LLM only.
_SUBJECT_KB = {
    "math": "七年级数学上",
    "chinese": "七年级语文上",
    "english": "七年级英语外研版2025最新上",
}


@router.post("/chapter/{chapter_id}/book")
async def create_chapter_book(chapter_id: str):
    """One-click: deterministically create a chapter-scoped courseware book.

    Reads the curriculum chapter + its sub-chapters (with textbook page
    ranges), maps the subject to a knowledge base, and calls
    ``BookEngine.create_from_chapter`` which builds the spine from the
    chapter tree and queues block-level compilation in the background.
    Idempotent: if a non-archived book already exists for this chapter it is
    returned instead of creating a duplicate.
    """
    from deeptutor.learning.curriculum import CurriculumStore

    cs = CurriculumStore()
    all_chapters = cs.list_chapters("")
    chapter = next((c for c in all_chapters if c.id == chapter_id), None)
    if chapter is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="chapter not found")

    textbooks = cs.list_textbooks("")
    textbook = next((t for t in textbooks if t.id == chapter.textbook_id), None)
    children = sorted(
        (c for c in all_chapters if c.parent_id == chapter_id),
        key=lambda c: c.order,
    )

    # Resolve knowledge point names from kp_ids
    kp_names: list[str] = []
    if chapter.kp_ids:
        all_kps = cs.list_kps((textbook.subject if textbook else "math"))
        kp_map = {k.id: k for k in all_kps}
        kp_names = [kp_map[kid].name for kid in chapter.kp_ids if kid in kp_map]

    # Wrong questions for this chapter
    wrong_count = 0
    wrong_titles: list[str] = []
    try:
        from deeptutor.learning.mother_question import MotherQuestionStore

        store = MotherQuestionStore()
        all_mq = store.list_all_mothers()
        chapter_mq = [
            m for m in all_mq if m.chapter_id == chapter_id and not m.deleted_time
        ]
        wrong_count = len(chapter_mq)
        wrong_titles = [m.title for m in chapter_mq[:5]]
    except Exception:
        pass

    # Idempotency: reuse an existing book for this chapter.
    from deeptutor.book.engine import get_book_engine

    engine = get_book_engine()
    existing = None
    for b in engine.list_books():
        meta = b.metadata or {}
        if (
            meta.get("curriculum_chapter_id") == chapter_id
            and b.status.value not in ("archived",)
        ):
            existing = b
            break
    if existing is not None:
        return {
            "book_id": existing.id,
            "status": existing.status.value,
            "reused": True,
        }

    subject = textbook.subject if textbook else "math"
    book, _spine = await engine.create_from_chapter(
        curriculum_chapter_id=chapter_id,
        chapter_name=chapter.name,
        textbook_id=chapter.textbook_id,
        textbook_name=textbook.name if textbook else "",
        subject=subject,
        knowledge_base=_SUBJECT_KB.get(subject),
        children=[
            {
                "name": c.name,
                "page_start": c.page_start,
                "page_end": c.page_end,
            }
            for c in children
        ]
        or None,
        page_start=chapter.page_start,
        page_end=chapter.page_end,
        kp_names=kp_names,
        wrong_count=wrong_count,
        wrong_titles=wrong_titles,
    )
    return {"book_id": book.id, "status": book.status.value, "reused": False}


@router.get("/chapter/{chapter_id}/books")
def chapter_books(chapter_id: str):
    """Return internal courseware books linked to a chapter, including its parent chapter's books.

    Books are generated at the top-level chapter (e.g. 第一章 有理数), so sub-chapters
    (e.g. 1.1 正数和负数) inherit the parent's book.
    """
    from deeptutor.learning.curriculum import CurriculumStore
    from deeptutor.book.engine import get_book_engine

    # Find chapter + its parent id
    cids = {chapter_id}
    for c in CurriculumStore().list_chapters(""):
        if c.id == chapter_id:
            if c.parent_id:
                cids.add(c.parent_id)
            break

    books = []
    for b in get_book_engine().list_books():
        meta = b.metadata or {}
        cid = meta.get("curriculum_chapter_id")
        if cid in cids and b.status.value not in ("archived",):
            books.append({
                "id": b.id,
                "title": b.title,
                "status": b.status.value,
                "chapter_count": b.chapter_count,
                "page_count": b.page_count,
            })
    return {"items": books, "count": len(books)}


@router.get("/chapter/{chapter_id}/resources")
def chapter_resources(
    chapter_id: str,
    u: str = "",
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """Return grade-7 interactive resources (courseware / 闯关练习 / 语音领读 / 数学图形演示) linked to a chapter.
    Includes resources of all sub-chapters of the given chapter.
    *u*（H5 用户标识）：个性化闯关选题时读取对应用户的学情画像（薄弱优先）。"""
    from deeptutor.services.path_service import get_path_service
    from deeptutor.learning.curriculum import CurriculumStore
    import json as _json

    # Collect this chapter + its parent + all its sub-chapters' ids (sub-chapter 继承父章节资源)
    cids = {chapter_id}
    for c in CurriculumStore().list_chapters(""):
        if c.id == chapter_id:
            if c.parent_id:
                cids.add(c.parent_id)
        elif c.parent_id == chapter_id:
            cids.add(c.id)

    # T7 泛化：glob workspace/*/grade*_index.json 合并各年级索引（grade7 单文件
    # 直读先例的泛化，grade7 现行行为不变——chapter_id 全局唯一，两索引同 id 不
    # 冲突）。只合并四消费键（courseware/exercises/voices/figures）；
    # recite_materials 为背诵专用键，不入本端点（T11 背诵端点直读索引）。
    workspace_dir = get_path_service().get_workspace_dir()
    index_paths = sorted(workspace_dir.glob("*/grade*_index.json"))
    if not index_paths:
        return {"courseware": [], "exercises": [], "voices": [], "figures": []}
    idx: dict = {"courseware": [], "exercises": [], "voices": [], "figures": []}
    for index_path in index_paths:
        loaded = _json.loads(index_path.read_text(encoding="utf-8"))
        for key in idx:
            idx[key].extend(loaded.get(key) or [])

    def _match(items: list) -> list:
        return [
            it for it in items
            if any(cid in it.get("chapter_ids", []) for cid in cids)
        ]

    exercises = _match(idx.get("exercises", []))

    # 闯关自适应选题（design §3.7）：薄弱优先 -> 到期复习 -> 已掌握抽查
    # best-effort：排序失败时回退原始顺序，不阻塞资源加载。
    # R1-c：访问码守卫必须在 try 之外——401 不能被 best-effort 吞掉（否则
    # 带 u 无码请求会绕过门禁直接返回资源）。
    adapted_summary: list[str] = []
    adapted = False
    _h5_cm = None
    if u:
        from deeptutor.multi_user.h5 import h5_user_guarded
        from deeptutor.multi_user.paths import user_context

        _h5_cm = user_context(h5_user_guarded(u, code, x_access_code))
    try:
        from deeptutor.learning.exercise_selector import select_exercises

        profile = None
        if _h5_cm is not None:
            # 在 h5 用户上下文下读取其学情画像（MU-2/T9：修复之前
            # select_exercises 无 profile 导致 ?u= 不个性化的问题）
            with _h5_cm:
                from deeptutor.learning.learner_profile import build_learner_profile

                profile = build_learner_profile(user_id=u)
        sel = select_exercises(exercises, profile=profile)
        exercises = sel["ordered"]
        adapted = sel["adapted"]
        adapted_summary = sel["summary"]
    except Exception:  # noqa: BLE001
        pass

    return {
        "courseware": _match(idx.get("courseware", [])),
        "exercises": exercises,
        "voices": _match(idx.get("voices", [])),
        "figures": _match(idx.get("figures", [])),
        "adaptive": {"adapted": adapted, "summary": adapted_summary},
    }


# ---------------------------------------------------------------------------
# recite 四端点（M25 三年级上批次 T11，规格 §4.6）：
# materials / check / attempts POST+GET。全带 u 门禁（u 非空时
# h5_user_guarded 强制访问码——R1-c 不变量同 chapter_overview）；
# check 零 LLM 纯算法（验收判例 7/10）；attempts POST 留档 + L1 事件
# recitation_completed 且与 FSRS 复习队列隔离（验收判例 9）。
# ---------------------------------------------------------------------------

class ReciteSegmentIn(BaseModel):
    """背诵判分请求的单段输入。"""
    idx: int
    text: str


class ReciteCheckRequest(BaseModel):
    """POST /recite/check 请求体（规格 §4.6）。

    segments（逐段）与 whole_text（整篇，审查 R1-必修2 契约：整篇参考
    = 全部段参考文本按 idx 顺序拼接）二选一，二者皆空/皆有 → 422。
    整篇判分结果以单条 per_segment（idx=0）返回——UI 整篇态只渲染一张卡。"""
    material_id: str
    mode: Literal["recite", "dictation"]
    input_mode: Literal["voice", "type"]
    segments: list[ReciteSegmentIn] = Field(default_factory=list)
    whole_text: str = ""


class ReciteAttemptRequest(BaseModel):
    """POST /recite/attempts 请求体（规格 §4.5 十四字段去 id/ts/u——
    id 服务端生成、ts 服务端打点、u 取守卫后的当前用户）。
    mode/input_mode 给默认值：守卫（401）先于业务语义，最小 body 亦可
    构造；数据完整性由 store 层模型 Literal 校验兜底。"""
    textbook_id: str = ""
    chapter_id: str = ""
    material_id: str
    material_title: str = ""
    mode: Literal["recite", "dictation"] = "recite"
    input_mode: Literal["voice", "type"] = "type"
    segmented: bool = False
    total_score: float = 0.0
    per_segment: list[dict] = Field(default_factory=list)
    wrong_chars: list[str] = Field(default_factory=list)
    homophones: list[str] = Field(default_factory=list)


def _glob_recite_materials() -> tuple[list[dict], dict[str, dict]]:
    """glob workspace/*/grade*_index.json 收集 recite_materials 键。

    返回 (materials 列表, material_id -> material 索引映射)。
    无键 = 空列表（七年级索引只有四消费键，自然为空——规格 §4.4）。
    """
    import json as _json

    from deeptutor.services.path_service import get_path_service

    workspace_dir = get_path_service().get_workspace_dir()
    materials: list[dict] = []
    by_id: dict[str, dict] = {}
    for index_path in sorted(workspace_dir.glob("*/grade*_index.json")):
        loaded = _json.loads(index_path.read_text(encoding="utf-8"))
        for m in (loaded.get("recite_materials") or []):
            materials.append(m)
            mid = m.get("id")
            if mid:
                by_id[mid] = m
    return materials, by_id


@router.get("/recite/materials")
def recite_materials(
    textbook_id: str = Query("", description="教材 id（路径对称参数，素材按章节过滤）"),
    chapter_id: str = Query("", description="章节 id"),
    u: str = Query("", description="H5 用户标识（?u=），缺省=admin"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header("", alias="X-Access-Code"),
):
    """该章节的背诵/默写素材（规格 §4.6 materials）。

    recite_materials 为背诵专用键（T7 泛化时明确不入 chapter_resources，
    本端点直读索引）；grade7 索引无该键 = 空列表。
    """
    from deeptutor.multi_user.h5 import h5_user_guarded

    # R1-c：守卫在 try/业务之外——401 不能被吞（同 chapter_overview）。
    h5_user_guarded(u, code, x_access_code)

    materials, _by_id = _glob_recite_materials()
    items = [m for m in materials if chapter_id in (m.get("chapter_ids") or [])]
    return {"items": items, "count": len(items)}


@router.post("/recite/check")
def recite_check(
    body: ReciteCheckRequest,
    u: str = Query("", description="H5 用户标识（?u=），缺省=admin"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header("", alias="X-Access-Code"),
):
    """背诵判分（零 LLM 纯算法，规格 §4.6 check；验收判例 7/10）。

    check_segment 逐段判定 + 按原文归一化单元数加权合成篇级总分
    （§4.3 段/篇两级）；响应 {per_segment, total_score, wrong_chars,
    homophones}——分数带阈值由前端消费，端点只返回分数。
    """
    from deeptutor.learning.recitation.matcher import check_segment, normalize
    from deeptutor.multi_user.h5 import h5_user_guarded

    h5_user_guarded(u, code, x_access_code)

    _materials, by_id = _glob_recite_materials()
    material = by_id.get(body.material_id)
    if not material:
        raise HTTPException(status_code=404, detail="背诵素材不存在")

    lang = "english" if material.get("subject") == "english" else "chinese"
    segments_src = sorted(material.get("segments") or [], key=lambda s: s.get("idx", 0))
    ref_by_idx = {s.get("idx"): s.get("text", "") for s in segments_src}

    # 整篇模式（审查 R1-必修2）：参考文本=全部段拼接，单卡返回。
    # 此前前端整篇只送 {idx:0, whole} → 仅与第 0 段比对，其余全文进
    # extra 不入分母（对 0 段+废话可判满分）。
    if body.whole_text:
        if body.segments:
            raise HTTPException(status_code=422, detail="segments 与 whole_text 只能二选一")
        body.segments = [ReciteSegmentIn(idx=0, text=body.whole_text)]
        ref_by_idx = {0: "\n".join(s.get("text", "") for s in segments_src)}
    elif not body.segments:
        raise HTTPException(status_code=422, detail="segments 与 whole_text 必须其一")

    per_segment: list[dict] = []
    wrong_chars: list[str] = []
    homophones: list[str] = []
    weighted = 0.0
    total_units = 0
    for seg in body.segments:
        ref_text = ref_by_idx.get(seg.idx, "")
        result = check_segment(ref_text, seg.text, lang=lang)
        per_segment.append({
            "idx": seg.idx,
            "score": result["score"],
            "diff": {
                "wrong_chars": result["wrong_chars"],
                "homophones": result["homophones"],
                "missing": result["missing"],
                "extra": result["extra"],
            },
        })
        wrong_chars.extend(result["wrong_chars"])
        homophones.extend(result["homophones"])
        # 篇级总分按原文归一化单元数加权（§4.3）：score_i 已是段内
        # (正确+同音)/段归一化单元数，还原分子后按总单元数归一。
        n_units = len(normalize(ref_text, lang=lang))
        weighted += result["score"] * n_units
        total_units += n_units

    total_score = (weighted / total_units) if total_units else 0.0
    return {
        "per_segment": per_segment,
        "total_score": total_score,
        "wrong_chars": wrong_chars,
        "homophones": homophones,
    }


@router.post("/recite/attempts")
def recite_attempt_create(
    body: ReciteAttemptRequest,
    u: str = Query("", description="H5 用户标识（?u=），缺省=admin"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header("", alias="X-Access-Code"),
):
    """留档一次背诵/默写记录（规格 §4.6 attempts POST；判例 9）。

    store 留档 + L1 学情事件 recitation_completed（learner_profile L608
    契约）；与 FSRS 复习队列隔离——背诵不入复习调度，事件只进 trace。
    """
    from deeptutor.learning.recitation.store import RecitationStore
    from deeptutor.multi_user.h5 import h5_user_guarded
    from deeptutor.multi_user.paths import user_context

    h5_user = h5_user_guarded(u, code, x_access_code)

    with user_context(h5_user):
        att = RecitationStore().record(
            u=u,
            textbook_id=body.textbook_id,
            chapter_id=body.chapter_id,
            material_id=body.material_id,
            material_title=body.material_title,
            mode=body.mode,
            input_mode=body.input_mode,
            segmented=body.segmented,
            total_score=body.total_score,
            per_segment=body.per_segment,
            wrong_chars=body.wrong_chars,
            homophones=body.homophones,
        )
        from deeptutor.learning.learner_profile import emit_learning_event

        emit_learning_event(
            kind="recitation_completed",
            payload={
                "chapter_id": body.chapter_id,
                "material_title": body.material_title,
                "mode": body.mode,
                "score": body.total_score,
            },
        )
    return {"id": att.id}


@router.get("/recite/attempts")
def recite_attempts_list(
    chapter_id: str = Query("", description="章节 id（空 = 全部）"),
    u: str = Query("", description="H5 用户标识（?u=），缺省=admin"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header("", alias="X-Access-Code"),
):
    """背诵历史：最近 50 条倒序（规格 §4.6 GET），chapter_id 可选过滤。"""
    from deeptutor.learning.recitation.store import RecitationStore
    from deeptutor.multi_user.h5 import h5_user_guarded
    from deeptutor.multi_user.paths import user_context

    h5_user = h5_user_guarded(u, code, x_access_code)

    with user_context(h5_user):
        attempts = RecitationStore().list_attempts(
            u=u or None, chapter_id=chapter_id or None,
        )
    items = [a.model_dump(mode="json") for a in attempts]
    return {"items": items, "count": len(items)}


# ---------------------------------------------------------------------------
# tab 导出端点（M25 三年级上批次 T16，规格 §3.1/§3.2；验收判例 6）
# ---------------------------------------------------------------------------

# 10 个合法 tab → 中文标签（文件名用；与桌面 ChapterTabs/h5 learn 页对齐）
_EXPORT_TAB_LABELS: dict[str, str] = {
    "original": "原文",
    "internal_books": "内部书籍",
    "courseware": "课件",
    "voice": "语音视频",
    "knowledge": "知识点",
    "exercise": "闯关",
    "wrong": "章节错题",
    "notes": "笔记",
    "memory": "章节记忆",
    "ai": "AI资源",
}

# format → (media_type, 扩展名)
_EXPORT_FORMATS: dict[str, tuple[str, str]] = {
    "pdf": ("application/pdf", "pdf"),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", "docx"),
}


def _sanitize_filename(name: str) -> str:
    """Windows/通用文件名非法字符清洗；清洗后为空回退 export。"""
    cleaned = re.sub(r'[\\/:*?"<>|\r\n\t]', "", name).strip()
    return cleaned or "export"


def _build_tab_doc(
    tab: str,
    chapter,
    chapter_id: str,
    chapter_name: str,
    textbook_name: str,
    u: str,
    answer_sheet: int,
    subject: str = "",
    textbook_id: str = "",
):
    """端点层取数 → tab_export.builders 装配（builders 为纯函数）。

    内容类数据（原文页/书籍/知识点/索引资源）在 admin 上下文取；
    学情类（错题/笔记/画像）在当前用户上下文取（外层 user_context
    已建立——h5_progress._content_store 同款双上下文惯例）。
    chapter_id 为章节 id 字符串（chapter 对象可能为 None，索引类资源
    按 id 过滤需要它——审查 R1-必修1：缺失会 NameError 被吞 → 恒空页）。
    任何取数失败/无数据 → None → 端点回退空数据提示页（§3.2 不报错）。
    answer_sheet 仅 exercise 有效，其他 tab 忽略。
    """
    from deeptutor.learning.tab_export import builders
    from deeptutor.multi_user.paths import local_admin_user

    tab_label = _EXPORT_TAB_LABELS[tab]
    title = " ".join(p for p in (textbook_name, chapter_name, tab_label) if p)

    def _admin_ctx():
        from deeptutor.multi_user.paths import user_context

        return user_context(local_admin_user())

    try:
        if tab == "original":
            from deeptutor.learning.curriculum import CurriculumStore

            with _admin_ctx():
                cs = CurriculumStore()
                if chapter:
                    pages = cs.list_pages(chapter.textbook_id)
                elif textbook_id:
                    # 教材级导出（H5 原文页 T20）：全书页不按章节过滤
                    pages = cs.list_pages(textbook_id)
                else:
                    pages = []
            rows = []
            for p in pages:
                num = p.page_num or 0
                if chapter and chapter.page_start is not None and num < chapter.page_start:
                    continue
                if chapter and chapter.page_end is not None and num > chapter.page_end:
                    continue
                rows.append({"page_num": p.page_num, "ocr_text": p.ocr_text or ""})
            return builders.build_original(rows, title=title)

        if tab == "internal_books":
            from deeptutor.book.engine import get_book_engine

            cids: set[str] = set()
            if chapter:
                cids.add(chapter.id)
                if chapter.parent_id:
                    cids.add(chapter.parent_id)
            with _admin_ctx():
                books = []
                for b in get_book_engine().list_books():
                    meta = b.metadata or {}
                    if meta.get("curriculum_chapter_id") in cids and b.status.value != "archived":
                        books.append({
                            "id": b.id, "title": b.title, "status": b.status.value,
                            "chapter_count": b.chapter_count, "page_count": b.page_count,
                        })
            spines = {}
            return builders.build_internal_books(books, spines, title=title)

        if tab == "knowledge":
            from deeptutor.learning.curriculum import CurriculumStore
            from deeptutor.learning.learner_profile import build_learner_profile

            if not chapter or not chapter.kp_ids:
                return None
            subject = getattr(chapter, "subject", None) or "math"
            with _admin_ctx():
                cs = CurriculumStore()
                all_kps = cs.list_kps(subject)
            kp_map = {k.id: k for k in all_kps}
            profile = build_learner_profile(user_id=u)
            rows = []
            for kid in chapter.kp_ids:
                k = kp_map.get(kid)
                if not k:
                    continue
                mastery_row = profile.kp_mastery.get(kid)
                rows.append({
                    "name": k.name,
                    "description": k.description or "",
                    "difficulty": k.difficulty,
                    "mastery": mastery_row.mastery if mastery_row else None,
                })
            return builders.build_knowledge(rows, title=title)

        if tab == "exercise":
            from deeptutor.learning.curriculum import CurriculumStore

            with _admin_ctx():
                exercises = _glob_index_key("exercises")
            exercises = [
                it for it in exercises
                if chapter_id in (it.get("chapter_ids") or [])
            ]
            if not exercises:
                return None
            kp_names: dict[str, str] = {}
            try:
                with _admin_ctx():
                    cs = CurriculumStore()
                    for subj in ("math", "chinese", "english"):
                        for k in cs.list_kps(subj):
                            kp_names[k.id] = k.name
            except Exception:  # noqa: BLE001 — kp 名解析失败不阻塞导出
                pass
            groups: dict[str, list[dict]] = {}
            order: list[str] = []
            for it in exercises:
                gtitle = it.get("title") or it.get("id") or "题组"
                # 真实索引形态（init_grade3）：组级 {title, chapter_ids,
                # questions:[{ask,...}]}；兼容扁平单题 {ask,...}
                questions = it.get("questions") or ([it] if it.get("ask") else [])
                if not questions:
                    continue
                if gtitle not in groups:
                    groups[gtitle] = []
                    order.append(gtitle)
                for q in questions:
                    groups[gtitle].append({
                        "ask": q.get("ask", ""),
                        "options": list(q.get("options") or []),
                        "answer": q.get("answer"),
                        "why": q.get("why", ""),
                        "kp_name": kp_names.get(q.get("kp_id") or "", ""),
                    })
            payload = [{"title": t, "questions": groups[t]} for t in order if groups[t]]
            return builders.build_exercise(
                payload, title=title, answer_sheet=bool(answer_sheet),
            )

        if tab == "wrong":
            from deeptutor.learning.mother_question import MotherQuestionStore

            all_mq = MotherQuestionStore().list_all_mothers(status="active")
            rows = [
                {
                    "title": m.title,
                    "question_text": m.question_text,
                    "wrong_answer": m.wrong_answer or "",
                    "standard_answer": m.standard_answer or "",
                    "detailed_analysis": m.detailed_analysis or "",
                    "mastery_status": m.mastery_status,
                }
                for m in all_mq
                if (m.chapter_id or "") == chapter_id
            ]
            return builders.build_wrong(rows, title=title)

        if tab == "notes":
            from deeptutor.services.notebook import notebook_manager

            notebooks = notebook_manager.list_notebooks()
            rows = []
            for nb in notebooks:
                # 章节 scope best-effort：名称/描述含章节名视为本章笔记
                if chapter_name and chapter_name not in (nb.get("name", "") + nb.get("description", "")):
                    continue
                detail = notebook_manager.get_notebook(nb["id"]) or {}
                parts: list[str] = []
                for rec in detail.get("records") or []:
                    line = str(rec.get("title", "") or "")
                    body = str(rec.get("summary") or rec.get("output") or "")
                    parts.append(f"{line}：{body}" if line and body else (line or body))
                rows.append({
                    "title": nb.get("name", "") or "笔记",
                    "content": "\n".join(p for p in parts if p),
                })
            return builders.build_notes(rows, title=title)

        if tab == "memory":
            from deeptutor.learning.curriculum import CurriculumStore
            from deeptutor.learning.learner_profile import build_learner_profile

            kp_ids = list(chapter.kp_ids) if chapter and chapter.kp_ids else []
            with _admin_ctx():
                cs = CurriculumStore()
                all_kps = cs.list_kps(getattr(chapter, "subject", None) or "math") if chapter else []
            kp_map = {k.id: k for k in all_kps}
            profile = build_learner_profile(user_id=u)
            rows = []
            for kid in kp_ids:
                k = kp_map.get(kid)
                if not k:
                    continue
                m = profile.kp_mastery.get(kid)
                rows.append({
                    "name": k.name,
                    "mastery": m.mastery if m else None,
                    "status": m.status if m else "new",
                })
            summary = ""
            if rows:
                mastered = [r for r in rows if r["mastery"] is not None]
                avg = (
                    round(sum(r["mastery"] for r in mastered) / len(rows) * 100)
                    if mastered else 0
                )
                summary = f"本章 {len(rows)} 个知识点，平均掌握度 {avg}%"
            return builders.build_memory(rows, summary, title=title)

        if tab == "ai":
            with _admin_ctx():
                resources = {
                    "courseware": [
                        it for it in _glob_index_key("courseware")
                        if chapter_id in (it.get("chapter_ids") or [])
                    ],
                    "voices": [
                        it for it in _glob_index_key("voices")
                        if chapter_id in (it.get("chapter_ids") or [])
                    ],
                    "figures": [
                        it for it in _glob_index_key("figures")
                        if chapter_id in (it.get("chapter_ids") or [])
                    ],
                    "adaptive": {},
                }
                exercises = [
                    it for it in _glob_index_key("exercises")
                    if chapter_id in (it.get("chapter_ids") or [])
                ]
            resources["adaptive"] = {
                "adapted": [],
                "summary": (
                    f"本章自适应练习池共 {sum(len(it.get('questions') or []) or (1 if it.get('ask') else 0) for it in exercises)} 题"
                    if exercises else ""
                ),
            }
            return builders.build_ai(resources, title=title)

        if tab == "courseware":
            with _admin_ctx():
                units_data = _load_units_data(subject)
                cw_goals: list[str] = []
                for it in _glob_index_key("courseware"):
                    if chapter_id in (it.get("chapter_ids") or []):
                        cw_goals = [str(g) for g in (it.get("goals") or [])]
                        break
            return builders.build_courseware(
                units_data, subject=subject, chapter_name=chapter_name,
                title=title, goals=cw_goals or None, book_spine=None,
            )

        if tab == "voice":
            with _admin_ctx():
                units_data = _load_units_data(subject)
                voice_items = [
                    it for it in _glob_index_key("voices")
                    if chapter_id in (it.get("chapter_ids") or [])
                ]
            return builders.build_voice(
                units_data, subject=subject, chapter_name=chapter_name,
                title=title, voices=voice_items,
            )

        # recite 等其余 tab：T18 富媒体 builder 落位；此前统一空数据页
        return None
    except Exception:  # noqa: BLE001 — 单 tab 取数失败不阻塞导出（§3.2）
        logger.warning("tab 导出取数失败 tab=%s chapter_id=%s", tab, chapter_id, exc_info=True)
        return None


def _glob_index_key(key: str) -> list[dict]:
    """glob workspace/*/grade*_index.json 合并指定索引键（T7 泛化同款）。"""
    import json as _json

    from deeptutor.services.path_service import get_path_service

    workspace_dir = get_path_service().get_workspace_dir()
    items: list[dict] = []
    for index_path in sorted(workspace_dir.glob("*/grade*_index.json")):
        try:
            loaded = _json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 — 坏索引跳过
            continue
        items.extend(loaded.get(key) or [])
    return items


_UNITS_DATA_FILES = {
    "math": "units_data_math.json",
    "chinese": "units_data_chinese.py",
    "english": "units_data_english.py",
}


def _load_units_data(subject: str):
    """加载 units_data 工作区副本（T18；scripts/init_grade3.py 同款加载惯例）。

    数学 = JSON ``{"units": [...]}``；语文/英语 = .py 数据模块常量
    ``UNITS``（list / dict）。无副本（grade7）或加载失败 → None，
    由 builder 走 goals+spine 降级。禁止 sys.path 注入。
    """
    import importlib.util
    import json as _json

    from deeptutor.services.path_service import get_path_service

    filename = _UNITS_DATA_FILES.get(subject)
    if not filename:
        return None
    paths = sorted(get_path_service().get_workspace_dir().glob(f"*/{filename}"))
    if not paths:
        return None
    path = paths[0]
    try:
        if path.suffix == ".json":
            data = _json.loads(path.read_text(encoding="utf-8"))
            units = data.get("units")
            return units if isinstance(units, list) else None
        spec = importlib.util.spec_from_file_location(f"{path.stem}_tab_export_data", path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        units = getattr(module, "UNITS", None)
        return units if isinstance(units, (list, dict)) else None
    except Exception:  # noqa: BLE001 — 数据副本损坏不阻塞导出
        return None


@router.get("/chapter/{chapter_id}/export")
def export_chapter_tab(
    chapter_id: str,
    tab: str = Query("original", description="导出的 tab（合法值之一）"),
    format: str = Query("pdf", description="导出格式 pdf|docx"),
    answer_sheet: int = Query(0, description="答题卡版式（仅 exercise 有效，其他 tab 忽略）"),
    textbook_id: str = Query("", description="教材 id（H5 原文页教材级导出，T20；chapter 未命中时生效）"),
    u: str = Query("", description="H5 用户标识（?u=），缺省=admin"),
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header("", alias="X-Access-Code"),
):
    """导出某章节某 tab 的内容为 PDF/DOCX（规格 §3.1/§3.2）。

    - tab/format 非法 → 422；带 u 无码 → 401（h5_user_guarded）
    - 章节无该 tab 数据 → 200 + 空数据提示页文档（不报错）
    - 教材级导出（H5 原文页）：chapter_id 用 "-" 占位 + textbook_id 直通
    - 文件名 "{教材名}-{章节名}-{tab中文}-{YYYYMMDD}.{ext}"，空槽不残留
      连字符；中文经 quote 编码（mother_question.py L1413-1422 同款双形态）。
    """
    from deeptutor.learning.curriculum import CurriculumStore
    from deeptutor.learning.tab_export.model import empty_doc
    from deeptutor.learning.tab_export.render_docx import render_docx
    from deeptutor.learning.tab_export.render_pdf import render_pdf
    from deeptutor.multi_user.h5 import h5_user_guarded
    from deeptutor.multi_user.paths import user_context

    if tab not in _EXPORT_TAB_LABELS:
        raise HTTPException(status_code=422, detail=f"未知 tab: {tab}")
    if format not in _EXPORT_FORMATS:
        raise HTTPException(status_code=422, detail=f"未知 format: {format}")
    media_type, ext = _EXPORT_FORMATS[format]

    # R1-c：守卫在业务之外——401/422 不能被 best-effort 吞掉
    h5_user = h5_user_guarded(u, code, x_access_code)

    # 章节对象与名称（查不到 chapter=None，回退 id，不阻塞导出）
    chapter = None
    chapter_name, textbook_name, subject = chapter_id, "", ""
    try:
        cs = CurriculumStore()
        for c in cs.list_chapters(""):
            if c.id == chapter_id:
                chapter = c
                chapter_name = c.name
                tb = next(
                    (t for t in cs.list_textbooks("") if t.id == c.textbook_id),
                    None,
                )
                textbook_name = tb.name if tb else ""
                subject = (tb.subject if tb else "") or ""
                break
        if chapter is None and textbook_id:
            # 教材级导出（H5 原文页 T20）：章节槽留空，文件名不重复教材名
            chapter_name = ""
            if not textbook_name:
                tb = next(
                    (t for t in cs.list_textbooks("") if t.id == textbook_id),
                    None,
                )
                textbook_name = tb.name if tb else ""
                subject = (tb.subject if tb else "") or ""
    except Exception:  # noqa: BLE001 — 名称解析失败不阻塞导出
        pass

    tab_label = _EXPORT_TAB_LABELS[tab]
    title = " ".join(p for p in (textbook_name, chapter_name, tab_label) if p)

    with user_context(h5_user):
        doc = _build_tab_doc(
            tab, chapter, chapter_id, chapter_name, textbook_name, u,
            answer_sheet, subject=subject, textbook_id=textbook_id,
        )
    if doc is None:
        doc = empty_doc(title)
    doc.title = doc.title or title
    doc.meta = doc.meta or [{"label": "导出时间", "value": date.today().strftime("%Y-%m-%d")}]

    payload = render_pdf(doc) if format == "pdf" else render_docx(doc)
    name_parts = [p for p in (textbook_name, chapter_name, tab_label) if p]
    filename = _sanitize_filename(
        "-".join(name_parts) + f"-{date.today().strftime('%Y%m%d')}",
    ) + f".{ext}"
    filename_encoded = quote(filename)
    return Response(
        content=payload,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f"attachment; filename={filename_encoded}; "
                f"filename*=UTF-8''{filename_encoded}"
            )
        },
    )
