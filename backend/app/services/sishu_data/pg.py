# -*- coding: utf-8 -*-
"""v4批2：sishu_data PG 引擎（25432 db=tupu，E-48 勘误实名）。
沿 learning/pg.py 模式（TUPU_PG_* env + .env.infra/.env 兜底读密）。"""
import os
from pathlib import Path

from sqlalchemy import create_engine


def _pg_password() -> str:
    pw = os.getenv("TUPU_PG_PASSWORD", "")
    if pw:
        return pw
    for f in (Path(__file__).resolve().parents[4] / ".env.infra",
              Path(__file__).resolve().parents[4] / ".env"):
        if f.exists():
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip().startswith("TUPU_PG_PASSWORD"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


_url = ("postgresql+psycopg2://postgres:{pw}@{host}:{port}/{db}").format(
    pw=_pg_password(), host=os.getenv("TUPU_PG_HOST", "localhost"),
    port=os.getenv("TUPU_PG_PORT", "25432"), db=os.getenv("TUPU_PG_DB", "tupu"))
engine = create_engine(_url, pool_pre_ping=True, future=True)
