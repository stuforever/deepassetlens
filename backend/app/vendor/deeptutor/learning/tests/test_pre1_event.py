"""PRE-1 学习事件异步上下文丢失修复测试。

覆盖：emit_learning_event 在 同步 / 异步 两种调用上下文都真实写入 trace
（修复前异步分支是 `pass`，事件静默丢弃）。trace 文件被重定向到 tmp，
不污染真实 memory 目录。
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest


@pytest.fixture
def fake_trace(tmp_path: Path, monkeypatch):
    """把 trace.trace_file 重定向到 tmp，返回 (tmp_path, learning.jsonl 路径)。"""
    from deeptutor.services.memory import trace as trace_mod

    def _fake_trace_file(surface, date):
        return tmp_path / f"{surface}.jsonl"

    monkeypatch.setattr(trace_mod, "trace_file", _fake_trace_file)
    # 清空 per-surface asyncio 锁，避免跨测试残留绑定旧事件循环的 Lock
    monkeypatch.setattr(trace_mod, "_locks", {})
    return tmp_path


def test_sync_context_emits_event(fake_trace: Path) -> None:
    """同步上下文：asyncio.run 路径应真实写入事件。"""
    from deeptutor.learning import learner_profile

    learner_profile.emit_learning_event(
        kind="grade_exercise", payload={"kp_id": "kp_a", "correct": True}
    )
    content = (fake_trace / "learning.jsonl").read_text(encoding="utf-8")
    assert "grade_exercise" in content
    assert "kp_a" in content


def test_async_context_emits_event(fake_trace: Path) -> None:
    """异步上下文：create_task 调度路径应真实写入事件（PRE-1 修复点）。"""
    from deeptutor.learning import learner_profile

    async def _run() -> None:
        learner_profile.emit_learning_event(
            kind="mastery_grade", payload={"kp_id": "kp_a", "correct": True}
        )
        # 给 fire-and-forget task 留出执行时间
        await asyncio.sleep(0.3)

    asyncio.run(_run())
    content = (fake_trace / "learning.jsonl").read_text(encoding="utf-8")
    assert "mastery_grade" in content
    assert "kp_a" in content


def test_async_context_multiple_events_all_land(fake_trace: Path) -> None:
    """异步上下文连发多条：全部写入且 JSON 每行一条（不互相覆盖）。"""
    from deeptutor.learning import learner_profile

    async def _run() -> None:
        for i in range(5):
            learner_profile.emit_learning_event(
                kind="mastery_grade", payload={"seq": i, "correct": i % 2 == 0}
            )
        await asyncio.sleep(0.4)

    asyncio.run(_run())
    lines = (fake_trace / "learning.jsonl").read_text(encoding="utf-8").splitlines()
    assert len([l for l in lines if l.strip()]) == 5
    assert '"seq":0' in lines[0]
    assert '"seq":4' in lines[4]
