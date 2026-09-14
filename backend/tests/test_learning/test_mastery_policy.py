# -*- coding: utf-8 -*-
"""⑤批1（A1）：compute_mastery 低置信上限策略——DeepTutor 直迁（前 5 条纯测，语义零改）。"""
import pytest

from app.services.learning.mastery import compute_mastery


def test_compute_mastery_single_correct_is_capped_at_half():
    """A single lucky answer cannot 'master' a point: 1 attempt caps at 0.5."""
    assert compute_mastery([True]) == 0.5


def test_compute_mastery_cap_progression():
    """Cap relaxes as evidence accumulates: 1->0.5, 2->0.8, 3+->up to 1.0."""
    assert compute_mastery([True]) == 0.5
    assert compute_mastery([True, True]) == 0.8
    assert compute_mastery([True, True, True]) == pytest.approx(1.0)


def test_compute_mastery_empty_is_zero():
    assert compute_mastery([]) == 0.0


def test_compute_mastery_partial_correctness_scales():
    """More correct answers within the recency window yield a higher score
    (below the cap, where attempt count no longer clamps the result)."""
    one_of_five = compute_mastery([True, False, False, False, False])
    two_of_five = compute_mastery([True, True, False, False, False])
    three_of_five = compute_mastery([True, True, True, False, False])
    assert one_of_five < two_of_five < three_of_five


def test_compute_mastery_weighs_recent_attempts_more_heavily():
    """Regression test for #618: recency weighting must actually distinguish
    a recovering history from a declining one, even with the same correct
    count. A miss-then-two-hits history should score higher than a
    two-hits-then-miss history."""
    recovering = compute_mastery([False, True, True])
    declining = compute_mastery([True, True, False])
    assert recovering > declining
    assert recovering == pytest.approx(0.696, abs=1e-3)
