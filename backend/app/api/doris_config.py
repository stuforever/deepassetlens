# -*- coding: utf-8 -*-
"""Doris 配置 + Catalog 管理 API

- /doris/config        GET/PUT  Doris 连接配置（单例）
- /doris/config/test    POST    测试连接（不保存）
- /doris/catalogs       GET     Catalog 列表（SHOW CATALOGS + DB 纳管记录合并）
- /doris/catalogs       POST    创建 Catalog（DB + 执行 CREATE CATALOG）
- /doris/catalogs/{name} DELETE 删除 Catalog（执行 DROP CATALOG + DB 删除）
"""
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
        "charset": "utf8mb4",
        "connect_timeout": 10,
    }


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
            "password": cfg.password,
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
                d[k] = v
        cfg = DorisConfig(
            host=d["host"], port=d["port"], user=d["user"], password=d["password"],
            charset=d["charset"], connect_timeout=d["connect_timeout"],
        )
        db.add(cfg)
    else:
        for k, v in payload.dict(exclude_unset=True).items():
            if v is not None:
                setattr(cfg, k, v)
    db.commit()
    db.refresh(cfg)
    return {"code": 200, "data": {
        "host": cfg.host, "port": cfg.port, "user": cfg.user, "password": cfg.password,
        "charset": cfg.charset, "connect_timeout": cfg.connect_timeout,
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
    catalog_type: Optional[str] = "jdbc"
    jdbc_url: Optional[str] = None
    jdbc_user: Optional[str] = None
    jdbc_password: Optional[str] = None
    driver_class: Optional[str] = None
    driver_url: Optional[str] = None


@router.get("/doris/catalogs")
def list_catalogs(db: Session = Depends(get_db)):
    """Catalog 列表：SHOW CATALOGS(live) + DB 纳管记录(props) 合并

    每项: {name, catalog_type, in_db, jdbc_url, jdbc_user, driver_class, driver_url, created_at}
    """
    live = doris_engine.list_catalogs()
    live_names = {c["name"] for c in live}
    db_rows = {c.name: c for c in db.query(DorisCatalog).all()}
    all_names = live_names | set(db_rows.keys())
    out = []
    for name in sorted(all_names):
        row = db_rows.get(name)
        out.append({
            "name": name,
            "catalog_type": row.catalog_type if row else "jdbc",
            "in_db": row is not None,
            "jdbc_url": row.jdbc_url if row else None,
            "jdbc_user": row.jdbc_user if row else None,
            "driver_class": row.driver_class if row else None,
            "driver_url": row.driver_url if row else None,
            "created_at": row.created_at.isoformat() if row and row.created_at else None,
        })
    return {"code": 200, "data": out}


@router.post("/doris/catalogs")
def create_catalog(payload: CatalogCreateRequest, db: Session = Depends(get_db)):
    """创建 Catalog：DB 插入 + 执行 CREATE CATALOG（失败回滚 DB）"""
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
    )
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=f"Doris 创建失败: {result.get('error')}")
    # 成功后写 DB
    cat = DorisCatalog(
        name=payload.name,
        catalog_type=payload.catalog_type or "jdbc",
        jdbc_url=payload.jdbc_url,
        jdbc_user=payload.jdbc_user,
        jdbc_password=payload.jdbc_password,
        driver_class=payload.driver_class,
        driver_url=payload.driver_url,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return {"code": 200, "data": {"id": str(cat.id), "name": cat.name}}


@router.delete("/doris/catalogs/{name}")
def delete_catalog(name: str, db: Session = Depends(get_db)):
    """删除 Catalog：执行 DROP CATALOG + 删 DB 行（即使 Doris 失败也删 DB 记录）"""
    result = doris_engine.drop_catalog(name)
    row = db.query(DorisCatalog).filter(DorisCatalog.name == name).first()
    if row:
        db.delete(row)
        db.commit()
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=f"Doris 删除失败: {result.get('error')}")
    return {"code": 200, "data": {"ok": True}}
