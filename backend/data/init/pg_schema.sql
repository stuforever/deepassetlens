-- PostgreSQL 演示业务表结构。
-- pg_init_data.sql 仅保留数据，因此全新部署时必须先执行本文件。
CREATE TABLE IF NOT EXISTS public.dim_ps_wbs_cost (
    id INTEGER PRIMARY KEY,
    cost_id VARCHAR(50) NOT NULL,
    wbs_element VARCHAR(50) NOT NULL,
    fiscal_year VARCHAR(10) NOT NULL,
    cost_element VARCHAR(50) NOT NULL,
    actual_cost NUMERIC(18, 2),
    committed_cost NUMERIC(18, 2),
    planned_cost NUMERIC(18, 2),
    variance NUMERIC(18, 2),
    currency VARCHAR(10),
    posting_date DATE
);
