"""M2 测试（图谱问数融合设计 §4.2 G3 / §4.4 DA-3）。

覆盖：
  1. G3 sample_column_values（MCP 第 17 工具）：
     - 已注册进 FastMCP（mcp.list_tools() 单一事实源）
     - generic 白名单 GENERIC_ALLOWED_TOOLS 与全局名册 GLOBAL_TOOL_REGISTRY 同步
     - handler 参数守卫：缺参 / 非法列名（SQL 注入防护）被拒
  2. DA-3 常驻纪律 AGENTS.md：
     - 文件存在且包含关键纪律关键词
     - create_tupu_agent 装配了 memory=["/memory/AGENTS.md"]（MemoryMiddleware 框架自动装配）

运行方式：
    cd backend && python -m pytest tests/test_m2_accuracy.py -v
"""
from pathlib import Path

import pytest


class TestG3SampleColumnValues:
    def test_白名单包含取样工具(self):
        """G3: generic 白名单 + 全局名册必须含 sample_column_values（防幽灵/缺失）。"""
        from app.services.query_contract import GENERIC_ALLOWED_TOOLS
        from app.services.skill_catalog import GLOBAL_TOOL_REGISTRY

        assert "sample_column_values" in GENERIC_ALLOWED_TOOLS
        assert "sample_column_values" in GLOBAL_TOOL_REGISTRY

    @pytest.mark.asyncio
    async def test_mcp已注册第17工具(self):
        """G3: FastMCP 实注册工具集必须含 sample_column_values（单一事实源）。"""
        from app.mcp_server import mcp

        tools = await mcp.list_tools()
        names = {t.name for t in tools}
        assert "sample_column_values" in names
        assert len(names) >= 17

    def test_缺参被拒(self):
        """G3: 缺 entity_code/column 时 handler 拒绝（不触库）。"""
        from app.services.kg_action_handlers import _kg_sample_column_values

        assert "error" in _kg_sample_column_values({}, "12:00:00")
        assert "error" in _kg_sample_column_values({"entity_code": "x"}, "12:00:00")
        assert "error" in _kg_sample_column_values({"column": "col"}, "12:00:00")

    def test_非法列名被拒(self):
        """G3: 列名含 SQL 注入载荷 / 中文列名被拒（物理标识符白名单）。"""
        from app.services.kg_action_handlers import _kg_sample_column_values

        for bad in ["1; DROP TABLE a; --", "col) FROM x --", "列中文名", "a b", ""]:
            r = _kg_sample_column_values({"entity_code": "e", "column": bad}, "12:00:00")
            assert "error" in r, f"列名应被拒: {bad!r}"

    def test_limit边界不崩(self):
        """G3: limit 越界被夹取到 [1,200]，不抛异常。"""
        from app.services.kg_action_handlers import _kg_sample_column_values

        for lim in [-5, 0, 99999]:
            r = _kg_sample_column_values({"entity_code": "e", "column": "col", "limit": lim}, "12:00:00")
            # 参数校验通过后才会进实体解析；limit 越界不应抛异常（实体不存在属于业务错误而非崩溃）
            assert isinstance(r, dict)


class TestDA3Memory:
    def test_agents_md存在且含纪律(self):
        """DA-3: data/memory/AGENTS.md 存在，包含关键纪律（取样/搜索确认/数字真实）。"""
        p = Path(__file__).resolve().parent.parent / "data" / "memory" / "AGENTS.md"
        assert p.is_file(), "AGENTS.md 不存在"
        text = p.read_text(encoding="utf-8")
        for kw in ["sample_column_values", "search_entities", "禁止编造", "先结论后过程"]:
            assert kw in text, f"AGENTS.md 缺关键词: {kw}"

    def test_agent装配memory源(self):
        """DA-3: create_tupu_agent 源码装配 memory 纪律源（MemoryMiddleware 框架自动追加）。
        2026-09-12 专家地基① 锚点适配：装配改按卡，默认值移至 default_wenshu_card()。
        2026-09-12 记忆插槽② 批1 锚点适配：memory 归一形状后消费点切 _mem_inject_list 收口
        （legacy 优先+槽按 order；wenshu slots=[] → legacy 列表=等值）——意图不变。"""
        import app.services.tupu_deepagent as mod
        import app.services.expert_config as _ec

        src = Path(mod.__file__).read_text(encoding="utf-8")
        assert 'memory=_mem_inject_list(card or {}) if _on("memory") else None' in src
        assert _ec.default_wenshu_card()["memory"] == ["/memory/AGENTS.md"]  # wenshu 默认纪律源等值（①形状基线）
