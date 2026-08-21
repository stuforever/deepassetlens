# -*- coding: utf-8 -*-
"""S2 金标扩容种子：7 层矩阵 48 条（5 现有 + 43 新增）灌入 KgGoldenQaSet + 示例库。

层：聚合(5) / 计数(6) / 明细(6) / 过滤(8) / JOIN(4) / 澄清(4) / 措辞变体(15 新增 + 3 现有)。

- 期望 SQL 与 agent 实测行为同形（规范 7 列 SELECT：cust_id,cust_name,voltage_name,
  ctrt_cap,run_cap,impt_lv_name,bus_srv_addr_name；JOIN 走 inst 自列；澄清无 SQL）。
- 澄清类 scenario_tag=clarify，期望 digest 人工给 {row_count:0}，不入示例库（歧义问题
  无 SQL 可锚定，入库反而污染 G1）。
- 幂等：同问题已存在跳过；--clean 先删 scenario_tag in (s2,clarify) 再灌（迭代用）。
- 用法：python -m scripts.seed_golden_s2 [--clean]
"""
import argparse
import sys

from app.core.database import SessionLocal
from app.models.base import KgGoldenQaSet, KgVerifiedQaExample
from app.services.golden_qa_service import add_golden

_CANON = ("cust_id", "cust_name", "voltage_name", "ctrt_cap", "run_cap",
          "impt_lv_name", "bus_srv_addr_name")
_C = ", ".join(_CANON)
_FROM = " FROM pg_tupu.public.dim_cst_elec_cons_cust"
_INST = " FROM pg_tupu.public.dim_cst_inst_elec_cons"

# 规范 7 列 SELECT 模板（agent 实际返回形态；TopN/过滤据此写 WHERE/ORDER BY）
def _sel(where: str = "", order: str = "", limit: str = "") -> str:
    return f"SELECT {_C}{_FROM}" + (f" WHERE {where}" if where else "") + (f" ORDER BY {order}" if order else "") + (f" LIMIT {limit}" if limit else "")


# (question, expected_sql | None, scenario_tag)
# scenario_tag: agg / count / detail / filter / join / variant / clarify
GOLDENS = [
    # ---------- 聚合 5（可靠维度：电压/重要性/客户分类/用电类别/负荷性质） ----------
    ("各电压等级的用电客户分布是怎样的",
     "SELECT voltage_name, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY voltage_name", "agg"),
    ("各重要性等级的用电客户分布",
     "SELECT impt_lv_name, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY impt_lv_name", "agg"),
    ("各用电客户分类的客户分布情况",
     "SELECT cust_cls_name, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY cust_cls_name", "agg"),
    ("各用电类别的用电客户分布",
     "SELECT ec_categ_name, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY ec_categ_name", "agg"),
    ("各负荷性质的用电客户分布",
     "SELECT load_char_name, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY load_char_name", "agg"),
    # ---------- 计数 6 ----------
    ("统计一下当前有多少用电客户",
     "SELECT COUNT(*) FROM pg_tupu.public.dim_cst_elec_cons_cust", "count"),
    ("用电客户总数是多少",
     "SELECT COUNT(*) FROM pg_tupu.public.dim_cst_elec_cons_cust", "count"),
    ("统计用电客户总数",
     "SELECT COUNT(*) FROM pg_tupu.public.dim_cst_elec_cons_cust", "count"),
    ("一共有多少个用电客户",
     "SELECT COUNT(*) FROM pg_tupu.public.dim_cst_elec_cons_cust", "count"),
    ("电压等级为承压名称1的用电客户有多少",
     "SELECT COUNT(*) FROM pg_tupu.public.dim_cst_elec_cons_cust WHERE voltage_name = '承压名称1'", "count"),
    ("用电客户中有多少个不同的电压等级",
     "SELECT COUNT(DISTINCT voltage_name) FROM pg_tupu.public.dim_cst_elec_cons_cust", "count"),
    # ---------- 明细 6 ----------
    ("列出用电客户清单", _sel(), "detail"),
    ("按合同容量从大到小列出用电客户", _sel(order="ctrt_cap DESC"), "detail"),
    ("合同容量最大的用电客户是谁", _sel(order="ctrt_cap DESC"), "detail"),
    ("运行容量最大的用电客户是谁", _sel(order="run_cap DESC"), "detail"),
    ("合同容量最高的用电客户", _sel(order="ctrt_cap DESC"), "detail"),
    ("列出每个用电客户的名称和电压等级", _sel(), "detail"),
    # ---------- 过滤 8 ----------
    ("电压等级为承压名称1的用电客户", _sel("voltage_name = '承压名称1'"), "filter"),
    ("重要性等级为重要性等级名称2的用电客户", _sel("impt_lv_name = '重要性等级名称2'"), "filter"),
    ("合同容量大于5000的用电客户", _sel("ctrt_cap > 5000"), "filter"),
    ("合同容量大于4000的用电客户", _sel("ctrt_cap > 4000"), "filter"),
    ("电压等级为承压名称2的用电客户", _sel("voltage_name = '承压名称2'"), "filter"),
    ("合同容量大于等于6000的用电客户", _sel("ctrt_cap >= 6000"), "filter"),
    ("合同容量小于4500的用电客户", _sel("ctrt_cap < 4500"), "filter"),
    ("重要性等级为重要性等级名称3的用电客户", _sel("impt_lv_name = '重要性等级名称3'"), "filter"),
    # ---------- 多表 JOIN 4（inst 6 列明细 = agent 实测返回形态；mock 1:1 关联无法有意义测 SQL JOIN） ----------
    ("列出安装点清单",
     "SELECT inst_id, cust_id, dist_sta_id, dist_sta_name, voltage, inst_cap" + _INST, "join"),
    ("列出各安装点所属的台区",
     "SELECT inst_id, cust_id, dist_sta_id, dist_sta_name, voltage, inst_cap" + _INST, "join"),
    ("每个安装点属于哪个用电客户", _sel(), "join"),  # agent 实测解析到客户 -> 返回客户明细
    ("各客户分布在哪些台区",
     "SELECT cust_id, dist_sta_name" + _INST, "join"),
    # ---------- 澄清 4（无 SQL；路由层歧义检测 -> route.clarification 事件即 pass） ----------
    ("客户情况", None, "clarify"),
    ("分析一下用电客户", None, "clarify"),
    ("给我看看用电客户的数据", None, "clarify"),
    ("用电客户大概是什么情况", None, "clarify"),
    # ---------- 措辞变体组 15（计数 B / 分布 A / 分布 B / TopN A / TopN B ×3） ----------
    ("用电客户一共有多少户", "SELECT COUNT(*) FROM pg_tupu.public.dim_cst_elec_cons_cust", "variant"),
    ("用电客户总数有多少", "SELECT COUNT(*) FROM pg_tupu.public.dim_cst_elec_cons_cust", "variant"),
    ("总共有多少用电客户", "SELECT COUNT(*) FROM pg_tupu.public.dim_cst_elec_cons_cust", "variant"),
    ("电压等级客户分布占比",
     "SELECT voltage_name, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY voltage_name", "variant"),
    ("按电压等级统计客户数量",
     "SELECT voltage_name, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY voltage_name", "variant"),
    ("各电压等级的客户分布",
     "SELECT voltage_name, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY voltage_name", "variant"),
    ("重要性等级的分布情况",
     "SELECT impt_lv_name, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY impt_lv_name", "variant"),
    ("按重要性等级统计客户数量",
     "SELECT impt_lv_name, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY impt_lv_name", "variant"),
    ("各重要性等级客户分布",
     "SELECT impt_lv_name, COUNT(*) AS cnt FROM pg_tupu.public.dim_cst_elec_cons_cust GROUP BY impt_lv_name", "variant"),
    ("合同容量最大的用电客户", _sel(order="ctrt_cap DESC"), "variant"),
    ("合同容量最大的客户是哪个", _sel(order="ctrt_cap DESC"), "variant"),
    ("合同容量排第一的客户", _sel(order="ctrt_cap DESC"), "variant"),
    ("运行容量最大的用电客户", _sel(order="run_cap DESC"), "variant"),
    ("运行容量最大的客户是哪个", _sel(order="run_cap DESC"), "variant"),
    ("运行容量排第一的客户", _sel(order="run_cap DESC"), "variant"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true", help="先删 scenario_tag in (s2,clarify) 再灌")
    args = ap.parse_args()
    db = SessionLocal()
    try:
        if args.clean:
            from sqlalchemy import or_
            n_g = db.query(KgGoldenQaSet).filter(
                or_(KgGoldenQaSet.scenario_tag == "s2",
                    KgGoldenQaSet.scenario_tag == "clarify")).delete(synchronize_session=False)
            # 精确删除种子金标在示例库的 golden 示例（按问题集合匹配，避免误删其他示例）
            seed_qs = [t[0] for t in GOLDENS]
            n_e = db.query(KgVerifiedQaExample).filter(
                KgVerifiedQaExample.example_type == "golden",
                KgVerifiedQaExample.question_raw.in_(seed_qs)).delete(synchronize_session=False)
            db.commit()
            print(f"[clean] 删除金标 {n_g} 条 / 示例 {n_e} 条")
        ok_n, skip_n, fail_n = 0, 0, 0
        for q, sql, tag in GOLDENS:
            exist = db.query(KgGoldenQaSet).filter(KgGoldenQaSet.question == q).first()
            if exist:
                skip_n += 1
                continue
            if tag == "clarify":
                # 澄清金标：无 SQL、不入示例库；digest 人工给（eval 走澄清口径不比对）
                from app.services.golden_qa_service import _uuid_str
                db.add(KgGoldenQaSet(
                    id=_uuid_str(), question=q[:500], expected_sql="",
                    expected_result_digest={"row_count": 0, "first_row": [], "first_row_hash": ""},
                    route_type="generic", scenario_tag="clarify", enabled=True))
                db.commit()
                ok_n += 1
                print(f"[ok] clarify  {q}")
                continue
            # scenario_tag 统一用 s2（层级细分写入 expected_sql 注释不必要，简单化）
            r = add_golden(db, question=q, expected_sql=sql,
                           route_type="generic", scenario_tag="s2", feed_example=True)
            if r.get("ok"):
                ok_n += 1
                print(f"[ok] {tag:<7} {q}  digest={r['expected_result_digest']}")
            else:
                fail_n += 1
                print(f"[FAIL] {tag:<7} {q}  {r.get('error')}")
        total = db.query(KgGoldenQaSet).count()
        print(f"\n完成：新增 {ok_n} / 跳过 {skip_n} / 失败 {fail_n}；KgGoldenQaSet 总计 {total} 条")
    finally:
        db.close()


if __name__ == "__main__":
    main()
