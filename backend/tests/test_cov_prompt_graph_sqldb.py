# -*- coding: utf-8 -*-
"""覆盖补全批次1d：prompt_templates 模板渲染 + graph_sync Cypher 构建 + sql_db_helper 降级路径。

characterization 纪律：每个测试注明会让它失败的生产改动。
隔离：graph_sync 只测 @staticmethod（FakeTx 捕获，不建 driver 不碰网络）；
sql_db_helper monkeypatch 模块级单例/依赖。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

from app.services.prompt_templates import BOSS_ROUTER_PROMPT  # noqa: E402
from app.services import graph_sync as gs  # noqa: E402
from app.services import sql_db_helper as sh  # noqa: E402


# ---------------------------------------------------------------------------
# prompt_templates
# ---------------------------------------------------------------------------

def test_boss_router_prompt_renders_two_messages():
    """format_messages 渲染 system+human 两条消息。改动：消息结构被改 -> 失败。"""
    msgs = BOSS_ROUTER_PROMPT.format_messages(secretary_state="S_STATE", user_query="Q_TEXT")
    assert len(msgs) == 2
    assert isinstance(msgs[0], SystemMessage) and isinstance(msgs[1], HumanMessage)
    assert "Q_TEXT" in msgs[1].content and "S_STATE" in msgs[1].content
    assert "严格 JSON" in msgs[1].content


def test_boss_router_prompt_system_content_contract():
    """system 模板：双意图分类 + 8 个合法任务 + JSON 大括号正确转义（{{ -> {）。改动：模板被改坏 -> 失败。"""
    content = BOSS_ROUTER_PROMPT.format_messages(secretary_state="S", user_query="Q")[0].content
    assert "intent_type" in content and "location" in content and "exploration" in content
    for task in ("实体定位", "属性定位", "关系定位", "溯源定位", "SQL 拼装", "SQL 执行", "分类查询", "兜底"):
        assert task in content, f"缺任务: {task}"
    # {{ }} 在 ChatPromptTemplate 里是字面大括号转义：渲染后不应残留 {{
    assert "{{" not in content
    assert '"entity_code":"CUSTOMER"' in content  # locked_hint 示例正确展开


# ---------------------------------------------------------------------------
# graph_sync（只测静态 Cypher 构建，不实例化 driver）
# ---------------------------------------------------------------------------

class _FakeTx:
    def __init__(self):
        self.calls = []

    def run(self, query, **kwargs):
        self.calls.append((query, kwargs))


def test_create_concept_node_cypher():
    """概念节点 MERGE 幂等 + 动态 Level 标签。改动：Level 标签拼接被改 -> 失败。"""
    tx = _FakeTx()
    gs.Neo4jSyncService._create_concept_node(tx, "id1", "客户", 3)
    q, kw = tx.calls[0]
    assert "MERGE (c:Concept {id: $id})" in q
    assert "SET c:Level3" in q
    assert kw == {"id": "id1", "name": "客户", "level": 3}


def test_hierarchy_relation_type_mapping():
    """层级关系名映射：L1->L2 细分 / L2->L3 关联 / L3->L4 细分 / 其余 BELONGS_TO。改动：映射表被改 -> 失败。"""
    cases = [
        (1, 2, "细分"),
        (2, 3, "关联"),
        (3, 4, "细分"),
        (1, 3, "BELONGS_TO"),
        (4, 2, "BELONGS_TO"),
    ]
    for parent_level, child_level, expect in cases:
        tx = _FakeTx()
        gs.Neo4jSyncService._create_hierarchy_relation(tx, "c1", "p1", parent_level, child_level)
        q, kw = tx.calls[0]
        assert f"-[:`{expect}`]->" in q, f"L{parent_level}->L{child_level} 应为 {expect}"
        assert kw == {"child_id": "c1", "parent_id": "p1"}


# ---------------------------------------------------------------------------
# sql_db_helper
# ---------------------------------------------------------------------------

class _FakeDB:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def get_table_info(self, table_names=None):
        self.calls.append(("get_table_info", table_names))
        if self.fail:
            raise RuntimeError("schema boom")
        return "DDL:" + ",".join(table_names or [])

    def get_context(self):
        self.calls.append(("get_context", None))
        return "CTX"

    def run(self, sql):
        self.calls.append(("run", sql))
        if self.fail:
            raise RuntimeError("run boom")
        return "ROWS"


def test_get_sql_database_singleton_fast_path(monkeypatch):
    """单例已存在 -> 直接返回不再碰引擎。改动：单例早退被删 -> 失败。"""
    sentinel = object()
    monkeypatch.setattr(sh, "_sql_db", sentinel)
    assert sh.get_sql_database() is sentinel


def test_none_db_graceful_empty(monkeypatch):
    """SQLDatabase 不可用 -> get_table_info/run_sql 返回空串不抛异常。改动：None 短路被删 -> 失败。"""
    monkeypatch.setattr(sh, "get_sql_database", lambda: None)
    assert sh.get_table_info(["t"]) == ""
    assert sh.get_table_info() == ""
    assert sh.run_sql("SELECT 1") == ""


def test_get_table_info_routing(monkeypatch):
    """tables 非空走 get_table_info(table_names=...)；None 走 get_context()。改动：路由分支被改 -> 失败。"""
    db = _FakeDB()
    monkeypatch.setattr(sh, "get_sql_database", lambda: db)
    assert sh.get_table_info(["a", "b"]) == "DDL:a,b"
    assert db.calls[-1] == ("get_table_info", ["a", "b"])
    assert sh.get_table_info() == "CTX"
    assert db.calls[-1] == ("get_context", None)


def test_run_sql_and_exception_swallowed(monkeypatch):
    """run_sql 正常返回；异常吞掉返回空串（降级语义）。改动：异常吞噬被删 -> 失败。"""
    db = _FakeDB()
    monkeypatch.setattr(sh, "get_sql_database", lambda: db)
    assert sh.run_sql("SELECT 1") == "ROWS"
    bad = _FakeDB(fail=True)
    monkeypatch.setattr(sh, "get_sql_database", lambda: bad)
    assert sh.run_sql("SELECT 1") == ""
    assert sh.get_table_info(["t"]) == ""


def test_init_failure_returns_none(monkeypatch):
    """业务引擎初始化异常 -> get_sql_database 返回 None（不抛）。改动：except 分支被删 -> 失败。"""
    import app.services.sql_executor as sex
    monkeypatch.setattr(sh, "_sql_db", None)

    def _boom():
        raise RuntimeError("engine down")

    monkeypatch.setattr(sex, "_get_biz_engine", _boom)
    assert sh.get_sql_database() is None
