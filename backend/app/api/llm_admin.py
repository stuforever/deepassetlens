from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import uuid

from ..core.database import get_db
from ..models.base import LLMConnectionConfig, SmartPlannerConfig
from ..services.llm_client import call_openai_compatible_chat, call_openai_compatible_messages, resolve_connection_api_key

router = APIRouter()


class LLMConnectionCreate(BaseModel):
    name: str
    provider: Optional[str] = "openai_compatible"
    capability: Optional[str] = "chat"
    description: Optional[str] = None
    base_url: str
    api_path: Optional[str] = "/chat/completions"
    api_key: Optional[str] = None
    model_name: str
    is_default: Optional[bool] = False
    enabled: Optional[bool] = True
    temperature: Optional[str] = "0.2"
    max_tokens: Optional[int] = 512
    timeout_seconds: Optional[int] = 60
    extra_config: Optional[Dict[str, Any]] = None


class LLMConnectionUpdate(BaseModel):
    provider: Optional[str] = None
    capability: Optional[str] = None
    description: Optional[str] = None
    base_url: Optional[str] = None
    api_path: Optional[str] = None
    api_key: Optional[str] = None
    model_name: Optional[str] = None
    is_default: Optional[bool] = None
    enabled: Optional[bool] = None
    temperature: Optional[str] = None
    max_tokens: Optional[int] = None
    timeout_seconds: Optional[int] = None
    extra_config: Optional[Dict[str, Any]] = None


class PlannerConfigUpdate(BaseModel):
    planner_mode: Optional[str] = "rule"
    llm_connection_id: Optional[str] = None
    enabled: Optional[bool] = True
    system_prompt: Optional[str] = None
    retrieval_mode: Optional[str] = None
    vector_model_name: Optional[str] = None
    vector_model_path: Optional[str] = None
    keyword_weight: Optional[float] = None
    vector_weight: Optional[float] = None
    rerank_enabled: Optional[bool] = None
    query_entity_pipeline_code: Optional[str] = None
    query_entity_workflow_code: Optional[str] = None
    query_attribute_workflow_code: Optional[str] = None


class LLMChatRequest(BaseModel):
    messages: Optional[list] = None
    user_input: Optional[str] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


def _serialize_conn(x: LLMConnectionConfig):
    return {
        "id": str(x.id),
        "name": x.name,
        "provider": x.provider,
        "capability": x.capability or "chat",
        "description": x.description,
        "base_url": x.base_url,
        "api_path": x.api_path,
        "api_key": x.api_key,
        "model_name": x.model_name,
        "is_default": bool(x.is_default),
        "enabled": bool(x.enabled),
        "temperature": x.temperature,
        "max_tokens": x.max_tokens,
        "timeout_seconds": int(x.timeout_seconds or 60),
        "extra_config": x.extra_config or {},
        "created_at": str(x.created_at) if x.created_at else None,
    }


def _sync_default_llm_to_planner(db: Session, llm_connection_id: Optional[str]):
    items = db.query(SmartPlannerConfig).order_by(SmartPlannerConfig.created_at.desc()).all()
    if items:
        item = items[0]
        item.llm_connection_id = llm_connection_id
    else:
        item = SmartPlannerConfig(
            planner_mode="rule",
            llm_connection_id=llm_connection_id,
            enabled=True,
        )
        db.add(item)


def _serialize_planner(x: SmartPlannerConfig):
    return {
        "id": str(x.id),
        "planner_mode": x.planner_mode,
        "llm_connection_id": str(x.llm_connection_id) if x.llm_connection_id else None,
        "enabled": bool(x.enabled),
        "system_prompt": x.system_prompt,
        "retrieval_mode": x.retrieval_mode,
        "vector_model_name": x.vector_model_name,
        "vector_model_path": x.vector_model_path,
        "keyword_weight": x.keyword_weight,
        "vector_weight": x.vector_weight,
        "rerank_enabled": bool(x.rerank_enabled) if x.rerank_enabled is not None else True,
        "query_entity_pipeline_code": x.query_entity_pipeline_code or "query_entity_pipeline",
        "query_entity_workflow_code": x.query_entity_workflow_code or "query_entity_main_workflow",
        "created_at": str(x.created_at) if x.created_at else None,
    }


def _to_uuid_or_none(v):
    if v in (None, "", "null"):
        return None
    try:
        return uuid.UUID(str(v))
    except Exception:
        raise HTTPException(status_code=400, detail=f"非法UUID: {v}")


@router.get("/llm-connections")
def list_llm_connections(db: Session = Depends(get_db)):
    items = db.query(LLMConnectionConfig).order_by(LLMConnectionConfig.created_at.desc()).all()
    return {"code": 200, "data": [_serialize_conn(x) for x in items]}


@router.post("/llm-connections")
def create_llm_connection(payload: LLMConnectionCreate, db: Session = Depends(get_db)):
    data = payload.dict()
    exists = db.query(LLMConnectionConfig).filter(LLMConnectionConfig.name == data["name"]).first()
    if exists:
        raise HTTPException(status_code=400, detail="连接名称已存在")
    if data.get("is_default"):
        db.query(LLMConnectionConfig).update({LLMConnectionConfig.is_default: False})
    item = LLMConnectionConfig(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    if item.is_default:
        _sync_default_llm_to_planner(db, str(item.id))
        db.commit()
    return {"code": 200, "data": _serialize_conn(item)}


@router.put("/llm-connections/{item_id}")
def update_llm_connection(item_id: str, payload: LLMConnectionUpdate, db: Session = Depends(get_db)):
    items = db.query(LLMConnectionConfig).all()
    item = next((x for x in items if str(x.id) == str(item_id)), None)
    if not item:
        raise HTTPException(status_code=404, detail="连接不存在")
    update_data = payload.dict(exclude_unset=True)
    if update_data.get("is_default") is True:
        db.query(LLMConnectionConfig).update({LLMConnectionConfig.is_default: False})
    for k, v in update_data.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    if update_data.get("is_default") is True:
        _sync_default_llm_to_planner(db, str(item.id))
        db.commit()
    elif update_data.get("is_default") is False and not item.is_default:
        default_conn = db.query(LLMConnectionConfig).filter(LLMConnectionConfig.is_default == True).first()  # noqa: E712
        _sync_default_llm_to_planner(db, str(default_conn.id) if default_conn else None)
        db.commit()
    return {"code": 200, "data": _serialize_conn(item)}


@router.delete("/llm-connections/{item_id}")
def delete_llm_connection(item_id: str, db: Session = Depends(get_db)):
    items = db.query(LLMConnectionConfig).all()
    item = next((x for x in items if str(x.id) == str(item_id)), None)
    if not item:
        raise HTTPException(status_code=404, detail="连接不存在")
    was_default = bool(item.is_default)
    db.delete(item)
    db.commit()
    if was_default:
        next_default = (
            db.query(LLMConnectionConfig)
            .filter(LLMConnectionConfig.is_default == True)  # noqa: E712
            .order_by(LLMConnectionConfig.created_at.desc())
            .first()
        )
        _sync_default_llm_to_planner(db, str(next_default.id) if next_default else None)
        db.commit()
    return {"code": 200, "message": "deleted"}


@router.post("/llm-connections/{item_id}/test")
def test_llm_connection(item_id: str, db: Session = Depends(get_db)):
    items = db.query(LLMConnectionConfig).all()
    item = next((x for x in items if str(x.id) == str(item_id)), None)
    if not item:
        raise HTTPException(status_code=404, detail="连接不存在")
    capability = (item.capability or "chat").strip().lower()
    try:
        if capability == "embedding":
            import json as _json
            import urllib.request as _urlrequest
            api_key = resolve_connection_api_key(item.api_key)
            if not api_key:
                return {"code": 200, "data": {"ok": False, "error": "API Key 未配置或环境变量未设置"}}
            base_url = (item.base_url or "").rstrip("/")
            api_path = item.api_path or "/embeddings"
            if not api_path.startswith("/"):
                api_path = f"/{api_path}"
            payload = _json.dumps({
                "model": item.model_name,
                "input": ["ping"],
            }).encode("utf-8")
            req = _urlrequest.Request(
                url=f"{base_url}{api_path}",
                data=payload,
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
                method="POST",
            )
            with _urlrequest.urlopen(req, timeout=float(item.timeout_seconds or 30)) as resp:
                body = _json.loads(resp.read().decode("utf-8"))
            data_rows = body.get("data") or []
            dim = len(data_rows[0].get("embedding", [])) if data_rows else 0
            return {"code": 200, "data": {"ok": True, "response": f"向量模型连接成功，返回维度={dim}", "dimension": dim}}
        resp = call_openai_compatible_chat(
            item,
            system_prompt="你是测试助手，请回答pong。",
            user_prompt="ping",
        )
        return {"code": 200, "data": {"ok": True, "response": resp}}
    except Exception as e:
        import traceback as _tb
        err_detail = f"{type(e).__name__}: {e}"
        print(f"[llm_test] ERROR: {err_detail}\n{_tb.format_exc()}", flush=True)
        return {"code": 200, "data": {"ok": False, "error": err_detail, "traceback": _tb.format_exc()}}


@router.get("/planner-config")
def get_planner_config(db: Session = Depends(get_db)):
    items = db.query(SmartPlannerConfig).order_by(SmartPlannerConfig.created_at.desc()).all()
    if not items:
        return {"code": 200, "data": None}
    return {"code": 200, "data": _serialize_planner(items[0])}


@router.put("/planner-config")
def upsert_planner_config(payload: PlannerConfigUpdate, db: Session = Depends(get_db)):
    data = payload.dict(exclude_unset=True)
    if "llm_connection_id" in data:
        data["llm_connection_id"] = _to_uuid_or_none(data.get("llm_connection_id"))

    items = db.query(SmartPlannerConfig).order_by(SmartPlannerConfig.created_at.desc()).all()
    if items:
        item = items[0]
        for k, v in data.items():
            setattr(item, k, v)
    else:
        item = SmartPlannerConfig(**data)
        db.add(item)
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": _serialize_planner(item)}


@router.post("/llm-connections/{item_id}/chat")
def chat_with_llm_connection(item_id: str, payload: LLMChatRequest, db: Session = Depends(get_db)):
    items = db.query(LLMConnectionConfig).all()
    item = next((x for x in items if str(x.id) == str(item_id)), None)
    if not item:
        raise HTTPException(status_code=404, detail="连接不存在")
    if not item.enabled:
        raise HTTPException(status_code=400, detail="连接未启用")

    messages = payload.messages if isinstance(payload.messages, list) else []
    if payload.system_prompt:
        messages = [{"role": "system", "content": payload.system_prompt}] + messages
    if payload.user_input:
        messages = messages + [{"role": "user", "content": payload.user_input}]
    if not messages:
        raise HTTPException(status_code=400, detail="messages或user_input至少提供一个")

    resp = call_openai_compatible_messages(
        item,
        messages=messages,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
    )
    answer = (
        (((resp or {}).get("choices") or [{}])[0].get("message") or {}).get("content")
        or ""
    )
    return {"code": 200, "data": {"answer": answer, "raw": resp}}
