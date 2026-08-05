"""LangSmith Trace 封装 - 轻量级可观测层

设计原则：
  1. 不强制依赖 langsmith SDK（未配置 key 时自动降级为本地结构化日志）
  2. 提供统一的 trace 上下文（一次数据智能对话 = 一个 trace，含多个 span）
  3. 覆盖三类埋点：LLM 调用 / 技能执行 / 状态机跳转

用法：
    from app.services.trace_wrapper import trace_llm_call, trace_skill_exec, trace_state_transition

    with trace_llm_call("boss_router", model="minimax-m3") as t:
        t.add_input(user_query="查客户")
        result = call_llm(...)
        t.add_output(decision=result)

环境变量：
    LANGSMITH_API_KEY  - 配置则上报 LangSmith，否则降级本地日志
    LANGSMITH_PROJECT  - 项目名（默认 tupu-dev）
    TUPU_TRACE_ENABLED - 开关（默认 true，设为 false 完全关闭）
"""
import os
import json
import time
import uuid
import logging
import contextlib
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(logging.NullHandler())
logger.setLevel(logging.INFO)

_ENABLED = os.getenv("TUPU_TRACE_ENABLED", "true").lower() != "false"
_LANGSMITH_KEY = os.getenv("LANGSMITH_API_KEY", "").strip()
_PROJECT = os.getenv("LANGSMITH_PROJECT", "tupu-dev").strip()

try:
    from langsmith import Client as _LangsmithClient
    _LS_CLIENT = _LangsmithClient() if _LANGSMITH_KEY and _LANGSMITH_KEY != "lsv2_pt_dummy" else None
except Exception:
    _LS_CLIENT = None

if _LS_CLIENT:
    logger.info("LangSmith trace 已启用，project=%s", _PROJECT)
else:
    logger.info("LangSmith trace 降级为本地日志（未配置有效 LANGSMITH_API_KEY）")


def _gen_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _safe_json(obj: Any, limit: int = 4000) -> str:
    try:
        s = json.dumps(obj, ensure_ascii=False, default=str)
        return s[:limit] + ("...[truncated]" if len(s) > limit else "")
    except Exception:
        return str(obj)[:limit]


class _Span:
    """单个 trace span（LLM 调用 / 技能执行 / 状态跳转）"""

    def __init__(self, name: str, span_type: str, trace_id: str, parent_id: Optional[str] = None):
        self.name = name
        self.span_type = span_type
        self.trace_id = trace_id
        self.span_id = _gen_id(f"span-{span_type}")
        self.parent_id = parent_id
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.inputs: Dict[str, Any] = {}
        self.outputs: Dict[str, Any] = {}
        self.error: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    def add_input(self, **kwargs):
        self.inputs.update(kwargs)

    def add_output(self, **kwargs):
        self.outputs.update(kwargs)

    def add_metadata(self, **kwargs):
        self.metadata.update(kwargs)

    def finish(self, error: Optional[str] = None):
        self.end_time = time.time()
        self.error = error
        self._flush()

    def _flush(self):
        duration_ms = int((self.end_time - self.start_time) * 1000) if self.end_time else 0
        record = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "span_type": self.span_type,
            "duration_ms": duration_ms,
            "inputs": _safe_json(self.inputs),
            "outputs": _safe_json(self.outputs),
            "error": self.error,
            "metadata": _safe_json(self.metadata),
        }

        if _LS_CLIENT:
            try:
                _LS_CLIENT.create_run(
                    name=self.name,
                    run_id=self.span_id,
                    project_name=_PROJECT,
                    run_type=self.span_type,
                    inputs=self.inputs,
                    outputs=self.outputs if not self.error else None,
                    error=self.error,
                    extra={"metadata": {**self.metadata, "trace_id": self.trace_id, "duration_ms": duration_ms}},
                    start_time=self.start_time,
                    end_time=self.end_time,
                )
            except Exception as e:
                logger.debug("LangSmith 上报失败，降级日志: %s", e)
                logger.info("[TRACE] %s", _safe_json(record))
        else:
            print(f"[TRACE] {_safe_json(record)}", flush=True)


class _TraceContext:
    """一次对话/请求的 trace 上下文"""

    _stack: list = []

    def __init__(self, name: str, trace_id: Optional[str] = None):
        self.name = name
        self.trace_id = trace_id or _gen_id("trace")
        self.root_span: Optional[_Span] = None

    def __enter__(self):
        _TraceContext._stack.append(self)
        self.root_span = _Span(self.name, "chain", self.trace_id)
        self.root_span.add_metadata(trace_name=self.name)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        err = f"{exc_type.__name__}: {exc_val}" if exc_type else None
        self.root_span.finish(err)
        if _TraceContext._stack and _TraceContext._stack[-1] is self:
            _TraceContext._stack.pop()
        return False

    def child_span(self, name: str, span_type: str = "tool") -> _Span:
        parent = _TraceContext._stack[-1].root_span if _TraceContext._stack else None
        parent_id = parent.span_id if parent else None
        return _Span(name, span_type, self.trace_id, parent_id)


@contextlib.contextmanager
def trace_context(name: str, trace_id: Optional[str] = None):
    """顶层 trace 上下文（一次数据智能对话）"""
    if not _ENABLED:
        yield None
        return
    with _TraceContext(name, trace_id) as ctx:
        yield ctx


@contextlib.contextmanager
def trace_llm_call(name: str, **metadata):
    """LLM 调用 span"""
    if not _ENABLED:
        yield _NoopSpan()
        return
    ctx = _TraceContext._stack[-1] if _TraceContext._stack else None
    if ctx:
        span = ctx.child_span(name, "llm")
    else:
        span = _Span(name, "llm", _gen_id("trace"))
    span.add_metadata(**metadata)
    try:
        yield span
    except Exception as e:
        span.finish(error=f"{type(e).__name__}: {e}")
        raise
    else:
        span.finish()


@contextlib.contextmanager
def trace_skill_exec(skill_name: str, **metadata):
    """技能执行 span"""
    if not _ENABLED:
        yield _NoopSpan()
        return
    ctx = _TraceContext._stack[-1] if _TraceContext._stack else None
    if ctx:
        span = ctx.child_span(skill_name, "tool")
    else:
        span = _Span(skill_name, "tool", _gen_id("trace"))
    span.add_metadata(skill=skill_name, **metadata)
    try:
        yield span
    except Exception as e:
        span.finish(error=f"{type(e).__name__}: {e}")
        raise
    else:
        span.finish()


@contextlib.contextmanager
def trace_state_transition(from_node: str, to_node: str, **metadata):
    """状态机跳转 span"""
    if not _ENABLED:
        yield _NoopSpan()
        return
    ctx = _TraceContext._stack[-1] if _TraceContext._stack else None
    name = f"{from_node}→{to_node}"
    if ctx:
        span = ctx.child_span(name, "chain")
    else:
        span = _Span(name, "chain", _gen_id("trace"))
    span.add_metadata(from_node=from_node, to_node=to_node, **metadata)
    try:
        yield span
    except Exception as e:
        span.finish(error=f"{type(e).__name__}: {e}")
        raise
    else:
        span.finish()


class _NoopSpan:
    """trace 关闭时的空 span，避免调用方写 if"""
    def add_input(self, **kwargs): pass
    def add_output(self, **kwargs): pass
    def add_metadata(self, **kwargs): pass


def is_enabled() -> bool:
    return _ENABLED


def is_langsmith_active() -> bool:
    return _LS_CLIENT is not None
