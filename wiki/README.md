# Tupu 项目 Code Wiki

> 版本：2026-06-13（v5 重构后）
> 仓库路径：`d:\gitcangku\DB-GPT\tupu`
> 文档目的：面向开发者 & 维护者，提供项目整体架构、模块职责、关键类/函数、依赖关系与运行方式的完整索引

---

## 目录

| # | 文档 | 内容 |
|---|------|------|
| 1 | [01-项目总览](./01-项目总览.md) | 项目目标、技术栈、目录结构、运行端口一览 |
| 2 | [02-系统架构](./02-系统架构.md) | 整体分层、模块关系、数据流、关键不变量 |
| 3 | [03-后端模块详解](./03-后端模块详解.md) | backend/app 各包职责、关键类与函数 |
| 4 | [04-数据模型与数据库](./04-数据模型与数据库.md) | ORM 模型表结构、迁移与初始数据 |
| 5 | [05-认证与权限系统](./05-认证与权限系统.md) | Authentik OIDC 集成、RBAC、资源级 ACL |
| 6 | [06-技能与执行引擎](./06-技能与执行引擎.md) | 技能模型、文件系统存储、ExecutionEngine、沙箱 |
| 7 | [07-工作流与编排](./07-工作流与编排.md) | SchedulerCore、DAG 调度、LangGraph 集成、HITL |
| 8 | [08-智能问数与图谱](./08-智能问数与图谱.md) | SmartQA/Metric/Entity/Attribute/Connection 业务流 |
| 9 | [09-前端架构与组件](./09-前端架构与组件.md) | React 路由、AntD 页面、状态管理、OIDC 守卫 |
| 10 | [10-基础设施与部署](./10-基础设施与部署.md) | Docker 编排、LangGraph Studio、环境变量、构建 |
| 11 | [11-开发指南与测试](./11-开发指南与测试.md) | 启动顺序、常用命令、调试、回归脚本 |
| 12 | [12-API 接口索引](./12-API接口索引.md) | v1/v2 REST 路由总览 |

---

## 项目速查

| 维度 | 信息 |
|------|------|
| 项目名 | tupu（数据智能分析组件 / Data Intelligence Analysis Components） |
| 后端 | FastAPI + SQLAlchemy + PyMySQL + LangGraph 0.2.50+ |
| 前端 | React 18 + AntD 5 + G6 + Zustand + Monaco Editor |
| 主存储 | MySQL 5.7+/8.0（外部 3306，100% 业务真源） |
| 图存储 | Neo4j 5.24（Docker，按需启用） |
| 向量库 | Qdrant 1.12（Docker，按需启用） |
| 鉴权 | Authentik 2025.10 OIDC（Docker，可选开关 `ENABLE_AUTH`） |
| 嵌入模型 | bge-large-zh-v1.5（本地文件） |
| 端口 | backend 8000/8100、frontend 3000、LangGraph Studio 2024、Authentik 9100/9143、Qdrant 6333/6334、Neo4j 7474/7687 |
| 文档体系 | `OPERATION_MANUAL.md`（运维手册）、`docs/*.md`（设计稿）、`wiki/*.md`（本仓库代码 Wiki） |

---

## 阅读建议

- **新加入项目**：先看 `01-项目总览` + `02-系统架构`，再按角色选读：
  - 后端开发 → `03` `04` `05` `06` `07`
  - 前端开发 → `09` `05`
  - 算法/语义 → `08` `04`
  - 运维/DevOps → `10` `11`
- **扩展新能力**：参考 `08-智能问数与图谱` 的 pipeline 模式，参考 `06-技能与执行引擎` 的技能包约定
- **调试 LangGraph 化能力**：参考 `07-工作流与编排` §LangGraph 集成 + `10-基础设施与部署` §LangGraph Studio

