---
name: project-lifecycle-cost
description: 项目预算与成本对比分析（WBS预算->WBS成本->按 WBSElement 关联计算执行率/超支/超预算）。何时用：用户问"WBS预算/成本/超成本/超支/预算执行率/全生命周期成本/总成本/LCC/哪些WBS超预算"。
category: scenario

x_tupu:
  version: "1.1"
  enabled: true
  priority: 90
  # 预算(api_integration)->duckdb 与 成本(sql_integration)->doris 分属两个数据源：
  # multi_engine=true 允许逐源确认后两引擎工具并存（禁跨源 JOIN，由答案按 WBSElement 关联）。
  multi_engine: true
  # 评审 P1-1（二轮）：多引擎**必达数据源**显式声明 —— 复合终止按实体/角色判断，
  # 而非"当前已确认引擎"（避免"确认一个→取一个→再确认第二个"顺序下提前终止）。
  required_sources:
    - entity: dim_ps_wbs_budget
      role: budget
    - entity: dim_ps_wbs_cost
      role: cost

  triggers:
    any:
      - WBS预算
      - 预算执行率
      - 超成本
      - 超支
      - 超预算
      - 全生命周期成本
      - LCC
      - 各阶段成本
    all_groups:
      - [WBS, 预算]
      - [WBS, 成本]
      - [项目, 预算]
      - [项目, 成本]
      - [预算, 超]
      - [成本, 超]

  forbidden_tools:
    - task
    - write_file
    - edit_file
    - execute
    - grep
    - glob

  # ⟦业务中文名⟧ -> 物理表名（kg_entities 元数据 entity_en_name 核对）
  entity_aliases:
    预算: dim_ps_wbs_budget
    成本: dim_ps_wbs_cost
    项目定义: dim_ps_project_def

  output:
    mode: analysis_and_result_table
    # 预算+成本跨源由答案汇总呈现对比表（无单一权威 sql_result），保留答案表格不剥离。
    forbid_markdown_detail_table: false

  steps:
    - id: analysis
      title: 预算成本对比分析
      triggers:
        any: [预算, 成本, 超成本, 超支, 超预算, 预算执行率, 全生命周期成本, 总成本, LCC, 各阶段成本]
      allowed_tools:
        - batch_entity_source_mode
        - get_entity_source_mode
        - execute_entity_api
        - execute_doris_sql
      required_slots: []
      templates: []
      stop_when:
        - sql_result.row_count >= 0
      allowed_next:
        - final
---

# 项目预算与成本对比分析（场景剧本）

本剧本为业务分析任务，口径固化。命中后按下方步骤执行，口径以"口径定义"为准，不得自行变更。

## 触发条件
用户提及"预算""成本""超成本""超支""超预算""预算执行""全生命周期成本""总成本""LCC""各阶段成本"且涉及 WBS 或项目。

支持两种范围：
- **全部 WBS**（用户说"所有/全部 WBS"或未指定项目）-> 不加项目过滤，列出所有 WBS
- **指定项目**（用户给项目编号 Project 或项目名）-> 过滤到该项目下的 WBS

## 执行优先级（重要，覆盖通用问数流程）
本剧本涉及的实体已由契约预解析（`dim_ps_wbs_budget`/`dim_ps_wbs_cost`/`dim_ps_project_def`，带 entity_aliases 来源标注）——按实体定位标准顺序（批13-M）步骤①：预解析实体直接从「取数步骤」开始，无需定位轮次；仅当取数报实体/列名错误时，按步骤③用 search_entities 兜底排查（2026-08-25 措辞对齐定位优先定调，预解析快捷路径不受影响）。
预算与成本分属两个数据源，**必须先确认数据源模式**：调 `batch_entity_source_mode(["dim_ps_wbs_budget", "dim_ps_wbs_cost"])` 一次确认两源（也可 `get_entity_source_mode` 逐实体）；预算(api_integration)->execute_entity_api，成本(sql_integration)->execute_doris_sql。**不要用 execute_sql**（多源数据查不到）。两份数据取回后按 WBSElement 关联算超成本，**不要在 SQL 里跨源 JOIN**。

## 涉及数据（多源，必须按数据源模式分发执行）
预算与成本分属两个数据源，**不能混用 execute_sql**。每个实体先确认 source_mode，再按模式选执行工具：

- **WBS 预算**：实体 `dim_ps_wbs_budget`，source_mode=api_integration
  - 走 `execute_entity_api`（联邦 SQL：ES dim+amt 两表 JOIN，由映射配置自动 JOIN）
  - 字段：WBSElement、TotalBudget（预算总额）、DistributedBudget、ReleasedBudget、AvailableBudget（可用余额）、FiscalYear、Currency
- **WBS 成本**：实体 `dim_ps_wbs_cost`，source_mode=sql_integration
  - 走 `execute_doris_sql`（Doris 整合 SQL，源表 pg_tupu.public.dim_ps_wbs_cost）
  - 字段：WBSElement、ActualCost（实际成本）、PlannedCost（计划成本）、CommittedCost（承诺成本）、Variance（偏差=实际-计划，正值表示超计划）、FiscalYear、CostElement
- **项目定义**（可选，指定项目时用）：实体 `dim_ps_project_def`，source_mode=api_integration
  - 走 `execute_entity_api`
  - 字段：Project（项目编号）、ProjectDescription、BudgetAmount（项目级预算）

## 取数步骤（按序执行）
1. **确认数据源模式**：`batch_entity_source_mode(["dim_ps_wbs_budget", "dim_ps_wbs_cost"])`（或逐实体 `get_entity_source_mode`），按返回 source_mode 分发，引擎确认后只允许对应执行工具。
2. **取预算**：`execute_entity_api(entity_code="dim_ps_wbs_budget", filters={})` 取所有 WBS 的 WBSElement + TotalBudget + AvailableBudget。
   - 指定项目时：先 `execute_entity_api("dim_ps_project_def")` 取 Project，再用 Project 过滤（如预算表含项目字段则加 filters）。
3. **取成本**：`execute_doris_sql(entity_code="dim_ps_wbs_cost", filters={})` 取 WBSElement + ActualCost + PlannedCost + Variance。
4. **按 WBSElement 关联**预算与成本（两份结果在回答里按 WBSElement 对齐，算每条 WBS 的）：
   - 预算执行率 = ActualCost / TotalBudget × 100%
   - 预算余额 = TotalBudget - ActualCost
   - 是否超计划成本 = Variance > 0（ActualCost > PlannedCost）
   - 是否超预算 = ActualCost > TotalBudget
5. **输出**：每条 WBS 的 预算/成本/执行率/余额/超计划标记；汇总超计划 WBS 清单；结论。

## 口径定义（硬规则，不可改）
- **超成本（超计划成本）** = ActualCost > PlannedCost，即 Variance > 0（Variance 字段正值即超计划）
- **超预算** = ActualCost > TotalBudget（实际超过预算总额）
- **预算执行率** = ActualCost / TotalBudget × 100%
- **预算余额** = TotalBudget - ActualCost（负值表示已超预算）
- **偏差** = ActualCost - PlannedCost = Variance（正值超计划，负值节约）
- **金额单位**：元（Currency 字段），汇总保留 2 位小数
- **统计范围**：全部 WBS（默认）或指定项目下 WBS（按 Project 过滤）
- **JOIN 键**：WBSElement（预算表与成本表共有，逐 WBS 对齐）
- 当前库无生命周期阶段字段，按 WBS 元素分解；如需四阶段分析须补充阶段归属配置并在结论注明。

## 输出规范
1. **WBS 预算-成本对比明细表**：

   | WBS编号 | 预算总额 | 实际成本 | 计划成本 | 偏差 | 预算执行率 | 预算余额 | 超计划 |
   |---|---|---|---|---|---|---|---|

2. **超成本（超计划）WBS 清单**：列出 Variance > 0 的 WBS 及其超支金额（Variance 值）。
3. **超预算 WBS 清单**（如有）：列出 ActualCost > TotalBudget 的 WBS。
4. **结论**：N 条 WBS 中，M 条超计划成本（合计超支 X 元），K 条超预算；整体预算执行率平均 Y%；建议关注哪些 WBS。

## 降级规则
- 项目编号缺失 -> 先 `execute_entity_api("dim_ps_project_def")` 反查项目编号（按项目名模糊）
- 项目不存在 -> 如实告知"未找到项目 X"，列出已有项目供用户选择
- 预算/成本某源数据为空 -> 如实说明"该源无记录"，不编造金额
- 某实体 source_mode 与预期不符 -> 按 source_mode 实际返回选工具，不臆测

## 字段口径变更记录
- 2026-09-13 第七批：PS 实体字段由 SAP DDIC 口径全量重命名对齐 OData V4 CamelCase（wbs_element→WBSElement、actual_cost→ActualCost、pspid→Project 等），本剧本同步更新；原名映射存档见《实体SAP对应关系全量对照_L2L4_20260910.md》。
