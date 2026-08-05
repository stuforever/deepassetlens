# 数据智能对话 - 任务节点与老板状态机设计

> 与 [ENTITY_RELATIONSHIP_MODEL.md](ENTITY_RELATIONSHIP_MODEL.md) 配套。本文档描述 8 个任务节点、9 个技能、LangGraph 老板状态机的协同设计。

## 1. 总体架构

```
            ┌────────────────────────────────────────────────────────┐
            │              用户自然语言（多轮对话）                    │
            └─────────────────────────┬──────────────────────────────┘
                                      ↓
                ┌─────────────────────────────────────────┐
                │  LangGraph StateGraph（老板状态机）        │
                │   • boss_router（老板分派）              │
                │   • 8 个任务节点                         │
                │   • InMemorySaver（持久化秘书态）        │
                └────────────────────┬────────────────────┘
                                     ↓
            ┌────────────────────────────────────────────────────┐
            │  秘书态 SecretaryState（横切关注点）                  │
            │   • 5 个 flag: chain_locked / entity_locked /        │
            │     attribute_locked / relation_locked / sql_executed │
            │   • ConfirmedItems: L1/L2/L2X/L3/L4/L4X/attrs/...   │
            │   • TaskSnapshot[]：每个任务的恢复点                 │
            │   • pending_clarification：HITL 中断 payload         │
            └────────────────────────────────────────────────────┘
                                     ↓
                ┌─────────────────────────────────────────┐
                │  9 个 Skill（复用既有技能框架）          │
                │   S1 大类 → S2 小类 → S3 实体           │
                │   S4 属性                              │
                │   S5 关系 / S6 血缘                     │
                │   S7 SQL 拼装 / S8 SQL 执行            │
                │   S9 路由意图                            │
                └─────────────────────────────────────────┘
```

## 2. 8 个任务节点

| 任务 | 中文名 | 使用技能 | 入口检查 | 完成判定 |
|------|--------|----------|----------|----------|
| 1 | 实体定位 | S1+S2+S3 | entity_locked=False | entity_locked=True |
| 2 | 属性定位 | S4 | entity_locked=True | attribute_locked=True |
| 3 | 关系定位 | S5 | entity_locked=True | relation_locked=True |
| 4 | 溯源定位 | S6 | entity_locked=True | lineage 数据返回 |
| 5 | SQL 拼装 | S7 | entity+attribute 已锁 | assembled_sql 非空 |
| 6 | SQL 执行 | S8 | assembled_sql 已存 | sql_executed=True |
| 7 | 探索 | 动态多技能 | 无前置 | 探索步骤完成 |
| 8 | 兜底 | （无技能） | 无前置 | 弹出任务清单 |

### 2.1 任务 1：实体定位（三级漏斗）

```python
# 入口
if state.entity_locked and (state.confirmed.L2X or state.confirmed.L4X):
    state.mark_task_done("实体定位")
    return state

# 三级漏斗
step1:  S1 → L1/L3（大类）
step2:  S2 → L2/L4（小类，依赖 step1 锁定）
step3:  S3 → L2X/L4X（实体，依赖 step2 锁定）

# 每级处理 3 种状态
locked          → 直接进入下一步
candidates      → pending_clarification（HITL 中断）
needs_clarification → pending_clarification（带具体问题）
```

### 2.2 任务 2：属性定位（双模式）

```
入口：entity_locked=True（前置）
模式：vector_llm（推荐）/ precise（精确）
  vector_llm: 向量召回候选 → LLM 推理锁定
  precise:    直接精确匹配 user_query 与属性名

锁定条件：
  snap.mode ∈ {vector_llm, precise}
  AND state.user_has_selected_fields == True
  AND state.user_selection 非空

HUMAN-IN-THE-LOOP：
  候选列表 → 用户确认 → 设置 user_selection + user_has_selected_fields → 锁定
```

### 2.3-2.8 其他任务节点

详细设计同 1/2，区别在：
- 任务 3/4：前置 entity_locked，输出分别是 relations 和 lineage
- 任务 5：前置 entity+attribute，输出 assembled_sql
- 任务 6：前置 assembled_sql，输出 executed_data
- 任务 7：自由探索，调用 1+ 个技能，不修改秘书态主结构
- 任务 8：兜底，弹出 7 选 1 任务清单

## 3. LangGraph 老板状态机

### 3.1 图结构

```
                START
                  ↓
            ┌──────────────┐
            │  boss_router │  ← 路由决策
            └──────┬───────┘
                   ↓
        ┌──────────┴──────────┐
        ↓          ↓          ↓
    实体定位   属性定位   ...    兜底
        │          │              │
        └──────────┴──────────────┘
                   ↓
        decide_next: pending? → END : boss_router
```

### 3.2 boss_router 决策逻辑

```python
def _decide_from_state(sec, user_input, selection, current) -> str:
    # 1. 用户显式任务切换（go_task_*）
    # 2. 关键词推断（血缘 > 关系 > 属性 > SQL 执行 > SQL 拼装 > 实体 > 探索 > 兜底）
    # 3. 默认：未锁实体 → 实体定位，否则兜底
```

关键词优先级（血缘 > 关系 > 属性 > SQL）：
```python
if "物理表"/"血缘"/"溯源"/"在哪张表" in text:
    return "溯源定位"
if "关系"/"关联"/"和谁" in text:
    return "关系定位"
if "电话"/"字段"/"属性"/"行业"/... in text:
    return "属性定位"
if "执行"/"跑一下"/"跑跑" in text:
    return "SQL 执行"  # 仅当 assembled_sql 已存
if "拼 SQL"/"拼装"/"生成 SQL" in text:
    return "SQL 拼装"  # 仅当 entity+attr 已锁
if "客户"/"设备"/"查一下"/... in text and not entity_locked:
    return "实体定位"
if "随便"/"什么是" in text:
    return "探索"
if not entity_locked:
    return "实体定位"  # 默认入口
return "兜底"
```

### 3.3 HITL 中断

```python
# 任务节点触发
state.pending_clarification = {
    "task": "实体定位",
    "stage": "step1_chain",
    "question": "请选择大类",
    "options": [...],   # 候选列表
}
return state  # 走到 END

# 老板状态机检测到 pending → END → 用户响应 → resume

# 用户响应
state.user_selection = [{...}]
state.user_has_selected_fields = True
# 重新进入任务节点（接续 TaskSnapshot）
```

### 3.4 跨任务切换

```python
# 用户随时可以切换
state.user_selection = [{"value": "go_task_explore"}]
# boss_router 第一分支识别 go_task_*，直接跳转
```

## 4. 秘书态 SecretaryState

### 4.1 5 个 flag

```python
chain_locked      # 大类已锁（L1/L3）
entity_locked     # 实体已锁（L2X/L4X）
attribute_locked  # 属性已锁（attributes 列表非空）
relation_locked   # 关系已锁
sql_executed      # SQL 已执行
```

### 4.2 ConfirmedItems

```python
@dataclass
class ConfirmedItems:
    L1: str | None          # 主数据大类
    L2: str | None          # 主数据小类
    L2X: str | None         # 主实体（主表）
    L2X_related: list       # 关联实体
    L3: str | None          # 业务大类
    L4: str | None          # 业务小类
    L4X: str | None         # 业务实体
    attributes: list        # 已锁字段
    relations: list         # 已锁关系
    assembled_sql: str      # 已拼装 SQL
    sql_execution_result    # 执行结果
```

### 4.3 TaskSnapshot 恢复

```python
@dataclass
class TaskSnapshot:
    task_name: str
    current_stage: str
    status: str          # "init" / "in_progress" / "done" / "needs_clarification"
    started_at: str
    last_updated: str
    # 子类扩展字段（如 EntityLocationSnapshot.stage / step1_result / ...）
```

每个任务节点继承 TaskSnapshot 加字段：
- EntityLocationSnapshot: stage/step1_result/step2_result/step3_result/selected_*
- AttributeLocationSnapshot: mode/candidates/vector_candidates/locked_attributes
- 其他任务节点的快照字段按需扩展

### 4.4 序列化（LangGraph 跨节点）

```python
def secretary_state_to_dict(state) -> dict:
    # 序列化所有字段
    # task_snapshots 通过 __dataclass_fields__ 遍历序列化
    ...

def _sec_from_dict(data) -> SecretaryState:
    # 重建 SecretaryState + ConfirmedItems
    # 用 restore_snapshot_from_dict 重建 task_snapshots
    ...
```

## 5. 测试覆盖

### 5.1 单元测试 15 个（test_all_skills.py）

| # | 技能 | 测试场景 | 状态 |
|---|------|----------|------|
| 1 | S1 | L3 锁定（LLM mock） | ✓ |
| 2 | S1 | 无注入回落 | ✓ |
| 3 | S2 | 给定 L1 找 L2 | ✓ |
| 4 | S3 | 给定 L2 找 L2X | ✓ |
| 5 | S4 | 精确模式定位属性 | ✓ |
| 6 | S4 | 向量化模式 | ✓ |
| 7 | S5 | 主↔关联关系 | ✓ |
| 8 | S5 | 无 LLM 回落 | ✓ |
| 9 | S6 | 三层血缘溯源 | ✓ |
| 10 | S7 | 单表 SQL 拼装 | ✓ |
| 11 | S7 | JOIN SQL 拼装 | ✓ |
| 12 | S8 | SELECT 执行 | ✓ |
| 13 | S8 | 拒绝非 SELECT | ✓ |
| 14 | S9 | LLM 路由到 SQL | ✓ |
| 15 | S9 | 关键词路由 | ✓ |

### 5.2 端到端测试 10 个（test_end_to_end.py）

| # | 场景 | 状态 |
|---|------|------|
| 1 | 完整 happy path（4 轮：实体→属性→拼装→执行） | ✓ |
| 2 | 探索路由 | ✓ |
| 3 | 兜底路由 | ✓ |
| 4 | 显式任务切换 | ✓ |
| 5 | 属性快捷路由 | ✓ |
| 6 | 关系快捷路由 | ✓ |
| 7 | 血缘快捷路由 | ✓ |
| 8 | 跨任务切换（实体→属性→探索→拼 SQL） | ✓ |
| 9 | 澄清恢复（candidates→用户选择→锁定） | ✓ |
| 10 | 推荐下一步 | ✓ |

## 6. 关键技术决策

### 6.1 globals() 注入陷阱

**问题**：`importlib.util.spec_from_file_location` 加载的模块，`globals()` 函数返回的是**测试模块**的 globals，不是被加载模块的 globals。

**解决方案**：每个技能脚本自动注入 `_injected(name)` helper：

```python
import sys as _sys
def _injected(name, default=None):
    mod = _sys.modules.get(__name__)
    return getattr(mod, name, default) if mod else default

# 使用
client = _injected("_llm_client")
```

### 6.2 技能模块单例

**问题**：每次 `_invoke_skill()` 都重新 importlib 加载技能脚本，导致 mock 注入丢失。

**解决方案**：`_get_skill_module()` 缓存到 `_SKILL_LOADERS` dict，并优先复用 `sys.modules` 中已有的同名模块（`{skill_name}_skill_module`）。

### 6.3 任务快照序列化

**问题**：LangGraph 跨节点传递秘书态时，`task_snapshots` 是 dataclass 不可序列化。

**解决方案**：
- `secretary_state_to_dict()` 遍历 `__dataclass_fields__` 序列化所有子字段
- `_sec_from_dict()` 调用 `restore_snapshot_from_dict()` 用 `_create_snapshot()` 工厂 + setattr 重建

## 7. 入口检查模板

每个任务节点的入口检查（防止重入 + 提前返回）：

```python
def 任务节点(state):
    # 1. 任务已完成 → 直接返回
    if state.flag_locked:
        state.mark_task_done("任务名")
        return state
    
    # 2. 前置检查（依赖任务未完成）
    if not state.entity_locked:
        state.pending_clarification = {"task": "...", "stage": "precheck", ...}
        return state
    
    # 3. 用户响应处理（HITL 恢复）
    if state.user_selection and not state.last_task_done:
        # 应用 user_selection 到 secretary
        ...
        return state
    
    # 4. 核心逻辑：调技能 → 处理结果
    ...
```

## 8. 文件清单

| 路径 | 作用 |
|------|------|
| `backend/data/skills/{S1-S9}/scripts/main.py` | 9 个技能（既有框架） |
| `backend/app/services/secretary_state.py` | SecretaryState 数据类 + 序列化 |
| `backend/app/services/data_intelligence_skills_bootstrap.py` | 9 个技能的 bootstrap 注册 |
| `backend/app/services/data_intelligence_graph.py` | LangGraph 老板状态机 |
| `backend/app/services/tasks/entity_location.py` | 任务 1 节点 |
| `backend/app/services/tasks/attribute_location.py` | 任务 2 节点 |
| `backend/app/services/tasks/relation_location.py` | 任务 3 节点 |
| `backend/app/services/tasks/lineage_location.py` | 任务 4 节点 |
| `backend/app/services/tasks/sql_assembly.py` | 任务 5 节点 |
| `backend/app/services/tasks/sql_execution.py` | 任务 6 节点 |
| `backend/app/services/tasks/exploration.py` | 任务 7 节点 |
| `backend/app/services/tasks/fallback.py` | 任务 8 节点 |
| `test_all_skills.py` | 15 个技能单元测试 |
| `test_end_to_end.py` | 10 个端到端集成测试 |
| `fix_injected.py` | 批量修复 globals() 注入问题 |
| `docs/ENTITY_RELATIONSHIP_MODEL.md` | 业务框架（5 levels + 3 entities + 3 relations） |

## 9. 后续工作

- [ ] S9 route_intent 升级：把当前的关键词+L1/L3 路由替换为正式的任务分派模式
- [ ] 老板状态机升级：增加"记忆与推荐"模块，主动根据 secretary_state 推荐下一步
- [ ] 任务 7 探索节点的 LLM 决策：当前是硬编码链路，应改为 LLM 决策调用哪些技能
- [ ] API 层：把 LangGraph 状态图暴露为 REST/WebSocket 接口
- [ ] 数据库持久化：当前 InMemorySaver，应替换为 SqliteSaver / PostgresSaver
- [ ] 沙箱执行：`_invoke_skill` 当前是本地直连，应走 ExecutionEngineV2.execute_by_code