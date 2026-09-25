---
name: 练习与判分
description: 教学场景契约：选题→作答→判分→错题登记/查询/错因分析/导出（学习闭环核心）。写前确认：错题登记、评分调度走两段臂确认流。
---

# 练习与判分（tutor/practice）

## 何时使用
- 用户要练习题、做题、判分、登记错题、分析错因、导出错题本时触发。

## 可用工具（专家卡 sishu ∩ 用户权限 ∩ 本技能 allowed_tools 三交集后的最终面）
select_exercises / generate_practice / grade_answer / wrong_question_add /
wrong_question_query / analyze_wrong_questions / export_wrong_book /
mother_question_find_or_create

## 执行步骤
1. 选题：`select_exercises`（按知识点与难度档）或 `generate_practice`（生成练习）。
2. 判分：`grade_answer`（用户作答后逐题判分，给出对错与依据）。
3. 错题登记：判错的题 → `wrong_question_add`。
   ⚠ 两段臂：首次调用返回 pending_confirmation + confirm_token；
   用户在确认卡上确认后，携 confirm_token 原参数重调才落库。
4. 错题查询/错因：`wrong_question_query`、`analyze_wrong_questions`。
5. 导出：`export_wrong_book`（两段臂，同步骤 3）。
6. 需要把好题固化进母题库时用 `mother_question_find_or_create`（两段臂）。

## 纪律
- 禁止编造题库内容；一切题目以工具返回为准。
- 写操作（登记/导出/建母题）必须等用户确认后才携 token 执行。
