---
name: relate
description: 关系能力包。查实体间关联关系和JOIN字段。含查关系列表、查JOIN表达式两个工具。何时用：跨表查询需要JOIN字段、或查实体间关系结构时。
---

# relate 关系能力包

## 用途
查实体间的关联关系和 JOIN 字段。

## 工具清单（按需挑用）
- **get_entity_relations**：查实体关联关系（全量关系图）。参数 `{"entity_code":"表名"}`。返回 relations（含 join_expr/cardinality/direction）。
- **fetch_join_expr**：查两表 JOIN ON 表达式。参数 `{"source_entity":"主表","target_entity":"关联表"}`。返回 join_on。

## 依赖关系
- 需要 entity_code 或实体名（来自 locate，或对话历史，或用户直接给）

## 硬约束
- get_entity_relations 当前仅覆盖 13 条关系，查不到不等于没关系，需如实告知用户
- fetch_join_expr 查不到会 fallback 成 `src.cust_id = tgt.cust_id`，须判断是否合理，不合理则放弃跨表
- 多跳时对每个目标实体分别调 get_entity_relations，逐跳记录 JOIN 字段

## 挑用示例
- 看关系结构（不出数据） -> get_entity_relations
- 拼跨表 SQL -> fetch_join_expr 取 JOIN ON
- 多跳穿透 -> 对每跳调 get_entity_relations，记录路径 A->B->C

## 当前已登记关系（覆盖有限）
- dim_cst_elec_cons_cust <-> dim_cst_contact（联系人）
- dim_cst_elec_cons_cust <-> dim_cst_cert_set（证件）
- dim_cst_inst_elec_cons <-> dwd_cst_bilg_*（计费结算5张表）
