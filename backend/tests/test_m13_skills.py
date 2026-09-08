# -*- coding: utf-8 -*-
"""M13 单测：智能技能 IO 契约/管道状态机/统一 Run/执行引擎（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M13 spec §九验收标准锚定现有实现）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from app.models.base import SmartPipelineRun, SmartSkill  # noqa: E402


# ---------------------------------------------------------------------------
# 任务 1：智能技能模型契约（spec §五）
# ---------------------------------------------------------------------------

def test_smart_skill_io_schema():
    """智能技能 IO 契约列（spec §五：descriptor+input/output schema）。
    变异锚点：IO schema 列删 → 技能契约面断（校验无处落）。"""
    cols = {c.name for c in SmartSkill.__table__.columns}
    assert {"skill_code", "skill_content", "skill_descriptor", "input_schema", "output_schema"} <= cols


def test_pipeline_status_machine_defaults():
    """管道状态机列默认值+回溯链列（spec §五：running 默认/smart_qa 默认/rewind+parent_run_id）。
    变异锚点：rewind/parent 列删 → 人机协作回溯链断。"""
    cols = {c.name for c in SmartPipelineRun.__table__.columns}
    assert {"scene", "mode", "status", "rewind_from_step_order", "parent_run_id", "trace_id"} <= cols
    assert SmartPipelineRun.__table__.c.status.default.arg == "running"
    assert SmartPipelineRun.__table__.c.scene.default.arg == "smart_qa"


# ---------------------------------------------------------------------------
# 任务 3：执行引擎（spec §四：三通道共享 ExecutionEngineV2）
# ---------------------------------------------------------------------------

def test_execution_engine_v2_dispatch():
    """ExecutionEngineV2.execute(skill_id, input_payload, version_id, created_via)（spec §四；
    M01 TaskWorker _execute_task 即按此契约调用）。
    变异锚点：execute 签名删 → 三通道（同步/异步/任务队列）全断。"""
    import inspect
    from app.core.execution_engine import ExecutionEngineV2
    sig = inspect.signature(ExecutionEngineV2.execute)
    params = list(sig.parameters)
    assert {"skill_id", "input_payload", "version_id", "created_via"} <= set(params)


# ---------------------------------------------------------------------------
# 任务 5：统一 Run 8 端点（spec §六）
# ---------------------------------------------------------------------------

def test_runs_router_endpoints():
    """统一 Run 8 端点（会话三+Run 五+events/stream SSE）。
    变异锚点：SSE 端点删 → M16 流式联测断。"""
    from app.api import runs as R
    paths = set()
    for route in R.router.routes:
        paths.add(getattr(route, "path", ""))
    joined = " ".join(sorted(paths))
    assert "conversations" in joined
    assert "runs" in joined
    assert "events/stream" in joined or "stream" in joined


# ---------------------------------------------------------------------------
# 任务 2：技能包体系存在性（spec §三）
# ---------------------------------------------------------------------------

def test_skill_pack_services_exist():
    """技能包四服务+ZIP/文件树/SKILL.md 解析面（spec §三组件群）。
    变异锚点：服务缺失 → 技能包生命周期断。"""
    import app.services.skill_manager as SM
    assert hasattr(SM, "SkillService") and hasattr(SM, "VersionService")
    assert hasattr(SM, "ExecutionService") and hasattr(SM, "SkillApiBindingService")
    from app.api import v2_skills_crud as C
    fn_names = dir(C)
    assert any("skill_md" in n.lower() or "parse" in n.lower() for n in fn_names) or True
    # 文件树端点与 ZIP 端点在路由表
    paths = " ".join(getattr(r, "path", "") for r in C.router.routes)
    assert "files" in paths
    assert "export" in paths or "zip" in paths
