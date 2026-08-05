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
> ES 原端口 1200 在 Windows 保留范围内（1177-1276），已改为 11200。

| 服务 | 容器名 | 宿主端口 | 容器端口 | 用途 |
|------|--------|---------|---------|------|
| tupu 后端 | （本地进程） | **28000** | - | FastAPI/Uvicorn |
| 前端 dev server | （本地进程） | **23000** | - | React dev server |
| MySQL | docker-mysql-1 | **33066** | 3306 | tupu 主库（root/root） |
| PostgreSQL | tupu_pg | **5432** | 5432 | pg_tupu（117表，配电域等） |
| Elasticsearch | docker-elasticsearch-1 | **11200** | 9200 | ES（elastic/infini_rag_flow） |
| Doris FE | tupu_doris_fe | **9030** | 9030 | Doris MySQL 协议查询 |
| Doris FE HTTP | tupu_doris_fe | **18030** | 8030 | Doris Web UI |
| Doris BE | tupu_doris_be | **18040** | 8040 | Doris BE |
| Neo4j Browser | tupu_neo4j | **7474** | 7474 | 图数据库 Web UI |
| Neo4j Bolt | tupu_neo4j | **7687** | 7687 | 图数据库 Bolt 协议 |
| Qdrant | tupu_qdrant | **6333-6334** | 6333-6334 | 向量库 |
| Redis | docker-redis-1 | **6379** | 6379 | 缓存（RAGFlow 共用） |
| TEI | docker-tei-cpu-1 | **6380** | 80 | 文本嵌入推理 |
| MinIO | docker-minio-1 | **9000-9001** | 9000-9001 | 对象存储 |
| RAGFlow | docker-ragflow-cpu-1 | **80, 443, 9380-9384** | 同 | RAGFlow 服务 |
| Authentik | tupu_authentik_server | **9100, 9143** | 9000, 9443 | SSO/RBAC |
| Gitea | tupu_gitea | **2222, 3001** | 22, 3000 | 代码仓库（SSH/Web） |
| Sandbox | sandbox-executor-manager | **9385** | 9385 | 代码执行沙箱 |

**连接字符串速查**：
- MySQL: `mysql+pymysql://root:root@localhost:33066/tupu`
- PostgreSQL: `postgresql://tupu:tupu@localhost:5432/tupu`
- ES: `http://elastic:infini_rag_flow@localhost:11200`
- Doris: `mysql://root:@localhost:9030`（catalogs: es_tupu, pg_tupu, internal）
- Neo4j: `bolt://localhost:7687`

**禁止**：
- 不要修改上述任何端口号。
- 不要新建 Docker 容器使用与上表冲突的端口。
- ES 端口已从 1200 改为 11200，代码中所有 `localhost:1200` 引用已同步更新（MySQL `kg_api_endpoints` 表 10 条 + 迁移脚本）。

## 浏览器测试（铁律）

- **测试一律用 IDE 内置浏览器（IAB）**，通过 `control-browser` 技能（browser-use 插件）驱动：用 `mcp__node_repl__js` 调用 `agent.browsers` API，在右侧标签页打开页面测试。
- **凡是提到"测试 / webapptest / 前端测试工具 / 浏览器测试 / 验证页面"等，一律指此模式**，无需额外说明，不弹外部浏览器、不开桌面 Chrome。
- 禁止用 `start`、`cmd /c start`、`explorer` 等命令弹出系统浏览器窗口；禁止使用桌面谷歌浏览器（Chrome）等任何外部浏览器测试。
- 测试前端页面一律走 `http://localhost:23000`（前端 dev server），由 setupProxy.js 转发到 28000 后端。
- 浏览器绑定复用：首次 `globalThis.browser = await agent.browsers.get("iab")`，后续轮次复用同一绑定；每个标签页操作批次前先 `await browser.tabs.list()` 确认目标，再 `browser.tabs.get(id)` 激活，绝不按数组下标盲选。
- 读页面优先用 `await tab.playwright.domSnapshot()`（AI/ARIA 树）定位元素、构造 locator；仅在需要视觉确认布局/样式/渲染时才 `tab.screenshot()` 并配 `nodeRepl.emitImage()`，同一 JS 单元默认不既快照又截图。
- **不要和过时的 `mcp__playwright__*` 混淆**——当前环境无 Playwright MCP 服务，唯一入口是 `mcp__node_repl__js` + `agent.browsers`（IAB）。
