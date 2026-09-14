# -*- coding: utf-8 -*-
"""专家地基①（2026-09-12 spec R2）单测：批1 卡服务 / 批2 装配与三段键 / 批3 迁移 / 批4 CRUD。

变异锚点：每测 docstring 标明何种生产改动会让它红。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# 批 1：卡实体/服务/种子
# ---------------------------------------------------------------------------

def test_expert_tables_created():
    """kg_expert_profiles + expert_events 两表 create_all 幂等建出（表 84→86）。
    变异锚点：删任一 ORM 类 → 此测红。"""
    from app.models.base import ExpertProfile, ExpertEvent
    assert ExpertProfile.__tablename__ == "kg_expert_profiles"
    assert ExpertEvent.__tablename__ == "expert_events"


def test_default_wenshu_card_equivalence():
    """内置基线逐字段=种子值：tools=活注册表全集（18 实测快照）；system_prompt=_BASE_ROLE 原文。
    变异锚点：卡 tools 少一件/基座被改写 → 此测红（A1/A2 的构造级保险）。"""
    from app.services.expert_config import default_wenshu_card, _mcp_tool_registry
    from app.services.tupu_deepagent import _BASE_ROLE
    card = default_wenshu_card()
    assert card["expert_id"] == "wenshu" and card["name"] == "数据资产探查"
    assert card["entry_kind"] == "chat" and card["enabled"] is True
    assert card["system_prompt"] == _BASE_ROLE                    # 逐字节（含 __CURRENT_DATE__ 占位符原样）
    assert card["skills"] == ["/skills/"] and card["memory"] == ["/memory/AGENTS.md"]
    assert card["knowledge_sources"] == ["ontology_graph"] and card["llm_connection_id"] is None
    assert card["ui_config"]["placeholder"] == "想问什么数据？"
    assert card["ui_config"]["suggestions"] == ["统计用电客户总数", "什么是变压器",
                                                 "配电变压器有哪些？列出编号和名称", "用电客户数据的来源"]
    assert card["ui_config"]["welcome"]["title"] == "数据资产探查"
    assert card["ui_config"]["welcome"]["tagline"] == "一句话问数 · 受控执行 · 全程可审计"
    reg = _mcp_tool_registry()
    assert len(reg) == 18 and set(reg) == set(card["tools"])      # 活注册表派生，数字仅快照断言


def test_get_card_fail_safe_wenshu(monkeypatch):
    """卡读取失败：wenshu 兜底内置基线+source 标记；其他专家抛错不降级（spec §十）。
    变异锚点：兜底换成任意专家/其他专家降级 wenshu → 红。"""
    from app.services import expert_config as ec
    def _boom(force=False):
        raise RuntimeError("db down")
    monkeypatch.setattr(ec, "_load_rows", _boom)
    card, source = ec.get_card("wenshu", with_source=True)
    assert source == "builtin_baseline" and card["expert_id"] == "wenshu"
    with pytest.raises(Exception):
        ec.get_card("nonexistent_expert", with_source=True)      # 不可用如实上屏


def test_chat_request_expert_id_default():
    """ChatRequest.expert_id 默认 wenshu——存量请求/测试/e2e 零改动（spec §五请求链）。"""
    from app.api.data_intelligence import ChatRequest
    req = ChatRequest(user_input="x")
    assert req.expert_id == "wenshu"
