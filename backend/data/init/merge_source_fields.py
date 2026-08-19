# -*- coding: utf-8 -*-
"""
表字段目录增量合并脚本
- 读取备份 CSV（表字段导入模板，21 列）
- 读取当前库中 kg_source_field_imports
- 合并规则：备份全量（权威）+ 库中 (table_en, field_en) 不在备份的字段保留（配电场景字段）
- 输出合并 CSV（模板格式）→ POST /api/v1/source_fields/import?clear_existing=true
用法：python merge_source_fields.py
"""
import os
import sys

import pandas as pd
import pymysql
import requests

BACKUP_DIR = r"D:\gitcangku\图谱工程导出备份\最新版本"
BACKUP_CSV = os.path.join(BACKUP_DIR, "表字段导入模板.csv")
API = "http://127.0.0.1:28000/api/v1/source_fields/import"

DB_CFG = dict(host="localhost", port=33066, user="root", password="root", database="tupu", charset="utf8mb4")

# 模板 21 列（upload.py 按位置解析）
COLUMNS = [
    "序号", "来源表中文名", "来源表英文名", "来源系统编码", "库表定义",
    "来源字段中文名称", "来源字段英文名称", "字段描述", "数据类型", "长度/精度",
    "小数位", "主/外键", "是否参考数据", "参考数据引用说明", "参考数据调用说明",
    "是否建历史表", "修改状态", "修改时间", "变更原因", "应用范围",
]


def _s(v):
    if v is None:
        return ""
    s = str(v).strip()
    if s in ("", "nan", "None", "NaN"):
        return ""
    return s


def load_db_fields():
    conn = pymysql.connect(**DB_CFG)
    cur = conn.cursor()
    cur.execute("SELECT seq_no, table_cn, table_en, sys_code, table_def, field_cn, field_en, "
                "field_desc, data_type, length_precision, scale, pk_fk, is_ref_data, ref_data_desc, "
                "ref_table_en, ref_data_usage_desc, is_history, mod_status, mod_time, mod_reason, app_scope "
                "FROM kg_source_field_imports")
    rows = cur.fetchall()
    conn.close()
    return rows


def load_backup():
    df = pd.read_csv(BACKUP_CSV, encoding="utf-8-sig", dtype=str)
    df = df.fillna("")
    # 清洗：来源表英文名/字段英文名缺失的行丢弃
    df = df[df["来源表英文名"].str.strip().ne("") & df["来源字段英文名称"].str.strip().ne("")]
    return df


def main():
    print("读取当前库中字段...")
    db_rows = load_db_fields()
    print(f"  库中: {len(db_rows)} 条")

    print("读取备份字段 CSV...")
    bk = load_backup()
    print(f"  备份: {len(bk)} 条（清洗后）")

    # 备份键集合
    bk_keys = set(zip(bk["来源表英文名"].str.strip(), bk["来源字段英文名称"].str.strip()))
    kept = []
    for r in db_rows:
        seq_no, table_cn, table_en, sys_code, table_def, field_cn, field_en, field_desc, data_type, \
            length_precision, scale, pk_fk, is_ref_data, ref_data_desc, ref_table_en, \
            ref_data_usage_desc, is_history, mod_status, mod_time, mod_reason, app_scope = r
        key = (_s(table_en), _s(field_en))
        if key not in bk_keys:
            kept.append({
                "来源表中文名": _s(table_cn), "来源表英文名": _s(table_en),
                "来源系统编码": _s(sys_code), "库表定义": _s(table_def),
                "来源字段中文名称": _s(field_cn), "来源字段英文名称": _s(field_en),
                "字段描述": _s(field_desc), "数据类型": _s(data_type),
                "长度/精度": _s(length_precision), "小数位": _s(scale),
                "主/外键": _s(pk_fk), "是否参考数据": _s(is_ref_data),
                # upload.py 列映射（模板列索引→DB列）：13→ref_data_desc, 14→ref_table_en,
                # 15→ref_data_usage_desc, 16→is_history, 17→mod_status, 18→mod_time,
                # 19→mod_reason, 20→app_scope（模板仅20列，app_scope 上传后恒为 None）
                # 故 kept 行逆映射：引用说明←ref_data_desc, 调用说明←ref_table_en,
                # 建历史表←ref_data_usage_desc, 修改状态←is_history, 修改时间←mod_status,
                # 变更原因←mod_time, 应用范围←mod_reason
                "参考数据引用说明": _s(ref_data_desc), "参考数据调用说明": _s(ref_table_en),
                "是否建历史表": _s(ref_data_usage_desc), "修改状态": _s(is_history),
                "修改时间": _s(mod_status), "变更原因": _s(mod_time),
                "应用范围": _s(mod_reason),
            })
    print(f"库中独有保留: {len(kept)} 条")

    # 合并：备份全量 + 库中独有
    merged = bk[[c for c in COLUMNS if c != "序号"]].copy()
    if kept:
        kept_df = pd.DataFrame(kept)
        merged = pd.concat([merged, kept_df], ignore_index=True)
    # 重新生成序号
    merged.insert(0, "序号", [str(i + 1) for i in range(len(merged))])

    out_csv = "merged_source_fields.csv"
    merged.to_csv(out_csv, index=False, encoding="utf-8-sig")
    print(f"合并结果: {len(merged)} 条 -> {out_csv}")

    with open(out_csv, "rb") as f:
        resp = requests.post(
            API,
            data={"clear_existing": "true"},
            files={"file": ("merged_source_fields.csv", f, "text/csv")},
            timeout=600,
        )
    print("POST", resp.status_code)
    print(resp.text[:500])
    if resp.status_code != 200:
        sys.exit(1)


if __name__ == "__main__":
    main()
