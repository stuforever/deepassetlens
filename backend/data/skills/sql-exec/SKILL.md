---
name: sql-exec
description: SQL执行能力包。校验并执行SQL，含表名校验兜底。何时用：拼好SQL后校验执行、或执行报错需要排查表名时。
---

# sql-exec SQL执行能力包

## 用途
校验并执行 SQL，含表名存在性校验兜底。

## 工具清单（按需挑用）
- **validate_safe_sql**：SQL 安全校验（白/黑名单）。参数 `{"sql":"SELECT ..."}`。返回 safe + reason。
- **execute_sql**：执行 SELECT 取数。参数 `{"sql":"SELECT ..."}`。返回 columns/rows/row_count，或 error。
- **list_tables**：列出物理表名/验表存在。参数 `{}` 或 `{"keyword":"关键词"}`。

## 依赖关系
- execute_sql 逻辑上需 validate_safe_sql 先过（prompt 软约束）
- list_tables 是 execute_sql 报"表不存在"时的兜底

## 硬约束
- **必须先 validate_safe_sql 通过才能 execute_sql**
- SQL 只允许 SELECT/WITH，必须加 LIMIT（默认500，全量可2000）
- execute_sql 报错重试不超过 1 次，仍失败如实报告
- SQL 含 `{{` 未解析占位符或为空：拒绝执行
- 字段名一律加表名前缀（多表时）：`表名.字段名`

## 挑用示例
- 正常流程 -> validate_safe_sql -> execute_sql
- 表不存在 -> list_tables 查正确表名
- Unknown column -> 回 locate 的 validate_attributes 或 explore 查正确列名
- execute_sql 内置容错：Unknown column 会自动改 COUNT(*) 或删列，多次失败 fallback SELECT * FROM 表 LIMIT
