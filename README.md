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
