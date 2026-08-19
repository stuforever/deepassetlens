"""添加 ES 数据源连接 + Doris es_tupu catalog 纳管

原则（与前序 init_catalog_binding.py 一致）：
- 数据源连接（kg_data_source_configs）与 Doris catalog（kg_doris_catalog）一一匹配
- ES 信息：elastic / infini_rag_flow，host docker-internal:11200（ragflow 的 ES）
- Doris es_tupu catalog 已存在（SHOW CREATE CATALOG 确认），此脚本只做"纳管"录入

可重复执行（idempotent）：已存在则跳过。
"""
import pymysql
import uuid
from datetime import datetime

MYSQL = dict(host="localhost", port=33066, user="root", password="root", database="tupu", charset="utf8mb4")

# ES 数据源连接信息
ES_DS = dict(
    name="Elasticsearch(ragflow ES)",
    db_type="elasticsearch",
    host="host.docker.internal",
    port=11200,
    database="es",  # ES 无 database 概念，填占位
    username="elastic",
    password="infini_rag_flow",
    doris_catalog_name="es_tupu",
)

# Doris es_tupu catalog 纳管信息
ES_CATALOG = dict(
    name="es_tupu",
    catalog_type="es",
    jdbc_url="http://host.docker.internal:11200",  # es catalog 用 hosts 不是 jdbc_url，但表结构用 jdbc_url 字段存
    jdbc_user="elastic",
    jdbc_password="infini_rag_flow",
    driver_class="",
    driver_url="",
)


def main():
    conn = pymysql.connect(**MYSQL)
    cur = conn.cursor()
    changed = 0

    # ---- 1. kg_data_source_configs 加 ES 数据源 ----
    print("=== 1. kg_data_source_configs 加 ES ===")
    cur.execute("SELECT id FROM kg_data_source_configs WHERE name=%s", (ES_DS["name"],))
    existing = cur.fetchone()
    if existing:
        es_ds_id = existing[0]
        print(f"  ES 数据源已存在 id={es_ds_id}，跳过")
    else:
        es_ds_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO kg_data_source_configs "
            "(id,name,db_type,host,port,`database`,username,password,is_default,enabled,doris_catalog_name,created_at,updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (es_ds_id, ES_DS["name"], ES_DS["db_type"], ES_DS["host"], ES_DS["port"],
             ES_DS["database"], ES_DS["username"], ES_DS["password"],
             0, 1, ES_DS["doris_catalog_name"], datetime.now(), datetime.now()),
        )
        print(f"  插入 ES 数据源 id={es_ds_id} ({cur.rowcount} 行)")
        changed += cur.rowcount
    conn.commit()

    # ---- 2. kg_doris_catalog 纳管 es_tupu ----
    print("=== 2. kg_doris_catalog 纳管 es_tupu ===")
    cur.execute("SELECT id FROM kg_doris_catalog WHERE name=%s", (ES_CATALOG["name"],))
    if cur.fetchone():
        print(f"  es_tupu 已纳管，跳过")
    else:
        cur.execute(
            "INSERT INTO kg_doris_catalog "
            "(id,name,catalog_type,jdbc_url,jdbc_user,jdbc_password,driver_class,driver_url,created_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (str(uuid.uuid4()), ES_CATALOG["name"], ES_CATALOG["catalog_type"],
             ES_CATALOG["jdbc_url"], ES_CATALOG["jdbc_user"], ES_CATALOG["jdbc_password"],
             ES_CATALOG["driver_class"], ES_CATALOG["driver_url"], datetime.now()),
        )
        print(f"  纳管 es_tupu catalog ({cur.rowcount} 行)")
        changed += cur.rowcount
    conn.commit()

    # ---- 验证 ----
    print("\n=== 验证: kg_data_source_configs ===")
    cur.execute("SELECT name,db_type,host,port,doris_catalog_name FROM kg_data_source_configs ORDER BY name")
    for r in cur.fetchall(): print("  ", r)
    print("\n=== 验证: kg_doris_catalog ===")
    cur.execute("SELECT name,catalog_type,jdbc_url,jdbc_user FROM kg_doris_catalog ORDER BY name")
    for r in cur.fetchall(): print("  ", r)

    print(f"\n=== 完成，共改动 {changed} 处 ===")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
