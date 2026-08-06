# DeepAssetLens · 资产深度探查平台

> 电力行业数据资产知识图谱问答平台 —— 用自然语言探查主数据实体、业务活动与关联关系。

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

## 项目简介

DeepAssetLens 将企业数据资产组织为**知识图谱**（L1 业务域 → L2 主数据分类 → 实体 → 字段 → 关系），用户用自然语言提问，平台自动路由到对应技能（SQL 查询 / 概念解释 / 图谱浏览 / 血缘追溯），通过 Doris 联邦查询 / Neo4j 图查询 / ES 检索取数并生成结构化回答。

### 核心能力

- **智能问答**：ChatGPT 式对话界面，自动识别意图、路由技能、拼装 SQL、取数作答
- **知识图谱建模**：四区建模（业务域 / 主数据 / 业务活动 / 字段），可视化图谱管理
- **数据资产矩阵**：主数据实体 + 业务活动 + 来源表 + 映射配置一体化管理
- **向量检索**：实体/属性向量库 + 自定义知识库（RAG），支持模糊召回
- **多源联邦查询**：Doris catalog 跨 MySQL / PostgreSQL / ES 联邦取数
- **技能管理**：可编排的问答技能（locate / explore / sql-exec / trace-lineage 等）

## 项目特色

### 1. 本体建模：严格的主数据/业务活动双链四层体系

不是简单的表/字段堆砌，而是严格按业务语义建模，有明确的层级关系与上下文：

- **双链四层**：主数据链（L1 行业域 -> L2 主数据小类 -> L2X 实体）+ 业务链（L3 业务活动 -> L4 业务实体 -> L4X 实体），L4X 通过 `business_chain_spec` 跨链关联到 L2X
- **层级约束**：每层有父级约束（L2 必须挂 L1、L4 必须挂 L3），实体只能挂在 L2/L4
- **一个本体三套存储**：MySQL 存元数据、Neo4j 供图查询、Qdrant 供向量召回，各司其职

### 2. 真正的图检索：图节点定位 -> 子图内容 -> 向量化保底

不是单纯靠向量相似度匹配，而是图谱结构优先、向量化兜底的分层检索：

- **第一段 · 图节点定位**：通过 Neo4j 图谱邻居展开，先定位到业务域/实体节点（L2/L2X）
- **第二段 · 子图内容定位**：在已锁实体下定位属性、关系（L4/L4X 及跨链关联）
- **第三段 · 向量化保底**：双向量召回（实体名 + 属性名）+ Hybrid 检索（整句向量 + 分词向量 + 关键词 LIKE），覆盖语义与字面双维度

### 3. 本体对象虚拟化连接：跨源计算 + 跨API计算

知识图谱里的实体不必绑定单一物理表，通过 `source_mode` 支持三种取数来源，真正实现一体化数据探查：

| 来源 | 引擎 | 能力 |
|------|------|------|
| 落地实体表映射 | PostgreSQL 直查 | 已落库表的字段级血缘治理 |
| 虚拟SQL映射 | **Doris 联邦** | **跨源计算**：jdbc catalog 跨 MySQL/PG/ES 等库联邦 JOIN（3 段命名） |
| 多源API映射 | **DuckDB 内存联邦** | **跨API计算**：多 API 端点 -> DataFrame -> 内存库联邦 JOIN/聚合 |

- **跨源计算**：一段 `integration_sql` 用 `catalog.db.table` 命名，由 Doris 跨 catalog JOIN，filters 经 sqlglot 下推，并支持 LLM AI 校验改写
- **跨API计算**：每个 API 端点定义虚拟表名，`pseudo_sql` 引用多虚拟表做 JOIN，DuckDB 内存库执行联邦，可 ATTACH PG/Doris 做更广整合

### 4. LangGraph 状态机驱动对话

- `SecretaryState` 秘书态贯穿多轮对话，5 旗标跟踪进度（chain/entity/attribute/relation/sql_executed）
- 8 任务节点状态机：实体定位 -> 属性定位 -> SQL 拼装 -> SQL 执行 -> 答案生成 -> 推荐
- 条件边自动链：定位锁完直接进 SQL 拼装，省一轮路由

### 5. 流式体验与可解释推理

- 后端 LangGraph StreamWriter + SSE，前端 fetch ReadableStream + 8 事件回调
- ThinkStream 推理面板：token 级实时展示思考过程（策略标签：向量召回+LLM / LLM推理+分类 / 精准查询 / 规则拼装）
- 5 段式结构化答案：总结 / 执行过程 / 属性清单 / 实体间关系 / 联接SQL

### 6. 技能沙箱与 MCP 集成

- 技能脚本以 `data/skills/{name}/scripts/main.py` 存在，importlib 动态加载 + 依赖注入，与核心解耦
- MCP Server 暴露 16 个工具，集成 deepagents 框架，支持技能编排与外部工具调用

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI · Uvicorn · SQLAlchemy · LangGraph · deepagents · MCP |
| 前端 | React · TypeScript · Ant Design · Zustand |
| 图数据库 | Neo4j |
| 关系库 | MySQL（元数据）· PostgreSQL（业务数据）|
| 搜索 | Elasticsearch |
| 向量库 | Qdrant |
| 联邦查询 | Apache Doris |
| 基础设施 | Docker Compose |

## 架构概览

```
┌──────────────┐   ┌──────────────────────────────────────┐
│  React 前端  │──▶│  FastAPI 后端 (28000)                │
│  (23000)     │   │  ├─ freeplan 智能问答 (deepagents)   │
└──────────────┘   │  ├─ 知识图谱 API (kg_api)            │
                   │  ├─ MCP Server (16 工具)             │
                   │  └─ 数据同步 (Neo4j/向量)            │
                   └───┬──────┬──────┬──────┬──────┬─────┘
                       │      │      │      │      │
                    ┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐┌──▼──┐
                    │MySQL││ PG  ││Neo4j││ ES  ││Qdrant│
                    └─────┘└─────┘└─────┘└─────┘└──────┘
                                        │
                                   ┌────▼────┐
                                   │  Doris  │ (联邦查询 catalog)
                                   └─────────┘
```

## 快速启动

### 前置要求

- Docker Desktop + Docker Compose
- Python 3.10+
- Node.js 18+
- 本地嵌入模型：`bge-large-zh-v1.5`（[HuggingFace](https://huggingface.co/BAAI/bge-large-zh-v1.5) 下载到 `models/bge-large-zh-v1.5/`）

### 1. 启动基础设施

```bash
# 配置基础设施密码（必填，docker-compose 强制要求）
cp .env.infra.example .env.infra
# 编辑 .env.infra 填入自定义密码

# 启动 MySQL / PG / Neo4j / ES / Qdrant / Doris / Redis
docker compose -f docker-compose.infra.yml up -d
```

### 2. 启动后端

```bash
cd backend
cp .env.example .env
# 编辑 .env 填入数据库连接、LLM API key 等

pip install -r requirements.txt
python __start_8000.py   # 启动在 28000 端口
```

### 3. 启动前端

```bash
cd frontend
npm install
npm start   # 启动在 23000 端口，proxy 转发到 28000
```

### 4. 配置大模型

启动后访问前端 → 系统配置 → LLM 配置，添加你的大模型连接（GLM / DeepSeek / 通义千问 / 豆包等），填入 API key。问答功能依赖至少一个可用的 LLM 连接。

## 环境变量

| 文件 | 用途 | 说明 |
|---|---|---|
| `.env.infra` | 基础设施密码 | Docker 容器密码（MySQL/PG/Neo4j/Qdrant/Authentik），见 `.env.infra.example` |
| `backend/.env` | 后端应用配置 | 数据库连接、LLM key、模型路径，见 `backend/.env.example` |

> ⚠️ `.env*` 文件已被 `.gitignore` 忽略，不会入库。请勿提交真实密码。

## 嵌入模型

项目使用本地 BGE 嵌入模型做向量化，需自行下载：

```bash
mkdir -p models
# 下载 bge-large-zh-v1.5
git clone https://huggingface.co/BAAI/bge-large-zh-v1.5 models/bge-large-zh-v1.5
# 可选：bge-m3（多语言）
git clone https://huggingface.co/BAAI/bge-m3 models/bge-m3
```

模型文件较大（~1.3GB/个），已被 `.gitignore` 忽略，不入仓库。

## 项目结构

```
├── backend/              # FastAPI 后端
│   ├── app/
│   │   ├── api/          # API 路由（kg_api, data_intelligence, data_sync, ...）
│   │   ├── services/     # 业务服务（deepagent, doris_engine, neo4j, qdrant, ...）
│   │   ├── models/       # SQLAlchemy 数据模型
│   │   └── core/         # 数据库、认证、配置
│   ├── data/skills/      # 问答技能剧本（SKILL.md）
│   └── requirements.txt
├── frontend/             # React 前端
│   └── src/
│       ├── pages/        # 页面（FreePlanChat, GraphManager, ...）
│       ├── components/   # 组件
│       └── services/     # API 层
├── docker-compose.infra.yml  # 基础设施编排
├── .env.infra.example       # 基础设施密码示例
└── LICENSE                  # Apache 2.0
```

## License

[Apache License 2.0](LICENSE)

## 致谢

- [BAAI/bge-large-zh-v1.5](https://huggingface.co/BAAI/bge-large-zh-v1.5) 嵌入模型
- [deepagents](https://github.com/langchain-ai/deepagents) Agent 框架
- [Apache Doris](https://doris.apache.org/) 联邦查询引擎
