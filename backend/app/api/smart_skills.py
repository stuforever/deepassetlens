from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import json
import time
import re
import math
from datetime import datetime

from ..core.database import get_db
from ..models.base import (
    SmartSkill,
    SmartSkillType,
    SmartSkillWorkflow,
    SmartWorkflowRun,
    Concept,
    Entity,
    EntityRelation,
    LLMConnectionConfig,
    IntentSemanticAsset,
)
from .smart_apps import generate_smart_join_candidates, CONFIDENCE_THRESHOLD
from ..services.smart_planner import plan_steps, get_active_planner_config, call_openai_compatible_messages
from ..services.semantic_retrieval import (
    get_or_init_retrieval_config,
    rebuild_semantic_index,
    semantic_status,
    score_entities_semantic,
    hybrid_score,
    embed_texts,
    cosine_similarity,
)
from ..services.standard_semantic_service import query_standard_semantic_matches

from .smart_skill_pipeline import _invoke_skill, _pick_script_assistant_llm


router = APIRouter()


class SmartSkillCreate(BaseModel):
    skill_code: str
    skill_name: str
    app_type: Optional[str] = "smart_join"
    status: Optional[str] = "enabled"
    description: Optional[str] = None
    skill_kind: Optional[str] = "natural_language"
    version: Optional[str] = "v1"
    skill_content: Optional[str] = None
    skill_descriptor: Optional[Dict[str, Any]] = None
    target_menu: Optional[str] = "connection"
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    runtime_config: Optional[Dict[str, Any]] = None


class SmartSkillUpdate(BaseModel):
    skill_name: Optional[str] = None
    app_type: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    skill_kind: Optional[str] = None
    version: Optional[str] = None
    skill_content: Optional[str] = None
    skill_descriptor: Optional[Dict[str, Any]] = None
    target_menu: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None
    runtime_config: Optional[Dict[str, Any]] = None


class WorkflowCreate(BaseModel):
    workflow_code: str
    workflow_name: str
    app_type: Optional[str] = "smart_join"
    target_menu: Optional[str] = "connection"
    strategy_config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = True
    steps: Optional[List[Dict[str, Any]]] = None
    description: Optional[str] = None


class WorkflowUpdate(BaseModel):
    workflow_name: Optional[str] = None
    app_type: Optional[str] = None
    target_menu: Optional[str] = None
    strategy_config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None
    steps: Optional[List[Dict[str, Any]]] = None
    description: Optional[str] = None


class WorkflowRunRequest(BaseModel):
    input_payload: Optional[Dict[str, Any]] = None


class SkillTestRequest(BaseModel):
    input_payload: Optional[Dict[str, Any]] = None


class SkillScriptAssistantRequest(BaseModel):
    task_type: str  # generate | fix | explain
    requirement: Optional[str] = None
    error_message: Optional[str] = None
    input_sample: Optional[Dict[str, Any]] = None
    output_expectation: Optional[Dict[str, Any]] = None
    auto_apply: Optional[bool] = False


class SemanticRebuildRequest(BaseModel):
    force_rebuild: Optional[bool] = True


def _serialize_skill(item: SmartSkill):
    return {
        "id": str(item.id),
        "skill_code": item.skill_code,
        "skill_name": item.skill_name,
        "app_type": item.app_type,
        "status": item.status,
        "description": item.description,
        "skill_kind": item.skill_kind,
        "version": item.version,
        "skill_content": item.skill_content,
        "skill_descriptor": item.skill_descriptor or {},
        "target_menu": item.target_menu,
        "input_schema": item.input_schema or {},
        "output_schema": item.output_schema or {},
        "runtime_config": item.runtime_config or {},
        "created_at": str(item.created_at) if item.created_at else None,
    }


def _serialize_workflow(item: SmartSkillWorkflow):
    return {
        "id": str(item.id),
        "workflow_code": item.workflow_code,
        "workflow_name": item.workflow_name,
        "app_type": item.app_type,
        "target_menu": item.target_menu,
        "strategy_config": item.strategy_config or {},
        "enabled": bool(item.enabled),
        "steps": item.steps or [],
        "description": item.description,
        "created_at": str(item.created_at) if item.created_at else None,
    }


def _serialize_run(item: SmartWorkflowRun):
    return {
        "id": str(item.id),
        "workflow_id": str(item.workflow_id),
        "workflow_code": item.workflow_code,
        "app_type": item.app_type,
        "status": item.status,
        "input_payload": item.input_payload or {},
        "output_payload": item.output_payload or {},
        "step_logs": item.step_logs or [],
        "error_message": item.error_message,
        "created_at": str(item.created_at) if item.created_at else None,
    }




@router.get("/smart-skills")
def list_skills(app_type: Optional[str] = None, db: Session = Depends(get_db)):
    items = db.query(SmartSkill).order_by(SmartSkill.created_at.desc()).all()
    if app_type:
        items = [x for x in items if (x.app_type or "").lower() == app_type.lower()]
    return {"code": 200, "data": [_serialize_skill(x) for x in items]}


@router.post("/smart-skills")
def create_skill(payload: SmartSkillCreate, db: Session = Depends(get_db)):
    data = payload.dict()
    exists = db.query(SmartSkill).filter(SmartSkill.skill_code == data["skill_code"]).first()
    if exists:
        raise HTTPException(status_code=400, detail="skill_code已存在")
    item = SmartSkill(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": _serialize_skill(item)}


@router.put("/smart-skills/{item_id}")
def update_skill(item_id: str, payload: SmartSkillUpdate, db: Session = Depends(get_db)):
    items = db.query(SmartSkill).all()
    item = next((x for x in items if str(x.id) == str(item_id)), None)
    if not item:
        raise HTTPException(status_code=404, detail="skill not found")
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": _serialize_skill(item)}


@router.delete("/smart-skills/{item_id}")
def delete_skill(item_id: str, db: Session = Depends(get_db)):
    items = db.query(SmartSkill).all()
    item = next((x for x in items if str(x.id) == str(item_id)), None)
    if not item:
        raise HTTPException(status_code=404, detail="skill not found")
    db.delete(item)
    db.commit()
    return {"code": 200, "message": "deleted"}


@router.post("/smart-skills/{item_id}/test")
def test_skill(item_id: str, payload: SkillTestRequest, db: Session = Depends(get_db)):
    items = db.query(SmartSkill).all()
    skill = next((x for x in items if str(x.id) == str(item_id)), None)
    if not skill:
        raise HTTPException(status_code=404, detail="skill not found")
    context = {"input_payload": payload.input_payload or {}, "is_test": True}
    result = _invoke_skill(db=db, skill=skill, step={"config": {}}, context=context)
    return {"code": 200, "data": {"skill_code": skill.skill_code, "result": result}}


@router.get("/smart-skills/semantic/status")
def get_semantic_retrieval_status(db: Session = Depends(get_db)):
    return {"code": 200, "data": semantic_status(db)}


@router.post("/smart-skills/semantic/rebuild-index")
def rebuild_semantic_retrieval_index(payload: SemanticRebuildRequest, db: Session = Depends(get_db)):
    # 先保留force_rebuild参数，后续可扩展为增量/全量模式
    _ = bool(payload.force_rebuild)
    data = rebuild_semantic_index(db)
    return {"code": 200, "data": data}


@router.post("/smart-skills/{item_id}/script-assistant")
def skill_script_assistant(item_id: str, payload: SkillScriptAssistantRequest, db: Session = Depends(get_db)):
    items = db.query(SmartSkill).all()
    skill = next((x for x in items if str(x.id) == str(item_id)), None)
    if not skill:
        raise HTTPException(status_code=404, detail="skill not found")

    task_type = (payload.task_type or "").strip().lower()
    if task_type not in ("generate", "fix", "explain"):
        raise HTTPException(status_code=400, detail="task_type必须是generate/fix/explain")

    conn = _pick_script_assistant_llm(db)
    if not conn:
        raise HTTPException(status_code=400, detail="未找到可用LLM连接，请先在LLM配置里启用豆包或其他连接")

    current_script = (skill.skill_content or "").strip()
    requirement = (payload.requirement or "").strip()
    error_message = (payload.error_message or "").strip()
    input_sample = payload.input_sample or {}
    output_expectation = payload.output_expectation or {}

    system_prompt = (
        "你是Python技能脚本助手。"
        "目标是为DB-GPT技能生成可运行脚本。"
        "脚本约定：定义 run(input_payload, context) 函数并返回JSON可序列化对象。"
        "避免危险操作（文件系统、网络、进程、eval）。"
    )

    if task_type == "generate":
        user_prompt = json.dumps(
            {
                "task": "generate_python_skill_script",
                "skill_code": skill.skill_code,
                "skill_name": skill.skill_name,
                "requirement": requirement,
                "input_sample": input_sample,
                "output_expectation": output_expectation,
                "must_return_json": True,
                "output_format": {"script": "python code", "explain": "short text"},
            },
            ensure_ascii=False,
        )
    elif task_type == "fix":
        user_prompt = json.dumps(
            {
                "task": "fix_python_skill_script",
                "skill_code": skill.skill_code,
                "current_script": current_script,
                "error_message": error_message,
                "requirement": requirement,
                "input_sample": input_sample,
                "output_expectation": output_expectation,
                "output_format": {"script": "python code", "explain": "short text"},
            },
            ensure_ascii=False,
        )
    else:
        user_prompt = json.dumps(
            {
                "task": "explain_python_skill_script",
                "skill_code": skill.skill_code,
                "current_script": current_script,
                "output_format": {
                    "summary": "what this script does",
                    "input_contract": "expected input",
                    "output_contract": "expected output",
                    "risks": ["risk1"],
                },
            },
            ensure_ascii=False,
        )

    try:
        resp = call_openai_compatible_messages(
            conn,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.1,
            max_tokens=1800,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"脚本助手调用LLM失败: {e}")
    content = (
        (((resp or {}).get("choices") or [{}])[0].get("message") or {}).get("content")
        or ""
    ).strip()

    script = None
    explain = None
    parsed = None
    try:
        cleaned = content
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("python") or cleaned.startswith("json"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end >= start:
            parsed = json.loads(cleaned[start : end + 1])
            script = parsed.get("script")
            explain = parsed.get("explain") or parsed.get("summary")
    except Exception:
        parsed = None

    if task_type in ("generate", "fix") and not script:
        script = content
    if task_type == "explain" and not explain:
        explain = content

    applied = False
    if payload.auto_apply and task_type in ("generate", "fix") and script:
        skill.skill_content = script
        if (skill.skill_kind or "").lower() != "python":
            skill.skill_kind = "python"
        db.commit()
        db.refresh(skill)
        applied = True

    return {
        "code": 200,
        "data": {
            "task_type": task_type,
            "skill_id": str(skill.id),
            "skill_code": skill.skill_code,
            "script": script,
            "explain": explain,
            "applied": applied,
            "llm_connection": {"id": str(conn.id), "name": conn.name, "provider": conn.provider, "model_name": conn.model_name},
            "raw_text": content,
            "raw_json": parsed,
        },
    }


@router.get("/smart-skill-workflows")
def list_workflows(app_type: Optional[str] = None, target_menu: Optional[str] = None, db: Session = Depends(get_db)):
    items = db.query(SmartSkillWorkflow).order_by(SmartSkillWorkflow.created_at.desc()).all()
    if app_type:
        items = [x for x in items if (x.app_type or "").lower() == app_type.lower()]
    if target_menu:
        items = [x for x in items if (x.target_menu or "").lower() == target_menu.lower()]
    return {"code": 200, "data": [_serialize_workflow(x) for x in items]}


@router.post("/smart-skill-workflows")
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    data = payload.dict()
    exists = db.query(SmartSkillWorkflow).filter(SmartSkillWorkflow.workflow_code == data["workflow_code"]).first()
    if exists:
        raise HTTPException(status_code=400, detail="workflow_code已存在")
    item = SmartSkillWorkflow(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": _serialize_workflow(item)}


@router.put("/smart-skill-workflows/{item_id}")
def update_workflow(item_id: str, payload: WorkflowUpdate, db: Session = Depends(get_db)):
    items = db.query(SmartSkillWorkflow).all()
    item = next((x for x in items if str(x.id) == str(item_id)), None)
    if not item:
        raise HTTPException(status_code=404, detail="workflow not found")
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": _serialize_workflow(item)}


@router.delete("/smart-skill-workflows/{item_id}")
def delete_workflow(item_id: str, db: Session = Depends(get_db)):
    items = db.query(SmartSkillWorkflow).all()
    item = next((x for x in items if str(x.id) == str(item_id)), None)
    if not item:
        raise HTTPException(status_code=404, detail="workflow not found")
    db.delete(item)
    db.commit()
    return {"code": 200, "message": "deleted"}


@router.post("/smart-skill-workflows/{item_id}/run")
def run_workflow(item_id: str, payload: WorkflowRunRequest, db: Session = Depends(get_db)):
    workflows = db.query(SmartSkillWorkflow).all()
    wf = next((x for x in workflows if str(x.id) == str(item_id)), None)
    if not wf:
        raise HTTPException(status_code=404, detail="workflow not found")
    if not wf.enabled:
        raise HTTPException(status_code=400, detail="workflow未启用")

    skill_by_code = {s.skill_code: s for s in db.query(SmartSkill).all()}
    steps = wf.steps if isinstance(wf.steps, list) else []
    ordered_steps = sorted(
        steps,
        key=lambda x: int((x or {}).get("order", 9999)),
    )
    skills_meta = [
        {
            "skill_code": s.skill_code,
            "skill_name": s.skill_name,
            "app_type": s.app_type,
            "description": s.description,
        }
        for s in skill_by_code.values()
    ]
    intent = str((payload.input_payload or {}).get("intent") or "")
    planned_steps, planning_info = plan_steps(
        db=db,
        app_type=wf.app_type,
        intent=intent,
        steps=ordered_steps,
        skills_meta=skills_meta,
    )

    def _build_step_detail(result: Dict[str, Any] | Any) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return {"summary": "无结构化输出", "trace": []}
        rtype = result.get("type")
        if rtype == "ontology_semantic_align":
            terms = result.get("aligned_terms") or []
            return {
                "summary": "完成本体语义对齐",
                "trace": [
                    f"本体置信度: {result.get('ontology_confidence', 0):.4f}",
                    f"低置信度: {'是' if result.get('low_confidence') else '否'}",
                ],
                "aligned_top": terms[:3],
            }
        if rtype == "low_confidence_clarify":
            return {
                "summary": "完成低置信度澄清判断",
                "trace": [
                    f"是否需要澄清: {'是' if result.get('need_clarify') else '否'}",
                    f"澄清问题数: {len(result.get('clarify_questions') or [])}",
                ],
            }
        if rtype == "graph_query_generate":
            return {
                "summary": "完成图谱查询生成与规则预检查",
                "trace": [
                    f"规则检查通过: {'是' if result.get('rule_check_passed') else '否'}",
                    f"违规数: {len(result.get('violations') or [])}",
                ],
                "query_plan": result.get("query_plan"),
            }
        if rtype == "graph_query_execute":
            return {
                "summary": "完成图查询执行与空结果回退",
                "trace": [
                    f"结果数: {result.get('result_count', 0)}",
                    f"回退触发: {'是' if result.get('fallback_triggered') else '否'}",
                    f"重试次数: {result.get('retry_count', 0)}",
                ],
            }
        if rtype == "vector_hybrid_retrieve":
            return {
                "summary": "完成混合检索召回",
                "trace": [
                    f"召回模式: {(result.get('retrieval_meta') or {}).get('retrieval_mode')}",
                    f"证据条数: {len(result.get('evidences') or [])}",
                ],
            }
        if rtype == "llm_reasoning_answer":
            return {
                "summary": "完成思维链合成回答",
                "trace": [
                    f"显式比较式数量: {len(result.get('explicit_comparisons') or [])}",
                    f"引用证据数: {len(result.get('citations') or [])}",
                ],
            }
        if rtype == "ontology_compliance_trace_check":
            return {
                "summary": "完成本体合规与事实一致性校验",
                "trace": [
                    f"一致性通过率: {result.get('fact_consistency_pass_rate', 0):.2f}",
                    f"最终通过: {'是' if result.get('final_passed') else '否'}",
                ],
            }
        if rtype == "biz_requirement_understand":
            entities = (((result.get("graph_context_hit") or {}).get("entities")) or [])[:3]
            entity_names = [x.get("entity_cn_name") or x.get("entity_name") for x in entities]
            return {
                "summary": "业务理解与图谱上下文注入完成",
                "trace": [
                    f"是否调用豆包: {'是' if result.get('used_llm') else '否'}",
                    f"命中实体: {', '.join([str(x) for x in entity_names if x]) or '-'}",
                ],
                "understanding_excerpt": str(result.get("understanding") or "")[:240],
            }
        if rtype == "graph_entity_field_locator":
            hit_summary = (result.get("hit_summary") or [])[:3]
            return {
                "summary": "完成实体字段定位",
                "trace": [
                    f"候选实体数: {len(result.get('entities') or [])}",
                    f"关系样本数: {len(result.get('entity_relations') or [])}",
                ],
                "hit_top": hit_summary,
            }
        if rtype in ("join_sql_recommend", "smart_join_recommend"):
            candidates = (((result.get("result") or {}).get("candidates")) or [])[:3]
            return {
                "summary": "完成联接SQL推荐",
                "trace": [
                    f"策略: {result.get('single_table_policy') or 'auto'}",
                    f"候选数量: {len(((result.get('result') or {}).get('candidates')) or [])}",
                ],
                "candidates_top": [
                    {
                        "title": c.get("title"),
                        "confidence": c.get("confidence"),
                        "can_execute_now": c.get("can_execute_now"),
                    }
                    for c in candidates
                ],
            }
        if rtype == "join_sql_validate":
            return {
                "summary": "完成候选SQL可执行性校验",
                "trace": [f"通过数: {result.get('ok_count')}/{result.get('total')}"],
                "checks_top": (result.get("checks") or [])[:3],
            }
        return {"summary": f"技能输出类型: {rtype}", "trace": []}

    context = {
        "input_payload": payload.input_payload or {},
        "workflow_strategy": wf.strategy_config or {},
        "output_history": {},
    }
    planned_path = [str((s or {}).get("skill_code")) for s in planned_steps]
    default_path = [str((s or {}).get("skill_code")) for s in ordered_steps]
    planning_detail = {
        **(planning_info or {}),
        "planned_path": planned_path,
        "default_path": default_path,
        "planner_chain": [
            "读取编排默认步骤",
            "判断是否使用LLM规划",
            "生成规划路径并去重补全",
        ],
    }
    step_logs = [{"phase": "planning", "status": "success", "detail": planning_detail}]
    outputs = []
    run_status = "success"
    run_error = None

    total_steps = len(planned_steps)
    for step in planned_steps:
        skill_code = (step or {}).get("skill_code")
        required = bool((step or {}).get("required", True))
        step_start = time.time()
        step_no = len([x for x in step_logs if x.get("skill_code")]) + 1
        skill = skill_by_code.get(skill_code)
        if not skill:
            msg = f"技能不存在: {skill_code}"
            step_logs.append(
                {
                    "skill_code": skill_code,
                    "status": "missing",
                    "error": msg,
                    "duration_ms": int((time.time() - step_start) * 1000),
                    "step_no": step_no,
                    "total_steps": total_steps,
                }
            )
            if required:
                run_status = "failed"
                run_error = msg
                break
            run_status = "partial"
            continue

        if (skill.status or "").lower() != "enabled":
            msg = f"技能未启用: {skill_code}"
            step_logs.append(
                {
                    "skill_code": skill_code,
                    "status": "disabled",
                    "error": msg,
                    "duration_ms": int((time.time() - step_start) * 1000),
                    "step_no": step_no,
                    "total_steps": total_steps,
                }
            )
            if required:
                run_status = "failed"
                run_error = msg
                break
            run_status = "partial"
            continue

        try:
            result = _invoke_skill(db=db, skill=skill, step=step, context=context)
            outputs.append(
                {
                    "skill_code": skill_code,
                    "input_payload": context.get("input_payload") or {},
                    "step_config": (step.get("config") if isinstance(step, dict) else {}) or {},
                    "output": result,
                }
            )
            detail_preview = None
            if isinstance(result, dict):
                detail_preview = _build_step_detail(result)
            step_logs.append(
                {
                    "skill_code": skill_code,
                    "status": "success",
                    "duration_ms": int((time.time() - step_start) * 1000),
                    "output_type": result.get("type") if isinstance(result, dict) else None,
                    "used_llm": bool((result or {}).get("used_llm")) if isinstance(result, dict) else False,
                    "detail_preview": detail_preview,
                    "step_no": step_no,
                    "total_steps": total_steps,
                }
            )
            context["last_output"] = result
            if isinstance(result, dict) and result.get("type"):
                context["output_history"][str(result.get("type"))] = result
        except Exception as e:
            msg = str(e)
            step_logs.append(
                {
                    "skill_code": skill_code,
                    "status": "failed",
                    "error": msg,
                    "duration_ms": int((time.time() - step_start) * 1000),
                    "step_no": step_no,
                    "total_steps": total_steps,
                }
            )
            if required:
                run_status = "failed"
                run_error = msg
                break
            run_status = "partial"

    run_item = SmartWorkflowRun(
        workflow_id=wf.id,
        workflow_code=wf.workflow_code,
        app_type=wf.app_type,
        status=run_status,
        input_payload=payload.input_payload or {},
        output_payload={"outputs": outputs},
        step_logs=step_logs,
        error_message=run_error,
    )
    db.add(run_item)
    db.commit()
    db.refresh(run_item)

    return {
        "code": 200,
        "data": {
            "run": _serialize_run(run_item),
            "threshold": CONFIDENCE_THRESHOLD,
            "outputs": outputs,
        },
    }


@router.get("/smart-skill-workflows/{item_id}/runs")
def list_workflow_runs(item_id: str, limit: int = 20, db: Session = Depends(get_db)):
    lim = max(1, min(limit, 200))
    items = db.query(SmartWorkflowRun).order_by(SmartWorkflowRun.created_at.desc()).all()
    runs = [x for x in items if str(x.workflow_id) == str(item_id)][:lim]
    return {"code": 200, "data": [_serialize_run(x) for x in runs]}


# ==================== 类型管理 API ====================

class SkillTypeCreate(BaseModel):
    type_key: str
    type_name: str
    icon: Optional[str] = "fa-puzzle-piece"
    editor_mode: str = "prompt"
    default_template: Optional[str] = None
    description: Optional[str] = None


class SkillTypeUpdate(BaseModel):
    type_name: Optional[str] = None
    icon: Optional[str] = None
    editor_mode: Optional[str] = None
    default_template: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


def _serialize_skill_type(item: SmartSkillType) -> Dict[str, Any]:
    return {
        "id": str(item.id),
        "type_key": item.type_key,
        "type_name": item.type_name,
        "icon": item.icon,
        "editor_mode": item.editor_mode,
        "default_template": item.default_template,
        "description": item.description,
        "enabled": bool(item.enabled),
        "created_at": str(item.created_at) if item.created_at else None,
        "updated_at": str(item.updated_at) if item.updated_at else None,
    }


@router.get("/skill-types")
def list_skill_types(include_disabled: bool = False, db: Session = Depends(get_db)):
    query = db.query(SmartSkillType)
    if not include_disabled:
        query = query.filter(SmartSkillType.enabled == True)
    items = query.order_by(SmartSkillType.created_at.desc()).all()
    return {"code": 200, "data": [_serialize_skill_type(x) for x in items]}


@router.post("/skill-types")
def create_skill_type(payload: SkillTypeCreate, db: Session = Depends(get_db)):
    exists = db.query(SmartSkillType).filter(SmartSkillType.type_key == payload.type_key).first()
    if exists:
        raise HTTPException(status_code=400, detail="类型标识已存在")
    item = SmartSkillType(
        type_key=payload.type_key,
        type_name=payload.type_name,
        icon=payload.icon,
        editor_mode=payload.editor_mode,
        default_template=payload.default_template,
        description=payload.description,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": _serialize_skill_type(item)}


@router.put("/skill-types/{item_id}")
def update_skill_type(item_id: str, payload: SkillTypeUpdate, db: Session = Depends(get_db)):
    item = db.query(SmartSkillType).filter(SmartSkillType.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="类型不存在")
    if payload.type_name is not None:
        item.type_name = payload.type_name
    if payload.icon is not None:
        item.icon = payload.icon
    if payload.editor_mode is not None:
        item.editor_mode = payload.editor_mode
    if payload.default_template is not None:
        item.default_template = payload.default_template
    if payload.description is not None:
        item.description = payload.description
    if payload.enabled is not None:
        item.enabled = payload.enabled
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": _serialize_skill_type(item)}


@router.delete("/skill-types/{item_id}")
def delete_skill_type(item_id: str, db: Session = Depends(get_db)):
    item = db.query(SmartSkillType).filter(SmartSkillType.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="类型不存在")
    # 检查是否有技能在使用此类型
    using_skills = db.query(SmartSkill).filter(SmartSkill.skill_type == item.type_key).count()
    if using_skills > 0:
        raise HTTPException(status_code=400, detail=f"该类型被 {using_skills} 个技能使用，无法删除")
    db.delete(item)
    db.commit()
    return {"code": 200, "message": "已删除"}


# ==================== 更新技能序列化函数 ====================

def _serialize_skill_v2(item: SmartSkill, type_def: Optional[SmartSkillType] = None) -> Dict[str, Any]:
    return {
        "id": str(item.id),
        "skill_code": item.skill_code,
        "skill_name": item.skill_name,
        "app_type": item.app_type,
        "status": item.status,
        "description": item.description,
        "skill_type": item.skill_type,
        "skill_kind": item.skill_kind,
        "version": item.version,
        "skill_content": item.skill_content,
        "skill_descriptor": item.skill_descriptor or {},
        "tags": item.tags or [],
        "target_menu": item.target_menu,
        "input_schema": item.input_schema or [],
        "output_schema": item.output_schema or [],
        "http_config": item.http_config or {"method": "GET", "url": "", "headers": [], "body": ""},
        "dependencies": item.dependencies or [],
        "runtime_config": item.runtime_config or {},
        "created_at": str(item.created_at) if item.created_at else None,
        "updated_at": str(item.updated_at) if item.updated_at else None,
    }


# 更新技能API以支持新字段
@router.get("/smart-skills")
def list_skills_v2(app_type: Optional[str] = None, db: Session = Depends(get_db)):
    items = db.query(SmartSkill).order_by(SmartSkill.created_at.desc()).all()
    if app_type:
        items = [x for x in items if (x.app_type or "").lower() == app_type.lower()]
    types_by_key = {t.type_key: t for t in db.query(SmartSkillType).all()}
    return {"code": 200, "data": [_serialize_skill_v2(x, types_by_key.get(x.skill_type)) for x in items]}


class SkillCreateV2(BaseModel):
    skill_code: str
    skill_name: str
    app_type: Optional[str] = "smart_join"
    description: Optional[str] = None
    skill_type: Optional[str] = "natural"
    skill_kind: Optional[str] = "natural_language"
    skill_content: Optional[str] = None
    tags: Optional[List[str]] = []
    target_menu: Optional[str] = "connection"
    input_schema: Optional[List[Dict[str, Any]]] = []
    output_schema: Optional[List[Dict[str, Any]]] = []
    http_config: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[str]] = []
    runtime_config: Optional[Dict[str, Any]] = None


class SkillUpdateV2(BaseModel):
    skill_name: Optional[str] = None
    app_type: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    skill_type: Optional[str] = None
    skill_kind: Optional[str] = None
    version: Optional[str] = None
    skill_content: Optional[str] = None
    tags: Optional[List[str]] = None
    target_menu: Optional[str] = None
    input_schema: Optional[List[Dict[str, Any]]] = None
    output_schema: Optional[List[Dict[str, Any]]] = None
    http_config: Optional[Dict[str, Any]] = None
    dependencies: Optional[List[str]] = None
    runtime_config: Optional[Dict[str, Any]] = None


def _bump_version(version: str, is_publish: bool = False) -> str:
    try:
        major, minor, patch = map(int, version.split("."))
        if is_publish:
            minor += 1
            patch = 0
        else:
            patch += 1
        return f"{major}.{minor}.{patch}"
    except:
        return is_publish and "0.2.0" or "0.1.1"


@router.post("/smart-skills")
def create_skill_v2(payload: SkillCreateV2, db: Session = Depends(get_db)):
    exists = db.query(SmartSkill).filter(SmartSkill.skill_code == payload.skill_code).first()
    if exists:
        raise HTTPException(status_code=400, detail="skill_code已存在")
    item = SmartSkill(
        skill_code=payload.skill_code,
        skill_name=payload.skill_name,
        app_type=payload.app_type or "smart_join",
        status="draft",
        description=payload.description,
        skill_type=payload.skill_type or "natural",
        skill_kind=payload.skill_kind or "natural_language",
        version="0.1.0",
        skill_content=payload.skill_content,
        tags=payload.tags or [],
        target_menu=payload.target_menu or "connection",
        input_schema=payload.input_schema or [],
        output_schema=payload.output_schema or [],
        http_config=payload.http_config,
        dependencies=payload.dependencies or [],
        runtime_config=payload.runtime_config,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": _serialize_skill_v2(item)}


@router.put("/smart-skills/{item_id}")
def update_skill_v2(item_id: str, payload: SkillUpdateV2, db: Session = Depends(get_db)):
    item = db.query(SmartSkill).filter(SmartSkill.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="skill not found")
    if payload.skill_name is not None:
        item.skill_name = payload.skill_name
    if payload.app_type is not None:
        item.app_type = payload.app_type
    if payload.status is not None:
        item.status = payload.status
    if payload.description is not None:
        item.description = payload.description
    if payload.skill_type is not None:
        item.skill_type = payload.skill_type
    if payload.skill_kind is not None:
        item.skill_kind = payload.skill_kind
    if payload.version is not None:
        item.version = payload.version
    if payload.skill_content is not None:
        item.skill_content = payload.skill_content
    if payload.tags is not None:
        item.tags = payload.tags
    if payload.target_menu is not None:
        item.target_menu = payload.target_menu
    if payload.input_schema is not None:
        item.input_schema = payload.input_schema
    if payload.output_schema is not None:
        item.output_schema = payload.output_schema
    if payload.http_config is not None:
        item.http_config = payload.http_config
    if payload.dependencies is not None:
        item.dependencies = payload.dependencies
    if payload.runtime_config is not None:
        item.runtime_config = payload.runtime_config
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": _serialize_skill_v2(item)}


@router.post("/smart-skills/{item_id}/save-draft")
def save_draft(item_id: str, payload: SkillUpdateV2, db: Session = Depends(get_db)):
    item = db.query(SmartSkill).filter(SmartSkill.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="skill not found")
    # 更新内容
    if payload.skill_name is not None:
        item.skill_name = payload.skill_name
    if payload.description is not None:
        item.description = payload.description
    if payload.skill_content is not None:
        item.skill_content = payload.skill_content
    if payload.tags is not None:
        item.tags = payload.tags
    if payload.input_schema is not None:
        item.input_schema = payload.input_schema
    if payload.output_schema is not None:
        item.output_schema = payload.output_schema
    if payload.http_config is not None:
        item.http_config = payload.http_config
    if payload.dependencies is not None:
        item.dependencies = payload.dependencies
    # 自动升级patch版本号
    item.version = _bump_version(item.version or "0.1.0", is_publish=False)
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": _serialize_skill_v2(item)}


@router.post("/smart-skills/{item_id}/publish")
def publish_skill(item_id: str, db: Session = Depends(get_db)):
    item = db.query(SmartSkill).filter(SmartSkill.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="skill not found")
    item.status = "published"
    item.version = _bump_version(item.version or "0.1.0", is_publish=True)
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": _serialize_skill_v2(item)}

