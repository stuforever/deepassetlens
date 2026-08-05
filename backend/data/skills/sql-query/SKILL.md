---
name: sql-query
description: SQL数据查询场景。用户要查数据：数量/统计/占比/排名/趋势/对比/质检/具体字段/跨实体关联。包含聚合、排名、趋势、对比、质检5类SQL写法提示，由LLM根据问句自主判定走哪类。用户已给表名也走此技能。
---

# sql-query SQL数据查询

## 何时使用
用户要查数据，包括：数量/统计/占比/平均/分组、排名/前N/最大最少、同比/环比/趋势/增长率、对比/相比/哪个多哪个少、空值/重复/异常/质检、查具体字段值、跨实体关联穿透。用户已明确给表名和字段名也走此技能。

## 可能用到的能力包
- **locate**：定位实体和字段（用户没给表名时）
- **relate**：查 JOIN 字段（跨实体时）
- **execute_api_sql**：多源API联邦SQL取数（数据源为 api_integration 时）
- **sql-exec**：校验并执行 SQL
- **explore**：兜底搜字段（字段不存在时）

## 调用模式（LLM 自主判定走哪种，可组合）
- **基础查询**：locate -> 拼 SELECT -> sql-exec
- **用户给表名（直查）**：跳过 locate，explore(转表名) -> 拼 SQL -> sql-exec
- **跨实体（多跳）**：locate -> relate(查JOIN) -> 拼 LEFT JOIN -> sql-exec
- **API数据源**：locate -> execute_api_sql(联邦SQL) -> 取数
- 已定位同一 L2+实体：跳过 locate，直接拼 SQL

## SQL 写法参考（LLM 根据问句自主判定走哪类）

### 聚合类（问数量/统计/占比/平均/分组）
| 用户说法 | SQL |
|---------|-----|
| "多少条/多少个/数量/总数" | `COUNT(*)` |
| "各...有多少/按...分组统计" | `COUNT(*) GROUP BY <分组字段>` |
| "占比/比例/百分比" | `SUM(CASE WHEN <条件> THEN 1 ELSE 0 END)*100/COUNT(*)`，加 `ROUND(x,2)` |
| "平均/均值/平均值" | `AVG(<数值字段>)` |
| "总和/总计" | `SUM(<数值字段>)` |
| "最大值/最小值" | `MAX(<字段>)` / `MIN(<字段>)` |
| "有多少个不同的/去重计数" | `COUNT(DISTINCT <字段>)` |
| "分布" | `COUNT(*) GROUP BY <字段>` |

拼装规则：分组字段用中文别名（`SELECT ec_categ_name AS 用电类别, COUNT(*) AS 数量`）

### 排名类（问排名/前N/最大/最多/最少）
排序方向：最大/最多/最高/排名前/Top -> `ORDER BY <字段> DESC`；最小/最少/最低/最后 -> `ORDER BY <字段> ASC`
N值：前10/top10/10个 -> LIMIT 10；没说 -> 默认 LIMIT 10
排序字段："用能面积最大"->用能面积；"客户数量最多"->COUNT(*)（需GROUP BY）；"最近登记"->登记日期

简单 TopN：`SELECT <展示字段>, <排序字段> FROM <表> ORDER BY <排序字段> DESC LIMIT <N>`
分组 TopN：`SELECT <分组字段>, COUNT(*) AS 数量 FROM <表> GROUP BY <分组字段> ORDER BY 数量 DESC LIMIT <N>`

### 趋势类（问同比/环比/趋势/逐月/增长率）
| 用户说法 | SQL 模板 |
|---------|---------|
| "逐月/按月统计" | `SELECT DATE_FORMAT(<日期字段>, '%Y-%m') AS 月份, COUNT(*)/SUM(<指标>) AS 数值 FROM <表> GROUP BY 月份 ORDER BY 月份` |
| "逐季/按季统计" | `SELECT CONCAT(YEAR(<日期字段>),'-Q',QUARTER(<日期字段>)) AS 季度, COUNT(*) AS 数量 FROM <表> GROUP BY 季度 ORDER BY 季度` |
| "同比" | `SELECT YEAR(<日期字段>) AS 年份, COUNT(*) AS 数量 FROM <表> WHERE YEAR(<日期字段>) IN (今年,去年) GROUP BY 年份 ORDER BY 年份` |
| "环比" | 本期 vs 上期，子查询：`SELECT m.月份, m.数量, (m.数量 - prev.数量) AS 环比增量 FROM (...) m LEFT JOIN (...) prev` |
| "增长率" | `(本期-上期)/上期*100`，用 LAG 窗口：`SELECT 月份, 数量, ROUND((数量 - LAG(数量) OVER(ORDER BY 月份)) / LAG(数量) OVER(ORDER BY 月份) * 100, 2) AS 增长率 FROM (...)` |

规则：日期字段优先用 validate_attributes 校验出的 code；没明确日期字段用 create_time；结果按时间正序；同比/环比年份未指定默认取当前年份和去年。

### 对比类（问对比/相比/哪个多哪个少）
| 用户说法 | 对比类型 | SQL 模板 |
|---------|---------|---------|
| "A vs B 对比" | 两类对比 | `SELECT <维度> AS 类别, SUM(<指标>) AS 用电量 FROM <表> WHERE <维度> IN ('A','B') GROUP BY 类别` |
| "各地市对比" | 分组对比 | `SELECT <维度> AS 地市, COUNT(*) AS 客户数 FROM <表> GROUP BY 地市 ORDER BY 客户数 DESC` |
| "并排展示" | 行转列对比 | `SELECT SUM(CASE WHEN <维度> LIKE '%A%' THEN <指标> ELSE 0 END) AS A值, SUM(CASE WHEN <维度> LIKE '%B%' THEN <指标> ELSE 0 END) AS B值 FROM <表>` |
| "今年去年对比" | 两期对比 | `SELECT YEAR(<日期>) AS 年份, COUNT(*) AS 数量 FROM <表> WHERE YEAR(<日期>) IN (今年,去年) GROUP BY 年份` |
| "哪个多哪个少" | 排序对比 | `SELECT <维度>, COUNT(*) AS 数量 FROM <表> GROUP BY <维度> ORDER BY 数量 DESC` |

规则：对比维度用中文别名；指标字段加聚合函数；"哪个多/少"加 ORDER BY；多组对比标注最大最小值。

### 质检类（问空值/重复/异常/完整性）
| 用户说法 | 检测类型 | SQL 模板 |
|---------|---------|---------|
| "空值/为空/缺失" | 空值检测 | `SELECT COUNT(*) FROM <表> WHERE <字段> IS NULL OR <字段> = ''` |
| "重复/重复的" | 重复检测 | `SELECT <字段>, COUNT(*) AS cnt FROM <表> GROUP BY <字段> HAVING cnt > 1` |
| "异常/超过/不合理" | 异常检测 | `SELECT * FROM <表> WHERE <字段> > <阈值>` |
| "空值率/缺失率" | 完整性率 | `SELECT ROUND(SUM(CASE WHEN <字段> IS NULL OR <字段>='' THEN 1 ELSE 0 END)*100/COUNT(*), 2) AS 空值率 FROM <表>` |
| "有没有问题/数据质量" | 综合检测 | 对主表关键字段分别跑空值检测，汇总报告 |

规则：用户没指定检测字段->对主键和前5个属性做综合空值检测；没给阈值但说"异常"->默认数值字段>99999或<0；重复检测字段不确定->默认主键。

## 通用规则（见系统提示 _COMMON_RULES）
- 字段加表名前缀（多表时）：`表名.字段名`
- 加 LIMIT 500（默认），全量可提 2000
- 只 SELECT/WITH，禁 DDL/DML
- 不编造字段，不确定先 validate_attributes
- SQL 只允许 SELECT/WITH，必须加 LIMIT

## 多跳 JOIN 拼装（跨实体时）
```
SELECT <展示字段>
FROM <起始表>
LEFT JOIN <第1跳表> ON <起始表>.<字段> = <第1跳表>.<字段>
LEFT JOIN <第2跳表> ON <第1跳表>.<字段> = <第2跳表>.<字段>
WHERE <筛选条件>
LIMIT 500
```
- 用 LEFT JOIN（避免内连接丢数据）
- 字段名一律加表名前缀
- JOIN 字段来自 relate 的 fetch_join_expr

## 输出（见系统提示 _SQL_FLOW_RULES 步骤9）
- summary：必须基于实际返回数据，引用具体数据值，指出数据特征，避免模板化
- execution_process：定位了哪个 L2、哪个实体、查了哪些字段
- sql：执行的 SQL（API 路径填联邦 SQL，引用虚拟表名）
- data_source：数据来源（SQL 路径为业务库名/Doris，API 路径为 ES虚拟表）
- row_count：返回行数
- recommendations：3-5 个后续问题
