# -*- coding: utf-8 -*-
"""批A1 覆盖补全：核心规则件行为测试（TDD 补测纪律——每条带变异锚点）。

覆盖模块：subagent_specs / prompt_templates / sql_rewrite_service / engine_health / skill_templates
纪律：断言真实行为不断言实现；每条测试注释标明「变异锚点」——什么生产代码改动会让它失败。
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# subagent_specs.build_subagent_specs —— 四护栏（13-Q/13-Z）
# ---------------------------------------------------------------------------

class _FakeTool:
    def __init__(self, name):
        self.name = name


def _policy(enabled=True, specs=None, max_concurrent=2):
    return {"enabled": enabled, "params": {"specs": specs or [], "max_concurrent": max_concurrent}}


@pytest.fixture()
def fake_registry(monkeypatch):
    """monkeypatch capability_config：registry 返回固定集合，record_event 收集事件。"""
    import app.services.capability_config as cc
    events = []
    monkeypatch.setattr(cc, "_global_tool_registry", lambda: {"search_entities", "execute_doris_sql"})
    monkeypatch.setattr(cc, "record_event", lambda cap, kind, **kw: events.append((cap, kind, kw)))
    return events


def test_specs_disabled_returns_none(fake_registry):
    """变异锚点：删 L35 enabled 判定 → 关闭时不再返回 None。"""
    from app.services.subagent_specs import build_subagent_specs
    assert build_subagent_specs({"enabled": False, "params": {}}, model="m") is None
    assert build_subagent_specs({}, model="m") is None
    assert build_subagent_specs(None, model="m") is None


def test_specs_empty_tool_overlap_rejected_with_event(fake_registry):
    """护栏3：规格工具与全局注册表交集为空 → 拒装配 + spec_invalid 事件。
    变异锚点：删 L54-61 空交集分支 → spec 混入 out。"""
    from app.services.subagent_specs import build_subagent_specs
    pol = _policy(specs=[{"name": "s1", "tools": ["nonexistent_tool"]}], max_concurrent=1)
    out = build_subagent_specs(pol, model="m")
    assert out is None  # 唯一规格被拒 → 全 None
    assert any(k == "spec_invalid" for _, k, _ in fake_registry)


def test_specs_name_level_listing_without_parent_tools(fake_registry):
    """parent_tools=None：名字级清单（探针/校验用），交集内工具保留。
    变异锚点：L82 改为 spec["tools"] = tools（全集而非交集）→ 非注册工具混入。"""
    from app.services.subagent_specs import build_subagent_specs
    pol = _policy(specs=[{"name": "s1", "tools": ["search_entities", "ghost"], "description": "d",
                          "prompt": "p"}], max_concurrent=1)
    out = build_subagent_specs(pol, model="m")
    assert out and len(out) == 1
    assert out[0]["tools"] == ["search_entities"]  # ghost 被交集窄化掉
    assert out[0]["model"] == "m"
    assert "middleware" not in out[0]  # 未传守卫则不带 middleware 键


def test_specs_real_tool_mapping_and_parent_narrowing(fake_registry):
    """parent_tools 给定：映射真实 BaseTool 对象；交集工具不在父工具面 → 拒装配+事件。
    变异锚点：删 L73-79 父工具面校验 → real 含缺失映射时 KeyError 或混入。"""
    from app.services.subagent_specs import build_subagent_specs
    parent = [_FakeTool("search_entities")]
    pol = _policy(specs=[{"name": "ok", "tools": ["search_entities"]},
                         {"name": "bad", "tools": ["execute_doris_sql"]}], max_concurrent=1)
    out = build_subagent_specs(pol, model="m", parent_tools=parent)
    # ok 规格通过；bad（execute_doris_sql 在注册表但不在父工具面）被拒
    assert len(out) == 1 and out[0]["name"] == "ok"
    assert out[0]["tools"] == [parent[0]]  # 真实对象非字符串
    assert any(k == "spec_invalid" and "父代理工具面" in (kw.get("detail") or {}).get("reason", "")
               for _, k, kw in fake_registry)


def test_specs_guard_middlewares_explicitly_carried(fake_registry):
    """护栏2：guard_middlewares 显式进 spec["middleware"]（子代理继承守卫链）。
    变异锚点：删 L83-85 → middleware 键缺失，子代理脱离守卫链。"""
    from app.services.subagent_specs import build_subagent_specs
    guard = object()
    pol = _policy(specs=[{"name": "s1", "tools": ["search_entities"]}], max_concurrent=1)
    out = build_subagent_specs(pol, model="m", guard_middlewares=[guard])
    assert out[0]["middleware"] == [guard]


def test_specs_max_concurrent_appended_to_prompt(fake_registry):
    """max_concurrent>1：system_prompt 追加并发约束行；=1 不追加。
    变异锚点：删 L63-64 → 并发约束文案消失。"""
    from app.services.subagent_specs import build_subagent_specs
    pol = _policy(specs=[{"name": "s1", "tools": ["search_entities"], "prompt": "P"}], max_concurrent=3)
    out = build_subagent_specs(pol, model="m")
    assert "最多 3 个委派并行" in out[0]["system_prompt"]
    pol1 = _policy(specs=[{"name": "s2", "tools": ["search_entities"], "prompt": "P"}], max_concurrent=1)
    out1 = build_subagent_specs(pol1, model="m")
    assert out1[0]["system_prompt"] == "P"


# ---------------------------------------------------------------------------
# prompt_templates.BOSS_ROUTER_PROMPT
# ---------------------------------------------------------------------------

def test_boss_router_prompt_renders_with_variables():
    """模板可渲染：secretary_state/user_query 双变量注入。
    变异锚点：任一变量名改写 → format_messages 抛 KeyError。"""
    from app.services.prompt_templates import BOSS_ROUTER_PROMPT
    msgs = BOSS_ROUTER_PROMPT.format_messages(secretary_state="S-STATE", user_query="查客户")
    assert len(msgs) == 2
    assert msgs[0].type == "system" and msgs[1].type == "human"
    assert "S-STATE" in msgs[1].content and "查客户" in msgs[1].content


def test_boss_router_prompt_system_contract_sections():
    """system 消息承载路由契约：两类意图/8 合法任务/JSON 输出格式段在位。
    变异锚点：删任一契约段 → 对应断言失败（提示词层协议有测试锚定）。"""
    from app.services.prompt_templates import BOSS_ROUTER_PROMPT
    sys_text = BOSS_ROUTER_PROMPT.format_messages(secretary_state="x", user_query="y")[0].content
    for token in ("intent_type", "location", "exploration", "实体定位", "SQL 拼装", "SQL 执行",
                  "兜底", "locked_hint", "vector_store_hint"):
        assert token in sys_text, f"缺少契约段: {token}"


def test_boss_router_prompt_brace_escaping():
    """JSON 示例的花括号双写转义正确：渲染后示例形如 {"intent_type":"location",...} 而非被 format 吞掉。
    变异锚点：模板里 {{}} 误改 {} → format_messages 抛 KeyError/IndexError。"""
    from app.services.prompt_templates import BOSS_ROUTER_PROMPT
    sys_text = BOSS_ROUTER_PROMPT.format_messages(secretary_state="x", user_query="y")[0].content
    assert '{"intent_type":"location"' in sys_text      # 示例行（无空格形态）
    assert '"intent_type": "location 或 exploration"' in sys_text  # 格式说明段（多行花括号展开后）
    assert '{{' not in sys_text  # 渲染后不应残留双花括号


# ---------------------------------------------------------------------------
# sql_rewrite_service._parse_json_response
# ---------------------------------------------------------------------------

def test_parse_json_bare():
    """裸 JSON 直解。变异锚点：函数体改空 → 返回非 dict。"""
    from app.services.sql_rewrite_service import _parse_json_response
    assert _parse_json_response('{"a": 1}') == {"a": 1}


def test_parse_json_markdown_wrapped():
    """```json 包裹剥离。变异锚点：正则 r"```(?:json)?\\s*(.*?)```" 被改 → 包裹剥离失败。"""
    from app.services.sql_rewrite_service import _parse_json_response
    raw = '说明文字\n```json\n{"matched": true}\n```\n尾注'
    assert _parse_json_response(raw) == {"matched": True}


def test_parse_json_noise_extraction():
    """无代码块但有前后噪音：截取首个 { 到末个 }。
    变异锚点：L62-64 截取逻辑删 → json.loads 崩。"""
    from app.services.sql_rewrite_service import _parse_json_response
    raw = '好的，结果如下：{"rewritten_sql": "SELECT 1", "matched": false} 以上供参考'
    assert _parse_json_response(raw)["matched"] is False


def test_parse_json_invalid_raises():
    """非法 JSON 透传 json.JSONDecodeError（调用方负责容错）。"""
    from app.services.sql_rewrite_service import _parse_json_response
    with pytest.raises(Exception):
        _parse_json_response("完全不是 JSON")


# ---------------------------------------------------------------------------
# engine_health（缓存行为，探针 monkeypatch 不触真库）
# ---------------------------------------------------------------------------

@pytest.fixture()
def health_probe_env(monkeypatch):
    """替换三引擎探针为可控桩，清空缓存。"""
    import app.services.engine_health as eh
    calls = {"n": 0}

    def fake_probe():
        calls["n"] += 1
        if calls.get("fail"):
            raise RuntimeError("boom-conn")
    monkeypatch.setattr(eh, "_PROBES", {"doris": fake_probe, "duckdb": fake_probe, "pg": fake_probe})
    eh.invalidate()
    return eh, calls


def test_health_probe_unknown_engine(health_probe_env):
    """未知引擎 → status=unknown。变异锚点：L58-60 未知分支删 → KeyError。"""
    eh, _ = health_probe_env
    r = eh.probe("no-such")
    assert r["status"] == "unknown" and r["error"] == "未知引擎"


def test_health_probe_caches_within_ttl(health_probe_env):
    """TTL 内二调命中缓存（探针不重调）。变异锚点：删 L55 缓存命中分支 → calls.n==2。"""
    eh, calls = health_probe_env
    a = eh.probe("doris")
    b = eh.probe("doris")
    assert a["status"] == "ok" and b["status"] == "ok"
    assert calls["n"] == 1


def test_health_probe_force_reprobes(health_probe_env):
    """force=True 强制重测。变异锚点：L55 force 判定删 → force 调用也走缓存。"""
    eh, calls = health_probe_env
    eh.probe("doris")
    eh.probe("doris", force=True)
    assert calls["n"] == 2


def test_health_probe_error_captured_and_truncated(health_probe_env):
    """探针异常 → status=error；失败结果也进缓存（TTL 内不重测）。
    变异锚点：L66-68 异常分支删 → 异常外泄；L75-76 缓存写删 → 失败每次重试。"""
    eh, calls = health_probe_env
    calls["fail"] = True
    r = eh.probe("doris", force=True)
    assert r["status"] == "error" and "boom-conn" in r["error"]
    calls["fail"] = False
    # 失败结果在 TTL 内命中缓存（不因 fail 复位而重测——n 不增）
    assert eh.probe("doris")["status"] == "error"
    assert calls["n"] == 1
    # force 重测 → 成功
    assert eh.probe("doris", force=True)["status"] == "ok"
    assert calls["n"] == 2


def test_health_invalidate_scoped_and_all(health_probe_env):
    """invalidate(engine) 单清；invalidate() 全清。变异锚点：L91-95 分支删 → 清理失效。"""
    eh, calls = health_probe_env
    eh.probe("doris")
    eh.probe("pg")
    assert calls["n"] == 2
    eh.invalidate("doris")
    eh.probe("doris")
    assert calls["n"] == 3
    eh.probe("pg")  # pg 仍在缓存
    assert calls["n"] == 3
    eh.invalidate()
    eh.probe("pg")
    assert calls["n"] == 4


def test_health_snapshot_three_engines(health_probe_env):
    """snapshot 并行探测三引擎，键齐全。变异锚点：keys 元组改 → 键缺失。"""
    eh, _ = health_probe_env
    snap = eh.snapshot()
    assert set(snap.keys()) == {"doris", "duckdb", "pg"}
    assert all(v["status"] == "ok" for v in snap.values())


# ---------------------------------------------------------------------------
# skill_templates
# ---------------------------------------------------------------------------

def test_templates_list_nonempty_with_contract_fields():
    """模板清单非空且每条含 id/name/description/skill_type/content 契约字段。
    变异锚点：SKILL_TEMPLATES 条目缺字段 → 下游 apply_template KeyError 前置暴露。"""
    from app.services.skill_templates import list_templates
    tpls = list_templates()
    assert tpls
    for t in tpls:
        for k in ("id", "name", "description", "skill_type", "content"):
            assert k in t, f"模板 {t.get('id')} 缺 {k}"


def test_get_template_hit_and_miss():
    """命中返回条目；未命中 None。变异锚点：L168-171 匹配逻辑改 → 语义破坏。"""
    from app.services.skill_templates import get_template, list_templates
    first = list_templates()[0]
    assert get_template(first["id"])["id"] == first["id"]
    assert get_template("no-such-tpl") is None


def test_apply_template_structure_and_overrides():
    """apply_template：产出 create_skill 可用结构+overrides 覆盖生效+不存在抛 ValueError。
    变异锚点：L191-192 overrides.update 删 → 覆盖不生效；L181 raise 删 → None 解引用。"""
    from app.services.skill_templates import apply_template, list_templates
    tid = list_templates()[0]["id"]
    data = apply_template(tid, overrides={"name": "自定义名"})
    assert data["name"] == "自定义名"
    assert data["skill_type"] and data["content"]
    assert "input_schema" in data and "output_schema" in data
    with pytest.raises(ValueError):
        apply_template("no-such-tpl")
