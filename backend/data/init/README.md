# 数据库初始化脚本

本目录提供 DeepAssetLens 开源版的数据库种子数据与初始化脚本，用于在全新部署后还原项目域（电力工程项目管理）的演示数据与配置。

## 初始化顺序

按以下步骤依次执行，缺一不可：

### 1. 建表（应用层 ORM）

```bash
cd backend
python -c "from app.core.database import engine; from app.models import Base; Base.metadata.create_all(engine)"
```

或启动后端时由 `init_db` 自动建表。`init_db.py` 仅写入默认技能类型，不写概念/实体，业务种子数据由本目录脚本提供。

### 2. 导入 MySQL 种子数据

```bash
mysql -h 127.0.0.1 -P 33066 -u root -p tupu < mysql_init_data.sql
```

包含：项目域概念层级（L0 项目域 → L1 项目主数据 → L2 实体）、6 个实体定义（WBS 元素/活动物料组件/网络/网络活动/里程碑/项目定义）、Doris 查询配置、LLM 连接记录（api_key 已清空，需自行填入）、技能、指标、API 端点等。

> 数据量约 24MB / 84 张 INSERT，无真实 API Key、无敏感凭据。

### 3. 导入 PostgreSQL 种子数据

```bash
psql -h 127.0.0.1 -p 5432 -U postgres -d tupu -f pg_init_data.sql
```

包含：`dim_ps_wbs_cost`（项目 WBS 成本表）少量演示数据。

> PG 表结构需由 `create_all` 或 `dwd_ps` 建表脚本先行创建（本脚本仅含数据）。

### 4. 导入 Elasticsearch 索引

```bash
cd backend
ES_PASSWORD=<your_es_password> python data/init/init_es.py
```

创建 12 个 `tupu_dim_ps_*` 索引并批量导入文档（项目定义、WBS 元素、网络、活动、里程碑、状态、预算、成本等）。

### 5. 创建 Doris 外部 Catalog

```bash
mysql -h 127.0.0.1 -P 9030 -u root < doris_catalog_init.sql
```

> 执行前请修改脚本中的 `<your_es_password>` 与 `<your_pg_password>` 占位。

建立 `es_tupu`（ES 联邦查询）与 `pg_tupu`（PG 联邦查询）两个外部 catalog，使 Doris 可跨源查询 ES 与 PG 数据。

### 6. 同步 Neo4j 图谱

启动后端后，调用同步接口从 MySQL 重建图数据库：

```bash
curl -X POST http://localhost:28000/api/v1/sync/neo4j-all
```

或在前端「图谱同步」页面触发。Neo4j 节点（Category/Entity）与关系将按 MySQL 中的项目域配置自动生成。

## 文件清单

| 文件 | 说明 |
|------|------|
| `mysql_init_data.sql` | MySQL 种子数据（配置 + 演示数据，无 API Key） |
| `pg_init_data.sql` | PostgreSQL 演示数据（dim_ps_wbs_cost） |
| `es/` | ES 索引 mapping + data（12 索引 × 2 文件） |
| `init_es.py` | ES 索引导入脚本 |
| `doris_catalog_init.sql` | Doris 外部 catalog 建立脚本 |

## 验证

完成上述步骤后：

- 前端侧栏应只显示「项目域」及其下 6 个实体
- 「智能查询」中输入「查询项目定义主数据」应能正常路由到 Doris 并返回结果
- Neo4j Browser（http://localhost:7474）可见 Category 与 Entity 节点
