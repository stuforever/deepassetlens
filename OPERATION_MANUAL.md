# tupu 操作手册

> 适用版本：2026-06-13 v5 重构后
> 范围：基础设施启动、权限系统使用、LangGraph 配置与调试

---

## 0. 端口与服务总览

| 服务 | 端口 | 协议 | 启动方 |
|---|---|---|---|
| frontend (React) | 3000 | HTTP | `npm start`（frontend 目录） |
| backend (FastAPI) | 8000 / 8100 | HTTP | `uvicorn app.main:app` |
| Authentik UI | 9100 | HTTP | docker-compose.infra.yml |
| Authentik HTTPS | 9143 | HTTPS | 同上 |
| Qdrant REST / gRPC | 6333 / 6334 | HTTP / gRPC | 同上 |
| Neo4j HTTP / Bolt | 7474 / 7687 | HTTP / Bolt | 同上 |
| LangGraph Studio dev server | 2024 | HTTP | `langgraph dev` |
| MySQL（业务库） | 3306 | TCP | 用户自管 |

8000 vs 8100：
- 8000 是历史 backend 端口（不带权限集成）。
- 8100 是新加权限集成的 backend，验证期同时存在；未来确认稳定后可统一回 8000。

---

## 1. 一键启动

### 1.1 启动基础设施（Authentik / Qdrant / Neo4j）

```powershell
cd d:\gitcangku\DB-GPT\tupu
docker compose --env-file .env.infra -f docker-compose.infra.yml up -d
```

健康检查：

```powershell
docker compose -f docker-compose.infra.yml ps --format "table {{.Name}}\t{{.Status}}"
# 期望：6 个容器 (Up X minutes (healthy))
```

可视化访问：
- Authentik 管理 UI: http://localhost:9100/  （账号：`akadmin` / 密码：`<change_me>`）
- Qdrant Dashboard: http://localhost:6333/dashboard  （需 API key：`tupu_qdrant_dev_key`）
- Neo4j Browser: http://localhost:7474/  （账号：`neo4j` / 密码：`tupu_neo4j_dev_pass`）

### 1.2 启动 backend

不带权限（默认，等同改造前行为）：

```powershell
cd d:\gitcangku\DB-GPT\tupu\backend
$env:PYTHONUTF8="1"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8100 --reload
```

带权限（强制 Bearer JWT 校验）：

```powershell
$env:PYTHONUTF8="1"
$env:ENABLE_AUTH="1"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8100 --reload
```

### 1.3 启动 frontend

```powershell
cd d:\gitcangku\DB-GPT\tupu\frontend
$env:BROWSER="none"
npm start
```

访问：http://localhost:3000/

---

## 2. 权限系统（Authentik OIDC + 自研 RBAC）

### 2.1 架构一图

```
┌──────────┐  ① 跳转 /authorize       ┌──────────────┐
│ frontend │  + PKCE code_challenge   │  Authentik   │
│  :3000   │ ───────────────────────▶│   :9100      │
└────┬─────┘                          └──────┬───────┘
     │                                       │ ② 用户登录
     │  ④ Bearer access_token                │
     │     调 backend                        │ ③ 回调 + code
     ▼                                       ▼
┌──────────┐  验签 + RBAC + ACL    ┌────────────────┐
│ backend  │ ◀───── JWKS ──────── │  /jwks/        │
│  :8100   │                       └────────────────┘
└──────────┘
```

四个数据库表（启动时自动建）：
- `auth_users` — Authentik sub 镜像
- `auth_roles` — 角色定义（admin/operator/viewer + 自定义）
- `auth_user_roles` — 用户↔角色 N:N
- `auth_resource_acl` — 资源级 ACL（per-skill / per-workflow 授权）

### 2.2 ENABLE_AUTH 开关行为

| 设置 | 行为 |
|---|---|
| `ENABLE_AUTH=0`（默认） | 所有请求按"匿名 admin"处理，与改造前等价；UserBadge 显示 `anonymous` + `admin` + `权限关闭` |
| `ENABLE_AUTH=1` | 公共路径（`/`、`/docs`、`/api/v1/auth/config`）放行；其他路径无 token → 401，假 token → 401，合法 token → 解析用户走 RBAC |

### 2.3 在 Authentik 创建测试用户

1. 浏览器访问 http://localhost:9100/  用 `akadmin` / `<change_me>` 登录
2. 左侧菜单 **Directory → Users → Create**
3. 输入 username (例：`alice`)、name、email；提交后点 **Set password** 设密码
4. 进入 **Directory → Groups**，把 alice 加入 `tupu-admin` / `tupu-operator` / `tupu-viewer` 中的某一个
   - 角色映射规则在 [`app/core/auth.py`](backend/app/core/auth.py) 的 `GROUP_ROLE_MAP`：
     ```
     tupu-admin    → admin
     tupu-operator → operator
     tupu-viewer   → viewer
     ```

### 2.4 让 access_token 携带 username / groups（关键）

Authentik OAuth Provider 默认不会把 `preferred_username` 和 `groups` claim 注入 access_token。如果不配置，UserBadge 会显示 sub 哈希、groups 为空、用户兜底进 `viewer` 角色。

**配置步骤**：

1. Authentik UI → **Applications → Providers → tupu-oidc → Edit**
2. 展开 **Advanced protocol settings**
3. **Scopes** 字段勾选/输入：
   - `authentik default OAuth Mapping: OpenID 'openid'`
   - `authentik default OAuth Mapping: OpenID 'profile'`
   - `authentik default OAuth Mapping: OpenID 'email'`
   - `authentik default OAuth Mapping: Proxy outpost`（含 groups）
4. 如果没有 `groups` mapping，进 **Customisation → Property Mappings → Create → Scope Mapping**：
   - Name: `tupu-groups`
   - Scope name: `groups`
   - Expression:
     ```python
     return {
         "groups": [g.name for g in request.user.ak_groups.all()],
     }
     ```
5. 回到 Provider，把 `tupu-groups` 加到 Scopes
6. 保存后用户**重新登录**才生效（旧 token 不会刷新 claims）

验证：

```powershell
# 拿到一个真 token 后
$T = "<access_token>"
Invoke-RestMethod -Uri "http://localhost:8100/api/v1/auth/me" -Headers @{ Authorization = "Bearer $T" } | ConvertTo-Json -Depth 5
# 期望：username=alice, groups=["tupu-admin"], roles=["admin"], is_anonymous=false
```

### 2.5 资源级 ACL 用法

backend API：

```powershell
# 把"skill_x" 的 read+execute 权限授给用户 alice (sub=xxx)
Invoke-RestMethod -Uri "http://localhost:8100/api/v1/auth/grant" -Method Post `
  -Headers @{ Authorization = "Bearer $ADMIN_TOKEN"; "Content-Type"="application/json" } `
  -Body (@{
    resource_type = "skill"
    resource_id = "skill_x"
    principal_type = "user"
    principal_id = "<alice 的 sub>"
    actions = @("read", "execute")
  } | ConvertTo-Json)

# 列出某资源的所有授权
Invoke-RestMethod -Uri "http://localhost:8100/api/v1/auth/grants?resource_type=skill&resource_id=skill_x" `
  -Headers @{ Authorization = "Bearer $ADMIN_TOKEN" }

# 撤销
Invoke-RestMethod -Method Delete -Uri "http://localhost:8100/api/v1/auth/grant/123" `
  -Headers @{ Authorization = "Bearer $ADMIN_TOKEN" }
```

frontend 用 `<ResourceAclDrawer>` 组件直接挂载：

```tsx
import ResourceAclDrawer from '../components/ResourceAclDrawer';

<ResourceAclDrawer
  open={open}
  onClose={() => setOpen(false)}
  resourceType="skill"
  resourceId={skillCode}
/>
```

### 2.6 权限判定优先级（自上而下命中即放行）

1. 用户角色含 `admin` → 全部允许
2. 角色默认权限模板 `_DEFAULT_ROLE_PERMS` 命中（在 `app/core/auth.py`）
3. ResourceACL `principal=user` + 具体 resource_id 命中
4. ResourceACL `principal=role` + 具体 resource_id 命中
5. ResourceACL `principal=role` + resource_id='\*' 命中

### 2.7 常见问题排查

| 现象 | 排查 |
|---|---|
| frontend 一直 spinning "加载权限配置..." | backend 没起 / 8100 端口不通；浏览器 F12 看 `/auth/config` 请求 |
| 跳了 Authentik 但永远回不来 | redirect_uri 不匹配；Authentik UI Provider → Redirect URIs 检查是 `http://localhost:3000/auth/callback`（strict 模式） |
| 401 一直重定向 | localStorage 里 token 过期；F12 → Application → Local Storage → 删除 `tupu.oidc` |
| /auth/me 返回 is_anonymous=false 但 username 是 hash | Authentik 没注入 preferred_username claim，按 §2.4 配 ScopeMapping |
| 改了 Authentik 配置但用户仍是旧角色 | JWT 是离线签的，不会主动刷新；让用户登出重登 |

---

## 3. LangGraph 配置与调试

### 3.1 当前接入状况

仅 **query_attribute** 一个能力被 LangGraph 化（试点）：

| 文件 | 作用 |
|---|---|
| [`app/services/query_attribute_langgraph.py`](backend/app/services/query_attribute_langgraph.py) | StateGraph + Checkpointer + HITL API |
| [`app/services/langgraph_skill_wrapper.py`](backend/app/services/langgraph_skill_wrapper.py) | OpenClaw 龙虾技能 → LangGraph 节点适配器 |
| [`app/services/query_attribute_skill_runtime.py`](backend/app/services/query_attribute_skill_runtime.py) | 入口分流（特性开关）|
| [`backend/langgraph.json`](backend/langgraph.json) | LangGraph Studio 配置入口 |
| [`backend/scripts/run_langgraph_studio.ps1`](backend/scripts/run_langgraph_studio.ps1) | Studio 启动脚本 |

### 3.2 切换执行路径（特性开关）

```powershell
# legacy（SchedulerCore 路径，默认）
$env:QUERY_ATTRIBUTE_USE_LANGGRAPH = "0"

# LangGraph 路径
$env:QUERY_ATTRIBUTE_USE_LANGGRAPH = "1"
```

**重要**：`_use_langgraph_path()` 每次请求都重新读 env，但 backend 进程启动时如果 env 没设，子进程也读不到。改 env 后需重启 backend。

### 3.3 启动 LangGraph Studio dev server

```powershell
cd d:\gitcangku\DB-GPT\tupu\backend
$env:PYTHONUTF8="1"
$env:LANGSMITH_API_KEY="lsv2_pt_dummy"   # Studio 强制要这个，dummy 即可
langgraph dev --host 127.0.0.1 --port 2024 --no-browser --allow-blocking
```

启动后会输出：

```
- 🚀 API:       http://127.0.0.1:2024
- 🎨 Studio UI: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- 📚 API Docs:  http://127.0.0.1:2024/docs
```

Studio UI 走 LangSmith 反向代理（你访问 smith.langchain.com 但实际数据走本地 2024）。**不需要登录 LangSmith**，会自动连本地。

### 3.4 在 Studio 里调试一个 thread

1. 访问 Studio UI 链接
2. 左侧 graph 列表选 `query_attribute`
3. 点 **+ New Run**
4. 在 **Input** 里填：
   ```json
   {
     "user_inputs": {
       "user_query": "查用电客户的客户名称、行业分类、重要性等级",
       "metadata_source": "system",
       "metadata": {},
       "llm_connection_id": null
     },
     "step_results": {},
     "step_trace": [],
     "last_step_id": null,
     "last_step_status": null,
     "last_error": null
   }
   ```
5. 点 **Run** 看 6 步逐步执行
6. 中间任意步可点 **Edit** 改 state，再 **Resume** 续跑

### 3.5 HITL（Human-in-the-Loop）调用方式

代码层面（在 backend 内部）：

```python
from app.services.query_attribute_langgraph import (
    run_query_attribute_via_langgraph,
    get_thread_state,
    resume_thread,
    rewind_thread,
)
from app.core.database import SessionLocal

db = SessionLocal()

# 1. 跑一次（自动生成 thread_id）
result = run_query_attribute_via_langgraph(
    db,
    user_query="查用电客户的客户名称",
    metadata_source="system",
)
thread_id = result["thread_id"]

# 2. 看当前状态
state = get_thread_state(db, thread_id)
print(state["next"], state["last_step_id"], state["last_step_status"])

# 3. 上次因故障中断 → 续跑（state 里 step1/step2 的结果还在）
result2 = resume_thread(db, thread_id)

# 4. 跑完后想从 step3 重跑（基于既有上下文）
result3 = rewind_thread(db, thread_id, to_step_id="step3")
# 然后再调 resume_thread 续跑
```

REST API 层面（暂未暴露成路由，需要自加）：当前 HITL 只在 Python 层用，前端要触发需要先包一层 HTTP endpoint。这是已知遗留项。

### 3.6 检查点持久化

当前用的是进程级 `InMemorySaver`，进程重启后 thread 状态全部丢失。
- **想要跨进程持久化**有三个选项（按工作量从小到大）：
  - `pip install langgraph-checkpoint-sqlite` → 落本地 .db 文件（最简单）
  - `pip install langgraph-checkpoint-postgres` → 用独立 PG（与业务库隔离）
  - 自实现 `MySQLCheckpointSaver`（约 600 行，对齐 BaseCheckpointSaver 接口）
- **当前不做的原因**：步骤审计已落到 `kg_smart_pipeline_step_runs` 表（通过 step_event_callback），跨进程持久化只对"中断后续跑"场景有用，目前是 dev 期不必要。

### 3.7 Studio 启动失败排查

| 错误 | 原因 / 修复 |
|---|---|
| `UnicodeDecodeError 'gbk' codec` | Windows 编码问题；启动前 `$env:PYTHONUTF8="1"` |
| `AttributeError: module 'langgraph_api.config' has no attribute 'LSD_PROM_METRICS_ENABLED'` | 装到了 prerelease；用 `pip install --force-reinstall --no-deps "langgraph-api==0.10.0" "langgraph-runtime-inmem==0.30.0" "langgraph-cli==0.4.29"` 锁定到 stable |
| `starlette` 版本冲突 | Studio CLI 会装 starlette 1.x 但 fastapi 0.112 要 0.38.x；`pip install "starlette>=0.37.2,<0.39.0" --force-reinstall --no-deps` 强制降回 |
| graph 列表为空 | langgraph.json 路径错误；确认 `"./app/services/query_attribute_langgraph.py:studio_graph_factory"` 字面量正确 |

### 3.8 自测脚本

```powershell
cd d:\gitcangku\DB-GPT\tupu\backend
$env:PYTHONUTF8="1"

# 9 个用例（含 HITL Checkpoint）
python tmp_test_lg_query_attribute.py

# 新旧路径回归对比（真调 LLM，慢但可信）
python tmp_test_lg_query_attribute_regress.py
```

### 3.9 LangGraph 学习路径建议

按这个顺序读源码 / 文档：

1. **概念入门**：StateGraph、TypedDict state、reducer 合并语义 — 看 `langgraph_skill_wrapper.SkillNodeFactory.wrap()` 的 return patch 怎么和 state merge
2. **路由 & 条件边**：`add_conditional_edges()` — 看 `query_attribute_langgraph._build_graph()` 的 `_make_router()`
3. **Checkpointer**：BaseCheckpointSaver / InMemorySaver / SqliteSaver — 看 `_get_default_checkpointer()` 和 `get_state` / `get_state_history` / `update_state` 三件套
4. **HITL 模式**：interrupt / resume / fork — 看 `rewind_thread()` 用 `update_state(target_snapshot.config)` 制造 fork 的细节
5. **Studio 调试范式**：0 参 graph factory — 看 `studio_graph_factory()` 为什么用 `_build_graph(db, None, None, with_checkpointer=True)`，db 可以为 None 是什么意思（Studio 只展示拓扑时不需要 DB）

---

## 4. 重启清单（每次开机后）

```powershell
# 1. 基础设施
cd d:\gitcangku\DB-GPT\tupu
docker compose --env-file .env.infra -f docker-compose.infra.yml up -d

# 2. backend
cd backend
$env:PYTHONUTF8="1"
$env:ENABLE_AUTH="1"        # 想测权限就设 1，否则 0
python -m uvicorn app.main:app --host 127.0.0.1 --port 8100 --reload

# 3. frontend（新开窗口）
cd ..\frontend
$env:BROWSER="none"
npm start

# 4. （可选）LangGraph Studio（新开窗口）
cd ..\backend
$env:PYTHONUTF8="1"
$env:LANGSMITH_API_KEY="lsv2_pt_dummy"
langgraph dev --host 127.0.0.1 --port 2024 --no-browser --allow-blocking
```

---

## 5. 关键文件索引

| 类型 | 文件 |
|---|---|
| 基础设施 | [docker-compose.infra.yml](docker-compose.infra.yml) / [.env.infra](.env.infra) |
| Authentik 配置脚本 | [backend/tmp_authentik_bootstrap.py](backend/tmp_authentik_bootstrap.py) |
| Authentik 配置产物 | [backend/authentik_bootstrap.json](backend/authentik_bootstrap.json) |
| 后端权限核心 | [backend/app/core/auth.py](backend/app/core/auth.py) |
| 后端权限模型 | [backend/app/models/auth.py](backend/app/models/auth.py) |
| 后端权限 API | [backend/app/api/auth.py](backend/app/api/auth.py) |
| 前端登录守卫 | [frontend/src/auth/AuthGate.tsx](frontend/src/auth/AuthGate.tsx) |
| 前端 OIDC 流 | [frontend/src/auth/oidc.ts](frontend/src/auth/oidc.ts) |
| 前端用户徽标 | [frontend/src/components/UserBadge.tsx](frontend/src/components/UserBadge.tsx) |
| 资源级 ACL UI | [frontend/src/components/ResourceAclDrawer.tsx](frontend/src/components/ResourceAclDrawer.tsx) |
| LangGraph 主文件 | [backend/app/services/query_attribute_langgraph.py](backend/app/services/query_attribute_langgraph.py) |
| 技能桥接器 | [backend/app/services/langgraph_skill_wrapper.py](backend/app/services/langgraph_skill_wrapper.py) |
| Studio 配置 | [backend/langgraph.json](backend/langgraph.json) |
| Studio 启动脚本 | [backend/scripts/run_langgraph_studio.ps1](backend/scripts/run_langgraph_studio.ps1) |
| 单测脚本 | [backend/tmp_test_lg_query_attribute.py](backend/tmp_test_lg_query_attribute.py) |
| 回归脚本 | [backend/tmp_test_lg_query_attribute_regress.py](backend/tmp_test_lg_query_attribute_regress.py) |

---

> 维护：本手册随 v5 重构一并交付。后续如新增 RBAC 资源类型、LangGraph 化新能力，请在 §2.6 / §3.1 增补。
