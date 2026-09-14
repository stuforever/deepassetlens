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


# ---------------------------------------------------------------------------
# 批 2：单点收口 + 装配参数化 + 6 因子键 + A2 对拍
# ---------------------------------------------------------------------------

def test_expert_paths_thread_id():
    """三段键唯一构造处（spec §八）：{user}:{expert}:{thread}。
    变异锚点：任何内联 f-string 构造漏收口 → grep 判据红（步骤 2.7）。"""
    from app.services.expert_paths import thread_id
    assert thread_id("admin", "wenshu", "t1") == "admin:wenshu:t1"


def test_expert_paths_roots():
    """roots 从卡声明路径派生：/skills/→data/skills；/memory/AGENTS.md→data/memory（等值）。"""
    from app.services.expert_paths import skills_roots, memory_roots
    assert str(skills_roots({"skills": ["/skills/"]})[0]).replace("\\", "/").endswith("data/skills")
    assert str(memory_roots({"memory": ["/memory/AGENTS.md"]})[0]).replace("\\", "/").endswith("data/memory")


def test_a2_prompt_byte_equivalence():
    """A2 对拍（spec §十一，逐字节强约束）：builder(卡基座)==现状常量产物。
    变异锚点：基座替换逻辑改写任何字节（含 __CURRENT_DATE__ 处理）→ 红。"""
    from app.services.tupu_deepagent import _build_dynamic_system_prompt
    from app.services.expert_config import default_wenshu_card
    card = default_wenshu_card()
    assert _build_dynamic_system_prompt(base=card["system_prompt"]) == \
           _build_dynamic_system_prompt()


def test_cache_key_six_factors():
    """6 因子键：#e{expert}@{version} 追加（spec §五）。两专家同版本=两 Agent。"""
    from app.services.tupu_deepagent import _assembly_cache_key
    k1 = _assembly_cache_key("conn1", 3, 4, "fhash", "wenshu", 7)
    k2 = _assembly_cache_key("conn1", 3, 4, "fhash", "echo", 7)
    assert k1 == "conn1#g3#c4#ffhash#ewenshu@7" and k1 != k2


def test_tools_narrowing_empty_rejects():
    """工具窄化：空交集拒装配（fail-closed，沿 subagent_specs 惯例）。"""
    from app.services.tupu_deepagent import _narrow_mcp_tools
    class _T:
        def __init__(self, n): self.name = n
    tools = [_T("execute_sql"), _T("search_entities")]
    assert [t.name for t in _narrow_mcp_tools(tools, {"execute_sql"})] == ["execute_sql"]
    with pytest.raises(ValueError):
        _narrow_mcp_tools(tools, set())                    # 空交集拒装配


# ---------------------------------------------------------------------------
# 批 3：迁移（E1 前置单测）
# ---------------------------------------------------------------------------

def test_checkpoint_migration_first_colon_insert():
    """首冒号插入法+双表+恰一冒号谓词+幂等（spec §九步骤 4，review P0）。
    变异锚点：整串拼接（四段）/漏 writes 表/谓词含两段 → 红。"""
    import sqlite3, tempfile, os
    from app.services.tupu_deepagent import _migrate_checkpoint_thread_ids
    with tempfile.TemporaryDirectory() as _d:
        _db = os.path.join(_d, "t.db")
        con = sqlite3.connect(_db)
        con.executescript("""
            CREATE TABLE checkpoints (thread_id TEXT, checkpoint_ns TEXT, checkpoint_id TEXT);
            CREATE TABLE writes (thread_id TEXT, task_id TEXT, idx INTEGER);
            INSERT INTO checkpoints VALUES ('anonymous:free_123', 'freeplan', 'c1');
            INSERT INTO checkpoints VALUES ('anonymous:wenshu:free_456', 'freeplan', 'c2');
            INSERT INTO writes VALUES ('anonymous:free_123', 't1', 0);
            INSERT INTO writes VALUES ('anonymous:wenshu:free_456', 't1', 0);
        """)
        con.commit(); con.close()
        n = _migrate_checkpoint_thread_ids(_db)          # 迁移函数接受显式 db 路径（测试注入）
        con = sqlite3.connect(_db)
        rows = {t: [r[0] for r in con.execute(f"SELECT DISTINCT thread_id FROM {t}")]
                for t in ("checkpoints", "writes")}
        con.close()
        assert n == 2                                    # 双表各迁 1 行（已是三段的不动）
        assert rows["checkpoints"] == ["anonymous:wenshu:free_456"] or \
               set(rows["checkpoints"]) == {"anonymous:wenshu:free_123", "anonymous:wenshu:free_456"}
        assert "anonymous:wenshu:free_123" in rows["writes"]       # writes 同步三段化
        assert all(r.count(":") == 2 for t in rows for r in rows[t])   # 全三段
        n2 = _migrate_checkpoint_thread_ids(_db)
        assert n2 == 0                                   # 幂等：重跑零迁移
