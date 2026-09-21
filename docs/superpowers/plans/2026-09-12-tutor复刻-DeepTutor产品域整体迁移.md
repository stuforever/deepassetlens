# tutor 复刻实现计划（⑤R·DeepTutor 产品域整体迁移 R3）

> 📦 **已并入唯一交棒（2026-09-12）**：本计划全部批任务已并入《`2026-09-12-唯一交棒-全部未完成任务.md`》（单文件完整版，实施窗口唯一拷贝对象）——本文件保留作分卷详案存档，不需要拷贝。

> **面向 AI 代理的工作者：** 必需子技能：使用 subagent-driven-development（推荐）或 executing-plans 逐批实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

> **⚠️ 执行前置**：①-⑤ 已落地；**实施抢跑存量已在**（附件五 §五实测：Tutor 六页 Learn/Path/Practice/Progress/Review/WrongBook+tutor/admin 两页 AdminHome/AdminZones+ExpertGrants 页——本计划 R1 批全量退役）。
> **⚠️ 仓库绝对路径（复-0 生命线，勘误钉死）**：原仓=`D:\gitcangku\xiaobaohaohao\DeepTutor`——**双 hao**；历史棒次/计划中 `xiaobaohao` 单 hao 全部是错的。
> **规格来源**：`specs/2026-09-12-tutor复刻-DeepTutor产品域整体迁移-design.md`（R3=唯一执行批序）＋`specs/2026-09-12-平台能力统一规划-deepassetlens×DeepTutor.md`（附件五=菜单落点与合并裁定，78 行主表）＋B 计划 v2（⑥-2a 权限件）＋A 计划 v3 处置注（A-4 存活批）。
> **总序（钉死）**：复-0→[B0 条件批]→B1→B2→B3→B4→E1→F1→F2→F3→F4→R1 退役→R2 终验收→（权限件）B-0..B-2→A-4 守卫收口→B-3 登录动线→**B-4 翻转全局最后**。

**目标：** DeepTutor 教学产品**能力面全量 1:1**（14 router 实 10,138 行+learning 整包+web 五路由组页面动线）×**基座面归 tupu**（deepagents 引擎/⑥-2a 认证/expert_paths 工作区/③模型网关/React 23000 壳/平台验收铁律）×**通用能力平台一套不双轨**（DT 平台件 16 项并入 tupu 基座，tutor 消费侧经契约适配层）。

**四铁律（spec §一，先于一切）**：①**零裁剪**——范围=教学产品调用闭包（复-0 grep 机械定稿含 main.py 内联路由/静态挂载），人不得删减，无「判据/延后/简化」条款；②**零重设计**——端点契约/数据模型/页面动线 1:1，JSON 存储实现照搬（根=tutor 工作区），改动仅限基座接线四点+契约适配层；③**基座归 tupu**；④**通用能力平台一套**——通用合并不得变成功能裁剪（契约保真）。

**技术栈/纪律：** FastAPI 28000（PYTHONUTF8=1）+React 23000（**无新端口**——R1 的 24000 方案作废）；pytest 全绿不降；Playwright headless 串行唯一验收；TDD（照搬件的「测试」=对拍重放，原仓 learning/tests 随包搬用作对拍资产）；设计窗口不 commit；**计数以 grep 实测，注释不算数**。

---

## 〇、长任务模式（用户定调，四条）

1. **任务分批**：复-0→[B0]→B1-B4（后端四批，**按域分不合并**）→E1→F1-F4（前端四批，**每批独立可验收不合并**）→R1→R2——对齐 spec §四批表；附件五不新增实施批，其裁定作为本计划批内步骤落位。
2. **每批独立可验收**：B 批=基线子集对拍；F 批=逐屏对拍（+动线 e2e）；验收门照 spec §四表。
3. **断点可续传**：全步骤 checkbox+计划头部总序；恢复=读 checkbox 定位→重验最近完成批对账三件套→过了才继续。
4. **批间对账三件套**：①`cd backend && python -m pytest`；②`python backend/scripts/_pw_e2e.py "查询所有WBS及下属层级的对象状态信息" ⑤R对账N 400`；③manifest 对**基线⑤R** diff——**wenshu 零感知恒定**；E1/F4 批 tutor 卡变更（工具面重建/入口接线）→tutor manifest 差异=**预期项登记**（f 因子缓存键自然失效重建），其余项零变化。

## 一、纪律

**落位与接线**：后端 `backend/app/vendor/deeptutor/`（教学域子树**原结构**，保相对导入）；main.py 挂载**原 prefix**（/api/v1/... 端点契约不变的前提）；**全路径 diff 冲突审计先行**（tupu main.py 挂 32 include_router、/api/v1 前缀 22 处——同 prefix 不冲突、**路径撞车才冲突**）。改动仅四点：认证 shim（`_auth` 同名同形背靠 core/auth，⑥-2a）/路径根（env 单点 `DT_TUTOR_WORKSPACE_ROOT`→`backend/data/experts/tutor/workspace/`）/LLM（llm/ 客户端照搬，配置指③）/引擎（chat 不搬→deepagents+E1）。

**契约适配层（spec §2.4 唯一深水个案）**：tutor 前端所调 `/api/v1/knowledge/*`＝适配层（原 prefix、原请求/响应形状，实现指④）；④未覆盖端点=复-0 diff 生成差距清单交 B0；**保底回退**——单端点适配成本>复刻成本→该端点回退 tutor 域内复刻（功能完整性优先于架构纯度）。

**差异台账纪律**：四点接线+适配层之外，与原仓任何差异（命名/依赖版本/环境常量）**逐条登记理由**，默认不许差异——A4 零未登记项才过。

**数据分区（spec §2.5）**：教学 store（curriculum/mother_questions/notebook/学习进度/h5_links.json）→照搬进 tutor 工作区；knowledge_bases/parse_cache→导入④实例；memory/不搬（tutor 记忆走②槽）；partners/system/user/users 不搬。

**依赖纪律**：vendor 子树**允许新 pip 依赖**（零裁剪覆盖依赖最小化——tab_export 的 docx/pdf 渲染器等），复-0 依赖核对出清单、逐条登记（含版本），不装原仓全量 requirements、按闭包最小装。

**口径差登记（P2×2，不回炉）**：①**F 批编号**按 ⑤R §四 F 行字面定稿：F1=(workspace) 组→tutor 后台、F2=h5 组→tutor 空间、F3=(admin)+(auth)+(utility)→平台承接与合并、F4=入口接线与菜单终版；附件五 §3.3.5「tutor 后台（⑤R F3）」注记按「F1=工作台组（落点=后台）」理解——勘误登记。②**A-2 卡配置落点**：AdminHome 页随 R1 退役、卡配置能力保留——默认落位 F1 教学设置页「专家卡配置」tab（附件四 §10.2「管在专家」判定延伸），开放裁定，用户可改。

**菜单单源**：菜单树以**附件五 §3.3.5 终版**为唯一基准（平台 21 项+tutor 空间 12+tutor 后台 3+wenshu 空间）；F 批页面路由与注册一律对表落位。

## 二、文件结构

| 文件/目录 | 动作 | 批 |
|---|---|---|
| `backend/scripts/dt_baseline/`（样本+截图+清单） | **创建**（复-0 底册） | 复-0 |
| `backend/app/vendor/deeptutor/**`（教学域子树原结构） | **创建**（照搬+接线） | B1-B4 |
| `backend/app/api/dt_knowledge_adapter.py` | **创建**（契约适配层） | B1 |
| `backend/app/core/dt_auth_shim.py` | **创建**（认证 shim） | B1 |
| `backend/app/main.py` | 修改（vendor 挂载原 prefix） | B1 |
| `.env`（DT_TUTOR_WORKSPACE_ROOT 等） | 修改（路径根单点） | B1 |
| `backend/app/api/knowledge_base.py`+④页 | 修改（B0 差距增强+DT 页语义并入） | B0/F3 |
| `backend/app/services/tupu_deepagent.py`/工具注册 | 修改（E1 工具面） | E1 |
| `frontend/src/pages/tutor/**`（新页族）+`expertPages.tsx`+`navigation.tsx` | 创建/修改 | F1/F2/F4 |
| 退役清单（六页/两后台页/tutor_admin.py/tutor.py/9 工具/PG 四表冻结/相关测试） | 删除/冻结 | R1 |

## 三、批与任务分解

### 复-0：底册与闭包（全件生命线——零裁剪审计的底册在此冻成）

- [ ] **0.1 tupu 基线存照**：pytest 通过数/manifest（`_diag_assembly_baseline5R.json`）/WBS e2e 成功行；**抢跑存量实测登记**（R1 退役底册）：`frontend/src/pages/tutor/` 六页+`tutor/admin/` 两页+`ExpertGrants.tsx`（已实测在）+`backend/app/api/tutor.py`（6 端点）+`tutor_admin.py`+mcp 9 工具（grep 实测计数）+PG learning 四表。
- [ ] **0.2 原仓起服务**：`D:\gitcangku\xiaobaohaohao\DeepTutor`（.venv 在仓内）——按原仓 README/compose 起 backend+web；**临时端口以原仓默认实测为准，禁占 28000/23000，录完即停**（不留常驻进程）。
- [ ] **0.3 端点对拍基线**：全教学域端点（§2.3 表 13 router+curriculum）样例请求/响应 JSON 落盘 `backend/scripts/dt_baseline/endpoints/`——httpx 脚本遍历端点清单（`GET/POST` 各带代表性样例，响应原文落档，含错误形态）。
- [ ] **0.4 逐屏截图底册**：Playwright headless 逐屏走原仓 web 五路由组（(workspace)/h5/(admin)/(auth)/(utility) 全页面——页面底册以 §2.6 实测清单+复-0 全量补截断项），截图落 `dt_baseline/screens/`。
- [ ] **0.5 chat 能力清单提取**（E1 映射审计左源）：原仓 capabilities/+前端 chat 调用面（home/h5-chat 的工具与端点调用）→能力清单冻结。
- [ ] **0.6 knowledge×④ diff**：knowledge.py 端点全清单×④现有端点机械 diff→**B0 差距清单**（含「④可承接（适配层）/差距（B0 增强）/回退判定」三分类初判）。
- [ ] **0.7 调用闭包+import 闭包 grep**：从 web/ 全部 API 调用 grep 出闭包（**覆盖 main.py 内联路由/静态挂载**——L352-357 curriculum/pages 一例）→**能力清单机械冻结**（与 spec §2.3 实名清单+附件五 78 行主表逐项对账，出入项登记）。
- [ ] **0.8 全路径 diff 冲突审计**：复刻路由全路径×tupu 现役路由全路径——撞车项清单（quiz_judge 挂 /api/v1 根、unified_ws 同前缀——逐路径核）。
- [ ] **0.9 依赖兼容核对**：闭包内 import 的第三方包×tupu 现装——新依赖清单（版本钉死）。
- [ ] **0.10 wechat_push/voice 闭包判定**：入闭包→全还原（含渠道配置面）；不入→⑥-8 登记。
- [ ] **0.11 对账+Commit**——三件套；`git commit -m "⑤R复-0：底册与闭包（端点基线+逐屏截图+能力清单冻结+冲突审计+依赖核对）"`。

**验收门（spec §四）**：底册落盘（差异台账开账）。

### B0（条件批）：④差距增强+④页 DT 语义并入

- [ ] **步骤 1（条件判定）**：0.6 差距清单非空才启动；空→登记跳过。
- [ ] **步骤 2：④差距增强**：差距端点逐个增强④（沿 m15 升级路线 a 纪律+变更记录）；单端点适配成本>复刻成本→**保底回退**登记转域内复刻。
- [ ] **步骤 3：④页 DT 语义并入**（附件五 §3.6 知识库管理行）：实例浏览/文档管理/解析状态/检索测试语义并入④页（与 F3 的菜单更名协同，此处做页面语义）。
- [ ] **步骤 4：验收+对账+Commit**——④回归全绿+m15 变更记录；`git commit -m "⑤R B0：④差距增强+DT页语义并入（B0条件批）"`。

### B1：课程与题库（vendor 落位+接线四点落地）

- [ ] **步骤 1：vendor 骨架+四点接线**：

```python
# backend/app/main.py（⑤R B1）：vendor 子树挂载——原 prefix，端点契约不变。
from app.vendor.deeptutor.api.main import tutor_routers  # 逐 router 原前缀
for r in tutor_routers:  # [(router, prefix), ...] 与原仓 main.py L441-588 挂载表一致
    app.include_router(r.router, prefix=r.prefix)

# backend/app/core/dt_auth_shim.py（接线点1）：同名同形——原仓 `dependencies=_auth` 零感知。
# ?u=→会话用户（缺省=admin 桌面语义保留）；access_code 能力照常（h5_links 域内）。
from app.core.auth import get_current_user  # ⑥-2a 基座
def _auth(request):  # 同名同形 shim：原仓依赖签名不变，实现背靠 tupu 会话
    return get_current_user(request)

# .env（接线点2）：路径根单点
DT_TUTOR_WORKSPACE_ROOT=backend/data/experts/tutor/workspace
```

- [ ] **步骤 2：契约适配层**：`dt_knowledge_adapter.py`——`/api/v1/knowledge/*` 原形状路由→实现指④（0.6 清单「④可承接」类）；数据导入（knowledge_bases/parse_cache→④实例，tutor 卡 knowledge_sources 挂接）。
- [ ] **步骤 3：B1 域照搬**：curriculum（learning 包内 1214 行，含 pages 静态挂载同款接线）+mother_question+storage——原结构进 vendor，路径根走 env，测试随包（learning/tests 对拍资产）。
- [ ] **步骤 4：对拍子集**：0.3 基线中 B1 域端点重放——响应形状 1:1（时间戳/ID 白名单豁免）。
- [ ] **步骤 5：对账三件套+Commit**——`git commit -m "⑤R B1：课程与题库（vendor落位+四点接线+契约适配层+curriculum/mother_question/storage照搬）"`。

### B2：问答判题练习件

- [ ] **步骤 1**：question+quiz_judge+recitation 子包+simhash_util+image_pipeline 照搬（原结构）。
- [ ] **步骤 2**：对拍子集（B2 域端点基线重放）+三件套；`git commit -m "⑤R B2：问答判题练习件（question/quiz_judge/recitation/simhash_util/image_pipeline照搬）"`。

### B3：学习闭环

- [ ] **步骤 1**：learner_profile+mastery_path+self_learning+policy+h5_progress 照搬。
- [ ] **步骤 2**：对拍子集+三件套；`git commit -m "⑤R B3：学习闭环（learner_profile/mastery_path/self_learning/policy/h5_progress照搬）"`。

### B4：配套件

- [ ] **步骤 1**：notebook+question_notebook+book（书源管理面——解析调④）+imports+dashboard+h5_links 照搬；wechat_push/voice 按 0.10 判定（入则全还原含配置面）。
- [ ] **步骤 2**：对拍子集+三件套；`git commit -m "⑤R B4：配套件（notebook×2/book书源/imports/dashboard/h5_links照搬）"`。

### E1：引擎工具面（chat 能力=功能等价）

- [ ] **步骤 1：工具面重建**：复刻域 API→deepagents 工具（tutor 卡 tools 更新——注册表 **grep 实测计数**登记）；tutor 卡变更→manifest 预期差异登记。
- [ ] **步骤 2：映射审计（spec §四验收门）**：域工具面↔复刻端点**能力映射清单**——每工具映射一端点、零缺失（左源=0.5 chat 能力清单）。
- [ ] **步骤 3：e2e**：关键域操作经 tutor chat 完成（讲题问答→判分→错题录入动线）。
- [ ] **步骤 4：对账+Commit**——`git commit -m "⑤R E1：引擎工具面（域API→deepagents工具+映射清单审计+chat动线e2e）"`。

### F1：工作台组→tutor 后台（(workspace) 组页面重建）

- [ ] **步骤 1**：母题库管理×6 子页（主列表/new 录题/photo 拍照/photo-center 拍照中心/analysis 错题分析/review+trash）+书源管理——antd 重建，布局/交互/文案照原样，逐屏对 0.4 底册。
- [ ] **步骤 2：教学设置**（settings/curriculum：FSRS/调度/教材参数）+**「专家卡配置」tab（A-2 成果落位——开放裁定，默认在此）**。
- [ ] **步骤 3：expertPages 后台注册**（/e/tutor/admin/{mother-questions×6, book, settings}）+逐屏对拍；三件套；`git commit -m "⑤R F1：工作台组→tutor后台（母题库×6+书源+教学设置+卡配置tab）"`。

### F2：h5 组→tutor 空间（12 菜单项）

- [ ] **步骤 1**：对话（①壳复用+移动形态适配）/自主学习+教材学（learn/textbook）/课堂/复习/错题录入（手动/拍照/对话式）/错题本（含导出 tab_export）/精通之路（paths+[bookId]）/学情报告（report）/知识地图（atlas——cytoscape 组件可复用平台图件、数据分治）/教材阅读（book/[bookId]）/笔记本（学习+题目两 tab）/分享（share 页照原样+各页内嵌动作）。
- [ ] **步骤 2：逐屏对拍+动线 e2e**（首页→章节自主学习→错题录入管理→练习判分→精通之路——串行+截图）。
- [ ] **步骤 3：对账+Commit**——`git commit -m "⑤R F2：h5组→tutor空间12项（逐屏对拍+动线e2e）"`。

### F3：平台组承接与合并（(admin)+(auth)+(utility)——附件五「合并·tupu 为主」落位）

- [ ] **步骤 1：(admin)/(auth) 承接**：users 用户管理语义（列表/角色/启停）→**并入 ExpertGrants 页**（挂 B-2 尾步执行，本批登记衔接）；login/register→⑥-2a 登录（B-3 承接，登记）。
- [ ] **步骤 2：utility 组合并**：memory×8 分层视图语义（L1/L2/L3 分层 tab/记忆图谱/resolve）**并入 memory-admin**（单套不双轨）；knowledge 页语义并入④（与 B0 协同收口）；agents 六家=③连接实例（登记映射，无代码）；appearance/chat/me/profile→用户态（⑥-2a 用户面，登记）；attachments 按 0.7 闭包定（差距则平台补最小件）；playground 不复刻（等价物已有）。
- [ ] **步骤 3：wenshu 双入口等值核验**（首页直入保留+①等值切换——附件五 §3.6 行）。
- [ ] **步骤 4：对账+Commit**——`git commit -m "⑤R F3：平台组承接与合并（users→赋权/memory分层视图并入/六家映射/用户态登记）"`。

### F4：入口接线与菜单终版（附件五 §3.3.5 菜单树落地）

- [ ] **步骤 1：平台层 21 项**：菜单树对表落位——**「向量管理」更名「知识库管理」+/vector 路径重定向**；其余原样。
- [ ] **步骤 2：专家门户+侧栏**：卡墙 tutor 卡接线（F4 接线=附件五行）；侧栏=tutor 空间 12 项+后台 3 项（admin 可见；wenshu 退化单 chat 项——等值）；suggestions 动线。
- [ ] **步骤 3：ACL**：与 B 件联调位（vendor shim 统一门——B-1 执法点 3；前端守卫管体验不管安全）。
- [ ] **步骤 4：入口动线 e2e**（门户→tutor 空间各页→后台）+三件套；`git commit -m "⑤R F4：入口接线与菜单终版（§3.3.5菜单树+更名重定向+门户侧栏+ACL联调位）"`。

### R1：退役清理（以复-0.1 实测清单为准）

- [ ] **步骤 1：前端退役**：Tutor 六页（Learn/Path/Practice/Progress/Review/WrongBook）+tutor/admin 两页（AdminHome/AdminZones）+expertPages 对应注册项。
- [ ] **步骤 2：后端退役**：`tutor_admin.py`+/api/tutor 六端点（`tutor.py`）+9 件 MCP 教学工具（注册表 grep 复测计数归零）。
- [ ] **步骤 3：PG 四表冻结**（learning_* 表保留不迁移，M00 登记；有测试数据不迁——原仓数据随 B 批来）。
- [ ] **步骤 4：测试退役**：test_tutor_api/test_tutor_tools/⑤补件测试随端点工具下线（pytest 全量不降验证）。
- [ ] **步骤 5：验收**：pytest 全量+**wenshu 零感知**+manifest 复验（tutor 差异=复刻件预期项）；`git commit -m "⑤R R1：退役清理（六页+两后台+六端点+9工具+PG四表冻结+测试退役）"`。

### R2：终验收（spec §五 A1-A6 全组）

- [ ] **A1 端点契约对拍等值**：0.3 基线样本全量重放（**含 knowledge 适配层端点**），响应形状 1:1（时间戳/ID 白名单豁免）。
- [ ] **A2 前端逐屏对拍+动线 e2e**：五路由组逐屏对 0.4 底册+关键动线（串行+截图）。
- [ ] **A3 零裁剪审计**：0.7 冻结清单逐项勾验（router×13+learning 实名件+页面组——含 recitation/tab_export 子包、simhash_util、llm_cost_log、mother_question），缺项=不通过。
- [ ] **A4 零重设计审计**：数据模型字段级 diff+端点契约 diff+**差异台账零未登记项**。
- [ ] **A5 基座回归**：wenshu 零感知；平台页零破（探查页 e2e+pytest 全量）；tutor chat 与复刻域并存不串；**通用层不双轨**（memory/KB 单套）。
- [ ] **A6 铁律**：28000/23000 不动、无新端口、e2e 串行、PYTHONUTF8。
- [ ] **M00 汇总+Commit**：vendor 子树/四点接线/契约适配层/新依赖清单/新工具面/菜单终版/退役清单（六页两后台六端点九工具 PG 四表冻结）/卡配置落点终裁；`git commit -m "⑤R R2：终验收A1-A6全组+M00汇总"`。

### 尾段（权限件与守卫收口——见 B 计划 v2/A 计划 v3）

R2 过闸后按总序执行：B-0 泄漏修复→B-1 expert 进 ACL（**执法点 3=vendor shim 统一门**）→B-2 赋权面（+users 语义并入）→A-4 守卫收口（A 计划 v3 存活批，前置=⑤R R2+B-1/B-2）→B-3 登录动线→**B-4 灰度翻转全局最后**。

## 四、风险

| 风险 | 应对 |
|---|---|
| 前端五路由组全量重建工作量大 | F 批不合并+0.4 底册先行+逐屏对拍逐批验收 |
| 契约适配层④形状≠DT 形状 | A1 对拍覆盖适配端点+保底回退（功能完整性优先） |
| 原仓起服务环境不可用 | .venv 在仓内实测；临时端口纪律+录完即停；起不来=停下问用户（底册是全件地基） |
| vendor 依赖面扩散 | 0.9 闭包最小装+版本钉死登记，不装全量 requirements |
| 全路径撞车（/api/v1 根挂载族） | 0.8 全路径 diff 先行定案，撞车项逐个处置登记 |
| F 批编号/A-2 落点口径差 | §一口径差登记（F1-F4 字面定稿+卡配置默认 tab 可改） |
| 退役误伤 wenshu | R1 三件套+wenshu 零感知断言+manifest 复验 |

## 五、自检

1. **规格覆盖度**：⑤R §一四铁律→§一纪律；§2.2 通用合并表→F3/B0/尾段；§2.3 个性化表→B1-B4；§2.4 专案→B1 步骤 2+B0；§2.5 数据分区→§一；§2.6+附件五 78 行主表→F1-F4/R1（逐行有落点：原样保留=零改动核验、合并 tupu=F3/B0/F4、合并 DT=R1+F 批、复刻=F 批、分治=F2 report/atlas、并入用户态=F3 登记、域外=F3 登记）；§四批表→批结构一一对应；§五 A1-A6→R2；§六诚实账→风险表。遗漏：无。
2. **占位符扫描**：无待定——原仓起服务端口/截断页面清单为复-0 实测目标（有明确步骤与纪律，非占位）；四点接线/适配层/shim 有实码骨架。
3. **类型一致性**：端点 prefix 在 vendor 挂载表/适配层/对拍基线三处同源（原仓 main.py 挂载表）；菜单树单源（附件五 §3.3.5）；`_auth` shim 同名同形（原仓依赖签名不变）；工作区根 env 单点；工具面计数口径 grep 实测（E1/R1 两处一致）。
