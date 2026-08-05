"""
技能管理 API (v2)
资源导向设计：/skills, /skills/{id}/versions, /skills/{id}/executions
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime
import re
import uuid

from app.core.database import get_db
from app.core.execution_engine import ExecutionEngineV2
from app.models.skill import Skill, SkillVersion, SkillExecLog, SkillApiBinding
from app.services.skill_manager import SkillService, VersionService, ExecutionService
from app.services.skill_templates import list_templates, get_template, apply_template


router = APIRouter()


def _sid(val):
    s = str(val).strip()
    if len(s) == 32:
        s = f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
    return s


# ============== 请求/响应模型 ==============

class SkillCreateRequest(BaseModel):
    skill_code: Optional[str] = None
    name: str
    description: Optional[str] = None
    skill_type: str = "natural"  # natural|python|sql|http|mixed|claude
    tags: Optional[List[str]] = None
    priority: int = 0
    timeout: int = 30
    retry_policy: Optional[Dict[str, Any]] = None
    resource_limits: Optional[Dict[str, Any]] = None
    permissions: Optional[Dict[str, Any]] = None
    app_type: Optional[str] = None
    target_menu: Optional[str] = None


class SkillUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    skill_type: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None
    priority: Optional[int] = None
    timeout: Optional[int] = None
    retry_policy: Optional[Dict[str, Any]] = None
    resource_limits: Optional[Dict[str, Any]] = None
    permissions: Optional[Dict[str, Any]] = None
    app_type: Optional[str] = None
    target_menu: Optional[str] = None


class VersionCreateRequest(BaseModel):
    version: str = "1.0.0"
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    content: Optional[Dict[str, Any]] = None
    dependencies: Optional[Dict[str, Any]] = None
    changelog: Optional[str] = None


class ExecutionCreateRequest(BaseModel):
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    version: Optional[str] = None  # 指定版本号，默认使用当前激活版本


class TaskSubmitRequest(BaseModel):
    skill_id: str
    input_payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = 1
    created_by: Optional[str] = None


class APIResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None


def _strip_inline_version_content(content: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    payload = dict(content or {})
    for key in [
        "script",
        "sql",
        "prompt",
        "steps",
        "method",
        "url",
        "headers",
        "body_template",
        "auth",
    ]:
        payload.pop(key, None)
    return payload


class SkillApiBindingUpsertRequest(BaseModel):
    api_code: str
    api_name: str
    api_type: str = "capability"
    provider_type: str = "internal"
    target_ref: str
    version_id: Optional[str] = None
    enabled: bool = True
    timeout_seconds: int = 30
    retry_policy: Optional[Dict[str, Any]] = None
    auth_mode: Optional[str] = None
    route_config: Optional[Dict[str, Any]] = None
    remark: Optional[str] = None


def _serialize_skill_api_binding(binding) -> Dict[str, Any]:
    return {
        "binding_id": str(binding.binding_id),
        "skill_id": str(binding.skill_id),
        "version_id": str(binding.version_id) if binding.version_id else None,
        "api_code": binding.api_code,
        "api_name": binding.api_name,
        "api_type": binding.api_type,
        "provider_type": binding.provider_type,
        "target_ref": binding.target_ref,
        "enabled": bool(binding.enabled),
        "timeout_seconds": binding.timeout_seconds,
        "retry_policy": binding.retry_policy or {},
        "auth_mode": binding.auth_mode,
        "route_config": binding.route_config,
        "remark": binding.remark,
        "created_at": binding.created_at.isoformat() if binding.created_at else None,
        "updated_at": binding.updated_at.isoformat() if binding.updated_at else None,
    }


def _get_api_catalog_readmes() -> Dict[str, Dict[str, Any]]:
    return {
        "query_entity_metadata_provider": {
            "api_code": "query_entity_metadata_provider",
            "api_name": "问实体元数据提供器",
            "call_type": "capability",
            "backend_call_kind": "后台直接API",
            "retain_reason": "正式元数据依赖数据库与系统配置，技能脚本无法自行获取，必须保留为后台能力。",
            "api_type": "capability",
            "provider_type": "internal",
            "target_ref": "service:query_entity_service.build_metadata_from_system",
            "description": "读取系统正式元数据并构造问实体所需上下文。",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "metadata": {"type": "object"},
                },
            },
            "process_example": {
                "input_example": {},
                "process_example": [
                    "读取系统正式元数据",
                    "整理实体层级、关系骨架和活动绑定信息",
                    "输出统一 metadata 对象供后续技能使用",
                ],
                "output_example": {
                    "metadata": {
                        "domain_catalog": [],
                        "relation_catalog": [],
                        "_meta": {},
                    }
                },
            },
        },
        "query_attribute_metadata_provider": {
            "api_code": "query_attribute_metadata_provider",
            "api_name": "问属性元数据提供器",
            "call_type": "capability",
            "backend_call_kind": "后台直接API",
            "retain_reason": "正式属性元数据依赖数据库与系统配置，技能脚本无法自行获取，必须保留为后台能力。",
            "api_type": "capability",
            "provider_type": "internal",
            "target_ref": "service:query_attribute_service.build_attribute_metadata_from_system",
            "description": "读取系统正式元数据并构造问属性所需上下文。",
            "input_schema": {
                "type": "object",
                "properties": {},
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "entity_catalog": {"type": "array"},
                    "relation_catalog": {"type": "array"},
                    "attribute_catalog": {"type": "array"},
                },
            },
            "process_example": {
                "input_example": {},
                "process_example": [
                    "读取正式实体、关系和属性配置",
                    "整理实体目录、关系目录和属性目录",
                    "输出问属性可直接消费的元数据视图",
                ],
                "output_example": {
                    "entity_catalog": [],
                    "relation_catalog": [],
                    "attribute_catalog": [],
                },
            },
        },
        "llm_gateway": {
            "api_code": "llm_gateway",
            "api_name": "统一大模型网关",
            "call_type": "capability",
            "backend_call_kind": "后台直接API",
            "retain_reason": "真实模型调用涉及连接配置、密钥、超时和供应商协议，必须集中保留在后台网关。",
            "api_type": "capability",
            "provider_type": "internal",
            "target_ref": "service:smart_planner.call_openai_compatible_chat",
            "description": "统一管理连接配置、超时、密钥和真实模型调用。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "system_prompt": {"type": ["string", "null"]},
                    "user_prompt": {"type": ["string", "null"]},
                    "user_query": {"type": ["string", "null"]},
                },
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "content": {"type": ["string", "null"]},
                    "parsed": {"type": "object"},
                    "used": {"type": "boolean"},
                    "reason": {"type": ["string", "null"]},
                },
            },
            "process_example": {
                "input_example": {
                    "system_prompt": "你是一个结构化解析器",
                    "user_prompt": "请根据元数据完成判定",
                    "user_query": "查询用电客户证件信息",
                },
                "process_example": [
                    "选择启用中的模型连接配置",
                    "把系统提示词和用户提示词发送给大模型",
                    "返回原始内容和解析结果供技能继续处理",
                ],
                "output_example": {
                    "used": True,
                    "content": "{\"decision\":\"final\"}",
                    "parsed": {"decision": "final"},
                    "reason": None,
                },
            },
        },
        "llm_connection_provider": {
            "api_code": "llm_connection_provider",
            "api_name": "LLM连接提供器",
            "call_type": "capability",
            "backend_call_kind": "后台直接API",
            "retain_reason": "LLM连接选择依赖数据库配置和默认规划器设置，技能脚本只能显式调用后台能力获取。",
            "api_type": "capability",
            "provider_type": "internal",
            "target_ref": "service:query_entity_service.get_query_llm_connection",
            "description": "技能显式调用该后台能力获取本次应使用的 LLM 连接，优先使用传入连接ID，其次读取默认配置。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "preferred_connection_id": {"type": ["string", "null"]},
                },
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "connection_id": {"type": ["string", "null"]},
                    "connection_name": {"type": ["string", "null"]},
                    "model_name": {"type": ["string", "null"]},
                },
            },
            "process_example": {
                "input_example": {
                    "preferred_connection_id": None,
                },
                "process_example": [
                    "技能先显式传入期望使用的 LLM 连接ID",
                    "如果没有传入，则后台读取当前默认可用模型连接",
                    "把最终连接信息返回给技能，供后续统一大模型网关调用",
                ],
                "output_example": {
                    "connection_id": "planner-default-llm-id",
                    "connection_name": "默认推理模型",
                    "model_name": "gpt-4.1",
                },
            },
        },
        "entity_attribute_repository": {
            "api_code": "entity_attribute_repository",
            "api_name": "实体属性仓储查询",
            "call_type": "capability",
            "backend_call_kind": "后台直接API",
            "retain_reason": "正式实体与属性明细来自数据库仓储，技能脚本不应内置仓储访问细节。",
            "api_type": "capability",
            "provider_type": "internal",
            "target_ref": "repository:Entity.attributes",
            "description": "根据实体候选读取正式实体和属性明细，用于整理属性清单与校核目录。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "entity_ids": {"type": "array"},
                },
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "entities": {"type": "array"},
                    "attributes": {"type": "array"},
                },
            },
            "process_example": {
                "input_example": {
                    "entity_ids": ["entity-customer-main", "entity-customer-cert"],
                },
                "process_example": [
                    "根据候选实体ID查询正式实体记录",
                    "展开关联的正式属性明细与别名信息",
                    "返回实体与属性数据供技能整理 attribute_rows",
                ],
                "output_example": {
                    "entities": [
                        {"entity_id": "entity-customer-main", "entity_name": "用电客户信息"}
                    ],
                    "attributes": [
                        {"entity_id": "entity-customer-main", "field_cn": "客户编号"}
                    ],
                },
            },
        },
        "standard_semantic_query": {
            "api_code": "standard_semantic_query",
            "api_name": "标准语义向量检索",
            "call_type": "capability",
            "backend_call_kind": "后台直接API",
            "retain_reason": "向量检索依赖后台索引与服务资源，必须保留为统一检索能力。",
            "api_type": "capability",
            "provider_type": "internal",
            "target_ref": "service:standard_semantic_service.query_standard_semantic_matches",
            "description": "在标准语义库中检索属性文档并返回匹配结果。",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query_text": {"type": "string"},
                    "top_k": {"type": "integer"},
                    "term_types": {"type": "array"},
                    "entity_scope": {"type": "string"},
                },
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "matches": {"type": "array"},
                },
            },
            "process_example": {
                "input_example": {
                    "query_text": "帮我查客户编号和证件类型",
                    "top_k": 20,
                    "term_types": ["attribute"],
                    "entity_scope": "all",
                },
                "process_example": [
                    "把整句问句送入标准语义检索",
                    "召回属性文档并补齐所属实体信息",
                    "返回候选命中结果供技能聚合实体清单",
                ],
                "output_example": {
                    "matches": [
                        {
                            "entity_name": "用电客户信息",
                            "attribute_name": "客户编号",
                            "score": 0.92,
                        }
                    ],
                },
            },
        },
    }


def _build_dynamic_service_ref_readme(api_code: str) -> Optional[Dict[str, Any]]:
    prefix = "service_ref__"
    if not str(api_code or "").startswith(prefix):
        return None
    payload = str(api_code)[len(prefix):]
    if "__" not in payload:
        return None
    module_name, function_name = payload.rsplit("__", 1)
    target_ref = f"service:{module_name}.{function_name}"
    return {
        "api_code": api_code,
        "api_name": f"后台Service函数 {module_name}.{function_name}",
        "call_type": "helper",
        "backend_call_kind": "helper",
        "retain_reason": "这是技能脚本直接导入的同进程 helper，用于暂时复用后台基础函数；后续若能完全收回技能，应继续清理。",
        "api_type": "capability",
        "provider_type": "internal",
        "target_ref": target_ref,
        "description": f"技能脚本直接导入后台 service 函数 `{module_name}.{function_name}`。",
        "input_schema": {
            "type": "object",
            "properties": {
                "call_site": {"type": "string"},
                "note": {"type": "string"},
            },
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "return_value": {"type": "object"},
                "note": {"type": "string"},
            },
        },
        "process_example": {
            "input_example": {
                "call_site": target_ref,
                "note": "实际参数由技能脚本在运行时组织。",
            },
            "process_example": [
                "技能脚本直接导入该 service 函数",
                "在技能执行时以代码调用，而非通过工作流显式传参",
                "返回结果继续在技能脚本内部加工",
            ],
            "output_example": {
                "return_value": {"target_ref": target_ref},
                "note": "具体返回结构取决于该 service 函数实现。",
            },
        },
    }


def _infer_retain_reason(api_code: str, target_ref: str, backend_call_kind: str) -> str:
    api_code_text = str(api_code or "")
    target_ref_text = str(target_ref or "")
    if api_code_text == "query_entity_metadata_provider" or target_ref_text.endswith("query_entity_service.build_metadata_from_system"):
        return "正式元数据依赖数据库与系统配置，技能脚本无法自行获取，必须保留后台读取能力。"
    if api_code_text == "query_attribute_metadata_provider" or target_ref_text.endswith("query_attribute_service.build_attribute_metadata_from_system"):
        return "正式属性元数据依赖数据库与系统配置，技能脚本无法自行获取，必须保留后台读取能力。"
    if api_code_text == "llm_connection_provider" or target_ref_text.endswith("query_entity_service.get_query_llm_connection"):
        return "LLM连接选择依赖数据库配置和默认规划器设置，技能脚本只能显式调用后台能力获取。"
    if api_code_text == "llm_gateway" or target_ref_text.endswith("smart_planner.call_openai_compatible_chat"):
        return "真实模型调用涉及密钥、连接、超时和供应商协议，必须集中保留在后台网关。"
    if api_code_text == "standard_semantic_query" or target_ref_text.endswith("standard_semantic_service.query_standard_semantic_matches"):
        return "向量检索依赖后台索引与检索服务，不能搬入技能脚本。"
    if target_ref_text.startswith("repository:"):
        return "仓储访问依赖数据库模型和持久化层，保留在后台更稳定。"
    if backend_call_kind == "helper":
        return "当前仍是技能脚本直接复用的 helper；若后续能改写为技能内逻辑，应继续压缩。"
    return "这是当前技能仍需复用的后台能力，保留原因已在技能链路中显式标注。"


def _split_imported_service_symbols(body: str) -> List[str]:
    items: List[str] = []
    for raw_part in (body or "").replace("\r", "\n").split("\n"):
        for chunk in raw_part.split(","):
            item = str(chunk or "").strip()
            if not item or item.startswith("#"):
                continue
            item = item.split("#", 1)[0].strip()
            if not item:
                continue
            if " as " in item:
                item = item.split(" as ", 1)[0].strip()
            item = item.strip("()")
            if item:
                items.append(item)
    return items


def _extract_service_refs_from_script(script: str) -> List[Dict[str, str]]:
    refs: List[Dict[str, str]] = []
    seen = set()
    text = str(script or "")
    if not text.strip():
        return refs

    patterns = [
        re.finditer(
            r"from\s+app\.services\.(?P<module>[a-zA-Z0-9_]+)\s+import\s*\((?P<body>[\s\S]*?)\)",
            text,
            flags=re.MULTILINE,
        ),
        re.finditer(
            r"from\s+app\.services\.(?P<module>[a-zA-Z0-9_]+)\s+import\s+(?P<body>[^\n]+)",
            text,
            flags=re.MULTILINE,
        ),
    ]
    for iterator in patterns:
        for match in iterator:
            module_name = str(match.group("module") or "").strip()
            for symbol in _split_imported_service_symbols(match.group("body") or ""):
                target_ref = f"service:{module_name}.{symbol}"
                if not module_name or not symbol or target_ref in seen:
                    continue
                seen.add(target_ref)
                refs.append(
                    {
                        "api_code": f"service_ref__{module_name}__{symbol}",
                        "api_name": f"后台Service函数 {module_name}.{symbol}",
                        "target_ref": target_ref,
                    }
                )
    return refs


def _get_skill_logic_catalog() -> Dict[str, Dict[str, Any]]:
    return {
        "query_entity_step1_metadata_overview": {
            "summary": [
                "技能脚本内直接调用正式元数据能力。",
                "输出共享 metadata，不接 user_query 等额外输入。",
            ]
        },
        "query_entity_step3_llm_prompt": {
            "summary": [
                "共享技能脚本内按场景拼装问实体或问属性 system_prompt。",
                "技能脚本内把 metadata 和可选 attribute_rows 收缩成 prompt_metadata，并生成 user_prompt。",
            ]
        },
        "query_entity_step4_llm_inference": {
            "summary": [
                "技能脚本内显式获取 LLM 连接并调用统一大模型网关。",
                "技能脚本内完成 JSON 解析和问实体/问属性两套 clarification 提取。",
            ]
        },
        "query_entity_step5_finalize": {
            "summary": [
                "技能脚本内显式消费 Step1 输出的 metadata。",
                "技能脚本内完成实体、活动、关系校核和落版。",
            ]
        },
    }


def _build_workflow_skill_api_relations(db: Session) -> List[Dict[str, Any]]:
    from app.core.skill_storage import get_skill_storage

    readmes = _get_api_catalog_readmes()
    skill_logic_catalog = _get_skill_logic_catalog()
    storage = get_skill_storage()
    skills = db.query(Skill).all()
    bindings = (
        db.query(SkillApiBinding)
        .filter(SkillApiBinding.enabled == True)  # noqa: E712
        .all()
    )

    skill_by_code = {str(item.skill_code): item for item in skills}
    _ = skill_by_code
    bindings_by_skill_id: Dict[str, List[SkillApiBinding]] = {}
    for binding in bindings:
        key = str(binding.skill_id)
        bindings_by_skill_id.setdefault(key, []).append(binding)

    rows: List[Dict[str, Any]] = []
    for skill in skills:
        skill_bindings = bindings_by_skill_id.get(str(skill.skill_id), [])
        script = ""
        try:
            script = storage.read_file(skill.skill_code, "scripts/main.py")
        except FileNotFoundError:
            script = ""
        implicit_service_refs = _extract_service_refs_from_script(script)
        explicit_target_refs = {str(item.target_ref or "") for item in skill_bindings}
        for binding in skill_bindings:
            readme = readmes.get(binding.api_code) or {}
            rows.append(
                {
                    "workflow_id": None,
                    "workflow_name": None,
                    "skill_id": str(skill.skill_id),
                    "skill_code": skill.skill_code,
                    "skill_name": skill.name,
                    "api_code": binding.api_code,
                    "api_name": binding.api_name,
                    "call_type": readme.get("call_type") or binding.api_type or "capability",
                    "backend_call_kind": readme.get("backend_call_kind") or "后台直接API",
                    "purpose": binding.remark or readme.get("description") or "",
                    "retain_reason": readme.get("retain_reason")
                    or _infer_retain_reason(binding.api_code, binding.target_ref, "后台直接API"),
                    "skill_logic_summary": (skill_logic_catalog.get(skill.skill_code) or {}).get("summary") or [],
                    "_workflow_order": 0,
                }
            )
        for service_ref in implicit_service_refs:
            if service_ref["target_ref"] in explicit_target_refs:
                continue
            readme = _build_dynamic_service_ref_readme(service_ref["api_code"]) or {}
            rows.append(
                {
                    "workflow_id": None,
                    "workflow_name": None,
                    "skill_id": str(skill.skill_id),
                    "skill_code": skill.skill_code,
                    "skill_name": skill.name,
                    "api_code": service_ref["api_code"],
                    "api_name": service_ref["api_name"],
                    "call_type": readme.get("call_type") or "helper",
                    "backend_call_kind": readme.get("backend_call_kind") or "helper",
                    "purpose": readme.get("description") or f"技能脚本直接调用 {service_ref['target_ref']}",
                    "retain_reason": readme.get("retain_reason")
                    or _infer_retain_reason(service_ref["api_code"], service_ref["target_ref"], "helper"),
                    "skill_logic_summary": (skill_logic_catalog.get(skill.skill_code) or {}).get("summary") or [],
                    "_workflow_order": 0,
                }
            )

    rows.sort(
        key=lambda item: (
            str(item.get("skill_name") or ""),
            str(item.get("api_name") or ""),
        )
    )
    for item in rows:
        item.pop("_workflow_order", None)
    return rows


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

    # 保存上传的 ZIP 到临时文件
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_zip = tmp_dir / "uploaded.zip"
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
    return APIResponse(data={"type_code": type_code, "is_active": False})


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
