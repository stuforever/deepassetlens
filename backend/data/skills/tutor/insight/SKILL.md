---
name: 学情与复习
description: 教学场景契约：掌握度画像/薄弱点报告 → 今日复习清单 → 评分调度（写前确认）。fsrs_review 走两段臂确认流。
---

# 学情与复习（tutor/insight）

## 何时使用
- 用户问掌握度、薄弱点、今日该复习什么时触发。

## 可用工具（三交集后的最终面）
mastery_query / fsrs_due / fsrs_review / analyze_wrong_questions

## 执行步骤
1. 画像：`mastery_query`（按知识点掌握度）+ `analyze_wrong_questions`（错因聚类）。
2. 今日清单：`fsrs_due`（到期复习项）。
3. 评分调度：用户对某题自评后 → `fsrs_review` 提交评分调度下次复习时间。
   ⚠ 两段臂：首次调用返回 pending_confirmation + confirm_token；
   用户确认评分后携 confirm_token 原参数重调才生效。

## 纪律
- 掌握度结论必须来自 mastery_query 返回，禁止猜测。
- fsrs_review 必须与用户确认评分（1-4 档）后再携 token 执行。
