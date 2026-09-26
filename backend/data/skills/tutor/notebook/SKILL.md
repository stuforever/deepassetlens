---
name: 学习笔记本
description: 教学场景契约：笔记索引→记录检索→笔记写入（append/edit）。write_note 走两段臂确认流。摘要口径：主题/关键结论/适用场景/保存价值，80-180 字。
---

# 学习笔记本（tutor/notebook）

## 何时使用
- 用户要求保存对话内容、总结知识点到笔记本时触发。
- 用户询问历史笔记内容、检索以往记录时触发。

## 可用工具（三交集后的最终面）
has_notebooks / list_notebook / write_note

## 执行步骤
1. 前查：`has_notebooks`——无笔记本时如实告知用户先建笔记本，**禁止臆造 notebook_id**。
2. 检索：`list_notebook`（空 id=索引模式取全部笔记本概览；带 id=该本记录新→旧清单）。
   notebook_id 必须来自索引输出；未知 id 报错会列出有效 id。
3. 写入：`write_note`（mode=append 新增 | edit 改 record_id）。
   ⚠ 两段臂：首次调用返回 pending_confirmation + confirm_token；
   向用户确认内容后携 confirm_token 原参数重调才生效。

## 摘要纪律（vendor notebook summary agent 逐字保留）
保存记录时把内容提炼成简洁、可检索、面向未来复用的摘要：
- 突出主题、关键结论、适用场景和保存价值；
- 内容是草稿或中间过程时，说明当前完成度；
- 80-180 字中文，不加标题、前缀或项目符号。

## 选取纪律（vendor notebook analysis agent 逐字保留）
回答依赖历史笔记时，优先选择最能支撑当前问题的记录（最多 5 条），避免冗余；
只需摘要即可支撑的记录不展开原文细节。
