# -*- coding: utf-8 -*-
"""M12 单测：单例契约/catalog 三型/探针缓存（金标准对齐补测）。

变异锚点：每条注释标明何种生产代码改动会让它失败——本模块是对既有工程的金标准
对齐补测（as-if-greenfield 视角：按 M12 spec §七验收标准锚定现有实现）。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

from fastapi import HTTPException  # noqa: E402

from app.models.base import DorisCatalog, DorisConfig  # noqa: E402


# ---------------------------------------------------------------------------
# 任务 1：单例模型契约（spec §三）
# ---------------------------------------------------------------------------

def test_doris_config_singleton_defaults():
    """单例连接列契约+默认值（spec §三：host/port 9030/charset/timeout）。
    变异锚点：port 默认漂移 → Doris 默认连不上。"""
    cols = {c.name for c in DorisConfig.__table__.columns}
    assert {"host", "port", "user", "database", "connect_timeout", "charset"} <= cols
    assert DorisConfig.__table__.c.port.default.arg == 9030


def test_catalog_model_columns():
    """catalog 三型列契约（spec §四：jdbc 四列/es 三列 P4/name+type）。
    变异锚点：es 列删 → ES 联邦断；jdbc_url 删 → 外部库联邦断。"""
    cols = {c.name for c in DorisCatalog.__table__.columns}
    assert {"name", "catalog_type", "jdbc_url", "jdbc_user", "jdbc_password",
            "driver_class", "driver_url", "es_hosts", "es_user", "es_password"} <= cols


# ---------------------------------------------------------------------------
# 任务 1：config GET 无行建默认（spec §七.1）
# ---------------------------------------------------------------------------

def test_get_config_builds_default_row():
    """GET /doris/config 无行时建默认行（spec §七.1）。实现为真连接 DB——
    直接锚定端点函数存在与 _default_config 形态（不触发真建行副作用）。
    变异锚点：默认行逻辑删 → 首次配置页 500/空。"""
    from app.api.doris_config import _default_config
    d = _default_config()
    assert isinstance(d, dict)
    assert d.get("port") == 9030


# ---------------------------------------------------------------------------
# 任务 2：catalog 创建参数校验矩阵（spec §七.2）
# ---------------------------------------------------------------------------

def test_catalog_create_validation_matrix():
    """三型参数校验：jdbc 必填 jdbc_url/driver；es 必填 es_hosts；internal 免参数。
    变异锚点：分派校验删 → 残缺 catalog 落库（联邦执行期才崩）。"""
    from app.api.doris_config import CatalogCreateRequest, create_catalog
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        # jdbc 缺 jdbc_url → 400
        with pytest.raises(HTTPException) as ei:
            create_catalog(CatalogCreateRequest(name="m12j", catalog_type="jdbc"), db=db)
        assert ei.value.status_code == 400
        # es 缺 es_hosts → 400
        with pytest.raises(HTTPException) as ei:
            create_catalog(CatalogCreateRequest(name="m12e", catalog_type="es"), db=db)
        assert ei.value.status_code == 400
    finally:
        db.close()


def test_catalog_duplicate_name_rejected():
    """重名 catalog → 400（spec §七.2）。
    变异锚点：重名校验删 → 联邦三段命名歧义。"""
    from app.api.doris_config import CatalogCreateRequest, create_catalog
    from app.core.database import SessionLocal
    from app.models.base import DorisCatalog as DC
    import uuid
    db = SessionLocal()
    name = f"m12dup{uuid.uuid4().hex[:6]}"
    try:
        db.query(DC).filter(DC.name == name).delete()
        db.add(DC(name=name, catalog_type="internal"))
        db.commit()
        with pytest.raises(HTTPException) as ei:
            create_catalog(CatalogCreateRequest(name=name, catalog_type="internal"), db=db)
        assert ei.value.status_code == 400
    finally:
        db.query(DC).filter(DC.name == name).delete()
        db.commit()
        db.close()


# ---------------------------------------------------------------------------
# 任务 3：探针缓存（spec §七.3 plan 原文测试）
# ---------------------------------------------------------------------------

def test_probe_cached_within_ttl(monkeypatch):
    """60s TTL 内重复探测零额外连接；force 穿透（spec §五/§八.3）。
    _PROBES 注册表模块加载时绑定引用——patch 字典值（非模块属性）。
    变异锚点：缓存删 → 探针风暴；force 删 → 手动刷新失效。"""
    from app.services import engine_health as H
    calls = []
    monkeypatch.setitem(H._PROBES, "doris", lambda: calls.append(1))
    H.invalidate("doris")
    H.probe("doris")
    H.probe("doris")            # 第二次命中缓存
    assert len(calls) == 1
    H.probe("doris", force=True)  # 穿透
    assert len(calls) == 2


def test_snapshot_covers_three_engines():
    """snapshot 汇总三引擎（spec §五）。
    变异锚点：注册表缺引擎 → 快照缺面。"""
    from app.services.engine_health import snapshot, _PROBES
    assert set(_PROBES.keys()) == {"doris", "duckdb", "pg"}
    snap = snapshot()
    assert set(snap.keys()) == {"doris", "duckdb", "pg"}


# ---------------------------------------------------------------------------
# R5批①（清单安全）：build_sql_with_filters 拼接回退废除 + CREATE CATALOG 值侧防线
# ---------------------------------------------------------------------------

def test_build_sql_filters_unparseable_sql_raises():
    """sqlglot 解析失败 → 拒绝拼接回退，抛 ValueError（原：字符串拼 WHERE 可注入）。
    变异锚点：回退拼接复活 → 本测红。"""
    from app.services.doris_engine import build_sql_with_filters
    with pytest.raises(ValueError):
        build_sql_with_filters("NOT (( VALID SQL", {"col": "x' OR '1'='1"})
    # 可解析 SQL 仍走 AST 正常拼条件（守卫：fix 不得误伤主路径）
    out = build_sql_with_filters("SELECT 1 FROM t", {"col": "v"})
    assert "WHERE" in out and "'v'" in out


def test_create_catalog_rejects_injection_values():
    """catalog 属性值含 " / \ / 换行 → ValueError 拒收（原：f-string 直嵌 DDL 可注入
    PROPERTIES）。变异锚点：值侧校验删除 → 本测红。"""
    from app.services.doris_engine import create_catalog
    for bad in ('x"', "y\\", "a\nb"):
        with pytest.raises(ValueError):
            create_catalog("ct", jdbc_url=bad, jdbc_user="u", jdbc_password="p",
                           driver_class="c", driver_url="d")
    with pytest.raises(ValueError):
        create_catalog("ct", jdbc_url="j", jdbc_user="u", jdbc_password="p",
                       driver_class="c", driver_url="d", catalog_type="es", es_hosts="h\\")
