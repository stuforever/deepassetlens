-- 第2步：台区级96点功率汇集，分负荷类型判定重载/过载（含时段）
-- 用户问"重载/过载/负载率/96点功率/用电负载/上网负载/发电负载"。执行第1步+第2步。
-- 仅判定上网+用电；发电负载(1101)不判定，结论中作参考提及。
-- 口径定义见 reference/rules.md（负载率=台区功率/台区总容量，重载≥80%连续8点，过载≥100%连续8点）

WITH 计量点台区 AS (
  -- 计量点->台区(不JOIN配变,避免多路供电笛卡尔积翻倍); 仅上网+用电判定,发电不判定
  SELECT DISTINCT
    CASE WHEN i.inst_usage_cls='01' THEN '用电负载'
         WHEN i.inst_usage_cls='1102' THEN '上网负载' END AS 负荷类型,
    i.inst_id, i.inst_usage_cls, i.dist_sta_id AS 台区编号
  FROM ⟦计量点⟧ i
  WHERE i.inst_usage_cls IN ('01','1102')
    -- 【动态】用户只看某类负荷: AND i.inst_usage_cls = '1102'
    -- 【动态】用户指定计量点状态: AND i.inst_stat = '02'
),
台区容量 AS (
  -- 配变->台区, SUM容量(多路台区容量汇总), 配变列表
  SELECT v.dist_sta_id AS 台区编号,
    SUM(t.capacity) AS 台区总容量,
    GROUP_CONCAT(t.psrid, ', ') AS 配变列表,
    GROUP_CONCAT(t.equipname, ', ') AS 配变名称列表
  FROM ⟦调压设备⟧ v
  JOIN ⟦调压设备资产⟧ va ON v.adj_volt_dev_asset_id = va.adj_volt_dev_asset_id
  JOIN ⟦配电变压器⟧ t ON va.pms_equip_id = t.psrid
  WHERE t.runstate = '20'
  GROUP BY v.dist_sta_id
),
dist_power AS (
  -- 台区级功率汇总(分负荷类型) / 台区总容量 = 负载率
  SELECT m.负荷类型, c.台区编号, c.台区总容量, c.配变列表, c.配变名称列表,
         pw.date, pw.occur_time,
         SUM(CASE WHEN m.inst_usage_cls='1102' THEN abs(pw.power) ELSE pw.power END) AS 负载_kw,
         SUM(CASE WHEN m.inst_usage_cls='1102' THEN abs(pw.power) ELSE pw.power END) / c.台区总容量 * 100 AS 负载率
  FROM 计量点台区 m
  JOIN ⟦客户功率时序⟧ pw ON m.inst_id = pw.inst_id
  JOIN 台区容量 c ON m.台区编号 = c.台区编号
  WHERE pw.measuerment_type = 'TotW'
    -- 【动态】用户指定日期: AND pw.date = '20260801'
  GROUP BY m.负荷类型, c.台区编号, c.台区总容量, c.配变列表, c.配变名称列表, pw.date, pw.occur_time
),
flagged AS (
  SELECT 负荷类型, 台区编号, 台区总容量, 配变列表, 配变名称列表, date, occur_time, 负载_kw, 负载率,
    SUM(CASE WHEN 负载率 >= 80 THEN 1 ELSE 0 END)
      OVER (PARTITION BY 负荷类型, 台区编号, date ORDER BY occur_time ROWS 7 PRECEDING) AS heavy_run8,
    SUM(CASE WHEN 负载率 >= 100 THEN 1 ELSE 0 END)
      OVER (PARTITION BY 负荷类型, 台区编号, date ORDER BY occur_time ROWS 7 PRECEDING) AS over_run8
  FROM dist_power
)
SELECT 负荷类型, 台区编号, 配变列表, 配变名称列表, 台区总容量,
       MAX(负载率) AS 最大负载率, MAX(负载_kw) AS 最大功率,
       SUM(CASE WHEN 负载率 >= 80 THEN 1 ELSE 0 END) AS 重载点数,
       SUM(CASE WHEN 负载率 >= 100 THEN 1 ELSE 0 END) AS 过载点数,
       MAX(heavy_run8) AS 最长连续重载, MAX(over_run8) AS 最长连续过载,
       MIN(CASE WHEN 负载率 >= 100 THEN occur_time END) AS 过载时段起,
       MAX(CASE WHEN 负载率 >= 100 THEN occur_time END) AS 过载时段止,
       MIN(CASE WHEN 负载率 >= 80 THEN occur_time END) AS 重载时段起,
       MAX(CASE WHEN 负载率 >= 80 THEN occur_time END) AS 重载时段止,
       CASE WHEN MAX(over_run8) >= 8 THEN '过载'
            WHEN MAX(heavy_run8) >= 8 THEN '重载'
            ELSE '正常' END AS 判定
FROM flagged
GROUP BY 负荷类型, 台区编号, 配变列表, 配变名称列表, 台区总容量
ORDER BY 负荷类型, 最大负载率 DESC

-- 多路供电台区(配变列表含多个)的负载率 = 台区功率 / 台区总容量(配变容量之和)。
-- 单路台区(1配变)与多路台区统一计算。用户指定日期则加 AND pw.date='YYYYMMDD'。
