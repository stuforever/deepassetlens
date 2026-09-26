# -*- coding: utf-8 -*-
"""G1 询问 Future（切换 v3.0 R1，design §三 G1）：审批 Future 泛化为询问 Future。

复用 S5 HITL 的 asyncio.Future 审批轨（skill_policy._HITL_INTERRUPTS 同构——不新造机制）：
ask_user 工具注册 Future 并 await（agent 在图内暂停）；前端答后两条恢复路：
  1. resume 端点（复用 HITL /resume 通道，扩 question_id+answer 字段）；
  2. 正常下一条 chat 消息（run_chat 入口按 (user_prefix, session_id) 拦截代答——
     会话流语义：问题卡→用户在 composer 打字→答案回流 agent 续跑）。
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

_ASK_TIMEOUT = float(os.getenv("TUPU_ASK_USER_TIMEOUT", "600"))

# qid -> Future（结果 {"answer": str, "source": "resume"|"chat"|"timeout"}）
_PENDING: Dict[str, asyncio.Future] = {}
# (user_prefix, session_id) -> qid（下一条消息代答路由；后到覆盖先到=同会话仅一个活跃问题）
_BY_SESSION: Dict[Tuple[str, str], str] = {}


def create_question(*, question: str, options: Optional[list] = None,
                    user_prefix: str = "", session_id: str = "",
                    timeout: Optional[float] = None) -> Tuple[str, asyncio.Future, float]:
    """注册待答问题：返回 (question_id, Future, 超时秒)。"""
    qid = str(uuid.uuid4())
    fut = asyncio.get_running_loop().create_future()
    _PENDING[qid] = fut
    if user_prefix and session_id:
        old = _BY_SESSION.get((user_prefix, session_id))
        if old and old in _PENDING and not _PENDING[old].done():
            _PENDING[old].set_result({"answer": "", "source": "superseded"})
        _BY_SESSION[(user_prefix, session_id)] = qid
    return qid, fut, float(timeout if timeout is not None else _ASK_TIMEOUT)


def drop_question(qid: str) -> None:
    _PENDING.pop(qid, None)
    for k, v in list(_BY_SESSION.items()):
        if v == qid:
            _BY_SESSION.pop(k, None)


def resolve(qid: str, answer: str, source: str = "resume") -> bool:
    """恢复端点/会话代答共用：解析 Future（幂等——已处理返回 False）。"""
    fut = _PENDING.get(qid)
    if fut is None or fut.done():
        return False
    fut.set_result({"answer": str(answer or ""), "source": source})
    return True


def pending_for_session(user_prefix: str, session_id: str) -> Optional[Dict[str, Any]]:
    """会话当前活跃问题（run_chat 拦截用）；无则 None。"""
    qid = _BY_SESSION.get((user_prefix, session_id))
    if not qid:
        return None
    fut = _PENDING.get(qid)
    if fut is None or fut.done():
        return None
    return {"question_id": qid}


def pending_count() -> int:
    return sum(1 for f in _PENDING.values() if not f.done())


def now() -> float:
    return time.time()
