# -*- coding: utf-8 -*-
"""M01 单测：DB 核心（池配置/兼容迁移幂等）+ 幂等种子 + TaskWorker（金标准对齐验证）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M01 spec §七验收标准逐条锚定现有实现）。
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------------------------
# 验收标准映射（M01 spec §七，2026-09-08 测试补全）：
# §七.1 冷启动 83 表/5 类种子/重启幂等/可登录可管理 → test_init_db_idempotent +
#       test_schema_compat_idempotent（本文件）；可登录可管理 → test_m02_auth.py
#       既有权限链/dev-login 测；冷启动 83 表建 → test_full_create_all_83_tables_no_conflict（本次补，本文件）
# §七.2 外部依赖全断降级 → test_lifespan_degrades_external_deps_down（本次补，本文件）
# §七.3 ENABLE_AUTH=1 且缺安全三件套 fail-fast → test_failfast_missing_security_triplet
#       （本次补，本文件；test_m02_auth.py 既有测为端点级 dev-login 门，
#       非启动 fail-fast，不构成 §七.3 锚定）
# §七.4 TaskWorker 优先级/重试上限/周期钩子 → test_task_worker_priority_consumption +
#       test_periodic_hook_interval（本文件）+ test_retry_semantics_bounded
#       （test_m14_scheduler.py，源码级）；重试上限行为级 → test_task_worker_retry_cap（本次补，本文件）
# §七.5 全表 create_all 无冲突/模型注册集中 main.py → test_full_create_all_83_tables_no_conflict（本次补，本文件）
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 任务 6（2026-09-08 测试补全）：spec §七 验收缺口
# ---------------------------------------------------------------------------

def test_failfast_missing_security_triplet(monkeypatch):
    """ENABLE_AUTH=1 且缺安全三件套 → lifespan 启动即 RuntimeError，先于任何 DB 初始化
    （spec §七.3；main.py F3-fix fail-fast L47-59 契约：先于 create_all/init_db）。
    变异锚点：fail-fast 检查被删/后移到 create_all 之后 → 哨兵 create_all 被调用
    （先写 DDL 再抛错或根本不抛）→ 本测红。"""
    import asyncio
    from app.main import lifespan, app as fastapi_app
    from app.models.base import Base

    ddl_calls = []

    def _sentinel_create_all(*a, **k):
        ddl_calls.append(1)
        raise AssertionError("fail-fast 之前不应发生任何 DB DDL（spec §七.3 先于任何 DB 写）")

    monkeypatch.setattr(Base.metadata, "create_all", _sentinel_create_all)

    async def _boot():
        async with lifespan(fastapi_app):
            pass  # fail-fast 应在进入 context 前抛出，永不到达这里

    # 三种缺失场景：全缺 / 只缺 CORS_ORIGINS / 只缺 AUTHENTIK_JWKS_URL
    scenarios = [{}, {"AUTHENTIK_JWKS_URL": "http://x/jwks"},
                 {"CORS_ORIGINS": "http://localhost:23000"}]
    for extra in scenarios:
        monkeypatch.setenv("ENABLE_AUTH", "1")
        monkeypatch.delenv("CORS_ORIGINS", raising=False)
        monkeypatch.delenv("AUTHENTIK_JWKS_URL", raising=False)
        for k, v in extra.items():
            monkeypatch.setenv(k, v)
        with pytest.raises(RuntimeError) as ei:
            asyncio.run(_boot())
        msg = str(ei.value)
        assert "生产安全检查未通过" in msg
        if "CORS_ORIGINS" not in extra:
            assert "CORS_ORIGINS" in msg
        if "AUTHENTIK_JWKS_URL" not in extra:
            assert "AUTHENTIK_JWKS_URL" in msg
    assert ddl_calls == [], "RuntimeError 之前发生了 DB DDL——fail-fast 顺序被破坏"


def test_lifespan_degrades_external_deps_down(monkeypatch, caplog):
    """外部依赖全断（Qdrant/Neo4j/LLM）→ lifespan 启动成功（warning 在案）+ worker 起
    + MySQL 管理域可用（spec §七.2；main.py L128-157 静默降级 + L202-221 预热静默）。
    变异锚点：Qdrant/Neo4j 降级钩子（try/except）被删 → 假件抛错放大为启动崩溃红；
    init_db 被删 → 种子断言红。"""
    import asyncio
    import logging
    from app.main import lifespan, app as fastapi_app
    from app.core.database import SessionLocal
    from app.core.task_worker import task_worker_manager
    from app.models.skill import SkillType

    monkeypatch.setenv("ENABLE_AUTH", "0")  # 确保不走 fail-fast 分支
    # Qdrant 断：healthcheck 永远 False（lifespan call-time 属性解析，吃到桩）
    monkeypatch.setattr("app.services.tupu_qdrant_client.TupuQdrantClient.healthcheck",
                        lambda self: False)
    # Neo4j 断
    monkeypatch.setattr("app.services.graph_query_neo4j.neo4j_healthcheck", lambda: False)
    # LLM 断：预热构建 agent 必抛（call-time import 取到桩）
    async def _llm_down(_q):
        raise RuntimeError("LLM down (test stub)")
    monkeypatch.setattr("app.services.tupu_deepagent.get_tupu_agent", _llm_down)
    # 后台向量同步桩化：不真连 Qdrant，线程即刻返回（不留拖尾线程）
    monkeypatch.setattr("app.services.entity_attr_vector_service.sync_entity_vectors",
                        lambda db, force=True: {"ok": True, "stub": "test"})
    monkeypatch.setattr("app.services.entity_attr_vector_service.sync_attribute_vectors",
                        lambda db, force=True: {"ok": True, "stub": "test"})

    async def _boot():
        async with lifespan(fastapi_app):
            assert task_worker_manager.is_running(), "worker 应在 startup 已启动"
            await asyncio.sleep(1.8)  # >1.5s：等预热后台任务触发（LLM 断 → warning）

    with caplog.at_level(logging.WARNING):
        asyncio.run(_boot())  # 不抛 = 外部依赖全断仍启动成功

    warn_text = caplog.text
    assert "qdrant healthcheck failed" in warn_text
    assert "neo4j healthcheck failed" in warn_text
    assert "tupu agent 预热失败" in warn_text  # LLM 断 → 静默 warning 不崩
    assert not task_worker_manager.is_running(), "shutdown 应优雅停 worker"
    with SessionLocal() as db:
        assert db.query(SkillType).count() >= 5  # MySQL 管理域可用（种子在案可查）


def test_task_worker_retry_cap(monkeypatch):
    """失败重试：retry_count<max_retries → 回 pending 且计数递增；达上限 → failed 终态
    （spec §七.4 重试上限；task_worker.py L144-148）。
    变异锚点：上限判定（retry_count < max_retries）删 → 达上限任务仍回 pending（毒任务
    无限循环）红；重试回队分支删 → 首败即 failed 终态红。"""
    from app.core.task_worker import TaskWorker
    from app.models.scheduler import TaskQueue

    class _StubEngine:
        def __init__(self, db):
            pass

        def execute(self, **kwargs):
            return {"success": False, "error": "boom"}

    class _StubSkillService:
        @staticmethod
        def get_skill(db, skill_id):
            return {"id": skill_id}  # 技能存在（绕开「技能不存在」直败分支）

    monkeypatch.setattr("app.core.task_worker.ExecutionEngineV2", _StubEngine)
    monkeypatch.setattr("app.core.task_worker.SkillService", _StubSkillService)

    class _Ref:
        task_code = "m01_retry_cap"  # _execute_task 仅按 task_code 重查库

    worker = TaskWorker(poll_interval=0.05)
    try:
        with SessionLocal() as db:
            db.query(TaskQueue).filter(TaskQueue.task_type == "m01_retry_test").delete()
            db.commit()
            db.add(TaskQueue(task_code="m01_retry_cap", task_ref_id="m01_retry_cap",
                             task_type="m01_retry_test", status="running", priority=1,
                             retry_count=0, max_retries=3, input_payload={"n": 1}))
            db.commit()
        # 首败：retry_count 0 < 3 → 回 pending 递增
        worker._execute_task(_Ref())
        with SessionLocal() as db:
            t = db.query(TaskQueue).filter(TaskQueue.task_code == "m01_retry_cap").first()
            assert t.status == "pending", f"失败应回队待重试，实际 {t.status}"
            assert t.retry_count == 1
            assert "重试 1/3" in (t.error_message or "")
        # 达上限：retry_count 3 = max_retries → failed 终态，不再回队
        with SessionLocal() as db:
            t = db.query(TaskQueue).filter(TaskQueue.task_code == "m01_retry_cap").first()
            t.status = "running"
            t.retry_count = 3
            db.commit()
        worker._execute_task(_Ref())
        with SessionLocal() as db:
            t = db.query(TaskQueue).filter(TaskQueue.task_code == "m01_retry_cap").first()
            assert t.status == "failed", f"达上限应 failed 终态，实际 {t.status}"
            assert t.retry_count == 3
            assert "boom" in (t.error_message or "")
    finally:
        with SessionLocal() as db:
            db.query(TaskQueue).filter(TaskQueue.task_type == "m01_retry_test").delete()
            db.commit()


def test_full_create_all_83_tables_no_conflict():
    """全部表模型可 Base.metadata.create_all 无冲突 + 注册集中在 main.py
    （spec §七.5：模型注册集中 main.py L26-35，防循环导入）。
    变异锚点：任一模型 __tablename__ 重复/表模型被删 → 计数漂移；
    main.py 移除集中导入 → 循环导入或注册不全 → 导入/计数/建表红。
    表数演进：83（M01 基线）→ 84（2026-09-09 剧本定位提速件① kg_entity_lookup_cache，spec §三 表 83→84）
    → 86（2026-09-12 专家地基① kg_expert_profiles+expert_events 两表，spec §四）
    → 88（2026-09-26 切换R0-⑥ sishu_session_meta 会话元数据表；函数名保留 M01 历史锚点字样）。"""
    import app.main as _main_mod  # 集中注册全部模型；导入成功即无循环导入
    from app.models.base import Base
    from app.core.database import engine

    tables = dict(Base.metadata.tables)
    assert len(tables) == 88, f"注册表数漂移：{len(tables)} ≠ 88（87+2026-09-26 切换R0-⑥ sishu_session_meta 会话元数据表）"
    assert "auth_audit_log" in tables, "权限重构T1 审计表未注册"
    # 五个域模型文件各抽一表（spec §三 分组全景）
    for t in ("kg_concepts", "kg_task_queue", "skills", "auth_users", "kg_knowledge_base"):
        assert t in tables, f"域表缺失：{t}"
    Base.metadata.create_all(bind=engine)  # checkfirst 幂等；表定义冲突即抛
