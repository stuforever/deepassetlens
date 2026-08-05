# tupu 工程重构设计方案 v5（落地版）

> 文档状态：**待审核**
> 制定日期：2026-06-12
> 适用范围：tupu/backend + tupu/frontend
> 不影响：tupu/models（BGE 模型本地缓存）、3000/8000 端口的原始参考工程

---

## 0. 总则

### 0.1 重构目标

1. 引入用户登录与权限管理（面向 Agent 领域）
2. 引入图谱知识检索（承载 L0-L4 + L2X/L4X 七层结构 + L2-L3 N:N 隐式关系）
3. 升级编排框架（统一回退/HITL/Checkpoint/可视化调试）
4. 不丢现有问数准确率（85%+）的前提下，把 prompt token 从 30-80K 砍到 7-12K

### 0.2 不变量（必须守住的对外契约）

| 契约 | 说明 |
|------|------|
| **SSE 11 事件协议** | run.started / context.prepared / step.started/completed/failed / assistant.delta / tool.delta / block.completed / message.card / run.completed/failed / stream.end |
| **skill_api_bindings.target_ref 机制** | `target_ref="service:foo_service.method"` 字符串解析为 `getattr` 调用 |
| **PythonExecutor 6 全局沙箱注入** | `_db_session / _common_stop_words / _standard_dict / _nl2cypher_semantic_data` + 新增 `_current_user / _retriever` |
| **资产矩阵打点 API 方向不对称** | URL `entity_id=L4X / target_entity_id=L2X`，写库时 `source=L2X / target=L4X` |
| **kg_smart_pipeline_runs / step_runs / rewind_logs 表 schema** | 沿用，LangGraph Checkpointer 写入这些表 |
| **kg_dag_workflows / executions / step_executions 表** | scheduler_core 不动 |
| **MySQL 100% 持久化主源** | 业务真源永远在 MySQL，Neo4j/Qdrant 是检索副本 |

### 0.3 三层 Pipeline 抽象的最终边界

```
agent_run_runtime.py (统一 SSE 入口)        ← 不替换，加 auth 中间件
   ├── pipeline_runtime.py                  ← 替换为 LangGraph
   │   场景: smart_qa / smart_metric / smart_conn / smart_traceability
   │
   └── scheduler_core.py                    ← 不替换（DAG 即时执行已够）
       场景: query_entity / query_attribute
```

---

## 1. 技术栈 v5 锁定

| 层 | 组件 | 版本 | 部署形态 |
|----|------|------|----------|
| 认证 | **Authentik** | 2025.10 LTS | 单机 Docker（外接 PostgreSQL 容器） |
| 图存储 | **Neo4j Community** | 5.24 | 单机 Docker |
| 向量库 | **Qdrant** | 1.12 | 单机 Docker |
| 嵌入模型 | bge-large-zh-v1.5 | 沿用 | 本地文件，无需服务化 |
| 编排 | **LangGraph** | 0.2.50+ | Python 库，进程内 |
| 调试器 | **LangGraph Studio** | 最新 | 桌面应用（开发环境用） |
| 后端框架 | FastAPI | 沿用现有 | 进程内 |
| ORM | SQLAlchemy | 沿用 | 进程内 |
| Schema 校验 | **Pydantic v2.9+** | 升级 | 阻塞前置 |
| 前端框架 | React + AntD 4.x + G6 5 | 沿用 | 静态资源 |
| HTTP 客户端 | axios | 沿用 + 加 interceptor | - |

### 1.1 Python 依赖增量

```
# 新增到 tupu/backend/requirements.txt
langgraph==0.2.50
langgraph-checkpoint==2.0.0
langchain-core==0.3.30      # langgraph 强依赖，最小化使用
qdrant-client==1.12.1
neo4j==5.24.0
python-keycloak==4.5.0      # 也兼容 Authentik 的 OIDC（OIDC 是标准协议）
authlib==1.3.2              # JWT 验签
httpx==0.27.2               # python-keycloak/authlib 底层

# Pydantic v1 → v2 升级
pydantic==2.9.2
pydantic-settings==2.6.1
```

---

## 2. 部署架构与 docker-compose

### 2.1 部署拓扑

```
┌──────────────── 本机进程（开发态）────────────────┐
│   tupu/backend  uvicorn :8000                  │
│   tupu/frontend npm start :3000                │
└──────────────────────┬─────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────┐
│              Docker（5 个容器）                          │
│                                                         │
│  ┌────────────────┐  ┌────────────────┐               │
│  │  authentik     │  │  authentik-pg  │               │
│  │  :9000 (web)   │←→│  :5432 (内网)  │               │
│  │  :9443 (https) │  └────────────────┘               │
│  └────────────────┘                                    │
│                                                         │
│  ┌────────────────┐  ┌────────────────┐               │
│  │  neo4j         │  │  qdrant        │               │
│  │  :7474 (web)   │  │  :6333 (api)   │               │
│  │  :7687 (bolt)  │  │  :6334 (grpc)  │               │
│  └────────────────┘  └────────────────┘               │
│                                                         │
│  ┌────────────────┐                                    │
│  │  authentik-redis│                                   │
│  │  :6379 (内网)  │                                    │
│  └────────────────┘                                    │
└─────────────────────────────────────────────────────────┘

外部：宿主机 MySQL 3306 (tupu 业务真源)
```

### 2.2 完整 docker-compose.yml（替换现有空文件）

```yaml
# tupu/docker-compose.yml
version: "3.9"

services:
  # ============ Authentik 认证 ============
  authentik-pg:
    image: postgres:16-alpine
    container_name: tupu-authentik-pg
    restart: unless-stopped
    environment:
      POSTGRES_PASSWORD: ${AUTHENTIK_PG_PASS:-authentik}
      POSTGRES_USER: authentik
      POSTGRES_DB: authentik
    volumes:
      - authentik_pg_data:/var/lib/postgresql/data
    networks:
      - tupu-net

  authentik-redis:
    image: redis:7-alpine
    container_name: tupu-authentik-redis
    restart: unless-stopped
    networks:
      - tupu-net

  authentik-server:
    image: ghcr.io/goauthentik/server:2025.10
    container_name: tupu-authentik
    restart: unless-stopped
    command: server
    environment:
      AUTHENTIK_REDIS__HOST: authentik-redis
      AUTHENTIK_POSTGRESQL__HOST: authentik-pg
      AUTHENTIK_POSTGRESQL__USER: authentik
      AUTHENTIK_POSTGRESQL__NAME: authentik
      AUTHENTIK_POSTGRESQL__PASSWORD: ${AUTHENTIK_PG_PASS:-authentik}
      AUTHENTIK_SECRET_KEY: ${AUTHENTIK_SECRET_KEY:-CHANGE_ME_50_RANDOM_CHARS}
    volumes:
      - authentik_media:/media
      - authentik_templates:/templates
    ports:
      - "9000:9000"
      - "9443:9443"
    depends_on:
      - authentik-pg
      - authentik-redis
    networks:
      - tupu-net

  authentik-worker:
    image: ghcr.io/goauthentik/server:2025.10
    container_name: tupu-authentik-worker
    restart: unless-stopped
    command: worker
    environment:
      AUTHENTIK_REDIS__HOST: authentik-redis
      AUTHENTIK_POSTGRESQL__HOST: authentik-pg
      AUTHENTIK_POSTGRESQL__USER: authentik
      AUTHENTIK_POSTGRESQL__NAME: authentik
      AUTHENTIK_POSTGRESQL__PASSWORD: ${AUTHENTIK_PG_PASS:-authentik}
      AUTHENTIK_SECRET_KEY: ${AUTHENTIK_SECRET_KEY:-CHANGE_ME_50_RANDOM_CHARS}
    volumes:
      - authentik_media:/media
      - authentik_templates:/templates
      - authentik_certs:/certs
    depends_on:
      - authentik-pg
      - authentik-redis
    networks:
      - tupu-net

  # ============ Neo4j 图存储 ============
  neo4j:
    image: neo4j:5.24-community
    container_name: tupu-neo4j
    restart: unless-stopped
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASS:-tupu_neo4j_pass}
      NEO4J_PLUGINS: '["apoc"]'
      NEO4J_dbms_security_procedures_unrestricted: apoc.*
      NEO4J_server_memory_heap_max__size: 2G
      NEO4J_server_memory_pagecache_size: 1G
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_plugins:/plugins
    ports:
      - "7474:7474"
      - "7687:7687"
    networks:
      - tupu-net

  # ============ Qdrant 向量库 ============
  qdrant:
    image: qdrant/qdrant:v1.12.1
    container_name: tupu-qdrant
    restart: unless-stopped
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"
    networks:
      - tupu-net

volumes:
  authentik_pg_data:
  authentik_media:
  authentik_templates:
  authentik_certs:
  neo4j_data:
  neo4j_logs:
  neo4j_plugins:
  qdrant_data:

networks:
  tupu-net:
    driver: bridge
```

### 2.3 .env 模板

```bash
# tupu/.env
AUTHENTIK_SECRET_KEY=<生成 50 个随机字符>
AUTHENTIK_PG_PASS=<8 位以上密码>
NEO4J_PASS=<8 位以上密码>

# tupu 后端读取
TUPU_AUTHENTIK_URL=http://localhost:9000
TUPU_AUTHENTIK_REALM=tupu
TUPU_AUTHENTIK_CLIENT_ID=tupu-backend
TUPU_AUTHENTIK_CLIENT_SECRET=<在 Authentik 创建 Application 后获得>

TUPU_NEO4J_URI=bolt://localhost:7687
TUPU_NEO4J_USER=neo4j
TUPU_NEO4J_PASS=${NEO4J_PASS}

TUPU_QDRANT_URL=http://localhost:6333
TUPU_QDRANT_API_KEY=                      # 单机版可空

TUPU_BGE_MODEL_PATH=./models/bge-large-zh-v1.5
```

---

## 3. 数据模型设计

### 3.1 Neo4j Schema

#### 节点类型

```cypher
// L0 业务域
(:Concept:L0 {id, name, area_index, system_names, created_at})

// L1 主数据大类
(:Concept:L1 {id, name, parent_id, sort_order})

// L2 主数据小类
(:Concept:L2 {id, name, parent_id, sort_order})

// L3 业务流程
(:Concept:L3 {id, name, parent_id, system_names, sort_order})

// L4 业务活动
(:Concept:L4 {id, name, parent_id, sort_order})

// L2X 主数据实体（kg_entities.concept_id 指向 L2）
(:Entity:L2X {
  id, entity_code, entity_name, entity_en_name,
  entity_explanation, properties_schema, is_main_table,
  data_layer, sort_order, concept_id
})

// L4X 业务活动实体（kg_entities.concept_id 指向 L4）
(:Entity:L4X { ... 同 L2X 结构 ... })

// 属性节点（用于属性级向量召回）
(:Attribute {
  id, entity_id, attr_name, attr_en_name,
  attr_type, attr_description
})
```

#### 关系类型

```cypher
// 静态层级归属（来自 kg_concepts.parent_id）
(L1)-[:B