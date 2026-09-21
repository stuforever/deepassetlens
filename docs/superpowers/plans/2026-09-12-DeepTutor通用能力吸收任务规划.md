# DeepTutor 通用能力吸收任务规划（③④⑤⑥ 路线总规划）

> **依据（已批准）**：`docs/superpowers/specs/2026-09-12-DeepTutor能力吸收规划.md`（头脑风暴窗口交付，用户拍板「凡后续子项目，DeepTutor 通用能力一律纳入吸收评估；方式恒为重造，代码零搬运」）。本文是第二棒把判定表转成**任务规划**——定序列、定任务包、定各件开放问题。
> **边界（诚实声明）**：③④⑤⑥ 的**实施计划（plan.md）尚未到产出时机**——吸收规划明确「到各自 spec 时再钻」。本文到「任务包+批结构雏形+spec 开放决策清单」粒度为止；各件 spec 经头脑风暴窗口成文批准后，回本窗口出正式 plan.md+交棒提示词（与①②同模式）。
> **本窗口纪律**：只出规划不写代码；本文档随首个依赖它的 spec/plan 入库。

## 〇、总序列与依赖

```
①专家地基 ──执行中（计划已成，交棒已发）──┐
②记忆插槽 ──计划已成，待执行（硬前置=①）──┤
                                          ├→ ⑤教学引擎（最大件）→ ⑥收尾件
③模型目录 ┐                               │
④知识库   ┴─ 双件并行设计（平台两大通用件）──┘
```

- **设计先行、实施排队**：③④ 的 spec 设计不依赖①②代码落地（只引用已冻结的①② spec），**头脑风暴窗口现在就可发起**；但 ④ 的实施硬依赖 ① 落地（指针型 KB 直接挂①的 `knowledge_sources` 白名单），③ 实施无硬依赖可先走。
- 序列依据：吸收规划 §三（②成文 → ③+④双件并行设计 → ⑤ → ⑥）。

## 一、③ 模型目录与能力门控（任务包）

| 项 | 内容 |
|---|---|
| 范围 | DeepTutor `llm/` + `model_selection`（39 py，**未深读**——spec 时再钻）→ tupu「模型目录化+按模型能力门控（v1.4.6 能力位设计）」 |
| tupu 锚点 | `kg_llm_connection_configs`（models/base.py L391，m11-LLM连接与客户端 域）；`get_chat_model` 装配链（①计划沿用） |
| 吸收物 | 模型目录（名称→元数据：上下文窗/能力位）+ 按能力位门控（如 vision/json/工具调用）——设计纪律+文案级继承，代码零搬运 |
| spec 开放决策 | ①目录载体（静态代码目录 vs DB 表 vs 连接配置扩展列）；②能力位粒度与命名；③门控生效点（装配期拒 or 守卫）；④与 m11 现状（连接配置）的边界——哪些进目录哪些留连接 |
| 形态 | 预计中件；无新基建（都在既有 LLM 连接域内） |

## 二、④ 文档知识库四纪律重造（任务包，本文示例主件·调研重点）

### 2.1 现状与缺口（m15 亲读实测，2026-09-12 本窗口）

tupu **已有索引型 RAG**（m15，非绿地——④是升级不是新建）：`kg_knowledge_base`+`kg_knowledge_document` 两模型；8 端点（prefix `/knowledge-bases`：列表/建库/详情/删库/上传/删文档/全库向量化/检索）；每 KB 一个 Qdrant collection（`kb_` 前缀）；原文在磁盘 `backend/data/kb_documents/{kb_id}/`；前端寄宿向量管理页（VectorManagePanel L164-340）；问数侧 answer_type=`knowledge` 消费。

对照 DeepTutor 四纪律的**缺口**：

| # | DeepTutor 纪律 | tupu 现状 | 缺口 |
|---|---|---|---|
| 1 | 索引型 vs 指针型二分（connected 五种指针，删除永不碰外部资源） | 只有索引型 | **无指针型**；①的 `knowledge_sources` 白名单现仅 `{"ontology_graph"}` |
| 2 | 四方法引擎协议（initialize/add_documents/search/delete，duck-typing hasattr 探测） | 管线硬绑 Qdrant | 无引擎注册表（对齐①工具注册表模式） |
| 3 | 增量与对账（嵌入指纹 `_reconcile_embedding_flags`/文件夹变更检测/`clean_rag_storage(backup=True)`） | m15 验收4 明文松账：「重复 vectorize 幂等（跳过或按 hash 重算——**以实现为准登记**）」 | **指纹对账未做**——重嵌入策略无签名管理 |
| 4 | 状态报告持有内容（get_info/get_kb_status 产品语义） | status/error_msg 骨架在 | 报告语义薄（探针文化与①同源但未展开） |

**tupu 先天优势**（吸收规划亲证维持）：四库基建在跑（Qdrant/ES/Neo4j/Doris）；`TupuQdrantClient`（services/tupu_qdrant_client.py L39）已是统一客户端，消费面 7 文件（main.py L134 健康检查、knowledge_base.py L56、golden_qa/qa_example/standard_semantic 三服务族、entity_attr_vector_service）——DeepTutor 要引 LlamaIndex 全家，tupu 只需组织已有件。

### 2.2 批结构雏形（六批，spec 冻结后细化成正式 plan.md）

- **批 0 基准固定**：m15 八端点全链 e2e 存照（建库→上传→vectorize→search）+ 重复 vectorize 行为实录（松账锚——批 3 修后对照）+ `knowledge_sources` 白名单现状存照；
- **批 1 引擎协议**：四方法 Protocol+注册表（qdrant 族=现 m15 管线收编）；duck-typing 容忍部分实现；云引擎（PageIndex/IMA/LightRAG）**不收**（真实需求再议）；
- **批 2 指针型 KB**：kb_types 二分落地；①`knowledge_sources` 白名单扩展（本体图谱=指针、Doris catalog=指针）；**删除永不碰外部资源**铁则+越界矩阵单测；
- **批 3 增量与对账**：collection 签名管理（模型/维度/分块器指纹——指纹变更才重嵌入）+ 对账防漂移 + `clean(backup=True)` 清理纪律——**补 m15 验收4 的松账**；
- **批 4 状态报告+管理页**：get_info/get_kb_status 产品语义（④ KB 管理页核心数据源）；VectorManagePanel 知识库区升级（选择器零改动）；
- **批 5 验收总账**：四纪律逐条+指针/索引删除语义分测+等值回归（m15 原功能零退化）+M00 回写。

### 2.3 spec 开放决策清单（带去头脑风暴窗口）

1. `knowledge_sources` 白名单扩展到哪些指针型（本体图谱/Doris catalog 先收两个，外部 ES 等真实需求）？
2. 指针型 KB 与索引型 KB 在①专家卡上是同一字段还是分槽（`knowledge_sources` vs 卡 `memory` 槽形态）？
3. parsing 的 factory/cache/signature 纪律（吸收规划：并入④）——分块器指纹构成、缓存键？
4. 增量对账的触发时机（上传时/定时时/手动）与 m14 调度域的边界？
5. 删除语义矩阵：索引型删库三处清（m15 现状）vs 指针型只删引用——单测矩阵怎么铺？
6. 与 m09（向量基建供应方）/m15（现 KB）/m16·m18（问数消费方）三域的边界声明。

## 三、⑤ 教学引擎（任务包）

| 项 | 内容 |
|---|---|
| 范围 | DeepTutor `learning/` 53 py + `book/` + H5 前端 100+ py——**最大件，本质搬运+MCP 壳**（15 篇 H5 设计文档在库）；React 重写原则已立 |
| 硬前置 | ①专家（多教学专家）+②记忆（L1-L3 教学轨迹/画像）+③模型目录+④知识库（教材即 KB）——**全落地后开工** |
| spec 开放决策 | 教学循环与 LoopCapability 的关系（①已同构吸收配置卡四要素）；教材 KB 的指针/索引选型；教学专家卡模板；H5→React 的页面清单与裁剪 |
| 形态 | 超长任务模式（预计多 plan 分件：引擎件/前端件/内容件）——届时单独立规 |

## 四、⑥ 收尾件（任务包）

- **cron 定时任务**（DeepTutor 3 py，小件）：定时专家任务——挂①专家卡+②consolidator 周期扫描同族后台模式；spec 时定触发面（对话任务 or 巩固任务）。
- **partners/IM 召唤+私有记忆**（31 py）：延后——专家卡+门户已覆盖核心形态，入口扩展类（⑥+）。
- **search/ web 搜索**（15 py）：延后，真实需求再议。
- **向量/图谱记忆载体**：② spec 载体升级路径（②期 md → ⑥期扩 PG/向量/图谱）——届时与②consolidator 模式注册表对齐。

## 五、不吸收清单（定案，不再评估）

multi_user（Authentik 已有）· mcp（自研 mcp_server 18 工具）· sandbox（9385 容器已有）· voice/imagegen/videogen/wechat_push（TTS 朗读教学远期再议）。

## 六、下一步与交接

1. **③④双件并行设计现在可发起**：各开一个头脑风暴窗口，输入=《DeepTutor 能力吸收规划》对应节+本文任务包（④重点带 §2.1 现状缺口表+§2.3 开放决策清单）+①②已冻结 spec（引用不重写）；
2. ③④ spec 批准后回**本窗口**（writing-plans）：各出 plan.md（长任务模式，对齐各自 spec 验收组）+交棒提示词——与①②同模式；
3. 实施顺序铁律：③④实施排在①②验收后（④硬依赖①的 knowledge_sources 扩展点；③无硬依赖可先走）；⑤等③④；⑥收尾。

## 七、自检

1. **规格覆盖度**：吸收规划 §一（四纪律+tupu 优势）→本文 §二；§二逐域判定表 12 行→§一（③）/§二（④）/§三（⑤）/§四（⑥）/§五（不吸收 4+4 行）全覆盖；§三优先级与诚实账→§〇+§六。遗漏：无（partners「⑥+」与 search「延后」按原文保留延后态）。
2. **证据锚点**：m15 现状（8 端点/两模型/磁盘路径/验收4 松账原文/VectorManagePanel L164-340）亲读本窗口；TupuQdrantClient L39+消费面 7 文件 grep 实测；kg_llm_connection_configs models/base.py L391 实测；①`knowledge_sources` 白名单 `{"ontology_graph"}` 出自①计划批 4 校验码；DeepTutor 侧数字（manager 1721 行 41 方法等）引自吸收规划亲读记录，本窗口未重读其源码（诚实账：③llm/39py、④parsing 引擎细节 spec 时再钻——与吸收规划 §三一致）。
3. **粒度纪律**：无实施级代码/命令占位（未到 spec 的件不假装可施工）；批雏形仅④给出（调研重点+用户点名示例），③⑤⑥止于任务包表——各自 spec 后补全。
