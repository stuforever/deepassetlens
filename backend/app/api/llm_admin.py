from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import uuid
import logging

from ..core.database import get_db
from ..models.base import LLMConnectionConfig, SmartPlannerConfig
from ..services.llm_client import call_openai_compatible_chat, call_openai_compatible_messages, resolve_connection_api_key

logger = logging.getLogger(__name__)

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
    capabilities: Optional[Dict[str, bool]] = None   # ③模型目录化：能力位（白名单键）

    @field_validator("capabilities")
    @classmethod
    def _caps_whitelist(cls, v):
        if v is None:
            return v
        unknown = set(v) - {"tool_call", "vision", "json_mode", "stream"}
        if unknown:
            raise ValueError(f"未知能力键: {sorted(unknown)}（白名单: tool_call/vision/json_mode/stream）")
        return v


class LLMConnectionUpdate(BaseModel):
    name: Optional[str] = None
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
    capabilities: Optional[Dict[str, bool]] = None   # ③模型目录化：能力位（白名单键）

    @field_validator("capabilities")
    @classmethod
    def _caps_whitelist(cls, v):
        if v is None:
            return v
        unknown = set(v) - {"tool_call", "vision", "json_mode", "stream"}
        if unknown:
            raise ValueError(f"未知能力键: {sorted(unknown)}（白名单: tool_call/vision/json_mode/stream）")
        return v


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
        "capabilities": x.capabilities,   # ③模型目录化：能力位原样回显（None=读取端 D5 默认兜底）
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


@router.post("/llm-connections/{item_id}/duplicate")
def duplicate_llm_connection(item_id: str, db: Session = Depends(get_db)):
    """复制连接：拷贝全部配置（含 api_key），名称加" 副本"后缀并去重，is_default=False。"""
    src = next((x for x in db.query(LLMConnectionConfig).all() if str(x.id) == str(item_id)), None)
    if not src:
        raise HTTPException(status_code=404, detail="连接不存在")
    base_name = (src.name or "").rstrip()
    new_name = f"{base_name} 副本"
    # 名称去重：已存在则追加 (2)(3)...
    if db.query(LLMConnectionConfig).filter(LLMConnectionConfig.name == new_name).first():
        n = 2
        while db.query(LLMConnectionConfig).filter(LLMConnectionConfig.name == f"{base_name} 副本({n})").first():
            n += 1
        new_name = f"{base_name} 副本({n})"
    item = LLMConnectionConfig(
        name=new_name,
        provider=src.provider,
        capability=src.capability,
        description=src.description,
        base_url=src.base_url,
        api_path=src.api_path,
        api_key=src.api_key,
        model_name=src.model_name,
        is_default=False,
        enabled=bool(src.enabled),
        temperature=src.temperature,
        max_tokens=src.max_tokens,
        timeout_seconds=src.timeout_seconds,
        extra_config=src.extra_config,
        capabilities=src.capabilities,   # ③模型目录化：复制含能力位
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": _serialize_conn(item)}


@router.put("/llm-connections/{item_id}")
def update_llm_connection(item_id: str, payload: LLMConnectionUpdate, db: Session = Depends(get_db)):
    items = db.query(LLMConnectionConfig).all()
    item = next((x for x in items if str(x.id) == str(item_id)), None)
    if not item:
        raise HTTPException(status_code=404, detail="连接不存在")
    update_data = payload.dict(exclude_unset=True)
    # 名称唯一性校验
    if update_data.get("name") and update_data["name"] != item.name:
        existing = db.query(LLMConnectionConfig).filter(LLMConnectionConfig.name == update_data["name"]).first()
        if existing:
            raise HTTPException(status_code=400, detail="连接名称已存在")
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


def _probe_tool_call(item) -> bool:
    """③spec §4.3：测试消息带一个 tool 定义，响应含 tool_calls 即 true（照 embedding 分支
    raw urllib 先例，不动 call_openai_compatible_chat）。"""
    import json as _pj
    import urllib.request as _purl
    api_key = resolve_connection_api_key(item.api_key)
    if not api_key:
        return False
    base_url = (item.base_url or "").rstrip("/")
    api_path = item.api_path or "/chat/completions"
    if not api_path.startswith("/"):
        api_path = f"/{api_path}"
    payload = _pj.dumps({
        "model": item.model_name,
        "messages": [{"role": "user", "content": "请调用工具回复 pong"}],
        "tools": [{"type": "function", "function": {"name": "ping_tool",
                   "description": "连通性探测", "parameters": {"type": "object", "properties": {}}}}],
        "tool_choice": "auto"}).encode("utf-8")
    req = _purl.Request(url=f"{base_url}{api_path}", data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}, method="POST")
    with _purl.urlopen(req, timeout=float(item.timeout_seconds or 30)) as resp:
        body = _pj.loads(resp.read().decode("utf-8"))
    msg = (body.get("choices") or [{}])[0].get("message") or {}
    return bool(msg.get("tool_calls"))


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
        # ③模型目录化（spec §4.3）：实测探测+声明对账（mismatch=声明≠实测，前端提示一键回填）。
        from app.services.tupu_deepagent import _capabilities_of
        _declared = _capabilities_of(item.capabilities).get("tool_call")
        _detected = _probe_tool_call(item)
        return {"code": 200, "data": {"ok": True, "response": resp,
                "detected": {"tool_call": _detected},
                "mismatch": bool(_detected) != bool(_declared)}}
    except Exception as e:
        import traceback as _tb
        err_detail = f"{type(e).__name__}: {e}"
        logger.error(f"[llm_test] ERROR: {err_detail}\n{_tb.format_exc()}")
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


# ===== ③模型目录化（spec §4.1/§4.3/§六）：能力位列迁移+回填端点 =====

_D5_DEFAULTS = {"tool_call": True, "vision": False, "json_mode": False, "stream": True}


def _ensure_capabilities_column(db) -> None:
    """③（spec §六步骤1）：列+存量回填，幂等。chat→tool_call=true（在跑工具调用=既成事实）；
    embedding→false（不装配 Agent，防误指向）。"""
    import json as _json
    from sqlalchemy import text
    n = db.execute(text(
        "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema=DATABASE() "
        "AND table_name='kg_llm_connection_configs' AND column_name='capabilities'")).scalar()
    if not n:
        db.execute(text("ALTER TABLE kg_llm_connection_configs ADD COLUMN capabilities JSON NULL"))
        db.execute(text(
            "UPDATE kg_llm_connection_configs SET capabilities = "
            "CASE WHEN LOWER(TRIM(IFNULL(capability,'chat')))='embedding' THEN :e ELSE :c END"),
            {"e": _json.dumps({**_D5_DEFAULTS, "tool_call": False}),
             "c": _json.dumps(_D5_DEFAULTS)})
        db.commit()


@router.put("/llm-connections/{item_id}/capabilities")
def backfill_capabilities(item_id: str, body: dict, db: Session = Depends(get_db)):
    """实测回填（spec §4.3）：body=能力位字典（白名单校验复用 Update schema 语义）。
    声明优先+实测校准——本端点只做显式回填动作，不改门控语义。"""
    from pydantic import ValidationError
    caps = (body or {}).get("capabilities")
    if caps is None:
        raise HTTPException(status_code=422, detail="capabilities 必填（能力位字典）")
    try:
        LLMConnectionUpdate(capabilities=caps)
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=str(ve.errors()[0].get("msg", "校验失败")))
    item = db.query(LLMConnectionConfig).filter(LLMConnectionConfig.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="连接不存在")
    item.capabilities = caps
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": _serialize_conn(item)}
