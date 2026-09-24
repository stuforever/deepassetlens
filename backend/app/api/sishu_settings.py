# -*- coding: utf-8 -*-
"""批11深水：settings 平台路由——vendor settings.py 消费面 1:1（27 端点）。

承接（前端消费面+管理面，底层全走移植件）：
  GET ""（ui/catalog/providers 组合）、PUT /catalog、POST /apply、
  PUT /ui /theme /language /voice-autoplay /chat-response-timeout /enabled-tools、
  POST /reset、GET/PUT /network、GET/PUT /chat-attachments、GET /llm-options、
  GET /themes、GET /sidebar、PUT /sidebar/description、PUT /sidebar/nav-order、
  POST /tests/{service}/start、GET /tests/{service}/{run_id}/events(SSE)、
  POST /tests/{service}/{run_id}/cancel。

vendor 续服务（重闭包低频面，台账登记）：providers/openai-codex/oauth×5、
  mineru×7、document-parsing×8、fetch-models、tour×3。
本平台路由全静态径（无参数路由）——对 vendor 续服务面零遮挡（E-92 教训）。

数据面：与 vendor 同文件（path_service settings/interface.json）——
零漂移构造；PG 配置表③=数据层远期池（协议 F⑤，不动端点形状）。
USER_TOGGLEABLE_TOOL_NAMES=7 工具名内联冻结（纯数据常量；工具运行时
本体=引擎域远期池，随 GET /api/v1/tools 一并 vendor 续服务）。
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.sishu.compat.context import get_current_user
from app.services.sishu.compat.model_access import allowed_llm_options
from app.services.sishu.services.config import (
    get_config_test_runner,
    get_model_catalog_service,
    get_runtime_settings_service,
)
from app.services.sishu.services.config.origins import normalize_origins
from app.services.sishu.services.config.runtime_settings import (
    CHAT_ATTACHMENT_CHARS_RANGE,
    CHAT_ATTACHMENT_MAX_FILE_MB_RANGE,
    CHAT_ATTACHMENT_MAX_TOTAL_MB_RANGE,
    compute_ws_max_size,
)
from app.services.sishu.services.embedding.client import reset_embedding_client
from app.services.sishu.services.llm.client import reset_llm_client
from app.services.sishu.services.llm.config import clear_llm_config_cache
from app.services.sishu.services.model_selection import list_llm_options
from app.services.sishu.services.path_service import get_path_service

logger = logging.getLogger(__name__)

router = APIRouter()

# 数据常量内联冻结（vendor tools/builtin.USER_TOGGLEABLE_TOOL_NAMES 当前值——
# 纯名单数据；上游修订需同步本表（复刻纪律回灌点）。
USER_TOGGLEABLE_TOOL_NAMES = frozenset({
    "brainstorm",
    "geogebra_analysis",
    "imagegen",
    "paper_search",
    "reason",
    "videogen",
    "web_search",
})

DEFAULT_SIDEBAR_NAV_ORDER = {
    "start": ["/", "/history", "/knowledge", "/notebook"],
    "learnResearch": ["/question", "/solver", "/research", "/co_writer"],
}

DEFAULT_UI_SETTINGS = {
    "theme": "snow",
    "language": "en",
    "sidebar_description": "✨ Data Intelligence Lab @ HKU",
    "sidebar_nav_order": DEFAULT_SIDEBAR_NAV_ORDER,
    "enabled_optional_tools": sorted(USER_TOGGLEABLE_TOOL_NAMES),
    "voice_autoplay": False,
    "chat_response_timeout": 180,
}

CHAT_RESPONSE_TIMEOUT_MIN = 30
CHAT_RESPONSE_TIMEOUT_MAX = 1800


class SidebarNavOrder(BaseModel):
    start: List[str]
    learnResearch: List[str]


class UISettingsUpdate(BaseModel):
    theme: Literal["light", "dark", "glass", "snow"] | None = None
    language: Literal["zh", "en"] | None = None
    sidebar_description: str | None = None
    sidebar_nav_order: SidebarNavOrder | None = None
    code_block_theme: str | None = None
    code_block_show_line_numbers: bool | None = None
    code_block_wrap_long_lines: bool | None = None


class VoiceAutoplayUpdate(BaseModel):
    voice_autoplay: bool


class ChatResponseTimeoutUpdate(BaseModel):
    chat_response_timeout: int = Field(ge=CHAT_RESPONSE_TIMEOUT_MIN, le=CHAT_RESPONSE_TIMEOUT_MAX)


class ThemeUpdate(BaseModel):
    theme: Literal["light", "dark", "glass", "snow"]


class LanguageUpdate(BaseModel):
    language: Literal["zh", "en"]


class SidebarDescriptionUpdate(BaseModel):
    description: str


class SidebarNavOrderUpdate(BaseModel):
    nav_order: SidebarNavOrder


class EnabledToolsUpdate(BaseModel):
    enabled_tools: List[str]


class CatalogPayload(BaseModel):
    catalog: dict[str, Any]


class NetworkSettingsUpdate(BaseModel):
    backend_port: int = Field(ge=1, le=65535)
    frontend_port: int = Field(ge=1, le=65535)
    public_api_base: str = ""
    cors_origins: list[str] = Field(default_factory=list)


class ChatAttachmentSettingsUpdate(BaseModel):
    max_file_mb: int = Field(
        ge=CHAT_ATTACHMENT_MAX_FILE_MB_RANGE[0], le=CHAT_ATTACHMENT_MAX_FILE_MB_RANGE[1]
    )
    max_total_mb: int = Field(
        ge=CHAT_ATTACHMENT_MAX_TOTAL_MB_RANGE[0], le=CHAT_ATTACHMENT_MAX_TOTAL_MB_RANGE[1]
    )
    max_chars_per_doc: int = Field(ge=CHAT_ATTACHMENT_CHARS_RANGE[0], le=CHAT_ATTACHMENT_CHARS_RANGE[1])
    max_chars_total: int = Field(ge=CHAT_ATTACHMENT_CHARS_RANGE[0], le=CHAT_ATTACHMENT_CHARS_RANGE[1])


def _settings_file():
    return get_path_service().get_settings_file("interface")


def _tour_cache_file():
    return get_path_service().get_settings_dir() / ".tour_cache.json"


def _invalidate_runtime_caches() -> None:
    """1:1 vendor settings.py _invalidate_runtime_caches。"""
    logger.warning(
        "Admin applied catalog; resetting global LLM/embedding clients. "
        "In-flight user turns may flip backend client mid-call."
    )
    clear_llm_config_cache()
    reset_llm_client()
    reset_embedding_client()


def load_ui_settings() -> dict[str, Any]:
    settings_file = _settings_file()
    if settings_file.exists():
        try:
            with open(settings_file, encoding="utf-8") as handle:
                saved = json.load(handle)
                merged = {**DEFAULT_UI_SETTINGS, **saved}
                merged["enabled_optional_tools"] = _sanitize_enabled_tools(
                    merged.get("enabled_optional_tools")
                )
                return merged
        except Exception:
            pass
    return DEFAULT_UI_SETTINGS.copy()


def _sanitize_enabled_tools(value: Any) -> list[str]:
    if not isinstance(value, list):
        return sorted(USER_TOGGLEABLE_TOOL_NAMES)
    allowed = set(USER_TOGGLEABLE_TOOL_NAMES)
    seen: set[str] = set()
    out: list[str] = []
    for name in value:
        if isinstance(name, str) and name in allowed and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def get_enabled_optional_tools() -> list[str]:
    """vendor 同款（chat 管线消费——本件暴露供平台 chat 栈使用）。

    注：vendor 原版在此与 multi_user.tool_access 授权白名单求交——授权面
    属 multi_user 域远期池；auth=0 直通语义下两版同行为（allowed=None）。
    """
    return _sanitize_enabled_tools(load_ui_settings().get("enabled_optional_tools"))


def save_ui_settings(settings: dict[str, Any]) -> None:
    settings_file = _settings_file()
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_file, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, ensure_ascii=False, indent=2)


import hmac as _hmac
import uuid as _uuid

# UX批（反馈测试运行）：诊断 SSE 凭据——EventSource 带不了 Authorization 头，
# start（已鉴权）铸造一次性 run_token，events/cancel 凭 token 放行
_RUN_TOKENS: dict[str, str] = {}


def _require_settings_admin() -> None:
    if not get_current_user().is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Model configuration is managed by an administrator.",
        )


def _provider_choices() -> dict[str, list[dict[str, Any]]]:
    """1:1 vendor settings.py _provider_choices（目录选项——③数据面）。"""
    from app.services.sishu.services.config.provider_runtime import (
        EMBEDDING_PROVIDERS,
        IMAGEGEN_PROVIDERS,
        STT_PROVIDERS,
        TTS_PROVIDERS,
        VIDEOGEN_PROVIDERS,
    )
    from app.services.sishu.services.provider_registry import PROVIDERS

    llm = sorted(
        [
            {
                "value": s.name,
                "label": (
                    "Custom (OpenAI API)"
                    if s.name == "custom"
                    else "Custom (Anthropic API)"
                    if s.name == "custom_anthropic"
                    else s.label
                ),
                "base_url": s.default_api_base,
                "auth_mode": s.auth_mode,
            }
            for s in PROVIDERS
        ],
        key=lambda p: p["label"].lower(),
    )
    embedding = sorted(
        [
            {
                "value": name,
                "label": spec.label,
                "base_url": spec.default_api_base,
                "default_dim": str(spec.default_dim) if spec.default_dim else "",
            }
            for name, spec in EMBEDDING_PROVIDERS.items()
            if name != "custom_openai_sdk"
        ],
        key=lambda p: p["label"].lower(),
    )
    search = [
        {"value": "none", "label": "None", "base_url": ""},
        {"value": "brave", "label": "Brave", "base_url": ""},
        {"value": "tavily", "label": "Tavily", "base_url": ""},
        {"value": "jina", "label": "Jina", "base_url": ""},
        {"value": "searxng", "label": "SearXNG", "base_url": ""},
        {"value": "duckduckgo", "label": "DuckDuckGo", "base_url": ""},
        {"value": "perplexity", "label": "Perplexity", "base_url": ""},
        {"value": "serper", "label": "Serper", "base_url": ""},
    ]
    tts = sorted(
        [
            {
                "value": name,
                "label": spec.label,
                "base_url": spec.default_api_base,
                "default_model": spec.default_model,
                "default_voice": spec.default_voice,
            }
            for name, spec in TTS_PROVIDERS.items()
        ],
        key=lambda p: p["label"].lower(),
    )
    stt = sorted(
        [
            {
                "value": name,
                "label": spec.label,
                "base_url": spec.default_api_base,
                "default_model": spec.default_model,
            }
            for name, spec in STT_PROVIDERS.items()
        ],
        key=lambda p: p["label"].lower(),
    )
    imagegen = sorted(
        [
            {
                "value": name,
                "label": spec.label,
                "base_url": spec.default_api_base,
                "default_model": spec.default_model,
            }
            for name, spec in IMAGEGEN_PROVIDERS.items()
        ],
        key=lambda p: p["label"].lower(),
    )
    videogen = sorted(
        [
            {
                "value": name,
                "label": spec.label,
                "base_url": spec.default_api_base,
                "default_model": spec.default_model,
            }
            for name, spec in VIDEOGEN_PROVIDERS.items()
        ],
        key=lambda p: p["label"].lower(),
    )
    return {
        "llm": llm,
        "embedding": embedding,
        "search": search,
        "tts": tts,
        "stt": stt,
        "imagegen": imagegen,
        "videogen": videogen,
    }


def _api_base_source(system: dict[str, Any]) -> str:
    if system.get("next_public_api_base_external"):
        return "next_public_api_base_external"
    if system.get("next_public_api_base"):
        return "next_public_api_base"
    return "default_backend_url"


def _network_settings_payload() -> dict[str, Any]:
    service = get_runtime_settings_service()
    file_system = service.load_system(include_process_overrides=False)
    effective_system = service.load_system(include_process_overrides=True)
    auth = service.load_auth(include_process_overrides=True)
    backend_url = f"http://localhost:{effective_system['backend_port']}"
    browser_api_base = (
        effective_system["next_public_api_base_external"]
        or effective_system["next_public_api_base"]
        or backend_url
    )
    cors_origins = normalize_origins(
        [effective_system["cors_origin"], effective_system["cors_origins"]]
    )
    auth_enabled = bool(auth["enabled"])
    cookie_secure = bool(auth["cookie_secure"])
    return {
        "settings": {
            "backend_port": file_system["backend_port"],
            "frontend_port": file_system["frontend_port"],
            "public_api_base": file_system["next_public_api_base_external"],
            "cors_origins": normalize_origins(
                [file_system["cors_origin"], file_system["cors_origins"]]
            ),
        },
        "effective": {
            "backend_url": backend_url,
            "frontend_url": f"http://localhost:{effective_system['frontend_port']}",
            "browser_api_base": browser_api_base,
            "api_base_source": _api_base_source(effective_system),
            "cors_mode": "explicit" if auth_enabled else "permissive",
            "cors_origins": cors_origins,
            "allow_remote_http_origins": not auth_enabled,
        },
        "auth": {
            "enabled": auth_enabled,
            "cookie_secure": cookie_secure,
            "cookie_samesite": "none" if cookie_secure else "lax",
            "cross_site_cookie_ready": bool(auth_enabled and cookie_secure),
        },
        "restart_required": True,
    }


def _chat_attachments_payload() -> dict[str, Any]:
    service = get_runtime_settings_service()
    stored = service.load_system(include_process_overrides=False)
    effective = service.load_system(include_process_overrides=True)
    max_total_bytes = int(effective["chat_attachment_max_total_mb"]) * 1024 * 1024
    return {
        "settings": {
            "max_file_mb": stored["chat_attachment_max_file_mb"],
            "max_total_mb": stored["chat_attachment_max_total_mb"],
            "max_chars_per_doc": stored["chat_attachment_max_chars_per_doc"],
            "max_chars_total": stored["chat_attachment_max_chars_total"],
        },
        "effective": {
            "max_file_bytes": int(effective["chat_attachment_max_file_mb"]) * 1024 * 1024,
            "max_total_bytes": max_total_bytes,
            "max_chars_per_doc": effective["chat_attachment_max_chars_per_doc"],
            "max_chars_total": effective["chat_attachment_max_chars_total"],
            "ws_max_size": compute_ws_max_size(max_total_bytes),
        },
        "bounds": {
            "max_file_mb": list(CHAT_ATTACHMENT_MAX_FILE_MB_RANGE),
            "max_total_mb": list(CHAT_ATTACHMENT_MAX_TOTAL_MB_RANGE),
            "chars": list(CHAT_ATTACHMENT_CHARS_RANGE),
        },
        "restart_required_for_larger_uploads": True,
    }


@router.get("")
async def get_settings():
    user = get_current_user()
    if not user.is_admin:
        return {"ui": load_ui_settings()}
    return {
        "ui": load_ui_settings(),
        "catalog": get_model_catalog_service().load(),
        "providers": _provider_choices(),
    }


@router.get("/catalog")
async def get_catalog():
    _require_settings_admin()
    return {"catalog": get_model_catalog_service().load()}


@router.put("/catalog")
async def update_catalog(payload: CatalogPayload):
    _require_settings_admin()
    catalog = get_model_catalog_service().save(payload.catalog)
    _invalidate_runtime_caches()
    return {"catalog": catalog}


@router.post("/apply")
async def apply_catalog(payload: CatalogPayload | None = None):
    _require_settings_admin()
    catalog = payload.catalog if payload is not None else get_model_catalog_service().load()
    applied = get_model_catalog_service().apply(catalog)
    _invalidate_runtime_caches()
    return {
        "message": "Catalog applied to runtime settings.",
        "catalog": get_model_catalog_service().load(),
        "runtime": applied,
    }


@router.get("/llm-options")
async def get_llm_options():
    if not get_current_user().is_admin:
        return allowed_llm_options()
    return list_llm_options(get_model_catalog_service().load())


@router.get("/network")
async def get_network_settings():
    _require_settings_admin()
    return _network_settings_payload()


@router.put("/network")
async def update_network_settings(payload: NetworkSettingsUpdate):
    _require_settings_admin()
    service = get_runtime_settings_service()
    current = service.load_system(include_process_overrides=False)
    service.save_system(
        {
            **current,
            "backend_port": payload.backend_port,
            "frontend_port": payload.frontend_port,
            "next_public_api_base_external": payload.public_api_base,
            "cors_origins": payload.cors_origins,
            "cors_origin": "",
        }
    )
    return _network_settings_payload()


@router.get("/chat-attachments")
async def get_chat_attachment_settings():
    return _chat_attachments_payload()


@router.put("/chat-attachments")
async def update_chat_attachment_settings(payload: ChatAttachmentSettingsUpdate):
    _require_settings_admin()
    service = get_runtime_settings_service()
    current = service.load_system(include_process_overrides=False)
    service.save_system(
        {
            **current,
            "chat_attachment_max_file_mb": payload.max_file_mb,
            "chat_attachment_max_total_mb": payload.max_total_mb,
            "chat_attachment_max_chars_per_doc": payload.max_chars_per_doc,
            "chat_attachment_max_chars_total": payload.max_chars_total,
        }
    )
    return _chat_attachments_payload()


@router.put("/theme")
async def update_theme(update: ThemeUpdate):
    current_ui = load_ui_settings()
    current_ui["theme"] = update.theme
    save_ui_settings(current_ui)
    return {"theme": update.theme}


@router.put("/language")
async def update_language(update: LanguageUpdate):
    current_ui = load_ui_settings()
    current_ui["language"] = update.language
    save_ui_settings(current_ui)
    return {"language": update.language}


@router.put("/voice-autoplay")
async def update_voice_autoplay(update: VoiceAutoplayUpdate):
    current_ui = load_ui_settings()
    current_ui["voice_autoplay"] = update.voice_autoplay
    save_ui_settings(current_ui)
    return {"voice_autoplay": update.voice_autoplay}


@router.put("/chat-response-timeout")
async def update_chat_response_timeout(update: ChatResponseTimeoutUpdate):
    current_ui = load_ui_settings()
    current_ui["chat_response_timeout"] = update.chat_response_timeout
    save_ui_settings(current_ui)
    return {"chat_response_timeout": update.chat_response_timeout}


@router.put("/ui")
async def update_ui_settings(update: UISettingsUpdate):
    current_ui = load_ui_settings()
    dump = update.model_dump(exclude_unset=True)
    current_ui.update(dump)
    save_ui_settings(current_ui)
    return current_ui


@router.post("/reset")
async def reset_settings():
    _require_settings_admin()
    save_ui_settings(DEFAULT_UI_SETTINGS)
    return DEFAULT_UI_SETTINGS


@router.get("/themes")
async def get_themes():
    return {
        "themes": [
            {"id": "snow", "name": "Default"},
            {"id": "light", "name": "Cream"},
            {"id": "dark", "name": "Dark"},
            {"id": "glass", "name": "Glass"},
        ]
    }


@router.get("/sidebar")
async def get_sidebar_settings():
    current_ui = load_ui_settings()
    return {
        "description": current_ui.get(
            "sidebar_description", DEFAULT_UI_SETTINGS["sidebar_description"]
        ),
        "nav_order": current_ui.get("sidebar_nav_order", DEFAULT_UI_SETTINGS["sidebar_nav_order"]),
    }


@router.put("/sidebar/description")
async def update_sidebar_description(update: SidebarDescriptionUpdate):
    current_ui = load_ui_settings()
    current_ui["sidebar_description"] = update.description
    save_ui_settings(current_ui)
    return {"description": update.description}


@router.put("/sidebar/nav-order")
async def update_sidebar_nav_order(update: SidebarNavOrderUpdate):
    current_ui = load_ui_settings()
    current_ui["sidebar_nav_order"] = update.nav_order.model_dump()
    save_ui_settings(current_ui)
    return {"nav_order": update.nav_order.model_dump()}


@router.put("/enabled-tools")
async def update_enabled_tools(update: EnabledToolsUpdate):
    sanitized = _sanitize_enabled_tools(update.enabled_tools)
    current_ui = load_ui_settings()
    current_ui["enabled_optional_tools"] = sanitized
    save_ui_settings(current_ui)
    return {"enabled_optional_tools": sanitized}


@router.post("/tests/{service}/start")
async def start_service_test(service: str, payload: CatalogPayload | None = None):
    _require_settings_admin()
    run = get_config_test_runner().start(service, payload.catalog if payload else None)
    _tok = _uuid.uuid4().hex
    _RUN_TOKENS[run.id] = _tok
    return {"run_id": run.id, "run_token": _tok}


@router.get("/tests/{service}/{run_id}/events")
async def stream_service_test_events(service: str, run_id: str, request: Request, run_token: str = ""):
    _expected = _RUN_TOKENS.get(run_id)
    if not (_expected and _hmac.compare_digest(_expected, str(run_token))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="诊断流凭据无效")
    _RUN_TOKENS.pop(run_id, None)
    runner = get_config_test_runner()
    run = runner.get(run_id)

    async def event_stream():
        sent = 0
        while True:
            if await request.is_disconnected():
                return
            events = run.snapshot(sent)
            if events:
                for event in events:
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                sent += len(events)
                if events[-1]["type"] in {"completed", "failed"}:
                    return
            else:
                yield "event: heartbeat\ndata: {}\n\n"
            await asyncio.sleep(0.35)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/tests/{service}/{run_id}/poll")
async def poll_service_test_events(service: str, run_id: str):
    """UX批：轮询式诊断事件查询（替代 SSE EventSource——fetch 可带 Bearer 头）。"""
    _require_settings_admin()
    runner = get_config_test_runner()
    run = runner.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="诊断运行不存在")
    return {"events": run.snapshot(0), "status": run.status if hasattr(run, 'status') else "running"}


@router.post("/tests/{service}/{run_id}/cancel")
async def cancel_service_test(service: str, run_id: str, run_token: str = ""):
    _expected = _RUN_TOKENS.get(run_id)
    if not (_expected and _hmac.compare_digest(_expected, str(run_token))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="诊断流凭据无效")
    _RUN_TOKENS.pop(run_id, None)
    get_config_test_runner().cancel(run_id)
    return {"message": "Cancelled"}
