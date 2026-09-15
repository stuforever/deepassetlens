# -*- coding: utf-8 -*-
"""⑤（spec §二）：PG pg_tupu（25432）——域状态机数据载体（D1：记忆槽保持 MD）。
psycopg2 现役依赖复用（sql_executor.py L44-46 同款 URL 形）；四表 CREATE IF NOT EXISTS
（PG 原生幂等）挂 main.py lifespan（沿①启动序列惯例）。"""
import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, text


def _pg_password() -> str:
    """环境变量优先；独立进程（测试/冒烟）兜底读 .env.infra（后端进程由 dotenv 预设）。"""
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
_engine = create_engine(_url, pool_pre_ping=True, future=True)

_DDL = [
    """CREATE TABLE IF NOT EXISTS learning_review_cards (
      card_id VARCHAR(64) PRIMARY KEY,
      kind VARCHAR(20) NOT NULL,               -- mother_question | knowledge_point
      item_id VARCHAR(128) NOT NULL,
      user_id VARCHAR(128) NOT NULL,
      stability DOUBLE PRECISION NOT NULL DEFAULT 0,
      difficulty DOUBLE PRECISION NOT NULL DEFAULT 0,
      reps INT NOT NULL DEFAULT 0,
      lapses INT NOT NULL DEFAULT 0,
      due TIMESTAMPTZ NOT NULL DEFAULT now(),
      last_review TIMESTAMPTZ,
      UNIQUE (kind, item_id, user_id))""",
    """CREATE TABLE IF NOT EXISTS learning_review_records (
      id BIGSERIAL PRIMARY KEY,
      card_id VARCHAR(64) NOT NULL REFERENCES learning_review_cards(card_id) ON DELETE CASCADE,
      user_id VARCHAR(128) NOT NULL,
      rating SMALLINT NOT NULL,                 -- 1-4
      scheduled_interval DOUBLE PRECISION NOT NULL,
      reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now())""",
    """CREATE TABLE IF NOT EXISTS learning_wrong_questions (
      wq_id VARCHAR(64) PRIMARY KEY,
      user_id VARCHAR(128) NOT NULL,
      mother_question_id VARCHAR(64) NOT NULL,
      variant_text TEXT NOT NULL,
      error_context TEXT,
      status VARCHAR(20) NOT NULL DEFAULT 'open',  -- open | resolved
      wrong_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      resolved_at TIMESTAMPTZ)""",
    """CREATE TABLE IF NOT EXISTS learning_mother_questions (
      mq_id VARCHAR(64) PRIMARY KEY,
      title TEXT NOT NULL,
      archetype_text TEXT NOT NULL,
      knowledge_point_id VARCHAR(128) NOT NULL,     -- 本体图谱节点 id（批 0.3 实测字段名）
      variant_count INT NOT NULL DEFAULT 0,
      enabled BOOLEAN NOT NULL DEFAULT TRUE)""",
    # 三索引（⑤a 列契约——due 清单/错题筛选/图谱邻接查询路径）
    "CREATE INDEX IF NOT EXISTS idx_lrc_user_due ON learning_review_cards (user_id, due)",
    "CREATE INDEX IF NOT EXISTS idx_lwq_user_status ON learning_wrong_questions (user_id, status)",
    "CREATE INDEX IF NOT EXISTS idx_lmq_kp ON learning_mother_questions (knowledge_point_id)",
]


def ensure_tables() -> None:
    with _engine.begin() as c:
        for ddl in _DDL:
            c.execute(text(ddl))
        _ensure_wrong_question_columns(c)


def _ensure_wrong_question_columns(c=None) -> None:
    """⑤补补-5 步骤 2（M00 +4 列）：错题管理全套扩列——幂等 ALTER，旧行新列 NULL，旧路径零感知。

    question JSON（完整题结构：题干/选项/正确答案）/my_answer（我的答案——错因分析原料）/
    error_type（concept|careless|technique——LLM 判+用户改）/source（chat|manual|practice——渠道溯源）。
    """
    if c is None:
        with _engine.begin() as _c:
            for ddl in (
                "ALTER TABLE learning_wrong_questions ADD COLUMN IF NOT EXISTS question JSON",
                "ALTER TABLE learning_wrong_questions ADD COLUMN IF NOT EXISTS my_answer TEXT",
                "ALTER TABLE learning_wrong_questions ADD COLUMN IF NOT EXISTS error_type VARCHAR(32)",
                "ALTER TABLE learning_wrong_questions ADD COLUMN IF NOT EXISTS source VARCHAR(16)",
            ):
                _c.execute(text(ddl))
        return
    for ddl in (
        "ALTER TABLE learning_wrong_questions ADD COLUMN IF NOT EXISTS question JSON",
        "ALTER TABLE learning_wrong_questions ADD COLUMN IF NOT EXISTS my_answer TEXT",
        "ALTER TABLE learning_wrong_questions ADD COLUMN IF NOT EXISTS error_type VARCHAR(32)",
        "ALTER TABLE learning_wrong_questions ADD COLUMN IF NOT EXISTS source VARCHAR(16)",
    ):
        c.execute(text(ddl))


@contextmanager
def pg_session():
    from sqlalchemy.orm import Session
    s = Session(_engine)
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
