"""
[sishu port] 批16deep 机械复制自 vendor deeptutor（1:1 语义，仅 import 改写）——vendor 物理删除段前置。
"""

from __future__ import annotations

import types
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from app.services.sishu_full.api.routers import learner_profile as lp
from app.services.sishu_full.services.memory import trace as trace_mod


@dataclass
class _Ev:
    ts: str
    kind: str
    payload: dict

    # 兼容 TraceEvent 的属性访问
    @property
    def id(self) -> str:
        return "x"


def _iso(offset_days: int) -> str:
    return (
        datetime(2026, 8, 17, 10, 0, 0, tzinfo=timezone.utc) + timedelta(days=offset_days)
    ).isoformat()


def _mk_events() -> list[_Ev]:
    """周一(8/17)为周首；周一 3 题、周三 2 题，跨 2 个 kp；另有上周事件与本周新增错题/复习。"""
    return [
        # 上周（周首前）· kp_a 已有 mastery
        _Ev(_iso(-2), "quiz_attempt", {"kp_id": "kp_a", "kp_name": "A", "is_correct": True, "mastery_after": 0.5}),
        # 本周一 · kp_a 一错一队（0.5 -> 0.8）
        _Ev(_iso(0), "quiz_attempt", {"kp_id": "kp_a", "kp_name": "A", "is_correct": False, "error_type": "计算错误", "mastery_after": 0.3}),
        _Ev(_iso(0), "quiz_attempt", {"kp_id": "kp_a", "kp_name": "A", "is_correct": True, "mastery_after": 0.8}),
        # 本周一 · kp_b 首次出现（new kp）
        _Ev(_iso(0), "quiz_attempt", {"kp_id": "kp_b", "kp_name": "B", "is_correct": True, "mastery_after": 0.5}),
        # 本周三 · kp_b 再答对
        _Ev(_iso(2), "quiz_attempt", {"kp_id": "kp_b", "kp_name": "B", "is_correct": True, "error_type": "审题", "mastery_after": 0.8}),
        # 本周三 · 新增错题 + 完成复习
        _Ev(_iso(2), "mother_created", {"mid": "m1", "title": "t", "kp_id": "kp_b", "source": "auto"}),
        _Ev(_iso(2), "review_completed", {"mid": "m1", "is_correct": True}),
        # 下周（周尾后）· 不属于本周
        _Ev(_iso(9), "quiz_attempt", {"kp_id": "kp_a", "is_correct": True, "mastery_after": 1.0}),
    ]


def test_weekly_digest_aggregation(monkeypatch):
    events = _mk_events()
    monkeypatch.setattr(trace_mod, "iter_since", lambda *a, **k: iter(events))

    out = lp.weekly_digest(week_start="2026-08-17", _user=None)

    assert out["attempts"] == 4  # 本周 4 次 quiz_attempt（上周/下周不算）
    assert out["accuracy"] == 0.75  # 3/4 对
    assert out["kps_touched"] == 2
    assert out["mothers_added"] == 1
    assert out["reviews_done"] == 1
    # 错因分布：本周 error_type 计算错误(1) + 审题(1)
    assert out["error_types"] == {"计算错误": 1, "审题": 1}

    # 新学 kp：kp_b 本周首次出现
    new_ids = {k["kp_id"] for k in out["new_kps"]}
    assert new_ids == {"kp_b"}

    # 掌握度增量：kp_a before=0.5 after=0.8 delta=0.3；kp_b before=None after=0.8
    delta_map = {d["kp_id"]: d for d in out["mastery_delta"]}
    assert delta_map["kp_a"]["before"] == 0.5
    assert delta_map["kp_a"]["after"] == 0.8
    assert abs(delta_map["kp_a"]["delta"] - 0.3) < 1e-6
    assert delta_map["kp_b"]["before"] is None
    assert delta_map["kp_b"]["after"] == 0.8

    # top_improved 按 delta 排序首位是 kp_a
    assert out["top_improved"][0]["kp_id"] == "kp_a"


def test_weekly_digest_default_week_start(monkeypatch):
    """week_start 缺省时取本周一，不抛错且返回合法结构。"""
    monkeypatch.setattr(trace_mod, "iter_since", lambda *a, **k: iter([]))
    out = lp.weekly_digest(week_start="", _user=None)
    assert out["attempts"] == 0
    assert out["accuracy"] is None
    assert out["new_kps"] == []
    assert out["top_improved"] == []


# ── 成长叙事三层画像（L1 事件 → L2 章节/学科 → L3 全科）──────────────────
#
# 任务 5.2 表征断言：weekly_digest 之外，learner_profile 的确定性三层
# 画像写入链需逐层钉死 —— 全部离线（tmp_path 隔离，不触真实 memory）。


class TestThreeLayerProfileNarrative:
    @pytest.fixture
    def isolated(self, tmp_path, monkeypatch):
        """隔离 workspace / L1 trace / L2 L3 写入目标到 tmp。"""
        from app.services.sishu_full.learning import learner_profile as profile_mod
        from app.services.sishu_full.services.memory import paths as paths_mod

        workspace = tmp_path / "ws"
        trace_root = tmp_path / "trace"
        l2_target = tmp_path / "l2" / "learning.md"
        l3_target = tmp_path / "l3" / "learning_profile.md"

        monkeypatch.setattr(profile_mod, "_workspace", lambda: workspace)
        monkeypatch.setattr(paths_mod, "trace_dir", lambda surface: trace_root)
        monkeypatch.setattr(paths_mod, "l2_file", lambda surface: l2_target)
        monkeypatch.setattr(paths_mod, "l3_file", lambda slot: l3_target)
        # emit_learning_event -> trace.append 用 trace 模块命名空间的 trace_file
        monkeypatch.setattr(trace_mod, "trace_file", lambda surface, day: trace_root / f"{day.isoformat()}.jsonl")
        monkeypatch.setattr(trace_mod, "_locks", {})
        return types.SimpleNamespace(
            workspace=workspace, trace_root=trace_root, l2_target=l2_target, l3_target=l3_target
        )

    @staticmethod
    def _write_plan(workspace, plan: dict) -> None:
        import json

        d = workspace / "learning"
        d.mkdir(parents=True, exist_ok=True)
        (d / "plan1.json").write_text(json.dumps(plan, ensure_ascii=False), encoding="utf-8")

    def test_build_profile_classifies_weak_strong_due(self, isolated):
        """三层画像的输入侧：plan + mother 聚合出 weak/strong/due 分类。"""
        import json
        import time as _time

        now = _time.time()
        self._write_plan(
            isolated.workspace,
            {
                "modules": [
                    {
                        "knowledge_points": [
                            {"id": "kp_weak", "name": "一元一次方程", "subject": "math"},
                            {"id": "kp_strong", "name": "正数和负数", "subject": "math"},
                        ]
                    }
                ],
                "mastery_levels": {"kp_weak": 0.3, "kp_strong": 0.95},
                "quiz_attempts": [
                    {"knowledge_point_id": "kp_weak", "is_correct": False},
                    {"knowledge_point_id": "kp_strong", "is_correct": True},
                ],
                "updated_at": now,
            },
        )
        mother_dir = isolated.workspace / "mother_questions"
        mother_dir.mkdir(parents=True, exist_ok=True)
        (mother_dir / "index.json").write_text(
            json.dumps(
                [{"id": "m1", "title": "移项错题", "subject": "math", "knowledge_point_id": "kp_due", "mastery_status": "not_mastered"}],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (mother_dir / "review_states.json").write_text(
            json.dumps({"m1": {"stability": 2.0, "reps": 3, "due": now - 10, "last_review": now - 100}}, ensure_ascii=False),
            encoding="utf-8",
        )

        profile = lp.build_learner_profile()

        assert profile.weak_points == ["kp_weak"]
        assert profile.strong_points == ["kp_strong"]
        assert profile.kp_mastery["kp_weak"].status == "weak"
        assert profile.kp_mastery["kp_strong"].status == "mastered"
        due_ids = {r["kp_id"] for r in profile.due_reviews}
        assert "kp_due" in due_ids

    def test_l3_profile_md_renders_subjects_weak_and_rhythm(self, isolated):
        """L3 全科层：确定性 learning_profile.md 渲染 + 落盘。"""
        from app.services.sishu_full.learning.learner_profile import KpMastery, LearnerProfile, write_learning_profile_md

        profile = LearnerProfile(
            kp_mastery={
                "k1": KpMastery(kp_id="k1", kp_name="一元一次方程", subject="math", mastery=0.3, attempts=4, correct_rate=0.25, status="weak", error_types=["计算错误"]),
                "k2": KpMastery(kp_id="k2", kp_name="正数和负数", subject="chinese", mastery=0.95, attempts=2, correct_rate=1.0, status="mastered"),
            },
            weak_points=["k1"],
            streak_days=3,
            total_study_minutes=42.0,
        )
        md = write_learning_profile_md(profile)

        assert isolated.l3_target.exists()
        assert "# 学情画像 Learning Profile" in md
        assert "## 掌握度概览" in md
        assert "## 数学" in md and "## 语文" in md  # L3 = 全科
        assert "一元一次方程" in md and "30% 掌握" in md
        assert "## 薄弱点（需重点练习）" in md
        assert "计算错误" in md
        assert "连续学习：3 天" in md

    def test_l2_learning_md_renders_per_subject_digest(self, isolated):
        """L2 层：按学科摘要 learning.md（章节/学科层）+ 落盘。"""
        from app.services.sishu_full.learning.learner_profile import KpMastery, LearnerProfile, write_learning_l2_md

        profile = LearnerProfile(
            kp_mastery={
                "k1": KpMastery(kp_id="k1", kp_name="去分母", subject="math", mastery=0.2, status="weak"),
                "k2": KpMastery(kp_id="k2", kp_name="移项", subject="math", mastery=0.7, status="learning"),
            },
            weak_points=["k1"],
        )
        md = write_learning_l2_md(profile)

        assert isolated.l2_target.exists()
        assert "# 学习摘要 Learning Summary" in md
        assert "## 数学" in md
        assert "知识点：2 个（已掌握 0 / 学习中 1 / 薄弱 1）" in md
        assert "薄弱点：去分母" in md

    def test_empty_profile_renders_placeholder(self, isolated):
        """空画像：L2/L3 均渲染占位文案（成长叙事的起点态）。"""
        from app.services.sishu_full.learning.learner_profile import LearnerProfile, write_learning_l2_md, write_learning_profile_md

        empty = LearnerProfile()
        md3 = write_learning_profile_md(empty)
        md2 = write_learning_l2_md(empty)
        assert "（暂无学习数据" in md3
        assert "（暂无学习数据" in md2

    def test_l1_event_feeds_profile_rhythm_then_layers(self, isolated):
        """L1 事件 → 画像节奏（streak/时长）→ L2/L3 落盘 全链路。"""
        import json

        from app.services.sishu_full.learning import learner_profile as profile_mod

        # 前置：workspace 有一个已掌握 kp（L3 掌握度来源）
        self._write_plan(
            isolated.workspace,
            {
                "modules": [{"knowledge_points": [{"id": "kp1", "name": "有理数", "subject": "math"}]}],
                "mastery_levels": {"kp1": 0.9},
                "quiz_attempts": [],
                "updated_at": 0,
            },
        )

        # L1：emit 一条 quiz_attempt 事件（同步上下文走 asyncio.run 路径）
        profile_mod.emit_learning_event(kind="quiz_attempt", payload={"kp_id": "kp1", "is_correct": True})
        # emit 内部 asyncio.run 已完成写入（同步路径无并发调度）
        files = list(isolated.trace_root.glob("*.jsonl"))
        assert files, "L1 事件应真实落到 trace 目录"
        event_line = json.loads(files[0].read_text(encoding="utf-8").splitlines()[0])
        assert event_line["kind"] == "quiz_attempt"
        assert event_line["surface"] == "learning"

        profile = lp.build_learner_profile()
        assert profile.total_study_minutes == 3.0  # 每次答题估算 3 分钟
        # 事件文件以 UTC 日期命名；本地时区下「今天有学」或「昨天有学」
        # 宽限逻辑（compute_streak_days）均计 streak=1（东八区恒成立）
        assert profile.streak_days == 1

        md3 = profile_mod.write_learning_profile_md(profile)
        md2 = profile_mod.write_learning_l2_md(profile)
        assert isolated.l3_target.exists() and isolated.l2_target.exists()
        assert "有理数" in md3 and "90% 掌握" in md3
        assert "## 数学" in md2
