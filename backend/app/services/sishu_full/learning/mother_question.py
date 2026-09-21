"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.services.sishu_full.services.file_io import atomic_write_text as _atomic_write_text
from app.services.sishu_full.services.path_service import get_path_service

logger = logging.getLogger(__name__)

# Module-level re-entrant lock so CAS semantics hold across all store instances.
# Some operations update two files as one logical transaction (for example,
# deleting a variant and adjusting its mother's counter), so they may call a
# helper that also acquires the store lock.
_cas_lock = threading.RLock()


def _now() -> float:
    return time.time()


def _gen_id() -> str:
    return uuid.uuid4().hex


# --------------------------------------------------------------------------- #
# Models (Pydantic, extra="ignore" to match DeepTutor convention)            #
# --------------------------------------------------------------------------- #

class MotherQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    subject: str = "math"
    grade: str | None = None                # 一年级...六年级
    category: str | None = None             # 应用题/计算/几何/统计/综合
    archetype_code: str | None = None       # 内部编码 MQ_CHICKEN_RABBIT
    question_text: str
    standard_answer: str | None = None
    wrong_answer: str | None = None          # 学生错误答案（你的答案）
    detailed_analysis: str | None = None     # 详细解析（文本形式，区别于 solution_steps 列表）
    note: str | None = None                  # 学生笔记
    solution_steps: list[dict[str, Any]] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    difficulty: int = 3                     # 1-5
    knowledge_point_id: str | None = None   # 挂 DeepTutor KnowledgePoint
    textbook_id: str | None = None
    chapter_id: str | None = None
    cover_image_url: str | None = None
    photo_url: str | None = None              # 题目图（原题截图 / 拍照切题小图）
    wrong_answer_image_url: str | None = None  # 错误答案截图
    source_image_url: str | None = None       # 拍照整页原图 URL
    crop_box: list[int] | None = None         # 切题裁剪框 [x1,y1,x2,y2]
    ocr_text: str | None = None               # OCR 识别的原始文本
    has_checkmark: bool | None = None         # 红笔标记（是否有 ✓，None=未检测）
    tags: list[str] = Field(default_factory=list)  # 自由标签
    assets: list[dict[str, Any]] = Field(default_factory=list)  # 多图资产 [{url,type,ocr_text,create_time}]
    simhash: int | None = None
    variant_count: int = 0
    video_count: int = 0
    status: str = "active"                  # active/deleted
    deleted_time: float | None = None       # 软删除时间（回收站排序用）
    mastery_status: str = "not_mastered"    # not_mastered/reviewing/mastered
    wrong_reason: str | None = None        # 错因（错误模式分析用）
    wrong_advice: str | None = None        # 错因改进建议（P2-B LLM 归因输出）
    related_lecture_doc_ids: list[str] = Field(default_factory=list)  # 关联讲义文档ID
    correct_transferred_at: float | None = None  # 转正确题时间（None=未转）
    create_time: float = Field(default_factory=_now)
    update_time: float = Field(default_factory=_now)
    created_at: str = ""  # ISO 时间戳（P2-A 周聚合用；旧数据缺省 "" 向后兼容）


class QuestionVariant(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    mother_id: str
    question_text: str
    answer: str | None = None
    solution_steps: list[dict[str, Any]] = Field(default_factory=list)
    difficulty: int = 3
    variant_type: str | None = None         # 数值变式/情境变式/逆向变式/综合变式
    source: str = "manual"                  # manual/llm_gen/ocr_import
    simhash: int | None = None
    status: str = "active"
    create_time: float = Field(default_factory=_now)
    update_time: float = Field(default_factory=_now)


class Attempt(BaseModel):
    """单次答题记录 (移植自 ragflow WrongQuestionAttempt)."""
    model_config = ConfigDict(extra="ignore")

    id: str
    mother_id: str
    variant_id: str | None = None
    is_correct: bool
    user_answer: str | None = None          # 学生作答
    source: str = "manual"                  # manual/review/photo
    time_spent: float | None = None         # 作答耗时（秒）
    rating: int | None = None              # FSRS 评分 1-4（如使用 FSRS）
    create_time: float = Field(default_factory=_now)

class MotherQuestionStore:
    """JSON-backed store for mother questions and their variants.

    Layout under <workspace>/mother_questions/:
      index.json    - list of all MotherQuestion
      variants.json - list of all QuestionVariant
    Single-file list is fine for a few thousand entries; migrate to SQLite if it grows.
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = root or (get_path_service().get_workspace_dir() / "mother_questions")
        self._root.mkdir(parents=True, exist_ok=True)
        self._mq_path = self._root / "index.json"
        self._vq_path = self._root / "variants.json"

    # ---------- mother questions ----------

    def _load_mq(self) -> list[MotherQuestion]:
        if not self._mq_path.exists():
            return []
        data = json.loads(self._mq_path.read_text(encoding="utf-8"))
        return [MotherQuestion.model_validate(d) for d in data]

    def _save_mq(self, items: list[MotherQuestion]) -> None:
        text = json.dumps(
            [m.model_dump(mode="json") for m in items],
            ensure_ascii=False, indent=2,
        )
        _atomic_write_text(self._mq_path, text)

    def list_mothers(
        self,
        *,
        subject: str | None = None,
        grade: str | None = None,
        category: str | None = None,
        knowledge_point_id: str | None = None,
        textbook_id: str | None = None,
        chapter_id: str | None = None,
        tag: str | None = None,
        difficulty_min: int | None = None,
        difficulty_max: int | None = None,
        keyword: str | None = None,
        status: str = "active",
        start_date: str | None = None,
        end_date: str | None = None,
        sort_by: str = "create_time",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[MotherQuestion], int]:
        items = self._load_mq()
        # filter
        out: list[MotherQuestion] = []
        for m in items:
            if m.status != status:
                continue
            if subject and m.subject != subject:
                continue
            if grade and m.grade != grade:
                continue
            if category and m.category != category:
                continue
            if knowledge_point_id and m.knowledge_point_id != knowledge_point_id:
                continue
            if textbook_id and m.textbook_id != textbook_id:
                continue
            if chapter_id and m.chapter_id != chapter_id:
                continue
            if tag and tag not in (m.tags or []):
                continue
            if difficulty_min is not None and m.difficulty < difficulty_min:
                continue
            if difficulty_max is not None and m.difficulty > difficulty_max:
                continue
            if start_date:
                import datetime as _dt
                try:
                    sd = _dt.datetime.strptime(start_date, "%Y-%m-%d").timestamp()
                    if m.create_time < sd:
                        continue
                except ValueError:
                    pass
            if end_date:
                import datetime as _dt
                try:
                    ed = _dt.datetime.strptime(end_date, "%Y-%m-%d").timestamp() + 86400
                    if m.create_time > ed:
                        continue
                except ValueError:
                    pass
            if keyword:
                kw = keyword.lower()
                # 搜索 title + question_text + archetype_code + solution_steps + wrong_reason + tags
                steps_text = " ".join(s.get("text", "") for s in (m.solution_steps or []))
                hay = f"{m.title} {m.question_text} {m.archetype_code or ''} {steps_text} {m.wrong_reason or ''} {' '.join(m.tags or [])}".lower()
                if kw not in hay:
                    continue
            out.append(m)
        sort_field = {"create_time": "create_time", "difficulty": "difficulty", "title": "title"}.get(sort_by, "create_time")
        out.sort(key=lambda x: getattr(x, sort_field, x.create_time), reverse=(sort_order != "asc"))
        total = len(out)
        start = (page - 1) * page_size
        return out[start : start + page_size], total

    def list_all_mothers(self, status: str = "active") -> list[MotherQuestion]:
        """All mothers (no pagination) - for analysis aggregation."""
        items = [m for m in self._load_mq() if m.status == status]
        items.sort(key=lambda x: x.create_time, reverse=True)
        return items

    def find_duplicates(
        self, simhash_val: int | None, threshold: int = 4, exclude_id: str | None = None,
    ) -> list[dict]:
        """Return [{id,title,distance,grade,category}] within hamming threshold."""
        if simhash_val is None:
            return []
        from app.services.sishu_full.learning.simhash_util import hamming_distance

        out: list[dict] = []
        for m in self._load_mq():
            if m.id == exclude_id or m.simhash is None:
                continue
            d = hamming_distance(simhash_val, m.simhash)
            if d <= threshold:
                out.append({
                    "id": m.id, "title": m.title, "distance": d,
                    "grade": m.grade, "category": m.category,
                })
        out.sort(key=lambda x: x["distance"])
        return out[:10]

    def find_similar(
        self, mid: str, top_k: int = 5, threshold: int = 10,
    ) -> list[dict]:
        """Find similar questions by simhash, returning rich detail.

        Returns [{id,title,subject,distance,similarity,snippet,grade,category}].
        similarity = 1 - distance/64 (simhash is 64-bit).
        """
        m = self.get_mother(mid)
        if not m or m.simhash is None:
            return []
        from app.services.sishu_full.learning.simhash_util import hamming_distance

        out: list[dict] = []
        for other in self._load_mq():
            if other.id == mid or other.simhash is None:
                continue
            if other.status == "deleted":
                continue
            d = hamming_distance(m.simhash, other.simhash)
            if d <= threshold:
                snippet = (other.question_text or "")[:150]
                out.append({
                    "id": other.id,
                    "title": other.title,
                    "subject": other.subject,
                    "distance": d,
                    "similarity": round(1 - d / 64, 4),
                    "snippet": snippet,
                    "grade": other.grade,
                    "category": other.category,
                    "difficulty": other.difficulty,
                    "mastery_status": other.mastery_status,
                })
        out.sort(key=lambda x: x["distance"])
        return out[:top_k]

    def list_correct(self, limit: int = 100) -> list[MotherQuestion]:
        """List questions transferred to correct (correct_transferred_at is not None)."""
        items = [m for m in self._load_mq() if m.correct_transferred_at is not None]
        items.sort(key=lambda m: m.correct_transferred_at or 0, reverse=True)
        return items[:limit]

    def get_mother(self, mid: str) -> MotherQuestion | None:
        for m in self._load_mq():
            if m.id == mid:
                return m
        return None

    def create_mother(self, m: MotherQuestion) -> MotherQuestion:
        if not m.created_at:
            m.created_at = datetime.now(timezone.utc).isoformat()
        with _cas_lock:
            items = self._load_mq()
            items.append(m)
            self._save_mq(items)
        return m

    def update_mother(self, mid: str, patch: dict[str, Any]) -> MotherQuestion | None:
        with _cas_lock:
            items = self._load_mq()
            for m in items:
                if m.id == mid:
                    for k, v in patch.items():
                        if hasattr(m, k) and k not in ("id", "create_time"):
                            setattr(m, k, v)
                    m.update_time = _now()
                    self._save_mq(items)
                    return m
        return None

    def delete_mother(self, mid: str, hard: bool = False) -> bool:
        with _cas_lock:
            items = self._load_mq()
            for i, m in enumerate(items):
                if m.id == mid:
                    if hard:
                        items.pop(i)
                    else:
                        m.status = "deleted"
                        m.deleted_time = _now()
                        m.update_time = _now()
                    self._save_mq(items)
                    return True
        return False

    def restore_mother(self, mid: str) -> bool:
        """从回收站恢复（status deleted -> active）."""
        with _cas_lock:
            items = self._load_mq()
            for m in items:
                if m.id == mid and m.status == "deleted":
                    m.status = "active"
                    m.deleted_time = None
                    m.update_time = _now()
                    self._save_mq(items)
                    return True
        return False

    def list_trash(self, page: int = 1, page_size: int = 20) -> tuple[list[MotherQuestion], int]:
        """回收站列表（仅 status=deleted）."""
        items = [m for m in self._load_mq() if m.status == "deleted"]
        items.sort(key=lambda x: x.deleted_time or x.update_time, reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return items[start : start + page_size], total

    def _bump_counter(self, mid: str, field: str, delta: int) -> None:
        """Adjust variant_count / video_count on the mother (best-effort)."""
        with _cas_lock:
            items = self._load_mq()
            for m in items:
                if m.id == mid:
                    cur = getattr(m, field, 0) or 0
                    setattr(m, field, max(0, cur + delta))
                    m.update_time = _now()
                    self._save_mq(items)
                    return

    # ---------- review states (SpacedRepetitionScheduler) ----------

    def _rs_path(self) -> Path:
        return self._root / "review_states.json"

    def _load_rs(self) -> dict[str, dict]:
        p = self._rs_path()
        if not p.exists():
            return {}
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_rs(self, rs: dict[str, dict]) -> None:
        _atomic_write_text(self._rs_path(), json.dumps(rs, ensure_ascii=False, indent=2))

    def append_review_log(self, entry: dict[str, Any]) -> int:
        """Append one review event atomically and return the new total."""
        with _cas_lock:
            path = self._root / "review_log.json"
            try:
                log = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
                if not isinstance(log, list):
                    log = []
            except (OSError, ValueError, TypeError):
                log = []
            log.append(entry)
            _atomic_write_text(path, json.dumps(log, ensure_ascii=False, indent=2))
            return len(log)

    def list_review_log(self, mother_id: str | None = None) -> list[dict]:
        """Read review events, tolerating a missing or damaged legacy file."""
        with _cas_lock:
            path = self._root / "review_log.json"
            if not path.exists():
                return []
            try:
                log = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                return []
            if not isinstance(log, list):
                return []
            if mother_id is not None:
                return [item for item in log if item.get("mother_id") == mother_id]
            return log

    def get_review_state(self, mid: str) -> dict | None:
        return self._load_rs().get(mid)

    def upsert_review_state(self, mid: str, is_correct: bool) -> dict:
        """Update review state via DeepTutor SpacedRepetitionScheduler (legacy binary)."""
        from app.services.sishu_full.learning.scheduler import SpacedRepetitionScheduler
        from app.services.sishu_full.learning.models import KnowledgeType, RepetitionState

        with _cas_lock:
            scheduler = SpacedRepetitionScheduler()
            rs = self._load_rs()
            cur = rs.get(mid)
            if cur:
                state = RepetitionState.model_validate(cur)
            else:
                state = scheduler.get_initial_state(KnowledgeType.CONCEPT)
            new_state = scheduler.schedule_next(state, KnowledgeType.CONCEPT, is_correct)
            rs[mid] = new_state.model_dump(mode="json")
            self._save_rs(rs)

            # 同步 mastery_status: 连对足够次数 -> mastered, 否则 reviewing
            items = self._load_mq()
            for m in items:
                if m.id == mid:
                    if new_state.consecutive_correct >= 2 and new_state.interval_index >= 2:
                        m.mastery_status = "mastered"
                    else:
                        m.mastery_status = "reviewing"
                    m.update_time = _now()
                    self._save_mq(items)
                    break
            self._refresh_learner_profile()
            self._emit_review_event(mid, 3 if is_correct else 1)
        return rs[mid]

    def upsert_review_fsrs(self, mid: str, rating: int) -> dict:
        """Update review state via FSRS-5 (rating 1=Again 2=Hard 3=Good 4=Easy)."""
        from app.services.sishu_full.learning import fsrs as _fsrs

        with _cas_lock:
            rs = self._load_rs()
            cur = rs.get(mid)
            if cur and cur.get("stability") is not None:
                card = _fsrs.review(cur, rating)
            else:
                card = _fsrs.new_card(rating)
            rs[mid] = card
            self._save_rs(rs)

            # 同步 mastery_status: reps>=3 且 stability>=7 -> mastered, else reviewing
            items = self._load_mq()
            for m in items:
                if m.id == mid:
                    if card["reps"] >= 3 and card["stability"] >= 7:
                        m.mastery_status = "mastered"
                    elif card["reps"] >= 1:
                        m.mastery_status = "reviewing"
                    else:
                        m.mastery_status = "not_mastered"
                    m.update_time = _now()
                    self._save_mq(items)
                    break
            self._refresh_learner_profile()
            self._emit_review_event(mid, rating)
        return rs[mid]

    def _refresh_learner_profile(self) -> None:
        """Best-effort refresh of the deterministic L2/L3 learning memory docs
        so review outcomes immediately show up in the learner profile."""
        try:
            from app.services.sishu_full.learning.learner_profile import (
                write_learning_l2_md,
                write_learning_profile_md,
            )

            write_learning_profile_md()
            write_learning_l2_md()
        except Exception:  # noqa: BLE001
            logger.warning("learner_profile refresh failed after review", exc_info=True)

    def _emit_review_event(self, mid: str, rating: int) -> None:
        """Emit one spaced-repetition review event into L1 learning trace."""
        try:
            from app.services.sishu_full.learning.learner_profile import emit_learning_event

            items = self._load_mq()
            mother = next((m for m in items if m.id == mid), None)
            emit_learning_event(
                kind="review",
                payload={
                    "mother_id": mid,
                    "question_id": mid,
                    "kp_id": mother.knowledge_point_id if mother else None,
                    "kp_name": mother.title if mother else "",
                    "rating": rating,
                    "mastery_status_after": mother.mastery_status if mother else None,
                },
            )
        except Exception:  # noqa: BLE001
            logger.warning("review event emit failed", exc_info=True)

    def get_retention(self, mid: str) -> float:
        """当前保留率 0..100 (FSRS forgetting curve)."""
        from app.services.sishu_full.learning import fsrs as _fsrs

        st = self._load_rs().get(mid)
        if not st or st.get("stability") is None:
            return 0.0
        return _fsrs.retrievability(st) * 100

    def list_due(self, max_items: int = 20) -> list[MotherQuestion]:
        """Mothers whose next_review_at / FSRS due <= now (or never reviewed)."""
        import time as _time

        rs = self._load_rs()
        now = _time.time()
        due: list[MotherQuestion] = []
        for m in self._load_mq():
            if m.status != "active":
                continue
            st = rs.get(m.id)
            if st is None:
                # 从未复习 -> 到期
                due.append(m)
            elif st.get("due") is not None:
                # FSRS 卡片
                if st["due"] <= now:
                    due.append(m)
            elif st.get("next_review_at") is None or st["next_review_at"] <= now:
                # 旧格式 scheduler 状态
                due.append(m)
        due.sort(key=lambda x: x.create_time)
        return due[:max_items]

    def due_count(self) -> int:
        return len(self.list_due(max_items=10000))

    # ---------- tags (virtual tag store) ----------

    def _tags_path(self) -> Path:
        return self._root / "tags.json"

    def list_all_tags(self) -> list[dict]:
        """收集所有母题用过的标签 + tags.json 中预定义的标签（去重）."""
        seen: dict[str, dict] = {}
        # 1. tags.json 预定义
        p = self._tags_path()
        if p.exists():
            try:
                for t in json.loads(p.read_text(encoding="utf-8")):
                    seen[t["name"]] = t
            except Exception:
                pass
        # 2. 从母题收集
        for m in self._load_mq():
            for name in (m.tags or []):
                if name and name not in seen:
                    seen[name] = {"id": name, "name": name, "color": None}
        return list(seen.values())

    def create_tag(self, name: str, color: str | None = None) -> dict:
        """创建标签实体（存 tags.json）."""
        with _cas_lock:
            p = self._tags_path()
            tags: list = []
            if p.exists():
                try:
                    tags = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    tags = []
            if any(t["name"] == name for t in tags):
                return {"id": name, "name": name, "color": color}
            tag = {"id": name, "name": name, "color": color}
            tags.append(tag)
            _atomic_write_text(p, json.dumps(tags, ensure_ascii=False, indent=2))
            return tag

    def delete_tag(self, name: str) -> bool:
        """删除标签实体 + 从所有母题移除该标签."""
        with _cas_lock:
            p = self._tags_path()
            if p.exists():
                tags = json.loads(p.read_text(encoding="utf-8"))
                tags = [t for t in tags if t["name"] != name]
                _atomic_write_text(p, json.dumps(tags, ensure_ascii=False, indent=2))
            # 从母题移除
            items = self._load_mq()
            changed = False
            for m in items:
                if name in (m.tags or []):
                    m.tags = [t for t in (m.tags or []) if t != name]
                    changed = True
            if changed:
                self._save_mq(items)
            return True

    # ---------- attempts (答题记录) ----------

    def _att_path(self) -> Path:
        return self._root / "attempts.json"

    def _load_att(self) -> list[dict]:
        p = self._att_path()
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save_att(self, items: list[dict]) -> None:
        _atomic_write_text(self._att_path(), json.dumps(items, ensure_ascii=False, indent=2))

    def list_attempts(self, mother_id: str | None = None, limit: int = 100) -> list[dict]:
        items = self._load_att()
        if mother_id:
            items = [a for a in items if a.get("mother_id") == mother_id]
        items.sort(key=lambda x: x.get("create_time", 0), reverse=True)
        return items[:limit]

    def create_attempt(self, a: Attempt) -> Attempt:
        with _cas_lock:
            items = self._load_att()
            items.append(a.model_dump(mode="json"))
            self._save_att(items)
        return a

    def delete_attempt(self, aid: str) -> bool:
        with _cas_lock:
            items = self._load_att()
            new = [a for a in items if a.get("id") != aid]
            if len(new) != len(items):
                self._save_att(new)
                return True
        return False

    # ---------- assets (多图资产) ----------

    def add_asset(self, mid: str, asset: dict) -> dict | None:
        with _cas_lock:
            items = self._load_mq()
            for m in items:
                if m.id == mid:
                    m.assets = (m.assets or []) + [asset]
                    m.update_time = _now()
                    self._save_mq(items)
                    return asset
        return None

    def remove_asset(self, mid: str, asset_url: str) -> bool:
        with _cas_lock:
            items = self._load_mq()
            for m in items:
                if m.id == mid:
                    before = len(m.assets or [])
                    m.assets = [a for a in (m.assets or []) if a.get("url") != asset_url]
                    if len(m.assets) < before:
                        m.update_time = _now()
                        self._save_mq(items)
                        return True
                    return False
        return False

    # ---------- variants ----------

    def _load_vq(self) -> list[QuestionVariant]:
        if not self._vq_path.exists():
            return []
        data = json.loads(self._vq_path.read_text(encoding="utf-8"))
        return [QuestionVariant.model_validate(d) for d in data]

    def _save_vq(self, items: list[QuestionVariant]) -> None:
        text = json.dumps(
            [v.model_dump(mode="json") for v in items],
            ensure_ascii=False, indent=2,
        )
        _atomic_write_text(self._vq_path, text)

    def list_variants(
        self, mother_id: str, *, status: str = "active",
    ) -> list[QuestionVariant]:
        out = [
            v for v in self._load_vq()
            if v.mother_id == mother_id and v.status == status
        ]
        out.sort(key=lambda x: x.create_time, reverse=True)
        return out

    def get_variant(self, vid: str) -> QuestionVariant | None:
        for v in self._load_vq():
            if v.id == vid:
                return v
        return None

    def create_variant(self, v: QuestionVariant) -> QuestionVariant:
        with _cas_lock:
            items = self._load_vq()
            items.append(v)
            self._save_vq(items)
        self._bump_counter(v.mother_id, "variant_count", 1)
        return v

    def update_variant(self, vid: str, patch: dict[str, Any]) -> QuestionVariant | None:
        with _cas_lock:
            items = self._load_vq()
            for v in items:
                if v.id == vid:
                    for k, val in patch.items():
                        if hasattr(v, k) and k not in ("id", "create_time", "mother_id"):
                            setattr(v, k, val)
                    v.update_time = _now()
                    self._save_vq(items)
                    return v
        return None

    def delete_variant(self, vid: str, hard: bool = False) -> bool:
        with _cas_lock:
            items = self._load_vq()
            for i, v in enumerate(items):
                if v.id == vid:
                    mid = v.mother_id
                    was_active = v.status == "active"
                    if hard:
                        items.pop(i)
                    else:
                        v.status = "deleted"
                        v.update_time = _now()
                    self._save_vq(items)
                    if was_active:
                        self._bump_counter(mid, "variant_count", -1)
                    return True
        return False


__all__ = [
    "MotherQuestion",
    "QuestionVariant",
    "Attempt",
    "MotherQuestionStore",
    "_gen_id",
    "_now",
]
