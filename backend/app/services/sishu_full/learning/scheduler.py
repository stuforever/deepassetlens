"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""
from __future__ import annotations

import os
import time

from app.services.sishu_full.learning.models import (
    KnowledgeType,
    LearningProgress,
    RepetitionState,
    ReviewTask,
)

INTERVAL_SEQUENCES: dict[KnowledgeType, list[int]] = {
    KnowledgeType.MEMORY: [0, 1, 3, 7, 14, 30, 60],
    KnowledgeType.CONCEPT: [3, 7, 14, 30],
    KnowledgeType.PROCEDURE: [3, 7, 14],
    KnowledgeType.DESIGN: [14, 28],
}

_TYPE_PRIORITY: dict[KnowledgeType, int] = {
    KnowledgeType.MEMORY: 2,
    KnowledgeType.CONCEPT: 3,
    KnowledgeType.PROCEDURE: 4,
    KnowledgeType.DESIGN: 5,
}


class SpacedRepetitionScheduler:
    def __init__(self) -> None:
        # When True, intervals are in seconds instead of days (for testing)
        self.DEBUG_MODE: bool = os.environ.get("LEARNING_DEBUG", "").lower() in ("1", "true", "yes")

    def _seconds_per_unit(self) -> float:
        return 1.0 if self.DEBUG_MODE else 86400.0

    def get_initial_state(self, knowledge_type: KnowledgeType) -> RepetitionState:
        intervals = INTERVAL_SEQUENCES[knowledge_type]
        return RepetitionState(
            interval_index=0,
            consecutive_correct=0,
            consecutive_wrong=0,
            next_review_at=time.time() + intervals[0] * self._seconds_per_unit(),
        )

    def schedule_next(
        self, state: RepetitionState, knowledge_type: KnowledgeType, is_correct: bool
    ) -> RepetitionState:
        intervals = INTERVAL_SEQUENCES[knowledge_type]
        max_index = len(intervals) - 1

        if is_correct:
            state.consecutive_wrong = 0
            state.consecutive_correct += 1
            if state.consecutive_correct >= 2:
                state.interval_index += 2
                state.consecutive_correct = 0
            else:
                state.interval_index += 1
        else:
            state.consecutive_wrong += 1
            state.consecutive_correct = 0
            state.interval_index = max(0, state.interval_index - 1)
            if state.consecutive_wrong >= 2:
                state.consecutive_wrong = 0

        state.interval_index = max(0, min(state.interval_index, max_index))
        state.next_review_at = (
            time.time() + intervals[state.interval_index] * self._seconds_per_unit()
        )
        return state

    def get_due_tasks(self, progress: LearningProgress, max_tasks: int = 5) -> list[ReviewTask]:
        now = time.time()
        due = [t for t in progress.review_queue if t.due_at <= now]
        due.sort(key=lambda t: t.priority)
        return due[:max_tasks]

    def build_review_queue(self, progress: LearningProgress) -> list[ReviewTask]:
        tasks: list[ReviewTask] = []
        error_kps: set[str] = set()
        for rec in progress.error_records:
            if rec.status in ("active", "retrying"):
                error_kps.add(rec.knowledge_point_id)

        for kp_id, state in progress.repetition_states.items():
            kp_type = progress.knowledge_types.get(kp_id, KnowledgeType.MEMORY)
            priority = 1 if kp_id in error_kps else _TYPE_PRIORITY[kp_type]
            tasks.append(
                ReviewTask(
                    id=f"review_{kp_id}",
                    knowledge_point_id=kp_id,
                    knowledge_type=kp_type,
                    due_at=state.next_review_at,
                    priority=priority,
                    state=state,
                )
            )
        return tasks


class FsrsSpacedRepetitionScheduler:
    """FSRS-5 spaced-repetition scheduler for mastery-path knowledge points
    (design §3.5 阶段3a).

    Bridges the FSRS-5 algorithm (``deeptutor.learning.fsrs``) onto the
    ``RepetitionState`` shape used by ``LearningProgress.repetition_states``:
    the FSRS card fields are stored in the state's extension fields and
    ``next_review_at`` mirrors the card's ``due`` so existing queue/review
    consumers keep working unchanged.
    """

    def __init__(self) -> None:
        from app.services.sishu_full.learning import fsrs as _fsrs

        self._fsrs = _fsrs

    def get_initial_state(self, knowledge_type: KnowledgeType) -> RepetitionState:
        _ = knowledge_type  # FSRS uses one parameter set regardless of type
        card = self._fsrs.new_card(self._fsrs.GOOD)
        return self._card_to_state(card)

    def _card_to_state(self, card: dict) -> RepetitionState:
        return RepetitionState(
            interval_index=0,
            consecutive_correct=0,
            consecutive_wrong=0,
            next_review_at=float(card.get("due", time.time())),
            stability=card.get("stability"),
            difficulty=card.get("difficulty"),
            reps=int(card.get("reps", 0)),
            lapses=int(card.get("lapses", 0)),
            fsrs=True,
        )

    def _state_to_card(self, state: RepetitionState) -> dict:
        return {
            "stability": float(state.stability) if state.stability is not None else 1.0,
            "difficulty": float(state.difficulty) if state.difficulty is not None else self._fsrs.DEFAULT_W[4],
            "reps": int(state.reps),
            "lapses": int(state.lapses),
            "due": state.next_review_at,
            "last_review": time.time(),
            "elapsed_days": 0,
        }

    def schedule_next(
        self, state: RepetitionState, knowledge_type: KnowledgeType, is_correct: bool
    ) -> RepetitionState:
        _ = knowledge_type
        card = self._state_to_card(state)
        rating = self._fsrs.GOOD if is_correct else self._fsrs.AGAIN
        new_card = self._fsrs.review(card, rating)
        return self._card_to_state(new_card)

    def get_due_tasks(self, progress: LearningProgress, max_tasks: int = 5) -> list[ReviewTask]:
        return SpacedRepetitionScheduler().get_due_tasks(progress, max_tasks)

    def build_review_queue(self, progress: LearningProgress) -> list[ReviewTask]:
        return SpacedRepetitionScheduler().build_review_queue(progress)


__all__ = ["SpacedRepetitionScheduler", "FsrsSpacedRepetitionScheduler", "INTERVAL_SEQUENCES"]
