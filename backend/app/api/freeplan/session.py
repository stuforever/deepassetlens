# -*- coding: utf-8 -*-
"""freeplan/session.py - 会话锁与 KG 工具标签（批13-D Step3：从 data_intelligence_support 迁入）

- _get_session_lock：同 thread_id 会话执行锁（防 checkpoint 分叉覆盖），P3 超阈值回收
- _KG_ACTION_LABELS：KG 工具中文名映射（think 流 task_label 前端展示用）

行为零变化：data_intelligence_support 保留同名转发 import，旧引用零改动。
"""
from __future__ import annotations

import asyncio
from typing import Dict

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

# v3.5 同一会话执行锁：防止同 thread_id 并发请求导致 checkpoint 分叉覆盖
# 不同会话可并发（各自持不同锁），同一会话串行
_SESSION_LOCKS: dict[str, "asyncio.Lock"] = {}
_SESSION_LOCK_MAX = 200  # P3: 防无界增长，超阈值清理已解锁的旧锁


def _get_session_lock(thread_id: str):
    """获取或创建会话级异步锁（P3: 超阈值时回收无锁定的旧锁）"""
    if thread_id not in _SESSION_LOCKS:
        # 回收：超过上限时清理已解锁的旧锁（locked()=False 表示无人在用）
        if len(_SESSION_LOCKS) > _SESSION_LOCK_MAX:
            _stale = [k for k, v in _SESSION_LOCKS.items() if not v.locked() and k != thread_id]
            for k in _stale[:len(_SESSION_LOCKS) - _SESSION_LOCK_MAX // 2]:
                del _SESSION_LOCKS[k]
        _SESSION_LOCKS[thread_id] = asyncio.Lock()
    return _SESSION_LOCKS[thread_id]
