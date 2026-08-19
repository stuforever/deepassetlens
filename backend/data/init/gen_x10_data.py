# -*- coding: utf-8 -*-
"""配变重过载数据生成(v5): 105配变/100台区(95单路+5多路)/300计量点/3天/一用户多计量点
v5变更(跨天持续):
  - 数据扩展到3天(20260801/02/03), 重过载台区有跨天持续性
  - 统计口径9台(上网5+用电5-重叠1): 连续>=3天3台(1/3), 连续>=2天5台(1/2), 只1天4台
  - 发电参考10台(上台5+自发自用5)也跨天; 发电不判定
v4基线: 电压10kV/35kV各半; 多路台区仅5个; 上网重过载5台(过载2+重载3)/过载2台(2%)
"""
import psycopg2, random
random.seed(42)

PG = dict(host='localhost', port=25432, user='postgres', password='postgres', dbname='tupu')
c = psycopg2.connect(**PG); c.autocommit = True; cur = c.cursor()

V96 = [f"v{i*15//60:02d}{i*15%60:02d}" for i in range(96)]  # v0000..v2345
N_TF = 105   # 配变数(非柱上105)
N_STA = 100  # 台区数(95单路+5多路)
N_CUST = 200  # 客户数(发电100+用电100)
N_INST = 300  # 主计量点(每台区3个: 1102上网+1101发电+01用电)
# 一户多号第二户号独立计量点(挂台区2, cust_id=1/101跨台区): (inst_id,usage_cls,台区,cust_id,gpc_id,elec_cons_cust_id)
# gpc_id=901(cust_id=1) 在台区2另挂上网+发电; elec_cons_cust_id=901(cust_id=101) 在台区2另挂用电
EXTRA_INST = [(301,'1102',2,1,901,None),(302,'1101',2,1,901,None),(303,'01',2,101,None,901)]
DATES = ['20260801', '20260802', '20260803']  # 3天数据

# ---- 参考数据码值字典 ----
VL_10KV = 'AC00101'   # 10kV
VL_35KV = 'AC00201'   # 35kV
INDCLS_GEN = ['D4410', 'D4445', 'D4441', 'D4444', 'D4442']
INDCLS_USE = ['A000', 'B000', 'C000', 'D000', 'E000', 'F000', 'H000', 'I000', 'K000', 'G000']
PSCATEG = ['01', '02', '03']
CUSTCLS = ['01', '02', '03']

# ---- 码值->中文映射(编码与码值冗余存储, _name列) ----
# 细分码(ind_cls 的 D44xx)为模拟值, 可在此 dict 直接校准
NAME = {
    'inst_usage_cls':  {'01': '用电', '1101': '发电', '1102': '上网'},
    'inst_cls':        {'01': '售电结算', '03': '关口计量'},
    'inst_stat':       {'02': '在用', '01': '停用'},
    'inst_lv':         {'1': '高压'},
    'cust_pscateg':    {'01': '分布式光伏', '02': '风电', '03': '其他'},
    'gc_stat':         {'01': '正常', '02': '停用'},
    'cust_cls':        {'01': '高压', '02': '中压', '03': '低压'},
    'ecc_stat':        {'01': '正常'},
    'voltagelevel':    {'AC00101': '10kV', 'AC00201': '35kV', 'AC01101': '110kV'},
    'runstate':        {'20': '在运', '40': '停运'},
    'pubprivflag':     {'0': '公用', '1': '专用'},
    'resrc_supl_stat': {'01': '运行'},
    'pub_clg_flag':    {'0': '否'},
    'ind_cls': {'A000': '农林牧渔', 'B000': '采矿业', 'C000': '制造业', 'D000': '电力热力',
                'E000': '建筑业', 'F000': '批发零售', 'G000': '交通运输', 'H000': '住宿餐饮',
                'I000': '信息技术', 'K000': '房地产',
                'D4410': '电力生产', 'D4441': '电力供应', 'D4442': '电力工程',
                'D4444': '电力辅助', 'D4445': '其他电力'},
    'categ': {'01': '电流互感器', '02': '电压互感器', '03': '组合互感器'},
    'meter_spcl_flag': {'0': '非计量专用', '1': '计量专用'},
    'phase': {'A': 'A相', 'B': 'B相', 'C': 'C相', 'ABC': '三相'},
}
def nm(col, code):
    """取码值中文名, 缺省回退编码原文"""
    return NAME.get(col, {}).get(str(code), str(code))

# ---- 拓扑映射函数 ----
def sta_of_tf(j):
    """配变T00j -> 所属台区 (台区1-95单路1配变, 台区96-100多路各2配变)"""
    if j <= 95: return j
    return 96 + (j - 96) // 2   # j=96,97->台区96; j=98,99->台区97; ... j=104,105->台区100

def sta_total_cap(sta):
    """台区总容量(单路=配变容量, 多路=配变容量之和)"""
    if sta <= 95:
        return 800 + sta * 50
    k = sta - 96  # 0..4
    j1, j2 = 96 + 2*k, 97 + 2*k
    return (800 + j1*50) + (800 + j2*50)

def inst_sta(j):
    """计量点inst j -> 所属台区
    inst1-100 上网 -> 台区j; inst101-200 发电 -> 台区j-100; inst201-300 用电 -> 台区j-200"""
    if j <= 100: return j
    if j <= 200: return j - 100
    return j - 200

def inst_total_cap(j):
    return sta_total_cap(inst_sta(j))

def inst_usage_cls_of(j):
    """inst j -> inst_usage_cls: 1-100上网1102, 101-200发电1101, 201-300用电01"""
    if j <= 100: return '1102'
    if j <= 200: return '1101'
    return '01'

def load_type_of(j):
    """inst j -> 负荷类型名(中文)"""
    return {'1102': '上网', '1101': '发电', '01': '用电'}[inst_usage_cls_of(j)]

def day_index(date):
    """日期 -> 天序号 1/2/3"""
    return DATES.index(date) + 1

# ---- 重过载案例持续天数字典 ----
# 台区 -> {负荷类型: (mode, 持续天数)}
# mode: overload(过载1.06×)/heavy(重载0.89×)/self_use(自发自用上网0.05×全天低)
# 持续天数N: 8/1..8/N 重过载, 之后正常。发电不判定, 仅参考。
# 统计口径9台: 连续>=3天3台(1,96,11), 连续正好2天2台(3,12), 只1天4台(4,5,13,14)
DURATION = {
    # 连续3天(统计口径1/3): 台区1(三重叠)/96(多路)/11(用电)
    1:  {'上网': ('overload', 3), '发电': ('heavy', 3), '用电': ('heavy', 3)},
    96: {'上网': ('overload', 3), '发电': ('heavy', 3)},
    11: {'用电': ('heavy', 3)},
    # 连续正好2天(非3天): 台区3/12
    3:  {'上网': ('heavy', 2), '发电': ('heavy', 2)},
    12: {'用电': ('heavy', 2)},
    # 只1天8/1: 台区4/5/13/14
    4:  {'上网': ('heavy', 1), '发电': ('heavy', 1)},
    5:  {'上网': ('heavy', 1), '发电': ('heavy', 1)},
    13: {'用电': ('heavy', 1)},
    14: {'用电': ('heavy', 1)},
    # 自发自用发电(参考): 台区6-10, 上网self_use全天低, 发电跨天参考
    6:  {'发电': ('heavy', 3), '上网': ('self_use', 0)},
    7:  {'发电': ('heavy', 3), '上网': ('self_use', 0)},
    8:  {'发电': ('heavy', 2), '上网': ('self_use', 0)},
    9:  {'发电': ('heavy', 1), '上网': ('self_use', 0)},
    10: {'发电': ('heavy', 1), '上网': ('self_use', 0)},
}

def gen_power(total_cap, mode):
    """生成96点功率(kW), 基于台区总容量"""
    p = []
    for i in range(96):
        t = i * 15
        base = int(total_cap * (0.40 + (i % 10) * 0.03))
        if mode == 'overload':
            if 720 <= t <= 825: p.append(int(total_cap * 1.06))   # 连续8点≥100%(过载)
            else: p.append(base)
        elif mode == 'heavy':
            if 480 <= t <= 585: p.append(int(total_cap * 0.89))   # 连续8点80-100%(重载)
            else: p.append(base)
        elif mode == 'self_use':
            p.append(int(total_cap * 0.05))   # 自发自用上网很低, 不构成重过载
        else:
            p.append(base)
    return p

def mode_for_inst(j, date):
    """根据inst的台区、负荷类型、日期得mode。
    持续天数N: 8/1..8/N 重过载, 之后正常。self_use全天低(自发自用上网)。"""
    sta = inst_sta(j)
    lt = load_type_of(j)
    entry = DURATION.get(sta, {}).get(lt)
    if entry is None:
        return 'normal'
    mode, dur = entry
    if mode == 'self_use':
        return 'self_use'   # 自发自用上网全天低
    if day_index(date) <= dur:
        return mode   # 在持续期内 -> 重过载(overload/heavy)
    return 'normal'   # 超过持续期 -> 正常

# 1. DROP视图 + TRUNCATE 业务表(含cms20_dist_sta)
print('[1] 清空视图和业务表 ...')
cur.execute('DROP VIEW IF EXISTS vw_transformer')
cur.execute('DROP VIEW IF EXISTS vw_cust_power_ts')
for t in ['dwd_cust_analog_p','dwd_cst_gpc','cms20_elec_cons_cust','cms20_adj_volt_dev_asset',
          'cms20_adj_volt_dev','cms20_inst_elec_cons','cms20_cst_cust','cms20_dist_sta',
          'dwd_grid_psr_ds_transformer','dwd_grid_psr_ds_p_transformer']:
    cur.execute(f'TRUNCATE TABLE {t} RESTART IDENTITY')

# 1.5 加列: 编码旁冗余 _name 中文名 + 计量点加 gpc_id/elec_cons_cust_id 精确归属户号(防一户多号笛卡尔积)
print('[1.5] 加 _name 冗余列 + gpc_id/elec_cons_cust_id (ALTER IF NOT EXISTS, 幂等) ...')
_ALTERS = [
    "ALTER TABLE cms20_inst_elec_cons ADD COLUMN IF NOT EXISTS gpc_id BIGINT",
    "ALTER TABLE cms20_inst_elec_cons ADD COLUMN IF NOT EXISTS elec_cons_cust_id BIGINT",
    "ALTER TABLE cms20_inst_elec_cons ADD COLUMN IF NOT EXISTS inst_usage_cls_name VARCHAR",
    "ALTER TABLE cms20_inst_elec_cons ADD COLUMN IF NOT EXISTS inst_cls_name VARCHAR",
    "ALTER TABLE cms20_inst_elec_cons ADD COLUMN IF NOT EXISTS inst_stat_name VARCHAR",
    "ALTER TABLE cms20_inst_elec_cons ADD COLUMN IF NOT EXISTS inst_lv_name VARCHAR",
    "ALTER TABLE dwd_cst_gpc ADD COLUMN IF NOT EXISTS cust_pscateg_name VARCHAR",
    "ALTER TABLE dwd_cst_gpc ADD COLUMN IF NOT EXISTS gc_stat_name VARCHAR",
    "ALTER TABLE cms20_elec_cons_cust ADD COLUMN IF NOT EXISTS cust_cls_name VARCHAR",
    "ALTER TABLE cms20_elec_cons_cust ADD COLUMN IF NOT EXISTS ecc_stat_name VARCHAR",
    "ALTER TABLE cms20_cst_cust ADD COLUMN IF NOT EXISTS ind_cls_name VARCHAR",
    "ALTER TABLE dwd_grid_psr_ds_transformer ADD COLUMN IF NOT EXISTS voltagelevel_name VARCHAR",
    "ALTER TABLE dwd_grid_psr_ds_transformer ADD COLUMN IF NOT EXISTS runstate_name VARCHAR",
    "ALTER TABLE dwd_grid_psr_ds_transformer ADD COLUMN IF NOT EXISTS pubprivflag_name VARCHAR",
    "ALTER TABLE dwd_grid_psr_ds_p_transformer ADD COLUMN IF NOT EXISTS voltagelevel_name VARCHAR",
    "ALTER TABLE dwd_grid_psr_ds_p_transformer ADD COLUMN IF NOT EXISTS runstate_name VARCHAR",
    "ALTER TABLE dwd_grid_psr_ds_p_transformer ADD COLUMN IF NOT EXISTS pubprivflag_name VARCHAR",
    "ALTER TABLE cms20_dist_sta ADD COLUMN IF NOT EXISTS resrc_supl_stat_name VARCHAR",
    "ALTER TABLE cms20_dist_sta ADD COLUMN IF NOT EXISTS pub_clg_flag_name VARCHAR",
    "ALTER TABLE dwd_grid_psr_ds_feeder ADD COLUMN IF NOT EXISTS voltagelevel_name VARCHAR",
    "ALTER TABLE dwd_grid_psr_ds_feeder ADD COLUMN IF NOT EXISTS runstate_name VARCHAR",
    "ALTER TABLE dwd_grid_psr_ds_feeder ADD COLUMN IF NOT EXISTS pubprivflag_name VARCHAR",
    "ALTER TABLE dwd_cst_it_run ADD COLUMN IF NOT EXISTS categ_name VARCHAR",
    "ALTER TABLE dwd_cst_it_run ADD COLUMN IF NOT EXISTS meter_spcl_flag_name VARCHAR",
    "ALTER TABLE dwd_cst_it_run ADD COLUMN IF NOT EXISTS phase_name VARCHAR",
]
for sql in _ALTERS:
    cur.execute(sql)

# 2. 配变: 非柱上T001-T105 + 柱上pole-T001-T105 (电压等级10kV/35kV各半)
print(f'[2] 生成 {N_TF} 台配变(非柱上+柱上, 电压10kV/35kV各半) ...')
for j in range(1, N_TF+1):
    cap = 800 + j * 50
    vlevel = VL_10KV if j <= 52 else VL_35KV   # 1-52=10kV, 53-105=35kV
    feeder = f'F{(sta_of_tf(j)-1)//5+1:03d}'   # 馈线: 每5个台区一个(一对多)
    vlname, rsname, ppname = nm('voltagelevel', vlevel), nm('runstate', '20'), nm('pubprivflag', '0')
    cur.execute("INSERT INTO dwd_grid_psr_ds_transformer (psrid,astid,equipname,feeder,capacity,voltagelevel,voltagelevel_name,pubprivflag,pubprivflag_name,runstate,runstate_name) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (f'T{j:03d}', f'AST_T{j:03d}', f'配电变压器{j:03d}', feeder, cap, vlevel, vlname, '0', ppname, '20', rsname))
    cur.execute("INSERT INTO dwd_grid_psr_ds_p_transformer (psrid,astid,equipname,feeder,capacity,voltagelevel,voltagelevel_name,pubprivflag,pubprivflag_name,runstate,runstate_name) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (f'pole-T{j:03d}', f'pole-AST_T{j:03d}', f'柱上变压器{j:03d}', feeder, cap, vlevel, vlname, '0', ppname, '20', rsname))

# 3. 台区: 100个(95单路+5多路), 填充cms20_dist_sta(原空表)
print(f'[3] 生成 {N_STA} 个台区(95单路+5多路) ...')
for sta in range(1, N_STA+1):
    tcnt = 1 if sta <= 95 else 2  # 单路1配变, 多路2配变
    cur.execute("INSERT INTO cms20_dist_sta (dist_sta_id,resrc_supl_name,resrc_supl_stat,resrc_supl_stat_name,pub_clg_flag,pub_clg_flag_name) VALUES (%s,%s,%s,%s,%s,%s)",
        (sta, f'台区{sta:03d}({"单路" if tcnt==1 else "多路"}供电)', '01', nm('resrc_supl_stat','01'), '0', nm('pub_clg_flag','0')))

# 4. 客户: 200个(发电1-100, 用电101-200)
print(f'[4] 生成 {N_CUST} 个客户 ...')
for i in range(1, N_CUST+1):
    ind = INDCLS_GEN[i % len(INDCLS_GEN)] if i <= 100 else INDCLS_USE[(i-101) % len(INDCLS_USE)]
    cur.execute("INSERT INTO cms20_cst_cust (cust_id,cust_no,cust_name,ind_cls,ind_cls_name) VALUES (%s,%s,%s,%s,%s)",
        (i, f'C{i:05d}', f'客户{i:03d}', ind, nm('ind_cls', ind)))

# 5. 计量点: 300个(每台区3个: 1102上网+1101发电+01用电)
#    inst1-100: 1102上网(cust_id=inst, 发电户1-100) -- 一用户多计量点: 发电户各有inst(1102)+inst+100(1101)
#    inst101-200: 1101发电(cust_id=inst-100, 同一发电户) -- 一用户多计量点!
#    inst201-300: 01用电(cust_id=inst-100, 用电户101-200)
print(f'[5] 生成 {N_INST}+{len(EXTRA_INST)} 个计量点(每台区3个 + 一户多号第二户号独立计量点) ...')
def _insert_inst(j, usage, inst_cls, cust_id, gpc_id, ecc, sta):
    cur.execute("INSERT INTO cms20_inst_elec_cons (inst_id,inst_cls,inst_cls_name,inst_lv,inst_lv_name,inst_stat,inst_stat_name,inst_usage_cls,inst_usage_cls_name,cust_id,gpc_id,elec_cons_cust_id,dist_sta_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (j, inst_cls, nm('inst_cls', inst_cls), '1', nm('inst_lv','1'), '02', nm('inst_stat','02'),
         usage, nm('inst_usage_cls', usage), cust_id, gpc_id, ecc, sta))
for j in range(1, N_INST+1):
    if j <= 100:        # 上网关口: gpc_id=j(发电户号), 用电户号空
        _insert_inst(j, '1102', '03', j, j, None, inst_sta(j))
    elif j <= 200:     # 发电关口: 同一发电户号 gpc_id=j-100
        _insert_inst(j, '1101', '03', j-100, j-100, None, inst_sta(j))
    else:              # 售电结算用电: elec_cons_cust_id=j-100, 发电户号空
        _insert_inst(j, '01', '01', j-100, None, j-100, inst_sta(j))
# 一户多号第二户号独立计量点(cust_id=1的gpc_id=901 / cust_id=101的elec_cons_cust_id=901 挂台区2, 各自独立不共享)
for eid, usage, sta, cust_id, gpc_id, ecc in EXTRA_INST:
    inst_cls = '03' if usage in ('1101','1102') else '01'
    _insert_inst(eid, usage, inst_cls, cust_id, gpc_id, ecc, sta)

# 6. 调压设备+资产: 105套(配变1:1:1), dist_sta_id=所属台区
print(f'[6] 生成 {N_TF} 套调压设备/资产(配变1:1:1, 多路台区共享dist_sta_id) ...')
for j in range(1, N_TF+1):
    sta = sta_of_tf(j)
    cur.execute("INSERT INTO cms20_adj_volt_dev (adj_volt_dev_id,adj_volt_dev_asset_id,cust_id,dist_sta_id) VALUES (%s,%s,%s,%s)",(j,j,sta,sta))
    cur.execute("INSERT INTO cms20_adj_volt_dev_asset (adj_volt_dev_asset_id,pms_equip_id) VALUES (%s,%s)",(j,f'T{j:03d}'))

# 7. 发电户: gpc_id 1-100(cust_id 1-100) + gpc_id=901(cust_id=1, 一户多号, 电源类别01)
print('[7] 生成 100 发电户 + 一户多号(gpc_id=901) ...')
for i in range(1, 101):
    pscateg = PSCATEG[i % len(PSCATEG)]
    cur.execute("INSERT INTO dwd_cst_gpc (gpc_id,cust_id,cust_pscateg,cust_pscateg_name,gc_stat,gc_stat_name) VALUES (%s,%s,%s,%s,%s,%s)",
        (i, i, pscateg, nm('cust_pscateg', pscateg), '01', nm('gc_stat','01')))
cur.execute("INSERT INTO dwd_cst_gpc (gpc_id,cust_id,cust_pscateg,cust_pscateg_name,gc_stat,gc_stat_name) VALUES (%s,%s,%s,%s,%s,%s)",
    (901, 1, '01', nm('cust_pscateg','01'), '01', nm('gc_stat','01')))  # cust_id=1多号, 电源类别01

# 8. 用电户: elec_cons_cust_id 101-200(cust_id 101-200) + 901(cust_id=101, 一户多号)
print('[8] 生成 100 用电户 + 一户多号(901) ...')
for i in range(101, 201):
    cust_cls = CUSTCLS[i % len(CUSTCLS)]
    cur.execute("INSERT INTO cms20_elec_cons_cust (elec_cons_cust_id,cust_id,cust_cls,cust_cls_name,ecc_stat,ecc_stat_name) VALUES (%s,%s,%s,%s,%s,%s)",
        (i, i, cust_cls, nm('cust_cls', cust_cls), '01', nm('ecc_stat','01')))
cur.execute("INSERT INTO cms20_elec_cons_cust (elec_cons_cust_id,cust_id,cust_cls,cust_cls_name,ecc_stat,ecc_stat_name) VALUES (%s,%s,%s,%s,%s,%s)",
    (901, 101, '01', nm('cust_cls','01'), '01', nm('ecc_stat','01')))  # cust_id=101多号

# 9. 功率: 300计量点×3天×96点
#    案例由 DURATION 字典驱动(持续天数), 跨天持续重过载
#    功率方向: 1102上网(inst1-100)取负(倒送), 1101发电(inst101-200)正, 01用电(inst201-300)正
print(f'[9] 生成 {N_INST}+{len(EXTRA_INST)} 计量点×{len(DATES)}天×96点功率 ...')
cols = ['inst_id','equip_src_id','measuerment_type','date'] + V96
collist = ",".join(f'"{n}"' for n in cols)
placeholders = ",".join(["%s"] * len(cols))
for date in DATES:
    for j in range(1, N_INST+1):
        total_cap = inst_total_cap(j)
        mode = mode_for_inst(j, date)
        pw = gen_power(total_cap, mode)
        if j <= 100:  # 1102上网功率取负(倒送)
            pw = [-p for p in pw]
        vals = [j, j, 'TotW', date] + pw
        cur.execute(f'INSERT INTO dwd_cust_analog_p ({collist}) VALUES ({placeholders})', vals)
    # 一户多号第二户号计量点: 极低功率(self_use 0.05×), 不干扰台区2负载率; 上网(1102)取负
    for eid, usage, sta, cust_id, gpc_id, ecc in EXTRA_INST:
        pw = gen_power(sta_total_cap(sta), 'self_use')
        if usage == '1102':
            pw = [-p for p in pw]
        vals = [eid, eid, 'TotW', date] + pw
        cur.execute(f'INSERT INTO dwd_cust_analog_p ({collist}) VALUES ({placeholders})', vals)

# 10. 一计量点多表: inst 1 加副表(equip_src_id=901, 功率翻倍, 视图应过滤掉)
print('[10] 生成 inst 1 副表(equip_src_id=901, 测试视图去重) ...')
for date in DATES:
    j = 1
    total_cap = inst_total_cap(j)
    mode = mode_for_inst(j, date)
    pw = gen_power(total_cap, mode)
    pw = [-p * 2 for p in pw]  # 1102取负 + 副表功率翻倍(应被视图过滤)
    vals = [j, 901, 'TotW', date] + pw  # equip_src_id=901 != inst_id=1
    cur.execute(f'INSERT INTO dwd_cust_analog_p ({collist}) VALUES ({placeholders})', vals)

# 11. 重建视图
print('[11] 重建 vw_transformer + vw_cust_power_ts ...')
cur.execute("""CREATE VIEW vw_transformer AS
    SELECT psrid,astid,equipname,feeder,capacity,voltagelevel,voltagelevel_name,pubprivflag,pubprivflag_name,runstate,runstate_name,'柱上变压器'::VARCHAR AS transformer_type FROM dwd_grid_psr_ds_p_transformer
    UNION ALL
    SELECT psrid,astid,equipname,feeder,capacity,voltagelevel,voltagelevel_name,pubprivflag,pubprivflag_name,runstate,runstate_name,'非柱上配电变压器'::VARCHAR AS transformer_type FROM dwd_grid_psr_ds_transformer""")
v96_vals = ",\n  ".join(f"('{i*15//60:02d}:{i*15%60:02d}', v{i*15//60:02d}{i*15%60:02d})" for i in range(96))
cur.execute(f"""CREATE VIEW vw_cust_power_ts AS
    SELECT p.inst_id, p.equip_src_id, p.measuerment_type, p.date, t.occur_time, t.power
    FROM dwd_cust_analog_p p, LATERAL (VALUES
      {v96_vals}
    ) AS t(occur_time, power) WHERE t.power IS NOT NULL AND p.equip_src_id = p.inst_id""")

# 12. 验证
print('\n=== 验证 ===')
cur.execute("SELECT COUNT(*) FROM vw_transformer"); print('配变视图总数:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM cms20_dist_sta"); print('台区表记录数:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM cms20_inst_elec_cons"); print('计量点数:', cur.fetchone()[0])
cur.execute("SELECT COUNT(DISTINCT date) FROM vw_cust_power_ts"); print('功率天数:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM vw_cust_power_ts"); print('功率总点数:', cur.fetchone()[0])

# 电压等级分布(10kV/35kV各半)
cur.execute("SELECT voltagelevel, COUNT(*) FROM dwd_grid_psr_ds_transformer GROUP BY voltagelevel ORDER BY voltagelevel")
print('电压等级分布(非柱上):', cur.fetchall())

# 台区-配变拓扑验证
cur.execute("""SELECT CASE WHEN cnt=1 THEN '单路' ELSE '多路' END AS 类型, COUNT(*) AS 台区数
  FROM (SELECT v.dist_sta_id, COUNT(DISTINCT va.pms_equip_id) AS cnt
    FROM cms20_adj_volt_dev v JOIN cms20_adj_volt_dev_asset va ON v.adj_volt_dev_asset_id=va.adj_volt_dev_asset_id
    GROUP BY v.dist_sta_id) x GROUP BY CASE WHEN cnt=1 THEN '单路' ELSE '多路' END""")
print('台区-配变拓扑:', cur.fetchall())

# 计量点-用户验证(一用户多计量点 + 一户多号独立计量点)
cur.execute("SELECT cust_id, COUNT(*) AS 计量点数 FROM cms20_inst_elec_cons GROUP BY cust_id HAVING COUNT(*)>1 ORDER BY cust_id LIMIT 5")
rows = cur.fetchall()
print(f'一用户多计量点: {len(rows)}个客户有多个计量点(前5):', rows)
# 一户多号: cust_id=1 的 gpc_id=901 应独立挂台区2(inst301/302), 不与 gpc_id=1(台区1 inst1/101) 共享
cur.execute("SELECT inst_id, inst_usage_cls, inst_usage_cls_name, gpc_id, elec_cons_cust_id, dist_sta_id FROM cms20_inst_elec_cons WHERE cust_id=1 ORDER BY inst_id")
print('cust_id=1 计量点(应: 台区1 inst1/101 gpc_id=1; 台区2 inst301/302 gpc_id=901):', cur.fetchall())

# 跨天重过载判定(分天+连续天数统计, 仅上网+用电判定, 发电不判定)
print('\n=== 跨天重过载判定(上网+用电, 分天) ===')
cur.execute("""WITH 计量点台区 AS (
  SELECT DISTINCT
    CASE WHEN i.inst_usage_cls='01' THEN '用电负载' WHEN i.inst_usage_cls='1102' THEN '上网负载' END AS 负荷类型,
    i.inst_id, i.inst_usage_cls, i.dist_sta_id AS 台区编号
  FROM cms20_inst_elec_cons i WHERE i.inst_usage_cls IN ('01','1102')),
台区容量 AS (
  SELECT v.dist_sta_id AS 台区编号, SUM(t.capacity) AS 台区总容量, STRING_AGG(t.psrid,',') AS 配变列表
  FROM cms20_adj_volt_dev v JOIN cms20_adj_volt_dev_asset va ON v.adj_volt_dev_asset_id=va.adj_volt_dev_asset_id
  JOIN vw_transformer t ON va.pms_equip_id=t.psrid WHERE t.runstate='20' GROUP BY v.dist_sta_id),
dp AS (SELECT m.负荷类型,c.台区编号,c.台区总容量,c.配变列表,pw.date,pw.occur_time,
    SUM(CASE WHEN m.inst_usage_cls='1102' THEN abs(pw.power) ELSE pw.power END)/c.台区总容量*100 AS rate
  FROM 计量点台区 m JOIN vw_cust_power_ts pw ON m.inst_id=pw.inst_id JOIN 台区容量 c ON m.台区编号=c.台区编号
  WHERE pw.measuerment_type='TotW'
  GROUP BY m.负荷类型,c.台区编号,c.台区总容量,c.配变列表,pw.date,pw.occur_time),
flagged AS (SELECT 负荷类型,台区编号,台区总容量,配变列表,date,occur_time,rate,
    SUM(CASE WHEN rate>=80 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号,date ORDER BY occur_time ROWS 7 PRECEDING) hr8,
    SUM(CASE WHEN rate>=100 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号,date ORDER BY occur_time ROWS 7 PRECEDING) or8 FROM dp),
daily AS (SELECT 负荷类型,台区编号,date,
    CASE WHEN MAX(or8)>=8 THEN '过载' WHEN MAX(hr8)>=8 THEN '重载' ELSE '正常' END AS 判定
  FROM flagged GROUP BY 负荷类型,台区编号,date)
SELECT date, COUNT(*) FILTER (WHERE 判定!='正常') AS 重过载台区条数,
  COUNT(*) FILTER (WHERE 判定='过载') AS 过载条数
FROM daily GROUP BY date ORDER BY date""")
for r in cur.fetchall(): print(' ',r)

# 跨天连续天数统计(去重台区, 按负荷类型判定后去重台区)
print('\n=== 跨天连续重过载天数(去重台区) ===')
cur.execute("""WITH 计量点台区 AS (
  SELECT DISTINCT
    CASE WHEN i.inst_usage_cls='01' THEN '用电负载' WHEN i.inst_usage_cls='1102' THEN '上网负载' END AS 负荷类型,
    i.inst_id, i.inst_usage_cls, i.dist_sta_id AS 台区编号
  FROM cms20_inst_elec_cons i WHERE i.inst_usage_cls IN ('01','1102')),
台区容量 AS (SELECT v.dist_sta_id AS 台区编号, SUM(t.capacity) AS cap FROM cms20_adj_volt_dev v
  JOIN cms20_adj_volt_dev_asset va ON v.adj_volt_dev_asset_id=va.adj_volt_dev_asset_id
  JOIN vw_transformer t ON va.pms_equip_id=t.psrid WHERE t.runstate='20' GROUP BY v.dist_sta_id),
dp AS (SELECT m.负荷类型,m.台区编号,pw.date,pw.occur_time,
    SUM(CASE WHEN m.inst_usage_cls='1102' THEN abs(pw.power) ELSE pw.power END)/c.cap*100 AS rate
  FROM 计量点台区 m JOIN vw_cust_power_ts pw ON m.inst_id=pw.inst_id JOIN 台区容量 c ON m.台区编号=c.台区编号
  WHERE pw.measuerment_type='TotW'
  GROUP BY m.负荷类型,m.台区编号,c.cap,pw.date,pw.occur_time),
flagged AS (SELECT 负荷类型,台区编号,date,
    SUM(CASE WHEN rate>=80 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号,date ORDER BY occur_time ROWS 7 PRECEDING) hr8,
    SUM(CASE WHEN rate>=100 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号,date ORDER BY occur_time ROWS 7 PRECEDING) or8
  FROM dp),
daily AS (SELECT 负荷类型,台区编号,date,
    CASE WHEN MAX(or8)>=8 THEN '过载' WHEN MAX(hr8)>=8 THEN '重载' ELSE '正常' END AS 判定
  FROM flagged GROUP BY 负荷类型,台区编号,date)
-- 去重台区: 某天上网或用电任一重过载则该天计入
SELECT 台区编号, COUNT(DISTINCT date) AS 重过载天数
FROM daily WHERE 判定!='正常'
GROUP BY 台区编号 ORDER BY 重过载天数 DESC, 台区编号""")
rows_dur = cur.fetchall()
for r in rows_dur: print(' ',r)
n3 = sum(1 for r in rows_dur if r[1]>=3)
n2 = sum(1 for r in rows_dur if r[1]>=2)
print(f'\n断言: 重过载台区{len(rows_dur)}台(应9); 连续>=2天{n2}台(应5,占~一半); 连续>=3天{n3}台(应3,占~三分之一)')

# 发电负荷参考统计(不判定, 仅展示8/1发电负载率≥80%台区, 应10台)
print('\n=== 发电负荷参考(8/1, 不判定, 应10台) ===')
cur.execute("""WITH 计量点台区 AS (
  SELECT DISTINCT i.inst_id, i.dist_sta_id AS 台区编号 FROM cms20_inst_elec_cons i WHERE i.inst_usage_cls='1101'),
台区容量 AS (SELECT v.dist_sta_id AS 台区编号, SUM(t.capacity) AS 台区总容量 FROM cms20_adj_volt_dev v
  JOIN cms20_adj_volt_dev_asset va ON v.adj_volt_dev_asset_id=va.adj_volt_dev_asset_id
  JOIN vw_transformer t ON va.pms_equip_id=t.psrid WHERE t.runstate='20' GROUP BY v.dist_sta_id),
dp AS (SELECT m.台区编号,c.台区总容量,pw.occur_time, SUM(pw.power)/c.台区总容量*100 AS rate
  FROM 计量点台区 m JOIN vw_cust_power_ts pw ON m.inst_id=pw.inst_id JOIN 台区容量 c ON m.台区编号=c.台区编号
  WHERE pw.measuerment_type='TotW' AND pw.date='20260801'
  GROUP BY m.台区编号,c.台区总容量,pw.occur_time),
f AS (SELECT 台区编号,台区总容量,SUM(CASE WHEN rate>=80 THEN 1 ELSE 0 END) OVER (PARTITION BY 台区编号 ORDER BY occur_time ROWS 7 PRECEDING) hr8 FROM dp)
SELECT 台区编号,MAX(hr8) AS 连续重载点 FROM f GROUP BY 台区编号,台区总容量 HAVING MAX(hr8)>=8 ORDER BY 台区编号""")
rows_gen = cur.fetchall()
for r in rows_gen: print(' ',r)
print(f'断言: 发电参考台区 {len(rows_gen)}台(应10)')

c.close()
print('\n配变数据生成完成(v5: 3天跨天持续+连续2天5台/3天3台+发电不判定+电压各半)')
