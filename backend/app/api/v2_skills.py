"""
技能管理 API (v2)
资源导向设计：/skills, /skills/glm-5.3_common/versions, /skills/glm-5.3_common/executions

机械拆分（零行为变更）：路由实现分布在兄弟模块，本模块聚合后仍以 router 对外暴露
（main.py: app.include_router(v2_skills.router, prefix="/api/v2", tags=["skills-v2"])）：
  - v2_skills_crud.py  技能/版本/文件 CRUD、发布、导入导出
  - v2_skills_exec.py  执行/调试/异步任务/Worker/Tool Calling
  - v2_skills_misc.py  模板/调度/技能类型/版本快照/密钥柜
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.core.database import get_db
from app.core.execution_engine import ExecutionEngineV2
from app.models.skill import Skill, SkillVersion, SkillExecLog
from app.services.skill_manager import SkillService, VersionService, ExecutionService
from app.services.skill_templates import list_templates, get_template, apply_template


router = APIRouter()

from .skill_v2_support import (
    _sid,
    SkillCreateRequest, SkillUpdateRequest, VersionCreateRequest, ExecutionCreateRequest,
    TaskSubmitRequest, APIResponse, _strip_inline_version_content,
    SkillApiBindingUpsertRequest, _serialize_skill_api_binding,
    _get_api_catalog_readmes, _build_dynamic_service_ref_readme, _infer_retain_reason,
    _split_imported_service_symbols, _extract_service_refs_from_script,
    _get_skill_logic_catalog, _build_workflow_skill_api_relations,
)

from .v2_skills_crud import router as _crud_router
from .v2_skills_exec import router as _exec_router
from .v2_skills_misc import router as _misc_router
router.include_router(_crud_router)
router.include_router(_exec_router)
router.include_router(_misc_router)
