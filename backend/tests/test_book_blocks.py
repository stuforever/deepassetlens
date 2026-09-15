# -*- coding: utf-8 -*-
"""⑤批3（⑤d 验收）：book 解析器块结构/两面一次编译/报告行。编译纯函数为主
（vectorize 全链依赖 Qdrant——块面编译单测+列/报告行形状断言）。"""
import json

from app.services.parsing.book import compile_blocks
from app.services.parsing.factory import parse_book_text


def test_text_and_headings():
    """## 标题→text 块（title+content 聚合）；无标题前置段→兜底 text 块。"""
    blocks = compile_blocks("前言段落\n\n## 第一章 资产\n正文 A\n正文 B\n\n## 第二章 图谱\n正文 C")
    assert [b["type"] for b in blocks] == ["text", "text", "text"]
    assert blocks[0]["title"] == "" and blocks[0]["content"] == "前言段落"
    assert blocks[1]["title"] == "第一章 资产" and "正文 A" in blocks[1]["content"] and "正文 B" in blocks[1]["content"]
    assert blocks[2]["title"] == "第二章 图谱"
    assert [b["seq"] for b in blocks] == [1, 2, 3]          # seq 连续从 1


def test_quiz_fence():
    """```quiz 围栏→quiz 块（items[{q,options,answer}]）。"""
    body = json.dumps({"items": [{"q": "主表是？", "options": ["A 表", "B 表"], "answer": 0}]},
                      ensure_ascii=False)
    blocks = compile_blocks(f"## 测验\n```quiz\n{body}\n```")
    quiz = [b for b in blocks if b["type"] == "quiz"]
    assert len(quiz) == 1 and quiz[0]["items"][0]["q"] == "主表是？"
    assert quiz[0]["items"][0]["options"] == ["A 表", "B 表"] and quiz[0]["items"][0]["answer"] == 0


def test_flashcards_fence_json_and_lines():
    """```flashcards 围栏：JSON 列表与 `front :: back` 行式两路。"""
    j = json.dumps([{"front": "什么是主数据", "back": "跨系统共享的核心数据"}], ensure_ascii=False)
    b1 = compile_blocks(f"```flashcards\n{j}\n```")
    assert b1[0]["type"] == "flash_cards" and b1[0]["cards"][0]["front"] == "什么是主数据"
    b2 = compile_blocks("```flashcards\n卡A :: 背A\n卡B :: 背B\n```")
    assert [c["front"] for c in b2[0]["cards"]] == ["卡A", "卡B"]


def test_bad_fence_dropped_and_animation_absent():
    """非法围栏体→弃块（不产非法块）；解析器不产 animation（⑤d 诚实账②）。"""
    blocks = compile_blocks("```quiz\n不是JSON\n```")
    assert all(b["type"] == "text" for b in blocks)
    assert not any(b["type"] == "animation" for b in blocks)


def test_plain_note_no_blocks():
    """普通单文本（无标题无结构围栏）→单 text 块——vectorize 触发判定（结构块≥1 或 块数≥2）不为假。"""
    blocks = parse_book_text("只是一段普通笔记，没有结构。")
    assert len(blocks) == 1 and blocks[0]["type"] == "text"


def test_doc_report_row_shape():
    """_doc_to_dict 块概要行：count/types 分布（H5 消费预检）。"""
    from app.api.knowledge_base import _doc_to_dict
    class _Doc:
        id = "d1"; kb_id = "k1"; filename = "教材.md"; file_size = 10; chunk_count = 3
        status = "vectorized"; error_msg = None; checksum = "x"; embedding_signature = None
        blocks_json = [{"seq": 1, "type": "text"}, {"seq": 2, "type": "quiz"},
                       {"seq": 3, "type": "text"}]; created_at = None
    row = _doc_to_dict(_Doc())
    assert row["block_summary"] == {"count": 3, "types": {"text": 2, "quiz": 1}}


def test_model_has_blocks_json_column():
    """blocks_json 列在模型面（省第五张 PG 表——⑤d 修改点 2）。"""
    from app.models.knowledge_base import KnowledgeDocument
    assert hasattr(KnowledgeDocument, "blocks_json")
