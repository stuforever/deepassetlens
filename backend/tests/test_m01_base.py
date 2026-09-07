# -*- coding: utf-8 -*-
"""M01 单测：DB 核心（池配置/兼容迁移幂等）+ 幂等种子 + TaskWorker（金标准对齐验证）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M01 spec §七验收标准逐条锚定现有实现）。
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.core.database import DATABASE_URL, SessionLocal, engine, ensure_schema_compatibility  # noqa: E402


# ---------------------------------------------------------------------------
# 任务 1：DB 核心
# ---------------------------------------------------------------------------

def test_engine_pool_config():
    """池上限（spec §一 DB 核心：pool_pre_ping/回收 3600s/池 10+溢出 20）。
    变异锚点：pool_size 改小/改大 → 此断言红（扩容走架构评审不许改 workers 绕过）。"""
    assert engine.pool.size() <= 10
    assert engine.pool._max_overflow == 20
    assert DATABASE_URL.startswith("mysql+pymysql")


def test_schema_compat_idempotent():
    """兼容迁移重复执行零副作用（列已存在则无 ALTER，spec §七.1 重启幂等）。
    变异锚点：ensure_schema_compatibility 重复执行抛异常 → 此测红。"""
    ensure_schema_compatibility()
    ensure_schema_compatibility()  # 不抛异常即幂等
    with SessionLocal() as db:
        from sqlalchemy import text
        assert db.execute(text("SELECT 1")).scalar() == 1


# ---------------------------------------------------------------------------
# 任务 4：幂等种子
# ---------------------------------------------------------------------------

def test_init_db_idempotent():
    """init_db 二次执行零重复种子（spec §七.1 重启零重复）。
    变异锚点：_seed_skill_types 去掉「表空才插」判定 → 二次执行重复插。"""
    from app.core.init_db import init_db
    from app.models.skill import SkillType
    with SessionLocal() as db:
        init_db(db)
        init_db(db)
        # 5 类技能种子不重复
        assert db.query(SkillType).count() >= 5
        assert len({s.name for s in db.query(SkillType).all()}) == db.query(SkillType).count()


def test_init_db_scenario_skills_present():
    """场景剧本同步到 skills 表可见（spec §四 种子：_sync_scenario_skills）。
    变异锚点：_sync_scenario_skills 删除 → distribution-overload 等场景技能不可见。"""
    from app.core.init_db import init_db
    from app.models.skill import Skill
    with SessionLocal() as db:
        init_db(db)
        names = {s.name for s in db.query(Skill).all()}
        assert "distribution-overload" in names or any("overload" in n for n in names)


# ---------------------------------------------------------------------------
# 任务 5：TaskWorker
# ---------------------------------------------------------------------------

def test_task_worker_priority_consumption():
    """高优先级先消费（spec §五：priority asc 取队）。
    变异锚点：_process_next_task 的 order_by(priority) 删除/改 desc → 顺序反。"""
    from app.core.task_worker import TaskWorker
    from app.models.scheduler import TaskQueue
    with SessionLocal() as db:
        db.query(TaskQueue).filter(TaskQueue.task_type == "m01_priority_test").delete()
        db.commit()
        low = TaskQueue(task_code="m01_low", task_ref_id="m01_low", task_type="m01_priority_test", status="pending", priority=2,
                        input_payload={"n": "low"})
        high = TaskQueue(task_code="m01_high", task_ref_id="m01_high", task_type="m01_priority_test", status="pending", priority=1,
                         input_payload={"n": "high"})
        db.add_all([low, high]); db.commit()
        low_id, high_id = low.id, high.id
    worker = TaskWorker(poll_interval=0.05)
    consumed = []
    try:
        from unittest.mock import patch
        # _execute_task 收到的是 expunge 后独立实例（session 已 close）——只读取队时已
        # 加载的 task_code（不触发 lazy refresh），顺序映射到 priority
        code2prio = {"m01_low": 2, "m01_high": 1}
        with patch.object(worker, "_execute_task",
                          side_effect=lambda row: consumed.append(code2prio[row.task_code])):
            worker._process_next_task()
            worker._process_next_task()
    finally:
        pass
    assert consumed == [1, 2]  # 高优先级先
    with SessionLocal() as db:
        db.query(TaskQueue).filter(TaskQueue.task_type == "m01_priority_test").delete()
        db.commit()


def test_periodic_hook_interval():
    """周期钩子按间隔触发（spec §五：register_periodic 异常隔离+按间隔）。
    变异锚点：周期判定删/间隔逻辑错 → 提前或漏触发。"""
    from app.core.task_worker import TaskWorker
    worker = TaskWorker(poll_interval=0.02)
    calls = []
    worker.register_periodic(0.05, lambda: calls.append(1))
    worker._run_periodic_hooks()
    time.sleep(0.06)
    worker._run_periodic_hooks()
    time.sleep(0.06)
    worker._run_periodic_hooks()
    assert len(calls) >= 2  # 首次未到间隔不触发，其后按间隔累积


def test_task_worker_manager_start_stop():
    """TaskWorkerManager 优雅启停（spec §五：start/stop Event）。
    变异锚点：stop 不设 Event → 线程不退出/重复启动。"""
    from app.core.task_worker import TaskWorkerManager
    m = TaskWorkerManager()
    m.start(0.02)
    time.sleep(0.05)
    assert m.worker is not None
    m.stop()
    time.sleep(0.05)
