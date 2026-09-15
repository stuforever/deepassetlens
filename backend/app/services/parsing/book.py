# -*- coding: utf-8 -*-
"""⑤批3（⑤d）：教材块解析器——文本→blocks_json 精简消费行（校准定稿 §六）。
type ∈ {text, quiz, flash_cards}（animation 仅接口，本解析器不产）；
行形状：{seq, type, title, content|items|front/back}，seq 连续从 1。
结构约定（md/txt；pdf/docx 先转文本走同一编译）：
  - `## 标题` → 开新 text 块（title=标题，后续段落聚合进 content）
  - ```quiz 围栏（JSON {"items":[{q,options,answer}]}）→ quiz 块
  - ```flashcards 围栏（JSON [{"front","back"}] 或每行 `front :: back`）→ flash_cards 块
  - 无标题前置段落 → 兜底 text 块（title=""）
"""
from __future__ import annotations

import json
from pathlib import Path

_FENCES = {"quiz", "flashcards", "flash_cards"}


def parse_book(path: Path) -> list[dict]:
    """教材文件→块结构（正文文本先按扩展名转出，再结构编译）。"""
    from .factory import parse_file
    raw = parse_file(path)
    return compile_blocks(raw)


def compile_blocks(text: str) -> list[dict]:
    """文本→blocks_json 行（纯函数——测试面）。"""
    blocks: list[dict] = []
    cur: dict | None = None
    lines = text.splitlines()
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.strip()
        fence = None
        if stripped.startswith("```"):
            fence = stripped[3:].strip().lower() or None
        if fence in _FENCES:
            # 围栏块：聚合到闭合 ```
            body: list[str] = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                body.append(lines[i])
                i += 1
            _append_structured(blocks, fence, "\n".join(body))
            cur = None
            i += 1
            continue
        if stripped.startswith("## ") and not stripped.startswith("###"):
            cur = {"type": "text", "title": stripped[3:].strip(), "content": []}
            blocks.append(cur)
            i += 1
            continue
        if stripped:
            if cur is None:
                cur = {"type": "text", "title": "", "content": []}
                blocks.append(cur)
            cur["content"].append(stripped)
        i += 1
    # 收口：content 列表拼正文；seq 连续从 1
    out: list[dict] = []
    for seq, b in enumerate(blocks, start=1):
        if b["type"] == "text":
            if not ("\n".join(b["content"])).strip():
                continue  # 空 text 块不占 seq（连续性由 enumerate 保证）
            out.append({"seq": len(out) + 1, "type": "text", "title": b["title"],
                        "content": "\n".join(b["content"])})
        else:
            b["seq"] = len(out) + 1
            out.append(b)
    return out


def _append_structured(blocks: list[dict], fence: str, body: str) -> None:
    """quiz/flashcards 围栏体→结构块（JSON 优先，flashcards 退化行式 `front :: back`）。"""
    if fence == "quiz":
        try:
            data = json.loads(body)
            items = data.get("items") if isinstance(data, dict) else data
            if isinstance(items, list) and items:
                blocks.append({"type": "quiz", "title": str(data.get("title", "") if isinstance(data, dict) else ""),
                               "items": [{"q": str(x.get("q", "")), "options": [str(o) for o in x.get("options", [])],
                                          "answer": x.get("answer", 0)} for x in items if isinstance(x, dict)]})
                return
        except (json.JSONDecodeError, AttributeError):
            pass
        return  # 围栏体不可解析→弃（不产非法块）
    # flashcards
    cards: list[dict] = []
    try:
        data = json.loads(body)
        if isinstance(data, list):
            cards = [{"front": str(x.get("front", "")), "back": str(x.get("back", ""))}
                     for x in data if isinstance(x, dict) and str(x.get("front", "")).strip()]
    except json.JSONDecodeError:
        for ln in body.splitlines():
            if "::" in ln:
                front, _, back = ln.partition("::")
                if front.strip() and back.strip():
                    cards.append({"front": front.strip(), "back": back.strip()})
    if cards:
        blocks.append({"type": "flash_cards", "title": "", "cards": cards})
