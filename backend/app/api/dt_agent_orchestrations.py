# -*- coding: utf-8 -*-
"""引擎批1/3：deepagent 编排派发——dispatch(req, session_id, turn_id, user_prefix)。
批1：run_chat（chat 全链）；批3：run_solve（推理循环）/run_mastery（loop+精通工具组）/
run_wrong_intake（抽取→确认卡→落库）；其余技能「未就绪」error（批4 quiz/visualize/research、
批5 book-generate——分批交付中间态，台账登记）。

共享流循环 _agent_stream（批3 重构，chat 复用同路径——批1 冒烟 19/19 回归护航）：
- agent：get_tupu_agent(connection_id="", expert_id="tutor")（L116 同款）
- thread：expert_paths.thread_id(user_prefix, "tutor", session_id)（L93-94 同款三段键）
- config：{"configurable": {"thread_id": ..., "checkpoint_ns": "bridge"}, "recursion_limit": 80}
  （prep.py L64 同构；checkpoint_ns="bridge"=与 freeplan 隔离的记忆域）
- 工具白名单：TOOL_WHITIST ∩ req.tools；4 舍弃件永拒（裁定②）。
- KB 注入：kb_query（platform ④ D9——E-18）；web_search=ddgs 前置检索（E-19）。
- 事件翻译：模型流 token→content；推理段→thinking；工具起→tool_call；工具回→tool_result；
  自定义→stage_start/stage_end；异常→error；结束→result+done；首帧→session_meta。

批3 技能脚本节点纪律（plan 3.2 授权「数据面打 vendor/learning API」——非 MCP 回装）：
mastery 数据面=app/services/learning 单源 impl（tutor_inprocess 同源函数直调）；
wrong-intake 落库=learning_dao.wrong_question_add/mother_question_find_or_create；
工具调用以合成 tool_call/tool_result 事件呈现（metadata.pre_retrieval 同批1 如实标记）。
"""
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List

logger = logging.getLogger(__name__)

# 可用工具面（白名单∩req.tools 生效）：web_search=ddgs 实现；
# reason=DT 语义的"扩展思考"标记（不产生工具调用，允许模型长推理）；其余批4+ 接入。
TOOL_WHITELIST = {"web_search"}
# 裁定②舍弃件（永拒，不进白名单）：geogebra_analysis/paper_search/imagegen/videogen
DISCARDED_TOOLS = {"geogebra_analysis", "paper_search", "imagegen", "videogen"}

EXPERT_ID = "tutor"

# 批3：wrong-intake 确认卡挂起态（桥进程内——确认轮同 session_id 取回）
_WRONG_INTAKE_PENDING: Dict[str, Dict[str, Any]] = {}

_SOLVE_DIRECTIVE = (
    "[solve 模式]\n你是解题引擎。按多步推理解题：先复述已知与目标，再分步推导（每步给出依据），"
    "最后验证答案（代入/量纲/特例）并给出最终结论。工具仅在确需外部事实时使用。\n\n"
)

_MASTERY_DIRECTIVE = (
    "[mastery 模式]\n你是精通路径导师。基于已检索到的学情数据（见上）规划学习：先报当前状态，"
    "再给下一步（复习/练习/新知）。硬门：未经评测(assess)不得直接给大题答案或代做；"
    "学生要答案时给引导问题与学习路径建议。\n\n"
)


def _evt(type_, source, stage, content="", metadata=None, session_id=None,
         turn_id=None, seq=0):
    return {"type": type_, "source": source, "stage": stage, "content": content,
            "metadata": metadata or {}, "session_id": session_id, "turn_id": turn_id,
            "seq": seq, "timestamp": time.time()}


async def dispatch(req, session_id: str, turn_id: str, user_prefix: str) -> AsyncGenerator[Dict[str, Any], None]:
    """按 skill_code 派发到编排实现（批1 chat+批3 三件）。"""
    code = req.skill_code
    if code == "tutor/chat":
        async for ev in run_chat(req, session_id, turn_id, user_prefix):
            yield ev
        return
    if code == "tutor/solve":
        async for ev in run_solve(req, session_id, turn_id, user_prefix):
            yield ev
        return
    if code == "tutor/mastery":
        async for ev in run_mastery(req, session_id, turn_id, user_prefix):
            yield ev
        return
    if code == "tutor/wrong-intake":
        async for ev in run_wrong_intake(req, session_id, turn_id, user_prefix):
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


async def _prepare(req, session_id: str, turn_id: str):
    """prepare 段（批1 run_chat 前段抽取——chat/solve/mastery/wrong-intake 共用）。
    返回 (kb_block, ref_block, requested_tools)；事件帧就地 yield。"""
    yield _evt("session_meta", "bridge", "session", session_id=session_id, turn_id=turn_id,
               metadata={"skill_code": req.skill_code, "user_prefix": user_prefix_of(req)})
    yield _evt("stage_start", "bridge", "prepare", content="准备上下文",
               session_id=session_id, turn_id=turn_id)

    kb_block = await _kb_context(req)
    if kb_block:
        yield _evt("sources", "bridge", "prepare", content="知识库命中",
                   metadata={"kb_count": len(req.knowledge_bases)},
                   session_id=session_id, turn_id=turn_id)

    ref_block = ""
    if req.history_references:
        lines = "\n".join(f"- {r.get('title', '')}: {str(r.get('content', ''))[:200]}"
                          for r in req.history_references[:5])
        ref_block = f"[引用笔记]\n{lines}\n\n"

    requested = [t for t in (req.tools or []) if t in TOOL_WHITELIST]
    yield _evt("stage_end", "bridge", "prepare", session_id=session_id, turn_id=turn_id,
               metadata={"kb_block": bool(kb_block), "tools": requested})
    yield (kb_block, ref_block, requested)


def user_prefix_of(req) -> str:
    """桥 user 口径（dt_agent_capabilities._user_prefix 同值——记 session_meta 用）。"""
    return getattr(req, "_user_prefix", "") or "anonymous"


async def _agent_stream(req, session_id: str, turn_id: str, parts: List[str],
                        *, on_first_content=None) -> AsyncGenerator[Dict[str, Any], None]:
    """共享 agent 流循环（批1 run_chat 主体抽取——事件翻译表逐帧同型）。"""
    from app.services.tupu_deepagent import get_tupu_agent
    agent = await get_tupu_agent(connection_id="", expert_id=EXPERT_ID)
    from app.services.expert_paths import thread_id as _expert_thread_id
    user_prefix = user_prefix_of(req)
    memory_thread_id = _expert_thread_id(user_prefix, EXPERT_ID, session_id)

    from langchain_core.messages import HumanMessage
    input_state = {"messages": [HumanMessage(content="".join(parts))]}
    config = {"configurable": {"thread_id": memory_thread_id, "checkpoint_ns": "bridge"},
              "recursion_limit": 80}

    content_acc: List[str] = []
    first_content_fired = False
    # response_format 结构化交付的流内捕获：模型对 FinalAnswer schema 产出 tool_call_chunks
    # （args JSON 分片流——非 content token）。累积分片，循环末解析出 final_answer 补发 content。
    fa_args_acc: List[str] = []
    fa_active = False
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
                # FinalAnswer 结构化调用：tool_call_chunks 分片流（content 为空）
                tc_chunks = getattr(chunk, "tool_call_chunks", None) or []
                for tcc in tc_chunks:
                    tcc_name = tcc.get("name") if isinstance(tcc, dict) else getattr(tcc, "name", "")
                    tcc_args = tcc.get("args") if isinstance(tcc, dict) else getattr(tcc, "args", "")
                    if tcc_name and "finalanswer" in str(tcc_name).lower():
                        fa_active = True
                    if fa_active and tcc_args:
                        fa_args_acc.append(str(tcc_args))
                reasoning = (getattr(chunk, "additional_kwargs", {}) or {}).get("reasoning_content")
                if reasoning:
                    yield _evt("thinking", "agent", "answer", content=reasoning,
                               session_id=session_id, turn_id=turn_id)
                    continue
                c = getattr(chunk, "content", "")
                if isinstance(c, str) and c:
                    content_acc.append(c)
                    if not first_content_fired:
                        first_content_fired = True
                        if on_first_content is not None:
                            for close_ev in on_first_content():
                                yield close_ev
                    yield _evt("content", "agent", "answer", content=c,
                               session_id=session_id, turn_id=turn_id)
                continue

            if etype == "on_tool_start":
                name = ev.get("name", "")
                tool_in = ev.get("data", {}).get("input")
                # FinalAnswer 容器（tupu_deepagent L925 终答工具）：模型可把最终答复
                # 走工具 args 而非 content 流（mastery/solve 结构化倾向实测）——
                # args.final_answer 转发为 content 帧（与正文流同型，前端零感知）。
                if name.lower() == "finalanswer" and isinstance(tool_in, dict):
                    fa = str(tool_in.get("final_answer", "") or "")
                    if fa:
                        if not first_content_fired:
                            first_content_fired = True
                            if on_first_content is not None:
                                for close_ev in on_first_content():
                                    yield close_ev
                    if fa and not content_acc:
                        for i in range(0, len(fa), 64):
                            content_acc.append(fa[i:i + 64])
                            yield _evt("content", "agent", "answer", content=fa[i:i + 64],
                                       session_id=session_id, turn_id=turn_id)
                    elif fa:
                        tail = "".join(content_acc)
                        if fa.strip()[:80] not in tail[:400]:
                            content_acc.append(fa)
                            yield _evt("content", "agent", "answer", content=fa,
                                       session_id=session_id, turn_id=turn_id)
                    continue
                yield _evt("tool_call", "agent", "tools", content=f"调用工具 {name}",
                           metadata={"name": name, "args": _safe_json(tool_in)},
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
                if ev.get("name") in ("stage_start", "stage_end"):
                    yield _evt(ev["name"], "agent", str((ev.get("data") or {}).get("stage", "")),
                               content=str((ev.get("data") or {}).get("text", "")),
                               session_id=session_id, turn_id=turn_id)
                continue
    except Exception as e:
        logger.exception("[bridge] _agent_stream 异常")
        yield _evt("error", "agent", "run", content=str(e),
                   session_id=session_id, turn_id=turn_id)
        yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
                   metadata={"ok": False})
        return

    final_content = "".join(content_acc).strip()
    if not final_content and fa_args_acc:
        # FinalAnswer args JSON → final_answer（流内 tool_call_chunks 捕获——批3 mastery
        # 实测驱动：response_format 交付走结构化调用，content 流为空）
        try:
            fa_json = json.loads("".join(fa_args_acc))
            fa = str(fa_json.get("final_answer", "") or "")
        except Exception:
            fa = "".join(fa_args_acc)
        if fa.strip():
            for i in range(0, len(fa), 64):
                yield _evt("content", "agent", "answer", content=fa[i:i + 64],
                           session_id=session_id, turn_id=turn_id)
            final_content = fa.strip()
    if not final_content:
        # 图态兜底（structured_response——流外保险）
        try:
            st = await agent.aget_state(config)
            sr = (st.values or {}).get("structured_response") if st and st.values else None
            fa = ""
            if isinstance(sr, dict):
                fa = str(sr.get("final_answer", "") or "")
            elif sr is not None:
                fa = str(sr)
            if fa.strip():
                for i in range(0, len(fa), 64):
                    yield _evt("content", "agent", "answer", content=fa[i:i + 64],
                               session_id=session_id, turn_id=turn_id)
                final_content = fa.strip()
        except Exception as e:
            logger.warning(f"[bridge] structured_response 兜底取态失败: {e!r}")
    if final_content:
        yield _evt("result", "agent", "answer", content=final_content,
                   session_id=session_id, turn_id=turn_id)
    yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
               metadata={"ok": True, "final_len": len(final_content)})


async def run_chat(req, session_id: str, turn_id: str, user_prefix: str) -> AsyncGenerator[Dict[str, Any], None]:
    """chat 全链编排（批1 路径——批3 重构后走 _prepare+_agent_stream 共享面）。"""
    req._user_prefix = user_prefix
    gen = _prepare(req, session_id, turn_id)
    # 抽出 prepare 帧与块（_prepare 是 async generator——先逐帧转发直到返回值）
    kb_block = ref_block = ""
    requested: List[str] = []
    while True:
        try:
            ev = await gen.__anext__()
        except StopAsyncIteration:
            break
        if isinstance(ev, tuple):
            kb_block, ref_block, requested = ev
            break
        yield ev

    # web_search 前置检索（E-19 同款合成事件）
    web_block = ""
    web_hits: List[Dict[str, Any]] = []
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

    parts = []
    if ref_block:
        parts.append(ref_block)
    if kb_block:
        parts.append(kb_block + "\n\n")
    if web_block:
        parts.append(web_block)
    parts.append(req.message)

    def _meta_webhits():
        # result 事件补 web_hits 计数（批1 result metadata 形状保持）
        return []

    async for ev in _agent_stream(req, session_id, turn_id, parts):
        if ev.get("type") == "result":
            ev.setdefault("metadata", {})
            ev["metadata"]["web_hits"] = len(web_hits)
        yield ev


async def run_solve(req, session_id: str, turn_id: str, user_prefix: str) -> AsyncGenerator[Dict[str, Any], None]:
    """solve 编排（批3）：推理循环=同 chat 链+solve 指令前缀+reason 阶段包裹
    （阶段事件契约见 dt_baseline/behavior-specs/tutor_solve.md）。"""
    req._user_prefix = user_prefix
    gen = _prepare(req, session_id, turn_id)
    kb_block = ref_block = ""
    requested: List[str] = []
    while True:
        try:
            ev = await gen.__anext__()
        except StopAsyncIteration:
            break
        if isinstance(ev, tuple):
            kb_block, ref_block, requested = ev
            break
        yield ev

    web_block = ""
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

    # reason 阶段：开帧在流前；闭帧在首个 content token（on_first_content 钩子）
    yield _evt("stage_start", "bridge", "reason", content="多步推理中",
               session_id=session_id, turn_id=turn_id)

    def _close_reason():
        return [_evt("stage_end", "bridge", "reason", session_id=session_id, turn_id=turn_id)]

    parts = [_SOLVE_DIRECTIVE]
    if ref_block:
        parts.append(ref_block)
    if kb_block:
        parts.append(kb_block + "\n\n")
    if web_block:
        parts.append(web_block)
    parts.append(req.message)

    async for ev in _agent_stream(req, session_id, turn_id, parts, on_first_content=_close_reason):
        yield ev


async def run_mastery(req, session_id: str, turn_id: str, user_prefix: str) -> AsyncGenerator[Dict[str, Any], None]:
    """mastery 编排（批3）：学情数据面（learning 单源 impl）→ 合成工具事件 → 注入 → loop。
    硬门语义在指令面（未经 assess 不给答案）；工具组挂载面=twin 工厂未挂（⑤R R1 退役态），
    本编排以技能脚本节点承接（plan 3.2 授权；E-16 同源口径）。"""
    req._user_prefix = user_prefix
    gen = _prepare(req, session_id, turn_id)
    kb_block = ref_block = ""
    requested: List[str] = []
    while True:
        try:
            ev = await gen.__anext__()
        except StopAsyncIteration:
            break
        if isinstance(ev, tuple):
            kb_block, ref_block, requested = ev
            break
        yield ev

    # 技能脚本节点：mastery_status（学情概览=due_cards+wrong_question_query 聚合——
    # 单源 impl 同函数面，user=桥 user 口径）
    status_payload: Dict[str, Any] = {}
    yield _evt("tool_call", "agent", "tools", content="调用工具 mastery_status",
               metadata={"name": "mastery_status", "args": {"scope": "overview"},
                         "mastery_group": True, "scripted": True},
               session_id=session_id, turn_id=turn_id)
    try:
        from app.services.learning.service import due_cards
        from app.services.learning.learning_dao import wrong_question_query
        due = due_cards(user_prefix, limit=10)
        wqs = wrong_question_query(user_prefix, limit=5)
        status_payload = {"due_count": len(due), "due_items": due[:5],
                          "wrong_open": len([w for w in wqs if (w.get("status") or "open") == "open"]),
                          "wrong_recent": wqs[:3]}
    except Exception as e:
        logger.warning(f"[bridge] mastery_status 数据面失败: {e}")
        status_payload = {"error": str(e)[:120]}
    yield _evt("tool_result", "agent", "tools",
               content=json.dumps(status_payload, ensure_ascii=False, default=str)[:400],
               metadata={"name": "mastery_status", "ref": "tool://mastery_status",
                         "mastery_group": True, "scripted": True},
               session_id=session_id, turn_id=turn_id)

    parts = [_MASTERY_DIRECTIVE,
             "[学情数据]\n" + json.dumps(status_payload, ensure_ascii=False, default=str)[:1200] + "\n\n"]
    if ref_block:
        parts.append(ref_block)
    if kb_block:
        parts.append(kb_block + "\n\n")
    parts.append(req.message)

    async for ev in _agent_stream(req, session_id, turn_id, parts):
        yield ev


_EXTRACTION_SYSTEM = (
    "你是错题录入助手。从学生消息中抽取错题结构化字段，返回 JSON：\n"
    "{\"question\": \"题面（含完整题目与条件）\", \"correct_answer\": \"正确答案\", "
    "\"wrong_answer\": \"学生的错误答案\", \"error_type\": \"concept|careless|technique\", "
    "\"subject\": \"学科\", \"complete\": true/false}\n"
    "字段抽不全时 complete=false 并在 missing 中列出缺失项（追加 \"missing\": [\"...\"]）。只输出 JSON。"
)


async def run_wrong_intake(req, session_id: str, turn_id: str, user_prefix: str) -> AsyncGenerator[Dict[str, Any], None]:
    """wrong-intake 编排（批3）：对话式结构化抽取→confirmation_card→确认轮落库
    （规格见 dt_baseline/behavior-specs/tutor_wrong_intake.md；数据面=learning_dao）。"""
    req._user_prefix = user_prefix
    gen = _prepare(req, session_id, turn_id)
    kb_block = ref_block = ""
    while True:
        try:
            ev = await gen.__anext__()
        except StopAsyncIteration:
            break
        if isinstance(ev, tuple):
            kb_block, ref_block, _ = ev
            break
        yield ev

    msg = (req.message or "").strip()

    # 确认轮：挂起卡存在 + 确认语义 → 落库（mother_question_find_or_create+wrong_question_add）
    pending = _WRONG_INTAKE_PENDING.get(session_id)
    if pending and (msg in ("确认", "确认保存", "保存", "确认录入", "好的，确认") or msg.startswith("确认")):
        yield _evt("tool_call", "agent", "tools", content="调用工具 wrong_question_save",
                   metadata={"name": "wrong_question_save",
                             "args": {"question": pending.get("question", "")[:80]},
                             "scripted": True},
                   session_id=session_id, turn_id=turn_id)
        save_res: Dict[str, Any] = {}
        try:
            from app.services.learning.learning_dao import (
                mother_question_find_or_create, wrong_question_add,
            )
            mq = mother_question_find_or_create(
                pending.get("question", "")[:60],
                title=pending.get("subject", "") or "错题录入")
            mq_id = (mq or {}).get("mq_id") or (mq or {}).get("id") or ""
            wq_id = wrong_question_add(
                user_prefix, pending.get("question", ""),
                mother_question_id=str(mq_id or ""),
                error_context=f"误答: {pending.get('wrong_answer', '')}",
                question={"question": pending.get("question", ""),
                          "answer": pending.get("correct_answer", "")},
                my_answer=pending.get("wrong_answer", ""),
                error_type=pending.get("error_type") or "concept",
                source="chat")
            save_res = {"ok": True, "wq_id": wq_id, "mq_id": str(mq_id or "")}
        except Exception as e:
            logger.exception("[bridge] wrong_question_save 落库失败")
            save_res = {"ok": False, "error": str(e)[:160]}
        yield _evt("tool_result", "agent", "tools",
                   content=json.dumps(save_res, ensure_ascii=False)[:400],
                   metadata={"name": "wrong_question_save", "ref": "tool://wrong_question_save",
                             "scripted": True},
                   session_id=session_id, turn_id=turn_id)
        _WRONG_INTAKE_PENDING.pop(session_id, None)
        receipt = ("已入库 ✓\n" if save_res.get("ok")
                   else f"落库失败：{save_res.get('error', '未知错误')}\n")
        if save_res.get("ok"):
            receipt += f"母题 {save_res.get('mq_id', '')} 关联错题 {save_res.get('wq_id', '')} 已记录，可在错题本查看。"
        # 回执经 agent loop 润色?——规格 TC2 要求 content×N+落库回执；确定性回执直发（不进 loop）
        for line_i, chunk in enumerate(_chunk_text(receipt)):
            yield _evt("content", "agent", "answer", content=chunk,
                       session_id=session_id, turn_id=turn_id)
        yield _evt("result", "agent", "answer", content=receipt,
                   metadata={"save": save_res},
                   session_id=session_id, turn_id=turn_id)
        yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
                   metadata={"ok": bool(save_res.get("ok")), "saved": bool(save_res.get("ok"))})
        return

    # 抽取轮：LLM 结构化抽取（get_chat_model 平台默认连接——tutor_llm 同款）
    card: Dict[str, Any] = {}
    try:
        from app.services.llm_client import get_chat_model
        resp = get_chat_model(temperature=0).invoke([
            {"role": "system", "content": _EXTRACTION_SYSTEM},
            {"role": "user", "content": msg}])
        txt = str(resp.content)
        card = json.loads(txt[txt.find("{"):txt.rfind("}") + 1])
    except Exception as e:
        logger.warning(f"[bridge] wrong-intake 抽取失败: {e}")
        card = {}

    complete = bool(card.get("complete")) and card.get("question") and card.get("correct_answer")
    if complete:
        pending_card = {
            "question": str(card.get("question", "")),
            "correct_answer": str(card.get("correct_answer", "")),
            "wrong_answer": str(card.get("wrong_answer", "")),
            "error_type": str(card.get("error_type", "concept")),
            "subject": str(card.get("subject", "")),
        }
        _WRONG_INTAKE_PENDING[session_id] = pending_card
        intro = ("我把这道错题整理如下，请确认：\n"
                 f"题面：{pending_card['question'][:120]}\n"
                 f"正确答案：{pending_card['correct_answer']}\n"
                 f"你的答案：{pending_card.get('wrong_answer', '') or '（未提供）'}\n"
                 f"错因归类：{pending_card.get('error_type', 'concept')}\n"
                 "回复「确认」即录入错题本。")
        for chunk in _chunk_text(intro):
            yield _evt("content", "agent", "answer", content=chunk,
                       session_id=session_id, turn_id=turn_id)
        yield _evt("confirmation_card", "agent", "answer", content="错题确认卡",
                   metadata={"question": pending_card["question"],
                             "correct_answer": pending_card["correct_answer"],
                             "wrong_answer": pending_card.get("wrong_answer", ""),
                             "error_type": pending_card.get("error_type", "concept"),
                             "subject": pending_card.get("subject", ""),
                             "source": "wrong_intake"},
                   session_id=session_id, turn_id=turn_id)
        yield _evt("result", "agent", "answer", content=intro,
                   metadata={"confirmation_card": pending_card},
                   session_id=session_id, turn_id=turn_id)
        yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
                   metadata={"ok": True, "pending_confirmation": True})
        return

    # 信息不足：追问（规格 TC3——不 发卡不落库）；对话面走 agent loop（记忆线程内追问更自然）
    parts = ["[wrong-intake 模式]\n你在协助学生录入错题。当前信息不足以结构化成卡，"
             "请自然地追问题面/正确答案/学生的错误答案（一次只追问最关键的一项）。不要编造字段。\n\n"]
    if ref_block:
        parts.append(ref_block)
    if kb_block:
        parts.append(kb_block + "\n\n")
    parts.append(msg or "帮我记一道错题")
    async for ev in _agent_stream(req, session_id, turn_id, parts):
        yield ev


def _chunk_text(text: str, size: int = 48) -> List[str]:
    """确定性回执分片（content×N 流感——不进 LLM）。"""
    return [text[i:i + size] for i in range(0, len(text), size)] or [""]


def _safe_json(v: Any) -> Any:
    """tool args→可 JSON 序列化（langgraph input 可能含非基元对象）。"""
    try:
        json.dumps(v)
        return v
    except Exception:
        return {"repr": repr(v)[:400]}
