#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配电重过载本体导入脚本（DeepAssetLens）
- PostgreSQL(25432/tupu): sim_*业务表(规范名) + 柱上样例 + 空表 + 遥测表 + vw_transformer视图
- MySQL(33066/tupu): kg_*元数据(concepts/entities/concept_links/relations/source/field/mapping)

可重跑：所有ID用确定性uuid5/bom原ID，先清理后插入。
"""
import pymysql, psycopg2, json, uuid, re, sys

# === 配置 ===
MYSQL_CFG = dict(host='localhost', port=33066, user='root', password='root', database='tupu', charset='utf8mb4')
MYSQL_TMP = dict(host='localhost', port=33066, user='root', password='root', database='tupu_sim_tmp', charset='utf8mb4')
PG_CFG = dict(host='localhost', port=25432, user='postgres', password='postgres', dbname='tupu')
BOM_SQL = r'D:/gitcangku/benti/deploy2/export_ontology_schema_data.sql'
SIM_SQL = r'D:/gitcangku/benti/deploy2/export_feeder_overload_sample_data.sql'
NS = uuid.uuid5(uuid.NAMESPACE_DNS, 'tupu_distribution')

def u5(key):
    return str(uuid.uuid5(NS, key))

# === 概念层级 ===
# 主数据链：无业务域，L1为根(parent=NULL)；业务活动链：有业务域L0->L3->L4
# (key, name, level, parent_key, area_index, sort_order)
CONCEPTS = [
    # === 主数据链（无业务域，L1为根）===
    ('cust', '客户', 1, None, 4, 1),
    ('cust_elec', '用电户', 2, 'cust', 4, 1),
    ('cust_gen', '发电户', 2, 'cust', 4, 2),
    ('cust_ecust', '能源客户', 2, 'cust', 4, 3),
    ('cust_sta', '台区', 2, 'cust', 4, 4),
    ('cust_meter', '计量点', 2, 'cust', 4, 5),
    ('dev', '设备', 1, None, 3, 1),
    ('dist_dev', '配电设备', 2, 'dev', 3, 1),
    ('user_dev', '用户设备', 2, 'dev', 3, 2),
    # === 业务活动链（有业务域L0）===
    ('grid_domain', '电网域', 0, None, 3, 1),
    ('cust_domain', '客户域', 0, None, 4, 2),
    ('main_run', '主网运行', 3, 'grid_domain', 3, 1),
    ('dist_run', '配网运行', 3, 'grid_domain', 3, 2),
    ('cust_run', '客户侧设备运行', 3, 'cust_domain', 4, 1),
    # L4 业务实体（每个L3下：遥测/遥信/事件/电能量）
    ('main_telem', '遥测', 4, 'main_run', 3, 1),
    ('main_sign', '遥信', 4, 'main_run', 3, 2),
    ('main_event', '事件', 4, 'main_run', 3, 3),
    ('main_energy', '电能量', 4, 'main_run', 3, 4),
    ('dist_telem', '遥测', 4, 'dist_run', 3, 1),
    ('dist_sign', '遥信', 4, 'dist_run', 3, 2),
    ('dist_event', '事件', 4, 'dist_run', 3, 3),
    ('dist_energy', '电能量', 4, 'dist_run', 3, 4),
    ('cust_telem', '遥测', 4, 'cust_run', 4, 1),
    ('cust_sign', '遥信', 4, 'cust_run', 4, 2),
    ('cust_event', '事件', 4, 'cust_run', 4, 3),
    ('cust_energy', '电能量', 4, 'cust_run', 4, 4),
]
CONCEPT_MAP = {c[0]: c for c in CONCEPTS}

def concept_path(ckey):
    """返回 (domain_name, l1, l2, l3, l4) 沿父链上溯"""
    k = ckey; l1 = l2 = l3 = l4 = None; domain = None
    while k:
        c = CONCEPT_MAP[k]
        if c[2] == 0: domain = c[1]
        elif c[2] == 1: l1 = c[1]
        elif c[2] == 2: l2 = c[1]
        elif c[2] == 3: l3 = c[1]
        elif c[2] == 4: l4 = c[1]
        k = c[3]
    return domain, l1, l2, l3, l4

# === 对象 bom_object_id -> (concept_key, pg_table, is_main, en_name, cn_name, sys_code) ===
# entity_id 直接用 bom_object_id（确定性）
OBJ_MAP = {
    # 客户(L1) 下 5 个 L2，每个 L2 对应 1 个实体（主数据无业务域）
    'd13ff82a-9ebd-5e76-b137-2e4e3774638d': ('cust_ecust', 'cms20_cst_cust', True, 'EnergyCustomer', '能源客户', 'YX'),
    '2b4b2adf-a605-57d5-b44d-89d613e00fb5': ('cust_elec', 'cms20_elec_cons_cust', True, 'ElectricityConsumer', '用电户', 'YX'),
    '5f83a695-966f-599c-836b-4761e2cc674b': ('cust_gen', 'dwd_cst_gpc', True, 'GenerationCustomer', '发电户', 'YX'),
    'e3af9638-1d7b-5e37-a7bb-a8c6293293d2': ('cust_sta', 'cms20_dist_sta', True, 'DistributionStation', '台区', 'YX'),
    'c3d13b6d-cc47-5072-8b9a-4b13e99793d8': ('cust_meter', 'cms20_inst_elec_cons', True, 'MeteringPoint', '计量点', 'YX'),
    # 电网域 / 设备(L1) / 配电设备(L2) - 4个实体
    'bc012786-acf1-5c96-9398-f0bde5b58de1': ('dist_dev', 'vw_transformer', True, 'DistributionTransformer', '配电变压器', 'DWZYYWZT'),
    '1e742fc3-7d4f-57c6-b9c4-0eeb74dc50ec': ('dist_dev', 'dwd_grid_psr_ds_feeder', True, 'Feeder', '馈线', 'DWZYYWZT'),
    '49ee39c1-fa58-5688-971d-1c7a00aa3a1c': ('dist_dev', 'cms20_adj_volt_dev_asset', True, 'AdjVoltDevAsset', '调压设备资产', 'YX'),
    'c420aafb-edf8-5c9a-ab37-bfcc5f20b5eb': ('dist_dev', 'cms20_adj_volt_dev', True, 'AdjVoltDev', '调压设备', 'YX'),
    # 电网域 / 设备(L1) / 用户设备(L2) - 2个实体
    '2da597bc-a033-52e9-9b84-a6d0b060c9c6': ('user_dev', 'dwd_cst_it_run', True, 'InstrumentTransformer', '互感器', 'YX'),
    'b7cbc2ab-9c27-59bb-8030-69cb9ec6d812': ('user_dev', 'cms20_cst_meter_run', True, 'MeterRun', '计量表计', 'YX'),
    # 电网域 / 配网运行(L3) / 遥测(L4) - 4个配网遥测实体
    '3e435e08-4fb6-599a-a062-8d6683a6697b': ('dist_telem', 'dwd_psr_d_grid_analog_p', False, 'GridAnalogPower', '配网遥测功率', 'DWZYYWZT'),
    '4de07374-0744-5254-9bcc-1927b3b4a4af': ('dist_telem', 'dwd_psr_d_grid_analog_i', False, 'GridAnalogCurrent', '配网遥测电流', 'DWZYYWZT'),
    '958975ab-d0bc-5538-b812-1b1be1d9150c': ('dist_telem', 'dwd_psr_d_grid_analog_u', False, 'GridAnalogVoltage', '配网遥测电压', 'DWZYYWZT'),
    '3766bf28-4c55-566c-a626-01a266bfa14f': ('dist_telem', 'dwd_psr_d_grid_analog_f', False, 'GridAnalogPowerFactor', '配网遥测功率因数', 'DWZYYWZT'),
    # 客户域 / 客户侧设备运行(L3) / 遥测(L4) - 4个用户遥测实体
    '14c7fbc8-e650-5b6e-94a7-7a2f325fe78a': ('cust_telem', 'dwd_cust_analog_p', False, 'CustAnalogPower', '用户遥测功率', 'YX'),
    'b0d25f3e-d911-5ec8-ba9c-77cdc606472e': ('cust_telem', 'dwd_cust_analog_i', False, 'CustAnalogCurrent', '用户遥测电流', 'YX'),
    'fa3bac27-d420-5594-921a-aa963325159b': ('cust_telem', 'dwd_cust_analog_u', False, 'CustAnalogVoltage', '用户遥测电压', 'YX'),
    '47c30be8-307a-57fe-b4f2-8fb1b24081b4': ('cust_telem', 'dwd_cust_analog_f', False, 'CustAnalogPowerFactor', '用户遥测功率因数', 'YX'),
}

# bom 未定义但 PG 实际有的列(视图字段/gen_x10 后加的关联键), 需补注册到实体元数据
# (pg_table, [(col_en, col_cn, data_type)])
_EXTRA_FIELDS = {
    'vw_transformer': [('transformer_type', '变压器类型', 'string')],
    'cms20_inst_elec_cons': [('gpc_id', '发电户号', 'bigint'), ('elec_cons_cust_id', '用电户号', 'bigint')],
}

# sim表 -> PG规范名
SIM_TO_PG = {
    'sim_dwd_grid_psr_ds_transformer': 'dwd_grid_psr_ds_transformer',
    'sim_cms20_adj_volt_dev_asset': 'cms20_adj_volt_dev_asset',
    'sim_cms20_adj_volt_dev': 'cms20_adj_volt_dev',
    'sim_cms20_inst_elec_cons': 'cms20_inst_elec_cons',
    'sim_cms20_cst_meter_run': 'cms20_cst_meter_run',
    'sim_cms20_cst_cust': 'cms20_cst_cust',
    'sim_cms20_elec_cons_cust': 'cms20_elec_cons_cust',
    'sim_dwd_cst_gpc': 'dwd_cst_gpc',
    'sim_dwd_cust_analog_p': 'dwd_cust_analog_p',
}

# 96点列名 v0000..v2345
V96 = []
for i in range(96):
    tm = i * 15
    V96.append(f"v{tm // 60:02d}{tm % 60:02d}")

# ===================================================================
# 1. 导入 sim dump 到临时 MySQL 库
# ===================================================================
def import_sim_to_tmp():
    print('[1] 导入 sim dump 到临时 MySQL 库 tupu_sim_tmp ...')
    src = open(SIM_SQL, encoding='utf-8').read()
    src = re.sub(r'LOCK TABLES.*?;', '', src)
    src = re.sub(r'UNLOCK TABLES.*?;', '', src)
    src = re.sub(r'/\*!.*?\*/;', '', src, flags=re.S)
    src = re.sub(r'SET [^;]*;', '', src)
    src = re.sub(r'^--.*$', '', src, flags=re.M)
    stmts = [s.strip() for s in src.split(';\n')
             if s.strip() and (s.strip().upper().startswith('CREATE TABLE') or s.strip().upper().startswith('INSERT INTO'))]
    c = pymysql.connect(**{k: v for k, v in MYSQL_CFG.items() if k != 'database'})
    cur = c.cursor()
    cur.execute('DROP DATABASE IF EXISTS tupu_sim_tmp')
    cur.execute('CREATE DATABASE tupu_sim_tmp DEFAULT CHARSET utf8mb4')
    c.close()
    c = pymysql.connect(**MYSQL_TMP)
    cur = c.cursor()
    for s in stmts:
        cur.execute(s)
    c.commit()
    cur.execute('SHOW TABLES')
    tables = [r[0] for r in cur.fetchall()]
    print(f'    临时库表: {len(tables)} 张')
    c.close()
    return list(SIM_TO_PG.keys())

def read_mysql_table(table):
    """读 MySQL 表的列定义和数据行"""
    c = pymysql.connect(**MYSQL_TMP)
    cur = c.cursor(pymysql.cursors.DictCursor)
    cur.execute("""SELECT COLUMN_NAME,DATA_TYPE,CHARACTER_MAXIMUM_LENGTH,NUMERIC_PRECISION,NUMERIC_SCALE,
                   COLUMN_COMMENT,COLUMN_KEY,IS_NULLABLE FROM information_schema.COLUMNS
                   WHERE TABLE_SCHEMA='tupu_sim_tmp' AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION""", (table,))
    cols = cur.fetchall()
    cur.execute(f"SELECT * FROM `{table}`")
    rows = cur.fetchall()
    c.close()
    return cols, rows

def mysql_type_to_pg(col):
    t = col['DATA_TYPE']
    if t in ('bigint', 'int', 'tinyint', 'smallint'):
        return 'BIGINT' if t == 'bigint' else 'INTEGER'
    if t == 'varchar':
        return f"VARCHAR({col['CHARACTER_MAXIMUM_LENGTH'] or 255})"
    if t == 'decimal':
        return f"NUMERIC({col['NUMERIC_PRECISION']},{col['NUMERIC_SCALE']})"
    if t == 'text':
        return 'TEXT'
    if t == 'datetime':
        return 'TIMESTAMP'
    if t == 'char':
        return f"CHAR({col['CHARACTER_MAXIMUM_LENGTH'] or 36})"
    return 'TEXT'

# ===================================================================
# 2. PG 建表 + 数据 + 视图
# ===================================================================
def telem_cols_user():
    cols = [('inst_id', 'VARCHAR(64)', False), ('equip_src_id', 'VARCHAR(64)', False),
            ('measuerment_type', 'VARCHAR(30)', False), ('date', 'VARCHAR(20)', False)]
    cols += [(v, 'NUMERIC(18,4)', False) for v in V96]
    return cols

def telem_cols_grid():
    cols = [('equip_type', 'VARCHAR(20)', False), ('psrid', 'VARCHAR(64)', False),
            ('pos_code', 'VARCHAR(20)', False), ('measuerment_type', 'VARCHAR(30)', False),
            ('date', 'VARCHAR(20)', False)]
    cols += [(v, 'NUMERIC(18,4)', False) for v in V96]
    return cols

# 显式列定义：(col_name, pg_type, is_pk)
EMPTY_TABLES = {
    'dwd_grid_psr_ds_feeder': [('psrid', 'VARCHAR(64)', True), ('astid', 'VARCHAR(64)', False),
        ('linename', 'VARCHAR(200)', False), ('capacity', 'NUMERIC(18,4)', False),
        ('voltagelevel', 'VARCHAR(20)', False), ('pubprivflag', 'VARCHAR(10)', False), ('runstate', 'VARCHAR(10)', False),
        ('voltagelevel_name', 'VARCHAR(50)', False), ('pubprivflag_name', 'VARCHAR(50)', False), ('runstate_name', 'VARCHAR(50)', False)],
    'dwd_cst_it_run': [('it_id', 'BIGINT', True), ('categ', 'VARCHAR(20)', False),
        ('meter_spcl_flag', 'VARCHAR(20)', False), ('phase', 'VARCHAR(20)', False),
        ('categ_name', 'VARCHAR(50)', False), ('meter_spcl_flag_name', 'VARCHAR(50)', False), ('phase_name', 'VARCHAR(50)', False),
        ('cur_rto', 'VARCHAR(50)', False), ('usage_cur_tr', 'VARCHAR(50)', False), ('inst_id', 'BIGINT', False)],
    'cms20_dist_sta': [('dist_sta_id', 'BIGINT', True), ('pub_clg_flag', 'VARCHAR(10)', False),
        ('resrc_supl_name', 'VARCHAR(200)', False), ('resrc_supl_stat', 'VARCHAR(20)', False)],
}
TELEM_TABLES = {
    'dwd_cust_analog_p': telem_cols_user(), 'dwd_cust_analog_i': telem_cols_user(),
    'dwd_cust_analog_u': telem_cols_user(), 'dwd_cust_analog_f': telem_cols_user(),
    'dwd_psr_d_grid_analog_p': telem_cols_grid(), 'dwd_psr_d_grid_analog_i': telem_cols_grid(),
    'dwd_psr_d_grid_analog_u': telem_cols_grid(), 'dwd_psr_d_grid_analog_f': telem_cols_grid(),
}

def build_pg():
    print('[2] PG 建表 + 数据 + 视图 ...')
    pg = psycopg2.connect(**PG_CFG)
    pg.autocommit = True
    cur = pg.cursor()
    cur.execute('DROP VIEW IF EXISTS vw_transformer')
    pg_cols_cache = {}  # pg_table -> [(col_name, pg_type, comment, is_pk)]

    # 2a. 9张样本表（从 sim 转 PG）
    for sim_t, pg_t in SIM_TO_PG.items():
        cols, rows = read_mysql_table(sim_t)
        coldefs = []
        pg_cols = []
        for col in cols:
            pgtype = mysql_type_to_pg(col)
            pk = ' PRIMARY KEY' if col['COLUMN_KEY'] == 'PRI' else ''
            coldefs.append(f'"{col["COLUMN_NAME"]}" {pgtype}{pk}')
            pg_cols.append((col['COLUMN_NAME'], pgtype, col['COLUMN_COMMENT'], col['COLUMN_KEY'] == 'PRI'))
        cur.execute(f'DROP TABLE IF EXISTS "{pg_t}"')
        cur.execute(f'CREATE TABLE "{pg_t}" ({", ".join(coldefs)})')
        if rows:
            colnames = [c['COLUMN_NAME'] for c in cols]
            collist = ",".join(f'"{n}"' for n in colnames)
            placeholders = ",".join(["%s"] * len(colnames))
            for r in rows:
                cur.execute(f'INSERT INTO "{pg_t}" ({collist}) VALUES ({placeholders})', [r[n] for n in colnames])
        pg_cols_cache[pg_t] = pg_cols
        print(f'    {pg_t}: {len(rows)}行 ({len(cols)}列)')

    # 2b. 柱上变压器表（补样例20行，与非柱上同构）
    pg_t = 'dwd_grid_psr_ds_p_transformer'
    pole_cols = pg_cols_cache['dwd_grid_psr_ds_transformer']
    colnames = [c[0] for c in pole_cols]
    collist = ",".join(f'"{n}"' for n in colnames)
    placeholders = ",".join(["%s"] * len(colnames))
    coldefs = ", ".join(f'"{c[0]}" {c[1]}{" PRIMARY KEY" if c[3] else ""}' for c in pole_cols)
    cur.execute(f'DROP TABLE IF EXISTS "{pg_t}"')
    cur.execute(f'CREATE TABLE "{pg_t}" ({coldefs})')
    cur.execute(f'SELECT {collist} FROM dwd_grid_psr_ds_transformer LIMIT 20')
    base_rows = cur.fetchall()
    for i, r in enumerate(base_rows, 1):
        rd = dict(zip(colnames, r))
        rd['psrid'] = f'pole-psrid-{i:04d}'
        rd['astid'] = f'pole-astid-{i:04d}'
        rd['equipname'] = f'柱上变压器{i:03d}'
        cur.execute(f'INSERT INTO "{pg_t}" ({collist}) VALUES ({placeholders})', [rd[n] for n in colnames])
    pg_cols_cache[pg_t] = pole_cols
    print(f'    {pg_t}: 20行(柱上样例)')

    # 2c. 3张空表
    for pg_t, cols in EMPTY_TABLES.items():
        coldefs = ", ".join(f'"{nm}" {ty}{" PRIMARY KEY" if pk else ""}' for nm, ty, pk in cols)
        cur.execute(f'DROP TABLE IF EXISTS "{pg_t}"')
        cur.execute(f'CREATE TABLE "{pg_t}" ({coldefs})')
        pg_cols_cache[pg_t] = [(nm, ty, nm, pk) for nm, ty, pk in cols]
        print(f'    {pg_t}: 0行(空表)')

    # 2d. 8张遥测表（仅 dwd_cust_analog_p 有数据）
    for pg_t, cols in TELEM_TABLES.items():
        coldefs = ", ".join(f'"{nm}" {ty}' for nm, ty, pk in cols)
        cur.execute(f'DROP TABLE IF EXISTS "{pg_t}"')
        cur.execute(f'CREATE TABLE "{pg_t}" ({coldefs})')
        pg_cols_cache[pg_t] = [(nm, ty, nm, pk) for nm, ty, pk in cols]
    cols, rows = read_mysql_table('sim_dwd_cust_analog_p')
    target_cols = ['inst_id', 'equip_src_id', 'measuerment_type', 'date'] + V96
    collist = ",".join(f'"{n}"' for n in target_cols)
    placeholders = ",".join(["%s"] * len(target_cols))
    for r in rows:
        cur.execute(f'INSERT INTO dwd_cust_analog_p ({collist}) VALUES ({placeholders})', [r.get(n) for n in target_cols])
    print(f'    dwd_cust_analog_p: {len(rows)}行(从sim拷贝)')
    print(f'    其余7张遥测表: 0行(空表)')

    # 2e. vw_transformer 视图（柱上+非柱上合并）
    tcols = [c[0] for c in pg_cols_cache['dwd_grid_psr_ds_transformer']]
    sel = ",".join(f'"{c}"' for c in tcols)
    cur.execute(f'''CREATE VIEW vw_transformer AS
        SELECT {sel}, '柱上变压器'::VARCHAR AS transformer_type FROM dwd_grid_psr_ds_p_transformer
        UNION ALL
        SELECT {sel}, '非柱上配电变压器'::VARCHAR AS transformer_type FROM dwd_grid_psr_ds_transformer''')
    print(f'    vw_transformer: 视图(柱上+非柱上合并)')
    # vw_transformer 是视图，不在 pg_cols_cache 中；补注册其列定义（=源表列 + transformer_type），
    # 否则后续 insert_kg_metadata 拿不到 pg_cols，match_pg_col 全部 fallback 到 BOM 逻辑名，
    # 导致 properties_schema 列名与 PG 物理列名不一致（如 equip_name vs equipname）
    pg_cols_cache['vw_transformer'] = pg_cols_cache['dwd_grid_psr_ds_transformer'] + [
        ('transformer_type', 'VARCHAR', '变压器类型', False)]

    # 2f. 统一 join 键类型（sim dump 遗留 varchar->bigint）+ 96点 unpivot 视图
    for s in [
        "ALTER TABLE dwd_cust_analog_p ALTER COLUMN inst_id TYPE bigint USING inst_id::bigint",
        "ALTER TABLE dwd_cust_analog_p ALTER COLUMN equip_src_id TYPE bigint USING equip_src_id::bigint",
        "ALTER TABLE cms20_adj_volt_dev ALTER COLUMN dist_sta_id TYPE bigint USING dist_sta_id::bigint",
        "ALTER TABLE cms20_adj_volt_dev ALTER COLUMN cust_id TYPE bigint USING cust_id::bigint",
    ]:
        cur.execute(s)
    v96_vals = ",\n  ".join(f"('{i*15//60:02d}:{i*15%60:02d}', v{i*15//60:02d}{i*15%60:02d})" for i in range(96))
    cur.execute("DROP VIEW IF EXISTS vw_cust_power_ts")
    cur.execute(f"""CREATE VIEW vw_cust_power_ts AS
        SELECT p.inst_id, p.equip_src_id, p.measuerment_type, p.date, t.occur_time, t.power
        FROM dwd_cust_analog_p p, LATERAL (VALUES
          {v96_vals}
        ) AS t(occur_time, power) WHERE t.power IS NOT NULL AND p.equip_src_id = p.inst_id""")
    print(f'    vw_cust_power_ts: 96点宽表->窄表视图(主测量点equip_src_id=inst_id去重, 供重过载剧本用)')

    pg.close()
    return pg_cols_cache

# ===================================================================
# 3. 解析 bom_object / bom_object_property / bom_object_relation
# ===================================================================
def parse_bom():
    print('[3] 解析 bom 本体 ...')
    src = open(BOM_SQL, encoding='utf-8').read()
    objects = {}  # object_id -> (cn, en)
    for m in re.finditer(r"INSERT INTO `bom_object` VALUES \('([^']*)','([^']*)','([^']*)','([^']*)'", src):
        objects[m.group(1)] = (m.group(2), m.group(3))
    # properties: object_id -> [{cn,en,type,is_pk}]
    props = {}
    pat = re.compile(r"INSERT INTO `bom_object_property` VALUES \('([^']*)','([^']*)','([^']*)','([^']*)','([^']*)',NULL,(\d+),")
    for m in pat.finditer(src):
        oid, cn, en, typ, ispk = m.group(2), m.group(3), m.group(4), m.group(5), int(m.group(6))
        props.setdefault(oid, []).append({'cn': cn, 'en': en, 'type': typ, 'is_pk': bool(ispk)})
    # relations: [{rel_id, name, src_obj, tgt_obj, src_prop, tgt_prop, direction, cardinality}]
    relations = []
    rpat = re.compile(r"INSERT INTO `bom_object_relation` VALUES \('([^']*)','([^']*)','([^']*)','([^']*)','([^']*)','([^']*)','([^']*)','([^']*)','([^']*)','([^']*)','([^']*)',NULL,'active'")
    for m in rpat.finditer(src):
        relations.append({
            'rel_id': m.group(1), 'name': m.group(2), 'src_obj': m.group(4), 'tgt_obj': m.group(5),
            'src_prop': m.group(6), 'tgt_prop': m.group(7), 'direction': m.group(8), 'cardinality': m.group(9),
            'fwd': m.group(10), 'rev': m.group(11),
        })
    print(f'    对象:{len(objects)} 属性对象:{len(props)} 关系:{len(relations)}')
    return objects, props, relations

def norm(s):
    return s.replace('_', '').lower()

def match_pg_col(prop_en, pg_cols):
    """bom逻辑名 -> PG物理列名匹配"""
    names = [c[0] for c in pg_cols]
    if prop_en in names:
        return prop_en
    n = norm(prop_en)
    for c in names:
        if norm(c) == n:
            return c
    return prop_en  # fallback

def fix_field(name):
    """关系字段修正：resrc_id -> psrid"""
    return 'psrid' if name == 'resrc_id' else name

def card_map(c):
    return {'many_to_one': 'N:1', 'one_to_many': '1:N', 'one_to_one': '1:1', 'many_to_many': 'N:N'}.get(c, c)

# ===================================================================
# 4. MySQL kg_* 元数据
# ===================================================================
def insert_kg_metadata(objects, props, relations, pg_cols_cache):
    print('[4] 写入 MySQL kg_* 元数据 ...')
    c = pymysql.connect(**MYSQL_CFG)
    cur = c.cursor()

    concept_ids = {k: u5(k) for k in [x[0] for x in CONCEPTS]}
    entity_ids = {oid: oid for oid in OBJ_MAP}  # 直接用 bom object_id

    # === 清理（幂等）===
    print('    清理旧数据 ...')
    cur.execute("DELETE FROM kg_entity_concept_links WHERE entity_id IN (%s)" % ",".join(["%s"] * len(entity_ids)),
                list(entity_ids.keys()))
    cur.execute("DELETE FROM kg_entity_mapping_rules WHERE id IN (%s)" % ",".join(["%s"] * len(entity_ids)),
                [u5('map_' + oid) for oid in entity_ids])
    cur.execute("DELETE FROM kg_entity_relations WHERE id IN (%s)" % ",".join(["%s"] * len(relations)),
                [r['rel_id'] for r in relations])
    cur.execute("DELETE FROM kg_entity_relations WHERE source_entity_id IN (%s)" % ",".join(["%s"] * len(entity_ids)),
                list(entity_ids.keys()))
    cur.execute("DELETE FROM kg_source_field_imports WHERE table_en IN (%s)" % ",".join(["%s"] * len(OBJ_MAP)),
                [v[1] for v in OBJ_MAP.values()])
    src_ids = [u5('src_' + v[1]) for v in OBJ_MAP.values()]
    cur.execute("DELETE FROM kg_source_master_tables WHERE id IN (%s)" % ",".join(["%s"] * len(src_ids)), src_ids)
    cur.execute("DELETE FROM kg_source_business_tables WHERE id IN (%s)" % ",".join(["%s"] * len(src_ids)), src_ids)
    cur.execute("DELETE FROM kg_entities WHERE id IN (%s)" % ",".join(["%s"] * len(entity_ids)), list(entity_ids.keys()))
    # 概念有 parent_id 自引用 FK，关检查后删
    cur.execute("SET FOREIGN_KEY_CHECKS=0")
    cur.execute("DELETE FROM kg_concepts WHERE id IN (%s)" % ",".join(["%s"] * len(concept_ids)), list(concept_ids.values()))
    # 清理旧版 pd_* 概念（v1 结构，已弃用）
    old_pd = [u5(k) for k in ['pd_domain', 'pd_master', 'pd_cust', 'pd_dev', 'pd_meter', 'pd_sta', 'pd_mon', 'pd_telem', 'cust_arch']]
    cur.execute("DELETE FROM kg_concepts WHERE id IN (%s)" % ",".join(["%s"] * len(old_pd)), old_pd)
    cur.execute("SET FOREIGN_KEY_CHECKS=1")

    # === concepts ===
    print('    插入 8 概念 ...')
    for key, name, level, parent, area, sort in CONCEPTS:
        cur.execute("""INSERT INTO kg_concepts(id,name,level,parent_id,area_index,sort_order,description,system_names)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (concept_ids[key], name, level, concept_ids[parent] if parent else None, area, sort,
                     f'配电重过载场景-{name}', 'null'))

    # === entities + concept_links + source tables + fields + mapping ===
    print('    插入 19 实体 + concept_links + source + fields + mapping ...')
    for oid, (ckey, pg_table, is_main, en_name, cn_name, sys_code) in OBJ_MAP.items():
        eid = entity_ids[oid]
        cid = concept_ids[ckey]
        pg_cols = pg_cols_cache.get(pg_table, [])
        # properties_schema: name 必须用 PG 物理列名(match_pg_col), 不能用 BOM 逻辑名
        # 否则 vw_transformer 等表会出现 equip_name vs equipname 不一致
        ps = []
        for p in props.get(oid, []):
            typ = 'int' if p['type'] == 'integer' else p['type']
            _phys = match_pg_col(p['en'], pg_cols)
            ps.append({'name': _phys, 'type': typ, 'cnName': p['cn'], 'description': p['cn'], 'isPrimaryKey': p['is_pk']})
            # 码值列带 _name 冗余列(编码+名称两列)时, 注册为实体属性, 数据来源配置预览可见
            if any(c[0] == _phys + '_name' for c in pg_cols):
                ps.append({'name': _phys + '_name', 'type': 'string', 'cnName': p['cn'] + '名称',
                           'description': p['cn'] + '名称', 'isPrimaryKey': False})
        # 补注册 bom 未定义但 PG 实际有的列(视图字段/gen_x10 后加的关联键)
        for _col, _cn, _typ in _EXTRA_FIELDS.get(pg_table, []):
            if any(c[0] == _col for c in pg_cols):
                ps.append({'name': _col, 'type': _typ, 'cnName': _cn, 'description': _cn, 'isPrimaryKey': False})
        cur.execute("""INSERT INTO kg_entities(id,concept_id,entity_code,entity_name,entity_en_name,properties_schema,
            description,is_main_table,data_layer,sort_order,source_mode,integration_sql,doris_catalog,data_source_id,entity_explanation)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,NULL,NULL,%s)""",
                    (eid, cid, en_name, cn_name, pg_table, json.dumps(ps, ensure_ascii=False),
                     f'{cn_name}实体', 1 if is_main else 0, 'DWD', 1, 'physical_table', cn_name))
        # concept_link
        cur.execute("INSERT INTO kg_entity_concept_links(id,entity_id,concept_id,created_at) VALUES(%s,%s,%s,NOW())",
                    (u5('link_' + oid), eid, cid))
        # source table 注册（按概念层级派生 major/l1/l2/l3/l4）
        sys_name = '电网资源业务中台' if sys_code == 'DWZYYWZT' else '客户服务业务中台'
        src_id = u5('src_' + pg_table)
        domain, l1, l2, l3, l4 = concept_path(ckey)
        major = domain or ''  # 主数据无业务域->空；业务活动->电网域/客户域
        if is_main:
            cur.execute("""INSERT INTO kg_source_master_tables(id,major,deploy,sysName,sysCode,l1,l2,enName,cnName,type)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (src_id, major, '一级部署', sys_name, sys_code, l1 or '', l2 or '', pg_table, cn_name, '主数据'))
        else:
            cur.execute("""INSERT INTO kg_source_business_tables(id,major,deploy,sysName,sysCode,l3,l4,enName,cnName,type,relL1,relL2)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (src_id, major, '一级部署', sys_name, sys_code, l3 or '', l4 or '', pg_table, cn_name, '业务表', l1 or '', l2 or ''))
        # source_field_imports
        for p in props.get(oid, []):
            phys = match_pg_col(p['en'], pg_cols)
            cur.execute("""INSERT INTO kg_source_field_imports(id,table_cn,table_en,field_cn,field_en,data_type,pk_fk,is_ref_data,created_at)
                VALUES(%s,%s,%s,%s,%s,%s,%s,%s,NOW())""",
                        (u5('fld_' + pg_table + '_' + p['en']), cn_name, pg_table, p['cn'], phys,
                         'int' if p['type'] == 'integer' else p['type'], 'PK' if p['is_pk'] else '', '否'))
            # 码值列带 _name 冗余列时, 注册 _name 字段(编码+名称两列), 数据来源配置预览可见
            if any(c[0] == phys + '_name' for c in pg_cols):
                cur.execute("""INSERT INTO kg_source_field_imports(id,table_cn,table_en,field_cn,field_en,data_type,pk_fk,is_ref_data,created_at)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,NOW())""",
                            (u5('fld_' + pg_table + '_' + p['en'] + '_name'), cn_name, pg_table, p['cn'] + '名称', phys + '_name',
                             'string', '', '否'))
        # 补注册 bom 未定义但 PG 实际有的列
        for _col, _cn, _typ in _EXTRA_FIELDS.get(pg_table, []):
            if any(c[0] == _col for c in pg_cols):
                cur.execute("""INSERT INTO kg_source_field_imports(id,table_cn,table_en,field_cn,field_en,data_type,pk_fk,is_ref_data,created_at)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,NOW())""",
                            (u5('fld_' + pg_table + '_' + _col), cn_name, pg_table, _cn, _col, _typ, '', '否'))
        # mapping_rules: key 和 source 都用 PG 物理列名(phys), 不用 BOM 逻辑名(p['en'])
        fm = {'__meta__': {'main_source_table_id': src_id, 'primary_key_overrides': {}}}
        for p in props.get(oid, []):
            phys = match_pg_col(p['en'], pg_cols)
            fm[f'{eid}_{phys}'] = {'desc': '', 'is_pk': p['is_pk'], 'source': [f'{src_id}_{phys}']}
            # _name 冗余列映射(编码+名称两列)
            if any(c[0] == phys + '_name' for c in pg_cols):
                fm[f'{eid}_{phys}_name'] = {'desc': '', 'is_pk': False, 'source': [f'{src_id}_{phys}_name']}
        # 补 EXTRA_FIELDS 映射
        for _col, _cn, _typ in _EXTRA_FIELDS.get(pg_table, []):
            if any(c[0] == _col for c in pg_cols):
                fm[f'{eid}_{_col}'] = {'desc': '', 'is_pk': False, 'source': [f'{src_id}_{_col}']}
        cur.execute("""INSERT INTO kg_entity_mapping_rules(id,name,source_table_ids,entity_ids,field_mappings,is_advanced_sql,sql_content,created_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,NOW())""",
                    (u5('map_' + oid), f'{cn_name}映射规则', json.dumps([src_id], ensure_ascii=False),
                     json.dumps([eid], ensure_ascii=False), json.dumps(fm, ensure_ascii=False), 0, None))

    # === relations ===
    print('    插入 27 关系 ...')
    for r in relations:
        src_eid = entity_ids.get(r['src_obj'])
        tgt_eid = entity_ids.get(r['tgt_obj'])
        if not src_eid or not tgt_eid:
            print(f'    跳过关系(对象未映射): {r["name"]}'); continue
        sp = fix_field(r['src_prop'])
        tp = fix_field(r['tgt_prop'])
        join_expr = f't0.{sp} = t1.{tp}'
        cat = '采集' if '采集' in r['name'] else '归属'
        remark = r['fwd']
        # 用电户->计量表计 特殊标注
        if r['src_obj'] == '2b4b2adf-a605-57d5-b44d-89d613e00fb5' and r['tgt_obj'] == 'b7cbc2ab-9c27-59bb-8030-69cb9ec6d812':
            remark = '物理需经计量点2跳:用电户.cust_id->计量点.cust_id->计量点.inst_id->计量表计.inst_id'
        cur.execute("""INSERT INTO kg_entity_relations(id,source_entity_id,target_entity_id,relation_name,direction,cardinality,join_expr,description,relation_category,source_field_name,target_field_name,remark,created_at)
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())""",
                    (r['rel_id'], src_eid, tgt_eid, r['name'], 'forward', card_map(r['cardinality']),
                     join_expr, r['fwd'], cat, sp, tp, remark))
    c.commit()
    c.close()
    print('    kg_* 元数据写入完成')

    # === 补注册 vw_cust_power_ts 视图实体（BOM 无此对象，但剧本 SQL 依赖此视图）===
    register_view_entity(c)

def register_view_entity(c):
    """注册 vw_cust_power_ts 视图为实体（BOM 无此对象，需单独注册）。
    确保 search_entities 可查到其列定义，剧本列名以元数据为准。"""
    cur = c.cursor()
    eid = u5('vw_cust_power_ts')
    cid = u5('cust_telem')
    cur.execute("DELETE FROM kg_entities WHERE id=%s", (eid,))
    ps = json.dumps([
        {'name': 'inst_id', 'type': 'bigint', 'cnName': '计量点标识', 'description': '计量点标识(关联cms20_inst_elec_cons.inst_id)', 'isPrimaryKey': False},
        {'name': 'equip_src_id', 'type': 'bigint', 'cnName': '测量点设备源标识', 'description': '测量点设备源标识(已按equip_src_id=inst_id去重)', 'isPrimaryKey': False},
        {'name': 'measuerment_type', 'type': 'string', 'cnName': '测量类型', 'description': '测量类型(TotW=总有功功率)', 'isPrimaryKey': False},
        {'name': 'date', 'type': 'string', 'cnName': '日期', 'description': '日期(YYYYMMDD格式)', 'isPrimaryKey': False},
        {'name': 'occur_time', 'type': 'string', 'cnName': '发生时间', 'description': '发生时间(HH:MM格式, 96点之一)', 'isPrimaryKey': False},
        {'name': 'power', 'type': 'decimal', 'cnName': '功率值', 'description': '功率值(kW); 正=用电/发电出力, 负=上网倒送', 'isPrimaryKey': False},
    ], ensure_ascii=False)
    cur.execute("""INSERT INTO kg_entities(id,concept_id,entity_code,entity_name,entity_en_name,properties_schema,
        description,is_main_table,data_layer,sort_order,source_mode,integration_sql,doris_catalog,data_source_id,entity_explanation)
        VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NULL,NULL,NULL,%s)""",
        (eid, cid, 'CustPowerTimeSeries', '客户功率时序', 'vw_cust_power_ts', ps,
         '客户功率时序视图(96点宽表unpivot为窄表)', 0, 'DWD', 99, 'view', '客户功率时序'))
    c.commit()
    print(f'    vw_cust_power_ts 视图实体已注册(id={eid})')

def main():
    try:
        import_sim_to_tmp()
    except Exception as e:
        print('sim导入失败:', e); return
    pg_cols_cache = build_pg()
    objects, props, relations = parse_bom()
    insert_kg_metadata(objects, props, relations, pg_cols_cache)
    # 清理临时库
    try:
        c = pymysql.connect(**{k: v for k, v in MYSQL_CFG.items() if k != 'database'})
        c.cursor().execute('DROP DATABASE IF EXISTS tupu_sim_tmp'); c.commit(); c.close()
        print('[5] 临时库 tupu_sim_tmp 已清理')
    except Exception as e:
        print('清理临时库失败(可忽略):', e)
    print('\n=== 导入完成 ===')
    print('下一步: 调用 POST http://127.0.0.1:28000/api/v1/sync/neo4j-all?force=true 同步Neo4j')

if __name__ == '__main__':
    main()
