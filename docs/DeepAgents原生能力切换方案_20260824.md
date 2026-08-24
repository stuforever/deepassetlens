# 切换 DeepAgents 原生能力：迁移方案（原生化路线图）

> 2026-08-24 · 设计窗口产出
> 立场修正：不再论证「为什么不用」，改为回答「**哪些自研件应该切回框架原生、怎么切、何时切**」。
> 总策略三原则：①原生优先——自研面每减一米，框架升级维护债减一分；②红线不翻案——subagents/shell/sandbox/response_format 永不启用；③触发器驱动——生态不适配项绑定明确触发条件，条件到了再切。

---

## 一、当前自研面清单（要削减的对象）

| 自研件 | 有无原生对应 | 处置 |
|---|---|---|
| `_TupuSummarizationMiddleware` 子类 | ✅ 原生已参数化（trigger/keep/token_counter） | **T1 切换** |
| PatchToolCalls 未装配 | ✅ 原生现成 | **T1 切换** |
| HITL 条件人审（langgraph interrupt+自研恢复端点） | 🟡 原生 interrupt_on 仅静态工具级 | **专项协议对齐** |
| SkillPolicy/DataSummary/EntityResolver 中间件 | ❌ 无对应概念 | 保持自研（域核心资产） |
| SkillRouter/QueryContract/template_guard | ❌ 无对应 | 保持自研 |
| 示例库/直通管道/治理三本账 | ❌ 无对应 | 保持自研 |
| contextvar rubric 桥 | 🟡 框架走 stream_writer，astream_events 收不到 | 保持（技术必需） |

## 二、T1 直接切换（本周期执行）

### 1. PatchToolCallsMiddleware 补装配（0.25d）
- 动作：middleware_list 追加一行 + 全量回归；
- 收益：模型流式中断留下的悬空 tool_calls 自动修复（防下一轮解析错乱）；
- 验收：pytest 全绿；手工构造中断场景验证修复行为。

### 2. Summarization 子类退役（0.5d，含验证）
- 新事实：原生构造器支持 `trigger`（阈值）、`keep`（保留条数）、`token_counter`——**当年被迫子类化的理由已消失**；
- 切换路径：
  ```
  试：直接用原生 SummarizationMiddleware(model, backend, trigger=30_000, keep=("messages",10))
  验证点：excluded_middleware={"SummarizationMiddleware"} 是否会误杀同名实例
        → 若会：改用 profile 白名单式装配或保留「只传参的薄壳子类」
        → 若不会：删除 _TupuSummarizationMiddleware 整个类
  回归锚：长会话摘要行为对比（同输入同输出）+ pytest
  ```
- 收益：少维护一个依赖框架内部命名的子类（框架升级脆弱点 -1）。

## 三、T2 条件切换（绑定触发器，条件到即切）

| 能力 | 触发器 | 届时动作 |
|---|---|---|
| PromptCachingMiddleware + `cache` 断点 | 接入任一 Anthropic 系模型连接 | 装配中间件+显式缓存断点，TTFT/费用立降 |
| LangSmith tracing / ContextHub 后端 | 出现云端观测或多环境协同需求 | backend 切换+tracing 开关 |
| StoreBackend（长期记忆 KV） | 出现非向量型记忆需求（用户偏好/项目级设定） | store 参数挂接 |
| `_message_eviction` / `_overflow_clip` | 实测出现单条超大消息撑爆上下文的案例 | 先确认与 summarization 的联动关系，再按 DataSummary 同策略启用为第二道保险 |

## 四、专项：HITL 协议原生化（中等强度，0.5d）

- 现状：SkillPolicy 内 langgraph `interrupt()` + 自研恢复端点/事件协议；
- 目标：**对齐协议不对齐机制**——恢复请求/响应采用框架 `Command(resume)` 惯例形态，`_fs_interrupt` 的事件结构作参照；
- 不切换机制的理由：`interrupt_on` 只能静态按工具配置审批，表达不了「仅 TABLE_MISSING 且 generic 路径才审」的条件逻辑；
- 收益：升级兼容性提升、自研协议面缩小。

## 五、T3 保持自研（永久或长期）

路由器/契约体系/模板指纹守卫/错误分类学纠错/DataSummary 双通道/示例库学习飞轮/直通管道/治理三本账——框架无这些概念，它们是问数域核心资产，**原生化≠消灭自研，而是把自研集中在框架没有的地方**。

## 六、排期与回归纪律

| 步骤 | 内容 | 归属 |
|---|---|---|
| 本周 | PatchToolCalls 装配（搭车最近功能批） | 批10/11 顺带 |
| 本周期 | Summarization 子类退役验证 | 独立 0.5d |
| 下周期 | HITL 协议对齐 Command(resume) | 0.5d |
| 触发即动 | T2 四项按各自触发器 | - |

回归纪律（每次切换通用）：pytest 全绿 + Playwright e2e 事件序列比对 + 金标 eval 双口径不降；任何一项破线即回退。

## 七、预期收益量化

切换完成后自研面变化：
```
现状自研件：8 个（3 中间件 + 2 子类 + 1 桥 + 路由族 + 守卫族）
T1 后：    7 个（Summarization 子类退役）
专项后：   6.5 个（HITL 协议面对齐框架惯例）
```
绝对数不大，但**削掉的两个恰好是对框架内部实现依赖最重的两处**（命名匹配技巧、私有事件通道）——它们是历次升级风险评估里的常客，退役一个，未来每次升级就少验一处。
