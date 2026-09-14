# -*- coding: utf-8 -*-
"""记忆插槽②（spec §六）：L1 轨迹——追加 JSONL，永不抛错，per-surface asyncio 锁。

四类 TraceEvent（每行 JSON）：user_msg/assistant_msg 全文、tool_call 名+args、
tool_result 状态+截断500+result_ref。session_id=memory_thread_id、turn_id=run_id。
两账两用途（spec §六分工表）：RunEventSink=平台观测（MySQL）；本件=consolidator
原料（{expert}/{user}/trace/*.jsonl）。
"""
import asyncio
import datetime as _dt
import json
import logging
import uuid
from pathlib import Path

from app.services.expert_paths import memory_user_root

logger = logging.getLogger(__name__)
_SURFACE_LOCKS: dict = {}


def _surface_lock(surface: str) -> asyncio.Lock:
    if surface not in _SURFACE_LOCKS:
        _SURFACE_LOCKS[surface] = asyncio.Lock()
    return _SURFACE_LOCKS[surface]


def _trace_file(expert_id: str, user: str, surface: str) -> Path:
    day = _dt.date.today().isoformat()
    return memory_user_root(expert_id, user) / "trace" / (surface or "chat") / f"{day}.jsonl"


def append_event(expert_id: str, user: str, surface: str, event: dict) -> None:
    """追加一行（永不抛错——失败 logger.warning 即吞，spec §六）。锁内直写不引线程池。
    行形状恒定七键 {id, ts, surface, kind, payload, session_id, turn_id}——event 缺键补
    缺省（批3 实证修正 #3：计划测试断言七键齐而实现不补缺省键，矛盾，以测试语义为准）。"""
    try:
        row = {"id": uuid.uuid4().hex[:12],
               "ts": _dt.datetime.now().isoformat(timespec="milliseconds"),
               "surface": surface,
               "payload": {}, "session_id": "", "turn_id": "",
               **event}
        p = _trace_file(expert_id, user, surface)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"[L1] trace append 失败(吞): {e}")


async def aappend_event(expert_id: str, user: str, surface: str, event: dict) -> None:
    """per-surface asyncio 锁版（中间件用——防 JSONL 行交错）。"""
    try:
        async with _surface_lock(surface):
            await asyncio.get_running_loop().run_in_executor(
                None, lambda: append_event(expert_id, user, surface, event))
    except Exception as e:
        logger.warning(f"[L1] trace aappend 失败(吞): {e}")


def truncate(text: str, n: int = 500) -> str:
    return text if len(text or "") <= n else (text or "")[:n] + "…"


from typing import Any  # noqa: E402
from langchain.agents.middleware.types import AgentMiddleware  # noqa: E402


class MemoryTraceMiddleware(AgentMiddleware[Any, Any, Any]):
    """L1 轨迹中间件（spec §六）：洋葱最外层（SkillPolicy 之前——守卫拒绝也当轨迹记）。
    卡 L1 槽多 surface 声明则同事件写多份。永不抛错（各 append 自吞）。
    继承 langchain AgentMiddleware（SkillPolicyMiddleware 同款基类同款泛参；只实现
    三个 async 钩子；name 用基类默认=类名——基类 name 是只读 property，实例赋值
    self.name=… 会 AttributeError，切勿覆写）。"""

    def __init__(self, card: dict):
        super().__init__()
        from app.services.memory_slots import normalize_memory_field
        _mem = normalize_memory_field((card or {}).get("memory"))
        self._surfaces = [s.get("surface") or "chat" for s in _mem["slots"]
                          if s.get("type") == "L1_TRACE"]

    async def _emit(self, kind: str, payload: dict) -> None:
        from app.services.memory_runtime import current as _cur
        rt = _cur()
        # ⑤b（批 0.5 核验分支）：请求级 surface 指定（∈ 声明集，endpoint 已 422 校验）
        # →只写该 surface；未指定→②原语义（全部声明 surface 同写）。
        _req_surface = rt.get("surface")
        surfaces = [s for s in self._surfaces if s == _req_surface] if _req_surface else self._surfaces
        for s in surfaces:                            # 多槽声明→同事件写多份（spec §六）
            await aappend_event(rt["expert_id"], rt["user"], s,
                                {"kind": kind, "payload": payload,
                                 "session_id": rt["session_id"], "turn_id": rt["turn_id"]})

    async def abefore_agent(self, state, runtime) -> None:
        try:                                            # user_msg：全文（consolidator 核心原料）
            last = state.get("messages") or [-1]
            text = getattr(last[-1], "content", "") or ""
            if isinstance(text, list):
                text = "".join(str(x) for x in text)
            await self._emit("user_msg", {"text": text})
        except Exception as e:
            logger.warning(f"[L1] user_msg 记录失败(吞): {e}")

    async def awrap_tool_call(self, request, handler):
        try:
            tc = getattr(request, "tool_call", None)
            _args = getattr(tc, "args", None) or {}
            if not isinstance(_args, dict):
                _args = {"value": str(_args)}                # dataclass/其它形状防御
            await self._emit("tool_call", {"tool": getattr(tc, "name", "") or "",
                                           "args": _args})
        except Exception as e:
            logger.warning(f"[L1] tool_call 记录失败(吞): {e}")
        result = await handler(request)
        try:
            rtxt = str(getattr(result, "result", result) or "")
            await self._emit("tool_result", {"status": "ok" if not getattr(result, "error", None) else "error",
                                             "text": truncate(rtxt),
                                             "result_ref": getattr(result, "result_ref", None)
                                             or _args.get("result_ref")})
        except Exception as e:
            logger.warning(f"[L1] tool_result 记录失败(吞): {e}")
        return result

    async def aafter_agent(self, state, runtime) -> None:
        try:                                            # assistant_msg：最终回答全文
            msgs = state.get("messages") or []
            text = ""
            for m in reversed(msgs):
                if getattr(m, "type", "") == "ai" and not getattr(m, "tool_calls", None):
                    text = m.content or ""
                    break
            if isinstance(text, list):
                text = "".join(str(x) for x in text)
            await self._emit("assistant_msg", {"text": text})
        except Exception as e:
            logger.warning(f"[L1] assistant_msg 记录失败(吞): {e}")
