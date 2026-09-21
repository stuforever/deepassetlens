"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ..models import BlockType, SourceAnchor
from .base import BlockContext, BlockGenerator, GenerationFailure

logger = logging.getLogger(__name__)


class QuizGenerator(BlockGenerator):
    block_type = BlockType.QUIZ

    async def _generate(
        self, ctx: BlockContext
    ) -> tuple[dict[str, Any], list[SourceAnchor], dict[str, Any]]:
        params = ctx.block.params
        chapter_title = params.get("chapter_title", ctx.chapter.title)
        chapter_summary = params.get("chapter_summary", ctx.chapter.summary)
        objectives = params.get("objectives") or ctx.chapter.learning_objectives
        num_questions = max(1, min(8, int(params.get("num_questions") or 3)))
        difficulty = str(params.get("difficulty") or "medium")
        question_type = str(params.get("question_type") or "")
        focus = str(params.get("focus") or "").strip()

        # Textbook-locked pages already carry an exact Unit outline. Keep
        # their review local so a slow question pipeline cannot block the
        # whole book compilation queue.
        unit_outline = self._unit_outline(ctx)
        if unit_outline:
            extra = getattr(ctx.chapter, "model_extra", None) or {}
            return self._textbook_review(
                chapter_title=chapter_title,
                unit_outline=unit_outline,
                num_questions=num_questions,
                task=str(extra.get("module_task") or "").strip(),
                focus=focus,
            )

        topic = chapter_title.strip() or ctx.book_id
        # Fold chapter context directly into the topic so the planner sees
        # it without needing a separate "preference" channel.
        extra_context = "; ".join(filter(None, [chapter_summary, *objectives]))
        if extra_context:
            topic = f"{topic}\n\n[Chapter context: {extra_context}]"
        question_types = [question_type] if question_type else []

        try:
            from app.services.sishu_full.agents.question.coordinator import AgentCoordinator

            coordinator = AgentCoordinator(
                kb_name=ctx.primary_kb,
                language=ctx.language,
                enable_idea_rag=ctx.rag_enabled and bool(ctx.primary_kb),
            )
            summary = await asyncio.wait_for(
                coordinator.generate_from_topic(
                    user_topic=topic,
                    num_questions=num_questions,
                    difficulty=difficulty,
                    question_types=question_types,
                ),
                timeout=90,
            )
        except Exception as exc:
            logger.warning(f"QuizGenerator failed: {exc}", exc_info=True)
            return self._fallback_review(
                chapter_title=chapter_title,
                chapter_summary=chapter_summary,
                num_questions=num_questions,
                reason=str(exc),
            )

        questions = self._extract_questions(summary)
        if not questions:
            raise GenerationFailure("no questions generated")

        return (
            {"questions": questions, "topic": topic},
            [],
            {
                "completed": summary.get("completed", 0),
                "failed": summary.get("failed", 0),
                "kb": ctx.primary_kb,
            },
        )

    @staticmethod
    def _unit_outline(ctx: BlockContext) -> list[dict[str, str]]:
        extra = getattr(ctx.chapter, "model_extra", None) or {}
        outline = extra.get("unit_outline")
        if not isinstance(outline, list):
            return []
        result: list[dict[str, str]] = []
        for item in outline:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            page = str(item.get("page") or "").strip()
            if title:
                result.append({"title": title, "page": page})
        return result

    @staticmethod
    def _textbook_review(
        *,
        chapter_title: str,
        unit_outline: list[dict[str, str]],
        num_questions: int,
        task: str,
        focus: str,
    ) -> tuple[dict[str, Any], list[SourceAnchor], dict[str, Any]]:
        if chapter_title == "Module 1 My classmates":
            return QuizGenerator._module1_review(focus=focus, num_questions=num_questions)

        units = unit_outline[: max(1, min(num_questions, 8))]
        questions: list[dict[str, Any]] = []
        for index, unit in enumerate(units, start=1):
            title = unit["title"]
            page = unit.get("page") or "the textbook"
            questions.append(
                {
                    "question_id": f"{chapter_title}-unit-{index}",
                    "question": f'Which textbook Unit is titled "{title}"?',
                    "question_type": "written",
                    "options": {"A": title, "B": "A different unit", "C": "Not included in this module"},
                    "correct_answer": "A",
                    "explanation": f"It is Unit {index} on textbook page {page}.",
                    "difficulty": "easy",
                    "concentration": "textbook sequence",
                }
            )
        if task and len(questions) < num_questions:
            questions.append(
                {
                    "question_id": f"{chapter_title}-task",
                    "question": f"What is the Module task for {chapter_title}?",
                    "question_type": "written",
                    "options": {"A": task, "B": "Skip all textbook activities", "C": "Use unrelated material"},
                    "correct_answer": "A",
                    "explanation": "This is the task recorded in the textbook outline for the module.",
                    "difficulty": "easy",
                    "concentration": "module task",
                }
            )
        return (
            {"questions": questions, "topic": chapter_title},
            [],
            {"completed": len(questions), "failed": 0, "source": "textbook_outline"},
        )

    @staticmethod
    def _module1_review(
        *,
        focus: str,
        num_questions: int,
    ) -> tuple[dict[str, Any], list[SourceAnchor], dict[str, Any]]:
        """A textbook-grounded practice set used as the Module 1 pattern."""
        unit = 0
        if "Unit 2" in focus:
            unit = 2
        elif "Unit 3" in focus:
            unit = 3
        elif "Unit 1" in focus:
            unit = 1

        sets: dict[int, list[dict[str, Any]]] = {
            1: [
                {"question": "Choose the best response: Nice to meet you.", "options": {"A": "Nice to meet you, too.", "B": "I am thirteen.", "C": "It is Monday."}, "answer": "A", "explanation": "The natural reply is Nice to meet you, too."},
                {"question": "Complete: What's your ___? — My name is Wang Lingling.", "options": {"A": "name", "B": "age", "C": "class"}, "answer": "A", "explanation": "What's your name? asks for a person's name."},
                {"question": "Complete: Where are you ___? — I'm from China.", "options": {"A": "from", "B": "old", "C": "name"}, "answer": "A", "explanation": "Where are you from? asks about where someone comes from."},
                {"question": "Which greeting fits the morning?", "options": {"A": "Good morning.", "B": "Good night.", "C": "Goodbye yesterday."}, "answer": "A", "explanation": "Good morning is the textbook morning greeting."},
                {"question": "Role-play Unit 1: greet a new classmate, say your name and ask where the classmate is from.", "options": {}, "answer": "Learner response", "explanation": "Use Hello/Good morning, My name is... and Where are you from?"},
            ],
            2: [
                {"question": "Complete: I'm Wang Lingling and I'm thirteen ___ old.", "options": {"A": "years", "B": "year", "C": "years'"}, "answer": "A", "explanation": "The textbook expression is thirteen years old."},
                {"question": "Complete: I'm ___ Beijing.", "options": {"A": "from", "B": "at", "C": "on"}, "answer": "A", "explanation": "Use I'm from + place to say where you are from."},
                {"question": "Which word joins the two pieces of information in the Unit 2 sentence?", "options": {"A": "and", "B": "but", "C": "because"}, "answer": "A", "explanation": "I'm Wang Lingling and I'm thirteen years old uses and."},
                {"question": "Choose the suitable answer: How old are you?", "options": {"A": "I'm thirteen years old.", "B": "I'm from Beijing.", "C": "Nice to meet you."}, "answer": "A", "explanation": "How old are you? asks about age."},
                {"question": "Write a two-sentence self-introduction using your name, age and where you are from.", "options": {}, "answer": "Learner response", "explanation": "Use I'm... and I'm... years old. / I'm from..."},
            ],
            3: [
                {"question": "Complete: This is ___ friend.", "options": {"A": "my", "B": "I", "C": "me"}, "answer": "A", "explanation": "This is my friend introduces a friend."},
                {"question": "Complete: Her ___'s Betty.", "options": {"A": "name", "B": "age", "C": "class"}, "answer": "A", "explanation": "Her name's Betty gives the girl's name."},
                {"question": "Choose the correct sentence for introducing a male teacher.", "options": {"A": "This is my teacher. His name's Mr Li.", "B": "This is my teacher. Her name's Mr Li.", "C": "This are my teacher."}, "answer": "A", "explanation": "Use His for a male person and This is for one person."},
                {"question": "Which pronoun completes the sentence about Betty? Betty is a girl. ___ name's Betty.", "options": {"A": "Her", "B": "His", "C": "Their"}, "answer": "A", "explanation": "Her refers to one girl or woman."},
                {"question": "Introduce one friend to the class using This is... and His/Her name's... .", "options": {}, "answer": "Learner response", "explanation": "This is my friend. His/Her name's... follows the Unit 3 pattern."},
            ],
            0: [
                {"question": "Which sentence asks for a person's name?", "options": {"A": "What's your name?", "B": "How old are you?", "C": "Where are you from?"}, "answer": "A", "explanation": "Unit 1 practises asking and answering names."},
                {"question": "Which sentence gives age?", "options": {"A": "I'm thirteen years old.", "B": "I'm from China.", "C": "This is my friend."}, "answer": "A", "explanation": "Unit 2 practises age and personal information."},
                {"question": "Which sentence introduces another person?", "options": {"A": "This is my friend.", "B": "What's your name?", "C": "How old are you?"}, "answer": "A", "explanation": "Unit 3 practises introducing a friend or teacher."},
                {"question": "Complete a short self-introduction and then introduce one friend.", "options": {}, "answer": "Learner response", "explanation": "Combine the three Unit patterns in the Module task."},
                {"question": "What is the Module 1 task?", "options": {"A": "Introduce yourself to your new friends.", "B": "Describe a zoo animal.", "C": "Write about a computer."}, "answer": "A", "explanation": "The Module task is introducing yourself to your new friends."},
            ],
        }
        selected = sets[unit][: max(1, min(num_questions, 8))]
        questions = [
            {
                "question_id": f"module1-practice-{unit}-{index}",
                "question": item["question"],
                "question_type": "written",
                "options": item["options"],
                "correct_answer": item["answer"],
                "explanation": item["explanation"],
                "difficulty": "easy",
                "concentration": "textbook practice",
            }
            for index, item in enumerate(selected, start=1)
        ]
        return (
            {"questions": questions, "topic": focus or "Module 1 My classmates"},
            [],
            {"completed": len(questions), "failed": 0, "source": "textbook_module1_pattern"},
        )

    @staticmethod
    def _fallback_review(
        *,
        chapter_title: str,
        chapter_summary: str,
        num_questions: int,
        reason: str,
    ) -> tuple[dict[str, Any], list[SourceAnchor], dict[str, Any]]:
        # 优先用确定性题库（真实题目，不依赖 LLM），保证「快速检查」始终可用
        banked = QuizGenerator._deterministic_review(chapter_title, num_questions)
        if banked:
            return (
                {"questions": banked, "topic": chapter_title},
                [],
                {
                    "completed": len(banked),
                    "failed": 0,
                    "source": "deterministic_bank",
                    "fallback_reason": reason,
                },
            )
        questions = [
            {
                "question_id": f"{chapter_title}-review-{index}",
                "question": f"Write one key point you learned from {chapter_title}.",
                "question_type": "written",
                "options": {},
                "correct_answer": "Learner response",
                "explanation": chapter_summary,
                "difficulty": "easy",
                "concentration": "module review",
            }
            for index in range(1, max(1, min(num_questions, 8)) + 1)
        ]
        return (
            {"questions": questions, "topic": chapter_title},
            [],
            {
                "completed": len(questions),
                "failed": 0,
                "source": "local_timeout_fallback",
                "fallback_reason": reason,
            },
        )

    # 确定性题库：按章节标题关键词匹配，生成真实「快速检查」题（choice，带答案与解析）。
    _BANK: list[tuple[tuple[str, ...], list[dict[str, Any]]]] = [
        (
            ("1.1", "正数和负数"),
            [
                {"question": "下列各数中，是负数的是：", "options": {"A": "3", "B": "0", "C": "−2.5", "D": "0.5"}, "correct_answer": "C", "explanation": "小于 0 的数是负数，−2.5 < 0。", "difficulty": "easy"},
                {"question": "0 是：", "options": {"A": "正数", "B": "负数", "C": "既不是正数也不是负数", "D": "正整数"}, "correct_answer": "C", "explanation": "0 既不是正数，也不是负数，它是正数和负数的分界点。", "difficulty": "easy"},
                {"question": "如果零上 5℃ 记作 +5℃，那么零下 3℃ 记作：", "options": {"A": "−3℃", "B": "+3℃", "C": "3℃", "D": "−5℃"}, "correct_answer": "A", "explanation": "相反意义的量用正负数表示，零下 3℃ 记作 −3℃。", "difficulty": "easy"},
                {"question": "下列各组中，表示一对相反意义的量的是：", "options": {"A": "收入和支出", "B": "3 和 5", "C": "长方形的长和宽", "D": "苹果和香蕉"}, "correct_answer": "A", "explanation": "收入和支出是一对相反意义的量。", "difficulty": "medium"},
            ],
        ),
        (
            ("1.2", "有理数", "数轴", "相反数", "绝对值"),
            [
                {"question": "−3 的相反数是：", "options": {"A": "3", "B": "−3", "C": "1/3", "D": "0"}, "correct_answer": "A", "explanation": "只有符号不同的两个数互为相反数，−3 的相反数是 3。", "difficulty": "easy"},
                {"question": "|−5| 的值是：", "options": {"A": "5", "B": "−5", "C": "0", "D": "1/5"}, "correct_answer": "A", "explanation": "绝对值表示数到原点的距离，|−5| = 5。", "difficulty": "easy"},
                {"question": "在数轴上，表示 −2 的点位于原点的：", "options": {"A": "左侧", "B": "右侧", "C": "原点上", "D": "无法确定"}, "correct_answer": "A", "explanation": "数轴上原点左侧的点表示负数，−2 在原点左侧。", "difficulty": "easy"},
                {"question": "下列说法正确的是：", "options": {"A": "整数和分数统称有理数", "B": "正数和负数统称有理数", "C": "0 不是有理数", "D": "π 是有理数"}, "correct_answer": "A", "explanation": "整数和分数统称为有理数，0 是有理数，π 不是。", "difficulty": "medium"},
            ],
        ),
        (
            ("1.3", "加减法"),
            [
                {"question": "计算：(−3) + 5 = ?", "options": {"A": "2", "B": "−2", "C": "8", "D": "−8"}, "correct_answer": "A", "explanation": "异号相加，取绝对值较大的符号，5 − 3 = 2。", "difficulty": "easy"},
                {"question": "计算：(−3) − (−5) = ?", "options": {"A": "2", "B": "−2", "C": "8", "D": "−8"}, "correct_answer": "A", "explanation": "减去一个数等于加上它的相反数：−3 + 5 = 2。", "difficulty": "medium"},
                {"question": "计算：(−4) + (−6) = ?", "options": {"A": "−10", "B": "10", "C": "−2", "D": "2"}, "correct_answer": "A", "explanation": "同号相加，取相同的符号并相加绝对值：−(4+6) = −10。", "difficulty": "easy"},
            ],
        ),
        (
            ("1.4", "乘除法"),
            [
                {"question": "计算：(−3) × 4 = ?", "options": {"A": "−12", "B": "12", "C": "−7", "D": "7"}, "correct_answer": "A", "explanation": "异号相乘得负，3 × 4 = 12，结果为 −12。", "difficulty": "easy"},
                {"question": "计算：(−8) ÷ (−2) = ?", "options": {"A": "4", "B": "−4", "C": "16", "D": "−16"}, "correct_answer": "A", "explanation": "同号相除得正，8 ÷ 2 = 4。", "difficulty": "easy"},
                {"question": "两个负数的乘积是：", "options": {"A": "正数", "B": "负数", "C": "0", "D": "无法确定"}, "correct_answer": "A", "explanation": "同号相乘得正，负负得正。", "difficulty": "easy"},
            ],
        ),
        (
            ("1.5", "乘方"),
            [
                {"question": "计算：2³ = ?", "options": {"A": "8", "B": "6", "C": "9", "D": "5"}, "correct_answer": "A", "explanation": "2³ 表示 3 个 2 相乘，2×2×2 = 8。", "difficulty": "easy"},
                {"question": "计算：(−2)² = ?", "options": {"A": "4", "B": "−4", "C": "2", "D": "−2"}, "correct_answer": "A", "explanation": "(−2)² = (−2)×(−2) = 4，偶数次幂为正。", "difficulty": "easy"},
                {"question": "计算：(−1)²⁰²⁴ = ?", "options": {"A": "1", "B": "−1", "C": "2024", "D": "−2024"}, "correct_answer": "A", "explanation": "−1 的偶数次幂等于 1。", "difficulty": "medium"},
            ],
        ),
        (
            ("2.1", "整式"),
            [
                {"question": "单项式 3x²y 的次数是：", "options": {"A": "3", "B": "2", "C": "4", "D": "1"}, "correct_answer": "A", "explanation": "单项式的次数是所有字母指数之和：2 + 1 = 3。", "difficulty": "medium"},
                {"question": "当 x = 3 时，代数式 2x + 1 的值是：", "options": {"A": "7", "B": "5", "C": "6", "D": "9"}, "correct_answer": "A", "explanation": "2×3 + 1 = 7。", "difficulty": "easy"},
                {"question": "下列各式中，是单项式的是：", "options": {"A": "3x²", "B": "x + 1", "C": "1/x", "D": "x² + y"}, "correct_answer": "A", "explanation": "数与字母的乘积是单项式，3x² 是单项式。", "difficulty": "medium"},
            ],
        ),
        (
            ("2.2", "整式的加减"),
            [
                {"question": "合并同类项：3x + 2x = ?", "options": {"A": "5x", "B": "6x", "C": "5x²", "D": "6x²"}, "correct_answer": "A", "explanation": "同类项合并：系数相加，3 + 2 = 5，结果为 5x。", "difficulty": "easy"},
                {"question": "计算：(2x + 1) − (x − 3) = ?", "options": {"A": "x + 4", "B": "x − 2", "C": "3x + 4", "D": "3x − 2"}, "correct_answer": "A", "explanation": "去括号：2x + 1 − x + 3 = x + 4。", "difficulty": "medium"},
            ],
        ),
        (
            ("3.2", "3.3", "合并同类项", "移项", "去括号", "去分母", "解一元一次"),
            [
                {"question": "解方程：2x = 8，则 x = ?", "options": {"A": "4", "B": "16", "C": "6", "D": "2"}, "correct_answer": "A", "explanation": "系数化为 1：x = 8 ÷ 2 = 4。", "difficulty": "easy"},
                {"question": "解方程：x + 5 = 12，则 x = ?", "options": {"A": "7", "B": "17", "C": "5", "D": "12"}, "correct_answer": "A", "explanation": "移项：x = 12 − 5 = 7。", "difficulty": "easy"},
                {"question": "解方程：3x + 1 = 10，则 x = ?", "options": {"A": "3", "B": "11/3", "C": "9", "D": "4"}, "correct_answer": "A", "explanation": "移项得 3x = 9，x = 3。", "difficulty": "medium"},
            ],
        ),
        (
            ("3.1", "从算式到方程", "3.4", "实际问题"),
            [
                {"question": "下列各式中，是方程的是：", "options": {"A": "2x + 3 = 7", "B": "2x + 3", "C": "2 + 3 = 5", "D": "2x"}, "correct_answer": "A", "explanation": "含有未知数的等式叫做方程。", "difficulty": "easy"},
                {"question": "方程 x + 3 = 7 的解是：", "options": {"A": "x = 4", "B": "x = 10", "C": "x = 3", "D": "x = 7"}, "correct_answer": "A", "explanation": "移项：x = 7 − 3 = 4。", "difficulty": "easy"},
                {"question": "小明买 3 支笔和 1 个本子共花 14 元，本子 5 元，设每支笔 x 元，正确的方程是：", "options": {"A": "3x + 5 = 14", "B": "3x − 5 = 14", "C": "3 + x = 14", "D": "5x + 3 = 14"}, "correct_answer": "A", "explanation": "3 支笔 3x 元，加本子 5 元共 14 元：3x + 5 = 14。", "difficulty": "medium"},
            ],
        ),
        (
            ("4.1", "几何图形"),
            [
                {"question": "下列图形中，是立体图形的是：", "options": {"A": "球", "B": "圆", "C": "三角形", "D": "长方形"}, "correct_answer": "A", "explanation": "球是立体图形，圆、三角形、长方形是平面图形。", "difficulty": "easy"},
                {"question": "长方体有（ ）个面：", "options": {"A": "6", "B": "4", "C": "8", "D": "12"}, "correct_answer": "A", "explanation": "长方体有 6 个面、12 条棱、8 个顶点。", "difficulty": "easy"},
            ],
        ),
        (
            ("4.2", "直线", "射线", "线段"),
            [
                {"question": "下列说法正确的是：", "options": {"A": "射线有一个端点", "B": "直线有一个端点", "C": "线段可以无限延长", "D": "射线有两个端点"}, "correct_answer": "A", "explanation": "射线有一个端点并向一方无限延伸。", "difficulty": "easy"},
                {"question": "过两点可以画（ ）条直线：", "options": {"A": "1", "B": "2", "C": "无数", "D": "0"}, "correct_answer": "A", "explanation": "两点确定一条直线。", "difficulty": "easy"},
            ],
        ),
        (
            ("4.3", "角"),
            [
                {"question": "直角等于（ ）度：", "options": {"A": "90", "B": "45", "C": "180", "D": "360"}, "correct_answer": "A", "explanation": "直角是 90°。", "difficulty": "easy"},
                {"question": "一个角是 30°，它的余角是：", "options": {"A": "60°", "B": "30°", "C": "150°", "D": "90°"}, "correct_answer": "A", "explanation": "互为余角的两个角和为 90°，90° − 30° = 60°。", "difficulty": "medium"},
            ],
        ),
        (
            ("4.4", "包装纸盒"),
            [
                {"question": "长方体纸盒展开后，相对的两个面（ ）：", "options": {"A": "形状大小相同", "B": "形状不同", "C": "大小不同", "D": "无法确定"}, "correct_answer": "A", "explanation": "长方体中相对的两个面全等（形状大小相同）。", "difficulty": "easy"},
            ],
        ),
        (
            ("圆柱", "圆锥"),
            [
                {"question": "圆柱有（ ）个底面：", "options": {"A": "2", "B": "1", "C": "3", "D": "0"}, "correct_answer": "A", "explanation": "圆柱有两个圆形的底面。", "difficulty": "easy"},
                {"question": "圆锥的底面是：", "options": {"A": "圆", "B": "三角形", "C": "正方形", "D": "长方形"}, "correct_answer": "A", "explanation": "圆锥有一个圆形的底面和一个顶点。", "difficulty": "easy"},
            ],
        ),
        (
            ("比例"),
            [
                {"question": "在比例 2 : 3 = 4 : 6 中，两个内项是：", "options": {"A": "3 和 4", "B": "2 和 6", "C": "2 和 3", "D": "4 和 6"}, "correct_answer": "A", "explanation": "比例 a : b = c : d 中，b 和 c 是内项，即 3 和 4。", "difficulty": "medium"},
            ],
        ),
        (
            ("图形", "旋转"),
            [
                {"question": "一个图形绕某点旋转，旋转前后（ ）：", "options": {"A": "形状和大小不变", "B": "大小改变", "C": "形状改变", "D": "位置不变"}, "correct_answer": "A", "explanation": "旋转只改变位置，不改变图形的形状和大小。", "difficulty": "easy"},
            ],
        ),
        (
            ("统计", "扇形统计图"),
            [
                {"question": "要表示各部分占总体的百分比，用（ ）统计图最合适：", "options": {"A": "扇形", "B": "条形", "C": "折线", "D": "以上都不行"}, "correct_answer": "A", "explanation": "扇形统计图能直观表示各部分占总体的百分比。", "difficulty": "easy"},
            ],
        ),
        (
            ("总复习"),
            [
                {"question": "计算：(−2) + 5 = ?", "options": {"A": "3", "B": "−3", "C": "7", "D": "−7"}, "correct_answer": "A", "explanation": "−2 + 5 = 3。", "difficulty": "easy"},
                {"question": "解方程：3x = 12，则 x = ?", "options": {"A": "4", "B": "36", "C": "9", "D": "6"}, "correct_answer": "A", "explanation": "x = 12 ÷ 3 = 4。", "difficulty": "easy"},
                {"question": "互为倒数的两个数，它们的积是：", "options": {"A": "1", "B": "0", "C": "−1", "D": "2"}, "correct_answer": "A", "explanation": "乘积为 1 的两个数互为倒数。", "difficulty": "medium"},
            ],
        ),
        (
            ("语文", "单元", "春", "济南", "散步", "怀念", "百草园", "再塑", "白求恩", "牧羊人",
             "皇帝的新装", "女娲", "寓言", "天上的街市", "散文诗", "古代诗歌", "论语", "世说新语",
             "诫子书", "狼", "写作", "综合性学习", "名著导读", "朝花夕拾", "阅读"),
            [
                {"question": "记叙文的六要素中，不包括下列哪一项：", "options": {"A": "修辞手法", "B": "时间", "C": "地点", "D": "人物"}, "correct_answer": "A", "explanation": "记叙文六要素是时间、地点、人物、起因、经过、结果，不包括修辞手法。", "difficulty": "easy"},
                {"question": "比喻句中，直接用“是”把甲事物说成乙事物的是：", "options": {"A": "暗喻", "B": "明喻", "C": "借代", "D": "拟人"}, "correct_answer": "A", "explanation": "暗喻用“是、变成”等连接，明喻用“像、好像”等。", "difficulty": "medium"},
                {"question": "写人记叙文要抓住人物的（ ）来写：", "options": {"A": "特点", "B": "姓名", "C": "年龄", "D": "住址"}, "correct_answer": "A", "explanation": "写人要抓住特点，才能让人物形象鲜明。", "difficulty": "easy"},
                {"question": "作文的中心思想应做到（ ）：", "options": {"A": "明确集中", "B": "含糊不清", "C": "随意发挥", "D": "与题目无关"}, "correct_answer": "A", "explanation": "中心明确、集中是作文的基本要求。", "difficulty": "easy"},
            ],
        ),
        (
            ("Module", "Starter", "Unit", "英语", "English"),
            [
                {"question": "— What's your name? — ____", "options": {"A": "My name is Li Ming.", "B": "I'm thirteen.", "C": "I'm fine.", "D": "Goodbye."}, "correct_answer": "A", "explanation": "What's your name? 用 My name is... 回答。", "difficulty": "easy"},
                {"question": "— How old are you? — ____", "options": {"A": "I'm thirteen years old.", "B": "I'm from China.", "C": "It's Monday.", "D": "Nice to meet you."}, "correct_answer": "A", "explanation": "How old are you? 询问年龄，用 I'm... years old. 回答。", "difficulty": "easy"},
                {"question": "This is ____ friend, Lingling.", "options": {"A": "my", "B": "I", "C": "me", "D": "mine"}, "correct_answer": "A", "explanation": "名词前用形容词性物主代词 my。", "difficulty": "easy"},
                {"question": "I'm ____ Beijing.", "options": {"A": "from", "B": "to", "C": "at", "D": "on"}, "correct_answer": "A", "explanation": "be from 表示来自某地。", "difficulty": "easy"},
                {"question": "一般现在时中，主语是第三人称单数时，动词要（ ）：", "options": {"A": "加 s 或 es", "B": "保持不变", "C": "加 ing", "D": "加 ed"}, "correct_answer": "A", "explanation": "第三人称单数主语，一般现在时动词加 s/es。", "difficulty": "medium"},
                {"question": "There ____ a book on the desk.", "options": {"A": "is", "B": "are", "C": "am", "D": "be"}, "correct_answer": "A", "explanation": "There be 句型就近原则，a book 是单数，用 is。", "difficulty": "medium"},
            ],
        ),
    ]

    @staticmethod
    def _deterministic_review(chapter_title: str, num_questions: int) -> list[dict[str, Any]]:
        """按章节标题关键词匹配确定性题库，生成真实「快速检查」题（无匹配则返回空）。"""
        for keywords, qs in QuizGenerator._BANK:
            if any(k in chapter_title for k in keywords):
                picked = qs[: max(1, min(num_questions, len(qs)))]
                return [
                    {
                        "question_id": f"bank-{chapter_title}-{index}",
                        "question": item["question"],
                        "question_type": "choice",
                        "options": item["options"],
                        "correct_answer": item["correct_answer"],
                        "explanation": item["explanation"],
                        "difficulty": item.get("difficulty", "medium"),
                        "concentration": "deterministic practice",
                    }
                    for index, item in enumerate(picked, start=1)
                ]
        return []

    @staticmethod
    def _extract_questions(summary: dict[str, Any]) -> list[dict[str, Any]]:
        results = summary.get("results") or []
        if not isinstance(results, list):
            return []
        out: list[dict[str, Any]] = []
        for item in results:
            if not isinstance(item, dict) or not item.get("success"):
                continue
            qa = item.get("qa_pair") or {}
            if not isinstance(qa, dict):
                continue
            out.append(
                {
                    "question_id": qa.get("question_id", ""),
                    "question": qa.get("question", ""),
                    "question_type": qa.get("question_type", "written"),
                    "options": qa.get("options") or {},
                    "correct_answer": qa.get("correct_answer", ""),
                    "explanation": qa.get("explanation", ""),
                    "difficulty": qa.get("difficulty", ""),
                    "concentration": qa.get("concentration", ""),
                }
            )
        return out


__all__ = ["QuizGenerator"]
