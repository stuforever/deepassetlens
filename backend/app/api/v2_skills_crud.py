"""
技能管理 API (v2) -- CRUD 子模块
资源导向设计：/skills, /skills/glm-5.3_common/versions
从 v2_skills.py 机械拆分（零行为变更）：技能主表 / 文件树 / 版本 CRUD 与发布、导入导出。
路由由 v2_skills.router 聚合挂载（prefix 由 main.py 的 include_router 提供）。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime

from app.core.database import get_db
from app.services.skill_manager import SkillService, VersionService

from .skill_v2_support import (
    _sid,
    SkillCreateRequest, SkillUpdateRequest, VersionCreateRequest,
    APIResponse, _strip_inline_version_content,
)


router = APIRouter()

# ============== Skill 主表 API ==============

@router.get("/skills", summary="获取技能列表")
def list_skills(
    status: Optional[str] = None,
    skill_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    skills = SkillService.list_skills(db, status=status, skill_type=skill_type, skip=skip, limit=limit)
    return APIResponse(
        data=[{
            "skill_id": str(s.skill_id),
            "skill_code": s.skill_code,
            "name": s.name,
            "description": s.description,
            "skill_type": s.skill_type,
            "status": s.status,
            "current_version_id": str(s.current_version_id) if s.current_version_id else None,
            "tags": s.tags or [],
            "priority": s.priority,
            "timeout": s.timeout,
            "retry_policy": s.retry_policy,
            "resource_limits": s.resource_limits,
            "permissions": s.permissions,
            "app_type": s.app_type,
            "target_menu": s.target_menu,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        } for s in skills]
    )


@router.post("/skills", summary="创建技能")
def create_skill(request: SkillCreateRequest, db: Session = Depends(get_db)):
    try:
        skill = SkillService.create_skill(db, request.dict(exclude_none=True))
        return APIResponse(data={"skill_id": str(skill.skill_id), "skill_code": skill.skill_code})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/skills/{skill_id}", summary="获取技能详情")
def get_skill(skill_id: str, db: Session = Depends(get_db)):
    skill = SkillService.get_skill(db, _sid(skill_id))
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    return APIResponse(data={
        "skill_id": str(skill.skill_id),
        "skill_code": skill.skill_code,
        "name": skill.name,
        "description": skill.description,
        "skill_type": skill.skill_type,
        "status": skill.status,
        "current_version_id": str(skill.current_version_id) if skill.current_version_id else None,
        "tags": skill.tags or [],
        "priority": skill.priority,
        "timeout": skill.timeout,
        "retry_policy": skill.retry_policy,
        "resource_limits": skill.resource_limits,
        "permissions": skill.permissions,
        "app_type": skill.app_type,
        "target_menu": skill.target_menu,
        "created_at": skill.created_at.isoformat() if skill.created_at else None,
        "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
    })


@router.put("/skills/{skill_id}", summary="更新技能")
def update_skill(skill_id: str, request: SkillUpdateRequest, db: Session = Depends(get_db)):
    try:
        skill = SkillService.update_skill(db, skill_id, request.dict(exclude_none=True))
        return APIResponse(data={"skill_id": str(skill.skill_id)})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/skills/{skill_id}", summary="删除技能")
def delete_skill(skill_id: str, db: Session = Depends(get_db)):
    from app.models.scheduler import SkillSchedule
    skill = SkillService.get_skill(db, skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    # 1.6 熔断提示：检查引用关系
    ref_count = db.query(SkillSchedule).filter(
        SkillSchedule.skill_code == skill.skill_code,
        SkillSchedule.status == "active"
    ).count()
    if ref_count > 0:
        raise HTTPException(status_code=409, detail=f"该技能被 {ref_count} 个活跃定时任务引用，请先禁用相关调度")
    try:
        SkillService.delete_skill(db, _sid(skill_id))
        return APIResponse(message="技能已删除")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/skills/by-code/{skill_code}", summary="通过代码获取技能")
def get_skill_by_code(skill_code: str, db: Session = Depends(get_db)):
    skill = SkillService.get_skill_by_code(db, skill_code)
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    return APIResponse(data={
        "skill_id": str(skill.skill_id),
        "skill_code": skill.skill_code,
        "name": skill.name,
        "skill_type": skill.skill_type,
        "status": skill.status,
    })


@router.post("/skills/{skill_id}/publish", summary="发布技能")
def publish_skill(skill_id: str, db: Session = Depends(get_db)):
    skill = SkillService.get_skill(db, _sid(skill_id))
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    if skill.status == "published":
        raise HTTPException(status_code=400, detail="技能已处于发布状态")
    skill.status = "published"
    skill.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(skill)
    return APIResponse(data={"skill_id": str(skill.skill_id), "status": skill.status})


@router.post("/skills/{skill_id}/unpublish", summary="取消发布技能")
def unpublish_skill(skill_id: str, db: Session = Depends(get_db)):
    skill = SkillService.get_skill(db, _sid(skill_id))
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    if skill.status != "published":
        raise HTTPException(status_code=400, detail="只有已发布技能可以取消发布")
    skill.status = "draft"
    skill.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(skill)
    return APIResponse(data={"skill_id": str(skill.skill_id), "status": skill.status})


# ============== FileTree 文件树 API (五件套) ==============

class FileWriteRequest(BaseModel):
    path: str
    content: str


@router.get("/skills/{skill_id}/files", summary="获取技能包文件树")
def list_skill_files(skill_id: str, db: Session = Depends(get_db)):
    from app.core.skill_storage import get_skill_storage
    skill = SkillService.get_skill(db, _sid(skill_id))
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    storage = get_skill_storage()
    try:
        files = storage.list_files(skill.skill_code)
        return APIResponse(data=files)
    except FileNotFoundError:
        return APIResponse(data=[])


@router.get("/skills/{skill_id}/files/content", summary="读取技能包内文件内容")
def read_skill_file(skill_id: str, path: str, db: Session = Depends(get_db)):
    from app.core.skill_storage import get_skill_storage
    skill = SkillService.get_skill(db, _sid(skill_id))
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    storage = get_skill_storage()
    try:
        content = storage.read_file(skill.skill_code, path)
        return APIResponse(data={"path": path, "content": content})
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"文件不存在: {path}")
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.put("/skills/{skill_id}/files/content", summary="写入技能包内文件内容")
def write_skill_file(skill_id: str, request: FileWriteRequest, db: Session = Depends(get_db)):
    from app.core.skill_storage import get_skill_storage
    skill = SkillService.get_skill(db, _sid(skill_id))
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    storage = get_skill_storage()
    try:
        storage.write_file(skill.skill_code, request.path, request.content)
        return APIResponse(data={"path": request.path, "message": "文件已保存"})
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.delete("/skills/{skill_id}/files/content", summary="删除技能包内文件")
def delete_skill_file(skill_id: str, path: str, db: Session = Depends(get_db)):
    from app.core.skill_storage import get_skill_storage
    skill = SkillService.get_skill(db, _sid(skill_id))
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    storage = get_skill_storage()
    try:
        storage.delete_file(skill.skill_code, path)
        return APIResponse(data={"path": path, "message": "文件已删除"})
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"文件不存在: {path}")


@router.get("/skills/{skill_id}/skill-md", summary="获取 SKILL.md 解析结果")
def get_skill_md(skill_id: str, db: Session = Depends(get_db)):
    from app.core.skill_storage import get_skill_storage
    skill = SkillService.get_skill(db, _sid(skill_id))
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")
    storage = get_skill_storage()
    try:
        metadata = storage.parse_skill_md(skill.skill_code)
        return APIResponse(data=metadata)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="SKILL.md 不存在")


# ============== Version 版本 API ==============

@router.get("/skills/{skill_id}/versions", summary="获取技能版本列表")
def list_versions(skill_id: str, status: Optional[str] = None, db: Session = Depends(get_db)):
    versions = VersionService.list_versions(db, _sid(skill_id), status=status)
    return APIResponse(data=[{
        "version_id": str(v.version_id),
        "version": v.version,
        "status": v.status,
        "input_schema": v.input_schema,
        "output_schema": v.output_schema,
        "content": _strip_inline_version_content(v.content),
        "changelog": v.changelog,
        "released_by": v.released_by,
        "released_at": v.released_at.isoformat() if v.released_at else None,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    } for v in versions])


@router.post("/skills/{skill_id}/versions", summary="创建新版本")
def create_version(skill_id: str, request: VersionCreateRequest, db: Session = Depends(get_db)):
    try:
        version = VersionService.create_version(db, _sid(skill_id), request.dict(exclude_none=True))
        return APIResponse(data={"version_id": str(version.version_id), "version": version.version})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/skills/{skill_id}/versions/{version}", summary="获取指定版本详情")
def get_version(skill_id: str, version: str, db: Session = Depends(get_db)):
    versions = VersionService.list_versions(db, _sid(skill_id))
    v = next((x for x in versions if x.version == version), None)
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    return APIResponse(data={
        "version_id": str(v.version_id),
        "version": v.version,
        "status": v.status,
        "input_schema": v.input_schema,
        "output_schema": v.output_schema,
        "content": _strip_inline_version_content(v.content),
        "dependencies": v.dependencies,
        "changelog": v.changelog,
    })


@router.post("/skills/{skill_id}/versions/{version}/publish", summary="发布版本")
def publish_version(skill_id: str, version: str, db: Session = Depends(get_db), released_by: str = "system"):
    versions = VersionService.list_versions(db, _sid(skill_id))
    v = next((x for x in versions if x.version == version), None)
    if not v:
        raise HTTPException(status_code=404, detail="版本不存在")
    try:
        v = VersionService.publish_version(db, v.version_id, released_by)
        return APIResponse(data={"version_id": str(v.version_id), "status": v.status})
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============== Export/Import 导入导出 API ==============

@router.get("/skills/{skill_id}/export", summary="导出技能为ZIP（五件套完整目录）")
def export_skill(skill_id: str, db: Session = Depends(get_db)):
    from fastapi.responses import FileResponse
    from app.core.skill_storage import get_skill_storage

    skill = SkillService.get_skill(db, _sid(skill_id))
    if not skill:
        raise HTTPException(status_code=404, detail="技能不存在")

    storage = get_skill_storage()
    if not skill.skill_code:
        raise HTTPException(status_code=400, detail="技能无 skill_code")

    # 导出为 ZIP（包含完整五件套目录）
    zip_path = storage.export_zip(skill.skill_code)

    return FileResponse(
        path=str(zip_path),
        filename=zip_path.name,
        media_type="application/zip"
    )


class SkillImportRequest(BaseModel):
    data: Dict[str, Any]


@router.post("/skills/import", summary="导入技能 (ZIP 五件套目录）")
def import_skill(request: SkillImportRequest, db: Session = Depends(get_db), uploaded_file: UploadFile = File(...)):
    """
    从 ZIP 导入技能包
    解压到 skill_storage 目录，数据库仅存储元数据
    """
    from app.core.skill_storage import get_skill_storage
    from fastapi import UploadFile
    import tempfile
    import shutil
    from pathlib import Path

    # 保存上传的 ZIP 到临时文件
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_zip = Path(tmp_dir) / "uploaded.zip"
        with open(temp_zip, "wb") as f:
            shutil.copyfileobj(uploaded_file.file, f)

        # 使用 skill_storage 导入 ZIP（包含安全校验）
        storage = get_skill_storage()
        new_skill_code = storage.import_zip(temp_zip)

        # 解析导入的 SKILL.md 提取元数据
        try:
            metadata = storage.parse_skill_md(new_skill_code)
        except FileNotFoundError:
            metadata = {"name": new_skill_code, "description": "", "skill_type": "python"}

        # 在数据库中创建技能记录（不创建新技能包目录，因为导入已解压）
        skill = SkillService.create_skill(db, {
            "skill_code": new_skill_code,
            "name": metadata.get("name", "Imported Skill"),
            "description": metadata.get("description"),
            "skill_type": metadata.get("skill_type", "python"),
            "storage_path": str(storage._skill_path(new_skill_code)),
        })

        # 重新写入 SKILL.md 中的名称（使用正确的 skill_code）
        storage.update_skill_md(new_skill_code, {"name": skill.name})

        # 解析导入的 assets/input_schema.json 和 output_schema.json
        input_schema = storage.get_schema(new_skill_code, "input")
        output_schema = storage.get_schema(new_skill_code, "output")

        # 查找导入的最大版本号
        versions_to_import = []
        if storage.get_schema(new_skill_code, "input") or storage.get_schema(new_skill_code, "output"):
            # 简化：直接将导入的版本设为 1.0.0 active
            v = VersionService.create_version(db, skill.skill_id, {
                "version": "1.0.0",
                "input_schema": input_schema,
                "output_schema": output_schema,
                "changelog": "从 ZIP 导入",
            })
            VersionService.publish_version(db, v.version_id, "import")
            versions_to_import.append({"version": "1.0.0", "version_id": str(v.version_id), "status": "active"})

        db.refresh(skill)
        return APIResponse(data={
            "skill_id": str(skill.skill_id),
            "skill_code": skill.skill_code,
            "imported_versions": len(versions_to_import),
        })
