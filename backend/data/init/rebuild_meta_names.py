#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重跑实体元数据(补 _name 冗余列属性), 不重建PG表/不覆盖业务数据。
读现有PG表/视图列 + bom本体 -> insert_kg_metadata(清理+重插, 含 _name 字段属性)。
可重跑。跑完需同步Neo4j: POST /api/v1/sync/neo4j-all?force=true
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psycopg2
from init_distribution_ontology import OBJ_MAP, parse_bom, insert_kg_metadata, PG_CFG


def read_pg_cols():
    """从现有PG库读所有实体表/视图的列(不重建表, 不破坏数据)"""
    pg = psycopg2.connect(**PG_CFG)
    cur = pg.cursor()
    cache = {}
    for oid, (ckey, pg_table, is_main, en, cn, sys_code) in OBJ_MAP.items():
        cur.execute("""SELECT column_name, data_type FROM information_schema.columns
                       WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position""", (pg_table,))
        cache[pg_table] = [(r[0], r[1], r[0], False) for r in cur.fetchall()]
        name_cols = [c[0] for c in cache[pg_table] if c[0].endswith('_name')]
        print(f'    {pg_table}: {len(cache[pg_table])} 列, 含 _name 冗余列 {len(name_cols)} 个')
    pg.close()
    return cache


if __name__ == '__main__':
    print('=== 重建实体元数据(补 _name 属性, 不动PG业务数据) ===')
    pg_cols_cache = read_pg_cols()
    objects, props, relations = parse_bom()
    insert_kg_metadata(objects, props, relations, pg_cols_cache)
    print('\n=== 完成: 实体元数据已含 _name 冗余列属性 ===')
    print('下一步: 调用 POST http://127.0.0.1:28000/api/v1/sync/neo4j-all?force=true 同步Neo4j')
