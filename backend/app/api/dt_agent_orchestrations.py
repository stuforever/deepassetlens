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

EXPERT_ID = "sishu"

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


# ---------------------------------------------------------------------------
# v4批3 3.1：判分自研（E-24① 收口）——评分提示词与多模态构造均为平台自撰实现
# （语义规格=判定首行结论+分条反馈+多解承认+针对作答；行为以批0 黑盒基线重放对拍，
# 容差±5+理由语义等价）。vendor quiz_judge 导入清零，物理文件随批16 树删。
# ---------------------------------------------------------------------------
_JUDGE_ZH_SYSTEM = (
    "你是批改测验作答的助教：严谨、具体、对学习者友好。基于题目、参考答案与解析，"
    "对学习者的作答给出针对性判定与反馈。\n"
    "输出格式：\n"
    "1) 第一行给判定结论——✅ 正确 / ⚠️ 部分正确 / ❌ 不正确——并附一句关键依据；\n"
    "2) 接着分条说明：作答中正确的部分、错误或遗漏的部分、应当如何修正；\n"
    "3) 若该题存在多种合理答案，须承认学习者作答里的合理成分；\n"
    "4) 点评必须紧扣学习者提交的内容本身，不得空泛。\n"
    "5) 使用中文。"
)
_JUDGE_EN_SYSTEM = (
    "You grade quiz submissions as a teaching assistant: rigorous, specific, and "
    "encouraging. Use the question, reference answer, and explanation to assess the "
    "learner's answer.\n"
    "Output format:\n"
    "1) First line: the verdict — ✅ Correct / ⚠️ Partially correct / ❌ Incorrect — plus "
    "one sentence with the key reason;\n"
    "2) Then itemize: what was right, what was wrong or missing, and how to fix it;\n"
    "3) If multiple reasonable answers exist, acknowledge the valid parts of the submission;\n"
    "4) Address the learner's actual submission — never generic;\n"
    "5) Reply in English."
)


def _judge_user_prompt(*, language: str, question: str, question_type: str,
                       options, correct_answer: str, explanation: str,
                       user_answer: str, has_image: bool, image_count: int = 0) -> str:
    """判分 user prompt（自研拼装——字段面与措辞自主定义）。"""
    zh = language != "en"
    NL = chr(10)
    opt_lines = ""
    if options:
        try:
            opt_lines = NL.join(f"  {k}. {v}" for k, v in options.items())
        except Exception:
            opt_lines = ""
    parts = [(f"题目类型：{question_type or 'unknown'}" if zh
              else f"Question type: {question_type or 'unknown'}"),
             (f"题干：{NL}{question}" if zh else f"Question:{NL}{question}")]
    if opt_lines:
        parts.append((f"选项：{NL}" if zh else f"Options:{NL}") + opt_lines)
    if correct_answer:
        parts.append((f"参考答案：{NL}" if zh else f"Reference answer:{NL}") + correct_answer)
    if explanation:
        parts.append((f"参考解析：{NL}" if zh else f"Reference explanation:{NL}") + explanation)
    empty_note = "（未提供文字作答）" if zh else "(no typed answer provided)"
    parts.append((f"学习者作答：{NL}" if zh else f"Learner's answer:{NL}")
                 + (user_answer.strip() if user_answer and user_answer.strip() else empty_note))
    if has_image:
        note = (f"学习者另附了 {image_count} 张图片，请结合图片内容一并判定。"
                if zh else
                f"The learner attached {image_count} image(s); grade with the image content in mind.")
        parts.append(note)
    parts.append("请给出针对该作答的判定与反馈。" if zh else "Provide the verdict and feedback for this submission.")
    return NL.join(parts)


async def _judge_multimodal_content(*, text: str, image_records: list) -> list:
    """判分多模态 content 组装（自研）：base64→data_url；http(s) 直传；
    本地 /api/attachments 路径批14 平台附件面落地前不做字节回源（如实降级为 URL 直传）。"""
    content: list = [{"type": "text", "text": text}]
    for rec in image_records:
        b64 = rec.get("base64") or ""
        url = rec.get("url") or ""
        mime = rec.get("mime_type") or "image/png"
        if b64:
            content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
        elif url:
            content.append({"type": "image_url", "image_url": {"url": url}})
    return content


async def dispatch(req, session_id: str, turn_id: str, user_prefix: str) -> AsyncGenerator[Dict[str, Any], None]:
    """按 skill_code 派发到编排实现（批1 chat+批3 三件+批4 三件）。"""
    code = req.skill_code
    if code == "sishu/chat":
        async for ev in run_chat(req, session_id, turn_id, user_prefix):
            yield ev
        return
    if code == "sishu/solve":
        async for ev in run_solve(req, session_id, turn_id, user_prefix):
            yield ev
        return
    if code == "sishu/mastery":
        async for ev in run_mastery(req, session_id, turn_id, user_prefix):
            yield ev
        return
    if code == "sishu/wrong-intake":
        async for ev in run_wrong_intake(req, session_id, turn_id, user_prefix):
            yield ev
        return
    if code == "sishu/quiz":
        async for ev in run_quiz(req, session_id, turn_id, user_prefix):
            yield ev
        return
    if code == "sishu/visualize":
        async for ev in run_visualize(req, session_id, turn_id, user_prefix):
            yield ev
        return
    if code == "sishu/research":
        async for ev in run_research(req, session_id, turn_id, user_prefix):
            yield ev
        return
    if code == "sishu/book-generate":
        async for ev in run_book_generate(req, session_id, turn_id, user_prefix):
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
                        *, on_first_content=None, stage_label: str = "answer") -> AsyncGenerator[Dict[str, Any], None]:
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
                    yield _evt("thinking", "agent", stage_label, content=reasoning,
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
                    yield _evt("content", "agent", stage_label, content=c,
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
                            yield _evt("content", "agent", stage_label, content=fa[i:i + 64],
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
                yield _evt("content", "agent", stage_label, content=fa[i:i + 64],
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
                    yield _evt("content", "agent", stage_label, content=fa[i:i + 64],
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


# ---------------------------------------------------------------------------
# 引擎批4：quiz / visualize / research 三编排
# ---------------------------------------------------------------------------

def _cfg(req) -> Dict[str, Any]:
    """桥请求 config（dict 保护）。"""
    c = getattr(req, "config", None)
    return c if isinstance(c, dict) else {}


def _llm_stream_text(system: str, user: str, temperature: float = 0.3):
    """平台默认连接流式文本生成（async generator of chunks）。"""
    from app.services.llm_client import get_chat_model
    model = get_chat_model(temperature=temperature, streaming=True)
    return model.astream([{"role": "system", "content": system},
                          {"role": "user", "content": user}])


async def run_quiz(req, session_id: str, turn_id: str, user_prefix: str) -> AsyncGenerator[Dict[str, Any], None]:
    """quiz 编排（批4）：action=judge 判题回分（vendor quiz_judge prompt 语义 1:1 复用——
    零触导入）/mimic 试卷 PDF 仿制/默认=计划器→结构化出题→自检→题卡事件。"""
    req._user_prefix = user_prefix
    cfg = _cfg(req)
    action = str(cfg.get("action") or "generate")
    kb_block_q = ref_block_q = ""
    gen = _prepare(req, session_id, turn_id)
    while True:
        try:
            ev = await gen.__anext__()
        except StopAsyncIteration:
            break
        if isinstance(ev, tuple):
            kb_block_q, ref_block_q, _ = ev
            break
        yield ev

    if action == "judge":
        # 判题分支（v4批3 3.1：自研评分提示词——vendor quiz_judge 导入清零，黑盒重放对拍）。
        yield _evt("stage_start", "bridge", "judge", content="AI 判分中",
                   session_id=session_id, turn_id=turn_id)
        lang = str(cfg.get("language") or "zh")
        has_image = bool(cfg.get("user_answer_images"))
        user_prompt = _judge_user_prompt(
            language=lang,
            question=str(cfg.get("question") or req.message or ""),
            question_type=str(cfg.get("question_type") or ""),
            options=cfg.get("options"),
            correct_answer=str(cfg.get("correct_answer") or ""),
            explanation=str(cfg.get("explanation") or ""),
            user_answer=str(cfg.get("user_answer") or ""),
            has_image=has_image, image_count=len(cfg.get("user_answer_images") or []),
        )
        acc: List[str] = []
        try:
            system_prompt = _JUDGE_EN_SYSTEM if lang == "en" else _JUDGE_ZH_SYSTEM
            from app.services.llm_client import get_chat_model
            model = get_chat_model(temperature=0.1, streaming=True)
            user_msg: Dict[str, Any] = {"role": "user", "content": user_prompt}
            if has_image:
                parts = await _judge_multimodal_content(
                    text=user_prompt,
                    image_records=[img for img in (cfg.get("user_answer_images") or [])
                                   if isinstance(img, dict)])
                user_msg = {"role": "user", "content": parts}
            aiter = model.astream([{"role": "system", "content": system_prompt}, user_msg]).__aiter__()
            while True:
                try:
                    chunk = await aiter.__anext__()
                except StopAsyncIteration:
                    break
                c = getattr(chunk, "content", "")
                if isinstance(c, str) and c:
                    acc.append(c)
                    yield _evt("content", "agent", "judge", content=c,
                               session_id=session_id, turn_id=turn_id)
        except Exception as e:
            logger.exception("[bridge] quiz judge 失败")
            yield _evt("error", "agent", "judge", content=str(e),
                       session_id=session_id, turn_id=turn_id)
            yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
                       metadata={"ok": False})
            return
        final_text = "".join(acc).strip()
        yield _evt("stage_end", "bridge", "judge", session_id=session_id, turn_id=turn_id)
        if final_text:
            yield _evt("result", "agent", "judge", content=final_text,
                       metadata={"action": "judge"}, session_id=session_id, turn_id=turn_id)
        yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
                   metadata={"ok": True, "action": "judge"})
        return

    # 出题分支（generate/mimic）：计划器→结构化出题→自检→题卡事件
    yield _evt("stage_start", "bridge", "plan", content="出题计划中",
               session_id=session_id, turn_id=turn_id)
    mimic_text = ""
    if action == "mimic":
        pdf_b64 = str(cfg.get("quiz_pdf") or cfg.get("pdf_base64") or "")
        atts = getattr(req, "attachments", None) or []
        if not pdf_b64 and atts:
            first = atts[0] if isinstance(atts[0], dict) else {}
            pdf_b64 = str(first.get("base64") or "")
        if pdf_b64:
            import base64 as _b64
            raw = _b64.b64decode(pdf_b64)
            import io as _io
            try:
                import pdfplumber
                with pdfplumber.open(_io.BytesIO(raw)) as pdf:
                    mimic_text = "\n".join((p.extract_text() or "") for p in pdf.pages[:12])
            except Exception:
                try:
                    from pypdf import PdfReader
                    mimic_text = "\n".join((p.extract_text() or "") for p in PdfReader(_io.BytesIO(raw)).pages[:12])
                except Exception as e:
                    logger.warning(f"[bridge] quiz mimic PDF 解析失败: {e}")
        if not mimic_text:
            yield _evt("error", "agent", "plan", content="mimic 需要 PDF 附件且解析失败（pypdf/pdfplumber 均不可用或空文档）",
                       session_id=session_id, turn_id=turn_id)
            yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
                       metadata={"ok": False})
            return

    plan_cfg = {k: cfg.get(k) for k in
                ("question_types", "questionCount", "question_count", "difficulty", "knowledgePoints",
                 "knowledge_points", "gradeBand", "grade_band", "language", "includeAnswers", "include_explanations")
                if cfg.get(k) is not None}
    plan_note = f"[配置]\n{json.dumps(plan_cfg, ensure_ascii=False)}\n\n" if plan_cfg else ""
    yield _evt("stage_end", "bridge", "plan", session_id=session_id, turn_id=turn_id)

    yield _evt("stage_start", "bridge", "generate", content="结构化出题中",
               session_id=session_id, turn_id=turn_id)
    quiz_directive = (
        "[quiz 模式]\n你是出题引擎。按配置与素材生成结构化试卷，返回 JSON：\n"
        "{\"questions\": [{\"question\": \"题干\", \"question_type\": \"multiple_choice|fill_blank|short_answer|math_proof\", "
        "\"options\": {\"A\": \"...\", \"B\": \"...\"} 或 null, \"correct_answer\": \"正确答案\", "
        "\"explanation\": \"解析\", \"difficulty\": \"基础|提高|挑战\"}]}\n"
        "只输出 JSON。题目必须与配置/素材语义一致，不出超纲题。\n\n")
    parts: List[str] = []
    if kb_block_q:
        parts.append(kb_block_q + "\n\n")
    if ref_block_q:
        parts.append(ref_block_q)
    parts.append(quiz_directive + plan_note
                 + (f"[mimic 源试卷]\n{mimic_text[:6000]}\n\n" if mimic_text else "")
                 + (req.message or "按配置出题"))
    acc = []
    try:
        async for ev in _agent_stream(req, session_id, turn_id, parts, stage_label="generate"):
            # v4批3：抑制 agent 循环自带的 result/done 帧（chat 语义）——本编排末尾自产
            # 题卡/summary/result/done（帧序=L6 契约）。
            if ev.get("type") in ("result", "done"):
                continue
            if ev.get("type") == "content":
                acc.append(ev.get("content", ""))
            yield ev
    except Exception as e:
        logger.exception("[bridge] quiz 出题失败")
        yield _evt("error", "agent", "generate", content=str(e),
                   session_id=session_id, turn_id=turn_id)
        yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
                   metadata={"ok": False})
        return
    raw_txt = "".join(acc)
    questions: List[Dict[str, Any]] = []
    try:
        data = json.loads(raw_txt[raw_txt.find("{"):raw_txt.rfind("}") + 1])
        questions = list(data.get("questions") or [])
    except Exception:
        questions = []
    yield _evt("stage_end", "bridge", "generate", session_id=session_id, turn_id=turn_id)

    # 自检（self-check）：逐题校验结构完整性（确定性面——不二次 LLM，省时且可测）
    valid = [q for q in questions if isinstance(q, dict) and q.get("question") and q.get("correct_answer")]
    for i, q in enumerate(valid):
        yield _evt("question_card", "agent", "answer", content="题卡",
                   metadata={"index": i, "question": q.get("question", ""),
                             "question_type": q.get("question_type", "multiple_choice"),
                             "options": q.get("options"), "correct_answer": q.get("correct_answer", ""),
                             "explanation": q.get("explanation", ""), "difficulty": q.get("difficulty", ""),
                             "self_check": "pass"},
                   session_id=session_id, turn_id=turn_id)
    summary = f"共出 {len(valid)} 题（自检通过 {len(valid)}/{len(questions)}）。"
    if valid:
        yield _evt("result", "agent", "answer", content=summary,
                   metadata={"action": action, "count": len(valid), "self_check_total": len(questions),
                             "questions": valid},
                   session_id=session_id, turn_id=turn_id)
    yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
               metadata={"ok": True, "action": action, "count": len(valid)})


_VISUALIZE_TEXT_MODES = {"auto", "svg", "chartjs", "mermaid", "html"}
_VISUALIZE_SYSTEM = (
    "你是可视化引擎。按 render_mode 生成可直接渲染的产物，只输出产物本身（无解释无代码围栏）：\n"
    "- svg: 完整 <svg> 标记\n- chartjs: Chart.js 配置 JSON（含 type/data/options）\n"
    "- mermaid: mermaid 图源码\n- html: 完整自包含 HTML\n"
    "- auto: 按数据形态选最合适的一种并输出。")


async def run_visualize(req, session_id: str, turn_id: str, user_prefix: str) -> AsyncGenerator[Dict[str, Any], None]:
    """visualize 编排（批4）：文本类 render_mode（svg/chartjs/mermaid/html/auto）=LLM 直出产物；
    manim_video/manim_image=LLM 生成 manim 代码→SandboxService(9385 runner) 执行→产物事件。
    render_mode 7 值=frontend lib/visualize-types.ts 枚举 1:1。"""
    req._user_prefix = user_prefix
    cfg = _cfg(req)
    render_mode = str(cfg.get("render_mode") or "auto")
    quality = str(cfg.get("quality") or "standard")
    gen = _prepare(req, session_id, turn_id)
    kb_block = ""
    while True:
        try:
            ev = await gen.__anext__()
        except StopAsyncIteration:
            break
        if isinstance(ev, tuple):
            _, kb_block, _ = ev
            break
        yield ev

    yield _evt("stage_start", "bridge", "generate", content="生成可视化产物",
               session_id=session_id, turn_id=turn_id)
    user = (f"render_mode={render_mode}\nquality={quality}\n\n{kb_block}\n\n" if kb_block else
            f"render_mode={render_mode}\nquality={quality}\n\n") + (req.message or "")

    if render_mode in _VISUALIZE_TEXT_MODES:
        acc = []
        try:
            model = _llm_stream_text(_VISUALIZE_SYSTEM, user, temperature=0.2)
            async for chunk in model:
                c = getattr(chunk, "content", "")
                if isinstance(c, str) and c:
                    acc.append(c)
                    yield _evt("content", "agent", "generate", content=c,
                               session_id=session_id, turn_id=turn_id)
        except Exception as e:
            logger.exception("[bridge] visualize 文本产物失败")
            yield _evt("error", "agent", "generate", content=str(e),
                       session_id=session_id, turn_id=turn_id)
            yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
                       metadata={"ok": False})
            return
        artifact = "".join(acc).strip()
        yield _evt("artifact", "agent", "answer", content="可视化产物",
                   metadata={"render_mode": render_mode, "render_type": render_mode,
                             "content": artifact},
                   session_id=session_id, turn_id=turn_id)
        yield _evt("stage_end", "bridge", "generate", session_id=session_id, turn_id=turn_id)
        yield _evt("result", "agent", "answer", content=artifact or "（空产物）",
                   metadata={"render_mode": render_mode, "artifact": True},
                   session_id=session_id, turn_id=turn_id)
        yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
                   metadata={"ok": True, "render_mode": render_mode})
        return

    # manim 分支：代码→沙箱（vendor SandboxService——runner=DEEPTUTOR_SANDBOX_RUNNER_URL）
    manim_system = ("你是 manim 代码引擎。生成单文件 manim Community 版脚本（Scene 类名 Main），"
                    "渲染参数由调用方注入。只输出 Python 代码。")
    code_acc = []
    try:
        model = _llm_stream_text(manim_system, user, temperature=0.2)
        async for chunk in model:
            c = getattr(chunk, "content", "")
            if isinstance(c, str) and c:
                code_acc.append(c)
    except Exception as e:
        yield _evt("error", "agent", "generate", content=str(e),
                   session_id=session_id, turn_id=turn_id)
        yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
                   metadata={"ok": False})
        return
    code = "".join(code_acc).strip().removeprefix("```python").removeprefix("```").removesuffix("```")
    exec_res: Dict[str, Any] = {}
    try:
        from app.vendor.deeptutor.services.sandbox.service import SandboxService
        from app.vendor.deeptutor.services.sandbox.spec import ExecRequest, ResourceLimits
        svc = SandboxService()
        script_name = "manim_scene.py"
        out_flag = "-ql" if render_mode == "manim_video" else "-qm"
        req_exec = ExecRequest(
            command=f"bash -lc \"cat > /tmp/{script_name} << 'PYEOF'\n{code}\nPYEOF\nmanim {out_flag} /tmp/{script_name} Main\"",
            limits=ResourceLimits(timeout_s=300, memory_mb=2048, max_output_chars=20_000, cpu_seconds=300))
        result = await svc.run(req_exec, user_id=user_prefix or "anonymous")
        exec_res = {"exit_code": result.exit_code, "stdout": result.stdout[-2000:], "stderr": result.stderr[-2000:],
                    "error": result.error, "timed_out": result.timed_out}
    except Exception as e:
        logger.warning(f"[bridge] manim 沙箱执行失败: {e}")
        exec_res = {"error": str(e)[:300]}
    ok = not exec_res.get("error") and exec_res.get("exit_code") == 0
    yield _evt("artifact", "agent", "answer", content="manim 产物",
               metadata={"render_mode": render_mode, "render_type": render_mode,
                         "exec": exec_res, "ok": ok, "code": code[:4000]},
               session_id=session_id, turn_id=turn_id)
    yield _evt("stage_end", "bridge", "generate", session_id=session_id, turn_id=turn_id)
    if ok:
        yield _evt("result", "agent", "answer", content="manim 产物已生成（见 artifact）",
                   metadata={"render_mode": render_mode, "artifact": True},
                   session_id=session_id, turn_id=turn_id)
    else:
        yield _evt("result", "agent", "answer", content="manim 执行未成功（沙箱环境缺 manim 或超时）",
                   metadata={"render_mode": render_mode, "artifact": True, "degraded": True},
                   session_id=session_id, turn_id=turn_id)
    yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
               metadata={"ok": True, "render_mode": render_mode, "manim_ok": ok})


_RESEARCH_SYSTEM_OUTLINE = (
    "你是研究大纲规划器。按主题与研究配置产出分节大纲，返回 JSON："
    "{\"title\": \"...\", \"sections\": [{\"heading\": \"...\", \"points\": [\"要点1\", \"...\"]}]}。只输出 JSON。")
_RESEARCH_SYSTEM_SECTION = (
    "你是研究写作者。按小节标题与要点写出该节正文（Markdown，300-600 字，有依据地展开，不编造具体数据）。")
_RESEARCH_SYSTEM_MERGE = (
    "你是研究汇总者。把各节正文合并为一篇结构化研究报告（Markdown：标题+导语+各节+结论），不改写事实。")


async def _agent_text(req, session_id: str, turn_id: str, parts: List[str]) -> str:
    """v4批3 3.2：research 相位换芯助手——agent 循环静默采集（outline/section/merge
    原本即静默直驱，帧序不变；agent 循环=平台唯一引擎裁定，§2.1）。"""
    acc: List[str] = []
    async for ev in _agent_stream(req, session_id, turn_id, parts):
        if ev.get("type") == "content":
            acc.append(ev.get("content", ""))
        elif ev.get("type") == "result" and ev.get("content"):
            acc.append(ev.get("content", ""))
    return "".join(acc)


async def run_research(req, session_id: str, turn_id: str, user_prefix: str) -> AsyncGenerator[Dict[str, Any], None]:
    """research 编排（批4）：大纲→分节生成（逐节 progress 事件）→汇总。
    DT 子代理编排语义吸收为分节独立生成+进度事件（E-24③：进程内顺序分节，
    非 langgraph 子代理——桥线程面等价可观察行为=大纲/进度/汇总帧序一致）。"""
    req._user_prefix = user_prefix
    cfg = _cfg(req)
    depth = str(cfg.get("depth") or "standard")
    mode = str(cfg.get("mode") or "report")
    gen = _prepare(req, session_id, turn_id)
    kb_block = ""
    while True:
        try:
            ev = await gen.__anext__()
        except StopAsyncIteration:
            break
        if isinstance(ev, tuple):
            _, kb_block, _ = ev
            break
        yield ev

    topic = req.message or ""
    yield _evt("stage_start", "bridge", "outline", content="规划大纲",
               session_id=session_id, turn_id=turn_id)
    outline: Dict[str, Any] = {}
    try:
        outline_raw = await _agent_text(req, session_id, turn_id, [
            _RESEARCH_SYSTEM_OUTLINE,
            f"主题：{topic}\nmode={mode} depth={depth}\n" +
            (f"\n[知识库素材]\n{kb_block}" if kb_block else "")])
        # agent 循环输出可能带尾文/多段——raw_decode 取首个完整 JSON 对象
        _t = outline_raw[outline_raw.find("{"):]
        outline, _ = json.JSONDecoder().raw_decode(_t)
    except Exception as e:
        logger.exception("[bridge] research 大纲失败")
        yield _evt("error", "agent", "outline", content=str(e),
                   session_id=session_id, turn_id=turn_id)
        yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
                   metadata={"ok": False})
        return
    sections = [s for s in (outline.get("sections") or []) if isinstance(s, dict) and s.get("heading")]
    yield _evt("outline", "agent", "outline", content=outline.get("title", topic),
               metadata={"title": outline.get("title", topic),
                         "sections": [{"heading": s.get("heading"), "points": s.get("points") or []} for s in sections]},
               session_id=session_id, turn_id=turn_id)
    yield _evt("stage_end", "bridge", "outline", session_id=session_id, turn_id=turn_id)

    section_texts: List[str] = []
    for i, sec in enumerate(sections):
        yield _evt("progress", "agent", "sections", content=f"撰写第 {i + 1}/{len(sections)} 节：{sec.get('heading')}",
                   metadata={"index": i, "total": len(sections), "heading": sec.get("heading"),
                             "phase": "section"},
                   session_id=session_id, turn_id=turn_id)
        sec_acc: List[str] = []
        try:
            sec_text = await _agent_text(req, session_id, turn_id, [
                _RESEARCH_SYSTEM_SECTION,
                f"主题：{outline.get('title', topic)}\n"
                f"小节：{sec.get('heading')}\n要点：{json.dumps(sec.get('points') or [], ensure_ascii=False)}"])
            sec_acc.append(sec_text)
        except Exception as e:
            logger.warning(f"[bridge] research 第{i + 1}节失败: {e}")
        section_texts.append("## " + str(sec.get("heading")) + "\n\n" + "".join(sec_acc).strip())

    yield _evt("stage_start", "bridge", "merge", content="汇总成文",
               session_id=session_id, turn_id=turn_id)
    try:
        merged = (await _agent_text(req, session_id, turn_id, [
            _RESEARCH_SYSTEM_MERGE,
            f"标题：{outline.get('title', topic)}\n\n" + "\n\n".join(section_texts)])).strip()
    except Exception as e:
        merged = "\n\n".join(section_texts)
        logger.warning(f"[bridge] research 汇总降级直拼: {e}")
    yield _evt("stage_end", "bridge", "merge", session_id=session_id, turn_id=turn_id)
    if merged:
        yield _evt("result", "agent", "answer", content=merged,
                   metadata={"mode": mode, "depth": depth, "sections": len(sections)},
                   session_id=session_id, turn_id=turn_id)
    yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
               metadata={"ok": True, "sections": len(sections)})


# ---------------------------------------------------------------------------
# 引擎批5：book-generate 编排（书籍工作台生成面切桥）
# ---------------------------------------------------------------------------

def _ws_frame(event: Any) -> Dict[str, Any]:
    """vendor book WS 帧 1:1（_serialize_event 语义拷贝——vendor 零触）。"""
    t = getattr(event, "type", None)
    return {"type": t.value if hasattr(t, "value") else str(t),
            "source": getattr(event, "source", ""),
            "stage": getattr(event, "stage", ""),
            "content": getattr(event, "content", ""),
            "metadata": getattr(event, "metadata", None) or {}}


async def run_book_generate(req, session_id: str, turn_id: str, user_prefix: str) -> AsyncGenerator[Dict[str, Any], None]:
    """book 生成编排（批5 5.4，E-25）：vendor BookEngine 数据面直驱（零触）——
    op=create/confirm_proposal/confirm_spine/compile_page/regenerate_block；
    StreamBus 泵→桥帧 metadata.ws_event（vendor WS 帧同型），终帧 metadata.ws_result=
    vendor WS handler 同款 result 形状。接口面=lib/book-api.ts requestOverBridge。"""
    cfg = _cfg(req)
    op = str(cfg.get("type") or "create")
    import asyncio as _asyncio
    from deeptutor.book import BookProposal, Spine, get_book_engine
    from deeptutor.core.stream import StreamEventType
    from deeptutor.core.stream_bus import StreamBus
    try:
        from deeptutor.book.streaming import SOURCE as BOOK_SOURCE
    except Exception:
        BOOK_SOURCE = None
    try:
        from deeptutor.multi_user.context import set_current_user
        set_current_user(user_prefix)
    except Exception:
        pass
    engine = get_book_engine()

    async def _run_op(bus: StreamBus):
        if op == "create":
            return await engine.create_book(
                user_intent=str(cfg.get("user_intent") or ""),
                chat_session_id=str(cfg.get("chat_session_id") or ""),
                chat_selections=cfg.get("chat_selections") or [],
                notebook_refs=cfg.get("notebook_refs") or [],
                knowledge_bases=cfg.get("knowledge_bases") or [],
                question_categories=[int(c) for c in (cfg.get("question_categories") or [])],
                question_entries=[int(e) for e in (cfg.get("question_entries") or [])],
                language=str(cfg.get("language") or "en"),
                stream=bus)
        if op == "confirm_proposal":
            edited = BookProposal.model_validate(cfg["proposal"]) if cfg.get("proposal") else None
            return await engine.confirm_proposal(
                book_id=str(cfg.get("book_id") or ""), edited_proposal=edited, stream=bus)
        if op == "confirm_spine":
            edited_spine = Spine.model_validate(cfg["spine"]) if cfg.get("spine") else None
            return await engine.confirm_spine(
                book_id=str(cfg.get("book_id") or ""), edited_spine=edited_spine,
                auto_compile=bool(cfg.get("auto_compile", True)), stream=bus)
        if op == "compile_page":
            return await engine.compile_page(
                book_id=str(cfg.get("book_id") or ""), page_id=str(cfg.get("page_id") or ""),
                stream=bus, force=bool(cfg.get("force", False)))
        if op == "regenerate_block":
            return await engine.regenerate_block(
                book_id=str(cfg.get("book_id") or ""), page_id=str(cfg.get("page_id") or ""),
                block_id=str(cfg.get("block_id") or ""),
                params_override=cfg.get("params_override"), stream=bus)
        raise ValueError(f"Unknown book op: {op}")

    bus = StreamBus()
    q: "asyncio.Queue[Any]" = _asyncio.Queue()

    async def _pump() -> None:
        try:
            async for ev in bus.subscribe():
                if BOOK_SOURCE is not None and getattr(ev, "source", "") != BOOK_SOURCE:
                    continue
                q.put_nowait(ev)
        except Exception:
            pass
        finally:
            q.put_nowait(None)

    pump = _asyncio.create_task(_pump())
    op_task = _asyncio.create_task(_run_op(bus))
    op_error: Any = None
    result: Any = None
    # 泵送循环：op 进行中随到随发（vendor WS 同款流面）；op 完成后短窗排水尾帧。
    while not op_task.done():
        getq = _asyncio.ensure_future(q.get())
        waitop = _asyncio.ensure_future(_asyncio.shield(op_task))
        done, _pending = await _asyncio.wait({getq, waitop}, return_when=_asyncio.FIRST_COMPLETED)
        if getq in done:
            ev = getq.result()
            if ev is not None:
                yield _evt("progress", "agent", "book", content="book 事件",
                           metadata={"ws_event": _ws_frame(ev)},
                           session_id=session_id, turn_id=turn_id)
        elif not getq.done():
            getq.cancel()
    while True:  # 尾部排水（引擎收尾帧 + 哨兵）
        try:
            ev = await _asyncio.wait_for(q.get(), timeout=2.0)
        except _asyncio.TimeoutError:
            break
        if ev is not None:
            yield _evt("progress", "agent", "book", content="book 事件",
                       metadata={"ws_event": _ws_frame(ev)},
                       session_id=session_id, turn_id=turn_id)
    pump.cancel()
    await _asyncio.gather(pump, return_exceptions=True)
    try:
        result = op_task.result()
    except Exception as e:
        logger.exception("[bridge] book op %s 失败", op)
        op_error = e
        result = None

    ws_result: Any = None
    if result is not None and op_error is None:
        dumps = lambda m: m.model_dump(mode="json")
        if op == "create":
            book, proposal = result
            ws_result = {"type": "create_result", "book": dumps(book), "proposal": dumps(proposal)}
        elif op == "confirm_proposal":
            book, spine = result
            ws_result = {"type": "confirm_proposal_result", "book": dumps(book), "spine": dumps(spine)}
        elif op == "confirm_spine":
            ws_result = {"type": "confirm_spine_result", "pages": [dumps(p) for p in result]}
        elif op == "compile_page":
            ws_result = {"type": "compile_page_result", "page": dumps(result)}
        elif op == "regenerate_block":
            ws_result = {"type": "regenerate_block_result", "block": dumps(result) if result else None}
    if op_error is not None or ws_result is None:
        yield _evt("error", "agent", "book", content=str(op_error or f"book op {op} 无结果"),
                   session_id=session_id, turn_id=turn_id)
        yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
                   metadata={"ok": False})
        return
    yield _evt("result", "agent", "book", content=f"book {op} 完成",
               metadata={"ws_result": ws_result, "op": op},
               session_id=session_id, turn_id=turn_id)
    yield _evt("done", "bridge", "session", session_id=session_id, turn_id=turn_id,
               metadata={"ok": True, "op": op})


def _safe_json(v: Any) -> Any:
    """tool args→可 JSON 序列化（langgraph input 可能含非基元对象）。"""
    try:
        json.dumps(v)
        return v
    except Exception:
        return {"repr": repr(v)[:400]}
