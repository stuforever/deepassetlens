# -*- coding: utf-8 -*-
"""权限重构 T1 单测：权限词汇表 + 工具注册表单点 + 审计表模型。

计划：docs/superpowers/plans/2026-09-24-权限体系重构-实施计划.md 任务 1（v1.4）。
规格：docs/superpowers/specs/2026-09-24-权限体系重构-design.md §5.1 / §6.1。

变异锚点：
- 词汇表缺类型/动作 → 管理页矩阵编辑器少行少列、require_permission 校验漂移
- TOOL_REGISTRY 与 mcp_server 注册集漂移 → fail-closed 下已注册工具对所有人隐身（🛠R1）
- 审计表 decision 无约束 → 脏判定值落库，审计不可对账
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect as sa_inspect

from app.models.auth import AuthAuditLog
from app.services.permission_vocab import (
    EXEC_TOOLS,
    PERMISSION_VOCAB,
    READONLY_TOOLS,
    TOOL_REGISTRY,
    WRITE_TOOLS,
)


def test_vocab_resource_types():
    """词汇表 11 资源类型（design §5.1 原样）；tool 仅 execute（🛠R5 三态语义根基）。"""
    assert len(PERMISSION_VOCAB) == 11
    assert set(PERMISSION_VOCAB) == {
        "skill", "workflow", "data_source", "query_attribute", "query_entity",
        "metric", "expert", "sishu", "auth", "tool", "attachment",
    }
    assert PERMISSION_VOCAB["tool"] == ["execute"]
    # 动作词全部合法小写动单词（顺序按 design 原样，不做排序断言）
    for actions in PERMISSION_VOCAB.values():
        assert len(actions) == len(set(actions))
        assert all(a in {"read", "write", "execute", "delete", "use", "manage", "approval"} for a in actions)


def test_tool_registry_matches_mcp_server():
    """TOOL_REGISTRY 全集 = mcp_server 实际注册集（🛠R1：fail-closed 防已注册工具隐身）。

    W5/T8a 回挂教学 11 件前注册集=19 件；本测试在 T8a 后同步改为 30 件口径。
    """
    from app.mcp_server import mcp

    registered = {t.name for t in asyncio.run(mcp.list_tools())}
    assert TOOL_REGISTRY == registered
    assert len(TOOL_REGISTRY) == 19
    assert "search_kb" in TOOL_REGISTRY          # 🛠R1：不在 GENERIC 但已注册——必须入册
    assert "read_file" not in TOOL_REGISTRY      # 框架工具面外（design §6.1 R14）
    # 三分类划分：READONLY ∪ EXEC == REGISTRY（WRITE 是系统级面外集合，不在注册表）
    assert not (READONLY_TOOLS & EXEC_TOOLS)
    assert READONLY_TOOLS | EXEC_TOOLS == TOOL_REGISTRY
    assert len(READONLY_TOOLS) == 15
    assert len(EXEC_TOOLS) == 4
    assert EXEC_TOOLS == {
        "execute_sql", "execute_api_sql", "execute_entity_api", "execute_doris_sql",
    }


def test_write_tools_align_with_engine_forbidden():
    """WRITE 恒拒 6 件 = query_contract.ABSOLUTE_FORBIDDEN_TOOLS（design §8.4 WRITE=6）。

    同时钉住引擎侧 DATA_TOOLS ⊆ 注册表——v1.4 实施裁定：DATA_TOOLS 语义是引擎
    一致性判定、T8a 后 EXEC(8)≠DATA(4)，故 query_contract 常量原地保留不 import
    vocab（反向才绑权限口径），漂移由本断言把关。
    """
    from app.services.query_contract import ABSOLUTE_FORBIDDEN_TOOLS, DATA_TOOLS

    assert WRITE_TOOLS == ABSOLUTE_FORBIDDEN_TOOLS
    assert len(WRITE_TOOLS) == 6
    assert DATA_TOOLS <= TOOL_REGISTRY
    assert DATA_TOOLS == EXEC_TOOLS  # T1 时点两集合同值；T8a 拆分时改本断言


def test_auth_audit_log_model():
    """审计表 auth_audit_log：decision 三值 CheckConstraint（design §6.1 列清单）。"""
    assert AuthAuditLog.__tablename__ == "auth_audit_log"
    cols = {c.name for c in sa_inspect(AuthAuditLog).columns}
    assert {"id", "ts", "user_sub", "resource_type", "resource_id",
            "action", "decision", "reason", "session_id", "turn_id"} <= cols
    constraints = [c for c in AuthAuditLog.__table_args__] if isinstance(
        AuthAuditLog.__table_args__, tuple) else [AuthAuditLog.__table_args__]
    ck = [c for c in constraints if c.__class__.__name__ == "CheckConstraint"]
    assert any(all(v in str(c.sqltext) for v in ("decision", "allow", "deny", "approval"))
               for c in ck), ck
