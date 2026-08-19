# -*- coding: utf-8 -*-
"""
来源表目录增量合并脚本
- 读取备份 CSV（主数据表/业务数据表/参考数据表导入模板）
- 读取当前库中 kg_source_*_tables
- 合并规则：备份全量（权威）+ 库中 enName 不在备份的表保留（配电重过载场景等）
- 通过 POST /api/v1/source_tables/bulk_save 提交（覆盖为合并集）
用法：python merge_source_tables.py
"""
import os
import sys
import json

import pandas as pd
import pymysql
import requests

BACKUP_DIR = r"D:\gitcangku\图谱工程导出备份\最新版本"
API = "http://127.0.0.1:28000/api/v1/source_tables/bulk_save"

DB_CFG = dict(host="localhost", port=33066, user="root", password="root", database="tupu", charset="utf8mb4")


def load_db_tables():
    conn = pymysql.connect(**DB_CFG)
    cur = conn.cursor()

    cur.execute("SELECT major, deploy, sysName, sysCode, l1, l2, enName, cnName, type FROM kg_source_master_tables")
    master = [
        {"major": r[0], "deploy": r[1], "sysName": r[2], "sysCode": r[3], "l1": r[4], "l2": r[5],
         "enName": r[6], "cnName": r[7], "type": r[8]}
        for r in cur.fetchall()
    ]

    cur.execute("SELECT major, deploy, sysName, sysCode, l3, l4, enName, cnName, type, relL1, relL2 FROM kg_source_business_tables")
    business = [
        {"major": r[0], "deploy": r[1], "sysName": r[2], "sysCode": r[3], "l3": r[4], "l4": r[5],
         "enName": r[6], "cnName": r[7], "type": r[8], "relL1": r[9], "relL2": r[10]}
        for r in cur.fetchall()
    ]

    cur.execute("SELECT major, deploy, sysName, sysCode, category, enName, cnName, type FROM kg_source_reference_tables")
    reference = [
        {"major": r[0], "deploy": r[1], "sysName": r[2], "sysCode": r[3], "category": r[4],
         "enName": r[5], "cnName": r[6], "type": r[7]}
        for r in cur.fetchall()
    ]
    conn.close()
    return master, business, reference


def load_backup():
    m = pd.read_csv(os.path.join(BACKUP_DIR, "主数据表导入模板.csv"), encoding="utf-8-sig", dtype=str)
    b = pd.read_csv(os.path.join(BACKUP_DIR, "业务数据表导入模板.csv"), encoding="utf-8-sig", dtype=str)
    r = pd.read_csv(os.path.join(BACKUP_DIR, "参考数据表导入模板.csv"), encoding="utf-8-sig", dtype=str)

    def _s(v):
        return None if pd.isna(v) or str(v).strip() == "" else str(v).strip()

    master = []
    for _, row in m.iterrows():
        master.append({
            "major": _s(row.get("专业")), "deploy": _s(row.get("部署方式")),
            "sysName": _s(row.get("系统名称")), "sysCode": _s(row.get("系统编码")),
            "l1": _s(row.get("L1-主数据")), "l2": _s(row.get("L2-主数据对象")),
            "enName": _s(row.get("来源表英文名")), "cnName": _s(row.get("来源表中文名")),
            "type": _s(row.get("表类型")) or "主数据",
        })

    business = []
    for _, row in b.iterrows():
        business.append({
            "major": _s(row.get("专业")), "deploy": _s(row.get("部署方式")),
            "sysName": _s(row.get("系统名称")), "sysCode": _s(row.get("系统编码")),
            "l3": _s(row.get("L3-业务模块")), "l4": _s(row.get("L4-业务活动对象")),
            "enName": _s(row.get("来源表英文名")), "cnName": _s(row.get("来源表中文名")),
            "type": _s(row.get("表类型")) or "业务表",
            "relL1": _s(row.get("关联主数据大类")), "relL2": _s(row.get("关联主数据小类")),
        })

    reference = []
    for _, row in r.iterrows():
        reference.append({
            "major": _s(row.get("专业")), "deploy": _s(row.get("部署方式")),
            "sysName": _s(row.get("系统名称")), "sysCode": _s(row.get("系统编码")),
            "category": _s(row.get("参考数据分类")),
            "enName": _s(row.get("来源表英文名")), "cnName": _s(row.get("来源表中文名")),
            "type": _s(row.get("表类型")) or "参考数据表",
        })
    return master, business, reference


def merge(db_rows, backup_rows, en_col="enName"):
    """备份全量 + 库中 enName 不在备份的保留。返回 (合并结果, 保留的库中独有数)"""
    backup_names = {r[en_col] for r in backup_rows if r.get(en_col)}
    kept = [r for r in db_rows if r.get(en_col) and r[en_col] not in backup_names]
    return backup_rows + kept, len(kept)


def main():
    print("读取当前库中来源表...")
    db_m, db_b, db_r = load_db_tables()
    print(f"  库中: master={len(db_m)} business={len(db_b)} reference={len(db_r)}")

    print("读取备份 CSV...")
    bk_m, bk_b, bk_r = load_backup()
    print(f"  备份: master={len(bk_m)} business={len(bk_b)} reference={len(bk_r)}")

    m_merged, m_kept = merge(db_m, bk_m)
    b_merged, b_kept = merge(db_b, bk_b)
    r_merged, r_kept = merge(db_r, bk_r)
    print(f"合并: master={len(m_merged)} (保留库中独有 {m_kept}) | "
          f"business={len(b_merged)} (保留 {b_kept}) | reference={len(r_merged)} (保留 {r_kept})")

    payload = {"master_data": m_merged, "business_data": b_merged, "reference_data": r_merged}
    with open("merged_source_tables.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    print("合并结果已写入 merged_source_tables.json")

    resp = requests.post(API, json=payload, timeout=300)
    print("POST", resp.status_code)
    print(resp.text[:500])
    if resp.status_code != 200:
        sys.exit(1)


if __name__ == "__main__":
    main()
