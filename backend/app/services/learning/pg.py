# -*- coding: utf-8 -*-
"""v4批2 2.2：learning/pg → sishu_data 兼容 re-export 层（单源不双轨——登记取舍：
引擎/全族 DDL 单点迁至 app/services/sishu_data/{pg,schemas}.py，本文件仅保留既有
导入面 _engine/ensure_tables/pg_session 供 chapter_service/learner_profile/
learning_dao/service/main.py 既有消费零改）。新代码一律 from app.services.sishu_data import ...。"""
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.services.sishu_data.pg import engine as _engine  # noqa: F401
from app.services.sishu_data.schemas import ensure as _schemas_ensure


def ensure_tables() -> None:
    """兼容名：四表改名后=全族 ensure（幂等；含 wrong_questions +4 扩列）。"""
    _schemas_ensure()


@contextmanager
def pg_session():
    s = Session(_engine)
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
