"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Header
from pydantic import BaseModel

from app.services.sishu_full.learning.learner_profile import (
    build_learner_profile,
    recommend_exercises,
    write_learning_l2_md,
)
from app.services.sishu_full.multi_user.h5 import h5_scope_dep

router = APIRouter()


@router.get("/learner-profile")
def get_learner_profile(
    u: str = Query("", description="用户标识（H5 ?u= 参数），作为 profile 维度"),
    openid: str = Query("", description="微信 openid（公众号遗留）；经 identity 映射"),
    _user=Depends(h5_scope_dep),
):
    """Return the aggregated learner profile (mastery map, weak/strong, due).

    *u*（H5 用户标识）优先；其次 *openid*（公众号遗留）会经
    ``openid_to_profile_openid`` 映射（parent -> 关联学生）。
    都未提供时返回 admin 默认画像（兼容单用户场景）。
    ``h5_scope_dep`` 把 data-class 读取隔离到对应 H5 用户工作区。
    """
    if u:
        user_id = u
        profile_openid = u
        src = "u"
    elif openid:
        from app.services.sishu_full.services.wechat_push.identity import openid_to_profile_openid

        profile_openid = openid_to_profile_openid(openid)
        user_id = profile_openid
        src = "openid"
    else:
        user_id = "default"
        profile_openid = ""
        src = "default"
    profile = build_learner_profile(user_id=user_id)
    return {
        "user_id": profile.user_id,
        "src": src,
        "openid": openid,
        "u": u,
        "profile_openid": profile_openid,
        "kp_mastery": {
            kid: {
                "kp_id": kp.kp_id,
                "kp_name": kp.kp_name,
                "subject": kp.subject,
                "mastery": kp.mastery,
                "attempts": kp.attempts,
                "correct_rate": kp.correct_rate,
                "last_practiced_at": kp.last_practiced_at,
                "next_review_at": kp.next_review_at,
                "status": kp.status,
                "error_types": kp.error_types,
            }
            for kid, kp in profile.kp_mastery.items()
        },
        "weak_points": [
            {"kp_id": kp.kp_id, "kp_name": kp.kp_name, "mastery": kp.mastery}
            for kp in (profile.kp_mastery.get(kid) for kid in profile.weak_points)
            if kp is not None
        ],
        "strong_points": [
            {"kp_id": kp.kp_id, "kp_name": kp.kp_name}
            for kp in (profile.kp_mastery.get(kid) for kid in profile.strong_points)
            if kp is not None
        ],
        "due_reviews": profile.due_reviews,
        "streak_days": profile.streak_days,
        "total_study_minutes": profile.total_study_minutes,
        "badges": profile.badges,
        "updated_at": profile.updated_at,
    }


@router.post("/learner-profile/refresh")
def refresh_learner_profile():
    """Best-effort regenerate the deterministic L2/L3 learning memory docs."""
    write_learning_l2_md()
    return {"ok": True}


# ── C3（M18-B）：今日面板 ────────────────────────────────────────────────────


def _greeting() -> str:
    from datetime import datetime

    h = datetime.now().hour
    if h < 5:
        return "夜深了"
    if h < 11:
        return "早上好"
    if h < 13:
        return "中午好"
    if h < 18:
        return "下午好"
    return "晚上好"


def _today_done() -> bool:
    """今天（学习事件意义上）是否已经练过/复习过。"""
    try:
        from app.services.sishu_full.learning.learner_profile import _learning_day_dates
        from datetime import date

        return date.today().isoformat() in set(_learning_day_dates())
    except Exception:
        return False


@router.get("/today-panel")
def today_panel(
    u: str = Query("", description="H5 用户标识"),
    _user=Depends(h5_scope_dep),
):
    """C3 今日面板聚合数据：问候/streak/到期数/路径进度/预计时间。

    数据全部现成：画像（streak/due/weak）+ 精通之路 progress + 今日活跃标记。
    """
    profile = build_learner_profile(user_id=u or "default")
    due = len(profile.due_reviews)
    due_names = [d.get("kp_name", "") for d in profile.due_reviews[:2]]

    # 路径进度：取最近更新的一个 mastery path
    path_info = None
    try:
        from app.services.sishu_full.api.routers.mastery_path import get_learning_service

        summaries = get_learning_service().list_progress()
        items = (summaries or {}).get("summaries", []) if isinstance(summaries, dict) else (summaries or [])
        if items:
            latest = max(items, key=lambda s: float(s.get("updated_at") or 0))
            kp_count = int(latest.get("kp_count") or 0)
            pct = float(latest.get("avg_mastery_pct") or 0.0)
            path_info = {
                "book_id": latest.get("book_id"),
                "name": latest.get("name") or "",
                "kp_count": kp_count,
                "avg_mastery_pct": round(pct, 1),
                "remaining_kp": max(0, round(kp_count * (1 - pct / 100.0))),
            }
    except Exception:
        path_info = None

    est_minutes = 0
    if due:
        est_minutes += due * 2  # 每张到期卡约 2 分钟
    if path_info and path_info["remaining_kp"]:
        est_minutes += 10  # 继续学习一段粗估 10 分钟
    est_minutes = max(est_minutes, 5) if (due or path_info) else 0

    weak_top = ""
    if profile.weak_points:
        weak_top = next(
            (kp.kp_name for kid in profile.weak_points if (kp := profile.kp_mastery.get(kid))),
            "",
        )

    done_today = _today_done()
    return {
        "u": u,
        "greeting": _greeting(),
        "streak_days": profile.streak_days,
        "due_count": due,
        "due_names": due_names,
        "path": path_info,
        "est_minutes": est_minutes,
        "done_today": done_today,
        "weak_top": weak_top,
    }


# ── C5（M18-B）：episodic 会话摘要入记忆 ─────────────────────────────────────


class SessionSummaryRequest(BaseModel):
    topics: list[str] = []       # 本次会话涉及的 KP / 主题名
    wins: list[str] = []         # 搞定了什么（如「负数乘方从薄弱变学习中」）
    stuck: str = ""              # 卡在哪（一句话）
    questions: int = 0           # 本次练了几题
    correct: int = 0             # 对了几题
    source: str = "practice"     # practice | mastery | chat | book


@router.post("/session-summary")
def post_session_summary(
    request: SessionSummaryRequest,
    u: str = Query("", description="H5 用户标识"),
    session_id: str = Query("", description="可选会话 id"),
    _user=Depends(h5_scope_dep),
):
    """C5 episodic 记忆：会话收尾时把「这次学了什么/搞定了什么/卡在哪」写进 L1
    （surface=learning, kind=session_summary），consolidator 自然汇入 L2，
    read_memory 可读 —— 下次 mastery 开场即可「接上话」。
    """
    from app.services.sishu_full.learning.learner_profile import emit_learning_event, compute_streak_days

    payload = {
        "topics": request.topics,
        "wins": request.wins,
        "stuck": request.stuck,
        "questions": request.questions,
        "correct": request.correct,
        "source": request.source,
        "streak_after": compute_streak_days(),
    }
    emit_learning_event(kind="session_summary", payload=payload, session_id=session_id or None)
    return {"ok": True}


# ── C2（M18-C）：内部书/教材阅读回流 ─────────────────────────────────────────


class ReadingEventRequest(BaseModel):
    book_id: str = ""
    chapter_title: str = ""
    page_index: int = 0
    source: str = "book"   # book | textbook


@router.post("/reading-event")
def post_reading_event(
    request: ReadingEventRequest,
    u: str = Query("", description="H5 用户标识"),
    _user=Depends(h5_scope_dep),
):
    """C2 阅读事件回流：翻页即上报（kind=book_progress），学情/周报可见。"""
    from app.services.sishu_full.learning.learner_profile import emit_learning_event

    if not request.book_id:
        raise HTTPException(status_code=422, detail="book_id required")
    emit_learning_event(
        kind="book_progress",
        payload={
            "book_id": request.book_id,
            "chapter_title": request.chapter_title,
            "page": request.page_index,
            "source": request.source,
        },
    )
    return {"ok": True}


# ── C7（M18-C）：生成题反馈三键 ──────────────────────────────────────────────


class QuestionFeedbackRequest(BaseModel):
    chapter_id: str = ""
    tier: str = ""
    version: int = 0
    question_id: str = ""
    tag: str = ""              # too_hard | too_easy | wrong
    question_text: str = ""


@router.post("/question-feedback")
def post_question_feedback(
    request: QuestionFeedbackRequest,
    u: str = Query("", description="H5 用户标识"),
    _user=Depends(h5_scope_dep),
):
    """C7 反馈三键入库：太难/太简单/题有误 -> L1（kind=question_feedback），
    作为 PG 生成提示词调优的数据积累。"""
    from app.services.sishu_full.learning.learner_profile import emit_learning_event

    if request.tag not in ("too_hard", "too_easy", "wrong"):
        raise HTTPException(status_code=422, detail="tag must be too_hard|too_easy|wrong")
    emit_learning_event(
        kind="question_feedback",
        payload={
            "chapter_id": request.chapter_id,
            "tier": request.tier,
            "version": request.version,
            "question_id": request.question_id,
            "tag": request.tag,
            "question_text": request.question_text[:200],
        },
    )
    return {"ok": True}


class _AskRequest(BaseModel):
    question: str = ""
    u: str = ""                      # H5 用户标识（默认 default）
    code: str = ""                   # R5批⑨：访问码（access_code 启用时必填）
    image_base64: str = ""           # 可选：拍照题图 base64 -> OCR 后答疑
    context_hint: str = ""           # 可选：额外上下文（如题目文本）
    max_chars: int = 800


@router.post("/ask")
async def ask(request: _AskRequest, x_access_code: str = Header("")):
    """H5 拍错题/答疑通用端点：文字提问或拍照题图 -> AI 讲解。

    复用 ChatOrchestrator（真实 LLM + 学情画像注入）。*u* 作为会话/画像
    维度；*image_base64* 存在时先 OCR 识别题目再答疑。内部包
    ``user_context(h5_user(u))`` 使画像读取与会话存储隔离到该用户。
    """
    from app.services.sishu_full.learning.learner_profile import build_learner_profile
    from app.services.sishu_full.multi_user.h5 import h5_user, user_context  # noqa: F401
    from app.services.sishu_full.services.wechat_push.chat import answer_with_orchestrator

    u = request.u or ""
    question = (request.question or "").strip()

    prompt_parts = []
    if request.image_base64:
        # 解码 base64 -> OCR
        import base64 as _b64

        try:
            raw = _b64.b64decode(request.image_base64)
            from app.services.sishu_full.learning.image_pipeline import ocr_image

            ocr_text = str(ocr_image(raw).get("text") or "").strip()
        except Exception:  # noqa: BLE001
            ocr_text = ""
        if ocr_text:
            prompt_parts.append(f"图片中识别到的题目文字：\n{ocr_text}")
    if question:
        prompt_parts.append(f"用户的补充说明：{question}")
    if not prompt_parts:
        return {"ok": False, "msg": "请提供问题文字或拍照题图", "answer": ""}
    prompt_parts.append("请识别这道题并给出：1）题目考查的知识点；2）分步解答；3）易错点提醒。")

    # 学情画像注入（按 u），在 h5 用户上下文下读取（数据隔离）
    from app.services.sishu_full.multi_user.h5 import h5_user_guarded

    # R5批⑨（清单安全）：走统一守卫——原 resolve_h5_current_user 无访问码校验，
    # access_code 启用时本端点=门禁绕过点
    h5_user_ctx = h5_user_guarded(u, request.code or "", x_access_code)
    with user_context(h5_user_ctx):
        context_hint = request.context_hint or _profile_summary_for(u)
        answer = await answer_with_orchestrator(
            "\n".join(prompt_parts),
            openid=f"h5:{u}",
            context_hint=context_hint,
            max_chars=request.max_chars,
        )
    return {"ok": True, "answer": answer, "u": u}


def _profile_summary_for(u: str) -> str:
    """按用户标识 u 生成学情画像摘要（供答疑 prompt 注入）。"""
    try:
        from app.services.sishu_full.learning.learner_profile import build_learner_profile

        profile = build_learner_profile(user_id=u or "default")
    except Exception:  # noqa: BLE001
        return ""
    if not profile or not profile.kp_mastery:
        return ""
    weak_names = [
        profile.kp_mastery[k].kp_name
        for k in profile.weak_points
        if k in profile.kp_mastery
    ]
    strong_names = [
        profile.kp_mastery[k].kp_name
        for k in profile.strong_points
        if k in profile.kp_mastery
    ]
    due_names = [
        d.get("kp_name", "") for d in profile.due_reviews[:5] if d.get("kp_name")
    ]
    parts = []
    if strong_names:
        parts.append(f"已掌握：{'、'.join(strong_names[:5])}")
    if weak_names:
        parts.append(f"薄弱点：{'、'.join(weak_names[:5])}（重点辅导这些）")
    if due_names:
        parts.append(f"今日应复习：{'、'.join(due_names)}")
    if parts:
        return "当前学生学习画像：" + "；".join(parts) + "。"
    return ""


@router.get("/exercise-hint")
def exercise_hint(chapter_title: str = ""):
    """Adaptive hint for a grade7 exercise chapter (design §3.7).

    Tells the client whether this chapter matches a weak knowledge point,
    so the exercise tab can surface a "focus here" prompt and prioritise it.
    """
    if not chapter_title.strip():
        raise HTTPException(status_code=400, detail="chapter_title is required")
    profile = build_learner_profile()
    return recommend_exercises(chapter_title, profile)


class _GradeExerciseRequest(BaseModel):
    chapter_id: str = ""            # 章节 id（grade7 exercise 归属）
    question_id: str = ""           # 题号（grade7 题库内题目标识）
    question_type: str = "choice"   # choice | fill
    question_text: str = ""         # 题干（错题本沉淀用，前端从题库带）
    user_answer: str = ""           # 用户作答（choice 传选项序号字符串）
    expected_answer: str = ""       # 缺省时后端从 grade7_index 反查
    u: str = ""                     # H5 用户标识
    attempt_id: str = ""            # E3（M12）离线答题幂等键：同 id 重放副作用只一次
    # PG-2（M15）：LLM 生成题直填——无需反查题库，前端上报自带归属与答案
    kp_id: str = ""                 # 生成题自带的知识点 id（优先于反查）
    expected_answer_pg: str = ""    # 生成题自带的标准答案（choice=选项字母/fill=文本）


class _GeneratePracticeRequest(BaseModel):
    chapter_id: str = ""
    tier: str = "basic"             # basic | intermediate | advanced
    count: int = 5                  # 本次生成题数
    u: str = ""


@router.post("/grade-exercise")
def grade_exercise(
    request: _GradeExerciseRequest,
    code: str = Query("", description="访问码（access_code 启用时必填）"),
    x_access_code: str = Header(""),
):
    """H5 答题上报 -> 完整学习闭环（总纲 G1，开箱即学情）。

    复用 LearningService.grade_and_record（判题/掌握度/FSRS/错题沉淀/
    学习事件/画像刷新），用户不建路径自动产生影子进度。

    返回前端可立即展示的结果：对错、归属知识点、掌握度、下次复习、
    是否新沉淀错题、是否判为薄弱。
    """
    from app.services.sishu_full.multi_user.h5 import h5_user_guarded, user_context

    u = request.u or ""
    with user_context(h5_user_guarded(u, code, x_access_code)):
        from app.services.sishu_full.learning.h5_progress import grade_h5_exercise

        # 从 grade7_index 反查 exercise / question（补充 expected_answer / 题干）
        exercise, question = _lookup_grade7(request.chapter_id, request.question_id)
        if question is not None and not request.question_text:
            request.question_text = str(question.get("ask") or "")
        result = grade_h5_exercise(
            chapter_id=request.chapter_id,
            question_id=request.question_id,
            question_type=request.question_type,
            question_text=request.question_text,
            user_answer=request.user_answer,
            expected_answer=request.expected_answer,
            exercise=exercise or {},
            question=question,
            attempt_id=request.attempt_id or "",
            kp_id_override=request.kp_id or "",
            expected_answer_pg=request.expected_answer_pg or "",
        )
        result["u"] = u
        return result


# --------------------------------------------------------------------------- #
# PG-1（M15）：三档难度练习生成（第七篇）                                        #
# --------------------------------------------------------------------------- #


@router.get("/practice")
def get_practice(
    chapter_id: str = Query(...),
    tier: str = Query("basic"),
    u: str = Query(""),
    code: str = Query(""),
    x_access_code: str = Header(""),
):
    """读该章节某档缓存题组（PG-1）。

    带 ?u= 时在该用户工作区读（缓存自动随 u 隔离）。缺省档返回推荐档。
    """
    from app.services.sishu_full.learning.practice_generator import (
        TIERS,
        TIER_ORDER,
        cooldown_left,
        current_questions,
        recommend_tier,
    )
    from app.services.sishu_full.multi_user.h5 import h5_user_guarded
    from app.services.sishu_full.multi_user.paths import user_context

    with user_context(h5_user_guarded(u, code, x_access_code)):
        if tier not in TIERS:
            tier = "basic"
        questions, cur, n = current_questions(chapter_id, tier)
        rec = recommend_tier(chapter_id, u)
        return {
            "chapter_id": chapter_id,
            "tier": tier,
            "recommended_tier": rec,
            "questions": questions,
            "version": cur,
            "version_count": n,
            "cooldown": cooldown_left(chapter_id, tier),
            "tiers": [{"key": k, "label": v} for k, v in TIERS.items()],
            "tier_order": TIER_ORDER,
        }


@router.get("/practice/rotate")
def rotate_practice(
    chapter_id: str = Query(...),
    tier: str = Query("basic"),
    u: str = Query(""),
    code: str = Query(""),
    x_access_code: str = Header(""),
):
    """「换一批」：轮换到该档下一版本（缓存内零成本，不调 LLM）。"""
    from app.services.sishu_full.learning.practice_generator import (
        TIERS,
        cooldown_left,
        rotate_version,
    )
    from app.services.sishu_full.multi_user.h5 import h5_user_guarded
    from app.services.sishu_full.multi_user.paths import user_context

    with user_context(h5_user_guarded(u, code, x_access_code)):
        if tier not in TIERS:
            tier = "basic"
        out = rotate_version(chapter_id, tier)
        out["chapter_id"] = chapter_id
        out["tier"] = tier
        out["cooldown"] = cooldown_left(chapter_id, tier)
        return out


@router.post("/generate-practice")
def generate_practice_endpoint(
    request: _GeneratePracticeRequest,
    u: str = Query(""),
    code: str = Query(""),
    x_access_code: str = Header(""),
):
    """LLM 按档位生成新题组（PG-1 + PG-5 冷却）。

    - 60s 冷却：同一用户同一章节同一档位，生成间隔不足则 409
    - 挑战档（advanced）：以该用户本章错题为种子出变式
    - LLM 未配置 -> 503
    """
    import time

    from app.services.sishu_full.learning.practice_generator import (
        COOLDOWN_SECONDS,
        TIERS,
        cooldown_left,
        current_questions,
        generate_practice as _gen,
    )
    from app.services.sishu_full.multi_user.h5 import h5_user_guarded
    from app.services.sishu_full.multi_user.paths import user_context

    # u 兼容：body 或 ?u= 均可（H5 前端惯例用 ?u=）
    u = request.u or u
    tier = request.tier if request.tier in TIERS else "basic"
    with user_context(h5_user_guarded(u, code, x_access_code)):
        remain = cooldown_left(request.chapter_id, tier)
        if remain > 0:
            raise HTTPException(
                status_code=409,
                detail=f"生成太频繁，请 {remain} 秒后再试",
            )
        seed_mothers: list[dict] = []
        if tier == "advanced" and request.chapter_id:
            try:
                from app.services.sishu_full.learning.mother_question import MotherQuestionStore

                items, _total = MotherQuestionStore().list_mothers(
                    chapter_id=request.chapter_id, page_size=5,
                )
                seed_mothers = [m.model_dump(mode="json") for m in items]
            except Exception:  # noqa: BLE001
                seed_mothers = []
        try:
            out = _gen(
                request.chapter_id,
                tier,
                request.count or 5,
                u,
                seed_mothers=seed_mothers,
            )
        except RuntimeError as e:
            msg = str(e)
            if "LLM key 未配置" in msg or "LLM" in msg:
                raise HTTPException(status_code=503, detail=msg) from e
            raise HTTPException(status_code=500, detail=msg) from e
        questions, cur, n = current_questions(request.chapter_id, tier)
        return {
            "chapter_id": request.chapter_id,
            "tier": tier,
            "generated": out["generated"],
            "version": out["version"],
            "questions": questions,
            "version_count": n,
            "cooldown": COOLDOWN_SECONDS,
        }


def _lookup_grade7(chapter_id: str, question_id: str):
    """在 grade7_index.json 中反查 (exercise, question)。

    grade7 题库是内容类（全局共享）——在 admin 上下文读取，与 h5 用户的
    data-class 隔离互不影响。

    优先用 exercise.id == question_id；否则在 chapter 的 exercises 里按
    question 序号匹配。返回 (exercise_dict|None, question_dict|None)。
    """
    import json

    from app.services.sishu_full.multi_user.paths import local_admin_user, user_context
    from app.services.sishu_full.services.path_service import get_path_service

    with user_context(local_admin_user()):
        index_path = get_path_service().get_workspace_dir() / "grade7" / "grade7_index.json"
        if not index_path.exists():
            return None, None
        try:
            idx = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None, None
    exercises = idx.get("exercises", [])
    # 0) question_id 形如 "<exercise.id>#<序号>"（H5 前端构造的唯一题号）
    if "#" in question_id:
        ex_id, _, tail = question_id.partition("#")
        for ex in exercises:
            if ex.get("id") == ex_id:
                try:
                    pos = int(tail)
                except (TypeError, ValueError):
                    return ex, None
                qs = ex.get("questions") or []
                if 0 <= pos < len(qs):
                    return ex, qs[pos]
                return ex, None
    # 1) exercise 级：question_id == exercise.id
    for ex in exercises:
        if ex.get("id") == question_id:
            return ex, None
    # 2) 题目级：在该 chapter 的 exercises 里按 question 序号匹配
    if chapter_id:
        for ex in exercises:
            cids = ex.get("chapter_ids") or []
            if chapter_id not in cids:
                continue
            for i, q in enumerate(ex.get("questions") or []):
                if str(q.get("id") or i) == str(question_id) or i == _int_question_id(question_id):
                    return ex, q
    return None, None


def _int_question_id(question_id: str) -> int | None:
    try:
        return int(question_id)
    except (TypeError, ValueError):
        return None


@router.get("/weekly-digest")
def weekly_digest(
    week_start: str = Query("", description="周起始日 YYYY-MM-DD（UTC），缺省=本周一"),
    _user=Depends(h5_scope_dep),
):
    """P2-A 周增量学情：按周聚合 L1 learning 事件，输出成长叙事。

    返回本周答题数/正确率/新学知识点/掌握度增量/错因分布/新增错题/完成复习。
    week_start 缺省本周一；mastery_delta 用全量事件算每 kp 的 before/after。
    """
    from collections import Counter
    from datetime import datetime, timedelta, timezone as _tz

    from app.services.sishu_full.services.memory import trace

    def _parse_monday(s: str) -> datetime:
        if s:
            try:
                return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=_tz.utc)
            except ValueError:
                pass
        now = datetime.now(_tz.utc)
        return (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

    start = _parse_monday(week_start)
    end = start + timedelta(days=7)
    start_iso, end_iso = start.isoformat(), end.isoformat()

    # 全量事件（含周前）→ 逐条分桶
    events = list(trace.iter_since("learning"))
    week_events = [e for e in events if start_iso <= e.ts < end_iso]

    attempts = [e for e in week_events if e.kind == "quiz_attempt"]
    mother_events = [e for e in week_events if e.kind == "mother_created"]
    mothers_added = len(mother_events)
    # W5（第八篇 M16-C）：四源分布（photo/chat/practice/manual，家长看得见错题从哪来）
    mother_sources = Counter(
        str(e.payload.get("source") or "unknown") for e in mother_events
    )
    reviews_done = len([e for e in week_events if e.kind == "review_completed"])

    correct = sum(1 for e in attempts if bool(e.payload.get("is_correct")))
    kp_meta: dict[str, str] = {}  # kp_id -> kp_name
    for e in attempts:
        pid = e.payload.get("kp_id")
        if pid:
            kp_meta[pid] = str(e.payload.get("kp_name") or kp_meta.get(pid) or "")
    error_types = Counter(
        str(e.payload.get("error_type")) for e in attempts if e.payload.get("error_type")
    )

    # 每 kp 的 mastery 轨迹（全量）：本周前最后一条 = before，本周最后一条 = after
    mastery_hist: dict[str, list[tuple[str, float]]] = {}
    for e in events:
        if e.kind != "quiz_attempt":
            continue
        pid = e.payload.get("kp_id")
        ma = e.payload.get("mastery_after")
        if pid and ma is not None:
            try:
                mastery_hist.setdefault(pid, []).append((e.ts, float(ma)))
            except (TypeError, ValueError):
                pass

    deltas: list[dict] = []
    for pid, hist in mastery_hist.items():
        hist.sort(key=lambda x: x[0])
        # before = 本周前最后一条；after = 本周内最后一条（不含下周）
        before = None
        week_hist: list[tuple[str, float]] = []
        for ts, val in hist:
            if ts < start_iso:
                before = val
            elif ts < end_iso:
                week_hist.append((ts, val))
        after = week_hist[-1][1] if week_hist else None
        if after is None:
            continue
        deltas.append(
            {
                "kp_id": pid,
                "kp_name": kp_meta.get(pid) or "",
                "before": before,
                "after": after,
                "delta": round(after - before, 3) if before is not None else None,
            }
        )

    week_kp_ids = {e.payload.get("kp_id") for e in attempts if e.payload.get("kp_id")}
    new_kps = [
        {"kp_id": pid, "kp_name": kp_meta.get(pid) or ""}
        for pid, d in ((x["kp_id"], x) for x in deltas)
        if pid in week_kp_ids and d["before"] is None
    ]
    top_improved = sorted(
        [d for d in deltas if d["delta"] is not None],
        key=lambda x: x["delta"],
        reverse=True,
    )[:3]

    # C2（M18-C）：本周阅读回流统计（内部书/教材翻页事件）
    reading_events = [e for e in week_events if e.kind == "book_progress"]
    books_read: set[str] = set()
    pages_read: set[tuple] = set()
    for e in reading_events:
        bid = str(e.payload.get("book_id") or "")
        if not bid:
            continue
        books_read.add(bid)
        pages_read.add((bid, int(e.payload.get("page") or 0)))

    return {
        "week_start": start_iso,
        "week_end": end_iso,
        "attempts": len(attempts),
        "accuracy": round(correct / len(attempts), 3) if attempts else None,
        "kps_touched": len(week_kp_ids),
        "new_kps": new_kps,
        "mastery_delta": deltas,
        "top_improved": top_improved,
        "error_types": dict(error_types),
        "mothers_added": mothers_added,
        "mother_sources": dict(mother_sources),
        "reviews_done": reviews_done,
        "books_read_count": len(books_read),
        "pages_read_count": len(pages_read),
    }


__all__ = ["router"]
