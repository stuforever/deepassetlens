"""T15（M25 阶段①）：tab_export 文档模型 + 双渲染器 单元测试。

规格 §3.1 统一文档模型 / 验收判例 1（PDF 文件头）：
- render_pdf → b"%PDF-" 文件头（reportlab Platypus，STSong-Light 内置
  CID 字体零文件依赖，中英混排可渲染）；
- render_docx → b"PK" 文件头（docx=zip），document.xml 含 eastAsia 字体
  设置（qn 先例：mother_question.py L1288 同款 oxml 操作）；
- empty_doc → 空数据提示页（单节「本章节暂无该内容」）。
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import date
from pathlib import Path
from urllib.parse import unquote

import pytest

from deeptutor.learning.tab_export.model import ExportDoc, Section, empty_doc
from deeptutor.learning.tab_export.render_docx import render_docx
from deeptutor.learning.tab_export.render_pdf import render_pdf

DOC = ExportDoc(
    title="北师大版 三年级上册 数学 · 混合运算 · 闯关",
    meta=[{"label": "导出时间", "value": "2026-09-08"}],
    sections=[
        Section(
            heading="题组",
            paragraphs=["第 1 题"],
            list_items=[],
            table=None,
            questions=[{
                "ask": "先算什么？",
                "options": ["A", "B"],
                "answer": 1,
                "why": "先乘后加",
            }],
        )
    ],
)


def test_pdf_bytes_header():
    # 验收判例 1：PDF 文件头
    assert render_pdf(DOC)[:5] == b"%PDF-"


def test_docx_bytes_header():
    # docx=zip → PK 头
    assert render_docx(DOC)[:2] == b"PK"


def test_pdf_chinese_cid_font_no_file():
    # STSong-Light 为内置 CID，无字体文件依赖；拉丁走 Helvetica；
    # 断言：渲染含中文标题/表格/questions 不抛异常且非空
    assert len(render_pdf(DOC)) > 1000


def test_docx_eastasia_font():
    # eastAsia 设置参照 mother_question.py L1286 qn 先例；
    # 断言 document.xml 含 eastAsia 字体名
    data = render_docx(DOC)
    xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8")
    assert "eastAsia" in xml


def test_empty_doc_single_section_placeholder():
    doc = empty_doc("北师大版 三年级上册 数学 · 混合运算 · 错题")
    assert doc.title.endswith("错题")
    assert len(doc.sections) == 1
    assert doc.sections[0].paragraphs == ["本章节暂无该内容"]
    # 空数据页同样可被双渲染器渲染
    assert render_pdf(doc)[:5] == b"%PDF-"
    assert render_docx(doc)[:2] == b"PK"


def test_fill_in_answer_rendered_parent_edition():
    """审查 R1-建议1：填空/简答题（options=[]）的 answer 必须渲染进
    家长版导出（判例 3）——旧守卫 ``answer is not None and options``
    把填空答案全部拦掉；list 多候选以「 / 」连接（疑义 E 落地形态）。"""
    from deeptutor.learning.tab_export.model import format_answer

    doc = ExportDoc(
        title="闯关 · 家长版",
        sections=[Section(questions=[
            {"ask": "3 米 = ____ 分米", "options": [], "answer": "30",
             "why": "1 米 = 10 分米"},
            {"ask": "写出两个偶数", "options": [], "answer": ["甲", "乙"], "why": ""},
            {"ask": "选择题", "options": ["甲", "乙", "丙"], "answer": 2, "why": ""},
            {"ask": "未作答", "options": [], "answer": None, "why": ""},
            {"ask": "空白答案", "options": [], "answer": "  ", "why": ""},
        ])],
    )
    xml = zipfile.ZipFile(io.BytesIO(render_docx(doc))).read(
        "word/document.xml").decode("utf-8")
    assert "答案：30" in xml
    assert "答案：甲 / 乙" in xml
    assert "答案：C" in xml  # 选择题 answer=2 → 选项字母（甲乙丙仅选项文本）
    assert xml.count("答案：") == 3
    # PDF 渲染同口径不抛错
    assert len(render_pdf(doc)) > 1000
    # format_answer 直测：越界 int 原样、bool/空表/None 拒渲染
    assert format_answer(9) == "9"
    assert format_answer(True) is None
    assert format_answer([]) is None
    assert format_answer(None) is None


def test_docx_strips_illegal_xml_chars():
    """T21 e2e 发现：OCR 原文含 XML 非法控制符（\\x0b 等）时 docx 渲染
    抛 ValueError（PDF 容忍、XML 1.0 拒绝）——渲染器必须剥离而非 500。"""
    dirty = "第一页\x0b第二页\x0c第三页\x00末尾"
    doc = ExportDoc(
        title="人教版 七年级上册 数学-原文",
        meta=[{"label": "导出来源", "value": "tab=original"}],
        sections=[Section(heading="教材原文", paragraphs=[dirty], questions=[])],
    )
    data = render_docx(doc)
    assert data[:2] == b"PK"
    xml = zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode("utf-8")
    assert "第一页第二页第三页末尾" in xml  # 控制符被剥，正文保留
    for ch in ("\x0b", "\x0c", "\x00"):
        assert ch not in xml


def test_section_table_and_questions_roundtrip():
    section = Section(
        heading="表",
        paragraphs=[],
        list_items=["要点一", "要点二"],
        table={"headers": ["题", "正确率"], "rows": [["第 1 题", "80%"]]},
        questions=[],
    )
    doc = ExportDoc(title="学情", meta=[], sections=[section])
    assert section.table["headers"] == ["题", "正确率"]
    assert doc.sections[0].list_items == ["要点一", "要点二"]
    # 带表格的文档可渲染（PDF 表格 + docx 表格路径）
    assert render_pdf(doc)[:5] == b"%PDF-"
    assert render_docx(doc)[:2] == b"PK"


# ---------------------------------------------------------------------------
# T16：导出端点契约（GET /self-learning/chapter/{cid}/export）
# 验收判例 6（401 门禁）+ 规格 §3.2（无数据 → 200 空数据提示页不报错）
# ---------------------------------------------------------------------------

@pytest.fixture()
def h5_settings(tmp_path, monkeypatch):
    """访问码门禁隔离环境（test_recitation_api.h5_settings 同款）。"""
    from deeptutor.api.routers import h5_links
    from deeptutor.multi_user import h5 as h5_mod

    users_root = tmp_path / "users"
    users_root.mkdir(parents=True, exist_ok=True)
    settings_dir = tmp_path / "user" / "settings"
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "h5.json").write_text(
        json.dumps(
            {"public_base": "https://h5.example.com", "access_code": "1234"},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(h5_mod, "USERS_ROOT", users_root)
    monkeypatch.setattr(h5_links, "USERS_ROOT", users_root)
    return tmp_path


def test_export_endpoint_contract(h5_settings):
    from deeptutor.api.routers import self_learning as sl

    out = sl.export_chapter_tab(chapter_id="c1", tab="exercise", format="pdf",
                                answer_sheet=1, u="", code="", x_access_code="")
    assert out.media_type == "application/pdf"
    header = out.headers["Content-Disposition"]
    assert "attachment" in header
    # 文件名 "{教材名}-{章节名}-{闯关}-{YYYYMMDD}.pdf"（中文经 quote 编码，
    # mother_question.py L1413-1422 同款；解回断言结构与 tab 中文 + 日期）
    today = date.today().strftime("%Y%m%d")
    assert f"闯关-{today}.pdf" in unquote(header)
    # 章节无该 tab 数据 → 200 + 空数据提示页文档（规格 §3.2：不报错）
    assert bytes(out.body)[:5] == b"%PDF-"


def test_export_endpoint_validations(h5_settings):
    from fastapi import HTTPException

    from deeptutor.api.routers import self_learning as sl

    # tab ∉ 10 合法值 → 422
    with pytest.raises(HTTPException) as ei:
        sl.export_chapter_tab(chapter_id="c1", tab="nope", format="pdf",
                              answer_sheet=0, u="", code="", x_access_code="")
    assert ei.value.status_code == 422
    # format ∉ {pdf, docx} → 422
    with pytest.raises(HTTPException) as ei2:
        sl.export_chapter_tab(chapter_id="c1", tab="exercise", format="html",
                              answer_sheet=0, u="", code="", x_access_code="")
    assert ei2.value.status_code == 422


def test_export_docx_media_and_answer_sheet_ignored_elsewhere(h5_settings):
    from deeptutor.api.routers import self_learning as sl

    out = sl.export_chapter_tab(chapter_id="c1", tab="original", format="docx",
                                answer_sheet=0, u="", code="", x_access_code="")
    assert out.media_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert bytes(out.body)[:2] == b"PK"
    # answer_sheet 仅 exercise 有效（其他 tab 忽略，不抛错）
    out2 = sl.export_chapter_tab(chapter_id="c1", tab="original", format="pdf",
                                 answer_sheet=1, u="", code="", x_access_code="")
    assert bytes(out2.body)[:5] == b"%PDF-"


def test_export_endpoint_guarded(h5_settings):
    from fastapi import HTTPException

    from deeptutor.api.routers import self_learning as sl

    # 带 u 无码 → 401（验收判例 6；h5_user_guarded 门禁语义）
    with pytest.raises(HTTPException) as ei:
        sl.export_chapter_tab(chapter_id="c1", tab="exercise", format="pdf",
                              answer_sheet=0, u="小明", code="", x_access_code="")
    assert ei.value.status_code == 401


def test_export_textbook_level_original(h5_settings):
    """T20：H5 原文页教材级导出（chapter 未命中 + textbook_id 生效）。"""
    from deeptutor.api.routers import self_learning as sl

    out = sl.export_chapter_tab(
        chapter_id="-", tab="original", format="pdf", answer_sheet=0,
        u="", code="", x_access_code="", textbook_id="tb-x",
    )
    # 空 workspace 无页面数据 → 200 空数据提示页（§3.2 不报错）
    assert bytes(out.body)[:5] == b"%PDF-"
    today = date.today().strftime("%Y%m%d")
    # 文件名空章节槽不残留连击（-{原文}-{日期}.pdf）
    assert f"原文-{today}.pdf" in unquote(out.headers["Content-Disposition"])


def _seed_grade3_workspace(tmp: Path) -> None:
    """审查 R1-必修1 内容级回归夹具：向 tmp workspace 种入带章节数据的
    grade3 索引（exercises/courseware/voices）与一条本章错题。"""
    ws = tmp / "user" / "workspace"
    g3 = ws / "grade3"
    g3.mkdir(parents=True, exist_ok=True)
    (g3 / "grade3_index.json").write_text(
        json.dumps({
            # exercises 用真实组级形态（init_grade3 产物；审查 R1 复检发现
            # 分支曾按扁平单题读取 → 导出有组无题）
            "exercises": [{
                "id": "ex1", "title": "题组一", "subject": "math",
                "chapter_ids": ["c1"], "count": 1,
                "questions": [{
                    "ask": "8＋7 等于多少？", "type": "choice",
                    "options": ["14", "15"], "answer": 1,
                    "why": "先算 8＋2 再加 5", "kp_id": "", "difficulty": 2,
                }],
            }],
            "courseware": [{"id": "cw1", "title": "课件甲",
                            "chapter_ids": ["c1"], "goals": ["认识图形", "学会观察"]}],
            "voices": [{"id": "v1", "title": "课文领读",
                        "chapter_ids": ["c1"], "page": 3}],
            "figures": [],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    mq = ws / "mother_questions"
    mq.mkdir(parents=True, exist_ok=True)
    (mq / "index.json").write_text(
        json.dumps([{
            "id": "mq1", "title": "鸡兔同笼错题",
            "question_text": "笼中鸡兔共 10 头 28 足，求各几只。",
            "wrong_answer": "鸡 6 兔 4", "standard_answer": "鸡 6 只兔 4 只",
            "detailed_analysis": "假设全为鸡，则足数差对应兔数。",
            "chapter_id": "c1", "status": "active", "mastery_status": "not_mastered",
        }], ensure_ascii=False),
        encoding="utf-8",
    )


def test_export_content_tabs_non_empty(h5_settings, monkeypatch):
    """审查 R1-必修1：五个内容 tab 有数据时必须导出真实内容。

    此前 _build_tab_doc 分支引用未定义名 chapter_id，NameError 被外层
    except 吞掉 → exercise/wrong/ai/courseware/voice 恒为空数据页；
    既有端点测试用空 workspace 走「合法空」、e2e 只断言文件名/文件头，
    均无内容级护栏——本测试补上（判例 2/3/5）。"""
    from deeptutor.services import path_service as ps_mod

    _seed_grade3_workspace(h5_settings)
    fake_ps = ps_mod.PathService(workspace_root=h5_settings)
    monkeypatch.setattr(ps_mod, "get_path_service", lambda: fake_ps)
    # mother_question.py 顶部绑定自身引用——必须同名覆盖才隔离 wrong tab
    from deeptutor.learning import mother_question as mq_mod

    monkeypatch.setattr(mq_mod, "get_path_service", lambda: fake_ps)

    from deeptutor.api.routers import self_learning as sl

    def doc_xml(tab: str, answer_sheet: int = 0) -> str:
        out = sl.export_chapter_tab(
            chapter_id="c1", tab=tab, format="docx",
            answer_sheet=answer_sheet, u="", code="", x_access_code="",
        )
        assert bytes(out.body)[:2] == b"PK"
        return zipfile.ZipFile(io.BytesIO(bytes(out.body))).read(
            "word/document.xml").decode("utf-8")

    assert "本章节暂无该内容" not in doc_xml("exercise")
    assert "8＋7 等于多少" in doc_xml("exercise")          # 闯关题干入文（判例 3）
    assert "鸡兔同笼错题" in doc_xml("wrong")              # 章节错题（判例 5）
    assert "认识图形" in doc_xml("courseware")             # 课件教学目标（判例 2）
    assert "课文领读" in doc_xml("voice")                  # 语音资源清单（判例 2）
    assert "课件甲" in doc_xml("ai")                       # AI 资源卡（判例 12）


# ---------------------------------------------------------------------------
# T17：文本类 8 builder（纯函数，数据由端点层取好传入；规格 §9 每 builder 一例）
# ---------------------------------------------------------------------------

from deeptutor.learning.tab_export.builders import (  # noqa: E402
    build_ai,
    build_courseware,
    build_exercise,
    build_internal_books,
    build_knowledge,
    build_memory,
    build_notes,
    build_original,
    build_voice,
    build_wrong,
)


def test_build_original_pages_by_page_number():
    pages = [
        {"page_num": 10, "ocr_text": "第一页正文：混合运算先乘除后加减。"},
        {"page_num": 11, "ocr_text": "第二页正文：有小括号先算括号里。"},
    ]
    doc = build_original(pages, title="混合运算 · 原文")
    assert doc is not None
    assert doc.title == "混合运算 · 原文"
    assert [s.heading for s in doc.sections] == ["第 10 页", "第 11 页"]
    assert doc.sections[0].paragraphs == ["第一页正文：混合运算先乘除后加减。"]


def test_build_internal_books_list_and_spine():
    books = [
        {"id": "bk1", "title": "混合运算课件书", "status": "ready",
         "chapter_count": 3, "page_count": 12},
    ]
    spines = {"bk1": ["1. 同级运算从左到右", "2. 有括号先算括号"]}
    doc = build_internal_books(books, spines, title="混合运算 · 内部书籍")
    assert doc is not None
    assert doc.sections[0].table["rows"] == [["混合运算课件书", "ready", "3", "12"]]
    assert doc.sections[1].heading.startswith("目录")
    assert doc.sections[1].list_items == spines["bk1"]


def test_build_knowledge_table_with_mastery():
    kps = [
        {"name": "乘加混合", "description": "先乘后加的运算顺序", "difficulty": 2, "mastery": 0.86},
        {"name": "带小括号", "description": "括号优先", "difficulty": 3, "mastery": None},
    ]
    doc = build_knowledge(kps, title="混合运算 · 知识点")
    assert doc is not None
    rows = doc.sections[0].table["rows"]
    assert rows[0] == ["乘加混合", "先乘后加的运算顺序", "2", "86%"]
    assert rows[1][3] == "—"  # 无掌握度数据用占位符


def test_build_exercise_answer_sheet_toggle():
    groups = [{
        "title": "题组一",
        "questions": [{
            "ask": "5+3×2=？", "options": ["11", "16", "13"], "answer": 2,
            "why": "先算乘法", "kp_name": "乘加混合",
        }],
    }]
    parent = build_exercise(groups, title="混合运算 · 闯关", answer_sheet=True)
    student = build_exercise(groups, title="混合运算 · 闯关", answer_sheet=False)
    assert parent is not None and student is not None
    # 验收判例 3：家长版含答案+解析+kp 标注；学生版无答案
    q_parent = parent.sections[0].questions[0]
    assert q_parent["answer"] == 2
    assert "先算乘法" in q_parent["why"]
    assert "乘加混合" in q_parent["why"]
    q_student = student.sections[0].questions[0]
    assert q_student.get("answer") is None
    assert not q_student.get("why")


def test_build_wrong_questions_with_status_badge():
    questions = [{
        "title": "运算顺序错题",
        "question_text": "20-8÷2=？",
        "wrong_answer": "6",
        "detailed_analysis": "先算除法再算减法",
        "mastery_status": "reviewing",
    }]
    doc = build_wrong(questions, title="混合运算 · 章节错题")
    assert doc is not None
    section = doc.sections[0]
    assert section.heading == "运算顺序错题"
    joined = "\n".join(section.paragraphs)
    assert "20-8÷2=？" in joined
    assert "我的答案：6" in joined
    assert "复习中" in joined  # mastery_status 徽章中文


def test_build_notes_full_text():
    notes = [
        {"title": "错题订正", "content": "小括号优先级最高，先算括号内。"},
    ]
    doc = build_notes(notes, title="混合运算 · 笔记")
    assert doc is not None
    assert doc.sections[0].heading == "错题订正"
    assert doc.sections[0].paragraphs == ["小括号优先级最高，先算括号内。"]


def test_build_memory_mastery_table_and_summary():
    kp_mastery = [
        {"name": "乘加混合", "mastery": 0.75, "status": "learning"},
        {"name": "带小括号", "mastery": 0.92, "status": "mastered"},
    ]
    doc = build_memory(kp_mastery, "本章 2 个知识点，平均掌握度 84%", title="混合运算 · 章节记忆")
    assert doc is not None
    rows = doc.sections[0].table["rows"]
    assert rows[0] == ["乘加混合", "75%", "学习中"]
    assert rows[1] == ["带小括号", "92%", "已掌握"]
    assert doc.sections[1].paragraphs == ["本章 2 个知识点，平均掌握度 84%"]


def test_build_ai_four_cards():
    resources = {
        "courseware": [{"id": "cw1", "title": "运算顺序课件"}],
        "voices": [{"id": "v1", "title": "课文领读"}],
        "figures": [{"id": "f1", "title": "小棒图演示"}],
        "adaptive": {"adapted": [], "summary": "自适应练习：8 题，正确率 75%"},
    }
    doc = build_ai(resources, title="混合运算 · AI资源")
    assert doc is not None
    headings = [s.heading for s in doc.sections]
    assert headings == ["课件", "语音领读", "图形演示", "自适应练习"]
    assert doc.sections[0].paragraphs == ["运算顺序课件"]
    assert doc.sections[3].paragraphs == ["自适应练习：8 题，正确率 75%"]


# ---------------------------------------------------------------------------
# T18：富媒体 2 builder（courseware / voice；units_data 工作区副本为数据源）
# ---------------------------------------------------------------------------

def test_build_courseware_units_and_fallback():
    # 数学：concepts（name+desc）+ sections 小节；教学目标用索引 goals
    math_units = [{
        "title": "混合运算",
        "concepts": [{"name": "乘加混合运算", "desc": "先算乘法，再算加法"}],
        "sections": [{"title": "小熊购物", "page": 2}],
    }]
    doc = build_courseware(
        math_units, subject="math", chapter_name="混合运算",
        title="混合运算 · 课件", goals=["会算乘加混合运算"],
    )
    assert doc is not None
    by_heading = {s.heading: s for s in doc.sections}
    assert by_heading["教学目标"].paragraphs == ["会算乘加混合运算"]
    assert "乘加混合运算：先算乘法，再算加法" in by_heading["概念讲解"].list_items
    assert any("小熊购物" in it for it in by_heading["课时小节"].list_items)

    # 语文：hook + 课文段落 + 因果链 + 人物卡 + 作业
    cn_units = [{
        "title": "大青树下的小学", "hook": "边疆的早晨……",
        "passage": [{"text": "早晨，从山坡上，从坪坝里，走来了一群小学生。"}],
        "cause_effect": {
            "events": [{"ico": "🌅", "label": "早晨上学", "desc": "各民族孩子走来"}],
            "turning": "同上一间教室", "openQ": "你想和谁交朋友？",
        },
        "characters": {
            "characters": [{"name": "小学生们", "role": "边疆小学生", "bio": "多民族孩子"}],
        },
        "homework": {"base": ["朗读课文"], "up": [], "challenge": []},
    }]
    doc_cn = build_courseware(
        cn_units, subject="chinese", chapter_name="大青树下的小学",
        title="大青树下的小学 · 课件",
    )
    assert doc_cn is not None
    heads = [s.heading for s in doc_cn.sections]
    assert heads == ["教学目标", "课文段落", "因果链", "人物卡", "课后作业"]
    assert doc_cn.sections[1].paragraphs == ["早晨，从山坡上，从坪坝里，走来了一群小学生。"]
    assert any("🌅 早晨上学：各民族孩子走来" in it for it in doc_cn.sections[2].list_items)

    # 英语：词汇表（en/zh/谐音 py）+ 句组 + 歌谣
    en_units = {"M1U1": {
        "title": "Unit 1 Greetings",
        "vocab": [{"en": "cat", "zh": "猫", "py": "凯特"}],
        "groups": [{"title": "A", "lines": [{"en": "Hello!", "zh": "你好"}]}],
        "songs": [{"title": "Hi Song", "lyric": "Hello hi hello\nHow are you"}],
    }}
    doc_en = build_courseware(
        en_units, subject="english", chapter_name="Unit 1 Greetings",
        title="Unit 1 Greetings · 课件",
    )
    assert doc_en is not None
    heads_en = [s.heading for s in doc_en.sections]
    assert heads_en == ["教学目标", "词汇表", "句组", "歌谣"]
    assert doc_en.sections[1].table["rows"] == [["cat", "猫", "凯特"]]

    # grade7 章节无 units_data → 索引 goals + 书 spine 降级输出
    doc_fb = build_courseware(
        None, subject="math", chapter_name="有理数",
        title="有理数 · 课件", goals=["理解负数"], book_spine=["1.1 正数和负数"],
    )
    assert doc_fb is not None
    heads_fb = [s.heading for s in doc_fb.sections]
    assert heads_fb == ["教学目标", "书目录"]
    assert doc_fb.sections[1].list_items == ["1.1 正数和负数"]
    # 无任何降级素材 → None（空数据页由端点兜底）
    assert build_courseware(None, subject="math", chapter_name="x", title="x") is None

    # 验收判例 2：不解析课件 HTML——输出中无 html 字段
    for d in (doc, doc_cn, doc_en, doc_fb):
        assert all("html" not in (s.table or {}) for s in d.sections)
        assert not any("<" in p and ">" in p for s in d.sections for p in s.paragraphs)


def test_build_voice_read_script_and_media_table():
    # 英语：句子+谐音领读稿 + 音视频清单（table：标题/类型/路径）
    en_units = {"M1U1": {
        "title": "Unit 1 Greetings",
        "vocab": [{"en": "cat", "zh": "猫", "py": "凯特"}],
        "groups": [{"title": "A", "lines": [{"en": "Hello!", "zh": "你好"}]}],
        "songs": [],
    }}
    voices = [{"title": "s01-hero", "page": "/api/v1/grade3/英语/互动课件/M1U1/tts/s01-hero.mp3"}]
    doc = build_voice(en_units, subject="english", chapter_name="Unit 1 Greetings",
                      title="Unit 1 Greetings · 语音视频", voices=voices)
    assert doc is not None
    heads = [s.heading for s in doc.sections]
    assert heads == ["领读句组", "词汇读法", "音视频清单"]
    assert "Hello!（你好）" in doc.sections[0].list_items
    assert "cat（凯特）" in doc.sections[1].list_items
    assert doc.sections[2].table["rows"] == [["s01-hero", "音频", voices[0]["page"]]]

    # 语文：课文段落领读稿
    cn_units = [{"title": "大青树下的小学", "passage": [{"text": "早晨，从山坡上……"}]}]
    doc_cn = build_voice(cn_units, subject="chinese", chapter_name="大青树下的小学",
                         title="大青树下的小学 · 语音视频", voices=[])
    assert doc_cn is not None
    assert doc_cn.sections[0].heading == "领读课文"
    assert doc_cn.sections[0].paragraphs == ["早晨，从山坡上……"]

    # 数学无领读稿且无音视频 → None（空数据页由端点兜底）
    assert build_voice([], subject="math", chapter_name="x", title="x", voices=[]) is None
