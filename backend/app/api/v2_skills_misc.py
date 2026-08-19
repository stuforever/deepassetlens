"""
技能管理 API (v2) -- 模板/调度/类型/快照/密钥子模块
从 v2_skills.py 机械拆分（零行为变更）：模板、定时调度、技能类型、版本快照归档、密钥柜。
路由由 v2_skills.router 聚合挂载（prefix 由 main.py 的 include_router 提供）。
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.skill_manager import SkillService, VersionService
from app.services.skill_templates import list_templates, get_template, apply_template

from .skill_v2_support import _sid, APIResponse


router = APIRouter()

# ============== Templates 模板 API ==============

@router.get("/templates", summary="获取技能模板列表")
def list_skill_templates():
    return APIResponse(data=list_templates())


@router.get("/templates/{template_id}", summary="获取模板详情")
def get_skill_template(template_id: str):
    tpl = get_template(template_id)
    if not tpl:
        raise HTTPException(status_code=404, detail="模板不存在")
    return APIResponse(data=tpl)


@router.post("/templates/{template_id}/apply", summary="应用模板创建技能")
def apply_skill_template(template_id: str, db: Session = Depends(get_db)):
    try:
        data = apply_template(template_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    skill = SkillService.create_skill(db, {
        "name": data["name"],
        "description": data["description"],
        "skill_type": data["skill_type"],
    })
    version = VersionService.create_version(db, skill.skill_id, {
        "version": "1.0.0",
        "content": data["content"],
        "input_schema": data.get("input_schema"),
        "output_schema": data.get("output_schema"),
    })
    VersionService.publish_version(db, version.version_id, "system")
    db.refresh(skill)
    return APIResponse(data={
        "skill_id": str(skill.skill_id),
        "skill_code": skill.skill_code,
        "message": "技能已根据模板创建并发布"
    })


# ============== Schedule 定时调度 API ==============

class ScheduleCreateRequest(BaseModel):
    skill_id: str
    name: str
    cron_expression: str
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    workspace_id: Optional[str] = None


@router.post("/schedules", summary="创建定时调度")
def create_schedule(request: ScheduleCreateRequest, db: Session = Depends(get_db)):
    from app.models.scheduler import SkillSchedule
    import uuid as uuid_mod

    skill = SkillService.get_skill(db, _sid(request.skill_id))
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    # 熔断检查：不允许为已下线技能创建调度
    if skill.status == "archived":
        raise HTTPException(status_code=400, detail="技能已下线，不可创建定时调度")

    schedule_code = f"sch_{uuid_mod.uuid4().hex[:8]}"

    # 计算下次运行时间（简化：用 cron_descriptor 解析）
    try:
        from cron_descriptor import get_description
        cron_desc = get_description(request.cron_expression)
    except ImportError:
        cron_desc = request.cron_expression

    schedule = SkillSchedule(
        schedule_code=schedule_code,
        skill_id=_sid(request.skill_id),
        skill_code=skill.skill_code,
        name=request.name,
        cron_expression=request.cron_expression,
        input_payload=request.input_payload,
        status="active",
        workspace_id=_sid(request.workspace_id) if request.workspace_id else None,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return APIResponse(data={
        "schedule_code": schedule.schedule_code,
        "name": schedule.name,
        "cron_expression": schedule.cron_expression,
        "cron_description": cron_desc,
        "status": schedule.status,
        "skill_code": skill.skill_code,
    })


@router.get("/schedules", summary="获取定时调度列表")
def list_schedules(status: Optional[str] = None, db: Session = Depends(get_db)):
    from app.models.scheduler import SkillSchedule
    query = db.query(SkillSchedule)
    if status:
        query = query.filter(SkillSchedule.status == status)
    schedules = query.order_by(SkillSchedule.created_at.desc()).limit(100).all()
    return APIResponse(data=[{
        "schedule_code": s.schedule_code,
        "skill_code": s.skill_code,
        "name": s.name,
        "cron_expression": s.cron_expression,
        "status": s.status,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
        "last_run_status": s.last_run_status,
        "run_count": s.run_count,
        "fail_count": s.fail_count,
    } for s in schedules])


@router.put("/schedules/{schedule_code}/pause", summary="暂停定时调度")
def pause_schedule(schedule_code: str, db: Session = Depends(get_db)):
    from app.models.scheduler import SkillSchedule
    schedule = db.query(SkillSchedule).filter(SkillSchedule.schedule_code == schedule_code).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="调度不存在")
    schedule.status = "paused"
    db.commit()
    return APIResponse(data={"schedule_code": schedule_code, "status": "paused"})


@router.put("/schedules/{schedule_code}/resume", summary="恢复定时调度")
def resume_schedule(schedule_code: str, db: Session = Depends(get_db)):
    from app.models.scheduler import SkillSchedule
    schedule = db.query(SkillSchedule).filter(SkillSchedule.schedule_code == schedule_code).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="调度不存在")
    schedule.status = "active"
    db.commit()
    return APIResponse(data={"schedule_code": schedule_code, "status": "active"})


@router.delete("/schedules/{schedule_code}", summary="删除定时调度")
def delete_schedule(schedule_code: str, db: Session = Depends(get_db)):
    from app.models.scheduler import SkillSchedule
    schedule = db.query(SkillSchedule).filter(SkillSchedule.schedule_code == schedule_code).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="调度不存在")
    db.delete(schedule)
    db.commit()
    return APIResponse(data={"message": "调度已删除"})


# ============== SkillType 技能类型管理 API (1.1 动态配置) ==============

class SkillTypeCreateRequest(BaseModel):
    type_code: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    ext: Optional[str] = None


@router.get("/skill-types", summary="获取技能类型列表")
def list_skill_types(db: Session = Depends(get_db)):
    from app.models.skill import SkillType
    types = db.query(SkillType).filter(SkillType.is_active == True).order_by(SkillType.sort_order).all()
    return APIResponse(data=[{
        "type_code": t.type_code,
        "name": t.name,
        "description": t.description,
        "icon": t.icon,
        "color": t.color,
        "ext": t.ext,
        "sort_order": t.sort_order,
    } for t in types])


@router.post("/skill-types", summary="新增技能类型")
def create_skill_type(request: SkillTypeCreateRequest, db: Session = Depends(get_db)):
    from app.models.skill import SkillType
    existing = db.query(SkillType).filter(SkillType.type_code == request.type_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"类型代码 '{request.type_code}' 已存在")
    t = SkillType(
        type_code=request.type_code,
        name=request.name,
        description=request.description,
        icon=request.icon,
        color=request.color,
        ext=request.ext,
    )
    db.add(t)
    db.commit()
    return APIResponse(data={"type_code": t.type_code, "name": t.name})


@router.put("/skill-types/{type_code}", summary="编辑技能类型")
def update_skill_type(type_code: str, request: SkillTypeCreateRequest, db: Session = Depends(get_db)):
    from app.models.skill import SkillType
    t = db.query(SkillType).filter(SkillType.type_code == type_code).first()
    if not t:
        raise HTTPException(status_code=404, detail="类型不存在")
    for field in ["name", "description", "icon", "color", "ext"]:
        if field in request.dict(exclude_none=True):
            setattr(t, field, request.dict()[field])
    db.commit()
    return APIResponse(data={"type_code": t.type_code})


@router.put("/skill-types/{type_code}/disable", summary="禁用技能类型")
def disable_skill_type(type_code: str, db: Session = Depends(get_db)):
    from app.models.skill import SkillType
    t = db.query(SkillType).filter(SkillType.type_code == type_code).first()
    if not t:
        raise HTTPException(status_code=404, detail="类型不存在")
    t.is_active = False
    db.commit()
    return APIResponse(data={"type_code": t.type_code, "is_active": False})


# ============== 6.2 版本快照归档 ==============

@router.post("/skills/{skill_id}/versions/{version}/snapshot", summary="版本发布时物理快照归档")
def snapshot_version(skill_id: str, version: str, db: Session = Depends(get_db)):
    from app.core.skill_storage import get_skill_storage
    skill = SkillService.get_skill(db, _sid(skill_id))
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    storage = get_skill_storage()
    try:
        zip_path = storage.export_zip(skill.skill_code)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="技能包目录不存在")

    # 移动快照到归档目录
    import shutil
    from pathlib import Path
    archive_dir = Path(storage.root) / "archives" / skill.skill_code
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_name = f"v{version}_{zip_path.name}"
    archive_path = archive_dir / archive_name
    shutil.move(str(zip_path), str(archive_path))

    # 更新版本记录中的快照路径
    versions = VersionService.list_versions(db, _sid(skill_id))
    v = next((x for x in versions if x.version == version), None)
    if v and isinstance(v.content, dict):
        v.content["snapshot_path"] = str(archive_path)
        db.commit()

    return APIResponse(data={
        "snapshot_path": str(archive_path),
        "message": f"版本 {version} 快照已归档",
    })


# ============== 5.2 密钥柜 ==============

class SecretVaultEntry(BaseModel):
    key_name: str
    key_value: str
    description: Optional[str] = None


@router.get("/secrets", summary="获取密钥列表（值脱敏）")
def list_secrets(db: Session = Depends(get_db)):
    from app.core.database import SessionLocal
    from app.core.skill_storage import get_skill_storage
    import json
    from pathlib import Path

    vault_path = Path(get_skill_storage().root) / "vault" / "secrets.json"
    if not vault_path.exists():
        return APIResponse(data=[])

    secrets = json.loads(vault_path.read_text(encoding="utf-8"))
    return APIResponse(data=[
        {"key_name": k, "description": v.get("description", ""), "masked_value": "******"}
        for k, v in secrets.items()
    ])


@router.post("/secrets", summary="创建/更新密钥")
def upsert_secret(request: SecretVaultEntry, db: Session = Depends(get_db)):
    from app.core.skill_storage import get_skill_storage
    import json
    from pathlib import Path

    vault_path = Path(get_skill_storage().root) / "vault" / "secrets.json"
    vault_path.parent.mkdir(parents=True, exist_ok=True)

    secrets = {}
    if vault_path.exists():
        secrets = json.loads(vault_path.read_text(encoding="utf-8"))

    secrets[request.key_name] = {
        "value": request.key_value,
        "description": request.description or "",
    }
    vault_path.write_text(json.dumps(secrets, indent=2, ensure_ascii=False), encoding="utf-8")

    return APIResponse(data={"key_name": request.key_name, "message": "密钥已保存"})


@router.delete("/secrets/{key_name}", summary="删除密钥")
def delete_secret(key_name: str, db: Session = Depends(get_db)):
    from app.core.skill_storage import get_skill_storage
    import json
    from pathlib import Path

    vault_path = Path(get_skill_storage().root) / "vault" / "secrets.json"
    if not vault_path.exists():
        raise HTTPException(status_code=404, detail="密钥不存在")

    secrets = json.loads(vault_path.read_text(encoding="utf-8"))
    if key_name not in secrets:
        raise HTTPException(status_code=404, detail="密钥不存在")

    del secrets[key_name]
    vault_path.write_text(json.dumps(secrets, indent=2, ensure_ascii=False), encoding="utf-8")
    return APIResponse(data={"message": "密钥已删除"})
