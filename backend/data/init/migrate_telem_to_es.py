# -*- coding: utf-8 -*-
"""8张量测表迁移：PG(25432) -> ES(11200) + DB配置(ApiEndpoint/EntityApiMapping/source_mode)

执行后：
- 8张量测表在 ES 中有索引+数据
- 8个 ApiEndpoint + 8个 EntityApiMapping 记录已创建
- 8个 Entity.source_mode 改为 api_integration
- vw_cust_power_ts 也转为 api_integration（DuckDB UNPIVOT）
"""
import sys, os, json, uuid, base64
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import psycopg2
import requests
from datetime import datetime
from app.core.database import SessionLocal
from app.models.base import Entity, ApiEndpoint, EntityApiMapping

# ── 配置 ──────────────────────────────────────────────
ES_HOST = "http://localhost:11200"
ES_AUTH = ("elastic", "infini_rag_flow")
ES_HEADERS = {"Content-Type": "application/json"}
ES_B64_AUTH = base64.b64encode(f"{ES_AUTH[0]}:{ES_AUTH[1]}".encode()).decode()

PG_CFG = dict(host='localhost', port=25432, user='postgres', password='postgres', dbname='tupu')

# 96点列名 v0000..v2345（每15分钟一个）
V_COLS = []
for h in range(24):
    for m in (0, 15, 30, 45):
        V_COLS.append(f"v{h:02d}{m:02d}")

# 8张表配置：表名 -> (entity_code, entity_id, 标识字段列表)
TABLES = [
    # 用户遥测组
    ("dwd_cust_analog_p",       "CustAnalogPower",       "14c7fbc8-e650-5b6e-94a7-7a2f325fe78a", ["inst_id", "equip_src_id", "measuerment_type", "date"]),
    ("dwd_cust_analog_i",       "CustAnalogCurrent",     "b0d25f3e-d911-5ec8-ba9c-77cdc606472e", ["inst_id", "equip_src_id", "measuerment_type", "date"]),
    ("dwd_cust_analog_u",       "CustAnalogVoltage",     "fa3bac27-d420-5594-921a-aa963325159b", ["inst_id", "equip_src_id", "measuerment_type", "date"]),
    ("dwd_cust_analog_f",       "CustAnalogPowerFactor",  "47c30be8-307a-57fe-b4f2-8fb1b24081b4", ["inst_id", "equip_src_id", "measuerment_type", "date"]),
    # 配网遥测组
    ("dwd_psr_d_grid_analog_p", "GridAnalogPower",       "3e435e08-4fb6-599a-a062-8d6683a6697b", ["equip_type", "psrid", "pos_code", "measuerment_type", "date"]),
    ("dwd_psr_d_grid_analog_i", "GridAnalogCurrent",     "4de07374-0744-5254-9bcc-1927b3b4a4af", ["equip_type", "psrid", "pos_code", "measuerment_type", "date"]),
    ("dwd_psr_d_grid_analog_u", "GridAnalogVoltage",     "958975ab-d0bc-5538-b812-1b1be1d9150c", ["equip_type", "psrid", "pos_code", "measuerment_type", "date"]),
    ("dwd_psr_d_grid_analog_f", "GridAnalogPowerFactor", "3766bf28-4c55-566c-a626-01a266bfa14f", ["equip_type", "psrid", "pos_code", "measuerment_type", "date"]),
]

# vw_cust_power_ts entity
VW_ENTITY_ID = "2d49c1f3-8fa3-5708-be5c-83f708b36fc1"
VW_ENTITY_CODE = "CustPowerTimeSeries"


def build_es_mapping(id_cols):
    """生成 ES mapping：标识字段 keyword + 96个 vXXXX float"""
    props = {}
    for col in id_cols:
        props[col] = {"type": "keyword"}
    for v in V_COLS:
        props[v] = {"type": "double"}
    return {"settings": {"number_of_shards": "1", "number_of_replicas": "0"},
            "mappings": {"properties": props}}


def build_columns_json(id_cols):
    """生成 ApiEndpoint.columns JSON：标识字段 + 96个 vXXXX"""
    cols = []
    for col in id_cols:
        cols.append({"name": col, "json_path": f"_source.{col}", "type": "VARCHAR"})
    for v in V_COLS:
        cols.append({"name": v, "json_path": f"_source.{v}", "type": "DOUBLE"})
    return cols


def create_es_index(index_name, mapping):
    """创建 ES 索引（已存在则先删）"""
    r = requests.delete(f"{ES_HOST}/{index_name}", auth=ES_AUTH, headers=ES_HEADERS)
    r = requests.put(f"{ES_HOST}/{index_name}", auth=ES_AUTH, headers=ES_HEADERS, json=mapping)
    if r.status_code not in (200, 201):
        print(f"  ❌ 创建索引 {index_name} 失败: {r.text[:200]}")
        return False
    print(f"  ✅ ES 索引 {index_name} 已创建")
    return True


def bulk_index_data(index_name, rows, id_cols):
    """批量灌数据到 ES"""
    if not rows:
        print(f"  ⏭️  {index_name} 无数据，跳过灌入")
        return 0
    # 构造 NDJSON bulk body
    lines = []
    for i, row in enumerate(rows):
        doc = {}
        all_cols = id_cols + V_COLS
        for j, col in enumerate(all_cols):
            val = row[j] if j < len(row) else None
            if val is not None:
                doc[col] = float(val) if col.startswith('v') and val != '' else val
        lines.append(json.dumps({"index": {"_index": index_name, "_id": str(i)}}))
        lines.append(json.dumps(doc))
    body = "\n".join(lines) + "\n"
    r = requests.post(f"{ES_HOST}/_bulk", auth=ES_AUTH,
                      headers={"Content-Type": "application/x-ndjson"}, data=body.encode('utf-8'))
    result = r.json()
    if result.get("errors"):
        errs = [item for item in result.get("items", []) if item.get("index", {}).get("error")]
        print(f"  ⚠️  {index_name} 灌入部分失败: {len(errs)} errors")
    else:
        print(f"  ✅ {index_name} 灌入 {len(rows)} 行")
    return len(rows)


def migrate_table(pg_conn, table_name, entity_code, entity_id, id_cols):
    """迁移单张表：PG -> ES"""
    index_name = f"tupu_{table_name}"
    print(f"\n=== 迁移 {table_name} ({entity_code}) ===")

    # 1. 创建 ES 索引
    mapping = build_es_mapping(id_cols)
    if not create_es_index(index_name, mapping):
        return None

    # 2. 从 PG 读数据
    cur = pg_conn.cursor()
    all_cols = id_cols + V_COLS
    col_list = ", ".join(f'"{c}"' for c in all_cols)
    cur.execute(f'SELECT {col_list} FROM "{table_name}"')
    rows = cur.fetchall()
    cur.close()
    print(f"  PG 读取 {len(rows)} 行")

    # 3. 灌入 ES
    bulk_index_data(index_name, rows, id_cols)

    return index_name


def create_db_records(db, table_name, entity_code, entity_id, id_cols, index_name):
    """创建 ApiEndpoint + EntityApiMapping + 更新 source_mode"""
    # 检查是否已存在
    existing = db.query(ApiEndpoint).filter(ApiEndpoint.table_name == table_name).first()
    if existing:
        print(f"  ⏭️  ApiEndpoint {table_name} 已存在，跳过")
        ep_id = existing.id
    else:
        ep = ApiEndpoint(
            id=str(uuid.uuid4()),
            name=f"{table_name}量测端点",
            table_name=table_name,
            entity_id=entity_id,
            api_url=f"{ES_HOST}/{index_name}/_search",
            method="POST",
            params=[],
            columns=build_columns_json(id_cols),
            data_path="hits.hits",
            headers={"Content-Type": "application/json", "Authorization": f"Basic {ES_B64_AUTH}"},
            body_template='{"query":{"match_all":{}},"size":10000}',
        )
        db.add(ep)
        db.flush()
        ep_id = ep.id
        print(f"  ✅ ApiEndpoint {table_name} -> {ep_id}")

    # EntityApiMapping
    existing_map = db.query(EntityApiMapping).filter(EntityApiMapping.entity_id == entity_id).first()
    if existing_map:
        print(f"  ⏭️  EntityApiMapping for {entity_code} 已存在，跳过")
    else:
        mapping = EntityApiMapping(
            id=str(uuid.uuid4()),
            entity_id=entity_id,
            api_endpoint_ids=[ep_id],
            field_mappings={},
            pseudo_sql=f"SELECT * FROM {table_name}",
        )
        db.add(mapping)
        print(f"  ✅ EntityApiMapping for {entity_code}")

    # 更新 source_mode
    ent = db.query(Entity).filter(Entity.id == entity_id).first()
    if ent:
        ent.source_mode = "api_integration"
        ent.integration_sql = None
        ent.doris_catalog = None
        ent.data_source_id = None
        print(f"  ✅ {entity_code} source_mode -> api_integration")


def migrate_vw_cust_power_ts(db):
    """vw_cust_power_ts 转为 api_integration：复用 dwd_cust_analog_p 端点 + DuckDB UNPIVOT"""
    print(f"\n=== 迁移 vw_cust_power_ts ({VW_ENTITY_CODE}) ===")

    # 找 dwd_cust_analog_p 的 ApiEndpoint
    ep = db.query(ApiEndpoint).filter(ApiEndpoint.table_name == "dwd_cust_analog_p").first()
    if not ep:
        print("  ❌ dwd_cust_analog_p ApiEndpoint 不存在，先迁移该表")
        return

    # pseudo_sql: DuckDB UNPIVOT 96点宽表 -> 窄表
    v_col_list = ", ".join(V_COLS)
    pseudo_sql = f"""SELECT inst_id, occur_time, power
FROM dwd_cust_analog_p
UNPIVOT (power FOR occur_time IN ({v_col_list}))"""

    # EntityApiMapping
    existing = db.query(EntityApiMapping).filter(EntityApiMapping.entity_id == VW_ENTITY_ID).first()
    if existing:
        existing.pseudo_sql = pseudo_sql
        existing.api_endpoint_ids = [ep.id]
        print(f"  ✅ 更新 EntityApiMapping pseudo_sql (UNPIVOT)")
    else:
        mapping = EntityApiMapping(
            id=str(uuid.uuid4()),
            entity_id=VW_ENTITY_ID,
            api_endpoint_ids=[ep.id],
            field_mappings={},
            pseudo_sql=pseudo_sql,
        )
        db.add(mapping)
        print(f"  ✅ 创建 EntityApiMapping (UNPIVOT)")

    # 更新 source_mode
    ent = db.query(Entity).filter(Entity.id == VW_ENTITY_ID).first()
    if ent:
        ent.source_mode = "api_integration"
        ent.integration_sql = None
        ent.doris_catalog = None
        ent.data_source_id = None
        print(f"  ✅ {VW_ENTITY_CODE} source_mode -> api_integration")


def main():
    print("=" * 60)
    print("8张量测表迁移：PG(25432) -> ES(11200) + DB配置")
    print("=" * 60)

    # 1. PG -> ES 数据迁移
    pg_conn = psycopg2.connect(**PG_CFG)
    for table_name, entity_code, entity_id, id_cols in TABLES:
        index_name = migrate_table(pg_conn, table_name, entity_code, entity_id, id_cols)
        if index_name:
            # 2. DB 配置记录
            db = SessionLocal()
            try:
                create_db_records(db, table_name, entity_code, entity_id, id_cols, index_name)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"  ❌ DB 记录失败: {e}")
            finally:
                db.close()
    pg_conn.close()

    # 3. vw_cust_power_ts 转为 api_integration
    db = SessionLocal()
    try:
        migrate_vw_cust_power_ts(db)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"  ❌ vw_cust_power_ts 迁移失败: {e}")
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("迁移完成！下一步：PG 删除8张表 + 视图，然后验证 API 调用")
    print("=" * 60)


if __name__ == "__main__":
    main()
