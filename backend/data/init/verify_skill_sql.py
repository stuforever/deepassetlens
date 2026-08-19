# -*- coding: utf-8 -*-
"""验证 SKILL.md v5 台区级SQL(第2步+第3步) + 跨天持续 + 发电不判定 + 电压分布
v5变更: 数据3天(8/1,8/2,8/3); 重过载台区跨天持续(连续>=3天3台/连续>=2天5台); 发电不判定
"""
import psycopg2
c = psycopg2.connect(host='localhost', port=25432, user='postgres', password='postgres', dbname='tupu')
cur = c.cursor()

# ====== 电压等级分布(10kV/35kV各半) ======
print('===== 电压等级分布(非柱上配变) =====')
cur.execute("SELECT voltagelevel, COUNT(*) FROM dwd_grid_psr_ds_transformer GROUP BY voltagelevel ORDER BY voltagelevel")
for r in cur.fetchall(): print(' ', r)

# ====== 第2步: 台区级重过载判定(分天, 仅上网+用电判定, 发电不判定) ======
print('\n===== 第2步: 分天重过载判定汇总 =====')
cur.execute("""
WITH 计量点台区 AS (
  SELECT DISTINCT
    CASE WHEN i.inst_usage_cls='01' THEN '用电负载' WHEN i.inst_usage_cls='1102' THEN '上网负载' END AS 负荷类型,
    i.inst_id, i.inst_usage_cls, i.dist_sta_id AS 台区编号
  FROM cms20_inst_elec_cons i WHERE i.inst_usage_cls IN ('01','1102')),
台区容量 AS (
  SELECT v.dist_sta_id AS 台区编号, SUM(t.capacity) AS 台区总容量, STRING_AGG(t.psrid,', ') AS 配变列表
  FROM cms20_adj_volt_dev v JOIN cms20_adj_volt_dev_asset va ON v.adj_volt_dev_asset_id=va.adj_volt_dev_asset_id
  JOIN vw_transformer t ON va.pms_equip_id=t.psrid WHERE t.runstate='20' GROUP BY v.dist_sta_id),
dp AS (
  SELECT m.负荷类型,c.台区编号,c.台区总容量,c.配变列表,pw.date,pw.occur_time,
    SUM(CASE WHEN m.inst_usage_cls='1102' THEN abs(pw.power) ELSE pw.power END)/c.台区总容量*100 AS 负载率
  FROM 计量点台区 m JOIN vw_cust_power_ts pw ON m.inst_id=pw.inst_id JOIN 台区容量 c ON m.台区编号=c.台区编号
  WHERE pw.measuerment_type='TotW'
  GROUP BY m.负荷类型,c.台区编号,c.台区总容量,c.配变列表,pw.date,pw.occur_time),
flagged AS (
  SELECT 负荷类型,台区编号,台区总容量,配变列表,date,occur_time,负载率,
    SUM(CASE WHEN 负载率>=80 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号,date ORDER BY occur_time ROWS 7 PRECEDING) AS hr8,
    SUM(CASE WHEN 负载率>=100 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号,date ORDER BY occur_time ROWS 7 PRECEDING) AS or8 FROM dp),
daily AS (SELECT 负荷类型,台区编号,date,
    CASE WHEN MAX(or8)>=8 THEN '过载' WHEN MAX(hr8)>=8 THEN '重载' ELSE '正常' END AS 判定
  FROM flagged GROUP BY 负荷类型,台区编号,date)
SELECT date, COUNT(*) FILTER (WHERE 判定!='正常') AS 重过载条数,
  COUNT(*) FILTER (WHERE 判定='过载') AS 过载条数,
  COUNT(*) FILTER (WHERE 判定='重载') AS 重载条数
FROM daily GROUP BY date ORDER BY date""")
for r in cur.fetchall(): print(' ',r)

# 8/1 详细判定(应上网5条[过载2+重载3]+用电5条=10条)
print('\n===== 第2步: 8/1 详细重过载判定 =====')
cur.execute("""
WITH 计量点台区 AS (
  SELECT DISTINCT
    CASE WHEN i.inst_usage_cls='01' THEN '用电负载' WHEN i.inst_usage_cls='1102' THEN '上网负载' END AS 负荷类型,
    i.inst_id, i.inst_usage_cls, i.dist_sta_id AS 台区编号
  FROM cms20_inst_elec_cons i WHERE i.inst_usage_cls IN ('01','1102')),
台区容量 AS (
  SELECT v.dist_sta_id AS 台区编号, SUM(t.capacity) AS 台区总容量, STRING_AGG(t.psrid,', ') AS 配变列表
  FROM cms20_adj_volt_dev v JOIN cms20_adj_volt_dev_asset va ON v.adj_volt_dev_asset_id=va.adj_volt_dev_asset_id
  JOIN vw_transformer t ON va.pms_equip_id=t.psrid WHERE t.runstate='20' GROUP BY v.dist_sta_id),
dp AS (SELECT m.负荷类型,c.台区编号,c.台区总容量,c.配变列表,pw.date,pw.occur_time,
    SUM(CASE WHEN m.inst_usage_cls='1102' THEN abs(pw.power) ELSE pw.power END)/c.台区总容量*100 AS 负载率
  FROM 计量点台区 m JOIN vw_cust_power_ts pw ON m.inst_id=pw.inst_id JOIN 台区容量 c ON m.台区编号=c.台区编号
  WHERE pw.measuerment_type='TotW' AND pw.date='20260801'
  GROUP BY m.负荷类型,c.台区编号,c.台区总容量,c.配变列表,pw.date,pw.occur_time),
flagged AS (
  SELECT 负荷类型,台区编号,台区总容量,配变列表,负载率,
    SUM(CASE WHEN 负载率>=80 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号 ORDER BY occur_time ROWS 7 PRECEDING) AS hr8,
    SUM(CASE WHEN 负载率>=100 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号 ORDER BY occur_time ROWS 7 PRECEDING) AS or8 FROM dp)
SELECT 负荷类型,台区编号,配变列表,台区总容量,ROUND(MAX(负载率)::numeric,1) AS 最大负载率,
  CASE WHEN MAX(or8)>=8 THEN '过载' WHEN MAX(hr8)>=8 THEN '重载' ELSE '正常' END AS 判定
FROM flagged GROUP BY 负荷类型,台区编号,配变列表,台区总容量 HAVING MAX(hr8)>=8 ORDER BY 负荷类型,MAX(负载率) DESC""")
rows81 = cur.fetchall()
for r in rows81: print(' ',r)
up = [r for r in rows81 if r[0]=='上网负载']
el = [r for r in rows81 if r[0]=='用电负载']
print(f'断言: 8/1 上网{len(up)}条(过载{sum(1 for r in up if r[5]=="过载")},应5); 用电{len(el)}条(应5)')

# ====== 跨天连续天数统计(去重台区) ======
print('\n===== 跨天连续重过载天数(去重台区, 应9: 连续>=3天3台/连续>=2天5台) =====')
cur.execute("""
WITH 计量点台区 AS (
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
    SUM(CASE WHEN rate>=100 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号,date ORDER BY occur_time ROWS 7 PRECEDING) or8 FROM dp),
daily AS (SELECT 负荷类型,台区编号,date,
    CASE WHEN MAX(or8)>=8 THEN '过载' WHEN MAX(hr8)>=8 THEN '重载' ELSE '正常' END AS 判定
  FROM flagged GROUP BY 负荷类型,台区编号,date)
SELECT 台区编号, COUNT(DISTINCT date) AS 重过载天数
FROM daily WHERE 判定!='正常'
GROUP BY 台区编号 ORDER BY 重过载天数 DESC, 台区编号""")
rows_dur = cur.fetchall()
for r in rows_dur: print(' ',r)
n3 = sum(1 for r in rows_dur if r[1]>=3)
n2 = sum(1 for r in rows_dur if r[1]>=2)
print(f'断言: 重过载台区{len(rows_dur)}台(应9); 连续>=2天{n2}台(应5,约一半); 连续>=3天{n3}台(应3,约三分之一)')

# ====== SKILL.md 第2步扩展SQL验证(连续N天, to_date-ROW_NUMBER严谨连续段) ======
print('\n===== SKILL.md 第2步扩展: 连续N天重过载统计(严谨连续段) =====')
cur.execute("""
WITH 计量点台区 AS (
  SELECT DISTINCT
    CASE WHEN i.inst_usage_cls='01' THEN '用电负载' WHEN i.inst_usage_cls='1102' THEN '上网负载' END AS 负荷类型,
    i.inst_id, i.inst_usage_cls, i.dist_sta_id AS 台区编号
  FROM cms20_inst_elec_cons i WHERE i.inst_usage_cls IN ('01','1102')),
台区容量 AS (SELECT v.dist_sta_id AS 台区编号, SUM(t.capacity) AS 台区总容量 FROM cms20_adj_volt_dev v
  JOIN cms20_adj_volt_dev_asset va ON v.adj_volt_dev_asset_id=va.adj_volt_dev_asset_id
  JOIN vw_transformer t ON va.pms_equip_id=t.psrid WHERE t.runstate='20' GROUP BY v.dist_sta_id),
dist_power AS (SELECT m.负荷类型,m.台区编号,pw.date,pw.occur_time,
    SUM(CASE WHEN m.inst_usage_cls='1102' THEN abs(pw.power) ELSE pw.power END)/c.台区总容量*100 AS 负载率
  FROM 计量点台区 m JOIN vw_cust_power_ts pw ON m.inst_id=pw.inst_id JOIN 台区容量 c ON m.台区编号=c.台区编号
  WHERE pw.measuerment_type='TotW'
  GROUP BY m.负荷类型,m.台区编号,c.台区总容量,pw.date,pw.occur_time),
flagged AS (SELECT 负荷类型,台区编号,date,负载率,
    SUM(CASE WHEN 负载率>=80 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号,date ORDER BY occur_time ROWS 7 PRECEDING) hr8,
    SUM(CASE WHEN 负载率>=100 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号,date ORDER BY occur_time ROWS 7 PRECEDING) or8 FROM dist_power),
daily AS (SELECT 台区编号,date, BOOL_OR(or8>=8 OR hr8>=8) AS 重过载 FROM flagged GROUP BY 台区编号,date),
连续段 AS (SELECT 台区编号,date,
    to_date(date,'YYYYMMDD') - (ROW_NUMBER() OVER (PARTITION BY 台区编号 ORDER BY date))::int AS 段标识
  FROM daily WHERE 重过载),
段统计 AS (SELECT 台区编号, MIN(date) AS 持续起始, MAX(date) AS 持续结束, COUNT(*) AS 连续天数
  FROM 连续段 GROUP BY 台区编号, 段标识)
SELECT 台区编号, 连续天数, 持续起始, 持续结束
FROM 段统计 ORDER BY 连续天数 DESC, 台区编号""")
rows_ext = cur.fetchall()
for r in rows_ext: print(' ',r)
ext3 = sum(1 for r in rows_ext if r[1]>=3)
ext2 = sum(1 for r in rows_ext if r[1]>=2)
print(f'断言: 连续段{len(rows_ext)}段(应9); 连续>=2天{ext2}段(应5); 连续>=3天{ext3}段(应3)')

# ====== 发电负荷参考统计(不判定, 8/1, 应10台) ======
print('\n===== 发电负荷参考(8/1, 不判定, 应10台: 上台5+自发自用5) =====')
cur.execute("""
WITH 计量点台区 AS (
  SELECT DISTINCT i.inst_id, i.dist_sta_id AS 台区编号 FROM cms20_inst_elec_cons i WHERE i.inst_usage_cls='1101'),
台区容量 AS (SELECT v.dist_sta_id AS 台区编号, SUM(t.capacity) AS 台区总容量 FROM cms20_adj_volt_dev v
  JOIN cms20_adj_volt_dev_asset va ON v.adj_volt_dev_asset_id=va.adj_volt_dev_asset_id
  JOIN vw_transformer t ON va.pms_equip_id=t.psrid WHERE t.runstate='20' GROUP BY v.dist_sta_id),
dp AS (SELECT m.台区编号,c.台区总容量,pw.occur_time, SUM(pw.power)/c.台区总容量*100 AS rate
  FROM 计量点台区 m JOIN vw_cust_power_ts pw ON m.inst_id=pw.inst_id JOIN 台区容量 c ON m.台区编号=c.台区编号
  WHERE pw.measuerment_type='TotW' AND pw.date='20260801'
  GROUP BY m.台区编号,c.台区总容量,pw.occur_time),
f AS (SELECT 台区编号,台区总容量,SUM(CASE WHEN rate>=80 THEN 1 ELSE 0 END) OVER (PARTITION BY 台区编号 ORDER BY occur_time ROWS 7 PRECEDING) hr8 FROM dp)
SELECT 台区编号,台区总容量,MAX(hr8) AS 连续重载点
FROM f GROUP BY 台区编号,台区总容量 HAVING MAX(hr8)>=8 ORDER BY 台区编号""")
rows_gen = cur.fetchall()
for r in rows_gen: print(' ',r)
print(f'断言: 发电参考台区 {len(rows_gen)}台(应10)')

# ====== 第3步: 客户倒排(8/1, 多计量点先SUM后AVG, 仅上网+用电) ======
print('\n===== 第3步: 客户负载占有率倒排(8/1, 上网+用电) =====')
cur.execute("""
WITH 户变关系 AS (
  SELECT '用电户' AS 客户类型, ec.elec_cons_cust_id AS 客户编号, c.cust_name,
    i.inst_id, i.inst_usage_cls, CASE WHEN i.inst_usage_cls='01' THEN '用电负载' END AS 负荷类型, i.dist_sta_id AS 台区编号
  FROM cms20_elec_cons_cust ec JOIN cms20_cst_cust c ON ec.cust_id=c.cust_id
  JOIN cms20_inst_elec_cons i ON ec.elec_cons_cust_id=i.elec_cons_cust_id WHERE i.inst_usage_cls='01' AND i.elec_cons_cust_id IS NOT NULL
  UNION ALL
  SELECT '发电户' AS 客户类型, g.gpc_id AS 客户编号, c.cust_name,
    i.inst_id, i.inst_usage_cls,
    CASE WHEN i.inst_usage_cls='1102' THEN '上网负载' END AS 负荷类型, i.dist_sta_id AS 台区编号
  FROM dwd_cst_gpc g JOIN cms20_cst_cust c ON g.cust_id=c.cust_id
  JOIN cms20_inst_elec_cons i ON g.gpc_id=i.gpc_id WHERE i.inst_usage_cls='1102' AND i.gpc_id IS NOT NULL),
台区容量 AS (SELECT v.dist_sta_id AS 台区编号, SUM(t.capacity) AS 台区总容量, STRING_AGG(t.psrid,', ') AS 配变列表
  FROM cms20_adj_volt_dev v JOIN cms20_adj_volt_dev_asset va ON v.adj_volt_dev_asset_id=va.adj_volt_dev_asset_id
  JOIN vw_transformer t ON va.pms_equip_id=t.psrid WHERE t.runstate='20' GROUP BY v.dist_sta_id),
dist_power AS (
  SELECT r.负荷类型,r.台区编号,c.台区总容量,c.配变列表,pw.date,pw.occur_time,
    SUM(CASE WHEN r.inst_usage_cls='1102' THEN abs(pw.power) ELSE pw.power END)/c.台区总容量*100 AS 负载率
  FROM (SELECT DISTINCT 负荷类型,inst_id,inst_usage_cls,台区编号 FROM 户变关系) r
  JOIN vw_cust_power_ts pw ON r.inst_id=pw.inst_id JOIN 台区容量 c ON r.台区编号=c.台区编号
  WHERE pw.measuerment_type='TotW' AND pw.date='20260801'
  GROUP BY r.负荷类型,r.台区编号,c.台区总容量,c.配变列表,pw.date,pw.occur_time),
flagged AS (
  SELECT 负荷类型,台区编号,台区总容量,配变列表,date,occur_time,负载率,
    SUM(CASE WHEN 负载率>=80 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号,date ORDER BY occur_time ROWS 7 PRECEDING) AS hr8,
    SUM(CASE WHEN 负载率>=100 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号,date ORDER BY occur_time ROWS 7 PRECEDING) AS or8 FROM dist_power),
verdicts AS (SELECT 负荷类型,台区编号,台区总容量,配变列表,
    CASE WHEN MAX(or8)>=8 THEN '过载' WHEN MAX(hr8)>=8 THEN '重载' ELSE '正常' END AS 判定
  FROM flagged GROUP BY 负荷类型,台区编号,台区总容量,配变列表),
over_pts AS (SELECT f.负荷类型,f.台区编号,f.occur_time,f.date FROM flagged f JOIN verdicts v ON v.负荷类型=f.负荷类型 AND v.台区编号=f.台区编号
  WHERE (v.判定='过载' AND f.负载率>=100) OR (v.判定='重载' AND f.负载率>=80)),
cust_agg AS (
  SELECT r.客户类型,r.负荷类型,r.客户编号,r.cust_name,r.台区编号,c.台区总容量,c.配变列表,pw.date,pw.occur_time,
    SUM(CASE WHEN r.inst_usage_cls='1102' THEN abs(pw.power) ELSE pw.power END) AS 客户负载_kw
  FROM 户变关系 r JOIN vw_cust_power_ts pw ON r.inst_id=pw.inst_id
  JOIN 台区容量 c ON r.台区编号=c.台区编号
  JOIN over_pts o ON o.负荷类型=r.负荷类型 AND o.台区编号=r.台区编号 AND o.occur_time=pw.occur_time AND o.date=pw.date
  WHERE pw.measuerment_type='TotW'
  GROUP BY r.客户类型,r.负荷类型,r.客户编号,r.cust_name,r.台区编号,c.台区总容量,c.配变列表,pw.date,pw.occur_time)
SELECT 客户类型,负荷类型,客户编号,cust_name AS 客户名称,台区编号,配变列表,台区总容量,
  COUNT(*) AS 达标点数, ROUND(AVG(客户负载_kw)::numeric,1) AS 平均负载_kW,
  ROUND(AVG(客户负载_kw)/台区总容量*100::numeric,1) AS 负载占有率
FROM cust_agg GROUP BY 客户类型,负荷类型,客户编号,cust_name,台区编号,配变列表,台区总容量
ORDER BY 负荷类型,负载占有率 DESC
""")
for r in cur.fetchall(): print(' ',r)

# ====== 验证: 一户多号独立计量点 + 无笛卡尔积 + 码值名列 ======
print('\n===== 验证: 一户多号独立计量点(gpc_id=901应挂台区2, 不与gpc_id=1共享台区1) =====')
cur.execute("SELECT inst_id, inst_usage_cls, inst_usage_cls_name, gpc_id, elec_cons_cust_id, dist_sta_id FROM cms20_inst_elec_cons WHERE cust_id=1 ORDER BY inst_id")
rows_c1 = cur.fetchall()
for r in rows_c1: print(' ', r)
g901_sta = set(r[5] for r in rows_c1 if r[3]==901)
g1_sta = set(r[5] for r in rows_c1 if r[3]==1)
print(f'断言: cust_id=1 共{len(rows_c1)}计量点; gpc_id=1在台区{g1_sta}(应{{1}}); gpc_id=901在台区{g901_sta}(应{{2}})')

print('\n===== 验证: 第1步户变关系无笛卡尔积(发电户号×2计量点) =====')
cur.execute("""SELECT COUNT(*) FROM (
  SELECT g.gpc_id, i.inst_id FROM dwd_cst_gpc g
  JOIN cms20_inst_elec_cons i ON g.gpc_id=i.gpc_id
  WHERE i.inst_usage_cls IN ('1101','1102') AND i.gpc_id IS NOT NULL) t""")
n_relate = cur.fetchone()[0]
print(f'断言: 发电户户变关系 {n_relate}行(应202=101户号×2, 无笛卡尔积假数据)')

print('\n===== 验证: 码值名列非空且与编码一致 =====')
cur.execute("SELECT COUNT(*) FROM cms20_inst_elec_cons WHERE inst_usage_cls_name IS NULL OR inst_usage_cls_name=''")
print('断言: inst_usage_cls_name 空值数(应0):', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM cms20_inst_elec_cons WHERE inst_usage_cls='1102' AND inst_usage_cls_name<>'上网'")
print('断言: 1102->上网 不一致数(应0):', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM vw_transformer WHERE voltagelevel='AC00101' AND voltagelevel_name<>'10kV'")
print('断言: AC00101->10kV 不一致数(应0):', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM dwd_cst_gpc WHERE cust_pscateg='01' AND cust_pscateg_name<>'分布式光伏'")
print('断言: 电源01->分布式光伏 不一致数(应0):', cur.fetchone()[0])

# ====== 验证: 多路台区(应5个, 台区96-100各2配变) ======
print('\n===== 验证: 多路台区拓扑(应5个) =====')
cur.execute("""SELECT v.dist_sta_id AS 台区, COUNT(DISTINCT va.pms_equip_id) AS 配变数, STRING_AGG(t.psrid,',') AS 配变列表
  FROM cms20_adj_volt_dev v JOIN cms20_adj_volt_dev_asset va ON v.adj_volt_dev_asset_id=va.adj_volt_dev_asset_id
  JOIN vw_transformer t ON va.pms_equip_id=t.psrid WHERE t.runstate='20'
  GROUP BY v.dist_sta_id HAVING COUNT(DISTINCT va.pms_equip_id)>1 ORDER BY v.dist_sta_id""")
multi = cur.fetchall()
for r in multi: print(' ',r)
print(f'断言: 多路台区 {len(multi)}个(应5)')

c.close()
print('\n验证完成(v5: 3天跨天持续+连续2天5台/3天3台+发电不判定+电压各半+多路5)')
