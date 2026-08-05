# tupu 40 题完整测试报告

- 测试时间: 2026-07-29 13:55:39
- 端点: `/api/data-intelligence/chat/freeplan/stream`
- 通过: **33/40** (82.5%)
- 总耗时: 1816.0s  平均: 45.4s

## 详细结果

| ID | 类别 | 问题 | 耗时(s) | 状态 | 行数 | 答案长度 | 摘要 |
|----|------|------|---------|------|------|----------|------|
| T01 | basic-query | 查询用电客户信息 | 52.6 | PASS | 3 | 168 | 行=3 |
| T02 | aggregate-query | 统计用电客户总数 | 34.9 | PASS | 1 | 50 | 行=1 |
| T03 | topn-query | 用电量最大的前10个客户 | 61.6 | PASS | 3 | 127 | 行=3 |
| T04 | direct-query | 查询 dim_customer 表的数据 | 23.9 | PASS | 0 | 658 | 答案长度=658 |
| T05 | multi-hop-query | 名称、联系电话、证件号码 | 67.4 | PASS | 3 | 150 | 行=3 |
| T06 | explain-concept | 什么是变压器 | 23.1 | PASS | 0 | 1008 | 答案长度=1008 |
| T07 | explore-graph | 用电客户有哪些属性 | 36.7 | PASS | 0 | 2947 | 答案长度=2947 |
| T08 | find-entity | 联系电话字段在哪个表 | 20.4 | PASS | 0 | 1211 | 答案长度=1211 |
| T09 | data-quality | 用电客户表的空值情况 | 71.4 | PASS | 1 | 188 | 行=1 |
| T10 | trace-lineage | 用电客户数据的来源 | 35.3 | PASS | 0 | 2098 | 答案长度=2098 |
| Q01 | ProjectDefinition 单表全量 | 查询所有项目定义信息 | 47.7 | PASS | 2 | 216 | 行=2 |
| Q02 | WbsElement 单表全量 | 查询所有WBS元素信息 | 53.0 | PASS | 7 | 222 | 行=7 |
| Q03 | Network 单表全量 | 查询所有网络信息 | 48.1 | PASS | 3 | 176 | 行=3 |
| Q04 | NetworkActivity 单表全量 | 查询所有网络活动信息 | 48.4 | PASS | 4 | 215 | 行=4 |
| Q05 | Milestone 单表全量 | 查询所有里程碑信息 | 53.6 | PASS | 11 | 221 | 行=11 |
| Q06 | ProjectBudget 单表全量 | 查询所有WBS预算信息 | 59.7 | PASS | 7 | 261 | 行=7 |
| Q07 | ProjectCost 单表全量 | 查询所有WBS成本信息 | 59.5 | PASS | 7 | 236 | 行=7 |
| Q08 | NetworkComponent 单表全量 | 查询所有网络组件信息 | 49.2 | PASS | 4 | 1268 | 行=4 |
| Q09 | PsStatus 单表全量 | 查询所有业务对象状态信息 | 58.0 | PASS | 16 | 218 | 行=16 |
| Q10 | ProjectDefinition 条件查询 | 查询项目编号为P-2024-001的项目定义信息 | 57.2 | PASS | 1 | 159 | 行=1 |
| Q11 | WbsElement+Budget+Cost 1:1:1 | 查询WBS元素W-001-2的预算和成本 | 67.3 | PASS | 1 | 130 | 行=1 |
| Q12 | PD→WBS 1:N | 查询项目P-2024-001下的所有WBS元素 | 58.0 | PASS | 4 | 271 | 行=4 |
| Q13 | NW→NA 1:N | 查询网络N-001下的所有网络活动 | 54.3 | PASS | 2 | 163 | 行=2 |
| Q14 | NA→NC 1:N | 查询网络活动A-001下的所有网络组件 | 55.6 | PASS | 1 | 112 | 行=1 |
| Q15 | WBS→MS 1:N | 查询WBS元素W-001下的所有里程碑 | 54.5 | PASS | 1 | 138 | 行=1 |
| Q16 | NA→MS 1:N | 查询网络活动A-001下的所有里程碑 | 54.1 | PASS | 1 | 115 | 行=1 |
| Q17 | WBS→WBS 自循环 1:N | 查询WBS元素W-001下的所有下级WBS | 72.5 | PASS | 3 | 178 | 行=3 |
| Q18 | PD→PS 1:1 | 查询项目P-2024-001的状态信息 | 97.9 | PASS | 16 | 187 | 行=16 |
| Q19 | PD→WBS→PB 三表关联 | 查询项目P-2024-001下的所有WBS元素及其预算金额 | 77.5 | PASS | 4 | 1512 | 行=4 |
| Q20 | PD→WBS 聚合 | 查询所有项目的WBS数量统计 | 48.3 | PASS | 2 | 108 | 行=2 |
| Q21 | aggregate-query 分组统计 | 统计每个项目下有多少个WBS元素 | 44.3 | PASS | 2 | 122 | 行=2 |
| Q22 | aggregate-query SUM聚合 | 统计所有WBS的预算总金额 | 45.9 | PASS | 1 | 94 | 行=1 |
| Q23 | topn-query 排序取前N | 查询预算金额最高的前3个WBS元素 | 78.9 | PASS | 3 | 196 | 行=3 |
| Q24 | topn-query 成本排序 | 查询实际成本最高的前3个WBS元素 | 30.3 | FAIL | 0 | 95 | error: Error code: 429 - {'error': {'message': 'Your token-plan 1-week quota has been exhausted. The quota will reset at 08-01  |
| Q25 | explain-concept 概念解释 | 什么是WBS元素 | 2.6 | FAIL | 0 | 0 | error: Error code: 429 - {'error': {'message': 'Your token-plan 1-week quota has been exhausted. The quota will reset at 08-01  |
| Q26 | explore-graph 浏览结构 | 项目域有哪些实体 | 2.5 | FAIL | 0 | 0 | error: Error code: 429 - {'error': {'message': 'Your token-plan 1-week quota has been exhausted. The quota will reset at 08-01  |
| Q27 | find-entity 反查字段 | 预算金额字段在哪个表 | 2.4 | FAIL | 0 | 0 | error: Error code: 429 - {'error': {'message': 'Your token-plan 1-week quota has been exhausted. The quota will reset at 08-01  |
| Q28 | data-quality 空值检测 | 检查项目定义表有哪些字段是空值 | 2.2 | FAIL | 0 | 0 | error: Error code: 429 - {'error': {'message': 'Your token-plan 1-week quota has been exhausted. The quota will reset at 08-01  |
| Q29 | multi-hop-query 预算成本对比 | 查询每个WBS元素的预算和实际成本对比 | 2.5 | FAIL | 0 | 0 | error: Error code: 429 - {'error': {'message': 'Your token-plan 1-week quota has been exhausted. The quota will reset at 08-01  |
| Q30 | compare-query 两项目对比 | 对比P-2024-001和P-2024-002两个项目的WBS数量和预算总额 | 2.7 | FAIL | 0 | 0 | error: Error code: 429 - {'error': {'message': 'Your token-plan 1-week quota has been exhausted. The quota will reset at 08-01  |
