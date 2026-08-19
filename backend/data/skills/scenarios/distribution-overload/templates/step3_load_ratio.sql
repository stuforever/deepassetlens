-- 第3步：客户负载占有率倒排（重过载达标时段内，多计量点先SUM后AVG）
-- 用户问"负载占有率/倒排/排序/影响最大/哪些用户受影响"。执行第1步+第2步+第3步。
-- 口径见 reference/rules.md（负载占有率=达标时段客户平均负载/台区总容量×100%）

WITH 户变关系 AS (
  -- 带客户编号+台区(不JOIN配变,避免多路翻倍); 仅上网+用电参与倒排,发电不参与
  -- 户号精确关联(gpc_id/elec_cons_cust_id), 防一户多号笛卡尔积
  SELECT '用电户' AS 客户类型, ec.elec_cons_cust_id AS 客户编号, c.cust_name,
    i.inst_id, i.inst_usage_cls,
    CASE WHEN i.inst_usage_cls='01' THEN '用电负载' END AS 负荷类型,
    i.dist_sta_id AS 台区编号
  FROM ⟦用电户⟧ ec
  JOIN ⟦能源客户⟧ c ON ec.cust_id = c.cust_id
  JOIN ⟦计量点⟧ i ON ec.elec_cons_cust_id = i.elec_cons_cust_id
  WHERE i.inst_usage_cls = '01' AND i.elec_cons_cust_id IS NOT NULL
  -- 【动态】用户限定客户: AND c.cust_name IN ('客户001','客户003')
  UNION ALL
  SELECT '发电户' AS 客户类型, g.gpc_id AS 客户编号, c.cust_name,
    i.inst_id, i.inst_usage_cls,
    CASE WHEN i.inst_usage_cls='1102' THEN '上网负载' END AS 负荷类型,
    i.dist_sta_id AS 台区编号
  FROM ⟦发电户⟧ g
  JOIN ⟦能源客户⟧ c ON g.cust_id = c.cust_id
  JOIN ⟦计量点⟧ i ON g.gpc_id = i.gpc_id
  WHERE i.inst_usage_cls = '1102' AND i.gpc_id IS NOT NULL
  -- 【动态】用户限定客户: AND c.cust_name IN ('客户001','客户003')
),
台区容量 AS (
  SELECT v.dist_sta_id AS 台区编号, SUM(t.capacity) AS 台区总容量,
    GROUP_CONCAT(t.psrid, ', ') AS 配变列表
  FROM ⟦调压设备⟧ v
  JOIN ⟦调压设备资产⟧ va ON v.adj_volt_dev_asset_id = va.adj_volt_dev_asset_id
  JOIN ⟦配电变压器⟧ t ON va.pms_equip_id = t.psrid
  WHERE t.runstate = '20'
  GROUP BY v.dist_sta_id
),
dist_power AS (
  SELECT r.负荷类型, r.台区编号, c.台区总容量, c.配变列表, pw.date, pw.occur_time,
    SUM(CASE WHEN r.inst_usage_cls='1102' THEN abs(pw.power) ELSE pw.power END) AS 负载_kw,
    SUM(CASE WHEN r.inst_usage_cls='1102' THEN abs(pw.power) ELSE pw.power END) / c.台区总容量 * 100 AS 负载率
  FROM (SELECT DISTINCT 负荷类型, inst_id, inst_usage_cls, 台区编号 FROM 户变关系) r
  JOIN ⟦客户功率时序⟧ pw ON r.inst_id = pw.inst_id
  JOIN 台区容量 c ON r.台区编号 = c.台区编号
  WHERE pw.measuerment_type = 'TotW'
    -- 【动态】用户指定日期: AND pw.date = '20260801'
  GROUP BY r.负荷类型, r.台区编号, c.台区总容量, c.配变列表, pw.date, pw.occur_time
),
flagged AS (
  SELECT 负荷类型, 台区编号, 台区总容量, 配变列表, date, occur_time, 负载率,
    SUM(CASE WHEN 负载率 >= 80 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型, 台区编号, date ORDER BY occur_time ROWS 7 PRECEDING) AS heavy_run8,
    SUM(CASE WHEN 负载率 >= 100 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型, 台区编号, date ORDER BY occur_time ROWS 7 PRECEDING) AS over_run8
  FROM dist_power
),
verdicts AS (
  SELECT 负荷类型, 台区编号, 台区总容量, 配变列表,
    CASE WHEN MAX(over_run8) >= 8 THEN '过载' WHEN MAX(heavy_run8) >= 8 THEN '重载' ELSE '正常' END AS 判定
  FROM flagged GROUP BY 负荷类型, 台区编号, 台区总容量, 配变列表
),
over_pts AS (
  SELECT f.负荷类型, f.台区编号, f.occur_time, f.date
  FROM flagged f JOIN verdicts v ON v.负荷类型 = f.负荷类型 AND v.台区编号 = f.台区编号
  WHERE (v.判定 = '过载' AND f.负载率 >= 100)
     OR (v.判定 = '重载' AND f.负载率 >= 80)
),
-- 多计量点客户: 先SUM同一客户各计量点功率(得到客户在该时间点真实总负载)
cust_agg AS (
  SELECT r.客户类型, r.负荷类型, r.客户编号, r.cust_name,
    r.台区编号, c.台区总容量, c.配变列表, pw.date, pw.occur_time,
    SUM(CASE WHEN r.inst_usage_cls='1102' THEN abs(pw.power) ELSE pw.power END) AS 客户负载_kw
  FROM 户变关系 r
  JOIN ⟦客户功率时序⟧ pw ON r.inst_id = pw.inst_id
  JOIN 台区容量 c ON r.台区编号 = c.台区编号
  JOIN over_pts o ON o.负荷类型 = r.负荷类型 AND o.台区编号 = r.台区编号 AND o.occur_time = pw.occur_time AND o.date = pw.date
  WHERE pw.measuerment_type = 'TotW'
  GROUP BY r.客户类型, r.负荷类型, r.客户编号, r.cust_name, r.台区编号, c.台区总容量, c.配变列表, pw.date, pw.occur_time
)
-- 再AVG跨达标时间点取平均
SELECT 客户类型, 负荷类型, 客户编号, cust_name AS 客户名称,
       台区编号, 配变列表, 台区总容量,
       COUNT(*) AS 达标点数,
       ROUND(AVG(客户负载_kw), 1) AS 平均负载_kW,
       ROUND(AVG(客户负载_kw) / 台区总容量 * 100, 1) AS 负载占有率
FROM cust_agg
GROUP BY 客户类型, 负荷类型, 客户编号, cust_name, 台区编号, 配变列表, 台区总容量
ORDER BY 负荷类型, 负载占有率 DESC

-- 多计量点客户先 SUM 各计量点功率再 AVG（直接AVG会低估多计量点客户负载）。
-- 分负荷类型倒排（仅上网+用电，发电不参与）。over_pts JOIN 带date防跨天。
