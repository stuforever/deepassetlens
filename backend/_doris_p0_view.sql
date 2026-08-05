-- 在 Doris FE 执行：创建 WBS 成本视图（跨源读 MySQL 外部表）
SWITCH internal;
USE test_db;

DROP VIEW IF EXISTS v_wbs_cost_summary;

CREATE VIEW v_wbs_cost_summary AS
SELECT
    wbs_element,
    fiscal_year,
    currency,
    COUNT(*) AS cost_record_count,
    SUM(actual_cost) AS total_actual_cost,
    SUM(planned_cost) AS total_planned_cost,
    SUM(variance) AS total_variance,
    COUNT(DISTINCT cost_element) AS cost_element_count
FROM mysql_tupu.tupu.biz_wbs_cost_src
GROUP BY wbs_element, fiscal_year, currency;

-- 验证视图
SHOW VIEWS FROM test_db;
SELECT * FROM v_wbs_cost_summary ORDER BY total_actual_cost DESC;
