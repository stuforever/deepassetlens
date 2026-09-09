---
name: distribution-overload
description: 配电变压器重过载分析（户变关系->台区级96点功率汇集->客户负载占有率倒排）。何时用：用户问"户变关系/用电户与配变/发电户与配变/重载/过载/负载率/96点功率/用电负载/上网负载/发电负载/负载占有率/倒排/排序"，或带日期/状态等动态条件。
category: scenario

x_tupu:
  version: "1.0"
  enabled: true
  priority: 100
  # P0-2 强牢笼：模板派生 SQL 强制执行 —— 结构指纹与模板不一致（同表但骨架不同）即拒绝
  template_mode: scenario_strict

  # 批13-Z 子代理激活（路线A）：多实体域跨表定位（台区+客户+线路）允许委派 entity_locator
  # 子代理（定位类只读工具窄集，见 capability_policies.subagents.specs）。
  # 护栏1 复合条件：本声明 AND caps.subagents.enabled（能力开关仍是总闸）；其他剧本未声明默认拒绝。
  allow_subagents: true

  # 批13-M 定位优先（用户定调：先定位、找不到再搜索）：定位类工具入步骤 allowed_tools，
  # 跨业务域取数前先 validate_l2/fetch_subgraph 确认实体归属（防凭 entity_aliases/记忆猜表
  # 导致错挂业务域，如「业扩表」案例）；L0 金标直通不受影响（直通 SQL 自带表，跳过定位）。
  locate_first: true

  triggers:
    any:
      - 户变关系
      - 用电户与配变
      - 发电户与配变
      - 重载
      - 过载
      - 负载率
      - 负载占有率
      - 96点功率
      - 用电负载
      - 上网负载
      - 发电负载
      - 倒排
      - 排序
    all_groups:
      - [用电户, 配变]
      - [发电户, 配变]

  forbidden_tools:
    - write_file
    - edit_file
    - execute
    - grep
    - glob

  # SQL 模板/参考文件中 ⟦业务中文名⟧ -> 物理表名（模板表集合校验的唯一依据）。
  # 值带 Doris catalog 前缀（pg_tupu.public.<表名>）：execute_doris_sql 必须用 3 段命名，
  # 裸表名在默认 catalog（internal/test_db）下解析失败（2026-08-21 前端实测暴露，Fix1 复核）。
  # 表集合校验经 extract_tables 去前缀归一化，候选写裸名/3段名均匹配；执行必须 3 段名。
  entity_aliases:
    用电户: pg_tupu.public.dim_cst_elec_cons_cust
    发电户: pg_tupu.public.dim_cst_gpc
    台区: pg_tupu.public.dim_cst_dist_sta
    计量点: pg_tupu.public.dim_cst_inst_elec_cons
    调压设备: pg_tupu.public.cms20_adj_volt_dev
    调压设备资产: pg_tupu.public.cms20_adj_volt_dev_asset
    配电变压器: pg_tupu.public.dim_grid_pub_dist_trans_resrc_standbk_e
    能源客户: pg_tupu.public.cms20_cst_cust
    # 2026-08-25 一致性修复：「客户功率时序」= PG 视图 vw_cust_power_ts（96点宽表 UNPIVOT 窄表，
    # inst_id 由测量点 MET 前缀回填为 INS 与计量点对齐）。此前该实体元数据登记缺失且 PG 视图被删，
    # Doris 联邦查无此表致 Unknown table 拦截。注意：PG 侧 DDL 变更后需 REFRESH CATALOG pg_tupu。
    客户功率时序: pg_tupu.public.vw_cust_power_ts

  output:
    mode: single_result_table
    forbid_markdown_detail_table: true
    final_sections:
      - conclusion
      - findings
      - warning
      - recommendation

  steps:
    - id: relationship
      title: 户变关系查询
      triggers:
        any: [户变关系, 用电户与配变, 发电户与配变]
      allowed_tools:
        - batch_entity_source_mode
        - execute_doris_sql
        - execute_api_sql
        - execute_entity_api
        - execute_sql
        - fetch_l1_l2_tree
        - validate_l2
        - fetch_subgraph
        - search_entities
        - search_entities_batch
      required_slots: []
      templates:
        - templates/step1_household_transformer.sql
        - templates/step1_household_transformer_elec.sql
        - templates/step1_household_transformer_gen.sql
      reference_files:
        - reference/scope_cte.md
        - reference/dynamic_filters.md
      stop_when:
        - sql_result.row_count >= 0
      allowed_next: []

    - id: overload
      title: 台区重过载判定
      triggers:
        any: [重载, 过载, 负载率, 96点功率, 用电负载, 上网负载, 发电负载]
      allowed_tools:
        - batch_entity_source_mode
        - execute_doris_sql
        - execute_api_sql
        - execute_entity_api
        - execute_sql
        - fetch_l1_l2_tree
        - validate_l2
        - fetch_subgraph
        - search_entities
        - search_entities_batch
      templates:
        - templates/step1_household_transformer.sql
        - templates/step1_household_transformer_elec.sql
        - templates/step1_household_transformer_gen.sql
        - templates/step2_power_aggregation.sql
        - templates/step2_count_overload.sql
      required_slots: []
      allowed_next:
        - load_ratio

    - id: load_ratio
      title: 客户负载占有率倒排
      triggers:
        any: [负载占有率, 倒排, 排序, 影响最大]
      allowed_tools:
        - execute_doris_sql
        - execute_api_sql
        - execute_entity_api
        - execute_sql
        - fetch_l1_l2_tree
        - validate_l2
        - fetch_subgraph
        - search_entities
        - search_entities_batch
      templates:
        - templates/step3_load_ratio.sql
      required_slots: []
      allowed_next: []
---

# 配电变压器重过载分析（场景剧本·三步模块化）

> **实体定位顺序（批13-M 定位优先，用户定调：先定位、找不到再搜索）**：
> ⓪ **scenario_strict 剧本且 entity_aliases 覆盖模板全部 ⟦⟧**：服务端已预解析注入（契约消息含已替换模板与表名清单）——直接使用+一次 batch_entity_source_mode，跳过逐个定位；仅当契约提示有未覆盖占位符时才走 ①-④（此时一次 search_entities_batch 批量补齐缺口）；
> ① 契约已预解析实体（带来源标注）→ validate_l2/fetch_subgraph 确认后直接用；
> ② 问题可锚定业务域（明示台区/客户/线路/计量点等业务域，或上轮 L2 上下文）→ 先 validate_l2 → fetch_subgraph(l2_id) 从子图选实体——**跨业务域取数前必须定位确认**，禁止凭 entity_aliases 或记忆猜表（防错挂业务域，如「业扩表」案例）（本条适用于 generic 流与未预解析场景）；
> ③ 定位失败（L2 下无该实体 / 无业务域线索）→ search_entities 混合检索兜底；
> ④ 仍失败 → fetch_l1_l2_tree 层级树请用户选择。
> **L0 直通豁免**：金标锚定命中的直通题 SQL 自带表，跳过定位直接执行（回归 <4s 红线）。
>
> **执行流程（场景剧本优先，跳过通用定位流程）**：本剧本已含完整 SQL 模板（表名、列名、JOIN 关系、码值字典均已核对一致）。
> **执行前必查数据源模式**：本剧本涉及的表名即为 entity_code。调一次 `batch_entity_source_mode(entity_codes)` 批量查询 SQL 涉及的**所有表**模式，按返回的 `recommended_tool` 选工具（铁律，不可切换）。**只调一次批量接口**，不要逐表查询：
> - **表名 3 段命名铁律**：模板中 `⟦别名⟧` 一律翻译为 `x_tupu.entity_aliases` 给出的**完整表名（含 `pg_tupu.public.` 前缀）**，`FROM pg_tupu.public.cms20_adj_volt_dev`；**禁止写裸表名**（裸表名在默认 catalog 下 Unknown table，前端实测 2026-08-21）。
> - `recommended_tool=execute_doris_sql`（表已绑 doris_catalog）-> `execute_doris_sql(sql=三段命名SQL)`，**不传 entity_code**，传完整 SQL。表名前缀按 batch 返回的 `doris_catalog` 拼：`pg_tupu` -> `pg_tupu.public.表名`，`es_tupu` -> `es_tupu.default_db.表名`，跨 catalog JOIN 直接拼接。例：`SELECT ... FROM pg_tupu.public.cms20_cst_cust a JOIN es_tupu.default_db.vw_cust_power_ts b ON ...`
> - `recommended_tool=execute_api_sql`（多表含 api_integration 跨源 JOIN）-> `execute_api_sql(sql=SQL)`，DuckDB 联邦，API 虚拟表 + pg 物理表自动 JOIN，表名用裸表名（后端自动加 pg. 前缀 + API 虚拟表替换）
> - `recommended_tool=execute_entity_api`（单表 api_integration）-> `execute_entity_api(entity_code, filters)`
> - `recommended_tool=execute_sql`（未绑 catalog 的物理表，兜底）-> `execute_sql(sql, entity_code)`（传主表 entity_code）
> - **兜底降级**：若 `execute_doris_sql` 报 `Unknown table`/`Unknown catalog`（表未纳管 catalog），可降级 `execute_sql(sql, entity_code)` 物理直连重试一次。
> 无需调 fetch_join_expr / validate_safe_sql / validate_attributes（剧本已覆盖其职责）；定位类工具（fetch_l1_l2_tree/validate_l2/fetch_subgraph）按上方「实体定位顺序」在跨业务域取数前使用，`search_entities` 仅作定位失败兜底或列名排查（2026-08-25 批13-M 改写：原「一律无需定位」与定位优先定调冲突，已按四步顺序修订）。
> **列名/表名以元数据为准**：SQL 模板中的列名已与 `kg_entities` 元数据核对一致（三方核对：技能↔元数据↔PG 全部匹配），**直接使用模板即可**。用户改了实体属性后，若 SQL 执行报列名错误，调 `kg_api(action=search_entities, params={"entity_code":"<表名>"})` 确认正确列名后修改重试。
>
> **空结果处理铁律（2026-08-24 前端实测「哪些台区过载」暴露后补）**：判定 SQL 执行成功（无 error）但返回 0 行时，**这就是最终答案**——如实作答「查询时段内无重载/过载台区」，并提示用户可指定日期缩小范围（模板含 `【动态】AND pw.date='YYYYMMDD'` 注释位）。**禁止**因结果为空而换工具、换引擎、改写 SQL 结构重试：
> - 空结果的常见原因是功率时序表在该日期段无 96 点数据，换任何工具重查结果相同；
> - 模板经 strict 校验绑定，改写结构必被拦截并计违规（2 次违规阻断本轮）；
> - 引擎锁定后切换引擎同样被拦（契约一致性）。正确动作只有两个：如实报告空结果，或按用户补充的日期过滤重查一次。

## 核心设计：三步可独立执行

| 用户问什么 | 执行步骤 | 返回 |
|---|---|---|
| 户变关系（用电户/发电户 与 台区/配变关系） | **仅第1步** | 关系明细表 |
| 重过载情况（重载/过载/负载率/96点功率） | **第1步+第2步** | 判定结果表(含重过载时段) |
| 连续N天重过载（持续重过载/连续几天） | **第1步+第2步扩展** | 连续天数统计表 |
| 负载占有率排序（倒排/影响最大） | **第1步+第2步+第3步** | 客户负载倒排表 |

> **台区是计算单元**：一个台区有一个或多个配电变压器（多路供电），负载率 = 台区下所有计量点功率 / 台区所有配变容量之和。计量点(inst_id)是最小粒度，功率从计量点出发汇集到台区。

## 触发条件
满足任一即命中：
1. 含"户变关系"+"用电户/发电户/配电变压器/配变"
2. 含"重载/过载/负载率/96点功率/用电负载/上网负载/发电负载"
3. 含"负载占有率/倒排/排序/影响最大"
4. 含"哪些用户受影响"+"配电/配变"上下文
5. 含"连续N天/持续重过载/连续几天重过载/重过载持续天数"

## 按需读取子文件（不要一次全读）

用户问什么 -> 执行哪步 -> read_file 读哪个子文件（完整路径，直接用 read_file(file_path=...) 读取）：

| 用户问 | 执行 | 必读 SQL 模板 | 按需读参考 |
|--------|------|-------------|-----------|
| 户变关系 | 第1步 | 只问**用电户**: `/skills/scenarios/distribution-overload/templates/step1_household_transformer_elec.sql`；只问**发电户**: `.../step1_household_transformer_gen.sql`；问**两者/泛问**（如"所有户变关系"）: `.../step1_household_transformer.sql`（UNION 全量）| `/skills/scenarios/distribution-overload/reference/scope_cte.md`（限客户时）|
| 重载/过载/负载率 | 1+2 | step1 + `/skills/scenarios/distribution-overload/templates/step2_power_aggregation.sql` | `/skills/scenarios/distribution-overload/reference/rules.md`（口径）|
| 统计/多少/几个/数量类（如"统计重过载台区数量"、"有多少个台区重过载"） | 第2步 COUNT | `/skills/scenarios/distribution-overload/templates/step2_count_overload.sql`（单行四列计数，勿用明细模板） | `/skills/scenarios/distribution-overload/reference/rules.md`（口径）|
| 连续N天重过载 | 1+2扩展 | step1 + `/skills/scenarios/distribution-overload/templates/step2b_continuous_days.sql` | `.../reference/rules.md` |
| 负载占有率/倒排 | 1+2+3 | step1 + step2 + `/skills/scenarios/distribution-overload/templates/step3_load_ratio.sql` | `.../reference/rules.md` |
| 任何步（用户带过滤条件） | - | - | `/skills/scenarios/distribution-overload/reference/dynamic_filters.md` |
| SQL 列名报错 | - | - | `/skills/scenarios/distribution-overload/reference/table_schema.md` + search_entities |
| 码值转码 | - | - | `/skills/scenarios/distribution-overload/reference/code_dict.md` |

> **按需读，不预读**：只读当前问句需要的 SQL 模板，不把 4 个模板全读进来。表结构/关联键在 `reference/table_schema.md`，码值在 `reference/code_dict.md`，口径硬规则在 `reference/rules.md`，只在需要时 read_file 读取。
> **read_file 调用示例**：`read_file(file_path="/skills/scenarios/distribution-overload/templates/step1_household_transformer.sql")`

## 最小终止规则（硬规则，违反即错误）

1. **第1步拿到结果即终止**：户变关系查询只要 SQL 返回 `row_count > 0`，立即基于结果生成最终答案。禁止为"展示完整结果"分页重查或启动 task 子代理。
2. **row_count 就是全部数量**：SQL 工具返回的 `row_count` 是完整结果数（如 N 行）。`returned_rows`/`preview_row_count` 是给 LLM 的预览行数（如 10 行），不等于数据不完整。完整数据已推前端表格分页展示。**禁止在结论里写死行数**——一律以 SQL 实际返回的 `row_count` 为准，不要引用任何预设数字。
3. **"所有"类查询不拆分**：用户问"所有用电户与配变户变关系"时，一次查询拿到全部行（以 `row_count` 为准）即完成。禁止按台区段（020-029、030-039）逐段查询。
4. **row_count=0 时如实报告**：SQL 返回 0 行时，如实说明"当前数据中未查到用电户与配变/台区的关联记录"，给出已查询的表与关联范围，**不编造行数、不臆造关系**，仍输出结论（数据不足结论）。
4. **禁止 task 子代理**：户变关系是简单全量查询，不需要独立推理链。task 子代理仅用于复杂分析（如需要多步推理的重过载判定）。
5. **仅在以下情况才执行第2/3步**：用户明确要求"重载/过载/负载率/96点功率/负载占有率/倒排"，或用户指定了日期/状态需要做判定分析。

## 输出格式硬规则（必须遵守）

1. **禁用波浪号 `~` 表示范围**：范围一律用中横线 `-`（写"台区001-095"，禁写"台区001~095"）。波浪号会被前端 Markdown 误渲染成删除线，导致范围文字被划掉、`~` 消失。
2. **原始明细由前端查询结果表唯一展示**：禁止在最终回答输出与结果表同字段的 Markdown 明细表、前 N 行预览表格。最终回答仅输出结论、关键发现、风险/限制、后续建议，并明确写"完整明细见下方查询结果表"。前端会在存在权威 `sql_result` 时自动屏蔽 Markdown 表格节点。
3. **码值一律显示中文名**（如"用电"而非"01"、"10kV"而非"AC00101"、"分布式光伏"而非"01"、"在运"而非"20"）。实体表已冗余存储 `_name` 中文名列，SELECT 时优先取 `_name` 列；裸编码仅在不产生歧义时作为括注补充。
4. **一户多号须如实呈现**：同一 cust_id 有多个户号(如 gpc_id=1 和 gpc_id=901)时，分属不同台区的独立计量点，SQL 须逐行返回、不合并、不省略（展示由前端查询结果表完成）。
5. **样本≠全量**：只对 row_count 下全量结论（如"共 101 条"）；对行内字段（单路供电/状态正常/10kV 等）只能说"样本显示"。要输出"全部正常 / 全部单路供电 / 所有 X 均 Y"类全量结论，必须由 SQL 显式聚合统计（COUNT/GROUP BY）提供证据后再下。

## 输出规范

> **列规范说明**：以下表格定义的是**前端查询结果表（唯一数据表）的列结构**——SQL 必须 SELECT 这些列，返回的行即查询结果表的内容。**不要把下列列输出为 Markdown 表格**；最终回答只写结论、关键发现、限制与建议，并注明"完整明细见下方查询结果表"（见"输出格式硬规则"第 2 条）。

**第1步（户变关系）**：

| 客户类型 | 客户编号 | 客户名称 | 行业分类 | 客户分类 | 计量点编号 | 用途类型 | 台区编号 | 台区名称 | 配变列表 | 台区总容量 | 电压等级 |
|---|---|---|---|---|---|---|---|---|---|---|---|

**第2步（台区级重过载判定，含时段）**：

| 负荷类型 | 台区编号 | 配变列表 | 台区总容量 | 最大负载率 | 重载点数 | 过载点数 | 最长连续重载 | 最长连续过载 | 过载时段起 | 过载时段止 | 重载时段起 | 重载时段止 | 判定 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

**第2步扩展（连续N天重过载统计）**：

| 台区编号 | 连续天数 | 持续起始 | 持续结束 |
|---|---|---|---|

**第3步（客户负载占有率倒排，仅重过载台区）**：

| 客户类型 | 负荷类型 | 客户编号 | 客户名称 | 台区编号 | 配变列表 | 台区总容量 | 达标点数 | 平均负载(kW) | 负载占有率(%) |
|---|---|---|---|---|---|---|---|---|---|

**COUNT 例外条款（问法级，优先于下方四段模板）**：COUNT 类问法（用户问数量/多少/几个，如"统计重过载台区数量"）**不适用四段输出**——使用 `templates/step2_count_overload.sql` 单行计数模板，只输出一句结论（含具体数值，如"重过载台区共 N 个，其中过载 X 个、重载 Y 个"）+ 一句口径注（阈值口径/时间范围/数据源），合计 ≤150 字；不展开结论/发现/风险/建议四段。

**一句话结论**：共 X 个台区（单路 Y 个、多路 Z 个），用电负载重载 A 台、过载 B 台；上网负载重载 C 台、过载 D 台；负载占有率最高用户 W（占有率 V%，达标点 N 个），为该台区重过载主因。其中连续多天重过载 M 个台区（最长持续 K 天，起止 [起始]~[结束]）。另有 E 个台区发电负荷较高（自发自用），发电负荷仅参考不计入配电重过载统计。若用户指定了日期/状态，结论注明"基于[日期][状态]数据统计"。

## 降级规则
- 台区/配变/客户编号缺失 -> 第1步先查户变关系反查编号
- 台区无配变关联（dist_sta_id 在调压设备中无记录）-> 如实说明"该台区无配变关联，无法定位配变"
- 功率数据不足8个时间点 -> 按点数近似判定，结论注明"数据稀疏，连续性为近似"
- 功率数据为空 -> 如实告知"该计量点无96点功率监测数据"，不编造结果
- 用户只问用电户/发电户 -> 选用电户/发电户**单段变体模板**（`step1_household_transformer_elec.sql` / `step1_household_transformer_gen.sql`），**禁止对 UNION 模板做删段改写**（scenario_strict 结构冻结：删段属结构变化，平台不允许）；问两者/泛问（"所有户变关系"）才用 `step1_household_transformer.sql`（UNION 全量）
- 用户只问某类负荷 -> WHERE 加 `AND inst_usage_cls='对应码'`（仅支持'01'用电/'1102'上网，发电'1101'不判定只参考）
- 用户指定日期 -> dist_power 的 WHERE 加 `AND pw.date='YYYYMMDD'`；未指定则全量(多天分别判定)
- 用户指定状态/分类 -> 按 `reference/dynamic_filters.md` 传参表注入对应 AND 条件
- 第3步无重过载台区 -> 如实告知"本周期无台区达到重过载阈值，无法做客户负载占有率倒排"
- 多路供电台区 -> 配变列表显示多个配变，台区总容量为各配变容量之和，负载率按总容量计算
- 用户问"连续N天" -> 第2步扩展 WHERE `连续天数 >= N`；数据无跨天则各台区最多1天，如实说明
