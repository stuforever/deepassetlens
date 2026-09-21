"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""
from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File
from pydantic import BaseModel, ConfigDict, Field

from app.services.sishu_full.services.file_io import atomic_write_text as _atomic_write_text
from app.services.sishu_full.services.path_service import get_path_service

_lock = threading.Lock()


def _now() -> float:
    return time.time()


def _gen_id() -> str:
    return uuid.uuid4().hex


# --------------------------------------------------------------------------- #
# Models                                                                       #
# --------------------------------------------------------------------------- #

class KnowledgePoint(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    parent_id: str | None = None        # None = 根节点
    subject: str = "math"
    grade: str | None = None            # 学段: 小学 / 初中（按教材归类）
    difficulty: int | None = None       # 难度 1-5（越大越难），用于树内易→难排序
    description: str | None = None      # 总结（一句话/一段）
    explanation: str | None = None      # 讲解（markdown，可含 $...$ 公式）
    examples: list[dict] = Field(default_factory=list)  # 实例 [{title, content}]
    related: list[dict] = Field(default_factory=list)   # 相关知识点 [{kp_id, relation}]
    formula: dict | None = None         # 公式 {name, latex, derivation}（数学）
    figure: dict | None = None          # 可拖拽图形 {type, config}（数学，离线控件）
    create_time: float = Field(default_factory=_now)


class Textbook(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    subject: str = "math"
    grade: str | None = None
    publisher: str | None = None
    version: str | None = None              # 版本（人教版/北师大版/苏教版）
    create_time: float = Field(default_factory=_now)


class TextbookPage(BaseModel):
    """教材页码：PDF 导入后每页一张图 + OCR 文本."""
    model_config = ConfigDict(extra="ignore")
    id: str
    textbook_id: str
    page_num: int
    image_url: str | None = None
    ocr_text: str | None = None
    create_time: float = Field(default_factory=_now)


class Chapter(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    textbook_id: str
    parent_id: str | None = None         # None = 顶级章
    name: str
    order: int = 0
    kp_ids: list[str] = Field(default_factory=list)  # 关联知识点 M:N
    page_start: int | None = None        # 起始页码
    page_end: int | None = None          # 结束页码
    create_time: float = Field(default_factory=_now)


# --------------------------------------------------------------------------- #
# Store                                                                        #
# --------------------------------------------------------------------------- #

class CurriculumStore:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or (get_path_service().get_workspace_dir() / "curriculum")
        self._root.mkdir(parents=True, exist_ok=True)
        self._kp_path = self._root / "knowledge_points.json"
        self._tb_path = self._root / "textbooks.json"
        self._ch_path = self._root / "chapters.json"
        self._pg_path = self._root / "textbook_pages.json"

    def _load(self, path: Path, cls):
        if not path.exists():
            return []
        return [cls.model_validate(d) for d in json.loads(path.read_text(encoding="utf-8"))]

    def _save(self, path: Path, items: list) -> None:
        text = json.dumps([x.model_dump(mode="json") for x in items], ensure_ascii=False, indent=2)
        _atomic_write_text(path, text)

    # ---------- knowledge points ----------

    def list_kps(self, subject: str | None = None, grade: str | None = None) -> list[KnowledgePoint]:
        items = self._load(self._kp_path, KnowledgePoint)
        if subject:
            items = [k for k in items if k.subject == subject]
        if grade:
            items = [k for k in items if (k.grade or "") == grade]
        return items

    def kp_tree(self, subject: str | None = None, grade: str | None = None) -> list[dict]:
        items = self.list_kps(subject)
        by_parent: dict[str | None, list[KnowledgePoint]] = {}
        for k in items:
            by_parent.setdefault(k.parent_id, []).append(k)
        # 难度：叶子直接取值；分类节点取子节点最大难度（自底向上），未标为 0
        def _eff_diff(k: KnowledgePoint) -> int:
            if k.difficulty:
                return k.difficulty
            kids = [c for c in items if c.parent_id == k.id]
            if kids:
                return max((_eff_diff(c) or 0) for c in kids)
            return 0
        diff_map = {k.id: _eff_diff(k) for k in items}

        def build(pid: str | None) -> list[dict]:
            nodes = []
            for k in sorted(
                by_parent.get(pid, []),
                key=lambda x: (diff_map.get(x.id, 0), x.name),
            ):
                children = build(k.id)
                # 学段过滤：保留自身匹配 或 有匹配后代 的节点（保留树形结构）
                keep = (not grade) or k.grade == grade or bool(children)
                if keep:
                    node = {**k.model_dump(mode="json"), "children": children}
                    node["difficulty"] = diff_map.get(k.id, 0)
                    nodes.append(node)
            return nodes
        return build(None)

    def create_kp(self, k: KnowledgePoint) -> KnowledgePoint:
        with _lock:
            items = self._load(self._kp_path, KnowledgePoint)
            items.append(k)
            self._save(self._kp_path, items)
        return k

    def update_kp(self, kid: str, patch: dict) -> KnowledgePoint | None:
        with _lock:
            items = self._load(self._kp_path, KnowledgePoint)
            for k in items:
                if k.id == kid:
                    for key, v in patch.items():
                        if hasattr(k, key) and key not in ("id", "create_time"):
                            setattr(k, key, v)
                    self._save(self._kp_path, items)
                    return k
        return None

    def delete_kp(self, kid: str) -> bool:
        with _lock:
            items = self._load(self._kp_path, KnowledgePoint)
            # 递归收集子节点
            to_del = {kid}
            changed = True
            while changed:
                changed = False
                for k in items:
                    if k.parent_id in to_del and k.id not in to_del:
                        to_del.add(k.id)
                        changed = True
            new = [k for k in items if k.id not in to_del]
            if len(new) != len(items):
                self._save(self._kp_path, new)
                return True
        return False

    # ---------- textbooks ----------

    def list_textbooks(self, subject: str | None = None) -> list[Textbook]:
        items = self._load(self._tb_path, Textbook)
        if subject:
            items = [t for t in items if t.subject == subject]
        return items

    def create_textbook(self, t: Textbook) -> Textbook:
        with _lock:
            items = self._load(self._tb_path, Textbook)
            items.append(t)
            self._save(self._tb_path, items)
        return t

    def update_textbook(self, tid: str, patch: dict) -> Textbook | None:
        with _lock:
            items = self._load(self._tb_path, Textbook)
            for t in items:
                if t.id == tid:
                    for key, v in patch.items():
                        if hasattr(t, key) and key not in ("id", "create_time"):
                            setattr(t, key, v)
                    self._save(self._tb_path, items)
                    return t
        return None

    def delete_textbook(self, tid: str) -> bool:
        with _lock:
            items = self._load(self._tb_path, Textbook)
            new = [t for t in items if t.id != tid]
            if len(new) != len(items):
                self._save(self._tb_path, new)
                # 级联删章节
                chs = self._load(self._ch_path, Chapter)
                self._save(self._ch_path, [c for c in chs if c.textbook_id != tid])
                return True
        return False

    # ---------- chapters ----------

    def list_chapters(self, textbook_id: str | None = None) -> list[Chapter]:
        items = self._load(self._ch_path, Chapter)
        if textbook_id:
            items = [c for c in items if c.textbook_id == textbook_id]
        return items

    def chapter_tree(self, textbook_id: str) -> list[dict]:
        items = self.list_chapters(textbook_id)
        by_parent: dict[str | None, list[Chapter]] = {}
        for c in items:
            by_parent.setdefault(c.parent_id, []).append(c)
        def build(pid: str | None) -> list[dict]:
            return [
                {**c.model_dump(mode="json"), "children": build(c.id)}
                for c in sorted(by_parent.get(pid, []), key=lambda x: x.order)
            ]
        return build(None)

    def create_chapter(self, c: Chapter) -> Chapter:
        with _lock:
            items = self._load(self._ch_path, Chapter)
            items.append(c)
            self._save(self._ch_path, items)
        return c

    def update_chapter(self, cid: str, patch: dict) -> Chapter | None:
        with _lock:
            items = self._load(self._ch_path, Chapter)
            for c in items:
                if c.id == cid:
                    for key, v in patch.items():
                        if hasattr(c, key) and key not in ("id", "create_time", "textbook_id"):
                            setattr(c, key, v)
                    self._save(self._ch_path, items)
                    return c
        return None

    def delete_chapter(self, cid: str) -> bool:
        with _lock:
            items = self._load(self._ch_path, Chapter)
            to_del = {cid}
            changed = True
            while changed:
                changed = False
                for c in items:
                    if c.parent_id in to_del and c.id not in to_del:
                        to_del.add(c.id)
                        changed = True
            new = [c for c in items if c.id not in to_del]
            if len(new) != len(items):
                self._save(self._ch_path, new)
                return True
        return False

    # ---------- chapter <-> knowledge point M:N ----------

    def link_chapter_kp(self, cid: str, kp_id: str) -> bool:
        """关联章节与知识点 (M:N)."""
        with _lock:
            items = self._load(self._ch_path, Chapter)
            for c in items:
                if c.id == cid:
                    if kp_id not in (c.kp_ids or []):
                        c.kp_ids = (c.kp_ids or []) + [kp_id]
                        self._save(self._ch_path, items)
                    return True
        return False

    def unlink_chapter_kp(self, cid: str, kp_id: str) -> bool:
        with _lock:
            items = self._load(self._ch_path, Chapter)
            for c in items:
                if c.id == cid:
                    c.kp_ids = [k for k in (c.kp_ids or []) if k != kp_id]
                    self._save(self._ch_path, items)
                    return True
        return False

    # ---------- textbook pages ----------

    def list_pages(self, textbook_id: str) -> list[TextbookPage]:
        items = self._load(self._pg_path, TextbookPage)
        items = [p for p in items if p.textbook_id == textbook_id]
        items.sort(key=lambda x: x.page_num)
        return items

    def add_page(self, p: TextbookPage) -> TextbookPage:
        with _lock:
            items = self._load(self._pg_path, TextbookPage)
            items.append(p)
            self._save(self._pg_path, items)
        return p

    def delete_page(self, pid: str) -> bool:
        with _lock:
            items = self._load(self._pg_path, TextbookPage)
            new = [p for p in items if p.id != pid]
            if len(new) != len(items):
                self._save(self._pg_path, new)
                return True
        return False

    # ---------- 补齐: 教材联合树 / 知识点重置 / 重建知识树 / 批量建章节 ----------

    def textbook_tree(self) -> list[dict]:
        """教材-章节-知识点 联合树."""
        tbs = self.list_textbooks()
        all_chs = self._load(self._ch_path, Chapter)
        all_kps = self._load(self._kp_path, KnowledgePoint)
        kp_map = {kp.id: kp for kp in all_kps}
        result = []
        for tb in tbs:
            tb_chs = [c for c in all_chs if c.textbook_id == tb.id]
            by_parent: dict[str | None, list[Chapter]] = {}
            for c in tb_chs:
                by_parent.setdefault(c.parent_id, []).append(c)
            def build_ch(pid: str | None) -> list[dict]:
                nodes = []
                for c in sorted(by_parent.get(pid, []), key=lambda x: x.order):
                    node = c.model_dump(mode="json")
                    node["children"] = build_ch(c.id)
                    node["knowledge_points"] = [
                        kp_map[kid].model_dump(mode="json")
                        for kid in (c.kp_ids or []) if kid in kp_map
                    ]
                    nodes.append(node)
                return nodes
            tb_dict = tb.model_dump(mode="json")
            tb_dict["chapters"] = build_ch(None)
            result.append(tb_dict)
        return result

    def reset_kps(self) -> int:
        """清空所有知识点，返回删除数."""
        with _lock:
            items = self._load(self._kp_path, KnowledgePoint)
            count = len(items)
            self._save(self._kp_path, [])
            return count

    def rebuild_kp_tree(self, kp_dicts: list[dict]) -> list[KnowledgePoint]:
        """用给定列表重建知识点树 (替换全部)."""
        with _lock:
            items = [KnowledgePoint.model_validate(d) for d in kp_dicts]
            self._save(self._kp_path, items)
            return items

    def batch_create_chapters(self, textbook_id: str, chapter_list: list[dict]) -> list[Chapter]:
        """批量创建章节."""
        created = []
        with _lock:
            items = self._load(self._ch_path, Chapter)
            for ch_data in chapter_list:
                c = Chapter(
                    id=_gen_id(),
                    textbook_id=textbook_id,
                    parent_id=ch_data.get("parent_id"),
                    name=ch_data.get("name", ""),
                    order=ch_data.get("order", 0),
                    page_start=ch_data.get("page_start"),
                    page_end=ch_data.get("page_end"),
                )
                items.append(c)
                created.append(c)
            self._save(self._ch_path, items)
        return created


# --------------------------------------------------------------------------- #
# Router                                                                       #
# --------------------------------------------------------------------------- #

router = APIRouter()


def _store() -> CurriculumStore:
    return CurriculumStore()


class KpRequest(BaseModel):
    name: str
    parent_id: str | None = None
    subject: str = "math"
    grade: str | None = None
    difficulty: int | None = None
    description: str | None = None


class TextbookRequest(BaseModel):
    name: str
    subject: str = "math"
    grade: str | None = None
    publisher: str | None = None
    version: str | None = None


class ChapterRequest(BaseModel):
    textbook_id: str
    parent_id: str | None = None
    name: str
    order: int = 0
    kp_ids: list[str] = Field(default_factory=list)
    page_start: int | None = None
    page_end: int | None = None


# ---------- knowledge points ----------

@router.get("/knowledge-points/tree")
async def kp_tree(subject: str | None = None, grade: str | None = None):
    return {"tree": _store().kp_tree(subject, grade)}


@router.get("/knowledge-points")
async def list_kps(subject: str | None = None, grade: str | None = None):
    return {"items": [k.model_dump(mode="json") for k in _store().list_kps(subject, grade)]}


@router.post("/knowledge-points", status_code=201)
async def create_kp(body: KpRequest):
    k = KnowledgePoint(id=_gen_id(), **body.model_dump())
    _store().create_kp(k)
    return k.model_dump(mode="json")


@router.patch("/knowledge-points/{kid}")
async def update_kp(kid: str, body: dict = Body(...)):
    k = _store().update_kp(kid, body)
    if not k:
        raise HTTPException(404, "知识点不存在")
    return k.model_dump(mode="json")


@router.delete("/knowledge-points/{kid}")
async def delete_kp(kid: str):
    ok = _store().delete_kp(kid)
    if not ok:
        raise HTTPException(404, "知识点不存在")
    return {"deleted": True}


# ---------- knowledge point detail / relations / enrich ----------

def _match_kp_name(name: str, kp_map: dict[str, KnowledgePoint]) -> str | None:
    """按名称精确 / 双向子串模糊匹配知识点 id（容忍 LLM 轻微改写名称）."""
    n = str(name or "").strip()
    if not n:
        return None
    if n in kp_map:
        return n
    for kid, k in kp_map.items():
        if n == k.name or (n in k.name) or (k.name in n):
            return kid
    return None


@router.get("/knowledge-points/{kid}")
async def get_kp_detail(kid: str):
    """知识点详情：完整字段 + 出向/入向相关关系（带名称）+ 关联章节."""
    store = _store()
    all_kps = store.list_kps("")
    kp = next((k for k in all_kps if k.id == kid), None)
    if not kp:
        raise HTTPException(404, "知识点不存在")
    kp_map = {k.id: k for k in all_kps}

    out_related = []
    for r in (kp.related or []):
        rid = r.get("kp_id")
        target = kp_map.get(rid)
        out_related.append({
            "kp_id": rid,
            "relation": r.get("relation"),
            "name": target.name if target else "",
            "subject": target.subject if target else "",
        })
    in_related = []
    for k in all_kps:
        if k.id == kid:
            continue
        for r in (k.related or []):
            if r.get("kp_id") == kid:
                in_related.append({
                    "kp_id": k.id,
                    "relation": r.get("relation"),
                    "name": k.name,
                    "subject": k.subject,
                })
    chapters = []
    for c in store.list_chapters(""):
        if kid in (c.kp_ids or []):
            tb = next((t for t in store.list_textbooks("") if t.id == c.textbook_id), None)
            chapters.append({
                "chapter_id": c.id,
                "name": c.name,
                "textbook_id": c.textbook_id,
                "textbook_name": tb.name if tb else "",
            })

    payload = kp.model_dump(mode="json")
    payload["related_out"] = out_related
    payload["related_in"] = in_related
    payload["chapters"] = chapters
    return payload


@router.post("/knowledge-points/{kid}/enrich")
async def enrich_kp(kid: str):
    """单知识点 LLM 补全：总结/讲解/实例；数学附公式(LaTeX)与推导过程；并生成相关知识点.

    沿用稳定的非流式 client.complete + 超时，只回填非空字段，不覆盖已有手编内容。
    """
    import asyncio
    import logging as _logging
    from app.services.sishu_full.services.llm import clean_thinking_tags, get_llm_client, get_llm_config
    from app.services.sishu_full.utils.json_parser import parse_json_response

    store = _store()
    all_kps = store.list_kps("")
    kp = next((k for k in all_kps if k.id == kid), None)
    if not kp:
        raise HTTPException(404, "知识点不存在")
    kp_map = {k.id: k for k in all_kps}

    # 所在体系路径（用于提示词）
    path: list[str] = []
    cur = kp
    while cur and cur.parent_id in kp_map:
        cur = kp_map[cur.parent_id]
        path.append(cur.name)
    parent_path = " → ".join(reversed(path)) or "（顶级）"

    label = {"math": "数学", "chinese": "语文", "english": "英语"}.get(kp.subject, kp.subject)
    is_math = kp.subject == "math"
    candidates = [k for k in all_kps if k.id != kid and k.subject == kp.subject]
    cand_names = "、".join([c.name for c in candidates[:150]])

    prompt = (
        f"你是资深{label}教师。请为知识点「{kp.name}」撰写精讲内容，供学生自主学习。\n"
        f"学科：{label}；学段：{kp.grade or '未知'}；所在知识体系：{parent_path}\n"
        f"已有总结：{kp.description or '（无）'}\n"
        f"已有讲解：{str(kp.explanation or '')[:200] or '（无）'}\n"
        + (f"已有公式：{kp.formula.get('name')}（可跳过公式）\n" if (kp.formula or {}).get("name") else "")
        + f"同科可用知识点（从中选相关关系）：{cand_names}\n\n"
        + (
            "数学要求：必须给出核心公式 latex（LaTeX，不含 $ 定界符）和完整推导过程 derivation"
            "（markdown，可含 $...$ 公式）。\n"
            if is_math
            else ""
        )
        + "只输出 JSON：\n"
        '{"summary":"一段话总结(80-150字)",'
        '"explanation":"详细讲解(markdown，可含 ### 小节与 $...$ 公式，300-600字)",'
        '"examples":[{"title":"例1标题","content":"例子内容(markdown)"}](2-3个)'
        + (',"formula":{"name":"公式名","latex":"LaTeX","derivation":"推导过程(markdown)"}' if is_math else "")
        + ',"related":[{"name":"知识点名","relation":"前置知识|后置知识|相关|包含"}](1-5个，名称务必从上面候选里选)}'
    )

    cfg = get_llm_config()
    client = get_llm_client()
    try:
        resp = await asyncio.wait_for(
            client.complete(
                prompt=prompt,
                system_prompt="你是严谨的课程设计专家。只输出合法 JSON，不要多余文字。",
                max_tokens=3000,
                temperature=0.3,
            ),
            timeout=150,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"LLM 补全失败: {exc}")
    raw = clean_thinking_tags(
        str(resp or ""), getattr(cfg, "binding", None), getattr(cfg, "model", None)
    ).strip()
    if not raw:
        raise HTTPException(502, "LLM 无输出")
    payload = parse_json_response(raw, logger_instance=_logging.getLogger("curriculum.enrich_kp"), fallback={})

    patch: dict = {}
    for field, target in (("summary", "description"), ("explanation", "explanation")):
        v = payload.get(field)
        if isinstance(v, str) and v.strip():
            patch[target] = v.strip()
    examples = payload.get("examples")
    if isinstance(examples, list) and examples:
        cleaned = [
            {"title": str(ex.get("title") or "例"), "content": str(ex["content"]).strip()}
            for ex in examples
            if isinstance(ex, dict) and str(ex.get("content") or "").strip()
        ]
        if cleaned:
            patch["examples"] = cleaned
    if is_math:
        formula = payload.get("formula")
        if isinstance(formula, dict) and (formula.get("latex") or formula.get("derivation")):
            patch["formula"] = {
                "name": str(formula.get("name") or kp.name),
                "latex": str(formula.get("latex") or ""),
                "derivation": str(formula.get("derivation") or ""),
            }
    related = payload.get("related")
    if isinstance(related, list) and related:
        cleaned_rel: list[dict] = []
        seen_rel: set[str] = set()
        for r in related:
            if not isinstance(r, dict):
                continue
            rname = str(r.get("name") or "").strip()
            rel = str(r.get("relation") or "相关").strip()
            if rel not in ("前置知识", "后置知识", "相关", "包含"):
                rel = "相关"
            mid = _match_kp_name(rname, kp_map)
            if mid and mid != kid and mid not in seen_rel:
                seen_rel.add(mid)
                cleaned_rel.append({"kp_id": mid, "relation": rel})
        if cleaned_rel:
            patch["related"] = cleaned_rel

    if not patch:
        raise HTTPException(502, "LLM 未生成有效内容")
    updated = store.update_kp(kid, patch)
    return {"updated": True, "kp": updated.model_dump(mode="json") if updated else None}


@router.post("/knowledge-points/assign-grades")
async def assign_kp_grades():
    """按关联教材的年级自动给知识点归类学段（小学/初中）；父节点按子节点继承."""

    def _segment(g: str) -> str | None:
        if not g:
            return None
        if any(x in g for x in ("一", "二", "三", "四", "五", "六")):
            return "小学"
        if any(x in g for x in ("七", "八", "九")):
            return "初中"
        return None

    store = _store()
    all_chs = store.list_chapters("")
    tb_grade = {t.id: (t.grade or "") for t in store.list_textbooks("")}
    ch_seg: dict[str, str] = {}
    for c in all_chs:
        seg = _segment(tb_grade.get(c.textbook_id, ""))
        if seg:
            ch_seg[c.id] = seg
    ch_by_kp: dict[str, list[str]] = {}
    for c in all_chs:
        for kid in (c.kp_ids or []):
            ch_by_kp.setdefault(kid, []).append(c.id)

    # 学科顶级根（跨学段）不归类，先清掉历史遗留
    for k in store.list_kps(""):
        if k.parent_id is None and k.grade:
            store.update_kp(k.id, {"grade": None})

    for k in store.list_kps(""):
        segs = [ch_seg[cid] for cid in ch_by_kp.get(k.id, []) if cid in ch_seg]
        if segs:
            seg = max(set(segs), key=segs.count)
            if k.grade != seg:
                store.update_kp(k.id, {"grade": seg})

    # 父节点按子节点继承（多轮直至稳定）；学科顶级根（跨学段）不归类
    for _round in range(10):
        kps = store.list_kps("")
        changed = False
        for k in kps:
            if k.grade or k.parent_id is None:
                continue
            grades = [x.grade for x in kps if x.parent_id == k.id and x.grade]
            if grades:
                store.update_kp(k.id, {"grade": max(set(grades), key=grades.count)})
                changed = True
        if not changed:
            break

    kps = store.list_kps("")
    return {"updated": sum(1 for k in kps if k.grade), "count": len(kps)}


@router.post("/knowledge-points/assign-difficulty")
async def assign_kp_difficulty(body: dict = Body(...)):
    """按学科用 LLM 给知识点标注难度 1-5（越大越难），用于知识树易→难排序.

    每学科一次 LLM 调用（非流式 + 超时），输出全部知识点难度，模糊匹配落库；
    未匹配到的保持原值。
    """
    import asyncio
    import logging as _logging
    from app.services.sishu_full.services.llm import clean_thinking_tags, get_llm_client, get_llm_config
    from app.services.sishu_full.utils.json_parser import parse_json_response

    store = _store()
    subjects = body.get("subjects") or None
    all_kps = store.list_kps("")
    by_subject: dict[str, list[KnowledgePoint]] = {}
    for k in all_kps:
        by_subject.setdefault(k.subject, []).append(k)
    label = {"math": "数学", "chinese": "语文", "english": "英语"}
    cfg = get_llm_config()
    client = get_llm_client()
    logger = _logging.getLogger("curriculum.assign_difficulty")
    matched = 0

    for subject, kps in by_subject.items():
        if subjects and subject not in subjects:
            continue
        if len(kps) > 120:
            kps = kps[:120]
        by_parent: dict[str | None, list[KnowledgePoint]] = {}
        for k in kps:
            by_parent.setdefault(k.parent_id, []).append(k)
        lines: list[str] = []

        def _walk(pid: str | None, depth: int) -> None:
            for k in sorted(by_parent.get(pid, []), key=lambda x: x.name):
                suffix = f"（已有难度 {k.difficulty}）" if k.difficulty else ""
                lines.append(f"{'  ' * depth}- [{k.id}] {k.name}{suffix}")
                _walk(k.id, depth + 1)

        _walk(None, 0)
        lname = label.get(subject, subject)
        prompt = (
            f"你是课程设计专家。为以下【{lname}】学科知识树中的每个知识点标注难度等级 1-5"
            "（1=最简单，5=最难）。依据学习进阶：基础概念/引入=1-2，核心技能/法则=3，"
            "综合运用=4，难题压轴=5。已有难度可保持或微调。\n\n知识树：\n"
            + "\n".join(lines)
            + "\n\n只输出 JSON："
            '{"difficulties":[{"name":"知识点名","difficulty":3}]}（覆盖全部知识点，一个不漏，'
            "name 必须与上面完全一致）"
        )
        try:
            resp = await asyncio.wait_for(
                client.complete(
                    prompt=prompt,
                    system_prompt="你是严谨的课程设计专家。只输出合法 JSON，不要多余文字。",
                    max_tokens=3000,
                    temperature=0.2,
                ),
                timeout=150,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[difficulty] LLM failed for {subject}: {exc}")
            continue
        raw = clean_thinking_tags(
            str(resp or ""), getattr(cfg, "binding", None), getattr(cfg, "model", None)
        ).strip()
        if not raw:
            logger.warning(f"[difficulty] No output for {subject}, skipping")
            continue
        payload = parse_json_response(raw, logger_instance=logger, fallback={})
        kp_map = {k.id: k for k in kps}
        for item in payload.get("difficulties") or []:
            if not isinstance(item, dict):
                continue
            kid = _match_kp_name(str(item.get("name") or ""), kp_map)
            if not kid:
                continue
            try:
                d = int(item.get("difficulty"))
            except (TypeError, ValueError):
                continue
            d = max(1, min(5, d))
            if kp_map[kid].difficulty != d:
                store.update_kp(kid, {"difficulty": d})
                matched += 1

    return {"matched": matched, "count": len(all_kps)}


@router.post("/knowledge-points/assign-figures")
async def assign_kp_figures(body: dict = Body(...)):
    """按名称关键词规则给数学知识点自动标注可拖拽图形（离线 math-widgets 控件）.

    确定性规则、不调用 LLM：数轴类→numberline，方程/等式→balance，几何类→geoboard。
    """
    store = _store()
    subject = body.get("subject") or "math"
    kps = store.list_kps(subject)
    rules = [
        (
            ("数轴", "正数", "负数", "相反数", "绝对值", "有理数", "大小", "比较",
             "代数", "整式", "数学"),
            "numberline",
            {"min": -10, "max": 10, "modes": ["find", "compare", "free"], "targets": [3, -5, 0]},
        ),
        (
            ("方程", "等式", "一元一次", "移项", "去括号", "去分母", "合并同类项", "比例"),
            "balance",
            {"a": 2, "b": 3, "c": 9},
        ),
        (
            ("几何", "图形", "角", "线段", "直线", "射线", "三角形", "多边形", "立体",
             "圆柱", "圆锥", "圆", "面", "投影", "统计", "长方体", "包装"),
            "geoboard",
            {"title": "几何画板"},
        ),
    ]
    updated = 0
    for k in kps:
        fig = None
        for keywords, ftype, config in rules:
            if any(kw in k.name for kw in keywords):
                fig = {"type": ftype, "config": {**config, "title": k.name}}
                break
        if fig and fig != (k.figure or None):
            store.update_kp(k.id, {"figure": fig})
            updated += 1
    return {"updated": updated, "count": len(kps), "subject": subject}


# ---------- textbooks ----------

@router.get("/textbooks")
async def list_textbooks(subject: str | None = None):
    return {"items": [t.model_dump(mode="json") for t in _store().list_textbooks(subject)]}


@router.post("/textbooks", status_code=201)
async def create_textbook(body: TextbookRequest):
    t = Textbook(id=_gen_id(), **body.model_dump())
    _store().create_textbook(t)
    return t.model_dump(mode="json")


@router.patch("/textbooks/{tid}")
async def update_textbook(tid: str, body: dict = Body(...)):
    t = _store().update_textbook(tid, body)
    if not t:
        raise HTTPException(404, "教材不存在")
    return t.model_dump(mode="json")


@router.delete("/textbooks/{tid}")
async def delete_textbook(tid: str):
    ok = _store().delete_textbook(tid)
    if not ok:
        raise HTTPException(404, "教材不存在")
    return {"deleted": True}


# ---------- chapters ----------

@router.get("/textbooks/{tid}/chapters")
async def list_chapters(tid: str):
    return {"items": [c.model_dump(mode="json") for c in _store().list_chapters(tid)]}


@router.get("/textbooks/{tid}/chapter-tree")
async def chapter_tree(tid: str):
    return {"tree": _store().chapter_tree(tid)}


@router.post("/chapters", status_code=201)
async def create_chapter(body: ChapterRequest):
    c = Chapter(id=_gen_id(), **body.model_dump())
    _store().create_chapter(c)
    return c.model_dump(mode="json")


@router.patch("/chapters/{cid}")
async def update_chapter(cid: str, body: dict = Body(...)):
    c = _store().update_chapter(cid, body)
    if not c:
        raise HTTPException(404, "章节不存在")
    return c.model_dump(mode="json")


@router.delete("/chapters/{cid}")
async def delete_chapter(cid: str):
    ok = _store().delete_chapter(cid)
    if not ok:
        raise HTTPException(404, "章节不存在")
    return {"deleted": True}


# ---------- chapter <-> knowledge point M:N ----------

@router.post("/chapters/{cid}/kps/{kid}")
async def link_chapter_kp(cid: str, kid: str):
    """关联章节与知识点."""
    ok = _store().link_chapter_kp(cid, kid)
    if not ok:
        raise HTTPException(404, "章节不存在")
    return {"linked": True}


@router.delete("/chapters/{cid}/kps/{kid}")
async def unlink_chapter_kp(cid: str, kid: str):
    """取消关联章节与知识点."""
    ok = _store().unlink_chapter_kp(cid, kid)
    if not ok:
        raise HTTPException(404, "章节不存在")
    return {"unlinked": True}


# ---------- textbook pages ----------

@router.get("/textbooks/{tid}/pages")
async def list_textbook_pages(tid: str):
    return {"items": [p.model_dump(mode="json") for p in _store().list_pages(tid)]}


@router.post("/textbooks/{tid}/pages", status_code=201)
async def create_textbook_page(tid: str, body: dict = Body(...)):
    p = TextbookPage(
        id=_gen_id(), textbook_id=tid,
        page_num=body.get("page_num", 1),
        image_url=body.get("image_url"),
        ocr_text=body.get("ocr_text"),
    )
    _store().add_page(p)
    return p.model_dump(mode="json")


@router.delete("/textbook-pages/{pid}")
async def delete_textbook_page(pid: str):
    ok = _store().delete_page(pid)
    if not ok:
        raise HTTPException(404, "页码不存在")
    return {"deleted": True}


@router.post("/textbooks/{tid}/import")
async def import_textbook_pdf(tid: str, file: UploadFile = File(...)):
    """教材 PDF 导入：拆页渲染 -> 每页 PNG 存到 curriculum/pages/{tid}/p{n}.png + OCR 文本.

    路径与书籍引擎 / 原文 Tab 期望一致（/api/v1/curriculum/pages/{tid}/p{n}.png）。
    重新导入会清空该教材旧的页码记录与图片。
    """
    from app.services.sishu_full.learning.image_pipeline import ocr_image
    from app.services.sishu_full.services.path_service import get_path_service

    store = _store()
    tb = next((t for t in store.list_textbooks("") if t.id == tid), None)
    if not tb:
        raise HTTPException(404, "教材不存在")
    raw = await file.read()
    if not raw:
        raise HTTPException(400, "空文件")
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise HTTPException(503, "PyMuPDF 未安装，无法拆页")

    pages_dir = get_path_service().get_workspace_dir() / "curriculum" / "pages" / tid
    pages_dir.mkdir(parents=True, exist_ok=True)
    # 清空旧页码记录
    for p in store.list_pages(tid):
        store.delete_page(p.id)
    for old in pages_dir.glob("p*.png"):
        try:
            old.unlink()
        except Exception:  # noqa: BLE001
            pass

    created: list[dict] = []
    try:
        doc = fitz.open(stream=raw, filetype="pdf")
        for page_num in range(min(doc.page_count, 100)):  # 限制最多100页
            pix = doc[page_num].get_pixmap(dpi=150)
            img_bytes = pix.tobytes("png")
            fname = pages_dir / f"p{page_num + 1}.png"
            fname.write_bytes(img_bytes)
            ocr_text = ""
            try:
                ocr_result = ocr_image(img_bytes)
                ocr_text = str(ocr_result.get("text") or "") if isinstance(ocr_result, dict) else ""
            except Exception:  # noqa: BLE001
                pass
            rec = TextbookPage(
                id=_gen_id(),
                textbook_id=tid,
                page_num=page_num + 1,
                image_url=f"/api/v1/curriculum/pages/{tid}/p{page_num + 1}.png",
                ocr_text=ocr_text[:500],
            )
            store.add_page(rec)
            created.append(rec.model_dump(mode="json"))
        doc.close()
    except Exception as e:
        raise HTTPException(500, f"PDF 拆页失败: {e}")
    return {"textbook_id": tid, "pages": created, "page_count": len(created)}


# --------------------------------------------------------------------------- #
# 补齐: 教材联合树 / 批量建章节 / 知识点重置 / 重建知识树                    #
# --------------------------------------------------------------------------- #

@router.get("/textbooks/_tree")
async def textbook_combined_tree():
    """教材-章节-知识点 联合树 (一次请求返回完整层级结构)."""
    return {"tree": _store().textbook_tree()}


@router.post("/chapters/batch", status_code=201)
async def batch_create_chapters(body: dict = Body(...)):
    """批量创建章节.

    入参: {textbook_id: "...", chapters: [{name, parent_id?, order?, page_start?, page_end?}, ...]}
    """
    textbook_id = body.get("textbook_id")
    if not textbook_id:
        raise HTTPException(400, "textbook_id 必填")
    chapter_list = body.get("chapters", [])
    if not chapter_list:
        raise HTTPException(400, "chapters 列表不能为空")
    created = _store().batch_create_chapters(textbook_id, chapter_list)
    return {"created": len(created), "items": [c.model_dump(mode="json") for c in created]}


@router.post("/knowledge-points/reset")
async def reset_knowledge_points():
    """清空所有知识点 (不可恢复)."""
    count = _store().reset_kps()
    return {"deleted": count, "reset": True}


@router.post("/knowledge-points/tree")
async def rebuild_kp_tree(body: dict = Body(...)):
    """重建知识点树 (用给定列表替换全部知识点).

    入参: {knowledge_points: [{id?, name, parent_id?, subject?, description?}, ...]}
    """
    kp_list = body.get("knowledge_points", [])
    if not kp_list:
        raise HTTPException(400, "knowledge_points 列表不能为空")
    # 为缺失 id 的条目生成 id
    for kp in kp_list:
        if not kp.get("id"):
            kp["id"] = _gen_id()
    items = _store().rebuild_kp_tree(kp_list)
    return {"rebuilt": len(items), "items": [k.model_dump(mode="json") for k in items]}


# ---------- chapter <-> knowledge point (batch / reverse lookup) ----------

@router.put("/chapters/{cid}/kps")
async def set_chapter_kps(cid: str, body: dict = Body(...)):
    """全量替换章节关联的知识点（多对多）. body: {kp_ids: [..]}"""
    kp_ids = body.get("kp_ids", [])
    if not isinstance(kp_ids, list):
        raise HTTPException(400, "kp_ids 必须是列表")
    chapter = _store().update_chapter(cid, {"kp_ids": kp_ids})
    if chapter is None:
        raise HTTPException(404, "章节不存在")
    return {"chapter_id": cid, "kp_ids": kp_ids, "count": len(kp_ids)}


@router.get("/knowledge-points/{kid}/chapters")
async def kp_chapters(kid: str):
    """反查：引用某知识点的章节列表（多对多反向）. """
    store = _store()
    all_chs = store.list_chapters("")
    all_tbs = store.list_textbooks("")
    tb_map = {t.id: t for t in all_tbs}
    refs = []
    for c in all_chs:
        if kid in (c.kp_ids or []):
            tb = tb_map.get(c.textbook_id)
            refs.append(
                {
                    "chapter_id": c.id,
                    "name": c.name,
                    "textbook_id": c.textbook_id,
                    "textbook_name": tb.name if tb else "",
                }
            )
    return {"items": refs, "count": len(refs)}


# ---------- LLM auto-extract knowledge point tree from textbooks ----------

@router.post("/knowledge-points/extract-from-textbooks")
async def extract_kp_from_textbooks(body: dict = Body(...)):
    """用 LLM 从教材章节按学科分组自动提取「学科知识体系」知识点树（含说明），并自动建立章节↔知识点多对多关联.

    入参: {textbook_ids?: list[str]}（默认全部教材）.
    两阶段：① 每学科 LLM 生成知识点树（叶子带 desc 说明）② 每本教材 LLM 生成章节→知识点映射.
    每个 LLM 调用输出较短，避免长内容生成不稳定.
    """
    import logging as _logging
    import asyncio
    from collections import defaultdict
    from app.services.sishu_full.services.llm import clean_thinking_tags, get_llm_client, get_llm_config
    from app.services.sishu_full.utils.json_parser import parse_json_response

    logger = _logging.getLogger("curriculum.extract_kp")
    textbook_ids = body.get("textbook_ids") or None
    only_link = bool(body.get("only_link", False))
    store = _store()
    all_tbs = store.list_textbooks("")
    tbs = [t for t in all_tbs if not textbook_ids or t.id in textbook_ids]
    if not tbs:
        raise HTTPException(400, "没有可提取的教材")

    cfg = get_llm_config()
    client = get_llm_client()
    _SUBJECT_ALIAS = {
        "数学": "math", "语文": "chinese", "英语": "english",
        "科学": "science", "物理": "physics", "化学": "chemistry",
        "生物": "biology", "历史": "history", "地理": "geography",
        "政治": "politics",
    }
    _SUBJECT_LABEL = {
        "math": "数学", "chinese": "语文", "english": "英语",
        "science": "科学", "physics": "物理", "chemistry": "化学",
        "biology": "生物", "history": "历史", "geography": "地理",
    }
    by_subject: dict[str, list] = defaultdict(list)
    for tb in tbs:
        by_subject[tb.subject].append(tb)

    chapter_names: dict[str, str] = {}
    all_subjects: list[dict] = []

    # ---- 阶段A: 每学科生成知识点树（含 desc）; only_link 时跳过建树 ----
    all_subjects: list[dict] = []
    for subject, group in ([] if only_link else by_subject.items()):
        chapter_lines: list[str] = []
        for tb in group:
            chs = store.list_chapters(tb.id)
            lines = [f"## 教材《{tb.name}》"]
            for c in sorted(chs, key=lambda x: (x.parent_id is not None, x.order)):
                chapter_names[c.id] = c.name
                indent = "    " if c.parent_id else "  "
                lines.append(f"{indent}- [{c.id}] {c.name}")
            chapter_lines.append("\n".join(lines))

        label = _SUBJECT_LABEL.get(subject, subject)
        user_prompt = (
            f"你是课程设计专家。基于以下【{label}】教材的章节列表，构建该学科的「学科知识体系」"
            f"知识点目录树（叶子节点带一句话说明）。\n\n章节列表：\n"
            + "\n".join(chapter_lines)[:5000]
            + "\n\n要求：\n"
            f"1. 按{label}学科知识体系组织（如 数学→数与代数/图形与几何/统计与概率→有理数→正负数；"
            "语文→阅读/写作/古诗文/综合性学习→篇目知识点；英语→词汇/语法/听说/阅读→具体点）。\n"
            "2. 知识点名称精炼、可复用；叶子节点为具体知识点。\n"
            "3. **每个叶子知识点都要带一句话说明/典型例子、学段(小学/初中)和难度(1-5，越大越难)**，用对象表示："
            '{"name":"正负数","desc":"表示相反意义的量，如温度零上零下","grade":"初中","difficulty":2}。\n'
            "4. 只输出 JSON 的 subjects 部分："
            '{"subjects":[{"name":"' + label + '","children":[{"name":"数与代数",'
            '"children":[{"name":"有理数","children":[{"name":"正负数","desc":"..."}]}]}]}]}'
        )
        logger.info(f"[stageA] Extracting KP tree for subject={subject} ...")
        try:
            resp = await client.complete(
                prompt=user_prompt,
                system_prompt="你是严谨的课程设计专家。只输出合法 JSON，不要多余文字。",
                max_tokens=3000,
                temperature=0.2,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[stageA] LLM failed for subject {subject}: {exc}")
            resp = ""
        raw = clean_thinking_tags(
            str(resp or ""), getattr(cfg, "binding", None), getattr(cfg, "model", None)
        ).strip()
        if not raw:
            logger.warning(f"[stageA] No output for subject {subject}, skipping")
            continue
        payload = parse_json_response(raw, logger_instance=logger, fallback={})
        subs = payload.get("subjects", []) or []
        if isinstance(subs, list):
            all_subjects.extend(subs)

    # only_link 模式：保留现有知识点树，直接进入阶段B 章节映射
    if only_link:
        items = store.list_kps("")
        if not items:
            raise HTTPException(500, "当前没有知识点，无法关联章节")
        # 阶段A 未填充章节名映射，这里补上
        for tb in all_tbs:
            for c in store.list_chapters(tb.id):
                chapter_names[c.id] = c.name
    else:
        if not all_subjects:
            raise HTTPException(500, "LLM 未返回任何有效知识点树")

        # ---- 展开合并知识点树 ----
        kp_list: list[dict[str, Any]] = []

        def _flatten(node: dict, parent_id: str | None, subject: str) -> None:
            name = str(node.get("name") or "").strip()
            if not name:
                return
            nid = _gen_id()
            entry: dict[str, Any] = {
                "id": nid, "name": name, "parent_id": parent_id, "subject": subject,
            }
            desc = node.get("desc") or node.get("description")
            if desc:
                entry["description"] = str(desc).strip()[:300]
            grade = node.get("grade")
            if grade:
                g = str(grade).strip()
                entry["grade"] = "小学" if "小" in g else ("初中" if "初" in g else g)
            diff = node.get("difficulty")
            if isinstance(diff, int) and 1 <= diff <= 5:
                entry["difficulty"] = diff
            kp_list.append(entry)
            for child in node.get("children", []):
                if isinstance(child, str):
                    cname = child.strip()
                    if not cname:
                        continue
                    cid = _gen_id()
                    kp_list.append(
                        {"id": cid, "name": cname, "parent_id": nid, "subject": subject}
                    )
                elif isinstance(child, dict):
                    _flatten(child, nid, subject)

        for s in all_subjects:
            sname = str(s.get("name") or "").strip()
            subject = _SUBJECT_ALIAS.get(sname, str(s.get("subject") or "math"))
            _flatten(s, None, subject)

        if not kp_list:
            raise HTTPException(500, "LLM 未生成任何知识点")

        # 合并模式：保留现有树，仅替换本次提取到的学科顶级（含其子树）
        existing = store.list_kps("")
        if existing:
            new_subjects = {k["subject"] for k in kp_list}
            drop_ids = {
                k.id
                for k in existing
                if k.subject in new_subjects and k.parent_id is None
            }
            if drop_ids:
                drop_all = set(drop_ids)
                changed = True
                while changed:
                    changed = False
                    for k in existing:
                        if k.parent_id in drop_all and k.id not in drop_all:
                            drop_all.add(k.id)
                            changed = True
                existing = [k for k in existing if k.id not in drop_all]
            merged = [k.model_dump(mode="json") for k in existing]
            merged.extend(kp_list)
            items = store.rebuild_kp_tree(merged)
        else:
            items = store.rebuild_kp_tree(kp_list)

    # ---- 清空旧章节关联 ----
    for _c in store.list_chapters(""):
        if _c.kp_ids:
            store.update_chapter(_c.id, {"kp_ids": []})

    kp_by_name: dict[str, str] = {k.name: k.id for k in items}
    kp_names_all: list[str] = [k.name for k in items]
    links = 0
    linked_chapters = 0

    def _match_kp(name: str) -> str | None:
        """精确匹配，失败则双向子串模糊匹配（容忍 LLM 轻微改写知识点名）."""
        n = str(name or "").strip()
        if not n:
            return None
        if n in kp_by_name:
            return kp_by_name[n]
        for kn, kid in kp_by_name.items():
            if n in kn or kn in n:
                return kid
        return None

    # ---- 阶段B: 每本教材单独生成章节→知识点映射（处理全部教材，含未提取学科） ----
    for tb in all_tbs:
        chs = store.list_chapters(tb.id)
        chs_sorted = sorted(chs, key=lambda x: (x.parent_id is not None, x.order))
        desc = "\n".join(
            f"- [{c.id}] {c.name}" for c in chs_sorted
        )
        label = _SUBJECT_LABEL.get(tb.subject, tb.subject)
        prompt2 = (
            f"为以下【{label}】教材的章节关联知识点。可用知识点（选准确名称）："
            + "、".join(kp_names_all[:120])
            + f"\n\n待关联章节：\n{desc}\n\n"
            "为每个章节选 2~6 个最相关知识点（尽量用叶子知识点），一个都不能漏。"
            '只输出 JSON：{"chapter_kp_map":{"<章节id>":["知识点名1","知识点名2"]}}'
        )
        logger.info(f"[stageB] Linking chapters for {tb.name} ...")
        try:
            resp2 = await asyncio.wait_for(
                client.complete(
                    prompt=prompt2,
                    system_prompt="你是严谨的课程设计专家。只输出合法 JSON，不要多余文字。",
                    max_tokens=3000,
                    temperature=0.1,
                ),
                timeout=120,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[stageB] LLM failed for {tb.name}: {exc}")
            resp2 = ""
        raw2 = clean_thinking_tags(
            str(resp2 or ""), getattr(cfg, "binding", None), getattr(cfg, "model", None)
        ).strip()
        if not raw2:
            logger.warning(f"[stageB] No output for {tb.name}, skipping")
            continue
        payload2 = parse_json_response(raw2, logger_instance=logger, fallback={})
        for cid, names in (payload2.get("chapter_kp_map") or {}).items():
            if cid not in chapter_names:
                continue
            added = 0
            for name in names:
                kid = _match_kp(name)
                if kid:
                    store.link_chapter_kp(cid, kid)
                    added += 1
                    links += 1
            if added:
                linked_chapters += 1

    # ---- 补充：对仍未关联的章节二次 LLM 映射 ----
    unlinked = [
        c for c in store.list_chapters("") if not c.kp_ids and c.id in chapter_names
    ]
    if unlinked:
        unlinked_desc = "\n".join(f"- [{c.id}] {c.name}" for c in unlinked[:80])
        prompt3 = (
            "为以下章节关联知识点。可用知识点（选准确名称）："
            + "、".join(kp_names_all[:300])
            + "\n\n待关联章节：\n"
            + unlinked_desc
            + "\n\n为每个章节选 2~6 个知识点，一个都不能漏。"
            '只输出 JSON：{"chapter_kp_map":{"<章节id>":["知识点名1","知识点名2"]}}'
        )
        try:
            resp3 = await asyncio.wait_for(
                client.complete(
                    prompt=prompt3,
                    system_prompt="你是严谨的课程设计专家。只输出合法 JSON，不要多余文字。",
                    max_tokens=3000,
                    temperature=0.1,
                ),
                timeout=120,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"[complement] LLM failed: {exc}")
            resp3 = ""
        raw3 = clean_thinking_tags(
            str(resp3 or ""), getattr(cfg, "binding", None), getattr(cfg, "model", None)
        ).strip()
        payload3 = parse_json_response(raw3, logger_instance=logger, fallback={})
        for cid, names in (payload3.get("chapter_kp_map") or {}).items():
            if cid not in chapter_names:
                continue
            added = 0
            for name in names:
                kid = _match_kp(name)
                if kid:
                    store.link_chapter_kp(cid, kid)
                    added += 1
                    links += 1
            if added:
                linked_chapters += 1

    return {
        "rebuilt": len(items),
        "linked_chapters": linked_chapters,
        "linked_links": links,
        "tree": store.kp_tree(),
    }



__all__ = ["router", "CurriculumStore", "KnowledgePoint", "Textbook", "TextbookPage", "Chapter"]
