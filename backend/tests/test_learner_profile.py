# -*- coding: utf-8 -*-
"""⑤补补-2 步骤 1：画像聚合 TDD——streak/due/weak/今日活跃数学断言（不赌 LLM）。"""
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy import text

from app.services.learning.pg import _engine

UID = "tdd-profile-user"


def _mk_card(card_id: str, kind: str, item_id: str, *, stability: float, days_ago_last: float,
             due_days: float = -1.0, reps: int = 3, lapses: int = 0):
    now = datetime.now(timezone.utc)
    with _engine.begin() as c:
        c.execute(text(
            "INSERT INTO learning_review_cards (card_id, kind, item_id, user_id, stability, "
            "difficulty, reps, lapses, due, last_review) VALUES "
            "(:cid, :kind, :item, :uid, :st, 5.0, :reps, :lapses, :due, :lr) ON CONFLICT (card_id) DO UPDATE "
            "SET stability=:st, reps=:reps, lapses=:lapses, due=:due, last_review=:lr"),
            {"cid": card_id, "kind": kind, "item": item_id, "uid": UID, "st": stability,
             "reps": reps, "lapses": lapses, "due": now + timedelta(days=due_days),
             "lr": now - timedelta(days=days_ago_last)})


def _mk_record(card_id: str, days_ago: float):
    now = datetime.now(timezone.utc)
    with _engine.begin() as c:
        c.execute(text(
            "INSERT INTO learning_review_records (card_id, user_id, rating, scheduled_interval, reviewed_at) "
            "VALUES (:cid, :uid, 3, 1.0, :at)"),
            {"cid": card_id, "uid": UID, "at": now - timedelta(days=days_ago)})


def _cleanup():
    with _engine.begin() as c:
        c.execute(text("DELETE FROM learning_review_records WHERE user_id=:u"), {"u": UID})
        c.execute(text("DELETE FROM learning_review_cards WHERE user_id=:u"), {"u": UID})


@pytest.fixture()
def clean():
    _cleanup()
    yield
    _cleanup()


def test_streak_and_today_active(clean):
    """streak=reviewed_at::date 连续区间（今天+昨天+前天=3）；今日活跃=今日 records 数。"""
    _mk_card("c-streak-1", "knowledge_point", "kp:有理数", stability=5.0, days_ago_last=0.01)
    _mk_record("c-streak-1", 0.01)   # 今天
    _mk_record("c-streak-1", 1.2)    # 昨天
    _mk_record("c-streak-1", 2.1)    # 前天
    from app.services.learning.learner_profile import build_learner_profile
    p = build_learner_profile(UID)
    assert p.streak_days == 3, f"streak={p.streak_days}"
    assert p.today_reviews == 1, f"today={p.today_reviews}"


def test_streak_broken(clean):
    """断档：今天+前天（缺昨天）→ streak=1。"""
    _mk_card("c-streak-2", "knowledge_point", "kp:正数与负数", stability=5.0, days_ago_last=0.01)
    _mk_record("c-streak-2", 0.01)
    _mk_record("c-streak-2", 2.5)
    from app.services.learning.learner_profile import build_learner_profile
    p = build_learner_profile(UID)
    assert p.streak_days == 1, f"streak={p.streak_days}"


def test_weak_order_by_retention(clean):
    """weak=kind=knowledge_point 卡 retention 升序 top-5：久未复习+低稳定 → 更弱。"""
    _mk_card("c-w-strong", "knowledge_point", "kp:有理数", stability=60.0, days_ago_last=0.5)
    _mk_card("c-w-mid", "knowledge_point", "kp:正数与负数", stability=10.0, days_ago_last=3.0)
    _mk_card("c-w-weak", "knowledge_point", "kp:整式", stability=2.0, days_ago_last=10.0)
    from app.services.learning.learner_profile import build_learner_profile
    p = build_learner_profile(UID)
    weak_ids = [w["item_id"] for w in p.weak_points]
    assert weak_ids[:3] == ["kp:整式", "kp:正数与负数", "kp:有理数"], f"weak={weak_ids}"


def test_due_reviews_count(clean):
    """due=到期卡（due<=now）计数。"""
    _mk_card("c-due-1", "knowledge_point", "kp:整式", stability=5.0, days_ago_last=2.0, due_days=-1.0)
    _mk_card("c-due-2", "mother_question", "mq-seed-0001", stability=5.0, days_ago_last=1.0, due_days=3.0)
    from app.services.learning.learner_profile import build_learner_profile
    p = build_learner_profile(UID)
    due_ids = [d["item_id"] for d in p.due_reviews]
    assert "kp:整式" in due_ids and "mq-seed-0001" not in due_ids, f"due={due_ids}"


def test_empty_profile_defaults(clean):
    """无数据 → 空画像（streak 0/各清单空）——与 DeepTutor 无数据路径一致。"""
    from app.services.learning.learner_profile import build_learner_profile
    p = build_learner_profile("tdd-nobody-user")
    assert p.streak_days == 0 and p.weak_points == [] and p.due_reviews == []
