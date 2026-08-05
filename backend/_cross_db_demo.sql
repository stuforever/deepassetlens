-- ============================================================
-- 跨库 UNION 模拟：项目成本数据 PG ∪ ES（Doris 联邦查询）
-- 数据来源：项目成本(dim_ps_wbs_cost)原始数据全在 ES(index=tupu_dim_ps_wbs_cost，10条)
-- 拆分方式：前5条(id 1-5) -> ES 新 index tupu_dim_ps_wbs_cost_half
--           后5条(id 6-10) -> PG 表 tupu.public.dim_ps_wbs_cost
-- 目标：Doris 跨 catalog UNION ALL 合并为一个 10 行的表
-- ============================================================

-- ---------- 1. Doris Catalog 创建 ----------

-- PG catalog(jdbc, 需 postgresql-42.7.3.jar 驱动)
-- 驱动放置：FE/BE 的 jdbc_drivers 目录 + FE/BE 的 lib 目录(classpath)
-- 驱动下载：https://repo1.maven.org/maven2/org/postgresql/postgresql/42.7.3/postgresql-42.7.3.jar
CREATE CATALOG pg_tupu PROPERTIES (
  "type"="jdbc",
  "user"="postgres",
  "password"="postgres",
  "jdbc_url"="jdbc:postgresql://host.docker.internal:5432/tupu",
  "driver_url"="postgresql-42.7.3.jar",
  "driver_class"="org.postgresql.Driver"
);

-- ES catalog(原生 type=es)
CREATE CATALOG es_tupu PROPERTIES (
  "type"="es",
  "hosts"="http://host.docker.internal:1200",
  "user"="elastic",
  "password"="infini_rag_flow"
);

-- ---------- 2. 跨库 UNION SQL ----------
-- 在 internal catalog 下用全限定名 catalog.db.table 跨库查询
-- PG: pg_tupu.public.dim_ps_wbs_cost      (PG schema 'public' 映射为 Doris database)
-- ES: es_tupu.default_db.tupu_dim_ps_wbs_cost_half  (ES index 映射到 default_db 下)
SELECT 'PG库' AS 数据来源, id, cost_id, wbs_element, fiscal_year, cost_element,
       actual_cost, committed_cost, planned_cost, variance, currency, posting_date
  FROM pg_tupu.public.dim_ps_wbs_cost
  UNION ALL
SELECT 'ES库' AS 数据来源, id, cost_id, wbs_element, fiscal_year, cost_element,
       actual_cost, committed_cost, planned_cost, variance, currency, posting_date
  FROM es_tupu.default_db.tupu_dim_ps_wbs_cost_half
  ORDER BY id;
-- 结果：10 行(PG 5 + ES 5)，按 id 排序

-- ---------- 3. 在 tupu SqlIntegrationTab 配置 ----------
-- 实体 dim_ps_wbs_cost 的 integration_sql 填上面的 UNION SQL
-- Doris catalog 下拉选「不指定」(SQL 内用全限定名，无需 SWITCH)
-- 或选 pg_tupu/es_tupu(但 UNION 跨库必须用全限定名，建议不指定)
