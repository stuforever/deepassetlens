import copy
import time

import pytest

from deeptutor.learning import fsrs
from deeptutor.learning.models import (
    ErrorRecord,
    ErrorType,
    KnowledgeType,
    LearningProgress,
    RepetitionState,
    ReviewTask,
)
from deeptutor.learning.scheduler import (
    INTERVAL_SEQUENCES,
    FsrsSpacedRepetitionScheduler,
    SpacedRepetitionScheduler,
)


@pytest.fixture
def scheduler():
    return SpacedRepetitionScheduler()


# ── interval sequences ───────────────────────────────────────────────────


class TestIntervalSequences:
    def test_memory_sequence(self):
        assert INTERVAL_SEQUENCES[KnowledgeType.MEMORY] == [0, 1, 3, 7, 14, 30, 60]

    def test_concept_sequence(self):
        assert INTERVAL_SEQUENCES[KnowledgeType.CONCEPT] == [3, 7, 14, 30]

    def test_procedure_sequence(self):
        assert INTERVAL_SEQUENCES[KnowledgeType.PROCEDURE] == [3, 7, 14]

    def test_design_sequence(self):
        assert INTERVAL_SEQUENCES[KnowledgeType.DESIGN] == [14, 28]


# ── get_initial_state ────────────────────────────────────────────────────


class TestInitialState:
    def test_memory_initial(self, scheduler):
        state = scheduler.get_initial_state(KnowledgeType.MEMORY)
        assert state.interval_index == 0
        assert state.consecutive_correct == 0
        assert state.consecutive_wrong == 0
        assert abs(state.next_review_at - time.time()) < 5

    def test_design_initial(self, scheduler):
        state = scheduler.get_initial_state(KnowledgeType.DESIGN)
        assert state.interval_index == 0
        assert abs(state.next_review_at - time.time() - 14 * 86400) < 5


# ── schedule_next: correct advances ──────────────────────────────────────


class TestCorrectAdvances:
    def test_first_correct(self, scheduler):
        state = scheduler.get_initial_state(KnowledgeType.MEMORY)
        state = scheduler.schedule_next(state, KnowledgeType.MEMORY, True)
        assert state.interval_index == 1
        assert state.consecutive_correct == 1
        assert state.consecutive_wrong == 0

    def test_two_consecutive_skip(self, scheduler):
        state = scheduler.get_initial_state(KnowledgeType.MEMORY)
        state = scheduler.schedule_next(state, KnowledgeType.MEMORY, True)  # idx=1, cc=1
        state = scheduler.schedule_next(state, KnowledgeType.MEMORY, True)  # idx=3, cc=0
        assert state.interval_index == 3
        assert state.consecutive_correct == 0


# ── schedule_next: wrong retreats ────────────────────────────────────────


class TestWrongRetreats:
    def test_wrong_decrements(self, scheduler):
        state = scheduler.get_initial_state(KnowledgeType.MEMORY)
        state = scheduler.schedule_next(state, KnowledgeType.MEMORY, True)  # idx=1
        state = scheduler.schedule_next(state, KnowledgeType.MEMORY, False)  # idx=0
        assert state.interval_index == 0
        assert state.consecutive_wrong == 1
        assert state.consecutive_correct == 0

    def test_two_consecutive_wrong_resets(self, scheduler):
        state = scheduler.get_initial_state(KnowledgeType.MEMORY)
        state = scheduler.schedule_next(state, KnowledgeType.MEMORY, True)  # idx=1
        state = scheduler.schedule_next(state, KnowledgeType.MEMORY, False)  # idx=0, cw=1
        state = scheduler.schedule_next(state, KnowledgeType.MEMORY, False)  # idx=0, cw resets
        assert state.consecutive_wrong == 0


# ── schedule_next: boundaries ────────────────────────────────────────────


class TestBoundaries:
    def test_cant_go_below_zero(self, scheduler):
        state = scheduler.get_initial_state(KnowledgeType.MEMORY)
        state = scheduler.schedule_next(state, KnowledgeType.MEMORY, False)
        assert state.interval_index == 0

    def test_cant_exceed_sequence(self, scheduler):
        state = scheduler.get_initial_state(KnowledgeType.MEMORY)
        state.interval_index = 6  # max for MEMORY
        state = scheduler.schedule_next(state, KnowledgeType.MEMORY, True)
        assert state.interval_index == 6


# ── different types ──────────────────────────────────────────────────────


class TestDifferentTypes:
    def test_design_first_correct(self, scheduler):
        state = scheduler.get_initial_state(KnowledgeType.DESIGN)
        state = scheduler.schedule_next(state, KnowledgeType.DESIGN, True)
        assert state.interval_index == 1

    def test_concept_sequence(self, scheduler):
        state = scheduler.get_initial_state(KnowledgeType.CONCEPT)
        state = scheduler.schedule_next(state, KnowledgeType.CONCEPT, True)
        assert state.interval_index == 1


# ── get_due_tasks ────────────────────────────────────────────────────────


class TestGetDueTasks:
    def test_returns_due_only(self, scheduler):
        now = time.time()
        state = RepetitionState(next_review_at=now - 10)
        task = ReviewTask(
            id="r1",
            knowledge_point_id="kp1",
            knowledge_type=KnowledgeType.MEMORY,
            due_at=now - 10,
            priority=1,
            state=state,
        )
        lp = LearningProgress(book_id="b1", review_queue=[task])
        due = scheduler.get_due_tasks(lp)
        assert len(due) == 1

    def test_skips_future(self, scheduler):
        now = time.time()
        state = RepetitionState(next_review_at=now + 86400)
        task = ReviewTask(
            id="r1",
            knowledge_point_id="kp1",
            knowledge_type=KnowledgeType.MEMORY,
            due_at=now + 86400,
            priority=1,
            state=state,
        )
        lp = LearningProgress(book_id="b1", review_queue=[task])
        due = scheduler.get_due_tasks(lp)
        assert len(due) == 0

    def test_sorted_by_priority(self, scheduler):
        now = time.time()
        lp = LearningProgress(book_id="b1")
        lp.review_queue = [
            ReviewTask(
                id="r_low",
                knowledge_point_id="kp_low",
                knowledge_type=KnowledgeType.MEMORY,
                due_at=now - 10,
                priority=5,
                state=RepetitionState(next_review_at=now - 10),
            ),
            ReviewTask(
                id="r_high",
                knowledge_point_id="kp_high",
                knowledge_type=KnowledgeType.MEMORY,
                due_at=now - 10,
                priority=1,
                state=RepetitionState(next_review_at=now - 10),
            ),
        ]
        due = scheduler.get_due_tasks(lp)
        assert [t.id for t in due] == ["r_high", "r_low"]

    def test_respects_max_tasks(self, scheduler):
        now = time.time()
        lp = LearningProgress(book_id="b1")
        lp.review_queue = [
            ReviewTask(
                id=f"r{i}",
                knowledge_point_id=f"kp{i}",
                knowledge_type=KnowledgeType.MEMORY,
                due_at=now - 10,
                priority=i,
                state=RepetitionState(next_review_at=now - 10),
            )
            for i in range(8)
        ]
        due = scheduler.get_due_tasks(lp, max_tasks=3)
        assert len(due) == 3


# ── build_review_queue ───────────────────────────────────────────────────


class TestBuildReviewQueue:
    def test_error_records_get_priority_1(self, scheduler):
        now = time.time()
        state = RepetitionState(next_review_at=now)
        lp = LearningProgress(book_id="b1")
        lp.repetition_states["kp1"] = state
        lp.knowledge_types["kp1"] = KnowledgeType.MEMORY
        lp.error_records = [
            ErrorRecord(
                id="e1",
                question_id="q1",
                knowledge_point_id="kp1",
                module_id="m1",
                error_type=ErrorType.APPLICATION_ERROR,
            )
        ]
        tasks = scheduler.build_review_queue(lp)
        assert len(tasks) == 1
        assert tasks[0].priority == 1

    def test_non_error_kp_uses_type_priority(self, scheduler):
        now = time.time()
        lp = LearningProgress(book_id="b1")
        lp.repetition_states["kp_design"] = RepetitionState(next_review_at=now)
        lp.knowledge_types["kp_design"] = KnowledgeType.DESIGN
        tasks = scheduler.build_review_queue(lp)
        assert len(tasks) == 1
        # DESIGN has the lowest urgency -> largest priority number, never 1.
        assert tasks[0].priority == 5
        assert tasks[0].knowledge_type == KnowledgeType.DESIGN

    def test_graduated_error_does_not_promote_priority(self, scheduler):
        now = time.time()
        lp = LearningProgress(book_id="b1")
        lp.repetition_states["kp1"] = RepetitionState(next_review_at=now)
        lp.knowledge_types["kp1"] = KnowledgeType.CONCEPT
        # Only active/retrying error records boost priority to 1.
        lp.error_records = [
            ErrorRecord(
                id="e1",
                question_id="q1",
                knowledge_point_id="kp1",
                module_id="m1",
                error_type=ErrorType.APPLICATION_ERROR,
                status="graduated",
            )
        ]
        tasks = scheduler.build_review_queue(lp)
        assert len(tasks) == 1
        assert tasks[0].priority == 3  # CONCEPT type priority, not 1

    def test_retrying_error_promotes_priority(self, scheduler):
        now = time.time()
        lp = LearningProgress(book_id="b1")
        lp.repetition_states["kp1"] = RepetitionState(next_review_at=now)
        lp.knowledge_types["kp1"] = KnowledgeType.CONCEPT
        lp.error_records = [
            ErrorRecord(
                id="e1",
                question_id="q1",
                knowledge_point_id="kp1",
                module_id="m1",
                error_type=ErrorType.APPLICATION_ERROR,
                status="retrying",
            )
        ]
        tasks = scheduler.build_review_queue(lp)
        assert tasks[0].priority == 1

    def test_defaults_missing_type_to_memory(self, scheduler):
        now = time.time()
        lp = LearningProgress(book_id="b1")
        lp.repetition_states["kp1"] = RepetitionState(next_review_at=now)
        # No entry in knowledge_types -> defaults to MEMORY (priority 2).
        tasks = scheduler.build_review_queue(lp)
        assert len(tasks) == 1
        assert tasks[0].knowledge_type == KnowledgeType.MEMORY
        assert tasks[0].priority == 2


# ── FSRS 四档调度（design §3.5 阶段3a / 任务 5.2 表征蓝本）────────────────
#
# 四档评分行：again/hard/good/easy = rating 1..4（H5 评分行四键）。
# 表征要点（按真实实现钉死，非理想 FSRS 教科书值）：
#   * interval 有 1 天下限（_next_interval max(1.0, ...)），且 pass 分支有
#     max(s*0.5, s_new) 下限 —— 低保持率区间 HARD/GOOD 会被地板塌缩，
#     因此"四档阶梯"在稳定性维度用 (s=1, d=1, elapsed=1d) 区间严格断言，
#     interval 维度用 新卡 easy 最长 / 成熟卡 again 最短 断言。
#   * 难度维度四档严格逆序（again 提难、easy 降难），且钳制 [1, 10]。


class TestFsrsRatingConstants:
    def test_four_ratings_are_again_hard_good_easy(self):
        assert fsrs.AGAIN == 1
        assert fsrs.HARD == 2
        assert fsrs.GOOD == 3
        assert fsrs.EASY == 4

    def test_rating_to_bool_maps_h5_grading_row(self):
        # H5 评分行四键：1=again(错)、2/3/4=hard/good/easy(对)
        assert [fsrs.rating_to_bool(r) for r in (1, 2, 3, 4)] == [False, True, True, True]


class TestFsrsFourRatingLadder:
    def test_new_card_stability_ladder_strict(self):
        # FSRS-5 初始稳定性 w[rating-1] 严格递增
        stabilities = [fsrs.new_card(r)["stability"] for r in (1, 2, 3, 4)]
        assert stabilities == [
            pytest.approx(fsrs.DEFAULT_W[0]),
            pytest.approx(fsrs.DEFAULT_W[1]),
            pytest.approx(fsrs.DEFAULT_W[2]),
            pytest.approx(fsrs.DEFAULT_W[3]),
        ]
        assert stabilities[0] < stabilities[1] < stabilities[2] < stabilities[3]

    def test_new_card_easy_gives_longest_interval(self):
        # rating=4（easy）给最长间隔：15.47 天稳定度 -> 2 天，其余钉 1 天下限
        intervals = [round(fsrs.new_card(r)["due"] - fsrs.new_card(r)["last_review"]) for r in (1, 2, 3, 4)]
        assert intervals[3] > intervals[2] == intervals[1] == intervals[0] == round(86400.0)

    def test_lapsed_review_stability_ladder_strict(self):
        # 低难度、保持率回落的区间：四档稳定性严格递增（again < hard < good < easy）
        def _card() -> dict:
            return {
                "stability": 1.0,
                "difficulty": 1.0,
                "reps": 2,
                "lapses": 0,
                "due": time.time(),
                "last_review": time.time() - 86400.0,
                "elapsed_days": 1,
            }

        laddered = [fsrs.review(_card(), r)["stability"] for r in (1, 2, 3, 4)]
        assert laddered[0] < laddered[1] < laddered[2] < laddered[3]

    def test_lapsed_review_difficulty_inverse_ladder(self):
        # 难度严格逆序：again 提难最多、easy 降难最多
        def _card() -> dict:
            return {
                "stability": 1.0,
                "difficulty": 1.0,
                "reps": 2,
                "lapses": 0,
                "due": time.time(),
                "last_review": time.time() - 86400.0,
                "elapsed_days": 1,
            }

        difficulties = [fsrs.review(_card(), r)["difficulty"] for r in (1, 2, 3, 4)]
        assert difficulties[0] > difficulties[1] > difficulties[2] > difficulties[3]

    def test_again_is_the_only_lapsing_rating(self):
        base = fsrs.new_card(fsrs.GOOD)
        lapses = [fsrs.review(copy.deepcopy(base), r)["lapses"] for r in (1, 2, 3, 4)]
        assert lapses == [1, 0, 0, 0]

    def test_again_interval_shorter_than_pass_on_mature_card(self):
        # 成熟卡（s=60）隔 10 天复习：again 崩到 ~0.12 -> 1 天下限；
        # pass 档被 s*0.5 地板托住（30）-> 3 天，again 间隔严格最短
        def _mature() -> dict:
            now = time.time()
            return {
                "stability": 60.0,
                "difficulty": 5.0,
                "reps": 5,
                "lapses": 0,
                "due": now,
                "last_review": now - 10 * 86400.0,
                "elapsed_days": 10,
            }

        again = fsrs.review(_mature(), 1)
        good = fsrs.review(_mature(), 3)
        easy = fsrs.review(_mature(), 4)
        iv_again = again["due"] - again["last_review"]
        iv_good = good["due"] - good["last_review"]
        iv_easy = easy["due"] - easy["last_review"]
        assert iv_again < iv_good <= iv_easy
        assert again["stability"] < 1.0
        assert good["stability"] == pytest.approx(30.0)  # s*0.5 pass floor


class TestFsrsBoundaries:
    def test_consecutive_again_resets_stability_and_keeps_lapse_count(self):
        # 连错：lapses 逐次 +1（连错重置语义）、稳定性压到低位、难度顶死上限
        card = fsrs.new_card(fsrs.GOOD)
        seen_lapses = []
        for _ in range(6):
            card = fsrs.review(card, fsrs.AGAIN)
            seen_lapses.append(card["lapses"])
            assert card["stability"] <= 1.3  # 从 3.13 崩落后贴地
            assert card["difficulty"] <= 10.0
        assert seen_lapses == [1, 2, 3, 4, 5, 6]

    def test_difficulty_clamped_at_upper_bound(self):
        card = fsrs.new_card(fsrs.GOOD)
        for _ in range(6):
            card = fsrs.review(card, fsrs.AGAIN)
        assert card["difficulty"] == 10.0  # 不越界上界

    def test_difficulty_clamped_at_lower_bound(self):
        card = fsrs.new_card(fsrs.EASY)
        for _ in range(8):
            card = fsrs.review(card, fsrs.EASY)
        assert card["difficulty"] >= 1.0  # 不越界下界

    def test_interval_floor_is_one_day(self):
        # 不越界：任何评分链的下次到期间隔 >= 1 天
        card = fsrs.new_card(fsrs.AGAIN)
        for rating in (1, 2, 3, 4, 1, 4, 2):
            card = fsrs.review(card, rating)
            assert card["due"] - card["last_review"] >= 86400.0 - 1.0

    def test_stability_floor_on_lapse(self):
        card = fsrs.new_card(fsrs.EASY)
        for _ in range(5):
            card = fsrs.review(card, fsrs.AGAIN)
            assert card["stability"] >= 0.1

    def test_pass_never_drops_below_half_stability(self):
        # pass 分支文档化地板 max(s*0.5, s_new)：原地（elapsed=0）复习 GOOD
        # 增益项 (1-r)=0 -> 钉在 s*0.5（表征值，非理想 FSRS 行为）
        base = fsrs.new_card(fsrs.GOOD)
        out = fsrs.review(copy.deepcopy(base), fsrs.GOOD)
        assert out["stability"] == pytest.approx(base["stability"] * 0.5)


class TestFsrsSchedulerBridge:
    """FsrsSpacedRepetitionScheduler：fsrs.py 与 RepetitionState 的桥。"""

    @pytest.fixture
    def fsrs_scheduler(self):
        return FsrsSpacedRepetitionScheduler()

    def test_initial_state_is_fsrs_card(self, fsrs_scheduler):
        state = fsrs_scheduler.get_initial_state(KnowledgeType.MEMORY)
        assert state.fsrs is True
        assert state.reps == 1
        assert state.lapses == 0
        assert state.stability == pytest.approx(fsrs.DEFAULT_W[2])  # GOOD
        assert state.next_review_at > time.time()

    def test_wrong_answer_uses_again_rating(self, fsrs_scheduler):
        state = fsrs_scheduler.get_initial_state(KnowledgeType.MEMORY)
        out = fsrs_scheduler.schedule_next(state, KnowledgeType.MEMORY, is_correct=False)
        assert out.lapses == state.lapses + 1
        assert out.fsrs is True

    def test_correct_answer_uses_good_rating(self, fsrs_scheduler):
        state = fsrs_scheduler.get_initial_state(KnowledgeType.MEMORY)
        out = fsrs_scheduler.schedule_next(state, KnowledgeType.MEMORY, is_correct=True)
        assert out.lapses == 0
        assert out.reps == 2

    def test_legacy_state_roundtrips_through_bridge(self, fsrs_scheduler):
        # 旧固定间隔状态（无 FSRS 扩展字段）可无损过桥
        legacy = RepetitionState(next_review_at=time.time() - 5)
        out = fsrs_scheduler.schedule_next(legacy, KnowledgeType.MEMORY, is_correct=True)
        assert out.fsrs is True
        assert out.reps == 1

    def test_due_tasks_delegate_to_legacy_queue(self, fsrs_scheduler):
        # 到期队列/优先级排序沿用 legacy 调度器（到期优先级排序断言）
        now = time.time()
        lp = LearningProgress(book_id="b1")
        lp.review_queue = [
            ReviewTask(
                id="r_low",
                knowledge_point_id="kp_low",
                knowledge_type=KnowledgeType.MEMORY,
                due_at=now - 10,
                priority=5,
                state=RepetitionState(next_review_at=now - 10),
            ),
            ReviewTask(
                id="r_high",
                knowledge_point_id="kp_high",
                knowledge_type=KnowledgeType.MEMORY,
                due_at=now - 10,
                priority=1,
                state=RepetitionState(next_review_at=now - 10),
            ),
        ]
        due = fsrs_scheduler.get_due_tasks(lp)
        assert [t.id for t in due] == ["r_high", "r_low"]  # priority 排序不变
