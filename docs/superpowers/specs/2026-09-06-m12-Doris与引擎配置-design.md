# M12 Doris 与引擎配置 设计规格（金标准）

> 套件：DeepAssetLens 全量金标准 M12（总纲见 m00）。as-if-greenfield 视角。
> 取证基线：HEAD `0d67f4c`（2026-09-06）。本模块改动须先过两技能管线并回写本 spec 状态。

## 一、模块定位

系统配置域的引擎面：**Doris 连接单例配置**（首行即生效）、**Doris Catalog 联邦目录管理**（jdbc/es/internal 三型——跨源联邦的声明面）、**引擎健康探测**（doris/duckdb/pg 三引擎，缓存快照）。是 M21 引擎执行与 M06 数据源联邦前缀的配置底座。

**边界**：引擎执行与加速器归 M21；引擎观测端点归 M22；本模块只管配置与探活。

## 二、组件清单

| 组件 | 文件 | 职责 |
|---|---|---|
| Doris 配置 API | `app/api/doris_config.py` | config GET/PUT/test + catalogs 管理（8 端点） |
| 引擎健康 | `app/services/engine_health.py` | 三引擎探针+60s 缓存快照 |
| 模型 | kg_doris_config（单例）、kg_doris_catalog | 连接/联邦目录 |
| 前端 | `pages/DorisConfig.tsx` | 配置+目录管理页 |

## 三、Doris 连接单例（kg_doris_config）

**单例契约**（L605 docstring）：表内**首行为当前生效配置**——无 id 选择逻辑，first row wins。列：host（localhost）/port（9030）/user（root）/password（空默认）/database（test_db）/charset（utf8mb4）/connect_timeout（10s）。

**端点**：`GET /doris/config`（读首行，无则建默认行）/ `PUT /doris/config`（更新首行）/ `POST /doris/config/test`（连通测试）。

## 四、Doris Catalog 联邦目录（kg_doris_catalog）

> docstring：「Doris Catalog 定义（jdbc/es 联邦，便于 UI 创建/编辑/重建）」

| catalog_type | 关键列 | 用途 |
|---|---|---|
| `jdbc` | jdbc_url/jdbc_user/jdbc_password/driver_class/driver_url | 联邦外部关系库（如 PG pg_tupu） |
| `es` | es_hosts（逗号分隔）/es_user/es_password（P4 增列） | 联邦 ES |
| `internal` | （无外部参数） | Doris 内部库 |

**端点**：`GET /doris/catalogs`（清单）/ `POST /doris/catalogs`（创建=在 Doris 侧建 catalog）/ `POST /doris/catalogs/{name}/probe`（探测可用性）/ `POST /doris/catalogs/{name}/refresh`（元数据刷新）/ `DELETE /doris/catalogs/{name}`（删除）。

**消费方**：M06 DataSourceConfig.doris_catalog_name 引用此处 catalog 名（三段命名前缀 `catalog.database.table`）；M21 引擎执行按 catalog 路由联邦查询。

## 五、引擎健康探测（engine_health.py）

- **三探针**：`_probe_doris` / `_probe_duckdb` / `_probe_pg`（注册表 `_PROBES`）；
- **缓存**：60s TTL + 线程锁——`probe(engine, force=False)`（force 穿透缓存）/ `snapshot()`（全引擎快照）/ `invalidate(engine=None)`（失效重探）；
- 消费方：M21 执行前引擎选择、M22 观测面板（含启动期 TUPU_VECTOR_BACKEND 类决策模式的引擎面）。

## 六、设计原则（本模块特有）

1. **单例即契约**：Doris 连接首行生效——禁止多行并存（PUT 只改首行）；若需多 Doris 集群须先过设计（改表结构）；
2. **联邦声明化**：跨源联邦=声明 catalog（UI 建/探/刷/删），执行层零代码——与 M07「配置驱动」同宗；
3. **探测缓存**：健康检查 60s 缓存防探针风暴；force 供手动刷新；
4. **凭据现状明文**：Doris/Catalog 密码列明文（与 M06 同风险面，统一登记）。

## 七、验收标准

1. config：GET 无行时建默认行；PUT 后全局连接立即生效（M21 联测）；test 坏配置结构化错误；
2. catalogs：三型创建/探测/刷新/删除全链（jdbc/es 参数列正确落库）；重名 400；
3. engine_health：三引擎 probe 结果缓存（60s 内重复探测零额外连接）；force 穿透；invalidate 后重探；snapshot 汇总三引擎；
4. 与 M06 联测：数据源 doris_catalog_name 指向的 catalog 存在且可探测；
5. 与 M21 联测：联邦查询走声明的 catalog（三段命名）。

## 八、风险与偏差登记

| 项 | 说明 |
|---|---|
| 单例无唯一性保护 | 首行契约靠约定（无部分唯一约束）——多行插入会静默漂移；建议约束（登记） |
| 凭据明文 | Doris/catalog 密码列明文（与 M06 password 同批风险）——统一生产化批次处理 |
| es_hosts P4 列 | ES catalog 较新（P4 批次）——es 联邦路径联测覆盖度登记 |

**偏差登记**：
| 日期 | 差异 | 处置 |
|---|---|---|
| 2026-09-08 | 批次核验通过（验证-对齐主路径）：doris_config 8 端点+engine_health 三探针/_PROBES 注册表/TTL 60/锁/probe·snapshot·invalidate 与 spec §九锚点逐一对齐；两表列契约全对（单例默认 port 9030/catalog 三型含 es P4 列）；补测 7 条全绿（单例默认值/catalog 列契约/默认行构建/jdbc·es 参数校验矩阵 400/重名 400/探针 TTL 缓存+force 穿透/snapshot 三引擎汇总） | plan 任务 1-4 验证-对齐完成；Doris 侧真值操作（建/探/刷/删 catalog 真连接）与 M06/M21 联测留批次 4 |
| 2026-09-08 | 测试锚点：_PROBES 注册表模块加载时绑定函数引用——monkeypatch 须 patch 字典值（setitem）而非模块属性 | 测试按实现结构锚定（注册表为加载期常量属合理设计，非缺陷） |
| —— | —— | —— |

## 九、证据锚点

8 端点 `doris_config.py` L55-235（config L55-144/catalogs L145-235：probe L217/refresh L226/delete L235）｜单例模型 `models/base.py` L604-615（docstring L605/默认值 L608-614）｜catalog 模型 L618-632（三型 L623/ES P4 L629-631）｜探针 `engine_health.py` L17-98（TTL L17/锁 L19/三探针 L22-47/注册表 L47/probe L50/snapshot L80/invalidate L89）。
