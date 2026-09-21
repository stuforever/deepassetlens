"""
Skill v2 支持层 —— 请求/响应模型 + 只读目录/序列化工具

从 v2_skills.py 拆分（机械迁移，行为等价）：目录 README 构建、脚本符号解析、
流程-技能-API 关系构建等纯函数与 Pydantic 模型。路由仍留在 v2_skills.py。
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import re

from app.models.skill import Skill, SkillApiBinding

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


