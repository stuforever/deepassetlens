# -*- coding: utf-8 -*-
"""记忆插槽②（2026-09-12 spec）单测：批1 槽模型 / 批2 树与搬迁 / 批3 L1+f因子 / 批4 越界 / 批5 consolidator。

变异锚点：每测 docstring 标明何种生产改动会让它红。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402


# ---------------------------------------------------------------------------
# 批 1：槽类型注册表+形状兼容+五规则（D3 素材）
# ---------------------------------------------------------------------------

def test_slot_type_registry_four_kinds():
    """四张接线卡（spec §四注册表）。变异锚点：删任一类型 → 红。"""
    from app.services.memory_slots import SLOT_TYPE_REGISTRY
    assert set(SLOT_TYPE_REGISTRY) == {"L1_TRACE", "L2_SUMMARY", "L3_PROFILE", "RAW_MD"}


def test_normalize_memory_field_compat():
    """形状兼容读（spec §四）：①期列表→{slots:[], legacy_paths}；对象直通；非法形状抛错。
    wenshu 卡（①种子的列表形状）读出即归一——升级窗口两形状并存。"""
    from app.services.memory_slots import normalize_memory_field
    assert normalize_memory_field(["/memory/AGENTS.md"]) == \
        {"slots": [], "legacy_paths": ["/memory/AGENTS.md"]}
    assert normalize_memory_field({"slots": [], "legacy_paths": ["/memory/AGENTS.md"]}) == \
        {"slots": [], "legacy_paths": ["/memory/AGENTS.md"]}
    assert normalize_memory_field(None) == {"slots": [], "legacy_paths": []}
    with pytest.raises(ValueError):
        normalize_memory_field("bad")


def test_validate_slots_five_rules():
    """五规则（spec §四，D3 验收依据）：正例过+五类反例各拒。"""
    from app.services.memory_slots import validate_slots
    ok = [
        {"slot": "对话轨迹", "type": "L1_TRACE", "surface": "chat", "read": "不注入"},
        {"slot": "会话摘要", "type": "L2_SUMMARY", "surface": "chat", "read": "注入", "order": 2},
        {"slot": "用户画像", "type": "L3_PROFILE", "slot_key": "profile", "read": "注入", "order": 3},
        {"slot": "偏好", "type": "RAW_MD", "path": "/memory/偏好.md",
         "writer": "agent_edit", "read": "注入", "order": 4},
    ]
    assert validate_slots(ok)["injected"] == \
        ["/memory/L2/chat.md", "/memory/L3/profile.md", "/memory/偏好.md"]  # 规范路径+order
    with pytest.raises(ValueError, match="槽类型不在注册表"):
        validate_slots([{"slot": "x", "type": "L4_MAGIC", "surface": "chat"}])
    with pytest.raises(ValueError, match="重复"):
        validate_slots([{"slot": "x", "type": "L1_TRACE", "surface": "a"},
                        {"slot": "x", "type": "L1_TRACE", "surface": "b"}])
    with pytest.raises(ValueError, match="consolidator"):
        validate_slots(ok, consolidator_on=False)            # 规则2：L2/L3 需服务开
    with pytest.raises(ValueError, match="AGENTS.md"):
        validate_slots([{"slot": "手", "type": "RAW_MD", "path": "/memory/AGENTS.md",
                         "writer": "agent_edit", "read": "不注入"}])   # 规则3：不得为手册
    with pytest.raises(ValueError, match="surface"):
        validate_slots([{"slot": "x", "type": "L1_TRACE", "surface": "不良 Surface!"}])  # 规则5


def test_injection_list_order():
    """注入列表：legacy 手册优先+槽按 order（spec §四规则4）。"""
    from app.services.memory_slots import injection_list
    mem = {"slots": [
        {"slot": "偏好", "type": "RAW_MD", "path": "/memory/偏好.md", "writer": "agent_edit", "read": "注入", "order": 4},
        {"slot": "会话摘要", "type": "L2_SUMMARY", "surface": "chat", "read": "注入", "order": 2}],
        "legacy_paths": ["/memory/AGENTS.md"]}
    assert injection_list(mem) == \
        ["/memory/AGENTS.md", "/memory/L2/chat.md", "/memory/偏好.md"]  # L2 走规范路径
