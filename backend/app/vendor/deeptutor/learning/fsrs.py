"""FSRS-5 spaced repetition algorithm (pure Python, no external deps).

Migrated from ragflow/web/src/services/wrong-question-fsrs.ts (ts-fsrs).
Replaces DeepTutor's simple interval-sequence scheduler for mother questions,
giving per-card stability/difficulty tracking + forgetting-curve retention.

Refs:
  - https://github.com/open-spaced-repetition/fsrs4anki/wiki
  - py-fsrs / ts-fsrs use the same parameter vector w[19]

Card state is stored as a plain dict in review_states.json:
  {stability, difficulty, reps, lapses, due, last_review, elapsed_days}
"""
from __future__ import annotations

import math
import time
from typing import Any

# FSRS-5 default weights (19 params). These are the global defaults from the
# FSRS paper; users can re-optimize later via /fsrs/optimize if they log enough.
DEFAULT_W: list[float] = [
    0.4072, 1.1829, 3.1262, 15.4722, 7.2102, 0.5316, 1.0651, 0.0234,
    1.616, 0.1544, 1.0824, 1.9813, 0.0953, 0.2975, 2.2042, 0.2407,
    2.9466, 0.5034, 0.6567,
]

# Rating scale (same as ts-fsrs / Anki):
#   1 = Again (forgot), 2 = Hard, 3 = Good, 4 = Easy
AGAIN, HARD, GOOD, EASY = 1, 2, 3, 4

TARGET_RETENTION = 0.9  # schedule next review when retention drops to 90%
SECONDS_PER_DAY = 86400.0


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _now() -> float:
    return time.time()


def new_card(rating: int = GOOD, w: list[float] | None = None) -> dict[str, Any]:
    """Create a new FSRS card from the first rating.

    stability = w[rating-1], difficulty = w[4] - (rating-3)*w[5], clamped [1,10].
    """
    w = w or DEFAULT_W
    s = w[rating - 1]
    d = _clamp(w[4] - (rating - 3) * w[5], 1.0, 10.0)
    interval = _next_interval(s)
    return {
        "stability": round(s, 4),
        "difficulty": round(d, 2),
        "reps": 1,
        "lapses": 0 if rating != AGAIN else 1,
        "due": _now() + interval * SECONDS_PER_DAY,
        "last_review": _now(),
        "elapsed_days": 0,
    }


def retrievability(card: dict[str, Any], now: float | None = None) -> float:
    """Current retention R = exp(-elapsed / stability). 0..1."""
    now = now or _now()
    s = card.get("stability", 1.0)
    if s <= 0:
        return 0.0
    elapsed_days = max(0.0, (now - card.get("last_review", now)) / SECONDS_PER_DAY)
    return math.exp(-elapsed_days / s)


def _next_interval(stability: float, target: float = TARGET_RETENTION) -> float:
    """interval (days) where retention == target: I = -S * ln(target)."""
    if stability <= 0:
        return 1.0
    return max(1.0, round(stability * -math.log(target)))


def review(card: dict[str, Any], rating: int, w: list[float] | None = None) -> dict[str, Any]:
    """Apply a review to a card, returning the new card state.

    Implements FSRS-5 stability/difficulty updates:
      - D' = D - w[6]*(r-3)   (mean reversion toward w[4])
      - Again: S' = w[11]*S*... (stability drops, lapse++)
      - Hard/Good/Easy: S' = S * (1 + factor * exp(-w[9]*D) * (1-R) * ...)
    """
    w = w or DEFAULT_W
    now = _now()
    s = card.get("stability", 1.0)
    d = card.get("difficulty", w[4])
    reps = card.get("reps", 0)
    lapses = card.get("lapses", 0)
    last = card.get("last_review", now)

    elapsed_days = max(0.0, (now - last) / SECONDS_PER_DAY)
    r = retrievability(card, now)

    # Difficulty update (with mean reversion)
    d_new = d - w[6] * (rating - 3)
    d_new = _clamp(d_new + (w[4] - d_new) * w[7] if reps > 1 else d_new, 1.0, 10.0)

    if rating == AGAIN:
        # Stability decreases
        s_new = w[11] * (s ** w[12]) * ((s + 1) ** (w[13] - 1)) * math.exp(-(1 - r) * w[14])
        s_new = max(0.1, s_new)
        lapses += 1
    else:
        # Stability increases; bonus depends on difficulty, retrievability, and rating
        if rating == HARD:
            factor = w[8] * math.exp(-w[9] * d_new) * (1 - r) * (s ** -w[10]) * (s + 1) ** w[15] - 1
        elif rating == GOOD:
            factor = w[8] * math.exp(-w[9] * d_new) * (1 - r) * (s ** -w[10]) * (s + 1) ** w[15] * w[16] - 1
        else:  # EASY
            factor = w[8] * math.exp(-w[9] * d_new) * (1 - r) * (s ** -w[10]) * (s + 1) ** w[15] * (w[16] ** 2) - 1
        s_new = s * (1 + factor)
        s_new = max(s * 0.5, s_new)  # never drop below half on a pass

    interval = _next_interval(s_new)
    return {
        "stability": round(s_new, 4),
        "difficulty": round(d_new, 2),
        "reps": reps + 1,
        "lapses": lapses,
        "due": now + interval * SECONDS_PER_DAY,
        "last_review": now,
        "elapsed_days": round(elapsed_days, 2),
    }


def rating_to_bool(rating: int) -> bool:
    """Map FSRS rating to is_correct: Again=False, others=True."""
    return rating >= HARD


def format_card(card: dict[str, Any] | None) -> dict[str, Any]:
    """Human-readable summary of a card for the frontend."""
    if not card:
        return {
            "stability": 0, "difficulty": 0, "reps": 0, "lapses": 0,
            "due": None, "last_review": None, "retention": 0,
            "interval_days": 0, "state": "new",
        }
    now = _now()
    r = retrievability(card, now)
    s = card.get("stability", 0)
    due = card.get("due", now)
    interval_days = round((due - now) / SECONDS_PER_DAY, 1)
    state = "new" if card.get("reps", 0) == 0 else ("learning" if s < 1 else "review")
    if due <= now:
        state = "due"
    return {
        "stability": card.get("stability", 0),
        "difficulty": card.get("difficulty", 0),
        "reps": card.get("reps", 0),
        "lapses": card.get("lapses", 0),
        "due": due,
        "last_review": card.get("last_review"),
        "retention": round(r * 100, 1),
        "interval_days": interval_days,
        "state": state,
    }


__all__ = [
    "DEFAULT_W", "AGAIN", "HARD", "GOOD", "EASY", "TARGET_RETENTION",
    "new_card", "review", "retrievability", "rating_to_bool", "format_card",
    "_next_interval",
]
