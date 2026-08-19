# 数据表与关联键（entity_code = 表名，先查 source_mode 再选工具）

> **列定义以元数据为准**：以下仅列关联键和业务关键列速查，SQL 模板中已含完整列名（已核对一致，直接用）。若用户改了实体属性导致 SQL 报列名错误，调 `kg_api(action=search_entities, params={"entity_code":"<表名>"})` 确认最新列名后修改重试。

| 实体 | 表名 | 关联键(JOIN用) | 业务关键列 | 说明 |
|---|---|---|---|---|
| 配电变压器 | `⟦配电变压器⟧` | **psrid**, astid | capacity(容量), runstate, voltagelevel | 柱上+非柱上合并视图 |
| 台区 | `⟦台区⟧` | **dist_sta_id** | resrc_supl_stat | 台区主数据（单路/多路供电） |
| 计量点 | `⟦计量点⟧` | **inst_id**, cust_id, **dist_sta_id**, **gpc_id**, **elec_cons_cust_id** | inst_usage_cls(决定负荷类型) | **最小粒度**，户变关系枢纽；gpc_id 精确归属发电户号(1102/1101)、elec_cons_cust_id 精确归属用电户号(01)，防一户多号笛卡尔积 |
| 调压设备 | `⟦调压设备⟧` | adj_volt_dev_asset_id, **dist_sta_id** | - | 关联配变的桥；**同一台区多配变时有多条记录**（多路供电） |
| 调压设备资产 | `⟦调压设备资产⟧` | **adj_volt_dev_asset_id**, pms_equip_id | - | pms_equip_id=配变.psrid；配变1:1:1对应 |
| 用电户 | `⟦用电户⟧` | **elec_cons_cust_id**, **cust_id** | cust_cls, ecc_stat | cust_id=计量点.cust_id |
| 发电户 | `⟦发电户⟧` | **gpc_id**, **cust_id** | cust_pscateg, gc_stat | cust_id=计量点.cust_id |
| 能源客户 | `⟦能源客户⟧` | **cust_id** | cust_name, cust_no, ind_cls | 客户主档；**一个客户可有多个计量点** |
| 用户遥测功率 | `⟦客户功率时序⟧` | **inst_id** | date, occur_time, power, measuerment_type | 96点窄表视图(已按主测量点equip_src_id=inst_id去重)；power 正=用电/发电出力，负=上网倒送 |

> 各实体码值列均带 `*_name` 中文名冗余列（编码+名称两列存储），具体列名以元数据为准。SELECT 优先取 `*_name` 显示中文，WHERE 用编码过滤。

### 关联键链（已验证可JOIN）
```
发电户.gpc_id = 计量点.gpc_id                     -- 发电户号->计量点(精确, 防一户多号笛卡尔积; 仅1102/1101侧)
用电户.elec_cons_cust_id = 计量点.elec_cons_cust_id  -- 用电户号->计量点(精确, 防一户多号笛卡尔积; 仅01侧)
能源客户.cust_id = 发电户.cust_id / 用电户.cust_id   -- 客户主档(取名称/行业), 仍走cust_id
计量点.dist_sta_id = 台区.dist_sta_id             -- 计量点->台区(一台区N计量点)
调压设备.dist_sta_id = 台区.dist_sta_id           -- 台区->调压设备(一台区可多调压设备=多路供电)
调压设备.adj_volt_dev_asset_id = 调压设备资产.adj_volt_dev_asset_id
调压设备资产.pms_equip_id = 配电变压器.psrid       -- 调压资产->配变(1:1:1)
计量点.inst_id = ⟦客户功率时序⟧.inst_id          -- 计量点->96点功率
```
> **关键**：第1步户变关系**发电户段用 `g.gpc_id=i.gpc_id` 关联、用电户段用 `ec.elec_cons_cust_id=i.elec_cons_cust_id` 关联**（精确到户号，一户多号时各户号挂各自独立计量点，不笛卡尔积）。客户主档(名称/行业)仍走 `cust_id`。第2/3步功率汇集走"计量点->台区(dist_sta_id)"路径，**不走** 计量点->调压设备->配变（多路供电台区会产生笛卡尔积导致功率翻倍）。台区配变容量通过独立CTE汇总：`SUM(capacity) GROUP BY dist_sta_id`。
