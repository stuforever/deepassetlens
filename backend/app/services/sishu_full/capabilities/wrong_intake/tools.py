"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.services.sishu_full.core.tool_protocol import BaseTool, ToolDefinition, ToolParameter, ToolResult

if TYPE_CHECKING:  # 仅类型标注：避免经 mother_question → path_service 的顶层循环导入
    from app.services.sishu_full.learning.mother_question import MotherQuestion, MotherQuestionStore

# 错因六枚举（与 recognize_text / 归因对齐）
WRONG_REASON_ENUM = (
    "concept_gap",
    "careless",
    "method_wrong",
    "calculation",
    "reading",
    "time_pressure",
)


def _new_store():
    # 惰性导入（repo 惯例：mastery 的 LearningStore 亦在方法内导入）——打破
    # api.main → registry → wrong_intake → mother_question → path_service 环
    from app.services.sishu_full.learning.mother_question import MotherQuestionStore

    return MotherQuestionStore()


def _duplicate_mid(store, title: str, question_text: str) -> str | None:
    """Simhash 查重：命中返回既有 mid，否则 None（镜像 REST 端点的查重短路）。"""
    try:
        from app.services.sishu_full.learning.simhash_util import compute_simhash, hamming_distance

        new_hash = compute_simhash(title, question_text)
        if new_hash is None:
            return None
        for existing in store.list_all_mothers():
            eh = existing.simhash
            if eh is None:
                eh = compute_simhash(existing.title, existing.question_text)
            if eh is not None and hamming_distance(new_hash, eh) <= 4:
                return existing.id
    except Exception:  # noqa: BLE001
        return None
    return None


def _active_user_slug() -> str:
    """当前 ContextVar 用户的 h5 slug（用于直达链接）。"""
    try:
        from app.services.sishu_full.multi_user.context import get_current_user

        user = get_current_user()
        if user is None:
            return ""
        username = getattr(user, "username", "") or ""
        # h5 用户 username 即 slug；admin 返回空（桌面用无 u 链接）
        return username if username else ""
    except Exception:  # noqa: BLE001
        return ""


class SaveWrongQuestionTool(BaseTool):
    """Persist a wrong question (or a correct one, when is_wrong=false)."""

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="save_wrong_question",
            description=(
                "Persist a wrong question into the learner's wrong-question book. "
                "Call after the learner confirmed the fields. Required: title, "
                "question_text, and the learner's wrong_answer. Best practice: also "
                "pass standard_answer when the learner knows it, subject (math/"
                "chinese/english/…), and a wrong_reason from the enum (concept_gap/"
                "careless/method_wrong/calculation/reading/time_pressure). Returns "
                "the saved question's mid and a link to review it. Does NOT ask "
                "questions — use ask_user for anything the learner must decide."
            ),
            parameters=[
                ToolParameter(name="title", type="string", description="Short title for the question."),
                ToolParameter(name="question_text", type="string", description="The full question text."),
                ToolParameter(
                    name="wrong_answer",
                    type="string",
                    description="The learner's wrong answer. Omit only for correct questions (is_wrong=false).",
                ),
                ToolParameter(
                    name="standard_answer",
                    type="string",
                    description="The correct answer, when known.",
                    required=False,
                ),
                ToolParameter(
                    name="subject",
                    type="string",
                    description="math / chinese / english / physics / … Default math.",
                    required=False,
                    default="math",
                ),
                ToolParameter(
                    name="grade",
                    type="string",
                    description="Grade label, e.g. 四年级.",
                    required=False,
                ),
                ToolParameter(
                    name="category",
                    type="string",
                    description="Category label, e.g. 应用题.",
                    required=False,
                ),
                ToolParameter(
                    name="difficulty",
                    type="integer",
                    description="1-5 difficulty. Default 3.",
                    required=False,
                    default=3,
                ),
                ToolParameter(
                    name="detailed_analysis",
                    type="string",
                    description="Explanation / analysis of the correct solution.",
                    required=False,
                ),
                ToolParameter(
                    name="wrong_reason",
                    type="string",
                    description=(
                        "One of: concept_gap (concept unclear), careless (careless "
                        "mistake), method_wrong (wrong method), calculation "
                        "(calculation error), reading (misread), time_pressure "
                        "(rushed)."
                    ),
                    required=False,
                    enum=list(WRONG_REASON_ENUM),
                ),
                ToolParameter(
                    name="is_wrong",
                    type="boolean",
                    description="True (default) for a wrong question; false for a correct question the learner wants to keep.",
                    required=False,
                    default=True,
                ),
                ToolParameter(
                    name="key_points",
                    type="array",
                    description="Optional key points / tags (short strings).",
                    required=False,
                    items={"type": "string"},
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        title = str(kwargs.get("title") or "").strip()
        question_text = str(kwargs.get("question_text") or "").strip()
        if not title or not question_text:
            return ToolResult(
                content="save_wrong_question needs non-empty title and question_text.",
                success=False,
            )

        store = _new_store()
        existing = _duplicate_mid(store, title, question_text)
        if existing:
            return ToolResult(
                content=(
                    f"A very similar question already exists in the book "
                    f"(mid {existing}). Do NOT save a duplicate — tell the learner "
                    f"this question is already recorded and offer to edit it instead."
                ),
                success=False,
                metadata={"mid": existing, "duplicate": True},
            )

        subject = str(kwargs.get("subject") or "math").strip() or "math"
        try:
            difficulty = int(kwargs.get("difficulty"))
        except (TypeError, ValueError):
            difficulty = 3
        # 无效值（0/None/非数值）回退默认 3；域外数值夹取（99→5）
        difficulty = 3 if difficulty == 0 else max(1, min(difficulty, 5))

        raw_key_points = kwargs.get("key_points")
        key_points = (
            [str(k).strip() for k in raw_key_points if str(k).strip()]
            if isinstance(raw_key_points, list)
            else []
        )
        slug = _active_user_slug()
        tags = [
            *key_points,
            "h5",
            "src:wrong_intake",
            *([f"u:{slug}"] if slug else []),
        ]

        is_wrong = kwargs.get("is_wrong", True) is not False
        from app.services.sishu_full.learning.mother_question import MotherQuestion, _gen_id, _now

        m = MotherQuestion(
            id=_gen_id(),
            title=title,
            question_text=question_text,
            subject=subject,
            grade=str(kwargs.get("grade") or "").strip() or None,
            category=str(kwargs.get("category") or "").strip() or None,
            standard_answer=str(kwargs.get("standard_answer") or "").strip() or None,
            wrong_answer=str(kwargs.get("wrong_answer") or "").strip() or None,
            detailed_analysis=str(kwargs.get("detailed_analysis") or "").strip() or None,
            difficulty=difficulty,
            wrong_reason=str(kwargs.get("wrong_reason") or "").strip() or None,
            # is_wrong=false 即「正确题」：模型以 correct_transferred_at 表达（M24）
            correct_transferred_at=(_now() if not is_wrong else None),
            key_points=key_points,
            tags=tags,
        )
        store.create_mother(m)

        # 事件：周报四源分布统计（与 REST create 端点一致）
        try:
            from app.services.sishu_full.learning.learner_profile import emit_learning_event

            emit_learning_event(
                kind="mother_created",
                payload={
                    "mid": m.id,
                    "title": m.title,
                    "kp_id": m.knowledge_point_id or "",
                    "chapter_id": m.chapter_id or "",
                    "source": "wrong_intake",
                },
            )
        except Exception:  # noqa: BLE001
            pass

        query = f"&u={slug}" if slug else ""
        url = f"/h5/wrongbook?mid={m.id}{query}"
        return ToolResult(
            content=(
                f"Saved wrong question #{m.id} — {m.title}. "
                f"It is now in the learner's wrong-question book."
            ),
            metadata={"mid": m.id, "url": url, "duplicate": False},
        )


WRONG_INTAKE_TOOL_TYPES: tuple[type[BaseTool], ...] = (SaveWrongQuestionTool,)

WRONG_INTAKE_TOOL_NAMES: tuple[str, ...] = ("save_wrong_question",)

__all__ = [
    "WRONG_INTAKE_TOOL_TYPES",
    "WRONG_INTAKE_TOOL_NAMES",
    "SaveWrongQuestionTool",
    "WRONG_REASON_ENUM",
]
