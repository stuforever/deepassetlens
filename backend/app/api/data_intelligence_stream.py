# -*- coding: utf-8 -*-
"""data_intelligence_stream.py - freeplan 流路由挂载（批13-D Step3 瘦身后）

编排器主体已迁 freeplan/endpoint.py（Step3：endpoint 瘦身 + translator 状态机封装 +
session 会话锁迁入，行为零变化/SSE 字节一致）。本文件仅保留：
- 路由挂载（URL 不变：POST /api/data-intelligence/chat/freeplan/stream 与 /resume，
  prefix=/api/data-intelligence 保持与拆分前一致）
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data-intelligence", tags=["data-intelligence"])

# Step3：主函数与 HITL 端点从 freeplan.endpoint 迁入（字节原样），此处仅挂载路由
from .freeplan.endpoint import (  # noqa: E402,F401
    chat_freeplan_stream, resume_hitl, HITLResumeRequest,
)

router.post("/chat/freeplan/stream")(chat_freeplan_stream)
router.post("/chat/freeplan/resume")(resume_hitl)
