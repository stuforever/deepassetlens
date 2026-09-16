# 工作区开发原则（长期记忆）

本项目（tupu 知识图谱平台）开发时，始终遵循以下原则。

## 决策优先级（自上而下，命中即止）

1. **真的需要吗？** —— 不需要就跳过。遵守 YAGNI（You Ain't Gonna Need It）原则，不为想象中的需求写代码。
2. **标准库能搞定？** —— 用标准库。不要重复造轮子。
3. **平台原生有？** —— 用平台能力。不要引入额外依赖。
4. **现有依赖有？** —— 用已有的。不要加新包。
5. **一行能解决？** —— 就一行。不要写函数。
6. **以上都不行？** —— 写最小可行代码。

## 上下文管理

- 上下文 token 数接近或超过 20k 时，直接执行 `/compact` 整理上下文，不要硬撑到溢出。

## 后端端口（铁律）

- **tupu 后端固定运行在 28000 端口**，永远不要改用其他端口（如 8100 等）。
- 启动后端用 `backend/__start_8000.py`（文件名历史遗留，实际启动 28000 端口）；不要新建 `__start_8xxx.py` 这类脚本。
- 前端 dev proxy 必须指向 `http://127.0.0.1:28000`，不要改成别的端口。
- **前端代码禁止硬编码后端端口**：axios baseURL 等一律用相对路径（如 `/api/v1`、`/api/data-intelligence/*`），由 setupProxy.js 统一转发到 28000。不要写 `http://127.0.0.1:8xxx`，否则后端换端口时前端静默崩（接口 404/连接失败，如下拉空）。
- 若发现 28000 以外的端口被占用跑 tupu 后端，视为异常重复进程，应停掉，只保留 28000。

## Docker 端口映射（铁律，禁止修改）

> 2026-08-05 固化。端口尽量在 10000 以上，避免与 Windows Hyper-V 保留端口范围（1177-1876 等）冲突。
> MySQL 用 3306，ES 复用 docker-es01-1（11200），PG 用 25432。

| 服务 | 容器名 | 宿主端口 | 容器端口 | 用途 |
|------|--------|---------|---------|------|
| tupu 后端 | （本地进程） | **28000** | - | FastAPI/Uvicorn |
| 前端 dev server | （本地进程） | **23000** | - | React dev server |
| MySQL | tupu_mysql | **3306** | 3306 | tupu 主库（root/<.env.infra>） |
| PostgreSQL | tupu_pg | **25432** | 5432 | pg_tupu（项目域实体业务数据） |
| Elasticsearch | docker-es01-1 | **11200** | 9200 | ES（elastic/infini_rag_flow） |
| Doris FE | tupu_doris_fe | **9030** | 9030 | Doris MySQL 协议查询 |
| Doris FE HTTP | tupu_doris_fe | **18030** | 8030 | Doris Web UI |
| Doris BE | tupu_doris_be | **18040** | 8040 | Doris BE |
| Neo4j Browser | tupu_neo4j | **7474** | 7474 | 图数据库 Web UI |
| Neo4j Bolt | tupu_neo4j | **7687** | 7687 | 图数据库 Bolt 协议 |
| Qdrant | tupu_qdrant | **6333-6334** | 6333-6334 | 向量库 |
| Authentik | tupu_authentik_server | **9100, 9143** | 9000, 9443 | SSO/RBAC |
| Sandbox | sandbox-executor-manager | **9385** | 9385 | 代码执行沙箱 |

**连接字符串速查**：
- MySQL: `mysql+pymysql://root:<TUPU_MYSQL_PASSWORD>@localhost:3306/tupu`
- PostgreSQL: `postgresql://postgres:<TUPU_PG_PASSWORD>@localhost:25432/tupu`
- ES: `http://elastic:infini_rag_flow@localhost:11200`
- Doris: `mysql://root:@localhost:9030`（catalogs: es_tupu, pg_tupu, internal）
- Neo4j: `bolt://localhost:7687`

**禁止**：
- 不要修改上述任何端口号。
- 不要新建 Docker 容器使用与上表冲突的端口。

## 设计窗口规划纪律（铁律）

> **2026-09-06 用户定调（长期记忆）**：设计窗口做**任务规划拆解**时，**只使用 brainstorming、writing-plans 两个技能，只用这两个**：
> 1. **brainstorming**：探索意图 → 澄清问题 → 方案对比 → 分节确认 → 设计成文入 `docs/` → 规格自检 → 用户审查；
> 2. **writing-plans**：把用户已批准的设计拆解为实施计划，交实施会话执行。
>
> 设计窗口不做开发、不做测试；规划产出（设计/计划文档）落 `docs/` 后由实施会话随实施提交入库并登记主文档（设计窗口不双写，防冲突）。

## 浏览器测试（铁律）

> **2026-08-23 用户定调（长期记忆）**：测试**一律用 Playwright 真实前端模拟**（headless 驱动真实浏览器访问前端 23000 页面），
> **禁止把后端直连/后端流式脚本（_q_run 等）作为验收测试**——用户明确"后端测试没毛用"。

- **Playwright 方案（标准，当前无 IAB 时唯一可用）**：
  - 环境：Python313（`C:\Users\李钢柱\AppData\Local\Programs\Python\Python313\python.exe`）已装 playwright；
    浏览器缓存 `%USERPROFILE%\AppData\Local\ms-playwright`（chromium-1200/1223/1228/1234 齐全，`python -u scripts/_pw_smoke.py` 已验证可启动）。
  - 入口脚本：`backend/scripts/_pw_e2e.py <问题> <截图名> <超时秒>`——headless 打开 `http://localhost:23000`「数据资产探查」页 →
    输入问题 → 发送 → 等流式 → 抓 `.ant-table` 查询结果表（thead th / tbody tr>td）+ 回答文本 → 截图 `scripts/_pw_<名>.png`。
  - 定位选择器：输入框 `textarea.ant-input`（placeholder「想问什么数据？」），发送按钮 `button.ant-btn-primary`。
  - **必须串行执行**：并发多个 e2e 会串扰后端会话（曾出现模型"未收到用户请求"），一次只跑一个。
  - 登录态 anonymous/admin（前端已预置），打开即用。
  - 参考脚本：`_pw_probe_dom.py`（dump DOM）、`_pw_smoke.py`（环境冒烟）。
- 若将来 IAB（`mcp__node_repl__js` + `agent.browsers`）可用，优先 IAB（见下细则）；**无 IAB 时一律 Playwright headless**。
- 禁止用 `start`、`cmd /c start`、`explorer` 等命令弹出系统浏览器窗口；Playwright 一律 headless（不弹窗口）。
- 测试前端页面一律走 `http://localhost:23000`（前端 dev server），由 setupProxy.js 转发到 28000 后端。

### IAB 细则（仅 IAB 可用时）
- 浏览器绑定复用：首次 `globalThis.browser = await agent.browsers.get("iab")`，后续轮次复用同一绑定；每个标签页操作批次前先 `await browser.tabs.list()` 确认目标，再 `browser.tabs.get(id)` 激活，绝不按数组下标盲选。
- 读页面优先用 `await tab.playwright.domSnapshot()`（AI/ARIA 树）定位元素、构造 locator；仅在需要视觉确认布局/样式/渲染时才 `tab.screenshot()` 并配 `nodeRepl.emitImage()`，同一 JS 单元默认不既快照又截图。
- **不要和过时的 `mcp__playwright__*` 混淆**——当前环境无 Playwright MCP 服务，唯一入口是 `mcp__node_repl__js` + `agent.browsers`（IAB）。

## 复刻开发纪律（2026-09-16 用户定调，永久生效）

- 实施窗口**必须用技能**执行计划（executing-plans/systematic-debugging/verification-before-completion 等 superpowers 技能，开场宣布）；
- **完整复刻原有功能 1:1**（页面/子页面/字段/端点/能力一级不漏、一字不改），**不许重写新逻辑、不许「等价实现」糊弄**——对拍不一致必须修到一致或停下问用户，不许私自裁剪；
- 复刻任务总账=`docs/superpowers/plans/2026-09-12-唯一交棒-全部未完成任务.md`（唯一交棒，自包含 20 批）；没有对拍证据的批不算完成、不许 commit。
