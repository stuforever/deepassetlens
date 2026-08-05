# Tupu 知识图谱平台 — 完整工程描述

> 本文档为切换 IDE 时的上下文输入,涵盖工程设计、架构与核心原理。
> 生成时间: 2026-07-09

---

## 一、项目总览

### 1.1 项目定位

Tupu(图谱)是一个**面向电力行业的数据智能问答平台**,核心能力是把自然语言问题转化为可执行的 SQL,并返回结构化的 5 段式答案(总结、执行过程、属性清单、实体间关系、联接SQL)。

平台基于**知识图谱本体 + LangGraph 状态机 + 向量检索 + LLM 推理**构建,支持:
- **数据问答(question_data)**: 自然语言 -> 定位实体/属性 -> 拼装 SQL -> 5 段结构化答案
- **知识问答(knowledge_qa)**: 自然语言 -> 知识图谱检索 -> 长格式答案
- **图谱管理**: 四区建模(力导向/树状/矩阵三态可视化)、实体关系管理
- **指标中心**: 指标 CRUD、原子/派生指标、维度绑定、版本审计
- **技能编排**: DAG 工作流、技能沙箱执行引擎

### 1.2 技术栈一览

| 层 | 技术 | 版本/说明 |
|---|---|---|
| 后端框架 | FastAPI + Uvicorn | ASGI 异步,端口 8100 |
| ORM | SQLAlchemy + PyMySQL | MySQL 8.x,utf8mb4 |
| 图数据库 | Neo4j (neo4j-driver v6) | bolt://127.0.0.1:7687 |
| 向量数据库 | Qdrant (HTTP REST, 端口 6333) | 三个 collection |
| 状态机 | LangGraph >= 0.2.50 | StateGraph + InMemorySaver |
| LLM 客户端 | langchain-openai >= 0.1.0 | ChatOpenAI / OpenAIEmbeddings |
| 本地向量模型 | langchain-huggingface | bge-large-zh-v1.5 (1024d) |
| 认证 | PyJWT + Authentik OIDC | RS256 JWT 验签 |
| 前端框架 | React 18 + TypeScript | CRA (react-scripts 5.0.1) |
| UI 库 | Ant Design 5 | |
| 状态管理 | Zustand 4 | 仅全局画布态 |
| 图可视化 | @antv/g6 4 + @xyflow/react 12 | 力导向/树/矩阵/DAG |
| 代码编辑 | @monaco-editor/react | 技能脚本编辑 |
| HTTP | Axios | 拦截器注入 OIDC token |

### 1.3 顶层目录结构

```
tupu/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── main.py             # 启动入口 + lifespan + 路由注册
│   │   ├── api/                # 18 个路由文件
│   │   ├── services/           # 29 个服务文件 + tasks/ 子包
│   │   ├── models/             # ORM 模型 (base.py ~770行, 40+表)
│   │   ├── core/               # 数据库/认证/执行引擎/任务队列
│   │   └── schemas/            # Pydantic 请求/响应
│   ├── data/
│   │   ├── di_threads/         # 秘书态持久化 JSON
│   │   ├── skills/             # 技能脚本 (boss_router/locate_l2/explore/...)
│   │   └── business_chain_spec.yaml  # 业务链 YAML 规格
│   ├── requirements.txt
│   └── __start_8100.py         # 启动脚本
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── App.tsx             # 顶层布局 + 菜单 + switch路由
│   │   ├── pages/              # 20 个页面
│   │   ├── components/         # 通用组件 + conversation/ + editors/
│   │   ├── services/           # 7 个 API 封装
│   │   ├── store/              # Zustand
│   │   └── auth/               # AuthGate + OIDC
│   └── package.json
├── models/                     # 本地向量模型 bge-large-zh-v1.5
├── wiki/                       # 12 篇架构文档
├── docs/                       # 设计文档 + 验收报告
├── e2e/                        # Playwright 端到端测试
├── docker-compose.yml          # MySQL/Neo4j/Qdrant 基础设施
└── docker-compose.infra.yml    # Authentik 认证服务
```

---

## 二、后端架构

### 2.1 启动入口 (app/main.py)

```python
app = FastAPI(title="数据智能分析组件 API", lifespan=lifespan)

# 中间件
# 1. CORS: allow_origins=["*"]
# 2. Authentik OIDC: ENABLE_AUTH=0 时短路放行

@asynccontextmanager
async def lifespan(app):
    # 1. 建表 + 轻量迁移 (ensure_schema_compatibility)
    # 2. 初始化种子数据 (init_db)
    # 3. Qdrant 标准语义同步 (健康检查 -> 自动同步 -> 设 TUPU_VECTOR_BACKEND=qdrant)
    # 4. Neo4j 全量重建 (健康检查 -> sync_all_to_neo4j force=True)
    # 5. 后台线程: 实体/属性向量同步 (不阻塞 startup)
    # 6. 启动 TaskWorker (poll_interval=2.0)
    yield
    task_worker_manager.stop()
```

**路由注册(前缀)**:
- `/api/v1` — auth, concepts, mappings, chat, upload, source_tables, llm_admin, standard_semantic, data_source, entity_relation_manage, metrics, smart_metric, metadata, runs
- `/api/v2` — skills-v2
- `/api/data-intelligence` — 核心对话 API(chat / chat/stream / state / reset / health)
- `/api/v1/sync` — Neo4j/向量同步

### 2.2 API 路由层 (app/api/)

| 路由文件 | 前缀 | 职责 |
|---|---|---|
| auth.py | /auth | OIDC 配置、用户身份、开发模式登录、资源授权 |
| concept.py | /concepts | 概念/实体/关系 CRUD、Excel 导入导出、Neo4j 同步 |
| mapping.py | /mappings | 源表管理、映射规则、字段探查、实体建模 |
| chat.py | /chat | 旧版 Neo4j 图问数(NL2Cypher 规则匹配) |
| upload.py | /upload | CSV 源字段批量导入 |
| source_tables.py | /source_tables | 源主数据/业务/参考表 CRUD |
| llm_admin.py | /llm_admin | LLM 连接配置 CRUD、Planner 配置、LLM 测试 |
| standard_semantic.py | /standard_semantic | 术语提取、标准语义词条、向量化、检索 |
| data_source.py | /data_source | 多数据源配置 |
| entity_relation_manage.py | /entity_relation_manage | 实体关系手工维护、Excel 导入导出 |
| metric_center.py | /metrics | 指标 CRUD、原子/派生指标、维度绑定、版本审计 |
| metadata.py | /metadata | 元数据快照、分类树、诊断视图 |
| runs.py | /runs | Agent 运行、会话、消息、SSE 事件流 |
| **data_intelligence.py** | /api/data-intelligence | **核心对话**: chat 同步、chat/stream SSE、state、reset、health |
| data_sync.py | /api/v1/sync | Neo4j 重建/清空、实体/属性向量化 |
| v2_skills.py | /api/v2/skills-v2 | 技能 CRUD、版本、执行、API 绑定 |

### 2.3 核心服务层 (app/services/)

#### 2.3.1 data_intelligence_graph.py (~1765 行) — 主状态机

包含 **3 个独立 LangGraph 图**:

**图 1: 问数直通图** (question_data 模式,默认)
```
entry_router → 定位L2 → 定位实体属性 → SQL拼装 → 答案生成 → 推荐
```
- `entry_router_node`: 判断是否已有 assembled_sql 且用户要执行
- `locate_l2_node`: 调 query_entity_service 定位 L2 大类
- `locate_entity_attr_node`: 调 query_attribute_service 定位实体+属性
- `sql_assembly_node`: 生成 SQL
- `answer_synthesizer_node`: LLM 流式生成摘要 (chat.stream + StreamWriter)
- `recommend_node`: LLM 生成 3-5 个推荐问题

**图 2: 知识问答图** (knowledge_qa 模式)
```
知识问答 → 答案生成 → 推荐
```

**图 3: 主数据智能图** (legacy 模式)
```
boss_router → {定位 | SQL流水线 | 探索 | 兜底 | 意图确认}
定位 → locate_exit → {SQL流水线 | clarify | next_step}
```

**技能加载**: `_get_new_skill_module(skill_name)` 用 importlib 动态加载 `data/skills/{skill_name}/scripts/main.py`,`_inject_new_skill_globals()` 注入 LLM/向量/元数据依赖。

#### 2.3.2 secretary_state.py (~342 行) — 秘书态

跨轮次单一状态源,使用 Pydantic BaseModel(兼容 InMemorySaver 序列化):

```python
class ConfirmedItems(BaseModel):
    L1, L2, L2_id, L2X: Optional[str]      # 主数据层级
    L2X_related: List[str]                  # 关联实体
    L3, L4, L4X: Optional[str]              # 业务层级
    attributes: List[Dict]                  # 已锁定属性
    extra_entities: List[str]
    relations: List[Dict]                   # 关系
    assembled_sql: Optional[str]            # 已拼装 SQL
    sql_execution_result: Optional[Dict]    # SQL 执行结果

class SecretaryState(BaseModel):
    user_input, original_query, dialog_history
    confirmed: ConfirmedItems
    task_snapshots: Dict[str, TaskSnapshot] # 每任务快照
    current_task, goal                      # goal: sql_assembly | knowledge_only
    # 5 旗标
    chain_locked, entity_locked, attribute_locked, relation_locked, sql_executed
    completed_tasks: List[str]
    think_history: List[Dict]               # 思考链
    pending_clarification: Optional[Dict]
    final_answer: str
    recommendations: List
    session_id, thread_id
```

**快照机制**: `TaskSnapshot` 基类 + 子类(EntityLocationSnapshot, AttributeLocationSnapshot...),`_create_snapshot()` 按当前任务分派,`restore_snapshot_from_dict()` 恢复。

#### 2.3.3 llm_client.py (~209 行) — LLM 抽象层

```python
def build_chat_model(item, temperature, timeout, extra_payload, streaming):
    # 从 LLMConnectionConfig ORM 构造 langchain_openai.ChatOpenAI
    # api_key 支持 ${ENV_VAR} 占位符解析

def call_openai_compatible_chat(item, system_prompt, user_prompt) -> str:
    # System + User 双消息,纯文本 content

def call_openai_compatible_chat_stream(item, system_prompt, user_prompt):
    # 流式 chat.stream() 生成器,逐块 yield 文本
```

> **重要**: 所有 LLM 调用都是纯文本 `HumanMessage(content=str)`,无多模态/图片输入。

#### 2.3.4 query_entity_service.py (~1189 行) — 实体定位

- `build_metadata_from_system(db)`: 构建 domain_catalog(L1/L2 + primary/secondary entities) + relation_catalog
- `_invoke_query_llm(...)`: 调 LLM + 元数据,解析 JSON 响应
- `_validate_result(...)`: 校验 LLM 输出,回填 L2X,检查一致性
- `get_query_llm_connection(db, llm_connection_id)`: 解析 LLM 连接

#### 2.3.5 query_attribute_service.py (~1395 行) — 属性定位

- `build_attribute_metadata_from_system(db)`: 构建 scope/entity/attribute/relation catalog
- `_recall_attribute_hits_from_validation_catalog(...)`: 按名称/别名打分召回
- `_resolve_entity_candidates_from_attribute_hits(...)`: 按实体分组合并
- `_validate_query_attribute_result(...)`: 校验 + 回填 + 构建 SQL 蓝图
- `_build_sql_text(blueprint)`: 生成 `SELECT...FROM...LEFT JOIN` SQL

#### 2.3.6 skill_injections.py (~626 行) — 技能沙箱注入

为技能脚本提供依赖注入工厂:
- `build_llm_client()` / `build_llm_chat_model()`: LLM 客户端
- `build_vector_recall_fn()`: Qdrant entity_embeddings 向量召回
- `build_attribute_vector_search_fn()`: Qdrant attribute_embeddings 检索
- `build_fetch_all_l1_l3()` / `build_fetch_l2_l4_by_parent()` / `build_fetch_entities_by_parent()`: MySQL 层级导航
- `build_fetch_entity_attributes()`: 按 entity_code 查 properties_schema
- `build_search_knowledge()`: 知识图谱关键词 LIKE 检索

#### 2.3.7 semantic_retrieval.py (~515 行) — 向量嵌入调度

- `VECTOR_MODEL_REGISTRY`: 本地(bge-large-zh 1024d, bge-m3 1024d) + 远程(glm-embedding-3 2048d)
- `_EmbeddingEngine`: 三后端 — sentence_transformers / openai_compatible_embedding / hash
- `encode_texts_with_config(db, texts, model_name)`: 路由本地/远程嵌入
- `hybrid_score(keyword_score, semantic_score, cfg)`: 加权混合评分

#### 2.3.8 tasks/ 子包 — LangGraph 任务节点

| 文件 | 职责 |
|---|---|
| entity_location.py | 实体定位: 3 级漏斗 S1(锁大类)→S2(锁小类)→S3(锁实体),含 HITL |
| attribute_location.py | 属性定位 |
| relation_location.py | 关系定位 |
| lineage_location.py | 血缘定位 |
| sql_assembly.py | SQL 拼装 |
| sql_execution.py | SQL 执行 |
| exploration.py | 探索(RAG) |
| fallback.py | 兜底 |

---

## 三、数据模型 (app/models/base.py, ~770 行, 40+ 表)

### 3.1 知识图谱本体

| 表 | 模型 | 核心字段 |
|---|---|---|
| kg_concepts | Concept | id, name, level(1-4), parent_id(自引用), area_index, sort_order, description, system_names(JSON) |
| kg_entities | Entity | id, concept_id(FK), entity_code(unique), entity_name, entity_en_name, properties_schema(JSON), is_main_table, data_layer |
| kg_entity_relations | EntityRelation | source_entity_id, target_entity_id, relation_name, relation_category, direction, cardinality, source_field_name, target_field_name, join_expr |
| kg_entity_concept_links | EntityConceptLink | 实体-概念多对多 |
| kg_concept_relations | ConceptRelation | source_concept_id, target_concept_id, relation_type |

### 3.2 来源表族

| 表 | 说明 |
|---|---|
| kg_source_master_tables | 主数据源表(l1, l2 归属) |
| kg_source_business_tables | 业务源表(l3, l4, relL1, relL2 跨链) |
| kg_source_reference_tables | 参考数据表 |
| kg_source_field_imports | CSV 字段导入明细 |
| kg_source_table_relations | 源表间关系(relation_expr JOIN ON) |

### 3.3 建模映射

| 表 | 说明 |
|---|---|
| kg_entity_modelings | 实体物理建模(model_table_en, model_columns JSON, model_ddl) |
| kg_entity_mapping_rules | 实体-源表映射规则(field_mappings JSON) |
| kg_entity_init_data | 实体初始化数据(init_sql / init_data JSON) |

### 3.4 LLM 与配置

```python
class LLMConnectionConfig(Base):  # kg_llm_connection_configs
    name, provider, capability(chat/embedding)
    base_url, api_path, api_key(支持${ENV_VAR})
    model_name, is_default, enabled
    temperature, max_tokens, timeout_seconds
    extra_config(JSON)  # mode_profiles(quick/deep), thinking.type=disabled 等

class SmartPlannerConfig(Base):  # kg_smart_planner_configs
    planner_mode, llm_connection_id
    retrieval_mode(hybrid/keyword/vector)
    vector_model_name, vector_model_path
    keyword_weight(0.4), vector_weight(0.6), rerank_enabled
```

### 3.5 语义与标准

| 表 | 说明 |
|---|---|
| kg_semantic_embeddings | 本地语义索引(object_type, embedding JSON, content_hash) |
| kg_standard_semantic_terms | 标准语义词条(term, term_type, vector_status) |

### 3.6 指标体系

kg_metrics, kg_metric_aliases, kg_metric_atoms, kg_metric_derived, kg_metric_dim_bindings, kg_metric_versions, kg_metric_audit_logs, kg_metric_query_logs

### 3.7 技能与运行

kg_smart_skills, kg_smart_skill_workflows, kg_smart_workflow_runs, kg_smart_pipeline_runs, kg_smart_pipeline_step_runs

### 3.8 其他模型文件

- `scheduler.py`: TaskQueue, Conversation, ConversationMessage, AgentRun, RunEvent
- `skill.py`: Skill, SkillVersion, SkillExecLog, SkillApiBinding
- `auth.py`: User, Role, UserRole, ResourceACL

---

## 四、知识图谱层级设计

### 4.1 双链四层体系

```
ROOT_MD (主数据链根)
├── L1 (行业域: 客户/设备)
│   └── L2 (主数据小类: 用电客户/电能表/计量点)
│       └── L2X (实体: ENT_P_CUST / ENT_METER_MAIN)

ROOT_BZ (业务链根)
├── L3 (业务活动: 营销/工单/计量/电费结算)
│   └── L4 (业务实体: 营销活动/报修工单/抄表)
│       └── L4X (实体: BIZ_EXPAND_APPLY / ...)
```

### 4.2 层级约束

| 层级 | 含义 | 链类型 | 父级约束 | 可挂实体 |
|---|---|---|---|---|
| L1 | 行业域 | MD | 无 | 否 |
| L2 | 主数据小类 | MD | L1 | 是 → L2X |
| L3 | 业务活动 | BZ | L0 业务域 | 否 |
| L4 | 业务实体 | BZ | L3 | 是 → L4X |

### 4.3 实体编码规则

- **L2X**(主数据实体, chain_type="MD"): `ENT_P_CUST`(用电客户)、`ENT_METER_MAIN`(电能表)
- **L4X**(业务实体, chain_type="BZ"): `BIZ_EXPAND_APPLY`(业扩报装)

### 4.4 跨链关联

L4X → L2X 通过 `business_chain_spec.yaml` 定义,Neo4j 中用 `RELATES_TO` 边表达,并通过传递闭包派生 L4→L2、L4→L1 关系。

---

## 五、向量检索设计

### 5.1 三个 Qdrant Collection

| Collection | 内容 | Embedding 文本 | 维度 |
|---|---|---|---|
| entity_embeddings | 实体名向量 | entity_name / entity_code | 1024 或 2048 |
| attribute_embeddings | 属性名向量 | properties_schema.cnName | 同上 |
| tupu_standard_terms_{model} | 标准语义词条 | term + search_texts | 同上 |

> Point ID 用 `uuid.uuid5(NAMESPACE_URL, code)` 确定性生成,保证幂等。

### 5.2 向量模型注册 (VECTOR_MODEL_REGISTRY)

| key | provider | dimension | 说明 |
|---|---|---|---|
| bge-large-zh-v1.5 | local | 1024 | 本地 HuggingFace,默认 |
| bge-m3 | local | 1024 | 本地备选 |
| glm-embedding-3 | openai_compatible_embedding | 2048 | 智谱远程 API |

### 5.3 Hybrid 混合检索

```
combined = full_query_weight(0.55) × 整句向量分
         + token_weight(0.45) × 分词向量分(token_max×0.6 + token_avg×0.4)
         + exact_match_bonus(0.35) + multi_hit_bonus(0.12)
```

分词器 `tokenize_query`: jieba 分词 → 注入领域短语(100+ 电力术语) → 过滤停用词 → 同义词扩展(如"户号"→["户号","客户编号","用电户号"])。

### 5.4 三级检索协同

```
双向量召回(实体名 + 属性名)
  + Hybrid 检索(整句向量 + 分词向量 + 关键词 LIKE)
  + Neo4j 图谱邻居展开
→ 覆盖自然语言到知识图谱定位完整链路
```

---

## 六、Neo4j 图数据库

### 6.1 节点体系

- `ChainRoot`: ROOT_MD(主数据链根)、ROOT_BZ(业务链根)
- `Category`: L1/L2/L3/L4(概念节点,code = `L{level}-{id前8位}`)
- `Category:Entity`: L2X/L4X(实体节点,code = entity_code)

### 6.2 关系类型

| 关系 | 含义 |
|---|---|
| HAS_PARENT | 概念父子 + 实体→概念 |
| BELONGS_TO_CHAIN | L1/L2/L2X→ROOT_MD, L3/L4/L4X→ROOT_BZ |
| RELATES_TO | 实体间关系(从 EntityRelation 表) |
| RELATED_BY | RELATES_TO 的反向(自动派生) |

### 6.3 两条同步路径

1. **全量同步** `sync_all_to_neo4j(db)`: MySQL kg_concepts + kg_entities + kg_entity_relations → Neo4j
2. **YAML 同步** `sync_hierarchy_to_neo4j()`: business_chain_spec.yaml → L4/L4X + 跨链 + 传递闭包

---

## 七、前端架构

### 7.1 菜单与路由 (App.tsx)

无 react-router,用 `useState(currentMenu)` + `switch` 实现。4 大菜单组:

| 一级菜单 | 二级菜单 |
|---|---|
| 智能对话 | 数据问答(默认首页)、知识问答 |
| 图谱实体管理 | 图谱管理、四区建模、资产矩阵、主数据建模、业务活动建模、实体关系管理 |
| 来源表映射管理 | 来源表管理、映射、指标中心 |
| 扩展能力 | 标准语义、智能问指标、技能管理、API技能、数据源、向量管理、LLM配置、模型对话 |

### 7.2 数据问答页 (DataQueryChat.tsx)

固定 `MODE='question_data'`,会话存 localStorage key `di_sessions_data_v1`。三栏布局:

- **左栏(180px)**: 会话列表 + LLM 连接下拉
- **中栏**: 对话框(目标标签「目标:出数据」+ ConversationMessageList + Input.TextArea)
- **右栏(可收起)**: LocationTree 定位信息树

**流式占位消息模式**:
1. 发送时先 push 一个 `loading:true` 的 assistant 占位消息
2. 所有 SSE 回调精确更新「最后一个 loading 助手消息」的 payload
3. 完成后 `applyResponse` 移除占位,**保留 thinkStream(含 live_reason)** 再 push 正式消息

### 7.3 5 段输出渲染 (SummaryCard.tsx)

当 `msg.payload.confirmed` 含 L2/L2X/assembled_sql 时渲染 SummaryCard,否则降级 FinalAnswer:

| 段 | 渲染 | 数据来源 |
|---|---|---|
| 1.总结 | 蓝色文字段落 | finalAnswer 按「1.总结」「2.执行过程」切片 |
| 2.执行过程 | 灰色色块 | splitAnswer 的 process 段 |
| 3.属性清单 | antd Table(主表geekblue/联接表orange Tag) | attributes + extra_entities.attributes |
| 4.实体间关系 | 绿色色块(绿色JOIN Tag) | relations 数组或 allEntities 拼接 |
| 5.联接SQL | 淡绿色色块 + 执行按钮 | assembled_sql,Consolas 等宽字体 |

### 7.4 双 SSE 机制

**机制 A: fetch + ReadableStream**(数据问答/知识问答)
- `dataIntelligenceApi.chatStream()`: fetch POST `/chat/stream` + reader.read() 手动解析 SSE 帧
- 8 个事件回调: think / think_token / status / token / final / recommend / done / error

**机制 B: EventSource**(LLM 对话/统一 Run 协议)
- `useConversationRun.ts`: 浏览器原生 EventSource,走 runApi.getRunEventsStreamUrl(runId)
- 事件: run.started, context.prepared, block.completed, assistant.delta, step.*, message.card, run.failed, stream.end

### 7.5 ThinkStream 推理面板

Trae IDE 风格思考面板,三层结构:
1. **主组件**: 固定高度,头部旋转眼睛图标 + 三点跳动动画,折叠/展开态
2. **StepItem**: 单步骤,左侧蓝色竖线 + 圆形图标(锁定=红/活跃=蓝/其他=灰)
3. **二级展开**: `live_reason`(LLM 实时 token 累积,带闪烁光标) + `reason`(完成态) + result_status + process

策略标签映射: `vector_llm`→向量召回+LLM、`llm_classify`→LLM推理+分类、`precise_query`→精准查询、`rule_assemble`→规则拼装

---

## 八、数据问答核心流程

### 8.1 问数直通图(默认模式)

```
用户输入 "查用电客户的客户名称和联系电话"
  │
  ▼
entry_router → 判断是否已有 SQL 且要执行
  │ 否
  ▼
定位L2 (locate_l2_node)
  │ query_entity_service.build_metadata_from_system(db)
  │ → domain_catalog(L1/L2 + entities) + relation_catalog
  │ → LLM 推理锁定 L2 = "用电客户"
  │ → think_stream 推送: strategy=vector_llm/llm_classify
  ▼
定位实体属性 (locate_entity_attr_node)
  │ query_attribute_service.build_attribute_metadata_from_system(db)
  │ → scope/entity/attribute/relation catalog
  │ → 向量召回属性 → 按实体分组合并 → LLM 校验
  │ → 锁定 entity=dim_cst_elec_cons_cust, attr=cust_name
  │   + 关联 entity=dim_cst_contact, attr=contact_number
  │ → _build_sql_blueprint → _build_sql_text
  ▼
SQL拼装 (sql_assembly_node)
  │ 生成: SELECT cust_name, contact_number
  │       FROM dim_cst_elec_cons_cust
  │       LEFT JOIN dim_cst_contact ON cust_id = cust_id
  │       LIMIT 100
  ▼
答案生成 (answer_synthesizer_node)
  │ LLM 流式(chat.stream + StreamWriter)生成 5 段:
  │ 1.总结 2.执行过程 3.属性清单 4.实体间关系 5.联接SQL
  │ → SSE token 事件逐字推送前端
  ▼
推荐 (recommend_node)
  │ LLM 生成 3-5 个相似推荐问题
  ▼
done → ChatResponse(think_stream, confirmed, final_answer, recommendations)
```

### 8.2 5 段输出契约(必检)

1. **总结** — L2 主数据小类、定位实体、属性数量
2. **执行过程** — SQL 核心逻辑说明
3. **属性清单** — entity.attribute 列表
4. **实体间关系** — LEFT JOIN ON 关联条件
5. **联接SQL** — 可执行 SELECT 语句

### 8.3 SSE 事件流

```
event: think       → 新增推理步骤(去重 by task|action)
event: think_token → 步骤内 LLM token,追加到 live_reason
event: status      → 状态文本/阶段(running/done)
event: token       → 最终答案 token
event: final       → 完整 final_answer
event: recommend   → 推荐问题
event: done        → 最终 ChatResponse
event: error       → 错误
```

---

## 九、基础设施与部署

### 9.1 基础设施 (docker-compose.yml)

| 服务 | 端口 | 说明 |
|---|---|---|
| MySQL | 3306 | tupu 库,root/root,utf8mb4 |
| Neo4j | 7687(bolt)/7474(http) | tupu_neo4j_dev_pass |
| Qdrant | 6333 | 向量数据库 |

### 9.2 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| DATABASE_URL | mysql+pymysql://root:root@localhost:3306/tupu?charset=utf8mb4 | 元数据库 |
| GLM_API_KEY | — | 智谱 GLM API Key |
| NEO4J_URI | bolt://127.0.0.1:7687 | |
| NEO4J_USER / NEO4J_PASSWORD | neo4j / tupu_neo4j_dev_pass | |
| QDRANT_HOST / QDRANT_PORT | 127.0.0.1 / 6333 | |
| TUPU_VECTOR_BACKEND | qdrant | 向量后端 |
| ENABLE_AUTH | 0 | 0=关闭认证,1=开启 OIDC |
| BGE_MODEL_PATH | models/bge-large-zh-v1.5 | 本地向量模型路径 |

### 9.3 启动命令

```bash
# 后端 (端口 8100)
cd backend
python __start_8100.py
# 或: uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload

# 前端 (端口 3000)
cd frontend
npm start
# 代理 setupProxy.js: /api/* → http://127.0.0.1:8100 (SSE 路径关闭缓冲)
```

### 9.4 关键文件速查

| 用途 | 路径 |
|---|---|
| 后端入口 | backend/app/main.py |
| 主状态机 | backend/app/services/data_intelligence_graph.py |
| 秘书态 | backend/app/services/secretary_state.py |
| LLM 客户端 | backend/app/services/llm_client.py |
| 实体定位 | backend/app/services/query_entity_service.py |
| 属性定位 | backend/app/services/query_attribute_service.py |
| 向量检索 | backend/app/services/semantic_retrieval.py |
| 技能注入 | backend/app/services/skill_injections.py |
| 数据模型 | backend/app/models/base.py |
| 核心对话 API | backend/app/api/data_intelligence.py |
| 前端入口 | frontend/src/index.tsx |
| 前端路由 | frontend/src/App.tsx |
| 数据问答页 | frontend/src/pages/DataQueryChat.tsx |
| 5段输出卡 | frontend/src/components/conversation/SummaryCard.tsx |
| 推理面板 | frontend/src/components/conversation/ThinkStream.tsx |
| SSE 封装 | frontend/src/services/dataIntelligenceApi.ts |
| API 主文件 | frontend/src/services/api.ts |

---

## 十、架构设计原理总结

### 10.1 核心设计思想

1. **知识图谱本体驱动**: 4 层分类体系(L1-L4 + L2X/L4X 实体),存储 MySQL,同步 Neo4j 供图查询,同步 Qdrant 供向量召回。一个本体,三套存储,各司其职。

2. **LangGraph 状态机驱动对话**: SecretaryState 秘书态贯穿多轮对话,5 旗标(chain/entity/attribute/relation/sql_executed)跟踪进度,条件边实现自动链(定位锁完直接进 SQL 拼装,省一轮路由)。

3. **技能沙箱架构**: 技能脚本以 `data/skills/{name}/scripts/main.py` 存在,importlib 动态加载,skill_injections 注入依赖,实现技能与核心解耦。

4. **混合检索**: 关键词 + 向量加权融合,本地(bge)和远程(glm-embedding)双模型,覆盖语义+字面双维度。

5. **多数据源 SQL 执行**: DataSourceConfig 驱动,SQL 在业务库执行,fallback 到元数据库。

6. **流式体验**: 后端 LangGraph StreamWriter + SSE,前端 fetch ReadableStream + 8 事件回调,ThinkStream 实现 token 级实时推理展示。

### 10.2 已知问题与改进方向

1. 单字段 embedding 对同义不同名实体召回率低 → 拼接实体名+英文名+描述
2. 属性候选 top_k 偏少 → 增加 payload 过滤(按已锁实体过滤)
3. 召回层无阈值 → 引入 score 预过滤(<0.3 丢弃)
4. LLM JSON 解析偶发失败 → 用 with_structured_output 走 function calling
5. RAG 上下文只拼名称 → 拼接描述+数据类型+业务含义
6. smart_planner.py 已删除但 smart_skills.py 仍引用(死代码,未注册路由)

---

*本文档基于工程源码调研生成,可作为切换 IDE 后的完整上下文输入。*
