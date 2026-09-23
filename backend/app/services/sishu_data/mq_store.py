# -*- coding: utf-8 -*-
"""v4批6 6.B：PG 版 MotherQuestionStore——vendor deeptutor/learning/mother_question.py
MotherQuestionStore 消费方法面 1:1（行为同构，语义漂移清单已逐项对齐）。
数据=sishu_mq_docs/sishu_question_variants/sishu_mq_review_state/sishu_mq_tags/
sishu_mq_attempts/sishu_mq_review_log（全字段 JSONB doc+typed 热列；user_id=?u= 隔离列）。
用户作用域=vendor 同一上下文变量（app.services.sishu.compat.context）——路由
user_context(h5_user(u)) 切 scope.user_id（local-admin/h5_<slug>），store 零参数感知。
文档对象=vendor pydantic 模型（mq_models 逐字复制）——router 处理器零改语义移植的载体。
FSRS/SpacedRepetitionScheduler=移植件（app.services.sishu.learning.{fsrs,scheduler}）。"""
import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text

from app.services.sishu.compat.context import get_current_user_or_none
from app.services.sishu.learning.fsrs import new_card as _fsrs_new_card
from app.services.sishu.learning.fsrs import review as _fsrs_review
from app.services.sishu.learning.fsrs import retrievability as _fsrs_retrievability
from app.services.sishu.learning.mq_models import Attempt, MotherQuestion, QuestionVariant
from app.services.sishu_data.pg import engine

logger = logging.getLogger(__name__)

# Module-level re-entrant lock so CAS semantics hold across all store instances
# (vendor 同款——变式删除+母题计数回扣是两文件一个逻辑事务)。
_cas_lock = threading.RLock()


def _now() -> float:
    import time
    return time.time()


def hamming_distance(a: int, b: int) -> int:
    """simhash 汉明距（vendor simhash_util 同式：XOR popcount，纯函数）。"""
    return bin(a ^ b).count("1")


def _scope_user() -> str:
    """当前 ?u= 数据作用域（vendor user_context 切目录的 PG 同义——scope.user_id）。"""
    cu = get_current_user_or_none()
    if cu is None:
        return "local-admin"
    return getattr(getattr(cu, "scope", None), "user_id", "") or "local-admin"


class MotherQuestionStorePG:
    """PG 单轨 store——vendor MotherQuestionStore 方法面 1:1。"""

    # ---------- 装载/落盘（JSONB doc ↔ pydantic 模型） ----------
    def _load_mq(self) -> list[MotherQuestion]:
        with engine.connect() as c:
            rows = c.execute(text(
                "SELECT doc FROM sishu_mq_docs WHERE user_id=:u"),
                {"u": _scope_user()}).fetchall()
        return [MotherQuestion.model_validate(r[0]) for r in rows]

    def _save_mq_item(self, m: MotherQuestion) -> None:
        d = m.model_dump(mode="json")
        with engine.begin() as c:
            c.execute(text("""
                INSERT INTO sishu_mq_docs (mq_id, user_id, doc, status, subject, grade,
                                           knowledge_point_id, mastery_status, simhash, update_time)
                VALUES (:i, :u, CAST(:d AS JSONB), :s, :sj, :g, :kp, :ms, :sh, :t)
                ON CONFLICT (mq_id) DO UPDATE SET doc=CAST(:d AS JSONB), status=:s, subject=:sj,
                  grade=:g, knowledge_point_id=:kp, mastery_status=:ms, simhash=:sh, update_time=:t"""),
                {"i": d.get("id"), "u": _scope_user(),
                 "d": json.dumps(d, ensure_ascii=False),
                 "s": d.get("status") or "active", "sj": d.get("subject"), "g": d.get("grade"),
                 "kp": d.get("knowledge_point_id"), "ms": d.get("mastery_status"),
                 "sh": d.get("simhash"), "t": int(d.get("update_time") or 0)})

    def _del_mq(self, mq_id: str) -> None:
        with engine.begin() as c:
            c.execute(text("DELETE FROM sishu_mq_docs WHERE mq_id=:i AND user_id=:u"),
                      {"i": mq_id, "u": _scope_user()})

    # ---------- 母题 CRUD/列表 ----------
    def list_mothers(self, *, subject=None, grade=None, category=None, knowledge_point_id=None,
                     textbook_id=None, chapter_id=None, tag=None, difficulty_min=None,
                     difficulty_max=None, keyword=None, status="active", start_date=None,
                     end_date=None, sort_by="create_time", sort_order="desc",
                     page=1, page_size=20):
        items = self._load_mq()
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
        sort_field = {"create_time": "create_time", "difficulty": "difficulty",
                      "title": "title"}.get(sort_by, "create_time")
        out.sort(key=lambda x: getattr(x, sort_field, x.create_time),
                 reverse=(sort_order != "asc"))
        total = len(out)
        start = (page - 1) * page_size
        return out[start:start + page_size], total

    def list_all_mothers(self, status: str = "active") -> list[MotherQuestion]:
        """All mothers (no pagination) - for analysis aggregation."""
        items = [m for m in self._load_mq() if m.status == status]
        items.sort(key=lambda x: x.create_time, reverse=True)
        return items

    def find_duplicates(self, simhash_val, threshold: int = 4, exclude_id: str | None = None):
        """Return [{id,title,distance,grade,category}] within hamming threshold."""
        if simhash_val is None:
            return []
        out: list[dict] = []
        for m in self._load_mq():
            if m.id == exclude_id or m.simhash is None:
                continue
            d = hamming_distance(int(simhash_val), int(m.simhash))
            if d <= threshold:
                out.append({
                    "id": m.id, "title": m.title, "distance": d,
                    "grade": m.grade, "category": m.category,
                })
        out.sort(key=lambda x: x["distance"])
        return out[:10]

    def find_similar(self, mid: str, top_k: int = 5, threshold: int = 10):
        """Find similar questions by simhash, returning rich detail."""
        m = self.get_mother(mid)
        if not m or m.simhash is None:
            return []
        out: list[dict] = []
        for other in self._load_mq():
            if other.id == mid or other.simhash is None:
                continue
            if other.status == "deleted":
                continue
            d = hamming_distance(int(m.simhash), int(other.simhash))
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
        with engine.connect() as c:
            row = c.execute(text(
                "SELECT doc FROM sishu_mq_docs WHERE mq_id=:i AND user_id=:u"),
                {"i": mid, "u": _scope_user()}).fetchone()
        return MotherQuestion.model_validate(row[0]) if row else None

    def create_mother(self, m: MotherQuestion) -> MotherQuestion:
        if not m.created_at:
            m.created_at = datetime.now(timezone.utc).isoformat()
        with _cas_lock:
            self._save_mq_item(m)
        return m

    def update_mother(self, mid: str, patch: dict[str, Any]) -> MotherQuestion | None:
        with _cas_lock:
            m = self.get_mother(mid)
            if not m:
                return None
            for k, v in patch.items():
                if hasattr(m, k) and k not in ("id", "create_time"):
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
            else:
                m.status = "deleted"
                m.deleted_time = _now()
                m.update_time = _now()
                self._save_mq_item(m)
            return True

    def restore_mother(self, mid: str) -> bool:
        """从回收站恢复（status deleted -> active）."""
        with _cas_lock:
            m = self.get_mother(mid)
            if m and m.status == "deleted":
                m.status = "active"
                m.deleted_time = None
                m.update_time = _now()
                self._save_mq_item(m)
                return True
        return False

    def list_trash(self, page: int = 1, page_size: int = 20):
        """回收站列表（仅 status=deleted）."""
        items = [m for m in self._load_mq() if m.status == "deleted"]
        items.sort(key=lambda x: x.deleted_time or x.update_time, reverse=True)
        total = len(items)
        start = (page - 1) * page_size
        return items[start:start + page_size], total

    def _bump_counter(self, mid: str, field: str, delta: int) -> None:
        """Adjust variant_count / video_count on the mother (best-effort)."""
        with _cas_lock:
            m = self.get_mother(mid)
            if m:
                cur = getattr(m, field, 0) or 0
                setattr(m, field, max(0, cur + delta))
                m.update_time = _now()
                self._save_mq_item(m)

    # ---------- review states (SpacedRepetitionScheduler / FSRS) ----------

    def _load_rs(self) -> dict[str, dict]:
        with engine.connect() as c:
            rows = c.execute(text(
                "SELECT mq_id, doc FROM sishu_mq_review_state WHERE user_id=:u"),
                {"u": _scope_user()}).fetchall()
        return {r[0]: r[1] for r in rows}

    def _save_rs_one(self, mid: str, card: dict) -> None:
        with engine.begin() as c:
            c.execute(text("""
                INSERT INTO sishu_mq_review_state (mq_id, user_id, doc)
                VALUES (:i, :u, CAST(:d AS JSONB))
                ON CONFLICT (mq_id) DO UPDATE SET doc=CAST(:d AS JSONB)"""),
                {"i": mid, "u": _scope_user(),
                 "d": json.dumps(card, ensure_ascii=False)})

    def append_review_log(self, entry: dict[str, Any]) -> int:
        """Append one review event atomically and return the new total."""
        with _cas_lock:
            with engine.begin() as c:
                c.execute(text(
                    "INSERT INTO sishu_mq_review_log (user_id, doc) VALUES (:u, CAST(:d AS JSONB))"),
                    {"u": _scope_user(), "d": json.dumps(entry, ensure_ascii=False)})
                total = c.execute(text(
                    "SELECT count(*) FROM sishu_mq_review_log WHERE user_id=:u"),
                    {"u": _scope_user()}).scalar()
        return int(total or 0)

    def list_review_log(self, mother_id: str | None = None) -> list[dict]:
        """Read review events, tolerating a missing or damaged legacy file."""
        with engine.connect() as c:
            rows = c.execute(text(
                "SELECT doc FROM sishu_mq_review_log WHERE user_id=:u ORDER BY seq"),
                {"u": _scope_user()}).fetchall()
        log = [r[0] for r in rows]
        if mother_id is not None:
            return [item for item in log if item.get("mother_id") == mother_id]
        return log

    def get_review_state(self, mid: str) -> dict | None:
        return self._load_rs().get(mid)

    def upsert_review_state(self, mid: str, is_correct: bool) -> dict:
        """Update review state via DeepTutor SpacedRepetitionScheduler (legacy binary)."""
        from app.services.sishu.learning.models import KnowledgeType, RepetitionState
        from app.services.sishu.learning.scheduler import SpacedRepetitionScheduler

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
            self._save_rs_one(mid, rs[mid])

            # 同步 mastery_status: 连对足够次数 -> mastered, 否则 reviewing
            m = self.get_mother(mid)
            if m:
                if new_state.consecutive_correct >= 2 and new_state.interval_index >= 2:
                    m.mastery_status = "mastered"
                else:
                    m.mastery_status = "reviewing"
                m.update_time = _now()
                self._save_mq_item(m)
            self._refresh_learner_profile()
            self._emit_review_event(mid, 3 if is_correct else 1)
        return rs[mid]

    def upsert_review_fsrs(self, mid: str, rating: int) -> dict:
        """Update review state via FSRS-5 (rating 1=Again 2=Hard 3=Good 4=Easy)."""
        with _cas_lock:
            rs = self._load_rs()
            cur = rs.get(mid)
            if cur and cur.get("stability") is not None:
                card = _fsrs_review(cur, rating)
            else:
                card = _fsrs_new_card(rating)
            rs[mid] = card
            self._save_rs_one(mid, card)

            # 同步 mastery_status: reps>=3 且 stability>=7 -> mastered, else reviewing
            m = self.get_mother(mid)
            if m:
                if card["reps"] >= 3 and card["stability"] >= 7:
                    m.mastery_status = "mastered"
                elif card["reps"] >= 1:
                    m.mastery_status = "reviewing"
                else:
                    m.mastery_status = "not_mastered"
                m.update_time = _now()
                self._save_mq_item(m)
            self._refresh_learner_profile()
            self._emit_review_event(mid, rating)
        return rs[mid]

    def _refresh_learner_profile(self) -> None:
        """Best-effort refresh of the deterministic L2/L3 learning memory docs
        so review outcomes immediately show up in the learner profile."""
        try:
            from app.services.sishu.learning.learner_profile import (
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
            from app.services.sishu.learning.learner_profile import emit_learning_event

            mother = self.get_mother(mid)
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
        st = self._load_rs().get(mid)
        if not st or st.get("stability") is None:
            return 0.0
        return _fsrs_retrievability(st) * 100

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

    def list_all_tags(self) -> list[dict]:
        """收集所有母题用过的标签 + tags 表中预定义的标签（去重）."""
        seen: dict[str, dict] = {}
        # 1. 预定义（tags 表）
        with engine.connect() as c:
            rows = c.execute(text(
                "SELECT name, color, doc FROM sishu_mq_tags WHERE user_id=:u ORDER BY name"),
                {"u": _scope_user()}).fetchall()
        for name, color, _doc in rows:
            seen[name] = {"id": name, "name": name, "color": color}
        # 2. 从母题收集
        for m in self._load_mq():
            for name in (m.tags or []):
                if name and name not in seen:
                    seen[name] = {"id": name, "name": name, "color": None}
        return list(seen.values())

    def create_tag(self, name: str, color: str | None = None) -> dict:
        """创建标签实体（存 tags 表）。R5批⑧（清单安全）：name 是全局 PK——原
        ON CONFLICT DO UPDATE 只改 color、user_id 仍属先建者（跨用户状态污染：他人
        同名建标签会改我的行且自己看不到）。现冲突时校验归属：他人占用 → ValueError，
        本人同名 → 原地更新 color/doc。"""
        with _cas_lock:
            with engine.begin() as c:
                u = _scope_user()
                row = c.execute(text("SELECT user_id FROM sishu_mq_tags WHERE name=:n"),
                                {"n": name}).first()
                if row is not None:
                    if row[0] != u:
                        raise ValueError(f"标签名已存在且归属其他用户: {name}")
                    c.execute(text(
                        "UPDATE sishu_mq_tags SET color=:c, doc=CAST(:d AS JSONB) "
                        "WHERE name=:n AND user_id=:u"),
                        {"c": color, "n": name, "u": u,
                         "d": json.dumps({"id": name, "name": name, "color": color}, ensure_ascii=False)})
                else:
                    c.execute(text(
                        "INSERT INTO sishu_mq_tags (name, user_id, color, doc) "
                        "VALUES (:n, :u, :c, CAST(:d AS JSONB))"),
                        {"n": name, "u": u, "c": color,
                         "d": json.dumps({"id": name, "name": name, "color": color}, ensure_ascii=False)})
            return {"id": name, "name": name, "color": color}

    def delete_tag(self, name: str) -> bool:
        """删除标签实体 + 从所有母题移除该标签."""
        with _cas_lock:
            with engine.begin() as c:
                c.execute(text("DELETE FROM sishu_mq_tags WHERE name=:n AND user_id=:u"),
                          {"n": name, "u": _scope_user()})
            # 从母题移除
            items = self._load_mq()
            changed = False
            for m in items:
                if name in (m.tags or []):
                    m.tags = [t for t in (m.tags or []) if t != name]
                    changed = True
            if changed:
                self._save_mq_all(items)
            return True

    # ---------- attempts (答题记录) ----------

    def list_attempts(self, mother_id: str | None = None, limit: int = 100) -> list[dict]:
        with engine.connect() as c:
            rows = c.execute(text(
                "SELECT doc FROM sishu_mq_attempts WHERE user_id=:u"),
                {"u": _scope_user()}).fetchall()
        items = [r[0] for r in rows]
        if mother_id:
            items = [a for a in items if a.get("mother_id") == mother_id]
        items.sort(key=lambda x: x.get("create_time", 0), reverse=True)
        return items[:limit]

    def create_attempt(self, a: Attempt) -> Attempt:
        d = a.model_dump(mode="json")
        with _cas_lock:
            with engine.begin() as c:
                c.execute(text("""
                    INSERT INTO sishu_mq_attempts (attempt_id, user_id, mother_id, doc)
                    VALUES (:i, :u, :m, CAST(:d AS JSONB))
                    ON CONFLICT (attempt_id) DO UPDATE SET doc=CAST(:d AS JSONB)"""),
                    {"i": d.get("id"), "u": _scope_user(), "m": d.get("mother_id"),
                     "d": json.dumps(d, ensure_ascii=False)})
        return a

    def delete_attempt(self, aid: str) -> bool:
        with _cas_lock:
            with engine.begin() as c:
                n = c.execute(text(
                    "DELETE FROM sishu_mq_attempts WHERE attempt_id=:i AND user_id=:u"),
                    {"i": aid, "u": _scope_user()}).rowcount
        return n > 0

    # ---------- assets (多图资产) ----------

    def add_asset(self, mid: str, asset: dict) -> dict | None:
        with _cas_lock:
            m = self.get_mother(mid)
            if m:
                m.assets = (m.assets or []) + [asset]
                m.update_time = _now()
                self._save_mq_item(m)
                return asset
        return None

    def remove_asset(self, mid: str, asset_url: str) -> bool:
        with _cas_lock:
            m = self.get_mother(mid)
            if m:
                before = len(m.assets or [])
                m.assets = [a for a in (m.assets or []) if a.get("url") != asset_url]
                if len(m.assets) < before:
                    m.update_time = _now()
                    self._save_mq_item(m)
                    return True
                return False
        return False

    # ---------- variants ----------

    def _load_vq(self) -> list[QuestionVariant]:
        with engine.connect() as c:
            rows = c.execute(text(
                "SELECT doc FROM sishu_question_variants WHERE user_id=:u"),
                {"u": _scope_user()}).fetchall()
        return [QuestionVariant.model_validate(r[0]) for r in rows]

    def _save_vq_item(self, v: QuestionVariant) -> None:
        d = v.model_dump(mode="json")
        with engine.begin() as c:
            c.execute(text("""
                INSERT INTO sishu_question_variants (vq_id, user_id, mother_id, doc, status, update_time)
                VALUES (:i, :u, :m, CAST(:d AS JSONB), :s, :t)
                ON CONFLICT (vq_id) DO UPDATE SET doc=CAST(:d AS JSONB), status=:s, update_time=:t"""),
                {"i": d.get("id"), "u": _scope_user(), "m": d.get("mother_id"),
                 "d": json.dumps(d, ensure_ascii=False),
                 "s": d.get("status") or "active", "t": int(d.get("update_time") or 0)})

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
            self._save_vq_item(v)
        self._bump_counter(v.mother_id, "variant_count", 1)
        return v

    def update_variant(self, vid: str, patch: dict[str, Any]) -> QuestionVariant | None:
        with _cas_lock:
            for v in self._load_vq():
                if v.id == vid:
                    for k, val in patch.items():
                        if hasattr(v, k) and k not in ("id", "create_time", "mother_id"):
                            setattr(v, k, val)
                    v.update_time = _now()
                    self._save_vq_item(v)
                    return v
        return None

    def delete_variant(self, vid: str, hard: bool = False) -> bool:
        with _cas_lock:
            for v in self._load_vq():
                if v.id == vid:
                    mid = v.mother_id
                    was_active = v.status == "active"
                    if hard:
                        with engine.begin() as c:
                            c.execute(text(
                                "DELETE FROM sishu_question_variants WHERE vq_id=:i AND user_id=:u"),
                                {"i": vid, "u": _scope_user()})
                    else:
                        v.status = "deleted"
                        v.update_time = _now()
                        self._save_vq_item(v)
                    if was_active:
                        self._bump_counter(mid, "variant_count", -1)
                    return True
        return False

    # ---------- 内部：批量落盘（delete_tag 用——逐件 upsert 保 user_id 列面一致） ----------

    def _save_mq_all(self, items: list[MotherQuestion]) -> None:
        for m in items:
            self._save_mq_item(m)


__all__ = [
    "MotherQuestionStorePG",
    "hamming_distance",
    "_now",
]
