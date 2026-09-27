# -*- coding: utf-8 -*-
"""三轨M2（R1 安全6+流式3）failing 探针先行：

S1 api_mapping 黑名单收口（空白归一化+SELECT/WITH 面危险函数封禁）
S2 Doris 侧只读防护（verify/ai-rewrite 与 DuckDB 侧同款守卫）
S3 data_source 密码脱敏（掩码值=保持原密码语义）
S4 doris_config 密码脱敏（同上）
S5 doris create_catalog 参数校验
S6 dt_agent_capabilities 访问码落库脱敏
H7(:110) h5_ctx 异常路径 __exit__ 必达
H8(:87)  regenerate 先 create_turn 再 append_turn_event
H9(:134) GeneratorExit/CancelledError 捕获→_finish_log 必达+assistant 收尾落库
"""
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest


# ---------------------------------------------------------------------------
# S1+S2 只读守卫（共享 assert_readonly_sql）
# ---------------------------------------------------------------------------

def test_readonly_guard_whitespace_bypass_closed():
    from app.api.api_mapping import assert_readonly_sql
    for bad in ["INSERT\tINTO t VALUES(1)", "DELETE\nFROM t", "drop   table t",
                "update\tt set a=1"]:
        with pytest.raises(Exception):
            assert_readonly_sql(bad)


def test_readonly_guard_dangerous_functions_banned():
    from app.api.api_mapping import assert_readonly_sql
    for bad in ["SELECT read_csv_auto('/etc/passwd')",
                "SELECT * FROM read_parquet('/x/*.parquet')",
                "WITH x AS (SELECT 1) SELECT * FROM glob('/etc/*')",
                "SELECT read_text('/etc/passwd')",
                "SELECT len(load('/x'))"]:
        with pytest.raises(Exception):
            assert_readonly_sql(bad)


def test_readonly_guard_utility_statements_banned():
    from app.api.api_mapping import assert_readonly_sql
    for bad in ["ATTACH '/x' AS a", "PRAGMA database_list", "INSTALL httpfs",
                "LOAD httpfs", "COPY t TO '/tmp/x'", "CALL dsq('/x')",
                "SET enable_external_access=true", "EXPORT DATABASE 'x' TO 'y'"]:
        with pytest.raises(Exception):
            assert_readonly_sql(bad)


def test_readonly_guard_comment_prefix_still_checked():
    from app.api.api_mapping import assert_readonly_sql
    with pytest.raises(Exception):
        assert_readonly_sql("/* c */ DELETE FROM t")
    with pytest.raises(Exception):
        assert_readonly_sql("-- note\nDROP TABLE t")


def test_readonly_guard_legit_queries_pass():
    from app.api.api_mapping import assert_readonly_sql
    assert_readonly_sql("SELECT * FROM t WHERE a = 1")
    assert_readonly_sql("WITH x AS (SELECT 1) SELECT * FROM x")
    assert_readonly_sql("/* 说明 */ SELECT 1")
    assert_readonly_sql("  \n  select  \t 1")


def test_verify_integration_sql_blocks_dml(monkeypatch):
    """Doris 侧只读防护：DML 请求 400 且不触引擎。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.api_mapping as am

    called = {"n": 0}

    def _fake_engine(sql, catalog=None):
        called["n"] += 1
        return {"ok": True}

    import app.services.doris_engine as de
    monkeypatch.setattr(de, "test_integration_sql", _fake_engine)

    app = FastAPI()
    app.include_router(am.router)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/integration-sql/verify", json={"sql": "DELETE FROM t"})
    assert r.status_code == 400, f"Doris 侧 DML 未拦: {r.status_code} {r.text[:80]}"
    assert called["n"] == 0, "守卫失败时引擎不应被执行"


def test_verify_integration_sql_allows_select(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.api_mapping as am
    import app.services.doris_engine as de
    monkeypatch.setattr(de, "test_integration_sql", lambda sql, catalog=None: {"ok": True})
    app = FastAPI()
    app.include_router(am.router)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/integration-sql/verify", json={"sql": "SELECT 1"})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# S3 data_source 密码脱敏
# ---------------------------------------------------------------------------

@pytest.fixture()
def _ds_row():
    from app.core.database import SessionLocal
    from app.models.base import DataSourceConfig
    db = SessionLocal()
    row = DataSourceConfig(name=f"m2掩码探针{uuid.uuid4().hex[:4]}", db_type="mysql",
                           host="127.0.0.1", port=3306, database="dbx",
                           username="u1", password="REAL_SECRET_9", is_default=False)
    db.add(row)
    db.commit()
    yield str(row.id), row.password
    db.rollback()
    db.close()


MASK = "******"


def test_data_source_list_masks_password(_ds_row):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.data_source as dsm
    app = FastAPI()
    app.include_router(dsm.router)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get("/data-sources").json()
    hit = [x for x in r["data"] if x["name"].startswith("m2掩码探针")]
    assert hit and hit[0]["password"] == MASK, f"列表明文回传: {hit[0]['password'] if hit else '无行'}"


def test_data_source_get_masks_password(_ds_row):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.data_source as dsm
    ds_id, real = _ds_row
    app = FastAPI()
    app.include_router(dsm.router)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get(f"/data-sources/{ds_id}").json()
    assert r["data"]["password"] == MASK and r["data"]["password"] != real


def test_data_source_update_mask_keeps_original(_ds_row):
    """掩码值=保持原密码：PUT password=****** 时 DB 原密码不动。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.data_source as dsm
    ds_id, real = _ds_row
    app = FastAPI()
    app.include_router(dsm.router)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.put(f"/data-sources/{ds_id}", json={"description": "更新后", "password": MASK})
    assert r.status_code == 200
    from app.core.database import SessionLocal
    from app.models.base import DataSourceConfig
    db = SessionLocal()
    try:
        row = db.query(DataSourceConfig).filter(DataSourceConfig.id == ds_id).first()
        assert row.password == real, "掩码值覆盖了原密码"
        assert row.description == "更新后"
    finally:
        db.close()


def test_data_source_update_new_password_applies(_ds_row):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.data_source as dsm
    ds_id, _real = _ds_row
    app = FastAPI()
    app.include_router(dsm.router)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.put(f"/data-sources/{ds_id}", json={"password": "NEW_PW_1"})
    assert r.status_code == 200
    from app.core.database import SessionLocal
    from app.models.base import DataSourceConfig
    db = SessionLocal()
    try:
        row = db.query(DataSourceConfig).filter(DataSourceConfig.id == ds_id).first()
        assert row.password == "NEW_PW_1"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# S4 doris_config 密码脱敏（掩码值=保持原密码）
# ---------------------------------------------------------------------------

@pytest.fixture()
def _doris_cfg():
    from app.core.database import SessionLocal
    from app.models.base import DorisConfig
    db = SessionLocal()
    cfg = db.query(DorisConfig).first()
    created = False
    if not cfg:
        cfg = DorisConfig(host="127.0.0.1", port=9030, user="root",
                          password="DORIS_REAL_7", database="db", charset="utf8mb4",
                          connect_timeout=10)
        db.add(cfg)
        db.commit()
        created = True
    yield cfg
    if created:
        db.delete(cfg)
        db.commit()
    db.close()


def test_doris_config_get_masks(_doris_cfg):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.doris_config as dc
    app = FastAPI()
    app.include_router(dc.router)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.get("/doris/config").json()
    assert r["data"]["password"] == MASK


def test_doris_config_put_mask_keeps_original(_doris_cfg):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.doris_config as dc
    real = _doris_cfg.password
    app = FastAPI()
    app.include_router(dc.router)
    c = TestClient(app, raise_server_exceptions=False)
    r = c.put("/doris/config", json={"password": MASK})
    assert r.status_code == 200
    assert r.json()["data"]["password"] == MASK, "PUT 响应也不得回传明文"
    from app.core.database import SessionLocal
    from app.models.base import DorisConfig
    db = SessionLocal()
    try:
        cfg = db.query(DorisConfig).first()
        assert cfg.password == real, "掩码值覆盖了原密码"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# S5 create_catalog 参数校验
# ---------------------------------------------------------------------------

def test_create_catalog_rejects_bad_input(monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.doris_config as dc
    import app.services.doris_engine as de
    engine_called = {"n": 0}
    monkeypatch.setattr(de, "create_catalog", lambda *a, **k: engine_called.update(n=engine_called["n"] + 1) or {"ok": True})
    app = FastAPI()
    app.include_router(dc.router)
    c = TestClient(app, raise_server_exceptions=False)
    bad_bodies = [
        {"name": "x; DROP TABLE y", "catalog_type": "jdbc", "jdbc_url": "jdbc:mysql://h/db", "driver_class": "c"},
        {"name": "ok_name", "catalog_type": "not_a_type"},
        {"name": "ok_name2", "catalog_type": "jdbc", "jdbc_url": "http://evil/h", "driver_class": "c"},
        {"name": "ok_name3", "catalog_type": "jdbc", "jdbc_url": "jdbc:mysql://h/db"},  # 缺 driver_class
    ]
    for body in bad_bodies:
        r = c.post("/doris/catalogs", json=body)
        assert r.status_code == 400, f"{body.get('name')} 未被拒: {r.status_code}"
    assert engine_called["n"] == 0, "校验失败时引擎不应被触达"


def test_execute_sql_endpoint_hardened(monkeypatch):
    """S1 端点级：execute_sql 空白绕过/危险函数拒收（合法查询仍通）。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.api_mapping as am
    import app.services.duckdb_engine as dde
    monkeypatch.setattr(am.duckdb_engine, "load_endpoints_from_db", lambda db: [{"id": "e1"}])
    monkeypatch.setattr(am.duckdb_engine, "execute_sql", lambda sql, endpoints: {"columns": [], "rows": [], "row_count": 0})
    app = FastAPI()
    app.include_router(am.router)
    c = TestClient(app, raise_server_exceptions=False)
    for sql in ["INSERT\tINTO t VALUES(1)", "SELECT read_csv_auto('/etc/passwd')",
                "ATTACH 'x' AS y", "COPY t TO '/tmp/x'"]:
        r = c.post("/api-endpoints/execute", json={"sql": sql})
        assert r.status_code == 400, f"{sql[:30]} 未被拒: {r.status_code}"
    r = c.post("/api-endpoints/execute", json={"sql": "SELECT 1"})
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# S6 访问码落库脱敏
# ---------------------------------------------------------------------------

def test_sanitize_log_input_masks_access_codes():
    from app.api.dt_agent_capabilities import _sanitize_log_input
    out = _sanitize_log_input({"skill_code": "s", "message": "m", "code": "ACCESS123",
                               "x_access_code": "HEADERCODE", "h5_user": "u1"})
    assert out["code"] == MASK and out["x_access_code"] == MASK
    assert out["h5_user"] == "u1" and out["message"] == "m"


def test_capability_log_persists_sanitized(monkeypatch):
    """端点级：SkillExecLog.input_data 不得含明文访问码。"""
    from fastapi.testclient import TestClient
    import app.api.dt_agent_capabilities as cap
    from app.core.database import SessionLocal
    from app.models.skill import Skill

    db = SessionLocal()
    skill_code = db.query(Skill.skill_code).first()[0]
    db.close()

    async def _fake_dispatch(req, session_id, turn_id, user_prefix=""):
        yield {"type": "result", "content": "done", "metadata": {}}

    monkeypatch.setattr("app.api.dt_agent_orchestrations.dispatch", _fake_dispatch)
    c = TestClient(cap.router) if False else None
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(cap.router)
    c = TestClient(app, raise_server_exceptions=False)
    log_id = None
    body = {"skill_code": skill_code, "message": "hi", "h5_user": "tester",
            "session_id": f"s_{uuid.uuid4().hex[:6]}", "code": "ACCESS123",
            "x_access_code": "HEADERCODE"}
    with c.stream("POST", "/capability", json=body) as resp:
        for _ in resp.iter_text():
            pass
    db = SessionLocal()
    try:
        from sqlalchemy import text as _t
        row = db.execute(_t(
            "SELECT log_id, input_data FROM skill_exec_logs ORDER BY started_at DESC LIMIT 1")).first()
        assert row is not None, "SkillExecLog 未落库"
        log_id, input_data = row
        s = str(input_data)
        assert "ACCESS123" not in s and "HEADERCODE" not in s, "访问码明文落库"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# H7/H8/H9 流式生命周期（h5 桩流）
# ---------------------------------------------------------------------------

class _FakeStore:
    def __init__(self, fail_get_messages=False):
        self.calls = []
        self.fail_get_messages = fail_get_messages

    async def get_messages(self, session_id):
        self.calls.append("get_messages")
        if self.fail_get_messages:
            raise RuntimeError("boom_after_enter")
        return [{"id": "m1", "role": "user", "content": "旧问题"}]

    async def delete_message(self, mid):
        self.calls.append(("delete", mid))

    async def create_session(self, title, session_id):
        self.calls.append(("create_session", session_id))

    async def create_turn(self, session_id, capability="", turn_id=None):
        self.calls.append(("create_turn", session_id))

    async def add_message(self, session_id, role, content, **kw):
        self.calls.append(("add_message", role, content[:20]))

    async def append_turn_event(self, turn_id, ev):
        self.calls.append(("append_event", turn_id, ev.get("type")))


class _FakeCtx:
    def __init__(self, track):
        self.track = track

    def __enter__(self):
        self.track.append("enter")
        return self

    def __exit__(self, *a):
        self.track.append("exit")
        return False


def _h5_env(monkeypatch, store, ctx):
    import sys as _sys
    _vendor = str(Path(__file__).resolve().parents[1] / "app" / "vendor")
    if _vendor not in _sys.path:
        _sys.path.insert(0, _vendor)
    import app.services.sishu_full.multi_user.h5 as vh5
    import app.services.sishu_full.multi_user.paths as vpaths
    # R6/Wave2-4b：持久化已换平台 PG store——桩点随迁（原 sqlite_store 桩位退役）
    import app.services.learning.h5_session_store as pstore
    monkeypatch.setattr(vh5, "h5_user_guarded", lambda u, code="", xac="": f"h5_{u}")
    monkeypatch.setattr(vpaths, "user_context", lambda user: ctx)
    monkeypatch.setattr(pstore, "get_h5_pg_session_store", lambda: store)


def _run_gen(resp):
    async def _it():
        chunks = []
        async for chunk in resp.body_iterator:
            chunks.append(chunk)
        return chunks
    return asyncio.get_event_loop().run_until_complete(_it()) if False else asyncio.run(_it())


def _make_req(**kw):
    from app.api.dt_agent_capabilities import CapabilityRequest
    base = dict(skill_code="explore", message="测试消息", session_id=f"s_{uuid.uuid4().hex[:6]}",
                config={}, tools=[], knowledge_bases=[], attachments=[], history_references=[])
    base.update(kw)
    return CapabilityRequest(**base)


def test_regen_creates_turn_before_events(monkeypatch):
    """H8：regenerate 分支必须先 create_turn（vendor sqlite Turn not found 防线）。"""
    import app.api.dt_agent_capabilities as cap
    track = []
    store = _FakeStore()
    ctx = _FakeCtx(track)

    async def _fake_dispatch(req, session_id, turn_id, user_prefix=""):
        yield {"type": "content", "content": "x", "metadata": {}}

    monkeypatch.setattr("app.api.dt_agent_orchestrations.dispatch", _fake_dispatch)
    _h5_env(monkeypatch, store, ctx)
    resp = asyncio.run(cap.capability(_make_req(h5_user="tester", config={"action": "regenerate"})))
    _run_gen(resp)
    assert ("create_turn", store.calls and store.calls[-1][1] if False else None) or True
    ct = [i for i in store.calls if isinstance(i, tuple) and i[0] == "create_turn"]
    ae = [i for i in store.calls if isinstance(i, tuple) and i[0] == "append_event"]
    assert ct, "regenerate 分支未 create_turn（vendor 契约必炸 Turn not found）"
    assert ae and store.calls.index(ct[0]) < store.calls.index(ae[0]), "create_turn 必须先于 append_turn_event"


def test_h5_ctx_exits_on_setup_failure(monkeypatch):
    """H7：h5_ctx.__enter__ 后续语句抛异常时 __exit__ 必达（隔离上下文不泄漏）。"""
    import app.api.dt_agent_capabilities as cap
    track = []
    store = _FakeStore(fail_get_messages=True)
    ctx = _FakeCtx(track)

    async def _fake_dispatch(req, session_id, turn_id, user_prefix=""):
        yield {"type": "content", "content": "x", "metadata": {}}

    monkeypatch.setattr("app.api.dt_agent_orchestrations.dispatch", _fake_dispatch)
    _h5_env(monkeypatch, store, ctx)
    resp = asyncio.run(cap.capability(_make_req(h5_user="tester")))
    chunks = _run_gen(resp)
    assert track.count("enter") == 1 and track.count("exit") == 1, \
        f"上下文泄漏 enter/exit={track}"


def test_generator_exit_finishes_log_and_persists(monkeypatch):
    """H9：客户端断连（GeneratorExit/CancelledError）→ _finish_log 必达+assistant 收尾落库。"""
    import app.api.dt_agent_capabilities as cap
    from app.core.database import SessionLocal
    from app.models.skill import SkillExecLog
    track = []
    store = _FakeStore()
    ctx = _FakeCtx(track)
    log_id_holder = {}

    async def _fake_dispatch(req, session_id, turn_id, user_prefix=""):
        yield {"type": "content", "content": "部分内容", "metadata": {}}
        raise asyncio.CancelledError()

    monkeypatch.setattr("app.api.dt_agent_orchestrations.dispatch", _fake_dispatch)
    _h5_env(monkeypatch, store, ctx)

    # 捕获 _finish_log 目标 log_id：桩化 SessionLocal 不可行（跨模块），直接从日志表取最新
    resp = asyncio.run(cap.capability(_make_req(h5_user="tester")))
    try:
        _run_gen(resp)
    except (asyncio.CancelledError, GeneratorExit):
        pass
    add_assistant = [c for c in store.calls if isinstance(c, tuple)
                     and c[0] == "add_message" and c[1] == "assistant"]
    assert add_assistant, "断连后 assistant 收尾消息未落库"
    db = SessionLocal()
    try:
        from sqlalchemy import text as _t
        row = db.execute(_t(
            "SELECT status FROM skill_exec_logs WHERE execution_code=:c ORDER BY started_at DESC LIMIT 1"),
            {"c": "explore"}).first()
        assert row is not None and row[0] != "running", f"SkillExecLog 滞留 running: {row}"
    finally:
        db.close()
