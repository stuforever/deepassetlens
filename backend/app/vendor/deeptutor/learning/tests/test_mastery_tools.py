"""Tests for the Mastery Path tools — the seam between the chat-loop tutor and
the engine. They drive the full loop the tutor uses: build a path, read the
gate, pose + grade questions, assess qualitative objectives, with the active
path id injected server-side (never by the model)."""

from __future__ import annotations

import json
import time

import pytest

from deeptutor.learning import fsrs as fsrs_mod
from deeptutor.learning.models import PendingQuestion
from deeptutor.learning.service import LearningService
from deeptutor.learning.storage import LearningStore
from deeptutor.services.session.sqlite_store import SQLiteSessionStore
from deeptutor.tools.mastery_tool import (
    MASTERY_TOOL_TYPES,
    MasteryAssessTool,
    MasteryBuildTool,
    MasteryGradeTool,
    MasteryQuizTool,
    MasteryStatusTool,
)


@pytest.fixture
def path_id(tmp_path, monkeypatch):
    """Point the LearningStore at a temp workspace and yield a stable path id."""
    monkeypatch.setattr(LearningStore, "__init__", _store_init_factory(tmp_path))
    return "test_path"


@pytest.fixture(autouse=True)
def _isolate_runtime_roots(tmp_path, monkeypatch):
    """Redirect the default PathService (and its per-scope cache) at tmp_path.

    ``grade_and_record`` runs best-effort side effects that write through
    ``get_path_service()`` — learner-profile L1/L2/L3 files and, on wrong
    answers, the MotherQuestionStore under ``<workspace>/mother_questions``.
    Without this fixture those writes land in the developer's real workspace
    (ledgered as 5.2 对账项 "grade_and_record 侧效硬写真实 store"). Nothing in
    this module reads real workspace state, so the redirect is pure hygiene.
    """
    from deeptutor.multi_user import paths as mu_paths
    from deeptutor.services import path_service as ps_mod

    admin_service = ps_mod.PathService(workspace_root=tmp_path / "data")
    monkeypatch.setattr(ps_mod.PathService, "_instance", admin_service, raising=False)
    monkeypatch.setattr(
        ps_mod.PathService, "get_instance", classmethod(lambda cls: admin_service)
    )
    monkeypatch.setattr(mu_paths, "_path_services", {})


@pytest.fixture
def session_store(tmp_path, monkeypatch):
    store = SQLiteSessionStore(db_path=tmp_path / "chat.db")
    monkeypatch.setattr("deeptutor.services.session.get_sqlite_session_store", lambda: store)
    return store


def _store_init_factory(root):
    def _init(self, root_arg=None):  # mirrors LearningStore.__init__ signature
        from pathlib import Path

        self._root = Path(root) / "learning"
        self._root.mkdir(parents=True, exist_ok=True)

    return _init


async def _build_basic(path_id):
    build = MasteryBuildTool()
    return await build.execute(
        _mastery_path_id=path_id,
        mode="replace",
        modules=[
            {
                "name": "Module 1",
                "knowledge_points": [
                    {"name": "Truth tables", "type": "memory"},
                    {"name": "Why XOR matters", "type": "concept"},
                ],
            }
        ],
    )


# ── build ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_build_creates_path(path_id):
    result = await _build_basic(path_id)
    assert result.success
    payload = json.loads(result.content)
    assert payload["knowledge_points_added"] == 2
    assert payload["map"]["counts"]["total"] == 2


@pytest.mark.asyncio
async def test_build_rejects_empty_modules(path_id):
    result = await MasteryBuildTool().execute(_mastery_path_id=path_id, modules=[])
    assert result.success is False


@pytest.mark.asyncio
async def test_build_append_keeps_existing(path_id):
    await _build_basic(path_id)
    result = await MasteryBuildTool().execute(
        _mastery_path_id=path_id,
        mode="append",
        modules=[
            {"name": "Module 2", "knowledge_points": [{"name": "Adders", "type": "procedure"}]}
        ],
    )
    payload = json.loads(result.content)
    assert payload["map"]["counts"]["total"] == 3  # 2 existing + 1 appended


@pytest.mark.asyncio
async def test_build_unknown_type_defaults_to_concept(path_id):
    result = await MasteryBuildTool().execute(
        _mastery_path_id=path_id,
        modules=[{"name": "M", "knowledge_points": [{"name": "Thing", "type": "nonsense"}]}],
    )
    kp = json.loads(result.content)["map"]["modules"][0]["knowledge_points"][0]
    assert kp["type"] == "concept"


# ── status ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_status_empty_path_asks_for_build(path_id):
    payload = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    assert payload["status"] == "empty"


@pytest.mark.asyncio
async def test_status_points_at_first_objective(path_id):
    await _build_basic(path_id)
    payload = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    assert payload["status"] == "active"
    assert payload["next"]["action"] == "probe"
    assert payload["next"]["knowledge_point_type"] == "memory"


@pytest.mark.asyncio
async def test_no_path_id_fails_closed():
    result = await MasteryStatusTool().execute(_mastery_path_id="")
    assert result.success is False


# ── quiz + grade: the deterministic objective gate ───────────────────────────


@pytest.mark.asyncio
async def test_quiz_then_grade_drives_memory_gate(path_id):
    await _build_basic(path_id)
    status = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    kp_id = status["next"]["knowledge_point_id"]

    quiz, grade = MasteryQuizTool(), MasteryGradeTool()
    mastered = False
    for _ in range(3):
        await quiz.execute(
            _mastery_path_id=path_id,
            knowledge_point_id=kp_id,
            question="2+2?",
            expected_answer="4",
            question_type="short",
        )
        result = json.loads((await grade.execute(_mastery_path_id=path_id, answer="4")).content)
        assert result["is_correct"] is True
        mastered = result["mastered"]
    # 0.5 -> 0.8 -> 1.0 ≥ 0.9: mastered only after the third correct answer.
    assert mastered is True


@pytest.mark.asyncio
async def test_grade_without_pending_fails(path_id):
    await _build_basic(path_id)
    result = await MasteryGradeTool().execute(_mastery_path_id=path_id, answer="x")
    assert result.success is False


@pytest.mark.asyncio
async def test_quiz_unknown_kp_fails(path_id):
    await _build_basic(path_id)
    result = await MasteryQuizTool().execute(
        _mastery_path_id=path_id,
        knowledge_point_id="nope",
        question="?",
        expected_answer="x",
    )
    assert result.success is False


@pytest.mark.asyncio
async def test_wrong_answer_does_not_master(path_id):
    await _build_basic(path_id)
    status = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    kp_id = status["next"]["knowledge_point_id"]
    await MasteryQuizTool().execute(
        _mastery_path_id=path_id, knowledge_point_id=kp_id, question="2+2?", expected_answer="4"
    )
    result = json.loads(
        (await MasteryGradeTool().execute(_mastery_path_id=path_id, answer="5")).content
    )
    assert result["is_correct"] is False
    assert result["mastered"] is False


@pytest.mark.asyncio
async def test_grade_syncs_mastery_attempt_to_question_bank(path_id, session_store):
    session = await session_store.create_session(title="Mastery Session")
    await _build_basic(path_id)
    status = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    kp_id = status["next"]["knowledge_point_id"]
    await MasteryQuizTool().execute(
        _mastery_path_id=path_id,
        knowledge_point_id=kp_id,
        question="2+2?",
        expected_answer="4",
        question_type="short",
    )

    result = json.loads(
        (
            await MasteryGradeTool().execute(
                _mastery_path_id=path_id,
                _session_id=session["id"],
                _turn_id="turn_mastery_1",
                answer="5",
            )
        ).content
    )

    assert result["is_correct"] is False
    wrong_entries = await session_store.list_notebook_entries(is_correct=False)
    assert wrong_entries["total"] == 1
    entry = wrong_entries["items"][0]
    assert entry["session_title"] == "Mastery Session"
    assert entry["turn_id"] == "turn_mastery_1"
    assert entry["question"] == "2+2?"
    assert entry["question_type"] == "short_answer"
    assert entry["user_answer"] == "5"
    assert entry["correct_answer"] == "4"
    assert entry["is_correct"] is False


@pytest.mark.asyncio
async def test_choice_quiz_rejects_bare_option_labels(path_id):
    await _build_basic(path_id)
    status = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    kp_id = status["next"]["knowledge_point_id"]

    result = await MasteryQuizTool().execute(
        _mastery_path_id=path_id,
        knowledge_point_id=kp_id,
        question="Which order is correct?",
        expected_answer="A",
        question_type="choice",
        options=["A", "B", "C", "D"],
    )

    assert result.success is False
    assert "full option bodies" in result.content


@pytest.mark.asyncio
async def test_choice_quiz_preserves_bodies_and_normalizes_answer(path_id, session_store):
    session = await session_store.create_session(title="Choice Mastery")
    await _build_basic(path_id)
    status = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    kp_id = status["next"]["knowledge_point_id"]

    quiz = await MasteryQuizTool().execute(
        _mastery_path_id=path_id,
        knowledge_point_id=kp_id,
        question="Where is the stop condition added?",
        expected_answer="Step 6",
        question_type="choice",
        options=[
            "A: Step 2 — write the first tool",
            "B: Step 4 — test one call",
            "C: Step 6 — add the stop condition",
            "D: Step 7 — add another tool",
        ],
    )
    assert quiz.success is True

    grade = json.loads(
        (
            await MasteryGradeTool().execute(
                _mastery_path_id=path_id,
                _session_id=session["id"],
                _turn_id="turn_choice_1",
                answer="C",
            )
        ).content
    )
    assert grade["is_correct"] is True

    entries = await session_store.list_notebook_entries()
    entry = entries["items"][0]
    assert entry["options"] == {
        "A": "Step 2 — write the first tool",
        "B": "Step 4 — test one call",
        "C": "Step 6 — add the stop condition",
        "D": "Step 7 — add another tool",
    }
    assert entry["correct_answer"] == "C"
    assert entry["user_answer"] == "C"
    assert entry["is_correct"] is True


# ── assess: the qualitative gate ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_assess_passes_concept(path_id):
    await _build_basic(path_id)
    # Drive past the memory objective so status reaches the concept one.
    status = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    mem_kp = status["next"]["knowledge_point_id"]
    for _ in range(3):
        await MasteryQuizTool().execute(
            _mastery_path_id=path_id, knowledge_point_id=mem_kp, question="q", expected_answer="a"
        )
        await MasteryGradeTool().execute(_mastery_path_id=path_id, answer="a")

    status2 = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    concept_kp = status2["next"]["knowledge_point_id"]
    assert status2["next"]["action"] == "probe"
    assert status2["next"]["knowledge_point_type"] == "concept"

    result = json.loads(
        (
            await MasteryAssessTool().execute(
                _mastery_path_id=path_id, knowledge_point_id=concept_kp, passed=True, feedback="ok"
            )
        ).content
    )
    assert result["mastered"] is True
    assert result["next"]["action"] == "complete"


@pytest.mark.asyncio
async def test_assess_rejects_quantitative_type(path_id):
    await _build_basic(path_id)
    status = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    mem_kp = status["next"]["knowledge_point_id"]  # a memory objective
    result = await MasteryAssessTool().execute(
        _mastery_path_id=path_id, knowledge_point_id=mem_kp, passed=True
    )
    assert result.success is False


# ── fail-closed without a server-injected path id (task 8.6) ─────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_cls", MASTERY_TOOL_TYPES, ids=lambda cls: cls.__name__)
async def test_no_path_id_fails_closed_for_every_mastery_tool(tool_cls):
    """Every mastery tool refuses to act without the pipeline-injected path id.

    The model can never supply ``_mastery_path_id`` itself (augment_kwargs
    injects it server-side), so a missing id must fail closed on all five
    tools with the same guard message — not just ``mastery_status``.
    """
    result = await tool_cls().execute(_mastery_path_id="   ")
    assert result.success is False
    assert result.content == (
        "No mastery path is active on this turn; mastery tools are unavailable."
    )


# ── FSRS-5 wiring: MasteryGradeTool schedules through the FSRS bridge ────────


async def _grade_once(path_id: str, kp_id: str, *, answer: str) -> dict:
    await MasteryQuizTool().execute(
        _mastery_path_id=path_id,
        knowledge_point_id=kp_id,
        question="2+2?",
        expected_answer="4",
        question_type="short",
    )
    return json.loads((await MasteryGradeTool().execute(_mastery_path_id=path_id, answer=answer)).content)


@pytest.mark.asyncio
async def test_grade_persists_fsrs_repetition_state_and_review_queue(path_id):
    """A graded answer leaves an FSRS-5 card in ``repetition_states``.

    Pins the §3.5 阶段3a wiring: MasteryGradeTool constructs an
    ``FsrsSpacedRepetitionScheduler`` (not the legacy interval-sequence one),
    so the stored state carries the FSRS flag + card fields and the review
    queue is rebuilt from it.
    """
    await _build_basic(path_id)
    status = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    kp_id = status["next"]["knowledge_point_id"]

    result = await _grade_once(path_id, kp_id, answer="4")
    assert result["is_correct"] is True

    progress = LearningService(LearningStore()).get_or_create(path_id)
    state = progress.repetition_states[kp_id]
    assert state.fsrs is True  # legacy scheduler never sets this flag
    # The persisted card is the FSRS initial card for a first GOOD rating.
    assert state.reps == 1
    assert state.lapses == 0
    assert state.stability == pytest.approx(fsrs_mod.DEFAULT_W[2], abs=1e-3)
    assert state.difficulty == pytest.approx(round(fsrs_mod.DEFAULT_W[4], 2), abs=1e-2)
    # next_review_at mirrors the card's due: ~1 day out (I(-S·ln 0.9) = 1 day).
    assert state.next_review_at > time.time() + 12 * 3600
    assert state.next_review_at < time.time() + 36 * 3600

    # The review queue was rebuilt from the FSRS state.
    assert [task.knowledge_point_id for task in progress.review_queue] == [kp_id]
    task = progress.review_queue[0]
    assert task.due_at == state.next_review_at
    assert task.knowledge_type.value == "memory"
    assert task.priority == 2  # memory priority; no error record on a correct answer


@pytest.mark.asyncio
async def test_grade_wrong_answer_still_records_new_fsrs_card_shape(path_id):
    """Status quo pin: a wrong first answer still stores the initial GOOD card.

    ``FsrsSpacedRepetitionScheduler.get_initial_state`` always builds the card
    from a GOOD rating (correctness only feeds ``schedule_next``), so the
    persisted state after a wrong answer shows lapses=0/reps=1 — the AGAIN
    update never reaches storage. Annotated as 5.2 对账项 family behavior.
    """
    await _build_basic(path_id)
    status = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    kp_id = status["next"]["knowledge_point_id"]

    result = await _grade_once(path_id, kp_id, answer="5")
    assert result["is_correct"] is False

    progress = LearningService(LearningStore()).get_or_create(path_id)
    state = progress.repetition_states[kp_id]
    assert state.fsrs is True
    assert state.lapses == 0  # the AGAIN rating never landed on the card
    # The failure itself was recorded: error record + mastery dropped to 0.
    assert len(progress.error_records) == 1
    assert progress.mastery_levels[kp_id] == 0.0


@pytest.mark.asyncio
async def test_fsrs_state_stays_at_initial_card_across_grades_status_quo(path_id):
    """Status quo pin: the persisted FSRS card never advances past its birth.

    ``LearningService.grade_and_record`` discards
    ``scheduler.schedule_next(...)``'s return value (service.py:207). The
    legacy scheduler mutates the state in place, so this was invisible; the
    FSRS bridge returns a NEW state, so the stored card is frozen at the
    initial one while the FSRS ladder is unreachable. Same bridge-defect
    family as the 5.2 对账项 (``_state_to_card`` hardcoding). Pinning the
    current behavior per the 5.4 precedent: when the bridge is fixed this
    test flips red and triggers review.
    """
    await _build_basic(path_id)
    status = json.loads((await MasteryStatusTool().execute(_mastery_path_id=path_id)).content)
    kp_id = status["next"]["knowledge_point_id"]

    for _ in range(2):
        await _grade_once(path_id, kp_id, answer="4")

    progress = LearningService(LearningStore()).get_or_create(path_id)
    state = progress.repetition_states[kp_id]
    assert state.fsrs is True
    assert state.reps == 1  # two grades, card still at its initial reps
    assert state.stability == pytest.approx(fsrs_mod.DEFAULT_W[2], abs=1e-3)
    # Only the SR layer is frozen: both attempts were recorded and mastery
    # advanced 0.5 -> 0.8 under the cap policy.
    assert len(progress.quiz_attempts) == 2
    assert progress.mastery_levels[kp_id] == 0.8


# ── legacy choice recovery: the tools ↔ choices integration seam ─────────────


class _FakeSessionStore:
    """Session-store double: canned turn events + recorded notebook upserts."""

    def __init__(self, events=None):
        self._events = events or []
        self.upserted: list[tuple[str, list[dict]]] = []

    async def get_turn_events(self, turn_id, after_seq=0):
        return self._events

    async def upsert_notebook_entries(self, session_id, items):
        self.upserted.append((session_id, list(items)))
        return {"upserted": len(items)}


def _ask_user_event(prompt: str, options: list[tuple[str, str]]) -> dict:
    return {
        "type": "tool_call",
        "metadata": {
            "tool_name": "ask_user",
            "args": {
                "questions": [
                    {
                        "prompt": prompt,
                        "options": [
                            {"label": label, "description": body} for label, body in options
                        ],
                    }
                ]
            },
        },
    }


def _seed_legacy_choice_pending(path_id: str, kp_id: str, prompt: str) -> None:
    """Register a pending choice question with bare labels (legacy shape)."""
    service = LearningService(LearningStore())
    progress = service.get_or_create(path_id)
    service.set_pending_question(
        progress,
        PendingQuestion(
            question_id="q-legacy-1",
            knowledge_point_id=kp_id,
            module_id="test_path_m0",
            prompt=prompt,
            question_type="choice",
            expected_answer="C",
            options=["A", "B", "C", "D"],
        ),
    )


@pytest.mark.asyncio
async def test_legacy_choice_grade_recovers_bodies_from_ask_user_turn(path_id, monkeypatch):
    """A pre-contract pending question (bare labels) grades through bodies
    recovered from the turn's ``ask_user`` card, and the question-bank entry
    persists the recovered bodies — not the bare labels."""
    await _build_basic(path_id)
    prompt = "Where is the stop condition added?"
    kp_id = "test_path_m0_kp0"
    _seed_legacy_choice_pending(path_id, kp_id, prompt)

    store = _FakeSessionStore(
        [
            _ask_user_event(
                prompt,
                [("A", "Step 2"), ("B", "Step 4"), ("C", "Step 6")],
            )
        ]
    )
    monkeypatch.setattr(
        "deeptutor.services.session.get_sqlite_session_store", lambda: store
    )

    result = json.loads(
        (
            await MasteryGradeTool().execute(
                _mastery_path_id=path_id,
                _session_id="sess-1",
                _turn_id="turn_9",
                answer="C",
            )
        ).content
    )
    assert result["is_correct"] is True

    (session_id, items) = store.upserted[0]
    assert session_id == "sess-1"
    entry = items[0]
    assert entry["question_id"] == "q-legacy-1"
    assert entry["options"] == {"A": "Step 2", "B": "Step 4", "C": "Step 6"}
    assert entry["correct_answer"] == "C"
    assert entry["user_answer"] == "C"
    assert entry["is_correct"] is True


@pytest.mark.asyncio
async def test_legacy_choice_recovery_failure_falls_back_to_registered_answer(
    path_id, monkeypatch
):
    """When turn-event recovery fails, grading falls back to the registered
    expected answer and the question bank stores the bare legacy labels."""
    await _build_basic(path_id)
    kp_id = "test_path_m0_kp0"
    _seed_legacy_choice_pending(path_id, kp_id, "Where is the stop condition added?")

    class _RaisingTurnStore(_FakeSessionStore):
        async def get_turn_events(self, turn_id, after_seq=0):
            raise RuntimeError("store unavailable")

    store = _RaisingTurnStore()
    monkeypatch.setattr(
        "deeptutor.services.session.get_sqlite_session_store", lambda: store
    )

    result = json.loads(
        (
            await MasteryGradeTool().execute(
                _mastery_path_id=path_id,
                _session_id="sess-1",
                _turn_id="turn_9",
                answer="C",
            )
        ).content
    )
    # Expected stayed the registered label "C"; the learner answered "C" → correct.
    assert result["is_correct"] is True
    # The question-bank sync still ran, storing the bare legacy label map.
    (session_id, items) = store.upserted[0]
    assert items[0]["options"] == {"A": "A", "B": "B", "C": "C", "D": "D"}


@pytest.mark.asyncio
async def test_legacy_choice_recovery_miss_grades_against_registered_label(path_id, monkeypatch):
    """A non-matching ask_user prompt recovers no bodies; the registered label
    stays authoritative (deterministic grading compares like with like)."""
    await _build_basic(path_id)
    kp_id = "test_path_m0_kp0"
    _seed_legacy_choice_pending(path_id, kp_id, "Where is the stop condition added?")

    store = _FakeSessionStore(
        [
            _ask_user_event(
                "An unrelated question",
                [("A", "body a"), ("B", "body b")],
            )
        ]
    )
    monkeypatch.setattr(
        "deeptutor.services.session.get_sqlite_session_store", lambda: store
    )

    result = json.loads(
        (
            await MasteryGradeTool().execute(
                _mastery_path_id=path_id,
                _session_id="sess-1",
                _turn_id="turn_9",
                answer="C",
            )
        ).content
    )
    assert result["is_correct"] is True  # expected "C" vs answer "C"
    (session_id, items) = store.upserted[0]
    # No bodies recovered → the entry stores the bare legacy label map.
    assert items[0]["options"] == {"A": "A", "B": "B", "C": "C", "D": "D"}


# ── validation branches (task 8.6) ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_quiz_missing_required_fields_fails(path_id):
    await _build_basic(path_id)
    for kwargs in (
        {"question": "q", "expected_answer": "a"},  # no knowledge_point_id
        {"knowledge_point_id": "kp", "expected_answer": "a"},  # no question
        {"knowledge_point_id": "kp", "question": "q"},  # no expected_answer
    ):
        result = await MasteryQuizTool().execute(_mastery_path_id=path_id, **kwargs)
        assert result.success is False
        assert "knowledge_point_id, question, and expected_answer" in result.content


@pytest.mark.asyncio
async def test_quiz_invalid_question_type_falls_back_to_short(path_id):
    await _build_basic(path_id)
    result = await MasteryQuizTool().execute(
        _mastery_path_id=path_id,
        knowledge_point_id="test_path_m0_kp0",
        question="2+2?",
        expected_answer="4",
        question_type="Weird",
    )
    assert result.success is True
    progress = LearningService(LearningStore()).get_or_create(path_id)
    assert progress.pending_question.question_type == "short"


@pytest.mark.asyncio
async def test_assess_missing_knowledge_point_id_fails(path_id):
    await _build_basic(path_id)
    result = await MasteryAssessTool().execute(_mastery_path_id=path_id, passed=True)
    assert result.success is False
    assert "needs a knowledge_point_id" in result.content


@pytest.mark.asyncio
async def test_assess_unknown_objective_fails(path_id):
    await _build_basic(path_id)
    result = await MasteryAssessTool().execute(
        _mastery_path_id=path_id, knowledge_point_id="nope", passed=True
    )
    assert result.success is False
    assert "Unknown objective 'nope'" in result.content


@pytest.mark.asyncio
async def test_build_invalid_mode_falls_back_to_replace(path_id):
    await _build_basic(path_id)
    result = await MasteryBuildTool().execute(
        _mastery_path_id=path_id,
        mode="bogus",
        modules=[{"name": "Only", "knowledge_points": [{"name": "Thing", "type": "concept"}]}],
    )
    payload = json.loads(result.content)
    assert payload["mode"] == "replace"
    # Replace semantics: the old module is gone, only the new one remains.
    assert payload["map"]["counts"]["total"] == 1


@pytest.mark.asyncio
async def test_build_skips_invalid_module_and_kp_entries(path_id):
    result = await MasteryBuildTool().execute(
        _mastery_path_id=path_id,
        modules=[
            "not-a-dict",  # non-dict module skipped
            {"name": "  ", "knowledge_points": [{"name": "Lost", "type": "memory"}]},  # blank name
            {
                "name": "M2",
                "knowledge_points": [
                    {"name": "x"},  # name shorter than 2 chars skipped
                    {"name": "Kept", "type": "procedure"},
                ],
            },
            {"name": "M3", "knowledge_points": []},  # no kps left → module skipped
        ],
    )
    assert result.success is True
    payload = json.loads(result.content)
    assert payload["modules_added"] == 1
    assert payload["knowledge_points_added"] == 1
    assert payload["map"]["modules"][0]["name"] == "M2"


@pytest.mark.asyncio
async def test_build_with_no_surviving_modules_fails(path_id):
    result = await MasteryBuildTool().execute(
        _mastery_path_id=path_id,
        modules=[{"name": "M", "knowledge_points": []}],
    )
    assert result.success is False
    assert "No valid modules" in result.content


@pytest.mark.asyncio
async def test_build_append_generates_offset_server_side_ids(path_id):
    """Append-mode module ids continue after the existing map (m0, m1, …) so
    the model never controls storage keys."""
    await _build_basic(path_id)  # creates test_path_m0
    await MasteryBuildTool().execute(
        _mastery_path_id=path_id,
        mode="append",
        modules=[{"name": "M2", "knowledge_points": [{"name": "Adders", "type": "procedure"}]}],
    )
    progress = LearningService(LearningStore()).get_or_create(path_id)
    assert [m.id for m in progress.modules] == ["test_path_m0", "test_path_m1"]
    assert [kp.id for kp in progress.modules[1].knowledge_points] == ["test_path_m1_kp0"]
