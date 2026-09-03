# -*- coding: utf-8 -*-
"""批13-AB 摘要官方化回退与站点技能化 单测。

覆盖（按子批追加）：
- AB-1 摘要回退官方工厂：工厂实例与框架自动件同名（同名替换语义根基）、
  SummarizationToolMiddleware 提供 compact_conversation、manifest summarization_mode、
  排除栏条件化（开关开=空集/关=执行器）
"""
import os
from unittest.mock import MagicMock

import pytest

from deepagents.middleware.summarization import (
    create_summarization_middleware,
    SummarizationMiddleware,
    SummarizationToolMiddleware,
)

_SRC_PATH = os.path.join(os.path.dirname(__file__), "..", "app", "services", "tupu_deepagent.py")


def _agent_src() -> str:
    with open(_SRC_PATH, encoding="utf-8") as f:
        return f.read()


def _fake_chat_model():
    """工厂要求 BaseChatModel 实例（TypeError 硬校验）——用 langchain fake 模型。"""
    from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
    from langchain_core.messages import AIMessage
    return GenericFakeChatModel(messages=iter([AIMessage(content="ok")]))


class TestAB1OfficialFactory:
    def test_工厂实例与框架自动件同名(self):
        """同名替换语义根基：工厂件 .name=="SummarizationMiddleware"，
        与框架 graph.py 自动追加的默认件同名 -> 拼接机原地替换（无需排除栏）。"""
        model = _fake_chat_model()
        model.profile = None  # 无 profile -> 固定默认阈值分支
        mw = create_summarization_middleware(model, MagicMock())
        assert mw.name == "SummarizationMiddleware"  # name property 返回公开别名（排除栏按该字符串匹配）
        assert type(mw).__name__ == "_DeepAgentsSummarizationMiddleware"  # SummarizationMiddleware 是其公开别名

    def test_手动压缩件提供compact_conversation(self):
        """SummarizationToolMiddleware(_summ_mw) 提供 compact_conversation 工具（设计 §1.4 探针断言）。"""
        model = _fake_chat_model()
        model.profile = None
        mw = create_summarization_middleware(model, MagicMock())
        tool_mw = SummarizationToolMiddleware(mw)
        tool_names = [getattr(t, "name", "") for t in (getattr(tool_mw, "tools", None) or [])]
        assert "compact_conversation" in tool_names, f"compact_conversation 不在工具清单: {tool_names}"

    def test_装配源码接线(self):
        """tupu_deepagent：官方工厂双件套在位、自研类/观测钩子退役、排除栏条件化。"""
        src = _agent_src()
        assert "create_summarization_middleware(model, backend)" in src
        assert "SummarizationToolMiddleware(_summ_mw)" in src
        assert "class _TupuSummarizationMiddleware" not in src
        assert "_should_summarize" not in src
        assert '_mw_excl = frozenset({"SummarizationMiddleware"}) if not _on("summarization") else frozenset()' in src

    def test_manifest_summarization_mode(self):
        """manifest 记 summarization_mode（official_factory/disabled），探针断言用。"""
        src = _agent_src()
        assert 'manifest_items["summarization_mode"] = "official_factory" if _on("summarization") else "disabled"' in src


class TestAB2PlaceholderToSkill:
    """批13-AB2 占位符站转技能：删 read_file 运行时 ⟦⟧ 翻译站，装配时翻译搬迁 template_guard，
    模型按 AGENTS.md §五纪律主动 search_entities 翻译，漏网 ⟦⟧ SQL 由模板守卫硬拒。"""

    def test_运行时翻译站已删除(self):
        src = _agent_src()
        assert "class SkillEntityResolverMiddleware" not in src
        assert "SkillEntityResolverMiddleware()" not in src
        # 装配时翻译器已搬迁 template_guard（skill_policy/_load_skill_md 继续可用）
        from app.services.template_guard import _resolve_entity_refs  # noqa: F401 搬迁到位可导入
        from app.services import skill_policy  # noqa: F401 import 链健康（内部改从 template_guard 取）

    def test_AGENTS_md占位符纪律在位(self):
        from pathlib import Path
        p = Path(__file__).resolve().parent.parent / "data" / "memory" / "AGENTS.md"
        md = p.read_text(encoding="utf-8")
        assert "五、数据样本纪律（13-AB）" in md
        assert "⟦中文占位符⟧" in md and "search_entities" in md and "严禁出现 ⟦⟧" in md

    def test_守卫拒含占位符SQL(self):
        """探针（设计 §2.3）：含 ⟦x⟧ 的 SQL 走模板守卫必被拒（表不在模板表集合/解析失败）。"""
        from tests._tpl_helpers import relationship_template_sql
        from app.services.template_guard import validate_against_template
        tpl = relationship_template_sql()
        bad = "SELECT count(*) AS cnt FROM ⟦台区表⟧"
        chk = validate_against_template(bad, tpl, "t1")
        assert not chk.ok, "含 ⟦⟧ 占位符的 SQL 必须被模板守卫拒绝"
        bad2 = "SELECT a.cust_no FROM ⟦户变关系⟧ a JOIN dim_cst_elec_cons_cust b ON a.cust_no=b.cust_no"
        chk2 = validate_against_template(bad2, tpl, "t1")
        assert not chk2.ok
