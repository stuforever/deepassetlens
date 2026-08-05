
-- ===== dim_ps_wbs_cost =====
DROP TABLE IF EXISTS `dim_ps_wbs_cost`;
CREATE TABLE `dim_ps_wbs_cost` (
  `cost_id` varchar(50) COMMENT 'cost_id',
  `wbs_element` varchar(50) COMMENT 'wbs_element',
  `fiscal_year` varchar(10) COMMENT 'fiscal_year',
  `cost_element` varchar(20) COMMENT 'cost_element',
  `actual_cost` DECIMAL(15, 2) COMMENT 'actual_cost',
  `committed_cost` DECIMAL(15, 2) COMMENT 'committed_cost',
  `planned_cost` DECIMAL(15, 2) COMMENT 'planned_cost',
  `variance` DECIMAL(15, 2) COMMENT 'variance',
  `currency` varchar(5) COMMENT 'currency',
  `posting_date` date COMMENT 'posting_date'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dim_ps_wbs_cost` (`cost_id`, `wbs_element`, `fiscal_year`, `cost_element`, `actual_cost`, `committed_cost`, `planned_cost`, `variance`, `currency`, `posting_date`) VALUES
  ('COST-001', 'W-001-1', 2024, 'CE0001', 32185.16, 26729.89, 16896.64, 7063.35, 'CNY', '2024-01-31'),
  ('COST-002', 'W-001-2', 2024, 'CE0002', 39161.67, 39016.38, 28519.32, 14488.95, 'CNY', '2024-03-01'),
  ('COST-003', 'W-001-3', 2024, 'CE0003', 7840.59, 45786.3, 11249.28, 40165.65, 'CNY', '2024-03-31'),
  ('COST-004', 'W-001-4', 2024, 'CE0004', 10660.21, 30508.96, 3651.55, 19750.93, 'CNY', '2024-04-30'),
  ('COST-005', 'W-001-5', 2024, 'CE0005', 23194.94, 22947.9, 17404.38, 38647.07, 'CNY', '2024-05-30'),
  ('COST-006', 'W-001-6', 2024, 'CE0006', 28217.08, 6155.82, 17527.51, 4884.4, 'CNY', '2024-06-29'),
  ('COST-007', 'W-001-7', 2024, 'CE0007', 39867.93, 38252.7, 25950.48, 24625.25, 'CNY', '2024-07-29'),
  ('COST-008', 'W-001-8', 2024, 'CE0008', 46990.55, 34775.56, 38973.86, 36291.94, 'CNY', '2024-08-28'),
  ('COST-009', 'W-001-9', 2024, 'CE0009', 37938.38, 1557.7, 46695.51, 2565.44, 'CNY', '2024-09-27'),
  ('COST-010', 'W-001-10', 2024, 'CE0010', 40232.32, 7898.01, 16126.06, 10736.19, 'CNY', '2024-10-27');

-- ===== dim_ps_wbs_element =====
DROP TABLE IF EXISTS `dim_ps_wbs_element`;
CREATE TABLE `dim_ps_wbs_element` (
  `wbs_element` varchar(255) COMMENT 'WBS元素编号',
  `description` varchar(255) COMMENT 'WBS描述',
  `project_definition` varchar(255) COMMENT '所属项目定义',
  `parent_wbs` varchar(255) COMMENT '上级WBS',
  `wbs_level` bigint COMMENT '层级',
  `person_responsible` varchar(255) COMMENT '负责人',
  `accounting_flag` varchar(255) COMMENT '记账元素标识',
  `plan_start_date` date COMMENT '计划开始日期',
  `plan_finish_date` date COMMENT '计划完成日期',
  `company_code` varchar(255) COMMENT '公司代码',
  `profit_center` varchar(255) COMMENT '利润中心',
  `cost_center` varchar(255) COMMENT '成本中心',
  `settlement_profile` varchar(255) COMMENT '结算参数文件',
  `objnr` varchar(255) COMMENT '对象编号'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dim_ps_wbs_element` (`wbs_element`, `description`, `project_definition`, `parent_wbs`, `wbs_level`, `person_responsible`, `accounting_flag`, `plan_start_date`, `plan_finish_date`, `company_code`, `profit_center`, `cost_center`, `settlement_profile`, `objnr`) VALUES
  ('W-001-1', '测试description_1', 'P-2024-001', 'W-001', 1, '张三', '', '2024-01-31', '2024-01-31', 'CC01', 'PC0001', 'CC0001', 'SP001', 'OBJ000001'),
  ('W-001-2', '测试description_2', 'P-2024-002', 'W-001', 2, '张四', 'X', '2024-03-01', '2024-03-01', 'CC02', 'PC0002', 'CC0002', 'SP001', 'OBJ000002'),
  ('W-001-3', '测试description_3', 'P-2024-003', 'W-001', 3, '张五', '', '2024-03-31', '2024-03-31', 'CC03', 'PC0003', 'CC0003', 'SP001', 'OBJ000003'),
  ('W-001-4', '测试description_4', 'P-2024-004', 'W-001-1', 1, '张六', 'X', '2024-04-30', '2024-04-30', 'CC04', 'PC0004', 'CC0004', 'SP001', 'OBJ000004'),
  ('W-001-5', '测试description_5', 'P-2024-005', 'W-001-2', 2, '张七', '', '2024-05-30', '2024-05-30', 'CC05', 'PC0005', 'CC0005', 'SP001', 'OBJ000005'),
  ('W-001-6', '测试description_6', 'P-2024-006', 'W-001-2', 3, '张八', 'X', '2024-06-29', '2024-06-29', 'CC06', 'PC0006', 'CC0006', 'SP001', 'OBJ000006'),
  ('W-001-7', '测试description_7', 'P-2024-007', 'W-001-3', 1, '张九', '', '2024-07-29', '2024-07-29', 'CC07', 'PC0007', 'CC0007', 'SP001', 'OBJ000007'),
  ('W-001-8', '测试description_8', 'P-2024-008', 'W-001-3', 2, '张十', 'X', '2024-08-28', '2024-08-28', 'CC08', 'PC0008', 'CC0008', 'SP001', 'OBJ000008'),
  ('W-001-9', '测试description_9', 'P-2024-009', 'W-001-4', 3, '张一', '', '2024-09-27', '2024-09-27', 'CC09', 'PC0009', 'CC0009', 'SP001', 'OBJ000009'),
  ('W-001-10', '测试description_10', 'P-2024-010', 'W-001-4', 1, '张二', 'X', '2024-10-27', '2024-10-27', 'CC10', 'PC0010', 'CC0010', 'SP001', 'OBJ000010');

-- ===== dim_ps_wbs_budget =====
DROP TABLE IF EXISTS `dim_ps_wbs_budget`;
CREATE TABLE `dim_ps_wbs_budget` (
  `budget_id` varchar(255) COMMENT '预算记录ID',
  `wbs_element` varchar(255) COMMENT 'WBS元素',
  `fiscal_year` varchar(255) COMMENT '年度',
  `total_budget` decimal(15,2) COMMENT '预算总额',
  `distributed_budget` decimal(15,2) COMMENT '已分配预算',
  `released_budget` decimal(15,2) COMMENT '已释放预算',
  `available_budget` decimal(15,2) COMMENT '可用预算',
  `currency` varchar(255) COMMENT '货币',
  `budget_profile` varchar(255) COMMENT '预算参数文件'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dim_ps_wbs_budget` (`budget_id`, `wbs_element`, `fiscal_year`, `total_budget`, `distributed_budget`, `released_budget`, `available_budget`, `currency`, `budget_profile`) VALUES
  ('BUD-001', 'W-001-1', 2024, 21424.39, 25136.83, 49928.56, 10985.74, 'CNY', 'sample_01'),
  ('BUD-002', 'W-001-2', 2024, 34683.38, 14552.26, 25128.3, 27741.56, 'CNY', 'sample_02'),
  ('BUD-003', 'W-001-3', 2024, 43990.82, 40294.6, 36058.68, 31943.27, 'CNY', 'sample_03'),
  ('BUD-004', 'W-001-4', 2024, 3485.4, 31152.22, 29658.45, 49654.14, 'CNY', 'sample_04'),
  ('BUD-005', 'W-001-5', 2024, 17490.84, 36868.1, 35398.32, 40761.6, 'CNY', 'sample_05'),
  ('BUD-006', 'W-001-6', 2024, 13118.81, 39487.59, 35616.65, 35596.79, 'CNY', 'sample_06'),
  ('BUD-007', 'W-001-7', 2024, 18179.33, 45005.91, 16474.3, 668.14, 'CNY', 'sample_07'),
  ('BUD-008', 'W-001-8', 2024, 13326.11, 2760.97, 3312.47, 20631.85, 'CNY', 'sample_08'),
  ('BUD-009', 'W-001-9', 2024, 29331.55, 18495.85, 8949.73, 29677.19, 'CNY', 'sample_09'),
  ('BUD-010', 'W-001-10', 2024, 42839.44, 45793.43, 23172.79, 36259.28, 'CNY', 'sample_10');

-- ===== dim_ps_object_status =====
DROP TABLE IF EXISTS `dim_ps_object_status`;
CREATE TABLE `dim_ps_object_status` (
  `objnr` varchar(255) COMMENT '对象编号',
  `status_code` varchar(255) COMMENT '状态编码',
  `status_type` varchar(255) COMMENT '状态类型',
  `status_name` varchar(255) COMMENT '状态名称',
  `active_flag` varchar(255) COMMENT '激活标识',
  `object_type` varchar(255) COMMENT '对象类型',
  `change_date` date COMMENT '变更日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dim_ps_object_status` (`objnr`, `status_code`, `status_type`, `status_name`, `active_flag`, `object_type`, `change_date`) VALUES
  ('OBJ000001', 'TECO', '用户状态', '测试status_name_1', 1, 'TYPE_B', '2024-01-31'),
  ('OBJ000002', 'CLSD', '系统状态', '测试status_name_2', 0, 'TYPE_C', '2024-03-01'),
  ('OBJ000003', 'CRTD', '用户状态', '测试status_name_3', 1, 'TYPE_A', '2024-03-31'),
  ('OBJ000004', 'REL', '系统状态', '测试status_name_4', 0, 'TYPE_B', '2024-04-30'),
  ('OBJ000005', 'TECO', '用户状态', '测试status_name_5', 1, 'TYPE_C', '2024-05-30'),
  ('OBJ000006', 'CLSD', '系统状态', '测试status_name_6', 0, 'TYPE_A', '2024-06-29'),
  ('OBJ000007', 'CRTD', '用户状态', '测试status_name_7', 1, 'TYPE_B', '2024-07-29'),
  ('OBJ000008', 'REL', '系统状态', '测试status_name_8', 0, 'TYPE_C', '2024-08-28'),
  ('OBJ000009', 'TECO', '用户状态', '测试status_name_9', 1, 'TYPE_A', '2024-09-27'),
  ('OBJ000010', 'CLSD', '系统状态', '测试status_name_10', 0, 'TYPE_B', '2024-10-27');

-- ===== dim_ps_network_component =====
DROP TABLE IF EXISTS `dim_ps_network_component`;
CREATE TABLE `dim_ps_network_component` (
  `component_id` varchar(255) COMMENT '组件编号',
  `network_number` varchar(255) COMMENT '所属网络',
  `activity_number` varchar(255) COMMENT '所属活动',
  `material_number` varchar(255) COMMENT '物料号',
  `description` varchar(255) COMMENT '物料描述',
  `requirement_quantity` decimal(15,2) COMMENT '需求数量',
  `base_unit` varchar(255) COMMENT '基本单位',
  `requirement_date` date COMMENT '需求日期',
  `plant` varchar(255) COMMENT '工厂',
  `item_category` varchar(255) COMMENT '项目类别',
  `reservation_number` varchar(255) COMMENT '预留号'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dim_ps_network_component` (`component_id`, `network_number`, `activity_number`, `material_number`, `description`, `requirement_quantity`, `base_unit`, `requirement_date`, `plant`, `item_category`, `reservation_number`) VALUES
  ('C-001', 'N-001', 'A-001', 'sample_01', '测试description_1', 100, 'sample_01', '2024-01-31', 'sample_01', 'sample_01', 'sample_01'),
  ('C-002', 'N-002', 'A-002', 'sample_02', '测试description_2', 200, 'sample_02', '2024-03-01', 'sample_02', 'sample_02', 'sample_02'),
  ('C-003', 'N-003', 'A-003', 'sample_03', '测试description_3', 300, 'sample_03', '2024-03-31', 'sample_03', 'sample_03', 'sample_03'),
  ('C-004', 'N-004', 'A-004', 'sample_04', '测试description_4', 400, 'sample_04', '2024-04-30', 'sample_04', 'sample_04', 'sample_04'),
  ('C-005', 'N-005', 'A-005', 'sample_05', '测试description_5', 500, 'sample_05', '2024-05-30', 'sample_05', 'sample_05', 'sample_05'),
  ('C-006', 'N-006', 'A-006', 'sample_06', '测试description_6', 600, 'sample_06', '2024-06-29', 'sample_06', 'sample_06', 'sample_06'),
  ('C-007', 'N-007', 'A-007', 'sample_07', '测试description_7', 700, 'sample_07', '2024-07-29', 'sample_07', 'sample_07', 'sample_07'),
  ('C-008', 'N-008', 'A-008', 'sample_08', '测试description_8', 800, 'sample_08', '2024-08-28', 'sample_08', 'sample_08', 'sample_08'),
  ('C-009', 'N-009', 'A-009', 'sample_09', '测试description_9', 900, 'sample_09', '2024-09-27', 'sample_09', 'sample_09', 'sample_09'),
  ('C-010', 'N-010', 'A-010', 'sample_10', '测试description_10', 1000, 'sample_10', '2024-10-27', 'sample_10', 'sample_10', 'sample_10');

-- ===== dwd_cust_analog_f =====
DROP TABLE IF EXISTS `dwd_cust_analog_f`;
CREATE TABLE `dwd_cust_analog_f` (
  `inst_id` varchar(255) COMMENT '安装点ID',
  `equip_src_id` varchar(255) COMMENT '电能表ID',
  `measuerment_type` varchar(255) COMMENT 'TotPF功率因数',
  `date` varchar(255) COMMENT '数据日期',
  `v0000_v2345` decimal(15,2) COMMENT '96个时间点数据值'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dwd_cust_analog_f` (`inst_id`, `equip_src_id`, `measuerment_type`, `date`, `v0000_v2345`) VALUES
  ('INST000001', 'M000001', 'TotW', 'sample_01', 100),
  ('INST000002', 'M000002', 'PhV_phsA', 'sample_02', 200),
  ('INST000003', 'M000003', 'PhV_phsB', 'sample_03', 300),
  ('INST000004', 'M000004', 'PhV_phsC', 'sample_04', 400),
  ('INST000005', 'M000005', 'Cur_phsA', 'sample_05', 500),
  ('INST000006', 'M000006', 'Cur_phsB', 'sample_06', 600),
  ('INST000007', 'M000007', 'Cur_phsC', 'sample_07', 700),
  ('INST000008', 'M000008', 'TotPF', 'sample_08', 800),
  ('INST000009', 'M000009', 'TotW', 'sample_09', 900),
  ('INST000010', 'M000010', 'PhV_phsA', 'sample_10', 1000);

-- ===== dwd_cust_analog_p =====
DROP TABLE IF EXISTS `dwd_cust_analog_p`;
CREATE TABLE `dwd_cust_analog_p` (
  `inst_id` varchar(255) COMMENT '安装点ID',
  `equip_src_id` varchar(255) COMMENT '电能表ID',
  `measuerment_type` varchar(255) COMMENT 'TotW有功功率Totvar无功功率TotVA视在功率',
  `date` varchar(255) COMMENT '数据日期',
  `v0000_v2345` decimal(15,2) COMMENT '96个时间点数据值'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dwd_cust_analog_p` (`inst_id`, `equip_src_id`, `measuerment_type`, `date`, `v0000_v2345`) VALUES
  ('INST000001', 'M000001', 'TotW', 'sample_01', 100),
  ('INST000002', 'M000002', 'PhV_phsA', 'sample_02', 200),
  ('INST000003', 'M000003', 'PhV_phsB', 'sample_03', 300),
  ('INST000004', 'M000004', 'PhV_phsC', 'sample_04', 400),
  ('INST000005', 'M000005', 'Cur_phsA', 'sample_05', 500),
  ('INST000006', 'M000006', 'Cur_phsB', 'sample_06', 600),
  ('INST000007', 'M000007', 'Cur_phsC', 'sample_07', 700),
  ('INST000008', 'M000008', 'TotPF', 'sample_08', 800),
  ('INST000009', 'M000009', 'TotW', 'sample_09', 900),
  ('INST000010', 'M000010', 'PhV_phsA', 'sample_10', 1000);

-- ===== dwd_cust_analog_u =====
DROP TABLE IF EXISTS `dwd_cust_analog_u`;
CREATE TABLE `dwd_cust_analog_u` (
  `inst_id` varchar(255) COMMENT '安装点ID',
  `equip_src_id` varchar(255) COMMENT '电能表ID',
  `measuerment_type` varchar(255) COMMENT 'PhV电压PhV_phsA相电压PhV_phsAB线电压等',
  `date` varchar(255) COMMENT '数据日期',
  `v0000_v2345` decimal(15,2) COMMENT '96个时间点数据值'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dwd_cust_analog_u` (`inst_id`, `equip_src_id`, `measuerment_type`, `date`, `v0000_v2345`) VALUES
  ('INST000001', 'M000001', 'TotW', 'sample_01', 100),
  ('INST000002', 'M000002', 'PhV_phsA', 'sample_02', 200),
  ('INST000003', 'M000003', 'PhV_phsB', 'sample_03', 300),
  ('INST000004', 'M000004', 'PhV_phsC', 'sample_04', 400),
  ('INST000005', 'M000005', 'Cur_phsA', 'sample_05', 500),
  ('INST000006', 'M000006', 'Cur_phsB', 'sample_06', 600),
  ('INST000007', 'M000007', 'Cur_phsC', 'sample_07', 700),
  ('INST000008', 'M000008', 'TotPF', 'sample_08', 800),
  ('INST000009', 'M000009', 'TotW', 'sample_09', 900),
  ('INST000010', 'M000010', 'PhV_phsA', 'sample_10', 1000);

-- ===== dwd_cust_analog_i =====
DROP TABLE IF EXISTS `dwd_cust_analog_i`;
CREATE TABLE `dwd_cust_analog_i` (
  `inst_id` varchar(255) COMMENT '安装点ID',
  `equip_src_id` varchar(255) COMMENT '电能表ID',
  `measuerment_type` varchar(255) COMMENT 'A_phs电流A_phsA向电流A_phsB向电流A_phsC向电流',
  `date` varchar(255) COMMENT '数据日期',
  `v0000_v2345` decimal(15,2) COMMENT '96个时间点数据值'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dwd_cust_analog_i` (`inst_id`, `equip_src_id`, `measuerment_type`, `date`, `v0000_v2345`) VALUES
  ('INST000001', 'M000001', 'TotW', 'sample_01', 100),
  ('INST000002', 'M000002', 'PhV_phsA', 'sample_02', 200),
  ('INST000003', 'M000003', 'PhV_phsB', 'sample_03', 300),
  ('INST000004', 'M000004', 'PhV_phsC', 'sample_04', 400),
  ('INST000005', 'M000005', 'Cur_phsA', 'sample_05', 500),
  ('INST000006', 'M000006', 'Cur_phsB', 'sample_06', 600),
  ('INST000007', 'M000007', 'Cur_phsC', 'sample_07', 700),
  ('INST000008', 'M000008', 'TotPF', 'sample_08', 800),
  ('INST000009', 'M000009', 'TotW', 'sample_09', 900),
  ('INST000010', 'M000010', 'PhV_phsA', 'sample_10', 1000);

-- ===== dwd_cst_mtcl_cust_cons_power_min =====
DROP TABLE IF EXISTS `dwd_cst_mtcl_cust_cons_power_min`;
CREATE TABLE `dwd_cst_mtcl_cust_cons_power_min` (
  `cons_id` varchar(50) COMMENT '用电客户ID',
  `meter_id` varchar(50) COMMENT '电能表ID',
  `data_time` datetime COMMENT '数据时间',
  `tot_w` decimal(12,4) COMMENT '有功功率',
  `tot_var` decimal(12,4) COMMENT '无功功率',
  `data_date` date COMMENT '数据日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dwd_cst_mtcl_cust_cons_power_min` (`cons_id`, `meter_id`, `data_time`, `tot_w`, `tot_var`, `data_date`) VALUES
  ('C100001', 'M000001', '2024-01-02 01:01:00', 28586.21, 28168.84, '2024-01-31'),
  ('C100002', 'M000002', '2024-01-03 02:02:00', 33837.62, 20189.3, '2024-03-01'),
  ('C100003', 'M000003', '2024-01-04 03:03:00', 32665.24, 19237.01, '2024-03-31'),
  ('C100004', 'M000004', '2024-01-05 04:04:00', 9003.97, 28811.97, '2024-04-30'),
  ('C100005', 'M000005', '2024-01-06 05:05:00', 16640.36, 20570.82, '2024-05-30'),
  ('C100006', 'M000006', '2024-01-07 06:06:00', 46805.86, 38529.21, '2024-06-29'),
  ('C100007', 'M000007', '2024-01-08 07:07:00', 31291.6, 38935.56, '2024-07-29'),
  ('C100008', 'M000008', '2024-01-09 08:08:00', 22986.96, 12287.72, '2024-08-28'),
  ('C100009', 'M000009', '2024-01-10 09:09:00', 24966.83, 6362.16, '2024-09-27'),
  ('C1000010', 'M000010', '2024-01-11 10:10:00', 1504.81, 23258.13, '2024-10-27');

-- ===== dwd_cst_mtcl_cust_cons_vol_min =====
DROP TABLE IF EXISTS `dwd_cst_mtcl_cust_cons_vol_min`;
CREATE TABLE `dwd_cst_mtcl_cust_cons_vol_min` (
  `cons_id` varchar(50) COMMENT '用电客户ID',
  `meter_id` varchar(50) COMMENT '电能表ID',
  `data_time` datetime COMMENT '数据时间',
  `phv_phsa` decimal(10,2) COMMENT 'A相电压',
  `phv_phsb` decimal(10,2) COMMENT 'B相电压',
  `phv_phsc` decimal(10,2) COMMENT 'C相电压',
  `data_date` date COMMENT '数据日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dwd_cst_mtcl_cust_cons_vol_min` (`cons_id`, `meter_id`, `data_time`, `phv_phsa`, `phv_phsb`, `phv_phsc`, `data_date`) VALUES
  ('C100001', 'M000001', '2024-01-02 01:01:00', 13923.02, 42076.1, 34410.02, '2024-01-31'),
  ('C100002', 'M000002', '2024-01-03 02:02:00', 27750.29, 18245.18, 27787.47, '2024-03-01'),
  ('C100003', 'M000003', '2024-01-04 03:03:00', 36720.69, 5712.66, 25334.74, '2024-03-31'),
  ('C100004', 'M000004', '2024-01-05 04:04:00', 22044.44, 3843.07, 34261.91, '2024-04-30'),
  ('C100005', 'M000005', '2024-01-06 05:05:00', 9190.24, 46749.38, 46799.05, '2024-05-30'),
  ('C100006', 'M000006', '2024-01-07 06:06:00', 38851.46, 27812.69, 46024.95, '2024-06-29'),
  ('C100007', 'M000007', '2024-01-08 07:07:00', 8211.1, 44918.07, 49271.87, '2024-07-29'),
  ('C100008', 'M000008', '2024-01-09 08:08:00', 18873.47, 1556.66, 31932.33, '2024-08-28'),
  ('C100009', 'M000009', '2024-01-10 09:09:00', 26969.9, 39102.35, 39738.93, '2024-09-27'),
  ('C1000010', 'M000010', '2024-01-11 10:10:00', 18493.79, 36633.11, 21632.6, '2024-10-27');

-- ===== dwd_cst_mtcl_cust_cons_cur_min =====
DROP TABLE IF EXISTS `dwd_cst_mtcl_cust_cons_cur_min`;
CREATE TABLE `dwd_cst_mtcl_cust_cons_cur_min` (
  `cons_id` varchar(50) COMMENT '用电客户ID',
  `meter_id` varchar(50) COMMENT '电能表ID',
  `data_time` datetime COMMENT '数据时间',
  `cur_phsa` decimal(10,2) COMMENT 'A相电流',
  `cur_phsb` decimal(10,2) COMMENT 'B相电流',
  `cur_phsc` decimal(10,2) COMMENT 'C相电流',
  `data_date` date COMMENT '数据日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dwd_cst_mtcl_cust_cons_cur_min` (`cons_id`, `meter_id`, `data_time`, `cur_phsa`, `cur_phsb`, `cur_phsc`, `data_date`) VALUES
  ('C100001', 'M000001', '2024-01-02 01:01:00', 27163.22, 26995.25, 29594.88, '2024-01-31'),
  ('C100002', 'M000002', '2024-01-03 02:02:00', 12726.02, 40981.07, 28997.11, '2024-03-01'),
  ('C100003', 'M000003', '2024-01-04 03:03:00', 34862.47, 33875.44, 29503.77, '2024-03-31'),
  ('C100004', 'M000004', '2024-01-05 04:04:00', 25693.56, 5653.74, 1394.42, '2024-04-30'),
  ('C100005', 'M000005', '2024-01-06 05:05:00', 2795.87, 24698.73, 42564.2, '2024-05-30'),
  ('C100006', 'M000006', '2024-01-07 06:06:00', 26010.35, 4768.22, 21221.83, '2024-06-29'),
  ('C100007', 'M000007', '2024-01-08 07:07:00', 49929.21, 12610.67, 36599.44, '2024-07-29'),
  ('C100008', 'M000008', '2024-01-09 08:08:00', 48953.63, 3546.08, 48285.63, '2024-08-28'),
  ('C100009', 'M000009', '2024-01-10 09:09:00', 7713.68, 6735.25, 39797.96, '2024-09-27'),
  ('C1000010', 'M000010', '2024-01-11 10:10:00', 19396.49, 40387.14, 48006.55, '2024-10-27');

-- ===== dim_ps_network_activity =====
DROP TABLE IF EXISTS `dim_ps_network_activity`;
CREATE TABLE `dim_ps_network_activity` (
  `activity_number` varchar(255) COMMENT '活动编号',
  `network_number` varchar(255) COMMENT '所属网络',
  `description` varchar(255) COMMENT '活动描述',
  `activity_type` varchar(255) COMMENT '活动类型',
  `control_key` varchar(255) COMMENT '控制码',
  `work_center` varchar(255) COMMENT '工作中心',
  `planned_work` decimal(15,2) COMMENT '计划工时',
  `work_unit` varchar(255) COMMENT '工时单位',
  `plan_start_date` date COMMENT '计划开始日期',
  `plan_finish_date` date COMMENT '计划完成日期',
  `duration` decimal(15,2) COMMENT '工期',
  `duration_unit` varchar(255) COMMENT '工期单位',
  `objnr` varchar(255) COMMENT '对象编号'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dim_ps_network_activity` (`activity_number`, `network_number`, `description`, `activity_type`, `control_key`, `work_center`, `planned_work`, `work_unit`, `plan_start_date`, `plan_finish_date`, `duration`, `duration_unit`, `objnr`) VALUES
  ('A-001', 'N-001', '测试description_1', 'A-001', 'sample_01', 'sample_01', 25432.31, 'sample_01', '2024-01-31', '2024-01-31', 100, 'sample_01', 'OBJ000001'),
  ('A-002', 'N-002', '测试description_2', 'A-002', 'sample_02', 'sample_02', 16857.56, 'sample_02', '2024-03-01', '2024-03-01', 200, 'sample_02', 'OBJ000002'),
  ('A-003', 'N-003', '测试description_3', 'A-003', 'sample_03', 'sample_03', 44030.73, 'sample_03', '2024-03-31', '2024-03-31', 300, 'sample_03', 'OBJ000003'),
  ('A-004', 'N-004', '测试description_4', 'A-004', 'sample_04', 'sample_04', 20919.58, 'sample_04', '2024-04-30', '2024-04-30', 400, 'sample_04', 'OBJ000004'),
  ('A-005', 'N-005', '测试description_5', 'A-005', 'sample_05', 'sample_05', 37902.68, 'sample_05', '2024-05-30', '2024-05-30', 500, 'sample_05', 'OBJ000005'),
  ('A-006', 'N-006', '测试description_6', 'A-006', 'sample_06', 'sample_06', 13184.33, 'sample_06', '2024-06-29', '2024-06-29', 600, 'sample_06', 'OBJ000006'),
  ('A-007', 'N-007', '测试description_7', 'A-007', 'sample_07', 'sample_07', 18447.12, 'sample_07', '2024-07-29', '2024-07-29', 700, 'sample_07', 'OBJ000007'),
  ('A-008', 'N-008', '测试description_8', 'A-008', 'sample_08', 'sample_08', 32306.81, 'sample_08', '2024-08-28', '2024-08-28', 800, 'sample_08', 'OBJ000008'),
  ('A-009', 'N-009', '测试description_9', 'A-009', 'sample_09', 'sample_09', 14534.0, 'sample_09', '2024-09-27', '2024-09-27', 900, 'sample_09', 'OBJ000009'),
  ('A-010', 'N-010', '测试description_10', 'A-010', 'sample_10', 'sample_10', 49070.94, 'sample_10', '2024-10-27', '2024-10-27', 1000, 'sample_10', 'OBJ000010');

-- ===== cms20_adj_volt_dev =====
DROP TABLE IF EXISTS `cms20_adj_volt_dev`;
CREATE TABLE `cms20_adj_volt_dev` (
  `adj_volt_dev_id` bigint COMMENT '调压设备标识',
  `adj_volt_dev_asset_id` bigint COMMENT '关联调压设备资产表主键',
  `cust_id` varchar(255) COMMENT '客户标识',
  `dist_sta_id` varchar(255) COMMENT '配送站标识'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `cms20_adj_volt_dev` (`adj_volt_dev_id`, `adj_volt_dev_asset_id`, `cust_id`, `dist_sta_id`) VALUES
  (100, 100, 'C100001', 'sample_01'),
  (200, 200, 'C100002', 'sample_02'),
  (300, 300, 'C100003', 'sample_03'),
  (400, 400, 'C100004', 'sample_04'),
  (500, 500, 'C100005', 'sample_05'),
  (600, 600, 'C100006', 'sample_06'),
  (700, 700, 'C100007', 'sample_07'),
  (800, 800, 'C100008', 'sample_08'),
  (900, 900, 'C100009', 'sample_09'),
  (1000, 1000, 'C1000010', 'sample_10');

-- ===== cms20_adj_volt_dev_asset =====
DROP TABLE IF EXISTS `cms20_adj_volt_dev_asset`;
CREATE TABLE `cms20_adj_volt_dev_asset` (
  `adj_volt_dev_asset_id` bigint COMMENT '调压设备资产标识',
  `pms_equip_id` varchar(255) COMMENT '电网设备标识'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `cms20_adj_volt_dev_asset` (`adj_volt_dev_asset_id`, `pms_equip_id`) VALUES
  (100, 'sample_01'),
  (200, 'sample_02'),
  (300, 'sample_03'),
  (400, 'sample_04'),
  (500, 'sample_05'),
  (600, 'sample_06'),
  (700, 'sample_07'),
  (800, 'sample_08'),
  (900, 'sample_09'),
  (1000, 'sample_10');

-- ===== dwd_psr_d_grid_analog_f =====
DROP TABLE IF EXISTS `dwd_psr_d_grid_analog_f`;
CREATE TABLE `dwd_psr_d_grid_analog_f` (
  `equip_type` varchar(255) COMMENT '设备类型编码',
  `psrid` varchar(255) COMMENT '电网资源ID',
  `pos_code` varchar(255) COMMENT '位置编码',
  `measuerment_type` varchar(255) COMMENT 'TotPF功率因数',
  `date` varchar(255) COMMENT '数据日期',
  `v0000_v2345` decimal(15,2) COMMENT '96个时间点数据值'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dwd_psr_d_grid_analog_f` (`equip_type`, `psrid`, `pos_code`, `measuerment_type`, `date`, `v0000_v2345`) VALUES
  ('0401004', 'PSR000001', 'POS0001', 'TotW', 'sample_01', 100),
  ('0408001', 'PSR000002', 'POS0002', 'PhV_phsA', 'sample_02', 200),
  ('0403000', 'PSR000003', 'POS0003', 'PhV_phsB', 'sample_03', 300),
  ('0401004', 'PSR000004', 'POS0004', 'PhV_phsC', 'sample_04', 400),
  ('0408001', 'PSR000005', 'POS0005', 'Cur_phsA', 'sample_05', 500),
  ('0403000', 'PSR000006', 'POS0006', 'Cur_phsB', 'sample_06', 600),
  ('0401004', 'PSR000007', 'POS0007', 'Cur_phsC', 'sample_07', 700),
  ('0408001', 'PSR000008', 'POS0008', 'TotPF', 'sample_08', 800),
  ('0403000', 'PSR000009', 'POS0009', 'TotW', 'sample_09', 900),
  ('0401004', 'PSR000010', 'POS0010', 'PhV_phsA', 'sample_10', 1000);

-- ===== dwd_psr_d_grid_analog_p =====
DROP TABLE IF EXISTS `dwd_psr_d_grid_analog_p`;
CREATE TABLE `dwd_psr_d_grid_analog_p` (
  `equip_type` varchar(255) COMMENT '设备类型编码',
  `psrid` varchar(255) COMMENT '电网资源ID',
  `pos_code` varchar(255) COMMENT '位置编码',
  `measuerment_type` varchar(255) COMMENT 'TotW有功功率Totvar无功功率TotVA视在功率',
  `date` varchar(255) COMMENT '数据日期',
  `v0000_v2345` decimal(15,2) COMMENT '96个时间点数据值'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dwd_psr_d_grid_analog_p` (`equip_type`, `psrid`, `pos_code`, `measuerment_type`, `date`, `v0000_v2345`) VALUES
  ('0401004', 'PSR000001', 'POS0001', 'TotW', 'sample_01', 100),
  ('0408001', 'PSR000002', 'POS0002', 'PhV_phsA', 'sample_02', 200),
  ('0403000', 'PSR000003', 'POS0003', 'PhV_phsB', 'sample_03', 300),
  ('0401004', 'PSR000004', 'POS0004', 'PhV_phsC', 'sample_04', 400),
  ('0408001', 'PSR000005', 'POS0005', 'Cur_phsA', 'sample_05', 500),
  ('0403000', 'PSR000006', 'POS0006', 'Cur_phsB', 'sample_06', 600),
  ('0401004', 'PSR000007', 'POS0007', 'Cur_phsC', 'sample_07', 700),
  ('0408001', 'PSR000008', 'POS0008', 'TotPF', 'sample_08', 800),
  ('0403000', 'PSR000009', 'POS0009', 'TotW', 'sample_09', 900),
  ('0401004', 'PSR000010', 'POS0010', 'PhV_phsA', 'sample_10', 1000);

-- ===== dwd_psr_d_grid_analog_u =====
DROP TABLE IF EXISTS `dwd_psr_d_grid_analog_u`;
CREATE TABLE `dwd_psr_d_grid_analog_u` (
  `equip_type` varchar(255) COMMENT '设备类型编码',
  `psrid` varchar(255) COMMENT '电网资源ID',
  `pos_code` varchar(255) COMMENT '位置编码',
  `measuerment_type` varchar(255) COMMENT 'PhV电压PhV_phsA相电压PhV_phsAB线电压等',
  `date` varchar(255) COMMENT '数据日期',
  `v0000_v2345` decimal(15,2) COMMENT '96个时间点数据值'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dwd_psr_d_grid_analog_u` (`equip_type`, `psrid`, `pos_code`, `measuerment_type`, `date`, `v0000_v2345`) VALUES
  ('0401004', 'PSR000001', 'POS0001', 'TotW', 'sample_01', 100),
  ('0408001', 'PSR000002', 'POS0002', 'PhV_phsA', 'sample_02', 200),
  ('0403000', 'PSR000003', 'POS0003', 'PhV_phsB', 'sample_03', 300),
  ('0401004', 'PSR000004', 'POS0004', 'PhV_phsC', 'sample_04', 400),
  ('0408001', 'PSR000005', 'POS0005', 'Cur_phsA', 'sample_05', 500),
  ('0403000', 'PSR000006', 'POS0006', 'Cur_phsB', 'sample_06', 600),
  ('0401004', 'PSR000007', 'POS0007', 'Cur_phsC', 'sample_07', 700),
  ('0408001', 'PSR000008', 'POS0008', 'TotPF', 'sample_08', 800),
  ('0403000', 'PSR000009', 'POS0009', 'TotW', 'sample_09', 900),
  ('0401004', 'PSR000010', 'POS0010', 'PhV_phsA', 'sample_10', 1000);

-- ===== dwd_psr_d_grid_analog_i =====
DROP TABLE IF EXISTS `dwd_psr_d_grid_analog_i`;
CREATE TABLE `dwd_psr_d_grid_analog_i` (
  `equip_type` varchar(255) COMMENT '设备类型编码',
  `psrid` varchar(255) COMMENT '电网资源ID',
  `pos_code` varchar(255) COMMENT '位置编码',
  `measuerment_type` varchar(255) COMMENT 'A_phs电流A_phsA向电流A_phsB向电流A_phsC向电流',
  `date` varchar(255) COMMENT '数据日期',
  `v0000_v2345` decimal(15,2) COMMENT '00:00至23:45每15分钟一个数据值'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dwd_psr_d_grid_analog_i` (`equip_type`, `psrid`, `pos_code`, `measuerment_type`, `date`, `v0000_v2345`) VALUES
  ('0401004', 'PSR000001', 'POS0001', 'TotW', 'sample_01', 100),
  ('0408001', 'PSR000002', 'POS0002', 'PhV_phsA', 'sample_02', 200),
  ('0403000', 'PSR000003', 'POS0003', 'PhV_phsB', 'sample_03', 300),
  ('0401004', 'PSR000004', 'POS0004', 'PhV_phsC', 'sample_04', 400),
  ('0408001', 'PSR000005', 'POS0005', 'Cur_phsA', 'sample_05', 500),
  ('0403000', 'PSR000006', 'POS0006', 'Cur_phsB', 'sample_06', 600),
  ('0401004', 'PSR000007', 'POS0007', 'Cur_phsC', 'sample_07', 700),
  ('0408001', 'PSR000008', 'POS0008', 'TotPF', 'sample_08', 800),
  ('0403000', 'PSR000009', 'POS0009', 'TotW', 'sample_09', 900),
  ('0401004', 'PSR000010', 'POS0010', 'PhV_phsA', 'sample_10', 1000);

-- ===== dim_ps_milestone =====
DROP TABLE IF EXISTS `dim_ps_milestone`;
CREATE TABLE `dim_ps_milestone` (
  `milestone_number` varchar(255) COMMENT '里程碑编号',
  `description` varchar(255) COMMENT '里程碑描述',
  `wbs_element` varchar(255) COMMENT '所属WBS',
  `network_number` varchar(255) COMMENT '所属网络',
  `activity_number` varchar(255) COMMENT '所属活动',
  `target_date` date COMMENT '目标日期',
  `actual_date` date COMMENT '实际日期',
  `billing_related` varchar(255) COMMENT '开票相关性',
  `usage` varchar(255) COMMENT '用途'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='模拟数据表';
INSERT INTO `dim_ps_milestone` (`milestone_number`, `description`, `wbs_element`, `network_number`, `activity_number`, `target_date`, `actual_date`, `billing_related`, `usage`) VALUES
  ('M-001', '测试description_1', 'W-001-1', 'N-001', 'A-001', '2024-01-31', '2024-01-31', 'sample_01', 'sample_01'),
  ('M-002', '测试description_2', 'W-001-2', 'N-002', 'A-002', '2024-03-01', '2024-03-01', 'sample_02', 'sample_02'),
  ('M-003', '测试description_3', 'W-001-3', 'N-003', 'A-003', '2024-03-31', '2024-03-31', 'sample_03', 'sample_03'),
  ('M-004', '测试description_4', 'W-001-4', 'N-004', 'A-004', '2024-04-30', '2024-04-30', 'sample_04', 'sample_04'),
  ('M-005', '测试description_5', 'W-001-5', 'N-005', 'A-005', '2024-05-30', '2024-05-30', 'sample_05', 'sample_05'),
  ('M-006', '测试description_6', 'W-001-6', 'N-006', 'A-006', '2024-06-29', '2024-06-29', 'sample_06', 'sample_06'),
  ('M-007', '测试description_7', 'W-001-7', 'N-007', 'A-007', '2024-07-29', '2024-07-29', 'sample_07', 'sample_07'),
  ('M-008', '测试description_8', 'W-001-8', 'N-008', 'A-008', '2024-08-28', '2024-08-28', 'sample_08', 'sample_08'),
  ('M-009', '测试description_9', 'W-001-9', 'N-009', 'A-009', '2024-09-27', '2024-09-27', 'sample_09', 'sample_09'),
  ('M-010', '测试description_10', 'W-001-10', 'N-010', 'A-010', '2024-10-27', '2024-10-27', 'sample_10', 'sample_10');