"""数据智能对话 API（FastAPI 路由）

基于 DeepAgents 框架（LLM + kg_api 工具 + SKILL.md 文件驱动），提供：
  POST /api/data-intelligence/chat/freeplan/stream
    - 入参：thread_id, user_input, user_selection（可选）
    - 出参：SSE 流式推送（think/token/final/recommend/sql_result/trace/done）
  GET /api/data-intelligence/health
    - 健康检查
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-intelligence", tags=["data-intelligence"])


# kg_api action -> 中文任务名（on_tool_start 映射 task_label）
# action -> (技能包中文名, 工具中文名)
_ACTION_TOOL_MAP: Dict[str, tuple] = {
    "fetch_l1_l2_tree":       ("定位",     "获取层级树"),
    "validate_l2":            ("定位",     "校验L2"),
    "fetch_subgraph":         ("定位",     "获取子图"),
    "validate_attributes":    ("定位",     "校验属性"),
    "get_entity_relations":   ("关系查询", "查实体关系"),
    "fetch_join_expr":        ("关系查询", "查JOIN字段"),
    "validate_safe_sql":      ("SQL执行",  "校验SQL安全"),
    "execute_sql":            ("SQL执行",  "执行SQL"),
    "list_tables":            ("SQL执行",  "列出表名"),
    "get_entity_source_mode": ("API取数",  "查数据源模式"),
    "execute_api_sql":        ("API取数",  "多源API联邦SQL"),
    "execute_entity_api":     ("API取数",  "对象API执行"),
    "execute_doris_sql":      ("Doris整合", "Doris跨对象SQL"),
    "search_entities":        ("搜索探索", "搜索实体"),
    "search_concepts":        ("搜索探索", "搜索概念"),
}

# read_file 技能目录 -> 技能中文名
_SKILL_CODE_CN: Dict[str, str] = {
    "locate": "定位", "relate": "关系查询", "sql-exec": "SQL执行",
    "explore": "搜索探索", "sql-query": "SQL拼接",
    "explain-concept": "概念解释", "explore-graph": "图谱浏览",
    "find-entity": "字段反查", "trace-lineage": "数据血缘",
}

# task_label 仍需保留（on_tool_end 按 task 匹配 result_summary）
_KG_ACTION_LABELS: Dict[str, str] = {
    "fetch_l1_l2_tree": "获取层级树", "validate_l2": "校验L2",
    "fetch_subgraph": "获取子图", "validate_attributes": "校验属性",
    "fetch_join_expr": "查JOIN字段", "validate_safe_sql": "校验SQL",
    "execute_sql": "SQL执行", "search_concepts": "搜索概念",
    "search_entities": "搜索实体", "get_entity_relations": "查关系",
    "list_tables": "列出表名", "get_entity_source_mode": "查数据源模式",
    "execute_api_sql": "API联邦SQL",
    "execute_entity_api": "对象API执行",
    "execute_doris_sql": "Doris跨对象SQL",
}


def _build_action_detail(name: str, action: str, inp: dict) -> str:
    """on_tool_start 时拼接自然语言 detail：调用'XX'技能包的'XX'工具。"""
    if name == "read_file":
        fp = inp.get("file_path", "") if isinstance(inp, dict) else ""
        skill_cn = ""
        if isinstance(fp, str) and "/skills/" in fp:
            code = fp.split("/skills/")[-1].split("/")[0]
            skill_cn = _SKILL_CODE_CN.get(code, code)
        return f"调用{skill_cn}技能的'读取技能文件'" if skill_cn else "读取技能文件"
    if name == "write_todos":
        todos = inp.get("todos", []) if isinstance(inp, dict) else []
        steps = [t.get("content", "") if isinstance(t, dict) else str(t) for t in todos][:5]
        return "LLM规划任务步骤：" + "；".join(s for s in steps if s) if steps else "LLM规划任务步骤"
    if name == "kg_api":
        pkg_tool = _ACTION_TOOL_MAP.get(action)
        if pkg_tool:
            pkg_cn, tool_cn = pkg_tool
            return f"调用{pkg_cn}技能的'{tool_cn}{action}'"
        return f"调用工具'{action}'"
    return f"调用工具 {name}"


def _infer_decision_task(tc_name: str, tc_args) -> str:
    """根据 LLM 决策的工具调用推断判定标题（带推理结论）。"""
    if tc_name == "read_file":
        fp = tc_args.get("file_path", "") if isinstance(tc_args, dict) else ""
        code = ""
        if "/skills/" in str(fp):
            code = str(fp).split("/skills/")[-1].split("/")[0]
        cn = _SKILL_CODE_CN.get(code, code)
        return f"选择技能（判定使用'{cn}'技能）" if cn else "选择技能"
    if tc_name == "write_todos":
        return "LLM规划任务步骤"
    if tc_name == "kg_api":
        action = tc_args.get("action", "") if isinstance(tc_args, dict) else ""
        params = tc_args.get("params", "") if isinstance(tc_args, dict) else ""
        pkg_tool = _ACTION_TOOL_MAP.get(action)
        tool_cn = pkg_tool[1] if pkg_tool else action
        conclusion = ""
        try:
            import json as _j
            p = _j.loads(params) if params else {}
        except Exception:
            p = {}
        if action == "validate_l2" and p.get("l2_name"):
            conclusion = f"，推理出L2={p['l2_name']}"
        elif action == "execute_sql" and p.get("sql"):
            conclusion = f"，SQL：{str(p['sql'])[:50]}"
        elif action == "search_entities" and p.get("keyword"):
            conclusion = f"，关键词：{p['keyword']}"
        return f"判定{tool_cn}{conclusion}" if conclusion else f"判定：调用'{tool_cn}'"
    return "LLM思考判定"


def _build_result_summary(last_task: str, parsed: dict) -> str:
    """on_tool_end 时根据工具返回结果拼接自然语言结论 result_summary。"""
    if not isinstance(parsed, dict):
        return ""
    if last_task == "读技能":
        # read_file 返回的是技能文件内容，无法从内容提取技能名，靠 detail 已含
        return "判定使用该技能"
    if last_task == "获取层级树":
        l1_cnt = len(parsed.get("l1_list", [])) if isinstance(parsed.get("l1_list"), list) else 0
        # 统计 L2 总数
        l2_cnt = 0
        for l1 in parsed.get("l1_list", []) or []:
            if isinstance(l1, dict):
                l2_cnt += len(l1.get("l2_list", []) or [])
        return f"返回 {l1_cnt} 个L1、{l2_cnt} 个L2"
    if last_task == "校验L2":
        if parsed.get("valid"):
            return f"锁定 L2：{parsed.get('l2_name', '')}"
        return f"L2 校验未通过：{parsed.get('reason', '')}"
    if last_task == "获取子图":
        entities = parsed.get("l2x_entities", []) or []
        cnt = len(entities)
        main_tbl = next((e.get("entity_name", "") for e in entities if isinstance(e, dict) and e.get("is_main_table")), "")
        return f"该 L2 下共 {cnt} 个实体" + (f"，主表：{main_tbl}" if main_tbl else "")
    if last_task == "校验属性":
        attrs = parsed.get("attributes", []) or []
        names = [a.get("attribute_name", "") for a in attrs if isinstance(a, dict)][:5]
        return f"命中 {len(attrs)} 个属性" + (f"：{', '.join(names)}" if names else "")
    if last_task == "查关系":
        rels = parsed.get("relations", []) or []
        return f"找到 {len(rels)} 条关联关系"
    if last_task == "搜索实体":
        ents = parsed.get("entities", []) or []
        flds = parsed.get("fields", []) or []
        return f"命中 {len(ents)} 个实体、{len(flds)} 个字段"
    if last_task == "查JOIN字段":
        join_on = parsed.get("join_on", "")
        return f"JOIN 字段：{join_on}" if join_on else "未找到 JOIN 关系"
    if last_task == "校验SQL":
        if parsed.get("safe"):
            return "SQL 校验通过"
        return f"校验失败：{parsed.get('reason', '')}"
    if last_task == "SQL执行":
        row_cnt = parsed.get("row_count", 0)
        cols = parsed.get("columns", []) or []
        col_str = ", ".join(str(c) for c in cols[:4])
        return f"返回 {row_cnt} 行数据" + (f"，字段：{col_str}{'...' if len(cols) > 4 else ''}" if cols else "")
    # 兜底：用 tool_log 首行
    log = parsed.get("log", "")
    if log:
        return log.split("\n")[0][:80]
    return ""


def _build_nonjson_result_summary(last_task: str, tool_name: str, out_str: str) -> str:
    """on_tool_end 时 parsed=None（非 JSON 返回，如 read_file 返回技能文件内容）的结果摘要。"""
    if not out_str:
        return "工具执行完成"
    if last_task == "读技能" or tool_name == "read_file":
        # 技能文件内容，提取标题行（# 开头）
        for line in out_str.split("\n"):
            line = line.strip()
            if line.startswith("# ") and not line.startswith("# ---"):
                return f"读取技能文件：{line[2:].strip()}"
        return f"读取技能文件（{len(out_str)} 字符）"
    if tool_name == "write_todos":
        return "任务规划完成"
    # 兜底：取前 80 字符
    return out_str[:80].replace("\n", " ").strip() + ("..." if len(out_str) > 80 else "")


# --------------------------------------------------------------------------- #
# Pydantic 模型
# --------------------------------------------------------------------------- #


class UserSelection(BaseModel):
    label: Optional[str] = None
    value: Optional[str] = None
    name: Optional[str] = None
    code: Optional[str] = None
    level: Optional[str] = None
    entity_code: Optional[str] = None
    attribute_code: Optional[str] = None
    is_main_table: Optional[bool] = None


class ChatRequest(BaseModel):
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_input: str
    user_selection: List[UserSelection] = Field(default_factory=list)
    format: str = Field(default="default", description="响应格式：default | card")
    llm_connection_id: Optional[str] = Field(default=None, description="指定 LLM 连接 ID（不传则用默认）")
    mode: str = Field(default="free_plan", description="对话模式：free_plan")


class ChatResponse(BaseModel):
    thread_id: str
    current_task: str
    goal: Optional[str] = None
    pending_clarification: Optional[Dict[str, Any]] = None
    confirmed: Dict[str, Any] = Field(default_factory=dict)
    completed_tasks: List[str] = Field(default_factory=list)
    flags: Dict[str, bool] = Field(default_factory=dict)
    trace: List[Dict[str, Any]] = Field(default_factory=list)
    think_stream: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_next: List[Dict[str, str]] = Field(default_factory=list)
    next_step_recommendation: Optional[Dict[str, Any]] = None
    message_card: Optional[Dict[str, Any]] = None


@router.post("/chat/freeplan/stream")
def chat_freeplan_stream(req: ChatRequest):
    """数据资产探查（ReAct 流式对话）。

    - ReAct 模式（create_deep_agent），边规划边思考
    - 全量加载 10 个任务级 SKILL.md 到虚拟文件系统
    - astream_events v2 推送
    """
    async def event_iter():
        try:
            import asyncio as _asyncio
            from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
            from app.services.tupu_deepagent import build_skill_system_message
            from deepagents.backends.utils import create_file_data
            from pathlib import Path as _Path

            # 全量加载 10 个 SKILL.md 到虚拟文件系统（5个能力包 + 5个意图标签）
            skills_dir = _Path(__file__).resolve().parent.parent.parent / "data" / "skills"
            skills_files = {}
            _TASK_SKILLS = [
                # 能力包（工具箱，按需挑用）
                "locate", "relate", "sql-exec", "explore",
                # 意图标签（场景提示词）
                "sql-query", "explain-concept", "explore-graph", "find-entity", "trace-lineage",
                # 场景剧本（业务分析任务，口径固化）
                "scenarios/distribution-overload",
                "scenarios/project-lifecycle-cost",
            ]
            for skill_name in _TASK_SKILLS:
                skill_md = skills_dir / skill_name / "SKILL.md"
                if skill_md.exists():
                    content = skill_md.read_text("utf-8")
                    if content.strip().startswith("---"):
                        path = f"/skills/{skill_name}/SKILL.md"
                        skills_files[path] = create_file_data(content)

            logger.info(f"[FreePlan] 加载 {len(skills_files)} 个技能文件")

            # 创建 DeepAgent（不复用 Plan-Execute 单例）
            from app.services.tupu_deepagent import create_tupu_agent
            from langgraph.checkpoint.memory import MemorySaver
            # 自由规划用 MemorySaver（内存检查点），不持久化，避免与 Plan-Execute 的 SQLite 检查点冲突
            checkpointer = MemorySaver()
            agent = await create_tupu_agent(checkpointer=checkpointer)

            config = {"configurable": {"thread_id": req.thread_id}, "recursion_limit": 80}

            freeplan_prompt = build_skill_system_message()
            input_messages = [
                SystemMessage(content=freeplan_prompt),
                HumanMessage(content=req.user_input),
            ]

            tool_results = {}
            think_stream = []
            final_sent_at = [0.0]
            llm_round = [0]  # LLM 推理轮次计数器（每轮 ReAct 循环 +1）
            _last_decision = [""]  # 上一轮决策文本（去重用）

            yield f"event: status\n"
            yield f"data: {json.dumps({'node': 'DeepAgent', 'phase': 'running', 'text': '自由规划中...', 'routed_skill': 'free_plan'}, ensure_ascii=False)}\n\n"

            # 复用 ReAct 路径的事件消费逻辑
            async def _consume_events():
                import time as _time
                aiter = agent.astream_events(
                    {"messages": input_messages, "files": skills_files},
                    config=config,
                    version="v2",
                ).__aiter__()
                while True:
                    try:
                        if final_sent_at[0] > 0:
                            remaining = (final_sent_at[0] + 3.0) - _time.time()
                            if remaining <= 0:
                                break
                            ev = await _asyncio.wait_for(aiter.__anext__(), timeout=remaining)
                        else:
                            ev = await aiter.__anext__()
                    except StopAsyncIteration:
                        break
                    except _asyncio.TimeoutError:
                        break
                    etype = ev.get("event", "")
                    name = ev.get("name", "")
                    data = ev.get("data", {})

                    if etype == "on_chat_model_stream":
                        chunk = data.get("chunk")
                        if chunk is None:
                            continue
                        content = getattr(chunk, "content", "")
                        if content and isinstance(content, str) and content.strip():
                            yield f"event: token\n"
                            yield f"data: {json.dumps({'text': content}, ensure_ascii=False)}\n\n"
                        # reasoning_content 不单独推 think_token（思考决策统一在 on_chat_model_end 推送，避免一轮多工具 task 冲突）
                        continue

                    if etype == "on_chat_model_end":
                        out = data.get("output")
                        if out is not None:
                            has_tc = bool(getattr(out, "tool_calls", None))
                            c = getattr(out, "content", "")
                            if not has_tc and c and isinstance(c, str) and c.strip():
                                tool_results["ai_reply"] = c
                            # 有 tool_calls -> LLM 做了判定决策，推送推理+决策信息
                            elif has_tc:
                                _tcs = getattr(out, "tool_calls", None) or []
                                # 取上一步技能执行的结果摘要（衔接上下文）
                                _prev_summary = ""
                                for _ts in reversed(think_stream):
                                    if _ts.get("kind") in ("skill", "plan") and _ts.get("result_summary"):
                                        _prev_summary = _ts["result_summary"]
                                        break
                                _prev_text = f"{_prev_summary}完成" if _prev_summary else ("起点" if llm_round[0] == 0 else "")
                                _c_text = (c if (c and isinstance(c, str) and c.strip()) else "")
                                for _tc_idx, _tc in enumerate(_tcs):
                                    _tc_name = _tc.get("name", "") if isinstance(_tc, dict) else getattr(_tc, "name", "")
                                    _tc_args = _tc.get("args", {}) if isinstance(_tc, dict) else getattr(_tc, "args", {})
                                    # task 用对应工具中文名，与 on_tool_start 的 task_label 一致，
                                    # 使思考决策合并进同一执行条目（思考决策↔技能执行严格交替，避免"第N轮(idx)"扎堆）
                                    if _tc_name == "kg_api" and isinstance(_tc_args, dict):
                                        _rtask = _KG_ACTION_LABELS.get(_tc_args.get("action", ""), _tc_args.get("action", ""))
                                    elif _tc_name == "read_file":
                                        _rtask = "读技能"
                                    elif _tc_name == "write_todos":
                                        _rtask = "任务规划"
                                    else:
                                        _rtask = _tc_name
                                    _decision = ""
                                    if _tc_name == "kg_api" and isinstance(_tc_args, dict):
                                        _pkg_tool = _ACTION_TOOL_MAP.get(_tc_args.get("action", ""))
                                        _pkg_cn = _pkg_tool[0] if _pkg_tool else ""
                                        _tool_cn = _pkg_tool[1] if _pkg_tool else _tc_args.get("action", "")
                                        _action_en = _tc_args.get("action", "")
                                        _decision = f"，下一步准备调用{_pkg_cn}技能的'{_tool_cn}{_action_en}'"
                                    elif _tc_name == "read_file":
                                        _decision = "，下一步准备读取技能文件"
                                    elif _tc_name == "write_todos":
                                        _decision = "，下一步准备规划任务步骤"
                                    else:
                                        _decision = f"，下一步准备调用 {_tc_name}"
                                    # 去重：与上一轮相同决策则不重复追加
                                    if _decision and _decision == _last_decision[0]:
                                        _decision = ""
                                    _last_decision[0] = _decision
                                    # 第一个tool_call带"上一步完成+决策+content"，后续只带决策
                                    _reasoning = (_prev_text + _decision + _c_text) if _tc_idx == 0 else _decision
                                    _reasoning = _reasoning.lstrip("，")  # 去掉开头多余逗号（上一步无结果时 _prev_text 为空）
                                    if _reasoning.strip():
                                        yield f"event: think_token\n"
                                        yield f"data: {json.dumps({'task': _rtask, 'kind': 'decision', 'token': _reasoning}, ensure_ascii=False)}\n\n"
                                llm_round[0] += 1
                        continue

                    if etype == "on_tool_start":
                        task_label = name
                        inp = data.get("input", {})
                        action = inp.get("action", "") if (name == "kg_api" and isinstance(inp, dict)) else ""
                        # 判定 kind：write_todos=规划，其他=技能调用
                        if name == "write_todos":
                            _kind = "plan"
                            task_label = "任务规划"
                        else:
                            _kind = "skill"
                            if name == "kg_api" and isinstance(inp, dict):
                                task_label = _KG_ACTION_LABELS.get(action, action)
                            elif name == "read_file":
                                task_label = "读技能"
                        # 自然语言 detail（调用'XX'技能包的'XX'工具）
                        input_detail = _build_action_detail(name, action, inp if isinstance(inp, dict) else {})
                        # 中文参数摘要（不再暴露 action=xxx, params=xxx）
                        input_summary = ""
                        if name == "kg_api" and isinstance(inp, dict):
                            raw_params = inp.get("params", "")
                            input_summary = f"输入参数：{str(raw_params)[:200]}" if raw_params else ""
                        elif name == "write_todos":
                            todos = inp.get("todos", []) if isinstance(inp, dict) else []
                            input_summary = f"规划 {len(todos)} 步" if todos else ""
                        elif inp:
                            input_summary = f"输入参数：{str(inp)[:200]}"
                        yield f"event: think\n"
                        yield f"data: {json.dumps({'task': task_label, 'kind': _kind, 'strategy': 'free_plan', 'action': input_detail, 'detail': input_detail, 'input_summary': input_summary}, ensure_ascii=False)}\n\n"
                        think_stream.append({"task": task_label, "kind": _kind, "strategy": "free_plan", "action": input_detail, "result_status": "", "detail": input_detail, "input_summary": input_summary})
                        continue

                    if etype == "on_tool_end":
                        output = data.get("output")
                        out_str = ""
                        if output is not None:
                            if isinstance(output, str):
                                out_str = output
                            elif isinstance(output, dict):
                                out_str = json.dumps(output, ensure_ascii=False, default=str)
                            elif hasattr(output, "content"):
                                # content 可能是 dict/list（非 str），需用 json.dumps 而非 str()
                                if isinstance(output.content, str):
                                    out_str = output.content
                                elif isinstance(output.content, (dict, list)):
                                    out_str = json.dumps(output.content, ensure_ascii=False, default=str)
                                else:
                                    out_str = str(output.content)
                            else:
                                out_str = str(output)
                        parsed = None
                        if isinstance(out_str, str) and "{" in out_str:
                            import re as _re
                            brace_idx = out_str.find("{")
                            if brace_idx > 0:
                                out_str = out_str[brace_idx:]
                            json_match = _re.search(r'\{.*\}', out_str, _re.DOTALL)
                            if json_match:
                                try:
                                    parsed = json.loads(json_match.group(0))
                                except Exception:
                                    parsed = None
                                # JSON 解析失败时，尝试用 ast.literal_eval 处理 Python dict str（单引号）
                                if parsed is None:
                                    try:
                                        import ast as _ast
                                        parsed = _ast.literal_eval(json_match.group(0))
                                        # 转成标准 dict 后再 json.dumps 确保可序列化
                                        if isinstance(parsed, dict):
                                            parsed = json.loads(json.dumps(parsed, ensure_ascii=False, default=str))
                                    except Exception as _ast_err:
                                        print(f"[DEBUG ast.literal_eval failed] err={_ast_err} match_len={len(json_match.group(0))} match_tail={json_match.group(0)[-100:]}", flush=True)
                                        parsed = None

                        last_task = think_stream[-1]["task"] if think_stream else ""

                        # 调试日志：诊断 on_tool_end 解析情况
                        print(f"[DEBUG freeplan on_tool_end] name={name} last_task={last_task} parsed_is_none={parsed is None} out_str[:200]={out_str[:200]}", flush=True)

                        if parsed:
                            tool_log = parsed.get("log", "") if isinstance(parsed, dict) else ""
                            if last_task == "校验L2":
                                tool_results["l2_name"] = parsed.get("l2_name", "")
                                tool_results["l2_id"] = parsed.get("l2_id", "")
                                yield f"event: trace\n"
                                yield f"data: {json.dumps({'node': '校验L2', 'status': 'locked' if parsed.get('valid') else 'needs_clarification', 'l2_name': parsed.get('l2_name', ''), 'detail': tool_log}, ensure_ascii=False)}\n\n"
                            elif last_task == "SQL执行":
                                tool_results["sql_executed"] = True
                                tool_results["sql_result"] = parsed
                                tool_results["assembled_sql"] = parsed.get("sql", "")
                                yield f"event: trace\n"
                                yield f"data: {json.dumps({'node': 'SQL执行', 'status': 'done', 'row_count': parsed.get('row_count', 0), 'detail': tool_log}, ensure_ascii=False)}\n\n"
                                yield f"event: sql_result\n"
                                yield f"data: {json.dumps({'columns': parsed.get('columns', []), 'rows': parsed.get('rows', []), 'row_count': parsed.get('row_count', 0), 'sql': parsed.get('sql', '')}, ensure_ascii=False, default=str)}\n\n"
                            else:
                                if tool_log:
                                    yield f"event: trace\n"
                                    yield f"data: {json.dumps({'node': last_task or name, 'status': 'done', 'detail': tool_log}, ensure_ascii=False)}\n\n"

                        # 无论 parsed 是否为 None，都更新 think_stream 末项的结果（read_file 等非 JSON 返回也要有结果）
                        if think_stream and think_stream[-1].get("task") == last_task:
                            if parsed:
                                _rs_status = "locked" if (parsed.get("safe", parsed.get("valid", True))) else "done"
                                result_summary = _build_result_summary(last_task, parsed)
                            else:
                                # 非 JSON 返回（如 read_file 返回技能文件内容）
                                _rs_status = "done"
                                result_summary = _build_nonjson_result_summary(last_task, name, out_str)
                            think_stream[-1]["result_status"] = _rs_status
                            if result_summary:
                                think_stream[-1]["result_summary"] = result_summary
                            # 推送 think 更新事件：让前端实时显示结果结论（去掉 raw_log/result_status 冗余字段）
                            _end_kind = think_stream[-1].get("kind", "skill") if think_stream else "skill"
                            yield f"event: think\n"
                            yield f"data: {json.dumps({'task': last_task, 'kind': _end_kind, 'result_summary': result_summary}, ensure_ascii=False)}\n\n"
                        continue

                    if etype == "on_custom_event":
                        cdata = data
                        if isinstance(cdata, dict) and cdata.get("type") == "think_token":
                            yield f"event: think_token\n"
                            yield f"data: {json.dumps({'task': cdata.get('task', '推理'), 'kind': 'decision', 'token': cdata.get('token', '')}, ensure_ascii=False)}\n\n"
                        continue

                    if etype == "on_chain_start" and name in ("model", "tools"):
                        yield f"event: status\n"
                        yield f"data: {json.dumps({'node': name, 'phase': 'running', 'text': f'{name}执行中'}, ensure_ascii=False)}\n\n"
                    elif etype == "on_chain_end" and name in ("model", "tools"):
                        yield f"event: status\n"
                        yield f"data: {json.dumps({'node': name, 'phase': 'done', 'text': f'{name}完成'}, ensure_ascii=False)}\n\n"

            consume_error: Optional[Exception] = None
            try:
                async for sse_chunk in _consume_events():
                    yield sse_chunk
            except Exception as e:
                import traceback as _tb
                _tb_str = _tb.format_exc()
                logger.warning(f"[FreePlan] astream_events 消费异常: {e}\n{_tb_str}")
                consume_error = e

            # 消费异常时：已推送的中间步骤可能不全，直接发 error 事件终止，避免发空 done 让前端误以为成功
            if consume_error is not None:
                err_msg = str(consume_error) or repr(consume_error) or "DeepAgent 执行异常（LLM 调用失败或超时）"
                yield f"event: error\n"
                yield f"data: {json.dumps({'error': err_msg}, ensure_ascii=False)}\n\n"
                return

            # final：优先从 state 取最后一条 AIMessage（最终回复），避免推中间步骤汇报
            final_answer = ""
            try:
                final_state = await _asyncio.wait_for(agent.aget_state(config), timeout=10)
                msgs = final_state.values.get("messages", []) if final_state.values else []
                for msg in reversed(msgs):
                    if msg.__class__.__name__ == "AIMessage" and not getattr(msg, "tool_calls", None):
                        c = msg.content if isinstance(msg.content, str) else str(msg.content)
                        if c and c.strip():
                            final_answer = c
                            break
            except Exception:
                pass
            # state 无最终回复时，用 on_chat_model_end 捕获的 ai_reply
            if not final_answer:
                final_answer = tool_results.get("ai_reply", "")

            # 动态总结：SQL 执行成功有数据时，用 LLM 生成自然语言总结覆盖（对齐数据问答）
            if tool_results.get("sql_executed") and tool_results.get("sql_result"):
                sr = tool_results["sql_result"]
                row_cnt = sr.get("row_count", 0)
                cols = sr.get("columns", [])
                rows_data = sr.get("rows", [])
                if row_cnt > 0 and cols:
                    rows_preview = rows_data[:3]
                    data_preview = f"查询返回 {row_cnt} 行数据，字段：{', '.join(str(c) for c in cols)}\n数据预览（前3行）：\n"
                    for row in rows_preview:
                        data_preview += " | ".join(str(cell) for cell in row) + "\n"
                    summary_prompt = (
                        f"基于以下查询结果和定位信息，生成结构化最终答案。\n\n"
                        f"用户问题：{req.user_input}\n"
                        f"定位信息：业务域L2={tool_results.get('l2_name', '')}, 主表={tool_results.get('entity_name', '')}\n"
                        f"{data_preview}\n"
                        f"必须严格按以下 Markdown 结构输出（标题用 ## 开头，顺序固定）：\n\n"
                        f"## 一、综合结论\n（2-3句自然语言总结，引用具体数据值，指出数据特征）\n\n"
                        f"## 二、定位实体\n（说明定位到的业务域L2、主表实体）\n\n"
                        f"## 三、返回数据\n（说明返回行数、关键字段、典型值）\n\n"
                        f"## 四、推荐问题\n（推荐3-5个后续问题，用 1. 2. 3. 编号，每行一个）"
                    )
                    try:
                        from app.services.llm_client import get_chat_model
                        summary_model = get_chat_model(temperature=0.4, streaming=False)
                        summary_resp = await _asyncio.wait_for(
                            summary_model.ainvoke([HumanMessage(content=summary_prompt)]),
                            timeout=15.0,
                        )
                        dynamic_summary = summary_resp.content if isinstance(summary_resp.content, str) else str(summary_resp.content)
                        if dynamic_summary and dynamic_summary.strip():
                            final_answer = dynamic_summary.strip()
                    except Exception as e:
                        _e_str = str(e) or repr(e) or "(空异常)"
                        logger.warning(f"[FreePlan] 动态总结失败: {_e_str}")
                        # 动态总结失败且 DeepAgent 未自生成答案时，用数据采样兜底，避免 final_answer 为空
                        if not final_answer:
                            final_answer = (
                                f"查询返回 {row_cnt} 行数据，字段：{', '.join(str(c) for c in cols)}。\n"
                                f"数据预览（前3行）：\n" + "\n".join(
                                    " | ".join(str(cell) for cell in row) for row in rows_preview
                                )
                            )

            if final_answer and final_answer.strip():
                import time as _t2
                final_sent_at[0] = _t2.time()
                yield f"event: final\n"
                yield f"data: {json.dumps({'answer': final_answer}, ensure_ascii=False)}\n\n"

            # 推送推荐问题
            recs = ["统计用电客户总数", "查客户的联系电话", "什么是变压器"]
            yield f"event: recommend\n"
            yield f"data: {json.dumps({'questions': [{'label': r, 'shortcut': r} for r in recs]}, ensure_ascii=False)}\n\n"

            # 构建 confirmed
            confirmed = {
                "L2": tool_results.get("l2_name", ""),
                "L2_id": tool_results.get("l2_id", ""),
                "L2X": tool_results.get("entity_code", ""),
                "L2X_name": tool_results.get("entity_name", ""),
                "attributes": tool_results.get("attributes", []),
                "assembled_sql": tool_results.get("assembled_sql", ""),
            }

            # SQL 执行结果（供前端渲染数据表格）
            sql_result_data = None
            _sr = tool_results.get("sql_result")
            if _sr and isinstance(_sr, dict) and not _sr.get("error"):
                sql_result_data = {
                    "columns": _sr.get("columns", []),
                    "rows": _sr.get("rows", []),
                    "row_count": _sr.get("row_count", 0),
                    "sql": tool_results.get("assembled_sql", ""),
                }

            # 推送 done
            final_response = {
                "thread_id": req.thread_id,
                "current_task": "DeepAgent",
                "goal": "free_plan",
                "routed_skill": "free_plan",
                "pending_clarification": None,
                "confirmed": confirmed,
                "completed_tasks": [t["task"] for t in think_stream],
                "flags": {
                    "chain_locked": bool(confirmed.get("L2")),
                    "entity_locked": bool(confirmed.get("L2X")),
                    "sql_executed": tool_results.get("sql_executed", False),
                },
                "think_stream": think_stream,
                "final_answer": final_answer,
                "final_answer_structured": None,
                "sql_result": sql_result_data,
                "recommendations": [{"label": r, "shortcut": r} for r in recs],
                "next_step_recommendation": None,
                "message_card": None,
                "sql_result": tool_results.get("sql_result"),
            }
            yield f"event: done\n"
            yield f"data: {json.dumps(final_response, ensure_ascii=False, default=str)}\n\n"

        except Exception as e:
            import traceback as _tb
            logger.error(f"[FreePlan] event_iter 异常: {e}\n{_tb.format_exc()}")
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_iter(), media_type="text/event-stream")




@router.get("/health")
def health() -> Dict[str, str]:
    """健康检查"""
    return {"status": "ok", "service": "data-intelligence"}
