# 智能体技能管理平台 - 技能模块技术设计文档 (v2 修正版)

## 一、项目概述

| 项目信息 | 内容 |
|---------|------|
| 项目名称 | 智能体技能管理平台 |
| 技术栈 | Python / FastAPI / SQLAlchemy / PostgreSQL |
| 设计模式 | 数据库驱动、版本化管理、标准JSON Schema |

---

## 二、总体架构

```
┌─────────────────────────────────────────────────────┐
│                   前端展示层                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │技能列表   │  │技能编辑器  │  │版本管理  │  │执行监控  │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────┘
                              ↓ RESTful API (v2)
┌─────────────────────────────────────────────────────┐
│                   Controller层（FastAPI Router）       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │Skill CRUD │  │Version   │  │Execution │  │Tool Call │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────┐
│                   Service层（业务逻辑）                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │SkillSvc  │  │VersionSvc│  │ExecSvc   │            │
│  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────┘
                              ↓ ORM（SQLAlchemy）
┌─────────────────────────────────────────────────────┐
│                   数据模型层                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ Skill     │  │SkillVersion│  │SkillExecLog│       │
│  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────┘
                              ↓ PostgreSQL
┌─────────────────────────────────────────────────────┐
│                   持久存储层                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │ skills    │  │skill_versions│  │skill_exec_logs│  │
│  └──────────┘  └──────────┘  └──────────┘            │
└─────────────────────────────────────────────────────┘
```

---

## 三、数据库表设计

### 3.1 skills 表（技能主表）

| 字段名 | 类型 | 说明 | 默认值 | 约束 |
|---------|------|------|--------|--------|
| skill_id | UUID | 主键 | uuid.uuid4() | PK |
| skill_code | String(100) | 技能唯一代码 | auto-generate | UNIQUE, NOT NULL |
| name | String(255) | 技能名称 | - | NOT NULL |
| description | Text | 技能描述 | - | NULL |
| skill_type | String(50) | 技能类型 | - | NOT NULL | natural\|python\|sql\|http\|mixed |
| status | String(20) | 状态 | 'draft' | NOT NULL | draft\|published\|disabled |
| current_version_id | UUID | 当前版本ID | NULL | 无ForeignKey | Service层保证一致性 |
| tags | JSON | 标签列表 | '[]'::jsonb | NULL | ["tag1","tag2"] |
| priority | Integer | 优先级 | 0 | >= 0 | - |
| timeout | Integer | 超时时间（秒） | 30 | >= 0 | - |
| retry_policy | JSON | 重试策略 | '{"max_retries":0,"retry_delay":1}'::jsonb | NOT NULL | - |
| resource_limits | JSON | 资源限制 | '{"memory_mb":512,"timeout_seconds":30}'::jsonb | NOT NULL | - |
| **permissions** | **JSON** | **权限配置（含risk_level）** | **'{"network":true,"filesystem":false,"shell":false,"risk_level":"low","allowed_env":[]}'::jsonb** | **NOT NULL** | **risk_level: low\|medium\|high** |
| app_type | String(50) | 应用类型 | NULL | NULL | smart_join\|smart_lineage\|smart_qa |
| target_menu | String(50) | 目标菜单 | NULL | NULL | connection\|query\|dashboard |
| workspace_id | UUID | 工作区ID | NULL | NULL | - |
| created_at | DateTime | 创建时间 | now() | - | - |
| updated_at | DateTime | 更新时间 | now() | - | onupdate |
| created_by | String(100) | 创建人 | NULL | - | - |
| updated_by | String(100) | 更新人 | NULL | - | - |

**已移除字段**（GLM评审意见）：
- ~~skill_code_lower~~：在Service层通过 `.lower()` 处理
- ~~labels~~：从未讨论过，不添加
- ~~search_vector~~：从未讨论过，不添加

**索引**：
- idx_skills_current_version (current_version_id)
- idx_skills_status_priority (status, priority)
- idx_skills_tags_gin (tags) - GIN索引

**外键策略**：
- current_version_id：普通UUID列，**不加ForeignKey**（避免循环依赖），Service层保证一致性

---

### 3.2 skill_versions 表（技能版本表）

| 字段名 | 类型 | 说明 | 默认值 | 约束 |
|---------|------|------|--------|--------|
| version_id | UUID | 主键 | uuid.uuid4() | PK |
| skill_id | UUID | 技能ID | - | NOT NULL, FK->skills (ON DELETE CASCADE) |
| version | String(20) | 版本号 | - | NOT NULL | 1.0.0, 1.1.0 |
| status | String(20) | 版本状态 | 'draft' | NOT NULL | **draft\|active\|archived** |
| input_schema | JSON | 输入Schema | '{"type":"object","properties":{},"required":[]}'::jsonb | NOT NULL | - |
| output_schema | JSON | 输出Schema | '{"type":"object","properties":{}}'::jsonb | NOT NULL | - |
| content | JSON | 技能内容（统一字段） | **'{}'::jsonb** | NOT NULL | **schema_version在content内部** |
| dependencies | JSON | 依赖配置 | '{"pip":[],"apt":[],"env_vars":{}}'::jsonb | NOT NULL | - |
| changelog | Text | 变更日志 | NULL | NULL | - |
| released_by | String(100) | 发布人 | NULL | - | - |
| released_at | DateTime | 发布时间 | NULL | - | - |
| created_at | DateTime | 创建时间 | now() | - | - |
| created_by | String(100) | 创建人 | NULL | - | - |

**修正说明**（GLM评审）：
- **status** 值从 `draft|released|archived` 改为 `draft|active|archived`
- **content.server_default** 从 `'{"schema_version":"1.0"}'::jsonb` 改为 `'{}'::jsonb`，schema_version在content JSON内部动态管理

**索引**：
- uq_skill_version (skill_id, version) - 唯一约束
- idx_skill_versions_status (skill_id, status)
- idx_skill_versions_input_schema_gin (input_schema) - GIN索引
- idx_skill_versions_output_schema_gin (output_schema) - GIN索引

---

### 3.3 skill_exec_logs 表（执行日志表）

| 字段名 | 类型 | 说明 | 默认值 | 约束 |
|---------|------|------|--------|--------|
| log_id | UUID | 主键 | uuid.uuid4() | PK |
| version_id | UUID | 版本ID | NULL | FK->skill_versions (ON DELETE SET NULL) |
| skill_id | UUID | 技能ID | NULL | FK->skills (ON DELETE SET NULL) |
| execution_code | String(100) | 执行代码 | auto-generate | INDEX |
| input_data | JSON | 输入数据 | NULL | - |
| output_data | JSON | 输出数据 | NULL | - |
| status | String(20) | 执行状态 | - | NOT NULL | success\|failed\|timeout\|cancelled |
| error_message | Text | 错误信息 | NULL | - |
| duration_ms | Integer | 执行时长 | NULL | >= 0 |
| environment | JSON | 执行环境 | NULL | - |
| created_via | String(20) | 创建来源 | 'manual' | NOT NULL | manual\|agent\|workflow\|schedule |
| stack_info | JSON | 执行栈信息 | NULL | - |
| started_at | DateTime | 开始时间 | now() | - |
| completed_at | DateTime | 完成时间 | NULL | - |

**索引**：
- idx_exec_logs_status_time (status, started_at)
- idx_exec_logs_created_via_time (created_via, created_at)
- CheckConstraint: created_via IN ('manual', 'agent', 'workflow', 'schedule')

---

## 四、Content字段统一设计

### 4.1 Python技能
```json
{
  "schema_version": "1.0",
  "script": "def execute(inputs: dict) -> dict:\n    result = inputs.get('query', '')\n    return {'result': result}",
  "entrypoint": "execute"
}
```

### 4.2 自然语言技能
```json
{
  "schema_version": "1.0",
  "prompt": "你是一个智能助手，请帮我处理以下内容：{{input}}"
}
```

### 4.3 SQL技能
```json
{
  "schema_version": "1.0",
  "sql": "SELECT * FROM users WHERE name = :name",
  "database": "main_db"
}
```

### 4.4 HTTP技能
```json
{
  "schema_version": "1.0",
  "method": "POST",
  "url": "https://api.example.com/endpoint",
  "headers": {
    "Content-Type": "application/json"
  },
  "body_template": "{\"query\": \"{{input}}\"}",
  "auth": {
    "type": "bearer",
    "token_ref": "{{env.API_KEY}}"
  }
}
```

### 4.5 混合技能（mixed）
```json
{
  "schema_version": "1.0",
  "steps": [
    {
      "step_id": "step1",
      "type": "sql",
      "skill_code": "query_data",
      "input_mapping": {
        "table": "{{input.table}}"
      }
    },
    {
      "step_id": "step2",
      "type": "python",
      "skill_code": "process_data",
      "input_mapping": {
        "data": "{{step1.output}}"
      }
    }
  ]
}
```
**说明**：mixed类型通过 `skill_code` **引用**其他技能，不直接嵌入内容。

---

## 五、API接口规范 (v2 资源导向)

### 5.1 Skill 主表 API

| 方法 | 路径 | 说明 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| GET | /api/v2/skills | 列表 | Query: status, skill_type, skip, limit | APIResponse + skills数组 |
| POST | /api/v2/skills | 创建 | SkillCreateRequest | APIResponse + skill_id |
| GET | /api/v2/skills/{skill_id} | 详情 | - | APIResponse + skill详情 |
| PUT | /api/v2/skills/{skill_id} | 更新 | SkillUpdateRequest | APIResponse + skill_id |
| DELETE | /api/v2/skills/{skill_id} | 删除 | - | APIResponse + message |
| GET | /api/v2/skills/by-code/{skill_code} | 通过代码获取 | - | APIResponse + skill详情 |

### 5.2 Version 版本 API

| 方法 | 路径 | 说明 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| GET | /api/v2/skills/{skill_id}/versions | 版本列表 | Query: status | APIResponse + versions数组 |
| POST | /api/v2/skills/{skill_id}/versions | 创建版本 | VersionCreateRequest | APIResponse + version_id |
| GET | /api/v2/skills/{skill_id}/versions/{version} | 版本详情 | - | APIResponse + version详情 |
| POST | /api/v2/skills/{skill_id}/versions/{version}/publish | 发布版本 | - | APIResponse + status |

**修正说明**（GLM评审）：
- **删除**单独的 activate_version 操作，合并到 publish 中
- publish 同时完成：1) 旧active→archived 2) 当前版本→active 3) 更新 skill.current_version_id

### 5.3 Execution 执行 API (资源导向)

| 方法 | 路径 | 说明 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| POST | /api/v2/skills/{skill_id}/executions | **创建执行** | ExecutionCreateRequest | APIResponse + execution_code |
| GET | /api/v2/skills/{skill_id}/executions | 执行历史 | Query: status, skip, limit | APIResponse + executions数组 |
| GET | /api/v2/skills/executions/{execution_code} | 执行详情 | - | APIResponse + execution详情 |

**修正说明**（GLM评审）：
- ~~POST /skills/{id}/execute~~ → **POST /skills/{id}/executions**（资源导向，非动词）
- 执行作为资源创建，返回 execution_code

### 5.4 Tool Calling API

| 方法 | 路径 | 说明 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| GET | /api/v2/tools | 获取工具列表 | Query: skill_type, app_type | APIResponse + tools数组(OpenAI格式) |

**修正说明**（GLM评审）：
- get_tools 是纯读操作，**放在API层**，不通过执行引擎
- 直接调用 Service 读取已发布的技能

---

## 六、Service层设计

### 6.1 SkillService

```python
class SkillService:
    @staticmethod
    def generate_skill_code(name: str) -> str:
        """生成技能代码（转为小写，支持大小写不敏感）"""
        # 返回 .lower() 后的代码
        pass

    @staticmethod
    def create_skill(db: Session, data: dict) -> Skill:
        """创建技能，skill_code 存储时自动 to_lower()"""
        pass

    @staticmethod
    def get_skill(db: Session, skill_id: UUID) -> Optional[Skill]:
        pass

    @staticmethod
    def get_skill_by_code(db: Session, skill_code: str) -> Optional[Skill]:
        """查询时 skill_code.lower()"""
        pass

    @staticmethod
    def list_skills(...) -> List[Skill]:
        pass

    @staticmethod
    def update_skill(db: Session, skill_id: UUID, data: dict) -> Skill:
        pass

    @staticmethod
    def delete_skill(db: Session, skill_id: UUID):
        pass
```

### 6.2 VersionService

```python
class VersionService:
    @staticmethod
    def create_version(db: Session, skill_id: UUID, data: dict) -> SkillVersion:
        """创建新版本，**复制所有内容字段**（包括permissions, content等）"""
        pass

    @staticmethod
    def publish_version(db: Session, version_id: UUID, released_by: str) -> SkillVersion:
        """
        发布版本（合并激活操作）
        1. 旧 active → archived
        2. 当前版本 → active
        3. 更新 skill.current_version_id
        4. 更新 skill.status = 'published'
        """
        pass

    @staticmethod
    def get_version(db: Session, version_id: UUID) -> Optional[SkillVersion]:
        pass

    @staticmethod
    def list_versions(db: Session, skill_id: UUID, status: Optional[str]) -> List[SkillVersion]:
        pass
```

**修正说明**：
- ~~activate_version~~ 已删除，功能合并到 publish_version
- create_version 必须**完整复制所有内容字段**

### 6.3 ExecutionService

```python
class ExecutionService:
    @staticmethod
    def create_execution(...) -> SkillExecLog:
        """创建执行记录"""
        pass

    @staticmethod
    def complete_execution(...):
        """完成执行"""
        pass

    @staticmethod
    def get_execution(db: Session, execution_code: str) -> Optional[SkillExecLog]:
        pass

    @staticmethod
    def list_executions(...) -> List[SkillExecLog]:
        pass
```

---

## 七、数据库DDL（PostgreSQL）

### 7.1 skills表
```sql
CREATE TABLE skills (
    skill_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    skill_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    current_version_id UUID,  -- 无ForeignKey，Service层保证一致性
    tags JSONB DEFAULT '[]'::jsonb,
    priority INTEGER DEFAULT 0,
    timeout INTEGER DEFAULT 30,
    retry_policy JSONB DEFAULT '{"max_retries":0,"retry_delay":1}'::jsonb NOT NULL,
    resource_limits JSONB DEFAULT '{"memory_mb":512,"timeout_seconds":30}'::jsonb NOT NULL,
    permissions JSONB DEFAULT '{"network":true,"filesystem":false,"shell":false,"risk_level":"low","allowed_env":[]}'::jsonb NOT NULL,
    app_type VARCHAR(50),
    target_menu VARCHAR(50),
    workspace_id UUID,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skills_current_version ON skills(current_version_id);
CREATE INDEX idx_skills_status_priority ON skills(status, priority);
CREATE INDEX idx_skills_tags_gin ON skills USING gin(tags);
```

### 7.2 skill_versions表
```sql
CREATE TABLE skill_versions (
    version_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_id UUID NOT NULL REFERENCES skills(skill_id) ON DELETE CASCADE,
    version VARCHAR(20) NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',
    input_schema JSONB DEFAULT '{"type":"object","properties":{},"required":[]}'::jsonb NOT NULL,
    output_schema JSONB DEFAULT '{"type":"object","properties":{}}'::jsonb NOT NULL,
    content JSONB DEFAULT '{}'::jsonb NOT NULL,  -- schema_version在content内部
    dependencies JSONB DEFAULT '{"pip":[],"apt":[],"env_vars":{}}'::jsonb NOT NULL,
    changelog TEXT,
    released_by VARCHAR(100),
    released_at TIMESTAMP WITH TIME ZONE,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_skill_version UNIQUE (skill_id, version)
);

CREATE INDEX idx_skill_versions_status ON skill_versions(skill_id, status);
CREATE INDEX idx_skill_versions_input_schema_gin ON skill_versions USING gin(input_schema);
CREATE INDEX idx_skill_versions_output_schema_gin ON skill_versions USING gin(output_schema);
```

### 7.3 skill_exec_logs表
```sql
CREATE TABLE skill_exec_logs (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    version_id UUID REFERENCES skill_versions(version_id) ON DELETE SET NULL,
    skill_id UUID REFERENCES skills(skill_id) ON DELETE SET NULL,
    execution_code VARCHAR(100) NOT NULL,
    input_data JSONB,
    output_data JSONB,
    status VARCHAR(20) NOT NULL,
    error_message TEXT,
    duration_ms INTEGER,
    environment JSONB,
    created_via VARCHAR(20) DEFAULT 'manual' NOT NULL,
    stack_info JSONB,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT ck_exec_logs_created_via CHECK (created_via IN ('manual', 'agent', 'workflow', 'schedule'))
);

CREATE INDEX idx_exec_logs_status_time ON skill_exec_logs(status, started_at);
CREATE INDEX idx_exec_logs_created_via_time ON skill_exec_logs(created_via, started_at);
CREATE INDEX idx_exec_logs_execution_code ON skill_exec_logs(execution_code);
```

---

## 八、评审修正记录

### 8.1 GLM评审修正（已落地）

| # | 问题 | 修正前 | 修正后 |
|---|------|--------|--------|
| 1 | schema_version位置 | content server_default 硬编码 | content动态管理，server_default为'{}' |
| 2 | risk_level位置 | 已正确在permissions内，加强验证 | 保持现状，文档明确说明 |
| 3 | 未审批字段 | 添加了search_vector, labels | 已移除 |
| 4 | activate_version方法 | 单独存在activate_version | 删除，合并到publish_version |
| 5 | skill_code大小写 | 未做to_lower处理 | Service层生成和查询都to_lower() |
| 6 | API路由设计 | 使用/execute动词 | 改为/executions资源导向 |
| 7 | get_tools位置 | 放在执行引擎层 | 移到API层，纯读操作 |

### 8.2 豆包评审修正（已落地）

| # | 问题 | 修正 |
|---|------|------|
| 1 | risk_level | 确认在permissions JSON内部，不移到SkillVersion |
| 2 | current_version_id | 不加ForeignKey，Service层保证一致性 |
| 3 | mixed类型 | 通过skill_code引用其他技能，不直接嵌入 |
| 4 | HTTP auth校验 | 在content.auth中配置，执行引擎校验 |

---

## 九、实施阶段计划

### Phase 1: 数据模型（已完成）
- [x] 修正 Skill 模型（移除多余字段，调整permissions）
- [x] 修正 SkillVersion 模型（content.server_default, status值）
- [x] 确认 SkillExecLog 模型

### Phase 2: Service层（已完成）
- [x] SkillService（含generate_skill_code to_lower）
- [x] VersionService（含publish_version，无activate_version）
- [x] ExecutionService

### Phase 3: API层（已完成）
- [x] /skills CRUD
- [x] /skills/{id}/versions
- [x] /skills/{id}/executions（资源导向）
- [x] /tools（Tool Calling接口）

### Phase 4: 执行引擎（待实现）
- [ ] Python技能执行器
- [ ] SQL技能执行器
- [ ] HTTP技能执行器
- [ ] Mixed技能执行器（DAG编排）
- [ ] 调度中枢集成

### Phase 5: 前端适配（待实现）
- [ ] 技能编辑器（支持JSON Schema编辑）
- [ ] 版本管理界面
- [ ] 执行监控界面
- [ ] Tool Calling测试界面

---

文档版本：v2.0（GLM+豆包评审修正版）  
更新时间：2026-04-23
