"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

# Recency weights for the most recent attempts (oldest -> newest). Newer
# attempts count more, so recovery after early mistakes is rewarded.
_RECENCY_WEIGHTS: tuple[float, ...] = (0.5, 0.7, 0.85, 0.95, 1.0)

# Mastery cannot exceed this until enough attempts accumulate, so one or two
# correct answers cannot declare a point "mastered".
_CONFIDENCE_CAP: dict[int, float] = {1: 0.5, 2: 0.8}


def compute_mastery(correctness: list[bool]) -> float:
    """Return a 0..1 mastery score from a knowledge point's attempt outcomes.

    Args:
        correctness: per-attempt correctness in chronological order.
    """
    if not correctness:
        return 0.0
    recent = correctness[-len(_RECENCY_WEIGHTS) :]
    weights = _RECENCY_WEIGHTS[-len(recent) :]
    score = sum(w * (1.0 if c else 0.0) for c, w in zip(recent, weights, strict=True)) / sum(
        weights
    )
    return min(score, _CONFIDENCE_CAP.get(len(recent), 1.0))


__all__ = ["compute_mastery"]
