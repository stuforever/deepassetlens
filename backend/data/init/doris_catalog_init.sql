-- Doris 外部 Catalog 初始化脚本
-- 将 Elasticsearch (es_tupu) 与 PostgreSQL (pg_tupu) 接入 Doris，用于跨源联邦查询。
--
-- 使用方式：
--   mysql -h <doris_fe_host> -P 9030 -u root < doris_catalog_init.sql
--
-- 注意事项：
--   1. 按实际环境修改密码与 host。
--   2. Doris 运行在容器内，访问宿主机服务用 host.docker.internal
--      （Linux 需在 docker-compose 中加 --add-host=host.docker.internal:host-gateway）。
--   3. pg_tupu 的 driver_url 指向的 postgresql jar 需可被 Doris BE 访问：
--      可放至 Doris 的 jdbc_drivers 目录，或挂载后用 file:// 路径。

-- Elasticsearch catalog（项目域 12 个索引）
DROP CATALOG IF EXISTS es_tupu;
CREATE CATALOG es_tupu PROPERTIES (
  "type"     = "es",
  "user"     = "elastic",
  "password" = "<your_es_password>",
  "hosts"    = "http://host.docker.internal:11200"
);

-- PostgreSQL catalog（项目域 dim_ps_wbs_cost 等物理表）
DROP CATALOG IF EXISTS pg_tupu;
CREATE CATALOG pg_tupu PROPERTIES (
  "type"         = "jdbc",
  "user"         = "postgres",
  "password"     = "<your_pg_password>",
  "jdbc_url"     = "jdbc:postgresql://host.docker.internal:5432/tupu?reWriteBatchedInserts=true",
  "driver_url"   = "postgresql-42.7.3.jar",
  "driver_class" = "org.postgresql.Driver"
);
