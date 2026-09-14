# 账本：明细列表表头中英双显（2026-09-12）

## 简报
- **用户需求**：「输出的明细列表，抬头是英文字母，请核实并解决下，或者抬头双显示，中文一行、英文一行哈」——按 executing-plans 技能执行（特性面小，单会话直执行，未走 subagent-driven-development）。
- **核实结论**（执行前取证）：前端 SqlResultTable 表头=图标+技术列名（`columns: string[]` 无中文字段）；中文属性名在 kg_entities.properties_schema.cnName（`_entity_attrs` L308 既有解析纯函数）；载荷出口三处字段白名单（endpoint.py 实时帧/delivery.py done 帧/endpoint.py 降级帧）；金标查询表头本为中文（SQL 别名），裸列查询才是英文——问题面=裸列名无中文映射。
- **方案**：执行侧挂载 columns_cn（handler 知道 entity_code）+载荷透传+前端双行渲染；无映射回退单行现状；美化件失败降级空串不阻断主链。**mcp_server 零改动**。

## 任务执行（3 任务 3 commit）
- [x] 任务 1（67e9a7a）：`_build_columns_cn` helper+四执行口接线+载荷三出口透传；TDD 4 测（映射/降级/接线/透传）先红后绿。
- [x] 任务 2（cfd2630）：SqlResultTable 双行渲染（中文主行 600+英文次行 11px）；TDD 2 测先红后绿；jest 7 套件 56 测全绿（54+2）；tsc 基线=当前（既有 @types/jest 缺失非本批引入）。
- [x] 任务 3（终验 commit）：e2e 实证+金标回归+主文档登记行+本账本。

## 验证记录
- pytest 全量：**1044 passed / 6 deselected / 214 warnings**（基线 1040+4，`--ignore=tests/test_cov_db_crud.py -o timeout=600` 口径，388s）。
- e2e 双显实证：「查询台区台账前5条明细数据」→ 表头 7 列双显（配送站标识/dist_sta_id、配送站编码/resrc_supl_code…），5 行×20 列渲染正常，截图 `_pw_表头双显tztz.png`。
- e2e 金标回归：「统计重过载台区数量」→ 别名中文列单行现状（重过载台区数 16/过载 7/重载 9/判定总数 42），1 步直通命中金标，截图 `_pw_表头双显金标回归.png`。
- 计划文档勾选：docs/superpowers/plans/2026-09-12-明细表头中英双显.md 全 13 步 [x]。

## 藏账登记（如实）
1. **跨表 JOIN 他表列回退英文单行**：v1 只映射主实体（无 entity_code 时全实体并集）；多实体 JOIN 的他表裸列映射不到→前端回退单行英文（不空洞、可追溯）。
2. **endpoint.py DeepSeek 直答降级帧不接**：无实体上下文，columns_cn 缺省→前端回退单行（该路径本就罕见）。
3. **全实体并集同名列歧义**：execute_api_sql/doris inline 无 entity_code 时并集映射，同列名多实体中文名可能不同→取先到（先到者字典序由查询返回序决定）。
4. **测试侧导入规避**：test_sql_columns_cn.py 经 importlib 直载 delivery.py 绕过 app.api.freeplan 包 __init__——规避 Python 3.13+pydantic v2 导入期 copy 递归悬挂（2026-09-14 实测：delivery 单独经包链导入=单跑侥幸过/组合挂；faulthandler 取证悬挂于 _union_schema→copy(annotation)；**与本批代码无关**，属环境性 flake 规避，包链导入在既有 1040 基线中均正常）。
5. **pytest.ini 30s timeout 与当日环境态冲突**：2026-09-14 机器重启后（AV 实时扫描+异项目 init_grade3.py 磁盘负载）首次导入 langchain/deepagents 数百模块被节流至 ~1s/文件，collection 阶段超 30s 被 pytest-timeout 误杀（marker「+++ Timeout +++」+importlib get_data 栈）——当日全量门禁用 `-o timeout=600` 抬高（CLI 非侵入，pytest.ini 未动）；环境恢复后应回归默认口径。
6. **后端无 reload**：__start_8000.py 无 reload 参数，改码后须重启进程（本批重启验证；旧进程 9/13 起 = 无本批代码）。
7. **WBS 题卡 15 轮**：e2e 首跑 WBS 题 150s 内推理至第 15 轮未完成——红灯修复批已知方差形态（跨库 FeatureNotSupported 根因未修，等待用户下令修复批），与本批无关；表头验证改用稳定裸列题（台区台账）完成。
8. **工作区不处置项维持**：根目录游离文件 `b1`、12 个 tracked ES mapping JSON 运行态修改未混入本批 commit。

## 红线核对
- 端口铁律 ✓（后端 28000 单进程；前端 23000 未动）；前端无硬编码后端端口 ✓（载荷字段透传，无新 API 调用）；MCP 层零改动 ✓；Playwright headless 串行 e2e ✓（一次一题）；pytest 只升不降 ✓（1040→1044）。
