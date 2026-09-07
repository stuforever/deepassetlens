# 场景 COUNT 题直通收敛·欠账收口设计（spec）

> 2026-09-06 · 设计窗口产出。来源：用户「补欠账」定调——把会话与代码中登记的欠账收进两技能标准产物（本 spec + 配套 plan）。
> 证据基线：HEAD `0d67f4c`（批15 全落地、全量 680 passed、后端 28000 已运行新代码）。
> 分工：设计窗口出本设计与计划（不动码）；实施会话执行、提交入库、主文档登记（批16-A）。

## 一、欠账盘点（本 spec 覆盖范围）

| 类别 | 项 | 处置 |
|---|---|---|
| 可行动欠账（唯一） | 场景 COUNT 题「统计重过载台区数量」端到端 136~200s（输出已正确），与直通 9s 差一个量级；批14-A 验收登记「进一步收敛=定位链优化」至今未设计 | §四~§五 设计 + 配套 plan |
| 闸后欠账 | 13-Z 三后续 / 摘要 profile / 13-X-3 / http→https 等 | §六 登记（触发到才设计，YAGNI） |
| 交接欠账 | 设计初衷还原 doc / AGENTS.md 规划纪律节 / 本 spec+plan（均未提交） | §七（实施会话随批16-A 提交） |

## 二、现状证据（全部代码锚点，HEAD 0d67f4c）

1. **缺口根因（本轮取证新发现）**：直通管道的路由门——`evaluate_direct_eligibility`（`backend/app/services/direct_pipeline.py` L32-61）**L39 要求 `route_type == "generic"`**；场景 COUNT 题走 scenario 路由 → 永远进不了 0 LLM 轮直通（2~4s）→ 只能走 Agent 循环（多轮 × 每轮 LLM 延迟 ≈ 136~200s）。
2. 直通安全链（L11-13 原文声明）：来源可信（status=enabled 已验证 SQL 单源）+ `validate_safe_sql`（SELECT-only/强制 LIMIT）+ 模板白名单渲染；执行报错自动回退完整 Agent 路径。
3. 其余直通条件**已在位且场景题天然满足**：
   - `golden_hits` ≥0.95：契约组装通用流注入（`data_intelligence.py` L185，60s 短窗缓存 L169），**非路由门控**——scenario 契约同样携带；
   - `is_count_intent`（`intent_classifier.py` L107-118）：「统计重过载台区数量」含「数量」命中；
   - 无动态条件（`has_dynamic_condition` L121-135：比较/日期/编号词）；
   - engine ∈ (doris, physical)（L58-60）。
4. 金标机制（批13-C 后）：`kg_golden_qa_set` + Qdrant `tupu_golden_qa` 增删改同步；`add_golden`（`golden_qa_service.py` L157-176）digest 自动执行计算；**计数同义归一化**（L44：数量→总数，L43 注释「确定性命中金标 score=1.0」）。
5. 计时工具已在位：`backend/scripts/_diag_timing.py`（逐轮计时，诊断用）+ `[PrepTiming]` 五段（`freeplan/prep.py`）+ done 载荷 timing（`freeplan/endpoint.py` L132-137/L825-832）。
6. P0 预算闸门已装弹未收紧：`TUPU_LOCATE_BUDGET_SCENARIO` 默认 14（commit ad66b2d）。

## 三、目标 / 非目标

**目标**：
1. 场景 COUNT 题端到端 **≤15s**（直通级；现状 136~200s）；
2. 判定表输出与 14-A 验收**完全一致**（表头 重过载台区数/过载台区数/重载台区数/判定台区总数，首行 2/1/1/2）；
3. generic 直通、非 COUNT 场景题（明细题）、澄清卡行为**零变化**。

**非目标（YAGNI）**：
- 不做定位链轮次优化（若取证不支持则不做）；
- 不做 COUNT 措辞变体专项扩容（先测金标锚定+同义归一化的天然覆盖率，缺口才立项）；
- 闸后欠账一概不动。

## 四、方案对比

| 方案 | 内容 | 裁决 |
|---|---|---|
| 零·取证基线 | 跑 `_diag_timing.py` + 读 `[PrepTiming]`/done timing，落一页取证记录 | **必做前置**（0 新代码，工具现成） |
| 一·金标种子 | `add_golden` 入库该题已验证问答对（SQL 单源 = MetricQueryLog 最近成功执行的 `executed_sql`） | **必做**（数据前置；单独无效——scenario 仍被 L39 挡） |
| 二·直通资格放开 | `evaluate_direct_eligibility` L39 路由门 `generic` → `{generic, scenario}`，一处条件 + 单测 | **主案**（最小 diff，安全链全部不变） |
| 三·预算闸门收紧 | `TUPU_LOCATE_BUDGET_SCENARIO` 14 → 更紧 | **闸后备选**：仅当方案零取证显示定位轮爆量时启用 |

说明：方案一+二是一个交付单元的两半（种子给直通供「已验证 SQL」，路由门让 scenario 够得着直通）；与既有分层（批2-C 首选计划 0.90~0.95 → Agent 1-2 轮）不冲突——分层阈值 `TUPU_DIRECT_PIPELINE_SIM` 不动。

## 五、详细设计（代码级，落点在配套 plan）

1. **种子**（方案一）：`backend/scripts/_seed_16a.py`——幂等（同问题已存在跳过，对齐 `seed_golden` L204 语义）；SQL 取 `MetricQueryLog`（`query_status == "success"` 且 `user_query` 精确匹配，列名实据 `seed_golden` L228-232）；`route_type="scenario"`, `scenario_tag="distribution-overload"`；engine 由 `add_golden` 内 `_infer_engine` 推断；入库后脚本自查 `search_golden_qa` Tier1 命中。
2. **路由门**（方案二）：`direct_pipeline.py` L39 一处条件改动（`!= "generic"` → `not in ("generic", "scenario")`），注释注明批16-A 与安全链声明；新增 `backend/tests/test_16a.py` 七测（前置 sanity + 场景 COUNT 可直通 + 非 COUNT 场景不直通 + 动态条件不直通 + 低分不直通 + 澄清卡不直通 + generic 原样）。
3. **验收**：Playwright 串行 e2e（`_pw_e2e.py` 现成入口）——COUNT 题出表一致且 ≤15s；generic 直通题与明细题回归。

## 六、闸后欠账登记（触发条件到才设计，勿预支）

| 项 | 触发条件 | 出处 |
|---|---|---|
| 13-Z 三后续（小弟模型降配/委派成功率面板/并行收益验证） | task_invoke > 0 | 主文档 L420 |
| 摘要 model profile（官方件自适应 85%） | 超限重试日志 / 长会话常态化 | 主文档 L422（13-AB 潜在风险登记） |
| 13-X-3 adapter 候选 | 主文档 13-X 在册触发条件 | 主文档 13-X 条目 |
| http→https + apikey 安全连接（余 35 warnings 中 qdrant 相关项） | infra 变更窗口 | 批14-D 登记 |
| 方案三（预算闸门收紧） | 方案零取证显示定位轮爆量 | 本 spec §四 |
| COUNT 措辞变体专项扩容 | 任务五变体评估确认缺口 | 本 spec §八/plan 任务5 |

## 七、交接欠账（实施会话随批16-A 一并提交）

1. `docs/设计初衷还原_为什么用deepagents与能力使用全景_20260906.md`（设计窗口产出，未提交）；
2. `AGENTS.md`「设计窗口规划纪律（铁律）」节（2026-09-06 用户定调，未提交）；
3. 本 spec + 配套 plan。

## 八、验收标准（汇总，写入 plan）

1. `test_16a.py` 七测全绿，全量 pytest **687 passed**（680+7），warnings 不增；
2. Playwright 串行 e2e：「统计重过载台区数量」判定表 4 列表头 + 首行 2/1/1/2 + 端到端 ≤15s；
3. 回归：generic 直通题「统计用电客户总数」秒级出数不变；明细题「哪些台区重过载」走 Agent 出明细不变；
4. 决策点：3 个 COUNT 措辞变体（「重过载台区有多少个」「重过载的台区数目」「数一下重过载台区」）各跑一轮——全直通且出表一致 → 类级覆盖达标收口；有缺口 → 回设计窗口按两技能流程出后续 spec（闸后登记，不现场扩）。

## 九、风险登记

| 风险 | 评估 |
|---|---|
| count SQL 与 validate_safe_sql 强制 LIMIT 的相互作用 | 单行 4 列聚合输出；校验失败抛 `DirectPipelineError` → 回退 Agent（无损降级，L29 语义）；e2e 兜底验证 |
| 金标无自动漂移失效（数据变更后直通仍执行旧 SQL） | 与 generic 直通**同现状**（非新风险，不放大）；依赖 👎 反馈观测与管理页下架处置 |
| 跨路由金标命中（generic 问法命中 scenario 金标或反之） | 同一安全链下可接受（相似问法 → 已验证 SQL）；不另设路由匹配检查（YAGNI） |
| 变体题 Tier2 相似度达不到 0.95 | 预期行为（走 Agent，正确性不受影响）；缺口属§六闸后项 |

## 十、证据锚点表

| 论断 | 出处 |
|---|---|
| 路由门 L39 挡 scenario | `direct_pipeline.py` L39 |
| 直通安全链四件套 | `direct_pipeline.py` L11-13、L64-75（run_direct_pipeline） |
| golden_hits 契约通用注入（非路由门控） | `data_intelligence.py` L169-214（L185 写入） |
| add_golden 签名/同义归一化/幂等参照 | `golden_qa_service.py` L157-176 / L43-44 / L204 |
| MetricQueryLog 成功记录列名 | `golden_qa_service.py` L228-232（seed_golden 抽样过滤） |
| is_count_intent / has_dynamic_condition | `intent_classifier.py` L107-135 |
| 136~200s 现状与 9s 直通对照 | 批14-A 验收登记；批15 commit 05e855a e2e（场景 136s/直通 9s） |
| 计时工具 | `backend/scripts/_diag_timing.py`、`freeplan/prep.py`、`freeplan/endpoint.py` L132-137 |
