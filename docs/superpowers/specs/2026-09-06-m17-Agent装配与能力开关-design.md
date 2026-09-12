# M17 Agent 装配与能力开关 设计规格（金标准）

> 套件：DeepAssetLens 全量金标准 M17（总纲见 m00）。as-if-greenfield 视角。
> 取证基线：HEAD `0d67f4c`（2026-09-06）。本模块改动须先过两技能管线并回写本 spec 状态。

## 一、模块定位

问数智能体域的**装配层**：DeepAgent 实例的创建/缓存/版本化重建（能力开关+守卫版本+文件哈希三因子缓存键）、fail-safe 装配（新配置坏→回退上一可用版本→回退也坏 fail-closed）、**能力开关中心**（白名单打勾制、安全红线五件、物理锁定三件、DecisionGate 范围件、事件审计）、技能文件种子与 SKILL.md 缓存、会话持久化（Checkpointer）。前端安全控制中心的能力开关面板。

**边界**：SkillPolicy 执行守卫归 M19；路由与契约对象归 M18；LLM 连接归 M11（connection_id 透传）；MCP 工具挂载点归 M01/main.py（本模块定义受控工具注册表语义）。

## 二、组件清单

| 组件 | 文件 | 职责 |
|---|---|---|
| Agent 装配 | `services/tupu_deepagent.py`（1265 行） | create_tupu_agent（fail-safe）/_build_agent（caps 条件装配）/get_tupu_agent（三因子缓存）/LRU 回收/Checkpointer/规则常量族/SQL 纠错/Rubric 中间件 |
| 能力开关中心 | `services/capability_config.py` | policies 缓存（5s TTL）/版本号/白名单换算/参数校验/事件审计/reset-defaults |
| 能力开关 API | `api/capabilities.py` | /api/capabilities：list/manifest/PATCH update（confirm+close_reason）/probe/events/reset-defaults |
| 前端 | `pages/SecurityControlCenter.tsx`（CapabilityPanel 等）+ `services/api.ts` capabilitiesApi | 七步工作流 Tabs/装配清单总览/试探单/审计/导出 |

## 三、Agent 装配三因子缓存（核心架构）

```
缓存键 = "<connection_id|__default__>#g{guard_ver}#c{caps_ver}#f{files_hash}"
  g：guard_config 版本（M19 守卫 PATCH 后 +1）
  c：capability_config 版本（能力 PATCH 后 +1）
  f：_compute_files_hash()（技能/纪律树增删改——批13-Y）
任一成分变化 → 缓存失配 → 下次请求重建新实例
LRU：_evict_old_agents 保留最近 2 个能力版本（在跑请求引用计数保活）
懒加载 + _AGENT_INIT_LOCK（并发首次初始化互斥）
Checkpointer：AsyncSqliteSaver（data/deepagent_checkpoints.db）——HITL/记忆持久化
```

**失败语义**：create_tupu_agent 装配异常→_LAST_GOOD_ASSEMBLY 回退（写 capability_events fallback 事件）→回退也失败→**fail-closed 抛错**（P0-1：配置写坏不全瘫，但最后一道也不带病创建）。

## 四、能力开关中心（capability_config）

**工具白名单打勾制**（批13-W W-1，用户 2026-08-24 定调）：黑名单→白名单语义反转——新工具没打勾天然免疫（框架升级新增工具不漏网）。换算公式：`excluded = 安全红线5件 ∪ (勾选域 − allowed)`，喂 HarnessProfile(excluded_tools=...)。
- **安全红线 5 件**：write_file/edit_file/execute/grep/glob——物理不在勾选域（HarnessProfile 硬排除），白名单不可配置；
- **物理锁定 3 件**：read_file（技能渐进披露命脉）/ls（文件浏览域外恒允许）/task（子代理命根子）——前端灰显、PATCH 校验强制保留；
- **勾选域**：MCP 受控工具（GENERIC_ALLOWED_TOOLS 17 件）+ task。

**DecisionGate**（批13-W W-4/W-4a）：范围工具集代码基准 DECISION_GATE_SCOPE_DEFAULT 四件（execute_sql/execute_doris_sql/execute_entity_api/execute_api_sql）；seed_enabled=False——fail-safe 回代码基准=关（env=1 部署由环境变量兜底，TUPU_DECISION_GATE）；管理页只能改当前值，基准钉死代码。

**评分模式**（批13-AB3）：rubric mode 枚举校验——skill_prompt（自检段进系统提示词，默认）/middleware（独立评分模型路径保留）；非法值 400 不落库。

**API 契约**：PATCH 白名单语义（PATCH allowed 允许集；未知名 400；excluded 键显式拒收防黑名单混写）；黄/红线二次确认（confirm+close_reason）；probe 试探单；events 审计查询（30 天清理 cleanup_old_events）；reset-defaults 回代码基准；manifest 装配清单总览（Tab0）。

## 五、Agent 内部组装件（tupu_deepagent）

- **规则常量族**：_BASE_ROLE（电力数据图谱问答角色）/_SOURCE_MODE_DISPATCH_RULES（source_mode 三模式分派——M07 联动）/_COMMON_RULES/_SQL_FLOW_RULES/_DECISION_GATE_RULES（env 开关 TUPU_DECISION_GATE=1）/_DATA_COMPLETENESS_RULES/_KNOWLEDGE_FLOW_RULES——**动态 system prompt 组装**（_build_dynamic_system_prompt，skill_hint 空=自主模式全量概要/非空=该技能 SKILL.md 注入）；
- **技能文件种子**：_seed_files（store 命名空间 tupu.skills/tupu.memory）+ _compute_files_hash（mtime 归并哈希）；_load_skill_md（mtime+size 键缓存）；
- **Rubric 自评**：RUBRIC_SELF_CHECK_PROMPT + _rubric_effective_mode + _TupuRubricMiddleware(RubricMiddleware) + _on_rubric_evaluation + _is_clean_aggregate_result——**金标直通判定 rubric 路径**（M20 联动，阈值 0.85）；
- **最终交付 schema**：FinalFinding/FinalDelivery BaseModel + _FINAL_RESPONSE_FORMAT（**装配期静态参数**——response_format 运行时不可按题条件化，批13-L 框架边界证据）；
- **SQL 纠错循环**：_remove_column_from_select/_fix_aggregate_unknown_column——列名错误自动修复重试；
- **_DATA_QUERY_TOOLS frozenset**：数据查询工具白名单（守卫与分流引用）；
- **TupuAgentState/TupuAgentContext**：状态/上下文类型扩展（DeepAgentState 子类）。

## 六、设计原则（本模块特有）

1. **fail-safe 三段**：新配置坏→回退上一可用→回退坏 fail-closed——能力开关永远不能把 Agent 装配死；
2. **白名单天然免疫**：工具放行靠打勾（新工具默认禁）——黑名单模式被用户定调废止（2026-08-24）；
3. **红线物理排除、锁定件不可取消**：安全边界不由配置层决定（配置层只有「当前值」，基准钉死代码）；
4. **三因子缓存键**：配置/守卫/技能文件任一变化即重建，LRU 保活在跑请求——「PATCH 后下一问生效」是唯一语义；
5. **装配期静态约束如实登记**：response_format 不可运行时条件化（批13-L 框架边界）——契约指令等效落地；
6. **审计即事件**：一切装配行为（rebuild/fallback/update/reset）写 capability_events。

## 七、验收标准

1. 三因子缓存：PATCH 能力开关→版本+1→下一问新实例（旧请求不断）；files_hash 变化同理；LRU 保留 2 版；
2. fail-safe：构造坏配置 PATCH→装配失败自动回退旧版本（fallback 事件落表）；连回退也坏→抛错不建实例；
3. 白名单：取消勾选工具→下一问该工具被 excluded；红线 5 件无勾选框；锁定 3 件 PATCH 取消被拒（400）；
4. DecisionGate：默认关（代码基准）；开启后范围四件裁决；env=1 兜底部署生效；
5. 评分模式：PATCH 非法 mode 400；skill_prompt/middleware 两路径可用；
6. probe 试探单对坏配置返 ok=False；reset-defaults 回代码基准；manifest 返回装配清单+版本；
7. SQL 纠错：列名错自动修复重试（桩触发）；Rubric 自评流程按 mode 生效（M20 联测）；
8. 前端：七步 Tabs/总览/试探单/审计/导出/二次确认（黄红）全可用。

## 八、风险与偏差登记

| 项 | 说明 |
|---|---|
| response_format 装配期静态 | 框架边界（批13-L 已调和：契约指令等效）——运行时按题条件化需求须过设计 |
| 进程级 Agent 缓存 | _GLOBAL_AGENTS 在进程内（workers=1 前提）——多进程部署须重评（M01 登记联动） |
| 能力项未知按启用 | cap_enabled 未知名返 True（不改变现状行为）——登记：新能力注册须显式入表 |

**偏差登记**：
| 日期 | 差异 | 处置 |
|---|---|---|
| 2026-09-08 | 批次核验通过（验证-对齐主路径）：capability_config 锚点与 spec §九对齐（红线 W1_REDLINE_EXCLUSIONS 5 件/锁定 W1_LOCKED_TOOLS 3 件含 task/换算公式 L229/DecisionGate 基准四件/评分枚举校验）；补测 10 条全绿（白名单换算 excluded=红线∪(勾选域−allowed) 默认全勾=红线 5 件+locked 三件展示/cap_enabled 未知名 True 登记语义/DecisionGate 基准四件/rubric mode 非法值拒/_DATA_QUERY_TOOLS/FinalDelivery+FinalFinding pydantic/SQL 纠错双函数/files_hash 稳定/capabilities 6 端点 manifest+probe+events+reset） | plan 任务 1-4 验证-对齐完成；真装配（DeepAgent 实例/三因子缓存重建/fail-safe 回退）依赖框架与 LLM 留联测；rubric M20 联测留批次 4 |
| 2026-09-08 | 测试锚点：get_tool_exclusions 返回形状为 `{excluded:[...],locked:[read_file,ls,task]}` 单层双键（spec §四文字「锁定件前端灰显、PATCH 强制保留」对应 locked 键展示——锁定语义在 get_tool_allowance 侧强制） | 测试按真实形状锚定；LOCKED_TOOL_EXCLUSIONS 模块常量（L162）=read_file/ls 而 W1_LOCKED_TOOLS 含 task——以 W1_LOCKED_TOOLS 为锁定全集 |
| 2026-09-12 | 极速模式预设批次：capability 种子清单 **+1 行 `locate_budget`**（`CAPABILITY_POLICY_SEED` 尾增行：查询类工具定位预算 enabled 默认开 params={generic:8,scenario:14}——与 env 默认 TUPU_LOCATE_BUDGET 同值语义）+`_seed_capability_policies` 增量补种自动落行实证（存量库重启后 19→20 行，重启日志+GET /api/capabilities 双证）；decision_gate 预设联动（preset turbo/safe 组合表经既有 update_capability 链置态——env 兜底语义零改动，红线 5 守住）；e2e 实证 turbo 下 WBS 类题零拒绝三跑中位 81s（定位预算保留开+预算参数三级读取 enabled>params>env） | 见 init_db.py 种子行+skill_policy.py `_locate_budget_policy` L78-94；test_turbo_preset.py 11 测；M17 联动登记于 M19 批次行 |
| 2026-09-12 | 终局审查勘误（账面层，与 M19 勘误行同笔）：**`TUPU_DECISION_GATE=1` env 兜底交互**——capability_config L195 `enabled = env_on or cfg_on`，.env 置 1 时 preset 对 decision_gate 行的置关不改变运行态（env 兜底优先=中间件恒装）；「零拒绝」更正为守卫类拦截 0 次+决策门拒绝 1 次（同轮补判 committed）；速度结论反而更保守（决策门实际在装） | 红线 5 env 兜底语义保留；`.env` 去留交用户裁决 |
| —— | —— | —— |

## 九、证据锚点

装配 `tupu_deepagent.py`：fail-safe L1098-1125（fallback/fail-closed）/三因子缓存键 L1173-1225（LRU L1151-1170/懒加载锁 L1142-1143/Checkpointer L1145-1148）/规则常量族 L86-233/build_skill_system_message L1128-1134/_seed_files·files_hash L396-441/Rubric 族 L354-394·L632-789/FinalDelivery L513-548/SQL 纠错 L550-631/_DATA_QUERY_TOOLS L345-353/决策门 env L174｜开关中心 `capability_config.py`：白名单定调 L139-146/红线 L158-163/锁定件 L155-156/DecisionGate L170-196/评分枚举 L336-340/校验 L276-353/事件 L355-382/reset L434/清理 L475｜API `api/capabilities.py` + 前端 `SecurityControlCenter.tsx` CapabilityPanel L115-660（manifest Tab0 L550-558/七步 Tabs L1149-1157/导出 L360-363）+ `api.ts` L518-572。
