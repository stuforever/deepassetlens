"""H5 自主学习 G1 · 答题进引擎（开箱即学情）测试。

覆盖：影子进度建树 / 判题正确性（choice/fill）/ 掌握度变化 /
FSRS 复习队列生成 / 答错自动沉淀错题本 / 隔离（u 缺省=admin）/
E3 离线补报服务端契约（outbox 串行重放全落库 / attempt_id 幂等 /
乱序容忍——重复被吸收、不重复的不丢不重）。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


class _FakePathService:
    """指向 tmp 工作区的 PathService 替身（复用学习/课程 store 的默认根）。"""

    def __init__(self, root: Path) -> None:
        self._root = root

    def get_workspace_dir(self) -> Path:
        self._root.mkdir(parents=True, exist_ok=True)
        return self._root


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """把 learning 学习/课程/母题/记忆四个面的根重定向到 tmp 工作区。"""
    from deeptutor.learning import curriculum, storage
    import deeptutor.learning.mother_question as mq_mod
    import deeptutor.learning.h5_progress as h5p
    from deeptutor.services.memory import paths as memory_paths
    from deeptutor.services.memory import trace as trace_mod

    fake = _FakePathService(tmp_path)
    monkeypatch.setattr(storage, "get_path_service", lambda: fake)
    monkeypatch.setattr(curriculum, "get_path_service", lambda: fake)
    monkeypatch.setattr(mq_mod, "get_path_service", lambda: fake)
    # h5_progress 内容读走 admin（真实数据）——测试里指向 tmp，避免依赖真实章节
    monkeypatch.setattr(h5p, "_content_store", lambda: curriculum.CurriculumStore())

    class _FakeMemoryPathService:
        """memory_root() 替身：L1 trace / L2 / L3 写入全部指向 tmp。"""

        def get_memory_dir(self) -> Path:
            d = tmp_path / "memory"
            d.mkdir(parents=True, exist_ok=True)
            return d

    # grade_and_record 的 best-effort 画像块经 services.memory.paths 的
    # ContextVar 解析 memory 根，不受 storage.get_path_service 影响——
    # 不隔离会写穿真实 data/memory（5.2 泄漏同类，已在真实 trace 取证）。
    with memory_paths.memory_path_service_override(_FakeMemoryPathService()):
        # 同步上下文每条事件各起新事件循环；trace 的 per-surface 锁跨 loop
        # 复用会被 append 静默吞掉——每次取新锁，保证逐条事件真实落盘
        # （套件先例：test_pre1_event 的 trace 锁隔离）。
        monkeypatch.setattr(trace_mod, "_lock_for", lambda surface: asyncio.Lock())
        yield tmp_path


def _learning_trace_events(ws: Path) -> list[dict]:
    """读取 tmp 隔离区内的 L1 learning trace 事件（跨日期聚合）。"""
    import json

    trace_dir = ws / "memory" / "trace" / "learning"
    events: list[dict] = []
    if trace_dir.exists():
        for f in sorted(trace_dir.glob("*.jsonl")):
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    events.append(json.loads(line))
    return events


def _seed_chapter(ws: Path) -> tuple[str, str]:
    """写入 1 个 chapter + 2 个 kp，返回 (chapter_id, kp_id)。"""
    import json

    kp_dir = ws / "curriculum"
    kp_dir.mkdir(parents=True, exist_ok=True)
    kps = [
        {"id": "kp_a", "name": "正数和负数", "subject": "math", "grade": "初中"},
        {"id": "kp_b", "name": "数轴", "subject": "math", "grade": "初中"},
    ]
    (kp_dir / "knowledge_points.json").write_text(
        json.dumps(kps, ensure_ascii=False), encoding="utf-8"
    )
    chapter = {
        "id": "ch_1",
        "textbook_id": "tb_1",
        "name": "正数和负数",
        "order": 0,
        "kp_ids": ["kp_a"],
    }
    (kp_dir / "chapters.json").write_text(
        json.dumps([chapter], ensure_ascii=False), encoding="utf-8"
    )
    (kp_dir / "textbooks.json").write_text("[]", encoding="utf-8")
    (kp_dir / "textbook_pages.json").write_text("[]", encoding="utf-8")
    return "ch_1", "kp_a"


def _seed_exercise(ws: Path) -> dict:
    """写入 grade7_index.json 的 1 个 exercise（2 道 choice + 1 道 fill）。"""
    import json

    g7 = ws / "grade7"
    g7.mkdir(parents=True, exist_ok=True)
    idx = {
        "exercises": [
            {
                "id": "ch_1_负数",
                "title": "正数和负数",
                "chapter_ids": ["ch_1"],
                "count": 3,
                "questions": [
                    {
                        "id": "q1",
                        "ask": "下列属于负数的是？",
                        "type": "choice",
                        "options": ["-3", "0", "1"],
                        "answer": 0,
                        "why": "-3 是负数",
                    },
                    {
                        "id": "q2",
                        "ask": "0 是正数还是负数？",
                        "type": "choice",
                        "options": ["正数", "负数", "都不是"],
                        "answer": 2,
                        "why": "0 既不是正数也不是负数",
                    },
                    {
                        "id": "q3",
                        "ask": "零下 3℃ 记作？",
                        "type": "fill",
                        "answer": ["-3℃", "−3℃", "-3", "−3"],
                        "why": "零下为负",
                    },
                ],
            }
        ],
        "courseware": [],
        "voices": [],
        "figures": [],
    }
    (g7 / "grade7_index.json").write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")
    return idx


def _grade(ws, **overrides):
    from deeptutor.learning.h5_progress import grade_h5_exercise

    # 自动从 grade7_index 反查 exercise/question（模拟端点的 _lookup_grade7）
    import json

    idx_path = ws / "grade7" / "grade7_index.json"
    idx = json.loads(idx_path.read_text(encoding="utf-8")) if idx_path.exists() else {}
    exercise = question = None
    qid = overrides.get("question_id", "q1")
    for ex in idx.get("exercises", []):
        for q in ex.get("questions", []):
            if str(q.get("id")) == str(qid):
                exercise, question = ex, q
                break

    defaults = dict(
        chapter_id="ch_1",
        question_id="q1",
        question_type="choice",
        question_text="下列属于负数的是？",
        user_answer="0",
        expected_answer="",
        exercise=exercise,
        question=question,
    )
    defaults.update(overrides)
    return grade_h5_exercise(**defaults)


# --------------------------------------------------------------------------- #
# 建树                                                                         #
# --------------------------------------------------------------------------- #


def test_ensure_h5_progress_creates_shadow_progress(ws, monkeypatch):
    from deeptutor.learning.h5_progress import ensure_h5_progress

    chapter_id, kp_id = _seed_chapter(ws)
    progress = ensure_h5_progress(chapter_id)
    assert progress.book_id == f"shadow_{chapter_id}"
    assert progress.modules and progress.modules[0].id == chapter_id
    assert progress.knowledge_types.get(kp_id) is not None  # FSRS 可调度
    # 幂等：再次调用不重建
    progress2 = ensure_h5_progress(chapter_id)
    assert progress2.book_id == progress.book_id


# --------------------------------------------------------------------------- #
# 判题 + 掌握度                                                                #
# --------------------------------------------------------------------------- #


def test_grade_choice_correct_updates_mastery(ws):
    _seed_chapter(ws)
    _seed_exercise(ws)
    res = _grade(ws, question_id="q1", user_answer="0")
    assert res["is_correct"] is True
    assert res["kp_id"] == "kp_a"
    assert res["kp_name"] == "正数和负数"
    assert res["mastery"] == 0.5  # compute_mastery 单题正确=0.5（置信度上限）
    assert res["weak_now"] is False
    assert res["recorded_mother"] is False


def test_grade_choice_wrong_lowers_mastery_and_records_mother(ws):
    _seed_chapter(ws)
    _seed_exercise(ws)
    res = _grade(ws, question_id="q1", user_answer="1")  # 选 0，错
    assert res["is_correct"] is False
    assert res["mastery"] == 0.0
    assert res["weak_now"] is True
    assert res["recorded_mother"] is True


def test_grade_fill_multicandidate(ws):
    _seed_chapter(ws)
    _seed_exercise(ws)
    # 命中候选列表之一
    res = _grade(ws, question_id="q3", user_answer="-3", question_type="fill")
    assert res["is_correct"] is True


def test_grade_with_explicit_expected_answer(ws):
    _seed_chapter(ws)
    _seed_exercise(ws)
    res = _grade(ws, question_id="q2", user_answer="2", expected_answer="2")
    assert res["is_correct"] is True


# --------------------------------------------------------------------------- #
# FSRS 复习队列                                                                #
# --------------------------------------------------------------------------- #


def test_wrong_answer_builds_review_queue(ws):
    from deeptutor.learning.h5_progress import ensure_h5_progress

    _seed_chapter(ws)
    _seed_exercise(ws)
    _grade(ws, question_id="q1", user_answer="1")  # 错
    progress = ensure_h5_progress("ch_1")
    assert progress.review_queue, "答错后应生成复习队列"
    assert any(t.knowledge_point_id == "kp_a" for t in progress.review_queue)


# --------------------------------------------------------------------------- #
# 知识点归属                                                                   #
# --------------------------------------------------------------------------- #


def test_resolve_kp_uses_chapter_link(ws):
    from deeptutor.learning.h5_progress import resolve_kp_for_exercise

    _seed_chapter(ws)
    ex = {"id": "ch_1_负数", "title": "正数和负数", "chapter_ids": ["ch_1"]}
    kp_id, kp_name = resolve_kp_for_exercise(ex)
    assert kp_id == "kp_a"
    assert kp_name == "正数和负数"


def test_resolve_kp_fallback_when_no_chapter(ws):
    from deeptutor.learning.h5_progress import resolve_kp_for_exercise

    _seed_chapter(ws)
    ex = {"id": "x", "title": "不存在章节", "chapter_ids": []}
    kp_id, kp_name = resolve_kp_for_exercise(ex)
    assert kp_id.startswith("ex_")  # fallback 占位
    assert kp_name == "不存在章节"


# --------------------------------------------------------------------------- #
# E3 离线补报：outbox 联网回传 / 幂等 / 乱序容忍（服务端面）                     #
# outbox 本体在 web 侧 IndexedDB（web/lib/h5-outbox.ts，web 测试覆盖）；         #
# 这里钉死其依赖的服务端契约：串行重放全落库、attempt_id 幂等短路、              #
# 乱序到达不丢不重不崩（保序重放是客户端义务——设计第五篇 E3 边界）。             #
# --------------------------------------------------------------------------- #


def test_offline_outbox_replay_records_all_attempts(ws):
    """outbox 串行重放契约：3 条离线积累（2 对 1 错）逐条补报 → 全部落库。

    对应 E3 验收「断网做 3 题（含 1 错题）→ 联网 → 掌握度变化正确、
    错题本出现 1 条且不重复」的服务端面。
    """
    _seed_chapter(ws)
    _seed_exercise(ws)
    res1 = _grade(ws, question_id="q1", user_answer="0", attempt_id="a-1")  # 对
    res2 = _grade(ws, question_id="q2", user_answer="1", attempt_id="a-2")  # 错
    res3 = _grade(ws, question_id="q1", user_answer="0", attempt_id="a-3")  # 对（重试）
    assert all(r["ok"] is True for r in (res1, res2, res3))
    assert res2["is_correct"] is False
    assert res2["weak_now"] is True  # [对,错] 掌握度 0.49 < 判弱阈值 0.6

    from deeptutor.learning.h5_progress import ensure_h5_progress

    progress = ensure_h5_progress("ch_1")
    assert progress.attempt_ids == ["a-1", "a-2", "a-3"]  # 按回传顺序落库
    assert len(progress.quiz_attempts) == 3  # 每条恰记录一次
    # 掌握度按回传序列 [对, 错, 对] 精确推进（新近加权 + 置信上限）
    assert res3["mastery"] == pytest.approx(1.85 / 2.8)
    # 错题本恰 1 条且不重复
    assert len(progress.error_records) == 1
    assert progress.error_records[0].question_id == "q2"
    assert progress.error_records[0].status == "active"
    # 每条回传的离线做题都产生学习事件（L1 trace，tmp 隔离）
    events = [e for e in _learning_trace_events(ws) if e["kind"] == "quiz_attempt"]
    assert len(events) == 3


def test_replayed_attempt_id_is_idempotent(ws):
    """联网补报幂等：同 attempt_id 二次上报短路，副作用只发生一次。

    与 test_e3_dedup 的替身版互补：这里走真实 LearningService + tmp 落盘，
    验证 attempt_ids 跨调用持久化（二次上报经磁盘重载命中幂等集合）。
    """
    _seed_chapter(ws)
    _seed_exercise(ws)
    first = _grade(ws, question_id="q1", user_answer="0", attempt_id="a-1")
    assert "deduped" not in first
    assert first["is_correct"] is True

    import time

    from deeptutor.learning.h5_progress import ensure_h5_progress

    progress = ensure_h5_progress("ch_1")
    mastery_before = dict(progress.mastery_levels)
    review_before = [t.knowledge_point_id for t in progress.review_queue]
    next_review_before = progress.repetition_states["kp_a"].next_review_at

    repeat = _grade(ws, question_id="q1", user_answer="0", attempt_id="a-1")
    assert repeat["ok"] is True
    assert repeat["deduped"] is True  # 幂等短路真实命中
    assert repeat["is_correct"] is None  # 不重新判题
    assert repeat["mastery"] == first["mastery"]  # 回读既有快照，而非重算
    assert repeat["next_review_at"] == time.strftime(
        "%Y-%m-%d %H:%M", time.localtime(next_review_before)
    )

    progress2 = ensure_h5_progress("ch_1")
    assert progress2.attempt_ids == ["a-1"]  # 未二次追加
    assert len(progress2.quiz_attempts) == 1  # attempt 只记录一次
    assert dict(progress2.mastery_levels) == mastery_before  # 掌握度未再推进
    assert [t.knowledge_point_id for t in progress2.review_queue] == review_before
    assert progress2.repetition_states["kp_a"].next_review_at == next_review_before
    assert progress2.error_records == []
    # 幂等命中不产生新学习事件
    events = [e for e in _learning_trace_events(ws) if e["kind"] == "quiz_attempt"]
    assert len(events) == 1


def test_out_of_order_duplicate_replay_is_tolerated(ws):
    """乱序容忍：迟到重放旧条目（乱序重复）被幂等吸收，较新状态不回滚。"""
    _seed_chapter(ws)
    _seed_exercise(ws)
    _grade(ws, question_id="q1", user_answer="0", attempt_id="a-1")  # 先：对
    wrong = _grade(ws, question_id="q2", user_answer="1", attempt_id="a-2")  # 后：错
    assert wrong["mastery"] == pytest.approx(0.95 / 1.95)

    # 乱序迟到的旧条目重放（联网后 outbox 重放与增量上报竞态的典型形态）
    late = _grade(ws, question_id="q1", user_answer="0", attempt_id="a-1")
    assert late["deduped"] is True
    assert late["mastery"] == pytest.approx(0.95 / 1.95)  # 较新状态未被回滚

    from deeptutor.learning.h5_progress import ensure_h5_progress

    progress = ensure_h5_progress("ch_1")
    assert progress.attempt_ids == ["a-1", "a-2"]  # 未二次追加
    assert len(progress.quiz_attempts) == 2
    assert len(progress.error_records) == 1
    assert progress.mastery_levels["kp_a"] == pytest.approx(0.95 / 1.95)


def test_out_of_order_distinct_attempts_recorded_once_each(ws):
    """乱序容忍（服务端面）：不同 attempt 乱序到达各恰记录一次，不丢不重。

    到达顺序决定新近加权（设计 E3 边界：FSRS/掌握度状态机依赖顺序，
    保序重放是客户端义务）——服务端对任意到达序都不丢不崩。
    """
    _seed_chapter(ws)
    _seed_exercise(ws)
    first = _grade(ws, question_id="q2", user_answer="1", attempt_id="a-1")  # 后发生但先到：错
    second = _grade(ws, question_id="q1", user_answer="0", attempt_id="a-2")  # 先发生但后到：对
    assert first["is_correct"] is False
    assert second["is_correct"] is True

    from deeptutor.learning.h5_progress import ensure_h5_progress

    progress = ensure_h5_progress("ch_1")
    assert progress.attempt_ids == ["a-1", "a-2"]
    assert len(progress.quiz_attempts) == 2
    assert {(a.question_id, a.is_correct) for a in progress.quiz_attempts} == {
        ("q2", False),
        ("q1", True),
    }
    # 到达序决定掌握度：[错, 对] = 1.0/1.95（按发生序 [对, 错] 则为 0.95/1.95）
    assert progress.mastery_levels["kp_a"] == pytest.approx(1.0 / 1.95)
    assert len(progress.error_records) == 1  # q1 的答对不误"毕业"q2 的错题记录


def test_empty_attempt_id_replays_are_not_deduped(ws):
    """幂等键边界：attempt_id 为空（旧客户端/直调）不做去重——每次都完整处理。"""
    _seed_chapter(ws)
    _seed_exercise(ws)
    r1 = _grade(ws, question_id="q1", user_answer="0")  # attempt_id 缺省 ""
    r2 = _grade(ws, question_id="q1", user_answer="0")
    assert "deduped" not in r1
    assert "deduped" not in r2
    assert r1["is_correct"] is True
    assert r2["is_correct"] is True

    from deeptutor.learning.h5_progress import ensure_h5_progress

    progress = ensure_h5_progress("ch_1")
    assert progress.attempt_ids == []  # 无键不占幂等集合
    assert len(progress.quiz_attempts) == 2  # 两次都完整落库
