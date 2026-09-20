# -*- coding: utf-8 -*-
"""v4批2 2.2：learning_* 四表改名迁移 → sishu_*（ALTER RENAME，行数对账零损失）。
FK（review_records→review_cards）随 RENAME 自动重指；索引同步改名。幂等：存在即跳过。"""
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from sqlalchemy import text

from app.services.sishu_data.pg import engine

RENAMES = [
    ("learning_review_cards", "sishu_review_cards"),
    ("learning_review_records", "sishu_review_records"),
    ("learning_wrong_questions", "sishu_wrong_questions"),
    ("learning_mother_questions", "sishu_mother_questions"),
]
INDEX_RENAMES = [
    ("idx_lrc_user_due", "idx_sishu_review_cards_user_due"),
    ("idx_lwq_user_status", "idx_sishu_wrong_questions_user_status"),
    ("idx_lmq_kp", "idx_sishu_mother_questions_kp"),
]


def main() -> int:
    counts_before = {}
    with engine.begin() as c:
        existing = {r[0] for r in c.execute(text(
            "SELECT tablename FROM pg_tables WHERE schemaname='public'"))}
        for old, new in RENAMES:
            if old in existing:
                counts_before[old] = c.execute(text(f"SELECT COUNT(*) FROM {old}")).scalar()
        # 改名前快照行数合计
        total_before = sum(counts_before.values())
        for old, new in RENAMES:
            if old in existing:
                c.execute(text(f"ALTER TABLE {old} RENAME TO {new}"))
                print(f"renamed {old} -> {new}")
            elif new not in existing:
                print(f"MISSING BOTH: {old}/{new}")
                return 1
            else:
                print(f"skip {old}（已改名）")
        for old, new in INDEX_RENAMES:
            idxs = {r[0] for r in c.execute(text(
                "SELECT indexname FROM pg_indexes WHERE schemaname='public'"))}
            if old in idxs and new not in idxs:
                c.execute(text(f"ALTER INDEX {old} RENAME TO {new}"))
                print(f"renamed index {old} -> {new}")
    # 行数对账（仅当本轮发生过改名——纯 skip 重跑无对账意义）
    if not counts_before:
        print("幂等重跑：无改名发生，行数对账跳过")
        return 0
    total_after = 0
    with engine.connect() as c:
        for old, new in RENAMES:
            total_after += c.execute(text(f"SELECT COUNT(*) FROM {new}")).scalar()
    ok = total_after == total_before
    print(f"行数对账: before={total_before} after={total_after} -> {'OK' if ok else 'LOSS!'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
