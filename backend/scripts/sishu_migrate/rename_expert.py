# -*- coding: utf-8 -*-
"""v4 批1.1：expert 全局改名 tutor→sishu（裁定③）——数据行 UPDATE（幂等）。
范围：kg_expert_profiles 行 / auth_resource_acl grant 行 / skills.skill_code 前缀。
不迁：expert_events 历史账（审计保留，登记）；skill_exec_logs.execution_code 历史（审计）。
幂等：WHERE 条件精确匹配旧值——重跑=no-op。"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import os
os.chdir(str(Path(__file__).resolve().parents[2]))

from app.core.database import SessionLocal
from sqlalchemy import text


def main() -> int:
    db = SessionLocal()
    changed = []
    try:
        n = db.execute(text(
            "UPDATE kg_expert_profiles SET expert_id='sishu' WHERE expert_id='tutor'")).rowcount
        changed.append(("kg_expert_profiles", n))
        n = db.execute(text(
            "UPDATE auth_resource_acl SET resource_id='sishu' WHERE resource_id='tutor'")).rowcount
        changed.append(("auth_resource_acl", n))
        n = db.execute(text(
            "UPDATE skills SET skill_code=CONCAT('sishu/', SUBSTRING(skill_code, 7)) "
            "WHERE skill_code LIKE 'tutor/%'")).rowcount
        changed.append(("skills.skill_code", n))
        db.commit()
        print("updated:", changed)
        # 复位专家卡缓存（TTL 5s 自愈，这里 force 立即生效）
        from app.services import expert_config
        expert_config._load_rows(force=True)
        rows = db.execute(text("SELECT expert_id FROM kg_expert_profiles ORDER BY 1")).fetchall()
        print("expert_ids now:", [r[0] for r in rows])
        codes = db.execute(text(
            "SELECT skill_code FROM skills WHERE skill_code LIKE 'sishu/%' ORDER BY 1")).fetchall()
        print("sishu skills:", [r[0] for r in codes])
        return 0
    except Exception as e:
        db.rollback()
        print("ERROR:", e)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
