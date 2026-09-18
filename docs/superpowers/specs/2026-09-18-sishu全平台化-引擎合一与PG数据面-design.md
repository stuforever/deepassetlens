# sishu 全平台化：deepagents 引擎合一 × PG 数据面单轨 × vendor 树全清（design）

> 日期 2026-09-18。定调=用户四裁定（本会话）。上游：v3 件（2026-09-16，批1-8 已实施至 `91d5331`，批9 未跑）+⑤R 件（20 批已关账）。
> 本件=第四版转向（v4）：推翻 v3「执行面混合实现+vendor 数据面照搬」的既有授权登记，教学域整体归一平台栈。
> **v1.1 修订（2026-09-18 规划审查收口）**：并入 R3 五发 Critical 处置（§一之二）+执法面第五硬门（§2.4/§五）+协议 E v2（切换 delta+资产哈希双账）+工作区 M 类分诊（批0.0）+批数 17→18（新批15 执法面收口）+33066 另案登记（§八）。

## 一、用户四裁定（2026-09-18，先于一切）

| # | 裁定 | 推翻/收口的既往登记 |
|---|---|---|
| ① | **数据全量迁移**：错题/复习/母题/画像/书库全量（含页面资产）+会话历史 1.2GB+课程教材 2.3GB，全部入 PG | ⑤R「数据分区照搬 vendor store」 |
| ② | **全 vendor 树一次清**：教学核心+partners/voice/wechat/co_writer 全域；零消费域卸挂登记 | v3「裁定点 A vendor 物理保留」；⑥-8「partners 另立件」 |
| ③ | **expert 全局改名 tutor→sishu**：skill_code/路由/菜单/ACL/数据行/agent 代号 | v3「expert_id=tutor 既有键不动」 |
| ④ | **v3 批9 并入本件末批关账** | v3 批9 独立终验 |

既往台账项的归宿：E-23②（mastery/wrong-intake 走 tupu PG learning）由「授权偏离」**转正为本件方向**；E-24①（vendor 判分 prompt 复用）→自研重写（黑盒对拍）；E-25①（BookEngine 直驱）→重写；E-24⑥（vendor SandboxService）→平台客户端；E-30（vendor 冻结 catalog）→③统一；裁定点 A（vendor 物理保留）→**物理删除**（A4 sha256 审计使命随 ⑤R 关账完结，git 历史即存档）。

## 一之二、R3 五发 Critical 处置（2026-09-18 规划审查收口——与四裁定同等效力）

> 来源：`docs/superpowers/reviews/2026-09-17-R3复刻收口审核报告.md`（「修完再合」裁决；2026-09-18 复核实证五发全部未修）。处置原则：落在 v4 重建同一表面上的（C1/C2/C4）随重建**原生修复**，测试纪律（C5）随批0/批15 落地，33066 主数据另案（§八）。

| R3 | 处置 | 落点 |
|---|---|---|
| C1 后端执法层缺位（vendor shim 死代码） | **并入**：新 sishu_*.py 路由族全量挂 `require_expert(use/manage)`（端点×动作映射表=批0.2 机械推导），裸挂 grep=0 断言；vendor 死代码随批16 物理删除终账作废 | 批0.2 映射表／批6-14 各域／批15 探针 |
| C2 ?u= IDOR 跨用户读写 | **并入**：`sishu_user_binding(u)` 会话绑定单点——auth=1 且非 admin 时 u 必须等于会话用户绑定 slug（否则 403），auth=0 桌面语义保留；**一个函数覆盖全部消费点** | 批2 落位／批8 实证／批15 负向 |
| C3 前端 272 处裸 fetch（auth=1 数据面 401 空壳） | **并入（契约面豁免类）**：传输层 Authorization 注入（H5Shell patch 追加/统一 authedFetch，选型开放），不改路由/形状/页面/选择器；**顺序铁律=执法面（C1）之后落地** | 批15 |
| C4 深链 ?session= 永不命中 | **并入**：会话域 PG 化后 `/e/sishu/chat?session=`→平台 sessions `loadSession` 接通（结构性可达）；畸形 % 序列 try/catch 连带 | 批8 |
| C5 pytest auth 模式+33066 主数据 | **测试纪律并入**：新增测试 auth-mode-agnostic；既有 4 败（g1/s4/s5×2）fixture 化；**33066 主数据迁移另案（§八）** | 批0／批15 |

裁定注：C3「前端零改」豁免=传输层单类（Authorization 头注入），契约/页面/选择器零改动红线不破——2026-09-18 规划审查推荐、用户委托规划时认可。

## 二、目标架构（三面+执法面横切）

### 2.1 执行面：sishu agent 唯一引擎（零 vendor 导入）

- **sishu agent=平台 deepagents 装配**：`get_tupu_agent(expert_id="sishu")`（`tupu_deepagent.py` L1501 既有机制——与 wenshu「tupu agent」完全同构，一专家一装配）。
- **8 技能全部 agent 循环**（sishu/chat|solve|quiz|research|visualize|mastery|wrong-intake|book-generate）：统一 `_agent_stream` 骨架（现 dt_agent_orchestrations.py L162）+每技能系统提示词+结构化终答（response_format/FinalAnswer——E-23① response_format 机制沿用）；数据面工具=技能脚本节点（mastery_status/wrong_question_save 既有先例）。
- **判题**：自研评分提示词；行为以黑盒基线对拍（批0 先录题面×作答样本→判分输出，重写后重放 diff），非源码复用。
- **可视化**：平台 sandbox 客户端新件（HTTP→sandbox-executor-manager 9385 平台基建）——非 vendor 导入。
- **建书**：编排重写（意图→书脊结构化→逐页 15 块型路由→块再生），产物写 PG sishu_books 族。
- **桥 `POST /api/v2/skills/capability` 契约不变**（前端 5 消费件零改，除批1 改名）。

### 2.2 数据面：PG 25432 单轨

- 教学数据全量入 PG（表族蓝图 §四），资产 bytea 全量（裁定①）；PG 库预计 +4GB。
- 配置面（31 设置页消费）→平台主库配置表（③先例：llm_connections 同路数）。
- KB→④单源（桥已用 kb_query——E-18 沿用）；knowledge 进度通道归④/平台。
- 记忆面→平台 memory 服务扩展；**三层记忆槽 MD（D1 既有设计）不动**=平台自身机制非双轨。
- `llm-options`（全站模型下拉）切③——E-30 closure。

### 2.3 契约面：前端零改+后端换芯

- 前端复刻件（h5 15 页/11 tabs/书工作台 26 件/设置中心 31 页/MemoryAdmin/PartnerChat）**API 路径与响应形状零变化**。
- 平台路由按 vendor 同路径同形状实现（app/api/sishu_*.py 族），**L2 基线重放**（⑤R 复-0 `dt_baseline/endpoints/` 资产复用）为验收门。
- 唯一前端改动=批1 改名（/e/tutor/*→/e/sishu/*、菜单键、守卫、skill_code）+批15 传输层注入豁免类（§一之二 C3）。

### 2.4 执法面（横切面，R3 doctrine 落地）

- 新 sishu_* 路由族全量 `require_expert(use/manage)`（映射表批0.2 机械推导；admin 一票；判定单点=既有 `app/services/expert_auth.py`——零新造）；④/平台既有端点执法现状登记不扩造。
- `?u=` 消费点统一走 `sishu_user_binding` 单点（批2 落位）；端点永不自由收 u=、永不收 user_id。
- 前端守卫管体验不管安全——数据面必须被后端执法点挡（批15 auth=1 负向探针组=终验）。

## 三、域清单与处置（前端消费面 grep 实测 2026-09-18，调用计数）

| 域 | 消费 | 处置 | 批 |
|---|---|---|---|
| mother-questions（76）+files 静态 | 高 | PG 换芯+迁移 | 6 |
| learning=learner-profile/mastery（29+1） | 高 | PG 换芯+迁移 | 6 |
| self-learning（20） | 高 | PG 换芯+迁移 | 6 |
| notebook（17）+question-notebook（23） | 高 | PG 换芯（chat_history.db notebook 三表并入迁移） | 6 |
| recitation/practice_gen（随 self-learning） | 中 | PG 换芯+迁移 | 6 |
| book（6）+书静态资产 | 中 | PG 换芯+book_bk_* 全量迁移 | 7 |
| sessions（17）+chat REST（2） | 高 | PG 会话族+1.2GB 迁移；chat WS 终卸 | 8 |
| curriculum（31）+grade3/7 静态（4） | 高 | PG 换芯+2.3GB 迁移 | 9 |
| knowledge（58，含④既有承接） | 高 | 归④（检索已④/进度通道切平台④） | 10 |
| settings（26）+skills（12）+subagents（10）+personas（10）+tools（3）+system（2） | 高 | 平台配置表换芯+llm-options 切③ | 11 |
| voice（11） | 中 | 运行时最小件（③ provider 直连；深度语音 degraded 登记） | 11 |
| memory（32） | 高 | 平台 memory 扩展+数据迁移 | 12 |
| partners（24）+WS | 中 | 平台化（deepagents 装配+PG；WS 路径形状保留） | 13 |
| h5-links/settings（12）/imports（3）/attachments（8） | 低 | 平台化+迁移 | 14 |
| co_writer（4） | 低 | 批内核实：实消费→最小换芯；零→登记 | 14 |
| wechat_push/multi_user/space_mcp/space_cli_apps/plugins/agent-config/capabilities/dashboard | **零** | 卸挂+登记舍弃（批0 机械冻结为准） | 14 |

## 四、PG 表族蓝图（DDL 要点）

统一前缀 `sishu_`；既有 `learning_*` 四表（learning_dao/pg.py L32-60 ensure）随批2 改名迁移（learning_dao SQL 同批改写，单源不双轨）。

| 族 | 表 |
|---|---|
| 学习 | sishu_mother_questions / sishu_wrong_questions / sishu_review_cards / sishu_review_records（=learning_* 四表迁移）+ sishu_recitation / sishu_practice_gen / sishu_learner_profile / sishu_self_learning_progress |
| 笔记 | sishu_notebook_entries / sishu_notebook_categories / sishu_notebook_entry_categories（chat_history.db notebook 三表迁移） |
| 书 | sishu_books（manifest）/ sishu_book_spines / sishu_book_pages / sishu_book_blocks（15 块型 JSON）/ sishu_book_assets / sishu_book_logs / sishu_book_progress——book_bk_* 目录结构 1:1（manifest.json/spine.json/pages/progress.json/log.md/assets/inputs.json 实测） |
| 会话 | sishu_sessions / sishu_turns / sishu_turn_events / sishu_messages（chat_history.db 四表迁移，1.2GB） |
| 课程 | sishu_textbooks / sishu_chapters / sishu_knowledge_points / sishu_curriculum_assets（curriculum 744MB+grade3 533MB+grade7 129MB=grade/页面资产 bytea） |
| 伙伴 | sishu_partners / sishu_partner_sessions |
| 分享 | sishu_h5_links |
| 记忆域数据 | sishu_memory_*（vendor memory store 迁移；平台三层记忆槽 MD 不动） |
| 迁移基建 | sishu_migration_cursor（游标+幂等） |
| 通用资产 | sishu_assets（bytea，域列+用途列：母题图片/书资产/课程页共用） |

配置面表（settings/capabilities 等）落**平台主库**（③先例），不入 PG——与「项目域实体业务数据归 PG」的既有分工一致。

热路径索引随批2 DDL 同落（sessions(user,updated_at)/messages(session_id,seq)/turn_events(turn_id)/book_pages(book_id)/book_blocks(page_id)/notebook_entries(user)——1.2GB/2.3GB 数据量无索引=切换日拖垮 h5 历史抽屉与教材阅读）；资产迁移带 sha256 内容级双账（协议 E v2，见 plans/）。

## 五、验收矩阵（五面硬门）

| 轨 | 门 | 适用批 |
|---|---|---|
| L2 契约重放 | ⑤R 复-0 endpoints 基线样本重放 diff（时间戳/ID 白名单豁免同 ⑤R） | 6-14 每域批 |
| L4/L5 UI 不变 | 前端零改断言（豁免类=批1 改名件+批15 传输层注入）+逐屏对拍回归 | 6-14 抽屏+17 全量 |
| L6 行为规格 | 8 技能 behavior-specs 终跑；判分黑盒基线对拍（批0 先录，数值容差±5 登记） | 3-5/17 |
| L7' vendor 清零 | ①backend grep deeptutor 导入=0；②app/vendor/ 目录不存在；③老 WS 404 抽样组；④前端 new WebSocket 白名单复核 | 16/17 |
| L8 执法面 | ①新 sishu_*.py 路由 require_expert 全覆盖（裸挂 grep=0，`v4_acl_map.json` 驱动）；②批15 auth=1 负向探针组（无 token→401／student 打管理端点→403／student2 读他人 u=→403）+三态+深链+JWT 冒烟；③auth=0 常态回归零感知 | 6-14 各域+15 全组 |
| L1 能力账 | 复刻/平台化/舍弃三分类（零消费域舍弃显式登记）+R3 五发终账 | 17 |
| 基线四件套 | pytest 不劣化（批0 存照）/WBS e2e/manifest diff/wenshu 零感知 | 每批 |

## 六、批结构总览（18 批，详见 plans/ 同名计划）

批0 基线与施工面冻结（含 M 类分诊） → 批1 全局改名 tutor→sishu → 批2 PG DDL+执法基建（?u= 绑定单点） → 批3-5 引擎合一三批（quiz+research／visualize／book-generate）→ 批6-9 数据域换芯四批（学习／书库／会话 1.2GB／课程 2.3GB）→ 批10-14 归④/配置/记忆/伙伴/小域五批 → 批15 执法面收口（Bearer 注入+auth=1 探针组，R3 C3/C5）→ 批16 vendor 树终清（物理删除+L7'）→ 批17 终验收+关账（吸收 v3 批9+R3 终账，含 E-33/E-34 修复）。

## 七、风险与诚实账

1. **改名回归面大**（裁定③）：ExpertProfile 行/ACL grant 行/菜单键/路由/会话 expertId/memory 路径/skill_code 全链——独立成批1+全链 e2e+旧路由 redirect 兜底。
2. **全量迁移容量**：PG +4GB；迁移脚本族幂等+断点续传（游标表）+行数/资产哈希双账（源=目标，差异如实登记）+**切换窗口 delta**（每数据域路由切换后追加一次增量迁移，防切换窗口 vendor 侧活写丢失——1.2GB 会话库风险实在）。
3. **中间态登记**：批5 书生成已写 PG 而书库读面批7 才切换（批5 验证 PG 产物 L6，工作台 e2e 归批7）。
4. **partners 运行时**：复刻件 WS 路径形状保留（平台实现同路径），agent 语义=平台装配。
5. **voice 运行时**：③无既有 TTS/STT 面——最小件=③ provider 配置直连，深度语音功能如实 degraded 登记。
6. **判分重写**：黑盒基线先行录制（批0），容差±5+理由语义等价。
7. **E-33/E-34**（v3 遗留缺陷）随批17 修复；ExpertChat 死代码（/api/tutor/profile 残留调用）批17 清理。
8. **28000 双窗口争用先例**（E-35）：每批开工前核唯一进程。
9. **批15 auth=1 窗口纪律**：临时翻转只跑探针组（负向×3+三态+深链+JWT 冒烟），跑完即回 0 并复跑全量四件套——B-4 先例；auth=0 为常驻回归基准。
10. **批0 基线污染**：工作区 M 类未提交改动（真实代码 2 件+24 ES JSON 等）必须批0.0 分诊后再存照——脏树上存照=基线口径失真。

## 八、不在本件

- **33066 主库主数据迁移**（kg_entities 45 行/dim_* 全缺——R3 C5 定案遗留，数据智能域另案；连带 R3 I4 perm_verify 33066 拓扑耦合随案处置）；
- 既有远期池（⑥-1 人格卡模板 v2／⑥-2 专家工厂向导／⑥-3 cron 投递器）与本件无涉；
- 除上述外无：裁定②为全 vendor 树清零，本件收尾后 vendor 域全部退役，后续仅剩平台自身演进。
