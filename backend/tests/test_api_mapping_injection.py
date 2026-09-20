# -*- coding: utf-8 -*-
"""三轨M1（R0 critical#1-3）failing 探针先行：

① api_mapping.py:480 SQL 注入——filters 值参数化+键/表名标识符白名单；
   preview_entity_data 的 f'SELECT * FROM "{table}"' 二次注入面同修。
   三态 payload：值单引号逃逸 / `;` 叠加语句 / 键双引号标识符逃逸 + dict/list/None 拒收
   + 合法 filters 契约回归（同形状返回）。
② data_sync.py:23 清库无鉴权——重建类接口挂 _require_admin（探针：非 admin→403）。
③ concept_admin.py:289/:345 原子性——损坏文件导入→图谱数据保留断言。
"""
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest


# ---------------------------------------------------------------------------
# ① SQL 注入：物理表分支 SQL 构造器（参数化+标识符白名单）
# ---------------------------------------------------------------------------

def _build(table, filters, limit=500):
    from app.api.api_mapping import build_biz_table_sql
    return build_biz_table_sql(table, filters, limit)


def test_injection_value_quote_escaped_via_params():
    """值 `x' OR '1'='1' --` 不得拼进 SQL 文本——必须走绑定参数。"""
    sql, params = _build("dim_customer", {"cust_name": "x' OR '1'='1' --"})
    assert "OR '1'='1'" not in sql, f"注入 payload 泄入 SQL 文本: {sql}"
    assert params and "x' OR '1'='1' --" in list(params.values()), "值应作为绑定参数"
    assert sql.count("'") == 0, f"SQL 文本不应含裸引号字面量: {sql}"


def test_injection_stacked_statement_neutralized():
    """`;` 叠加语句 payload 作为字面量参数，不产生第二语句。"""
    payload = "a'; DROP TABLE dim_customer; --"
    sql, params = _build("dim_customer", {"cust_name": payload})
    assert "DROP TABLE" not in sql.upper() or payload in list(params.values())
    assert ";" not in sql, f"SQL 文本含分号（叠加语句面）: {sql}"


def test_injection_key_identifier_rejected():
    """键双引号标识符逃逸：`x" WHERE "y` 等非法标识符必须拒收。"""
    for bad_key in ['x" WHERE "y', 'a"; DROP TABLE b; --', "col name", "col;drop", "col'x"]:
        with pytest.raises(Exception):
            _build("dim_customer", {bad_key: "v"})


def test_non_scalar_filter_value_rejected():
    """dict/list/None 值此前会把 Python repr 拼进 SQL——必须 400 拒收。"""
    for bad_val in [{"a": 1}, [1, 2], None]:
        with pytest.raises(Exception):
            _build("dim_customer", {"cust_name": bad_val})


def test_legit_filters_contract_regression():
    """合法过滤行为不变（契约回归）：同形状 WHERE，键值齐整。"""
    sql, params = _build("dim_customer", {"cust_name": "国网北京"})
    assert sql.startswith('SELECT * FROM "dim_customer"')
    assert '"cust_name"' in sql and "LIMIT 500" in sql
    assert params == {"p0": "国网北京"}


def test_injection_table_identifier_rejected():
    """表名（DB 二次注入面）非法标识符拒收。"""
    for bad in ['t"; DROP TABLE x; --', "t;drop", 't" OR "1"="1']:
        with pytest.raises(Exception):
            _build(bad, {})


def test_preview_table_validated():
    """preview_entity_data 同源校验：非法表名在构造 SQL 前被拒。"""
    from app.api.api_mapping import validate_sql_identifier
    assert validate_sql_identifier("dim_customer") == "dim_customer"
    for bad in ['t"; --', "t;drop", "", "9abc", "t t"]:
        with pytest.raises(Exception):
            validate_sql_identifier(bad)


# ---------------------------------------------------------------------------
# ② data_sync 重建类端点鉴权
# ---------------------------------------------------------------------------

def _sync_client(monkeypatch, *, is_admin, user_sub="tester"):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import app.api.data_sync as ds

    class _U:
        def __init__(self, admin):
            self._admin = admin
            self.sub = user_sub

        def is_admin(self):
            return self._admin

    monkeypatch.setattr(ds, "get_current_user", lambda request: _U(is_admin))
    # 服务层桩（不触真实 Neo4j/Milvus）
    monkeypatch.setattr(ds, "_svc_stub", True, raising=False)

    app = FastAPI()
    app.include_router(ds.router)
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("path", ["/api/v1/sync/neo4j-wipe", "/api/v1/sync/neo4j-all",
                                  "/api/v1/sync/entity-vectors", "/api/v1/sync/attribute-vectors"])
def test_rebuild_endpoints_require_admin(path, monkeypatch):
    """非 admin → 403（重建类破坏性操作四端点）。"""
    c = _sync_client(monkeypatch, is_admin=False)
    r = c.post(path)
    assert r.status_code == 403, f"{path} 匿名/非 admin 未被拒: {r.status_code}"


def test_rebuild_endpoints_admin_passes_gate(monkeypatch):
    """admin 过门（服务层桩返回，不触真实资源）。"""
    import app.api.data_sync as ds

    monkeypatch.setattr(ds, "sync_all_to_neo4j", lambda db, force: {"ok": True}, raising=False)
    c = _sync_client(monkeypatch, is_admin=True)
    r = c.post("/api/v1/sync/neo4j-all?force=false")
    assert r.status_code == 200, f"admin 被误拒: {r.status_code} {r.text[:120]}"


# ---------------------------------------------------------------------------
# ③ concept_admin clear+import 原子性
# ---------------------------------------------------------------------------

@pytest.fixture()
def _kg_seed():
    """PG kg 域种子：一条哨兵概念。"""
    from app.core.database import SessionLocal
    from app.models.base import Concept
    import uuid
    db = SessionLocal()
    sent = None
    try:
        sent = Concept(id=str(uuid.uuid4()), name=f"M1原子性哨兵{uuid.uuid4().hex[:6]}",
                       level=1, area_index=1, sort_order=0)
        db.add(sent)
        db.commit()
        yield sent.id
    finally:
        try:
            db.rollback()
        except Exception:
            pass
        db.close()


def _post_import(client, file_bytes: bytes, clear: bool):
    return client.post(
        "/api/v1/import/excel",
        params={"clear": str(clear)},
        files={"file": ("m1.xlsx", file_bytes,
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )


def test_import_corrupt_file_keeps_graph_data(_kg_seed):
    """损坏文件 + clear=True：清空不得先于解析提交——哨兵概念必须保留。"""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.core.database import SessionLocal
    from app.models.base import Concept

    import app.api.concept_admin as ca
    app = FastAPI()
    app.include_router(ca.router)
    c = TestClient(app, raise_server_exceptions=False)

    r = _post_import(c, b"this is not an excel file", clear=True)
    assert r.status_code >= 400, f"损坏文件未被拒: {r.status_code}"

    db = SessionLocal()
    try:
        row = db.query(Concept).filter(Concept.id == _kg_seed).first()
        assert row is not None, "clear 先于解析提交——图谱数据被误清（原子性破坏）"
    finally:
        db.close()


def test_import_partial_phase_failure_keeps_all_phases(_kg_seed):
    """合法概念 sheet + 缺列实体 sheet：四阶段分 commit 的中间态必须消除——概念也不得残留。"""
    import pandas as pd
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.core.database import SessionLocal
    from app.models.base import Concept

    import app.api.concept_admin as ca
    app = FastAPI()
    app.include_router(ca.router)
    c = TestClient(app, raise_server_exceptions=False)

    buf = io.BytesIO()
    marker = f"M1阶段测试{pd.Timestamp.now().value}"
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        pd.DataFrame([{"概念名称": marker, "层级": 1, "父级名称": "",
                       "业务域索引": 1, "顺序": 0, "描述": "", "所属系统": ""}]).to_excel(
            w, sheet_name="概念清单", index=False)
        # 实体清单缺必需列「实体编码」→ 第二阶段必然解析失败
        pd.DataFrame([{"所属概念": marker, "实体名称": "x"}]).to_excel(
            w, sheet_name="实体清单", index=False)
    r = _post_import(c, buf.getvalue(), clear=False)
    assert r.status_code >= 400, f"缺列文件未被拒: {r.status_code}"

    db = SessionLocal()
    try:
        leftover = db.query(Concept).filter(Concept.name == marker).count()
        assert leftover == 0, f"概念阶段已部分提交（{leftover} 行）——分阶段 commit 中间态仍在"
    finally:
        db.close()
