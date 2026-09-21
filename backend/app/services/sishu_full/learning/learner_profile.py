"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.sishu_full.services.path_service import get_path_service

logger = logging.getLogger(__name__)

WEAK_MASTERY = 0.6  # mastery below this -> weak point
MASTERED_MASTERY = 0.9  # mastery at/above this -> mastered (matches FSRS TARGET_RETENTION)


class KpMastery(BaseModel):
    """One knowledge point's learning state, aggregated across sources."""

    model_config = ConfigDict(extra="ignore")

    kp_id: str
    kp_name: str = ""
    subject: str = "math"
    mastery: float = 0.0  # 0..1 (FSRS retention or direct mastery)
    attempts: int = 0
    correct_rate: float = 0.0
    last_practiced_at: float | None = None
    next_review_at: float | None = None
    status: Literal["new", "learning", "weak", "mastered"] = "new"
    error_types: list[str] = Field(default_factory=list)


class LearnerProfile(BaseModel):
    """Aggregated learning aptitude for one user."""

    model_config = ConfigDict(extra="ignore")

    user_id: str = "default"
    kp_mastery: dict[str, KpMastery] = Field(default_factory=dict)
    weak_points: list[str] = Field(default_factory=list)
    strong_points: list[str] = Field(default_factory=list)
    due_reviews: list[dict] = Field(default_factory=list)
    recent_activity: list[dict] = Field(default_factory=list)
    streak_days: int = 0
    total_study_minutes: float = 0.0
    badges: list[dict] = Field(default_factory=list)  # 徽章（design §5.3 游戏化）
    updated_at: float = Field(default_factory=time.time)

    @property
    def by_subject(self) -> dict[str, list[KpMastery]]:
        out: dict[str, list[KpMastery]] = {}
        for kp in self.kp_mastery.values():
            out.setdefault(kp.subject, []).append(kp)
        return out

    def to_markdown(self) -> str:
        """Deterministic L3 learning_profile.md rendering (design §3.3)."""
        lines = [
            "# 学情画像 Learning Profile",
            "",
            f"> 最近更新：{time.strftime('%Y-%m-%d %H:%M', time.localtime(self.updated_at))}",
            "",
        ]
        if not self.kp_mastery:
            lines.append("（暂无学习数据 — 完成一次答题/复习后会在这里生成画像）")
            return "\n".join(lines)

        lines.append("## 掌握度概览")
        lines.append("")
        for subject, kps in sorted(self.by_subject.items()):
            subj_label = {"math": "数学", "chinese": "语文", "english": "英语"}.get(subject, subject)
            lines.append(f"### {subj_label}（{len(kps)} 个知识点）")
            for kp in sorted(kps, key=lambda k: -k.mastery):
                bar = "█" * int(round(kp.mastery * 10))
                lines.append(
                    f"- {kp.kp_name}：{kp.mastery:.0%} 掌握（{kp.status}）"
                    f"｜{kp.attempts}次练习，正确率{kp.correct_rate:.0%} {bar}"
                )
            lines.append("")

        if self.weak_points:
            lines.append("## 薄弱点（需重点练习）")
            for kpid in self.weak_points:
                kp = self.kp_mastery.get(kpid)
                if kp:
                    et = "、".join(kp.error_types) if kp.error_types else "未归类"
                    lines.append(f"- {kp.kp_name}（{et}）")
            lines.append("")

        if self.due_reviews:
            lines.append("## 今日/近期应复习")
            for r in self.due_reviews[:20]:
                lines.append(
                    f"- {r.get('kp_name', r.get('kp_id', ''))}（{r.get('reason', '到期复习')}）"
                )
            lines.append("")

        lines.append(f"## 学习节奏\n- 连续学习：{self.streak_days} 天")
        lines.append(f"- 累计学习时长：{self.total_study_minutes:.0f} 分钟")
        if self.badges:
            badge_names = " ".join(f"{b['icon']}{b['name']}" for b in self.badges[:8])
            lines.append(f"- 徽章：{badge_names}")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Aggregation helpers                                                          #
# --------------------------------------------------------------------------- #


def _read_json(path: Path) -> dict | None:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        logger.warning("learner_profile: failed to read %s", path, exc_info=True)
    return None


def _workspace() -> Path:
    return get_path_service().get_workspace_dir()


def _learning_plans_dir() -> Path:
    return _workspace() / "learning"


def _mother_dir() -> Path:
    return _workspace() / "mother_questions"


def _load_learning_plans() -> list[dict]:
    """All mastery_path plan files under workspace/learning."""
    plans = []
    d = _learning_plans_dir()
    if not d.exists():
        return plans
    for f in sorted(d.glob("*.json")):
        data = _read_json(f)
        if isinstance(data, dict):
            plans.append(data)
    return plans


def _load_mother_review_states() -> dict[str, dict]:
    """review_states.json: mid -> fsrs card state."""
    data = _read_json(_mother_dir() / "review_states.json")
    return data if isinstance(data, dict) else {}


def _load_mothers() -> list[dict]:
    """All mother_questions from index.json (mastery_status per mother)."""
    data = _read_json(_mother_dir() / "index.json")
    if isinstance(data, list):
        return [m for m in data if isinstance(m, dict)]
    return []


def _status_from_mastery(m: float) -> str:
    if m <= 0:
        return "new"
    if m >= MASTERED_MASTERY:
        return "mastered"
    if m < WEAK_MASTERY:
        return "weak"
    return "learning"


# --------------------------------------------------------------------------- #
# 学习节奏：streak / 学习时长 / 徽章（design §5.3 游戏化）                    #
# --------------------------------------------------------------------------- #


def _load_learning_events(days: int | None = None) -> list[dict]:
    """Read L1 learning trace events, optionally only the last *days* days.

    Each event is ``{kind, payload, created_at/ts, ...}`` (already parsed).
    """
    try:
        from app.services.sishu_full.services.memory import paths
        from datetime import date, timedelta

        trace_root = paths.trace_dir("learning")
        if not trace_root.exists():
            return []
        cutoff = None
        if days is not None:
            cutoff = (date.today() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
        out: list[dict] = []
        for f in sorted(trace_root.glob("*.jsonl")):
            if cutoff is not None and f.stem < cutoff:
                continue
            for line in f.open(encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except Exception:
                    continue
                if ev.get("surface") == "learning" or ev.get("kind"):
                    out.append(ev)
        return out
    except Exception:
        return []


def compute_weekly_delta(profile: LearnerProfile | None = None) -> dict:
    """本周（最近 7 天）学情增量，供周报「本周 vs 上周」使用（audit P1-4）。

    数据源：L1 learning trace（quiz_attempt / review 事件）。
    返回值：
      {
        "new_kps": int,            # 本周首次出现的知识点数
        "attempts": int,           # 本周答题次数
        "correct_rate": float,     # 本周答题正确率 0.0~1.0
        "mastered_this_week": int, # 本周首次达到 mastered 的知识点数
        "review_count": int,       # 本周复习（review 事件）次数
        "active_days": int,        # 本周有学习活动的天数
      }
    """
    events = _load_learning_events(days=7)
    if not events:
        return {
            "new_kps": 0,
            "attempts": 0,
            "correct_rate": 0.0,
            "mastered_this_week": 0,
            "review_count": 0,
            "active_days": 0,
        }
    seen_kps: set[str] = set()
    mastered_this_week: set[str] = set()
    attempts = 0
    correct = 0
    review_count = 0
    active_days: set[str] = set()
    for ev in events:
        payload = ev.get("payload") or {}
        ts = ev.get("created_at") or ev.get("ts") or 0
        if ts:
            from datetime import datetime

            try:
                active_days.add(datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d"))
            except Exception:
                pass
        kind = ev.get("kind")
        if kind == "quiz_attempt":
            kp_id = str(payload.get("kp_id") or "")
            attempts += 1
            if payload.get("is_correct"):
                correct += 1
            if kp_id:
                seen_kps.add(kp_id)
            # 首次达到 mastered（mastery_after >= 0.9）
            mastery_after = payload.get("mastery_after")
            if kp_id and mastery_after is not None and float(mastery_after) >= 0.9:
                mastered_this_week.add(kp_id)
        elif kind == "review":
            review_count += 1
    return {
        "new_kps": len(seen_kps),
        "attempts": attempts,
        "correct_rate": round(correct / attempts, 3) if attempts else 0.0,
        "mastered_this_week": len(mastered_this_week),
        "review_count": review_count,
        "active_days": len(active_days),
    }


def _learning_day_dates() -> list[str]:
    """Dates (YYYY-MM-DD) on which at least one learning event happened.

    Sources: L1 trace surface=learning (quiz_attempt / review events).
    """
    try:
        from app.services.sishu_full.services.memory import paths
        from datetime import datetime

        out: list[str] = []
        trace_root = paths.trace_dir("learning")
        if not trace_root.exists():
            return out
        for f in sorted(trace_root.glob("*.jsonl")):
            try:
                day = f.stem
                # 该天文件里至少有一条事件才算学了一天
                has_event = False
                for line in f.open(encoding="utf-8"):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                    except Exception:
                        continue
                    if ev.get("surface") == "learning" or ev.get("kind"):
                        has_event = True
                        break
                if has_event:
                    out.append(day)
            except Exception:
                continue
        return out
    except Exception:
        return []


def compute_streak_days() -> int:
    """连续学习天数：从今天往回数连续有学习事件的天数。"""
    from datetime import date, timedelta

    days = set(_learning_day_dates())
    if not days:
        return 0
    today = date.today()
    # 今天没学但昨天学了，streak 仍算（截至最近一天）
    cursor = today
    streak = 0
    for _ in range(400):
        if cursor.isoformat() in days:
            streak += 1
            cursor -= timedelta(days=1)
        else:
            # 允许"今天还没学但昨天有"——今天学习日刚开始不算断
            if streak == 0 and (today - timedelta(days=1)).isoformat() in days:
                cursor = today - timedelta(days=1)
                continue
            break
    return streak


def compute_study_minutes() -> float:
    """累计学习时长（分钟）。没有精确计时，按事件次数估算：每次答题/复习约 3 分钟。"""
    from datetime import datetime

    total = 0
    try:
        from app.services.sishu_full.services.memory import paths

        trace_root = paths.trace_dir("learning")
        if trace_root.exists():
            for f in trace_root.glob("*.jsonl"):
                for line in f.open(encoding="utf-8"):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        ev = json.loads(line)
                    except Exception:
                        continue
                    if ev.get("kind") in ("quiz_attempt", "review"):
                        total += 3
    except Exception:
        pass
    return float(total)


def compute_badges(profile: LearnerProfile) -> list[dict]:
    """基于学情画像计算徽章（design §5.3 游戏化）。"""
    badges: list[dict] = []
    total = len(profile.kp_mastery)
    mastered = len(profile.strong_points)
    weak = len(profile.weak_points)
    due = len(profile.due_reviews)
    streak = profile.streak_days

    if total >= 1:
        badges.append({"id": "first_learn", "name": "初窥门径", "desc": "建立第一个学情画像", "icon": "🌱"})
    if mastered >= 1:
        badges.append({"id": "first_master", "name": "旗开得胜", "desc": "掌握第 1 个知识点", "icon": "🏅"})
    if mastered >= 5:
        badges.append({"id": "master_5", "name": "小有所成", "desc": "掌握 5 个知识点", "icon": "🎓"})
    if weak == 0 and total >= 3:
        badges.append({"id": "no_weak", "name": "扫清障碍", "desc": "当前没有薄弱点", "icon": "🧹"})
    if due == 0 and total >= 3:
        badges.append({"id": "all_reviewed", "name": "今日事今日毕", "desc": "没有积压的到期复习", "icon": "✅"})
    if streak >= 3:
        badges.append({"id": "streak_3", "name": "三日之约", "desc": "连续学习 3 天", "icon": "🔥"})
    if streak >= 7:
        badges.append({"id": "streak_7", "name": "持之以恒", "desc": "连续学习 7 天", "icon": "⭐"})
    if streak >= 30:
        badges.append({"id": "streak_30", "name": "水滴石穿", "desc": "连续学习 30 天", "icon": "🏆"})
    return badges


def _fsrs_retention(card: dict | None) -> float:
    """FSRS-5 retention approximation from the card state (see fsrs.py).

    Supports both the FSRS-5 card shape (``stability``/``due``/``last_review``)
    and the legacy fixed-interval shape (``interval_index``/``next_review_at``).
    """
    if not card:
        return 0.0
    try:
        # FSRS-5 shape: explicit retention if present, else decay estimate.
        ret = float(card.get("retention") or 0.0)
        if ret > 0:
            return max(0.0, min(1.0, ret))
        due = card.get("due")
        last = card.get("last_review")
        if due and last:
            elapsed = (float(due) - float(last)) / 86400.0
            return max(0.0, min(1.0, 0.9 ** elapsed))
    except (TypeError, ValueError):
        pass
    # Legacy fixed-interval shape: mastery rises with consecutive correct runs.
    idx = card.get("interval_index")
    if isinstance(idx, (int, float)):
        ok = int(card.get("consecutive_correct") or 0)
        return max(0.0, min(1.0, 0.4 + 0.15 * ok))
    return 0.0


def _plan_mastery(plan: dict, kp_id: str) -> float:
    try:
        return float(plan.get("mastery_levels", {}).get(kp_id, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _plan_attempts_for(plan: dict, kp_id: str) -> list[dict]:
    return [
        a
        for a in plan.get("quiz_attempts") or []
        if isinstance(a, dict) and a.get("knowledge_point_id") == kp_id
    ]


def build_learner_profile(user_id: str = "default") -> LearnerProfile:
    """Aggregate mastery_path plans + mother_questions into one profile."""
    profile = LearnerProfile(user_id=user_id)
    kp_meta: dict[str, dict] = {}  # kp_id -> {name, subject} from plans

    # --- 1) mastery_path plans -------------------------------------------
    for plan in _load_learning_plans():
        for mod in plan.get("modules") or []:
            for kp in mod.get("knowledge_points") or []:
                kid = kp.get("id") or kp.get("knowledge_point_id")
                if not kid:
                    continue
                kp_meta.setdefault(kid, {"name": kp.get("name", ""), "subject": kp.get("subject", "math")})
        for kid, level in (plan.get("mastery_levels") or {}).items():
            entry = profile.kp_mastery.get(kid)
            attempts = _plan_attempts_for(plan, kid)
            correct = sum(1 for a in attempts if a.get("is_correct"))
            n = len(attempts)
            entry = KpMastery(
                kp_id=kid,
                kp_name=kp_meta.get(kid, {}).get("name", kid),
                subject=kp_meta.get(kid, {}).get("subject", "math"),
                mastery=max(profile.kp_mastery.get(kid, KpMastery(kp_id=kid)).mastery, float(level)),
                attempts=n,
                correct_rate=(correct / n) if n else 0.0,
                last_practiced_at=plan.get("updated_at"),
            )
            profile.kp_mastery[kid] = entry

    # --- 2) mother_questions (mastery_status + FSRS review states) ---------
    rev_states = _load_mother_review_states()
    for m in _load_mothers():
        kid = m.get("knowledge_point_id")
        if not kid:
            continue
        name = m.get("title", "")
        subject = m.get("subject", "math")
        kp_meta.setdefault(kid, {"name": name, "subject": subject})
        card = rev_states.get(m.get("id"))
        entry = profile.kp_mastery.get(kid)
        if entry is None:
            entry = KpMastery(kp_id=kid, kp_name=name, subject=subject)
        entry.kp_name = name
        entry.subject = subject
        # `mastery_status` is the authoritative signal from the review loop.
        status = m.get("mastery_status", "not_mastered")
        if status == "mastered":
            entry.mastery = max(entry.mastery, MASTERED_MASTERY)
        elif status == "reviewing":
            entry.mastery = max(entry.mastery, 0.5)
        else:  # not_mastered / unknown — use FSRS retention only with real history
            reps = 0
            if isinstance(card, dict):
                try:
                    reps = int(card.get("reps") or card.get("interval_index") or 0)
                except (TypeError, ValueError):
                    reps = 0
            if reps > 0:
                ret = _fsrs_retention(card)
                entry.mastery = max(entry.mastery, min(ret, 0.89))  # cap below mastered
        if card:
            # FSRS card uses `due`; legacy fixed-interval uses `next_review_at`.
            due_val = card.get("due", card.get("next_review_at"))
            try:
                entry.next_review_at = float(due_val or 0) or None
            except (TypeError, ValueError):
                pass
        profile.kp_mastery[kid] = entry

    # --- 3) derive status + weak/strong lists -----------------------------
    now = time.time()
    for kp in profile.kp_mastery.values():
        kp.status = _status_from_mastery(kp.mastery)
        if kp.status == "weak":
            profile.weak_points.append(kp.kp_id)
        if kp.status == "mastered":
            profile.strong_points.append(kp.kp_id)
        if kp.next_review_at and kp.next_review_at <= now:
            profile.due_reviews.append(
                {
                    "kp_id": kp.kp_id,
                    "kp_name": kp.kp_name,
                    "due_at": kp.next_review_at,
                    "reason": "到期复习（FSRS 遗忘曲线）",
                }
            )

    profile.streak_days = compute_streak_days()
    profile.total_study_minutes = compute_study_minutes()
    profile.badges = compute_badges(profile)
    profile.updated_at = time.time()
    return profile


# --------------------------------------------------------------------------- #
# Memory side effects                                                          #
# --------------------------------------------------------------------------- #


def write_learning_profile_md(profile: LearnerProfile | None = None) -> str:
    """Write the deterministic L3 learning_profile.md to memory."""
    from app.services.sishu_full.services.memory import paths

    profile = profile or build_learner_profile()
    md = profile.to_markdown()
    target = paths.l3_file("learning_profile")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(md, encoding="utf-8")
    except OSError:
        logger.warning("learner_profile: failed to write L3 md", exc_info=True)
    return md


def write_learning_l2_md(profile: LearnerProfile | None = None) -> str:
    """Deterministic L2 learning surface summary (design §3.3 改动点 B).

    Per-subject mastery digest written to ``L2/learning.md`` so the memory
    workbench and any surface listing show a human-readable learning summary.
    """
    from app.services.sishu_full.services.memory import paths

    profile = profile or build_learner_profile()
    lines = [
        "# 学习摘要 Learning Summary",
        "",
        f"> 最近更新：{time.strftime('%Y-%m-%d %H:%M', time.localtime(profile.updated_at))}",
        "",
    ]
    if not profile.kp_mastery:
        lines.append("（暂无学习数据 — 完成一次答题/复习后会在这里生成摘要）")
        md = "\n".join(lines)
    else:
        for subject, kps in sorted(profile.by_subject.items()):
            subj_label = {"math": "数学", "chinese": "语文", "english": "英语"}.get(subject, subject)
            mastered = sum(1 for k in kps if k.status == "mastered")
            weak = sum(1 for k in kps if k.status == "weak")
            learning = sum(1 for k in kps if k.status == "learning")
            lines.append(f"## {subj_label}")
            lines.append(f"- 知识点：{len(kps)} 个（已掌握 {mastered} / 学习中 {learning} / 薄弱 {weak}）")
            if weak:
                weak_names = [k.kp_name for k in kps if k.status == "weak"][:8]
                lines.append(f"- 薄弱点：{'、'.join(weak_names)}")
            lines.append("")
        md = "\n".join(lines)
    target = paths.l2_file("learning")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(md, encoding="utf-8")
    except OSError:
        logger.warning("learner_profile: failed to write L2 learning md", exc_info=True)
    return md


def emit_learning_event(*, kind: str, payload: dict, session_id: str | None = None) -> None:
    """Best-effort emit of a learning event into L1 trace surface=learning."""
    try:
        import asyncio
        from app.services.sishu_full.services.memory import TraceEvent
        from app.services.sishu_full.services.memory import trace as _trace

        event = TraceEvent.new(surface="learning", kind=kind, payload=payload, session_id=session_id)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            asyncio.run(_trace.append(event))
        else:
            # caller is in a loop; schedule without awaiting (fire-and-forget).
            # _trace.append 自带 per-surface 锁且 never raises，调度安全。
            asyncio.get_running_loop().create_task(_trace.append(event))
    except Exception:  # noqa: BLE001
        logger.warning("learner_profile: emit_learning_event failed", exc_info=True)


# --------------------------------------------------------------------------- #
# Exercise recommendation (design §3.7)                                        #
# --------------------------------------------------------------------------- #


def _strip_chapter_prefix(name: str) -> str:
    """`1.1_正数和负数` -> `正数和负数` (drop leading `n.n_`)."""
    import re as _re

    return _re.sub(r"^\d+(\.\d+)*_", "", name or "").strip()


def recommend_exercises(chapter_title: str, profile: LearnerProfile | None = None) -> dict:
    """Tell the exercise tab whether this chapter hits a weak point.

    Design §3.7: since grade7 exercise questions carry no knowledge_point_id,
    we bridge by name: the chapter title (e.g. ``1.1_正数和负数``) is matched
    against weak knowledge-point names in the learner profile. The frontend
    shows a hint + prioritises this chapter's questions when matched.
    """
    profile = profile or build_learner_profile()
    if not profile.weak_points:
        return {"matched_kp": None, "weak_relevant": False}

    title = _strip_chapter_prefix(chapter_title or "")
    matched = []
    for kid in profile.weak_points:
        kp = profile.kp_mastery.get(kid)
        if kp and title and (title in kp.kp_name or kp.kp_name in title):
            matched.append({"kp_id": kid, "kp_name": kp.kp_name, "mastery": kp.mastery})
    return {
        "matched_kp": matched,
        "weak_relevant": len(matched) > 0,
        "weak_point_names": [profile.kp_mastery[kid].kp_name for kid in profile.weak_points if kid in profile.kp_mastery],
    }


__all__ = [
    "KpMastery",
    "LearnerProfile",
    "MASTERED_MASTERY",
    "WEAK_MASTERY",
    "build_learner_profile",
    "compute_streak_days",
    "compute_study_minutes",
    "compute_weekly_delta",
    "emit_learning_event",
    "recommend_exercises",
    "write_learning_l2_md",
    "write_learning_profile_md",
]
