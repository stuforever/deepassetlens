"""
技能管理 API (v2) -- 执行/调试/任务/工具子模块
资源导向设计：/skills/glm-5.3_common/executions
从 v2_skills.py 机械拆分（零行为变更）：执行记录、调试会话、异步任务、Worker、Tool Calling。
路由由 v2_skills.router 聚合挂载（prefix 由 main.py 的 include_router 提供）。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import uuid

from app.core.database import get_db
from app.core.execution_engine import ExecutionEngineV2
from app.models.skill import Skill
from app.services.skill_manager import SkillService, VersionService, ExecutionService

from .skill_v2_support import (
    _sid,
    ExecutionCreateRequest, TaskSubmitRequest, APIResponse,
    _get_api_catalog_readmes, _build_dynamic_service_ref_readme,
    _build_workflow_skill_api_relations,
)


router = APIRouter()

# ============== Execution 执行 API (资源导向) ==============

@router.post("/skills/{skill_id}/executions", summary="创建执行（使用当前激活版本）")
def create_execution(skill_id: str, request: ExecutionCreateRequest, db: Session = Depends(get_db)):
    """创建执行记录并启动执行"""
    skill = SkillService.get_skill(db, _sid(skill_id))
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    # 确定使用哪个版本
    version_id = None
    if request.version:
        versions = VersionService.list_versions(db, _sid(skill_id))
        v = next((x for x in versions if x.version == request.version and x.status == "active"), None)
        if not v:
            raise HTTPException(status_code=400, detail=f"版本 '{request.version}' 不存在或未激活")
        version_id = v.version_id
    else:
        if skill.current_version_id:
            version_id = skill.current_version_id
        else:
            raise HTTPException(status_code=400, detail="技能没有激活的版本")

    # 使用执行引擎执行
    engine = ExecutionEngineV2(db)
    result = engine.execute(
        skill_id=_sid(skill_id),
        input_payload=request.input_payload,
        version_id=version_id,
        created_via="manual"
    )

    return APIResponse(
        success=result.get("success", False),
        data={
            "execution_code": result.get("execution_code"),
            "status": "success" if result.get("success") else "failed",
            "output": result.get("output"),
            "duration_ms": result.get("duration_ms"),
            "logs": result.get("logs", []),
        },
        error=result.get("error")
    )


def _execute_skill_sync(skill_id: str, version_id: str, input_payload: dict, db_session_factory) -> dict:
    """在线程中执行技能（用于后台任务）"""
    db = db_session_factory()
    try:
        engine = ExecutionEngineV2(db)
        return engine.execute(
            skill_id=skill_id,
            input_payload=input_payload,
            version_id=version_id,
            created_via="manual"
        )
    finally:
        db.close()


@router.post("/skills/{skill_id}/executions/async", summary="异步创建执行（后台运行）")
def create_execution_async(
    skill_id: str,
    request: ExecutionCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """异步执行：立即返回 execution_code，后台执行技能"""
    skill = SkillService.get_skill(db, _sid(skill_id))
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    version_id = None
    if request.version:
        versions = VersionService.list_versions(db, _sid(skill_id))
        v = next((x for x in versions if x.version == request.version and x.status == "active"), None)
        if not v:
            raise HTTPException(status_code=400, detail=f"版本 '{request.version}' 不存在或未激活")
        version_id = v.version_id
    else:
        version_id = skill.current_version_id
        if not version_id:
            raise HTTPException(status_code=400, detail="技能没有激活的版本")

    # 创建执行记录（状态为 running）
    log = ExecutionService.create_execution(
        db, _sid(skill_id), version_id, request.input_payload, "manual"
    )
    db.commit()

    # 后台执行
    from app.core.database import SessionLocal
    background_tasks.add_task(
        _execute_skill_sync,
        _sid(skill_id),
        version_id,
        request.input_payload,
        SessionLocal
    )

    return APIResponse(data={
        "execution_code": log.execution_code,
        "status": "running",
        "message": "任务已提交到后台执行"
    })


@router.get("/skills/{skill_id}/executions", summary="获取技能执行历史")
def list_executions(
    skill_id: str,
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    logs = ExecutionService.list_executions(db, _sid(skill_id), status=status, skip=skip, limit=limit)
    return APIResponse(data=[{
        "execution_code": log.execution_code,
        "status": log.status,
        "duration_ms": log.duration_ms,
        "created_via": log.created_via,
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "completed_at": log.completed_at.isoformat() if log.completed_at else None,
    } for log in logs])


@router.get("/skills/executions/{execution_code}", summary="获取执行详情")
def get_execution(execution_code: str, db: Session = Depends(get_db)):
    log = ExecutionService.get_execution(db, execution_code)
    if not log:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    return APIResponse(data={
        "execution_code": log.execution_code,
        "skill_id": str(log.skill_id) if log.skill_id else None,
        "version_id": str(log.version_id) if log.version_id else None,
        "status": log.status,
        "input_data": log.input_data,
        "output_data": log.output_data,
        "error_message": log.error_message,
        "duration_ms": log.duration_ms,
        "created_via": log.created_via,
        "started_at": log.started_at.isoformat() if log.started_at else None,
        "completed_at": log.completed_at.isoformat() if log.completed_at else None,
    })


@router.get("/workflow-skill-api-relations", summary="获取流程-技能-API 只读关系表")
def list_workflow_skill_api_relations(db: Session = Depends(get_db)):
    return APIResponse(data=_build_workflow_skill_api_relations(db))


@router.get("/apis/{api_code}/readme", summary="获取后台 API 只读说明")
def get_api_readme(api_code: str):
    item = _get_api_catalog_readmes().get(api_code) or _build_dynamic_service_ref_readme(api_code)
    if not item:
        raise HTTPException(status_code=404, detail="API说明不存在")
    return APIResponse(data=item)


# ============== Tool Calling API (放在API层，纯读操作) ==============

@router.get("/tools", summary="获取可用工具列表（Tool Calling接口）")
def get_tools(
    skill_type: Optional[str] = None,
    app_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    返回可用工具的 OpenAI-compatible function calling 格式
    供 AI Agent 调用
    """
    query = db.query(Skill).filter(Skill.status == "published")
    if skill_type:
        query = query.filter(Skill.skill_type == skill_type)
    if app_type:
        query = query.filter(Skill.app_type == app_type)

    skills = query.all()
    tools = []
    for skill in skills:
        # 获取当前激活版本的 input_schema
        input_schema = {"type": "object", "properties": {}}
        if skill.current_version_id:
            version = VersionService.get_version(db, skill.current_version_id)
            if version:
                input_schema = version.input_schema or input_schema

        tools.append({
            "type": "function",
            "function": {
                "name": skill.skill_code,
                "description": skill.description or f"执行技能: {skill.name}",
                "parameters": input_schema,
            }
        })

    return APIResponse(data=tools)


# ============== Debug API ==============

class DebugCreateRequest(BaseModel):
    skill_id: str
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    debug_mode: str = "step"
    breakpoints: Optional[List[int]] = None


class DebugStepRequest(BaseModel):
    session_code: str


class DebugBreakpointRequest(BaseModel):
    session_code: str
    line_number: int


@router.post("/debug/sessions", summary="创建调试会话")
def create_debug_session(request: DebugCreateRequest, db: Session = Depends(get_db)):
    from app.services.debug_service import DebugService
    service = DebugService(db)
    try:
        session_code = service.create_session(
            request.skill_id,
            request.input_payload,
            request.debug_mode,
            request.breakpoints or []
        )
        return APIResponse(data={"session_code": session_code})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/debug/sessions/{session_code}/step", summary="单步执行")
def debug_step(session_code: str, db: Session = Depends(get_db)):
    from app.services.debug_service import DebugService
    service = DebugService(db)
    result = service.step(session_code)
    if not result.get("success") and "不存在" in result.get("error", ""):
        raise HTTPException(status_code=404, detail=result["error"])
    return APIResponse(data=result, error=result.get("error") if not result.get("success") else None)


@router.get("/debug/sessions/{session_code}", summary="获取调试会话状态")
def get_debug_session(session_code: str, db: Session = Depends(get_db)):
    from app.services.debug_service import DebugService
    service = DebugService(db)
    session = service.get_session(session_code)
    if not session:
        raise HTTPException(status_code=404, detail="调试会话不存在")
    return APIResponse(data={
        "session_code": session.session_code,
        "status": session.status,
        "current_step": session.current_step,
        "phase": session.execution_state.get("phase") if session.execution_state else None,
        "skill_code": session.skill_code,
        "input_payload": session.input_payload,
        "breakpoints": session.breakpoints,
    })


@router.get("/debug/sessions/{session_code}/variables", summary="获取变量快照")
def get_debug_variables(session_code: str, db: Session = Depends(get_db)):
    from app.services.debug_service import DebugService
    service = DebugService(db)
    result = service.get_variable_snapshot(session_code)
    if "error" in result and "不存在" in result["error"]:
        raise HTTPException(status_code=404, detail=result["error"])
    return APIResponse(data=result)


@router.get("/debug/sessions/{session_code}/logs", summary="获取调试日志")
def get_debug_logs(session_code: str, db: Session = Depends(get_db)):
    from app.services.debug_service import DebugService
    service = DebugService(db)
    logs = service.get_logs(session_code)
    return APIResponse(data=logs)


@router.post("/debug/sessions/{session_code}/breakpoints", summary="设置断点")
def set_breakpoint(session_code: str, request: DebugBreakpointRequest, db: Session = Depends(get_db)):
    from app.services.debug_service import DebugService
    service = DebugService(db)
    success = service.set_breakpoint(session_code, request.line_number)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return APIResponse(data={"message": "断点已设置"})


@router.delete("/debug/sessions/{session_code}/breakpoints/{line_number}", summary="移除断点")
def remove_breakpoint(session_code: str, line_number: int, db: Session = Depends(get_db)):
    from app.services.debug_service import DebugService
    service = DebugService(db)
    success = service.remove_breakpoint(session_code, line_number)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return APIResponse(data={"message": "断点已移除"})


@router.delete("/debug/sessions/{session_code}", summary="终止调试会话")
def terminate_debug_session(session_code: str, db: Session = Depends(get_db)):
    from app.services.debug_service import DebugService
    service = DebugService(db)
    success = service.terminate(session_code)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return APIResponse(data={"message": "会话已终止"})


# ============== Async Task 异步任务 API ==============

@router.post("/tasks", summary="提交异步任务")
def submit_task(request: TaskSubmitRequest, db: Session = Depends(get_db)):
    """提交技能执行到异步任务队列，返回 task_code 用于轮询"""
    from app.services.skill_manager import SkillService
    from app.models.scheduler import TaskQueue
    import uuid

    skill = SkillService.get_skill(db, _sid(request.skill_id))
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    if not skill.current_version_id:
        raise HTTPException(status_code=400, detail="技能没有激活的版本")

    task_code = f"task_{uuid.uuid4().hex[:8]}"
    task = TaskQueue(
        task_code=task_code,
        task_type="skill",
        task_ref_id=_sid(request.skill_id),
        status="pending",
        priority=request.priority,
        input_payload=request.input_payload,
        max_retries=skill.retry_policy.get("max_retries", 0) if skill.retry_policy else 0,
        timeout_seconds=skill.timeout,
    )
    db.add(task)
    db.commit()

    return APIResponse(data={
        "task_code": task_code,
        "status": "pending",
        "message": "任务已提交到队列",
    })


@router.get("/tasks/{task_code}", summary="获取任务状态")
def get_task(task_code: str, db: Session = Depends(get_db)):
    from app.models.scheduler import TaskQueue
    task = db.query(TaskQueue).filter(TaskQueue.task_code == task_code).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return APIResponse(data={
        "task_code": task.task_code,
        "status": task.status,
        "priority": task.priority,
        "input_payload": task.input_payload,
        "output_payload": task.output_payload,
        "error_message": task.error_message,
        "retry_count": task.retry_count,
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    })


@router.post("/tasks/{task_code}/retry", summary="重试失败任务")
def retry_task(task_code: str, db: Session = Depends(get_db)):
    from app.models.scheduler import TaskQueue
    task = db.query(TaskQueue).filter(TaskQueue.task_code == task_code).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.status not in ("failed", "completed"):
        raise HTTPException(status_code=400, detail=f"当前状态 {task.status} 不支持重试")
    if task.retry_count >= task.max_retries:
        raise HTTPException(status_code=400, detail="已达最大重试次数")
    task.status = "pending"
    task.retry_count += 1
    db.commit()
    return APIResponse(data={"task_code": task_code, "status": "pending"})


@router.get("/worker/status", summary="获取 Worker 状态")
def worker_status():
    from app.core.task_worker import task_worker_manager
    return APIResponse(data=task_worker_manager.get_status())


@router.post("/worker/start", summary="启动 Worker")
def worker_start():
    from app.core.task_worker import task_worker_manager
    if task_worker_manager.is_running():
        return APIResponse(data={"message": "Worker 已在运行"})
    task_worker_manager.start(poll_interval=2.0)
    return APIResponse(data={"message": "Worker 已启动"})


@router.post("/worker/stop", summary="停止 Worker")
def worker_stop():
    from app.core.task_worker import task_worker_manager
    task_worker_manager.stop()
    return APIResponse(data={"message": "Worker 已停止"})


# ============== 3.2 risk_level 过滤 + 版本快照 ==============

# 修改 tools 接口：增加 risk_level 过滤
@router.get("/tools/v2", summary="获取可用工具列表（支持 risk_level 过滤）")
def get_tools_v2(
    skill_type: Optional[str] = None,
    risk_level: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Skill).filter(Skill.status == "published")
    if skill_type:
        query = query.filter(Skill.skill_type == skill_type)
    if risk_level:
        query = query.filter(Skill.permissions["risk_level"].as_string() == risk_level)

    skills = query.all()
    tools = []
    for skill in skills:
        input_schema = {"type": "object", "properties": {}}
        if skill.current_version_id:
            version = VersionService.get_version(db, skill.current_version_id)
            if version:
                # 优先从文件系统读取 schema
                from app.core.skill_storage import get_skill_storage
                storage = get_skill_storage()
                fs_schema = storage.get_schema(skill.skill_code, "input")
                input_schema = fs_schema or version.input_schema or input_schema

        tools.append({
            "type": "function",
            "function": {
                "name": skill.skill_code,
                "description": skill.description or f"执行技能: {skill.name}",
                "parameters": input_schema,
            }
        })
    return APIResponse(data=tools)
