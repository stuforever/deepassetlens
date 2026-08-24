# -*- coding: utf-8 -*-
"""批10① 金标录入：高频数量类口语变体 -> 直通管道锚点（交付体验演进设计 §七①）。

「查询项目数量」等问法此前未命中示例库（sim<0.95），走完整 Agent 链 45-105s 且出现
两段式交付观感；录入后 L0 直通 <4s 整卡一次成型。

- SQL 口径与 Agent 实测同形：dim_cst_compl_assb_proj（配装项目主数据）全表 COUNT。
- scenario_tag=b10（便于识别/清理）；feed_example=True 同步入示例库作直通锚点。
- 幂等：同问题已存在跳过；--clean 按 b10 tag + 问题集合精确回滚。
- 用法：python -m scripts.seed_golden_b10 [--clean]
"""
import argparse

from app.core.database import SessionLocal
from app.models.base import KgGoldenQaSet, KgVerifiedQaExample
from app.services.golden_qa_service import add_golden

_PROJ_COUNT_SQL = "SELECT COUNT(*) AS proj_cnt FROM pg_tupu.public.dim_cst_compl_assb_proj"

# (question, expected_sql)——数量类高频口语变体，全部同形 COUNT
GOLDENS_B10 = [
    ("查询项目数量", _PROJ_COUNT_SQL),
    ("一共有多少个项目", _PROJ_COUNT_SQL),
    ("项目总数是多少", _PROJ_COUNT_SQL),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true", help="删除本批 b10 金标+示例（回滚用）")
    args = ap.parse_args()
    db = SessionLocal()
    try:
        if args.clean:
            n_g = db.query(KgGoldenQaSet).filter(KgGoldenQaSet.scenario_tag == "b10").delete(synchronize_session=False)
            qs = [t[0] for t in GOLDENS_B10]
            n_e = db.query(KgVerifiedQaExample).filter(
                KgVerifiedQaExample.example_type == "golden",
                KgVerifiedQaExample.question_raw.in_(qs)).delete(synchronize_session=False)
            db.commit()
            print(f"[clean] 删除金标 {n_g} 条 / 示例 {n_e} 条")
            return
        ok, skip, fail = 0, 0, 0
        for q, sql in GOLDENS_B10:
            exist = db.query(KgGoldenQaSet).filter(KgGoldenQaSet.question == q).first()
            if exist:
                skip += 1
                print(f"[skip] {q}")
                continue
            r = add_golden(db, question=q, expected_sql=sql,
                           route_type="generic", scenario_tag="b10", feed_example=True)
            if r.get("ok"):
                ok += 1
                print(f"[ok] {q}  digest={r['expected_result_digest']}")
            else:
                fail += 1
                print(f"[FAIL] {q}  {r.get('error')}")
        total = db.query(KgGoldenQaSet).count()
        print(f"\n完成：新增 {ok} / 跳过 {skip} / 失败 {fail}；KgGoldenQaSet 总计 {total} 条")
    finally:
        db.close()


if __name__ == "__main__":
    main()
