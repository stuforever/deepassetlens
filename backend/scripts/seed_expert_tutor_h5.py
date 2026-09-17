# -*- coding: utf-8 -*-
"""IA 件批1：私塾先生h5 专家卡种子（幂等——存在即跳过，零 API 手工调用）。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.core.database import SessionLocal          # noqa: E402
from app.models.base import ExpertProfile           # noqa: E402

EXPERT_ID = "tutor-h5"
db = SessionLocal()
try:
    if db.get(ExpertProfile, EXPERT_ID) is None:
        db.add(ExpertProfile(
            expert_id=EXPERT_ID,
            name="私塾先生h5",
            tagline="面向学生的移动学习端——课堂/复习/错题/精通之路",
            enabled=True,
            entry_kind="chat",
            system_prompt="你是私塾先生h5，面向学生的移动学习端助手。",
            version=1,
        ))
        db.commit()
        print("[seed] tutor-h5 已创建")
    else:
        print("[seed] tutor-h5 已存在，跳过")
finally:
    db.close()
