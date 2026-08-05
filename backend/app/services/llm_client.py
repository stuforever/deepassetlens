"""LLM 客户端 - 基于 langchain-openai ChatOpenAI 标准化实现

阶段二升级：从手写 urllib 改为 langchain-openai ChatOpenAI
  - 支持流式输出（call_openai_compatible_chat_stream）
  - 多供应商开箱即用（OpenAI 兼容接口）
  - 保留 DB LLMConnectionConfig 配置驱动
  - 保留 LangSmith trace 埋点
  - 函数签名完全兼容（调用方无需改动）

环境变量：
    LANGSMITH_API_KEY  - trace 上报（trace_wrapper 处理）
"""
import os
import json
import logging
from typing import Any, Dict, List, Optional, Iterator

logger = logging.getLogger(__name__)


def resolve_connection_api_key(api_key: Optional[str]) -> str:
    """解析 API Key，支持 ${ENV_VAR} 占位符"""
    value = (api_key or "").strip()
    if value and not value.startswith("${"):
        return value
    if value.startswith("${") and value.endswith("}"):
        env_name = value[2:-1].strip()
        if env_name:
            return os.environ.get(env_name, "").strip()
    return value


def get_default_llm_connection(capability: str = "chat"):
    """从数据库查默认 LLM 连接配置（enabled + capability + is_default 优先）。

    Args:
        capability: 能力类型（chat/embedding），默认 chat

    Returns:
        LLMConnectionConfig ORM 对象，未找到返回 None
    """
    try:
        from app.core.database import SessionLocal
        from app.models.base import LLMConnectionConfig
        db = SessionLocal()
        try:
            return (
                db.query(LLMConnectionConfig)
                .filter(LLMConnectionConfig.enabled == True)  # noqa: E712
                .filter(LLMConnectionConfig.capability == capability)
                .order_by(LLMConnectionConfig.is_default.desc())
                .first()
            )
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[llm_client] 查默认 LLM 连接失败: {e}")
        return None


def get_llm_connection_by_id(connection_id: str, capability: str = "chat"):
    """按 id 取一条 LLM 连接（须 enabled + 指定 capability），用于让用户显式选模型。

    Args:
        connection_id: LLMConnectionConfig.id
        capability: 能力类型，默认 chat

    Returns:
        LLMConnectionConfig ORM 对象，未找到/禁用返回 None
    """
    try:
        from app.core.database import SessionLocal
        from app.models.base import LLMConnectionConfig
        db = SessionLocal()
        try:
            return (
                db.query(LLMConnectionConfig)
                .filter(LLMConnectionConfig.id == connection_id)
                .filter(LLMConnectionConfig.enabled == True)  # noqa: E712
                .filter(LLMConnectionConfig.capability == capability)
                .first()
            )
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"[llm_client] 按 id 查 LLM 连接失败: {e}")
        return None


def get_chat_model(
    *,
    capability: str = "chat",
    temperature: Optional[float] = None,
    timeout: Optional[float] = None,
    streaming: bool = False,
    extra_payload: Optional[Dict[str, Any]] = None,
):
    """统一 LLM 入口：从数据库读默认 chat 配置，构建 langchain ChatOpenAI 实例。

    所有需要 LLM 的地方都应走此函数，确保配置和超时统一来自后台 LLMConnectionConfig 表。
    优先级：显式参数 > 数据库字段 > 兜底默认值。

    Args:
        capability: 能力类型（chat/embedding），默认 chat
        temperature: 覆盖温度（None 则用数据库 temperature，再兜底 0.0）
        timeout: 覆盖超时秒数（None 则用数据库 timeout_seconds，再兜底 120）
        streaming: 是否启用流式
        extra_payload: 额外参数透传（如 thinking.type=disabled）

    Returns:
        langchain_openai.ChatOpenAI 实例

    Raises:
        RuntimeError: 数据库无可用 LLM 配置
    """
    conn = get_default_llm_connection(capability)
    if not conn:
        raise RuntimeError(f"LLM 模型不可用，请检查 kg_llm_connection_configs 表（capability={capability}）")

    # 温度：显式 > 数据库 > 0.0
    temp = temperature if temperature is not None else float(getattr(conn, "temperature", 0.0) or 0.0)
    # 超时：显式 > 数据库 timeout_seconds > 120 兜底
    tmo = float(timeout or getattr(conn, "timeout_seconds", 120) or 120)

    # 读取 LLM 配置的默认模式：deep -> 启用 thinking
    extra = getattr(conn, "extra_config", None) or {}
    default_mode = extra.get("default_mode", "quick") if isinstance(extra, dict) else "quick"
    merged_payload = dict(extra_payload or {})
    if default_mode == "deep":
        # 深度思考模式：注入 thinking 参数（模型不支持则忽略，不报错）
        merged_payload.setdefault("thinking", {"type": "enabled"})
        logger.info(f"[llm_client] thinking enabled: name={conn.name} model={conn.model_name}")

    logger.info(
        f"[llm_client] get_chat_model: name={conn.name} model={conn.model_name} "
        f"timeout={tmo}s temp={temp} streaming={streaming} mode={default_mode}"
    )

    # 复用 build_chat_model（已处理 api_key 解析、base_url 拼接、extra_body）
    return build_chat_model(
        conn,
        temperature=temp,
        timeout=tmo,
        streaming=streaming,
        extra_payload=merged_payload if merged_payload else None,
    )


def _build_base_url(item) -> str:
    """从 LLMConnectionConfig 构造 OpenAI 兼容 base_url（含 api_path）"""
    base_url = (getattr(item, "base_url", "") or "").rstrip("/")
    api_path = getattr(item, "api_path", None) or "/chat/completions"
    if not api_path.startswith("/"):
        api_path = f"/{api_path}"
    # ChatOpenAI 的 base_url 只需到根，api_path 默认是 /chat/completions
    # 若 api_path 是非标准的，拼进 base_url
    if api_path != "/chat/completions":
        return f"{base_url}{api_path}".replace("/chat/completions", "")
    return base_url


def build_chat_model(
    item,
    *,
    temperature: Optional[float] = None,
    timeout: Optional[float] = None,
    extra_payload: Optional[Dict[str, Any]] = None,
    streaming: bool = False,
):
    """从 LLMConnectionConfig 构建 langchain-openai ChatOpenAI 实例

    Args:
        item: LLMConnectionConfig ORM 对象
        temperature: 覆盖温度（None 则用 item.temperature）
        timeout: 覆盖超时（None 则用 item.timeout_seconds）
        extra_payload: 额外参数（如 thinking.type=disabled）
        streaming: 是否启用流式

    Returns:
        ChatOpenAI 实例

    Windows 稳定性修复：
        长时间运行的 uvicorn 进程中，httpx 默认 connection pool 会复用
        损坏的 socket，触发 [Errno 22] Invalid argument (OSError)。
        通过 http_client=httpx.Client(transport=...) 禁用 keepalive，
        每次请求新建连接，避免连接池状态损坏。
    """
    import httpx
    from langchain_openai import ChatOpenAI

    api_key = resolve_connection_api_key(getattr(item, "api_key", None))
    if not api_key:
        raise RuntimeError("API Key 未配置或环境变量未设置")

    model_name = getattr(item, "model_name", None) or "gpt-3.5-turbo"
    base_url = _build_base_url(item)
    temp = temperature if temperature is not None else float(getattr(item, "temperature", 0.2) or 0.2)
    tmo = float(timeout or getattr(item, "timeout_seconds", 60) or 60)

    # 每次新建 httpx client，禁用连接池 keepalive，避免 Windows socket 复用损坏
    http_client = httpx.Client(
        timeout=httpx.Timeout(tmo),
        transport=httpx.HTTPTransport(retries=1, http2=False),
        limits=httpx.Limits(max_keepalive_connections=0, max_connections=10),
    )

    kwargs: Dict[str, Any] = {
        "model": model_name,
        "api_key": api_key,
        "base_url": base_url,
        "temperature": temp,
        "timeout": tmo,
        "streaming": streaming,
        "http_client": http_client,
    }
    # extra_payload（如 thinking.type=disabled）透传给 OpenAI API
    if extra_payload:
        kwargs["extra_body"] = extra_payload

    # 国产模型兼容性修复：qwen/智谱 等模型在 thinking 模式下不支持 tool_choice=required，
    # 而 DeepAgents/langchain 框架在 bind_tools 时会设 tool_choice=any → required。
    # 用子类重写 bind_tools，强制 tool_choice=None。
    class _TupuChatOpenAI(ChatOpenAI):
        def bind_tools(self, tools, *, tool_choice=None, **kw):
            return super().bind_tools(tools, tool_choice=None, **kw)

    return _TupuChatOpenAI(**kwargs)


def _extract_usage(resp) -> Optional[Dict[str, Any]]:
    """从 ChatOpenAI 响应提取 token 用量"""
    try:
        meta = getattr(resp, "usage_metadata", None)
        if meta:
            return {
                "total_tokens": getattr(meta, "total_tokens", None),
                "prompt_tokens": getattr(meta, "input_tokens", None),
                "completion_tokens": getattr(meta, "output_tokens", None),
            }
    except Exception:
        pass
    return None


def call_openai_compatible_chat(
    item,
    *,
    system_prompt: str = "",
    user_prompt: str,
    temperature: Optional[float] = None,
    timeout: Optional[float] = None,
) -> str:
    """调用 LLM（system + user 双消息），返回内容字符串

    内部用 ChatOpenAI.invoke，保留 trace 埋点。
    """
    from .trace_wrapper import trace_llm_call
    model_name = getattr(item, "model_name", None) or "gpt-3.5-turbo"
    conn_name = getattr(item, "name", None) or "unknown"
    with trace_llm_call(f"llm:{conn_name}", model=model_name, connection=conn_name) as t:
        t.add_input(system_prompt=system_prompt, user_prompt=user_prompt, temperature=temperature)
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=user_prompt or ""))
        temp = temperature if temperature is not None else float(getattr(item, "temperature", 0.2) or 0.2)
        t.add_metadata(model=model_name, temperature=temp)
        chat = build_chat_model(item, temperature=temperature, timeout=timeout)
        resp = chat.invoke(messages)
        content = resp.content if isinstance(resp.content, str) else str(resp.content)
        t.add_output(content=content, usage=_extract_usage(resp))
        return content


def call_openai_compatible_messages(
    item,
    *,
    messages: List[Dict[str, str]],
    temperature: Optional[float] = None,
    timeout: Optional[float] = None,
    extra_payload: Optional[Dict[str, Any]] = None,
) -> str:
    """调用 LLM（自定义 messages 列表 + extra_payload），返回内容字符串

    内部用 ChatOpenAI.invoke，extra_payload 通过 extra_body 透传，保留 trace 埋点。
    """
    from .trace_wrapper import trace_llm_call
    model_name = getattr(item, "model_name", None) or "gpt-3.5-turbo"
    conn_name = getattr(item, "name", None) or "unknown"
    with trace_llm_call(f"llm:{conn_name}", model=model_name, connection=conn_name) as t:
        t.add_input(messages=messages, temperature=temperature, extra_payload=extra_payload)
        from langchain_core.messages import (
            SystemMessage, HumanMessage, AIMessage,
        )
        role_map = {
            "system": SystemMessage,
            "user": HumanMessage,
            "assistant": AIMessage,
        }
        lc_messages = []
        for m in messages or []:
            role = m.get("role", "user")
            cls = role_map.get(role, HumanMessage)
            lc_messages.append(cls(content=m.get("content", "")))
        temp = temperature if temperature is not None else float(getattr(item, "temperature", 0.2) or 0.2)
        t.add_metadata(model=model_name, temperature=temp, has_extra=bool(extra_payload))
        chat = build_chat_model(item, temperature=temperature, timeout=timeout, extra_payload=extra_payload)
        resp = chat.invoke(lc_messages)
        content = resp.content if isinstance(resp.content, str) else str(resp.content)
        t.add_output(content=content, usage=_extract_usage(resp))
        return content


def call_openai_compatible_chat_stream(
    item,
    system_prompt: str,
    user_prompt: str,
    temperature: Optional[float] = None,
    timeout: Optional[float] = None,
) -> Iterator[str]:
    """流式调用 LLM，逐块 yield 内容字符串

    用于 query_entity_step4 的 SSE 流式推理。
    """
    from .trace_wrapper import trace_llm_call
    model_name = getattr(item, "model_name", None) or "gpt-3.5-turbo"
    conn_name = getattr(item, "name", None) or "unknown"
    from langchain_core.messages import SystemMessage, HumanMessage
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=user_prompt or ""))

    with trace_llm_call(f"llm_stream:{conn_name}", model=model_name, connection=conn_name, streaming=True) as t:
        t.add_input(system_prompt=system_prompt, user_prompt=user_prompt, temperature=temperature)
        chat = build_chat_model(item, temperature=temperature, timeout=timeout, streaming=True)
        collected = []
        for chunk in chat.stream(messages):
            text = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
            if text:
                collected.append(text)
                yield text
        t.add_output(content="".join(collected))


def get_active_planner_config(db):
    from ..models.base import SmartPlannerConfig
    return db.query(SmartPlannerConfig).order_by(SmartPlannerConfig.created_at.desc()).first()
