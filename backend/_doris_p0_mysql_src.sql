-- 在 Windows MySQL tupu 库执行：创建 WBS 成本源表 + 5行数据
USE tupu;

DROP TABLE IF EXISTS biz_wbs_cost_src;
CREATE TABLE biz_wbs_cost_src (
  cost_id VARCHAR(32) NOT NULL PRIMARY KEY,
  wbs_element VARCHAR(32) NOT NULL,
  fiscal_year VARCHAR(10),
  cost_element VARCHAR(32),
  actual_cost DECIMAL(18,2),
  planned_cost DECIMAL(18,2),
  variance DECIMAL(18,2),
  currency VARCHAR(10),
  posting_date DATE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='WBS成本源表（供Doris视图读取）';

INSERT INTO biz_wbs_cost_src VALUES
('CT-001','W-001','2024','50000001',380000000,450000000,-70000000,'CNY','2024-11-30'),
('CT-002','W-001','2024','50000002',50000000,60000000,-10000000,'CNY','2024-11-30'),
('CT-003','W-002','2024','50000001',280000000,300000000,-20000000,'CNY','2024-11-30'),
('CT-004','W-002','2024','50000002',30000000,30000000,0,'CNY','2024-11-30'),
('CT-005','W-001-2','2024','50000001',200000000,200000000,0,'CNY','2024-11-30');

SELECT COUNT(*) AS row_count FROM biz_wbs_cost_src;
SELECT * FROM biz_wbs_cost_src;
