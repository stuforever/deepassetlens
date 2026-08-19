# 动态条件传参（执行时按用户意图注入 WHERE）

| 用户说 | 注入条件 | 注入位置 |
|---|---|---|
| "8月1日/那天的" | `AND pw.date = '20260801'` | 第2/3步 dist_power WHERE |
| "在运的配变" | `WHERE t.runstate = '20'`（默认） | 台区容量 CTE |
| "停运配变" | `WHERE t.runstate = '40'` | 台区容量 CTE |
| "在用计量点" | `AND i.inst_stat = '02'`（默认） | 计量点台区 CTE |
| "正常用电户" | `AND ec.ecc_stat = '01'` | 第1/3步用电户 WHERE |
| "正常发电户" | `AND g.gc_stat = '01'` | 第1/3步发电户 WHERE |
| "高压用户" | `AND ec.cust_cls = '01'` | 第1/3步用电户 WHERE |
| "分布式电源/光伏" | `AND g.cust_pscateg = '01'` | 第1/3步发电户 WHERE |
| "只看上网负载" | `AND i.inst_usage_cls = '1102'` | 计量点台区 CTE |
| "10kV/35kV/110kV配变" | `AND t.voltagelevel = 'AC00101'`(10kV) / `'AC00201'`(35kV) / `'AC01101'`(110kV) | 台区容量 CTE |
| "公用配变/专用配变" | `AND t.pubprivflag = '0'`(公用) / `'1'`(专用) | 台区容量 CTE |
| "分布式光伏/风电" | `AND g.cust_pscateg = '01'`(分布式光伏) / `'02'`(风电) / `'03'`(其他) | 第1/3步发电户 WHERE |
| "中压/低压用户" | `AND ec.cust_cls = '02'`(中压) / `'03'`(低压) | 第1/3步用电户 WHERE |
| "客户001/客户003"（带"客户"前缀的名称） | `AND c.cust_name IN ('客户001','客户003')` | 第1/3步能源客户(`⟦能源客户⟧`) WHERE |

> 日期格式："8月1日"转 `'20260801'`。负荷类型过滤使第2/3步只跑对应段。
> **客户标识三列区别**（`⟦能源客户⟧`）：`cust_name` 中文名格式"客户001"（**用户说"客户XXX"指此列**）；`cust_no` 编号格式"C00001"；`cust_id` 数字ID(1,2...)。用户说"客户001/客户003" -> `c.cust_name IN (...)`，**禁止用 cust_no/cust_id 反复试错**。
