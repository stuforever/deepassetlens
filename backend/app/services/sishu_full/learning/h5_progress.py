"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from app.services.sishu_full.learning.curriculum import CurriculumStore
from app.services.sishu_full.learning.models import (
    KnowledgePoint,
    KnowledgeType,
    LearningModule,
    LearningProgress,
)
from app.services.sishu_full.learning.service import LearningService

logger = logging.getLogger(__name__)

# grade7 数据里 148 个知识点均无 type 字段，影子进度统一按 MEMORY 处理
# （确保 FSRS 复习队列生成——grade_and_record 里 kp_type is None 会跳过调度）。
_DEFAULT_KP_TYPE = KnowledgeType.MEMORY

_CHAPTER_PREFIX_RE = re.compile(r"^\d+(\.\d+)*[_ ]")


def _content_store() -> CurriculumStore:
    """返回 admin 上下文的内容 store（章节/知识点为内容类，全局共享）。

    H5 用户上下文隔离的是 data-class（学习进度/母题/画像），而教材章节/
    知识点是内容数据，所有用户共用——故在 admin 上下文读取。
    """
    from app.services.sishu_full.multi_user.paths import local_admin_user, user_context

    with user_context(local_admin_user()):
        return CurriculumStore()


def _strip_chapter_prefix(name: str) -> str:
    """`1.1_正数和负数` -> `正数和负数`；`1.2 有理数` -> `有理数`。"""
    return _CHAPTER_PREFIX_RE.sub("", name or "").strip()


# --------------------------------------------------------------------------- #
# 知识点归属解析                                                               #
# --------------------------------------------------------------------------- #


def _chapter_map(store: CurriculumStore) -> dict[str, Any]:
    """chapter id -> chapter dict（含 kp_ids / name）。"""
    return {c.id: c for c in store.list_chapters("")}


def _find_chapter_by_name(store: CurriculumStore, name: str):
    """按去前缀后的章节名匹配 chapter（grade7 exercise 常引用父章名）。"""
    needle = _strip_chapter_prefix(name or "")
    if not needle:
        return None
    best, best_score = None, 0
    for c in store.list_chapters(""):
        cand = _strip_chapter_prefix(c.name or "")
        # 精确 / 包含匹配，取最长重合
        score = 0
        if cand == needle:
            score = 100
        elif needle and (needle in cand or cand in needle):
            score = len(needle)
        if score > best_score:
            best, best_score = c, score
    return best


def resolve_kp_for_exercise(
    exercise: dict[str, Any], store: CurriculumStore | None = None
) -> tuple[str, str]:
    """返回 (kp_id, kp_name)：从 exercise 定位到归属知识点。

    链路：exercise.chapter_ids -> chapter.kp_ids -> 与题目名最匹配的 kp；
    fallback：chapter 第一个 kp；再 fallback：构造占位 kp（exercise 名）。
    """
    store = store or _content_store()
    ch_map = _chapter_map(store)
    kp_by_id = {k.id: k for k in store.list_kps()}

    # 1) exercise 直引 chapter
    targets: list[Any] = []
    for cid in exercise.get("chapter_ids") or []:
        c = ch_map.get(cid)
        if c is not None:
            targets.append(c)
    if not targets:
        # 2) 按名称反查 chapter
        found = _find_chapter_by_name(store, str(exercise.get("title") or ""))
        if found is not None:
            targets.append(found)

    title = _strip_chapter_prefix(str(exercise.get("title") or ""))
    for c in targets:
        kps = [kp_by_id[kid] for kid in (c.kp_ids or []) if kid in kp_by_id]
        if not kps:
            continue
        # 与题目名最匹配的 kp
        best, best_score = kps[0], 0
        for kp in kps:
            score = 0
            if title and (title in kp.name or kp.name in title):
                score = len(title)
            if score > best_score:
                best, best_score = kp, score
        return best.id, best.name

    # 3) fallback：无 chapter 关联时以 exercise 名为占位 kp
    return f"ex_{exercise.get('id', '')}", title or str(exercise.get("id") or "")


def _kp_for_id(kp_id: str, name: str, module_id: str) -> KnowledgePoint:
    return KnowledgePoint(id=kp_id, name=name, type=_DEFAULT_KP_TYPE, module_id=module_id)


# --------------------------------------------------------------------------- #
# 影子进度                                                                     #
# --------------------------------------------------------------------------- #


def ensure_h5_progress(
    chapter_id: str,
    module_id: str | None = None,
    service: LearningService | None = None,
) -> LearningProgress:
    """为章节构造影子 LearningProgress（不存在则建，存在则复用）。

    不建完整 PathPlanner 路径：以章节为模块、章节关联知识点为 kp 集合，
    book_id 用 ``shadow_<chapter_id>`` 避免与桌面 mastery 进度冲突。
    """
    service = service or LearningService()
    store = _content_store()  # 内容（章节/知识点）admin 共享；进度写当前 h5 context
    chapter = None
    for c in store.list_chapters(""):
        if c.id == chapter_id:
            chapter = c
            break
    if chapter is None:
        raise LookupError(f"chapter not found: {chapter_id}")

    book_id = f"shadow_{chapter_id}"
    progress = service.get_or_create(book_id)
    module_id = module_id or chapter_id

    kp_by_id = {k.id: k for k in store.list_kps()}
    kps: list[KnowledgePoint] = []
    seen: set[str] = set()
    for kid in chapter.kp_ids or []:
        if kid in seen:
            continue
        seen.add(kid)
        k = kp_by_id.get(kid)
        name = k.name if k is not None else kid
        kps.append(_kp_for_id(kid, name, module_id))

    # 章节无关联 kp 时：以章节名占位，保证至少有一个可判 kp
    if not kps:
        kps.append(_kp_for_id(f"ch_{chapter_id}", chapter.name or chapter_id, module_id))

    # 已存在且模块未变（同名同序 + kp 集一致）则跳过重建——kp 集对给定章节
    # 是稳定的，避免每次答题全量 replace_modules+save。
    existing_module = next((m for m in (progress.modules or []) if m.id == module_id), None)
    if existing_module is not None:
        existing_kp_ids = {kp.id for kp in (existing_module.knowledge_points or [])}
        wanted_kp_ids = {kp.id for kp in kps}
        if existing_kp_ids == wanted_kp_ids and (existing_module.name or "") == (chapter.name or module_id):
            module = existing_module
        else:
            module = LearningModule(id=module_id, name=chapter.name or module_id, order=0, knowledge_points=kps)
            service.replace_modules(progress, [module])
    else:
        module = LearningModule(id=module_id, name=chapter.name or module_id, order=0, knowledge_points=kps)
        service.replace_modules(progress, [module])

    # knowledge_types 统一填充 MEMORY（数据缺 type），确保 FSRS 调度执行
    for kp in kps:
        if kp.id not in progress.knowledge_types:
            progress.knowledge_types[kp.id] = _DEFAULT_KP_TYPE
    service.save(progress)
    return progress


def _find_module_kp(progress: LearningProgress, kp_id: str):
    """从 progress.modules 找 kp 的 name（grade_and_record 事件用）。"""
    for mod in progress.modules:
        for kp in mod.knowledge_points:
            if kp.id == kp_id:
                return kp
    return None


# --------------------------------------------------------------------------- #
# 判题 + 落库                                                                  #
# --------------------------------------------------------------------------- #


def _normalize_expected(question: dict[str, Any]) -> str:
    """归一 expected answer 为 grade_answer 可用字符串。

    choice：answer 是选项索引 int（如 0/3）-> 转 str（与 user_answer 选项序号精确比）。
    fill：answer 是多候选 list -> 用 `；` 连接 + question_type=open（关键词匹配>=0.6）。
    """
    ans = question.get("answer")
    qtype = str(question.get("type") or "choice")
    if isinstance(ans, (int, float)) and not isinstance(ans, bool):
        return str(ans)
    if isinstance(ans, list):
        return "；".join(str(a) for a in ans if str(a).strip())
    return str(ans or "").strip()


def _question_type_for(question: dict[str, Any]) -> str:
    qtype = str(question.get("type") or "choice")
    if qtype == "fill":
        return "open"  # 多候选答案 -> 关键词匹配
    if qtype in ("choice", "short", "open"):
        return qtype
    return "choice"


def _is_fill(question: dict[str, Any]) -> bool:
    return str(question.get("type") or "").lower() == "fill"


def _norm(s: str) -> str:
    """判题规范化：小写 + 去除全角空格 + 归一全角减号/摄氏度。"""
    out = str(s or "").lower().strip()
    out = out.replace("−", "-").replace("﹣", "-").replace("－", "-")
    out = out.replace("℃", "c").replace("°c", "c")
    out = "".join(out.split())
    return out


def _fill_accepts(question: dict[str, Any], user_answer: str) -> bool:
    """fill 题：用户答案命中任一候选（规范化比较）即正确。"""
    ans = question.get("answer")
    if not isinstance(ans, list) or not ans:
        return False
    user = _norm(user_answer)
    if not user:
        return False
    return any(_norm(str(a)) == user for a in ans)


def grade_h5_exercise(
    *,
    chapter_id: str,
    question_id: str,
    question_type: str,
    question_text: str,
    user_answer: str,
    expected_answer: str,
    exercise: dict[str, Any] | None = None,
    question: dict[str, Any] | None = None,
    scheduler=None,
    attempt_id: str = "",
    kp_id_override: str = "",        # PG-2：LLM 生成题自带 kp_id，直填优先（避免 ex_ 占位）
    expected_answer_pg: str = "",    # PG-2：生成题自带标准答案（choice=字母/fill=文本）
) -> dict[str, Any]:
    """影子进度上判一题并走完整闭环，返回前端可用结果。

    复用 LearningService.grade_and_record（判题/掌握度/FSRS/错题沉淀/事件）。

    PG-2（M15）：LLM 生成题不在 grade7 题库，前端上报自带 kp_id（+标准答案）
    时直填归属与答案，跳过反查——掌握度落在题目声明的真实 kp 上，而非占位 ex_。

    E3（M12）幂等：同 attempt_id 的补报直接返回当前掌握度快照（deduped），
    跳过 mastery/error/FSRS/mother/事件等全部副作用——离线 outbox 联网
    重放时副作用只发生一次。
    """
    from app.services.sishu_full.learning.scheduler import SpacedRepetitionScheduler

    service = LearningService()
    progress = ensure_h5_progress(chapter_id, service=service)
    scheduler = scheduler or SpacedRepetitionScheduler()

    # 知识点归属：生成题直填 > 反查 exercise > 占位
    if kp_id_override:
        kp_id = kp_id_override
        _kp = _find_module_kp(progress, kp_id)
        kp_name = _kp.name if _kp else kp_id_override
    else:
        kp_id, kp_name = resolve_kp_for_exercise(exercise or {})
    # 生成题答案直填（choice=字母/fill=文本），否则走 expected_answer/反查
    if expected_answer_pg:
        expected_answer = expected_answer_pg

    # E3 幂等短路：命中已处理 attempt_id -> 直接返回当前快照，不落副作用
    if attempt_id and attempt_id in progress.attempt_ids:
        mastery = progress.mastery_levels.get(kp_id)
        next_review = None
        if kp_id in progress.repetition_states:
            ts = progress.repetition_states[kp_id].next_review_at
            next_review = time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
        return {
            "ok": True,
            "deduped": True,
            "is_correct": None,
            "kp_id": kp_id,
            "kp_name": kp_name,
            "mastery": mastery,
            "next_review_at": next_review,
            "recorded_mother": None,
            "weak_now": None,
        }
    if attempt_id:
        progress.attempt_ids.append(attempt_id)
        progress.attempt_ids = progress.attempt_ids[-500:]
        service.save(progress)

    # 归一 expected（choice int / fill list -> str）
    exp = expected_answer
    if question is not None:
        # 有完整题目对象时，优先以其答案 + 归一后的题型为准
        # （fill 多候选答案 -> open 关键词匹配，避免原样 fill 判题失败）
        if not expected_answer:
            exp = _normalize_expected(question)
        question_type = _question_type_for(question)

    # 若 kp 不在影子模块（反查失败落到占位），仍允许判题——grade_and_record
    # 对任意 kp_id 都能记录 attempt / 更新 mastery。
    if question is not None and _is_fill(question) and not expected_answer:
        # fill 多候选答案：用户答案命中任一候选即正确（规范化比较），
        # 不套 grade_answer 的 open 关键词比例（比例法对"候选集"语义颠倒）。
        is_correct = _fill_accepts(question, user_answer)
    else:
        is_correct = service.grade_and_record(
            progress,
            question_id=question_id,
            knowledge_point_id=kp_id,
            module_id=progress.modules[0].id if progress.modules else chapter_id,
            user_answer=user_answer,
            expected_answer=exp,
            question_type=question_type,
            scheduler=scheduler,
        )

    mastery = progress.mastery_levels.get(kp_id)
    next_review = None
    if kp_id in progress.repetition_states:
        ts = progress.repetition_states[kp_id].next_review_at
        next_review = time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))

    # 该 kp 是否被判为薄弱：答错 且 掌握度低于画像判弱共享阈值
    # （WEAK_MASTERY 见 deeptutor.learning.learner_profile）——答对一题即
    # 不算弱，避免单题即时反馈误伤刚学对的 kp。
    from app.services.sishu_full.learning.learner_profile import WEAK_MASTERY

    weak_now = bool(is_correct) is False and mastery is not None and float(mastery) < WEAK_MASTERY

    recorded_mother = False
    try:
        from app.services.sishu_full.learning.mother_question import MotherQuestionStore

        tag = f"auto:{kp_id}:{question_id}"
        items, _total = MotherQuestionStore().list_mothers(page_size=500)
        recorded_mother = any(tag in (m.tags or []) for m in items)
    except Exception:  # noqa: BLE001
        pass

    return {
        "ok": True,
        "is_correct": bool(is_correct),
        "kp_id": kp_id,
        "kp_name": kp_name,
        "mastery": mastery,
        "next_review_at": next_review,
        "recorded_mother": bool(recorded_mother),
        "weak_now": bool(weak_now),
    }


__all__ = [
    "ensure_h5_progress",
    "grade_h5_exercise",
    "resolve_kp_for_exercise",
]
