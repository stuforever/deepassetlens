# 能力开关中心 + subagents 受限启用 详细设计（批13-Q）

> 2026-08-24 · 设计窗口产出
> 用户定调：①所有 DeepAgents 能力做控制开关，按需增减；②subagents 翻案启用（受限模式）。
> 本批 = 批13-F（原生全量启用）的**运行时控制面**：F 项落地时即按 capability 开关装配，避免二次改造。
> 依赖：批13-E'（守卫管道先就位，子代理才有守卫传导链路）。

---

## 一、控制模型总览

```
安全控制中心（一个管理页，双 Tab）
├── Tab1 安全控制   —— 五类守卫 + 审批轨（批13-E'，已设计）
└── Tab2 能力开关   —— 14 个可切能力 + 4 项灰显锁定（本批）
        每项五件套：开关 + 三段式说明 + 统计 + 探针 + 参数区
        开关效果直达 Agent 装配：capability_version 变 -> 单例缓存键失配 -> 重建
```

两类生效路径：
- **装配类**（skills/filesystem_tools/memory/summarization/rubric/patch_tool_calls/message_eviction/response_format/subagents/permissions/debug）-> version+1 -> agent 重建（缓存键见 §四）；
- **运行时类**（store 读取）-> TTL 5s 缓存刷新，不重建。

## 二、数据模型

```sql
CREATE TABLE capability_policies (
  capability_id    VARCHAR(64) PRIMARY KEY,
  title            VARCHAR(64) NOT NULL,
  enabled          BOOLEAN     NOT NULL DEFAULT TRUE,   -- 默认基线=全开（批13-F 全量启用定调）
  params           JSON        NULL,      -- subagents:{"specs":[...],"max_concurrent":2}
                                            -- response_format:{"schema":"final"}
                                            -- store:{"max_prefs":5}
  risk_level       VARCHAR(8)  NOT NULL DEFAULT 'yellow',
  description      JSON        NULL,      -- {what,lose,remain} 三段式
  confirm_required BOOLEAN     NOT NULL DEFAULT TRUE,
  physical_blocked BOOLEAN     NOT NULL DEFAULT FALSE,  -- 灰显锁定项标记
  blocked_reason   VARCHAR(255) NULL,
  updated_by VARCHAR(64) NULL, updated_at DATETIME NULL,
  close_reason VARCHAR(500) NULL, version INT NOT NULL DEFAULT 1
);

CREATE TABLE capability_events (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  capability_id VARCHAR(64) NOT NULL, ts DATETIME NOT NULL,
  action VARCHAR(16) NOT NULL,     -- toggle|rebuild|probe|task_invoke|task_reject|spec_invalid
  detail JSON NULL,                -- {actor,reason,spec_name,duration_ms,result_digest}
  updated_by VARCHAR(64) NULL
);
```

**种子数据**（迁移内置，16 行）：

| capability_id | 默认 | 风险级 | 说明要点 |
|---|---|---|---|
| skills / filesystem_tools / memory / summarization / rubric / patch_tool_calls / message_eviction / response_format / store / permissions / debug / approval_track | 开 | 🟡/🟢 | 各框架件，三段说明按能力全景盘点填写 |
| **subagents** | **开**（受限） | 🔴 | 见 §五 |
| prompt_caching、video、local_shell、sandbox | 锁 | ⛔ | physical_blocked=TRUE：Anthropic 专属/域无关/安全红线，PATCH 一律 403 |

## 三、API（`app/api/capabilities.py`，与 guards.py 同构）

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/capabilities` | GET | items（含 stats：探针通过率/最近 task_invoke 数）+ capability_version |
| `/api/capabilities/{id}` | PATCH | `{enabled?,params?,confirm:true,close_reason?}`；🔴 需 close_reason；**params 前置校验**（subagent 规格工具交集非空、schema 名合法），非法 -> 400 且不落库 |
| `/api/capabilities/{id}/probe` | POST | 探针执行（§六），写 events |
| `/api/capabilities/events` | GET | 分页（含 task_invoke 审计流） |
| `/api/capabilities/reset-defaults` | POST | 全部回基线，version+1 |

权限同 guards：非 admin 只读，写操作 403。

## 四、装配改造与单例缓存键（核心工程件）

### 4.1 装配函数条件化（tupu_deepagent.py 改造）

```python
def _build_agent(model, caps):                    # caps = capability_config.get_policies()
    middleware_list = []
    if caps["skills"].enabled:              middleware_list.append(SkillsMiddleware(skills=SKILLS_DIR))
    if caps["filesystem_tools"].enabled:    middleware_list.append(FilesystemMiddleware(backend=fs_backend,
                                                              permissions=PERM if caps["permissions"].enabled else None))
    if caps["memory"].enabled:              middleware_list.append(MemoryMiddleware(...))
    if caps["summarization"].enabled:       middleware_list.append(SummarizationMiddleware(model, trigger=30_000))
    if caps["rubric"].enabled:              middleware_list.append(_TupuRubricMiddleware(...))
    if caps["patch_tool_calls"].enabled:    middleware_list.append(PatchToolCallsMiddleware())
    subagents = build_subagent_specs(caps["subagents"]) if caps["subagents"].enabled else None
    response_format = SCHEMAS[caps["response_format"].params["schema"]] if caps["response_format"].enabled else None
    return create_deep_agent(model=..., middleware=middleware_list, subagents=subagents,
                             response_format=response_format, store=store_if(caps), ...)
```

### 4.2 缓存键与 LRU

```
agent_cache_key = f"{provider}:{model}:caps{capability_version}"
```
- version 变化 -> 新 key 建新实例；旧实例保留（在跑的请求不断），**LRU 保留最近 2 个版本**后回收；
- 每次因 version 失配重建 -> 写 capability_events(rebuild)；**装配失败 fail-safe**：新装配异常时回退上一可用版本装配并告警（配置写坏不至于全瘫，与 PATCH 前置校验双保险）；
- 批13-N6 预热任务改按当前 capability_version 键预热。

## 五、subagents 受限启用（四护栏）

### 5.1 委派规格（数据化，capability_policies.params.specs）

```yaml
specs:
  - name: entity_locator              # 首发规格：并行实体定位（批13-M 定位优先流程的加速器）
    description: 按业务域并行定位实体表，返回候选清单（code/name/引擎/置信度）
    prompt: 只做实体定位与校验，不做 SQL 拼装，不做跨域推断，不超出给定工具。
    tools: [search_entities, fetch_l1_l2_tree, validate_l2, fetch_subgraph]
max_concurrent: 2
```
新增规格=改配置不改代码（PATCH params，前置校验）。

### 5.2 四护栏实现

| # | 护栏 | 实现点 |
|---|---|---|
| 1 | **task 入白名单复合条件** | QueryContract 加 `allow_subagents` 字段：generic/探索默认 True，场景默认 False；场景剧本 SKILL.md `x_tupu.allow_subagents: true` 可显式开（数据化）。run_guards 能力检查：`task 调用 -> caps.subagents.enabled AND contract.allow_subagents` 才放行 |
| 2 | **子代理继承守卫** | 子代理与父代理同栈装配（声明式 SubAgent 规格在父图内编译，共享中间件链）；验收用「子代理工具调用产生 guard_events」证明传导 |
| 3 | **工具白名单窄化** | 装配时 `specs.tools ∩ 全局工具注册表`，交集为空 -> 该规格拒装配+spec_invalid 事件；子代理工具集是全局白名单的子集 |
| 4 | **全程审计** | SkillPolicy 捕获 task 调用 -> capability_events(task_invoke/task_reject, detail 含规格名/耗时/结果摘要) |

### 5.3 降级语义

subagents 关闭或护栏拒绝时，模型回退串行定位（现有链路不变）--委派是加速器不是依赖项，任何失败不阻断主流程。

## 六、探针清单

| capability | 探针 | 预期 |
|---|---|---|
| skills/filesystem_tools/memory/summarization/rubric/patch_tool_calls/message_eviction/permissions/debug | 装配断言：当前 agent 装配清单含/不含该组件 | probe_ok/fail |
| response_format | 断言 agent 配置的 response_format 非 None | probe_ok/fail |
| store | 测试命名空间偏好写-读-删 roundtrip | probe_ok/fail |
| subagents-① | task 携带越权工具规格（含 write_file） | 拒绝 + task_reject（护栏3） |
| subagents-② | task 合法规格 entity_locator 轻量定位一跑 | 窄代理返回候选（护栏1/2 生效即全绿） |

探针直调装配断言/窄代理，不走 LLM 主链路；结果全部写 events，作为「开关不是摆设」的凭证。

## 七、前端（安全控制中心页 Tab2）

```
Tab「能力开关」
├── 顶栏：capability_version v{n} · [全部恢复默认] · 变更尾巴条（toggle/rebuild 最近5条）
├── 可切能力卡 ×14（五件套同款）
│    subagents 卡片特殊：风险🔴徽标 + 参数区=规格编辑器
│    （规格列表 + JSON/YAML 编辑 textarea + 校验按钮 + max_concurrent 步进器）
└── 灰显锁定区 ×4（prompt_caching/video/local_shell/sandbox）：开关禁用 + 原因 Tooltip
```

## 八、e2e 验收（Playwright 串行）

1. 能力 Tab：14 可切 + 4 灰显锁定（含原因）；
2. 关 skills -> 探针 fail + 下一问题装配无 SkillsMiddleware；重开恢复；
3. subagents off：generic 题模型侧无 task 工具；on：探索题委派 entity_locator 并行定位，events 有 task_invoke；
4. task 越权工具规格 -> 拒绝 + task_reject 事件；
5. 场景契约默认无 task；SKILL.md 声明 allow_subagents 后可用（护栏1 数据化验证）；
6. 子代理工具调用在守卫面拦截统计可见（护栏2 传导）；
7. capability_version 变更 -> rebuild 事件 + 旧版本 LRU 回收；
8. PATCH 非法规格 -> 400 不落库；装配 fail-safe：人为写坏配置 -> 自动回退上一装配 + 告警；
9. 全部恢复默认 -> 16 行回基线；非 admin 写操作 403。

## 九、排期与依赖

| 件 | 量级 |
|---|---|
| 表+API+前置校验 | 0.5d |
| 装配函数条件化 + 缓存键/LRU/fail-safe + 预热联动 | 1d |
| 前端能力 Tab（含规格编辑器） | 0.5d |
| subagents 规格构建器 + 四护栏 + 审计 | 1d |
| 探针全枚 | 0.5d |
| **合计** | **3.5d** |

依赖：批13-E'（守卫管道与页面骨架）；与批13-F 合并执行（F 的每项启用直接按 capability 默认值装配，一次到位不返工）。
