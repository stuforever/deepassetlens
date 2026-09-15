# -*- coding: utf-8 -*-
"""④（spec D5）：解析器工厂——格式→解析器；md/txt 直读（_read_text_file 语义收编），
pdf/docx 依赖已实测在位（pypdf 6.14/pymupdf 1.27/python-docx），解析失败返回空串由
调用方标记行 failed（不阻同批）。"""
from pathlib import Path
from typing import Dict


def parse_file(path: Path) -> str:
    """按扩展名分发解析；解析异常上抛（upload/vectorize 侧行级 try 捕获）。"""
    ext = path.suffix.lower()
    if ext in (".md", ".txt"):
        raw = path.read_bytes()
        for enc in ("utf-8-sig", "utf-8", "gbk"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")
    if ext == ".pdf":
        return _parse_pdf(path)
    if ext == ".docx":
        return _parse_docx(path)
    raise ValueError(f"不支持的文档格式: {ext}（当前支持 md/txt/pdf/docx）")


def _parse_pdf(path: Path) -> str:
    import fitz  # pymupdf
    doc = fitz.open(str(path))
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


def _parse_docx(path: Path) -> str:
    import docx  # python-docx
    d = docx.Document(str(path))
    return "\n".join(p.text for p in d.paragraphs if p.text.strip())


SUPPORTED_EXT: Dict[str, str] = {".md": "markdown", ".txt": "text", ".pdf": "pdf", ".docx": "docx"}


def parse_book_file(path: Path) -> list:
    """⑤批3（⑤d）：book 族解析——教材文件→blocks_json 消费行（块=结构面）。
    与 parse_file（正文检索面）分族：同一文件两面一次编译同时产出（⑤d §二）。"""
    from .book import parse_book
    return parse_book(path)


def parse_book_text(text: str) -> list:
    """⑤批3（⑤d）：文本→blocks_json 行（纯编译面——vectorize 已有正文文本时复用，
    免二次读盘；内容特征触发判定由调用方做）。"""
    from .book import compile_blocks
    return compile_blocks(text)
