# 会话交接文档（2026-08-17）

> 用途：新开会话时作为背景上下文。可直接把本文件内容喂给新会话，或用 `ReadSessionContext` 读取。
> 项目：**DeepAssetLens（tupu 知识图谱问答平台）**，根目录 `D:/gitcangku/deepassetlens`
> 主题：历次会话已完成的安全/交付协议/前端治理工作 + **未完成的「当前代码可优化方向分析」**。

---

## 〇、本会话最重要的事（务必先读）

1. **本会话主线任务（用户最初请求）未完成**：`分析下当前代码可优化方向`。当时因 Explore 子代理故障（"Provider authentication failed"）未产出分析，随后会话被 DeepTutor 任务占用。**新会话应优先补做这个分析**（只读分析，不改代码）。
2. **本会话实际执行的是 DeepTutor 前端优化**（另一仓库 `D:/gitcangku/xiaobaohaohao/DeepTutor`，用户误投任务书）：8 个任务全部完成（P0 死依赖/懒加载/清理、P1-1 消灭 any、P1-2 i18n、P2 Server Component/analyzer、P3 eslint）。**该仓库与本项目无关**，其交接文档已删除，代码改动保留在 DeepTutor 仓库（未提交）。新会话**不要**再进入 DeepTutor 工作，除非用户明确要求。
3. **DeepTutor 代码改动未回退**：因删除会连带清除用户自己新建的未追踪模块（mother-questions/self-learning 等）。若用户要求整体回退 DeepTutor，需另行操作（`git checkout` 追踪文件 + 删除未追踪文件，破坏性操作，先与用户确认）。

---

## 一、项目定位与基线

- **平台**：DeepAssetLens（tupu 知识图谱问答），FastAPI 后端 + React 前端，配 MySQL/PG/ES/Doris/Neo4j/Qdrant/Authentik/Sandbox。
- **git 基线**：`3bed53a refactor: decouple tupu from ragflow, add independent MySQL/ES stack`（此后改动均未提交）。
- **当前未提交改动**：87 项（后端服务/测试/数据脚本/前端工具/测试全为未提交状态），详见第五节。
- **服务状态（2026-08-17 实测）**：后端 28000 **LISTENING**（PID 33144）、前端 dev 23000 **LISTENING**（PID 16220）——均已在跑。

---

## 二、已完成工作清单（历次会话，均有代码/测试佐证）

### 1. FinalDelivery 交付协议（后端+前端全链路）
- `backend/app/services/tupu_deepagent.py`：`FinalFinding`/`FinalDelivery` 模型；`_SQL_FLOW_RULES`（规则7禁止原始明细/预览）；`_DATA_COMPLETENESS_RULES`；`DataSummaryMiddleware`（`data_result` 事件全量 payload、10 行 LLM 抽样截断、`is_preview`/`llm_is_preview`/`llm_preview_row_count` 语义）；`_response_format = None`（**GLM 不兼容嵌套 schema，勿改回结构化输出**）。
- `backend/app/api/data_intelligence.py`：`_safe_error_summary`、`_empty_result_text`、`_build_final_delivery`（A-E 确定性降级，已删除四段式摘要兜底）。
- 前端：`frontend/src/utils/finalDelivery.ts`（buildFinalDeliveryView/resolveFinalAnswer）；`components/conversation/MessageTabs.tsx`（5-tab：答案/思考/数据/定位/推荐）；`AssistantCanvas.tsx`（ReactMarkdown 组件级表格掩码）；`SqlResultTable.tsx`（分页 + "查询明细（唯一数据表）"）；`FreePlanChat.tsx`；`services/dataIntelligenceApi.ts`（ChatResponse.final_delivery）。
- 测试：`backend/tests/test_final_delivery.py`（8）、`test_output_contract.py`（6）、`test_e2e_scenario_contract.py`。

### 2. 双表收敛（double-table convergence）
- 前端数据表/明细表双表合一（改造完成，验收通过）。

### 3. 样本 ≠ 全量结论规则 + validator
- 严格区分"抽样结论"与"全量结论"；SKILL.md `_STATE_WORDS_STRONG` vs `_STATE_WORDS_ALL`（修复"全部用电户"误判）。
- `backend/data/skills/scenarios/distribution-overload/scripts/validate_output_contract.py`；`test_output_contract.py`。

### 4. ResizeObserver loop 修复（根因）
- `frontend/src/utils/suppressResizeObserverLoop.ts`：rAF patch 把回调延迟到下一帧（浏览器不再生成 loop 错误）；`initResizeObserverLoopGuard` 入口在 `frontend/src/index.tsx` root.render 前调用；保留事件拦截兜底。
- 测试：`frontend/src/__tests__/suppressResizeObserverLoop.test.ts`（jsdom 需注入 FakeRO）。
- 真实浏览器验证：重载跑查询浮层 overlay=0。

### 5. thinkStreamReducer 提取（P2-2/2-3，已完成）
- `frontend/src/utils/thinkStreamReducer.ts`：thinkReducer/decisionCommittedReducer/finalizeReducer；同 tool_call_id 去重、rejected 步骤标记 `superseded:true`（不删除）、retry_of_step 关联、decision↔tool 关联。
- 测试：`frontend/src/__tests__/thinkStreamReducer.test.ts`（28 项，import 生产代码）。

### 6. 安全链路（对应验收断点 P0，大部分已落地，状态需复核）
- 新增服务：`backend/app/services/decision_gate.py`（DecisionGateMiddleware、`_update_last_scope`、`_get_trusted_scope`）、`scope_checker.py`、`scope_adapters.py`、`secure_query_executor.py`、`run_event_sink.py`。
- `backend/app/api/kg_api.py`：execute_sql 校验。
- 测试（未追踪新增）：`test_decision_gate.py`、`test_secure_query_executor.py`、`test_f1_sql_injection.py`、`test_f4_f5_acceptance.py`、`test_scope_adapters.py`、`test_scope_checker.py`、`test_skill_path_traversal.py`、`test_e2e_scope_retry.py`。
- ⚠️ 注意：git 状态里还有已删除的测试（`test_e2e_context.py`、`test_e2e_intents.py`、`test_plan_execute.py`、`test_skill_router.py` 为 `D` 状态）。

### 7. 配电重过载场景（更早会话，2026-08-08）
- 详见同目录 `SESSION_HANDOFF_20260808.md`（数据模型 + SKILL.md 台区级重构 + IAB 验证 4 案例全过）。
- 关键产物：`backend/data/init/gen_x10_data.py`、`backend/data/skills/scenarios/distribution-overload/SKILL.md`、`verify_skill_sql.py`、`docs/配电重过载本体导入方案.md`。

---

## 三、验收断点修复计划（`.zcode/plans/plan-sess_66819a89-5104-40a6-ae07-f3401bea82d3.md`）

计划全文在 plan 文件。批次与状态（**需新会话复核代码确认**）：

| 项 | 内容 | 状态（依据现有测试/文件推断，需复核） |
|---|---|---|
| P0-1 | 可信范围链路修复（首工具拦截 + 模型声明范围 + user_input 客户名提取） | 部分落地（decision_gate 存在；user_input 提取与 source 优先级待复核） |
| P0-2 | SQL 安全执行器统一接入（kg_api 403、execute_api_sql 改写后重校验、allowed_tables、超时） | 大体落地（secure_query_executor + 多个安全测试存在；allowed_tables/超时细节待复核） |
| P1-1 | 删除 data_intelligence.py 旧技能枚举 + files 注入 | 待复核 |
| P1-2 | HarnessProfile 真实 model 名匹配（非硬编码 "openai:DeepSeek-V4-Flash"） | 待复核 |
| P1-3 | context_schema（TupuAgentContext）接入 | 待复核 |
| P1-4 | response_format 保持手动 + 修重复 sql_result 键/推荐问题 | 待复核（已知 `_response_format=None` 已生效） |
| P2-1 | 清空会话一致性（前端检查 response.cleared） | 待复核 |
| P2-2 | thinkStreamReducer 提取 + 测试 import 生产代码 | ✅ 完成 |
| P2-3 | rejected 步骤标记 superseded 保留 | ✅ 完成 |
| P3-1 | 依赖冲突(CORS/MCP 身份头/会话锁 TTL/ENABLE_AUTH 检查) | 待复核 |

> 建议新会话：先按 plan 逐项对照代码核对完成度，再决定补做项。

---

## 四、未完成 / 待办

1. **【主线】分析当前代码可优化方向**（用户请求，未交付）。建议输出：P0 安全 / P1 架构 / P2 可维护性 / P3 卫生 分级报告，带 `文件:行号` 证据，中文，只读不改码。此前一次尝试因子代理认证故障失败，可改用 Read/Grep 自行排查。
2. **验收断点计划未确认项复核**（见第三节表）。
3. **git 提交**：除非用户明确要求，不提交（见第六节约束）。

---

## 五、未提交改动清单（87 项，2026-08-17）

### 已修改（M）
- 后端核心：`backend/app/api/data_intelligence.py`、`data_source.py`、`doris_config.py`、`kg_api.py`、`llm_admin.py`、`main.py`、`mcp_server.py`、`core/auth.py`、`core/database.py`、`models/base.py`、`services/doris_engine.py`、`duckdb_engine.py`、`llm_client.py`、`sql_executor.py`、`tupu_deepagent.py`
- 数据/剧本：`backend/data/init/README.md`、`doris_catalog_init.sql`、`mysql_init_data.sql`、`backend/data/skills/scenarios/distribution-overload/SKILL.md`、`backend/requirements.txt`
- 测试：`backend/tests/test_e2e_api.py`（修改）；`test_e2e_context.py`、`test_e2e_intents.py`、`test_plan_execute.py`、`test_skill_router.py`（**已删除 D**）
- 配置/文档：`.env.infra.example`、`AGENTS.md`、`DEPLOYMENT_GUIDE.md`、`backend/.env.example`、`docker-compose.infra.yml`

### 未追踪（??）
- 后端服务：`decision_gate.py`、`run_event_sink.py`、`scope_adapters.py`、`scope_checker.py`、`secure_query_executor.py`
- 后端测试：`test_decision_gate`、`test_e2e_scenario_contract`、`test_e2e_scope_retry`、`test_f1_sql_injection`、`test_f4_f5_acceptance`、`test_final_delivery`、`test_output_contract`、`test_scope_adapters`、`test_scope_checker`、`test_secure_query_executor`、`test_skill_path_traversal` + `backend/pytest.ini`
- 数据脚本：`gen_x10_data.py`、`init_catalog_binding.py`、`init_distribution_ontology.py`、`init_es_catalog_binding.py`、`init_es_power_ts.py`、`migrate_telem_to_es.py`、`rebuild_meta_names.py`、`verify_skill_sql.py`
- SKILL 资源：`distribution-overload/{examples,reference,scripts,templates}/`
- 前端：`frontend/src/__tests__/`（finalDelivery/suppressResizeObserverLoop/thinkStreamReducer.test.ts）、`frontend/src/utils/`（finalDelivery/suppressResizeObserverLoop/thinkStreamReducer.ts）、`frontend/src/components/conversation/IntentCard.tsx`
- 文档/计划：`.mcp.json`、`.zcode/plans/plan-sess_059476e9-*.md`、`plan-sess_66819a89-*.md`、`SESSION_HANDOFF_20260808.md`、`docs/配电重过载本体导入方案.md`、后端临时文件 `_q09.txt`/`_sse_err.txt`/`_sse_out.txt`/`_sse_out2.txt`（调试残留，可清理）

---

## 六、站立约束（不可违反）

1. **不自动 git commit/push**——除非用户明确说"提交/同步到git"。
2. **后端固定 28000**（`backend/__start_8000.py` 启动，文件名历史遗留），前端 23000，setupProxy.js 转发；**前端禁止硬编码后端端口**（相对路径 `/api/v1`）。
3. **浏览器测试：Playwright MCP + 系统 Edge**（2026-08-16 起，用户批准的方案 A，项目根 `.mcp.json` 配置 `npx -y @playwright/mcp@latest --browser msedge`）。**这是当前唯一的浏览器测试方式**，已跑通冒烟测试。历史 IAB 约束（control-browser 技能 + `mcp__node_repl__js` + `agent.browsers.get("iab")`，禁外部浏览器）仅用于 08-08 配电重过载会话，**已过时**。
4. **Docker 端口映射不可改**（MySQL 3306、ES 11200、PG 25432、Doris 9030/18030/18040、Neo4j 7474/7687、Qdrant 6333-6334、Authentik 9100/9143、Sandbox 9385——按工作区 AGENTS.md 端口表）。
5. **YAGNI**：标准库能搞定不引依赖；不为想象需求写代码。
6. **DecisionGate 是硬闸门**："不能以牺牲强闸门来换速度"。

---

## 七、环境与基础设施

- 运行中：后端 28000（PID 33144）、前端 23000（PID 16220）。
- 连接串（按 AGENTS.md 目标态）：MySQL `mysql+pymysql://root:<TUPU_MYSQL_PASSWORD>@localhost:3306/tupu`；PG `postgresql://postgres:<TUPU_PG_PASSWORD>@localhost:25432/tupu`；ES `http://elastic:infini_rag_flow@localhost:11200`。
- ⚠️ **历史遗留端口偏差**（08-08 交接记录）：早期 MySQL 实际跑在 33066（ragflow 共享栈 `docker-mysql-1`），AGENTS.md 的 3306 是"目标态"；`init_distribution_ontology.py` 用 33066。ES 同理曾用 11200。新会话若碰 MySQL 元数据先确认实际端口（最近提交 `3bed53a` 已做 ragflow 解耦，可能已切换，需实测）。
- 后端测试基线：**178/184 collected（6 deselected）**，pytest.ini 已存在。

---

## 八、已知问题 / 注意事项

1. **GLM 与结构化输出**：`_response_format = None`（tupu_deepagent.py）是为兼容 GLM 的既有决策，勿改回嵌套 schema。
2. **jsdom 无原生 ResizeObserver**：前端测试需注入 FakeRO（见 suppressResizeObserverLoop.test.ts 先例）。
3. **IAB 测试坑**（08-08 交接）：`getByRole('button',{name:'play-circle'}).click()` 会超时，用 `evaluate` 读 bbox + `cua.click` 坐标点击；`keyboard.press`/`isDisabled`/`inputValue` 在 Codex IAB 不可用；`node_repl` 长等待(55s+)拆批。
4. **调试残留**：`backend/_q09.txt`、`_sse_err.txt`、`_sse_out.txt`、`_sse_out2.txt` 可清理（非交付物）。
5. **本交接文件**与 `SESSION_HANDOFF_20260808.md` 一起构成完整背景；08-08 文档含配电重过载数据模型/SKILL 剧本细节，需要时再读。

---

## 九、下一步建议（新会话）

1. **补做主线分析**：`分析当前代码可优化方向`（只读，产出 P0-P3 分级优化报告）。
2. **复核验收断点计划**：第三节状态表逐项对照代码，补做未完成项（每批跑测试 + curl e2e + IAB 验证）。
3. 需要时：跑后端全量 pytest 确认当前基线（178/184），前端 jest 全量。
4. DeepTutor 仓库的改动是否回退/提交——等用户明确指示，勿自行处理。

---

## 十、本会话补充（2026-08-16/17：浏览器测试基建 + 新发现）

### 1. Playwright MCP 浏览器测试基建（已完成并验证）
- 项目根 `.mcp.json`（未追踪，勿删）：`npx -y @playwright/mcp@latest --browser msedge`（v0.0.79，驱动系统 Edge，零下载）。
- 目的：**适配当前会话模型无图片能力（DeepSeek V4 Flash）**，测试全程用 aria 文本快照 + 文本断言，不依赖视觉。
- 冒烟测试已跑通：打开 `http://127.0.0.1:23000` → 首页渲染（14 主数据实体/11 业务实体）→ 点快捷问题「统计用电客户总数」→ 发送 → 收到完整问答（结论 **101 户**，含关键发现/风险/结果表/推荐）。Console 仅 antd 弃用警告 + favicon 404（无害）。
- 以后用户说「测试 XX 页面/流程」，直接用 Playwright MCP 工具驱动 Edge 做行为级测试；视觉验证需人工看有头浏览器或切换视觉模型。

### 2. 已知问题：模式锁禁止 execute_sql（未排查，待办）
- 冒烟测试中发现：实体 `cms20_elec_cons_cust` `source_mode=sql_integration`，被「模式锁」拦截，提示「禁止 execute_sql，请用 execute_doris_sql」。
- 最终答案仍基于数据生成（101 户），但执行走了降级/推断路径，**执行过程不完整**。
- 排查入口：`backend/app/services/secure_query_executor.py`（模式锁判断）、`doris_engine.py`、`kg_source_*` 表的 `source_mode` 字段、`execute_doris_sql` 链路。

### 3. 模型切换情况（会话期间实测）
- Claude Code 会话层：用户级 `~/.claude/settings.json` 映射档位——**HAIKU/FABLE 档 → deepseek-v4-flash[1M]、OPUS/SONNET 档 → glm-5.3[1M]**（经 ANTHROPIC_BASE_URL 网关接入）。
- 用 `/model` 命令切换档位即切换实际模型（已验证 `/model haiku` → deepseek-v4-flash、`/model sonnet` → GLM-5.3）。
- 应用层：前端默认 LLM 连接为 **4agent**（DeepSeek-V4-Flash）。
