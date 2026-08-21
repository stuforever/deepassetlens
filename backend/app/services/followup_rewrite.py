"""S3b（G9）追问改写 —— free_plan 入口的追问检测与单轮改写。

设计要点（S 阶段设计 §S3b）：
- 触发：纯规则不打模型（thread 有历史 && 问题 <12 字 || 含指代词「那/它/上述/该/也/再」）；
- 改写：单轮 LLM 调用（会话模型，temperature 沿用 S1d 固化 0.1），结合会话上文与上一轮口径
  （实体/时间/过滤）将追问改写为独立完整问题；
- 兜底：3s 超时或异常 -> 静默回退原问题（不阻塞主链路）；
- 边界：scenario 模式不改写（由调用方在路由后丢弃改写）；改写结果不进示例库（防污染）。
"""
from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# 指代词触发词（设计 §S3b：那/它/上述/该/也/再）
_FOLLOWUP_PRONOUNS = ("那", "它", "上述", "该", "也", "再")
# 短问题阈值（字）
_FOLLOWUP_SHORT_LEN = 12
# 改写单次 LLM 调用超时（秒）+ 流层 wait_for 硬封顶：
# 实测 volces LLM 单轮改写 warm ~3s / 冷 ~9s（长历史上下文 7s）——设计原定 3s 对当前 LLM 过紧
# （3s 封顶下实测每次都超时回退、功能失效），按测量放宽到 8s（仍为有界兜底，仅追问路径付费，
# 普通问题经 17ms 级 aget_state 判断后零额外开销）。超时即静默回退原问题。
_REWRITE_TIMEOUT = 8.0
# 改写上下文裁剪：只取最后一轮问答（上轮用户问题 + 上轮助手回答），每行 150 字——
# 足够携带实体/时间/过滤口径，又显著缩短 prompt 降低改写延迟
_REWRITE_HISTORY_TAIL = 2
_REWRITE_HISTORY_PER_LINE = 150
# 改写温度（S1d 固化 0.1：问数场景要稳不要浪）
_REWRITE_TEMPERATURE = 0.1
# 改写结果最大长度（防御异常输出）
_REWRITE_MAX_LEN = 200


def is_followup_question(question: Optional[str], has_history: bool) -> bool:
    """纯规则检测：thread 有历史 &&（问题 <12 字 || 含指代词）。"""
    if not has_history:
        return False
    q = (question or "").strip()
    if not q:
        return False
    if len(q) < _FOLLOWUP_SHORT_LEN:
        return True
    return any(p in q for p in _FOLLOWUP_PRONOUNS)


def history_text_from_state(prev_state: Any, tail: int = 4, per_line: int = 300) -> str:
    """从 checkpoint state 提取最近对话片段（用于改写上下文）。

    messages 为 langchain BaseMessage 列表；只保留有文本内容的消息，
    按「用户/助手」标注（ToolMessage/工具结果压缩为元信息，不污染改写）。
    """
    if prev_state is None or getattr(prev_state, "values", None) is None:
        return ""
    msgs = list((prev_state.values or {}).get("messages") or [])
    if not msgs:
        return ""
    lines: list[str] = []
    for m in msgs[-tail:]:
        cls = m.__class__.__name__ if m is not None else ""
        content = getattr(m, "content", "")
        if cls in ("HumanMessage",):
            role = "用户"
        elif cls in ("AIMessage",):
            role = "助手"
        elif cls in ("ToolMessage", "SystemMessage", "FunctionMessage"):
            continue  # 工具结果/系统消息不进改写上下文
        else:
            continue
        if isinstance(content, list):
            txt = str(content)[:per_line]
        else:
            txt = str(content or "").strip()[:per_line]
        if not txt:
            continue
        lines.append(f"{role}: {txt}")
    return "\n".join(lines)


def rewrite_followup_question(
    question: str,
    history_text: str,
    connection_id: str = "",
) -> str:
    """单轮 LLM 改写追问为独立完整问题；失败/超时回退空串（调用方用原问题）。

    Args:
        question: 追问原文
        history_text: 会话上文片段
        connection_id: 会话模型连接 id（None 用默认）

    Returns:
        改写后问题；异常/超时/空结果 -> ""（调用方回退原问题）
    """
    try:
        from app.services.llm_client import (
            get_default_llm_connection, get_llm_connection_by_id, call_openai_compatible_chat,
        )
        conn = get_llm_connection_by_id(connection_id, "chat") or get_default_llm_connection("chat")
        if conn is None:
            logger.warning("[FollowupRewrite] 无可用 LLM 连接，回退原问题")
            return ""
        system_prompt = (
            "你是数据问数助手。用户刚发了一条引用会话上文的追问（常含指代词或省略），"
            "请结合会话上文与上一轮问答的口径（实体、时间范围、过滤条件），"
            "把追问改写为一条独立完整的问数问题。只输出改写后的问题本身，"
            "不要任何解释、引号、编号或换行。若无需改写则原样返回。"
        )
        user_prompt = f"会话上文（最近对话）：\n{history_text}\n\n追问原文：{question}"
        out = call_openai_compatible_chat(
            conn,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=_REWRITE_TEMPERATURE,
            timeout=_REWRITE_TIMEOUT,
        )
        out = (out or "").strip().strip('"').strip("“”").strip()
        if not out or len(out) > _REWRITE_MAX_LEN:
            return ""
        return out
    except Exception as e:  # 3s 超时/异常 -> 静默回退，不阻塞主链路
        logger.warning(f"[FollowupRewrite] 改写失败回退原问题: {e}")
        return ""
