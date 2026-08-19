# DeepAgents 框架能力分析：在用 / 未用 / 最新版差异

> 2026-08-20 · 设计窗口产出（不动代码、不动环境）
> 方法论：**装机实测**（`import deepagents` 定位 site-packages，0.6.12）+ **PyPI 版本实测**（`pip index versions`）+ **0.7.7 wheel 下载解包 diff**（仅临时目录检视，未安装）。所有 API 面均为源码级事实，非文档转述。
> 结论预览：工程对框架用得**深**（17 个 agent 参数用 11 个 + 自研 4 个中间件 + HarnessProfile 高级用法）；装机版里还有 **4 项高价值未用能力**（Rubric 自评 / HITL 审批 / AGENTS.md 记忆 / 悬空调用修复）；0.6.12 -> 0.7.7 对本工程**收益≈0**，暂不升级。

---

## 一、版本事实

| 项 | 值 | 证据 |
|---|---|---|
| 装机版 | **0.6.12** | `python -c "import deepagents..."`；requirements.txt `deepagents==0.6.12`（注释「固定当前验证版本」） |
| PyPI 最新 | **0.7.7** | `pip index versions deepagents`（0.7.0-0.7.7 共 8 个小版本） |
| 语言栈 | langchain 1.3.14 / langgraph 1.2.6 / langchain-mcp-adapters 0.3.1 | `pip list` |

---

## 二、框架能力全景（0.6.12 装机源码枚举）

### 2.1 `create_deep_agent` 17 参数

| 参数 | 用途 | 本工程 |
|---|---|---|
| model / tools / system_prompt | 基础三件套 | ✅（model 按前端连接、tools=16 个 MCP 工具） |
| middleware | 中间件栈（LangChain AgentMiddleware 协议） | ✅（4 个自研 + 框架默认件） |
| skills | 技能目录（Anthropic Agent Skills 渐进披露） | ✅ `["/skills/"]` |
| permissions | FilesystemPermission 规则表 | ✅（3 条规则） |
| backend | 文件系统后端 | ✅ CompositeBackend |
| response_format | 结构化最终答案 | ⚠️ 显式传 None（F5：GLM/DeepSeek 与嵌套 schema 不兼容） |
| state_schema / context_schema | 状态与运行时上下文 | ✅ TupuAgentState / TupuAgentContext（F4：context 不进 checkpoint） |
| checkpointer | 持久化（跨请求记忆） | ✅ AsyncSqliteSaver + 按 connection_id 缓存 Agent |
| **subagents** | 子代理（task 工具） | ❌（且被契约 ABSOLUTE_FORBIDDEN_TOOLS 禁用） |
| **memory** | AGENTS.md 记忆源 | ❌ |
| **interrupt_on** | 人审中断（HITL）：工具名 -> 审批配置 | ❌ |
| **store** | 跨线程持久存储（LangGraph BaseStore） | ❌ |
| **cache** | LLM 响应缓存 | ❌ |
| name / debug | 命名（追踪）/ 调试 | ❌ |

### 2.2 Backends 家族（9 导出）

| Backend | 用途 | 本工程 |
|---|---|---|
| StateBackend | 内存态（ephemeral） | ✅ default |
| FilesystemBackend | 真实文件系统（root_dir + virtual_mode 防穿越） | ✅ /skills/ 路由 |
| CompositeBackend | 路由组合（default + routes 前缀表） | ✅ |
| ContextHubBackend | 上下文枢纽（跨 agent 共享上下文） | ❌ |
| StoreBackend | LangGraph Store 存储（NamespaceFactory 分命名空间） | ❌ |
| LocalShellBackend | 本地 shell 执行后端 | ❌（安全红线） |
| LangSmithSandbox | LangSmith 沙箱后端 | ❌ |

### 2.3 Middleware 家族（9 公开 + 6 私有模块）

| 模块 | 职责（源码 docstring 摘要） | 本工程 |
|---|---|---|
| filesystem | 文件系统工具 + FilesystemPermission | ✅（经 permissions 参数） |
| skills | Agent Skills 渐进披露，**分层源**（base->user->project->team，后者覆盖） | ✅（经 skills 参数） |
| summarization | 会话摘要压缩 | ✅（monkey-patch `compute_summarization_defaults`：3 万 token/保留 10 条，try/finally 包裹） |
| **rubric** | **自评迭代**：agent 将结束时分出 grader 子代理按 rubric 评分，`needs_revision` 则注入反馈继续，至 satisfied/failed/max_iterations | ❌ |
| **memory** | **AGENTS.md 规范**：常驻记忆（与 skills 按需加载相对），多源合并注入 system prompt | ❌ |
| **subagents** | task 工具派生子代理（含 HITL/InterruptOnConfig 集成） | ❌（契约红线禁 task） |
| **async_subagents** | 异步子代理（AsyncSubAgent/AsyncSubAgentMiddleware） | ❌ |
| **patch_tool_calls** | **悬空工具调用修复**：消息历史里 AIMessage 的 tool_calls 缺对应 ToolMessage 时（中断/幻觉调用）自动修补 | ❌ |
| permissions | 权限中间件 | （经 permissions 参数间接） |
| _fs_interrupt / _message_eviction / _overflow_clip / _tool_exclusion / _state / _utils | 内部件（HITL 文件审批/消息逐出/溢出裁剪/工具排除等） | _tool_exclusion 已被 HarnessProfile 公开替代 |

### 2.4 Profiles

- **HarnessProfile + register_harness_profile**：按 `provider:model` 注册模型行为档案（excluded_tools 等）--本工程**高级用法在用**（排除 grep/glob/write_file/edit_file/execute 五工具，含大小写变体注册）。
- **ProviderProfile + register_provider_profile**（beta）：模型构造 kwargs 声明（init_chat_model 定制、预初始化副作用）--未用。内置 openai（默认 Responses API）/openrouter 档案。**注意：管模型构造，不管 summarization 阈值，不能替代现有 monkey-patch。**

---

## 三、当前工程引用清单（12 项，全部带位置）

| # | 用法 | 位置 | 评价 |
|---|---|---|---|
| 1 | create_deep_agent 11 参数装配 | tupu_deepagent.py:763-775 | 主装配点 |
| 2 | CompositeBackend：/skills/ -> 只读 FilesystemBackend(virtual_mode)，default StateBackend | :671-683 | 路由组合 + 防目录穿越，教科书用法 |
| 3 | FilesystemPermission 三条规则（allow 读 /skills/**；deny 读 /\*\*；deny 写 /\*\*） | :688-692 | 白名单式兜底封堵 |
| 4 | HarnessProfile excluded_tools ×5 + 大小写双注册 | :696-721 | 消除私有 _ToolExclusionMiddleware 依赖（评审点 5 落地） |
| 5 | skills=["/skills/"]：原生 SkillsMiddleware 自动发现 SKILL.md frontmatter，Agent 按需 read_file | :773 | 替代了旧的手工枚举注入 |
| 6 | 自研中间件栈：SkillPolicyMiddleware(最外层契约硬校验) -> SkillEntityResolverMiddleware(⟦中文名⟧->物理表) -> DataSummaryMiddleware(明细截断 10 行摘要) -> DecisionGateMiddleware(判断闸门, feature flag) | :726-740 | 框架扩展点的深度使用，全仓最大亮点 |
| 7 | SummarizationMiddleware 保守阈值 monkey-patch（3 万 token/10 条，try/finally） | :747-755,776-778 | 有效但属技术债（注释已列「后续验证公开替换」） |
| 8 | TupuAgentState（DeepAgentState 扩展 last_skill 等） | state_schema | 定制状态 |
| 9 | TupuAgentContext 运行时上下文（不进 checkpoint，契约经此注入） | context_schema | F4 设计 |
| 10 | AsyncSqliteSaver + 按 connection_id 的 Agent 缓存 + 初始化锁 | :796-830 | 跨请求记忆 + 前端选模型生效 |
| 11 | MCP 工具加载（MultiServerMCPClient -> 16 单一职责工具） | :669 + mcp_server.py | 工具层与 agent 解耦 |
| 12 | response_format=None 显式禁用（GLM/DeepSeek 嵌套 schema 不兼容，降级为外层 A-E 确定性交付） | :757-760 | 有据的取舍 |

---

## 四、已装未用能力逐项分析

### 4.1 高价值，建议引入（4 项）

**① RubricMiddleware -- 自评迭代闸门（价值最高）**

- 机制：agent 每次要结束时，grader 子代理按调用方传入的 rubric 评审 transcript；`needs_revision` 则把反馈作为 HumanMessage 注入继续迭代；satisfied/failed/max_iterations 终止。**无 rubric 时零开销直通**（源码明确「safe to include unconditionally」）。
- 与本工程的融合点（天然契合）：
  - rubric 挂 **QueryContract**：generic 自由问答模式设 rubric（「结论必须与 SQL 结果一致；口径/时间范围必须披露；无数据不得臆断；引用实际表名」），scenario 模板模式不设（结构已由模板保证，省 token/延迟）；
  - grader 用轻量模型（连接池里选 flash 级）；`max_iterations=1` 防循环（P0 事故教训）；
  - 终止状态 `_rubric_status` / `rubric_evaluation_end` 流事件 -> SSE -> 前端**置信度卡片**（正是《图谱问数智能体增强设计》防线④的实现载体，框架原生件替代自研）。
- 成本：generic 每答一次多一轮 grader 调用（轻量模型，秒级）。

**② interrupt_on -- HITL 人审中断**

- 机制：`interrupt_on={工具名: True | InterruptOnConfig}`，命中工具时暂停等待人工批准/拒绝（langchain HumanInTheLoopMiddleware 底座），前端 resume 后继续。
- 融合点：把 SkillPolicy 的**硬拒绝**升级为可选**软审批**--典型场景：受控降级（TABLE_MISSING 时「表 X 不存在，是否降级查 Y？」）、引擎切换、首次访问新实体表。当前是自动降级一次或直接拒绝，企业场景常要「人点头」。
- 代价：前端要加中断事件渲染 + 批准/拒绝按钮 + resume 调用（data_intelligence 流式管道改造）；会话锁/超时语义要重新核。**建议作为 v2 项**，先把 Rubric 做完。

**③ MemoryMiddleware -- AGENTS.md 常驻记忆**

- 机制：加载 AGENTS.md 规范文件（https://agents.md/）常驻注入 system prompt，多源分层合并；与 skills（按需）互补。
- 融合点：把 `_build_dynamic_system_prompt` 里的**静态平台纪律**（工具使用纪律/表名规范/回答格式）迁到 `data/AGENTS.md`，运营改文件即可调全局纪律，**不改代码**；动态部分（契约/技能提示）保持现状。
- 注意与契约 SystemMessage 的职责划分：AGENTS.md=全局长期纪律，契约=本次运行约束，互补不重叠。

**④ PatchToolCallsMiddleware -- 悬空工具调用修复（健壮性）**

- 机制：消息历史里 AIMessage 的 tool_calls 缺对应 ToolMessage（用户取消/进程中断/模型幻觉调用）时自动修补，避免 LangGraph 恢复会话时报错。
- 融合点：本工程 checkpointer 跨请求长会话 + 用户随时关页面取消流，**命中该故障模式的概率不低**。装配成本≈一行（append 到 middleware_list）。建议与任何一项一起顺手加。

### 4.2 低价值 / 暂缓（4 项）

| 能力 | 判定理由 |
|---|---|
| store + StoreBackend | 跨线程共享存储；验证示例库等持久学习已规划走 MySQL+Qdrant（更贴合现有治理），Store 无增量收益 |
| cache | LLM 响应缓存；问数查询高变异性，命中率会很低 |
| name/debug | 追踪便利性，可在下次触碰装配代码时顺手加，不单独立项 |
| ContextHubBackend | 跨 agent 共享上下文；单 agent 架构无场景 |

### 4.3 红线：继续禁用（与受控平台的关系）

| 能力 | 禁用理由 |
|---|---|
| subagents / task / AsyncSubAgent | **契约红线**：ABSOLUTE_FORBIDDEN_TOOLS 明令禁 task（子代理逃逸契约管控、白名单失守）。受控平台的设计前提就是单代理确定性流。除非未来做「契约继承的受控子代理」（子代理契约为主契约子集），否则不动 |
| LocalShellBackend / LangSmithSandbox | shell 执行=安全红线；业务问数零需求 |
| response_format | 已验证 GLM/DeepSeek 不兼容嵌套结构化 schema（F5 记录在案），维持外层 A-E 确定性交付 |

---

## 五、0.6.12 -> 0.7.7 差异（wheel 解包实测）

| 维度 | 差异 |
|---|---|
| `create_deep_agent` 签名 | **完全一致**（17 参数同名同型） |
| 顶层 `__all__` | +1：`FsToolName`（文件系统工具名枚举，便利性） |
| middleware 目录 | +2：**`_prompt_caching`**（Anthropic/Bedrock 提示词缓存中间件，仅这两家 provider 生效--本工程 GLM/DeepSeek 走 OpenAI 兼容协议，**无收益**）、**`_video`**（PyAV 可选 extra，read_file 视频抽帧为图像块--问数场景无关） |
| backends 导出 | 完全一致 |
| 升级建议 | **暂不升级**。0.7 系列对本工程增量≈0；固定验证版的纪律（注释「固定当前验证版本」+ pytest 359 基线）应保持。触发升级的条件：某新能力命中需求（如 OpenAI 兼容家的 prompt caching 落地、或 bugfix 命中现有故障），届时按「升级->全量 pytest->冒烟脚本->发布清单」流程走 |

---

## 六、引入规划（四批，与既有体系融合）

| 批 | 内容 | 量级 | 依赖/顺序 |
|---|---|---|---|
| **DA-1 健壮性** | PatchToolCallsMiddleware 装配（+顺带 name） | 0.5 天 | 无依赖，可与任何批合并 |
| **DA-2 自评闸门** | RubricMiddleware：QueryContract 增 rubric 字段；generic 设默认 rubric、scenario 不设；grader 走轻量连接；max_iterations=1；`rubric_evaluation_end` -> SSE -> 前端置信度标注 | ~2 天 | 是《图谱问数增强设计》防线④的框架原生实现，**优先于自研证据链评分** |
| **DA-3 常驻记忆** | MemoryMiddleware + `data/AGENTS.md`：静态纪律迁移、动态提示保持注入 | ~1 天 | 与 DA-2 无耦合 |
| **DA-4 HITL 审批（v2）** | interrupt_on：受控降级/引擎切换转人审；前端中断渲染 + resume；会话锁语义复核 | ~3 天 | 依赖 DA-2 完成后的稳定期；前端改造量最大，单独立项 |

**与既有红线的关系**：全部四批不动 subagents/shell/response_format 三条红线；Rubric 的 grader 是框架内部子代理（非 task 工具暴露给主 agent），不违反契约禁令（装配前以 0.6.12 源码核实其实现路径）。

---

## 七、风险与注意事项

1. **Rubric 成本**：generic 每答多一轮 grader 调用；用轻量模型 + 仅 generic 启用 + max_iterations=1 控制在秒级/分级；金标评估集（G6）可度量其净收益后再决定是否扩到 scenario。
2. **HITL 改造面**：interrupt/resume 横跨 SSE 协议、前端交互、会话锁三处，是四批中唯一动前端的；务必单独排期。
3. **AGENTS.md 治理**：常驻记忆=每次请求都注入，内容膨胀会吃 token；纪律：AGENTS.md 限一屏（~60 行），超了就往 skills 迁。
4. **summarization monkey-patch 技术债**（既有，非本批新增）：0.6.12 已提供公开 SummarizationMiddleware，可直接装配实例替代 patch `compute_summarization_defaults`；注释里的 TODO 建议在 DA-1 顺手做掉（半天，消除 finally 恢复的脆弱性）。
5. **ProviderProfile 是 beta**：若未来用于模型构造定制，注意版本间 minor 变更风险；目前无需求不碰。

---

## 附：本次验证方法（可复现）

```powershell
python -c "import deepagents, os; print(deepagents.__file__)"        # 装机定位
pip index versions deepagents                                        # PyPI 版本
pip download deepagents==0.7.7 --no-deps -d $env:TEMP\da077          # 仅下载
python -c "import zipfile; zipfile.ZipFile(...).extractall(...)"     # 解包 diff
```

（0.7.7 wheel 解包于 `%TEMP%\da077_inspect`，纯检视未安装，工程环境仍是 0.6.12。）
