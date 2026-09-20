# -*- coding: utf-8 -*-
"""v4批6 6.1：PG 版 MotherQuestionStore——vendor store 22 消费方法面 1:1（行为同构）。
数据=sishu_mq_docs/sishu_question_variants/sishu_mq_review_state/sishu_mq_tags/sishu_mq_attempts
（全字段 JSONB doc+typed 热列；批6 迁移脚本 sishu_migrate/mother_questions.py 已灌 184+6+27）。
文档对象=AttrObj（属性访问+model_dump 兼容——vendor router 处理器零改语义移植的载体）。
simhash=vendor 纯函数 hamming_distance 移植（XOR popcount，零 vendor 导入）。"""
import json
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from .pg import engine

_cas_lock = threading.Lock()


def _now() -> float:
    return time.time()


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def hamming_distance(a: int, b: int) -> int:
    """simhash 汉明距（vendor simhash_util 同式：XOR popcount，纯函数移植）。"""
    return bin(a ^ b).count("1")


class AttrObj:
    """dict 的属性视图——vendor router 的 m.title/model_dump 访问语义载体。"""

    def __init__(self, data: dict):
        object.__setattr__(self, "_d", dict(data or {}))

    def __getattr__(self, k):
        try:
            return object.__getattribute__(self, "_d")[k]
        except KeyError:
            return None

    def __setattr__(self, k, v):
        object.__getattribute__(self, "_d")[k] = v

    def model_dump(self, mode: str = "json") -> dict:
        return dict(object.__getattribute__(self, "_d"))

    @classmethod
    def model_validate(cls, d: dict):
        return cls(d)

    def to_dict(self) -> dict:
        return dict(object.__getattribute__(self, "_d"))


class MotherQuestionStorePG:
    """PG 单轨 store——vendor MotherQuestionStore 消费方法面 1:1。"""

    # ---------- 装载（JSONB doc→AttrObj） ----------
    def _load_mq(self) -> list[AttrObj]:
        with engine.connect() as c:
            rows = c.execute(text(
                "SELECT doc FROM sishu_mq_docs ORDER BY update_time DESC NULLS LAST")).fetchall()
        return [AttrObj(r[0]) for r in rows]

    def _save_mq_item(self, m: AttrObj) -> None:
        d = m.model_dump()
        with engine.begin() as c:
            c.execute(text("""
                INSERT INTO sishu_mq_docs (mq_id, doc, status, subject, grade, knowledge_point_id,
                                           mastery_status, simhash, update_time)
                VALUES (:i, CAST(:d AS JSONB), :s, :sj, :g, :kp, :ms, :sh, :u)
                ON CONFLICT (mq_id) DO UPDATE SET doc=CAST(:d AS JSONB), status=:s, subject=:sj,
                  grade=:g, knowledge_point_id=:kp, mastery_status=:ms, simhash=:sh, update_time=:u"""),
                {"i": d.get("id"), "d": json.dumps(d, ensure_ascii=False),
                 "s": d.get("status") or "active", "sj": d.get("subject"), "g": d.get("grade"),
                 "kp": d.get("knowledge_point_id"), "ms": d.get("mastery_status"),
                 "sh": d.get("simhash"), "u": d.get("update_time") or 0})

    def _del_mq(self, mq_id: str) -> None:
        with engine.begin() as c:
            c.execute(text("DELETE FROM sishu_mq_docs WHERE mq_id=:i"), {"i": mq_id})

    # ---------- 母题 CRUD/列表 ----------
    def list_mothers(self, *, subject=None, grade=None, category=None, knowledge_point_id=None,
                     textbook_id=None, chapter_id=None, tag=None, difficulty_min=None,
                     difficulty_max=None, keyword=None, status="active", start_date=None,
                     end_date=None, sort_by="create_time", sort_order="desc",
                     page=1, page_size=20):
        items = self._load_mq()
        out = []
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
            if difficulty_min is not None and (m.difficulty or 0) < difficulty_min:
                continue
            if difficulty_max is not None and (m.difficulty or 0) > difficulty_max:
                continue
            if start_date:
                import datetime as _dt
                try:
                    sd = _dt.datetime.strptime(start_date, "%Y-%m-%d").timestamp()
                    if (m.create_time or 0) < sd:
                        continue
                except ValueError:
                    pass
            if end_date:
                import datetime as _dt
                try:
                    ed = _dt.datetime.strptime(end_date, "%Y-%m-%d").timestamp() + 86400
                    if (m.create_time or 0) > ed:
                        continue
                except ValueError:
                    pass
            if keyword:
                kw = keyword.lower()
                steps_text = " ".join(s.get("text", "") for s in (m.solution_steps or []))
                hay = f"{m.title} {m.question_text} {m.archetype_code or ''} {steps_text} {m.wrong_reason or ''} {' '.join(m.tags or [])}".lower()
                if kw not in hay:
                    continue
            out.append(m)
        sort_field = {"create_time": "create_time", "difficulty": "difficulty",
                      "title": "title"}.get(sort_by, "create_time")
        out.sort(key=lambda x: getattr(x, sort_field, x.create_time) or 0,
                 reverse=(sort_order != "asc"))
        total = len(out)
        start = (page - 1) * page_size
        return out[start:start + page_size], total

    def list_all_mothers(self, status: str = "active") -> list[AttrObj]:
        items = [m for m in self._load_mq() if m.status == status]
        items.sort(key=lambda x: x.create_time or 0, reverse=True)
        return items

    def find_duplicates(self, simhash_val, threshold: int = 4, exclude_id: str | None = None):
        if simhash_val is None:
            return []
        out = []
        for m in self._load_mq():
            if m.id == exclude_id or m.simhash is None:
                continue
            d = hamming_distance(int(simhash_val), int(m.simhash))
            if d <= threshold:
                out.append({"id": m.id, "title": m.title, "distance": d,
                            "grade": m.grade, "category": m.category})
        out.sort(key=lambda x: x["distance"])
        return out[:10]

    def find_similar(self, mid: str, top_k: int = 5, threshold: int = 10):
        m = self.get_mother(mid)
        if not m or m.simhash is None:
            return []
        out = []
        for other in self._load_mq():
            if other.id == mid or other.simhash is None:
                continue
            if other.status == "deleted":
                continue
            d = hamming_distance(int(m.simhash), int(other.simhash))
            if d <= threshold:
                out.append({"id": other.id, "title": other.title, "subject": other.subject,
                            "distance": d, "similarity": round(1 - d / 64, 4),
                            "snippet": (other.question_text or "")[:150], "grade": other.grade,
                            "category": other.category, "difficulty": other.difficulty,
                            "mastery_status": other.mastery_status})
        out.sort(key=lambda x: x["distance"])
        return out[:top_k]

    def list_correct(self, limit: int = 100):
        items = [m for m in self._load_mq() if m.correct_transferred_at is not None]
        items.sort(key=lambda m: m.correct_transferred_at or 0, reverse=True)
        return items[:limit]

    def get_mother(self, mid: str):
        with engine.connect() as c:
            row = c.execute(text("SELECT doc FROM sishu_mq_docs WHERE mq_id=:i"),
                            {"i": mid}).fetchone()
        return AttrObj(row[0]) if row else None

    def create_mother(self, m: AttrObj):
        if not m.created_at:
            m.created_at = datetime.now(timezone.utc).isoformat()
        with _cas_lock:
            self._save_mq_item(m)
        return m

    def update_mother(self, mid: str, patch: dict[str, Any]):
        with _cas_lock:
            m = self.get_mother(mid)
            if not m:
                return None
            for k, v in patch.items():
                if k not in ("id", "create_time"):
                    setattr(m, k, v)
            m.update_time = _now()
            self._save_mq_item(m)
            return m

    def delete_mother(self, mid: str, hard: bool = False) -> bool:
        with _cas_lock:
            m = self.get_mother(mid)
            if not m:
                return False
            if hard:
                self._del_mq(mid)
                return True
            m.status = "deleted"
            m.deleted_time = _now()
            self._save_mq_item(m)
            return True

    def restore_mother(self, mid: str) -> bool:
        with _cas_lock:
            m = self.get_mother(mid)
            if not m or m.status != "deleted":
                return False
            m.status = "active"
            m.deleted_time = None
            self._save_mq_item(m)
            return True

    def list_trash(self, page: int = 1, page_size: int = 20):
        items = [m for m in self._load_mq() if m.status == "deleted"]
        items.sort(key=lambda x: x.deleted_time or 0, reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return items[start:start + page_size], total

    def _bump_counter(self, mid: str, field: str, delta: int) -> None:
        m = self.get_mother(mid)
        if not m:
            return
        setattr(m, field, (getattr(m, field, 0) or 0) + delta)
        self._save_mq_item(m)

    # ---------- 变体 ----------
    def _load_vq(self) -> list[AttrObj]:
        with engine.connect() as c:
            rows = c.execute(text("SELECT doc FROM sishu_question_variants")).fetchall()
        return [AttrObj(r[0]) for r in rows]

    def _save_vq_item(self, v: AttrObj) -> None:
        d = v.model_dump()
        with engine.begin() as c:
            c.execute(text("""
                INSERT INTO sishu_question_variants (vq_id, mother_id, doc, status, update_time)
                VALUES (:i, :m, CAST(:d AS JSONB), :s, :u)
                ON CONFLICT (vq_id) DO UPDATE SET doc=CAST(:d AS JSONB), status=:s, update_time=:u"""),
                {"i": d.get("id"), "m": d.get("mother_id"), "d": json.dumps(d, ensure_ascii=False),
                 "s": d.get("status") or "active", "u": d.get("update_time") or 0})

    def list_variants(self, mother_id: str | None = None, status: str | None = None,
                      page: int = 1, page_size: int = 20):
        items = self._load_vq()
        if mother_id:
            items = [v for v in items if v.mother_id == mother_id]
        if status:
            items = [v for v in items if v.status == status]
        items.sort(key=lambda x: x.update_time or 0, reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return items[start:start + page_size], total

    def update_variant(self, vid: str, patch: dict[str, Any]):
        with _cas_lock:
            for v in self._load_vq():
                if v.id == vid:
                    for k, val in patch.items():
                        if k not in ("id", "create_time"):
                            setattr(v, k, val)
                    v.update_time = _now()
                    self._save_vq_item(v)
                    return v
        return None

    def delete_variant(self, vid: str, hard: bool = False) -> bool:
        with _cas_lock:
            for v in self._load_vq():
                if v.id == vid:
                    if hard:
                        with engine.begin() as c:
                            c.execute(text("DELETE FROM sishu_question_variants WHERE vq_id=:i"),
                                      {"i": vid})
                    else:
                        v.status = "deleted"
                        v.update_time = _now()
                        self._save_vq_item(v)
                    return True
        return False

    # ---------- 复习状态（FSRS 语义上移到 router/service 层——本 store 存取状态 doc） ----------
    def _rs_all(self) -> dict:
        with engine.connect() as c:
            rows = c.execute(text("SELECT mq_id, doc FROM sishu_mq_review_state")).fetchall()
        return {r[0]: r[1] for r in rows}

    def append_review_log(self, entry: dict) -> int:
        # review log=进度 JSONB 内 rows（vendor rs doc 同构：rs['logs'] 追加）
        mid = entry.get("mother_id")
        if not mid:
            return 0
        st = self.get_review_state(mid) or {}
        logs = st.get("logs") or []
        entry = {**entry, "id": len(logs) + 1}
        logs.append(entry)
        st["logs"] = logs
        with engine.begin() as c:
            c.execute(text("""
                INSERT INTO sishu_mq_review_state (mq_id, doc) VALUES (:i, CAST(:d AS JSONB))
                ON CONFLICT (mq_id) DO UPDATE SET doc=CAST(:d AS JSONB)"""),
                {"i": mid, "d": json.dumps(st, ensure_ascii=False)})
        return entry["id"]

    def list_review_log(self, mother_id: str | None = None) -> list[dict]:
        all_logs: list[dict] = []
        for mid, st in self._rs_all().items():
            for lg in (st.get("logs") or []):
                all_logs.append({**lg, "mother_id": lg.get("mother_id", mid)})
        if mother_id:
            all_logs = [x for x in all_logs if x.get("mother_id") == mother_id]
        all_logs.sort(key=lambda x: x.get("ts") or x.get("reviewed_at") or 0, reverse=True)
        return all_logs

    def get_review_state(self, mid: str):
        with engine.connect() as c:
            row = c.execute(text("SELECT doc FROM sishu_mq_review_state WHERE mq_id=:i"),
                            {"i": mid}).fetchone()
        return AttrObj(row[0]) if row else None

    def upsert_review_state(self, mid: str, is_correct: bool) -> dict:
        st = dict((self.get_review_state(mid) or {}).to_dict()) if self.get_review_state(mid) else {}
        st["is_correct"] = is_correct
        st["last_reviewed_at"] = _now()
        st["review_count"] = (st.get("review_count") or 0) + 1
        with engine.begin() as c:
            c.execute(text("""
                INSERT INTO sishu_mq_review_state (mq_id, doc) VALUES (:i, CAST(:d AS JSONB))
                ON CONFLICT (mq_id) DO UPDATE SET doc=CAST(:d AS JSONB)"""),
                {"i": mid, "d": json.dumps(st, ensure_ascii=False)})
        return st

    def upsert_review_fsrs(self, mid: str, rating: int) -> dict:
        # FSRS 调度语义=vendor fsrs.py 批6-后续接入；本批先落 rating/时间戳（状态推进账）
        st = dict((self.get_review_state(mid) or {}).to_dict()) if self.get_review_state(mid) else {}
        st["fsrs_rating"] = rating
        st["fsrs_last_review"] = _now()
        with engine.begin() as c:
            c.execute(text("""
                INSERT INTO sishu_mq_review_state (mq_id, doc) VALUES (:i, CAST(:d AS JSONB))
                ON CONFLICT (mq_id) DO UPDATE SET doc=CAST(:d AS JSONB)"""),
                {"i": mid, "d": json.dumps(st, ensure_ascii=False)})
        return st

    def get_retention(self, mid: str) -> float:
        st = self.get_review_state(mid)
        return float((st.retention if st else None) or 0.0)

    def list_due(self, max_items: int = 20):
        due = [(m, self.get_review_state(m.id)) for m in self.list_all_mothers()]
        items = [(m, s) for m, s in due if (s and (s.due or 0) <= _now()) or s is None]
        items.sort(key=lambda x: (x[1].due if x[1] else 0))
        return [m for m, _ in items[:max_items]]

    def due_count(self) -> int:
        return len(self.list_due(max_items=10_000))

    # ---------- 标签 ----------
    def _tags_all(self) -> list[AttrObj]:
        with engine.connect() as c:
            rows = c.execute(text("SELECT name, color, doc FROM sishu_mq_tags ORDER BY name")).fetchall()
        return [AttrObj({"name": r[0], "color": r[1], **(r[2] or {})}) for r in rows]

    def list_all_tags(self) -> list[dict]:
        return [t.model_dump() for t in self._tags_all()]

    def create_tag(self, name: str, color: str | None = None) -> dict:
        tag = {"name": name, "color": color}
        with engine.begin() as c:
            c.execute(text("""
                INSERT INTO sishu_mq_tags (name, color, doc) VALUES (:n, :c, CAST(:d AS JSONB))
                ON CONFLICT (name) DO UPDATE SET color=:c"""),
                {"n": name, "c": color, "d": json.dumps(tag, ensure_ascii=False)})
        return tag

    def delete_tag(self, name: str) -> bool:
        with engine.begin() as c:
            n = c.execute(text("DELETE FROM sishu_mq_tags WHERE name=:n"), {"n": name}).rowcount
        return n > 0

    # ---------- attempts ----------
    def list_attempts(self, mother_id: str | None = None, limit: int = 100) -> list[dict]:
        with engine.connect() as c:
            rows = c.execute(text(
                "SELECT doc FROM sishu_mq_attempts ORDER BY (doc->>'create_time') DESC NULLS LAST LIMIT :l"),
                {"l": limit}).fetchall()
        items = [AttrObj(r[0]) for r in rows]
        if mother_id:
            items = [a for a in items if a.mother_id == mother_id]
        return items

    def create_attempt(self, a: AttrObj):
        d = a.model_dump()
        with engine.begin() as c:
            c.execute(text("""
                INSERT INTO sishu_mq_attempts (attempt_id, mother_id, doc)
                VALUES (:i, :m, CAST(:d AS JSONB))
                ON CONFLICT (attempt_id) DO UPDATE SET doc=CAST(:d AS JSONB)"""),
                {"i": d.get("id") or _gen_id("att"), "m": d.get("mother_id"),
                 "d": json.dumps(d, ensure_ascii=False)})
        return a

    def delete_attempt(self, aid: str) -> bool:
        with engine.begin() as c:
            n = c.execute(text("DELETE FROM sishu_mq_attempts WHERE attempt_id=:i OR doc->>'id'=:i"),
                          {"i": aid}).rowcount
        return n > 0

    # ---------- assets ----------
    def add_asset(self, mid: str, asset: dict):
        m = self.get_mother(mid)
        if not m:
            return None
        assets = list(m.assets or [])
        entry = {"id": _gen_id("att"), **asset, "create_time": _now()}
        assets.append(entry)
        m.assets = assets
        self._save_mq_item(m)
        return entry

    def remove_asset(self, mid: str, asset_url: str) -> bool:
        m = self.get_mother(mid)
        if not m:
            return False
        assets = list(m.assets or [])
        kept = [a for a in assets if (a.get("url") or a.get("source_image_url")) != asset_url]
        if len(kept) == len(assets):
            return False
        m.assets = kept
        self._save_mq_item(m)
        return True
