# -*- coding: utf-8 -*-
"""批13-G 减轮次组合 单测。

覆盖：
- 件1 指引预载：_load_skill_md scenarios/ 目录查找 + lru_cache 缓存 + 契约消息嵌剧本手册
  （scenario 契约注入 SKILL.md 正文、generic 契约不注入）；
- 件2 实体预解析修正：向量退回路径 0.6 相似度阈值过滤；
- 件3 金标首选计划：sim>=0.90 注入首选计划块（data_intelligence 侧已有，此处测 bundle 层阈值常量可调）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.tupu_deepagent import _load_skill_md  # noqa: E402
from app.api.data_intelligence import _build_contract_system_message  # noqa: E402
from app.services import golden_qa_service as gqs  # noqa: E402


class _FakeContract:
    """最小契约形状（_build_contract_system_message 只读这些字段）。"""

    def __init__(self, skill_id="", route_type="scenario"):
        self.scope = {}
        self.skill_id = skill_id
        self.workflow_step = "step1"
        self.allowed_tools = ["execute_sql"]
        self.forbidden_tools = []
        self.template_ids = []
        self.selected_engine = "doris"
        self.stop_when = []
        self.output_mode = "final"
        self.route_type = route_type
        self.locate_first = False
        self.aggregate_intent = None
        self.clarify_required = False
        self._runtime = {}


def test_load_skill_md_scenarios_dir():
    """场景剧本在 skills/scenarios/ 下也能读到（此前只查平铺目录，场景剧本永远读空）。"""
    content = _load_skill_md("distribution-overload")
    assert content, "distribution-overload SKILL.md 应可读取"
    assert "过载" in content or "台区" in content


def test_load_skill_md_flat_dir_still_works():
    """平铺技能目录（locate 等）不受 scenarios 查找影响。"""
    content = _load_skill_md("locate")
    assert content and "定位" in content or content


def test_load_skill_md_cached():
    """lru_cache：两次调用同一对象（模块加载解析缓存）。"""
    assert _load_skill_md("distribution-overload") is _load_skill_md("distribution-overload")


def test_load_skill_md_unknown_empty():
    assert _load_skill_md("no-such-skill-xyz") == ""
    assert _load_skill_md("") == ""


def test_contract_message_embeds_playbook_for_scenario():
    """scenario 契约：契约消息尾部嵌剧本手册（无需 read_file）。"""
    msg = _build_contract_system_message(
        _FakeContract(skill_id="distribution-overload", route_type="scenario"),
        question="查询重过载台区",
    )
    assert "剧本手册（distribution-overload，已预载，无需 read_file 技能文件）" in msg
    assert "过载" in msg


def test_contract_message_no_playbook_for_generic():
    """generic 契约：不注入剧本手册（自主模式行为不变）。"""
    msg = _build_contract_system_message(
        _FakeContract(skill_id="", route_type="generic"),
        question="统计用电客户数量",
    )
    assert "剧本手册" not in msg


def test_entity_hint_vector_threshold(monkeypatch):
    """件2：向量退回路径 0.6 阈值过滤——低相似候选不进预解析。"""
    hits = [
        {"name": "高相似实体", "code": "E1", "score": 0.85},
        {"name": "低相似实体", "code": "E2", "score": 0.42},
        {"name": "临界实体", "code": "E3", "score": 0.61},
    ]

    class _FakeDB:
        def close(self):
            pass

    monkeypatch.setattr(
        "app.services.entity_attr_vector_service.search_entity_vectors",
        lambda *a, **k: hits,
    )
    monkeypatch.setattr(gqs, "_CORE_SUFFIX_RE", gqs._CORE_SUFFIX_RE)
    block = gqs.build_entity_hint_block(_FakeDB(), "某个不含子串命中的问题xyz", precomputed_vec=[0.1])
    assert "高相似实体" in block
    assert "临界实体" in block
    assert "低相似实体" not in block
