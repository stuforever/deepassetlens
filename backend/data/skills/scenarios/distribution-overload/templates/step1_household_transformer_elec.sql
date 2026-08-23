-- 第1步·用电户单段变体：户变关系（计量点为枢纽，展示台区+配变列表）
-- 用户只问"用电户与配变/户变关系(仅用电)"时使用本变体；问两者/泛问用 step1_household_transformer.sql（UNION 全量）。
-- 【同源】本文件与 step1_household_transformer.sql 的用电户段同源（CTE/JOIN 链一致）；改结构须三处同步：
--   UNION 模板(step1_household_transformer.sql) + 用电户变体(本文件) + 发电户变体(step1_household_transformer_gen.sql)。
-- 列名已与元数据核对一致（2026-08 实测），直接使用。仅当 SQL 执行报列名错误时调 search_entities 排查。
-- 关联口径（与 mock/真实表结构核对）：
--   * 用电户 dim_cst_elec_cons_cust.cust_id = 计量点 dim_cst_inst_elec_cons.cust_id（前缀一致，可精确关联）
--   * 计量点.dist_sta_id -> 台区 dim_cst_dist_sta.dist_sta_id（台区容量用台区表 dist_stacap）
--   * 台区 -> 调压设备 cms20_adj_volt_dev.dist_sta_id -> 资产 -> 配电变压器（配变列表 GROUP_CONCAT）
--   * 能源客户 cms20_cst_cust.cust_id 为数字（'1'），与用电户 CUS 前缀不同，**禁止用能源客户关联用电户**
--   * 计量点 inst_usage_cls 为中文业务码（如'安装点用途分类_1'），**禁止用 '01' 硬过滤**
-- 用户限定客户时，先读 reference/scope_cte.md 用模板B（WITH 目标客户 CTE 先锁客户再关联）。

WITH 台区配变 AS (
  -- 台区->配变列表（多路台区显示多个配变）；台区总容量取台区表 dist_stacap（配变表无容量列）
  SELECT v.dist_sta_id AS 台区编号,
    GROUP_CONCAT(t.psrid, ', ') AS 配变列表,
    GROUP_CONCAT(t.equipname, ', ') AS 配变名称列表,
    MAX(t.volt_lvl_dsc) AS 电压等级
  FROM ⟦调压设备⟧ v
  JOIN ⟦调压设备资产⟧ va ON v.adj_volt_dev_asset_id = va.adj_volt_dev_asset_id
  JOIN ⟦配电变压器⟧ t ON va.pms_equip_id = t.psrid
  GROUP BY v.dist_sta_id
)
-- 用电户 <-> 台区/配变 (用电户 cust_id 精确关联计量点)
SELECT '用电户' AS 客户类型,
       ec.elec_cons_cust_id AS 客户编号, ec.cust_name, ec.cust_no, ec.ind_cls_name AS 行业分类,
       ec.cust_cls_name AS 客户分类, ec.ecc_stat_name AS 客户状态,
       i.inst_id AS 计量点编号, i.inst_cls_name AS 安装点分类, i.inst_usage_cls_name AS 用途类型, i.inst_stat_name AS 安装点状态,
       i.dist_sta_id AS 台区编号, ds.resrc_supl_name AS 台区名称, ds.dist_stacap AS 台区总容量,
       tp.配变列表, tp.电压等级 AS 电压等级
FROM ⟦用电户⟧ ec
JOIN ⟦计量点⟧ i ON ec.cust_id = i.cust_id
LEFT JOIN ⟦台区⟧ ds ON i.dist_sta_id = ds.dist_sta_id
LEFT JOIN 台区配变 tp ON i.dist_sta_id = tp.台区编号
WHERE i.inst_id IS NOT NULL
  -- 【动态】用户指定客户状态: AND ec.ecc_stat = '01'
  -- 【动态】用户指定客户分类: AND ec.cust_cls = '01'
  -- 【动态】用户限定客户: AND ec.cust_name IN ('客户001','客户003')
ORDER BY 台区编号, 计量点编号

-- 多路供电台区的配变列表会显示多个(如"RES0003, RES0006, RES0009")。一个客户可能出现在多行(多计量点)。
-- 一户多号：同一 cust_id 有多个户号时，各户号挂各自独立计量点(不同台区)，按 cust_id 精确关联不产生笛卡尔积。
-- 码值列均带 _name 中文名，输出时优先显示中文。本变体仅返回用电户段（结构冻结：不对 UNION 模板做删段，改用本变体表达单类型问法）。
