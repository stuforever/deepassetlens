# 参考数据码值字典（编码与名称两列冗余存储，过滤用名称）

各实体的码值列均带同名 `*_name` 中文名冗余列（**编码与码值两列存储**），SQL 输出优先 SELECT `*_name` 显示中文；用户按名称过滤时注入对应编码（见 dynamic_filters.md）。全部码值如下：

| 实体表 | 码值列 | 名称列 | 编码 -> 中文名 |
|---|---|---|---|
| `⟦配电变压器⟧` | voltagelevel | voltagelevel_name | AC00101->10kV, AC00201->35kV, AC01101->110kV |
| `⟦配电变压器⟧` | runstate | runstate_name | 20->在运, 40->停运 |
| `⟦配电变压器⟧` | pubprivflag | pubprivflag_name | 0->公用, 1->专用 |
| `⟦发电户⟧` | cust_pscateg | cust_pscateg_name | 01->分布式光伏, 02->风电, 03->其他 |
| `⟦发电户⟧` | gc_stat | gc_stat_name | 01->正常, 02->停用 |
| `⟦计量点⟧` | inst_usage_cls | inst_usage_cls_name | 01->用电, 1101->发电, 1102->上网 |
| `⟦计量点⟧` | inst_cls | inst_cls_name | 01->售电结算, 03->关口计量 |
| `⟦计量点⟧` | inst_stat | inst_stat_name | 02->在用, 01->停用 |
| `⟦计量点⟧` | inst_lv | inst_lv_name | 1->高压 |
| `⟦用电户⟧` | cust_cls | cust_cls_name | 01->高压, 02->中压, 03->低压 |
| `⟦用电户⟧` | ecc_stat | ecc_stat_name | 01->正常 |
| `⟦能源客户⟧` | ind_cls | ind_cls_name | A000->农林牧渔, B000->采矿业, C000->制造业, D000->电力热力, E000->建筑业, F000->批发零售, G000->交通运输, H000->住宿餐饮, I000->信息技术, K000->房地产, D4410->电力生产, D4441->电力供应, D4442->电力工程, D4444->电力辅助, D4445->其他电力 |
| `⟦台区⟧` | resrc_supl_stat | resrc_supl_stat_name | 01->运行 |
| `⟦台区⟧` | pub_clg_flag | pub_clg_flag_name | 0->否 |

> **铁律**：码值列必须与 `*_name` 两列同时存在、同时输出。SELECT 时优先取 `*_name`（如 `voltagelevel_name AS 电压等级`），**不要在运行时用 CASE 转码**（已冗余存储）。WHERE 过滤用编码（如用户说"10kV"则 `voltagelevel='AC00101'`），由本字典提供 名称->编码 映射。
