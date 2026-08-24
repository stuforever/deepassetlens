# DeepAgents 能力全景盘点：黑能力全清单 × 使用状态 × 未用归因

> 2026-08-24 · 设计窗口产出（0.7.7 装机包逐模块解剖 + create_deep_agent 完整签名核对）

---

## 一、盘点范围与方法

以装机包为准解剖出 **6 大能力族**：

| 族 | 内容 |
|---|---|
| 图入口 | `create_deep_agent`（**18 个参数**） |
| 后端 backends×9 | filesystem / composite / state / **store** / **langsmith(ContextHub)** / **local_shell** / **sandbox** / protocol / utils |
| 中间件 middleware×15 | skills / filesystem / memory / summarization(+tool) / rubric / patch_tool_calls / permissions / **subagents** / **async_subagents** / **_prompt_caching** / **_message_eviction** / **_overflow_clip** / **_fs_interrupt** / **_tool_exclusion** / _video |
| Profiles | harness 内置预设（anthropic haiku/opus/sonnet、nvidia nemotron、openai codex）+ 自定义机制 |
| LangGraph 底座 | checkpointer / interrupt/Command / recursion_limit / Store / astream_events |

我方 `create_deep_agent` 实际传参：**model / tools / system_prompt / middleware / state_schema / checkpointer / backend / skills —— 18 个用了 8 个**。

## 二、四分类总表

### A. 深度使用（核心依赖，抽掉就瘫）
SkillsMiddleware（技能渐进披露）、FilesystemMiddleware（read_file/ls/write_todos）、MemoryMiddleware（AGENTS.md 常驻纪律）、SummarizationMiddleware 族（30k 摘要）、RubricMiddleware（自评）、FilesystemBackend+CompositeBackend（只读技能挂载）、AsyncSqliteSaver（跨题记忆）、state_schema（契约/rubric/last_skill 注入通道）、astream_events v2（SSE 数据源）、AgentMiddleware 协议（SkillPolicy/DataSummary/EntityResolver 三个自研闸门的挂载方式）。

### B. 用但定制（子类化/桥接适配业务）
`_TupuSummarizationMiddleware`（改阈值+excluded_middleware 精确丢弃框架默认件）、`_TupuRubricMiddleware`（批10② 异步化改造中）、自定义 HarnessProfile（excluded_tools 排除写工具）、contextvar 桥（评估事件→SSE）。

### C. 有意不用（每条都有明确理由）

| 能力 | 为什么不用 | 分类 |
|---|---|---|
| `subagents` / `async_subagents`（task 工具委派子代理） | **安全红线**：问数不需要委派；子代理是逃逸面且绕过契约闸门确定性 | 红线排除 |
| `backends/local_shell`（本地 shell 执行后端） | **安全红线**：问数零代码执行需求，shell=任意命令面 | 红线排除 |
| `backends/sandbox`（沙箱执行后端） | 同上红线（含 quickjs extra 的 JS 执行） | 红线排除 |
| `response_format`（结构化输出参数） | 会禁用工具调用能力，与 ReAct 根本冲突 | 红线排除 |
| `_prompt_caching` 中间件 + `cache` 参数（显式缓存断点） | **Anthropic/Bedrock 专属**，OpenAI 兼容协议不适用（我们的缓存走服务端隐式前缀缓存，批5） | 协议不适配 |
| `backends/langsmith`（ContextHub 云端存储） | 外接 SaaS 过重；本地治理三本账替代 | 生态不适配 |
| `store` 参数（LangGraph Store 长期记忆 KV） | 无向量索引能力，检索需求被 Qdrant 示例库替代 | 替代方案更优 |
| `interrupt_on` 参数 + `_fs_interrupt`（静态工具级人审） | 表达不了**条件动态触发**（TABLE_MISSING 才审）；已用 langgraph interrupt 原语自研条件 HITL。登记过「可向框架惯例靠拢」的机会项 | 替代方案更优（留迁移空间） |
| `_video` 视频多模态 | 与问数域无关 | 不相干 |
| profiles 内置 harness 预设 | 为海外模型（anthropic/nvidia/codex）调的装配预设；国产模型需自定义——我们已有自己的 profile | 不适配（已有替代） |
| `debug` / `name` 参数 | 装饰性 | 无需求 |

### D. 未用机会点（真正的账，只有三条）

| # | 能力 | 现状 | 建议 |
|---|---|---|---|
| D1 | `PatchToolCallsMiddleware`（悬空 tool_calls 修复） | ⚠️ **升级到 0.7.7 后复核：仍未装配**（测试三用例在、装配行不在）。模型流式中断可能留下悬空调用导致下一轮解析错乱 | 维持登记：一行装配+回归，随最近的功能批顺手带上 |
| D2 | `_message_eviction` / `_overflow_clip`（大消息驱逐/溢出裁剪 helpers） | 未单独启用。我们自研 DataSummary 只管工具结果截断；**单条超大消息**（如异常巨大的 ToolMessage）的极端场景框架件可能更稳 | 评估项：确认其是否已被 summarization 内部联动；若独立，考虑与 DataSummary 截断策略对齐后启用，作为上下文爆炸的第二道保险 |
| D3 | HITL 向 `interrupt_on` 惯例靠拢 | 自研协议面可用但非标准 | 老登记项：减少自研面，收益中等，不急 |

## 三、「为什么没用」的三类归因

1. **主动排除（5 项）**：subagents/local_shell/sandbox/response_format/quickjs——这些能力用在问数链路上是**负资产**（攻击面），不用是对的；
2. **生态不适配（4 项）**：prompt_caching/cache/langsmith/store/profiles 预设——为 Anthropic 系或 SaaS 生态设计，我们是 OpenAI 兼容+本地部署；
3. **替代方案更优（3 项）**：Store→Qdrant 示例库、interrupt_on→条件 HITL、message_eviction→DataSummary。

## 四、结论

> 18 个参数用 8 个、24 个模块用约 10 个——**未使用的部分不是损失，恰恰是边界清晰的表现**：框架的通用清单里，问数域真正需要的恰好是被深度使用的那组；没用的大多是「用了反而危险」或「别家生态专属」。真正的账只有三条（D1 补装配、D2 评估裁剪联动、D3 HITL 原生化），均已登记，无一紧急。
>
> 另注：0.6.12→0.7.7 的升级没有改变这张表的任何一行——新增三件（FsToolName/_prompt_caching/_video）全部落在「有意不用」区，印证了当时「升级零功能收益」的评估。
