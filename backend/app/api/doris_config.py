# -*- coding: utf-8 -*-
"""Doris 配置 + Catalog 管理 API

- /doris/config        GET/PUT  Doris 连接配置（单例）
- /doris/config/test    POST    测试连接（不保存）
- /doris/catalogs       GET     Catalog 列表（SHOW CATALOGS + DB 纳管记录合并）
- /doris/catalogs       POST    创建 Catalog（DB + 执行 CREATE CATALOG）
- /doris/catalogs/{name} DELETE 删除 Catalog（执行 DROP CATALOG + DB 删除）
"""
import re

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from ..core.database import get_db
from ..models.base import DorisConfig, DorisCatalog
from ..services import doris_engine

router = APIRouter()


# --------------------------------------------------------------------------- #
# Doris 连接配置（单例）
# --------------------------------------------------------------------------- #

class DorisConfigRequest(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    charset: Optional[str] = None
    connect_timeout: Optional[int] = None


class DorisConfigTestRequest(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None


def _default_config() -> dict:
    return {
        "host": "localhost",
        "port": 9030,
        "user": "root",
        "password": "",
        "database": "test_db",
        "charset": "utf8mb4",
        "connect_timeout": 10,
    }



_PASSWORD_MASK = "******"  # 三轨M2/S4：响应统一掩码；掩码值=保持原密码

@router.get("/doris/config")
def get_doris_config(db: Session = Depends(get_db)):
    """获取 Doris 连接配置（DB 首行，无则默认值）"""
    cfg = db.query(DorisConfig).first()
    if not cfg:
        return {"code": 200, "data": _default_config()}
    return {
        "code": 200,
        "data": {
            "host": cfg.host,
            "port": cfg.port,
            "user": cfg.user,
            "password": _PASSWORD_MASK,
            "database": cfg.database,
            "charset": cfg.charset,
            "connect_timeout": cfg.connect_timeout,
        },
    }


@router.put("/doris/config")
def put_doris_config(payload: DorisConfigRequest, db: Session = Depends(get_db)):
    """保存 Doris 连接配置（upsert 单例）"""
    cfg = db.query(DorisConfig).first()
    if not cfg:
        d = _default_config()
        for k, v in payload.dict(exclude_unset=True).items():
            if v is not None:
                if k == "password" and v == _PASSWORD_MASK:
                    v = ""  # 三轨M2/S4：新建遇掩码哨兵→存空串（无原密码可保持）
                d[k] = v
        cfg = DorisConfig(
            host=d["host"], port=d["port"], user=d["user"], password=d["password"],
            database=d.get("database", "test_db"), charset=d["charset"], connect_timeout=d["connect_timeout"],
        )
        db.add(cfg)
    else:
        for k, v in payload.dict(exclude_unset=True).items():
            if v is not None:
                if k == "password" and v == _PASSWORD_MASK:
                    continue  # 三轨M2/S4：掩码值=保持原密码
                setattr(cfg, k, v)
    db.commit()
    db.refresh(cfg)
    # 配置变更后重置 DuckDB 连接 + Doris 连接池，下次查询自动用新配置 ATTACH / 重建池
    try:
        from app.services.duckdb_engine import reset_conn as _reset_duckdb
        _reset_duckdb()
    except Exception:
        pass
    try:
        from app.services.doris_engine import reset_pool as _reset_doris_pool
        _reset_doris_pool()
    except Exception:
        pass
    return {"code": 200, "data": {
        "host": cfg.host, "port": cfg.port, "user": cfg.user, "password": _PASSWORD_MASK,
        "database": cfg.database, "charset": cfg.charset, "connect_timeout": cfg.connect_timeout,
    }}


@router.post("/doris/config/test")
def test_doris_config(payload: DorisConfigTestRequest, db: Session = Depends(get_db)):
    """测试 Doris 连接（payload 缺省字段用已存配置）"""
    saved = db.query(DorisConfig).first()
    d = _default_config()
    if saved:
        d.update({"host": saved.host, "port": saved.port, "user": saved.user, "password": saved.password})
    for k, v in payload.dict(exclude_unset=True).items():
        if v is not None:
            d[k] = v
    result = doris_engine.test_connection(d["host"], d["port"], d["user"], d["password"])
    if result["ok"]:
        return {"code": 200, "data": {"ok": True}}
    raise HTTPException(status_code=400, detail=result.get("error", "连接失败"))


# --------------------------------------------------------------------------- #
# Catalog 管理
# --------------------------------------------------------------------------- #

class CatalogCreateRequest(BaseModel):
    name: str
    catalog_type: Optional[str] = "jdbc"      # jdbc | es | internal
    jdbc_url: Optional[str] = None
    jdbc_user: Optional[str] = None
    jdbc_password: Optional[str] = None
    driver_class: Optional[str] = None
    driver_url: Optional[str] = None
    es_hosts: Optional[str] = None            # P4：ES catalog 地址（逗号分隔）
    es_user: Optional[str] = None
    es_password: Optional[str] = None


@router.get("/doris/catalogs")
def list_catalogs(db: Session = Depends(get_db)):
    """Catalog 列表：SHOW CATALOGS(live) + DB 纳管记录(props) 合并

    每项: {name, catalog_type, in_db, jdbc_url, jdbc_user, driver_class, driver_url,
          es_hosts, es_user, created_at}
    """
    live = doris_engine.list_catalogs()
    live_names = {c["name"] for c in live}
    db_rows = {c.name: c for c in db.query(DorisCatalog).all()}
    all_names = live_names | set(db_rows.keys())
    out = []
    for name in sorted(all_names):
        row = db_rows.get(name)
        live_type = next((c["type"] for c in live if c["name"] == name), None)
        out.append({
            "name": name,
            "catalog_type": (row.catalog_type if row else None) or live_type or "jdbc",
            "in_db": row is not None,
            "live_type": live_type,
            "jdbc_url": row.jdbc_url if row else None,
            "jdbc_user": row.jdbc_user if row else None,
            "driver_class": row.driver_class if row else None,
            "driver_url": row.driver_url if row else None,
            "es_hosts": row.es_hosts if row else None,
            "es_user": row.es_user if row else None,
            "created_at": row.created_at.isoformat() if row and row.created_at else None,
        })
    return {"code": 200, "data": out}


@router.post("/doris/catalogs")
def create_catalog(payload: CatalogCreateRequest, db: Session = Depends(get_db)):
    """创建 Catalog（jdbc/es）：DB 插入 + 执行 CREATE CATALOG（失败回滚 DB）。变更联动 reset_pool。"""
    # 三轨M2/S5：入参白名单校验（原样透传引擎前收口）
    if not re.match(r"^[A-Za-z0-9_]{1,64}$", payload.name or ""):
        raise HTTPException(status_code=400, detail="Catalog 名仅允许 1-64 位字母/数字/下划线")
    ctype = (payload.catalog_type or "jdbc").lower()
    if ctype not in ("jdbc", "es", "internal"):
        raise HTTPException(status_code=400, detail=f"不支持 catalog_type: {ctype}")
    for fld, val, cap in [("jdbc_url", payload.jdbc_url, 512), ("driver_class", payload.driver_class, 256),
                          ("driver_url", payload.driver_url, 512), ("es_hosts", payload.es_hosts, 512),
                          ("jdbc_user", payload.jdbc_user, 128), ("es_user", payload.es_user, 128),
                          ("jdbc_password", payload.jdbc_password, 256), ("es_password", payload.es_password, 256)]:
        if val and len(val) > cap:
            raise HTTPException(status_code=400, detail=f"{fld} 超长（上限 {cap}）")
    if ctype == "jdbc":
        if not payload.jdbc_url or not payload.jdbc_url.lower().startswith("jdbc:"):
            raise HTTPException(status_code=400, detail="jdbc 类型必须提供 jdbc: 前缀的 jdbc_url")
        if not (payload.driver_class or "").strip():
            raise HTTPException(status_code=400, detail="jdbc 类型必须提供 driver_class")
    existing = db.query(DorisCatalog).filter(DorisCatalog.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Catalog {payload.name} 已纳管")
    # 先在 Doris 执行 CREATE CATALOG
    result = doris_engine.create_catalog(
        payload.name,
        payload.jdbc_url or "",
        payload.jdbc_user or "",
        payload.jdbc_password or "",
        payload.driver_class or "",
        payload.driver_url or "",
        ctype,
        payload.es_hosts or "",
        payload.es_user or "",
        payload.es_password or "",
    )
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=f"Doris 创建失败: {result.get('error')}")
    # 成功后写 DB
    cat = DorisCatalog(
        name=payload.name,
        catalog_type=ctype,
        jdbc_url=payload.jdbc_url,
        jdbc_user=payload.jdbc_user,
        jdbc_password=payload.jdbc_password,
        driver_class=payload.driver_class,
        driver_url=payload.driver_url,
        es_hosts=payload.es_hosts,
        es_user=payload.es_user,
        es_password=payload.es_password,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    doris_engine.reset_pool()   # P4：catalog 变更联动重置连接池
    return {"code": 200, "data": {"id": str(cat.id), "name": cat.name}}


@router.post("/doris/catalogs/{name}/probe")
def probe_catalog(name: str):
    """探活 catalog：SHOW DATABASES FROM {name}（含采样库表数）。"""
    result = doris_engine.probe_catalog(name)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=f"Catalog 探活失败: {result.get('error')}")
    return {"code": 200, "data": result}


@router.post("/doris/catalogs/{name}/refresh")
def refresh_catalog(name: str):
    """刷新外部 catalog 元数据：REFRESH CATALOG {name}。"""
    result = doris_engine.refresh_catalog(name)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=f"Catalog 刷新失败: {result.get('error')}")
    return {"code": 200, "data": {"ok": True}}


@router.delete("/doris/catalogs/{name}")
def delete_catalog(name: str, db: Session = Depends(get_db)):
    """删除 Catalog：执行 DROP CATALOG + 删 DB 行（即使 Doris 失败也删 DB 记录）。变更联动 reset_pool。"""
    result = doris_engine.drop_catalog(name)
    row = db.query(DorisCatalog).filter(DorisCatalog.name == name).first()
    if row:
        db.delete(row)
        db.commit()
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=f"Doris 删除失败: {result.get('error')}")
    doris_engine.reset_pool()   # P4：catalog 变更联动重置连接池
    return {"code": 200, "data": {"ok": True}}
