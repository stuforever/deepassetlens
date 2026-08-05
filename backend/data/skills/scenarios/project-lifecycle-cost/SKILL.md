---
name: project-lifecycle-cost
description: 项目预算与成本对比分析。何时用：用户问"WBS预算/成本/超成本/超支/预算执行率/全生命周期成本/总成本/LCC/哪些WBS超预算"。
category: scenario
---

# 项目预算与成本对比分析（场景剧本）

本剧本为业务分析任务，口径固化。命中后按下方步骤执行，口径以"口径定义"为准，不得自行变更。

## 触发条件
用户提及"预算""成本""超成本""超支""超预算""预算执行""全生命周期成本""总成本""LCC""各阶段成本"且涉及 WBS 或项目。

支持两种范围：
- **全部 WBS**（用户说"所有/全部 WBS"或未指定项目）-> 不加项目过滤，列出所有 WBS
- **指定项目**（用户给项目编号 pspid 或项目名）-> 过滤到该项目下的 WBS

## 执行优先级（重要，覆盖通用问数流程）
本剧本涉及的实体已明确（`dim_ps_wbs_budget`/`dim_ps_wbs_cost`/`dim_ps_project_def`），**直接从「计算步骤」第1步开始**，跳过 locate 定位（fetch_l1_l2_tree/validate_l2/fetch_subgraph/validate_attributes/search_entities 等一律不调）。
预算与成本分属两个数据源，**必须用 get_entity_source_mode 分发**：预算(api_integration)->execute_entity_api，成本(sql_integration)->execute_doris_sql。**不要用 execute_sql**（多源数据查不到）。两份数据取回后按 wbs_element 关联算超成本，**不要在 SQL 里跨源 JOIN**。

## 涉及数据（多源，必须按数据源模式分发执行）
预算与成本分属两个数据源，**不能混用 execute_sql**。每个实体先调 `get_entity_source_mode` 确认 source_mode，再按模式选执行工具：

- **WBS 预算**：实体 `dim_ps_wbs_budget`，source_mode=api_integration
  - 走 `execute_entity_api`（联邦 SQL：ES dim+amt 两表 JOIN，由映射配置自动 JOIN）
  - 字段：wbs_element、total_budget（预算总额）、distributed_budget、released_budget、available_budget（可用余额）、fiscal_year、currency
- **WBS 成本**：实体 `dim_ps_wbs_cost`，source_mode=sql_integration
  - 走 `execute_doris_sql`（Doris 整合 SQL）
  - 字段：wbs_element、actual_cost（实际成本）、planned_cost（计划成本）、committed_cost（承诺成本）、variance（偏差=实际-计划，正值表示超计划）、fiscal_year、cost_element
- **项目定义**（可选，指定项目时用）：实体 `dim_ps_project_def`，source_mode=api_integration
  - 走 `execute_entity_api`
  - 字段：pspid（项目编号）、proj_desc、budget_amount（项目级预算）

## 计算步骤（按序执行）
1. **取预算**：`get_entity_source_mode("dim_ps_wbs_budget")` 确认 api_integration -> `execute_entity_api(entity_code="dim_ps_wbs_budget", filters={})` 取所有 WBS 的 wbs_element + total_budget + available_budget。
   - 指定项目时：先 `execute_entity_api("dim_ps_project_def")` 取 pspid，再用 pspid 过滤（如预算表含项目字段则加 filters）。
2. **取成本**：`get_entity_source_mode("dim_ps_wbs_cost")` 确认 sql_integration -> `execute_doris_sql(entity_code="dim_ps_wbs_cost", filters={})` 取 wbs_element + actual_cost + planned_cost + variance。
3. **按 wbs_element 关联**预算与成本（两份结果在回答里按 wbs_element 对齐，算每条 WBS 的）：
   - 预算执行率 = actual_cost / total_budget × 100%
   - 预算余额 = total_budget - actual_cost
   - 是否超计划成本 = variance > 0（actual_cost > planned_cost）
   - 是否超预算 = actual_cost > total_budget
4. **输出**：每条 WBS 的 预算/成本/执行率/余额/超计划标记；汇总超计划 WBS 清单；结论。

## 口径定义（硬规则，不可改）
- **超成本（超计划成本）** = actual_cost > planned_cost，即 variance > 0（variance 字段正值即超计划）
- **超预算** = actual_cost > total_budget（实际超过预算总额）
- **预算执行率** = actual_cost / total_budget × 100%
- **预算余额** = total_budget - actual_cost（负值表示已超预算）
- **偏差** = actual_cost - planned_cost = variance（正值超计划，负值节约）
- **金额单位**：元（currency 字段），汇总保留 2 位小数
- **统计范围**：全部 WBS（默认）或指定项目下 WBS（按 pspid 过滤）
- **JOIN 键**：wbs_element（预算表与成本表共有，逐 WBS 对齐）
- 当前库无生命周期阶段字段，按 WBS 元素分解；如需四阶段分析须补充阶段归属配置并在结论注明。

## 输出规范
1. **WBS 预算-成本对比明细表**：

   | WBS编号 | 预算总额 | 实际成本 | 计划成本 | 偏差 | 预算执行率 | 预算余额 | 超计划 |
   |---|---|---|---|---|---|---|---|

2. **超成本（超计划）WBS 清单**：列出 variance > 0 的 WBS 及其超支金额（variance 值）。
3. **超预算 WBS 清单**（如有）：列出 actual_cost > total_budget 的 WBS。
4. **结论**：N 条 WBS 中，M 条超计划成本（合计超支 X 元），K 条超预算；整体预算执行率平均 Y%；建议关注哪些 WBS。

## 降级规则
- 项目编号缺失 -> 先 `execute_entity_api("dim_ps_project_def")` 反查项目编号（按项目名模糊）
- 项目不存在 -> 如实告知"未找到项目 X"，列出已有项目供用户选择
- 预算/成本某源数据为空 -> 如实说明"该源无记录"，不编造金额
- 某实体 source_mode 与预期不符 -> 按 get_entity_source_mode 实际返回选工具，不臆测
