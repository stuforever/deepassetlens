-- 第2步扩展：连续N天重过载统计（跨天持续性）
-- 用户问"连续几天重过载/持续重过载/连续N天/重过载持续天数"。
-- 基于第2步分天判定，统计每个台区最长连续重过载天数及起止日期。仅统计上网+用电（发电不判定）。
-- 口径见 reference/rules.md

WITH 计量点台区 AS (
  SELECT DISTINCT
    CASE WHEN i.inst_usage_cls='01' THEN '用电负载' WHEN i.inst_usage_cls='1102' THEN '上网负载' END AS 负荷类型,
    i.inst_id, i.inst_usage_cls, i.dist_sta_id AS 台区编号
  FROM ⟦计量点⟧ i WHERE i.inst_usage_cls IN ('01','1102')
    -- 【动态】用户只看某类负荷: AND i.inst_usage_cls = '1102'
),
台区容量 AS (
  SELECT v.dist_sta_id AS 台区编号, SUM(CAST(t.capacity AS DOUBLE)) AS 台区总容量
  FROM ⟦调压设备⟧ v JOIN ⟦调压设备资产⟧ va ON v.adj_volt_dev_asset_id=va.adj_volt_dev_asset_id
  JOIN ⟦配电变压器⟧ t ON va.pms_equip_id=t.psrid WHERE t.runstate='20' GROUP BY v.dist_sta_id
),
dist_power AS (
  SELECT m.负荷类型, m.台区编号, pw.date, pw.occur_time,
    SUM(CASE WHEN m.inst_usage_cls='1102' THEN abs(pw.power) ELSE pw.power END) / c.台区总容量 * 100 AS 负载率
  FROM 计量点台区 m JOIN ⟦客户功率时序⟧ pw ON m.inst_id=pw.inst_id
  JOIN 台区容量 c ON m.台区编号=c.台区编号
  WHERE pw.measuerment_type='TotW'
    -- 【动态】用户指定日期范围: AND pw.date >= '20260801' AND pw.date <= '20260803'
  GROUP BY m.负荷类型, m.台区编号, c.台区总容量, pw.date, pw.occur_time
),
flagged AS (
  SELECT 负荷类型, 台区编号, date, 负载率,
    SUM(CASE WHEN 负载率>=80 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号,date ORDER BY occur_time ROWS 7 PRECEDING) AS hr8,
    SUM(CASE WHEN 负载率>=100 THEN 1 ELSE 0 END) OVER (PARTITION BY 负荷类型,台区编号,date ORDER BY occur_time ROWS 7 PRECEDING) AS or8
  FROM dist_power
),
daily AS (
  -- 每台区每天是否重过载(上网或用电任一达标即算该天重过载)
  SELECT 台区编号, date, BOOL_OR(or8>=8 OR hr8>=8) AS 重过载
  FROM flagged GROUP BY 台区编号, date
),
连续段 AS (
  -- 连续日期分段: 实际日期减序号=段标识, 同段标识即日期连续无断档
  -- Doris 语法: DATEDIFF 算日期差(天), CAST AS DATE 解析 'YYYYMMDD' 字符串, CAST AS INT 转整型做减法
  SELECT 台区编号, date,
    DATEDIFF(CAST(MIN(date) OVER (PARTITION BY 台区编号) AS DATE), CAST(date AS DATE)) - CAST(ROW_NUMBER() OVER (PARTITION BY 台区编号 ORDER BY date) AS INT) AS 段标识
  FROM daily WHERE 重过载
),
段统计 AS (
  SELECT 台区编号, MIN(date) AS 持续起始, MAX(date) AS 持续结束, COUNT(*) AS 连续天数
  FROM 连续段 GROUP BY 台区编号, 段标识
)
SELECT 台区编号, 连续天数, 持续起始, 持续结束
FROM 段统计
WHERE 连续天数 >= 1   -- 阈值值变化提示（strict 下按字面量规范化自动放行）：用户说"连续3天"则改 >=3，"连续2天"则改 >=2；不指定保持 >=1
ORDER BY 连续天数 DESC, 台区编号

-- 一个台区若有多段重过载（中间隔正常天），会输出多行，每行一段。
-- DATEDIFF(MIN(date), date) - ROW_NUMBER() 法保证只算日期真正连续的天数（中间断档切分成新段）。
-- 用户问"连续N天"则 WHERE 连续天数 >= N。
