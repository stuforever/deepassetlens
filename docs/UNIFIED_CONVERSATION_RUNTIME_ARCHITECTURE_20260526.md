﻿# 统一会话、双引擎与技能工作流架构设计文档

## 1. 文档定位

这份文档不是阶段性变更记录，也不是“这次又补了什么”的开发日志。

本文档的目标只有一个：用一套统一视角，说明当前 `tupu` 项目的整体架构选择。

核心要回答的问题是：

- 为什么我们现在要以工作流模式作为主路线
- 技能管理、工作流管理、统一会话之间是什么关系
- 为什么还要保留自由调度能力，但不把它作为主执行模式
- `tupu` 与 OpenClaw、Hermes 的相同点和差异点到底在哪里
- 后续应该如何在不破坏工业级高准确场景的前提下继续演进

本文档描述的是当前仓库基础上的整体设计结论，并以当前代码实现为主，必要时给出明确的目标架构表述。

## 2. 总体结论

### 2.1 架构选择

`tupu` 现在明确采用的是“双引擎架构”，但主次分明：

1. 主引擎：`Workflow Engine`
2. 备选引擎：`Agent Engine`

其中：

- `Workflow Engine` 用于承载工业级、高准确、强约束、强审计的核心业务链路
- `Agent Engine` 作为通用能力保留，用于承载开放式探索、自由调度、工具调用型任务

换句话说，当前项目不是“只做自由 Agent”，也不是“只做静态流程编排”，而是：

- 在统一会话与统一运行时之上
- 开放两种执行引擎
- 由场景和目标能力决定使用哪一种

### 2.2 当前主路线

当前真正的主路线是：

- 用户页统一进入 `Conversation + Run + Event Stream`
- 后端统一运行时根据场景解析执行目标
- 面向业务主链优先走 `Workflow Engine`
- 面向通用自由调度的能力保留 `Agent Engine`

这意味着：

- 技能管理不是为了“页面直接调技能”
- 工作流管理不是为了“替代统一会话”
- OpenClaw / Hermes 的自由调度能力也不是要直接替换现有工作流主链

更准确的说法是：

- 技能是能力原子
- 工作流是受控编排方式
- Agent 是另一种编排方式
- 统一运行时负责承载两者

## 3. 架构原则

当前项目遵循以下几条核心原则：

### 3.1 统一入口

用户型页面不直接调用业务专用执行接口，也不直接调用工作流管理接口。

统一入口始终是：

- `Conversation`
- `Run`
- `Event Stream`

### 3.2 双引擎共存，但工作流优先

对于问实体、问数、联接、溯源这类场景，优先使用工作流引擎。

原因很明确：

- 可控
- 可解释
- 可审计
- 可单步调试
- 可结构化输出
- 容易落地企业规则和元数据约束

### 3.3 自由调度不取消，但不篡位

OpenClaw、Hermes 代表的是另一类能力范式：统一 Agent Core + 通用工具调度。

这类能力有价值，但更适合：

- 开放式探索
- 通用工具型任务
- 非强约束知识工作
- 辅助性分析和运维型动作

所以在 `tupu` 中，它应作为通用能力存在，而不是直接替换业务主链。

### 3.4 技能是一等能力，但不等于直接自由调用

技能必须被管理、可配置、可测试、可复用，但技能并不意味着一定要交给 LLM 自由选择。

技能的消费方式可以有两种：

1. 被工作流节点引用
2. 被 Agent Engine 动态调度

这正是双引擎共享技能层的意义。

## 4. 整体架构图

```text
前端页面层
├─ QueryEntity.tsx
├─ LLMChatPlayground.tsx
├─ WorkflowManager.tsx
└─ 未来其他场景页
        │
        ▼
前端统一会话层
├─ sceneConfigs.tsx
├─ useConversationRun.ts
├─ ConversationPage.tsx
├─ ConversationMessageList.tsx
└─ CardRenderer.tsx
        │
        ▼
统一运行接口层
├─ POST /api/v1/conversations
├─ POST /api/v1/runs
├─ GET  /api/v1/runs/{id}
├─ GET  /api/v1/runs/{id}/events
└─ GET  /api/v1/runs/{id}/events/stream
        │
        ▼
统一运行时
└─ agent_run_runtime.py
        │
        ├─ Workflow Engine
        │   ├─ DAGWorkflow
        │   ├─ SchedulerCore
        │   ├─ DAGExecution / DAGStepExecution
        │   └─ 技能节点编排执行
        │
        └─ Agent Engine
            ├─ 通用模型对话
            ├─ 通用工具/技能调度
            └─ 未来的开放式 Agent Loop
        │
        ▼
统一能力层
├─ 技能
├─ 工作流
├─ 模型连接
├─ 上下文装配
└─ 事件与卡片协议
        │
        ▼
持久化
├─ kg_conversations
├─ kg_conversation_messages
├─ kg_agent_runs
├─ kg_run_events
├─ kg_dag_workflows
├─ kg_dag_executions
└─ kg_dag_step_executions
```

## 5. 统一对象模型

为了避免“技能管理一套说法、工作流管理一套说法、会话系统一套说法”，这里先统一对象模型。

### 5.1 Conversation

`Conversation` 是统一会话容器。

作用：

- 承载某个场景下的多轮上下文
- 持久化消息历史
- 持久化场景状态
- 为工作流引擎和 Agent 引擎提供共同会话基座

当前表：

- `kg_conversations`
- `kg_conversation_messages`

### 5.2 Run

`Run` 是一次具体执行。

作用：

- 表达一次用户提交触发的运行
- 记录输入、输出、状态和事件
- 作为统一回放和事件流基准

当前表：

- `kg_agent_runs`
- `kg_run_events`

### 5.3 Skill

`Skill` 是能力原子。

当前理解应统一为：

- 可被工作流节点引用
- 可被统一管理
- 应具备明确输入输出和调试样例
- 不绑定某一个页面

### 5.4 Workflow

`Workflow` 是受控编排单元。

当前定位是：

- 以 DAG 形式组织多个技能
- 有独立定义、独立执行、独立持久化
- 面向高准确场景作为首选执行方式

### 5.5 Engine

`Engine` 是编排策略，而不是页面类型。

当前应当有两种：

1. `workflow_engine`
2. `agent_engine`

它们共享：

- 会话容器
- Run
- 事件流
- 卡片协议
- 上下文装配

## 6. 双引擎设计

### 6.1 Workflow Engine

这是当前主引擎。

其特点是：

- 流程预定义
- 步骤明确
- 输入输出明确
- 可逐步回放
- 可单步调试
- 可加断点
- 可覆盖步骤输入
- 可从任意步骤重跑

适合场景：

- 问实体
- 问数
- 联接
- 溯源
- 其他高准确、可解释要求高的业务链路

当前已落地能力：

- 独立工作流定义
- 工作流可视化管理
- DAG 执行
- 执行历史
- 步骤回放
- 单步调试
- 断点
- 当前待执行步骤输入覆盖
- 从指定步骤重新开始

### 6.2 Agent Engine

这是当前保留的通用能力引擎。

其定位不是替换工作流，而是承载更开放的调度模式。

适合场景：

- 模型对话
- 通用工具型任务
- 开放式分析
- 未来的通用代理能力

从架构上说，它应该具备：

- 统一上下文装配
- 可选工具/技能集
- 模型主导的能力调度
- 多轮持续推理能力

但在当前项目中，它仍属于备选路线，而不是业务主链。

### 6.3 双引擎如何共存

当前最重要的设计结论是：

- 同一个页面不应该直接关心自己用的是哪种底层执行器
- 页面只发起统一 Run
- 运行时根据场景配置、目标能力和路由规则决定进入哪种引擎

也就是说，页面层只有一套入口，底层是双引擎。

## 7. 当前已经实现的统一会话体系

### 7.1 前端统一会话层

当前前端已经形成统一会话壳：

- `sceneConfigs.tsx`
- `useConversationRun.ts`
- `ConversationPage.tsx`
- `ConversationMessageList.tsx`
- `CardRenderer.tsx`

作用分别是：

- `sceneConfigs.tsx`：定义场景元信息和运行策略
- `useConversationRun.ts`：统一创建会话、发起 Run、消费 SSE
- `ConversationPage.tsx`：统一会话页面容器
- `ConversationMessageList.tsx`：统一消息列表与流式状态展示
- `CardRenderer.tsx`：统一卡片协议渲染

### 7.2 已接入统一会话的页面

当前已接入的页面有：

- `QueryEntity.tsx`
- `LLMChatPlayground.tsx`

其中：

- `QueryEntity` 当前主链走 `Workflow Engine`
- `LLMChatPlayground` 当前主链走 `Agent Engine`

### 7.3 当前统一接口

当前统一会话接口包括：

- `POST /api/v1/conversations`
- `GET /api/v1/conversations/{conversation_id}`
- `GET /api/v1/conversations/{conversation_id}/messages`
- `POST /api/v1/runs`
- `GET /api/v1/runs/{run_id}`
- `GET /api/v1/runs/by-code/{run_code}`
- `GET /api/v1/runs/{run_id}/events`
- `GET /api/v1/runs/{run_id}/events/stream`

这套接口的意义不是“只是多包装了一层”，而是：

- 把页面与底层执行引擎解耦
- 让工作流执行和自由调度执行共享同一个交付面

## 8. 当前技能管理设计

### 8.1 当前技能管理的真实状态

当前 `tupu` 的技能管理已经走出“页面写死逻辑”的阶段，但还没有完全达到“运行时原生 capability registry”的成熟度。

现状可以概括为：

- 技能有数据库实体、版本和执行记录
- 技能可以作为工作流节点被编排
- 技能可以在管理端被展示和维护
- 技能执行结果可以被回放和调试
- 但技能定义、bootstrap、系统级能力接入仍和后端代码有一定耦合

所以当前最准确的判断是：

- 技能已经可管理
- 但还没有完全能力注册中心化

### 8.2 技能在双引擎中的角色

技能层不应该只服务某一个引擎。

更合理的统一定位是：

- 对 `Workflow Engine` 来说，技能是节点能力
- 对 `Agent Engine` 来说，技能是可选调度能力

因此技能管理的目标不是“做成某个页面的配置面”，而是做成全局能力面。

### 8.3 技能管理的目标形态

后续技能管理建议统一向以下模型演进：

- `capability_code`
- `capability_type`
- `input_schema`
- `output_schema`
- `handler`
- `policy`
- `examples`
- `debug_contract`

这样技能、工具、系统动作可以逐步被统一到一个能力注册层中。

## 9. 当前工作流管理设计

### 9.1 工作流管理的定位

工作流管理页不是用户运行入口，而是管理端能力。

其职责是：

- 管理工作流定义
- 编辑 DAG
- 配置节点输入输出映射
- 做工作流级调试
- 查看执行历史和回放

当前页面：

- `WorkflowManager.tsx`
- `WorkflowDetailPage.tsx`

### 9.2 工作流管理接口

当前工作流管理接口包括：

- `/api/v1/workflows`
- `/api/v1/workflows/{id}`
- `/api/v1/workflows/by-code/{workflow_code}`
- `/api/v1/workflows/{id}/execute`
- `/api/v1/workflows/{id}/debug/start`
- `/api/v1/workflows/{id}/executions`
- `/api/v1/workflows/executions/{id}`
- `/api/v1/workflows/executions/by-code/{execution_code}`
- `/api/v1/workflows/executions/{execution_code}/next`
- `/api/v1/workflows/executions/{execution_code}/run-to-end`
- `/api/v1/workflows/executions/{execution_code}/stop`
- `/api/v1/workflows/executions/{execution_code}/breakpoints`
- `/api/v1/workflows/executions/{execution_code}/override-input`
- `/api/v1/workflows/executions/{execution_code}/restart-from-step`

### 9.3 为什么工作流模式是主路线

在 `tupu` 这个项目里，工作流模式不是因为“不会做 Agent”才选，而是因为业务要求决定了它必须成为主路线。

核心原因有：

1. 高准确
2. 强元数据约束
3. 强可解释
4. 强审计
5. 强调试
6. 强结构化输出

这些要求与 OpenClaw / Hermes 那类通用代理系统的价值并不冲突，但主次应当不同。

## 10. 当前场景落地情况

### 10.1 QueryEntity

当前 `QueryEntity` 已经完全切到统一会话模式。

执行链路是：

```text
QueryEntity.tsx
  -> useConversationRun.submitMessage()
  -> POST /conversations
  -> POST /runs
  -> Run Runtime
  -> Workflow Engine
  -> query_entity_main_workflow
  -> 4个问实体技能
  -> DAGExecution / DAGStepExecution
  -> RunEvent
  -> SSE
  -> query_entity_result / clarification 卡片
```

当前问实体工作流包含 4 步：

1. `query_entity_step1_metadata_overview`
2. `query_entity_step3_llm_prompt`
3. `query_entity_step4_llm_inference`
4. `query_entity_step5_finalize`

当前多轮澄清也是在工作流模式内实现的，原则是：

- 由 LLM 在正式工作流中决定是否需要澄清
- Runtime 负责挂起会话状态和续跑
- 不在本地做候选检索式硬编码澄清

### 10.2 LLMChat

当前 `LLMChatPlayground` 也已经切到统一会话模式。

执行链路是：

```text
LLMChatPlayground.tsx
  -> useConversationRun.submitMessage()
  -> POST /conversations
  -> POST /runs
  -> Run Runtime
  -> Agent Engine
  -> LLMConnectionConfig / model call
  -> rich_text 卡片
  -> SSE
```

它代表的是当前项目中 `Agent Engine` 的一个最轻量入口。

## 11. 当前统一运行时设计

### 11.1 运行时职责

统一运行时的职责不是“代替业务逻辑”，而是负责把不同执行引擎收口到同一交付协议。

当前职责包括：

- 会话创建与复用
- Run 创建与状态管理
- 场景路由与目标解析
- 上下文装配
- 事件写入与 SSE 推送
- 统一卡片与助手消息封装
- 统一回放与持久化

### 11.2 当前事件协议

当前已经使用的事件包括：

- `run.started`
- `context.prepared`
- `tool.delta`
- `assistant.delta`
- `block.started`
- `block.delta`
- `block.completed`
- `step.completed`
- `message.card`
- `run.completed`
- `run.failed`
- `stream.end`

这说明当前系统已经不是“只有最终结果”的同步接口模式，而是统一事件流模式。

### 11.3 当前上下文与记忆

当前统一运行时已经把以下内容纳入标准上下文：

- `runtime_context`
- `session_memory`
- `workspace`
- `session`
- `request`
- `capabilities`

这里的重点不是单独再讲“某次增强”，而是明确：

- 这些已经是当前运行时的组成部分
- 不是外挂章节
- 也不是后续可有可无的补丁

## 12. 页面入口与管理入口的边界

当前项目明确区分两类入口。

### 12.1 用户型入口

适用页面：

- `QueryEntity`
- `LLMChatPlayground`

调用方式：

- `Conversation + Run + Event Stream + Card`

### 12.2 管理型入口

适用页面：

- `WorkflowManager`
- `WorkflowDetailPage`
- 各类建模与管理页

调用方式：

- 资源管理接口
- 工作流定义接口
- 工作流调试接口

### 12.3 为什么必须分层

这条边界非常关键。

因为：

- 用户页关注的是“完成任务”
- 管理页关注的是“定义能力、编排能力、调试能力”

如果把两者混在一起，就会重新回到“页面自己调底层”的老路。

## 13. 当前数据持久化模型

### 13.1 会话与消息

表：

- `kg_conversations`
- `kg_conversation_messages`

作用：

- 统一会话容器
- 会话消息持久化
- 多轮上下文基础

### 13.2 Run 与事件

表：

- `kg_agent_runs`
- `kg_run_events`

作用：

- 统一执行记录
- 统一事件流回放
- 统一状态追踪

### 13.3 工作流执行

表：

- `kg_dag_workflows`
- `kg_dag_executions`
- `kg_dag_step_executions`

作用：

- 工作流定义持久化
- 执行记录持久化
- 步骤执行持久化

## 14. 与 OpenClaw、Hermes 的关系

这一节只讲一次，不重复展开。

### 14.1 我们借鉴了什么

`tupu` 当前吸收了 OpenClaw / Hermes 的几个关键思想：

- 统一会话入口
- 统一运行时
- 统一事件流
- 技能/工具不再是页面私有逻辑
- 上下文装配与会话记忆进入运行时

### 14.2 我们没有照搬什么

我们没有把项目主架构直接改成“完全自由调度的 Agent Loop”。

原因不是能力不足，而是场景不匹配。

对于企业知识图谱和工业级问答场景：

- 完全自由调度并不天然更优
- 反而容易牺牲准确率、可解释性和治理能力

### 14.3 三者定位差异

可以把三者概括成：

- `tupu`：受控业务能力平台，工作流优先，Agent 作为通用能力保留
- `OpenClaw`：统一 Agent Runtime，偏长期运行助手和多通道接入
- `Hermes`：统一 Agent Core，偏通用工具注册、调度和多入口代理工程

### 14.4 当前工程差距

如果只看工程能力，`tupu` 当前相对 OpenClaw / Hermes 的主要差距集中在：

1. 统一 capability registry 仍不够成熟
2. session lane / 并发治理仍不足
3. plugin / hook / MCP 体系还弱
4. 长期 memory / retrieval / compaction 仍不完整
5. 多入口、多通道复用同一 runtime 仍不足
6. provider、tool backend、capability policy 的统一抽象仍不足

### 14.5 当前不应机械对齐的地方

以下几点不应简单理解为“没有就是落后”：

1. 完全自由 Agent Loop
2. 开放式工具随意调用
3. 以多通道入口为第一优先级
4. 以 workspace markdown 作为主配置载体

对 `tupu` 更合适的方向是：

- 工作流主链保持高可控
- Agent Engine 作为补充能力存在
- 两者共享统一运行时、上下文和能力层

## 15. 当前不足与下一步方向

### 15.1 当前不足

当前最需要继续加强的不是“再做更多页面接统一会话”这么简单，而是底层统一能力层。

主要不足包括：

- 技能、工具、系统动作尚未统一成真正的 `Capability Registry`
- `Agent Engine` 还没有完整开放式能力调度框架
- `session lane`、运行锁、并发治理仍不完整
- 长期记忆、检索、压缩仍未形成完整体系
- 插件、Hook、MCP 接入层仍未标准化

### 15.2 下一步最合理的演进方向

后续最合适的路线不是二选一，而是继续明确双引擎：

#### 路线 A：继续增强 Workflow Engine

重点包括：

- 更强的节点输入输出治理
- 更强的工作流调试
- 更强的结构化结果与审计
- 让问实体、问数、联接、溯源全部纳入统一工作流体系

#### 路线 B：建设 Agent Engine

重点包括：

- 统一 capability registry
- 可选自由调度
- 通用工具调用
- Hook / Plugin / MCP
- 更完整的 memory / retrieval / compaction

### 15.3 最终目标

最终目标不是“把所有东西都改成 Agent”，而是形成如下结构：

- 同一个统一会话底座
- 同一个统一运行时
- 同一个能力注册层
- 两种编排引擎
- 由场景自己选择最合适的执行方式

## 16. 代码与模块索引

### 16.1 前端关键文件

- `frontend/src/App.tsx`
- `frontend/src/services/api.ts`
- `frontend/src/pages/QueryEntity.tsx`
- `frontend/src/pages/LLMChatPlayground.tsx`
- `frontend/src/pages/WorkflowManager.tsx`
- `frontend/src/pages/WorkflowDetailPage.tsx`
- `frontend/src/components/conversation/sceneConfigs.tsx`
- `frontend/src/components/conversation/useConversationRun.ts`
- `frontend/src/components/conversation/ConversationPage.tsx`
- `frontend/src/components/conversation/ConversationMessageList.tsx`
- `frontend/src/components/conversation/CardRenderer.tsx`

### 16.2 后端关键文件

- `backend/app/main.py`
- `backend/app/api/runs.py`
- `backend/app/api/workflows.py`
- `backend/app/api/query_entity.py`
- `backend/app/services/agent_run_runtime.py`
- `backend/app/core/scheduler_core.py`
- `backend/app/models/scheduler.py`
- `backend/app/services/query_entity_skill_runtime.py`
- `backend/app/services/query_entity_workflow_bootstrap.py`
- `backend/app/services/query_entity_service.py`

## 17. 参考基线

本节只说明本文档在架构思想上参考的公开资料范围，用来帮助理解双引擎设计与对比结论。

主要参考方向包括：

- OpenClaw 关于统一 Agent Runtime、Workspace、Session、Memory、Channel 的公开说明
- Hermes 关于统一 Agent Core、Tool Registry、Tool Runtime、Gateway、Provider Runtime 的公开说明

这些参考用于帮助判断：

- 哪些能力值得吸收
- 哪些能力适合作为备选引擎建设
- 哪些能力不应直接替换当前工作流主链
