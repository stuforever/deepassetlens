"""一次性数据修正：PG 为唯一业务库 + Doris pg_tupu 统一联邦

原则：
- PG(tupu_pg 25432) = 唯一业务库，物理表 + sql_integration 数据都在 PG
- MySQL(33066) = 系统运行库，只存 kg_* 配置表，不存业务数据
- Doris pg_tupu catalog = 统一联邦层，PG 业务表通过 pg_tupu.public.表名 访问

修正内容：
1. kg_data_source_configs: PG 行补 doris_catalog_name='pg_tupu'；删除 MySQL 行
2. kg_doris_catalog: 录入 pg_tupu 元数据（纳管）
3. kg_entities: physical_table + sql_integration 绑 doris_catalog='pg_tupu' + data_source_id=PG

可重复执行（idempotent）：UPERT 语义，已存在则跳过/更新。
"""
import pymysql
import uuid
from datetime import datetime

MYSQL = dict(host="localhost", port=33066, user="root", password="root", database="tupu", charset="utf8mb4")
PG_DS_ID = "91a87134-85ad-4e37-9846-023e969f9b77"  # PostgreSQL(tupu业务库) 的 id
DORIS_CATALOG = "pg_tupu"
MYSQL_DS_ID = "094339e4-d94b-4cab-b23d-f2ce481d2638"  # tupu数据库(MySQL) 的 id，要删

# physical_table 实体（entity_en_name），这些表在 PG public schema 下
PHYSICAL_TABLES = [
    "cms20_cst_cust", "cms20_inst_elec_cons", "cms20_dist_sta",
    "cms20_adj_volt_dev", "cms20_adj_volt_dev_asset", "vw_transformer",
    "dwd_cst_gpc", "dwd_cst_it_run", "dwd_grid_psr_ds_feeder",
    "cms20_cst_meter_run",
    # dim_ps_network_component 跳过：该表在 PG 里不存在（遗留错误配置）
]
SQL_INTEGRATION_TABLES = ["cms20_elec_cons_cust", "dim_ps_wbs_cost"]


def main():
    conn = pymysql.connect(**MYSQL)
    cur = conn.cursor()
    changed = 0

    # ---- 1a. kg_data_source_configs ----
    print("=== 1a. kg_data_source_configs ===")
    # PG 行补 doris_catalog_name
    cur.execute(
        "UPDATE kg_data_source_configs SET doris_catalog_name=%s WHERE id=%s",
        (DORIS_CATALOG, PG_DS_ID),
    )
    if cur.rowcount:
        print(f"  PG 行 doris_catalog_name -> '{DORIS_CATALOG}' ({cur.rowcount} 行)")
        changed += cur.rowcount
    else:
        print(f"  PG 行 doris_catalog_name 已是 '{DORIS_CATALOG}'，跳过")
    # 删除 MySQL 行
    cur.execute("SELECT name FROM kg_data_source_configs WHERE id=%s", (MYSQL_DS_ID,))
    if cur.fetchone():
        cur.execute("DELETE FROM kg_data_source_configs WHERE id=%s", (MYSQL_DS_ID,))
        print(f"  删除 MySQL 数据源行 '{MYSQL_DS_ID}' ({cur.rowcount} 行)")
        changed += cur.rowcount
    else:
        print(f"  MySQL 数据源行已不存在，跳过")
    # 检查是否有实体还绑着 MySQL data_source_id（安全检查）
    cur.execute("SELECT entity_code FROM kg_entities WHERE data_source_id=%s", (MYSQL_DS_ID,))
    orphans = cur.fetchall()
    if orphans:
        print(f"  ⚠️ 仍有 {len(orphans)} 个实体绑着 MySQL 数据源，需手动处理: {[r[0] for r in orphans]}")
    conn.commit()

    # ---- 1b. kg_doris_catalog 录入 pg_tupu ----
    print("=== 1b. kg_doris_catalog ===")
    cur.execute("SELECT id FROM kg_doris_catalog WHERE name=%s", (DORIS_CATALOG,))
    if cur.fetchone():
        print(f"  pg_tupu 已存在，跳过")
    else:
        cur.execute(
            "INSERT INTO kg_doris_catalog (id,name,catalog_type,jdbc_url,jdbc_user,jdbc_password,driver_class,driver_url,created_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (str(uuid.uuid4()), DORIS_CATALOG, "jdbc",
             "jdbc:postgresql://host.docker.internal:25432/tupu?reWriteBatchedInserts=true",
             "postgres", "postgres", "org.postgresql.Driver",
             "postgresql-42.7.3.jar", datetime.now()),
        )
        print(f"  录入 pg_tupu catalog 元数据 ({cur.rowcount} 行)")
        changed += cur.rowcount
    conn.commit()

    # ---- 1c. kg_entities 绑 catalog + data_source_id ----
    print("=== 1c. kg_entities ===")
    # physical_table：绑 data_source_id=PG + doris_catalog=pg_tupu
    ph_placeholders = ",".join(["%s"] * len(PHYSICAL_TABLES))
    cur.execute(
        f"UPDATE kg_entities SET data_source_id=%s, doris_catalog=%s "
        f"WHERE entity_en_name IN ({ph_placeholders}) AND source_mode='physical_table'",
        [PG_DS_ID, DORIS_CATALOG] + PHYSICAL_TABLES,
    )
    print(f"  physical_table 绑 catalog ({cur.rowcount} 行): {PHYSICAL_TABLES}")
    changed += cur.rowcount
    # sql_integration：补 doris_catalog
    si_placeholders = ",".join(["%s"] * len(SQL_INTEGRATION_TABLES))
    cur.execute(
        f"UPDATE kg_entities SET doris_catalog=%s "
        f"WHERE entity_en_name IN ({si_placeholders}) AND source_mode='sql_integration'",
        [DORIS_CATALOG] + SQL_INTEGRATION_TABLES,
    )
    print(f"  sql_integration 补 catalog ({cur.rowcount} 行): {SQL_INTEGRATION_TABLES}")
    changed += cur.rowcount
    conn.commit()

    # ---- 验证 ----
    print("\n=== 验证: kg_entities 绑定情况 ===")
    cur.execute(
        "SELECT source_mode, count(*), count(doris_catalog), count(data_source_id) "
        "FROM kg_entities GROUP BY source_mode ORDER BY 2 DESC"
    )
    print("  source_mode | 总数 | 已填catalog | 已绑data_source")
    for r in cur.fetchall():
        print(f"  {r[0] or '(空)':20s} | {r[1]:3d} | {r[2]:3d} | {r[3]:3d}")
    cur.execute(
        "SELECT entity_code, entity_en_name, source_mode, doris_catalog, data_source_id "
        "FROM kg_entities WHERE source_mode IN ('physical_table','sql_integration') ORDER BY source_mode, entity_en_name"
    )
    print("\n  实体明细:")
    for r in cur.fetchall():
        flag = "✅" if r[3] == DORIS_CATALOG else "❌"
        print(f"  {flag} {r[1]:30s} {r[2]:16s} catalog={r[3]!r:10s} ds={str(r[4])[:8] if r[4] else None}")

    print(f"\n=== 完成，共改动 {changed} 处 ===")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
