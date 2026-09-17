# tutor 复刻 R3——通用合并 × 个性化完整还原（多专家平台子项目⑤R 终版）

> **批准记录（2026-09-12，用户三轮定调）**：①「前后端功能现成的（界面/元素/接口/数据库），原封不动还原」；②「功能要复刻，框架用我们最新写的基座，完整复刻，可千万别重新设计能力或者裁剪能力」；③**「两套能力要做通用合并：读取全量 tutor 能力，与现有工程合并能力，重新规划——哪些能力归成通用、以那边为主；哪些是个性化能力，但要完整还原」**。
> **R2→R3 变更**：新增 §二 通用/个性化能力分区规划（核心章）；knowledge.py 移出个性化清单、入 §2.4 通用合并专案；应用规划窗口修单（P1×2+P2×4）与随棒总序（§四）。
> **取代声明**：《教学域补全-自主学习与错题管理》spec ⛔ 作废；R1「Next.js 整应用独立 24000」方案 ⛔ 作废。
> **设计窗口**：不 commit；实施会话随批入库并登记。供 writing-plans 出计划。

## 一、复刻边界四条铁律

1. **零裁剪**：范围=教学产品**调用闭包**（复-0 从 web/ 全部 API 调用 grep+import 闭包机械生成，**须覆盖 main.py 内联路由/挂载**——如 L352-357 `/api/v1/curriculum/pages` StaticFiles 实证一例）；闭包内能力一律落地——**或个性化复刻、或经通用层承接，功能不缺**；无「判据/延后/简化」条款；
2. **零重设计**：个性化域端点契约/数据模型/页面动线 1:1 对照原仓；JSON 存储实现照搬（根=expert 工作区）；改动仅限 §三基座接线四点+§2.4 契约适配层；
3. **基座归 tupu**：引擎（deepagents）/认证（⑥-2a）/路径根/模型网关（③）/前端壳（React 23000）/部署验收=平台铁律；
4. **通用能力平台一套（R3 新增）**：凡平台域能力（认证/记忆/知识库与解析/模型/工具/技能/会话/配置/流式/文件）**一律并入 tupu 基座、不双轨**；tutor 消费侧经**契约适配层**保持前端契约 1:1——通用合并不得变成功能裁剪。

## 二、通用/个性化能力分区规划（R3 核心）

### 2.1 分区总则

- **通用层**（平台一套）：DeepTutor 里的平台性能力并入 tupu 已建基座；**主导权原则上 tupu**（deepagents 信任锚+①-⑤/⑥-2a 已建成）；教材解析引擎以 **tupu④ 为主**（book 解析器已等值在库）；
- **个性化层**（教学域全套）：**主导权 DeepTutor**——完整还原，1:1；
- **契约保真**：通用合并不改 tutor 前端调用契约——原 prefix 端点由契约适配层承接（实现指平台基座），前端零改动；
- 边界裁定法：该能力若第二个专家也会用=通用；只属于教与学=个性化。

### 2.2 通用合并表（DeepTutor 平台件 → tupu 基座，主导与合并方式）

| DeepTutor 件（行） | tupu 基座 | 为主 | 合并方式 |
|---|---|---|---|
| knowledge.py 2468 | ④ 文档知识库 | **tupu④** | **§2.4 专案**：契约适配层+④差距增强；保底回退 |
| book.py 解析引擎 | ④ parsing（book.py 已等值） | tupu④ | 书源管理面归个性化（§2.3），解析调④ |
| auth.py 712 | ⑥-2a 认证 | tupu | shim 接线（§三.1） |
| memory.py 635 | ② 记忆插槽 | tupu | 不搬；tutor 会话记忆走②槽体系（数据不照搬） |
| capabilities_settings 24 | ③ 能力开关 | tupu | 不搬 |
| mcp_settings 111/space_mcp 390/space_cli_apps 189 | 自研 mcp_server+沙箱 9385 | tupu | 不搬 |
| skills.py 247 | 技能中心（SKILL.md 11 个） | tupu | 不搬；DeepTutor 技能资产择优入种子（登记清单） |
| sessions 213/chat 205 | ① 连接+deepagents 引擎 | tupu | 不搬（引擎面）；chat 能力面经 E1 工具面还原（功能等价） |
| personas 114/agent_config 49 | ① 专家卡 | tupu | 不搬；私塾先生人格=①卡（AGENTS.md） |
| subagents 267 | deepagents 原生 | tupu | 不搬 |
| tools 193 | query_contract 工具面 | tupu | 不搬 |
| settings 1051/system 280/unified_ws 343 | 平台配置/系统/流式基座 | tupu | 不搬 |
| attachments 72 | 平台文件面 | tupu | 复-0 闭包含则平台补最小件（差距登记） |
| plugins_api 368 | ① 专家体系（⑥-2 工厂方向） | tupu | 不搬；专家扩展语义=①卡注册表 |
| partners 977 | 渠道层 | tupu | ⑥-8 远期（非教学闭包则不动） |
| wechat_push 263/voice 130 | 推送/朗读 | tupu | **复-0 闭包定**：H5 动线依赖→按通用差距件最小并入；否则⑥-8 |
| multi_user/h5 守卫（?u=/access_code） | ⑥-2a 会话 | tupu | ?u=→会话用户；**access_code 分享能力随 h5_links 个性化复刻**（能力不裁剪） |

### 2.3 个性化完整还原表（教学域，DeepTutor 为主，全量）

14 个教学 router **实合计 10,138 行**（api/routers 实 37 件含 `__init__`、除之 36——R2 的「38 件/14,04 行」勘误；curriculum.py 实 **1214 行**且位于 `deeptutor/learning/`，路由 L405 自带、main.py L469-473 挂载）+ **learning/ 整包**（curriculum/service/storage/scheduler/policy/prompts/practice_generator/exercise_selector/grading/mastery/learner_profile/h5_progress/simhash_util/image_pipeline/recitation 子包/tab_export 子包/models/llm_cost_log/mother_question/fsrs——**实名全列，fsrs 已等值在库**）：

| 件 | 行数 | 挂载 | 能力 |
|---|---|---|---|
| mother_question.py | 2174 | /api/v1/mother-questions | 母题/变式/错题库管理 |
| self_learning.py | 966 | /api/v1/self-learning | 章节聚合总览（自主学习） |
| learner_profile.py | 657 | /api/v1/learning | 画像聚合（streak/due/weak） |
| book.py（书源管理面） | 564 | /api/v1/book | 教材书源 CRUD（解析调④） |
| question.py | 484 | /api/v1/question | 问答 |
| quiz_judge.py | 385 | /api/v1（根挂载） | 判题 |
| notebook.py | 350 | /api/v1/notebook | 笔记本 |
| question_notebook.py | 267 | /api/v1/question-notebook | 题目笔记本 |
| mastery_path.py | 299 | /api/v1/learning | 精通之路（导学模块/阶段） |
| curriculum.py（learning 包内） | 1214 | /api/v1/curriculum | 教材/章节/知识点树+精讲（含 main.py L352-357 pages 静态挂载） |
| h5_links.py | 139 | /api/v1/h5-links | H5 分享链接（access_code） |
| imports.py | 121 | /api/v1/imports | 导入 |
| dashboard.py | 50 | /api/v1/dashboard | 仪表盘 |

前端：web/ 五路由组（(workspace)/h5/(admin)/(auth)/(utility)）全部页面动线在我们 React 23000 壳内 1:1 重建（antd，布局/交互/文案照原样）；(auth) 由 ⑥-2a 登录承接。对拍基准=原仓逐屏截图底册（复-0 录制）。

### 2.4 knowledge.py 通用合并专案（唯一深水个案）

- **判定**：KB 管理=平台通用能力，**tupu④ 为主**（附件一已吸收其四纪律；④ R2 走 m15 升级路线 a）；
- **合并方式**：tutor 前端所调 `/api/v1/knowledge/*` 端点=**契约适配层**（原 prefix、原请求/响应形状），实现指④；④未覆盖端点=**④差距增强清单**——复-0 从「knowledge.py 端点全清单 × ④ 现有端点」机械 diff 生成，交 **B0 批**（④增强，沿升级路线 a 纪律+m15 spec 变更记录）；
- **保底**：单端点差距若 适配成本>复刻成本 → 该端点回退为 tutor 域内复刻——**功能完整性优先于架构纯度**（零裁剪铁律兜底）；
- **数据**：`data/knowledge_bases` 内容导入④实例（tutor 卡 knowledge_sources 挂接）；`parse_cache` 归④。

### 2.5 数据分区

| 原仓数据 | 归属 | 处置 |
|---|---|---|
| 教学 store（curriculum/mother_questions/notebook/learning 进度/h5_links.json 等） | 个性化 | 照搬进 tutor 工作区（复-0 精确落位） |
| knowledge_bases/parse_cache | 通用④ | 内容导入④（§2.4） |
| memory/ | 通用② | 不照搬（tutor 记忆走②槽） |
| partners/system/user/users | 平台域 | 不搬 |

### 2.6 功能级清单与菜单规划（R3 追加，依据 web/app 实测页面底册）

原仓页面底册（实测）：(workspace) home/book/co-writer/mother-questions×7 子页/new·photo·photo-center·analysis·review·trash·[mid]/partners×3/playground/self-learning；h5 atlas/book/[bookId]/chat/classroom/learn/learn/textbook/me/paths/paths/[bookId]/report/review/share/wrong/wrongbook；(utility) agents/knowledge/memory×8 子页(graph/l1/l2/[surface]/l3/[slot]/resolve)/notebook/profile/settings×N 子页(agents 六家/appearance/attachments/capabilities/chat/curriculum/…截断，复-0 全量补)；(admin) users；(auth) login/register。

| 一级模块 | 二级功能（原页面/端点） | 合并归属 | 承接 | 菜单路径（合并后） |
|---|---|---|---|---|
| **1 对话问答** | 多轮问答/讲题（home、h5/chat、question.py） | 专有 | deepagents tutor 卡+E1 工具面 | /e/tutor/chat |
| | 会话管理/历史 | 通用 | ①连接 | 侧栏会话（平台既有） |
| | 对话附件（截图/文件） | 通用 | 平台附件面（闭包定，差距件） | 对话内嵌 |
| **2 自主学习** | 学习首页画像（streak/due/weak/今日任务，learner_profile） | 专有 | learner_profile 复刻 | /e/tutor/learn |
| | 教材/章节树浏览（curriculum） | 专有 | curriculum 复刻 | /e/tutor/learn |
| | 知识点精讲+教材原文页图（curriculum+pages 静态挂载） | 专有 | 同上 | /e/tutor/learn |
| | 课堂（h5/classroom） | 专有 | 复刻 | /e/tutor/classroom |
| | 教材学（h5/learn/textbook） | 专有 | 复刻 | /e/tutor/learn/textbook |
| **3 练习判题** | 三档难度练习生成（practice_generator） | 专有 | 复刻 | 练习流（learn 内） |
| | 判题/订正（quiz_judge+grading） | 专有 | 复刻 | 练习流内 |
| | 复习到期/评分（h5/review、fsrs/scheduler） | 专有 | 复刻（fsrs 已等值） | /e/tutor/review |
| | 背诵（recitation 子包） | 专有 | 复刻 | 复习流内 |
| **4 错题域** | 错题录入-移动端（h5/wrong，含对话式） | 专有 | 复刻 | /e/tutor/wrong |
| | 错题本（h5/wrongbook 列表/筛选/详情） | 专有 | 复刻 | /e/tutor/wrongbook |
| | 母题库管理-桌面端（workspace/mother-questions 主列表） | 专有 | 复刻 | /e/tutor/admin/mother-questions |
| | 录题/拍照/拍照中心（new/photo/photo-center） | 专有 | 复刻（image_pipeline 同包） | /e/tutor/admin/mother-questions/{new,photo} |
| | 错题分析（analysis） | 专有 | 复刻 | /e/tutor/admin/mother-questions/analysis |
| | 错题复习/回收站（review/trash/[mid]） | 专有 | 复刻 | /e/tutor/admin/mother-questions/{review,trash} |
| | 错题本导出（tab_export） | 专有 | 复刻 | 错题本内动作 |
| **5 精通之路** | 路线图/模块阶段（h5/paths、mastery_path） | 专有 | 复刻 | /e/tutor/paths |
| | 学情报告（h5/report、dashboard） | 专有 | 复刻 | /e/tutor/report |
| **6 知识地图与教材** | 知识地图（h5/atlas，cytoscape 知识点图） | 专有 | 复刻（可视组件可用平台图件） | /e/tutor/atlas |
| | 教材阅读（h5/book/[bookId]） | 专有 | 复刻 | /e/tutor/book/[bookId] |
| | 教材书源管理（workspace/book） | 专有 | 书源 CRUD 复刻，解析调④ | /e/tutor/admin/book |
| **7 笔记本** | 学习笔记（utility/notebook、notebook.py） | 专有 | 复刻 | /e/tutor/notebook |
| | 题目笔记（question_notebook.py） | 专有 | 复刻 | 并入 /e/tutor/notebook |
| **8 分享推送** | H5 分享链接/二维码/access_code（h5/share、h5_links） | 专有 | 复刻 | 分享入口（各页内嵌） |
| | 学习提醒推送（wechat_push） | 复-0 闭包定 | 通用渠道层 or 最小并入 | 后台配置 |
| **9 知识库管理** | KB 实例/文档/解析/检索/向量化（utility/knowledge、knowledge.py 2468） | **通用** | ④为主+契约适配层+B0 差距批 | 平台 /knowledge（④页） |
| **10 记忆管理** | 三层记忆浏览/固化/图谱（utility/memory×8 子页，memory.py） | **通用** | ②槽体系+memory-admin | 平台 /memory-admin |
| **11 平台设置** | 模型/外部 agent 配置（settings/agents 六家） | **通用** | ③模型目录（LLM 连接） | 平台 /llm-config |
| | 能力开关（settings/capabilities） | **通用** | ③能力开关 | 平台 /capabilities |
| | 技能/MCP/子代理/工具 | **通用** | 技能中心/自研 mcp/deepagents | 平台 /skills 等 |
| | 用户管理（(admin)/users） | **通用** | ⑥-2a 认证+专家赋权 | 平台用户/赋权面 |
| | 个人中心（utility/profile、h5/me） | **通用** | ⑥-2a 用户面 | 平台用户中心 |
| | 外观/聊天/附件设置（settings/appearance 等） | **通用** | 平台设置面 | 平台设置 |
| | **课程/教学参数设置（settings/curriculum）** | **专有** | 复刻（FSRS/调度/教材参数） | /e/tutor/admin/settings |
| **12 域外件** | 写作（co-writer×2） | 域外另立 | 写作域 spec（不混入） | — |
| | 伙伴渠道（partners×3） | 域外远期 | ⑥-8 | — |
| | 试验场（playground） | 通用已有 | deepagents 对话/调试面（不复刻） | — |
| | 登录注册（(auth) login/register） | **通用** | ⑥-2a 登录 | 平台登录页 |

菜单汇总：**专家空间**（学生侧）=/e/tutor/{chat, learn, learn/textbook, classroom, review, wrong, wrongbook, paths, report, atlas, book/[bookId], notebook}；**专家后台**（教师/管理侧）=/e/tutor/admin/{mother-questions×6, book, settings}；**平台层**（通用）=/knowledge、/memory-admin、/llm-config、/capabilities、/skills、用户/赋权、登录。原 h5 组→学生侧、workspace 组→管理侧、utility 组→平台侧，组语义原样映射。

### 2.6.1 R3 对拍偏差登记（实施实测回写，2026-09-17）

> R3 对拍（原仓 30408/31007 vs tupu 23000/28000 实测）发现的本 spec 规划与落地差异，逐条登记（复刻纪律：对拍不一致必须修到一致或登记）：

1. **h5/ 路由前缀（登记保留）**：本表 §2.6 二级功能菜单列原规划 `/e/tutor/learn` 等无 h5 段形态；实际复刻按原仓 h5 组原结构 1:1 落地为 `/e/tutor/h5/*`（`/h5/learn`→`/e/tutor/h5/learn`、`/h5/learn/textbook`→`/e/tutor/h5/learn/textbook`、`/h5/classroom`→`/e/tutor/h5/classroom`、`/h5/review`→`/e/tutor/h5/review`、`/h5/wrong`→`/e/tutor/h5/wrong`、`/h5/wrongbook`→`/e/tutor/h5/wrongbook`、`/h5/paths`→`/e/tutor/h5/paths`、`/h5/paths/[bookId]`→`/e/tutor/h5/paths/:bookId`、`/h5/report`→`/e/tutor/h5/report`、`/h5/atlas`→`/e/tutor/h5/atlas`、`/h5/book/[bookId]`→`/e/tutor/h5/book/:bookId`、`/h5/chat`→`/e/tutor/h5/chat`，另含 `me/share`）。理由：h5 组为移动形态独立壳（H5Shell+12 页），保结构才能字段级 1:1 对拍（R3 A 段已按此对拍通过）；功能语义与本表一一对应，仅多一层 `h5/` 命名空间。**本表菜单列以本登记为准修正。**
2. **笔记本页补建（缺口修复）**：F2 曾记 9.1 notebook 完成——R3 A 段对拍发现仅 picker 链落位、页面本体缺位。已按原仓 `(utility)/notebook/page.tsx` 1:1 补建 `frontend/src/pages/tutor/notebook/NotebookPage.tsx` + 路由 `/e/tutor/notebook`（题库=学习笔记+题目笔记两 tab 语义由 question-notebook 单面承接，对应本表 #7 两行）；ExpertChat 增 `?session=` 深链消费（原仓 `/?session=` 等值）。
3. **权限联调收口（⑥-2a/B-F 段）**：h5 功能页+笔记本统一包 `withUseGuard`（use 语义，A-4 分层——后台 manage/功能页 use）；`RequireAdmin` 的 check 请求补 Bearer 头（auth=1 下裸 fetch=401 一律拒的缺陷修复）；Authentik tupu-oidc provider 补 scope mappings（openid/profile/email+自建 groups 映射——无 groups claim 则角色映射落 viewer）；部署项：`AUTHENTIK_FRONTEND_REDIRECT=http://localhost:23000/auth/callback`（后端 .env，provider 白名单同步）。
4. **默认账号（⑥-2a 分配）**：akadmin（admin@tupu.local，tupu-admin 组，bootstrap 密码）；student / student2（tupu-viewer 组，`Tupu_student_2026`）；student 已 grant `expert/tutor use`（ResourceACL id 1066，admin 经 /api/v1/auth/grant 分配）。三态实测 18/18：student=门户见卡+功能页可达+后台被拦；student2=门户无卡+直连被拦+wenshu 可用；akadmin=后台可达；匿名 401/dev-login 403 自证。

## 三、基座接线（唯一允许的改动，四处）

1. **认证 shim**：`_auth` 依赖→同名同形 shim 背靠 tupu `core/auth`（⑥-2a）；`?u=`→会话用户（缺省=admin 桌面语义保留）；access_code 能力照常复刻；
2. **路径根**：path_service workspace root→`backend/data/experts/tutor/workspace/`（env 单点）；
3. **LLM**：llm/ 客户端照搬，配置指③模型网关；
4. **引擎**：chat 不搬→deepagents tutor 卡+E1 域工具面。

**落位**：后端 `backend/app/vendor/deeptutor/`（教学域子树原结构，保相对导入，main.py 挂载**原 prefix**）；前端 23000 专家页；**无新端口**。

## 四、批次与总序（与规划窗口随棒对齐）

| 批 | 内容 | 验收门 |
|---|---|---|
| 复-0 底册与闭包 | 原仓起服务（**仓库绝对路径钉死：`D:\gitcangku\xiaobaohaohao\DeepTutor`——双 hao，历史棒次/计划中 `xiaobaohao` 单 hao 全部是错的，勘误登记**）：全教学域端点对拍基线+五路由组逐屏截图底册；**chat 能力清单提取**（capabilities/+前端 chat 调用面→E1 映射审计左源）；**knowledge.py 端点×④ diff**（④差距清单）；调用闭包+import 闭包 grep（**覆盖 main.py 内联路由/静态挂载**）；**全路径 diff 冲突审计**（tupu main.py 挂 32 个 include_router、/api/v1 前缀 22 处+模块自带前缀者——同 prefix 不冲突、**路径撞车才冲突**，以全路径 diff 定案）；**能力清单机械冻结**（§2.3 实名全列，零裁剪审计底册） | 底册落盘 |
| B0（条件批） | ④差距增强（diff 非空则启动） | ④回归+m15 变更记录 |
| B1 课程与题库 | curriculum+mother_question+storage 照搬+接线 | 基线子集对拍 |
| B2 问答判题练习件 | question+quiz_judge+recitation/simhash_util/image_pipeline | 同上 |
| B3 学习闭环 | learner_profile+mastery_path+self_learning+policy+h5_progress | 同上 |
| B4 配套件 | notebook+question_notebook+book 书源面+imports+dashboard+h5_links（+wechat_push/voice 若闭包含） | 同上 |
| E1 引擎工具面 | 复刻域 API→deepagents 工具；**验收门=（修单 P1-1 取 (b)）域工具面↔复刻端点能力映射清单审计（每工具映射一端点、零缺失，左源=复-0 chat 能力清单）+关键域操作经 tutor chat 完成 e2e**——chat.py 属引擎面不搬（基座原则），行为对拍无对象，功能等价以映射清单为据 | 映射审计+e2e |
| F1-F4 | (workspace)→h5→(admin)→入口/认证接线（门户/侧栏/ACL） | 逐屏对拍+动线 e2e |
| R1 退役清理 | **tutor 自建面全量退役——以复-0 实测为准**（2026-09-12 实测存量已超 R2 认知：Tutor 六页 Learn/Path/Practice/Progress/Review/WrongBook+tutor/admin 两页+tutor_admin.py+/api/tutor 端点+9 工具+PG 四表冻结——⑤补/附件四批次被实施会话先行落地，一并退役由复刻件取代） | pytest 全量+wenshu 零感知 |
| R2 终验收 | §五全组 | — |

**总序（对齐规划窗口随棒）**：复-0→[B0]→B1-B4→E1→F1-F4→R1 退役→R2 终验收→（权限件）B-0..B-2→A-4→B-3→**B-4 翻转全局最后**。
**A 件 v3 重排（登记）**：A-1 导航对象改 F 批路由；A-2 卡配置保留；A-3 被 F3 覆盖。**B 件升位（登记）**：执法点 3 改挂 vendor shim 统一门。

## 五、验收（A-F 组）

- [ ] A1 端点契约对拍等值：复-0 基线样本全量重放（含 knowledge 适配层端点），响应形状 1:1（时间戳/ID 白名单豁免）；
- [ ] A2 前端逐屏对拍+关键动线 e2e（首页→章节自主学习→错题录入管理→练习判分→精通之路）——串行+截图；
- [ ] A3 **零裁剪审计**：以**复-0 机械冻结清单**为准（含 recitation/tab_export 子包、simhash_util、llm_cost_log、mother_question 等全部实名件）逐项勾验，缺项不通过；
- [ ] A4 零重设计审计：数据模型字段级 diff+端点契约 diff+差异台账零未登记；
- [ ] A5 基座回归：wenshu 零感知；平台页零破；tutor chat 与复刻域并存不串；通用层不双轨（memory/KB 单套）；
- [ ] A6 铁律：28000/23000 不动、无新端口、e2e 串行、PYTHONUTF8。

## 六、诚实账

1. knowledge.py 专案双路（④适配/域内回退）判定权在复-0 diff——数量未勘明前不定死；B0 是条件批；
2. 通用合并的功能风险点=契约适配层（④形状≠DeepTutor 形状），A1 对拍必须覆盖适配端点；
3. wechat_push/voice 归属复-0 闭包定（入则全还原，含渠道配置面）；
4. 前端五路由组在 antd 壳重建工作量大，F 批独立可验收、不合并；
5. 差异台账纪律：接线四点+适配层之外任何差异逐条登记，默认不许差异；
6. ⑤a-e 重设计（含 PG 四表）沉没成本退役认账；原仓测试（learning/tests）随包搬用作对拍资产；
7. R2 数字勘误记录：curriculum 1404→**1214**、api/routers 38→**37（含 __init__，实件 36）**、合计 10,328→**10,138**；「25 个 /api/v1 router」与实测 22 处前缀口径差以复-0 全路径 diff 定案。

## 七、证据锚点（2026-09-12 实测）

**本会话验证（修单核实）**：`D:\gitcangku\xiaobaohaohao\DeepTutor`（pwsh 实存）；curriculum.py=1214 行（learning/ 内）；api/routers 36 实件+__init__；main.py L352-357 静态挂载 `/api/v1/curriculum/pages`（原文「Textbook page images…for the self-learning original-text tab」）；tupu main.py include_router=32、/api/v1 前缀=22 处。**早前实测**：api/main.py L441-482/L570-588 挂载清单；web/package.json（opentutor-web：next/react/katex/mermaid/cytoscape/recharts）；web/app 路由组 (admin)/(auth)/(utility)/(workspace)/h5；data/ 一级结构；routers 行数表（§2.2/2.3）。**依据文档**：附件一（KB 四纪律→④）、附件三/四、⑥-2a spec、修单原文（用户转交，2026-09-12）。
