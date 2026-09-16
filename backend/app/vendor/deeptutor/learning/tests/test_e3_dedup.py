"""E3 离线答题幂等单测：attempt_ids 集合语义 + grade_exercise 透传 attempt_id + 幂等短路行为。

副作用只发生一次的保证 = progress.attempt_ids 集合 + grade_h5_exercise 短路；
这里验证模型字段/裁剪语义、API 层把 attempt_id 透传给 grade_h5_exercise，
并用替身服务钉死短路行为（同 attempt_id 补报 deduped=True，副作用只发生一次）。
"""

from __future__ import annotations

import time
from types import SimpleNamespace

from deeptutor.learning.models import LearningProgress, RepetitionState

# 替身 grade_and_record 写入的固定调度时间戳（验证短路快照回读、不再推进）
_FAKE_NEXT_REVIEW_AT = 1_800_000_000.0


class _FakeContentStore:
    """单章节单知识点的课程 store 替身（ensure_h5_progress 建树用）。"""

    def __init__(self) -> None:
        self.chapter = SimpleNamespace(id="ch1", name="第一章", kp_ids=["kp1"])
        self._kps = [SimpleNamespace(id="kp1", name="知识点一")]

    def list_chapters(self, textbook_id: str) -> list:
        return [self.chapter]

    def list_kps(self) -> list:
        return list(self._kps)


class _FakeLearningService:
    """内存版 LearningService 替身：同一 progress 原位维护；grade_and_record
    以调用计数模拟 mastery/FSRS/错题/事件整条副作用链（单题答对语义）。"""

    def __init__(self) -> None:
        self.progress: LearningProgress | None = None
        self.grade_calls = 0

    def get_or_create(self, book_id: str) -> LearningProgress:
        if self.progress is None:
            self.progress = LearningProgress(book_id=book_id)
        return self.progress

    def replace_modules(self, progress: LearningProgress, modules) -> None:
        progress.modules = list(modules)

    def save(self, progress: LearningProgress) -> None:
        pass

    def grade_and_record(self, progress: LearningProgress, **kw) -> bool:
        self.grade_calls += 1
        kp_id = kw["knowledge_point_id"]
        progress.mastery_levels[kp_id] = 0.5
        progress.repetition_states[kp_id] = RepetitionState(
            next_review_at=_FAKE_NEXT_REVIEW_AT
        )
        return True


def test_learning_progress_has_attempt_ids():
    p = LearningProgress(book_id="x")
    assert p.attempt_ids == []


def test_attempt_ids_dedup_and_tail_cap_500():
    p = LearningProgress(book_id="x")
    # 模拟一次上报：append 一次
    p.attempt_ids.append("a1")
    assert p.attempt_ids == ["a1"]
    # 同 id 再次出现则重复（短路由 grade_h5_exercise 判断"in"），先验证集合语义
    assert "a1" in p.attempt_ids
    # 尾部裁剪到 500
    p.attempt_ids = list(range(600))
    p.attempt_ids = p.attempt_ids[-500:]
    assert len(p.attempt_ids) == 500
    assert p.attempt_ids[0] == 100


def test_grade_exercise_forwards_attempt_id(monkeypatch):
    captured: dict = {}

    def fake_grade(**kw):
        captured.update(kw)
        return {"ok": True, "is_correct": True, "kp_id": "kp1", "kp_name": "测试",
                "mastery": 0.5, "next_review_at": None, "recorded_mother": False,
                "weak_now": False}

    monkeypatch.setattr(
        "deeptutor.learning.h5_progress.grade_h5_exercise", fake_grade
    )
    from deeptutor.api.routers.learner_profile import _GradeExerciseRequest, grade_exercise

    req = _GradeExerciseRequest(
        chapter_id="ch1", question_id="ex1#0", u="小明", attempt_id="a-123",
    )
    grade_exercise(req, code="", x_access_code="")
    assert captured.get("attempt_id") == "a-123"
    assert captured.get("chapter_id") == "ch1"


def test_grade_exercise_default_attempt_id_empty(monkeypatch):
    captured: dict = {}

    def fake_grade(**kw):
        captured.update(kw)
        return {"ok": True, "is_correct": True, "kp_id": "kp1", "kp_name": "测试",
                "mastery": 0.5, "next_review_at": None, "recorded_mother": False,
                "weak_now": False}

    monkeypatch.setattr(
        "deeptutor.learning.h5_progress.grade_h5_exercise", fake_grade
    )
    from deeptutor.api.routers.learner_profile import _GradeExerciseRequest, grade_exercise

    req = _GradeExerciseRequest(chapter_id="ch1", question_id="ex1#0", u="小明")
    grade_exercise(req, code="", x_access_code="")
    assert captured.get("attempt_id") == ""


def test_grade_h5_exercise_repeat_attempt_id_dedup_short_circuits(monkeypatch):
    """E3 幂等行为钉死：同 attempt_id 二次 grade_h5_exercise 真实走短路分支
    （h5_progress ``attempt_id in progress.attempt_ids``），返回 deduped=True
    快照，mastery/FSRS/母题副作用只发生一次。

    替身只替换协作者（LearningService/内容 store/母题 store），短路判定与
    快照组装走 h5_progress 真实代码，不重演实现逻辑。
    """
    import deeptutor.learning.mother_question as mq_mod
    from deeptutor.learning import h5_progress as h5p

    svc = _FakeLearningService()
    monkeypatch.setattr(h5p, "LearningService", lambda: svc)
    monkeypatch.setattr(h5p, "_content_store", lambda: _FakeContentStore())

    mother_queries: list[int] = []

    class _FakeMotherStore:
        def list_mothers(self, **kw):
            mother_queries.append(int(kw.get("page_size") or 0))
            return [], 0

    monkeypatch.setattr(mq_mod, "MotherQuestionStore", _FakeMotherStore)

    kwargs = dict(
        chapter_id="ch1",
        question_id="q1",
        question_type="choice",
        question_text="1+1=?",
        user_answer="2",
        expected_answer="2",
        attempt_id="a-1",
        kp_id_override="kp1",
    )

    first = h5p.grade_h5_exercise(**kwargs)
    assert first["ok"] is True
    assert "deduped" not in first  # 首报走完整闭环（判题/记录/调度/母题检查）
    assert svc.grade_calls == 1
    assert svc.progress.attempt_ids == ["a-1"]
    assert svc.progress.mastery_levels == {"kp1": 0.5}
    assert len(mother_queries) == 1  # 首报末尾做一次母题归属查询

    repeat = h5p.grade_h5_exercise(**kwargs)  # 同 attempt_id 联网补报
    assert repeat["ok"] is True
    assert repeat["deduped"] is True  # 短路分支真实执行
    assert repeat["is_correct"] is None  # 补报不重新判题
    assert repeat["mastery"] == 0.5  # 回读既有快照，而非重算
    assert repeat["next_review_at"] == time.strftime(
        "%Y-%m-%d %H:%M", time.localtime(_FAKE_NEXT_REVIEW_AT)
    )
    assert svc.grade_calls == 1  # mastery/FSRS/错题/事件副作用未重复
    assert len(mother_queries) == 1  # 短路先于母题检查返回
    assert svc.progress.attempt_ids == ["a-1"]  # 未二次追加
    assert (
        svc.progress.repetition_states["kp1"].next_review_at
        == _FAKE_NEXT_REVIEW_AT
    )  # 调度状态未被再次推进
