-- 第1步：户变关系（计量点为枢纽，展示台区+配变列表）
-- 用户问"户变关系/用电户与配变关系/发电户与配变关系"。仅执行此步，返回关系明细。
-- 列名已与元数据核对一致，直接使用。仅当 SQL 执行报列名错误时调 search_entities 排查。
-- 用户限定客户时，先读 reference/scope_cte.md 用模板B（WITH 目标客户 CTE 先锁客户再关联）。

WITH 台区配变 AS (
  -- 台区->配变列表+总容量(多路台区显示多个配变)
  SELECT v.dist_sta_id AS 台区编号,
    SUM(t.capacity) AS 台区总容量,
    GROUP_CONCAT(t.psrid, ', ') AS 配变列表,
    GROUP_CONCAT(t.equipname, ', ') AS 配变名称列表,
    MAX(t.voltagelevel) AS 电压等级, MAX(t.voltagelevel_name) AS 电压等级名
  FROM ⟦调压设备⟧ v
  JOIN ⟦调压设备资产⟧ va ON v.adj_volt_dev_asset_id = va.adj_volt_dev_asset_id
  JOIN ⟦配电变压器⟧ t ON va.pms_equip_id = t.psrid
  WHERE t.runstate = '20'
  GROUP BY v.dist_sta_id
)
-- 用电户 <-> 台区/配变 (用电户号精确关联计量点, 防一户多号笛卡尔积)
SELECT '用电户' AS 客户类型,
       ec.elec_cons_cust_id AS 客户编号, c.cust_name, c.cust_no, c.ind_cls_name AS 行业分类,
       ec.cust_cls_name AS 客户分类, ec.ecc_stat_name AS 客户状态,
       i.inst_id AS 计量点编号, i.inst_cls_name AS 安装点分类, i.inst_usage_cls_name AS 用途类型, i.inst_stat_name AS 安装点状态,
       i.dist_sta_id AS 台区编号, ds.resrc_supl_name AS 台区名称,
       tp.配变列表, tp.台区总容量, tp.电压等级名 AS 电压等级
FROM ⟦用电户⟧ ec
JOIN ⟦能源客户⟧ c ON ec.cust_id = c.cust_id
JOIN ⟦计量点⟧ i ON ec.elec_cons_cust_id = i.elec_cons_cust_id
LEFT JOIN ⟦台区⟧ ds ON i.dist_sta_id = ds.dist_sta_id
LEFT JOIN 台区配变 tp ON i.dist_sta_id = tp.台区编号
WHERE i.inst_usage_cls = '01' AND i.elec_cons_cust_id IS NOT NULL
  -- 【动态】用户指定客户状态: AND ec.ecc_stat = '01'
  -- 【动态】用户指定客户分类: AND ec.cust_cls = '01'
  -- 【动态】用户限定客户: AND c.cust_name IN ('客户001','客户003')
UNION ALL
-- 发电户 <-> 台区/配变 (发电户号精确关联计量点, 防一户多号笛卡尔积)
SELECT '发电户' AS 客户类型,
       g.gpc_id AS 客户编号, c.cust_name, c.cust_no, c.ind_cls_name AS 行业分类,
       g.cust_pscateg_name AS 客户分类, g.gc_stat_name AS 客户状态,
       i.inst_id AS 计量点编号, i.inst_cls_name AS 安装点分类, i.inst_usage_cls_name AS 用途类型, i.inst_stat_name AS 安装点状态,
       i.dist_sta_id AS 台区编号, ds.resrc_supl_name AS 台区名称,
       tp.配变列表, tp.台区总容量, tp.电压等级名 AS 电压等级
FROM ⟦发电户⟧ g
JOIN ⟦能源客户⟧ c ON g.cust_id = c.cust_id
JOIN ⟦计量点⟧ i ON g.gpc_id = i.gpc_id
LEFT JOIN ⟦台区⟧ ds ON i.dist_sta_id = ds.dist_sta_id
LEFT JOIN 台区配变 tp ON i.dist_sta_id = tp.台区编号
WHERE i.inst_usage_cls IN ('1101','1102') AND i.gpc_id IS NOT NULL
  -- 【动态】用户指定电源类别: AND g.cust_pscateg = '01'
  -- 【动态】用户只看上网: AND i.inst_usage_cls = '1102'
  -- 【动态】用户限定客户: AND c.cust_name IN ('客户001','客户003')
ORDER BY 客户类型, 台区编号, 计量点编号

-- 多路供电台区的配变列表会显示多个(如"T096, T097")。一个客户可能出现在多行(多计量点)。
-- 一户多号：同一 cust_id 有多个发电户号(gpc_id)时，各 gpc_id 挂各自独立计量点(不同台区)，
-- 本查询按 gpc_id 精确关联，不产生笛卡尔积假数据。码值列均带 _name 中文名，输出时优先显示中文。
