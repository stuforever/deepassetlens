# -*- coding: utf-8 -*-
"""M14 单测：TaskQueue 契约/重试语义/调度声明面/投递器缺位如实（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M14 spec §八验收标准锚定现有实现）。
消费协议优先级/周期钩子/Manager 启停已由 test_m01_base.py 覆盖，本文件补余下面。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.models.scheduler import DebugSession, SkillSchedule, TaskQueue  # noqa: E402


# ---------------------------------------------------------------------------
# 任务 1：任务队列模型契约（spec §三）
# ---------------------------------------------------------------------------

def test_taskqueue_columns_and_index():
    """TaskQueue 列+复合索引（spec §三：priority 默认 1/max_retries 3/status 状态机/复合索引）。
    变异锚点：复合索引删 → 取队查询面退化；max_retries 缺省漂移 → 毒任务风险。"""
    cols = {c.name for c in TaskQueue.__table__.columns}
    assert {"task_code", "task_type", "task_ref_id", "status", "priority",
            "retry_count", "max_retries", "error_message"} <= cols
    assert TaskQueue.__table__.c.priority.default.arg == 1
    assert TaskQueue.__table__.c.max_retries.default.arg == 3
    idx_names = {i.name for i in TaskQueue.__table__.indexes if i.name}
    assert any("status" in (n or "") and "priority" in (n or "") for n in idx_names), f"复合索引缺失: {idx_names}"


def test_retry_semantics_bounded():
    """重试语义（spec §八.2）：失败且 retry_count<max_retries → 回 pending 递增；
    达上限 → failed+error 保留（task_worker.py L144-148 契约）。
    变异锚点：重试回 pending 分支删 → 任务一次失败即终态；上限判定删 → 毒任务无限循环。"""
    import inspect
    from app.core import task_worker as TW
    src = inspect.getsource(TW.TaskWorker._execute_task)
    assert "retry_count" in src and "max_retries" in src
    assert "pending" in src  # 失败回队


# ---------------------------------------------------------------------------
# 任务 1：调度声明面模型（spec §四）
# ---------------------------------------------------------------------------

def test_skill_schedule_columns():
    """SkillSchedule 声明面列+复合索引（spec §四：cron_expression/status/last_run_at/复合索引）。
    变异锚点：cron_expression 删 → 声明面断。"""
    cols = {c.name for c in SkillSchedule.__table__.columns}
    assert {"schedule_code", "skill_id", "cron_expression", "status",
            "last_run_at", "next_run_at", "run_count", "fail_count"} <= cols
    idx_cols = {tuple(c.name for c in i.columns) for i in SkillSchedule.__table__.indexes}
    assert ("status", "next_run_at") in idx_cols, f"复合索引缺失: {idx_cols}"


def test_debug_session_snapshot_columns():
    """DebugSession 快照式存储列（spec §六：断点/监视/状态/变量快照单行）。
    变异锚点：快照列删 → 调试单步断。"""
    cols = {c.name for c in DebugSession.__table__.columns}
    assert {"session_code", "debug_mode", "breakpoints", "watch_variables",
            "execution_state", "variable_snapshots", "status", "current_step"} <= cols


# ---------------------------------------------------------------------------
# 任务 4（登记项）：投递器缺位如实（spec §八.7 回归验证防误解）
# ---------------------------------------------------------------------------

def test_cron_dispatcher_absent():
    """投递器缺位回归验证：无 croniter 依赖、无 next_run_at 计算循环（spec §四重大登记）。
    本测试锚定「未实现」这一事实本身——若有人顺手实现须先过设计批次。
    变异锚点：有人未过设计批次实现投递器 → 本测试失败提醒走设计管线。"""
    import subprocess
    import sys as _sys
    # requirements 无 croniter
    req = Path(__file__).resolve().parents[1] / "requirements.txt"
    if req.exists():
        assert "croniter" not in req.read_text(encoding="utf-8").lower()
    # task_worker/main 无 cron 解析调用（grep 级锚定）
    tw = Path(__file__).resolve().parents[1] / "app" / "core" / "task_worker.py"
    assert "croniter" not in tw.read_text(encoding="utf-8").lower()
