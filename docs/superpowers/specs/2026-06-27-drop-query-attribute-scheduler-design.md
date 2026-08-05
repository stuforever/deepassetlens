# 全面下掉 query_attribute / SchedulerCore 旧路径设计 spec

| 项目 | 值 |
|------|---|
| 日期 | 2026-06-27 |
| 作者 | brainstorming session |
| 目标 | 把 `query_attribute` 旧路径 + SchedulerCore + DAGCanvas 节点编排前端全部清掉，tupu 框架只保留 LangGraph 单一编排引擎 |
| 状态 | 设计中（待用户 review） |
| 范围 | 后端 5 文件 + 3 技能脚本 + LangGraph.json + agent_run 拆解；前端 2 页 + 2 组件 + DAGCanvas + WorkflowManager/Detail + 拆 MixedEditor/QueryEntityMgr + @xyflow/react；DB/RBAC/技能画像/共享 tags 收尾；测试清理 |

---

## 1. 背景与目标

### 1.1 背景

tupu 早期有 3 套并存的"工作流编排"路径：

1. **SchedulerCore**（`backend/app/core/scheduler_core.py`）——自研 DAG 调度器
2. **LangGraph**（`@langchain/langgraph`）—— LangChain 官方 StateGraph
3. **DAGCanvas + WorkflowDetailPage**（前端）—— 基于 `@xyflow/react` 的可视化编排/单步调试/断点/步入参覆盖 UI

`tupu` 主场景（数据智能对话）已是 LangGraph 单一路径。`query_attribute` 是早期 SchedulerCore 路径的代表，特性开关 `QUERY_ATTRIBUTE_USE_LANGGRAPH` 控制是否切到 LangGraph（生产已开 = 0/默认走 SchedulerCore，1 = 走 LangGraph）。

`graph_query`（基于图问数）已经走 LangGraph，但其 6 步中 4 步直接复用 `query_attribute_step{2,3,6}` 三个技能。

### 1.2 目标

- **彻底清掉** `query_attribute` 旧路径（5 个后端文件 + 3 个技能脚本 + 1 个 API 路由 + 1 个 langgraph.json 注册）
- **彻底清掉** SchedulerCore 节点编排前端（`DAGCanvas` + `WorkflowManager` + `WorkflowDetailPage` + `workflowApi` + `@xyflow/react` 依赖）
- **彻底清掉** 问属性前端页面（`QueryAttribute` 页面 + 结果卡片 + 场景配置 + API 包装）
- **拆改 2 个有争议组件**：`MixedEditorV2` 改 YAML 入口，`QueryEntityWorkflowManager` 整页拆掉
- **保持** `graph_query` 业务行为不变（独立重构 4 处复用）
- **保持** 其他 LangGraph 场景（数据智能对话、问实体、问指标）零影响
- **tupu 框架最终只剩 LangGraph 单一编排引擎**——技能管理、图谱、节点配置全在后台 DB + 磁盘

### 1.3 非目标

- 不重写 `scheduler_core.py`（仍被 `workflows.py` 校验 API、`smart_metric` 等其他模块使用，保留）
- 不重构 LangGraph SkillNodeFactory（已验证可用，不动）
- 不下 `@antv/g6` 画布（Neo4jForceCanvas、ForceCanvas、TreeCanvas、LineageGraph 是图谱/血缘可视化，不是节点编排）
- 不动统一 Run 会话容器（`runApi` + EventSource 给所有 LangGraph 场景用）

---

## 2. 现状全景图（清理前）

### 2.1 后端模块依赖

```
agent_run_runtime.py
   └── query_attribute_skill_runtime.py  (特性开关 _use_langgraph_path)
          ├── query_attribute_langgraph.py  (LangGraph 路径)
          │      └── query_attribute_workflow_bootstrap.py
          │             └── query_attribute_skill_bootstrap.py
          │                    └── 3 个 skill_code: query_attribute_step{2,3,6}_*
          │                           (data/skills/query_attribute_step{2,3,6}_*/scripts/main.py)
          └── scheduler_core.py  (SchedulerCore 路径)
                 └── query_attribute_workflow_bootstrap.py  (共享)

api/query_attribute.py
   ├── /query-attribute/example-metadata  (硬编码 EXAMPLE_QUERIES)
   ├── /query-attribute/system-metadata    (build_attribute_metadata_from_system)
   └── /query-attribute/map                (run_query_attribute_via_skills)

graph_query_workflow_bootstrap.py
   ├── ensure_query_attribute_skills()  [要改：自建 ensure_graph_query_skills]
   └── 6 步中 4 步复用 query_attribute_step{2,3,6}_*  [要改：改 skill_code]

langgraph.json
   ├── data_intelligence  (留)
   ├── graph_query        (留)
   └── query_attribute    (删)
```

### 2.2 前端模块依赖

```
App.tsx
   ├── 路由 case 'queryattribute' → <QueryAttribute />
   ├── 路由 case 'queryentity_workflow' → <WorkflowManager />  (要改：删)
   ├── 菜单 queryattribute  (要删)
   └── 菜单 queryentity_workflow  (要删)

QueryAttribute.tsx
   └── queryAttributeApi.getExampleMetadata  (要改：删)

WorkflowManager.tsx → WorkflowDetailPage.tsx
   ├── workflowApi.*  (SchedulerCore 调试接口)
   └── DAGCanvas  (节点可视化)

QueryEntityWorkflowManager.tsx
   └── DAGCanvas  (要改：整页拆)

DAGCanvas.tsx
   ├── @xyflow/react  (要删)
   ├── 调用方 1: WorkflowDetailPage
   ├── 调用方 2: QueryEntityWorkflowManager
   └── 调用方 3: MixedEditorV2  (要改：改 YAML)

MixedEditorV2.tsx
   └── DAGCanvas  (要改：改 YAML)

GraphQuery.tsx
   └── queryAttributeApi.getExampleMetadata  (要改：自建 EXAMPLE_QUERIES)

LLMConfigManager.tsx
   └── query_attribute_workflow_code 字段  (要改：删)

services/api.ts
   ├── queryAttributeApi  (要删)
   └── workflowApi  (要删)

CardRenderer.tsx
   └── QueryAttributeResultCard  (要删)

sceneConfigs.tsx
   ├── QUERY_ATTRIBUTE_SCENE_CONFIG  (要删)
   └── GRAPH_QUERY_SCENE_CONFIG 中 query_attribute_result card_type  (要改)
```

### 2.3 共享/边界

- `query_entity_step1/3/4` 是 `query_attribute` 与 `graph_query` 共享的 step 技能（不能删，仅去 tags）
- `kg_smart_planner_configs.query_attribute_workflow_code` 是 Planner 配置列（要删）
- `kg_conversations.conversation_meta.query_attribute_scene_state` / `query_attribute_last_result` 是历史 meta key（要清）
- `core/auth.py` `query_attribute` 角色字符串（要删）
- `api/v2_skills.py` 6 处 query_attribute step 条目（要删）

---

## 3. 架构（清理后）

### 3.1 单一 LangGraph 框架

```
┌────────────────────────────────────────────────────────────────┐
│ tupu 框架（清理后）                                              │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─ 数据智能对话 ─┐  ┌─ 问实体 ─┐  ┌─ 基于图问数 ─┐  ┌─ 问指标 ┐│
│  │  data_         │  │ query_   │  │ graph_       │  │ smart_  ││
│  │  intelligence  │  │ entity   │  │ query        │  │ metric  ││
│  │  _graph.py     │  │ (LG)     │  │ (LG)         │  │ (LG)    ││
│  └────────────────┘  └──────────┘  └──────────────┘  └─────────┘│
│         │                │                  │                │    │
│         └────────────────┴──────────────────┴────────────────┘    │
│                              ▼                                    │
│         ┌─────────────────────────────────────────┐               │
│         │  SkillNodeFactory                       │               │
│         │  (langgraph_skill_wrapper.py)           │               │
│         │  → ExecutionEngineV2.execute_by_code()  │               │
│         └─────────────────────────────────────────┘               │
│                              ▼                                    │
│         ┌─────────────────────────────────────────┐               │
│         │  后台技能管理                            │               │
│         │  - DB: skills / skill_versions          │               │
│         │  - 磁盘: data/skills/*/scripts/main.py  │               │
│         │  - 沙箱: PythonExecutor with whitelists │               │
│         │  - 追踪: LangSmith + local fallback     │               │
│         └─────────────────────────────────────────┘               │
│                                                                 │
│  ┌─ LangGraph Studio (开发态) ─┐                                │
│  │  langgraph.json: data_intelligence / graph_query              │
│  │  studio_graph_factory() 0-arg 入口                            │
│  └────────────────────────────────┘                             │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 不可动的部分（保留）

| 模块 | 原因 |
|------|------|
| `backend/app/core/scheduler_core.py` | 仍被 `workflows.py` 校验 API、`smart_metric` 等使用 |
| `@antv/g6` 画布（Neo4jForceCanvas、ForceCanvas、TreeCanvas、LineageGraph） | 图谱/血缘可视化，非节点编排 |
| 统一 Run 会话容器 + EventSource + `runApi` | 给所有 LangGraph 场景用 |
| 技能管理（skillV2、SkillContentEditorV2） | 通用能力 |
| `query_entity_step1/3/4` 共享 skill | 问实体场景仍用 |
| `find_attribute` 技能（S4 task2 独立技能） | 数据智能对话 task2 独立模块 |

---

## 4. 3 阶段交付（推荐方案 B）

### 4.1 阶段总览

| 阶段 | 范围 | 风险 | 验收日 | 工时 |
|------|------|------|--------|------|
| **PR1 后端清理** | graph_query 独立重构 + 删 query_attribute 后端 5 文件 + 3 技能脚本 + 拆 agent_run 分支 | 中 | Day 3 | 1-2 天 |
| **PR2 前端清理** | 删 2 页 + 2 组件 + DAGCanvas + WorkflowMgr/Detail + 拆 MixedEditor/QueryEntityMgr + 删 @xyflow/react | 中 | Day 5 | 1-2 天 |
| **PR3 DB/配置收尾** | DB 迁移 + RBAC + 技能画像 + 共享 tags + 测试清理 | 低 | Day 6 | 0.5-1 天 |

### 4.2 PR1 后端清理

#### 4.2.1 步骤清单

1. **新增 3 个 graph_query 专属 skill**（从 query_attribute 复制）
   - `data/skills/query_attribute_step2_vector_entity_recall/` → `data/skills/graph_query_step2_vector_entity_recall/`
   - `data/skills/query_attribute_step3_attribute_catalog/` → `data/skills/graph_query_step3_attribute_catalog/`
   - `data/skills/query_attribute_step6_finalize/` → `data/skills/graph_query_step6_finalize/`
   - 每个目录的 SKILL.md + scripts/main.py + input_schema.json + output_schema.json 全部复制
   - **仅改 scripts/main.py 中的 skill_code 字符串**，行为零修改

2. **新增 `graph_query_skill_bootstrap.py`**
   - 参照 `query_attribute_skill_bootstrap.py:25-123` 的 3 个 ensure 函数
   - 复制一份只改 skill_code
   - 新增 `ensure_graph_query_skills(db)` 顶层入口

3. **改造 `graph_query_workflow_bootstrap.py`**
   - 删 `from app.services.query_attribute_skill_bootstrap import ensure_query_attribute_skills`
   - 新增 `from app.services.graph_query_skill_bootstrap import ensure_graph_query_skills`
   - `_graph_query_nodes()` 中 4 处 skill_code 替换为新值（step2/step3/step6）
   - `ensure_graph_query_workflow()` 删 `ensure_query_attribute_skills` + 加 `ensure_graph_query_skills`，保留 `ensure_find_attribute_skill` 和 `ensure_query_entity_skills`

4. **删 5 个 query_attribute 后端文件**
   - `backend/app/services/query_attribute_skill_runtime.py`
   - `backend/app/services/query_attribute_langgraph.py`
   - `backend/app/services/query_attribute_workflow_bootstrap.py`
   - `backend/app/services/query_attribute_skill_bootstrap.py`
   - `backend/app/api/query_attribute.py`

5. **删 3 个 query_attribute 技能脚本目录**
   - `backend/data/skills/query_attribute_step2_vector_entity_recall/`
   - `backend/data/skills/query_attribute_step3_attribute_catalog/`
   - `backend/data/skills/query_attribute_step6_finalize/`

6. **删 langgraph.json 注册**
   - `langgraph.json:4` 删 `"query_attribute": "..."` 行
   - 保留 `data_intelligence` + `graph_query`

7. **拆 `agent_run_runtime.py` query_attribute 分支**
   - [L830-832](file:///d:/gitcangku/DB-GPT/tupu/backend/app/services/agent_run_runtime.py#L830-L832) 条件简化为仅 graph_query
   - 删 5 个 query_attribute helper：`_clear_query_attribute_scene_state` / `_get_query_attribute_scene_state` / `_build_query_attribute_scene_state` / `_compose_attribute_resumed_query` / `_build_query_attribute_output`
   - 删 4 个常量：`DEFAULT_QUERY_ATTRIBUTE_PAGE` / `DEFAULT_QUERY_ATTRIBUTE_SCENE` / `QUERY_ATTRIBUTE_SCENE_STATE_KEY` / `QUERY_ATTRIBUTE_LAST_RESULT_KEY`
   - 删所有 `run.page_code == DEFAULT_QUERY_ATTRIBUTE_PAGE` 分支（L893, L912, L915, L916, L924-927, L1024-1029, L1033-1097, L1111-1136）

#### 4.2.2 PR1 验收

```bash
# 1. graph_query 独立跑通
cd backend && py -m pytest test_graph_query.py -v

# 2. 后端无 query_attribute 引用（除 PR1 不动的字段/RBAC/技能画像）
git grep "query_attribute" -- ':!*test*' backend/ | grep -v kg_smart_planner_configs | grep -v auth.py | grep -v v2_skills.py | grep -v llm_admin.py | grep -v models/base.py | grep -v database.py
# 期望：0 命中

# 3. 数据智能对话 + 问实体 + graph_query e2e 跑通
py tmp_test_lg_query_entity.py
py tmp_test_graph_query.py
py tmp_test_lg_data_intelligence.py

# 4. 前端 /example-metadata 会 404（PR2 修复）
curl -i http://127.0.0.1:8100/api/v1/query-attribute/example-metadata
# 期望：HTTP 404（不是 5xx）
```

#### 4.2.3 风险与缓解

| 风险 | 等级 | 缓解 |
|------|------|------|
| graph_query 复制 3 skill 漏改 skill_code | 中 | grep `query_attribute_step` 在新目录无残留 |
| `agent_run_runtime.py` 分支拆解漏改 | 高 | 全文 grep `query_attribute` 应 0 命中；跑 4 类 LangGraph e2e |
| `_build_query_attribute_output` 等被 graph_query 复用 | 中 | 确认 [graph_query_skill_runtime.py:226](file:///d:/gitcangku/DB-GPT/tupu/backend/app/services/graph_query_skill_runtime.py#L226) 引用；如有，inline 改造 |
| 老 `kg_conversations.conversation_meta.query_attribute_*` key 残留 | 低 | PR1 不清理，PR3 一并处理 |

### 4.3 PR2 前端清理

#### 4.3.1 步骤清单

1. **拆 `MixedEditorV2` 改 YAML 入口**
   - 移除 `import DAGCanvas`（L11）+ `<DAGCanvas>`（L201）
   - 用 `@monaco-editor/react` 编辑 `scripts/main.py`（已有依赖）
   - 或用 antd `Table` 渲染节点列表 + `Form` 编辑属性
   - 对外接口不变：`SkillContentEditorV2.tsx:32` `case 'mixed': return <MixedEditorV2 ... />` 不动

2. **拆 `QueryEntityWorkflowManager` 整页**
   - 删 [pages/QueryEntityWorkflowManager.tsx](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/pages/QueryEntityWorkflowManager.tsx) 整文件
   - 业务转移：问实体技能编辑走 `SkillContentEditorV2`（`skillManager` 页入口已有）
   - 删 `App.tsx:93-94, 150` `queryentity_workflow` 路由和菜单

3. **删 `DAGCanvas` 组件**
   - 删 [components/editors/DAGCanvas.tsx](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/components/editors/DAGCanvas.tsx) 整文件
   - 删 `package.json:11` `@xyflow/react` 依赖
   - 跑 `npm install` 重生成 `package-lock.json`

4. **删 `WorkflowManager` + `WorkflowDetailPage`**
   - 删 [pages/WorkflowManager.tsx](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/pages/WorkflowManager.tsx) 整文件
   - 删 [pages/WorkflowDetailPage.tsx](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/pages/WorkflowDetailPage.tsx) 整文件
   - 删 [App.tsx:33](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/App.tsx#L33) `import WorkflowManager` + 路由 + 菜单
   - 删 `App.tsx:93-94, 150` `queryentity_workflow` 路由和菜单（同上，与步骤 2 合并）

5. **删 `workflowApi` + `queryAttributeApi`**
   - [services/api.ts:306-328](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/services/api.ts#L306-L328) `workflowApi` 整块删
   - [services/api.ts:295-304](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/services/api.ts#L295-L304) `queryAttributeApi` 整块删

6. **删 `QueryAttribute` 页面 + 路由 + 菜单**
   - 删 [pages/QueryAttribute.tsx](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/pages/QueryAttribute.tsx) 整文件
   - 删 [App.tsx:28](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/App.tsx#L28) `import QueryAttribute` + [L83-84](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/App.tsx#L83-L84) `case 'queryattribute':` + [L144](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/App.tsx#L144) 菜单项

7. **删 `QueryAttributeResultCard` + 卡片分发**
   - 删 [components/conversation/QueryAttributeResultCard.tsx](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/components/conversation/QueryAttributeResultCard.tsx) 整文件
   - 删 [components/conversation/QueryAttributeResultCard.module.css](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/components/conversation/QueryAttributeResultCard.module.css) 整文件
   - 改 [components/conversation/CardRenderer.tsx:4](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/components/conversation/CardRenderer.tsx#L4) 删 import + [L30-31](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/components/conversation/CardRenderer.tsx#L30-L31) 删 `query_attribute_result` 分支

8. **改 `sceneConfigs.tsx`**
   - 删 [components/conversation/sceneConfigs.tsx:10-55](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/components/conversation/sceneConfigs.tsx#L10-L55) `QUERY_ATTRIBUTE_SCENE_CONFIG` 整块
   - 改 [components/conversation/sceneConfigs.tsx:92](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/components/conversation/sceneConfigs.tsx#L92) `GRAPH_QUERY_SCENE_CONFIG.shouldShowSuccessToast` 中 `card.card_type === 'query_attribute_result'` → 改为 graph_query 实际产出的 card_type
   - **PR2 实施时实测确认 graph_query 实际 card_type 名称**（预计是 `graph_query_result` 或 `attribute_query_result` 之一，PR1 后跑一次 graph_query e2e 抓 SSE 事件中 `card.card_type` 字段确认）
   - 如果实际 card_type 与 query_attribute 相同（即 graph_query 共用 query_attribute 卡片类型），那么 GraphQuery 场景需要新增一个独立的 `GraphQueryResultCard` 组件 + 在 `CardRenderer` 中加分发分支

9. **改 `GraphQuery.tsx` 残留**
   - [pages/GraphQuery.tsx:4](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/pages/GraphQuery.tsx#L4) 删 `queryAttributeApi` 导入
   - [pages/GraphQuery.tsx:57-64](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/pages/GraphQuery.tsx#L57-L64) `queryAttributeApi.getExampleMetadata()` 改为前端硬编码 `EXAMPLE_QUERIES` 常量（从原 `api/query_attribute.py` 复制内容）

10. **改 `LLMConfigManager.tsx` 字段**
    - 删 [pages/LLMConfigManager.tsx:87, 214, 329-335, 343](file:///d:/gitcangku/DB-GPT/tupu/frontend/src/pages/LLMConfigManager.tsx#L87-L343) 4 处 `query_attribute_workflow_code` 字段
    - 页面保留（问实体、智能问指标等场景仍用规划器）

#### 4.3.2 PR2 验收

```bash
# 1. 前端无 queryAttribute / DAGCanvas / xyflow 引用
cd frontend && npx tsc --noEmit
git grep -i "QueryAttribute\|queryAttribute\|DAGCanvas\|xyflow" src/
# 期望：0 命中

# 2. 前端 build 通过
npm run build

# 3. LangGraph 场景全跑通（手动 e2e）
# 浏览器：每个场景跑 1 个 example query
```

#### 4.3.3 风险与缓解

| 风险 | 等级 | 缓解 |
|------|------|------|
| `MixedEditorV2` 改 YAML 后用户体验下降 | 低 | 加 example YAML 模板；用户可复制修改 |
| `QueryEntityWorkflowManager` 整页拆后用户找不到入口 | 中 | `SkillManager` 页加"问实体技能"快捷入口 |
| `GraphQuery.tsx:57-64` 改 example 列表内容漂移 | 低 | 从 `api/query_attribute.py` 复制原 `EXAMPLE_QUERIES` |
| `sceneConfigs.tsx:92` 改 card_type 假设错 | 中 | PR2 实测确认 graph_query 实际 card_type |

### 4.4 PR3 DB/配置收尾

#### 4.4.1 步骤清单

1. **删 DB 列 + 写迁移**
   - 新增 `backend/migrate_drop_query_attribute_workflow_code.py`：
     ```python
     from sqlalchemy import text
     from app.core.database import engine

     def upgrade():
         with engine.begin() as conn:
             cols = [row[0] for row in conn.execute(text("SHOW COLUMNS FROM kg_smart_planner_configs")).fetchall()]
             if "query_attribute_workflow_code" in cols:
                 conn.execute(text("ALTER TABLE kg_smart_planner_configs DROP COLUMN query_attribute_workflow_code"))
                 print("✓ dropped")
             else:
                 print("✓ already dropped")
     ```
   - 删 [core/database.py:313-314](file:///d:/gitcangku/DB-GPT/tupu/backend/app/core/database.py#L313-L314) `ALTER TABLE ... ADD COLUMN` 语句
   - 删 [models/base.py:409](file:///d:/gitcangku/DB-GPT/tupu/backend/app/models/base.py#L409) `query_attribute_workflow_code` 字段定义

2. **清理 `kg_conversations` 旧 meta key**
   - 新增 `backend/migrate_clear_query_attribute_conversation_meta.py`：
     ```python
     from sqlalchemy import text
     from app.core.database import engine
     import json

     def upgrade():
         with engine.begin() as conn:
             rows = conn.execute(text("""
                 SELECT id, conversation_meta FROM kg_conversations
                 WHERE JSON_SEARCH(conversation_meta, 'one_or_all', 'query_attribute_scene_state') IS NOT NULL
                    OR JSON_SEARCH(conversation_meta, 'one_or_all', 'query_attribute_last_result') IS NOT NULL
             """)).fetchall()
             for row_id, meta in rows:
                 if not meta:
                     continue
                 data = json.loads(meta) if isinstance(meta, str) else meta
                 data.pop("query_attribute_scene_state", None)
                 data.pop("query_attribute_last_result", None)
                 conn.execute(
                     text("UPDATE kg_conversations SET conversation_meta = :m WHERE id = :i"),
                     {"m": json.dumps(data, ensure_ascii=False), "i": row_id},
                 )
             print(f"✓ cleaned {len(rows)} rows")
     ```

3. **清 RBAC 字符串**
   - 删 [core/auth.py:311, 318](file:///d:/gitcangku/DB-GPT/tupu/backend/app/core/auth.py#L311-L318) `query_attribute` 角色字符串
   - 如 `kg_user_roles.role_name='query_attribute'` 行存在，写脚本 `UPDATE kg_user_roles SET role_name=NULL WHERE role_name='query_attribute'`

4. **清 `api/llm_admin.py` Planner 字段**
   - 删 [api/llm_admin.py:60](file:///d:/gitcangku/DB-GPT/tupu/backend/app/api/llm_admin.py#L60) `query_attribute_workflow_code` 字段
   - PlannedConfig Pydantic 模型、读写 DB 代码、PATCH 接口的字段全删

5. **清 `api/v2_skills.py` 技能画像**
   - 删 [api/v2_skills.py:454-455, 524-567](file:///d:/gitcangku/DB-GPT/tupu/backend/app/api/v2_skills.py#L454-L567) 6 处 query_attribute step 条目 + retain_reason 分支
   - 特别注意 L454-455 的 `_infer_retain_reason` 改 reason 为"shared by graph_query step4 / query_entity step3"

6. **清共享 skill tags**
   - 改 [query_entity_skill_bootstrap.py](file:///d:/gitcangku/DB-GPT/tupu/backend/app/services/query_entity_skill_bootstrap.py) 3 处 tags：
     - `query_entity_step1_metadata_overview`: `["query_entity", "query_attribute", "shared", "step1", "metadata"]` → `["query_entity", "shared", "step1", "metadata"]`
     - `query_entity_step3_llm_prompt`: `["query_entity", "query_attribute", "shared", "step3", "prompt"]` → `["query_entity", "shared", "step3", "prompt"]`
     - `query_entity_step4_llm_inference`: `["query_entity", "query_attribute", "shared", "step4", "llm"]` → `["query_entity", "shared", "step4", "llm"]`
   - 启动时跑 `ensure_query_entity_skills(db)` 强制重写 tags

7. **删测试文件**
   - 删 [test_query_attribute.py](file:///d:/gitcangku/DB-GPT/tupu/backend/test_query_attribute.py)
   - 删 [tmp_test_lg_query_attribute.py](file:///d:/gitcangku/DB-GPT/tupu/backend/tmp_test_lg_query_attribute.py)
   - 删 [tmp_test_lg_query_attribute_regress.py](file:///d:/gitcangku/DB-GPT/tupu/backend/tmp_test_lg_query_attribute_regress.py)
   - 改 [test_query_entity.py:159](file:///d:/gitcangku/DB-GPT/tupu/backend/test_query_entity.py#L159) 删 `ensure_query_attribute_workflow` 调用
   - 保留 [test_query_entity.py:413](file:///d:/gitcangku/DB-GPT/tupu/backend/test_query_entity.py#L413) 反向校验

#### 4.4.2 PR3 验收

```bash
# 1. DB 迁移幂等
py migrate_drop_query_attribute_workflow_code.py
py migrate_drop_query_attribute_workflow_code.py  # 第二次跑应无变化
py migrate_clear_query_attribute_conversation_meta.py
py migrate_clear_query_attribute_conversation_meta.py

# 2. 技能画像无 query_attribute 条目
curl -s http://127.0.0.1:8100/api/v2/skills | python -c "import json,sys; d=json.load(sys.stdin); print([x for x in d.get('data',[]) if 'query_attribute' in json.dumps(x).lower()])"
# 期望：[]

# 3. 共享 skill tags 干净
mysql -e "SELECT skill_code, tags FROM skills WHERE skill_code IN ('query_entity_step1_metadata_overview','query_entity_step3_llm_prompt','query_entity_step4_llm_inference')" tupu
# 期望：tags 中无 query_attribute

# 4. 全 e2e
py test_query_entity.py
py test_graph_query.py
py tmp_test_lg_data_intelligence.py

# 5. 全代码库 grep query_attribute 命中 0
cd ../.. && git grep -i "query_attribute" -- ':!*.md' ':!*.lock' ':!wiki/'
# 期望：0 命中
```

#### 4.4.3 风险与缓解

| 风险 | 等级 | 缓解 |
|------|------|------|
| DB 迁移破坏老 conversation 续澄清 | 低 | 老 conversation 已是历史，无人会继续用 |
| RBAC 角色名删除后用户登录报错 | 低 | RBAC 角色名是约束，不在登录路径关键检查中 |
| 共享 skill tags 更新未生效 | 低 | 启动跑 ensure 强制重写 |
| 删测试时漏改 import | 低 | PR3 前跑 `git grep "test_query_attribute\|tmp_test_lg_query_attribute"` 应 0 命中 |

---

## 5. 验收标准汇总

### 5.1 静态检查

```bash
# 1. 后端无 query_attribute 引用
git grep -i "query_attribute" -- backend/ ':!*.md' ':!wiki/'
# 期望：3 PR 都为 0 命中

# 2. 前端无 queryAttribute / DAGCanvas / xyflow 引用
git grep -i "QueryAttribute\|queryAttribute\|DAGCanvas\|xyflow" -- frontend/src/
# 期望：PR1 仍有 4-6 处（页面/卡片/路由），PR2 起为 0 命中

# 3. 无特性开关
git grep "QUERY_ATTRIBUTE_USE_LANGGRAPH" -- backend/
# 期望：3 PR 都为 0 命中
```

### 5.2 编译/类型检查

```bash
# 后端
cd backend && py -m py_compile app/services/graph_query_*.py app/services/data_intelligence_graph.py
# 期望：无报错

# 前端
cd frontend && npx tsc --noEmit
# 期望：无 type error

# 前端 build
npm run build
# 期望：build 成功
```

### 5.3 运行时检查

```bash
# 后端启动
cd backend && py -m uvicorn app.main:app --port 8100
# 期望：启动无 5xx 错误；启动日志确认 query_attribute bootstrap 已不再调用

# query_attribute 接口全部 404
curl -i http://127.0.0.1:8100/api/v1/query-attribute/example-metadata
# 期望：HTTP 404

# 前端启动
cd frontend && npm start
# 期望：浏览器控制台无 404 红色报错
```

### 5.4 业务回归（每 PR 必跑）

| 场景 | example query | 期望结果 |
|------|---------------|---------|
| 数据智能对话 | "查一下金沙江下游梯级水电站的装机容量" | 走 LangGraph 多轮对话，实体→属性→SQL 拼装→执行 |
| 问实体 | "用电客户主数据有哪些" | 返回实体清单 |
| 问属性 | "用电客户的联系电话字段是哪个" | 返回属性归属 |
| graph_query | "查一下金沙江下游梯级水电站的装机容量"（基于图） | 返回 6 步结果（PR1 起新 skill_code） |
| 问指标 | "统计各行业用电量同比" | 返回指标 SQL |

### 5.5 文档/配置同步

| 文档 | 动作 |
|------|------|
| `wiki/07-工作流与编排.md` 第 7.5/7.6 节 | 删 `QUERY_ATTRIBUTE_USE_LANGGRAPH` 开关说明；删"工作流管理"前端描述 |
| `wiki/02-智能问属性.md` | 整文档改写为 LangGraph 实现说明，删除 SchedulerCore 路径描述 |
| README.md（如有"智能问属性"章节） | 同步改写 |
| `langgraph.json` 注释 | 删 `query_attribute` 字段 |
| `.env.example` / `.env.template` | 删 `QUERY_ATTRIBUTE_USE_LANGGRAPH` 模板变量 |

---

## 6. 风险汇总

| 风险 | 等级 | 缓解 |
|------|------|------|
| graph_query 复制 3 skill 漏改 skill_code | 中 | grep 校验；`ensure_graph_query_skills` 启动跑通 |
| `agent_run_runtime.py` 分支拆解漏改一处 | 高 | PR1 跑 4 类 LangGraph e2e，输出对照历史结果 |
| `MixedEditorV2` 改 YAML 后用户体验下降 | 低 | 加 example YAML 模板；用户可复制修改 |
| `QueryEntityWorkflowManager` 整页拆后用户找不到入口 | 中 | `SkillManager` 加"问实体技能"快捷入口 |
| `GraphQuery.tsx:57-64` 改 example 列表内容漂移 | 低 | 直接从 `api/query_attribute.py` 复制原 `EXAMPLE_QUERIES` |
| `sceneConfigs.tsx:92` 改 card_type 假设错 | 中 | PR2 实测确认 graph_query 实际 card_type |
| DB 迁移破坏老 conversation 续澄清 | 低 | 老 conversation 已是历史，无人会继续用 |
| RBAC 角色名删除后用户操作日志匹配失败 | 低 | `kg_user_roles.role_name='query_attribute'` 行清空或保留 |
| 共享 skill tags 未生效 | 低 | 启动跑 ensure 强制重写 |
| 测试覆盖回归 | 高 | PR3 跑 `test_query_entity.py` / `test_graph_query.py` 全量 |

---

## 7. 决策记录

| 问题 | 决策 |
|------|------|
| graph_query 怎么办？ | 保留，独立重构（4 处复用改为自带 skill） |
| 节点编排前端（DAGCanvas / WorkflowManager / Detail）怎么处理？ | 全部下掉 |
| MixedEditorV2（混合技能编辑器，嵌了 DAGCanvas）怎么处理？ | 拆掉改 YAML 入口 |
| QueryEntityWorkflowManager（问实体工作流编排，嵌了 DAGCanvas）怎么处理？ | 拆掉整页 |
| 用什么清理方案？ | 方案 B：3 PR 分阶段清 |
| `scheduler_core.py` 怎么办？ | 保留（被其他模块用） |
| `@antv/g6` 画布怎么办？ | 保留（图谱/血缘可视化） |
| 统一 Run 会话容器 + `runApi` 怎么办？ | 保留（给所有 LangGraph 场景用） |
| 共享 skill `query_entity_step{1,3,4}` 怎么办？ | 保留，仅去 tags |

---

## 8. 实施计划概要

- PR1 后端清理（1-2 天）：graph_query 独立重构 + 删 query_attribute 后端 5 文件 + 3 技能脚本 + 拆 agent_run 分支
- PR2 前端清理（1-2 天）：删 2 页 + 2 组件 + DAGCanvas + WorkflowMgr/Detail + 拆 MixedEditor/QueryEntityMgr + 删 @xyflow/react
- PR3 DB/配置收尾（0.5-1 天）：DB 迁移 + RBAC + 技能画像 + 共享 tags + 测试清理
- **总工时**：约 4-5 工作日
- **交付节奏**：每 PR 独立可发布 + 可回退

详细实施计划将在 spec 审阅后通过 writing-plans skill 生成。
