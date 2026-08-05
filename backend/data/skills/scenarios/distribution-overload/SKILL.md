---
name: distribution-overload
description: 配电重载过载分析（配电层面96点功率累加判定+户变关系影响分析）。何时用：用户问"配电重载/过载/96点功率/配电层面功率/累加功率/户变关系/受影响用户"。
category: scenario
---

# 配电重载过载分析（场景剧本·模块化）

本剧本按用户描述的配电关联链路固化：**配电变压器 → 调压设备资产 → 调压设备运行(运营) → 台区 → 安装点(计量点) → 电能表/计量点负荷 → 96点功率累加到配电 → 连续8点判定重载/过载 → 户变关系查受影响用户**。

剧本分 **6 个模块操作**，用户可随时只查其中一段（如"只看某变压器关联的台区"/"只查受影响用户"/"只看判定结果"）。命中后按用户问题覆盖的模块执行，不必全跑。

## 触发条件
满足任一即命中（与 transformer-overload 区分：本剧本强调**配电层面**累加 + 96点 + 户变关系）：
1. 含"配电"+"重载/过载/负载/功率/96点/累加"
2. 含"配电层面功率"/"配电功率曲线"/"96点功率"
3. 含"户变关系"/"受影响用户"/"影响最大"/"影响分析"（且上下文是配电/变压器重载）
4. 含"调压设备"+"配电"（查关联链路）
5. 含"哪些用户受影响"/"用户影响排序"（配电重载上下文）

## 数据表与关联键（物理表，走 execute_sql，全在 pg_tupu.public）

| 角色 | 表名 | 关键列 | 说明 |
|---|---|---|---|
| 配电变压器 | `dim_grid_pub_dist_trans_resrc_standbk_e` | astid, equipname, capacity(varchar须CAST), blg_stat_nm, detail_addr, run_st_dsc, volt_lvl_dsc, op_maint_org_nm, **voltreg_eqp_id**, **voltreg_eqp_asst_id**, voltreg_eqp_no | capacity是varchar，SQL须 CAST(... AS DECIMAL) |
| 调压设备资产 | `cms20_adj_volt_dev_asset` | adj_volt_dev_asset_id(decimal), pms_equip_id | 关联PMS设备 |
| 调压设备运行 | `cms20_adj_volt_dev` | adj_volt_dev_id(decimal), adj_volt_dev_asset_id(decimal), cust_id, **dist_sta_id** | **关联台区的关键桥** |
| 台区 | `dim_cst_dist_sta` | dist_sta_id, resrc_supl_name, dist_stacap(double 台区容量), voltage, mgt_org_name | |
| 安装点/计量点 | `dim_cst_inst_elec_cons` | inst_id, **cust_id**, **dist_sta_id**, dist_sta_name, voltage, inst_cap | **户变关系桥**：同时有cust_id和dist_sta_id |
| 计量点负荷 | `dwd_cst_mtcl_inst_load_min` | inst_id, occur_time, `load`(double,须反引号) | **配电层面功率主数据源**：已聚合到计量点 |
| 电能表功率 | `dwd_cst_mtcl_meter_power_min` | meter_id, occur_time, p(double 有功功率), p_a/p_b/p_c(三相) | 备选源（meter-inst无直链时降级用inst_load） |
| 电能表主数据 | `dim_cst_meter` | meter_id, asset_no, dev_type_name, mgt_org_name | 电能表台账（查挂表用） |
| 用电客户 | `dim_cst_elec_cons_cust` | cust_id, cust_name, voltage_name, ctrt_cap(合同容量), run_cap(运行容量), scy_cap(保安容量), impt_lv_name(重要等级), bus_srv_addr_name(用电地址) | 户变关系终端 |
| 停电影响用户 | `dwd_cst_srv_poweroff_affect_cons_dtl` | poweroff_info_no, cons_id, cons_nm, imp_cust_flg_dsc(重要客户), sensitive_cust_flg_dsc(敏感客户), tg_no, tg_nm, eqp_no, eqp_nm | 影响分析辅助表 |

### 关联键链（已验证可JOIN）
```
配电变压器.astid
  ├─ .voltreg_eqp_id ──JOIN──> 调压设备运行.adj_volt_dev_id
  └─ .voltreg_eqp_asst_id ──JOIN──> 调压设备资产.adj_volt_dev_asset_id
                                          └─ .adj_volt_dev_asset_id ──JOIN──> 调压设备运行.adj_volt_dev_asset_id
调压设备运行.dist_sta_id ──JOIN──> 台区.dist_sta_id
台区.dist_sta_id ──JOIN──> 安装点.dist_sta_id
安装点.inst_id ──JOIN──> 计量点负荷.inst_id  (主路径)
安装点.cust_id ──JOIN──> 用电客户.cust_id  (户变关系)
```
注：voltreg_eqp_id/adj_volt_dev_id 是 decimal，变压器侧是 varchar，JOIN 时须 `CAST(t.voltreg_eqp_id AS DECIMAL(20,4)) = v.adj_volt_dev_id`。

## 模块操作（用户可随时只查其中一段）

### 模块1：查配电变压器台账
> 用户问"有哪些配电变压器/某变压器信息/某区域变压器"
```sql
SELECT astid, equipname, CAST(capacity AS DECIMAL(10,2)) AS capacity,
       blg_stat_nm, detail_addr, run_st_dsc, volt_lvl_dsc, op_maint_org_nm,
       voltreg_eqp_id, voltreg_eqp_asst_id, voltreg_eqp_no
FROM pg_tupu.public.dim_grid_pub_dist_trans_resrc_standbk_e
WHERE run_st_dsc='在运' [AND op_maint_org_nm LIKE '%<单位>%'] [AND astid='<编号>']
```

### 模块2：配电关联调压设备资产+运营+台区
> 用户问"某变压器关联的调压设备/台区/关联链路"
```sql
SELECT t.astid, t.equipname, CAST(t.capacity AS DECIMAL(10,2)) AS capacity,
       va.adj_volt_dev_asset_id, va.pms_equip_id,
       v.adj_volt_dev_id, v.cust_id, v.dist_sta_id,
       ds.resrc_supl_name AS tg_name, ds.dist_stacap, ds.voltage AS tg_voltage
FROM pg_tupu.public.dim_grid_pub_dist_trans_resrc_standbk_e t
LEFT JOIN pg_tupu.public.cms20_adj_volt_dev_asset va
  ON CAST(t.voltreg_eqp_asst_id AS DECIMAL(20,4)) = va.adj_volt_dev_asset_id
LEFT JOIN pg_tupu.public.cms20_adj_volt_dev v
  ON va.adj_volt_dev_asset_id = v.adj_volt_dev_asset_id
LEFT JOIN pg_tupu.public.dim_cst_dist_sta ds ON v.dist_sta_id = ds.dist_sta_id
WHERE t.astid='<编号>' [AND t.run_st_dsc='在运']
```

### 模块3：查台区下计量点+挂的电能表
> 用户问"某台区下有哪些计量点/电能表/挂表情况"
```sql
SELECT i.inst_id, i.cust_id, i.dist_sta_id, i.dist_sta_name, i.voltage, i.inst_cap,
       i.inst_stat_name
FROM pg_tupu.public.dim_cst_inst_elec_cons i
WHERE i.dist_sta_id='<台区ID>'
```
电能表台账（如需查挂表）：
```sql
SELECT meter_id, asset_no, dev_type_name, mgt_org_name FROM pg_tupu.public.dim_cst_meter
WHERE meter_id IN (<该台区计量点关联的表号>)  -- 若库中无meter-inst对应关系则降级
```

### 模块4：取配电层面96点功率（核心·累加）
> 用户问"配电功率曲线/96点功率/配电层面功率"
- **主路径**（经计量点负荷累加，已验证可JOIN）：
```sql
SELECT t.astid, t.equipname, CAST(t.capacity AS DECIMAL(10,2)) AS capacity,
       l.occur_time,
       SUM(l.`load`) AS dist_power_kw,
       SUM(l.`load`)/CAST(t.capacity AS DECIMAL(10,2))*100 AS load_rate
FROM pg_tupu.public.dim_grid_pub_dist_trans_resrc_standbk_e t
JOIN pg_tupu.public.cms20_adj_volt_dev v
  ON CAST(t.voltreg_eqp_id AS DECIMAL(20,4)) = v.adj_volt_dev_id
JOIN pg_tupu.public.dim_cst_inst_elec_cons i ON v.dist_sta_id = i.dist_sta_id
JOIN pg_tupu.public.dwd_cst_mtcl_inst_load_min l ON i.inst_id = l.inst_id
WHERE t.astid='<编号>' [AND l.occur_time >= '<开始>'] [AND l.occur_time <= '<结束>']
GROUP BY t.astid, t.equipname, t.capacity, l.occur_time
ORDER BY l.occur_time
```
- **备选路径**（电能表功率累加，当meter-inst可关联时）：
```sql
-- 累加多个电能表功率到配电：SUM(p) GROUP BY astid, occur_time
SELECT t.astid, l.occur_time, SUM(m.p) AS dist_power_kw,
       SUM(m.p)/CAST(t.capacity AS DECIMAL(10,2))*100 AS load_rate
FROM ... JOIN dwd_cst_mtcl_meter_power_min m ON <meter-inst关系> ...
GROUP BY t.astid, l.occur_time
```
当前库 meter-inst 无直链，默认走主路径（inst_load 已是计量点聚合负荷），结论注明数据源。

### 模块5：判定重载/过载（连续8点）
> 用户问"哪些配电重载/过载/判定结果"
```sql
WITH dist_power AS (
  -- 模块4的聚合结果
  SELECT t.astid, t.equipname, CAST(t.capacity AS DECIMAL(10,2)) AS capacity,
         l.occur_time, SUM(l.`load`) AS power_kw,
         SUM(l.`load`)/CAST(t.capacity AS DECIMAL(10,2))*100 AS rate
  FROM pg_tupu.public.dim_grid_pub_dist_trans_resrc_standbk_e t
  JOIN pg_tupu.public.cms20_adj_volt_dev v ON CAST(t.voltreg_eqp_id AS DECIMAL(20,4))=v.adj_volt_dev_id
  JOIN pg_tupu.public.dim_cst_inst_elec_cons i ON v.dist_sta_id=i.dist_sta_id
  JOIN pg_tupu.public.dwd_cst_mtcl_inst_load_min l ON i.inst_id=l.inst_id
  WHERE t.run_st_dsc='在运'
  GROUP BY t.astid, t.equipname, t.capacity, l.occur_time
),
flagged AS (
  SELECT astid, equipname, capacity, occur_time, power_kw, rate,
    rate>=80 AS is_heavy, rate>=100 AS is_over,
    -- 连续8点判定：用窗口函数算连续重载/过载点数
    SUM(CASE WHEN rate>=80 THEN 1 ELSE 0 END) OVER (PARTITION BY astid ORDER BY occur_time ROWS 7 PRECEDING) AS heavy_run8,
    SUM(CASE WHEN rate>=100 THEN 1 ELSE 0 END) OVER (PARTITION BY astid ORDER BY occur_time ROWS 7 PRECEDING) AS over_run8
  FROM dist_power
)
SELECT astid, equipname, capacity,
  MAX(rate) AS max_rate, MAX(power_kw) AS max_power_kw,
  SUM(CASE WHEN rate>=80 THEN 1 ELSE 0 END) AS heavy_cnt,
  SUM(CASE WHEN rate>=100 THEN 1 ELSE 0 END) AS over_cnt,
  MAX(heavy_run8) AS max_heavy_run, MAX(over_run8) AS max_over_run,
  CASE WHEN MAX(over_run8)>=8 THEN '过载'
       WHEN MAX(heavy_run8)>=8 THEN '重载'
       ELSE '正常' END AS verdict
FROM flagged
GROUP BY astid, equipname, capacity
ORDER BY max_rate DESC
```

### 模块6：户变关系+受影响用户分析（重载后追问）
> 用户问"受影响用户/哪些用户影响最大/户变关系/影响分析"
```sql
SELECT c.cust_id, c.cust_name, c.voltage_name,
       CAST(c.ctrt_cap AS DECIMAL(12,2)) AS ctrt_cap,
       CAST(c.run_cap AS DECIMAL(12,2)) AS run_cap,
       CAST(c.scy_cap AS DECIMAL(12,2)) AS scy_cap,
       c.impt_lv_name, c.bus_srv_addr_name,
       t.astid, t.equipname, ds.resrc_supl_name AS tg_name
FROM pg_tupu.public.dim_grid_pub_dist_trans_resrc_standbk_e t
JOIN pg_tupu.public.cms20_adj_volt_dev v ON CAST(t.voltreg_eqp_id AS DECIMAL(20,4))=v.adj_volt_dev_id
JOIN pg_tupu.public.dim_cst_dist_sta ds ON v.dist_sta_id=ds.dist_sta_id
JOIN pg_tupu.public.dim_cst_inst_elec_cons i ON v.dist_sta_id=i.dist_sta_id
JOIN pg_tupu.public.dim_cst_elec_cons_cust c ON i.cust_id=c.cust_id
WHERE t.astid IN (<重载/过载变压器编号清单>)
ORDER BY CAST(c.ctrt_cap AS DECIMAL(12,2)) DESC, c.impt_lv_name
```
影响最大判定：合同容量(ctrt_cap)大 + 重要等级(impt_lv_name)高 = 影响最大。可结合停电影响表 `dwd_cst_srv_poweroff_affect_cons_dtl` 查历史停电受影响客户。

## 口径定义（硬规则，不可改）
- **配电层面功率** = 台区下所有计量点负荷之和 `SUM(inst_load.load)` GROUP BY 配电变压器, 时间点（电能表功率累加的等价：当meter-inst可链时用 `SUM(meter_power.p)`）
- **负载率** = 配电层面功率 / 变压器额定容量(capacity) × 100%
- **重载**：连续 ≥ 8 个时间点负载率 ≥ 80%（heavy_run8≥8）
- **过载**：连续 ≥ 8 个时间点负载率 ≥ 100%（over_run8≥8）
- **统计周期**：默认最近30天，用户指定则用用户值
- **单位**：容量 kVA（varchar 须 CAST），功率 kW
- **范围**：只统计 run_st_dsc='在运' 的变压器
- **影响最大用户**：合同容量(ctrt_cap)大 + 重要等级(impt_lv_name)高 优先

## 输出规范
1. **判定结果表**（模块5）：

   | 变压器编号 | 设备名称 | 额定容量 | 最大负载率 | 重载点数 | 过载点数 | 最长连续重载 | 最长连续过载 | 判定 |
   |---|---|---|---|---|---|---|---|---|

2. **受影响用户表**（模块6，重载/过载时追问）：

   | 客户编号 | 客户名称 | 合同容量 | 重要等级 | 用电地址 | 所属变压器 | 台区 |
   |---|---|---|---|---|---|---|

3. **一句话结论**：共 X 台配电变压器，其中重载 Y 台、过载 Z 台，最高负载率 W%；受影响用户 N 户，其中重要客户 M 户。

## 降级规则
- 配电编号/区域缺失 -> 模块1先查台账反查编号
- 调压设备关联不上（voltreg_eqp_id 为空）-> 如实说明"该变压器无调压设备关联，无法经调压链路定位台区"，可用变压器.blg_stat_nm(所属台区名)降级匹配台区
- meter-inst 无对应关系 -> 配电层面功率走 inst_load 主路径（已是计量点聚合负荷），结论注明"数据源为计量点负荷聚合"
- 负荷数据稀疏（不足8个时间点）-> 按点数近似判定（heavy_cnt/over_cnt），结论注明"数据稀疏，连续性为近似"
- 负荷数据为空 -> 如实告知"无负荷监测数据"，不编造结果
