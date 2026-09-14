# ⑤教学引擎 批 0 前置验证存照（2026-09-15）

## 0.1 硬前置复验
- ①专家地基：全部批勾选（commit 链至 998da09）；②记忆插槽：八批完成（goal-ade9fc70 blocked=LLM 402 补验遗留，主体已验收）；④文档知识库：批 0-5 全绿（4fa170e…4dce92d）。
- ④A5 实录（批 4 台账引证）：knowledge_sources 声明不存在 KB→422「声明的知识库不存在: kb:nonexistent-0000」；声明存在 KB→200；wenshu 原值回写 200。

## 0.2 PG 驱动验证（spec Runbook 步骤 0）
- psycopg2 2.9.12 (dt dec pq3 ext lo64)——现役依赖，免 psycopg2-binary。
- `SELECT 1 → 1` @ postgresql://localhost:25432/tupu（pg_tupu；密码源 .env.infra）。
- pg_tupu 现有表：123 张 dim/dwd 业务镜像表（无 learning_* 冲突——四表 CREATE IF NOT EXISTS 干净落地）。

## 0.3 图谱锚点实测（Neo4j 7687）
- 节点主键属性：**entity_id**（辅 entity_en_name/code/name；labels=['Category','Entity']）。
- 相邻关系类型：BELONGS_TO_CHAIN ×576 / HAS_PARENT ×552 / RELATES_TO ×175。
- ⑤b select_exercises 邻居扩展查询依据：`MATCH (n {entity_id: $id})-[r:RELATES_TO|HAS_PARENT]-(m)`。

## 0.4 EXPERT_PAGES 分支
- frontend/src/routes.tsx **未建** EXPERT_PAGES（①批 5 未落该件）→ **分支：⑤批 4 创建**（①spec L137 语义：`{slug: [自定义页]}` 静态注册表）。

## 0.5 基准
- pytest 基线：1086 passed（④批 3 收口）。
- manifest 基线：_diag_assembly_baseline5.json（wenshu 暖机快照）。
- DeepTutor 源：D:\gitcangku\xiaobaohaohao\DeepTutor（计划笔误 xiaobaohao——实际目录 xiaobaohaohao，已实测）。
- 四件算法源亲证：fsrs.py 5953B（头注亲证 "pure Python, no external deps"·ragflow 血统）/grading.py 1982B/exercise_selector.py 7892B/mastery.py 1552B。
- 26 测试源清单（learning/tests/，迁移候选）：test_e1_selector.py / test_e3_dedup.py / test_exercise_selector.py / test_grading.py / test_guided_mastery_updates.py / test_mastery_capability.py / test_mastery_choices.py / test_models.py / test_scheduler.py / test_storage.py（具体 26 条断言批 1 逐文件挑选，语义零改）。
