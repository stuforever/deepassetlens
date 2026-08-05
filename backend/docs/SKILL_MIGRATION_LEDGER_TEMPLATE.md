# 三模块技能迁移台账模板（智能问数/智能联结/智能溯源）

## 1. 目标与边界
- 目标：统一三模块重复技能，形成 `Core技能库 + 场景工作流`。
- 约束：
  - 智能问数、智能联结仅查询数据实体实例化表，不追溯源端表。
  - 智能溯源保留来源表/来源字段/关系链路分析能力。
  - 三模块均提供两种模式：用户模式、开发者模式。
  - 开发者模式必须支持“回退到任一步骤并重跑后续步骤”。

## 2. 技能分层（目标态）
### 2.1 Core技能（复用）
- `core.semantic_retrieval`
- `core.field_grounding`
- `core.entity_relation_planner`
- `core.condition_normalizer`
- `core.interactive_disambiguation`
- `core.sql_blueprint_builder`
- `core.sql_generator`
- `core.sql_validator_executor`
- `core.explain_builder`
- `core.run_logger`
- `core.step_rewind_controller`（新增：开发者模式回退控制）
- `core.lineage_analyzer`（仅溯源工作流调用）

### 2.2 场景工作流（编排层）
- `wf.smart_qa`：问数工作流（含条件消歧与SQL执行）。
- `wf.smart_connection`：联结工作流（偏重多实体关系与SQL组装）。
- `wf.smart_traceability`：溯源工作流（偏重来源表解释）。

## 3. 现状技能 -> 目标技能映射清单（首版）
| 序号 | 现有技能Code | 所属模块 | 目标技能Code | 迁移动作 | 兼容策略 | 下线策略 | 优先级 |
|---|---|---|---|---|---|---|---|
| 1 | smart_conn_vector_search | 智能联结 | core.semantic_retrieval | 合并 | 保留旧入参适配器2周 | 灰度100%后下线 | P0 |
| 2 | step2_2_vector_search / smart_qa_step2_field_search | 智能问数 | core.semantic_retrieval | 合并 | 旧输出字段映射到统一schema | 同上 | P0 |
| 3 | smart_conn_entity_relation | 智能联结 | core.entity_relation_planner | 合并 | 保留join_expr字段名兼容 | 同上 | P0 |
| 4 | smart_qa_step25_join / smart_qa_step3_entity_relation(若存在) | 智能问数 | core.entity_relation_planner | 合并 | 增加关系路径评分输出 | 同上 | P0 |
| 5 | smart_qa_step3_filter | 智能问数 | core.condition_normalizer | 升级 | 原条件结构透传 + 新标准结构并存 | 同上 | P0 |
| 6 | smart_conn_llm_sql / smart_qa_step4_sql_assemble | 联结/问数 | core.sql_generator | 合并 | LLM失败自动模板兜底 | 同上 | P0 |
| 7 | smart_qa_step5_validate + smart_qa_step6_execute | 智能问数 | core.sql_validator_executor | 合并 | 兼容data_source_id逻辑 | 同上 | P0 |
| 8 | smart_conn_traceability | 智能溯源 | core.lineage_analyzer | 升级 | 保持attribute_traces输出不变 | 同上 | P0 |
| 9 | 前端模块内解释拼装逻辑 | 三模块 | core.explain_builder | 收敛 | 前端只渲染，不拼业务语义 | 分阶段移除 | P1 |
| 10 | 三模块分散执行日志 | 三模块 | core.run_logger | 收敛 | 引入统一run_id/trace_id | 分阶段移除 | P1 |

## 4. 开发者模式“回退能力”改造清单（必须项）
> 现有智能溯源、智能联结页面作为开发者模式模板可复用；本次补齐“不可回退”的核心缺陷。

| 序号 | 能力 | 说明 | 责任端 | 验收标准 |
|---|---|---|---|---|
| R1 | 步骤快照 | 每步落库：输入/输出/耗时/状态 | 后端 | 每个run至少有N步快照 |
| R2 | 回退控制器 | 支持选择历史步骤作为重跑起点 | 后端 | 可从任一步重跑后续步骤 |
| R3 | UI回退入口 | 开发者模式步骤面板新增“回退到此步” | 前端 | 一键回退并看到新分支执行链 |
| R4 | 分支记录 | 回退后新链路保留父子关系 | 后端 | 可追踪原链路与回退链路 |
| R5 | 对比视图 | 原步骤输出 vs 回退后输出差异 | 前端 | 支持JSON差异高亮 |

## 5. 迁移任务台账模板（可复制）
| TaskID | 模块 | 当前技能 | 目标技能 | 工作内容 | 负责人 | 开始 | 截止 | 状态 | 风险 | 验收结果 |
|---|---|---|---|---|---|---|---|---|---|---|
| MIG-001 | 问数/联结 | vector_search类 | core.semantic_retrieval | 抽取共用检索逻辑，统一输出schema | TBD | YYYY-MM-DD | YYYY-MM-DD | 未开始 | 检索召回率波动 | 待验收 |
| MIG-002 | 问数/联结 | entity_relation类 | core.entity_relation_planner | 统一关系路径规划和评分 | TBD | YYYY-MM-DD | YYYY-MM-DD | 未开始 | join路径变化 | 待验收 |
| MIG-003 | 问数 | step3_filter | core.condition_normalizer | 统一时间/比较/范围结构化 | TBD | YYYY-MM-DD | YYYY-MM-DD | 未开始 | 时间字段歧义 | 待验收 |
| MIG-004 | 问数 | 条件消歧分散逻辑 | core.interactive_disambiguation | 字段不确定时交互选择 | TBD | YYYY-MM-DD | YYYY-MM-DD | 未开始 | 交互中断恢复 | 待验收 |
| MIG-005 | 问数/联结 | llm_sql/assemble | core.sql_generator | 统一蓝图渲染SQL与兜底 | TBD | YYYY-MM-DD | YYYY-MM-DD | 未开始 | SQL兼容性 | 待验收 |
| MIG-006 | 问数/联结 | validate+execute | core.sql_validator_executor | 校验与执行合并 | TBD | YYYY-MM-DD | YYYY-MM-DD | 未开始 | 数据源差异 | 待验收 |
| MIG-007 | 溯源 | traceability analyze | core.lineage_analyzer | 统一溯源分析接口 | TBD | YYYY-MM-DD | YYYY-MM-DD | 未开始 | 输出兼容性 | 待验收 |
| MIG-008 | 三模块 | 调试日志 | core.run_logger | 统一run_id与步骤日志 | TBD | YYYY-MM-DD | YYYY-MM-DD | 未开始 | 历史数据迁移 | 待验收 |
| MIG-009 | 三模块 | 无回退 | core.step_rewind_controller | 增加回退与分支能力 | TBD | YYYY-MM-DD | YYYY-MM-DD | 未开始 | 状态一致性 | 待验收 |

## 6. 工作流目标态定义（供技能管理发布）
### 6.1 wf.smart_qa（问数）
1. semantic_retrieval
2. field_grounding
3. entity_relation_planner
4. condition_normalizer
5. interactive_disambiguation（按需）
6. sql_blueprint_builder
7. sql_generator
8. sql_validator_executor
9. explain_builder
10. run_logger

### 6.2 wf.smart_connection（联结）
1. semantic_retrieval
2. field_grounding
3. entity_relation_planner
4. sql_blueprint_builder
5. sql_generator
6. sql_validator_executor
7. explain_builder
8. run_logger

### 6.3 wf.smart_traceability（溯源）
1. semantic_retrieval
2. field_grounding
3. entity_relation_planner
4. lineage_analyzer
5. explain_builder
6. run_logger

## 7. 统一验收口径
- 问数与联结：SQL仅访问数据实体实例化表。
- 溯源：必须返回来源表、来源字段、表间关系证据。
- 开发者模式：必须具备步骤回退、分支重跑、结果差异对比。
- 时间条件（如“本月”）无法自动映射字段时：必须进入交互式选择。

## 8. 发布与回滚策略
- 发布策略：10% -> 30% -> 70% -> 100% 灰度。
- 旧技能状态：先标记 `deprecated`，观察无调用后下线。
- 回滚策略：按workflow版本回滚，不做代码热修临时分叉。

---
版本：v1.0  
用途：迁移评审与周会跟踪模板  
维护人：架构/后端负责人
