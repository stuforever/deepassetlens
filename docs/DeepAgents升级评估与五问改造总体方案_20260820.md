# DeepAgents 升级评估 × 五问改造总体方案

> 2026-08-20 · 设计窗口产出
> 两部分：**A. 升级评估与操作 SOP**（0.6.12 → 0.7.7，依赖已实测核对）；**B. 结合五问的改造总体方案**（与既有批1-3 整合为完整批次图）。
> 关键结论先行：**升级与五问改造基本正交**——升级不解锁五问任何能力（0.7 新件均不适用 OpenAI 兼容协议），属卫生性维护；五问改造全部可在 0.6.12 上落地。

---

# 第一部分：DeepAgents 升级评估

## 1.1 版本与依赖核对（实测数据）

PyPI 最新 **0.7.7**（已重新核实），装机 **0.6.12**。0.7.7 依赖要求 vs 当前装机：

| 0.7.7 要求 | 当前装机 | 判定 |
|---|---|---|
| langchain >=1.3.14 | 1.3.14 | ✅ 恰好达线，**不动** |
| langchain-core >=1.5.0 | 1.5.1 | ✅ 满足 |
| **langchain-anthropic >=1.5.4** | **1.5.2** | ⚠️ **需升级**（小版本） |
| langchain-google-genai >=4.3.1 | 4.3.2 | ✅ 满足 |
| **langsmith >=0.10.9** | **0.8.18** | ⚠️ **需升级（跨 0.8→0.10，主要风险变量）** |
| packaging >=23.2 / wcmatch >=11.0 / Python >=3.11 | 26.3 / 11.0 / 3.13 | ✅ |
| （langgraph 未出现在 0.7.7 直接依赖中） | 1.2.6 | ✅ 经 langchain 传递链保持不动 |

**级联风险集中在两个包**：langchain-anthropic 小版本升级（低风险，我们不接 Anthropic 模型）；langsmith 0.8→0.10（中等——它是 langchain-core 的 tracing 底座，若 langchain-core 1.5.1 内部约束与之冲突，pip 会连带升 core，需评估后放行）。

## 1.2 差异与收益（wheel diff 结论沿用+本次复核）

0.6.12→0.7.7 差异仅三项：`+FsToolName` 枚举、`+_prompt_caching`（**仅 Anthropic/Bedrock**）、`+_video`（可选 PyAV）。

| 收益项 | 对本工程 |
|---|---|
| _prompt_caching | **≈0**——OpenAI 兼容协议不适用（除非未来接 Anthropic 系连接） |
| _video | 无关 |
| FsToolName | 外观性 |
| 战略收益 | 缩小未来跨版本跳跃；保持在维护线上 |

## 1.3 风险矩阵（我们触碰的框架面）

| 我们的使用面 | 0.7.7 变化 | 风险 | 拦截手段 |
|---|---|---|---|
| create_deep_agent 17 参数 | 无变化（diff 仅增量） | 低 | import 冒烟 |
| `_TupuSummarizationMiddleware` 子类 + `excluded_middleware={"SummarizationMiddleware"}` 按名匹配 | 类名未变 | 低 | test_m1_robustness 三用例直接拦 |
| RubricMiddleware/contextvar 桥 | 无变化 | 低 | rubric 集成测试 + e2e |
| HarnessProfile/excluded_tools | 无变化 | 低 | 白名单交叉校验测试 |
| astream_events v2 事件语义 | 无声明变化 | 低-中 | Playwright e2e + 事件名断言 |
| **langsmith 0.8→0.10 连带** | 见 1.1 | 中 | pip 自解析 → freeze → 全量回归 |

## 1.4 升级操作 SOP（8 步，独立窗口半天~1 天）

```
1. 基线固化    git tag pre-da-upgrade + pip freeze 存 docs/upgrade/pipfreeze-0612.txt
2. 依赖预检    已完成（本文档 §1.1）：预装 langchain-anthropic>=1.5.4、langsmith>=0.10.9
3. 分支隔离    git checkout -b upgrade/da-077
4. 安装        pip install "deepagents==0.7.7" "langchain-anthropic>=1.5.4" "langsmith>=0.10.9"
              requirements.txt 沿用现有双行模式（>=0.7.7 + ==0.7.7 锚定）；pip freeze 复存档
              ⚠️ 若 pip 连带升级 langchain-core：停下评估其 diff 再放行，否则锁 langsmith 中间版试探
5. 静态验证    import 冒烟：create_deep_agent / RubricMiddleware / PatchToolCallsMiddleware /
              SummarizationToolMiddleware / register_harness_profile / MemoryMiddleware 全部可导入
6. 全量测试    pytest 全绿（359+ 基线）——重点 m1 装配/rubric 集成/白名单交叉校验
7. 动态验证    四件套：smoke_release.py + 金标 eval（首轮+稳定双口径）+ Playwright e2e 一题 + tsc
8. 合入/回滚   全绿且 eval 不降 → merge；
              任一破线 → pip install deepagents==0.6.12（requirements 回滚）→ 重跑 pytest 确认回绿
```

## 1.5 决策建议

- 功能收益 ≈0；成本 0.5~1 天 + 一轮全量回归；风险可控且有测试网。
- **决策树**：30 天内有接 Anthropic 系模型计划 → 升（拿 prompt_caching）；否则两可，**倾向升级**（卫生性，避免未来 0.7→0.8 跳跃更大），排批1/批2 稳定后的独立窗口，**不与功能批混车**。

---

# 第二部分：五问改造总体方案（整合批次图）

> 与《问数提速与答案直出_详细设计》的批1-3 整合；新增批5-9 对应五个问题；批U=升级窗口。

## 2.0 批次全景

| 批 | 名称 | 来源问题 | 核心收益 | 量级 | 依赖 |
|---|---|---|---|---|---|
| 批1 | 答案直出 + rubric 分档 | （180s 解剖 P0） | 观感死等消灭、每问省 20-40s | 1.5d | - |
| 批2 | 减轮次三件套（示例直通/实体预解析/指引预载） | （P1） | 5 轮→2-3 轮 | 1.5d | 批1 定型 |
| 批3 | 计时外露 + grader 轻模型 | （P2） | 可观测 | 0.5d | 批1 |
| **批5** | **前缀缓存最大化** | 问一 | TTFT↓+账单↓（叠加增益） | 1d | 批2（文案稳定化在其上做） |
| **批6** | **路由健壮化** | 问二 | 措辞敏感治理制度化 | 0.5d | - |
| **批7** | **检索单调用化+短窗缓存** | 问三 | 每问省 0.5-3s 检索开销的一半 | 0.5d | 并入批2-D 实施 |
| **批8** | **search_entities 混合检索升级** | 问四 | 口语词召回显著改善 | 1d | - |
| **批9** | **模板直出管道 v1** | 问五 | 高频题 0 LLM 轮、2-4s | 2d | 批2-C 示例基建 |
| 批U | DeepAgents 0.7.7 升级 | 本文档上部 | 卫生性 | 0.5-1d | 批1/2 稳定后独立窗 |

推荐执行序：批1 → 批2(含7) → 批9 → 批8 → 批3 → 批5 → 批6 → 批U。

## 2.1 批5 前缀缓存最大化（问一）

**原理**：DeepSeek 服务端自动前缀缓存隐式生效，命中=前缀逐字节一致；我们只需「别打碎前缀」+「能看见命中率」。

| 项 | 改法 | 落点 |
|---|---|---|
| C1 契约文案模板化 | `_build_contract_system_message` 行文案抽模块级常量（同场景逐字节一致）；变化内容已在尾部（示例块）✅ | data_intelligence.py:83-93 |
| C2 工具顺序固化 | 确认 MCP list_tools 顺序稳定，必要时按名排序固定一次 | tupu_deepagent 工具装配处 |
| C3 摘要保守化 | trigger 30k 维持；摘要触发记治理事件（bust 缓存可见） | _TupuSummarizationMiddleware |
| C4 命中率观测 | DeepSeek usage 含 prompt_cache_hit_tokens/miss_tokens——llm_client 读取落日志/EngineQueryLog 附列；**先探测字段是否透传**（ChatOpenAI 可能吞），无则降级为仅 TTFT 观测 | llm_client.py + stream done 载荷 |

验收：同场景连续两问，第二问 cache_hit>0（日志）；TTFT 环比下降。
风险：usage 字段不透传 → 只做 TTFT 观测（收益打折但不阻塞）。

## 2.2 批6 路由健壮化（问二）

立场不变：**路由保持纯规则确定性**（权限边界不可交给采样）。本批治「措辞敏感的制度化」：

- R1 触发词治理流程化：SKILL.md triggers 变更必须跑金标措辞变体组（S2 已建组）；发布清单加门槛「triggers 变更 → eval 全量通过」；
- R2 意图分类集中化：detect_aggregate_intent/clarify/topn-count 分类收拢为 `intent_classifier.py` 纯规则单模块——路由、指引预载（批2-E）、模板直出（批9）三处共用同一套判定，消除散落关键词；
- R3 轻量 LLM 路由：**继续不做**（理由见五问文档问二）；若未来做，限定 generic 内部细分+快模型+受限枚举。

验收：措辞变体组金标全过；intent_classifier 单测（三类意图×正反例）。

## 2.3 批7 检索单调用化 + 短窗缓存（问三）

并入批2-D 实施细化：

- E1 单入口 `retrieve_context_bundle(db, question)`：**一次 embed_texts** → 并搜 tupu_qa_examples（示例）与实体集合（候选实体提示）→ 返回 `{examples_block, example_hits, entity_hint_block}`；`_build_contract_system_message` 改调此入口；
- E2 短窗缓存：LRU `{question_norm: bundle}` TTL=60s size=128——重复提问/纠错重试免远程检索；
- 验收：mock 断言单次 embedding 调用；二次提问 0 远程调用；Qdrant 断开降级不阻断。

## 2.4 批8 search_entities 混合检索升级（问四）

**现状**：MCP 工具层实体定位是纯 MySQL LIKE/code 匹配（kg_action_handlers 实查，向量/图零引用）。

**改法（对模型透明：签名不变、返回结构加 `match_type` 字段向后兼容）**：

```
三级融合：
①精确 entity_code/en_name 命中 → 直返（确定性保留，match_type=exact）
②关键词 LIKE（现状逻辑保留，match_type=like）
③向量召回：hybrid_retrieval 同义词扩展 → embed_texts → Qdrant 实体集合 top-N
  （集合盘点：entity_attr_vector_service 对应集合；分数阈值 ≥0.6）
融合排序：LIKE 命中优先，向量补充追加（match_type=vector）；同分按 entity_code 字典序（确定性）
事实源不变：属性清单仍从 MySQL properties_schema 取——向量只做召回，不做事实
```

- 降级：Qdrant 断开 → 静默回 LIKE（主链路零新依赖）；
- 验收：「配变」「专变」命中配电变压器实体；同输入同输出单测；金标 eval 不降；
- 量级 ~1 天。**收益**：「配变/专变」类口语词召回打通（现在 LIKE 匹配不上就找不到）。

## 2.5 批9 模板直出管道 v1（问五）

**触发判定**（路由后、Agent 前，stream 编排层插入分支）：

```
route_type=generic 且 example_hits 最高分 ≥0.95
且 intent_classifier=count 类 且 无动态条件（日期/客户名/比较词纯规则检测）
且 示例 sql 非空且 status=enabled
```

**直通执行**（新 direct_pipeline.py，绕过 Agent 循环）：

```
example.engine 定执行工具 → validate_sql 安全校验 → 引擎执行
→ verification 计算 → EngineQueryLog(direct_pipeline=true) → SSE(status/sql_result/final/done)
→ answer_renderer.py 模板填槽（row_count/scope 注释/data_snapshot_at）
```

- **SSE 兼容**：事件序列与 Agent 路径一致，前端零改动；evidence 带 `direct_pipeline=true`、置信度「高」（确定性来源）；
- **兜底**：执行报错 → governance 记 fallback → 回退完整 Agent 路径（用户无感，只是变慢）;
- **安全边界诚实声明**：直通绕过 SkillPolicy/Agent——安全由「来源可信」（验证 SQL 单源）+validate_sql+模板白名单承接，有意取舍登记在案；
- **与批2-C 的分层**：sim≥0.95 且无动态条件 → 批9 直通（0 轮）；sim 0.90~0.95 或带条件 → 批2-C 首选计划（Agent 2 轮）；其余 → 常规 Agent；
- **观测**：直通率/兜底率/直通答案 👎 率 vs Agent 答案（防僵化劣化看板）；
- 验收：「统计用电客户数量」e2e ≤4s；人为改坏示例 SQL → 自动回退 Agent 正常作答；👍 幂等（直通答案不重复入示例库）；
- 量级 ~2 天。

## 2.6 批U 与改造的正交性

升级不解锁五问任何能力（0.7 新件均不适用）；五问改造全部可在 0.6.12 落地。因此**升级窗口独立**，放在批1/批2 稳定后，避免「功能改动+依赖变更」混车的归因困难。

---

# 三、总验收矩阵

| 批 | 一句话验收 |
|---|---|
| 批1 | 「统计用电客户数量」答案首 token 即在输出区成型；示例锚定题无 grader 调用 |
| 批2 | 该题 ThinkStream 步骤数 ≤3；总时长 ≤25s（锚定）/≤60s（未锚定） |
| 批3 | done 载荷含 timing；徽标 hover 可见分段耗时 |
| 批5 | 同场景二问 cache_hit>0 或 TTFT 环比下降（有数据） |
| 批6 | 措辞变体组金标全过；intent_classifier 单测绿 |
| 批7 | mock 断言单次 embedding；二次提问 0 远程检索 |
| 批8 | 「配变/专变」命中配电变压器；同输入同输出；eval 不降 |
| 批9 | e2e ≤4s；坏 SQL 自动回退 Agent；直通率看板上线 |
| 批U | SOP 八步全绿；eval 双口径不降；否则 24h 内回滚归档 |

全程纪律：Playwright e2e 为验收标准（串行）；pytest 全绿；金标 eval 双口径不降；发布清单同步更新。
