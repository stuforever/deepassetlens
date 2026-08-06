# DeepAssetLens 本地部署手册

> 本手册基于全新环境从零部署实践整理，覆盖从获取源码到前后端可用的完整流程。
> 按顺序执行每一步，并完成每步末尾的「✓ 验证」再进入下一步。

---

## 目录

1. [部署架构与组件关系](#1-部署架构与组件关系)
2. [环境依赖与端口规划](#2-环境依赖与端口规划)
3. [获取源码](#3-获取源码)
4. [配置文件](#4-配置文件)
5. [基础设施启动](#5-基础设施启动)
6. [数据库初始化](#6-数据库初始化)
7. [嵌入模型下载](#7-嵌入模型下载)
8. [后端启动](#8-后端启动)
9. [前端启动](#9-前端启动)
10. [LLM 大模型配置](#10-llm-大模型配置)
11. [健康检查与验证](#11-健康检查与验证)
12. [一键启动 / 停止脚本](#12-一键启动--停止脚本)
13. [常见故障排查](#13-常见故障排查)
14. [安全说明](#14-安全说明)
15. [项目结构](#15-项目结构)

---

## 1. 部署架构与组件关系

DeepAssetLens 由「前端 + 后端 + 7 类数据基础设施」组成。基础设施分两层：

```
┌──────────────┐   ┌──────────────────────────────────────┐
│  React 前端  │──▶│  FastAPI 后端 (28000)                │
│  (23000)     │   │  ├─ 智能问答 (deepagents)             │
└──────────────┘   │  ├─ 知识图谱 API                      │
                   │  ├─ MCP Server                        │
                   │  └─ 数据同步 (Neo4j/向量)             │
                   └───┬──────┬──────┬──────┬──────┬──────┘
                       │      │      │      │      │
            ┌──────────┘      │      │      │      └──────────┐
            ▼                 ▼      ▼      ▼                 ▼
       ┌────────┐        ┌──────┐┌─────┐┌──────┐        ┌────────┐
       │ MySQL  │        │ PG   ││Neo4j││ ES   │        │Qdrant  │
       │ 元数据 │        │业务库││ 图  ││检索  │        │ 向量库 │
       └────────┘        └──────┘└─────┘└──────┘        └────────┘
            │                                                 
            ▼  联邦查询                                       
       ┌────────┐  Redis(缓存) ← RAGFlow 栈共用              
       │ Doris  │                                             
       └────────┘                                             
```

**基础设施来源说明（重要）**：

| 组件 | 来源 | 说明 |
|------|------|------|
| MySQL 8 | RAGFlow 栈 **或** 独立部署 | tupu 主库（元数据），端口 33066 |
| Elasticsearch | RAGFlow 栈 **或** 独立部署 | 全文检索，端口 11200 |
| Redis | RAGFlow 栈 **或** 独立部署 | 缓存，端口 6379 |
| PostgreSQL 16 | `docker-compose.infra.yml` | tupu 业务库，端口 5432 |
| Neo4j 5 | `docker-compose.infra.yml` | 图数据库，端口 7474/7687 |
| Qdrant 1.12 | `docker-compose.infra.yml` | 向量库，端口 6333/6334 |
| Doris | `docker-compose.doris.yml` | 联邦查询，端口 9030/18030/18040 |
| Authentik | `docker-compose.infra.yml` | SSO/RBAC（可选），端口 9100/9143 |
| Gitea | `docker-compose.infra.yml` | 私有 Git（可选），端口 3001/2222 |

> 若你已部署 RAGFlow，可直接复用其 MySQL/ES/Redis；否则按 §5.1 独立部署这三个组件。

---

## 2. 环境依赖与端口规划

### 2.1 系统要求

- **操作系统**：Windows 10/11 + WSL2（Docker Desktop 依赖），或 Linux / macOS
- **Docker Desktop**（含 docker compose）
- **Python 3.11**（后端运行时；3.13 缺部分依赖，不推荐）
- **Node.js 18+**（前端运行时；建议 18 LTS）
- **Git**（获取源码）

### 2.2 软件安装（Windows）

```powershell
# 1. 安装 Docker Desktop（含 WSL2），从官网下载
#    https://www.docker.com/products/docker-desktop

# 2. 安装 Python 3.11（勾选 Add to PATH）
#    https://www.python.org/downloads/

# 3. 安装 Node.js 18 LTS
#    https://nodejs.org/

# 4. 验证
docker --version
python --version    # 应为 3.11.x
node --version      # 应为 v18+
```

### 2.3 端口规划

| 服务 | 宿主端口 | 用途 | 是否必需 |
|------|---------|------|---------|
| tupu 后端 | 28000 | FastAPI / Uvicorn | ✅ 必需 |
| 前端 dev server | 23000 | React dev server | ✅ 必需 |
| MySQL | 33066 | tupu 主库 | ✅ 必需 |
| PostgreSQL | 5432 | tupu 业务库 | ✅ 必需 |
| Elasticsearch | 11200 | ES 全文检索 | ✅ 必需 |
| Neo4j | 7474 / 7687 | Browser / Bolt | ✅ 必需 |
| Qdrant | 6333 / 6334 | REST / gRPC | ✅ 必需 |
| Doris FE | 9030 / 18030 | MySQL 协议 / Web UI | ⬜ 联邦查询用 |
| Doris BE | 18040 | BE 数据节点 | ⬜ 联邦查询用 |
| Redis | 6379 | 缓存 | ✅ 必需 |
| Authentik | 9100 / 9143 | SSO/RBAC | ⬜ 可选 |
| Gitea | 3001 / 2222 | Web / SSH | ⬜ 可选 |

> **端口固定，禁止修改。** 前端代码一律用相对路径，由 `setupProxy.js` 转发到 28000。
> Windows 用户注意：避开 Hyper-V 保留端口范围（1177-1876 等），本表端口均已在 10000 以上或避开保留区。

---

## 3. 获取源码

```bash
git clone https://github.com/stuforever/deepassetlens.git
cd deepassetlens
```

> 若 Git 直连超时（国内常见），可配置代理：`git config --global http.proxy http://127.0.0.1:7897`
> 或直接从 GitHub 下载 ZIP 包解压。

✓ **验证**：`ls` 应看到 `backend/`、`frontend/`、`docker-compose.infra.yml` 等目录与文件。

---

## 4. 配置文件

项目有两个配置文件，均由 `.gitignore` 忽略，**禁止提交**。从示例文件复制后填入真实值。

### 4.1 创建 `.env.infra`（项目根目录）

基础设施密码与端口。

```powershell
cp .env.infra.example .env.infra        # Linux/macOS
copy .env.infra.example .env.infra      # Windows
```

编辑 `.env.infra`，把所有 `<change_me>` 替换为真实密码。完整字段见 `.env.infra.example`，主要包括：

```ini
# Authentik（可选，不启用权限可不改）
AUTHENTIK_PG_PASSWORD=<你的密码>
AUTHENTIK_SECRET_KEY=<至少50位随机字符串>
AUTHENTIK_BOOTSTRAP_PASSWORD=<管理员密码>
AUTHENTIK_BOOTSTRAP_TOKEN=<32位随机token>

# Qdrant
QDRANT_API_KEY=<你的qdrant密钥>

# Neo4j
NEO4J_AUTH=neo4j/<你的neo4j密码>
NEO4J_PASSWORD=<同上>

# tupu 业务 PostgreSQL
TUPU_PG_USER=postgres
TUPU_PG_DB=tupu
TUPU_PG_PASSWORD=<你的pg密码>
TUPU_PG_PORT=5432
```

✓ **验证**：`cat .env.infra` 确认无 `<change_me>` 残留。

### 4.2 创建 `backend/.env`（后端目录）

后端连接各服务的凭据。

```powershell
cd backend
cp .env.example .env
```

编辑 `backend/.env`，关键字段：

```ini
# MySQL（端口 33066；密码取决于是 RAGFlow 的 MySQL 还是独立部署）
DATABASE_URL=mysql+pymysql://root:root@localhost:33066/tupu?charset=utf8mb4

# Neo4j（密码与 .env.infra 一致）
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=<你的neo4j密码>

# Qdrant（密钥与 .env.infra 一致）
QDRANT_HOST=127.0.0.1
QDRANT_PORT=6333
QDRANT_API_KEY=<你的qdrant密钥>

# Elasticsearch（密码来自 RAGFlow 部署，独立部署则自定）
ES_HOST=http://localhost:11200
ES_USER=elastic
ES_PASSWORD=<你的ES密码>

# 大模型 API（至少配一个，详见 §10）
GLM_API_KEY=
DEEPSEEK_API_KEY=

# 本地嵌入模型路径（详见 §7，可选，留空则用默认查找路径）
# BGE_MODEL_PATH=D:/gitcangku/deepassetlens/models/bge-large-zh-v1.5
```

✓ **验证**：`backend/.env` 中所有密码与 `.env.infra` 一致。

### 4.3 连接字符串速查

| 服务 | 连接字符串 |
|------|-----------|
| MySQL | `mysql+pymysql://root:root@localhost:33066/tupu` |
| PostgreSQL | `postgresql://postgres:<密码>@localhost:5432/tupu` |
| Elasticsearch | `http://elastic:<密码>@localhost:11200` |
| Doris | `mysql://root:@localhost:9030` |
| Neo4j | `bolt://localhost:7687` |

---

## 5. 基础设施启动

### 5.1 启动 MySQL / ES / Redis（RAGFlow 栈 或 独立部署）

**方案 A：已有 RAGFlow 部署**

若已部署 RAGFlow，其 MySQL(33066)/ES(11200)/Redis(6379) 可直接复用。确认容器在运行：

```powershell
docker ps | findstr "mysql elasticsearch redis"
```

**方案 B：独立部署 MySQL / ES / Redis**

若没有 RAGFlow，用以下 docker 命令独立启动（端口须与上表一致）：

```powershell
# MySQL 8（端口 33066，root/root）
docker run -d --name tupu_mysql -p 33066:3306 `
  -e MYSQL_ROOT_PASSWORD=root `
  -e MYSQL_DATABASE=tupu `
  -e MYSQL_CHARSET=utf8mb4 -e MYSQL_COLLATION=utf8mb4_unicode_ci `
  mysql:8 --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

# Elasticsearch 8（端口 11200，密码自定，此处用 infiniragflow）
docker run -d --name tupu_es -p 11200:9200 `
  -e "discovery.type=single-node" `
  -e "xpack.security.enabled=true" `
  -e "ELASTIC_PASSWORD=infiniragflow" `
  docker.elastic.co/elasticsearch/elasticsearch:8.11.0

# Redis（端口 6379）
docker run -d --name tupu_redis -p 6379:6379 redis:7-alpine
```

✓ **验证**：
```powershell
docker exec tupu_mysql mysql -uroot -proot -e "SELECT 1"       # MySQL 正常
curl -u elastic:infiniragflow http://localhost:11200            # ES 返回集群信息
docker exec tupu_redis redis-cli ping                           # PONG
```

### 5.2 启动项目专用容器（PG + Qdrant + Neo4j + Authentik + Gitea）

```powershell
cd D:\gitcangku\deepassetlens
docker compose --env-file .env.infra -f docker-compose.infra.yml up -d
```

✓ **验证**：6 个容器全部 Up（authentik_postgres / redis / server / worker / qdrant / neo4j / gitea / tupu_pg）：
```powershell
docker compose -f docker-compose.infra.yml ps --format "table {{.Name}}\t{{.Status}}"
```

### 5.3 启动 Doris（联邦查询，可选）

```powershell
# 必须用 -p tupu 项目名，否则容器名不匹配 tupu_doris_fe / tupu_doris_be
docker compose -p tupu -f docker-compose.doris.yml up -d
```

✓ **验证**：`curl http://localhost:18030/api/health` 返回 `{"status":"UP"}`。

### 5.4 重置项目数据卷（仅首次或需要清空时）

```powershell
# 仅重置项目专用卷，不影响 RAGFlow 的 MySQL/ES/Redis
docker compose -f docker-compose.infra.yml down -v
docker volume rm tupu_qdrant_data tupu_neo4j_data tupu_pg_data 2>$null
docker compose --env-file .env.infra -f docker-compose.infra.yml up -d
```

---

## 6. 数据库初始化

> 严格按以下顺序执行。每步完成后用「✓ 验证」确认再进行下一步。

### 6.1 建表（ORM 自动建表）

```powershell
cd backend
python -c "from app.core.database import engine; from app.models.base import Base; Base.metadata.create_all(engine)"
```

> `app.models.base` 中定义了 `Base`。如果 import 报错，确认 `backend/app/models/` 目录存在（开源包曾误忽略此目录）。

✓ **验证**：连接 MySQL 看到 ~73 张 `kg_*` 表：
```powershell
docker exec tupu_mysql mysql -uroot -proot -e "USE tupu; SHOW TABLES" | findstr /c:"kg_" | measure | %{$_.Count}
```

### 6.2 补建缺失种子表

开源包遗漏了部分历史/空表，需手动创建：

```powershell
cd backend
python data/init/create_missing_seed_tables.py
```

✓ **验证**：MySQL 表数量增至 ~96 张。

### 6.3 导入 MySQL 种子数据

> ⚠️ **关键：必须加 `--default-character-set=utf8mb4`，否则中文字符会全部变成 `?`（问号）。**
> 推荐用容器内 mysql 客户端，避免宿主客户端编码不一致。

```powershell
# 方式一（推荐）：通过容器内客户端导入
docker exec -i tupu_mysql mysql -uroot -proot --default-character-set=utf8mb4 tupu < backend/data/init/mysql_init_data.sql

# 方式二：宿主 mysql 客户端（同样必须加 --default-character-set=utf8mb4）
mysql --default-character-set=utf8mb4 --force -h 127.0.0.1 -P 33066 -uroot -proot tupu < backend/data/init/mysql_init_data.sql
```

> 种子 SQL 有两条重复唯一键（`kg_graph_schema.field_name`、`kg_semantic_intent_norm.word`），用 `--force` 容错导入即可，重复记录会被跳过。

✓ **验证**：中文正常显示（不是问号）：
```powershell
docker exec tupu_mysql mysql -uroot -proot --default-character-set=utf8mb4 tupu -e "SELECT name FROM kg_concepts LIMIT 3"
# 期望看到中文：如 营销域、配电域 等，而非 ???
```

### 6.4 导入 PostgreSQL 种子数据

```powershell
# 先建表（pg_schema.sql 补充了开源包缺失的 dim_ps_wbs_cost 建表语句）
docker exec -i tupu_pg psql -U postgres -d tupu < backend/data/init/pg_schema.sql
docker exec -i tupu_pg psql -U postgres -d tupu < backend/data/init/pg_init_data.sql
```

✓ **验证**：`docker exec tupu_pg psql -U postgres -d tupu -c "SELECT count(*) FROM dim_ps_wbs_cost"` 返回 5。

### 6.5 导入 Elasticsearch 索引

```powershell
cd backend
$env:ES_PASSWORD="<你的ES密码>"        # Windows
# export ES_PASSWORD="<你的ES密码>"     # Linux/macOS
python data/init/init_es.py
```

> `init_es.py` 会在导入前剔除 ES 导出文件中的只读索引元数据（`creation_date`、`uuid` 等），解决 ES 400 错误。创建 12 个 `tupu_*` 索引。

✓ **验证**：`curl -u elastic:<密码> "http://localhost:11200/_cat/indices/tupu_*?v"` 列出 12 个索引。

### 6.6 创建 Doris 外部 Catalog（联邦查询，可选）

```powershell
# 先编辑 doris_catalog_init.sql，替换 <your_es_password> 和 <your_pg_password> 占位符
mysql -h 127.0.0.1 -P 9030 -u root < backend/data/init/doris_catalog_init.sql
```

建立 `es_tupu`（ES 联邦）与 `pg_tupu`（PG 联邦）两个外部 catalog。

✓ **验证**：
```sql
mysql -h 127.0.0.1 -P 9030 -u root -e "SELECT * FROM pg_tupu.public.dim_ps_wbs_cost LIMIT 5"
mysql -h 127.0.0.1 -P 9030 -u root -e "SELECT * FROM es_tupu.default_db.tupu_dim_ps_project_def LIMIT 3"
```

### 6.7 同步 Neo4j 图谱

后端启动后（见 §8），调用同步接口从 MySQL 重建图数据库：

```powershell
curl -X POST http://localhost:28000/api/v1/sync/neo4j-all
```

或在前端「图谱管理」页面手动触发。

✓ **验证**：访问 http://localhost:7474，执行：
```cypher
MATCH (n) RETURN count(n) AS nodes;        -- 期望 25
MATCH ()-[r]->() RETURN count(r) AS rels;  -- 期望 56
```

---

## 7. 嵌入模型下载

项目使用本地 BGE 嵌入模型做向量化（实体/属性向量化、语义检索）。需自行下载模型文件（约 1.3GB/个），**不入仓库**。

```bash
mkdir -p models
# 推荐：bge-large-zh-v1.5（中文嵌入）
git clone https://huggingface.co/BAAI/bge-large-zh-v1.5 models/bge-large-zh-v1.5
# 可选：bge-m3（多语言）
git clone https://huggingface.co/BAAI/bge-m3 models/bge-m3
```

> 国内可改用镜像：`git clone https://hf-mirror.com/BAAI/bge-large-zh-v1.5 models/bge-large-zh-v1.5`

下载后在 `backend/.env` 配置路径：
```ini
BGE_MODEL_PATH=D:/gitcangku/deepassetlens/models/bge-large-zh-v1.5
```

✓ **验证**：`ls models/bge-large-zh-v1.5/model.safetensors` 文件存在。

> 若暂不下载，后端仍可启动，但向量相关功能（向量管理、语义检索）会降级。

---

## 8. 后端启动

### 8.1 安装依赖

```powershell
cd backend
python -m pip install -r requirements.txt
```

✓ **验证**：`python -c "import fastapi, sqlalchemy, qdrant_client; print('ok')"` 输出 ok。

### 8.2 启动后端（端口 28000）

```powershell
cd backend
python __start_8000.py
```

> 文件名 `__start_8000.py` 为历史遗留，**实际监听 28000 端口**。
> 启动时会自动执行 `init_db`（建表），首次启动较慢。

✓ **验证**：
```powershell
curl http://127.0.0.1:28000/openapi.json        # 返回 JSON（HTTP 200）
curl http://127.0.0.1:28000/api/v1/concepts      # 返回概念列表（HTTP 200）
```

> 后台启动方式见 §12 `start_tupu.ps1`，日志输出到 `.runtime-logs/` 目录。

---

## 9. 前端启动

### 9.1 安装依赖

```powershell
cd frontend
npm ci --no-audit --no-fund
```

✓ **验证**：`frontend/node_modules` 目录存在，`npm ls` 无报错。

### 9.2 启动前端（端口 23000）

```powershell
cd frontend
# Windows PowerShell
$env:PORT="23000"; $env:BROWSER="none"; npm start

# Linux/macOS
PORT=23000 BROWSER=none npm start
```

> 前端 dev proxy 通过 `src/setupProxy.js` 将 `/api` 请求转发到 `http://127.0.0.1:28000`。
> `BROWSER=none` 防止自动弹出浏览器。首次编译约 30-60 秒。

✓ **验证**：
```powershell
curl http://127.0.0.1:23000                       # 返回 HTML（HTTP 200）
curl http://127.0.0.1:23000/api/v1/concepts        # 经代理访问后端，HTTP 200
```

浏览器访问 http://localhost:23000 ，应看到「数据资产探查」首页。

---

## 10. LLM 大模型配置

智能问答功能依赖至少一个可用的 LLM 连接。启动前后端后，在前端配置：

1. 访问 http://localhost:23000
2. 左侧菜单 → **系统配置** → **LLM 配置**
3. 点击「新增连接」，填写：
   - 连接名称（如「智谱GLM」）
   - 提供商：智谱 GLM / DeepSeek / 通义千问 / 豆包 等
   - API Key（从对应平台获取）
   - 模型名称（如 `glm-4`、`deepseek-chat`）
4. 点击「测试」确认连接成功
5. 可在「规划器配置」中设置默认 LLM 与深度思考模式

✓ **验证**：在首页输入「统计用电客户总数」，LLM 应流式返回结果。

---

## 11. 健康检查与验证

### 11.1 健康检查脚本

```powershell
.\check_health.ps1    # 检查前后端 + Qdrant
.\check_ports.ps1     # 检查所有服务端口监听状态
.\run_check.ps1       # 依次运行上述两个脚本
```

### 11.2 手动验证清单

| 检查项 | 命令 | 期望结果 |
|--------|------|---------|
| 前端首页 | `curl http://127.0.0.1:23000` | HTTP 200 |
| 后端 OpenAPI | `curl http://127.0.0.1:28000/openapi.json` | HTTP 200 |
| 前端代理→后端 | `curl http://127.0.0.1:23000/api/v1/concepts` | HTTP 200 + JSON |
| 图谱数据 | `curl http://127.0.0.1:28000/api/v1/graph/data` | HTTP 200 + 图谱 JSON |
| 实体列表 | `curl http://127.0.0.1:28000/api/v1/entities` | HTTP 200 + 实体 JSON |
| Neo4j | 浏览器 http://localhost:7474 | 25 节点 / 56 关系 |
| Doris 联邦 | `mysql -h 127.0.0.1 -P 9030 -u root -e "SELECT * FROM pg_tupu.public.dim_ps_wbs_cost LIMIT 5"` | 返回 5 行 |

### 11.3 部署完成标志

全部满足即部署成功：
- [ ] 前端 http://localhost:23000 可访问，菜单中文正常
- [ ] 后端 http://localhost:28000/openapi.json 返回 200
- [ ] 前端经代理访问后端 API 返回数据
- [ ] LLM 配置至少一个可用连接
- [ ] Neo4j 有图谱节点（非空）

---

## 12. 一键启动 / 停止脚本

项目根目录提供 PowerShell 脚本（Windows）：

```powershell
# 启动全部（Docker 基础设施 + 后端 + 前端）
.\start_tupu.ps1

# 停止全部
.\stop_tupu.ps1

# 健康检查
.\run_check.ps1
```

- 后端通过 `backend/__start_8000.py` 启动，日志输出到 `.runtime-logs/backend-<时间戳>.log`
- 前端以 `PORT=23000 BROWSER=none npm start` 启动，日志输出到 `.runtime-logs/frontend-<时间戳>.log`

---

## 13. 常见故障排查

### 13.1 开源包遗漏 `backend/app/models/`

GitHub 仓库的 `.gitignore` 曾误忽略 `backend/app/models/`。已在 `.gitignore` 添加例外 `!backend/app/models/**`。若从 ZIP 下载，确认该目录存在且含 `base.py`。

### 13.2 MySQL 种子导入后中文全是问号 `?`

**原因**：导入时未指定 utf8mb4 编码，中文字符被转成 `?`（HEX 3F），不可逆。
**解决**：重建数据库后用 `--default-character-set=utf8mb4` 重新导入（见 §6.3）。SQL 文件本身是 UTF-8，但客户端编码会覆盖 `SET NAMES`。

### 13.3 种子 SQL 缺失 DDL

- `pg_schema.sql`：补充了 `dim_ps_wbs_cost` 建表语句，必须先于 `pg_init_data.sql` 执行。
- `create_missing_seed_tables.py`：创建遗漏的历史/空表。

### 13.4 种子 SQL 重复唯一键

`mysql_init_data.sql` 中 `kg_graph_schema.field_name` 和 `kg_semantic_intent_norm.word` 有重复唯一键。用 `--force` 容错导入，重复记录自动跳过。

### 13.5 ES 导入 400 错误

ES 导出文件含只读元数据（`creation_date`、`uuid` 等），直接导入报 400。`init_es.py` 已自动剔除这些字段。

### 13.6 Doris 容器名不匹配

Doris 必须用 `-p tupu` 项目名启动，否则容器名不是 `tupu_doris_fe` / `tupu_doris_be`：
```powershell
docker compose -p tupu -f docker-compose.doris.yml up -d
```

### 13.7 Doris PostgreSQL 联邦查询失败

需在 Doris FE 容器挂载 PostgreSQL JDBC 驱动。`docker-compose.doris.yml` 已配置挂载，驱动文件 `backend/postgresql-42.7.3.jar` 随仓库分发。

### 13.8 Qdrant 客户端版本告警

Python 端 `qdrant-client` 与服务端（v1.12.4）版本差异过大会有告警。`requirements.txt` 已限定 `qdrant-client>=1.12,<1.14`。修改后重启后端。

### 13.9 前端代理 404 / 下拉为空

前端代码禁止硬编码后端端口。所有 API 用相对路径（`/api/v1/...`），由 `setupProxy.js` 转发到 28000。若 404 或下拉空，检查 `src/setupProxy.js` 指向 `http://127.0.0.1:28000`。

### 13.10 `query_attribute_workflow_code` 列缺失

种子 SQL 引用 `kg_smart_planner_configs.query_attribute_workflow_code` 列。`backend/app/models/base.py` 与 `backend/app/core/database.py` 已补充该列定义。若仍报错，重新执行 §6.1 建表。

### 13.11 `langchain_mcp_adapters` 模块缺失

后端启动或调用智能体时报 `No module named 'langchain_mcp_adapters'`。`requirements.txt` 已含 `langchain-mcp-adapters>=0.3.0`，重新 `pip install -r requirements.txt`。

### 13.12 后端启动端口冲突

后端固定 28000。若被占用，先停掉占用进程：
```powershell
netstat -ano | findstr :28000      # 查 PID
taskkill /PID <PID> /F
```
不要改用其他端口，前端 proxy 写死 28000。

---

## 14. 安全说明

- `.env.infra` 和 `backend/.env` 含本地开发密码，**已被 `.gitignore` 忽略，禁止提交**。
- 种子数据中的 LLM API Key 已清空，需自行填入。
- 所有密码均为本地开发默认值（root/root、postgres/postgres 等），**生产环境必须全部替换**。
- Gitea 已配置禁止自助注册、必须登录才能查看。
- Neo4j、Qdrant 的认证凭据在 `.env.infra` 配置，不要使用空密码。
- Authentik 默认未启用（`ENABLE_AUTH=false`），所有请求按匿名 admin 处理；生产环境应启用并配置 RBAC。

---

## 15. 项目结构

```
deepassetlens/
├── backend/
│   ├── __start_8000.py          # 后端启动入口（端口 28000）
│   ├── .env                     # 后端连接配置（git-ignored）
│   ├── .env.example             # 后端配置示例
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py           # 加载 backend/.env
│   │   ├── main.py               # FastAPI 应用入口
│   │   ├── core/database.py      # 数据库引擎
│   │   ├── models/               # ORM 模型（base.py 定义 Base）
│   │   ├── api/                  # API 路由
│   │   └── services/             # 业务服务（deepagent/neo4j/qdrant/...）
│   ├── data/init/                # 种子数据与初始化脚本
│   │   ├── mysql_init_data.sql   # MySQL 种子（utf8mb4 导入）
│   │   ├── pg_schema.sql         # PG 建表（补充 DDL）
│   │   ├── pg_init_data.sql      # PG 种子
│   │   ├── init_es.py            # ES 索引导入
│   │   ├── doris_catalog_init.sql# Doris 外部 catalog
│   │   └── create_missing_seed_tables.py
│   ├── postgresql-42.7.3.jar     # Doris PG 联邦 JDBC 驱动
│   └── data/skills/              # 问答技能剧本（SKILL.md）
├── frontend/
│   ├── src/
│   │   ├── pages/                # 页面组件
│   │   ├── components/           # 通用组件
│   │   ├── services/             # API 层
│   │   ├── setupProxy.js         # 代理配置 -> 127.0.0.1:28000
│   │   ├── routes.tsx            # 路由配置
│   │   └── config/navigation.tsx # 侧边栏菜单
│   └── package.json
├── models/                       # 嵌入模型（git-ignored，自行下载）
├── docs/screenshots/             # 用户手册截图
├── docker-compose.infra.yml      # PG + Qdrant + Neo4j + Authentik + Gitea
├── docker-compose.doris.yml      # Doris FE + BE
├── docker-compose.yml            # 占位（已弃用）
├── .env.infra                    # 基础设施配置（git-ignored）
├── .env.infra.example            # 基础设施配置示例
├── start_tupu.ps1                # 一键启动
├── stop_tupu.ps1                 # 一键停止
├── check_health.ps1              # 健康检查
├── check_ports.ps1               # 端口检查
├── run_check.ps1                 # 串联检查
├── DEPLOYMENT_GUIDE.md           # 本手册
├── USER_MANUAL.md                # 用户手册
└── .runtime-logs/                # 运行日志（git-ignored）
```

---

> 维护：本手册随开源部署实践持续更新。遇到新问题请补充到 §13。
