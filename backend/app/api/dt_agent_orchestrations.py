# -*- coding: utf-8 -*-
"""引擎批1：deepagent 编排派发——dispatch(req, session_id, turn_id, user_prefix)。
批1 只实现 run_chat（chat 全链）；其余 7 技能返回「能力编排未就绪」error（分批交付中间态，
台账登记——批3 solve/mastery/wrong-intake、批4 quiz/visualize/research、批5 book-generate）。

run_chat 全链（实名参照 freeplan/endpoint.py）：
- agent：get_tupu_agent(connection_id="", expert_id="tutor")（L116 同款）
- thread：expert_paths.thread_id(user_prefix, "tutor", session_id)（L93-94 同款三段键）
- config：{"configurable": {"thread_id": ..., "checkpoint_ns": "bridge"}, "recursion_limit": 80}
  （prep.py L64 同构；checkpoint_ns="bridge"=与 freeplan 隔离的记忆域）
- 工具白名单：TOOL_WHITELIST ∩ req.tools——批1 可用面={web_search}（ddgs 库实现，
  duckduckgo_search 更名后继——平台无既有 web_search 工具实证，计划 L248 授权降级实现）；
  reason=思维标记不走工具；code_execution 批3/4 SandboxExecutor 接入后入表；4 舍弃件永拒。
- KB 注入：kb_query(kb_id, query)（platform ④ D9 检索服务——vendor knowledge.py 无独立检索
  端点实证〔仅配置/文件夹/rag-pipeline 管理面〕，vendor rag 走整链 tool_registry 需全 runtime；
  基座归 tupu 纪律下用平台 kb_engines 检索面，vendor REST 数据面零改动——台账登记）
- 事件翻译表（L251）：模型流 token→content；推理段→thinking；工具起→tool_call；工具回→
  tool_result；langgraph custom→stage_start/stage_end；异常→error；结束→result+done；首帧→session_meta。
"""
import json
import logging
from typing import Any, AsyncGenerator, Dict, List

logger = logging.getLogger(__name__)

# 批1 可用工具面（白名单∩req.tools 生效）：web_search=ddgs 实现；
# reason=DT 语义的"扩展思考"标记（不产生工具调用，允许模型长推理）；其余批3+ 接入。
TOOL_WHITELIST = {"web_search"}
# 裁定②舍弃件（永拒，不进白名单）：geogebra_analysis/paper_search/imagegen/videogen
DISCARDED_TOOLS = {"geogebra_analysis", "paper_search", "imagegen", "videogen"}

EXPERT_ID = "tutor"


def _evt(type_, source, stage, content="", metadata=None, session_id=None,
         turn_id=None, seq=0):
    return {"type": type_, "source": source, "stage": stage, "content": content,
            "metadata": metadata or {}, "session_id": session_id, "turn_id": turn_id,
            "seq": seq, "timestamp": __import__("time").time()}


async def dispatch(req, session_id: str, turn_id: str, user_prefix: str) -> AsyncGenerator[Dict[str, Any], None]:
    """按 skill_code 派发到编排实现（批1 仅 tutor/chat）。"""
    code = req.skill_code
    if code == "tutor/chat":
        async for ev in run_chat(req, session_id, turn_id, user_prefix):
            yield ev
        return
    yield _evt("error", "bridge", "dispatch",
               content=f"能力编排未就绪: {code}（分批交付中间态，台账登记）",
               session_id=session_id, turn_id=turn_id)


async def _web_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """web_search 降级实现：ddgs（duckduckgo_search 更名后继——平台无既有工具，计划授权）。"""
    try:
        from ddgs import DDGS
        with DDGS() as d:
            rows = d.text(query, max_results=max_results)
        return [{"title": r.get("title", ""), "url": r.get("href", ""),
                 "snippet": r.get("body", "")} for r in rows]
    except Exception as e:
        logger.warning(f"[bridge] web_search 失败: {e}")
        return []


async def _kb_context(req) -> str:
    """KB 检索注入：req.knowledge_bases（kb_id 列表）逐库 kb_query（platform ④ D9 检索面）。"""
    if not req.knowledge_bases:
        return ""
    from app.services.kb_query import kb_query
    blocks = []
    for kb_id in req.knowledge_bases[:5]:  # 上限 5 库防请求爆炸
        try:
            res = kb_query(kb_id, req.message, top_k=6)
        except Exception as e:
            logger.warning(f"[bridge] kb_query {kb_id} 失败: {e}")
            continue
        if res.get("error") or not res.get("matches"):
            continue
        lines = "\n".join(f"- {m['text'][:400]}" for m in res["matches"])
        blocks.append(f"[知识库 {res.get('kb_name', kb_id)}]\n{lines}")
    return "\n\n".join(blocks)


async def run_chat(req, session_id: str, turn_id: str, user_prefix: str) -> AsyncGenerator[Dict[str, Any], None]:
    """chat 全链编排（deepagent 重构——L6 行为规格驱动，非源码对拍）。"""
    # 首帧 session_meta（session_id/turn_id 回传前端）
    yield _evt("session_meta", "bridge", "session", session_id=session_id, turn_id=turn_id,
               metadata={"skill_code": req.skill_code, "user_prefix": user_prefix})

    yield _evt("stage_start", "bridge", "prepare", content="准备上下文",
               session_id=session_id, turn_id=turn_id)

    # KB 检索注入（批内检索，语义照 DT retrieve_context：命中块拼首条消息前缀）
    kb_block = await _kb_context(req)
    if kb_block:
        yield _evt("sources", "bridge", "prepare", content="知识库命中",
                   metadata={"kb_count": len(req.knowledge_bases)},
                   session_id=session_id, turn_id=turn_id)

    # 历史引用前缀（req.history_references：[{title, content}] 摘要注入）
    ref_block = ""
    if req.history_references:
        lines = "\n".join(f"- {r.get('title', '')}: {str(r.get('content', ''))[:200]}"
                          for r in req.history_references[:5])
        ref_block = f"[引用笔记]\n{lines}\n\n"

    # 工具面：白名单∩请求（裁掉舍弃件与未接入件）
    requested = [t for t in (req.tools or []) if t in TOOL_WHITELIST]

    yield _evt("stage_end", "bridge", "prepare", session_id=session_id, turn_id=turn_id,
               metadata={"kb_block": bool(kb_block), "tools": requested})

    # web_search：前置检索+合成工具事件（get_tupu_agent=固定工具面单例，批1 不做请求级装挂；
    # L6 可观察契约=tool_call→tool_result→结果进上下文——与 DT 工具循环等价，
    # metadata.pre_retrieval=true 如实标记实现方式，台账登记）
    web_block = ""
    web_hits = []
    if "web_search" in requested and req.message.strip():
        yield _evt("tool_call", "agent", "tools", content="调用工具 web_search",
                   metadata={"name": "web_search", "args": {"query": req.message},
                             "pre_retrieval": True},
                   session_id=session_id, turn_id=turn_id)
        web_hits = await _web_search(req.message)
        if web_hits:
            lines = "\n".join(f"- {h['title']}: {h['snippet'][:200]} ({h['url']})"
                              for h in web_hits)
            web_block = f"[Web Search]\n{lines}\n\n"
        yield _evt("tool_result", "agent", "tools",
                   content=json.dumps(web_hits[:3], ensure_ascii=False)[:400],
                   metadata={"name": "web_search", "ref": "tool://web_search",
                             "hits": len(web_hits), "pre_retrieval": True},
                   session_id=session_id, turn_id=turn_id)

    # agent+thread（freeplan L115-116/L93-94 同款）
    from app.services.tupu_deepagent import get_tupu_agent
    agent = await get_tupu_agent(connection_id="", expert_id=EXPERT_ID)
    from app.services.expert_paths import thread_id as _expert_thread_id
    memory_thread_id = _expert_thread_id(user_prefix, EXPERT_ID, session_id)

    from langchain_core.messages import HumanMessage, SystemMessage
    parts = []
    if ref_block:
        parts.append(ref_block)
    if kb_block:
        parts.append(kb_block + "\n\n")
    if web_block:
        parts.append(web_block)
    parts.append(req.message)
    # 图状态入参=dict（freeplan L207 _inv_state 同构——裸消息列表触发
    # INVALID_GRAPH_NODE_RETURN_VALUE「Expected dict」实测）
    input_state = {"messages": [HumanMessage(content="".join(parts))]}
    config = {"configurable": {"thread_id": memory_thread_id, "checkpoint_ns": "bridge"},
              "recursion_limit": 80}

    content_acc = []
    final_content = ""
    try:
        aiter = agent.astream_events(input_state, config=config, version="v2").__aiter__()
        while True:
            try:
                ev = await aiter.__anext__()
            except StopAsyncIteration:
                break
            etype = ev.get("event", "")
            data = ev.get("data", {})

            if etype == "on_chat_model_stream":
                chunk = data.get("chunk")
                if chunk is None:
                    continue
                # 推理段→thinking；正文 token→content（freeplan L387-439 同源不同帧形）
                reasoning = (getattr(chunk, "additional_kwargs", {}) or {}).get("reasoning_content")
                if reasoning:
                    yield _evt("thinking", "agent", "answer", content=reasoning,
                               session_id=session_id, turn_id=turn_id)
                    continue
                c = getattr(chunk, "content", "")
                if isinstance(c, str) and c:
                    content_acc.append(c)
                    yield _evt("content", "agent", "answer", content=c,
                               session_id=session_id, turn_id=turn_id)
                continue

            if etype == "on_tool_start":
                name = ev.get("name", "")
                yield _evt("tool_call", "agent", "tools", content=f"调用工具 {name}",
                           metadata={"name": name, "args": _safe_json(ev.get("data", {}).get("input"))},
                           session_id=session_id, turn_id=turn_id)
                continue

            if etype == "on_tool_end":
                name = ev.get("name", "")
                out = data.get("output")
                yield _evt("tool_result", "agent", "tools",
                           content=str(getattr(out, "content", out))[:400],
                           metadata={"name": name, "ref": f"tool://{name}"},
                           session_id=session_id, turn_id=turn_id)
                continue

            if etype == "on_custom_event":
                # 编排自定义阶段事件（批3+ 编排用；批1 透传）
                if ev.get("name") in ("stage_start", "stage_end"):
                    yield _evt(ev["name"], "agent", str((ev.get("data") or {}).get("stage", "")),
                               content=str((ev.get("data") or {}).get("text", "")),
                               session_id=session_id, turn_id=turn_id)
                continue
    except Exception as e:
        logger.exception("[bridge] run_chat 异常")
        yield _evt("error", "agent", "run", content=str(e),
                   session_id=session_id, turn_id=turn_id)
        yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
                   metadata={"ok": False})
        return

    final_content = "".join(content_acc).strip()
    if final_content:
        yield _evt("result", "agent", "answer", content=final_content,
                   metadata={"web_hits": len(web_hits)},
                   session_id=session_id, turn_id=turn_id)
    yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
               metadata={"ok": True, "final_len": len(final_content)})


def _safe_json(v: Any) -> Any:
    """tool args→可 JSON 序列化（langgraph input 可能含非基元对象）。"""
    try:
        json.dumps(v)
        return v
    except Exception:
        return {"repr": repr(v)[:400]}
