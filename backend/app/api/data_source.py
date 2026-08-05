from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid

from ..core.database import get_db
from ..models.base import DataSourceConfig

router = APIRouter()


class DataSourceCreateRequest(BaseModel):
    name: str
    db_type: Optional[str] = "mysql"
    host: str
    port: Optional[int] = 3306
    database: str
    username: str
    password: str
    description: Optional[str] = None
    is_default: Optional[bool] = False
    doris_catalog_name: Optional[str] = None


class DataSourceUpdateRequest(BaseModel):
    name: Optional[str] = None
    db_type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None
    enabled: Optional[bool] = None
    doris_catalog_name: Optional[str] = None


def _norm_uuid(val):
    if not val:
        return val
    s = str(val).strip()
    if not s:
        return val
    if len(s) == 32:
        s = f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
    return s


def _to_uuid(val):
    try:
        s = str(val).strip()
        if len(s) == 32:
            s = f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"
        uuid.UUID(s)
        return s
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的ID格式: {val}")


@router.get("/data-sources")
def list_data_sources(db: Session = Depends(get_db)):
    items = db.query(DataSourceConfig).all()
    return {
        "code": 200,
        "data": [
            {
                "id": _norm_uuid(str(i.id)),
                "name": i.name,
                "db_type": i.db_type,
                "host": i.host,
                "port": i.port,
                "database": i.database,
                "username": i.username,
                "password": i.password,
                "description": i.description,
                "is_default": i.is_default,
                "enabled": i.enabled,
                "doris_catalog_name": i.doris_catalog_name,
                "created_at": i.created_at.isoformat() if i.created_at else None,
            }
            for i in items
        ],
    }


@router.get("/data-sources/{ds_id}")
def get_data_source(ds_id: str, db: Session = Depends(get_db)):
    uid = _to_uuid(ds_id)
    item = db.query(DataSourceConfig).filter(DataSourceConfig.id == uid).first()
    if not item:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return {
        "code": 200,
        "data": {
            "id": _norm_uuid(str(item.id)),
            "name": item.name,
            "db_type": item.db_type,
            "host": item.host,
            "port": item.port,
            "database": item.database,
            "username": item.username,
            "password": item.password,
            "description": item.description,
            "is_default": item.is_default,
            "enabled": item.enabled,
            "doris_catalog_name": item.doris_catalog_name,
        },
    }


@router.post("/data-sources")
def create_data_source(payload: DataSourceCreateRequest, db: Session = Depends(get_db)):
    if payload.is_default:
        db.query(DataSourceConfig).update({DataSourceConfig.is_default: False})

    item = DataSourceConfig(
        name=payload.name,
        db_type=payload.db_type or "mysql",
        host=payload.host,
        port=payload.port or 3306,
        database=payload.database,
        username=payload.username,
        password=payload.password,
        description=payload.description,
        is_default=payload.is_default or False,
        doris_catalog_name=payload.doris_catalog_name,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"code": 200, "data": {"id": _norm_uuid(str(item.id)), "name": item.name}}


@router.put("/data-sources/{ds_id}")
def update_data_source(ds_id: str, payload: DataSourceUpdateRequest, db: Session = Depends(get_db)):
    uid = _to_uuid(ds_id)
    item = db.query(DataSourceConfig).filter(DataSourceConfig.id == uid).first()
    if not item:
        raise HTTPException(status_code=404, detail="数据源不存在")

    if payload.is_default:
        db.query(DataSourceConfig).update({DataSourceConfig.is_default: False})

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return {"code": 200, "data": {"id": _norm_uuid(str(item.id)), "name": item.name}}


@router.delete("/data-sources/{ds_id}")
def delete_data_source(ds_id: str, db: Session = Depends(get_db)):
    uid = _to_uuid(ds_id)
    item = db.query(DataSourceConfig).filter(DataSourceConfig.id == uid).first()
    if not item:
        raise HTTPException(status_code=404, detail="数据源不存在")
    db.delete(item)
    db.commit()
    return {"code": 200, "data": {"message": "已删除"}}


@router.post("/data-sources/{ds_id}/test")
def test_data_source(ds_id: str, db: Session = Depends(get_db)):
    uid = _to_uuid(ds_id)
    item = db.query(DataSourceConfig).filter(DataSourceConfig.id == uid).first()
    if not item:
        raise HTTPException(status_code=404, detail="数据源不存在")
    try:
        if (item.db_type or "").lower() in ("postgresql", "postgres", "pg"):
            import psycopg2
            conn = psycopg2.connect(
                host=item.host, port=item.port, dbname=item.database,
                user=item.username, password=item.password,
                connect_timeout=5,
            )
        else:
            import pymysql
            conn = pymysql.connect(
                host=item.host, port=item.port, database=item.database,
                user=item.username, password=item.password,
                charset='utf8mb4', connect_timeout=5,
            )
        conn.close()
        return {"code": 200, "data": {"connected": True, "message": "连接成功"}}
    except Exception as e:
        return {"code": 200, "data": {"connected": False, "message": str(e)}}
