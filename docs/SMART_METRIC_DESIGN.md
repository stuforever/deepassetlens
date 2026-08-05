# 智能问指标（Smart Metric）行业级设计（方案B）
 
## 1. 目标与边界
 
### 1.1 产品目标
- 构建“指标中心 + 问指标”闭环：指标定义可治理、可发布、可版本化、可解释、可回归。
- 问指标严格走“指标定义检索 → 受控组装SQL”，不做智能问数式的实体属性发散。
- 输出必须可解释：指标口径、数据来源（事实/维度实体、物理表字段映射）、过滤条件、时间字段、最终SQL。
 
### 1.2 核心原则（强约束）
- 指标必须命中已定义的指标（Atomic / Derived）；命中不到直接返回“未定义/需补充定义”，最多给候选列表。
- JOIN 关系只能来自知识库/建模关系白名单，禁止 LLM 生成关联条件。
- 主表唯一且固定：事实实体（Fact Entity / Fact Table）为唯一主表；统一 LEFT JOIN 外表，禁止 INNER/RIGHT/FULL。
- 指标口径由配置 + 受控DSL决定；LLM 只允许做“命中/消歧/解释文本”，不允许造口径。
 
### 1.3 术语定义
- 指标目录（Metric Catalog）：业务可见的指标条目。
- 原子指标（Atomic Metric）：可直接在一个事实实体上通过聚合得到的度量。
- 派生指标（Derived Metric）：由原子指标/派生指标按受控表达式组合得到。
- 事实实体（Fact Entity）：承载可聚合事实明细的实体（或其落地事实表）。
- 维度实体（Dimension Entity）：用于切片（group by）、筛选（filter）和展示（attributes）。
 
## 2. 数据模型（多表，行业级治理）
 
> 说明：本设计以 MySQL 为例，命名风格与现有 `kg_*` 保持一致。字段类型可按你们现有 SQLAlchemy 约定调整。
 
### 2.1 指标主表：kg_metrics
存放“指标目录”信息，支持版本化与治理流转。
 
**字段建议**
- id (string36, pk)
- metric_code (varchar(128), unique) 指标编码（稳定主键）
- metric_name (varchar(255)) 指标名称
- metric_name_en (varchar(255), null) 英文名/简称
- metric_type (varchar(32)) atomic / derived
- domain (varchar(128)) 主题域/业务域
- description (text) 口径说明（人类可读）
- status (varchar(32)) draft / reviewing / approved / published / deprecated
- owner_user (varchar(128)) 指标负责人
- reviewer_user (varchar(128), null)
- version_current (int) 当前发布版本号（从1开始）
- enabled (bool)
- created_at / updated_at
 
**索引**
- uniq(metric_code)
- idx(metric_name)
- idx(domain, status)
 
### 2.2 指标同义词：kg_metric_aliases
用于“指标定义检索”召回，保证不发散的同时能容忍用户表达差异。
 
- id pk
- metric_id fk(kg_metrics.id)
- alias (varchar(255))
- alias_type (varchar(32)) name / abbrev / synonym / phrase
- weight (float) 默认为1.0，支持运营调优
- enabled, created_at
 
索引：idx(metric_id), idx(alias)
 
### 2.3 原子指标定义：kg_metric_atoms
原子指标的受控口径配置，必须绑定事实实体与度量字段。
 
- id pk
- metric_id fk(kg_metrics.id)（metric_type=atomic）
- fact_entity_id (string36) 事实实体ID（指向你们 Entity 表）
- fact_entity_name (varchar(255)) 冗余便于展示
- fact_table_en (varchar(255)) 物理表英文名（来自建模 EntityModeling）
- data_source_id (string36) 数据源ID（指向 kg_data_source_configs）
- agg_func (varchar(32)) sum / count / distinct_count / max / min / avg
- measure_field_en (varchar(255), null) 度量字段英文名（count(*) 可为空）
- measure_field_cn (varchar(255), null) 度量字段中文名
- measure_data_type (varchar(64), null)
- time_field_en (varchar(255)) 默认时间字段（强约束）
- time_field_cn (varchar(255), null)
- default_limit (int, default 200) 默认返回限制（明细类可用）
- grain_default (varchar(32), default 'day') 默认时间粒度（day/month/...)
- definition_json (json/text) 预留扩展：精度、单位、格式化等
- enabled, created_at, updated_at
 
索引：idx(metric_id), idx(fact_entity_id), idx(data_source_id)
 
### 2.4 原子指标默认过滤（口径内置）：kg_metric_atom_filters
用于表达“有效标志=1”“剔除作废记录”等口径过滤，必须受控维护。
 
- id pk
- atom_id fk(kg_metric_atoms.id)
- field_full_name (varchar(255)) 形如 factTable.field
- op (varchar(32)) =, !=, IN, NOT IN, BETWEEN, IS NULL, IS NOT NULL
- value_json (json/text) 值（可数组）
- enabled
 
索引：idx(atom_id)
 
### 2.5 派生指标定义：kg_metric_derived
受控DSL表达式 + 依赖关系，禁止自由SQL。
 
- id pk
- metric_id fk(kg_metrics.id)（metric_type=derived）
- expr_dsl (text) 受控DSL，例如：div(metric('A'), nullif(metric('B'),0))
- unit (varchar(64), null)
- precision (int, null)
- enabled, created_at, updated_at
 
索引：idx(metric_id)
 
### 2.6 派生指标依赖：kg_metric_deps
用于版本校验、血缘与防环。
 
- id pk
- metric_id fk(kg_metrics.id) 目标派生指标
- dep_metric_id fk(kg_metrics.id) 依赖指标
- dep_role (varchar(32)) numerator/denominator/other（可选）
 
索引：idx(metric_id), idx(dep_metric_id)
 
### 2.7 指标可关联维度白名单：kg_metric_dim_bindings
指标允许哪些维度实体参与 group by / filter，完全由配置决定（保证不发散）。
 
- id pk
- metric_id fk(kg_metrics.id)
- dim_entity_id (string36)
- dim_entity_name (varchar(255))
- join_path_id (string36, null) 预留：多跳路径ID（V2）
- enabled
 
索引：idx(metric_id), idx(dim_entity_id)
 
### 2.8 指标可过滤字段白名单：kg_metric_filter_whitelist
指标能被用户“额外过滤”的字段集合（避免任意字段造成口径污染/性能灾难）。
 
- id pk
- metric_id fk(kg_metrics.id)
- field_full_name (varchar(255)) 支持事实或维度字段
- field_cn (varchar(255), null)
- data_type (varchar(64), null)
- op_whitelist_json (json/text) 允许操作符列表
- enabled
 
索引：idx(metric_id)
 
### 2.9 指标版本快照：kg_metric_versions
发布时把全量定义快照固化，支持回滚、稽核、可回归。
 
- id pk
- metric_id fk(kg_metrics.id)
- version (int)
- status (varchar(32)) published / archived
- snapshot_json (json/text) 包含 atoms/filters/derived/deps/dim_bindings/filter_whitelist
- created_by, created_at
 
唯一索引：uniq(metric_id, version)
 
### 2.10 治理审计：kg_metric_audit_logs
用于合规、变更留痕、问题追溯。
 
- id pk
- metric_id fk
- action (varchar(64)) create/update/submit/approve/reject/publish/deprecate/rollback
- before_json / after_json
- operator, created_at
 
索引：idx(metric_id), idx(action)
 
### 2.11 运行与热度（可选但强烈建议）：kg_metric_usage_stats
用于“历史匹配权重”“常用指标置顶”“结果稳定性”。
 
- id pk
- metric_id fk
- query_fingerprint (varchar(64))（规范化问句hash/模板hash）
- hit_count (int)
- last_hit_at
 
唯一索引：uniq(metric_id, query_fingerprint)
 
## 3. 指标维护工作流（行业级）
 
### 3.1 生命周期
- draft：可编辑，未进入评审
- reviewing：提交评审后锁定关键口径字段（可允许备注修改）
- approved：评审通过，待发布
- published：线上可检索可问
- deprecated：下线/弃用（保留历史版本）
 
### 3.2 权限模型（建议）
- 指标Owner：创建/编辑/提交评审
- Reviewer：审核通过/驳回
- Admin：发布/回滚/强制下线
 
### 3.3 版本规则
- 任何口径变更（事实实体、聚合、过滤、time_field、派生表达式、维度白名单）必须 bump version，并生成 `kg_metric_versions` 快照。
- 回滚：将 `metric.version_current` 指向历史版本，并记录审计。
 
## 4. 问指标（Smart Metric）运行时链路
 
### 4.1 Scene 与步骤（建议对齐 smart_core / pipeline）
scene: `smart_metric`
 
步骤建议（用户模式可合并，开发者模式逐步可见）
1. metric_retrieval：指标检索（只检索指标库）
2. metric_disambiguation：消歧（候选太接近时交互）
3. dimension_binding：维度识别与绑定（只能用白名单）
4. time_range_extract：时间范围识别（默认用指标 time_field）
5. filter_extract_limited：用户过滤提取（只能落在 filter_whitelist）
6. sql_blueprint_metric：按定义生成SQL蓝图（主表固定为事实表）
7. sql_generate_deterministic：受控SQL生成（不走LLM或仅做格式化）
8. sql_validate：安全校验（复用现有）
9. sql_execute：执行（复用现有）
10. explain_pack：解释输出（口径/血缘/SQL）
 
### 4.2 指标检索策略（不发散）
- 第一层：精确匹配 metric_code / metric_name / alias（权重高）
- 第二层：向量检索（term_type=metric），只在 `kg_metrics + aliases` 语料内建索引
- 第三层：历史热度加权（usage_stats）
 
命中规则：
- Top1 分数 >= 阈值：直接选中
- TopN 接近：触发消歧
- 分数不足：返回“未定义”，提示去指标中心补齐
 
### 4.3 SQL 组装规则（与智能问数区分）
- FROM：atom.fact_table_en（唯一主表）
- JOIN：仅允许 `LEFT JOIN`，且只能来自知识库关系 / 预设 join path
- WHERE：time_range + atom_filters + user_filters（user_filters 需 whitelist）
- GROUP BY：绑定维度字段（需 dim_bindings）
- SELECT：
  - atomic：agg(measure)
  - derived：展开依赖指标的SQL表达式或先算子查询再组合
 
## 5. 前后端能力模块规划
 
### 5.1 后端模块建议
- models：新增 Metric/Atom/Derived/... SQLAlchemy 模型
- services：
  - metric_catalog_service：CRUD + 工作流 + 版本快照
  - metric_retrieval_service：检索（含别名与向量）
  - metric_query_service：执行链路（解析问句→蓝图→SQL→执行）
- api：
  - /metrics：目录查询与详情
  - /metrics/{id}/versions：版本列表与回滚
  - /metrics/{id}/submit、/approve、/publish：治理动作
  - /smart-metric/step-preview、/run-step：对齐 smart_core
 
### 5.2 前端页面建议
- 指标中心（MetricManager）
  - 目录列表、筛选（域/状态/负责人/版本）
  - 指标编辑（Atomic/Derived 分Tab）
  - 维度白名单配置、过滤白名单配置
  - 提交评审/审核/发布/回滚
  - 血缘/解释预览（Join路径、事实/维度实体来源）
- 问指标（SmartMetric）
  - 用户模式：输入问句 → 展示指标解释 + 结果
  - 开发者模式：步骤可点、单按钮执行、SQL可编辑、可选数据源
 
## 6. 与现有系统的集成点
- 数据源：`kg_data_source_configs`（已有）
- 实体/属性/关系：Entity/EntityRelation（已有）
- 实体建模到物理表：EntityModeling（已有）
- SQL 安全校验与执行：复用智能问数已有链路（sql_validate/sql_execute）
 
## 7. 运营与质量保障（行业级）
- 指标回归用例库：每个发布版本必须至少1条标准问法 + 预期SQL模板/预期结果范围
- 变更影响分析：派生指标依赖图，发布前检查下游依赖影响
- 命中率与误命中监控：Top1命中率、消歧率、未定义率、用户改问率
- 性能治理：每指标记录执行耗时P50/P95，超阈值触发优化建议（索引/预聚合/宽表）
 
## 8. 迁移策略（从现有 kg_ontology_metrics 过渡）
- `kg_ontology_metrics` 可作为早期目录数据源迁移到 `kg_metrics + kg_metric_aliases`
- 新增 atomic/derived 表后，逐步补齐口径与版本，最终前端以新表为准
 
