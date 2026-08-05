# 12 · API 接口索引

> 全部接口前缀 `/api/v1` 或 `/api/v2`，按业务域分组列出。
> 完整定义见 [`backend/app/api/`](../backend/app/api/) 各 router 文件。
> OpenAPI 在线文档：启动 backend 后访问 http://localhost:8100/docs

## 12.1 总览

| 业务域 | Router 文件 | 端点数 | 前缀 |
|--------|-------------|--------|------|
| 认证授权 | `api/auth.py` | 6 | `/api/v1/auth` |
| 图谱/概念/实体/关系 | `api/concept.py` | 30+ | `/api/v1` |
| 来源表/映射 | `api/source_tables.py` + `api/mapping.py` | 12 | `/api/v1` |
| 文件上传 | `api/upload.py` | 1 | `/api/v1` |
| LLM 配置 | `api/llm_admin.py` | 7 | `/api/v1` |
| 标准语义 | `api/standard_semantic.py` | 7 | `/api/v1` |
| 数据源 | `api/data_source.py` | 5 | `/api/v1` |
| 智能联接/溯源 | `api/smart_core.py` | 8 | `/api/v1` |
| 智能应用 | `api/smart_apps.py` | 5 | `/api/v1` |
| 智能问数 | `api/smart_apps.py` (smart_qa) | 5 | `/api/v1` |
| 智能问指标 | `api/smart_metric.py` | 5 | `/api/v1` |
| 智能问实体 | `api/query_entity.py` | 5 | `/api/v1` |
| 智能问属性 | `api/query_attribute.py` | 5 + 6(LangGraph) | `/api/v1` |
| 元数据 | `api/metadata.py` | 3 | `/api/v1` |
| Pipeline | `api/smart_pipeline.py` | 8 | `/api/v1` |
| 指标中心 | `api/metric_center.py` | 20+ | `/api/v1` |
| 实体关系 | `api/entity_relation_manage.py` | 4 | `/api/v1` |
| 智能对话 | `api/chat.py` | 2 | `/api/v1` |
| 工作流 | `api/workflows.py` | 18 | `/api/v1` |
| 运行历史 | `api/runs.py` | 3 | `/api/v1` |
| 技能 V2 | `api/v2_skills.py` | 57 | `/api/v2` |
| **合计** | | **~250** | |

## 12.2 认证授权（auth.py）

| Method | Path | 说明 |
|--------|------|------|
| GET    | `/api/v1/auth/config` | OIDC 公开配置 |
| GET    | `/api/v1/auth/me` | 当前用户信息（可选 token） |
| GET    | `/api/v1/auth/users` | 用户列表（admin） |
| POST   | `/api/v1/auth/dev-login` | 开发态伪登录 |
| POST   | `/api/v1/auth/grant` | 创建资源 ACL |
| DELETE | `/api/v1/auth/grant/{id}` | 删除资源 ACL |

## 12.3 图谱/概念/实体

### 12.3.1 概念与实体（concept.py）

```http
GET    /api/v1/concepts
POST   /api/v1/concepts
PUT    /api/v1/concepts/{id}
DELETE /api/v1/concepts/{id}
POST   /api/v1/concepts/bootstrap-template

GET    /api/v1/entities
POST   /api/v1/entities
PUT    /api/v1/entities/{id}
DELETE /api/v1/entities/{id}
POST   /api/v1/entities/explanation-suggestions
POST   /api/v1/entities/en-name-autofill
GET    /api/v1/entities/en-name-integrity-check
POST   /api/v1/entities/{id}/matrix/toggle

GET    /api/v1/entity-relations
POST   /api/v1/entity-relations
PUT    /api/v1/entity-relations/{id}
DELETE /api/v1/entity-relations/{id}

POST   /api/v1/sync
GET    /api/v1/graph/data
GET    /api/v1/graph/matrix
POST   /api/v1/export/excel
POST   /api/v1/import/excel
```

## 12.4 来源表/映射

```http
# source_tables.py
GET    /api/v1/source-master-tables
POST   /api/v1/source-master-tables
PUT    /api/v1/source-master-tables/{id}
DELETE /api/v1/source-master-tables/{id}
# (同样形式 for business-tables / reference-tables / tables / table-relations / field-imports)

# mapping.py
GET    /api/v1/mappings
POST   /api/v1/mappings
PUT    /api/v1/mappings/{id}
DELETE /api/v1/mappings/{id}
POST   /api/v1/mappings/{id}/test
```

## 12.5 智能问数（Query 系列）

```http
# query_entity.py
GET    /api/v1/query-entity/example-metadata
GET    /api/v1/query-entity/system-metadata
POST   /api/v1/query-entity/map

# query_attribute.py
GET    /api/v1/query-attribute/example-metadata
GET    /api/v1/query-attribute/system-metadata
POST   /api/v1/query-attribute/map
# LangGraph 化（6 个）
POST   /api/v1/query-attribute/langgraph/run
GET    /api/v1/query-attribute/langgraph/threads/{thread_id}/state
POST   /api/v1/query-attribute/langgraph/threads/{thread_id}/resume
POST   /api/v1/query-attribute/langgraph/threads/{thread_id}/rewind
GET    /api/v1/query-attribute/langgraph/threads/{thread_id}/history
DELETE /api/v1/query-attribute/langgraph/threads/{thread_id}

# smart_metric.py
GET    /api/v1/smart-metric/example
GET    /api/v1/smart-metric/system
POST   /api/v1/smart-metric/query
GET    /api/v1/smart-metric/result/{id}
GET    /api/v1/smart-metric/logs

# smart_apps.py（智能联接 / 智能溯源 / 智能问数）
GET    /api/v1/smart-connection/example
GET    /api/v1/smart-connection/system
POST   /api/v1/smart-connection/run
GET    /api/v1/smart-connection/result/{id}
GET    /api/v1/smart-connection/logs
```

## 12.6 智能应用 Pipeline（smart_pipeline.py）

```http
GET    /api/v1/smart-pipeline/runs
GET    /api/v1/smart-pipeline/runs/{id}
GET    /api/v1/smart-pipeline/runs/{id}/steps
GET    /api/v1/smart-pipeline/runs/{id}/rewinds
POST   /api/v1/smart-pipeline/runs
DELETE /api/v1/smart-pipeline/runs/{id}
POST   /api/v1/smart-pipeline/runs/{id}/rewind
```

## 12.7 指标中心（metric_center.py，~20 端点）

```http
GET    /api/v1/metrics
POST   /api/v1/metrics
PUT    /api/v1/metrics/{id}
DELETE /api/v1/metrics/{id}
GET    /api/v1/metrics/{id}
POST   /api/v1/metrics/{id}/publish
POST   /api/v1/metrics/{id}/unpublish

# 度量原子
GET    /api/v1/metrics/{id}/atoms
POST   /api/v1/metrics/{id}/atoms
PUT    /api/v1/metrics/atoms/{atom_id}
DELETE /api/v1/metrics/atoms/{atom_id}

# 衍生 / 依赖 / 维度绑定 / 白名单
GET    /api/v1/metrics/{id}/derived
POST   /api/v1/metrics/{id}/derived
GET    /api/v1/metrics/{id}/deps
POST   /api/v1/metrics/{id}/deps
GET    /api/v1/metrics/{id}/dim-bindings
POST   /api/v1/metrics/{id}/dim-bindings
GET    /api/v1/metrics/{id}/filter-whitelist
POST   /api/v1/metrics/{id}/filter-whitelist

# 版本 / 审计 / 统计 / 日志
GET    /api/v1/metrics/{id}/versions
POST   /api/v1/metrics/{id}/versions
GET    /api/v1/metrics/{id}/audit-logs
GET    /api/v1/metrics/{id}/usage-stats
GET    /api/v1/metrics/{id}/query-logs
```

## 12.8 标准语义（standard_semantic.py）

```http
GET    /api/v1/standard-semantic/terms
POST   /api/v1/standard-semantic/terms
PUT    /api/v1/standard-semantic/terms/{id}
DELETE /api/v1/standard-semantic/terms/{id}
POST   /api/v1/standard-semantic/vector-tasks
GET    /api/v1/standard-semantic/vector-tasks
```

## 12.9 LLM / 数据源 / 智能对话

```http
# llm_admin.py
GET    /api/v1/llm-configs
POST   /api/v1/llm-configs
PUT    /api/v1/llm-configs/{id}
DELETE /api/v1/llm-configs/{id}
POST   /api/v1/llm-configs/{id}/test

# data_source.py
GET    /api/v1/data-sources
POST   /api/v1/data-sources
PUT    /api/v1/data-sources/{id}
DELETE /api/v1/data-sources/{id}
POST   /api/v1/data-sources/{id}/test

# chat.py
POST   /api/v1/chat
POST   /api/v1/chat/stream
```

## 12.10 元数据（metadata.py）

```http
GET    /api/v1/metadata
POST   /api/v1/metadata/search
GET    /api/v1/metadata/{entity_id}
```

## 12.11 工作流（workflows.py）

```http
GET    /api/v1/workflows
GET    /api/v1/workflows/{id}
GET    /api/v1/workflows/by-code/{code}
POST   /api/v1/workflows
PUT    /api/v1/workflows/{id}
DELETE /api/v1/workflows/{id}
POST   /api/v1/workflows/{id}/execute
POST   /api/v1/workflows/{id}/debug/start
POST   /api/v1/workflows/executions/{code}/next
POST   /api/v1/workflows/executions/{code}/run-to-end
POST   /api/v1/workflows/executions/{code}/stop
POST   /api/v1/workflows/executions/{code}/breakpoints
POST   /api/v1/workflows/executions/{code}/override-input
POST   /api/v1/workflows/executions/{code}/restart-from-step
GET    /api/v1/workflows/{id}/executions
GET    /api/v1/workflows/executions/{id}
GET    /api/v1/workflows/executions/by-code/{code}
POST   /api/v1/workflows/validate-dag
```

## 12.12 运行历史（runs.py）

```http
GET    /api/v1/runs
GET    /api/v1/runs/{id}
GET    /api/v1/runs/{id}/events
```

## 12.13 技能 V2（v2_skills.py）

```http
# 技能 CRUD
GET    /api/v2/skills
POST   /api/v2/skills
GET    /api/v2/skills/{id}
PUT    /api/v2/skills/{id}
DELETE /api/v2/skills/{id}
GET    /api/v2/skills/by-code/{code}

# 发布 / 取消发布
POST   /api/v2/skills/{id}/publish
POST   /api/v2/skills/{id}/unpublish

# 文件树
GET    /api/v2/skills/{id}/files
GET    /api/v2/skills/{id}/files/content?path=...
PUT    /api/v2/skills/{id}/files/content?path=...
DELETE /api/v2/skills/{id}/files/content?path=...
GET    /api/v2/skills/{id}/skill-md

# 版本
GET    /api/v2/skills/{id}/versions
POST   /api/v2/skills/{id}/versions
GET    /api/v2/skills/{id}/versions/{version}
POST   /api/v2/skills/{id}/versions/{version}/publish
POST   /api/v2/skills/{id}/versions/{version}/snapshot

# 执行
POST   /api/v2/skills/{id}/executions
POST   /api/v2/skills/{id}/executions/async
GET    /api/v2/skills/{id}/executions
GET    /api/v2/skills/executions/{execution_code}

# 工具（带 v2 risk_level 过滤）
GET    /api/v2/tools
GET    /api/v2/tools/v2

# 调试
POST   /api/v2/debug/sessions
POST   /api/v2/debug/sessions/{code}/step
GET    /api/v2/debug/sessions/{code}
GET    /api/v2/debug/sessions/{code}/variables
GET    /api/v2/debug/sessions/{code}/logs
POST   /api/v2/debug/sessions/{code}/breakpoints
DELETE /api/v2/debug/sessions/{code}/breakpoints/{line}
DELETE /api/v2/debug/sessions/{code}

# 任务队列
POST   /api/v2/tasks
GET    /api/v2/tasks/{code}
POST   /api/v2/tasks/{code}/retry
GET    /api/v2/worker/status
POST   /api/v2/worker/start
POST   /api/v2/worker/stop

# 模板
GET    /api/v2/templates
GET    /api/v2/templates/{id}
POST   /api/v2/templates/{id}/apply

# 导入/导出
GET    /api/v2/skills/{id}/export
POST   /api/v2/skills/import

# 定时调度
GET    /api/v2/schedules
POST   /api/v2/schedules
PUT    /api/v2/schedules/{code}/pause
PUT    /api/v2/schedules/{code}/resume
DELETE /api/v2/schedules/{code}

# 技能类型
GET    /api/v2/skill-types
POST   /api/v2/skill-types
PUT    /api/v2/skill-types/{type_code}
PUT    /api/v2/skill-types/{type_code}/disable

# 密钥
GET    /api/v2/secrets
POST   /api/v2/secrets
DELETE /api/v2/secrets/{key_name}
```

## 12.14 通用响应格式

```json
// 成功
{
  "code": 200,
  "data": { ... }
}

// 失败
{
  "code": 500,
  "message": "error description",
  "data": null
}
```

## 12.15 鉴权规则速查

| 路径前缀 | 鉴权要求 |
|----------|----------|
| `/`, `/docs`, `/openapi.json`, `/redoc` | 公共（不鉴权） |
| `/api/v1/auth/config`, `/api/v1/auth/dev-login` | 公共 |
| `/api/v1/auth/me` | 可选 token |
| 其他 `/api/v1/**`, `/api/v2/**` | ENABLE_AUTH=1 时强制 Bearer |
| 401 | 缺 token / token 无效 |
| 403 | 权限不足（需 `require_permission` 或 ResourceACL） |

