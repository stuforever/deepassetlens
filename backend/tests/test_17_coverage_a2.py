# -*- coding: utf-8 -*-
"""批A2 覆盖补全：解析容错链/SQL 构建面/事件持久化（每条带变异锚点）。

覆盖模块：query_entity_utils（LLM JSON 容错链）/ query_attribute_support（SQL 构建）/
run_event_sink（决策门审计持久化，stub DB）。
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ---------------------------------------------------------------------------
# query_entity_utils：LLM JSON 解析容错链（每请求热路径）
# ---------------------------------------------------------------------------

def test_normalize_text_nfkc_and_punct():
    """全角→半角(NFKC)+去空白+去中英标点。变异锚点：L48-50 任一正则删 → 对应残留。"""
    from app.services.query_entity_utils import normalize_text
    assert normalize_text("用电 客户！") == "用电客户"
    assert normalize_text("ＡＢＣ１２３") == "abc123"     # 全角字母数字 NFKC 折叠
    assert normalize_text("客户，名称。编号") == "客户名称编号"
    assert normalize_text(None) == ""


def test_dedupe_keep_order():
    """保序去重+空串剔除。变异锚点：L54-63 seen 集合删 → 重复残留。"""
    from app.services.query_entity_utils import _dedupe_keep_order
    assert _dedupe_keep_order(["b", "a", "b", "", "a", "c"]) == ["b", "a", "c"]


def test_split_alias_text_multi_delimiters():
    """别名串按中英逗号/顿号/斜杠/分号/换行切分。变异锚点：L70 分隔符类删任一 → 该分隔残留。"""
    from app.services.query_entity_utils import _split_alias_text
    assert _split_alias_text("客户,客户名称、用电户/户号；C1\nC2") == ["客户", "客户名称", "用电户", "户号", "C1", "C2"]
    assert _split_alias_text("") == []


def test_strip_markdown_code_fence():
    """```json 围栏剥离+BOM 清理+非围栏原样。变异锚点：L76-78 剥离逻辑删 → 围栏残留。"""
    from app.services.query_entity_utils import _strip_markdown_code_fence
    assert _strip_markdown_code_fence('```json\n{"a":1}\n```') == '{"a":1}'
    assert _strip_markdown_code_fence('```\nplain\n```') == "plain"
    assert _strip_markdown_code_fence('{"a":1}') == '{"a":1}'
    assert _strip_markdown_code_fence('\ufeff{"a":1}') == '{"a":1}'


def test_extract_first_balanced_json_object_nested_and_strings():
    """嵌套平衡截取：字符串内花括号/引号转义不干扰深度计数。
    变异锚点：L87-109 深度计数或 in_string 分支删 → 字符串内 } 提前截断。"""
    from app.services.query_entity_utils import _extract_first_balanced_json_object
    text = '前缀 {"a": {"b": "含}花括号"}, "c": "}"} 后缀'
    got = _extract_first_balanced_json_object(text)
    assert got.startswith('{"a"') and got.endswith('}')
    import json
    assert json.loads(got)["c"] == "}"  # 字符串内的 } 没有截断
    assert _extract_first_balanced_json_object("没有花括号") == "没有花括号"


def test_cleanup_json_candidate_repairs():
    """尾逗号修复+json 前缀剥离。变异锚点：L115 尾逗号正则删 → 修复失效。"""
    from app.services.query_entity_utils import _cleanup_json_candidate
    assert _cleanup_json_candidate('{"a": 1,}') == '{"a": 1}'
    assert _cleanup_json_candidate('json{"a": 1}') == '{"a": 1}'


def test_parse_llm_json_payload_success_paths():
    """四条候选链依次兜底：原文/剥围栏/平衡截取/修复——干净与脏输入都解析成功。
    变异锚点：L134-138 任一 _push 删 → 对应脏输入形态解析失败。"""
    from app.services.query_entity_utils import _parse_llm_json_payload
    # 干净
    got, _, err = _parse_llm_json_payload('{"k": 1}')
    assert got == {"k": 1} and err is None
    # 围栏+噪音+尾逗号
    got2, _, err2 = _parse_llm_json_payload('```json\n前置 {"k": 2,}\n```\n')
    assert got2 == {"k": 2} and err2 is None


def test_parse_llm_json_payload_failure_reason():
    """全候选失败 → (None, 最后候选, reason 前缀 llm_parse_failed)。
    变异锚点：L151 reason 拼装改 → 下游错误分类失效。"""
    from app.services.query_entity_utils import _parse_llm_json_payload
    got, last, reason = _parse_llm_json_payload("这不是 json")
    assert got is None and reason.startswith("llm_parse_failed")


def test_parse_llm_json_payload_empty_with_factory():
    """空输入走 empty_result_factory。变异锚点：L122-123 分支删 → 返回 {} 而非工厂产物。"""
    from app.services.query_entity_utils import _parse_llm_json_payload
    got, raw, reason = _parse_llm_json_payload("", empty_result_factory=lambda: {"rows": [], "empty": True})
    assert got == {"rows": [], "empty": True} and reason is None


# ---------------------------------------------------------------------------
# query_attribute_support：SQL 标识符与蓝图构建
# ---------------------------------------------------------------------------

def test_quote_sql_identifier_escapes_backtick():
    """反引号包裹+内部反引号双写转义（SQL 注入面）。变异锚点：L227 replace 删 → 恶意标识符逃逸。"""
    from app.services.query_attribute_support import _quote_sql_identifier
    assert _quote_sql_identifier("table1") == "`table1`"
    assert _quote_sql_identifier("we`ird") == "`we``ird`"
    assert _quote_sql_identifier("") == ""
    assert _quote_sql_identifier(None) == ""


def test_build_sql_text_guards_and_shape():
    """sql_ready=False/缺 anchor/缺字段 → 空串；正常 → SELECT..AS..FROM..分号结尾。
    变异锚点：L231-237 守卫删 → 非法蓝图出残缺 SQL。"""
    from app.services.query_attribute_support import _build_sql_text
    assert _build_sql_text({"sql_ready": False}) == ""
    assert _build_sql_text({"sql_ready": True, "select_fields": []}) == ""
    # 字段行无任何字段名 → 全 continue → select_lines 空 → 空串
    assert _build_sql_text({"sql_ready": True, "anchor_entity": "t", "select_fields": [{}]}) == ""
    # field_cn 缺失时 alias 回退 field_en（合法产出）
    sql0 = _build_sql_text({"sql_ready": True, "anchor_entity": "t",
                            "select_fields": [{"field_en": "f"}]})
    assert "`t`.`f` AS `f`" in sql0
    sql = _build_sql_text({
        "sql_ready": True, "anchor_entity": "客户",
        "select_fields": [{"entity_name": "客户", "field_en": "cust_no", "field_cn": "客户编号"}],
        "join_relations": [],
    })
    assert sql.startswith("SELECT") and sql.endswith(";")
    assert "`客户`.`cust_no` AS `客户编号`" in sql
    assert "FROM `客户`" in sql


def test_build_sql_text_join_dedup_and_order():
    """重复 JOIN 按三元组去重保序。变异锚点：L258-268 seen_joins 删 → 重复 JOIN。"""
    from app.services.query_attribute_support import _build_sql_text
    rel = {"source_entity_name": "a", "target_entity_name": "b", "join_expr": "a.id = b.aid"}
    sql = _build_sql_text({
        "sql_ready": True, "anchor_entity": "a",
        "select_fields": [{"field_en": "x"}],
        "join_relations": [rel, dict(rel), {"target_entity_name": "c"}],
    })
    assert sql.count("LEFT JOIN") == 2
    assert "LEFT JOIN `b`\n  ON a.id = b.aid" in sql
    assert "LEFT JOIN `c`;" in sql  # 无 join_expr 不带 ON；末段补分号


def test_build_sql_blueprint_anchor_fallback_chain():
    """anchor 选取：主表 → 首个 master → activity 回退。
    变异锚点：L282-295 回退链任一级删 → 对应场景 anchor 为 None。"""
    from app.services.query_attribute_support import _build_sql_blueprint
    base = {"resolved_attributes": [], "requested_attributes": []}
    # 主表优先
    r1 = _build_sql_blueprint({**base, "master_entities": [
        {"entity_name": "m2"}, {"entity_name": "m1", "is_main_table": True}]}, {})
    assert r1["anchor_entity"] == "m1"
    # 无主表回退首个 master
    r2 = _build_sql_blueprint({**base, "master_entities": [{"entity_name": "m2"}]}, {})
    assert r2["anchor_entity"] == "m2"
    # master 空 → activity 兜底
    r3 = _build_sql_blueprint({**base, "activity_entities": [{"entity_name": "act"}]}, {})
    assert r3["anchor_entity"] == "act"


def test_build_sql_blueprint_unresolved_computation():
    """unresolved = requested - resolved（按 normalized/raw 名对账）。
    变异锚点：L335-342 集合差计算改 → 未解析属性误报/漏报。"""
    from app.services.query_attribute_support import _build_sql_blueprint
    final = {
        "master_entities": [{"entity_name": "m", "is_main_table": True}],
        "resolved_attributes": [{"entity_name": "m", "field_cn": "编号", "normalized_name": "编号"}],
        "requested_attributes": [
            {"normalized_name": "编号", "raw_name": "编号"},
            {"raw_name": "电话"},
        ],
    }
    bp = _build_sql_blueprint(final, {})
    assert [u.get("raw_name") for u in bp["unresolved_attributes"]] == ["电话"]
    assert bp["select_fields"][0]["field_cn"] == "编号"


# ---------------------------------------------------------------------------
# run_event_sink：flag 门控+容错铁律（stub DB）
# ---------------------------------------------------------------------------

class _StubDB:
    def __init__(self):
        self.committed = 0
        self.added = []
        self.fail_on_add = False

    def add(self, obj):
        if self.fail_on_add:
            raise RuntimeError("db down")
        self.added.append(obj)

    def commit(self):
        self.committed += 1

    def refresh(self, obj):
        pass

    def rollback(self):
        pass

    def close(self):
        self.closed = True


class _StubRun:
    def __init__(self, **kw):
        self.__dict__.update(kw)
        self.id = "run-1"
        self.status = "running"


class _StubEvent:
    def __init__(self, **kw):
        self.__dict__.update(kw)


@pytest.fixture()
def sink_env(monkeypatch):
    import app.services.run_event_sink as res
    stub_db = _StubDB()
    created_runs = []
    monkeypatch.setattr(res, "SessionLocal", lambda: stub_db)
    monkeypatch.setattr(res, "AgentRun", lambda **kw: (created_runs.append(kw) or _StubRun(**kw)))
    monkeypatch.setattr(res, "RunEvent", lambda **kw: _StubEvent(**kw))
    return res, stub_db, created_runs


def test_sink_flag_off_all_noop(monkeypatch):
    """闸门关 → 全方法 no-op 不炸（flag-gated）。变异锚点：L54 判定删 → 关门时误建 run。"""
    import app.services.run_event_sink as res
    monkeypatch.setattr(res, "_DECISION_GATE_ENABLED", False)
    s = res.RunEventSink("q")
    s.append("tool.started", {})
    s.complete({})
    s.fail("x")
    s.close()
    assert s.run_id is None


def test_sink_lifecycle_orders_and_status(sink_env, monkeypatch):
    """正常流：init 建 run+run.started → append 事件 order 递增 → complete 置 completed。
    变异锚点：L143 event_order=self._order 改常量 → 审计序破坏；L102 status 赋值删 → 状态卡 running。"""
    res, stub_db, created = sink_env
    monkeypatch.setattr(res, "_DECISION_GATE_ENABLED", True)
    s = res.RunEventSink("查客户")
    assert s.run_id == "run-1" and created[0]["scene_code"] == "free_plan"
    s.append("tool.started", {"t": 1}, step_id="1")
    s.append("tool.completed", {"t": 1}, step_id="1")
    events = [a for a in stub_db.added if isinstance(a, _StubEvent)]
    assert [e.event_order for e in events] == [1, 2, 3]  # run.started=1，append 递增
    assert events[0].event_type == "run.started"
    s.complete({"final_answer": "ok"})
    assert s._run.status == "completed"
    s.close()


def test_sink_append_failure_disables_persistently(sink_env, monkeypatch):
    """一次 append 失败 → 停用后续持久化（不刷日志不重试），close 仍安全。
    变异锚点：L94 self._active=False 删 → 长流式反复报错。"""
    res, stub_db, _ = sink_env
    monkeypatch.setattr(res, "_DECISION_GATE_ENABLED", True)
    s = res.RunEventSink("q")
    stub_db.fail_on_add = True
    s.append("tool.started", {})   # 失败 → 停用
    before = stub_db.committed
    s.append("tool.completed", {})  # no-op
    assert stub_db.committed == before and not s._active


def test_sink_init_failure_never_raises(sink_env, monkeypatch):
    """init DB 崩 → 不抛+未激活（容错铁律：绝不影响流式主流程）。
    变异锚点：L74-77 try/except 删 → 异常外泄炸掉 SSE。"""
    res, stub_db, _ = sink_env
    monkeypatch.setattr(res, "_DECISION_GATE_ENABLED", True)

    def boom():
        raise RuntimeError("no db")
    monkeypatch.setattr(res, "SessionLocal", boom)
    s = res.RunEventSink("q")
    assert s._active is False and s.run_id is None
    s.complete({}); s.fail("x"); s.close()  # 全 no-op 不炸
