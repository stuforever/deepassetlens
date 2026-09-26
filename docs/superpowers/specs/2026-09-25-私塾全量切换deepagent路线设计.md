# 私塾全量切换 deepagent 技术路线设计（v3.0，自包含·技术债清零）

> 2026-09-25 · 用户定调：**全面切换技术路线，功能能力重写，不保留 vendor 技术路线，不留老技术债**。
> **v3.0（2026-09-25）**：权限线两份文档（《2026-09-24-权限体系重构-design.md》《…实施计划.md》）已按用户指令删除；原本设计的"地基"——教学 11 件 MCP 化、X-Tupu-User 身份头、确认流——全部**内化进 R0**，本设计自此无外部依赖、单文档自包含。所有"冻结/保留/后续批"项按清零定调做终局处置（§四、§五）。
> **v3.0.1 实施对账（2026-09-25，权限线收尾提交 ad06416 后）**：权限线代码地基在其文档删除前已落地并提交——R0 的 ②教学 11 件 MCP 回挂+X-Tupu-User 身份头+EXEC 两段臂（T8a/T8b，53c0235/6128c3d）、④存活数据面 auth 换平台（T6批1-3，0d1db70/ad06416）、⑤前端死调用清理（同 ad06416）、vendor auth 三件套物理删除（routers/auth.py、services/auth.py、users.json 存储面）均已**完成**；§2.2/§2.3/§四相应项已就地标注 ✅。
> **v3.0.2 实施对账（2026-09-26，R0-R5 一夜执行后）**：R0-R5 全部批次已执行，账目如下（全部含测试，单批单 commit）。
>
> **R0（基建并轨）✅ 完成**：③文档 4 件 MCP 化（c6a0a08：generate_docx/pptx/xlsx/pdf，EXEC 12，注册集 34；顺修 T8a 潜伏 bug——execute_entity_api/execute_doris_sql 签名缺 confirm_token 每调即 NameError）；①LLM 收编+G5（8f8b9b0：双轨 agent 流挂卡默认连接——G5 多实例/#e 缓存因子/共用 checkpointer/thread_id 专家前缀经盘点既有；"一处配模型两专家生效"经实测：平台默认连接改指 4coding glm-5.3-flash 后双专家同源）；⑥session 元数据迁库（a70438c：SishuSessionMeta 表+幂等迁移脚本，实测 3 库 272 行落账）。
> **R1（chat 主对话）✅ 完成**：G1 询问 Future（cd42e7f：pending_question 服务+专家卡 ask_user 进程内工具（RunnableConfig 注入）+/resume 通道扩 question_id+answer+run_chat 会话代答拦截）；tutor/practice、insight 技能包 T8b 既有；前端对话页引擎批2 已走平台桥 SSE；**Playwright 全链路对拍通过**（21a5a7f：/e/sishu/chat 练习请求→桥 SSE→sishu deepagent 流式出题 LaTeX 渲染，内容实质增长+关键词命中；顺修 create_tupu_agent 缺 user 形参的 T5 潜伏 NameError——fresh assembly 全挂被缓存命中态掩盖）；G3 vision 位/白名单/回填端点既有+image_url 通道既有（前端选择器按 vision 标记过滤=随 vendor LLM 配置面收编，登记 §七残余）。运维处置：平台默认连接原指探针死链（ux-probe），改指 4coding glm-5.3-flash（记忆确认的私塾对话模型）。
> **R2（question+notebook）✅ 完成**（9f6913a）：笔记 3 件 MCP 工具（has_notebooks/list_notebook 只读、write_note EXEC 两段臂，NotebookManager 数据层收编留用）+ tutor/{solve,notebook} 技能包（摘要/选取纪律自 vendor notebook agents 逐字保留）；旧 notebook/mother_question/question_notebook 路由经核对批6 已卸挂。注册集 34→37（EXEC 13）。
> **R3（research）✅ 完成**（9cf9946）：research-analyst B 档子代理挂专家卡装配（deepagents subagents 参数；大纲→分节→汇总三节点语义与双轨 run_research 同源；工具=父面∩search_kb+进程内 web_search 包装）；wenshu 问数面零感知；装配实测+3 项规格测试过。
> **R4（math_animator+co_writer）✅ 完成**（0120353）：协同写作 3 件 MCP 工具（list_documents/read_document 只读、write_document EXEC 两段臂，CoWriterStorage 收编留用）；G4 长任务经盘点既有承接（动画渲染=双轨 run_visualize 图内 manim→Sandbox 9385+SSE 进度；真超时两段交互留 R6 书籍族）。注册集 37→40（READONLY 26/EXEC 14）。
> **R5（清零删除面）✅ Wave1 完成+Wave2-4 登记阻塞**（a82eb04，-12,169 行）：**已删**=已卸挂 24 个 vendor 路由文件（mother_question/notebook/question_notebook/book/sessions/memory/voice/wechat_push/dashboard/imports/capabilities_settings/mcp_settings/space_mcp/space_cli_apps/plugins/agent_config/system/personas/question/quiz_judge/unified_ws/learner_profile/mastery_path/self_learning）+vendor 遗留独立服务器（api/main.py+run_server.py）+被测主体消失的 5 个 vendor 锚定测试；tutor_routers 死导入/死行摘除（存活挂载相对次序保持）；表基线 87→88；SISHU_MOUNTS 漂移守护改「vendor 行存在才比对」。**§七 grep 实测**：core/agentic(0)/_dt_require_auth(0)/_dt_require_admin(0)/routers.auth(仅注释)/unified_ws(仅注释)/users.json(仅注释+T6批3 守卫桩)/skills/builtin(仅注释)/services/subagent(后端 0)/lib/auth(仅注释)/useAuthStatus(平台新版保留)——十项清零或注释级。**登记阻塞**（每项均有一个活消费方，需各自迁移批后删）：A 组 agents/chat+core/agentic+event_bus（book 一期保运行 R6 重写后删+vendor chat/sessions REST 被 book-api 消费+平台 sishu_learning/notebook.py 复用 NotebookSummarizeAgent）；C 组 sqlite_store（桥 h5 持久化消费，待切 SishuSessionMeta/checkpointer）；D 组 pocketbase(127 处)/vendor LLM 链（knowledge 活面）；E 组 skills/builtin（vendor skills/list 被对话能力选择器消费，待平台技能 API 迁移）；F 组 services/subagent CLI+partners/channels（tools/settings 活路由+capabilities/registry 链+partners/channels 三文件他窗未提交改动占用+前端 partners/CLI 设置页）；G 组前端 vendor 对话栈（unified-ws.ts 仍被多组件 import）；attachments/h5_links 两路由文件他窗未提交改动占用。**全量回归**：~1390 过（预存 3=batch8_hybrid 检索种子环境+1=嵌套 pytest 管道环境偶发+1=r2_platform_high 他窗脏文件在改）。
> **v3.0.3 复评处置（2026-09-26，五维事后评估后）**：①**book 核实**——一期**确在运行**：`/api/v1/book/books`=200（平台 sishu_book 路由 PG 面）；"agents/book 已删"说法不准（agents/ 从无 book 子目录），真阻塞=vendor `sishu_full/book/` 服务（blocks 惰性 import agents/{notebook,math_animator,visualize}）——A 组删除阻塞表述据此修正为「R6 book 重写换掉 sishu_full/book 服务后删 agents 族+core/agentic」。②**manim 入口下线**（c8d0348）：渲染沙箱 9385 未部署且镜像无 manim 必败——前端移除 Animation/Storyboard 选项、双轨即时明示降级（不烧 LLM），R6 随沙箱部署恢复。③**ExpertChat sishu 死分支删除**（a1cacd9）：动态数拉取/双胶囊/7 宫格均不可达（/e/sishu/chat=TutorHomeChat），防锚点再误。④**EXEC 签名契约测试**（d297634）：EXEC 件 schema 必含 confirm_token——当即抓到 execute_sql 直连无两段臂的同类潜伏缺陷并补齐；14 件 EXEC 全绿。⑤**.env 残留 ENABLE_AUTH=true 修正为 false**（裸启动雷；权限现状另见《docs/architecture/权限体系现状说明-2026-09-26.md》——补评估缺口③文档债）。
> 本文档取代《2026-09-25-tutor与deepagent路线差异审计.md》的"渐进收编"立场（该文档降级为差异事实参考）。
> 边界声明：**平台既有鉴权（core/auth 五层判定 + SuperTokens 登录）维持现状不动**，本设计只做"vendor 身份面 → 平台既有鉴权"的换线，不引入任何权限体系改造。

---

## 一、总原则（五条）

1. **框架唯一**：全平台只有 LangGraph/deepagents 一个 agent 执行框架。core/agentic/（loop.py/labeled_step.py/tool_dispatch.py/client.py/labels.py）整目录废弃删除，不做任何兼容层。
2. **功能平移而非搬运**：7+2 族业务能力的**提示词资产（yaml）与产品语义**保留，**编排代码全部重写**为 deepagents 子图/工具/技能剧本；禁止把 vendor 代码包一层适配器糊弄。
3. **基建全部用主线**：LLM 配置=kg_llm_connection_configs 表；会话=checkpointer+PG；事件=SSE（WS 仅留 h5 语音必要场景，事件词表对齐 SSE）；技能=data/skills 平台系；工具=MCP 唯一面。
4. **依赖主线已有机制，不新造**：HITL=SkillPolicy asyncio.Future 审批轨（skill_policy.py L99-106）+ interrupt_on 装配（init_db L76）；多模态=image_url data-url 通道（dt_agent_orchestrations.py L124-134 已验证）；流式=astream_events v2。
5. **零留债（v3.0 新增）**：任何 vendor 代码只有三种终局——**重写 / 收编 / 删除**；不允许"冻结保留""双源并存""以后再说"。切换完成态 = §七 grep 零残留清单全过。

---

## 二、迁移范围总账

### 2.1 业务族（9 族，重写或删除）

| 族 | 用户可见功能 | 核心 vendor 依赖 | 终局 |
|---|---|---|---|
| chat 对话族 | 私塾主对话（练习/判分/复习/错题） | loop pause/ask_user（agentic_pipeline.py L894-932）+ capabilities 注册表 | **重写**：sishu 专家卡 deepagent 实例 + 教学 11 件 MCP 工具 + tutor/practice、insight 技能剧本；ask_user → G1 询问 Future |
| question 解题族 | 母题解题、题本 | labeled_step 多步推理 | **重写**：解题技能包（yaml 逐字搬入 data/skills/tutor/solve）+ deepagent 子图 |
| research 调研族 | 深度调研报告 | 7+ label 协议（pipeline.py L33-160）+ ask_user（L608-716） | **重写**（B 档瘦身，§五）：3-4 节点 LangGraph 子图，作 subagent 注册 |
| notebook 笔记本 | 学习笔记本 | tool_composition.py（_shared L35-42） | **重写**：list_notebook/write_note/has_notebooks 3 件 MCP 工具 + 笔记技能包 |
| math_animator 数学动画 | Manim 动画生成 | 外部渲染进程 + 长耗时 | **重写**：动画工具 MCP 化 + G4 长任务方案；产品层确认流保留 |
| vision_solver 拍照解题 | 拍照/图片解题 | 多模态输入 + vision fallback（labeled_step.py L375-376） | **重写**：主线 image_url 通道已具备；vision 技能包 + capabilities 表 vision 标记选型 |
| co_writer 写作族 | AI 协同写作 | co_writer/ 整套长文档状态 | **重写**：写作技能包 + 文档状态工具 MCP 化 + G4 长任务 |
| book 书籍族 | 书籍生成（多 agent） | book/agents/ 多 agent 协作 | **二期重写**（R6）：书籍生成子图；一期旧路由保运行、R6 重写后删 |
| partners 伙伴/推送 | 编程伙伴（外部 CLI）+ 微信/telegram 推送 | services/subagent/ 进程编排 + partners/channels/ | **删除**（§五决策）；学习提醒类通知进 R6 平台通知服务重建清单 |

### 2.2 体系件（废弃/收编）

| 体系 | vendor 现状 | 终局 |
|---|---|---|
| LLM 配置 | resolve_llm_runtime_config 自有链 + provider_registry 12+ 家 + capabilities.py 500+ 行协议差异知识 + settings.py profile CRUD | **收编**（R0）：sishu 运行时改读 kg_llm_connection_configs；capabilities.py 差异知识提炼进表 extra_config；settings.py LLM 面下线删除 |
| session 存储 | sqlite_store chat_history.db + unified_session_manager + pocketbase_store 残留 | **废弃**（R0 迁元数据→PG，R5 删代码）：会话=checkpointer（thread_id）；历史数据一次性迁移脚本 |
| EventBus/WS | events/event_bus.py + unified_ws /ws + chat.py 旧 /chat | **废弃**（R5）：对话流式=SSE；WS 仅保留 h5 语音双向必要场景，事件词表对齐 SSE |
| builtin 技能 | skills/builtin/ docx/pptx/xlsx/pdf/skill-creator | docx/pptx/xlsx/pdf **重写为平台 MCP 工具**（G6/R0）；skill-creator **删除**（平台技能系已覆盖其职能） |
| subagent 外部 CLI | services/subagent/（claude_code/codex/gemini/kimi/opencode 进程编排） | **删除**（§五决策） |
| vendor 技能管理面 | routers/skills.py + 前端 vendor 技能页 | **删除**（R5）：技能统一 data/skills 平台系 + SkillManager 页 |
| vendor auth 面 | services/auth.py（sishu JWT/dt_token/users.json/bcrypt）+ routers/auth.py + _dt_require_auth/_dt_require_admin | ✅ **已完成**（T6批3，ad06416）：vendor JWT 登录/用户存储/PocketBase 分支物理删除；桥迁 api/vendor_bridge.py（require_auth/require_admin/platform_*/ws_require_auth + codex 回调保活），身份源=平台 AuthMiddleware/平台 JWT |
| multi_user 身份残留 | users.json 文件存储 + multi_user/identity.py | ✅ **已完成**（T6批2/批3）：CurrentUser 身份源=平台 JWT（AuthUser slug=username）；users.json 存储面删除，identity.py 改平台 auth_users 表为源；分目录机制（功能）保留 |
| 杂项基建 | i18n / logging / runtime / utils / config / wechat identity / codex_oauth | **随 R5 顺带删除**，不立项 |

### 2.3 数据面存活族（tutor_routers 25 个挂载点三分处置）

> 实证（T6批3 前原状）：tutor_routers 25 个 vendor 挂载点全部带 vendor `_auth`/`_admin` 依赖。它们不是 agent 框架问题，但挂着 vendor 身份面，须随切换一并清算。**T6批3（ad06416）已完成换线**：全部挂载点现走 api/vendor_bridge.py 平台桥（auth=0 local-admin 语义保留、auth=1 平台 JWT 验签），vendor 依赖清零；下表处置中"下线/删除"仍按批次执行。

| 处置 | 路由族 | 说明 |
|---|---|---|
| **随重写族下线** | mother_question、question_notebook（R2）、co_writer（R4）、notebook（R2 新工具替代）、sessions（checkpointer 替代）、multi-user（平台身份替代）、book（R6） | 新链路对拍过 → 旧路由删除 |
| **存活数据面：功能保留、auth 机械换平台**（✅ T6批3 已完成） | knowledge、curriculum、learner_profile、mastery_path、self_learning、imports、dashboard、memory、h5_links、h5-settings、voice（h5 语音） | `_auth`→require_expert("use","sishu") 已叠加处摘 vendor 依赖；`_admin`→平台 admin 判定；模式照抄 sishu_learning `_enforce.py` 既有桥 |
| **删除面**（R5） | wechat_push（功能暂停，进 R6 重建清单）、capabilities_settings、settings（LLM 面收编后）、mcp_settings、space_mcp、space_cli_apps（与平台 mcp_server 重复）、skills | 见 §四清单 |

---

## 三、主线框架缺口与补齐方案

| # | 缺口 | 严重度 | 补齐方案 |
|---|---|---|---|
| G1 | **HITL 暂停-恢复**：vendor ask_user 是 loop 一等公民；主线有 SkillPolicy asyncio.Future 审批（TABLE_MISSING/CATALOG_MISSING）+ interrupt_on 装配 | 已有机制，需泛化 | "审批 Future"泛化为"询问 Future"：SkillPolicy 注册通用 pending_question（问题文本+选项），SSE 推 question 事件，前端答后 resolve——复用现有 approve 通道改字段，不新造机制 |
| G2 | **多步编排**（research 族 label 协议） | 需扩展 | LangGraph 子图：research 独立 graph（rephrase→decompose→retrieve→report），作主 deepagent 的 subagent 注册；deepagents>=0.7.7 subagents 参数已支持 |
| G3 | **多模态 vision** | 已具备 | image_url data-url 通道编排层已通（dt_agent_orchestrations.py L124-134）；需做：llm 连接表 capabilities 加 vision 标记 + 模型选择器按标记过滤（UX 总册已定） |
| G4 | **长任务/后台**（动画渲染、写作、书籍生成，分钟级） | 需扩展 | 不引队列框架（YAGNI）：图内异步节点 + SSE 进度事件（trace 通道复用）+ 前端"产物"区轮询完成态；真超时的（书籍生成）拆"提交任务→轮询产物"两段交互 |
| G5 | **专家多实例**：当前单 agent 全局实例（wenshu） | 需扩展 | 专家卡维度实例缓存（experts.py 已按卡装配）：sishu 卡独立 deepagent 实例与 wenshu 并存；checkpointer 共用，thread_id 带专家前缀隔离 |
| G6 | **文档生成工具**（docx/pptx/xlsx/pdf） | 需新建 | 重写为 MCP 工具 4 件：内部生成库（python-docx/python-pptx/openpyxl 已在依赖）留用，注册面/确认流（产品层确认，同 dt_agent_orchestrations 写前确认模式）全走平台 |

---

## 四、技术债清零清单（终局处置总表）

> 零留债原则的落账：每一项 vendor 残留都有唯一终局和落点批次，R5 验收以本表 grep 零残留为准。

| 组 | 残留项 | 终局 | 落点 |
|---|---|---|---|
| A 框架 | core/agentic/ 整目录（loop/labeled_step/tool_dispatch/client/labels）、agents/ 7 族编排 py、events/event_bus.py、unified_ws、chat 旧 /chat WS | 删除 | R5（yaml 提示词已逐字搬走后） |
| B 身份 | services/auth.py（sishu JWT/dt_token/bcrypt）、routers/auth.py、_dt_require_auth、_dt_require_admin、users.json、multi_user/identity.py 存储面、pocketbase_store、wechat identity、codex_oauth | ✅ 前六项**已删除**（T6批3，ad06416）；pocketbase_store、wechat identity（=wechat_push/identity.py，活推送功能随 F 组）、codex_oauth（vendor_bridge 保活回调）按批次清 | 删除（R0 先换线） | R0 换 / R5 删 |
| B' 前端身份 | lib/auth.ts、hooks/useAuthStatus.ts（调 /api/v1/auth/status、/api/v1/auth/login，端点未挂载=死调用 404） | ✅ **已完成**（T6批3，ad06416）：lib/auth.ts 删除；useAuthStatus/SettingsSectionGrid 改平台 /auth/me 口径 | 删除 | R0 |
| C 会话 | sqlite_store（chat_history.db）、unified_session_manager | 删除（数据先迁 PG） | R0 迁 / R5 删 |
| D LLM 配置 | resolve_llm_runtime_config、provider_registry、capabilities.py、settings.py LLM 面、capabilities_settings/mcp_settings 路由及前端设置页 | 收编后删除 | R0 收 / R5 删 |
| E 技能 | skills/builtin/ 5 件、routers/skills.py、前端 vendor 技能管理页 | 4 件重写 / 其余删除 | R0 重写 / R5 删 |
| F 伙伴渠道 | services/subagent/ 外部 CLI、partners/channels/（weixin/telegram/msteams）、wechat_push 路由、前端 PartnerChat.tsx、pages/tutor/partners/ | 删除（功能进 R6 重建清单） | R5 |
| G 前端对话 | tutor 桌面对话页（独立消息流/composer/WS 栈）、lib/unified-ws.ts | 收敛到平台对话栈（UX 总册：统一对话页+统一 ThinkingChain）；voice h5 语音保留独立轻量 ws client | R1 收敛 / R5 删 |
| H 杂项 | vendor i18n/logging/runtime/utils/config 基建 | 随删 | R5 |

---

## 五、决策收口（按"技术债清零"定调锁定，可复议）

| 决策点 | 结论 | 理由 |
|---|---|---|
| research 族深度 | **B 档场景瘦身** | 私塾调研实际形态="课文主题调研+报告"；按实际场景重写 3-4 节点子图，提示词资产逐字保留，citation/token_tracker 以主线审计/追踪面替代 |
| 外部 CLI subagent（伙伴） | **删除**（原"冻结"建议作废） | 冻结=留债；编程伙伴与"数据资产+私塾教学"双主线定位偏离；若将来有呼声，按主线 deepagents subagent 机制重做，而不是复活 vendor 进程编排 |
| 微信/telegram 推送渠道 | **代码删除，功能进 R6 重建清单** | wechat_push 路由虽在挂载（tutor_routers L91），但依附 vendor 身份面与 EventBus，保留即留债；学习提醒是真实产品价值，R6 以"平台通知服务"重写（独立小服务，纳平台设置面） |
| book 书籍族 | **二期重写** | 一期旧路由保运行（不删功能），R6 重写为子图后删旧代码——这是"功能延期"不是"技术债保留" |

---

## 六、重写批次（自包含，每批含对拍验收）

| 批 | 内容 | 工期 | 验收 |
|---|---|---|---|
| **R0 基建并轨 + 身份地基** | ① LLM 配置收编：sishu 运行时改读 kg_llm_connection_configs，capabilities.py 协议差异知识提炼进 extra_config；G5 专家多实例一并做 ② ✅**已完成**（T8a/T8b，53c0235/6128c3d）：教学 11 件 MCP 回挂（薄包装消费 tutor_inprocess.py SPECS 单源，description 逐字沿用）+ X-Tupu-User 身份头（HMAC ±300s，_build_agent 注入、/mcp 面中间件验头重建 ContextVar，缺头 fail-closed——🔴-4 正面解法）+ EXEC 两段臂确认流 ③ 文档 4 件 MCP 化（G6） ④ ✅**已完成**（T6批1-3，0d1db70/ad06416）：存活数据面 auth 机械换平台 + vendor auth 物理删除 ⑤ ✅**已完成**（ad06416）：前端死调用清理（lib/auth 删、useAuthStatus 改 /auth/me） ⑥ session 元数据迁 PG | 4d→**余约 2d**（②④⑤已落地） | 一处配模型两专家生效；11 件工具 sishu 卡可见，**跨用户隔离负向用例**（两用户并发 fsrs_due 互不可见）通过（T8a 已验）；25 挂载点 vendor 依赖清零（T6批3 已验）；技能页见文档工具 |
| **R1 chat 主对话** | sishu 专家卡 deepagent 实例 + G1 询问 Future + tutor/practice、tutor/insight 技能包（yaml 逐字搬）+ vision 通道（G3）+ **前端对话页收敛平台对话栈** + twin（进程内 SPECS 直通）灰度双轨开启 | 5d | 练习→判分→错题全链路 Playwright 对拍；拍照解题走通；写前确认流产品语义不变 |
| **R2 question+notebook** | 解题技能包 + 笔记 3 件 MCP 工具 + 笔记技能包；旧 notebook/mother_question/question_notebook 路由下线 | 3d | 母题解题、笔记读写对拍 |
| **R3 research** | 调研子图（B 档）+ subagent 注册 | 4d | 调研全流对拍，报告质量人评 |
| **R4 math_animator+co_writer** | 动画/写作工具 MCP 化 + G4 长任务方案 | 4d | 动画生成、写作协同对拍 |
| **R5 清零删除面** | 按 §四清单 A-H 整目录删除：core/agentic、agents 7 族 py、EventBus、unified_ws、sqlite session、vendor auth 三件套、users.json、skills/builtin、capabilities、subagent CLI、partners/channels、wechat_push、mcp/space 配置面、前端 vendor 死代码；twin 删除（灰度稳定后）；旧 /chat WS 下线 | 3d | §七 grep 零残留全过；全量回归 |
| **R6 二期候选** | book 书籍族子图重写、平台通知服务（微信学习提醒）、skill-creator 评估 | 另行立项 | — |

**工期**：R0 余约 2d（4d 口径中 ②④⑤ 已落地）+ R1 5d + R2 3d + R3 4d + R4 4d + R5 3d ≈ **21 个工作日**；R2/R3/R4 人力允许可并行，压缩至 ≈ **17d**。无外部依赖线。

---

## 七、切换纪律与验收

- **双轨切换**：每批"新链路对拍通过 → 旧路由下线"，禁先删后写；
- **提示词资产铁律**：yaml 逐字搬进 data/skills/ 对应包，改一字需标注理由（描述漂移=行为漂移）；
- **全程 Playwright 对拍**（AGENTS.md 铁律），串行；
- **grep 零残留清单**（R5 验收逐项执行）：
  `core/agentic`、`_dt_require_auth`、`_dt_require_admin`、`routers.auth`、`event_bus`、`unified_ws`、`sqlite_store`、`pocketbase`、`users.json`、`skills/builtin`、`capabilities`、`services/subagent`、`partners/channels`、`wechat_push`、`lib/auth`、`useAuthStatus` —— 全部 = 0（前端后端同查）。（进度注记 2026-09-25：`_dt_require_auth`/`_dt_require_admin`/`routers.auth`/`users.json`/`lib/auth` 五项经 T6批3 已实测 = 0；其余项随 R5。）

---

## 八、与既有文档的关系

- **差异审计**（2026-09-25）：降级为"事实参考"，其 S1-S6 渐进路线作废；
- **UX 总册**（2026-09-22）：不受影响——统一对话页+统一 ThinkingChain 正是 R1 前端收敛的依据；
- **权限线文档**：已于 2026-09-25 按用户指令删除；平台既有鉴权（core/auth 五层 + SuperTokens 登录）维持现状，本设计只做 vendor→平台既有鉴权的换线，不引入权限改造；
- 教学工具归属：11 件经 R0 回挂后进入 mcp_server 注册集（19→30+笔记 3 件+文档 4 件+动画/写作若干），与平台工具同面同机制。
