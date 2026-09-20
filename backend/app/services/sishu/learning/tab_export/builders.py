# -*- coding: utf-8 -*-
# [sishu port] v4批6 机械复制自 vendor deeptutor/learning/tab_export/builders.py（1:1 语义，仅 import 改写）。
# 批16 vendor 物理删除后的存活拷贝；上游修订需回灌本件（复刻纪律）。
"""文本类 8 builder（M25 阶段① T17，规格 §3.1/§9）。

全部为**纯函数**：数据由端点层取好传入（课程/书籍内容在 admin 上下文
取，学情/错题/笔记在 u 上下文取——h5_progress.py L39-48 的
``_content_store()`` 上下文惯例），builder 只做 ExportDoc 装配。
输入数据为空时返回 None，由端点回退空数据提示页（规格 §3.2 不报错）。
"""

from __future__ import annotations

from typing import Any

from app.services.sishu.learning.tab_export.model import ExportDoc, Section

__all__ = [
    "build_ai",
    "build_courseware",
    "build_exercise",
    "build_internal_books",
    "build_knowledge",
    "build_memory",
    "build_notes",
    "build_original",
    "build_voice",
    "build_wrong",
]

# 错题掌握状态徽章中文（mother_question.MotherQuestion.mastery_status）
_WRONG_STATUS_LABELS = {
    "not_mastered": "未掌握",
    "reviewing": "复习中",
    "mastered": "已掌握",
}

# KP 学情状态中文（learner_profile.KpMastery.status）
_KP_STATUS_LABELS = {
    "new": "新学",
    "learning": "学习中",
    "weak": "薄弱",
    "mastered": "已掌握",
}


def _mastery_label(mastery: Any) -> str:
    """掌握度 0..1 → 百分数；None/缺失 → 占位符。"""
    if mastery is None:
        return "—"
    try:
        return f"{round(float(mastery) * 100)}%"
    except (TypeError, ValueError):
        return "—"


def build_original(pages: list[dict], *, title: str) -> ExportDoc | None:
    """原文：页区间 OCR 逐页一节标注页码（pages 已按章节页区间过滤）。"""
    rows = [p for p in pages or [] if (p.get("ocr_text") or "").strip()]
    if not rows:
        return None
    sections = [
        Section(
            heading=f"第 {p.get('page_num', '?')} 页",
            paragraphs=[p["ocr_text"]],
        )
        for p in rows
    ]
    return ExportDoc(title=title, meta=[], sections=sections)


def build_internal_books(
    books: list[dict],
    spines: dict[str, list[str]],
    *,
    title: str,
) -> ExportDoc | None:
    """内部书籍：书清单表（标题/状态/章数/页数）+ 每本 spine 目录。"""
    if not books:
        return None
    sections: list[Section] = [
        Section(
            heading="书清单",
            paragraphs=[],
            table={
                "headers": ["书名", "状态", "章数", "页数"],
                "rows": [
                    [
                        b.get("title", ""),
                        str(b.get("status", "")),
                        str(b.get("chapter_count", 0)),
                        str(b.get("page_count", 0)),
                    ]
                    for b in books
                ],
            },
        )
    ]
    for b in books:
        spine = spines.get(b.get("id", "")) or []
        sections.append(Section(
            heading=f"目录：《{b.get('title', '')}》",
            paragraphs=[] if spine else ["（暂无目录）"],
            list_items=[str(item) for item in spine],
        ))
    return ExportDoc(title=title, meta=[], sections=sections)


def build_knowledge(kps: list[dict], *, title: str) -> ExportDoc | None:
    """知识点：KP 清单表（名称/描述/难度/掌握度）。"""
    if not kps:
        return None
    return ExportDoc(
        title=title,
        meta=[],
        sections=[
            Section(
                heading="知识点清单",
                table={
                    "headers": ["知识点", "描述", "难度", "掌握度"],
                    "rows": [
                        [
                            k.get("name", ""),
                            k.get("description", "") or "",
                            str(k.get("difficulty", "") or ""),
                            _mastery_label(k.get("mastery")),
                        ]
                        for k in kps
                    ],
                },
            )
        ],
    )


def build_exercise(
    groups: list[dict],
    *,
    title: str,
    answer_sheet: bool,
) -> ExportDoc | None:
    """闯关：题组题干/选项；answer_sheet=True 家长版含答案+解析+kp 标注
    （验收判例 3），False 学生版无答案。"""
    if not groups:
        return None
    sections: list[Section] = []
    for g in groups:
        questions_out: list[dict[str, Any]] = []
        for q in g.get("questions") or []:
            item: dict[str, Any] = {"ask": q.get("ask", ""), "options": list(q.get("options") or [])}
            if answer_sheet:
                why = str(q.get("why", "") or "")
                kp_name = q.get("kp_name")
                if kp_name:
                    why = f"{why}【{kp_name}】" if why else f"【{kp_name}】"
                item.update(answer=q.get("answer"), why=why)
            questions_out.append(item)
        sections.append(Section(
            heading=g.get("title", "") or "题组",
            paragraphs=[],
            questions=questions_out,
        ))
    meta = [{"label": "版式", "value": "家长版（含答案解析）" if answer_sheet else "学生版（无答案）"}]
    return ExportDoc(title=title, meta=meta, sections=sections)


def build_wrong(questions: list[dict], *, title: str) -> ExportDoc | None:
    """章节错题：题干/我的错答/错因/状态徽章逐题一节。"""
    if not questions:
        return None
    sections: list[Section] = []
    for q in questions:
        paragraphs = [q.get("question_text", q.get("title", ""))]
        if q.get("wrong_answer"):
            paragraphs.append(f"我的答案：{q['wrong_answer']}")
        if q.get("standard_answer"):
            paragraphs.append(f"正确答案：{q['standard_answer']}")
        if q.get("detailed_analysis"):
            paragraphs.append(f"错因解析：{q['detailed_analysis']}")
        status = _WRONG_STATUS_LABELS.get(q.get("mastery_status") or "", "")
        if status:
            paragraphs.append(f"状态：{status}")
        sections.append(Section(
            heading=q.get("title", "") or "错题",
            paragraphs=[p for p in paragraphs if p],
        ))
    return ExportDoc(title=title, meta=[], sections=sections)


def build_notes(notes: list[dict], *, title: str) -> ExportDoc | None:
    """笔记：本章笔记全文逐篇一节。"""
    if not notes:
        return None
    sections = [
        Section(
            heading=n.get("title", "") or "笔记",
            paragraphs=[p for p in [n.get("content", "") or ""] if p.strip()] or ["（空笔记）"],
        )
        for n in notes
    ]
    return ExportDoc(title=title, meta=[], sections=sections)


def build_memory(
    kp_mastery: list[dict],
    chapter_summary: str,
    *,
    title: str,
) -> ExportDoc | None:
    """章节记忆：KP 掌握度表（名称/掌握度%/状态徽章）+ 章节摘要。"""
    if not kp_mastery and not chapter_summary:
        return None
    sections: list[Section] = []
    if kp_mastery:
        sections.append(Section(
            heading="知识点掌握度",
            table={
                "headers": ["知识点", "掌握度", "状态"],
                "rows": [
                    [
                        k.get("name", ""),
                        _mastery_label(k.get("mastery")),
                        _KP_STATUS_LABELS.get(k.get("status") or "", k.get("status") or ""),
                    ]
                    for k in kp_mastery
                ],
            },
        ))
    if chapter_summary:
        sections.append(Section(heading="章节摘要", paragraphs=[chapter_summary]))
    return ExportDoc(title=title, meta=[], sections=sections)


def build_voice(
    units_data,
    *,
    subject: str,
    chapter_name: str,
    title: str,
    voices: list[dict] | None = None,
) -> ExportDoc | None:
    """语音视频：领读文本稿（英语句子+谐音、语文课文段落）+ 音视频清单。

    领读稿从 units_data 工作区副本按章节名反查；音视频清单来自索引
    voices 条目（标题/类型/路径，类型按路径后缀推断）。数学无领读稿
    语义，仅有清单；两者皆无 → None（空数据页由端点兜底）。
    """
    sections: list[Section] = []

    def _unit() -> dict | None:
        return _find_unit(units_data, chapter_name)

    unit = _unit()
    if subject == "english" and isinstance(unit, dict):
        lines = [
            f"{ln.get('en', '')}（{ln.get('zh', '')}）"
            for g in (unit.get("groups") or [])
            for ln in (g.get("lines") or [])
            if ln.get("en")
        ]
        if lines:
            sections.append(Section(heading="领读句组", paragraphs=[], list_items=lines))
        vocab = [
            f"{v.get('en', '')}（{v.get('py', '')}）"
            for v in (unit.get("vocab") or [])
            if v.get("en")
        ]
        if vocab:
            sections.append(Section(heading="词汇读法", paragraphs=[], list_items=vocab))
    elif subject == "chinese" and isinstance(unit, dict):
        passage = [p.get("text", "") for p in (unit.get("passage") or []) if p.get("text")]
        if passage:
            sections.append(Section(heading="领读课文", paragraphs=passage))

    media_rows = []
    for v in voices or []:
        path = str(v.get("page", "") or "")
        if not path:
            continue
        lower = path.lower()
        kind = "视频" if (".mp4" in lower or ".webm" in lower) else "音频"
        media_rows.append([v.get("title", ""), kind, path])
    if media_rows:
        sections.append(Section(
            heading="音视频清单",
            table={"headers": ["标题", "类型", "路径"], "rows": media_rows},
        ))
    if not sections:
        return None
    return ExportDoc(title=title, meta=[], sections=sections)


def _find_unit(units_data, chapter_name: str) -> dict | None:
    """units_data（数学/语文 list，英语 dict）按章节名反查单元/课文。"""
    if isinstance(units_data, list):
        for u in units_data:
            if isinstance(u, dict) and u.get("title") == chapter_name:
                return u
    elif isinstance(units_data, dict):
        for u in units_data.values():
            if isinstance(u, dict) and u.get("title") == chapter_name:
                return u
    return None


def build_courseware(
    units_data,
    *,
    subject: str,
    chapter_name: str,
    title: str,
    goals: list[str] | None = None,
    book_spine: list[str] | None = None,
) -> ExportDoc | None:
    """课件：教学目标 + 文字讲稿（units_data 工作区副本，不解析课件 HTML）。

    - 数学：concepts（概念名+描述）+ sections 课时小节；
    - 语文：hook（引子）+ 课文段落 + 因果链（events/turning/openQ）
      + 人物卡（characters）+ 作业（base/up/challenge）；
    - 英语：词汇表（en/zh/谐音 py）+ 句组（groups.lines）+ 歌谣（songs.lyric）；
    - grade7 等无 units_data 的章节：索引条目 goals + 书 spine 降级输出；
      两者皆无 → None（空数据页由端点兜底）。
    """
    sections: list[Section] = []
    unit = _find_unit(units_data, chapter_name) if units_data else None

    if unit is not None and subject == "math":
        goal_lines = list(goals or [])
        if not goal_lines:
            goal_lines = [c.get("name", "") for c in (unit.get("concepts") or []) if c.get("name")]
        sections.append(Section(heading="教学目标", paragraphs=goal_lines or ["（待补充）"]))
        concepts = [
            f"{c.get('name', '')}：{c.get('desc', '')}"
            for c in (unit.get("concepts") or [])
            if c.get("name")
        ]
        if concepts:
            sections.append(Section(heading="概念讲解", paragraphs=[], list_items=concepts))
        secs = [
            f"{s.get('title', '')}（第 {s.get('page', '?')} 页）"
            for s in (unit.get("sections") or [])
            if s.get("title")
        ]
        if secs:
            sections.append(Section(heading="课时小节", paragraphs=[], list_items=secs))
    elif unit is not None and subject == "chinese":
        sections.append(Section(heading="教学目标", paragraphs=[unit.get("hook", "") or "（待补充）"]))
        passage = [p.get("text", "") for p in (unit.get("passage") or []) if p.get("text")]
        if passage:
            sections.append(Section(heading="课文段落", paragraphs=passage))
        ce = unit.get("cause_effect") or {}
        ce_items = [
            f"{e.get('ico', '')} {e.get('label', '')}：{e.get('desc', '')}".strip("： ")
            for e in (ce.get("events") or [])
            if e.get("label") or e.get("desc")
        ]
        ce_paras = [
            p for p in [
                f"转折：{ce.get('turning', '')}" if ce.get("turning") else "",
                f"思考：{ce.get('openQ', '')}" if ce.get("openQ") else "",
            ] if p
        ]
        if ce_items or ce_paras:
            sections.append(Section(heading="因果链", paragraphs=ce_paras, list_items=ce_items))
        chars = (unit.get("characters") or {}).get("characters") or []
        char_items = [
            f"{c.get('avatar', '')} {c.get('name', '')}（{c.get('role', '')}）：{c.get('bio', '')}"
            + (f"；{c['why']}" if c.get("why") else "")
            for c in chars
            if c.get("name")
        ]
        if char_items:
            sections.append(Section(heading="人物卡", paragraphs=[], list_items=char_items))
        hw = unit.get("homework") or {}
        hw_items: list[str] = []
        for label, key in (("基础", "base"), ("提高", "up"), ("挑战", "challenge")):
            for task in (hw.get(key) or []):
                hw_items.append(f"【{label}】{task}")
        if hw_items:
            sections.append(Section(heading="课后作业", paragraphs=[], list_items=hw_items))
    elif unit is not None and subject == "english":
        goal_lines = list(goals or [])
        sections.append(Section(
            heading="教学目标",
            paragraphs=goal_lines or [f"掌握本单元 {len(unit.get('vocab') or [])} 个词汇与句组表达"],
        ))
        vocab_rows = [
            [v.get("en", ""), v.get("zh", ""), v.get("py", "")]
            for v in (unit.get("vocab") or [])
            if v.get("en")
        ]
        if vocab_rows:
            sections.append(Section(
                heading="词汇表",
                table={"headers": ["单词", "中文", "谐音"], "rows": vocab_rows},
            ))
        line_items = [
            f"{ln.get('en', '')}（{ln.get('zh', '')}）"
            for g in (unit.get("groups") or [])
            for ln in (g.get("lines") or [])
            if ln.get("en")
        ]
        if line_items:
            sections.append(Section(heading="句组", paragraphs=[], list_items=line_items))
        lyrics: list[str] = []
        for song in (unit.get("songs") or []):
            lyric = (song.get("lyric") or "").strip()
            if lyric:
                lyrics.append(f"♪ {song.get('title', '') or '歌谣'}\n{lyric}")
        if lyrics:
            sections.append(Section(heading="歌谣", paragraphs=lyrics))
    else:
        # 降级（grade7 等）：索引 goals + 书 spine
        goal_lines = list(goals or [])
        spine = list(book_spine or [])
        if not goal_lines and not spine:
            return None
        sections.append(Section(
            heading="教学目标",
            paragraphs=goal_lines or ["（本章节暂无文字讲稿素材）"],
        ))
        if spine:
            sections.append(Section(heading="书目录", paragraphs=[], list_items=spine))
    return ExportDoc(title=title, meta=[], sections=sections)


def build_ai(resources: dict, *, title: str) -> ExportDoc | None:
    """AI资源：本章 4 卡文本（课件/语音领读/图形演示/自适应练习）。"""
    if not resources:
        return None
    sections: list[Section] = []

    def _titles(items: list[dict] | None) -> list[str]:
        return [str(i.get("title", "")) for i in (items or []) if i.get("title")]

    courseware = _titles(resources.get("courseware"))
    voices = _titles(resources.get("voices"))
    figures = _titles(resources.get("figures"))
    adaptive = resources.get("adaptive") or {}
    summary = adaptive.get("summary") or ""
    sections.append(Section(
        heading="课件",
        paragraphs=courseware or ["本章暂无课件"],
    ))
    sections.append(Section(
        heading="语音领读",
        paragraphs=voices or ["本章暂无语音资源"],
    ))
    sections.append(Section(
        heading="图形演示",
        paragraphs=figures or ["本章暂无图形资源"],
    ))
    sections.append(Section(
        heading="自适应练习",
        paragraphs=[summary] if summary else ["本章暂无自适应练习数据"],
    ))
    return ExportDoc(title=title, meta=[], sections=sections)
