-- PostgreSQL 演示业务表结构。
-- pg_init_data.sql 仅保留数据，因此全新部署时必须先执行本文件。
-- 2026-09-13 第七批：PS 字段由 DDIC 口径对齐 OData V4 CamelCase（wbs_element→WBSElement 等）。
CREATE TABLE IF NOT EXISTS public.dim_ps_wbs_cost (
    id INTEGER PRIMARY KEY,
    "CostId" VARCHAR(50) NOT NULL,
    "WBSElement" VARCHAR(50) NOT NULL,
    "FiscalYear" VARCHAR(10) NOT NULL,
    "CostElement" VARCHAR(50) NOT NULL,
    "ActualCost" NUMERIC(18, 2),
    "CommittedCost" NUMERIC(18, 2),
    "PlannedCost" NUMERIC(18, 2),
    "Variance" NUMERIC(18, 2),
    "Currency" VARCHAR(10),
    "PostingDate" DATE
);
