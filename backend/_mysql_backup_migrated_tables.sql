-- tupu 已迁移到 PG/ES 的实体表备份
-- 生成时间: 2026-08-04T12:13:48.596244
-- 表数: 125
-- 恢复: docker exec -i docker-mysql-1 mysql -uroot -proot tupu < _mysql_backup_migrated_tables.sql

-- MySQL dump 10.13  Distrib 8.0.39, for Linux (x86_64)
--
-- Host: localhost    Database: tupu
-- ------------------------------------------------------
-- Server version	8.0.39

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `cms20_adj_volt_dev`
--

DROP TABLE IF EXISTS `cms20_adj_volt_dev`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cms20_adj_volt_dev` (
  `adj_volt_dev_id` decimal(20,4) NOT NULL,
  `adj_volt_dev_asset_id` decimal(20,4) DEFAULT NULL,
  `cust_id` varchar(255) DEFAULT NULL,
  `dist_sta_id` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`adj_volt_dev_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cms20_adj_volt_dev`
--

LOCK TABLES `cms20_adj_volt_dev` WRITE;
/*!40000 ALTER TABLE `cms20_adj_volt_dev` DISABLE KEYS */;
INSERT INTO `cms20_adj_volt_dev` VALUES (1.0000,1.0000,'1','DIS0002'),(2.0000,2.0000,'2','DIS0003'),(3.0000,3.0000,'3','DIS0001'),(4.0000,4.0000,'4','DIS0002'),(5.0000,5.0000,'5','DIS0003'),(6.0000,6.0000,'6','DIS0001'),(7.0000,7.0000,'7','DIS0002'),(8.0000,8.0000,'8','DIS0003'),(9.0000,9.0000,'9','DIS0001'),(10.0000,10.0000,'10','DIS0002');
/*!40000 ALTER TABLE `cms20_adj_volt_dev` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cms20_adj_volt_dev_asset`
--

DROP TABLE IF EXISTS `cms20_adj_volt_dev_asset`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cms20_adj_volt_dev_asset` (
  `adj_volt_dev_asset_id` decimal(20,4) NOT NULL,
  `pms_equip_id` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`adj_volt_dev_asset_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cms20_adj_volt_dev_asset`
--

LOCK TABLES `cms20_adj_volt_dev_asset` WRITE;
/*!40000 ALTER TABLE `cms20_adj_volt_dev_asset` DISABLE KEYS */;
INSERT INTO `cms20_adj_volt_dev_asset` VALUES (1.0000,'RES0001'),(2.0000,'RES0002'),(3.0000,'RES0003'),(4.0000,'RES0004'),(5.0000,'RES0005'),(6.0000,'RES0006'),(7.0000,'RES0007'),(8.0000,'RES0008'),(9.0000,'RES0009'),(10.0000,'RES0010');
/*!40000 ALTER TABLE `cms20_adj_volt_dev_asset` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `cms20_cst_cust`
--

DROP TABLE IF EXISTS `cms20_cst_cust`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `cms20_cst_cust` (
  `cust_id` decimal(20,4) NOT NULL,
  `cust_no` varchar(255) DEFAULT NULL,
  `cust_name` varchar(255) DEFAULT NULL,
  `ind_cls` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`cust_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `cms20_cst_cust`
--

LOCK TABLES `cms20_cst_cust` WRITE;
/*!40000 ALTER TABLE `cms20_cst_cust` DISABLE KEYS */;
INSERT INTO `cms20_cst_cust` VALUES (1.0000,'CUST000001','能源客户1','IND01'),(2.0000,'CUST000002','能源客户2','IND02'),(3.0000,'CUST000003','能源客户3','IND03'),(4.0000,'CUST000004','能源客户4','IND04'),(5.0000,'CUST000005','能源客户5','IND05'),(6.0000,'CUST000006','能源客户6','IND06'),(7.0000,'CUST000007','能源客户7','IND07'),(8.0000,'CUST000008','能源客户8','IND08'),(9.0000,'CUST000009','能源客户9','IND09'),(10.0000,'CUST000010','能源客户10','IND10');
/*!40000 ALTER TABLE `cms20_cst_cust` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_acq_trml`
--

DROP TABLE IF EXISTS `dim_cst_acq_trml`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_acq_trml` (
  `dev_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `categ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `categ_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_type_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rv_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rc_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wire_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wire_mode_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ref_volt` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ref_volt_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `uplink_comm_chan` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `uplink_comm_chan_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `downlink_comm_chan` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `downlink_comm_chan_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_prot` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_prot_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_sprt_mod` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_sprt_mod_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sprt_all_evnt_deg` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sprt_all_evnt_deg_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hw_ver` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hw_ver_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `carr_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `carr_type_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `carr_chip_model` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `carr_sw_ver` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `carr_sw_ver_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `carr_freq_rng` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `carr_freq_rng_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `carr_chip_manuf` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `carr_center_freq_point` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `coll_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `coll_mode_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bar_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mfr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_model` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_model_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estab_arch_date` datetime DEFAULT NULL,
  `fty_date` datetime DEFAULT NULL,
  `last_chk_date` datetime DEFAULT NULL,
  `arr_batch_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_meter` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_meter_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ap_accu_lv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ap_accu_lv_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rp_accu_lv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rp_accu_lv_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_mode_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `disp_digit` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnst` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pile_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_in_meter_ctnr_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctnr_asset_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_categ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_categ_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_instal_date` datetime DEFAULT NULL,
  `col_number` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `row_number` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pr_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pr_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pr_org` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pur_batch` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mtrl_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spec_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spec_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `box_bar_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estab_arch_type_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estab_arch_type_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_date` datetime DEFAULT NULL,
  `rmv_date` datetime DEFAULT NULL,
  `retr_date` datetime DEFAULT NULL,
  `pro_spec_id_temp` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pro_spec_no_temp` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pro_spec_name_temp` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `other_dev_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `order_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `order_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bid_batch_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bid_lot_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arr_batch_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `creator` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `first_veri_date` datetime DEFAULT NULL,
  `old_new_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `old_new_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_fac_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `loc_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_srv_addr_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_loc_addr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `produce_mf_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `produce_mf_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `unified_soc_credit_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stat_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prnt_iot_point_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_stat_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_type_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acq_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acq_mode_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_sta_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `orgn_iot_point_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_acq_dev_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_asset_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_stat_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acs_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acs_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `conn_harmonic_dev_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `conn_harmonic_dev_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_side_sys_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_side_sys_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_cls` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_cls_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_date` datetime DEFAULT NULL,
  `trml_addr_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_loc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rem_comm_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rem_comm_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_code_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_code_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_code_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `create_time` datetime DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  `sn` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`dev_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_acq_trml`
--

LOCK TABLES `dim_cst_acq_trml` WRITE;
/*!40000 ALTER TABLE `dim_cst_acq_trml` DISABLE KEYS */;
INSERT INTO `dim_cst_acq_trml` VALUES ('DEV0001','类别_1','类别名称1','类型_1','类型名称1','额定电压_1','额定电压名称1','额定电流_1','额定电流名称1','接线方式_1','接线方式名称1','参比电压_1','参比电压名称1','上行通信信道_1','上行通信信道名称1','下行通信信道_1','下行通信信道名称1','通信规约_1','通信规约名称1','支持模块标志_1','支持模块名称1','支持全事件程度_1','支持全事件程度名称1','硬件版本_1','硬件版本名称1','载波类型_1','载波类型名称1','载波芯片型号_1','载波软件版本_1','载波软件版本名称1','载波频率范围_1','载波频率范围名称1','载波芯片厂商_1','载波中心频点_1','采集方式_1','采集方式名称1','BA-0001','AS-0001','FT-0001','MF-0001','型号_1','型号名称1','2025-03-05 20:00:00','2024-03-30 04:00:00','2024-02-26 21:00:00','ARR0001','自带交采表标志_1','自带交采表名称1','有功准确度等级_1','有功准确度等级名称1','无功准确度等级_1','无功准确度等级名称1','通讯方式_1','通讯方式名称1','表位数_1','常数_1','PI-0001','DEV0001','CTN0001','设备类别_1','设备类别名称1','2024-01-01 01:00:00','CO-0001','RO-0001','PR-0001','产权名称1','国家电投','采购批次_1','CTR0001','MT-0001','SP-0001','规格名称1','BO-0001','ES-0001','建档类型名称1','2024-07-29 11:00:00','2024-10-02 18:00:00','2024-03-10 02:00:00','品规标识_1','PR-0001','品规名称1','OTH0001','ORD0001','OR-0001','CT-0001','BID0001','BI-0001','AR-0001','创建人_1','2025-03-09 04:00:00','新旧标志_1','新旧名称1','DEV0001','LOC0001','名称1','SRV0001','BUS0001','广州市天河区zz路3号','PRO0001','生产厂家名称1','UN-0001','异常','状态名称1','IOT0001','PR-0001','停用','物联点状态名称1','物联点名称1','IO-0001','物联点类型_1','物联点类型名称1','物联点采集方式_1','物联点采集方式名称1','DIS0001','OR-0001','INS0001','DE-0001','正常','运行状态名称1','交流采样标志_1','交流采样名称1','IO-0001','接谐波装置标志_1','接谐波装置名称1','客户侧系统标志_1','客户侧系统名称1','设备分类_1','设备分类名称1','2025-04-06 09:00:00','TR-0001','安装位置_1','是否远程通讯_1','是否远程通讯名称1','DEV0001','DE-0001','设备码名称1','有效标志_1','有效名称1','2024-06-05 21:00:00','2024-08-03 09:00:00','顺序号_1','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-09-11 20:00:00'),('DEV0002','类别_2','类别名称2','类型_2','类型名称2','额定电压_2','额定电压名称2','额定电流_2','额定电流名称2','接线方式_2','接线方式名称2','参比电压_2','参比电压名称2','上行通信信道_2','上行通信信道名称2','下行通信信道_2','下行通信信道名称2','通信规约_2','通信规约名称2','支持模块标志_2','支持模块名称2','支持全事件程度_2','支持全事件程度名称2','硬件版本_2','硬件版本名称2','载波类型_2','载波类型名称2','载波芯片型号_2','载波软件版本_2','载波软件版本名称2','载波频率范围_2','载波频率范围名称2','载波芯片厂商_2','载波中心频点_2','采集方式_2','采集方式名称2','BA-0002','AS-0002','FT-0002','MF-0002','型号_2','型号名称2','2024-03-16 20:00:00','2025-02-11 07:00:00','2025-01-27 13:00:00','ARR0002','自带交采表标志_2','自带交采表名称2','有功准确度等级_2','有功准确度等级名称2','无功准确度等级_2','无功准确度等级名称2','通讯方式_2','通讯方式名称2','表位数_2','常数_2','PI-0002','DEV0002','CTN0002','设备类别_2','设备类别名称2','2024-08-12 08:00:00','CO-0002','RO-0002','PR-0002','产权名称2','国家电投','采购批次_2','CTR0002','MT-0002','SP-0002','规格名称2','BO-0002','ES-0002','建档类型名称2','2025-04-13 12:00:00','2024-08-25 23:00:00','2024-07-28 03:00:00','品规标识_2','PR-0002','品规名称2','OTH0002','ORD0002','OR-0002','CT-0002','BID0002','BI-0002','AR-0002','创建人_2','2024-08-01 08:00:00','新旧标志_2','新旧名称2','DEV0002','LOC0002','名称2','SRV0002','BUS0002','广州市天河区zz路3号','PRO0002','生产厂家名称2','UN-0002','注销','状态名称2','IOT0002','PR-0002','正常','物联点状态名称2','物联点名称2','IO-0002','物联点类型_2','物联点类型名称2','物联点采集方式_2','物联点采集方式名称2','DIS0002','OR-0002','INS0002','DE-0002','异常','运行状态名称2','交流采样标志_2','交流采样名称2','IO-0002','接谐波装置标志_2','接谐波装置名称2','客户侧系统标志_2','客户侧系统名称2','设备分类_2','设备分类名称2','2024-01-20 09:00:00','TR-0002','安装位置_2','是否远程通讯_2','是否远程通讯名称2','DEV0002','DE-0002','设备码名称2','有效标志_2','有效名称2','2025-03-31 16:00:00','2024-04-29 11:00:00','顺序号_2','省份名称2','地市名称2','MG-0002','管理单位名称2','2024-07-21 14:00:00'),('DEV0003','类别_3','类别名称3','类型_3','类型名称3','额定电压_3','额定电压名称3','额定电流_3','额定电流名称3','接线方式_3','接线方式名称3','参比电压_3','参比电压名称3','上行通信信道_3','上行通信信道名称3','下行通信信道_3','下行通信信道名称3','通信规约_3','通信规约名称3','支持模块标志_3','支持模块名称3','支持全事件程度_3','支持全事件程度名称3','硬件版本_3','硬件版本名称3','载波类型_3','载波类型名称3','载波芯片型号_3','载波软件版本_3','载波软件版本名称3','载波频率范围_3','载波频率范围名称3','载波芯片厂商_3','载波中心频点_3','采集方式_3','采集方式名称3','BA-0003','AS-0003','FT-0003','MF-0003','型号_3','型号名称3','2024-06-15 17:00:00','2025-02-25 09:00:00','2024-03-23 10:00:00','ARR0003','自带交采表标志_3','自带交采表名称3','有功准确度等级_3','有功准确度等级名称3','无功准确度等级_3','无功准确度等级名称3','通讯方式_3','通讯方式名称3','表位数_3','常数_3','PI-0003','DEV0003','CTN0003','设备类别_3','设备类别名称3','2024-11-10 16:00:00','CO-0003','RO-0003','PR-0003','产权名称3','大唐集团','采购批次_3','CTR0003','MT-0003','SP-0003','规格名称3','BO-0003','ES-0003','建档类型名称3','2024-06-10 11:00:00','2025-05-11 02:00:00','2024-11-24 16:00:00','品规标识_3','PR-0003','品规名称3','OTH0003','ORD0003','OR-0003','CT-0003','BID0003','BI-0003','AR-0003','创建人_3','2025-01-15 15:00:00','新旧标志_3','新旧名称3','DEV0003','LOC0003','名称3','SRV0003','BUS0003','上海市浦东新区yy路2号','PRO0003','生产厂家名称3','UN-0003','异常','状态名称3','IOT0003','PR-0003','停用','物联点状态名称3','物联点名称3','IO-0003','物联点类型_3','物联点类型名称3','物联点采集方式_3','物联点采集方式名称3','DIS0003','OR-0003','INS0003','DE-0003','停用','运行状态名称3','交流采样标志_3','交流采样名称3','IO-0003','接谐波装置标志_3','接谐波装置名称3','客户侧系统标志_3','客户侧系统名称3','设备分类_3','设备分类名称3','2024-05-02 01:00:00','TR-0003','安装位置_3','是否远程通讯_3','是否远程通讯名称3','DEV0003','DE-0003','设备码名称3','有效标志_3','有效名称3','2024-11-25 07:00:00','2025-02-14 08:00:00','顺序号_3','省份名称3','地市名称3','MG-0003','管理单位名称3','2025-05-13 18:00:00');
/*!40000 ALTER TABLE `dim_cst_acq_trml` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_cert_set`
--

DROP TABLE IF EXISTS `dim_cst_cert_set`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_cert_set` (
  `cert_set_id` int NOT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attach_id` int DEFAULT NULL,
  `ipt_sorc_id` int DEFAULT NULL,
  `ipt_sorc_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cert_dept` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cert_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cert_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cert_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cert_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cert_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_beg_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_end_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `residence` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `birthday` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cert_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cert_site` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cert_attr_map` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bp_id` int DEFAULT NULL,
  `creator` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `recent_updater` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recent_chg_date` datetime DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`cert_set_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_cert_set`
--

LOCK TABLES `dim_cst_cert_set` WRITE;
/*!40000 ALTER TABLE `dim_cst_cert_set` DISABLE KEYS */;
INSERT INTO `dim_cst_cert_set` VALUES (337390,'CU-0001',804121,366381,'录入来源类型_1','110105199018644067','CE-0001','CE-0001','CE-0001','证件类型名称1','证件名称1','2025-02-02 00:00:00','2025-05-09 00:00:00','住所_1','2024-12-28 00:00:00','2024-03-10 00:00:00','110105199039827696','有效标志_1','110105199030232236',952300,'创建人员_1','2024-08-20 19:00:00','2025-01-18 00:00:00','2024-09-23 23:00:00','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-04-06 10:00:00'),(940047,'CU-0003',323332,753069,'录入来源类型_3','110105199029797088','CE-0003','CE-0003','CE-0003','证件类型名称3','证件名称3','2024-05-29 00:00:00','2024-12-05 00:00:00','住所_3','2024-11-11 00:00:00','2024-07-23 00:00:00','110105199045766702','有效标志_3','110105199085620580',572747,'创建人员_3','2024-05-23 06:00:00','2025-02-17 00:00:00','2024-05-27 21:00:00','省份名称3','地市名称3','MG-0003','管理单位名称3','2024-07-01 01:00:00'),(975647,'CU-0002',317036,962397,'录入来源类型_2','110105199053423486','CE-0002','CE-0002','CE-0002','证件类型名称2','证件名称2','2024-04-25 00:00:00','2024-12-04 00:00:00','住所_2','2025-01-24 00:00:00','2024-09-14 00:00:00','110105199043265429','有效标志_2','110105199015363529',597490,'创建人员_2','2024-07-19 17:00:00','2025-04-10 00:00:00','2024-09-29 05:00:00','省份名称2','地市名称2','MG-0002','管理单位名称2','2024-10-07 17:00:00');
/*!40000 ALTER TABLE `dim_cst_cert_set` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_compl_assb_proj`
--

DROP TABLE IF EXISTS `dim_cst_compl_assb_proj`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_compl_assb_proj` (
  `compl_assb_proj_id` int NOT NULL,
  `proj_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bp_id` int DEFAULT NULL,
  `cust_id` int DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `aprv_date` datetime DEFAULT NULL,
  `aprv_gov_dept_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnfm_doc_num` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnfm_time` datetime DEFAULT NULL,
  `contact_tel` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_addr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_amt` double DEFAULT NULL,
  `proj_aprv_date` datetime DEFAULT NULL,
  `proj_bld_org` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_cmcnt_bld_time` datetime DEFAULT NULL,
  `contact` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_investor` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_invest_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_risk_lv` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_stat_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_stat_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_valid_date` datetime DEFAULT NULL,
  `rec_time` datetime DEFAULT NULL,
  `reply_doc_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reply_time` datetime DEFAULT NULL,
  `app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_run_time` datetime DEFAULT NULL,
  `run_size` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_chk_size` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fnl_load_size` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eng_id` int DEFAULT NULL,
  `proj_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_app_form_id` int DEFAULT NULL,
  `acpt_pwron_time` datetime DEFAULT NULL,
  `proj_attach_id` int DEFAULT NULL,
  `proj_fa_amt` double DEFAULT NULL,
  `aprv_gov_dept_level` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cvrn_base_proj_id` int DEFAULT NULL,
  `contact_bp_id` int DEFAULT NULL,
  `legal_bp_id` int DEFAULT NULL,
  `invest_bp_id` int DEFAULT NULL,
  `invest_bld_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_bld_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`compl_assb_proj_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_compl_assb_proj`
--

LOCK TABLES `dim_cst_compl_assb_proj` WRITE;
/*!40000 ALTER TABLE `dim_cst_compl_assb_proj` DISABLE KEYS */;
INSERT INTO `dim_cst_compl_assb_proj` VALUES (71357,'PR-0002',514700,77515,'CU-0002','2024-04-30 00:00:00','审批机关名称2','CN-0002','2025-02-16 21:00:00','13884646882','上海市浦东新区yy路2号',2833.6,'2024-11-16 21:00:00','华能集团','2024-02-12 22:00:00','联系人_2','项目描述测试数据2','项目投资方_2','项目投资类型_2','项目名称2','项目风险等级_2','PR-0002','项目状态名称2','2024-07-25 03:00:00','2025-04-06 15:00:00','RE-0002','2024-02-11 16:00:00','AP-0002','2024-10-28 08:00:00','已投产规模_2','项目核准规模_2','终期规模_2','MG-0002',357973,'PR-0002','项目类型名称2',391576,'2024-01-06 04:00:00',966021,6503.22,'审批机关层级_2',666617,154581,414025,668467,'IN-0002','投资建设模式名称2','省份名称2','地市名称2','MG-0002','管理单位名称2','2025-03-09 16:00:00'),(119058,'PR-0001',792989,959967,'CU-0001','2024-12-02 03:00:00','审批机关名称1','CN-0001','2025-04-11 00:00:00','13894497642','广州市天河区zz路3号',4299.25,'2024-09-03 05:00:00','华能集团','2024-11-01 20:00:00','联系人_1','项目描述测试数据1','项目投资方_1','项目投资类型_1','项目名称1','项目风险等级_1','PR-0001','项目状态名称1','2024-01-10 23:00:00','2024-10-15 01:00:00','RE-0001','2025-04-27 16:00:00','AP-0001','2024-02-28 03:00:00','已投产规模_1','项目核准规模_1','终期规模_1','MG-0001',330939,'PR-0001','项目类型名称1',198204,'2024-12-01 10:00:00',603472,6537.55,'审批机关层级_1',431789,457012,658779,494275,'IN-0001','投资建设模式名称1','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-11-26 05:00:00'),(692666,'PR-0003',703745,841744,'CU-0003','2024-03-13 09:00:00','审批机关名称3','CN-0003','2025-02-01 06:00:00','13832771523','上海市浦东新区yy路2号',4139.47,'2024-12-11 02:00:00','华能集团','2024-05-23 12:00:00','联系人_3','项目描述测试数据3','项目投资方_3','项目投资类型_3','项目名称3','项目风险等级_3','PR-0003','项目状态名称3','2025-05-13 23:00:00','2025-04-18 13:00:00','RE-0003','2024-03-14 11:00:00','AP-0003','2025-01-14 22:00:00','已投产规模_3','项目核准规模_3','终期规模_3','MG-0003',752843,'PR-0003','项目类型名称3',615488,'2024-01-11 06:00:00',335731,2461.54,'审批机关层级_3',227570,257001,759290,433574,'IN-0003','投资建设模式名称3','省份名称3','地市名称3','MG-0003','管理单位名称3','2025-01-16 00:00:00');
/*!40000 ALTER TABLE `dim_cst_compl_assb_proj` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_conn`
--

DROP TABLE IF EXISTS `dim_cst_conn`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_conn` (
  `conn_id` int NOT NULL,
  `conn_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` int DEFAULT NULL,
  `protect_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_contact_ep` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_all_incap` double DEFAULT NULL,
  `supl_tcap` double DEFAULT NULL,
  `supl_src_loc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_dev_cap` double DEFAULT NULL,
  `supl_dev_num` int DEFAULT NULL,
  `supl_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_lay_path_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_box_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ovrhd_line_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cable_spec_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dmd_cap` double DEFAULT NULL,
  `invest_intfc_loc_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_exp_lmt_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_supplier` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_id` int DEFAULT NULL,
  `t_pole_point` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bd_brk_rc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bd_brk_rv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `min_wire_sec_area` double DEFAULT NULL,
  `min_cable_sec_area` double DEFAULT NULL,
  `ps_dev_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `line_in_dev_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prnt_srv_loc_id` int DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `invalid_date` datetime DEFAULT NULL,
  `pr_point_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ap_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ps_dev_type_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ps_dev_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_char_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_char_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_phase_num_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_phase_num_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lay_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lay_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `protect_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `protect_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `orgn_cap` int DEFAULT NULL,
  `cntrl_sta_id` int DEFAULT NULL,
  `cntrl_sta_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_id` int DEFAULT NULL,
  `pipeline_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_sta_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_sta_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_tower_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pr_point_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pr_point_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`conn_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_conn`
--

LOCK TABLES `dim_cst_conn` WRITE;
/*!40000 ALTER TABLE `dim_cst_conn` DISABLE KEYS */;
INSERT INTO `dim_cst_conn` VALUES (569049,'CO-0003','CU-0003',112457,'保护类型_3','服务种类_3','供应备注测试数据3','供应接能点_3',3421.22,8499.73,'供应来源位置_3','供应类型_3',2865.16,7977,'SU-0003','管线铺设及路径说测试数据3','PI-0003','铺设管线选型（架_3','铺设管线选型（管_3',2248.82,'投资界面位置说明测试数据3','业扩受限标志_3','服务提供商_3',407929,'T接点_3','分界开关断路器额_3','分界开关断路器额_3',6310.84,1275.92,'PS0003','进线设备类型_3',723317,'2025-01-15 22:00:00','2024-06-04 04:00:00','产权分界点说明测试数据3','AP0003','PS-0003','电源类型名称3','SU-0003','电源性质名称3','SU-0003','电源相数名称3','VO-0003','供电电压名称3','LA-0003','进线方式名称3','PR-0003','保护方式名称3','RU-0003','运行方式名称3',257496,603956,'电源所属变电站名称3',248733,'电源所属线路名称3','DIS0003','电源所属台区名称3','PI-0003','PR-0003','产权分界点名称3','省份名称3','地市名称3','MG-0003','管理单位名称3','2024-02-09 17:00:00'),(934392,'CO-0002','CU-0002',704938,'保护类型_2','服务种类_2','供应备注测试数据2','供应接能点_2',99.09,4221.41,'供应来源位置_2','供应类型_2',53.1,35317,'SU-0002','管线铺设及路径说测试数据2','PI-0002','铺设管线选型（架_2','铺设管线选型（管_2',5841.81,'投资界面位置说明测试数据2','业扩受限标志_2','服务提供商_2',261747,'T接点_2','分界开关断路器额_2','分界开关断路器额_2',3522.21,4186.2,'PS0002','进线设备类型_2',905135,'2024-11-23 10:00:00','2024-06-19 11:00:00','产权分界点说明测试数据2','AP0002','PS-0002','电源类型名称2','SU-0002','电源性质名称2','SU-0002','电源相数名称2','VO-0002','供电电压名称2','LA-0002','进线方式名称2','PR-0002','保护方式名称2','RU-0002','运行方式名称2',624536,195935,'电源所属变电站名称2',565840,'电源所属线路名称2','DIS0002','电源所属台区名称2','PI-0002','PR-0002','产权分界点名称2','省份名称2','地市名称2','MG-0002','管理单位名称2','2024-08-17 18:00:00'),(940168,'CO-0001','CU-0001',64596,'保护类型_1','服务种类_1','供应备注测试数据1','供应接能点_1',732.31,4822.39,'供应来源位置_1','供应类型_1',9395.98,307749,'SU-0001','管线铺设及路径说测试数据1','PI-0001','铺设管线选型（架_1','铺设管线选型（管_1',8212.74,'投资界面位置说明测试数据1','业扩受限标志_1','服务提供商_1',202817,'T接点_1','分界开关断路器额_1','分界开关断路器额_1',508.68,6231.76,'PS0001','进线设备类型_1',445000,'2025-02-20 19:00:00','2024-01-24 22:00:00','产权分界点说明测试数据1','AP0001','PS-0001','电源类型名称1','SU-0001','电源性质名称1','SU-0001','电源相数名称1','VO-0001','供电电压名称1','LA-0001','进线方式名称1','PR-0001','保护方式名称1','RU-0001','运行方式名称1',370574,88358,'电源所属变电站名称1',818447,'电源所属线路名称1','DIS0001','电源所属台区名称1','PI-0001','PR-0001','产权分界点名称1','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-04-01 01:00:00');
/*!40000 ALTER TABLE `dim_cst_conn` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_conn_gen_power`
--

DROP TABLE IF EXISTS `dim_cst_conn_gen_power`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_conn_gen_power` (
  `conn_gen_power_id` int NOT NULL,
  `conn_gen_power_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` int DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `protect_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `protect_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `protect_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `protect_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_src_loc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_char_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_char_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_dev_cap` double DEFAULT NULL,
  `supl_dev_num` int DEFAULT NULL,
  `supl_phase_num_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_phase_num_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lay_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lay_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_lay_path_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_box_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pr_point_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pr_point_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ovrhd_line_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ovrhd_line_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cable_spec_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cable_spec_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_intfc_loc_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `relay_protect_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `relay_protect_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cntrl_sta_id` int DEFAULT NULL,
  `dist_sta_id` int DEFAULT NULL,
  `pipeline_id` int DEFAULT NULL,
  `pipeline_tower_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_supplier` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_id` int DEFAULT NULL,
  `t_pole_point` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accs_cap` double DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `invalid_date` datetime DEFAULT NULL,
  `ps_dev_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ps_dev_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ps_dev_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `line_in_dev_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pr_point_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ap_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`conn_gen_power_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_conn_gen_power`
--

LOCK TABLES `dim_cst_conn_gen_power` WRITE;
/*!40000 ALTER TABLE `dim_cst_conn_gen_power` DISABLE KEYS */;
INSERT INTO `dim_cst_conn_gen_power` VALUES (57779,'CO-0001',526081,'CU-0001','PR-0001','保护方式名称1','PR-0001','保护类型名称1','SR-0001','服务种类名称1','供应备注测试数据1','供应来源位置_1','SU-0001','供应类型名称1','SU-0001','供应性质名称1',5665.1,688242,'SU-0001','供应相数名称1','LA-0001','管线铺设方式名称1','管线铺设及路径说测试数据1','PI-0001','PR-0001','产权分界点名称1','VO-0001','承压名称1','OV-0001','铺设管线选型（架空）1','CA-0001','铺设管线选型（管线规1','投资界面位置说明测试数据1','RE-0001','继电保护类型名称1','RU-0001','运行方式名称1',865340,194252,201460,'PI-0001','服务提供商_1',536437,'T接点_1',7746.93,'2025-04-07 05:00:00','2024-06-27 04:00:00','PS-0001','电源设备类型名称1','PS0001','进线设备类型_1','产权分界点说明测试数据1','AP0001','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-11-20 17:00:00'),(494933,'CO-0002',118720,'CU-0002','PR-0002','保护方式名称2','PR-0002','保护类型名称2','SR-0002','服务种类名称2','供应备注测试数据2','供应来源位置_2','SU-0002','供应类型名称2','SU-0002','供应性质名称2',29.01,71963,'SU-0002','供应相数名称2','LA-0002','管线铺设方式名称2','管线铺设及路径说测试数据2','PI-0002','PR-0002','产权分界点名称2','VO-0002','承压名称2','OV-0002','铺设管线选型（架空）2','CA-0002','铺设管线选型（管线规2','投资界面位置说明测试数据2','RE-0002','继电保护类型名称2','RU-0002','运行方式名称2',661208,626137,516083,'PI-0002','服务提供商_2',955662,'T接点_2',9965.48,'2024-01-13 09:00:00','2025-02-03 21:00:00','PS-0002','电源设备类型名称2','PS0002','进线设备类型_2','产权分界点说明测试数据2','AP0002','省份名称2','地市名称2','MG-0002','管理单位名称2','2024-06-18 11:00:00'),(985061,'CO-0003',833597,'CU-0003','PR-0003','保护方式名称3','PR-0003','保护类型名称3','SR-0003','服务种类名称3','供应备注测试数据3','供应来源位置_3','SU-0003','供应类型名称3','SU-0003','供应性质名称3',8975.76,52616,'SU-0003','供应相数名称3','LA-0003','管线铺设方式名称3','管线铺设及路径说测试数据3','PI-0003','PR-0003','产权分界点名称3','VO-0003','承压名称3','OV-0003','铺设管线选型（架空）3','CA-0003','铺设管线选型（管线规3','投资界面位置说明测试数据3','RE-0003','继电保护类型名称3','RU-0003','运行方式名称3',682344,562877,45362,'PI-0003','服务提供商_3',291252,'T接点_3',8129.31,'2024-04-30 08:00:00','2024-01-25 03:00:00','PS-0003','电源设备类型名称3','PS0003','进线设备类型_3','产权分界点说明测试数据3','AP0003','省份名称3','地市名称3','MG-0003','管理单位名称3','2024-06-16 03:00:00');
/*!40000 ALTER TABLE `dim_cst_conn_gen_power` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_contact`
--

DROP TABLE IF EXISTS `dim_cst_contact`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_contact` (
  `id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `prtr_no_contact_id` int DEFAULT NULL,
  `contact_rec_id` int DEFAULT NULL,
  `cust_id` int DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prtr_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_prtr_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invalid_date` datetime DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `contact_prtr_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_prtr_priv` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_srv_addr_id` int DEFAULT NULL,
  `contact_remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_flag_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_flag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bp_id` int DEFAULT NULL,
  `contact_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prtr_rela_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prtr_rela_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gender` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_srv_addr_id` int DEFAULT NULL,
  `contact_bp_id` int DEFAULT NULL,
  `contact_rela_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_rela_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_rela_id` int DEFAULT NULL,
  `contact_stf_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `number_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `number_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `number_usage_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `number_usage_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_insert_time` datetime DEFAULT NULL,
  `data_insert_stf_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_id` int DEFAULT NULL,
  `num` int DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `create_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_contact`
--

LOCK TABLES `dim_cst_contact` WRITE;
/*!40000 ALTER TABLE `dim_cst_contact` DISABLE KEYS */;
INSERT INTO `dim_cst_contact` VALUES ('ID0001',999329,298415,913046,'CU-0001','PR-0001','CO-0001','2024-02-14 04:00:00','2024-12-24 16:00:00','业务合作伙伴关系_1','合作伙伴的权限_1',671210,'备注测试数据1','VA-0001','有效标志名称1',4957,'联系人名称1','PR-0001','业务伙伴关系类型名称1','性别_1',103962,612782,'CO-0001','联系人关系类型名称1',137731,'联络人1','NU-0001','号码类型名称1','NU-0001','号码用途名称1','CO-0001','2024-04-24 14:00:00','DAT0001','备注测试数据1',85214,351556,'MG-0001','管理单位名称1','省公司名称1','地市名称1','2025-01-05 04:00:00'),('ID0002',844653,986038,624385,'CU-0002','PR-0002','CO-0002','2024-06-05 06:00:00','2025-02-27 23:00:00','业务合作伙伴关系_2','合作伙伴的权限_2',751018,'备注测试数据2','VA-0002','有效标志名称2',768472,'联系人名称2','PR-0002','业务伙伴关系类型名称2','性别_2',762987,299133,'CO-0002','联系人关系类型名称2',182354,'联络人2','NU-0002','号码类型名称2','NU-0002','号码用途名称2','CO-0002','2024-01-15 02:00:00','DAT0002','备注测试数据2',137698,907562,'MG-0002','管理单位名称2','省公司名称2','地市名称2','2024-05-31 06:00:00'),('ID0003',951854,680114,271502,'CU-0003','PR-0003','CO-0003','2025-04-17 13:00:00','2024-05-02 23:00:00','业务合作伙伴关系_3','合作伙伴的权限_3',315486,'备注测试数据3','VA-0003','有效标志名称3',729160,'联系人名称3','PR-0003','业务伙伴关系类型名称3','性别_3',285322,566636,'CO-0003','联系人关系类型名称3',709622,'联络人3','NU-0003','号码类型名称3','NU-0003','号码用途名称3','CO-0003','2024-05-07 08:00:00','DAT0003','备注测试数据3',333229,90717,'MG-0003','管理单位名称3','省公司名称3','地市名称3','2024-08-15 21:00:00');
/*!40000 ALTER TABLE `dim_cst_contact` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_ctrt_setl_agrt`
--

DROP TABLE IF EXISTS `dim_cst_ctrt_setl_agrt`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_ctrt_setl_agrt` (
  `setl_agrt_id` int NOT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` int DEFAULT NULL,
  `ctrt_acct_id` int DEFAULT NULL,
  `setl_agrt_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_agrt_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rmdr_times` int DEFAULT NULL,
  `inv_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `note_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_days` int DEFAULT NULL,
  `pay_ovrd_days` int DEFAULT NULL,
  `bus_srv_addr_id` int DEFAULT NULL,
  `prnt_setl_agrt_app_id` int DEFAULT NULL,
  `ntce_number` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `agrt_prc_calc_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `agrt_prc` double DEFAULT NULL,
  `round_pwr_off_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_agrt_sub_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bank_branch_id` int DEFAULT NULL,
  `contact_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cost_center` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bp_id` int DEFAULT NULL,
  `settle_acct_id` int DEFAULT NULL,
  `valid_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_cyc_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_cyc_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_charg_issu_date` int DEFAULT NULL,
  `stop_supl_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_supl_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recoy_supl_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recoy_supl_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ntce_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ntce_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_tel` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrl_type_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrl_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bmk_st_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvd_adv_p_d_type_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvd_adv_p_d_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvd_adv_p_d_val` double DEFAULT NULL,
  `warn_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `warn_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_id` int DEFAULT NULL,
  `cm_id` int DEFAULT NULL,
  `app_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_amt` double DEFAULT NULL,
  `t_ctrt_cap` double DEFAULT NULL,
  `invalid_date` datetime DEFAULT NULL,
  `ctrt_path` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `drft_stf` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `drft_time` datetime DEFAULT NULL,
  `drft_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attach_id` int DEFAULT NULL,
  `bus_app_form_id` int DEFAULT NULL,
  `rela_ctrt_id` int DEFAULT NULL,
  `ctrt_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_type_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_text_form_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_text_form_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_stat_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_sig_type_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_sig_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_sig_time` datetime DEFAULT NULL,
  `ctrt_valid_time` datetime DEFAULT NULL,
  `supl_signer` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `usage_cust_signer` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_expiry_time` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `auto_renew_flag_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `auto_renew_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sig_site` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_valid_date_section` int DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`setl_agrt_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_ctrt_setl_agrt`
--

LOCK TABLES `dim_cst_ctrt_setl_agrt` WRITE;
/*!40000 ALTER TABLE `dim_cst_ctrt_setl_agrt` DISABLE KEYS */;
INSERT INTO `dim_cst_ctrt_setl_agrt` VALUES (413297,'CU-0003',755739,397772,'结算协议类别_3','结算协议类型_3',429529,'开票模式_3','NO-0003',407954,454397,48859,110605,'NT-0003','协议价格计算标志_3',676.55,'轮次停电标志_3','结算协议子类型_3',717462,'联系人姓名3','4324.95',412405,466605,'有效标志_3','PA-0003','结算周期名称3',969486,'ST-0003','停电方式名称3','RE-0003','复电方式名称3','NT-0003','停复电通知方式名称3','13852906281','CT-0003','控制类型名称3','BM-0003','RC-0003','预收代扣类型名称3',9798.91,'WA-0003','预警方式名称3',572305,922202,'AP-0003','服务种类_3','合同类别_3',4339.4,9402.9,'2024-09-28 09:00:00','合同路径_3','起草人_3','2025-01-18 04:00:00','起草标志_3','省份名称3','地市名称3','MG-0003','管理单位名称3','备注测试数据3',742904,225825,465017,'CT-0003','CT-0003','合同类型名称3','合同名称3','CT-0003','合同文本形式名称3','CT-0003','合同状态名称3','CT-0003','合同签订类型名称3','2024-05-31 20:00:00','2024-03-18 08:00:00','供电方签订人_3','用电方签订人_3','2024-10-03 00:00:00','AU-0003','自动续签标志名称3','杭州市西湖区bb路5号',662821,'2024-06-09 23:00:00'),(767465,'CU-0002',438154,748591,'结算协议类别_2','结算协议类型_2',164943,'开票模式_2','NO-0002',388413,50846,582646,650948,'NT-0002','协议价格计算标志_2',7601.89,'轮次停电标志_2','结算协议子类型_2',950715,'联系人姓名2','2398.87',101466,122060,'有效标志_2','PA-0002','结算周期名称2',812046,'ST-0002','停电方式名称2','RE-0002','复电方式名称2','NT-0002','停复电通知方式名称2','13848593412','CT-0002','控制类型名称2','BM-0002','RC-0002','预收代扣类型名称2',7447.2,'WA-0002','预警方式名称2',366187,425407,'AP-0002','服务种类_2','合同类别_2',4757.08,6464.62,'2024-11-16 22:00:00','合同路径_2','起草人_2','2025-02-03 13:00:00','起草标志_2','省份名称2','地市名称2','MG-0002','管理单位名称2','备注测试数据2',84790,465303,425620,'CT-0002','CT-0002','合同类型名称2','合同名称2','CT-0002','合同文本形式名称2','CT-0002','合同状态名称2','CT-0002','合同签订类型名称2','2024-11-15 10:00:00','2024-01-10 17:00:00','供电方签订人_2','用电方签订人_2','2024-10-06 00:00:00','AU-0002','自动续签标志名称2','广州市天河区zz路3号',390559,'2024-07-27 23:00:00'),(809004,'CU-0001',385872,237484,'结算协议类别_1','结算协议类型_1',326630,'开票模式_1','NO-0001',963994,774868,87918,885518,'NT-0001','协议价格计算标志_1',5161.36,'轮次停电标志_1','结算协议子类型_1',936650,'联系人姓名1','61935.18',731896,39443,'有效标志_1','PA-0001','结算周期名称1',253178,'ST-0001','停电方式名称1','RE-0001','复电方式名称1','NT-0001','停复电通知方式名称1','13854593894','CT-0001','控制类型名称1','BM-0001','RC-0001','预收代扣类型名称1',2684.73,'WA-0001','预警方式名称1',272092,760344,'AP-0001','服务种类_1','合同类别_1',6231.08,6542.24,'2025-01-02 19:00:00','合同路径_1','起草人_1','2024-07-12 21:00:00','起草标志_1','省份名称1','地市名称1','MG-0001','管理单位名称1','备注测试数据1',965486,861570,596430,'CT-0001','CT-0001','合同类型名称1','合同名称1','CT-0001','合同文本形式名称1','CT-0001','合同状态名称1','CT-0001','合同签订类型名称1','2024-08-10 15:00:00','2024-08-05 04:00:00','供电方签订人_1','用电方签订人_1','2024-08-28 00:00:00','AU-0001','自动续签标志名称1','深圳市南山区aa路4号',405131,'2024-08-23 12:00:00');
/*!40000 ALTER TABLE `dim_cst_ctrt_setl_agrt` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_dist_sta`
--

DROP TABLE IF EXISTS `dim_cst_dist_sta`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_dist_sta` (
  `dist_sta_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `resrc_supl_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `resrc_supl_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `resrc_supl_stat_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `resrc_supl_stat_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `publ_clg_flag_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `publ_clg_flag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_stacap` double DEFAULT NULL,
  `det_addr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `voltage` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`dist_sta_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_dist_sta`
--

LOCK TABLES `dim_cst_dist_sta` WRITE;
/*!40000 ALTER TABLE `dim_cst_dist_sta` DISABLE KEYS */;
INSERT INTO `dim_cst_dist_sta` VALUES ('DIS0001','RE-0001','配送站名称1','RE-0001','配送站状态名称1','PU-0001','公专标志名称1',4283.71,'杭州市西湖区bb路5号','SR-0001','服务种类名称1','2024-09-14 03:00:00','承压_1','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-10-21 10:00:00'),('DIS0002','RE-0002','配送站名称2','RE-0002','配送站状态名称2','PU-0002','公专标志名称2',5649.02,'杭州市西湖区bb路5号','SR-0002','服务种类名称2','2024-11-17 10:00:00','承压_2','省份名称2','地市名称2','MG-0002','管理单位名称2','2024-01-24 20:00:00'),('DIS0003','RE-0003','配送站名称3','RE-0003','配送站状态名称3','PU-0003','公专标志名称3',3932.02,'广州市天河区zz路3号','SR-0003','服务种类名称3','2024-09-17 19:00:00','承压_3','省份名称3','地市名称3','MG-0003','管理单位名称3','2024-07-19 19:00:00');
/*!40000 ALTER TABLE `dim_cst_dist_sta` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_dt_cust`
--

DROP TABLE IF EXISTS `dim_cst_dt_cust`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_dt_cust` (
  `dt_cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_addr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `esell_co_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `esell_co_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `esell_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dereg_attr_cls_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dereg_attr_cls_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reg_date` datetime DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `invalid_date` datetime DEFAULT NULL,
  `quit_trans_date` datetime DEFAULT NULL,
  `delist_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exec_punish_price_flag_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exec_punish_price_flag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_src_date` datetime DEFAULT NULL,
  `contact_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcv_time` datetime DEFAULT NULL,
  `dereg_member_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_stat_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_stat_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`dt_cust_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_dt_cust`
--

LOCK TABLES `dim_cst_dt_cust` WRITE;
/*!40000 ALTER TABLE `dim_cst_dt_cust` DISABLE KEYS */;
INSERT INTO `dim_cst_dt_cust` VALUES ('DT0001','CU-0001','客户名称1','杭州市西湖区bb路5号','EC-0001','用能类别名称1','VO-0001','承压名称1','ESE0001','ES-0001','售能公司名称1','DE-0001','市场化属性分类名称1','2024-05-25 12:00:00','2024-10-11 08:00:00','2024-12-12 03:00:00','2025-01-30 21:00:00','退市说明测试数据1','EX-0001','执行惩罚性电价标志名1','2024-07-04 23:00:00','联系人1','2025-04-12 21:00:00','DER0001','VA-0001','生效状态名称1','生效年月_1','省份名称1','地市名称1','MG-0001','管理单位名称1','2025-05-12 18:00:00'),('DT0002','CU-0002','客户名称2','深圳市南山区aa路4号','EC-0002','用能类别名称2','VO-0002','承压名称2','ESE0002','ES-0002','售能公司名称2','DE-0002','市场化属性分类名称2','2024-01-10 04:00:00','2024-04-28 23:00:00','2024-11-09 23:00:00','2024-11-27 04:00:00','退市说明测试数据2','EX-0002','执行惩罚性电价标志名2','2024-11-12 02:00:00','联系人2','2025-01-11 10:00:00','DER0002','VA-0002','生效状态名称2','生效年月_2','省份名称2','地市名称2','MG-0002','管理单位名称2','2025-02-25 12:00:00'),('DT0003','CU-0003','客户名称3','杭州市西湖区bb路5号','EC-0003','用能类别名称3','VO-0003','承压名称3','ESE0003','ES-0003','售能公司名称3','DE-0003','市场化属性分类名称3','2024-07-10 19:00:00','2024-08-08 23:00:00','2024-08-11 01:00:00','2024-01-26 04:00:00','退市说明测试数据3','EX-0003','执行惩罚性电价标志名3','2024-07-23 20:00:00','联系人3','2025-04-05 12:00:00','DER0003','VA-0003','生效状态名称3','生效年月_3','省份名称3','地市名称3','MG-0003','管理单位名称3','2024-07-25 00:00:00');
/*!40000 ALTER TABLE `dim_cst_dt_cust` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_elec_cons_cust`
--

DROP TABLE IF EXISTS `dim_cst_elec_cons_cust`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_elec_cons_cust` (
  `cust_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `elec_cons_cust_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bp_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `orgn_cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cstm_query_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hndl_time` datetime DEFAULT NULL,
  `estab_acct_date` datetime DEFAULT NULL,
  `cust_cls_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cls_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `urbanrural_categ_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `urbanrural_categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_char_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_char_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_flag_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cost_ctrl_flag_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cost_ctrl_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `main_hshd_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `main_hshd_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `impt_lv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `impt_lv_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_charts_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_charts_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `high_ecind_cls_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `high_ecind_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dereg_attr_cls_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dereg_attr_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_srv_addr_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_srv_addr_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_addr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_prov_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_city_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_county_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_county_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_rd_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_rd_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_st_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_st_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_neighbor_comm_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_neighbor_comm_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_cmny_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_cmny_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `house_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `longitude` double DEFAULT NULL,
  `latitude` double DEFAULT NULL,
  `prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_carea` double DEFAULT NULL,
  `ec_stf_num` int DEFAULT NULL,
  `holiday` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `usage_dur_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `usage_dur_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prod_shift_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prod_shift_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tmp_expr_date` datetime DEFAULT NULL,
  `tmp_ec_flag_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tmp_ec_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `scy_cap` double DEFAULT NULL,
  `ctrt_cap` double DEFAULT NULL,
  `run_cap` double DEFAULT NULL,
  `ecc_stat_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ecc_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `invalid_date` datetime DEFAULT NULL,
  `cncl_date` datetime DEFAULT NULL,
  `e_sdate` datetime DEFAULT NULL,
  `lock_stat_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lock_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pwr_off_reason` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_supl_flag_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_supl_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_supl_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_supl_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvr_supl_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvr_supl_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recent_chg_date` datetime DEFAULT NULL,
  `cr_pic_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cr_pic_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_calc_pic_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_calc_pic_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`cust_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_elec_cons_cust`
--

LOCK TABLES `dim_cst_elec_cons_cust` WRITE;
/*!40000 ALTER TABLE `dim_cst_elec_cons_cust` DISABLE KEYS */;
INSERT INTO `dim_cst_elec_cons_cust` VALUES ('CUS0001','ELE0001','CU-0001','BP0001','OR-0001','CS-0001','用电客户名称1','2024-08-26 04:00:00','2024-10-04 21:00:00','CU-0001','用电客户分类名称1','IN-0001','行业分类名称1','EC-0001','用电类别名称1','UR-0001','城乡类别名称1','LO-0001','负荷性质名称1','TR-0001','转供户标志名称1','CO-0001','费控标志名称1','是否主户_1','主户标志名称1','重要性等级_1','重要性等级名称1','LO-0001','负荷特性名称1','HI-0001','高耗能行业分类名称1','DE-0001','市场化属性分类名称1','BUS0001','业务服务地址名称1','广州市天河区zz路3号','ADM0001','AD-0001','省1','AD-0001','市1','AD-0001','区县1','AD-0001','道路1','AD-0001','街道（乡镇）1','AD-0001','居委会（村）1','AD-0001','小区1','HO-0001',1376.93,333.35,'省份名称1','地市名称1','MGT0001','MG-0001','管理单位名称1',7430.16,417108,'厂休日_1','US-0001','使用期限名称1','PR-0001','生产班次名称1','2024-06-12 07:00:00','TM-0001','临时用能标志名称1','VO-0001','承压名称1',806.36,6024.82,8916.77,'EC-0001','用电客户状态名称1','2024-02-25 07:00:00','2024-07-20 04:00:00','2024-03-30 15:00:00','2025-04-26 02:00:00','LO-0001','锁定状态名称1','最近一次停电原因_1','ST-0001','停供标志名称1','ST-0001','停供方式名称1','RC-0001','复供方式名称1','2024-10-14 19:00:00','CR0001','催费责任人名称1','CHK0001','核算责任人名称1','2025-04-23 20:00:00'),('CUS0002','ELE0002','CU-0002','BP0002','OR-0002','CS-0002','用电客户名称2','2025-02-21 18:00:00','2024-01-25 09:00:00','CU-0002','用电客户分类名称2','IN-0002','行业分类名称2','EC-0002','用电类别名称2','UR-0002','城乡类别名称2','LO-0002','负荷性质名称2','TR-0002','转供户标志名称2','CO-0002','费控标志名称2','是否主户_2','主户标志名称2','重要性等级_2','重要性等级名称2','LO-0002','负荷特性名称2','HI-0002','高耗能行业分类名称2','DE-0002','市场化属性分类名称2','BUS0002','业务服务地址名称2','北京市朝阳区xx路1号','ADM0002','AD-0002','省2','AD-0002','市2','AD-0002','区县2','AD-0002','道路2','AD-0002','街道（乡镇）2','AD-0002','居委会（村）2','AD-0002','小区2','HO-0002',9946.49,8975.98,'省份名称2','地市名称2','MGT0002','MG-0002','管理单位名称2',8986.06,28987,'厂休日_2','US-0002','使用期限名称2','PR-0002','生产班次名称2','2025-01-23 00:00:00','TM-0002','临时用能标志名称2','VO-0002','承压名称2',80.38,4382.59,7535.44,'EC-0002','用电客户状态名称2','2025-01-12 03:00:00','2024-11-10 04:00:00','2024-02-01 17:00:00','2024-12-09 04:00:00','LO-0002','锁定状态名称2','最近一次停电原因_2','ST-0002','停供标志名称2','ST-0002','停供方式名称2','RC-0002','复供方式名称2','2024-10-13 13:00:00','CR0002','催费责任人名称2','CHK0002','核算责任人名称2','2025-02-25 18:00:00'),('CUS0003','ELE0003','CU-0003','BP0003','OR-0003','CS-0003','用电客户名称3','2024-09-20 10:00:00','2024-07-07 03:00:00','CU-0003','用电客户分类名称3','IN-0003','行业分类名称3','EC-0003','用电类别名称3','UR-0003','城乡类别名称3','LO-0003','负荷性质名称3','TR-0003','转供户标志名称3','CO-0003','费控标志名称3','是否主户_3','主户标志名称3','重要性等级_3','重要性等级名称3','LO-0003','负荷特性名称3','HI-0003','高耗能行业分类名称3','DE-0003','市场化属性分类名称3','BUS0003','业务服务地址名称3','杭州市西湖区bb路5号','ADM0003','AD-0003','省3','AD-0003','市3','AD-0003','区县3','AD-0003','道路3','AD-0003','街道（乡镇）3','AD-0003','居委会（村）3','AD-0003','小区3','HO-0003',5815.31,3728.03,'省份名称3','地市名称3','MGT0003','MG-0003','管理单位名称3',5077.86,908041,'厂休日_3','US-0003','使用期限名称3','PR-0003','生产班次名称3','2024-02-02 15:00:00','TM-0003','临时用能标志名称3','VO-0003','承压名称3',6487.01,4408.47,2592.43,'EC-0003','用电客户状态名称3','2024-06-10 21:00:00','2024-03-11 21:00:00','2024-08-17 00:00:00','2024-10-03 22:00:00','LO-0003','锁定状态名称3','最近一次停电原因_3','ST-0003','停供标志名称3','ST-0003','停供方式名称3','RC-0003','复供方式名称3','2024-05-14 12:00:00','CR0003','催费责任人名称3','CHK0003','核算责任人名称3','2025-02-25 15:00:00');
/*!40000 ALTER TABLE `dim_cst_elec_cons_cust` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_elec_cons_cust_his`
--

DROP TABLE IF EXISTS `dim_cst_elec_cons_cust_his`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_elec_cons_cust_his` (
  `cust_id` int NOT NULL,
  `elec_cons_cust_id` int DEFAULT NULL,
  `cust_no` int DEFAULT NULL,
  `bp_id` int DEFAULT NULL,
  `orgn_cust_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cstm_query_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hndl_time` datetime DEFAULT NULL,
  `estab_acct_date` datetime DEFAULT NULL,
  `cust_cls_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_cls_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cls_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cls_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `frst_ind_cls_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `frst_ind_cls_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `scnd_ind_cls_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `scnd_ind_cls_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `third_ind_cls_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `third_ind_cls_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `furth_ind_cls_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `furth_ind_cls_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `urbanrural_categ_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `urbanrural_categ_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_char_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_char_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_flag_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `within_city_plan_range_flag_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `within_city_plan_range_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cost_ctrl_flag_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cost_ctrl_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `main_hshd_flag_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `main_hshd_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `impt_lv_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `impt_lv_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_charts_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_charts_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_scene_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_scene_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `scan_ecc_flag_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `scan_ecc_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `high_ecind_cls_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `high_ecind_cls_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dereg_attr_cls_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dereg_attr_cls_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_srv_addr_id` int DEFAULT NULL,
  `bus_srv_addr_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_addr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_id` int DEFAULT NULL,
  `adm_regn_prov_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_prov_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_city_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_city_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_county_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_county_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_rd_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_rd_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_st_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_st_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_neighbor_comm_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_neighbor_comm_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_cmny_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_cmny_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `house_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reside_regn_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reside_regn_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `longitude` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `latitude` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnty_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnty_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `branch_off_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `branch_off_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pow_sup_sta_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pow_sup_sta_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `energy_base` int DEFAULT NULL,
  `population_base` double DEFAULT NULL,
  `e_carea` double DEFAULT NULL,
  `ec_stf_num` int DEFAULT NULL,
  `holiday` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `usage_dur_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `usage_dur_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `frst_ees_date` datetime DEFAULT NULL,
  `prod_shift_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prod_shift_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tmp_expr_date` datetime DEFAULT NULL,
  `tmp_ec_flag_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tmp_ec_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `scy_cap` double DEFAULT NULL,
  `ctrt_cap` double DEFAULT NULL,
  `run_cap` double DEFAULT NULL,
  `ecc_stat_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ecc_stat_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `invalid_date` datetime DEFAULT NULL,
  `cncl_date` datetime DEFAULT NULL,
  `e_sdate` datetime DEFAULT NULL,
  `lock_stat_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lock_stat_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pwr_off_reason` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_supl_flag_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_supl_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_supl_mode_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_supl_mode_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvr_supl_mode_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvr_supl_mode_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recent_chg_date` datetime DEFAULT NULL,
  `cr_pic_team_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cr_pic_team_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_calc_pic_team_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_calc_pic_team_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chkr_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chkr_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cr_pic_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cr_pic_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_calc_pic_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_calc_pic_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_gen_cust_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charging_cust_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_sensitive_cust` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_div_inv_cust` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_spec_inv_cust` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `start_date` datetime DEFAULT NULL,
  `end_date` datetime DEFAULT NULL,
  `valid_state` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`cust_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_elec_cons_cust_his`
--

LOCK TABLES `dim_cst_elec_cons_cust_his` WRITE;
/*!40000 ALTER TABLE `dim_cst_elec_cons_cust_his` DISABLE KEYS */;
INSERT INTO `dim_cst_elec_cons_cust_his` VALUES (49964,655952,874239,643556,'OR-0003','CS-0003','用电客户名称3','2024-10-10 07:00:00','2024-01-23 16:00:00','CU-0003','用电客户分类名称3','IN-0003','行业分类名称3','FR-0003','一级行业分类名称3','SC-0003','二级行业分类名称3','TH-0003','三级行业分类名称3','FU-0003','四级行业分类名称3','EC-0003','用电类别名称3','UR-0003','城乡类别名称3','LO-0003','负荷性质名称3','TR-0003','转供户标志名称3','WI-0003','城镇规划范围内标志名3','CO-0003','费控标志名称3','MA-0003','主户标志名称3','IM-0003','重要性等级名称3','LO-0003','负荷特性名称3','EL-0003','用电场景名称3','SC-0003','扫码用电客户标志名称3','HI-0003','高耗能行业分类名称3','DE-0003','市场化属性分类名称3',350090,'业务服务地址名称3','北京市朝阳区xx路1号',796130,'AD-0003','省3','AD-0003','市3','AD-0003','区县3','AD-0003','道路3','AD-0003','街道（乡镇）3','AD-0003','居委会（村）3','AD-0003','小区3','HO-0003','RE-0003','居住区名称3','经度_3','纬度_3','PR-0003','省公司名称3','CI-0003','地市公司名称3','CN-0003','区县公司名称3','BR-0003','分公司名称3','PO-0003','供电所名称3','MG-0003','管理单位名称3',480320,2439.93,7555.52,839034,'厂休日_3','US-0003','使用期限名称3','2024-07-13 22:00:00','PR-0003','生产班次名称3','2024-01-28 18:00:00','TM-0003','临时用能标志名称3','VO-0003','承压名称3',7060.25,118.58,6795.78,'EC-0003','用电客户状态名称3','2024-05-04 19:00:00','2025-05-11 04:00:00','2024-02-04 21:00:00','2024-12-19 03:00:00','LO-0003','锁定状态名称3','最近一次停电原因_3','ST-0003','停供标志名称3','ST-0003','停供方式名称3','RC-0003','复供方式名称3','2024-04-15 01:00:00','CR-0003','催费责任人班组名称3','CH-0003','核算责任人班组名称3','CH-0003','用电检查人员名称3','CR0003','催费责任人名称3','CHK0003','核算责任人名称3','发电客户标志_3','充电桩客户标志_3','是否敏感客户_3','是否分割开票客户_3','是否特定开票客户_3','2024-09-24 18:00:00','2025-02-09 08:00:00','正常','历史数据 HT、_3','2025-04-23 13:00:00'),(569083,101639,996497,784493,'OR-0001','CS-0001','用电客户名称1','2024-02-03 05:00:00','2025-04-11 16:00:00','CU-0001','用电客户分类名称1','IN-0001','行业分类名称1','FR-0001','一级行业分类名称1','SC-0001','二级行业分类名称1','TH-0001','三级行业分类名称1','FU-0001','四级行业分类名称1','EC-0001','用电类别名称1','UR-0001','城乡类别名称1','LO-0001','负荷性质名称1','TR-0001','转供户标志名称1','WI-0001','城镇规划范围内标志名1','CO-0001','费控标志名称1','MA-0001','主户标志名称1','IM-0001','重要性等级名称1','LO-0001','负荷特性名称1','EL-0001','用电场景名称1','SC-0001','扫码用电客户标志名称1','HI-0001','高耗能行业分类名称1','DE-0001','市场化属性分类名称1',627760,'业务服务地址名称1','北京市朝阳区xx路1号',15336,'AD-0001','省1','AD-0001','市1','AD-0001','区县1','AD-0001','道路1','AD-0001','街道（乡镇）1','AD-0001','居委会（村）1','AD-0001','小区1','HO-0001','RE-0001','居住区名称1','经度_1','纬度_1','PR-0001','省公司名称1','CI-0001','地市公司名称1','CN-0001','区县公司名称1','BR-0001','分公司名称1','PO-0001','供电所名称1','MG-0001','管理单位名称1',600119,8379.18,998.89,210834,'厂休日_1','US-0001','使用期限名称1','2025-02-28 05:00:00','PR-0001','生产班次名称1','2025-04-24 15:00:00','TM-0001','临时用能标志名称1','VO-0001','承压名称1',6503.34,3700.12,3260.65,'EC-0001','用电客户状态名称1','2024-10-23 14:00:00','2025-05-07 13:00:00','2024-05-15 09:00:00','2024-07-06 12:00:00','LO-0001','锁定状态名称1','最近一次停电原因_1','ST-0001','停供标志名称1','ST-0001','停供方式名称1','RC-0001','复供方式名称1','2024-08-15 06:00:00','CR-0001','催费责任人班组名称1','CH-0001','核算责任人班组名称1','CH-0001','用电检查人员名称1','CR0001','催费责任人名称1','CHK0001','核算责任人名称1','发电客户标志_1','充电桩客户标志_1','是否敏感客户_1','是否分割开票客户_1','是否特定开票客户_1','2025-01-14 08:00:00','2024-04-18 17:00:00','正常','历史数据 HT、_1','2024-07-07 21:00:00'),(927316,356149,306542,173649,'OR-0002','CS-0002','用电客户名称2','2024-02-04 12:00:00','2024-07-11 01:00:00','CU-0002','用电客户分类名称2','IN-0002','行业分类名称2','FR-0002','一级行业分类名称2','SC-0002','二级行业分类名称2','TH-0002','三级行业分类名称2','FU-0002','四级行业分类名称2','EC-0002','用电类别名称2','UR-0002','城乡类别名称2','LO-0002','负荷性质名称2','TR-0002','转供户标志名称2','WI-0002','城镇规划范围内标志名2','CO-0002','费控标志名称2','MA-0002','主户标志名称2','IM-0002','重要性等级名称2','LO-0002','负荷特性名称2','EL-0002','用电场景名称2','SC-0002','扫码用电客户标志名称2','HI-0002','高耗能行业分类名称2','DE-0002','市场化属性分类名称2',147111,'业务服务地址名称2','广州市天河区zz路3号',779153,'AD-0002','省2','AD-0002','市2','AD-0002','区县2','AD-0002','道路2','AD-0002','街道（乡镇）2','AD-0002','居委会（村）2','AD-0002','小区2','HO-0002','RE-0002','居住区名称2','经度_2','纬度_2','PR-0002','省公司名称2','CI-0002','地市公司名称2','CN-0002','区县公司名称2','BR-0002','分公司名称2','PO-0002','供电所名称2','MG-0002','管理单位名称2',462737,5539.55,1680.6,757987,'厂休日_2','US-0002','使用期限名称2','2024-08-11 04:00:00','PR-0002','生产班次名称2','2024-03-11 15:00:00','TM-0002','临时用能标志名称2','VO-0002','承压名称2',4153.75,6876.89,302.99,'EC-0002','用电客户状态名称2','2025-01-20 08:00:00','2025-03-11 17:00:00','2025-02-14 17:00:00','2024-05-11 05:00:00','LO-0002','锁定状态名称2','最近一次停电原因_2','ST-0002','停供标志名称2','ST-0002','停供方式名称2','RC-0002','复供方式名称2','2024-11-28 10:00:00','CR-0002','催费责任人班组名称2','CH-0002','核算责任人班组名称2','CH-0002','用电检查人员名称2','CR0002','催费责任人名称2','CHK0002','核算责任人名称2','发电客户标志_2','充电桩客户标志_2','是否敏感客户_2','是否分割开票客户_2','是否特定开票客户_2','2024-03-30 04:00:00','2024-12-24 00:00:00','停用','历史数据 HT、_2','2025-02-26 18:00:00');
/*!40000 ALTER TABLE `dim_cst_elec_cons_cust_his` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_elec_stat_resrc_standbk`
--

DROP TABLE IF EXISTS `dim_cst_elec_stat_resrc_standbk`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_elec_stat_resrc_standbk` (
  `substation_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `main_chg_num` double DEFAULT NULL,
  `main_chg_cap` double DEFAULT NULL,
  `org_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `org_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `substation_addr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `substation_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `substation_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_st_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_st_dsc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `serv_type_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `serv_type_dsc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eff_dt` datetime DEFAULT NULL,
  `volt_lvl_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_lvl_dsc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pms_substation_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_tm` datetime DEFAULT NULL,
  PRIMARY KEY (`substation_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_elec_stat_resrc_standbk`
--

LOCK TABLES `dim_cst_elec_stat_resrc_standbk` WRITE;
/*!40000 ALTER TABLE `dim_cst_elec_stat_resrc_standbk` DISABLE KEYS */;
INSERT INTO `dim_cst_elec_stat_resrc_standbk` VALUES ('SUB0001',4294.24,9434.78,'OR-0001','管理单位名称1','省份名称1','地市名称1','广州市天河区zz路3号','SU-0001','变电站名称1','启用','正常','服务种类代码_1','服务种类描述_1','2024-08-19 16:00:00','承压代码_1','承压描述_1','PMS0001','2024-08-15 12:00:00'),('SUB0002',1308.41,1263.17,'OR-0002','管理单位名称2','省份名称2','地市名称2','北京市朝阳区xx路1号','SU-0002','变电站名称2','启用','激活','服务种类代码_2','服务种类描述_2','2024-09-19 02:00:00','承压代码_2','承压描述_2','PMS0002','2024-04-06 17:00:00'),('SUB0003',1434.18,4654.52,'OR-0003','管理单位名称3','省份名称3','地市名称3','深圳市南山区aa路4号','SU-0003','变电站名称3','启用','启用','服务种类代码_3','服务种类描述_3','2024-04-24 14:00:00','承压代码_3','承压描述_3','PMS0003','2024-06-13 21:00:00');
/*!40000 ALTER TABLE `dim_cst_elec_stat_resrc_standbk` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_gen_elec_cons_dev`
--

DROP TABLE IF EXISTS `dim_cst_gen_elec_cons_dev`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_gen_elec_cons_dev` (
  `id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `gen_elec_cons_dev_id` int DEFAULT NULL,
  `cust_id` int DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plant_id` int DEFAULT NULL,
  `dev_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rv_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rv_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pwr` double DEFAULT NULL,
  `t_pwr` double DEFAULT NULL,
  `t_num` int DEFAULT NULL,
  `dev_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_gen_elec_cons_dev`
--

LOCK TABLES `dim_cst_gen_elec_cons_dev` WRITE;
/*!40000 ALTER TABLE `dim_cst_gen_elec_cons_dev` DISABLE KEYS */;
INSERT INTO `dim_cst_gen_elec_cons_dev` VALUES ('ID0001',363668,206723,'CU-0001','AP-0001',445377,'DE-0001','设备类型名称1','设备名称1','设备型号_1','RV-0001','电压名称1',9850.44,652.74,378802,'DE-0001','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-09-11 09:00:00'),('ID0002',625469,798358,'CU-0002','AP-0002',505919,'DE-0002','设备类型名称2','设备名称2','设备型号_2','RV-0002','电压名称2',5730.37,166.61,641584,'DE-0002','省份名称2','地市名称2','MG-0002','管理单位名称2','2024-03-02 01:00:00'),('ID0003',444627,705085,'CU-0003','AP-0003',248996,'DE-0003','设备类型名称3','设备名称3','设备型号_3','RV-0003','电压名称3',5734.24,441.02,883193,'DE-0003','省份名称3','地市名称3','MG-0003','管理单位名称3','2025-04-05 11:00:00');
/*!40000 ALTER TABLE `dim_cst_gen_elec_cons_dev` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_gpc`
--

DROP TABLE IF EXISTS `dim_cst_gpc`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_gpc` (
  `cust_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `gpc_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chkr_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `orig_cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_srv_addr_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bp_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_cons_cust_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plant_type_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plant_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gc_stat_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gc_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gc_type_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gc_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `taxpayer_type_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `taxpayer_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gc_ctrt_cap` double DEFAULT NULL,
  `inst_cap` double DEFAULT NULL,
  `accs_cap` double DEFAULT NULL,
  `accs_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accs_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_cyc_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_cyc_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_loc_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_loc_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_pscateg_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_pscateg_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pv_paflag_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pv_paflag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `grid_volt_lv_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `grid_volt_lv_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_consp_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_consp_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_alow_flag_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_alow_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_alow_flag_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_alow_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_alow_flag_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_alow_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cntrl_alow_model_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cntrl_alow_model_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cls_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `impt_lv_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `impt_lv_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `urbanrural_categ_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `urbanrural_categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_categ_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dereg_attr_cls_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dereg_attr_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lock_stat_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lock_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tax_rate_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tax_rate_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `alow_plcy` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_addr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_date` datetime DEFAULT NULL,
  `cncl_date` datetime DEFAULT NULL,
  `creat_date` datetime DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `last_insp_date` datetime DEFAULT NULL,
  `billing_unit_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mr_unit_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ppy_auth_flag_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ppy_auth_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_calc_pic_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_calc_pic_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `longitude` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `latitude` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_sta_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `resrc_supl_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `resrc_supl_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `resrc_supl_stat_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `resrc_supl_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `publ_clg_flag_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `publ_clg_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_stacap` double DEFAULT NULL,
  `det_addr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_prov_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_city_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_county_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_county_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_st_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_st_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_neighbor_comm_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_neighbor_comm_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_rd_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_rd_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_cmny_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_regn_cmny_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  `der_pv_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `der_pv_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`cust_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_gpc`
--

LOCK TABLES `dim_cst_gpc` WRITE;
/*!40000 ALTER TABLE `dim_cst_gpc` DISABLE KEYS */;
INSERT INTO `dim_cst_gpc` VALUES ('CUS0001','GPC0001','CU-0001','发电客户名称1','CH-0001','OR-0001','BUS0001','BP0001','ELE0001','PL-0001','电站类型名称1','GC-0001','发电客户状态名称1','GC-0001','发电客户类型名称(01','TA-0001','纳税人类型名称1',4381.48,4830.76,7909.53,'AC-0001','接入方式名称1','CH-0001','检查周期名称1','IN-0001','安装位置名称1','CU-0001','客户电源类别名称1','PV-0001','光伏扶贫标志名称1','GR-0001','并网承压等级名称1','GE-0001','发电方式名称1','E-0001','能源消纳方式名称1','PR-0001','省级补助标志名称1','CI-0001','市级补助标志名称1','CO-0001','县级补助标志名称1','IN-0001','投资模式名称1','CN-0001','中央补助模式名称1','MG-0001','管理单位名称1','IN-0001','行业分类名称1','IM-0001','重要性等级名称1','UR-0001','城乡类别名称1','CU-0001','客户类别名称1','DE-0001','市场化属性分类名称1','LO-0001','锁定状态名称1','TA-0001','税率名称1','补贴政策_1','杭州市西湖区bb路5号','2024-10-19 09:00:00','2025-02-24 09:00:00','2025-02-24 22:00:00','2024-03-17 12:00:00','2024-06-23 06:00:00','BI-0001','MR-0001','PP-0001','户主认证标志名称1','CHK0001','核算责任人名称1','坐标经度_1','坐标纬度_1','DIS0001','RE-0001','配送站名称1','RE-0001','配送站状态名称1','PU-0001','公专标志名称1',8526.89,'深圳市南山区aa路4号','ADM0001','AD-0001','行政区域省名称1','AD-0001','行政区域市名称1','AD-0001','行政区域区县名称1','AD-0001','行政区域街道名称1','AD-0001','行政区域社区名称1','AD-0001','行政区域道路名称1','AD-0001','行政区域小区名称1','省份名称1','地市名称1','2024-02-10 08:00:00','分布式光伏分类_1','分布式光伏分类名称1'),('CUS0002','GPC0002','CU-0002','发电客户名称2','CH-0002','OR-0002','BUS0002','BP0002','ELE0002','PL-0002','电站类型名称2','GC-0002','发电客户状态名称2','GC-0002','发电客户类型名称(02','TA-0002','纳税人类型名称2',7452.34,5170.74,4930.76,'AC-0002','接入方式名称2','CH-0002','检查周期名称2','IN-0002','安装位置名称2','CU-0002','客户电源类别名称2','PV-0002','光伏扶贫标志名称2','GR-0002','并网承压等级名称2','GE-0002','发电方式名称2','E-0002','能源消纳方式名称2','PR-0002','省级补助标志名称2','CI-0002','市级补助标志名称2','CO-0002','县级补助标志名称2','IN-0002','投资模式名称2','CN-0002','中央补助模式名称2','MG-0002','管理单位名称2','IN-0002','行业分类名称2','IM-0002','重要性等级名称2','UR-0002','城乡类别名称2','CU-0002','客户类别名称2','DE-0002','市场化属性分类名称2','LO-0002','锁定状态名称2','TA-0002','税率名称2','补贴政策_2','北京市朝阳区xx路1号','2024-05-29 13:00:00','2024-01-28 17:00:00','2024-10-07 23:00:00','2024-09-06 15:00:00','2024-03-28 01:00:00','BI-0002','MR-0002','PP-0002','户主认证标志名称2','CHK0002','核算责任人名称2','坐标经度_2','坐标纬度_2','DIS0002','RE-0002','配送站名称2','RE-0002','配送站状态名称2','PU-0002','公专标志名称2',2671.09,'上海市浦东新区yy路2号','ADM0002','AD-0002','行政区域省名称2','AD-0002','行政区域市名称2','AD-0002','行政区域区县名称2','AD-0002','行政区域街道名称2','AD-0002','行政区域社区名称2','AD-0002','行政区域道路名称2','AD-0002','行政区域小区名称2','省份名称2','地市名称2','2024-06-30 00:00:00','分布式光伏分类_2','分布式光伏分类名称2'),('CUS0003','GPC0003','CU-0003','发电客户名称3','CH-0003','OR-0003','BUS0003','BP0003','ELE0003','PL-0003','电站类型名称3','GC-0003','发电客户状态名称3','GC-0003','发电客户类型名称(03','TA-0003','纳税人类型名称3',1762.02,87.79,7963.15,'AC-0003','接入方式名称3','CH-0003','检查周期名称3','IN-0003','安装位置名称3','CU-0003','客户电源类别名称3','PV-0003','光伏扶贫标志名称3','GR-0003','并网承压等级名称3','GE-0003','发电方式名称3','E-0003','能源消纳方式名称3','PR-0003','省级补助标志名称3','CI-0003','市级补助标志名称3','CO-0003','县级补助标志名称3','IN-0003','投资模式名称3','CN-0003','中央补助模式名称3','MG-0003','管理单位名称3','IN-0003','行业分类名称3','IM-0003','重要性等级名称3','UR-0003','城乡类别名称3','CU-0003','客户类别名称3','DE-0003','市场化属性分类名称3','LO-0003','锁定状态名称3','TA-0003','税率名称3','补贴政策_3','广州市天河区zz路3号','2025-03-10 09:00:00','2024-07-17 23:00:00','2024-10-15 09:00:00','2024-03-25 21:00:00','2025-04-24 16:00:00','BI-0003','MR-0003','PP-0003','户主认证标志名称3','CHK0003','核算责任人名称3','坐标经度_3','坐标纬度_3','DIS0003','RE-0003','配送站名称3','RE-0003','配送站状态名称3','PU-0003','公专标志名称3',6255.78,'上海市浦东新区yy路2号','ADM0003','AD-0003','行政区域省名称3','AD-0003','行政区域市名称3','AD-0003','行政区域区县名称3','AD-0003','行政区域街道名称3','AD-0003','行政区域社区名称3','AD-0003','行政区域道路名称3','AD-0003','行政区域小区名称3','省份名称3','地市名称3','2024-05-04 13:00:00','分布式光伏分类_3','分布式光伏分类名称3');
/*!40000 ALTER TABLE `dim_cst_gpc` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_inst_elec_cons`
--

DROP TABLE IF EXISTS `dim_cst_inst_elec_cons`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_inst_elec_cons` (
  `inst_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `inst_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `billing_unit_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mr_unit_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `loc_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_mgt_order_sn` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `creat_date` datetime DEFAULT NULL,
  `srv_kind` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mr_sn` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invalid_date` datetime DEFAULT NULL,
  `lc_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `can_be_stop_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `vrtl_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sw_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_usage_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tl_share_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tl_billing_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exc_point_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sys_ngmode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ll_share_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ll_billing_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rp_ll_calc_val` double DEFAULT NULL,
  `ec_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ap_ll_calc_val` double DEFAULT NULL,
  `pt_rp_inc_loss` double DEFAULT NULL,
  `pt_ap_inc_loss` double DEFAULT NULL,
  `cust_agrt_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ll_share_agrt_val` double DEFAULT NULL,
  `pi_los_calc_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_loss_agrt_val` double DEFAULT NULL,
  `prem_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_cond_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `response_load` double DEFAULT NULL,
  `rt_resp_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attach_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_stat_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_lv` int DEFAULT NULL,
  `inst_cls_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_char_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_char_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wire_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wire_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_cond_flag_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_cond_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_md_cls_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_md_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_cap` double DEFAULT NULL,
  `inst_affil_side_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_affil_side_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prtp_pf_calc_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prtp_pf_calc_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dereg_type_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dereg_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_calc_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_calc_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fr_ddct_flag_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fr_ddct_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fqr_val` double DEFAULT NULL,
  `exec_seq` int DEFAULT NULL,
  `inst_addr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cntrl_sta_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cntrl_sta_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_sta_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_sta_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`inst_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_inst_elec_cons`
--

LOCK TABLES `dim_cst_inst_elec_cons` WRITE;
/*!40000 ALTER TABLE `dim_cst_inst_elec_cons` DISABLE KEYS */;
INSERT INTO `dim_cst_inst_elec_cons` VALUES ('INS0001','安装点名称1','CU-0001','CUS0001','IN-0001','BI-0001','MR-0001','MG-0001','管理单位名称1','省份名称1','地市名称1','LOC0001','安装点管理顺序号_1','2025-01-16 11:00:00','服务种类_1','抄表顺序号_1','承压_1','行业分类_1','2024-04-18 15:00:00','安装负控标志_1','可停供标志_1','2024-06-08 21:00:00','虚拟标志_1','SW-0001','安装点用途分类_1','变损分摊标志_1','变损计费标志_1','交换点分类_1','系统中性点接地方_1','线损分摊标志_1','线损计费标志_1',8696.05,'用能类别_1',861.98,5385.02,8607.48,'CUS0001',995.74,'PI-0001',195.79,'PRE0001','具备装表条件标志_1',1779.94,'实时响应标志_1','SRV0001','ATT0001','IOT0001','IO-0001','IN-0001','计量点状态名称1',767007,'IN-0001','计量点分类名称1','IN-0001','计量点性质名称1','ME-0001','计量方式名称1','WI-0001','接线方式名称1','VO-0001','电压等级名称1','ME-0001','是否装表名称1','E-0001','计量装置分类名称1',9667.18,'IN-0001','计量点所属侧名称1','PR-0001','参与功率因数计算方式1','DE-0001','市场化类型名称1','E-0001','电量计算方式名称1','FR-0001','定比扣减标志名称1',3120.39,864259,'上海市浦东新区yy路2号','CNT0001','计量点所属变电站名称1','PIP0001','计量点所属线路名称1','DIS0001','计量点所属台区名称1','2024-01-16 02:00:00'),('INS0002','安装点名称2','CU-0002','CUS0002','IN-0002','BI-0002','MR-0002','MG-0002','管理单位名称2','省份名称2','地市名称2','LOC0002','安装点管理顺序号_2','2024-12-22 23:00:00','服务种类_2','抄表顺序号_2','承压_2','行业分类_2','2025-03-14 00:00:00','安装负控标志_2','可停供标志_2','2024-01-16 10:00:00','虚拟标志_2','SW-0002','安装点用途分类_2','变损分摊标志_2','变损计费标志_2','交换点分类_2','系统中性点接地方_2','线损分摊标志_2','线损计费标志_2',6977.06,'用能类别_2',356.87,6781.27,305.89,'CUS0002',5850.58,'PI-0002',2197.46,'PRE0002','具备装表条件标志_2',9797.51,'实时响应标志_2','SRV0002','ATT0002','IOT0002','IO-0002','IN-0002','计量点状态名称2',427046,'IN-0002','计量点分类名称2','IN-0002','计量点性质名称2','ME-0002','计量方式名称2','WI-0002','接线方式名称2','VO-0002','电压等级名称2','ME-0002','是否装表名称2','E-0002','计量装置分类名称2',6257.58,'IN-0002','计量点所属侧名称2','PR-0002','参与功率因数计算方式2','DE-0002','市场化类型名称2','E-0002','电量计算方式名称2','FR-0002','定比扣减标志名称2',5591.61,49308,'北京市朝阳区xx路1号','CNT0002','计量点所属变电站名称2','PIP0002','计量点所属线路名称2','DIS0002','计量点所属台区名称2','2025-01-03 08:00:00'),('INS0003','安装点名称3','CU-0003','CUS0003','IN-0003','BI-0003','MR-0003','MG-0003','管理单位名称3','省份名称3','地市名称3','LOC0003','安装点管理顺序号_3','2025-02-27 20:00:00','服务种类_3','抄表顺序号_3','承压_3','行业分类_3','2025-03-07 18:00:00','安装负控标志_3','可停供标志_3','2024-12-10 12:00:00','虚拟标志_3','SW-0003','安装点用途分类_3','变损分摊标志_3','变损计费标志_3','交换点分类_3','系统中性点接地方_3','线损分摊标志_3','线损计费标志_3',4984.49,'用能类别_3',4.66,4374.45,4015.4,'CUS0003',9237.74,'PI-0003',1746.33,'PRE0003','具备装表条件标志_3',8672.02,'实时响应标志_3','SRV0003','ATT0003','IOT0003','IO-0003','IN-0003','计量点状态名称3',857068,'IN-0003','计量点分类名称3','IN-0003','计量点性质名称3','ME-0003','计量方式名称3','WI-0003','接线方式名称3','VO-0003','电压等级名称3','ME-0003','是否装表名称3','E-0003','计量装置分类名称3',3337.67,'IN-0003','计量点所属侧名称3','PR-0003','参与功率因数计算方式3','DE-0003','市场化类型名称3','E-0003','电量计算方式名称3','FR-0003','定比扣减标志名称3',940.57,122578,'北京市朝阳区xx路1号','CNT0003','计量点所属变电站名称3','PIP0003','计量点所属线路名称3','DIS0003','计量点所属台区名称3','2024-01-14 14:00:00');
/*!40000 ALTER TABLE `dim_cst_inst_elec_cons` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_it`
--

DROP TABLE IF EXISTS `dim_cst_it`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_it` (
  `dev_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `categ_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_type_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `theory_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `theory_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rv_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rv_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `insul_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `insul_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wnd_config` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `made_std` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pf_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pf_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rated_freq` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rated_frstside_cur_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rated_frstside_cur_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rated_scnd_cur_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rated_scnd_cur_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ta_accu_lv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tv_accu_lv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ta_tr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ta_tr_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tv_tr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tv_tr_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cap` double DEFAULT NULL,
  `t_aturns` double DEFAULT NULL,
  `tv_turns` double DEFAULT NULL,
  `wire_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wire_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ta_rated_scnd_load_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ta_rated_scnd_load_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tv_rated_scnd_load_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tv_rated_scnd_load_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tvlight_load_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tvlight_load_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `t_alight_load_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `t_alight_load_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `enc_mode_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `enc_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rated_frstside_cur_amp_times` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_stat_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phase_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phase_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bar_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mfr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estab_arch_date` datetime DEFAULT NULL,
  `pile_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rated_frst_volt` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rated_scnd_volt` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_cyc` double DEFAULT NULL,
  `prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`dev_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_it`
--

LOCK TABLES `dim_cst_it` WRITE;
/*!40000 ALTER TABLE `dim_cst_it` DISABLE KEYS */;
INSERT INTO `dim_cst_it` VALUES ('DEV0001','CA-0001','类别名称1','DE-0001','类型名称1','TH-0001','原理名称1','RV-0001','额定电压名称1','IN-0001','绝缘方式名称1','绕组配置_1','制造标准_1','PF-0001','功率因数名称1','额定频率_1','RA-0001','额定一次电流名称1','RA-0001','额定二次电流名称1','TA准确度等级_1','TV准确度等级_1','TA变比_1','TA变比名称1','TV变比_1','TV变比名称1',7015.59,8141.18,425.76,'WI-0001','接线方式名称1','TA-0001','TA额定二次负荷名称1','TV-0001','TV额定二次负荷名称1','TV-0001','TV轻载负荷名称1','T-0001','TA轻载负荷1','EN-0001','加密方式名称1','2025-04-11 00:00:00','DE-0001','设备状态名称1','PH-0001','相别名称1','BA-0001','AS-0001','FT-0001','MF-0001','型号_1','2024-10-11 15:00:00','PI-0001','额定一次电压_1','额定二次电压_1',1127.61,'省份名称1','地市名称1','MG-0001','管理单位名称1','2025-05-10 13:00:00'),('DEV0002','CA-0002','类别名称2','DE-0002','类型名称2','TH-0002','原理名称2','RV-0002','额定电压名称2','IN-0002','绝缘方式名称2','绕组配置_2','制造标准_2','PF-0002','功率因数名称2','额定频率_2','RA-0002','额定一次电流名称2','RA-0002','额定二次电流名称2','TA准确度等级_2','TV准确度等级_2','TA变比_2','TA变比名称2','TV变比_2','TV变比名称2',8083.5,2261.13,8905.96,'WI-0002','接线方式名称2','TA-0002','TA额定二次负荷名称2','TV-0002','TV额定二次负荷名称2','TV-0002','TV轻载负荷名称2','T-0002','TA轻载负荷2','EN-0002','加密方式名称2','2024-08-29 00:00:00','DE-0002','设备状态名称2','PH-0002','相别名称2','BA-0002','AS-0002','FT-0002','MF-0002','型号_2','2024-11-25 14:00:00','PI-0002','额定一次电压_2','额定二次电压_2',4612.8,'省份名称2','地市名称2','MG-0002','管理单位名称2','2024-11-05 15:00:00'),('DEV0003','CA-0003','类别名称3','DE-0003','类型名称3','TH-0003','原理名称3','RV-0003','额定电压名称3','IN-0003','绝缘方式名称3','绕组配置_3','制造标准_3','PF-0003','功率因数名称3','额定频率_3','RA-0003','额定一次电流名称3','RA-0003','额定二次电流名称3','TA准确度等级_3','TV准确度等级_3','TA变比_3','TA变比名称3','TV变比_3','TV变比名称3',5265.73,139.2,8830.02,'WI-0003','接线方式名称3','TA-0003','TA额定二次负荷名称3','TV-0003','TV额定二次负荷名称3','TV-0003','TV轻载负荷名称3','T-0003','TA轻载负荷3','EN-0003','加密方式名称3','2024-12-20 00:00:00','DE-0003','设备状态名称3','PH-0003','相别名称3','BA-0003','AS-0003','FT-0003','MF-0003','型号_3','2024-05-10 10:00:00','PI-0003','额定一次电压_3','额定二次电压_3',830.28,'省份名称3','地市名称3','MG-0003','管理单位名称3','2024-10-15 03:00:00');
/*!40000 ALTER TABLE `dim_cst_it` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_it_run`
--

DROP TABLE IF EXISTS `dim_cst_it_run`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_it_run` (
  `it_logic_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `it_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_winding_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `categ_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `categ_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_spcl_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_spcl_flag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phase_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phase_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cur_rto` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cur_rto_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `usage_cur_tr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `usage_cur_tr_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_cyc` double DEFAULT NULL,
  `dev_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_date` datetime DEFAULT NULL,
  `last_insp_date` datetime DEFAULT NULL,
  `loc_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `share_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `share_flag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `share_it_logic_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prop_own_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prop_own_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`it_logic_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_it_run`
--

LOCK TABLES `dim_cst_it_run` WRITE;
/*!40000 ALTER TABLE `dim_cst_it_run` DISABLE KEYS */;
INSERT INTO `dim_cst_it_run` VALUES ('IT0001','IT0001','ME-0001','IN-0001','安装方式名称1','CA-0001','类别名称1','计量专用标志_1','计量专用标志名称1','PH-0001','相别名称1','在用电流变比_1','在用电流变比名称1','在用电压变比_1','在用电压变比名称1',3607.26,'设备描述测试数据1','DE-0001','DE-0001','设备类型名称1','2024-10-23 12:00:00','2024-09-08 20:00:00','LOC0001','共用标志_1','共用标志名称1','SHA0001','INS0001','PR-0001','产权归属名称1','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-09-13 16:00:00'),('IT0002','IT0002','ME-0002','IN-0002','安装方式名称2','CA-0002','类别名称2','计量专用标志_2','计量专用标志名称2','PH-0002','相别名称2','在用电流变比_2','在用电流变比名称2','在用电压变比_2','在用电压变比名称2',9439.31,'设备描述测试数据2','DE-0002','DE-0002','设备类型名称2','2025-01-06 19:00:00','2024-11-07 12:00:00','LOC0002','共用标志_2','共用标志名称2','SHA0002','INS0002','PR-0002','产权归属名称2','省份名称2','地市名称2','MG-0002','管理单位名称2','2025-01-28 16:00:00'),('IT0003','IT0003','ME-0003','IN-0003','安装方式名称3','CA-0003','类别名称3','计量专用标志_3','计量专用标志名称3','PH-0003','相别名称3','在用电流变比_3','在用电流变比名称3','在用电压变比_3','在用电压变比名称3',838.29,'设备描述测试数据3','DE-0003','DE-0003','设备类型名称3','2024-11-29 12:00:00','2025-01-24 14:00:00','LOC0003','共用标志_3','共用标志名称3','SHA0003','INS0003','PR-0003','产权归属名称3','省份名称3','地市名称3','MG-0003','管理单位名称3','2025-03-12 19:00:00');
/*!40000 ALTER TABLE `dim_cst_it_run` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_meter`
--

DROP TABLE IF EXISTS `dim_cst_meter`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_meter` (
  `meter_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `categ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `categ_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_type_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cali_cur` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wire_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ap_accu_lv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rp_accu_lv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_disp_digit` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `time_sec_digit` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnst` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ap_pulse_const` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rp_pulse_const` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `self_rto` double DEFAULT NULL,
  `overload_times` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reg_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `relay_contact` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accs_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `read_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_usage` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rate` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `multirate_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `card_meter_trip_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pulse_categ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meas_theory` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `made_std` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_meas_disp` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `freq` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prvnt_rev_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bidi_meter_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prepay_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `disp_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hrmnc_meter_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dmd_meter_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hw_ver` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `r_s485_line_num` int DEFAULT NULL,
  `baudrate` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_prot` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_intfc_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sprt_mod_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pwr_off_mrflag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cur_loss_judge` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_loss_judge` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rev_phase_seq_judge` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pwr_over_lmt_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_curve` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ir_mr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `carrier_wave_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mfr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_model` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estab_arch_date` datetime DEFAULT NULL,
  `pile_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_chk_time` datetime DEFAULT NULL,
  `pro_spec_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pro_spec_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pro_spec_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bar_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pr_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pr_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pr_org` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pur_batch` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arr_batch_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_date` datetime DEFAULT NULL,
  `warranty_prd` double DEFAULT NULL,
  `mtrl_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spec_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spec_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `box_bar_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estab_arch_type_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estab_arch_type_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_date` datetime DEFAULT NULL,
  `last_chk_date` datetime DEFAULT NULL,
  `rmv_date` datetime DEFAULT NULL,
  `retr_date` datetime DEFAULT NULL,
  `pro_spec_id_temp` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pro_spec_no_temp` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pro_spec_name_temp` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `other_dev_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `order_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `order_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bid_batch_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bid_lot_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arr_batch_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `creator` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `first_veri_date` datetime DEFAULT NULL,
  `old_new_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comps_date` datetime DEFAULT NULL,
  `wh_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_addr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_lv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_cls` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_area` double DEFAULT NULL,
  `wh_desc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cstr_area` double DEFAULT NULL,
  `run_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pic` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_stor_cap_area` double DEFAULT NULL,
  `inst_lv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `auto_dev_mfr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `affil_inst_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_sys_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_area_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_area_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_area_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_area_cap` double DEFAULT NULL,
  `wh_area_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_area_categ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_area_area` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `func_categ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prfs_categ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cab_asset_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cab_dev_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_area_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_area_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_area_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_area_categ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_area_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_area_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_loc_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_loc_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_loc_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_loc_actl_sn` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_loc_addr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_loc_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_dev_num` int DEFAULT NULL,
  `stor_loc_bar_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_loc_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_chg_time` datetime DEFAULT NULL,
  `produce_mf_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `produce_mf_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `unified_soc_credit_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`meter_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_meter`
--

LOCK TABLES `dim_cst_meter` WRITE;
/*!40000 ALTER TABLE `dim_cst_meter` DISABLE KEYS */;
INSERT INTO `dim_cst_meter` VALUES ('MET0001','类别_1','类别名称1','类型_1','类型名称1','额定电压_1','标定电流_1','接线方式_1','有功准确度等级_1','无功准确度等级_1','电能表显示位数_1','2024-05-27 00:00:00','常数_1','有功脉冲常数_1','无功脉冲常数_1',1976.88,'2024-02-07 00:00:00','计度器方式_1','继电器接点_1','接入方式_1','指示数类型_1','使用用途_1','费率_1','复费率表标志_1','卡表跳闸方式_1','脉冲类别_1','测量原理_1','制造标准_1','电测量显示_1','频率_1','阻逆标志_1','双向计量标志_1','预付费标志_1','显示方式_1','谐波计量标志_1','需量表标志_1','硬件版本_1',415660,'波特率_1','通讯方式_1','通讯规约_1','通讯接口类型_1','支持模块标志_1','停电抄表标志_1','失流判断_1','失压判断_1','逆相序判断_1','超功率_1','负荷曲线_1','红外抄表_1','注销','CAR0001','AS-0001','FT-0001','MF-0001','型号_1','2025-04-19 14:00:00','PI-0001','2024-03-12 17:00:00','PRO0001','PR-0001','设备码名称1','BA-0001','PR-0001','产权名称1','华能集团','采购批次_1','ARR0001','CTR0001','2024-12-24 07:00:00',7361.63,'MT-0001','SP-0001','规格名称1','BO-0001','ES-0001','建档类型名称1','2024-08-23 06:00:00','2024-05-28 07:00:00','2024-04-22 15:00:00','2024-01-08 07:00:00','品规标识_1','PR-0001','品规名称1','OTH0001','ORD0001','OR-0001','CT-0001','BID0001','BI-0001','AR-0001','创建人_1','2025-02-07 05:00:00','新旧标志_1','2024-02-24 14:00:00','WH0001','WH-0001','库房名称1','上海市浦东新区yy路2号','启用','库房级别_1','库房分类_1',2748.66,'库房说明测试数据1',4696.2,'运转方式_1','责任人_1',8754.86,'机构级别_1','国家电投','所属机构名称1','WH-0001','WH0001','WH-0001','库区名称1',438.02,'停用','库区类别_1','库区面积_1','功能类别_1','国网电力公司','专业类别_1','CA-0001','CAB0001','STO0001','ST-0001','存放区名称1','存放区类别_1','存放区类型_1','注销','STO0001','ST-0001','储位名称1','储位实际顺序号_1','杭州市西湖区bb路5号','异常',659817,'ST-0001','储位类型_1','2024-01-02 14:00:00','PRO0001','生产厂家名称1','UN-0001','有效标志_1','正常','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-12-26 17:00:00'),('MET0002','类别_2','类别名称2','类型_2','类型名称2','额定电压_2','标定电流_2','接线方式_2','有功准确度等级_2','无功准确度等级_2','电能表显示位数_2','2025-02-06 00:00:00','常数_2','有功脉冲常数_2','无功脉冲常数_2',4315.23,'2025-02-06 00:00:00','计度器方式_2','继电器接点_2','接入方式_2','指示数类型_2','使用用途_2','费率_2','复费率表标志_2','卡表跳闸方式_2','脉冲类别_2','测量原理_2','制造标准_2','电测量显示_2','频率_2','阻逆标志_2','双向计量标志_2','预付费标志_2','显示方式_2','谐波计量标志_2','需量表标志_2','硬件版本_2',28178,'波特率_2','通讯方式_2','通讯规约_2','通讯接口类型_2','支持模块标志_2','停电抄表标志_2','失流判断_2','失压判断_2','逆相序判断_2','超功率_2','负荷曲线_2','红外抄表_2','启用','CAR0002','AS-0002','FT-0002','MF-0002','型号_2','2024-06-05 17:00:00','PI-0002','2025-03-18 09:00:00','PRO0002','PR-0002','设备码名称2','BA-0002','PR-0002','产权名称2','南方电网公司','采购批次_2','ARR0002','CTR0002','2024-09-23 13:00:00',5791.95,'MT-0002','SP-0002','规格名称2','BO-0002','ES-0002','建档类型名称2','2024-02-27 13:00:00','2024-03-02 21:00:00','2024-02-17 04:00:00','2025-02-04 01:00:00','品规标识_2','PR-0002','品规名称2','OTH0002','ORD0002','OR-0002','CT-0002','BID0002','BI-0002','AR-0002','创建人_2','2024-01-15 12:00:00','新旧标志_2','2024-07-20 08:00:00','WH0002','WH-0002','库房名称2','深圳市南山区aa路4号','启用','库房级别_2','库房分类_2',4386.2,'库房说明测试数据2',9699.37,'运转方式_2','责任人_2',8270.47,'机构级别_2','国家电投','所属机构名称2','WH-0002','WH0002','WH-0002','库区名称2',7242.95,'激活','库区类别_2','库区面积_2','功能类别_2','大唐集团','专业类别_2','CA-0002','CAB0002','STO0002','ST-0002','存放区名称2','存放区类别_2','存放区类型_2','注销','STO0002','ST-0002','储位名称2','储位实际顺序号_2','上海市浦东新区yy路2号','激活',285780,'ST-0002','储位类型_2','2025-03-25 14:00:00','PRO0002','生产厂家名称2','UN-0002','有效标志_2','启用','省份名称2','地市名称2','MG-0002','管理单位名称2','2024-04-01 23:00:00'),('MET0003','类别_3','类别名称3','类型_3','类型名称3','额定电压_3','标定电流_3','接线方式_3','有功准确度等级_3','无功准确度等级_3','电能表显示位数_3','2024-04-18 00:00:00','常数_3','有功脉冲常数_3','无功脉冲常数_3',3077.91,'2024-12-08 00:00:00','计度器方式_3','继电器接点_3','接入方式_3','指示数类型_3','使用用途_3','费率_3','复费率表标志_3','卡表跳闸方式_3','脉冲类别_3','测量原理_3','制造标准_3','电测量显示_3','频率_3','阻逆标志_3','双向计量标志_3','预付费标志_3','显示方式_3','谐波计量标志_3','需量表标志_3','硬件版本_3',37849,'波特率_3','通讯方式_3','通讯规约_3','通讯接口类型_3','支持模块标志_3','停电抄表标志_3','失流判断_3','失压判断_3','逆相序判断_3','超功率_3','负荷曲线_3','红外抄表_3','异常','CAR0003','AS-0003','FT-0003','MF-0003','型号_3','2024-05-22 00:00:00','PI-0003','2024-05-24 02:00:00','PRO0003','PR-0003','设备码名称3','BA-0003','PR-0003','产权名称3','国网电力公司','采购批次_3','ARR0003','CTR0003','2024-04-19 02:00:00',4601.2,'MT-0003','SP-0003','规格名称3','BO-0003','ES-0003','建档类型名称3','2024-04-11 13:00:00','2024-03-17 08:00:00','2025-02-28 08:00:00','2025-02-04 22:00:00','品规标识_3','PR-0003','品规名称3','OTH0003','ORD0003','OR-0003','CT-0003','BID0003','BI-0003','AR-0003','创建人_3','2024-01-21 07:00:00','新旧标志_3','2024-06-17 19:00:00','WH0003','WH-0003','库房名称3','广州市天河区zz路3号','注销','库房级别_3','库房分类_3',9821.03,'库房说明测试数据3',1326.73,'运转方式_3','责任人_3',8166.84,'机构级别_3','南方电网公司','所属机构名称3','WH-0003','WH0003','WH-0003','库区名称3',2935.44,'停用','库区类别_3','库区面积_3','功能类别_3','国网电力公司','专业类别_3','CA-0003','CAB0003','STO0003','ST-0003','存放区名称3','存放区类别_3','存放区类型_3','正常','STO0003','ST-0003','储位名称3','储位实际顺序号_3','上海市浦东新区yy路2号','激活',340678,'ST-0003','储位类型_3','2024-07-22 20:00:00','PRO0003','生产厂家名称3','UN-0003','有效标志_3','异常','省份名称3','地市名称3','MG-0003','管理单位名称3','2024-10-11 06:00:00');
/*!40000 ALTER TABLE `dim_cst_meter` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_meter_box`
--

DROP TABLE IF EXISTS `dim_cst_meter_box`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_meter_box` (
  `dev_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `categ_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_type_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cap` double DEFAULT NULL,
  `box_row_num` double DEFAULT NULL,
  `col_num` double DEFAULT NULL,
  `sw_cur` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mtrl_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mtrl_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bar_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mfr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estab_arch_date` datetime DEFAULT NULL,
  `instal_date` datetime DEFAULT NULL,
  `dev_stat` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wire_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wire_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_digit` double DEFAULT NULL,
  `row_col_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pro_spec_id` int DEFAULT NULL,
  `pro_spec_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pro_spec_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pr_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pr_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pr_org` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pur_batch` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arr_batch_id` int DEFAULT NULL,
  `ctrt_id` int DEFAULT NULL,
  `fty_date` datetime DEFAULT NULL,
  `mtrl_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spec_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spec_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wh_area_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_area_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stor_loc_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `box_bar_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estab_arch_type_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estab_arch_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_chk_date` datetime DEFAULT NULL,
  `rmv_date` datetime DEFAULT NULL,
  `retr_date` datetime DEFAULT NULL,
  `pro_spec_id_temp` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pro_spec_no_temp` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pro_spec_name_temp` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `other_dev_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `order_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `order_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bid_lot_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arr_batch_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `creator` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `first_veri_date` datetime DEFAULT NULL,
  `old_new_flag_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `old_new_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`dev_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_meter_box`
--

LOCK TABLES `dim_cst_meter_box` WRITE;
/*!40000 ALTER TABLE `dim_cst_meter_box` DISABLE KEYS */;
INSERT INTO `dim_cst_meter_box` VALUES ('DEV0001','CA-0001','类别名称1','DE-0001','类型名称1',4475.57,3184.9,1085.6,'开关电流_1','材料类型_1','材料类型描述1','BA-0001','AS-0001','FT-0001','MF-0001','2024-02-05 11:00:00','2024-09-26 04:00:00','激活','设备状态描述1','接线方式_1','接线方式描述1',3903.39,'行数倒序测试数据1','安装模式_1','安装模式描述1',129920,'PR-0001','设备码名称1','PR-0001','产权名称1','华能集团','采购批次_1',17785,445843,'2025-03-01 18:00:00','MT-0001','SP-0001','规格名称1','WH0001','WH0001','STO0001','STO0001','BO-0001','ES-0001','建档类型名称1','2025-01-10 00:00:00','2025-03-04 10:00:00','2024-02-21 07:00:00','品规标识_1','PR-0001','品规名称1','OTH0001','ORD0001','OR-0001','CT-0001','BI-0001','AR-0001','创建人_1','2024-10-03 02:00:00','OL-0001','新旧标志名称1','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-04-10 07:00:00'),('DEV0002','CA-0002','类别名称2','DE-0002','类型名称2',5062.41,9549.14,3274.42,'开关电流_2','材料类型_2','材料类型描述2','BA-0002','AS-0002','FT-0002','MF-0002','2024-08-14 11:00:00','2024-09-24 19:00:00','激活','设备状态描述2','接线方式_2','接线方式描述2',182.54,'行数倒序测试数据2','安装模式_2','安装模式描述2',7922,'PR-0002','设备码名称2','PR-0002','产权名称2','国网电力公司','采购批次_2',225752,327103,'2025-03-31 11:00:00','MT-0002','SP-0002','规格名称2','WH0002','WH0002','STO0002','STO0002','BO-0002','ES-0002','建档类型名称2','2024-02-17 17:00:00','2024-08-03 16:00:00','2024-09-21 19:00:00','品规标识_2','PR-0002','品规名称2','OTH0002','ORD0002','OR-0002','CT-0002','BI-0002','AR-0002','创建人_2','2024-09-02 05:00:00','OL-0002','新旧标志名称2','省份名称2','地市名称2','MG-0002','管理单位名称2','2025-03-03 04:00:00'),('DEV0003','CA-0003','类别名称3','DE-0003','类型名称3',7359.26,1212.44,6543.09,'开关电流_3','材料类型_3','材料类型描述3','BA-0003','AS-0003','FT-0003','MF-0003','2024-06-14 12:00:00','2025-04-30 00:00:00','异常','设备状态描述3','接线方式_3','接线方式描述3',470.56,'行数倒序测试数据3','安装模式_3','安装模式描述3',85766,'PR-0003','设备码名称3','PR-0003','产权名称3','国网电力公司','采购批次_3',114034,667626,'2024-09-25 16:00:00','MT-0003','SP-0003','规格名称3','WH0003','WH0003','STO0003','STO0003','BO-0003','ES-0003','建档类型名称3','2024-02-11 06:00:00','2025-01-23 13:00:00','2025-03-04 15:00:00','品规标识_3','PR-0003','品规名称3','OTH0003','ORD0003','OR-0003','CT-0003','BI-0003','AR-0003','创建人_3','2024-05-18 12:00:00','OL-0003','新旧标志名称3','省份名称3','地市名称3','MG-0003','管理单位名称3','2025-04-28 03:00:00');
/*!40000 ALTER TABLE `dim_cst_meter_box` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_meter_run`
--

DROP TABLE IF EXISTS `dim_cst_meter_run`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_meter_run` (
  `meter_logic_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `meter_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ref_meter_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ref_meter_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comp_rto` double DEFAULT NULL,
  `mr_coef` double DEFAULT NULL,
  `ref_meter_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pi_caliber` double DEFAULT NULL,
  `chk_cyc` double DEFAULT NULL,
  `eqpt_desc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_date` datetime DEFAULT NULL,
  `last_chk_date` datetime DEFAULT NULL,
  `inst_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `share_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `share_met_logic_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `bar_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `categ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `categ_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_type_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cali_cur` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wire_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ap_accu_lv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rp_accu_lv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_disp_digit` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `time_sec_digit` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnst` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ap_pulse_const` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rp_pulse_const` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `self_rto` double DEFAULT NULL,
  `overload_times` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reg_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `relay_contact` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accs_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `read_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_usage` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rate` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `multirate_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `card_meter_trip_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pulse_categ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meas_theory` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `made_std` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_meas_disp` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `freq` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prvnt_rev_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bidi_meter_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prepay_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `disp_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hrmnc_meter_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dmd_meter_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hw_ver` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `r_s485_line_num` int DEFAULT NULL,
  `baudrate` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_prot` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_intfc_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sprt_mod_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pwr_off_mrflag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cur_loss_judge` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_loss_judge` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rev_phase_seq_judge` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pwr_over_lmt_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_curve` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ir_mr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `carrier_wave_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mfr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_model` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estab_arch_date` datetime DEFAULT NULL,
  `pile_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_chk_time` datetime DEFAULT NULL,
  `iot_acq_obj_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_in_meter_ctnr_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctnr_asset_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_categ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_instal_date` datetime DEFAULT NULL,
  `col_number` int DEFAULT NULL,
  `row_number` int DEFAULT NULL,
  `dev_fac_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `loc_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `loc_cls` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_srv_addr_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fac_dev_cls` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fac_dev_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_loc_addr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `longitude` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `latitude` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `altitude` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_acq_dev_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_asset_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acs_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `conn_harmonic_dev_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_side_sys_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_cls` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_date` datetime DEFAULT NULL,
  `trml_addr_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_loc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rem_comm_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_type_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acq_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_sta_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `orgn_iot_point_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`meter_logic_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_meter_run`
--

LOCK TABLES `dim_cst_meter_run` WRITE;
/*!40000 ALTER TABLE `dim_cst_meter_run` DISABLE KEYS */;
INSERT INTO `dim_cst_meter_run` VALUES ('MET0001','MET0001','REF0001','参考表计名称1',9513.76,2014.76,'参考表标志_1',9872.04,3360.57,'设备描述测试数据1','2024-12-03 18:00:00','2024-05-10 20:00:00','INS0001','CUS0001','DE-0001','共用标志_1','SHA0001','2024-04-30 03:00:00','BA-0001','类别_1','类别名称1','类型_1','类型名称1','额定电压_1','标定电流_1','接线方式_1','有功准确度等级_1','无功准确度等级_1','电能表显示位数_1','2024-05-18 00:00:00','常数_1','有功脉冲常数_1','无功脉冲常数_1',2214.24,'2024-11-06 00:00:00','计度器方式_1','继电器接点_1','接入方式_1','指示数类型_1','使用用途_1','费率_1','复费率表标志_1','卡表跳闸方式_1','脉冲类别_1','测量原理_1','制造标准_1','电测量显示_1','频率_1','阻逆标志_1','双向计量标志_1','预付费标志_1','显示方式_1','谐波计量标志_1','需量表标志_1','硬件版本_1',71509,'波特率_1','通讯方式_1','通讯规约_1','通讯接口类型_1','支持模块标志_1','停电抄表标志_1','失流判断_1','失压判断_1','逆相序判断_1','超功率_1','负荷曲线_1','红外抄表_1','启用','CAR0001','AS-0001','FT-0001','MF-0001','型号_1','2024-03-22 10:00:00','PI-0001','2024-04-06 10:00:00','IOT0001','DEV0001','CTN0001','DEV0001','设备类别_1','2025-02-23 19:00:00',520128,489904,'DEV0001','LOC0001','名称1','位置分类_1','SRV0001','BUS0001','设施设备分类_1','设施设备类型_1','杭州市西湖区bb路5号','坐标经度_1','坐标纬度_1','高程_1','INS0001','DE-0001','注销','交流采样标志_1','IO-0001','接谐波装置标志_1','客户侧系统标志_1','设备分类_1','2025-01-22 06:00:00','TR-0001','安装位置_1','是否远程通讯_1','IOT0001','启用','物联点名称1','IO-0001','物联点类型_1','物联点类型名称1','采集方式_1','DIS0001','OR-0001','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-11-09 13:00:00'),('MET0002','MET0002','REF0002','参考表计名称2',7616.88,4276.23,'参考表标志_2',871.55,9938.13,'设备描述测试数据2','2024-09-27 08:00:00','2025-04-01 07:00:00','INS0002','CUS0002','DE-0002','共用标志_2','SHA0002','2024-02-04 19:00:00','BA-0002','类别_2','类别名称2','类型_2','类型名称2','额定电压_2','标定电流_2','接线方式_2','有功准确度等级_2','无功准确度等级_2','电能表显示位数_2','2024-01-08 00:00:00','常数_2','有功脉冲常数_2','无功脉冲常数_2',6963.54,'2024-07-23 00:00:00','计度器方式_2','继电器接点_2','接入方式_2','指示数类型_2','使用用途_2','费率_2','复费率表标志_2','卡表跳闸方式_2','脉冲类别_2','测量原理_2','制造标准_2','电测量显示_2','频率_2','阻逆标志_2','双向计量标志_2','预付费标志_2','显示方式_2','谐波计量标志_2','需量表标志_2','硬件版本_2',664742,'波特率_2','通讯方式_2','通讯规约_2','通讯接口类型_2','支持模块标志_2','停电抄表标志_2','失流判断_2','失压判断_2','逆相序判断_2','超功率_2','负荷曲线_2','红外抄表_2','启用','CAR0002','AS-0002','FT-0002','MF-0002','型号_2','2025-02-10 21:00:00','PI-0002','2024-06-08 01:00:00','IOT0002','DEV0002','CTN0002','DEV0002','设备类别_2','2024-12-25 17:00:00',793837,69553,'DEV0002','LOC0002','名称2','位置分类_2','SRV0002','BUS0002','设施设备分类_2','设施设备类型_2','北京市朝阳区xx路1号','坐标经度_2','坐标纬度_2','高程_2','INS0002','DE-0002','异常','交流采样标志_2','IO-0002','接谐波装置标志_2','客户侧系统标志_2','设备分类_2','2024-06-10 19:00:00','TR-0002','安装位置_2','是否远程通讯_2','IOT0002','停用','物联点名称2','IO-0002','物联点类型_2','物联点类型名称2','采集方式_2','DIS0002','OR-0002','省份名称2','地市名称2','MG-0002','管理单位名称2','2024-05-23 01:00:00'),('MET0003','MET0003','REF0003','参考表计名称3',5410.56,1843.5,'参考表标志_3',4241.81,7582.9,'设备描述测试数据3','2024-08-08 16:00:00','2024-05-31 14:00:00','INS0003','CUS0003','DE-0003','共用标志_3','SHA0003','2024-07-02 15:00:00','BA-0003','类别_3','类别名称3','类型_3','类型名称3','额定电压_3','标定电流_3','接线方式_3','有功准确度等级_3','无功准确度等级_3','电能表显示位数_3','2024-06-25 00:00:00','常数_3','有功脉冲常数_3','无功脉冲常数_3',9941.42,'2024-03-19 00:00:00','计度器方式_3','继电器接点_3','接入方式_3','指示数类型_3','使用用途_3','费率_3','复费率表标志_3','卡表跳闸方式_3','脉冲类别_3','测量原理_3','制造标准_3','电测量显示_3','频率_3','阻逆标志_3','双向计量标志_3','预付费标志_3','显示方式_3','谐波计量标志_3','需量表标志_3','硬件版本_3',160047,'波特率_3','通讯方式_3','通讯规约_3','通讯接口类型_3','支持模块标志_3','停电抄表标志_3','失流判断_3','失压判断_3','逆相序判断_3','超功率_3','负荷曲线_3','红外抄表_3','停用','CAR0003','AS-0003','FT-0003','MF-0003','型号_3','2024-02-14 00:00:00','PI-0003','2025-01-14 00:00:00','IOT0003','DEV0003','CTN0003','DEV0003','设备类别_3','2024-12-08 00:00:00',532752,688212,'DEV0003','LOC0003','名称3','位置分类_3','SRV0003','BUS0003','设施设备分类_3','设施设备类型_3','杭州市西湖区bb路5号','坐标经度_3','坐标纬度_3','高程_3','INS0003','DE-0003','异常','交流采样标志_3','IO-0003','接谐波装置标志_3','客户侧系统标志_3','设备分类_3','2024-01-04 19:00:00','TR-0003','安装位置_3','是否远程通讯_3','IOT0003','启用','物联点名称3','IO-0003','物联点类型_3','物联点类型名称3','采集方式_3','DIS0003','OR-0003','省份名称3','地市名称3','MG-0003','管理单位名称3','2024-12-01 03:00:00');
/*!40000 ALTER TABLE `dim_cst_meter_run` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_mgt_org`
--

DROP TABLE IF EXISTS `dim_cst_mgt_org`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_mgt_org` (
  `mgt_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `srv_kind` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prnt_mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prnt_mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `valid_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_chn_abbr1` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sys_mgt_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `maj_attr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `update_time` datetime DEFAULT NULL,
  `prov_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnty_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnty_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `branch_off_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `branch_off_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pow_sup_sta_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pow_sup_sta_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name_auth` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name_auth` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`mgt_org_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_mgt_org`
--

LOCK TABLES `dim_cst_mgt_org` WRITE;
/*!40000 ALTER TABLE `dim_cst_mgt_org` DISABLE KEYS */;
INSERT INTO `dim_cst_mgt_org` VALUES ('MGT0001','服务种类_1','MG-0001','管理单位名称1','DI-0001','区域层级名称1','PR-0001','上级管理单位名称1','2024-03-13 21:00:00','有效标志_1','管理单位名称简称11','南方电网公司','SYS0001','专业属性_1','2024-07-19 22:00:00','PR-0001','省公司名称1','CI-0001','地市公司名称1','CN-0001','区县公司名称1','BR-0001','分公司名称1','PO-0001','供电所名称1','省份名称1','地市名称1','2024-01-24 06:00:00'),('MGT0002','服务种类_2','MG-0002','管理单位名称2','DI-0002','区域层级名称2','PR-0002','上级管理单位名称2','2024-06-30 13:00:00','有效标志_2','管理单位名称简称12','国家电投','SYS0002','专业属性_2','2025-05-11 19:00:00','PR-0002','省公司名称2','CI-0002','地市公司名称2','CN-0002','区县公司名称2','BR-0002','分公司名称2','PO-0002','供电所名称2','省份名称2','地市名称2','2024-07-22 02:00:00'),('MGT0003','服务种类_3','MG-0003','管理单位名称3','DI-0003','区域层级名称3','PR-0003','上级管理单位名称3','2024-03-20 12:00:00','有效标志_3','管理单位名称简称13','大唐集团','SYS0003','专业属性_3','2024-01-07 17:00:00','PR-0003','省公司名称3','CI-0003','地市公司名称3','CN-0003','区县公司名称3','BR-0003','分公司名称3','PO-0003','供电所名称3','省份名称3','地市名称3','2024-10-22 07:00:00');
/*!40000 ALTER TABLE `dim_cst_mgt_org` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_pay_acct`
--

DROP TABLE IF EXISTS `dim_cst_pay_acct`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_pay_acct` (
  `id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `pay_acct_id` int DEFAULT NULL,
  `chan_ctry_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bp_id` int DEFAULT NULL,
  `cust_id` int DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_acct_categ_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_acct_categ_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_acct_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_acct_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chan_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chan_acct` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acct_holder_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chan_acct_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `invalid_date` datetime DEFAULT NULL,
  `i_ban` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rela_pay_acct_id` int DEFAULT NULL,
  `valid_flag_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_flag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_pri` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acct_char_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acct_char_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_cap_rng_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_cap_rng_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acct_stat_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acct_stat_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_chan_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chan_cls_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `branch_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `creator` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `recent_updater` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `recent_chg_date` datetime DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_pay_acct`
--

LOCK TABLES `dim_cst_pay_acct` WRITE;
/*!40000 ALTER TABLE `dim_cst_pay_acct` DISABLE KEYS */;
INSERT INTO `dim_cst_pay_acct` VALUES ('ID0001',392854,'CH-0001',935537,168043,'CU-0001','PA-0001','支付账户类别名称1','PA-0001','渠道账户类型名称1','CH-0001','62220032683938184','账户持有人姓名/开户1','渠道账户的名称1','2025-02-08 05:00:00','2025-01-11 01:00:00','62220022846799195',201699,'VA-0001','有效标志名称1','付费优先级_1','AC-0001','账户性质名称1','CH-0001','收费资金范围名称1','AC-0001','账户状态名称1','支付渠道名称1','CH-0001','AP-0001','申请方式名称1','BR-0001','账户备注测试数据1','创建人员_1','2025-01-22 02:00:00','2024-06-07 00:00:00','2024-03-25 07:00:00','省份名称1','地市名称1','MG-0001','管理单位名称1','2025-01-28 12:00:00'),('ID0002',678931,'CH-0002',700867,533605,'CU-0002','PA-0002','支付账户类别名称2','PA-0002','渠道账户类型名称2','CH-0002','62220043293050210','账户持有人姓名/开户2','渠道账户的名称2','2024-10-21 19:00:00','2024-03-31 01:00:00','62220096492007276',822534,'VA-0002','有效标志名称2','付费优先级_2','AC-0002','账户性质名称2','CH-0002','收费资金范围名称2','AC-0002','账户状态名称2','支付渠道名称2','CH-0002','AP-0002','申请方式名称2','BR-0002','账户备注测试数据2','创建人员_2','2024-11-20 19:00:00','2025-01-12 00:00:00','2025-02-28 20:00:00','省份名称2','地市名称2','MG-0002','管理单位名称2','2024-11-06 02:00:00'),('ID0003',207151,'CH-0003',920225,874739,'CU-0003','PA-0003','支付账户类别名称3','PA-0003','渠道账户类型名称3','CH-0003','62220057415161311','账户持有人姓名/开户3','渠道账户的名称3','2024-05-18 15:00:00','2024-09-21 10:00:00','62220082954762145',144535,'VA-0003','有效标志名称3','付费优先级_3','AC-0003','账户性质名称3','CH-0003','收费资金范围名称3','AC-0003','账户状态名称3','支付渠道名称3','CH-0003','AP-0003','申请方式名称3','BR-0003','账户备注测试数据3','创建人员_3','2024-04-01 16:00:00','2025-04-05 00:00:00','2024-11-17 17:00:00','省份名称3','地市名称3','MG-0003','管理单位名称3','2024-11-02 12:00:00');
/*!40000 ALTER TABLE `dim_cst_pay_acct` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-04 12:13:49
-- MySQL dump 10.13  Distrib 8.0.39, for Linux (x86_64)
--
-- Host: localhost    Database: tupu
-- ------------------------------------------------------
-- Server version	8.0.39

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `dim_cst_setl_acct_agrt`
--

DROP TABLE IF EXISTS `dim_cst_setl_acct_agrt`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_setl_acct_agrt` (
  `setl_acct_id` int NOT NULL,
  `cust_id` int DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_acct_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_acct_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_acct_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_agrt_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cost_center` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invalid_date` datetime DEFAULT NULL,
  `valid_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `ntce_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rela_setl_acct_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `note_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `old_setl_acct_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bp_id` int DEFAULT NULL,
  `bill_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prepay_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_acct_alias` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `creator_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_stf_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cncl_stf_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_date` datetime DEFAULT NULL,
  `cncl_date` datetime DEFAULT NULL,
  `setl_acct_stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_acct_categ_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_acct_categ_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `main_setl_acct_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bill_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bill_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ntce_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ntce_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_acct_stat_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_acct_stat_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`setl_acct_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_setl_acct_agrt`
--

LOCK TABLES `dim_cst_setl_acct_agrt` WRITE;
/*!40000 ALTER TABLE `dim_cst_setl_acct_agrt` DISABLE KEYS */;
INSERT INTO `dim_cst_setl_acct_agrt` VALUES (270106,372043,'CU-0002','SE-0002','结算账户类别_2','结算账户名称2','结算协议类别_2','40960.7','2024-11-21 13:00:00','有效标志_2','2024-11-18 07:00:00','通知方式_2','RE-0002','结算类别_2','开票模式_2','NO-0002','OL-0002',299355,'账单方式_2','交费方式_2','付费方式_2','合同账户别名_2','CR-0002','ST-0002','CN-0002','2024-04-02 08:00:00','2024-04-13 06:00:00','停用','MG-0002','管理单位名称2','省份名称2','地市名称2','SE-0002','合同账户类别名称2','MA-0002','PA-0002','交费方式名称2','IN-0002','开票方式名称2','BI-0002','账单方式名称2','NT-0002','费用通知方式名称2','SE-0002','合同账户状态名称2','2024-02-22 16:00:00'),(427788,789529,'CU-0001','SE-0001','结算账户类别_1','结算账户名称1','结算协议类别_1','10443.97','2024-07-09 11:00:00','有效标志_1','2025-03-11 02:00:00','通知方式_1','RE-0001','结算类别_1','开票模式_1','NO-0001','OL-0001',630394,'账单方式_1','交费方式_1','付费方式_1','合同账户别名_1','CR-0001','ST-0001','CN-0001','2025-03-18 02:00:00','2024-08-19 04:00:00','注销','MG-0001','管理单位名称1','省份名称1','地市名称1','SE-0001','合同账户类别名称1','MA-0001','PA-0001','交费方式名称1','IN-0001','开票方式名称1','BI-0001','账单方式名称1','NT-0001','费用通知方式名称1','SE-0001','合同账户状态名称1','2024-01-08 19:00:00'),(642243,70003,'CU-0003','SE-0003','结算账户类别_3','结算账户名称3','结算协议类别_3','26391.53','2024-05-29 12:00:00','有效标志_3','2024-06-11 07:00:00','通知方式_3','RE-0003','结算类别_3','开票模式_3','NO-0003','OL-0003',322878,'账单方式_3','交费方式_3','付费方式_3','合同账户别名_3','CR-0003','ST-0003','CN-0003','2025-05-11 13:00:00','2024-11-30 19:00:00','异常','MG-0003','管理单位名称3','省份名称3','地市名称3','SE-0003','合同账户类别名称3','MA-0003','PA-0003','交费方式名称3','IN-0003','开票方式名称3','BI-0003','账单方式名称3','NT-0003','费用通知方式名称3','SE-0003','合同账户状态名称3','2025-02-19 09:00:00');
/*!40000 ALTER TABLE `dim_cst_setl_acct_agrt` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_srv_loc_elec`
--

DROP TABLE IF EXISTS `dim_cst_srv_loc_elec`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_srv_loc_elec` (
  `srv_loc_elec_id` int NOT NULL,
  `srv_loc_elec_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` int DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_id` int DEFAULT NULL,
  `rela_srv_loc_elec_id` int DEFAULT NULL,
  `voltage_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_elec_remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cap` double DEFAULT NULL,
  `bec_calc_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bec_calc_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `p_rela_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_st_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_st_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pf_eval_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pf_eval_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `date_of_signature` datetime DEFAULT NULL,
  `agrt_rated_val` double DEFAULT NULL,
  `dmd_veri_val` double DEFAULT NULL,
  `sys_rsrv_fee_calc_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_qty_sec` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sched_comm_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `interlock_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `interlock_loc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ps_sw_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ps_run_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ps_run_req_det_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `peak_pf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ddcttfr_elec_cap_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_char` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_cap` double DEFAULT NULL,
  `supl_resrc_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `relay_protect_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `relay_protect_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ps_run_mode_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_wire_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `invalid_date` datetime DEFAULT NULL,
  `elec_contact_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cfg_rpc_dev_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cfg_rpc_dev_cap` double DEFAULT NULL,
  `srv_loc_elec_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_elec_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ps_num_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ps_num_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spare_power_flag_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spare_power_flag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sp_cap` int DEFAULT NULL,
  `sp_lock_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sp_lock_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`srv_loc_elec_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_srv_loc_elec`
--

LOCK TABLES `dim_cst_srv_loc_elec` WRITE;
/*!40000 ALTER TABLE `dim_cst_srv_loc_elec` DISABLE KEYS */;
INSERT INTO `dim_cst_srv_loc_elec` VALUES (522428,'服务位置用电名称2','CU-0002',370424,'省份名称2','地市名称2','MG-0002','管理单位名称2',527464,365900,'VO-0002','承压名称2','服务位置用电备注测试数据2',6746.44,'BE-0002','基本电费计算方式名称2','P-0002','PR-0002','定价策略类型名称2','PF-0002','功率因数考核方式名称2','2024-10-31 17:00:00',6066.91,9364.53,'72038.12','551','调度通信方式_2','电源联锁方式_2','电源联锁装置位置_2','电源切换方式_2','电源运行方式_2','电源运行要求详细测试数据2','高峰负荷时功率因_2','扣减转供户容量标_2','服务种类_2','负荷性质_2',1868.67,'供应资源说明测试数据2','受能方式_2','RE-0002','继电保护类型名称2','电源运行方式说明测试数据2','电气接线方式_2','2025-02-07 12:00:00','2024-02-16 21:00:00','电气联络方式_2','配置无功补偿装置_2',7754.07,'SR-0002','受电点类型名称2','PS-0002','电源数目名称2','SP-0002','自备电源标志名称2',178982,'SP-0002','自备电源闭锁方式名称2','2024-05-20 01:00:00'),(564043,'服务位置用电名称3','CU-0003',301319,'省份名称3','地市名称3','MG-0003','管理单位名称3',206166,903632,'VO-0003','承压名称3','服务位置用电备注测试数据3',1611.83,'BE-0003','基本电费计算方式名称3','P-0003','PR-0003','定价策略类型名称3','PF-0003','功率因数考核方式名称3','2025-02-28 19:00:00',6405.33,3549.1,'48894.74','662','调度通信方式_3','电源联锁方式_3','电源联锁装置位置_3','电源切换方式_3','电源运行方式_3','电源运行要求详细测试数据3','高峰负荷时功率因_3','扣减转供户容量标_3','服务种类_3','负荷性质_3',6781.96,'供应资源说明测试数据3','受能方式_3','RE-0003','继电保护类型名称3','电源运行方式说明测试数据3','电气接线方式_3','2024-07-20 01:00:00','2024-02-07 15:00:00','电气联络方式_3','配置无功补偿装置_3',4779.08,'SR-0003','受电点类型名称3','PS-0003','电源数目名称3','SP-0003','自备电源标志名称3',68676,'SP-0003','自备电源闭锁方式名称3','2024-10-03 19:00:00'),(680964,'服务位置用电名称1','CU-0001',379266,'省份名称1','地市名称1','MG-0001','管理单位名称1',49880,794540,'VO-0001','承压名称1','服务位置用电备注测试数据1',1849.06,'BE-0001','基本电费计算方式名称1','P-0001','PR-0001','定价策略类型名称1','PF-0001','功率因数考核方式名称1','2024-12-30 22:00:00',1884.58,5129.05,'34322.24','136','调度通信方式_1','电源联锁方式_1','电源联锁装置位置_1','电源切换方式_1','电源运行方式_1','电源运行要求详细测试数据1','高峰负荷时功率因_1','扣减转供户容量标_1','服务种类_1','负荷性质_1',6565.37,'供应资源说明测试数据1','受能方式_1','RE-0001','继电保护类型名称1','电源运行方式说明测试数据1','电气接线方式_1','2024-05-22 10:00:00','2024-05-12 18:00:00','电气联络方式_1','配置无功补偿装置_1',2348.52,'SR-0001','受电点类型名称1','PS-0001','电源数目名称1','SP-0001','自备电源标志名称1',385229,'SP-0001','自备电源闭锁方式名称1','2024-08-05 03:00:00');
/*!40000 ALTER TABLE `dim_cst_srv_loc_elec` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_srv_loc_gen_elec`
--

DROP TABLE IF EXISTS `dim_cst_srv_loc_gen_elec`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_srv_loc_gen_elec` (
  `srv_loc_gen_elec_id` int NOT NULL,
  `rela_srv_loc_gen_elec_id` int DEFAULT NULL,
  `srv_loc_gen_elec_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` int DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_gen_elec_remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sw_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sw_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cap` double DEFAULT NULL,
  `srv_loc_gen_elec_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_gen_elec_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_id` int DEFAULT NULL,
  `interlock_loc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `interlock_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `interlock_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accs_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accs_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `proj_reply_doc_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invalid_date` datetime DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`srv_loc_gen_elec_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_srv_loc_gen_elec`
--

LOCK TABLES `dim_cst_srv_loc_gen_elec` WRITE;
/*!40000 ALTER TABLE `dim_cst_srv_loc_gen_elec` DISABLE KEYS */;
INSERT INTO `dim_cst_srv_loc_gen_elec` VALUES (20374,752230,'服务位置发电名称2',829056,'CU-0002','服务位置发电备注测试数据2','MG-0002','管理单位名称2','省份名称2','地市名称2','SW-0002','切换方式名称2','GE-0002','发电方式名称2','VO-0002','承压名称2',4074.95,'SR-0002','服务位置发电类型名称2',231730,'联锁装置位置_2','IN-0002','联锁方式名称2','AC-0002','接入方式名称2','2025-01-26 16:00:00','PR-0002','2025-02-18 22:00:00','2025-03-28 00:00:00'),(290159,811297,'服务位置发电名称1',870707,'CU-0001','服务位置发电备注测试数据1','MG-0001','管理单位名称1','省份名称1','地市名称1','SW-0001','切换方式名称1','GE-0001','发电方式名称1','VO-0001','承压名称1',1095.65,'SR-0001','服务位置发电类型名称1',804310,'联锁装置位置_1','IN-0001','联锁方式名称1','AC-0001','接入方式名称1','2025-03-11 14:00:00','PR-0001','2024-08-11 22:00:00','2024-03-13 17:00:00'),(589804,158029,'服务位置发电名称3',959914,'CU-0003','服务位置发电备注测试数据3','MG-0003','管理单位名称3','省份名称3','地市名称3','SW-0003','切换方式名称3','GE-0003','发电方式名称3','VO-0003','承压名称3',195.86,'SR-0003','服务位置发电类型名称3',22443,'联锁装置位置_3','IN-0003','联锁方式名称3','AC-0003','接入方式名称3','2025-01-30 06:00:00','PR-0003','2024-08-29 07:00:00','2025-02-05 10:00:00');
/*!40000 ALTER TABLE `dim_cst_srv_loc_gen_elec` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_trade_cls`
--

DROP TABLE IF EXISTS `dim_cst_trade_cls`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_trade_cls` (
  `code_cls_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `code_cls_val` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `code_cls_val_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `trade_code_4` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `trade_name_4` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `trade_code_3` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `trade_name_3` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `trade_code_2` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `trade_name_2` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `trade_code_1` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `trade_name_1` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `level` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`code_cls_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_trade_cls`
--

LOCK TABLES `dim_cst_trade_cls` WRITE;
/*!40000 ALTER TABLE `dim_cst_trade_cls` DISABLE KEYS */;
INSERT INTO `dim_cst_trade_cls` VALUES ('COD0001','CO-0001','代码分类值名称1','TR-0001','四级代码分类值名称1','TR-0001','三级代码分类值名称1','TR-0001','二级代码分类值名称1','TR-0001','一级代码分类值名称1','层级_1','2025-01-01 03:00:00'),('COD0002','CO-0002','代码分类值名称2','TR-0002','四级代码分类值名称2','TR-0002','三级代码分类值名称2','TR-0002','二级代码分类值名称2','TR-0002','一级代码分类值名称2','层级_2','2025-01-24 16:00:00'),('COD0003','CO-0003','代码分类值名称3','TR-0003','四级代码分类值名称3','TR-0003','三级代码分类值名称3','TR-0003','二级代码分类值名称3','TR-0003','一级代码分类值名称3','层级_3','2024-06-19 07:00:00');
/*!40000 ALTER TABLE `dim_cst_trade_cls` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_cst_value_added_tax`
--

DROP TABLE IF EXISTS `dim_cst_value_added_tax`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_cst_value_added_tax` (
  `id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `cust_id` int DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `vat_id` int DEFAULT NULL,
  `vat_tax_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reg_addr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `taxpayer_tel` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invalid_date` datetime DEFAULT NULL,
  `tax_rate` double DEFAULT NULL,
  `valid_flag_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_flag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `vat_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `vat_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `vat_acct` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bank_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_acct_id` int DEFAULT NULL,
  `ipt_sorc_id` int DEFAULT NULL,
  `ipt_sorc_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ipt_sorc_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bp_id` int DEFAULT NULL,
  `creator` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `create_date` datetime DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_cst_value_added_tax`
--

LOCK TABLES `dim_cst_value_added_tax` WRITE;
/*!40000 ALTER TABLE `dim_cst_value_added_tax` DISABLE KEYS */;
INSERT INTO `dim_cst_value_added_tax` VALUES ('ID0001',433508,'CU-0001',31250,'VA-0001','杭州市西湖区bb路5号','13855341815','2024-05-09 04:00:00',4204.51,'VA-0001','有效标志名称1','2024-10-24 14:00:00','VA-0001','增值税名1','62220037356888897','BA-0001',651797,291279,'IP-0001','录入来源类型名称1',183831,'创建人员_1','2024-10-30 15:00:00','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-08-15 05:00:00'),('ID0002',943713,'CU-0002',892630,'VA-0002','广州市天河区zz路3号','13896111409','2024-08-30 19:00:00',118.51,'VA-0002','有效标志名称2','2024-07-15 22:00:00','VA-0002','增值税名2','62220095814368020','BA-0002',530563,175608,'IP-0002','录入来源类型名称2',982347,'创建人员_2','2024-06-17 09:00:00','省份名称2','地市名称2','MG-0002','管理单位名称2','2024-07-18 17:00:00'),('ID0003',869692,'CU-0003',782468,'VA-0003','北京市朝阳区xx路1号','13877185508','2024-05-04 20:00:00',5912.85,'VA-0003','有效标志名称3','2024-09-09 09:00:00','VA-0003','增值税名3','62220049662549044','BA-0003',145775,249483,'IP-0003','录入来源类型名称3',298954,'创建人员_3','2024-11-22 18:00:00','省份名称3','地市名称3','MG-0003','管理单位名称3','2024-10-16 16:00:00');
/*!40000 ALTER TABLE `dim_cst_value_added_tax` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_grid_pms_mgt_org`
--

DROP TABLE IF EXISTS `dim_grid_pms_mgt_org`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_grid_pms_mgt_org` (
  `org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `org_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `org_nature_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `org_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sup_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sup_org_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `disp_seque_dsc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `major_nature_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `manage_lvl_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `create_tm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sync_tm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_prov_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_prov_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_city_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_city_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_feed_co_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_feed_co_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reserve_id1` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `erp_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `erp_org_typ_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `org_lvl_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `org_fullpath` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `org_fullpath_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_maint_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_maint_org_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `org_full_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name_auth` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name_auth` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_tm` datetime DEFAULT NULL,
  PRIMARY KEY (`org_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_grid_pms_mgt_org`
--

LOCK TABLES `dim_grid_pms_mgt_org` WRITE;
/*!40000 ALTER TABLE `dim_grid_pms_mgt_org` DISABLE KEYS */;
INSERT INTO `dim_grid_pms_mgt_org` VALUES ('ORG0001','单位名称1','单位性质名称1','OR-0001','SUP0001','上级单位名称1','显示顺序描述_1','专业性质代码_1','管理级别代码_1','2024-10-21 00:00:00','2025-01-19 00:00:00','BLG0001','所属网省名称1','BLG0001','所属地市名称1','BLG0001','所属供电公司名称1','预留ID1_1','ERP0001','华能集团','大唐集团','国网电力公司','ORG0001','BLG0001','所属运维单位名称1','华能集团','地市名称1','省份名称1','2025-03-01 18:00:00'),('ORG0002','单位名称2','单位性质名称2','OR-0002','SUP0002','上级单位名称2','显示顺序描述_2','专业性质代码_2','管理级别代码_2','2024-10-24 00:00:00','2024-04-14 00:00:00','BLG0002','所属网省名称2','BLG0002','所属地市名称2','BLG0002','所属供电公司名称2','预留ID1_2','ERP0002','南方电网公司','国网电力公司','南方电网公司','ORG0002','BLG0002','所属运维单位名称2','华能集团','地市名称2','省份名称2','2024-11-24 19:00:00'),('ORG0003','单位名称3','单位性质名称3','OR-0003','SUP0003','上级单位名称3','显示顺序描述_3','专业性质代码_3','管理级别代码_3','2024-11-10 00:00:00','2025-01-04 00:00:00','BLG0003','所属网省名称3','BLG0003','所属地市名称3','BLG0003','所属供电公司名称3','预留ID1_3','ERP0003','南方电网公司','华能集团','国家电投','ORG0003','BLG0003','所属运维单位名称3','南方电网公司','地市名称3','省份名称3','2024-08-04 15:00:00');
/*!40000 ALTER TABLE `dim_grid_pms_mgt_org` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_grid_pub_dist_trans_resrc_standbk_e`
--

DROP TABLE IF EXISTS `dim_grid_pub_dist_trans_resrc_standbk_e`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_grid_pub_dist_trans_resrc_standbk_e` (
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `psrid` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `astid` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `equipname` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_city_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_city_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `op_maint_org_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `op_maint_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `maint_team_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `maint_team_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_stat_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_stat_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_space_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_space_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_stat_typ_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_stat_typ_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_tower_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_tower_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_line_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_line_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltagelevel` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_lvl_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `runstate` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_st_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ship_dt` datetime DEFAULT NULL,
  `retrogres_dt` datetime DEFAULT NULL,
  `is_farmnet` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `imp_degree_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `imp_degree_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `region_feat_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `region_feat_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `feed_area_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `feed_area_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `use_nature_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `use_nature_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `auth_org_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `opera_org_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `permis_org_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `monit_org_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_trunk_branch_line_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_trunk_branch_line_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `feeder` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_feeder_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `create_tm` datetime DEFAULT NULL,
  `blg_switch_segmt` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pubprivflag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pub_priv_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `latest_upd_tm` datetime DEFAULT NULL,
  `is_std_customizing` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_area_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `urban_rural_cls_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tg_installation_tol_cap` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_have_distribt_ps_cons` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_a_second_time_fuse_complete_set` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_have_charging_pile_cons` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charging_pile_cons_typ_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eqp_master_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltreg_eqp_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltreg_eqp_asst_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltreg_eqp_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltreg_eqp_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_remark_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_remark_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `detail_addr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `capacity` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fst_run_dt` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `enabl_dt` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `standby_nature_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `standby_nature_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_cap` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `idle_tl` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `active_tl` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `damage_para_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tl_compute_mode_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tl_compute_mode_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_dt` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eqp_pos_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgmt_org_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgmt_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asst_nature_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asst_nature_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eqp_typ_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eqp_typ_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eqp_model_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_source` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_tm` datetime DEFAULT NULL,
  PRIMARY KEY (`psrid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_grid_pub_dist_trans_resrc_standbk_e`
--

LOCK TABLES `dim_grid_pub_dist_trans_resrc_standbk_e` WRITE;
/*!40000 ALTER TABLE `dim_grid_pub_dist_trans_resrc_standbk_e` DISABLE KEYS */;
INSERT INTO `dim_grid_pub_dist_trans_resrc_standbk_e` VALUES ('宁波','浙江','RES0001','AST0001','配电变压器01号','RUN0001','CITY001','宁波','ORG001','运维公司1','TEAM001','维护班组1','STAT0001','变电站1','SP0001','空间1','01','变电站','TWR0001','杆塔1','LINE0001','线路1','10','10kV','20','在运','2023-02-15 00:00:00',NULL,'0','02','重要','01','城市','A','A区','01','公用','AUTH001','OP001','PERM001','MON001','TBL0001','支线1','RES0001','馈线1','2023-02-01 00:00:00','SEG1','1','公用','2024-02-01 00:00:00','0','ADM001','01','100','0','0','0',NULL,'EM0001','1','1','VR0001','调压设备1','01','正常','浙江省杭州市xx路1号','200','2023-02-20','2023-02-25','01','运行','100','0','1100','DMG0001','01','计算方式A','2024-02-01','POS0001','MGMT001','管理单位1','01','自有','01','柱上变','型号1','PMS','2024-07-30 00:00:00'),('温州','浙江','RES0002','AST0002','配电变压器02号','RUN0002','CITY002','温州','ORG002','运维公司2','TEAM002','维护班组2','STAT0002','变电站2','SP0002','空间2','01','变电站','TWR0002','杆塔2','LINE0002','线路2','10','10kV','20','在运','2023-03-15 00:00:00',NULL,'0','02','重要','01','城市','A','A区','01','公用','AUTH002','OP002','PERM002','MON002','TBL0002','支线2','RES0002','馈线2','2023-03-01 00:00:00','SEG2','1','公用','2024-03-01 00:00:00','0','ADM002','01','200','0','0','0',NULL,'EM0002','2','2','VR0002','调压设备2','01','正常','浙江省杭州市xx路2号','300','2023-03-20','2023-03-25','01','运行','150','0','1200','DMG0002','01','计算方式A','2024-03-01','POS0002','MGMT002','管理单位2','01','自有','02','非柱上变','型号2','PMS','2024-07-30 00:00:00'),('嘉兴','浙江','RES0003','AST0003','配电变压器03号','RUN0003','CITY003','嘉兴','ORG003','运维公司3','TEAM003','维护班组3','STAT0003','变电站3','SP0003','空间3','01','变电站','TWR0003','杆塔3','LINE0003','线路3','10','10kV','30','停运','2023-04-15 00:00:00',NULL,'0','02','重要','01','城市','A','A区','01','公用','AUTH003','OP003','PERM003','MON003','TBL0003','支线3','RES0003','馈线3','2023-04-01 00:00:00','SEG3','1','公用','2024-04-01 00:00:00','0','ADM003','01','300','0','0','0',NULL,'EM0003','3','3','VR0003','调压设备3','01','正常','浙江省杭州市xx路3号','400','2023-04-20','2023-04-25','01','运行','50','0','1300','DMG0003','01','计算方式A','2024-04-01','POS0003','MGMT003','管理单位3','01','自有','01','柱上变','型号3','PMS','2024-07-30 00:00:00'),('湖州','浙江','RES0004','AST0004','配电变压器04号','RUN0004','CITY004','湖州','ORG004','运维公司4','TEAM004','维护班组4','STAT0004','变电站4','SP0004','空间4','01','变电站','TWR0004','杆塔4','LINE0004','线路4','10','10kV','20','在运','2023-05-15 00:00:00',NULL,'0','02','重要','01','城市','A','A区','01','公用','AUTH004','OP004','PERM004','MON004','TBL0004','支线4','RES0001','馈线4','2023-05-01 00:00:00','SEG4','1','公用','2024-05-01 00:00:00','0','ADM004','01','400','0','0','0',NULL,'EM0004','4','4','VR0004','调压设备4','01','正常','浙江省杭州市xx路4号','500','2023-05-20','2023-05-25','01','运行','100','0','1400','DMG0004','01','计算方式A','2024-05-01','POS0004','MGMT004','管理单位4','01','自有','02','非柱上变','型号4','PMS','2024-07-30 00:00:00'),('杭州','浙江','RES0005','AST0005','配电变压器05号','RUN0005','CITY005','杭州','ORG005','运维公司5','TEAM005','维护班组5','STAT0005','变电站5','SP0005','空间5','01','变电站','TWR0005','杆塔5','LINE0005','线路5','10','10kV','20','在运','2023-06-15 00:00:00',NULL,'0','02','重要','01','城市','A','A区','01','公用','AUTH005','OP005','PERM005','MON005','TBL0005','支线5','RES0002','馈线5','2023-06-01 00:00:00','SEG5','1','公用','2024-06-01 00:00:00','0','ADM005','01','500','0','0','0',NULL,'EM0005','5','5','VR0005','调压设备5','01','正常','浙江省杭州市xx路5号','100','2023-06-20','2023-06-25','01','运行','150','0','1500','DMG0005','01','计算方式A','2024-06-01','POS0005','MGMT005','管理单位5','01','自有','01','柱上变','型号5','PMS','2024-07-30 00:00:00'),('宁波','浙江','RES0006','AST0006','配电变压器06号','RUN0006','CITY006','宁波','ORG006','运维公司6','TEAM006','维护班组6','STAT0006','变电站6','SP0006','空间6','01','变电站','TWR0006','杆塔6','LINE0006','线路6','10','10kV','30','停运','2023-07-15 00:00:00',NULL,'0','02','重要','01','城市','A','A区','01','公用','AUTH006','OP006','PERM006','MON006','TBL0006','支线6','RES0003','馈线6','2023-07-01 00:00:00','SEG6','1','公用','2024-07-01 00:00:00','0','ADM006','01','600','0','0','0',NULL,'EM0006','6','6','VR0006','调压设备6','01','正常','浙江省杭州市xx路6号','200','2023-07-20','2023-07-25','01','运行','50','0','1600','DMG0006','01','计算方式A','2024-07-01','POS0006','MGMT006','管理单位6','01','自有','02','非柱上变','型号6','PMS','2024-07-30 00:00:00'),('温州','浙江','RES0007','AST0007','配电变压器07号','RUN0007','CITY007','温州','ORG007','运维公司7','TEAM007','维护班组7','STAT0007','变电站7','SP0007','空间7','01','变电站','TWR0007','杆塔7','LINE0007','线路7','10','10kV','20','在运','2023-08-15 00:00:00',NULL,'0','02','重要','01','城市','A','A区','01','公用','AUTH007','OP007','PERM007','MON007','TBL0007','支线7','RES0001','馈线7','2023-08-01 00:00:00','SEG7','1','公用','2024-08-01 00:00:00','0','ADM007','01','700','0','0','0',NULL,'EM0007','7','7','VR0007','调压设备7','01','正常','浙江省杭州市xx路7号','300','2023-08-20','2023-08-25','01','运行','100','0','1700','DMG0007','01','计算方式A','2024-08-01','POS0007','MGMT007','管理单位7','01','自有','01','柱上变','型号7','PMS','2024-07-30 00:00:00'),('嘉兴','浙江','RES0008','AST0008','配电变压器08号','RUN0008','CITY008','嘉兴','ORG008','运维公司8','TEAM008','维护班组8','STAT0008','变电站8','SP0008','空间8','01','变电站','TWR0008','杆塔8','LINE0008','线路8','10','10kV','20','在运','2023-09-15 00:00:00',NULL,'0','02','重要','01','城市','A','A区','01','公用','AUTH008','OP008','PERM008','MON008','TBL0008','支线8','RES0002','馈线8','2023-09-01 00:00:00','SEG8','1','公用','2024-09-01 00:00:00','0','ADM008','01','800','0','0','0',NULL,'EM0008','8','8','VR0008','调压设备8','01','正常','浙江省杭州市xx路8号','400','2023-09-20','2023-09-25','01','运行','150','0','1800','DMG0008','01','计算方式A','2024-09-01','POS0008','MGMT008','管理单位8','01','自有','02','非柱上变','型号8','PMS','2024-07-30 00:00:00'),('湖州','浙江','RES0009','AST0009','配电变压器09号','RUN0009','CITY009','湖州','ORG009','运维公司9','TEAM009','维护班组9','STAT0009','变电站9','SP0009','空间9','01','变电站','TWR0009','杆塔9','LINE0009','线路9','10','10kV','30','停运','2023-10-15 00:00:00',NULL,'0','02','重要','01','城市','A','A区','01','公用','AUTH009','OP009','PERM009','MON009','TBL0009','支线9','RES0003','馈线9','2023-10-01 00:00:00','SEG9','1','公用','2024-10-01 00:00:00','0','ADM009','01','900','0','0','0',NULL,'EM0009','9','9','VR0009','调压设备9','01','正常','浙江省杭州市xx路9号','500','2023-10-20','2023-10-25','01','运行','50','0','1900','DMG0009','01','计算方式A','2024-10-01','POS0009','MGMT009','管理单位9','01','自有','01','柱上变','型号9','PMS','2024-07-30 00:00:00'),('杭州','浙江','RES0010','AST0010','配电变压器10号','RUN0010','CITY010','杭州','ORG010','运维公司10','TEAM010','维护班组10','STAT0010','变电站10','SP0010','空间10','01','变电站','TWR0010','杆塔10','LINE0010','线路10','10','10kV','20','在运','2023-11-15 00:00:00',NULL,'0','02','重要','01','城市','A','A区','01','公用','AUTH010','OP010','PERM010','MON010','TBL0010','支线10','RES0001','馈线10','2023-11-01 00:00:00','SEG10','1','公用','2024-11-01 00:00:00','0','ADM010','01','1000','0','0','0',NULL,'EM0010','10','10','VR0010','调压设备10','01','正常','浙江省杭州市xx路10号','100','2023-11-20','2023-11-25','01','运行','100','0','2000','DMG0010','01','计算方式A','2024-11-01','POS0010','MGMT010','管理单位10','01','自有','02','非柱上变','型号10','PMS','2024-07-30 00:00:00');
/*!40000 ALTER TABLE `dim_grid_pub_dist_trans_resrc_standbk_e` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_grid_pub_feeder_resrc_standbk_e`
--

DROP TABLE IF EXISTS `dim_grid_pub_feeder_resrc_standbk_e`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_grid_pub_feeder_resrc_standbk_e` (
  `resrc_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `asst_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `line_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `commission_length` double DEFAULT NULL,
  `line_len` double DEFAULT NULL,
  `overhd_line_len` double DEFAULT NULL,
  `cable_line_len` double DEFAULT NULL,
  `install_capt` double DEFAULT NULL,
  `feed_radius` double DEFAULT NULL,
  `volt_lvl_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_lvl_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_st_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_st_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `imp_degree_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `imp_degree_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `line_color_scale_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `line_color_scale_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `erect_mode_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `erect_mode_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `overhd_wiring_mode_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `overhd_wiring_mode_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cable_wiring_mode_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cable_wiring_mode_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_farmnet` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `outline_switch_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `outline_switch_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `outline_switch_typ_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `outline_switch_typ_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `start_elec_stat_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `start_elec_stat_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `start_elec_stat_typ_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `start_elec_stat_typ_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `outline_space_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `outline_space_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `region_feat_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `region_feat_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `feed_area_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `feed_area_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_city_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_city_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `op_maint_org_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `op_maint_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `maint_team_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `maint_team_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sch_org_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pub_priv_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pub_priv_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ship_dt` datetime DEFAULT NULL,
  `retrogres_dt` datetime DEFAULT NULL,
  `create_tm` datetime DEFAULT NULL,
  `upd_tm` datetime DEFAULT NULL,
  `latest_upd_tm` datetime DEFAULT NULL,
  `pipeline_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `per_unit_len_line_x` double DEFAULT NULL,
  `per_unit_len_line_r` double DEFAULT NULL,
  `branch_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ap_rpll_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accs_rd_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_spec` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ll_calc_mode_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ll_calc_mode_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rp_ll_calc_val` double DEFAULT NULL,
  `ap_ll_calc_val` double DEFAULT NULL,
  `detail_addr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `path_org_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `path_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asst_nature_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asst_nature_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sch_lvl_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sch_lvl_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eqp_master_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_tm` datetime DEFAULT NULL,
  PRIMARY KEY (`resrc_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_grid_pub_feeder_resrc_standbk_e`
--

LOCK TABLES `dim_grid_pub_feeder_resrc_standbk_e` WRITE;
/*!40000 ALTER TABLE `dim_grid_pub_feeder_resrc_standbk_e` DISABLE KEYS */;
INSERT INTO `dim_grid_pub_feeder_resrc_standbk_e` VALUES ('RES0001','ASS0001','线路名称1','RU-0001',9161.02,8935.59,9098.26,3958.98,4118.52,5628.24,'电压等级代码_1','电压等级描述_1','激活','正常','重要程度代码_1','重要程度描述_1','线路色标代码_1','线路色标描述_1','架设方式代码_1','架设方式描述_1','架空接线方式代码_1','架空接线方式描述_1','电缆接线方式代码_1','电缆接线方式描述_1','是否农网(0:否_1','OUT0001','出线开关名称1','出线开关类型代码_1','出线开关类型描述_1','STA0001','起点电站名称1','起点电站类型代码_1','起点电站类型描述_1','OUT0001','出线间隔名称1','地区特征代码_1','地区特征描述_1','11866.55','93574.31','BLG0001','所属地市名称1','OP0001','运维单位名称1','MAI0001','维护班组名称1','SCH0001','公专标志代码_1','公专标志描述_1','2024-07-08 17:00:00','2024-12-23 07:00:00','2025-01-18 19:00:00','2025-04-29 20:00:00','2025-01-16 10:00:00','PIP0001','PI-0001',9135.33,5082.46,'分支标志(01:_1','有损无损标志(0_1','支路标志(01:_1','管线规格_1','管线损耗计算方式_1','管线损耗计算方式_1',9571.36,3480.5,'上海市浦东新区yy路2号','PA-0001','途径单位名称集合1','MG-0001','管理单位名称1','资产性质代码_1','资产性质描述_1','调度级别代码_1','调度级别描述_1','EQP0001','2025-05-11 23:00:00'),('RES0002','ASS0002','线路名称2','RU-0002',4286.07,4955.22,2075.2,7194.71,7373.97,7215.44,'电压等级代码_2','电压等级描述_2','异常','正常','重要程度代码_2','重要程度描述_2','线路色标代码_2','线路色标描述_2','架设方式代码_2','架设方式描述_2','架空接线方式代码_2','架空接线方式描述_2','电缆接线方式代码_2','电缆接线方式描述_2','是否农网(0:否_2','OUT0002','出线开关名称2','出线开关类型代码_2','出线开关类型描述_2','STA0002','起点电站名称2','起点电站类型代码_2','起点电站类型描述_2','OUT0002','出线间隔名称2','地区特征代码_2','地区特征描述_2','61262.06','55513.87','BLG0002','所属地市名称2','OP0002','运维单位名称2','MAI0002','维护班组名称2','SCH0002','公专标志代码_2','公专标志描述_2','2024-05-05 21:00:00','2024-09-05 00:00:00','2024-03-11 17:00:00','2024-01-12 22:00:00','2024-08-24 14:00:00','PIP0002','PI-0002',5159.88,4591.51,'分支标志(01:_2','有损无损标志(0_2','支路标志(01:_2','管线规格_2','管线损耗计算方式_2','管线损耗计算方式_2',111.42,2463.33,'深圳市南山区aa路4号','PA-0002','途径单位名称集合2','MG-0002','管理单位名称2','资产性质代码_2','资产性质描述_2','调度级别代码_2','调度级别描述_2','EQP0002','2024-02-13 07:00:00'),('RES0003','ASS0003','线路名称3','RU-0003',907.23,3739.86,4778.56,2208.42,6365.63,5829.03,'电压等级代码_3','电压等级描述_3','正常','异常','重要程度代码_3','重要程度描述_3','线路色标代码_3','线路色标描述_3','架设方式代码_3','架设方式描述_3','架空接线方式代码_3','架空接线方式描述_3','电缆接线方式代码_3','电缆接线方式描述_3','是否农网(0:否_3','OUT0003','出线开关名称3','出线开关类型代码_3','出线开关类型描述_3','STA0003','起点电站名称3','起点电站类型代码_3','起点电站类型描述_3','OUT0003','出线间隔名称3','地区特征代码_3','地区特征描述_3','36168.97','27801.47','BLG0003','所属地市名称3','OP0003','运维单位名称3','MAI0003','维护班组名称3','SCH0003','公专标志代码_3','公专标志描述_3','2024-11-22 05:00:00','2024-08-09 12:00:00','2024-10-02 08:00:00','2025-04-04 03:00:00','2024-05-07 11:00:00','PIP0003','PI-0003',8986.57,4481.51,'分支标志(01:_3','有损无损标志(0_3','支路标志(01:_3','管线规格_3','管线损耗计算方式_3','管线损耗计算方式_3',9331.84,6555.8,'杭州市西湖区bb路5号','PA-0003','途径单位名称集合3','MG-0003','管理单位名称3','资产性质代码_3','资产性质描述_3','调度级别代码_3','调度级别描述_3','EQP0003','2024-12-15 01:00:00');
/*!40000 ALTER TABLE `dim_grid_pub_feeder_resrc_standbk_e` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_grid_pv_plant`
--

DROP TABLE IF EXISTS `dim_grid_pv_plant`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_grid_pv_plant` (
  `id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `name_abbreviation` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `register_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `company_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dcc_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `max_voltage_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assets_ownership` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `assets_ownership_com_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plant_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `region` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `region_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `longitude` double DEFAULT NULL,
  `latitude` double DEFAULT NULL,
  `altitude` double DEFAULT NULL,
  `address` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `postcode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fax_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phone_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `email` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `operate_state` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `operate_state_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stamp` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `owner` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sys_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `check_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `state_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `state_code_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `expiry_date` datetime DEFAULT NULL,
  `operate_date` datetime DEFAULT NULL,
  `prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `connective_station_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inverter_count` int DEFAULT NULL,
  `type_num` int DEFAULT NULL,
  `energy_storage_capacity` double DEFAULT NULL,
  `energy_storage_device_count` int DEFAULT NULL,
  `hour_num` double DEFAULT NULL,
  `filt_num` int DEFAULT NULL,
  `ground_type` int DEFAULT NULL,
  `photometer_num` int DEFAULT NULL,
  `pv_type` int DEFAULT NULL,
  `zw_voltage_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accs_capacity` double DEFAULT NULL,
  `inst_capacity` double DEFAULT NULL,
  `p_capacity_composition` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_count` int DEFAULT NULL,
  `max_p` double DEFAULT NULL,
  `transfm_count` int DEFAULT NULL,
  `transfm_capacity` double DEFAULT NULL,
  `seriescapacitor_cap` double DEFAULT NULL,
  `grounddis_n` int DEFAULT NULL,
  `shuntcapacitor_cap` double DEFAULT NULL,
  `acfilter_n` int DEFAULT NULL,
  `busbar_n` int DEFAULT NULL,
  `seriesreactor_n` int DEFAULT NULL,
  `acline_n` int DEFAULT NULL,
  `ct_n` int DEFAULT NULL,
  `svg_cap` double DEFAULT NULL,
  `shuntreactor_n` int DEFAULT NULL,
  `svg_n` int DEFAULT NULL,
  `seriesreactor_cap` double DEFAULT NULL,
  `petersencoil_n` int DEFAULT NULL,
  `svc_n` int DEFAULT NULL,
  `synccondenser_cap` double DEFAULT NULL,
  `groundimpedance_n` int DEFAULT NULL,
  `pt_n` int DEFAULT NULL,
  `boiler_n` int DEFAULT NULL,
  `acfilter_cap` double DEFAULT NULL,
  `breaker_n` int DEFAULT NULL,
  `shuntcapacitor_n` int DEFAULT NULL,
  `svc_cap` double DEFAULT NULL,
  `seriescapacitor_n` int DEFAULT NULL,
  `dis_n` int DEFAULT NULL,
  `synccondenser_n` int DEFAULT NULL,
  `shuntreactor_cap` double DEFAULT NULL,
  `main_transfm_n` int DEFAULT NULL,
  `main_transfm_cap` double DEFAULT NULL,
  `voltage_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inverter_cap` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_grid_pv_plant`
--

LOCK TABLES `dim_grid_pv_plant` WRITE;
/*!40000 ALTER TABLE `dim_grid_pv_plant` DISABLE KEYS */;
INSERT INTO `dim_grid_pv_plant` VALUES ('ID0001','发电厂名称1','发电厂简称1','工商注册名称1','COM0001','DCC0001','最高电压等级_1','资产归属性质_1','ASS0001','发电厂类型_1','行政区划_1','行政区划名称1',2448.42,1292.7,9441.88,'北京市朝阳区xx路1号','PO-0001','FA-0001','PH-0001','电子邮箱_1','激活','运行状态名称1','更新标志_1','拥有者_1','系统属性_1','CH-0001','ST-0001','设备状态名称1','2025-03-25 13:00:00','2024-05-10 05:00:00','省份名称1','地市名称1','CON0001',768614,775352,3207.74,937182,704.74,823961,880415,925146,866858,'主网电压等级名称1',3012.68,3134.8,'发电容量构成_1',703906,1142.04,285639,2096.5,2077.69,158328,15.01,796914,267789,526498,676024,513721,8763.23,708699,569887,1629.13,785351,973272,8154.71,11298,528577,40401,6470.04,934782,416727,7797.15,882318,752921,146774,6934.79,662709,1433.06,'电压等级[主键]_1',407.33,'2024-08-09 06:00:00'),('ID0002','发电厂名称2','发电厂简称2','工商注册名称2','COM0002','DCC0002','最高电压等级_2','资产归属性质_2','ASS0002','发电厂类型_2','行政区划_2','行政区划名称2',4613.65,2166.27,3953.32,'杭州市西湖区bb路5号','PO-0002','FA-0002','PH-0002','电子邮箱_2','注销','运行状态名称2','更新标志_2','拥有者_2','系统属性_2','CH-0002','ST-0002','设备状态名称2','2024-04-17 21:00:00','2024-05-04 11:00:00','省份名称2','地市名称2','CON0002',800073,828878,9785.62,850620,4178.49,803277,733178,546002,102806,'主网电压等级名称2',9961.68,2960.69,'发电容量构成_2',307957,9236.31,565989,9799.95,9264.4,778621,5823.69,272609,83345,327306,991151,993742,3572.53,932798,912900,7435.52,867581,605314,4871.65,472707,415565,366801,7282.52,641270,792235,2522.47,629602,491236,8660,5705.23,989071,9556.28,'电压等级[主键]_2',9560.29,'2024-10-11 11:00:00'),('ID0003','发电厂名称3','发电厂简称3','工商注册名称3','COM0003','DCC0003','最高电压等级_3','资产归属性质_3','ASS0003','发电厂类型_3','行政区划_3','行政区划名称3',6827.35,8923.16,8794.61,'北京市朝阳区xx路1号','PO-0003','FA-0003','PH-0003','电子邮箱_3','注销','运行状态名称3','更新标志_3','拥有者_3','系统属性_3','CH-0003','ST-0003','设备状态名称3','2024-08-25 18:00:00','2025-02-20 22:00:00','省份名称3','地市名称3','CON0003',230157,546224,5996.7,583631,8964.27,778267,987767,922596,14640,'主网电压等级名称3',3702.14,7983.16,'发电容量构成_3',805993,8506.69,717112,5713.02,4148.36,20479,2548.41,358285,814904,340175,793463,270237,8598.38,124925,249219,1161.59,26918,952301,8193.04,466424,307268,339785,7787.35,749129,842398,2396.93,885999,498711,341047,3368.49,913983,5499.66,'电压等级[主键]_3',4558.07,'2025-03-01 08:00:00');
/*!40000 ALTER TABLE `dim_grid_pv_plant` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_grid_region_org`
--

DROP TABLE IF EXISTS `dim_grid_region_org`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_grid_region_org` (
  `region_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `region_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnty_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnty_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name_auth` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name_auth` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`region_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_grid_region_org`
--

LOCK TABLES `dim_grid_region_org` WRITE;
/*!40000 ALTER TABLE `dim_grid_region_org` DISABLE KEYS */;
INSERT INTO `dim_grid_region_org` VALUES ('REG0001','行政区划名称1','PR-0001','省公司名称1','CI-0001','地市公司名称1','CN-0001','区县公司名称1','省份名称1','地市名称1','2024-10-12 04:00:00'),('REG0002','行政区划名称2','PR-0002','省公司名称2','CI-0002','地市公司名称2','CN-0002','区县公司名称2','省份名称2','地市名称2','2025-01-02 14:00:00'),('REG0003','行政区划名称3','PR-0003','省公司名称3','CI-0003','地市公司名称3','CN-0003','区县公司名称3','省份名称3','地市名称3','2024-09-23 08:00:00');
/*!40000 ALTER TABLE `dim_grid_region_org` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_ps_milestone`
--

DROP TABLE IF EXISTS `dim_ps_milestone`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_ps_milestone` (
  `milestone_number` varchar(255) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `wbs_element` varchar(255) DEFAULT NULL,
  `network_number` varchar(255) DEFAULT NULL,
  `activity_number` varchar(255) DEFAULT NULL,
  `target_date` date DEFAULT NULL,
  `actual_date` date DEFAULT NULL,
  `billing_related` varchar(255) DEFAULT NULL,
  `usage` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`milestone_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_ps_milestone`
--

LOCK TABLES `dim_ps_milestone` WRITE;
/*!40000 ALTER TABLE `dim_ps_milestone` DISABLE KEYS */;
INSERT INTO `dim_ps_milestone` VALUES ('M-001','项目启动','W-001',NULL,NULL,'2024-01-20',NULL,NULL,NULL),('M-002','设备到货','W-001',NULL,NULL,'2024-03-15',NULL,NULL,NULL),('M-003','土建完成','W-001',NULL,NULL,'2024-05-30',NULL,NULL,NULL),('M-004','安装完成','W-002',NULL,NULL,'2024-06-15',NULL,NULL,NULL),('M-005','改造完成','W-003',NULL,NULL,'2024-08-30',NULL,NULL,NULL),('M-006','验收完成','W-003-1',NULL,NULL,'2024-09-15',NULL,NULL,NULL),('M-007','测试里程碑7','W-004',NULL,NULL,'2024-10-01',NULL,NULL,NULL),('M-008','土建施工完成',NULL,'N-001','A-001','2024-03-10',NULL,NULL,NULL),('M-009','设备安装完成',NULL,'N-001','A-002','2024-04-20',NULL,NULL,NULL),('M-010','系统调试完成',NULL,'N-002','A-003','2024-05-15',NULL,NULL,NULL),('M-011','线路铺设完成',NULL,'N-003','A-004','2024-04-10',NULL,NULL,NULL);
/*!40000 ALTER TABLE `dim_ps_milestone` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_ps_network`
--

DROP TABLE IF EXISTS `dim_ps_network`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_ps_network` (
  `aufnr` varchar(50) NOT NULL,
  `pspid` varchar(50) DEFAULT NULL,
  `pspnr` varchar(50) DEFAULT NULL,
  `auart` varchar(20) DEFAULT NULL,
  `autxt` varchar(255) DEFAULT NULL,
  `phas0` varchar(10) DEFAULT NULL,
  `sttxt` varchar(20) DEFAULT NULL,
  `gsbt` varchar(10) DEFAULT NULL,
  `werks` varchar(10) DEFAULT NULL,
  `bapi_create` varchar(100) DEFAULT NULL,
  `bapi_get` varchar(100) DEFAULT NULL,
  `objnr` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`aufnr`),
  KEY `idx_net_pspid` (`pspid`),
  KEY `idx_net_pspnr` (`pspnr`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_ps_network`
--

LOCK TABLES `dim_ps_network` WRITE;
/*!40000 ALTER TABLE `dim_ps_network` DISABLE KEYS */;
INSERT INTO `dim_ps_network` VALUES ('NET-001-01','P-2024-001','WBS-001-01','PS01','前期准备网络','001','REL','EL','1001','BAPI_NETWORK_CREATE','BAPI_NETWORK_GETINFO','OBJ_NET_001'),('NET-001-02','P-2024-001','WBS-001-02','PS01','设备采购网络','002','REL','EL','1001','BAPI_NETWORK_CREATE','BAPI_NETWORK_GETINFO','OBJ_NET_002'),('NET-001-03','P-2024-001','WBS-001-03','PS01','土建施工网络','003','REL','EL','1001','BAPI_NETWORK_CREATE','BAPI_NETWORK_GETINFO','OBJ_NET_003'),('NET-001-04','P-2024-001','WBS-001-04','PS01','电气安装网络','004','REL','EL','1001','BAPI_NETWORK_CREATE','BAPI_NETWORK_GETINFO','OBJ_NET_004'),('NET-001-05','P-2024-001','WBS-001-05','PS01','调试投产网络','005','CRTD','EL','1001','BAPI_NETWORK_CREATE','BAPI_NETWORK_GETINFO','OBJ_NET_005'),('NET-001-06','P-2024-002','WBS-002-01','PS01','配电网改造网络1','001','REL','EL','1002','BAPI_NETWORK_CREATE','BAPI_NETWORK_GETINFO','OBJ_NET_06'),('NET-001-07','P-2024-002','WBS-002-02','PS01','配电网改造网络2','002','REL','EL','1002','BAPI_NETWORK_CREATE','BAPI_NETWORK_GETINFO','OBJ_NET_07'),('NET-001-08','P-2024-002','WBS-002-03','PS01','配电网改造网络3','003','REL','EL','1002','BAPI_NETWORK_CREATE','BAPI_NETWORK_GETINFO','OBJ_NET_08'),('NET-002-01','P-2024-002','WBS-002-01','PS01','勘察设计网络','001','TECO','EL','1001','BAPI_NETWORK_CREATE','BAPI_NETWORK_GETINFO','OBJ_NET_006'),('NET-002-02','P-2024-002','WBS-002-02','PS01','线路改造网络','002','REL','EL','1001','BAPI_NETWORK_CREATE','BAPI_NETWORK_GETINFO','OBJ_NET_007'),('NET-002-03','P-2024-002','WBS-002-03','PS01','台区改造网络','003','REL','EL','1001','BAPI_NETWORK_CREATE','BAPI_NETWORK_GETINFO','OBJ_NET_008'),('NET-003-01','P-2024-003','WBS-003-01','PS01','旧表拆除网络','001','TECO','EL','1002','BAPI_NETWORK_CREATE','BAPI_NETWORK_GETINFO','OBJ_NET_009'),('NET-003-02','P-2024-003','WBS-003-02','PS01','新表安装网络','002','TECO','EL','1002','BAPI_NETWORK_CREATE','BAPI_NETWORK_GETINFO','OBJ_NET_010'),('NET-003-03','P-2024-003','WBS-003-03','PS01','系统调试网络','003','TECO','EL','1002','BAPI_NETWORK_CREATE','BAPI_NETWORK_GETINFO','OBJ_NET_011');
/*!40000 ALTER TABLE `dim_ps_network` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_ps_network_activity`
--

DROP TABLE IF EXISTS `dim_ps_network_activity`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_ps_network_activity` (
  `activity_number` varchar(255) NOT NULL,
  `network_number` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `activity_type` varchar(255) DEFAULT NULL,
  `control_key` varchar(255) DEFAULT NULL,
  `work_center` varchar(255) DEFAULT NULL,
  `planned_work` decimal(20,4) DEFAULT NULL,
  `work_unit` varchar(255) DEFAULT NULL,
  `plan_start_date` date DEFAULT NULL,
  `plan_finish_date` date DEFAULT NULL,
  `duration` decimal(20,4) DEFAULT NULL,
  `duration_unit` varchar(255) DEFAULT NULL,
  `objnr` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`activity_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_ps_network_activity`
--

LOCK TABLES `dim_ps_network_activity` WRITE;
/*!40000 ALTER TABLE `dim_ps_network_activity` DISABLE KEYS */;
INSERT INTO `dim_ps_network_activity` VALUES ('A-001','NET-001-01','土建施工','PS01','PS01','PS01',240.0000,'H','2024-02-01','2024-03-01',30.0000,'D','OBJ_NA_001'),('A-002','NET-001-01','设备安装','PS01','PS02','PS01',360.0000,'H','2024-02-01','2024-03-01',45.0000,'D','OBJ_NA_002'),('A-003','NET-001-02','系统调试','PS01','PS03','PS01',120.0000,'H','2024-02-01','2024-03-01',15.0000,'D','OBJ_NA_003'),('A-004','NET-001-03','线路铺设','PS01','PS01','PS02',480.0000,'H','2024-02-01','2024-03-01',60.0000,'D','OBJ_NA_004'),('A-005','NET-001-03','设备调试','PS01','PS03','PS02',160.0000,'H','2024-02-01','2024-03-01',20.0000,'D','OBJ_NA_005'),('A-006','NET-001-04','测试活动6','PS01','PS01','GS01',80.0000,'H','2024-02-01','2024-03-01',10.0000,'D','OBJ_NA_006'),('A-007','NET-001-05','测试活动7','PS01','PS01','GS01',80.0000,'H','2024-02-01','2024-03-01',10.0000,'D','OBJ_NA_007'),('A-008','NET-002-01','测试活动8','PS01','PS01','GS01',80.0000,'H','2024-02-01','2024-03-01',10.0000,'D','OBJ_NA_008'),('A-009','NET-002-02','测试活动9','PS01','PS01','GS01',80.0000,'H','2024-02-01','2024-03-01',10.0000,'D','OBJ_NA_009'),('A-010','NET-002-03','测试活动10','PS01','PS01','GS01',80.0000,'H','2024-02-01','2024-03-01',10.0000,'D','OBJ_NA_010');
/*!40000 ALTER TABLE `dim_ps_network_activity` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_ps_network_component`
--

DROP TABLE IF EXISTS `dim_ps_network_component`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_ps_network_component` (
  `component_id` varchar(255) NOT NULL,
  `network_number` varchar(255) DEFAULT NULL,
  `activity_number` varchar(255) DEFAULT NULL,
  `material_number` varchar(255) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `requirement_quantity` decimal(20,4) DEFAULT NULL,
  `base_unit` varchar(255) DEFAULT NULL,
  `requirement_date` date DEFAULT NULL,
  `plant` varchar(255) DEFAULT NULL,
  `item_category` varchar(255) DEFAULT NULL,
  `reservation_number` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`component_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_ps_network_component`
--

LOCK TABLES `dim_ps_network_component` WRITE;
/*!40000 ALTER TABLE `dim_ps_network_component` DISABLE KEYS */;
INSERT INTO `dim_ps_network_component` VALUES ('NC-001','NET-001-01','A-001','M001','光伏组件',1000.0000,'块','2024-03-01','PL01','L','R001'),('NC-002','NET-001-01','A-002','M002','逆变器',50.0000,'台','2024-04-01','PL01','L','R002'),('NC-003','NET-001-02','A-003','M003','调试设备',5.0000,'套','2024-05-01','PL01','L','R003'),('NC-004','NET-001-03','A-004','M004','电缆',5000.0000,'米','2024-03-15','PL02','L','R004'),('NC-005','NET-001-03','A-005','M005','变压器',2.0000,'台','2024-04-15','PL02','L','R005'),('NC-006','NET-001-04','A-006','M006','测试物料6',100.0000,'个','2024-06-01','PL01','L','R006'),('NC-007','NET-001-05','A-007','M007','测试物料7',100.0000,'个','2024-06-01','PL01','L','R007'),('NC-008','NET-001-06','A-008','M008','测试物料8',100.0000,'个','2024-06-01','PL01','L','R008'),('NC-009','NET-001-07','A-009','M009','测试物料9',100.0000,'个','2024-06-01','PL01','L','R009'),('NC-010','NET-001-08','A-010','M010','测试物料10',100.0000,'个','2024-06-01','PL01','L','R010');
/*!40000 ALTER TABLE `dim_ps_network_component` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_ps_object_status`
--

DROP TABLE IF EXISTS `dim_ps_object_status`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_ps_object_status` (
  `objnr` varchar(255) NOT NULL,
  `status_code` varchar(255) NOT NULL,
  `status_type` varchar(255) DEFAULT NULL,
  `status_name` varchar(255) DEFAULT NULL,
  `active_flag` varchar(255) DEFAULT NULL,
  `object_type` varchar(255) DEFAULT NULL,
  `change_date` date DEFAULT NULL,
  PRIMARY KEY (`objnr`,`status_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_ps_object_status`
--

LOCK TABLES `dim_ps_object_status` WRITE;
/*!40000 ALTER TABLE `dim_ps_object_status` DISABLE KEYS */;
INSERT INTO `dim_ps_object_status` VALUES ('OBJ_NA_001','REL','系统状态','已释放','1','NA','2024-02-01'),('OBJ_NA_002','REL','系统状态','已释放','1','NA','2024-02-15'),('OBJ_NA_003','TECO','系统状态','技术完成','1','NA','2024-05-20'),('OBJ_NET_001','REL','系统状态','已释放','1','NET','2026-07-30'),('OBJ_NET_002','CRTD','系统状态','已创建','1','NET','2026-07-30'),('OBJ_NET_003','REL','系统状态','已释放','1','NET','2026-07-30'),('OBJ_NET_004','CRTD','系统状态','已创建','1','NET','2026-07-30'),('OBJ_NET_005','REL','系统状态','已释放','1','NET','2026-07-30'),('OBJ_NET_006','CRTD','系统状态','已创建','1','NET','2026-07-30'),('OBJ_NET_007','REL','系统状态','已释放','1','NET','2026-07-30'),('OBJ_NET_008','CRTD','系统状态','已创建','1','NET','2026-07-30'),('OBJ_NET_009','REL','系统状态','已释放','1','NET','2026-07-30'),('OBJ_NET_010','CRTD','系统状态','已创建','1','NET','2026-07-30'),('OBJ_NET_011','REL','系统状态','已释放','1','NET','2026-07-30'),('OBJ_PD_001','REL','系统状态','已释放','1','PD','2024-01-15'),('OBJ_PD_002','REL','系统状态','已释放','1','PD','2024-03-01'),('OBJ_PD_003','CRTD','系统状态','已创建','1','PD','2024-01-01'),('OBJ_PD_004','CRTD','系统状态','已创建','1','PD','2024-01-01'),('OBJ_PD_005','CRTD','系统状态','已创建','1','PD','2024-01-01'),('OBJ_PD_006','CRTD','系统状态','已创建','1','PD','2024-01-01'),('OBJ_PD_007','CRTD','系统状态','已创建','1','PD','2024-01-01'),('OBJ_PD_008','CRTD','系统状态','已创建','1','PD','2024-01-01'),('OBJ_PD_009','CRTD','系统状态','已创建','1','PD','2024-01-01'),('OBJ_PD_010','CRTD','系统状态','已创建','1','PD','2024-01-01'),('OBJ_WBS_001','REL','系统状态','已释放','1','WBS','2024-01-16'),('OBJ_WBS_002','TECO','系统状态','技术完成','1','WBS','2024-06-01');
/*!40000 ALTER TABLE `dim_ps_object_status` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_ps_project_def`
--

DROP TABLE IF EXISTS `dim_ps_project_def`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_ps_project_def` (
  `pspid` varchar(50) NOT NULL,
  `proj_desc` varchar(255) DEFAULT NULL,
  `proj_type` varchar(20) DEFAULT NULL,
  `proj_area` varchar(20) DEFAULT NULL,
  `proj_resp` varchar(50) DEFAULT NULL,
  `plant` varchar(10) DEFAULT NULL,
  `controlling_area` varchar(10) DEFAULT NULL,
  `company_code` varchar(10) DEFAULT NULL,
  `start_date` date DEFAULT NULL,
  `finish_date` date DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `priority` varchar(10) DEFAULT NULL,
  `budget_amount` decimal(15,2) DEFAULT NULL,
  `currency` varchar(5) DEFAULT NULL,
  `created_date` date DEFAULT NULL,
  `created_by` varchar(50) DEFAULT NULL,
  `bapi_create` varchar(100) DEFAULT NULL,
  `bapi_get` varchar(100) DEFAULT NULL,
  `bapi_change` varchar(100) DEFAULT NULL,
  `objnr` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`pspid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_ps_project_def`
--

LOCK TABLES `dim_ps_project_def` WRITE;
/*!40000 ALTER TABLE `dim_ps_project_def` DISABLE KEYS */;
INSERT INTO `dim_ps_project_def` VALUES ('P-2024-001','某省电力公司110kV输变电工程','PSTD','华东','张工','1001','CO01','1000','2024-03-01','2024-12-31','REL','高',15000000.00,'CNY','2024-02-20','admin','BAPI_BUS2001_CREATE','BAPI_BUS2001_GET_DATA','BAPI_BUS2001_CHANGE','OBJ_PD_001'),('P-2024-002','城区配电网改造工程','PROJ','华东','李工','1001','CO01','1000','2024-05-10','2025-02-28','REL','中',8200000.00,'CNY','2024-04-15','admin','BAPI_BUS2001_CREATE','BAPI_BUS2001_GET_DATA','BAPI_BUS2001_CHANGE','OBJ_PD_002'),('P-2024-003','智能电表换装工程','PROJ','华北','王工','1002','CO01','1000','2024-06-01','2024-09-30','TECO','中',3500000.00,'CNY','2024-05-10','admin','BAPI_BUS2001_CREATE','BAPI_BUS2001_GET_DATA','BAPI_BUS2001_CHANGE','OBJ_PD_003');
/*!40000 ALTER TABLE `dim_ps_project_def` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_ps_wbs_budget`
--

DROP TABLE IF EXISTS `dim_ps_wbs_budget`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_ps_wbs_budget` (
  `budget_id` varchar(255) NOT NULL,
  `wbs_element` varchar(255) DEFAULT NULL,
  `fiscal_year` varchar(255) DEFAULT NULL,
  `total_budget` decimal(20,4) DEFAULT NULL,
  `distributed_budget` decimal(20,4) DEFAULT NULL,
  `released_budget` decimal(20,4) DEFAULT NULL,
  `available_budget` decimal(20,4) DEFAULT NULL,
  `currency` varchar(255) DEFAULT NULL,
  `budget_profile` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`budget_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_ps_wbs_budget`
--

LOCK TABLES `dim_ps_wbs_budget` WRITE;
/*!40000 ALTER TABLE `dim_ps_wbs_budget` DISABLE KEYS */;
INSERT INTO `dim_ps_wbs_budget` VALUES ('B-001','W-001','2024',50000000.0000,30000000.0000,20000000.0000,20000000.0000,'CNY','BP01'),('B-002','W-001-2','2024',20000000.0000,15000000.0000,10000000.0000,5000000.0000,'CNY','BP01'),('B-003','W-001-2-1','2024',10000000.0000,8000000.0000,5000000.0000,2000000.0000,'CNY','BP01'),('B-004','W-001-2-1-1','2024',5000000.0000,3000000.0000,2000000.0000,2000000.0000,'CNY','BP01'),('B-005','W-002','2024',8000000.0000,5000000.0000,3000000.0000,3000000.0000,'CNY','BP01'),('B-006','W-003','2024',15000000.0000,10000000.0000,8000000.0000,5000000.0000,'CNY','BP01'),('B-007','W-003-1','2024',8000000.0000,5000000.0000,3000000.0000,3000000.0000,'CNY','BP01'),('B-008','W-004','2024',5000000.0000,3000000.0000,2000000.0000,2000000.0000,'CNY','BP01'),('B-009','W-005','2024',3000000.0000,2000000.0000,1000000.0000,1000000.0000,'CNY','BP01'),('B-010','W-006','2024',3000000.0000,2000000.0000,1000000.0000,1000000.0000,'CNY','BP01');
/*!40000 ALTER TABLE `dim_ps_wbs_budget` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_ps_wbs_cost`
--

DROP TABLE IF EXISTS `dim_ps_wbs_cost`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_ps_wbs_cost` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cost_id` varchar(255) DEFAULT NULL,
  `wbs_element` varchar(255) DEFAULT NULL,
  `fiscal_year` varchar(255) DEFAULT NULL,
  `cost_element` varchar(255) DEFAULT NULL,
  `actual_cost` varchar(255) DEFAULT NULL,
  `committed_cost` varchar(255) DEFAULT NULL,
  `planned_cost` varchar(255) DEFAULT NULL,
  `variance` varchar(255) DEFAULT NULL,
  `currency` varchar(255) DEFAULT NULL,
  `posting_date` date DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_ps_wbs_cost`
--

LOCK TABLES `dim_ps_wbs_cost` WRITE;
/*!40000 ALTER TABLE `dim_ps_wbs_cost` DISABLE KEYS */;
INSERT INTO `dim_ps_wbs_cost` VALUES (1,'C-001','W-001','2024','500000','35000000','2000000','37000000','-2000000','CNY','2024-12-31'),(2,'C-002','W-001-2','2024','500001','18000000','500000','18500000','1500000','CNY','2024-12-31'),(3,'C-003','W-001-2-1','2024','500002','9000000','300000','9300000','700000','CNY','2024-12-31'),(4,'C-004','W-001-2-1-1','2024','500003','4500000','100000','4600000','400000','CNY','2024-12-31'),(5,'C-005','W-002','2024','500004','7000000','500000','7500000','500000','CNY','2024-12-31'),(6,'C-006','W-003','2024','500005','13000000','800000','13800000','1200000','CNY','2024-12-31'),(7,'C-007','W-003-1','2024','500006','7000000','300000','7300000','700000','CNY','2024-12-31'),(8,'C-008','W-004','2024','500007','4000000','200000','4200000','800000','CNY','2024-12-31'),(9,'C-009','W-005','2024','500008','2500000','100000','2600000','400000','CNY','2024-12-31'),(10,'C-010','W-006','2024','500009','2500000','100000','2600000','400000','CNY','2024-12-31');
/*!40000 ALTER TABLE `dim_ps_wbs_cost` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dim_ps_wbs_element`
--

DROP TABLE IF EXISTS `dim_ps_wbs_element`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dim_ps_wbs_element` (
  `wbs_element` varchar(255) NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  `project_definition` varchar(255) DEFAULT NULL,
  `parent_wbs` varchar(255) DEFAULT NULL,
  `wbs_level` int DEFAULT NULL,
  `person_responsible` varchar(255) DEFAULT NULL,
  `accounting_flag` varchar(255) DEFAULT NULL,
  `plan_start_date` date DEFAULT NULL,
  `plan_finish_date` date DEFAULT NULL,
  `company_code` varchar(255) DEFAULT NULL,
  `profit_center` varchar(255) DEFAULT NULL,
  `cost_center` varchar(255) DEFAULT NULL,
  `settlement_profile` varchar(255) DEFAULT NULL,
  `objnr` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`wbs_element`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dim_ps_wbs_element`
--

LOCK TABLES `dim_ps_wbs_element` WRITE;
/*!40000 ALTER TABLE `dim_ps_wbs_element` DISABLE KEYS */;
INSERT INTO `dim_ps_wbs_element` VALUES ('W-001','光伏电站一级WBS','P-2024-001',NULL,1,'负责人','X','2024-01-01','2024-12-31','CC01','PC01','CC01',NULL,'OBJ_WBS_001'),('W-001-2','光伏电站二级WBS','P-2024-001','W-001',2,'负责人','X','2024-01-01','2024-12-31','CC01','PC01','CC01',NULL,'OBJ_WBS_002'),('W-001-2-1','光伏电站三级WBS','P-2024-001','W-001-2',3,'负责人','X','2024-01-01','2024-12-31','CC01','PC01','CC01',NULL,'OBJ_WBS_003'),('W-001-2-1-1','光伏电站四级WBS','P-2024-001','W-001-2-1',4,'负责人','X','2024-01-01','2024-12-31','CC01','PC01','CC01',NULL,'OBJ_WBS_004'),('W-002','土建工程WBS','P-2024-001',NULL,1,'负责人','X','2024-01-01','2024-12-31','CC01','PC01','CC01',NULL,'OBJ_WBS_005'),('W-003','配电工程WBS','P-2024-002',NULL,1,'负责人','X','2024-01-01','2024-12-31','CC01','PC01','CC01',NULL,'OBJ_WBS_006'),('W-003-1','配电二级WBS','P-2024-002','W-003',2,'负责人','X','2024-01-01','2024-12-31','CC01','PC01','CC01',NULL,'OBJ_WBS_007'),('W-004','测试WBS1','P-2024-002',NULL,1,'负责人','X','2024-01-01','2024-12-31','CC01','PC01','CC01',NULL,'OBJ_WBS_008'),('W-005','测试WBS2','P-2024-003',NULL,1,'负责人','X','2024-01-01','2024-12-31','CC01','PC01','CC01',NULL,'OBJ_WBS_009'),('W-006','测试WBS3','P-2024-004',NULL,1,'负责人','X','2024-01-01','2024-12-31','CC01','PC01','CC01',NULL,'OBJ_WBS_010');
/*!40000 ALTER TABLE `dim_ps_wbs_element` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bilg_addl_charg_mi`
--

DROP TABLE IF EXISTS `dwd_cst_bilg_addl_charg_mi`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bilg_addl_charg_mi` (
  `addl_charg_id` int NOT NULL,
  `calc_id` int DEFAULT NULL,
  `qty_charg_ym` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `addl_num` int DEFAULT NULL,
  `addl_prc` double DEFAULT NULL,
  `addl_amt` double DEFAULT NULL,
  `addl_charg_ctlg` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `addl_charg_ctlg_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctlg_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctlg_cls_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_io_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bilg_card_id` int DEFAULT NULL,
  `prc_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bilg_std_ver_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_ind_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_ind_cls_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_ind_ustry_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_ind_cls_desc_1` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp_attr_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp_attr_cls_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exec_rng_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exec_rng_type_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctlg_prc_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `disc_mode_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `disc_mode_cls_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_volt_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_volt_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_ec_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_ec_categ_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_snap_id` int DEFAULT NULL,
  `inst_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_mode_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_usage_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_usage_type_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_char` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_char_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` int DEFAULT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_cons_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_cons_type_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_mode_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_pscateg` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_pscateg_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gc_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gc_type_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_consp_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_consp_mode_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_cls_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_ind_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_ind_cls_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_ind_ustry_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_ind_cls_desc_1` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `high_ec_ind_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `high_ec_ind_cls_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_volt_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_volt_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_ec_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_ec_categ_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_cap` double DEFAULT NULL,
  `run_cap` double DEFAULT NULL,
  `impt_lv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `impt_lv_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `urbanruran_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `urbanruran_categ_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `calc_bus_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `calc_bus_type_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `area` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `write_time` datetime DEFAULT NULL,
  PRIMARY KEY (`addl_charg_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bilg_addl_charg_mi`
--

LOCK TABLES `dwd_cst_bilg_addl_charg_mi` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bilg_addl_charg_mi` DISABLE KEYS */;
INSERT INTO `dwd_cst_bilg_addl_charg_mi` VALUES (604980,509238,'479',388879,2921.86,4935.44,'加收项：加收的项_3','加收项名称：加收项描3','目录分类：根据公_3','目录分类描述测试数据3','PL-0003','价内外标志：用于_3','服务种类_3','服务种类描述测试数据3',421385,'PR-0003','BI-0003','行业分类_电价：_3','行业分类描述测试数据3','产业分类_3','一级行业分类测试数据3','40561.15','42453.03','执行范围分类：安_3','执行范围分类描述测试数据3','目录定价名称：价格名3','华能集团','优惠方式分类描述测试数据3','PR-0003','电压等级描述：承测试数据3','PR-0003','用能类别描述_电测试数据3','电价类别：居民一_3',715628,'INS0003','IN-0003','计量方式：安装点_3','计量方式描述测试数据3','安装点用途类型：_3','安装点用途类型描测试数据3','安装点性质：安装_3','安装点性质描述测试数据3',571142,'CU-0003','客户名称：客户的名称3','发用电户类型_3','发用电户类型描述测试数据3','发电方式：客户快_3','发电方式描述测试数据3','客户电源类别：客_3','客户电源类别描述测试数据3','发电客户类型：客_3','发电客户类型描述测试数据3','能源消纳方式：客_3','能源消纳方式描述测试数据3','客户分类：客户快_3','客户分类描述测试数据3','行业分类：客户快_3','行业分类描述测试数据3','产业分类_3','一级行业分类测试数据3','高耗能行业类别：_3','高耗能行业类别描测试数据3','CU-0003','承压描述测试数据3','用能类别：客户快_3','用能类别描述测试数据3',8285.24,7080.05,'重要性等级：客户_3','重要性等级描述测试数据3','城乡类别：客户快_3','城乡类别描述测试数据3','量费计算业务类型_3','量费计算业务类型测试数据3','MG-0003','管理单位名称3','所属区域_3','PR-0003','所属省公司名称3','CI-0003','所属市公司名称3','CO-0003','所属县公司名称3','区域层级：01国_3','区域层级描述测试数据3','2024-06-06 19:00:00'),(633838,365715,'185',614461,2075.89,7677.09,'加收项：加收的项_2','加收项名称：加收项描2','目录分类：根据公_2','目录分类描述测试数据2','PL-0002','价内外标志：用于_2','服务种类_2','服务种类描述测试数据2',523119,'PR-0002','BI-0002','行业分类_电价：_2','行业分类描述测试数据2','产业分类_2','一级行业分类测试数据2','67445.12','56878.36','执行范围分类：安_2','执行范围分类描述测试数据2','目录定价名称：价格名2','华能集团','优惠方式分类描述测试数据2','PR-0002','电压等级描述：承测试数据2','PR-0002','用能类别描述_电测试数据2','电价类别：居民一_2',481266,'INS0002','IN-0002','计量方式：安装点_2','计量方式描述测试数据2','安装点用途类型：_2','安装点用途类型描测试数据2','安装点性质：安装_2','安装点性质描述测试数据2',291575,'CU-0002','客户名称：客户的名称2','发用电户类型_2','发用电户类型描述测试数据2','发电方式：客户快_2','发电方式描述测试数据2','客户电源类别：客_2','客户电源类别描述测试数据2','发电客户类型：客_2','发电客户类型描述测试数据2','能源消纳方式：客_2','能源消纳方式描述测试数据2','客户分类：客户快_2','客户分类描述测试数据2','行业分类：客户快_2','行业分类描述测试数据2','产业分类_2','一级行业分类测试数据2','高耗能行业类别：_2','高耗能行业类别描测试数据2','CU-0002','承压描述测试数据2','用能类别：客户快_2','用能类别描述测试数据2',587.5,2907.25,'重要性等级：客户_2','重要性等级描述测试数据2','城乡类别：客户快_2','城乡类别描述测试数据2','量费计算业务类型_2','量费计算业务类型测试数据2','MG-0002','管理单位名称2','所属区域_2','PR-0002','所属省公司名称2','CI-0002','所属市公司名称2','CO-0002','所属县公司名称2','区域层级：01国_2','区域层级描述测试数据2','2025-04-09 14:00:00'),(970502,663346,'106',327337,3743.48,7163.28,'加收项：加收的项_1','加收项名称：加收项描1','目录分类：根据公_1','目录分类描述测试数据1','PL-0001','价内外标志：用于_1','服务种类_1','服务种类描述测试数据1',928741,'PR-0001','BI-0001','行业分类_电价：_1','行业分类描述测试数据1','产业分类_1','一级行业分类测试数据1','62163.3','16213.43','执行范围分类：安_1','执行范围分类描述测试数据1','目录定价名称：价格名1','大唐集团','优惠方式分类描述测试数据1','PR-0001','电压等级描述：承测试数据1','PR-0001','用能类别描述_电测试数据1','电价类别：居民一_1',404204,'INS0001','IN-0001','计量方式：安装点_1','计量方式描述测试数据1','安装点用途类型：_1','安装点用途类型描测试数据1','安装点性质：安装_1','安装点性质描述测试数据1',187006,'CU-0001','客户名称：客户的名称1','发用电户类型_1','发用电户类型描述测试数据1','发电方式：客户快_1','发电方式描述测试数据1','客户电源类别：客_1','客户电源类别描述测试数据1','发电客户类型：客_1','发电客户类型描述测试数据1','能源消纳方式：客_1','能源消纳方式描述测试数据1','客户分类：客户快_1','客户分类描述测试数据1','行业分类：客户快_1','行业分类描述测试数据1','产业分类_1','一级行业分类测试数据1','高耗能行业类别：_1','高耗能行业类别描测试数据1','CU-0001','承压描述测试数据1','用能类别：客户快_1','用能类别描述测试数据1',2418.63,6997.42,'重要性等级：客户_1','重要性等级描述测试数据1','城乡类别：客户快_1','城乡类别描述测试数据1','量费计算业务类型_1','量费计算业务类型测试数据1','MG-0001','管理单位名称1','所属区域_1','PR-0001','所属省公司名称1','CI-0001','所属市公司名称1','CO-0001','所属县公司名称1','区域层级：01国_1','区域层级描述测试数据1','2025-03-30 22:00:00');
/*!40000 ALTER TABLE `dwd_cst_bilg_addl_charg_mi` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bilg_cash_chk_rec_df`
--

DROP TABLE IF EXISTS `dwd_cst_bilg_cash_chk_rec_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bilg_cash_chk_rec_df` (
  `cash_chk_rec_id` int NOT NULL,
  `cash_chk_amt` double DEFAULT NULL,
  `cash_chk_stf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cash_chk_bank` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cash_chk_bank_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cash_chk_bank_acct` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cash_chk_date` datetime DEFAULT NULL,
  `cash_chk_stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cash_chk_stat_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acct_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp_cls_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_chan` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_chan_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_mode_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_stf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_num` int DEFAULT NULL,
  `setl_note_bank` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bank_arr_acct_stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bank_arr_acct_stat_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bank_arr_acct_hndl_date` datetime DEFAULT NULL,
  `bank_arr_acct_handler` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bank_arr_acct_date` datetime DEFAULT NULL,
  `bank_arr_acct_rcpt_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cap_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chan_cls_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chan_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chan_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_form_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_card_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prft_center` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_note_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_stf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_date` datetime DEFAULT NULL,
  `veri_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_type_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cross_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cross_flag_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acctg_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `coll_amt_org` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `area` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `write_time` datetime DEFAULT NULL,
  PRIMARY KEY (`cash_chk_rec_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bilg_cash_chk_rec_df`
--

LOCK TABLES `dwd_cst_bilg_cash_chk_rec_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bilg_cash_chk_rec_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bilg_cash_chk_rec_df` VALUES (223707,2791.29,'解款人员：解款记_2','62220073278399909','解款银行名称2','62220064562504665','2024-05-26 10:00:00','启用','异常','AC-0002','65689.87','76535.8','国家电投','交费渠道描述测试数据2','62220035826511491','支付方式描述测试数据2','收费人员：解款记_2',271054,'SE-0002','正常','正常','2024-05-29 01:00:00','62220049243632175','2024-03-21 05:00:00','BA-0002','CA-0002','CH-0002','CH-0002','渠道名称：渠道的名称2','服务形式：线上/测试数据2','E-0002','大唐集团','国网电力公司','SE-0002','核定人员_2','2024-05-10 21:00:00','62220090294139332','核定类型描述测试数据2','跨月标志：（是/_2','跨月标志描述测试数据2','2024-01-25 00:00:00','大唐集团','管理单位名称2','所属区域_2','PR-0002','所属省公司名称2','CI-0002','所属市公司名称2','CO-0002','所属县公司名称2','区域层级：01国_2','区域层级描述测试数据2','2024-07-23 17:00:00'),(619682,8365.34,'解款人员：解款记_3','62220048640912755','解款银行名称3','62220055191858639','2024-10-04 17:00:00','启用','正常','AC-0003','24956.68','22566.45','南方电网公司','交费渠道描述测试数据3','62220072997292199','支付方式描述测试数据3','收费人员：解款记_3',60737,'SE-0003','激活','正常','2024-06-09 23:00:00','62220036391828710','2024-10-25 08:00:00','BA-0003','CA-0003','CH-0003','CH-0003','渠道名称：渠道的名称3','服务形式：线上/测试数据3','E-0003','国网电力公司','国家电投','SE-0003','核定人员_3','2024-06-02 15:00:00','62220089348070527','核定类型描述测试数据3','跨月标志：（是/_3','跨月标志描述测试数据3','2024-01-04 00:00:00','南方电网公司','管理单位名称3','所属区域_3','PR-0003','所属省公司名称3','CI-0003','所属市公司名称3','CO-0003','所属县公司名称3','区域层级：01国_3','区域层级描述测试数据3','2024-06-03 13:00:00'),(860400,4092.01,'解款人员：解款记_1','62220053447876493','解款银行名称1','62220069345898289','2024-10-13 05:00:00','停用','启用','AC-0001','3656.52','84844.07','华能集团','交费渠道描述测试数据1','62220054622628664','支付方式描述测试数据1','收费人员：解款记_1',336173,'SE-0001','停用','停用','2024-12-26 11:00:00','62220027009714943','2024-09-05 23:00:00','BA-0001','CA-0001','CH-0001','CH-0001','渠道名称：渠道的名称1','服务形式：线上/测试数据1','E-0001','大唐集团','国网电力公司','SE-0001','核定人员_1','2024-11-14 12:00:00','62220089533156971','核定类型描述测试数据1','跨月标志：（是/_1','跨月标志描述测试数据1','2024-07-05 00:00:00','南方电网公司','管理单位名称1','所属区域_1','PR-0001','所属省公司名称1','CI-0001','所属市公司名称1','CO-0001','所属县公司名称1','区域层级：01国_1','区域层级描述测试数据1','2024-07-04 18:00:00');
/*!40000 ALTER TABLE `dwd_cst_bilg_cash_chk_rec_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bilg_charg_acct_mi`
--

DROP TABLE IF EXISTS `dwd_cst_bilg_charg_acct_mi`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bilg_charg_acct_mi` (
  `charg_acct_id` int NOT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_date` datetime DEFAULT NULL,
  `charg_amt` double DEFAULT NULL,
  `charg_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_type_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_chan` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_chan_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_form_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chan_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chan_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_mode_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chan_cls_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chan_cls_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acct_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acct_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acct_date` datetime DEFAULT NULL,
  `prtr_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_cls_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_order_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cap_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `branch_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `trans_run_acct_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_order_id` int DEFAULT NULL,
  `cash_chk_rec_id` int DEFAULT NULL,
  `settle_acct_id` int DEFAULT NULL,
  `settle_acct_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_acct_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_acct_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_acct_categ_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prepay_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prepay_mode_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_chan_org` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `coll_amt_org_prft_center` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_prft_center` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `area` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_char` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_char_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `write_time` datetime DEFAULT NULL,
  PRIMARY KEY (`charg_acct_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bilg_charg_acct_mi`
--

LOCK TABLES `dwd_cst_bilg_charg_acct_mi` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bilg_charg_acct_mi` DISABLE KEYS */;
INSERT INTO `dwd_cst_bilg_charg_acct_mi` VALUES (277183,'CU-0002','客户名称2','收费年月：该笔交_2','2024-06-21 04:00:00',82.08,'华能集团','收费类型描述测试数据2','华能集团','交费渠道描述测试数据2','服务形式：线上/测试数据2','CH-0002','渠道名称：渠道的名称2','62220037717811859','支付方式描述测试数据2','CH-0002','渠道分类描述测试数据2','AC-0002','记账年月：该笔交_2','2024-02-04 11:00:00','PR-0002','用户分类：客户分_2','用户分类描述测试数据2','PA-0002','CA-0002','BR-0002','TR-0002',751909,595101,979803,'SE-0002','结算账户名称：债务结2','67965.49','结算账户类别描述测试数据2','22619.03','13594.11','付费方式描述测试数据2','MG-0002','华能集团','华能集团','国网电力公司','服务种类描述测试数据2','MG-0002','管理单位名称2','所属区域_2','PR-0002','所属省公司名称2','CI-0002','所属市公司名称2','CO-0002','所属县公司名称2','国网电力公司','国家电投','区域层级：01国_2','区域层级描述测试数据2','2024-01-16 20:00:00'),(486494,'CU-0001','客户名称1','收费年月：该笔交_1','2025-02-01 01:00:00',3524.37,'国家电投','收费类型描述测试数据1','国网电力公司','交费渠道描述测试数据1','服务形式：线上/测试数据1','CH-0001','渠道名称：渠道的名称1','62220097947284088','支付方式描述测试数据1','CH-0001','渠道分类描述测试数据1','AC-0001','记账年月：该笔交_1','2024-06-25 03:00:00','PR-0001','用户分类：客户分_1','用户分类描述测试数据1','PA-0001','CA-0001','BR-0001','TR-0001',968265,780274,944751,'SE-0001','结算账户名称：债务结1','51464.65','结算账户类别描述测试数据1','13067.4','31052.11','付费方式描述测试数据1','MG-0001','国网电力公司','国家电投','国家电投','服务种类描述测试数据1','MG-0001','管理单位名称1','所属区域_1','PR-0001','所属省公司名称1','CI-0001','所属市公司名称1','CO-0001','所属县公司名称1','国网电力公司','国网电力公司','区域层级：01国_1','区域层级描述测试数据1','2024-05-07 17:00:00'),(743988,'CU-0003','客户名称3','收费年月：该笔交_3','2025-04-09 11:00:00',6409.3,'国网电力公司','收费类型描述测试数据3','南方电网公司','交费渠道描述测试数据3','服务形式：线上/测试数据3','CH-0003','渠道名称：渠道的名称3','62220052467163240','支付方式描述测试数据3','CH-0003','渠道分类描述测试数据3','AC-0003','记账年月：该笔交_3','2025-04-03 06:00:00','PR-0003','用户分类：客户分_3','用户分类描述测试数据3','PA-0003','CA-0003','BR-0003','TR-0003',43560,863879,15092,'SE-0003','结算账户名称：债务结3','13449.91','结算账户类别描述测试数据3','32452.86','7013.94','付费方式描述测试数据3','MG-0003','南方电网公司','南方电网公司','国家电投','服务种类描述测试数据3','MG-0003','管理单位名称3','所属区域_3','PR-0003','所属省公司名称3','CI-0003','所属市公司名称3','CO-0003','所属县公司名称3','华能集团','国网电力公司','区域层级：01国_3','区域层级描述测试数据3','2024-02-03 11:00:00');
/*!40000 ALTER TABLE `dwd_cst_bilg_charg_acct_mi` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bilg_charg_pay_info_di`
--

DROP TABLE IF EXISTS `dwd_cst_bilg_charg_pay_info_di`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bilg_charg_pay_info_di` (
  `PAY_ORDER_ID` int NOT NULL,
  `pay_order_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `CHARG_YM` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `CHARG_DATE` datetime DEFAULT NULL,
  `pay_amt` double DEFAULT NULL,
  `pay_chan` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_chan_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_stat` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chan_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `branch_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_tel` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chan_cls_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_batch_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_stf` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_dept` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_org` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_note_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_note_bank` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pos_run_acct_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bank_cap_run_acct_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_card_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `trml_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rela_id` int DEFAULT NULL,
  `charg_acct_cnt` int DEFAULT NULL,
  `charg_acct_id` int DEFAULT NULL,
  `charg_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_amt` double DEFAULT NULL,
  `cap_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvd_acct_id` int DEFAULT NULL,
  `setl_acct_id` int DEFAULT NULL,
  `rcvd_amt` double DEFAULT NULL,
  `rcvbl_acct_id` int DEFAULT NULL,
  `rcvbl_amt` double DEFAULT NULL,
  `arer_bal` double DEFAULT NULL,
  `rcvd_adv_acct_id` int DEFAULT NULL,
  `RCVD_ADV_AMT` double DEFAULT NULL,
  `this_bal` double DEFAULT NULL,
  `bal_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bal_type_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `OP_EXP_RCVD_ID` int DEFAULT NULL,
  `RCVD_EXP_AMT` double DEFAULT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_addr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `impt_lv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `high_ec_ind_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dereg_attr_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dereg_attr_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `coll_amt_org_prft_center` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `area` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_char` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_char_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `write_time` datetime DEFAULT NULL,
  PRIMARY KEY (`PAY_ORDER_ID`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bilg_charg_pay_info_di`
--

LOCK TABLES `dwd_cst_bilg_charg_pay_info_di` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bilg_charg_pay_info_di` DISABLE KEYS */;
INSERT INTO `dwd_cst_bilg_charg_pay_info_di` VALUES (78174,'PA-0003','支付年月_3','2024-04-25 18:00:00',5308.76,'支付渠道_3','支付渠道名称3','支付方式_3','支付方式名称3','启用','CH-0003','BR-0003','联系人_3','13854938456','CH-0003','PA-0003','收费人员_3','收费部门_3','国网电力公司','SE-0003','SE-0003','PO-0003','BA-0003','E-0003','TR-0003',749877,117451,574540,'收费类型_3','收费类型名称3',3567.49,'CA-0003',210959,759587,8312.25,876335,42.96,1619.37,808453,6241.32,1212.67,'南方电网公司','结余类型描述测试数据3',654311,682.46,'CU-0003','客户名称3','广州市天河区zz路3号','承压_3','承压名称3','用电类别_3','用电类别名称3','行业分类_3','行业分类名称3','重要性等级_3','高耗能行业分类_3','市场化属性分类_3','市场化属性分类名称3','客户分类_3','客户分类名称3','华能集团','MG-0003','管理单位编码名称3','所属区域_3','PR-0003','所属省公司名称3','CI-0003','所属市公司名称3','CO-0003','所属县公司名称3','华能集团','华能集团','区域层级：01国_3','区域层级描述测试数据3','2024-01-10 23:00:00'),(224526,'PA-0001','支付年月_1','2024-08-30 11:00:00',4738.8,'支付渠道_1','支付渠道名称1','支付方式_1','支付方式名称1','注销','CH-0001','BR-0001','联系人_1','13895289683','CH-0001','PA-0001','收费人员_1','收费部门_1','国网电力公司','SE-0001','SE-0001','PO-0001','BA-0001','E-0001','TR-0001',919070,240967,704249,'收费类型_1','收费类型名称1',3830.31,'CA-0001',578976,485231,881.6,862577,7431.27,826.12,154273,9478.75,9383.09,'南方电网公司','结余类型描述测试数据1',555348,3761.18,'CU-0001','客户名称1','广州市天河区zz路3号','承压_1','承压名称1','用电类别_1','用电类别名称1','行业分类_1','行业分类名称1','重要性等级_1','高耗能行业分类_1','市场化属性分类_1','市场化属性分类名称1','客户分类_1','客户分类名称1','国网电力公司','MG-0001','管理单位编码名称1','所属区域_1','PR-0001','所属省公司名称1','CI-0001','所属市公司名称1','CO-0001','所属县公司名称1','华能集团','大唐集团','区域层级：01国_1','区域层级描述测试数据1','2025-01-23 17:00:00'),(303977,'PA-0002','支付年月_2','2024-09-26 23:00:00',4278.63,'支付渠道_2','支付渠道名称2','支付方式_2','支付方式名称2','正常','CH-0002','BR-0002','联系人_2','13893116747','CH-0002','PA-0002','收费人员_2','收费部门_2','国家电投','SE-0002','SE-0002','PO-0002','BA-0002','E-0002','TR-0002',418561,876229,413075,'收费类型_2','收费类型名称2',5307.67,'CA-0002',654786,210852,4804.35,934295,3486.92,54.22,28448,4599.32,5192.81,'大唐集团','结余类型描述测试数据2',464129,776.16,'CU-0002','客户名称2','上海市浦东新区yy路2号','承压_2','承压名称2','用电类别_2','用电类别名称2','行业分类_2','行业分类名称2','重要性等级_2','高耗能行业分类_2','市场化属性分类_2','市场化属性分类名称2','客户分类_2','客户分类名称2','国家电投','MG-0002','管理单位编码名称2','所属区域_2','PR-0002','所属省公司名称2','CI-0002','所属市公司名称2','CO-0002','所属县公司名称2','南方电网公司','南方电网公司','区域层级：01国_2','区域层级描述测试数据2','2024-05-17 03:00:00');
/*!40000 ALTER TABLE `dwd_cst_bilg_charg_pay_info_di` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bilg_inst_qty`
--

DROP TABLE IF EXISTS `dwd_cst_bilg_inst_qty`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bilg_inst_qty` (
  `inst_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` double DEFAULT NULL,
  `ap_cu_loss` double DEFAULT NULL,
  `ap_iron_loss` double DEFAULT NULL,
  `ap_ll` double DEFAULT NULL,
  `ap_tl` double DEFAULT NULL,
  `calc_id` double NOT NULL,
  `ctlg_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctlg_cls_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dtl_mr_qty` double DEFAULT NULL,
  `dtl_settle_qty` double DEFAULT NULL,
  `elec_qty_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_qty_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp_ymd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_acct_id` double DEFAULT NULL,
  `inst_id` double DEFAULT NULL,
  `inst_qty_id` double DEFAULT NULL,
  `inst_snap_id` double DEFAULT NULL,
  `lv_ling_mr_ap_q` double DEFAULT NULL,
  `lv_ling_mr_time_sec_pr` double DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mr_dmd` double DEFAULT NULL,
  `mr_elec_qty_time_sec_pr` double DEFAULT NULL,
  `mr_rp_q` double DEFAULT NULL,
  `plan_no` double DEFAULT NULL,
  `pt_ap_inc_loss` double DEFAULT NULL,
  `pt_rp_inc_loss` double DEFAULT NULL,
  `qty_charg_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rev_apt_apq` double DEFAULT NULL,
  `rev_rpt_rpq` double DEFAULT NULL,
  `rmn_mr_ap_q` double DEFAULT NULL,
  `rmn_mr_elec_qty_time_sec_pr` double DEFAULT NULL,
  `rmn_mr_rp_q` double DEFAULT NULL,
  `rp_cu_loss` double DEFAULT NULL,
  `rp_iron_loss` double DEFAULT NULL,
  `rp_ll` double DEFAULT NULL,
  `rp_settle_qty` double DEFAULT NULL,
  `rp_tl` double DEFAULT NULL,
  `rs_apq` double DEFAULT NULL,
  `rs_rpq` double DEFAULT NULL,
  `self_cons_elec_qty` double DEFAULT NULL,
  `settle_acct_id` double DEFAULT NULL,
  `settle_dmd` double DEFAULT NULL,
  `submeter_apq_ddct` double DEFAULT NULL,
  `submeter_rpq_ddct` double DEFAULT NULL,
  `write_off_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `write_off_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`calc_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bilg_inst_qty`
--

LOCK TABLES `dwd_cst_bilg_inst_qty` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bilg_inst_qty` DISABLE KEYS */;
INSERT INTO `dwd_cst_bilg_inst_qty` VALUES ('IN-0001',3983.95,7623.71,206.24,6395.47,8755.9,4268.48,'目录分类_1','目录分类名称1','CU-0001',5059.88,2192.8,'77','电量类型名称1','15334.2',9522.04,7081.42,5506.64,8993.82,9344.45,453.19,'MG-0001',2055.57,9091.99,4673.69,6507.66,1308.15,6409.25,'993',4227.09,1635.39,2444.44,8354.29,682.96,8105.71,4772.9,6658.98,7239.05,2662.9,5129.31,551.03,4759.93,7051.03,8151.2,307.12,3795.11,'冲减类型_1','冲减类型名称1'),('IN-0002',7765.6,1712.26,4094.97,2971.46,6847.71,6978.21,'目录分类_2','目录分类名称2','CU-0002',4440.1,6065.56,'190','电量类型名称2','21733.16',5538.5,2349.16,9672.71,7999.86,5306.55,2333.21,'MG-0002',9763.55,4888.5,7781.68,3688.64,7943.04,1747.77,'791',513.53,2128.85,718.13,2726.52,9103.55,8340.34,6124.79,7367.43,2382.3,1140.65,139.9,7471.88,8980.49,8167.52,7872,8692.65,1416.24,'冲减类型_2','冲减类型名称2'),('IN-0003',1847.45,5737.74,2924.05,2691.36,5276.13,8031.92,'目录分类_3','目录分类名称3','CU-0003',2109.82,9469.85,'671','电量类型名称3','23091.21',2613.67,4859.68,2164.37,9829.02,7336.72,6342.73,'MG-0003',7394.21,2967.99,6155.47,2596.11,9558.41,4631.21,'263',1231.72,1223.65,8894.37,3888.14,1705.71,4690.65,948.87,1550.73,7910.08,4619.92,2847.69,8394.81,3023.25,3997.87,1138.29,5799.07,7572.15,'冲减类型_3','冲减类型名称3');
/*!40000 ALTER TABLE `dwd_cst_bilg_inst_qty` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bilg_mr_data`
--

DROP TABLE IF EXISTS `dwd_cst_bilg_mr_data`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bilg_mr_data` (
  `inst_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` double DEFAULT NULL,
  `m_r_data_id` double NOT NULL,
  `calc_id` double DEFAULT NULL,
  `plan_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `qty_charg_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_id` double DEFAULT NULL,
  `dev_id` double DEFAULT NULL,
  `mr_sn` double DEFAULT NULL,
  `read_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `read_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_read_frz_date` datetime DEFAULT NULL,
  `last_m_r` double DEFAULT NULL,
  `last_mr_qty` double DEFAULT NULL,
  `this_read_frz_date` datetime DEFAULT NULL,
  `this_m_r` double DEFAULT NULL,
  `this_mr_qty` double DEFAULT NULL,
  `comp_rati` double DEFAULT NULL,
  `mr_digit` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mr_digit_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mr_stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mr_stat_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mr_abnor_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mr_abnor_categ_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `actl_mr_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `actl_mr_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `m_r_coef` double DEFAULT NULL,
  `rela_app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_date` datetime DEFAULT NULL,
  `data_src` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp_ymd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `this_read_act_date` datetime DEFAULT NULL,
  `last_read_act_date` datetime DEFAULT NULL,
  `dev_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sgmt_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_insert_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ref_meter_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ref_meter_flag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `time_slot` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `time_slot_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reg_read_vou_id` double DEFAULT NULL,
  `meter_logic_id` double DEFAULT NULL,
  `attach_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `as_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_read_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_snap_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`m_r_data_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bilg_mr_data`
--

LOCK TABLES `dwd_cst_bilg_mr_data` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bilg_mr_data` DISABLE KEYS */;
INSERT INTO `dwd_cst_bilg_mr_data` VALUES ('IN-0001',8749.36,4178.55,2248.51,'PL-0001','MG-0001','CU-0001','380','服务种类_1','服务种类名称1',2087.51,5488.81,3152.13,'计度器类型_1','计度器类型名称1','2024-12-27 18:00:00',5721.26,2801.1,'2024-12-20 17:00:00',2628.31,7846.46,4279.35,'抄见位数_1','抄见位数名称1','激活','抄表状态名称1','MR-0001','抄表异常类别名称1','实际抄表方式_1','实际抄表方式名称1',6263.67,'RE-0001','2025-04-23 05:00:00','数据来源_1','14866.86','2024-10-24 03:00:00','2024-11-04 08:00:00','设备类别_1','设备类别名称1','SG-0001','2024-12-07 00:00:00','参考表标志_1','参考表标志名称1','2025-03-21 00:00:00','现货交易时段名称1','AS-0001',1369.27,3335.53,'ATT0001','追补年月_1','修改示数类型_1','SRV0001','INS0001','变更说明测试数据1'),('IN-0003',2973.34,7982.75,2723.04,'PL-0003','MG-0003','CU-0003','880','服务种类_3','服务种类名称3',1685.79,61.99,51.06,'计度器类型_3','计度器类型名称3','2024-09-08 09:00:00',9397.06,8937.71,'2024-04-14 14:00:00',625.67,7367.92,5845.2,'抄见位数_3','抄见位数名称3','启用','抄表状态名称3','MR-0003','抄表异常类别名称3','实际抄表方式_3','实际抄表方式名称3',5786.26,'RE-0003','2024-06-25 05:00:00','数据来源_3','29935.32','2024-09-29 12:00:00','2024-10-28 09:00:00','设备类别_3','设备类别名称3','SG-0003','2024-05-20 00:00:00','参考表标志_3','参考表标志名称3','2024-08-08 00:00:00','现货交易时段名称3','AS-0003',5271.74,8816.55,'ATT0003','追补年月_3','修改示数类型_3','SRV0003','INS0003','变更说明测试数据3'),('IN-0002',2920.06,9754.19,3218.98,'PL-0002','MG-0002','CU-0002','626','服务种类_2','服务种类名称2',2642.91,9656.68,3764.72,'计度器类型_2','计度器类型名称2','2025-03-31 10:00:00',7706.61,6559.78,'2025-03-05 18:00:00',457.39,9214,9612.84,'抄见位数_2','抄见位数名称2','正常','抄表状态名称2','MR-0002','抄表异常类别名称2','实际抄表方式_2','实际抄表方式名称2',9422.19,'RE-0002','2024-02-26 21:00:00','数据来源_2','94573.33','2025-02-25 01:00:00','2024-12-08 20:00:00','设备类别_2','设备类别名称2','SG-0002','2025-02-18 00:00:00','参考表标志_2','参考表标志名称2','2024-05-12 00:00:00','现货交易时段名称2','AS-0002',4953.45,2070.27,'ATT0002','追补年月_2','修改示数类型_2','SRV0002','INS0002','变更说明测试数据2');
/*!40000 ALTER TABLE `dwd_cst_bilg_mr_data` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-04 12:13:49
-- MySQL dump 10.13  Distrib 8.0.39, for Linux (x86_64)
--
-- Host: localhost    Database: tupu
-- ------------------------------------------------------
-- Server version	8.0.39

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `dwd_cst_bilg_paied_acct_mi`
--

DROP TABLE IF EXISTS `dwd_cst_bilg_paied_acct_mi`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bilg_paied_acct_mi` (
  `paied_acct_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `gpc_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_date` datetime DEFAULT NULL,
  `paied_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `paied_amt` double DEFAULT NULL,
  `paied_ep_amt` double DEFAULT NULL,
  `paied_alow_amt` double DEFAULT NULL,
  `paied_tax_amt` double DEFAULT NULL,
  `paied_ep_tax_amt` double DEFAULT NULL,
  `paied_alow_tax_amt` double DEFAULT NULL,
  `paybl_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `paybl_acct_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `paybl_alow_amt` double DEFAULT NULL,
  `paybl_alow_tax_amt` double DEFAULT NULL,
  `paybl_amt` double DEFAULT NULL,
  `paybl_bal` double DEFAULT NULL,
  `paybl_ep_amt` double DEFAULT NULL,
  `paybl_ep_tax_amt` double DEFAULT NULL,
  `paybl_tax_amt` double DEFAULT NULL,
  `qty_charg_calc_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `t_gpq` double DEFAULT NULL,
  `t_grid_elec_qty` double DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`paied_acct_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bilg_paied_acct_mi`
--

LOCK TABLES `dwd_cst_bilg_paied_acct_mi` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bilg_paied_acct_mi` DISABLE KEYS */;
INSERT INTO `dwd_cst_bilg_paied_acct_mi` VALUES ('PAI0001','GP-0001','国家电投','2025-04-09 09:00:00','实付年月：实付台_1',3971.52,1435.66,7317.23,9100.48,6709,3212.01,'应付年月：应付台_1','PAY0001',2975.65,7111.85,1077.39,3426.39,4082.47,7908.33,2094.53,'QTY0001',6841.81,5228.84,'MG-0001','管理单位名称1','省份名称1','地市名称1','2025-04-23 22:00:00','分区字段_1'),('PAI0002','GP-0002','国网电力公司','2024-05-18 14:00:00','实付年月：实付台_2',2864.65,946.91,22.95,845.35,872.21,143.05,'应付年月：应付台_2','PAY0002',5559.56,8511.32,8190.74,3842.42,2175,9796.67,7120.23,'QTY0002',9037.03,5038.97,'MG-0002','管理单位名称2','省份名称2','地市名称2','2024-10-25 05:00:00','分区字段_2'),('PAI0003','GP-0003','大唐集团','2024-01-02 04:00:00','实付年月：实付台_3',21.29,7174.27,2991.14,3433.52,415.12,4049.21,'应付年月：应付台_3','PAY0003',676.91,3441.22,7787.56,3882.74,6819.61,8625.87,8920,'QTY0003',2317.83,8660.12,'MG-0003','管理单位名称3','省份名称3','地市名称3','2024-12-06 10:00:00','分区字段_3');
/*!40000 ALTER TABLE `dwd_cst_bilg_paied_acct_mi` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bilg_paybl_acct_mi`
--

DROP TABLE IF EXISTS `dwd_cst_bilg_paybl_acct_mi`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bilg_paybl_acct_mi` (
  `paybl_acct_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `qty_charg_calc_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `paybl_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `paybl_amt` double DEFAULT NULL,
  `paybl_ep_amt` double DEFAULT NULL,
  `paybl_alow_amt` double DEFAULT NULL,
  `paybl_bal` double DEFAULT NULL,
  `paied_ep_amt` double DEFAULT NULL,
  `paied_alow_amt` double DEFAULT NULL,
  `paybl_tax_amt` double DEFAULT NULL,
  `paybl_ep_tax_amt` double DEFAULT NULL,
  `paybl_alow_tax_amt` double DEFAULT NULL,
  `t_gpq` double DEFAULT NULL,
  `t_grid_elec_qty` double DEFAULT NULL,
  `exp_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp_categ_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gpc_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `issu_date` datetime DEFAULT NULL,
  `issu_stf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `issu_batch_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_flag_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_flag_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `batch_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `push_stf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `push_time` datetime DEFAULT NULL,
  `tax_rate` double DEFAULT NULL,
  `rs_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bp_role_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bp_role_type_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_pscateg_yf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_pscateg_yf_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_pur_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_pur_type_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `graded_settle_times` double DEFAULT NULL,
  `data_wrt_time` datetime DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`paybl_acct_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bilg_paybl_acct_mi`
--

LOCK TABLES `dwd_cst_bilg_paybl_acct_mi` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bilg_paybl_acct_mi` DISABLE KEYS */;
INSERT INTO `dwd_cst_bilg_paybl_acct_mi` VALUES ('PAY0001','QTY0001','应付年月是指应付_1',8326.61,9153.33,9343.08,3586.08,7963.48,9869.95,5201.01,3323.32,7935.92,8441.82,1770.21,'37270.2','23627.35','GP-0001','CUS0001','2024-01-12 06:00:00','91068.65','IS-0001','国家电投','结清标志描述测试数据1','国家电投','发票开具标志描述测试数据1','BA-0001','属性描述：推送人_1','2025-01-06 08:00:00',129.3,'属性描述：退补年_1','大唐集团','业务伙伴角色类型测试数据1','国网电力公司','来源于主表应付台测试数据1','国家电投','购电类型描述测试数据1',4277.64,'2024-09-17 03:00:00','MG-0001','管理单位名称1','省份名称1','地市名称1','2024-08-25 03:00:00','分区字段_1'),('PAY0002','QTY0002','应付年月是指应付_2',3800.18,2033.22,2394.76,7938.66,354.26,6090.66,4547.7,6949.73,4741.78,4253.26,2045.87,'25898.28','55015.07','GP-0002','CUS0002','2024-06-06 09:00:00','21852.85','IS-0002','国网电力公司','结清标志描述测试数据2','国家电投','发票开具标志描述测试数据2','BA-0002','属性描述：推送人_2','2025-03-04 05:00:00',9525.01,'属性描述：退补年_2','南方电网公司','业务伙伴角色类型测试数据2','国网电力公司','来源于主表应付台测试数据2','大唐集团','购电类型描述测试数据2',3861.15,'2024-07-19 07:00:00','MG-0002','管理单位名称2','省份名称2','地市名称2','2024-11-19 21:00:00','分区字段_2'),('PAY0003','QTY0003','应付年月是指应付_3',7926.28,7070.81,6038.94,2428.64,1450.91,383.73,1272.8,7714.92,3874.73,4771.03,8451.32,'84317.1','56116.58','GP-0003','CUS0003','2025-01-20 16:00:00','252.82','IS-0003','国家电投','结清标志描述测试数据3','国家电投','发票开具标志描述测试数据3','BA-0003','属性描述：推送人_3','2024-05-19 09:00:00',437.85,'属性描述：退补年_3','国网电力公司','业务伙伴角色类型测试数据3','国家电投','来源于主表应付台测试数据3','南方电网公司','购电类型描述测试数据3',1686.34,'2024-11-18 21:00:00','MG-0003','管理单位名称3','省份名称3','地市名称3','2025-03-13 18:00:00','分区字段_3');
/*!40000 ALTER TABLE `dwd_cst_bilg_paybl_acct_mi` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bilg_qty_charg`
--

DROP TABLE IF EXISTS `dwd_cst_bilg_qty_charg`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bilg_qty_charg` (
  `inst_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `calc_id` double DEFAULT NULL,
  `plan_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_id` double DEFAULT NULL,
  `prc_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_code_ind_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_snap_id` double DEFAULT NULL,
  `elec_qty_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_qty_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dtl_mr_qty` double DEFAULT NULL,
  `ap_tl` double DEFAULT NULL,
  `ap_ll` double DEFAULT NULL,
  `submeter_apq_ddct` double DEFAULT NULL,
  `sgmt_qty_charg_id` double DEFAULT NULL,
  `bilg_card_id` double DEFAULT NULL,
  `exp_attr_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp_attr_cls_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctlg_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctlg_cls_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_qty` double DEFAULT NULL,
  `exec_ctlg_up` double DEFAULT NULL,
  `ctlg_exp` double DEFAULT NULL,
  `deg_up` double DEFAULT NULL,
  `deg_exp` double DEFAULT NULL,
  `lvling_diff` double DEFAULT NULL,
  `ext_settle_qty` double DEFAULT NULL,
  `qty_charg_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `before_ctlg_exp` double DEFAULT NULL,
  `before_deg_exp` double DEFAULT NULL,
  `as_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pv_inc_dec_exp` double DEFAULT NULL,
  `exp_ymd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`inst_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bilg_qty_charg`
--

LOCK TABLES `dwd_cst_bilg_qty_charg` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bilg_qty_charg` DISABLE KEYS */;
INSERT INTO `dwd_cst_bilg_qty_charg` VALUES ('IN-0001','CUS0001',9351.36,'PL-0001','CU-0001',4876.16,'PR-0001','PR-0001',8399.68,'425','电量类型名称1',458.94,1440.93,8983.19,6639.07,5282.83,5574.53,'29558.98','费用属性分类名称1','目录分类_1','目录分类名称1','服务种类_1','服务种类名称1',7599.42,8130.85,433.01,7455.54,518.18,3788.58,8455.62,'375','MG-0001',9641.19,2380.34,'追补年月_1',9051.99,'23260.23'),('IN-0002','CUS0002',6468.69,'PL-0002','CU-0002',6828.98,'PR-0002','PR-0002',2880.92,'536','电量类型名称2',7574.73,603.74,11.18,2374.69,4302.66,6707.08,'98414.63','费用属性分类名称2','目录分类_2','目录分类名称2','服务种类_2','服务种类名称2',5086.91,7314.76,8041.87,5597.12,6237.22,6097.34,4923.26,'637','MG-0002',1237.13,3979.81,'追补年月_2',5814.67,'95826.42'),('IN-0003','CUS0003',4773.96,'PL-0003','CU-0003',7865.5,'PR-0003','PR-0003',9828.32,'753','电量类型名称3',1351.05,2993.36,8679.59,4068.81,4898.77,871.11,'57255.6','费用属性分类名称3','目录分类_3','目录分类名称3','服务种类_3','服务种类名称3',790.26,6781.37,6099.57,3794.94,9676.9,5739,2038.05,'512','MG-0003',4717.37,8043.55,'追补年月_3',4122.21,'30045.56');
/*!40000 ALTER TABLE `dwd_cst_bilg_qty_charg` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bilg_rcvbl_acct_mi`
--

DROP TABLE IF EXISTS `dwd_cst_bilg_rcvbl_acct_mi`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bilg_rcvbl_acct_mi` (
  `rcvbl_acct_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `qty_charg_calc_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prtr_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvbl_ym` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acct_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp_categ_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_qty` double DEFAULT NULL,
  `rcvbl_amt` double DEFAULT NULL,
  `rcvbl_in_prc_amt` double DEFAULT NULL,
  `rcvbl_addl_charg_amt` double DEFAULT NULL,
  `rcvd_amt` double DEFAULT NULL,
  `rcvd_in_prc_amt` double DEFAULT NULL,
  `rcvd_addl_charg_amt` double DEFAULT NULL,
  `dereg_trans_qty` double DEFAULT NULL,
  `dereg_rcvbl_amt` double DEFAULT NULL,
  `dereg_rcvd_amt` double DEFAULT NULL,
  `rcvbl_rsrv_amt` double DEFAULT NULL,
  `rcvd_rsrv_amt` double DEFAULT NULL,
  `in_trnst_amt` double DEFAULT NULL,
  `arer_bal` double DEFAULT NULL,
  `write_off_amt` double DEFAULT NULL,
  `this_lvling_amt` double DEFAULT NULL,
  `last_lvling_amt` double DEFAULT NULL,
  `rcvbl_lqd_damg` double DEFAULT NULL,
  `rcvd_lqd_damg` double DEFAULT NULL,
  `setl_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_flag_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp_stat` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp_stat_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `issu_date` datetime DEFAULT NULL,
  `lqd_damg_calc_beg_date` datetime DEFAULT NULL,
  `lqd_damg_ul_amt` double DEFAULT NULL,
  `issu_stf` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `issu_batch_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mr_unit_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `in_trnst_date` datetime DEFAULT NULL,
  `note_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `note_type_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_mode_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_flag_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_acct_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_acct_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_acct_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_acct_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_acct_categ_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_categ_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_mode_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_agrt_prd_times` double DEFAULT NULL,
  `srv_kind` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  `ds` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`rcvbl_acct_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bilg_rcvbl_acct_mi`
--

LOCK TABLES `dwd_cst_bilg_rcvbl_acct_mi` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bilg_rcvbl_acct_mi` DISABLE KEYS */;
INSERT INTO `dwd_cst_bilg_rcvbl_acct_mi` VALUES ('RCV0001','QTY0001','PR-0001','CUS0001','CU-0001','客户名称1','1716.25','AC-0001','77278.81','81886.83',9582.8,6836.4,5769.87,9618.33,7028.73,7965.65,1466.87,9926.83,8775.55,8985.68,4424.35,635.66,559.84,1810.48,2812.84,1165.26,8458.4,5573.39,4498.54,'84803.59','结清标志描述测试数据1','2205.89','52389.07','2024-04-10 18:00:00','2024-04-29 05:00:00',2605.91,'27575.7','IS-0001','国家电投','用能类别描述测试数据1','VO-0001','承压等级描述测试数据1','MR-0001','2024-05-08 06:00:00','NO-0001','NO-0001','开票模式：客户开_1','开票模式描述测试数据1','南方电网公司','发票开具标志描述测试数据1','SET0001','SE-0001','结算账户名称：债务结1','14453.26','结算账户类别描述测试数据1','20885.18','结算类别描述测试数据1','交费方式：缴纳电_1','交费方式描述测试数据1',1351.72,'3987.13','服务种类描述测试数据1','MG-0001','管理单位名称1','省份名称1','地市名称1','2025-04-21 09:00:00','86784.97'),('RCV0002','QTY0002','PR-0002','CUS0002','CU-0002','客户名称2','56771.2','AC-0002','23252.4','79228.72',7635.15,8266.25,6857.66,1927.58,5671.96,527.68,8008.66,9787.79,4692.02,9264.63,5047.05,7079.37,8994.51,3203.9,6951,1878.49,8437.32,9578.6,2792.06,'88455.72','结清标志描述测试数据2','65684.13','79070.77','2024-01-09 21:00:00','2024-09-27 12:00:00',290.73,'63716.37','IS-0002','华能集团','用能类别描述测试数据2','VO-0002','承压等级描述测试数据2','MR-0002','2025-01-19 06:00:00','NO-0002','NO-0002','开票模式：客户开_2','开票模式描述测试数据2','华能集团','发票开具标志描述测试数据2','SET0002','SE-0002','结算账户名称：债务结2','9212.24','结算账户类别描述测试数据2','73447.65','结算类别描述测试数据2','交费方式：缴纳电_2','交费方式描述测试数据2',5581.3,'2799.73','服务种类描述测试数据2','MG-0002','管理单位名称2','省份名称2','地市名称2','2025-01-25 04:00:00','14315.64'),('RCV0003','QTY0003','PR-0003','CUS0003','CU-0003','客户名称3','92103.4','AC-0003','15559.35','15495.05',6056.17,1275.93,9004.73,7489.29,2553.96,8185.03,1365.9,6256.11,7610.98,8436.87,8419.66,5390.97,6414.59,4174.62,193.78,7641.25,2333.6,7940.19,4508.15,'59561.73','结清标志描述测试数据3','21457.49','56222.9','2024-02-17 19:00:00','2024-11-05 13:00:00',2648.17,'93800.75','IS-0003','大唐集团','用能类别描述测试数据3','VO-0003','承压等级描述测试数据3','MR-0003','2024-08-24 19:00:00','NO-0003','NO-0003','开票模式：客户开_3','开票模式描述测试数据3','华能集团','发票开具标志描述测试数据3','SET0003','SE-0003','结算账户名称：债务结3','93659.84','结算账户类别描述测试数据3','37225.79','结算类别描述测试数据3','交费方式：缴纳电_3','交费方式描述测试数据3',1511.65,'27241.02','服务种类描述测试数据3','MG-0003','管理单位名称3','省份名称3','地市名称3','2025-03-02 03:00:00','16086.42');
/*!40000 ALTER TABLE `dwd_cst_bilg_rcvbl_acct_mi` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bilg_rcvd_acct_mi`
--

DROP TABLE IF EXISTS `dwd_cst_bilg_rcvd_acct_mi`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bilg_rcvd_acct_mi` (
  `rcvd_acct_id` int NOT NULL,
  `charg_acct_id` int DEFAULT NULL,
  `rcvbl_acct_id` int DEFAULT NULL,
  `prtr_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvbl_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvd_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvd_amt` double DEFAULT NULL,
  `dereg_rcvd_amt` double DEFAULT NULL,
  `rcvd_in_prc_amt` double DEFAULT NULL,
  `rcvd_addl_charg_amt` double DEFAULT NULL,
  `rcvd_lqd_damg` double DEFAULT NULL,
  `rcvd_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rchg_card_used_amt` double DEFAULT NULL,
  `acct_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_acct_id` int DEFAULT NULL,
  `ec_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvd_rsrv_amt` double DEFAULT NULL,
  `volt_lv` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_lv_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_acct_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_acct_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_acct_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_acct_categ_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_mode_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prepay_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prepay_mode_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bal_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bal_type_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `area` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `write_time` datetime DEFAULT NULL,
  PRIMARY KEY (`rcvd_acct_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bilg_rcvd_acct_mi`
--

LOCK TABLES `dwd_cst_bilg_rcvd_acct_mi` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bilg_rcvd_acct_mi` DISABLE KEYS */;
INSERT INTO `dwd_cst_bilg_rcvd_acct_mi` VALUES (656903,123874,123993,'PR-0001','CU-0001','应收年月：实收台_1','50091.29',145.59,744.38,649.41,2946.24,5974.84,'2024-05-07 00:00:00',698.32,'AC-0001',636888,'国网电力公司','用能类别描述测试数据1',5349.4,'南方电网公司','基础承压描述测试数据1','SE-0001','结算账户名称：债务结1','32359.24','结算账户类别描述测试数据1','9928.77','交费方式：缴纳电_1','交费方式描述测试数据1','67827.76','付费方式描述测试数据1','大唐集团','余额类型描述测试数据1','MG-0001','管理单位名称1','所属区域_1','PR-0001','所属省公司名称1','CI-0001','所属市公司名称1','CO-0001','所属县公司名称1','区域层级：01国_1','区域层级描述测试数据1','2025-04-03 13:00:00'),(758755,396787,871669,'PR-0002','CU-0002','应收年月：实收台_2','27365.13',416.97,7871.51,8356.83,4329.14,655.87,'2025-04-30 00:00:00',5130.75,'AC-0002',35026,'华能集团','用能类别描述测试数据2',7332.27,'大唐集团','基础承压描述测试数据2','SE-0002','结算账户名称：债务结2','92329.6','结算账户类别描述测试数据2','43303.97','交费方式：缴纳电_2','交费方式描述测试数据2','7294.72','付费方式描述测试数据2','华能集团','余额类型描述测试数据2','MG-0002','管理单位名称2','所属区域_2','PR-0002','所属省公司名称2','CI-0002','所属市公司名称2','CO-0002','所属县公司名称2','区域层级：01国_2','区域层级描述测试数据2','2024-08-10 16:00:00'),(790684,445782,274218,'PR-0003','CU-0003','应收年月：实收台_3','58856.98',1985.16,1457.53,3732.92,4772.22,5208.93,'2025-02-24 00:00:00',2217.03,'AC-0003',840847,'大唐集团','用能类别描述测试数据3',7812.94,'国家电投','基础承压描述测试数据3','SE-0003','结算账户名称：债务结3','5143.63','结算账户类别描述测试数据3','88144.88','交费方式：缴纳电_3','交费方式描述测试数据3','73076.45','付费方式描述测试数据3','华能集团','余额类型描述测试数据3','MG-0003','管理单位名称3','所属区域_3','PR-0003','所属省公司名称3','CI-0003','所属市公司名称3','CO-0003','所属县公司名称3','区域层级：01国_3','区域层级描述测试数据3','2024-02-12 07:00:00');
/*!40000 ALTER TABLE `dwd_cst_bilg_rcvd_acct_mi` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bilg_special_expense_mi`
--

DROP TABLE IF EXISTS `dwd_cst_bilg_special_expense_mi`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bilg_special_expense_mi` (
  `spcl_exp_id` int NOT NULL,
  `calc_id` int DEFAULT NULL,
  `qty_charg_ym` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `scpl_fee_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `scpl_fee_categ_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spcl_exp_scnd_lv_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spcl_exp_scnd_lv_cls_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `settle_exp_qty_val` double DEFAULT NULL,
  `settle_prc` double DEFAULT NULL,
  `settle_exp` double DEFAULT NULL,
  `calc_actl_pf_ap_q` int DEFAULT NULL,
  `calc_actl_pf_rp_q` int DEFAULT NULL,
  `actl_p_f` double DEFAULT NULL,
  `pf_std_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pf_std_value` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bilg_card_id` int DEFAULT NULL,
  `prc_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bilg_std_ver_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_ind_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_ind_cls_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_ind_ustry_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_ind_cls_desc_1` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctlg_prc_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_volt_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_volt_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_ec_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_ec_categ_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prtp_actl_pf_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pf_adj_calc_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_snap_id` int DEFAULT NULL,
  `inst_id` int DEFAULT NULL,
  `inst_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_mode_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_usage_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_usage_type_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_char` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_char_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` int DEFAULT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_cons_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_cons_type_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_cls_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_ind_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_ind_cls_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_ind_ustry_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_ind_cls_desc_1` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `high_ec_ind_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `high_ec_ind_cls_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_volt_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_volt_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_ec_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_ec_categ_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_cap` double DEFAULT NULL,
  `run_cap` double DEFAULT NULL,
  `impt_lv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `impt_lv_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `as_ym` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `area` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `write_time` datetime DEFAULT NULL,
  PRIMARY KEY (`spcl_exp_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bilg_special_expense_mi`
--

LOCK TABLES `dwd_cst_bilg_special_expense_mi` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bilg_special_expense_mi` DISABLE KEYS */;
INSERT INTO `dwd_cst_bilg_special_expense_mi` VALUES (216759,237234,'738','SC-0002','1004.15','38663.32','99409.91',6727.76,9231.04,4614.67,792204,210017,2800.23,'PF-0002','功率因数考核标准_2','PL-0002','服务种类_2','服务种类描述测试数据2',913243,'PR-0002','BI-0002','行业分类_电价：_2','行业分类描述测试数据2','产业分类_2','一级行业分类测试数据2','目录定价名称：价格名2','PR-0002','承压等级描述_电测试数据2','PR-0002','用能类别描述_电测试数据2','参与实际功率因数_2','参与功率因数调整_2',591946,604590,'IN-0002','安装点名称2','计量方式：安装点_2','计量方式描述测试数据2','安装点用途类型：_2','安装点用途类型描测试数据2','安装点性质：安装_2','安装点性质描述测试数据2',882318,'CU-0002','客户名称：客户的名称2','发用电户类型_2','发用电户类型描述测试数据2','客户分类：客户快_2','客户分类描述测试数据2','行业分类：客户快_2','行业分类描述测试数据2','产业分类_2','一级行业分类测试数据2','高耗能行业类别：_2','高耗能行业类别描测试数据2','CU-0002','承压描述测试数据2','用能类别：客户快_2','用能类别描述测试数据2',5623.87,211.55,'重要性等级：客户_2','重要性等级描述测试数据2','56360.94','MG-0002','管理单位名称2','所属区域_2','PR-0002','所属省公司名称2','CI-0002','所属市公司名称2','CO-0002','所属县公司名称2','区域层级：01国_2','区域层级描述测试数据2','2024-06-07 17:00:00'),(704368,435308,'554','SC-0001','37870.5','65849.54','68439.36',9334.22,7809.21,9925.38,93604,234463,9101.28,'PF-0001','功率因数考核标准_1','PL-0001','服务种类_1','服务种类描述测试数据1',746821,'PR-0001','BI-0001','行业分类_电价：_1','行业分类描述测试数据1','产业分类_1','一级行业分类测试数据1','目录定价名称：价格名1','PR-0001','承压等级描述_电测试数据1','PR-0001','用能类别描述_电测试数据1','参与实际功率因数_1','参与功率因数调整_1',308139,361475,'IN-0001','安装点名称1','计量方式：安装点_1','计量方式描述测试数据1','安装点用途类型：_1','安装点用途类型描测试数据1','安装点性质：安装_1','安装点性质描述测试数据1',32393,'CU-0001','客户名称：客户的名称1','发用电户类型_1','发用电户类型描述测试数据1','客户分类：客户快_1','客户分类描述测试数据1','行业分类：客户快_1','行业分类描述测试数据1','产业分类_1','一级行业分类测试数据1','高耗能行业类别：_1','高耗能行业类别描测试数据1','CU-0001','承压描述测试数据1','用能类别：客户快_1','用能类别描述测试数据1',6957.14,1278.89,'重要性等级：客户_1','重要性等级描述测试数据1','31479.9','MG-0001','管理单位名称1','所属区域_1','PR-0001','所属省公司名称1','CI-0001','所属市公司名称1','CO-0001','所属县公司名称1','区域层级：01国_1','区域层级描述测试数据1','2025-02-09 18:00:00'),(734254,943334,'647','SC-0003','13451.49','22430.8','25115.81',9570.84,2814.28,3882.17,486856,806542,4595.29,'PF-0003','功率因数考核标准_3','PL-0003','服务种类_3','服务种类描述测试数据3',103724,'PR-0003','BI-0003','行业分类_电价：_3','行业分类描述测试数据3','产业分类_3','一级行业分类测试数据3','目录定价名称：价格名3','PR-0003','承压等级描述_电测试数据3','PR-0003','用能类别描述_电测试数据3','参与实际功率因数_3','参与功率因数调整_3',813353,227526,'IN-0003','安装点名称3','计量方式：安装点_3','计量方式描述测试数据3','安装点用途类型：_3','安装点用途类型描测试数据3','安装点性质：安装_3','安装点性质描述测试数据3',901417,'CU-0003','客户名称：客户的名称3','发用电户类型_3','发用电户类型描述测试数据3','客户分类：客户快_3','客户分类描述测试数据3','行业分类：客户快_3','行业分类描述测试数据3','产业分类_3','一级行业分类测试数据3','高耗能行业类别：_3','高耗能行业类别描测试数据3','CU-0003','承压描述测试数据3','用能类别：客户快_3','用能类别描述测试数据3',6324.16,8587.49,'重要性等级：客户_3','重要性等级描述测试数据3','53567.87','MG-0003','管理单位名称3','所属区域_3','PR-0003','所属省公司名称3','CI-0003','所属市公司名称3','CO-0003','所属县公司名称3','区域层级：01国_3','区域层级描述测试数据3','2025-04-07 09:00:00');
/*!40000 ALTER TABLE `dwd_cst_bilg_special_expense_mi` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_acc_sch_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_acc_sch_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_acc_sch_df` (
  `accs_sch_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accs_categ_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accs_sch_prepared_date` datetime DEFAULT NULL,
  `biz_date` double DEFAULT NULL,
  `prov_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bp_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sch_drft_stf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sch_draft_opn` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accs_sys_sch_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_app_form_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attach_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`accs_sch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_acc_sch_df`
--

LOCK TABLES `dwd_cst_bus_acc_sch_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_acc_sch_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_acc_sch_df` VALUES ('ACC0001','2024-07-12 00:00:00','AC-0001','2024-05-16 01:00:00',4606.07,'省公司名称1','地市公司名称1','BP0001','CUS0001','CU-0001','客户名称1','方案拟定人_1','MGT0001','管理单位名称1','单位名称1','方案拟定意见_1','接入系统方案说明测试数据1','AP-0001','BUS0001','ATT0001'),('ACC0002','2024-10-13 00:00:00','AC-0002','2024-05-19 13:00:00',7970.06,'省公司名称2','地市公司名称2','BP0002','CUS0002','CU-0002','客户名称2','方案拟定人_2','MGT0002','管理单位名称2','单位名称2','方案拟定意见_2','接入系统方案说明测试数据2','AP-0002','BUS0002','ATT0002'),('ACC0003','2025-01-22 00:00:00','AC-0003','2024-08-05 17:00:00',6389.16,'省公司名称3','地市公司名称3','BP0003','CUS0003','CU-0003','客户名称3','方案拟定人_3','MGT0003','管理单位名称3','单位名称3','方案拟定意见_3','接入系统方案说明测试数据3','AP-0003','BUS0003','ATT0003');
/*!40000 ALTER TABLE `dwd_cst_bus_acc_sch_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_acpt_rec_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_acpt_rec_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_acpt_rec_df` (
  `bus_app_form_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` datetime DEFAULT NULL,
  `srv_kind` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_categ_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acpt_date` datetime DEFAULT NULL,
  `req_ec_date` datetime DEFAULT NULL,
  `arvl_expd_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `biz_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acpt_dept` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acpt_stf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acpt_stf_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `before_cont` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `after_cont` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attach_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `need_drflag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_subst_srv_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prtp_mkt_trans` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_incr_srv_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_over` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_stat_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prnt_app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `preapp_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `order_prd` int DEFAULT NULL,
  `stages_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stages_sub_order_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acpt_chan` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acpt_chan_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`bus_app_form_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_acpt_rec_df`
--

LOCK TABLES `dwd_cst_bus_acpt_rec_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_acpt_rec_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_acpt_rec_df` VALUES ('BUS0001','2025-05-12 06:00:00','服务种类_1','服务种类名称1','业务类型_1','业务类型名称1','业务类别_1','业务类别名称1','2025-02-17 02:00:00','2025-02-07 16:00:00','2024-11-04 07:00:00','2024-04-06 01:00:00','2025-02-17 00:00:00','省份名称1','地市名称1','CUS0001','受理部门_1','MG-0001','管理单位名称1','受理人员_1','受理人员名称1','申请方式_1','申请方式名称1','申请原因_1','申请备注测试数据1','变更前内容_1','变更后内容_1','ATT0001','需求响应标志_1','电能代替服务标志_1','参与市场交易标志_1','能效提升服务标志_1','拓扑维护结束标志_1','停用','申请状态名称1','AP-0001','PR-0001','PR-0001',450390,'分期标志_1','分期子工单标志_1','终止原因_1','AC-0001','受理渠道名称1'),('BUS0002','2024-09-07 21:00:00','服务种类_2','服务种类名称2','业务类型_2','业务类型名称2','业务类别_2','业务类别名称2','2024-02-09 11:00:00','2024-07-20 08:00:00','2025-01-23 06:00:00','2024-07-26 11:00:00','2024-04-12 00:00:00','省份名称2','地市名称2','CUS0002','受理部门_2','MG-0002','管理单位名称2','受理人员_2','受理人员名称2','申请方式_2','申请方式名称2','申请原因_2','申请备注测试数据2','变更前内容_2','变更后内容_2','ATT0002','需求响应标志_2','电能代替服务标志_2','参与市场交易标志_2','能效提升服务标志_2','拓扑维护结束标志_2','启用','申请状态名称2','AP-0002','PR-0002','PR-0002',229644,'分期标志_2','分期子工单标志_2','终止原因_2','AC-0002','受理渠道名称2'),('BUS0003','2025-02-01 19:00:00','服务种类_3','服务种类名称3','业务类型_3','业务类型名称3','业务类别_3','业务类别名称3','2024-11-06 04:00:00','2024-09-25 22:00:00','2024-12-17 19:00:00','2024-01-03 05:00:00','2024-12-27 00:00:00','省份名称3','地市名称3','CUS0003','受理部门_3','MG-0003','管理单位名称3','受理人员_3','受理人员名称3','申请方式_3','申请方式名称3','申请原因_3','申请备注测试数据3','变更前内容_3','变更后内容_3','ATT0003','需求响应标志_3','电能代替服务标志_3','参与市场交易标志_3','能效提升服务标志_3','拓扑维护结束标志_3','注销','申请状态名称3','AP-0003','PR-0003','PR-0003',944317,'分期标志_3','分期子工单标志_3','终止原因_3','AC-0003','受理渠道名称3');
/*!40000 ALTER TABLE `dwd_cst_bus_acpt_rec_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_be_accs_lfcyc_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_be_accs_lfcyc_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_be_accs_lfcyc_df` (
  `bus_app_form_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` datetime DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `create_time` datetime DEFAULT NULL,
  `bus_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acpt_date` datetime DEFAULT NULL,
  `invest_order_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_date` datetime DEFAULT NULL,
  `op_exp_rcvbl_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvbl_amt` double DEFAULT NULL,
  `exp_cnfm_time` datetime DEFAULT NULL,
  `op_exp_rcvd_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvd_amt` double DEFAULT NULL,
  `rcvd_date` datetime DEFAULT NULL,
  `wk_order_affil_mtrl_rec_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `aprv_date` datetime DEFAULT NULL,
  `veri_rslt` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_opn` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_form_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_num` double DEFAULT NULL,
  `aprv_num` double DEFAULT NULL,
  `app_date` datetime DEFAULT NULL,
  `cust_gen_elec_app_rec_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arch_status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estab_acct_date` datetime DEFAULT NULL,
  `cncl_date` datetime DEFAULT NULL,
  `ec_date` datetime DEFAULT NULL,
  `chg_date` datetime DEFAULT NULL,
  PRIMARY KEY (`bus_app_form_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_be_accs_lfcyc_df`
--

LOCK TABLES `dwd_cst_bus_be_accs_lfcyc_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_be_accs_lfcyc_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_be_accs_lfcyc_df` VALUES ('BUS0001','2024-02-08 17:00:00','MG-0001','管理单位名称，如：大1','省公司名称1','地市公司名称1','CUS0001','CU-0001','客户名称1','WK0001','WK-0001','2025-05-12 15:00:00','业务类型_1','业务类型名称1','2024-08-03 20:00:00','INV0001','2024-11-15 19:00:00','OP0001',7922.79,'2024-06-17 02:00:00','OP0001',7821.59,'2024-04-30 06:00:00','WK0001','2024-02-24 20:00:00','审核结果_1','审核意见_1','APP0001',4941.91,8779.81,'2024-07-24 07:00:00','CUS0001','停用','2024-01-19 01:00:00','2024-12-10 15:00:00','2024-10-24 02:00:00','2024-10-13 19:00:00'),('BUS0002','2024-09-15 16:00:00','MG-0002','管理单位名称，如：大2','省公司名称2','地市公司名称2','CUS0002','CU-0002','客户名称2','WK0002','WK-0002','2025-03-16 17:00:00','业务类型_2','业务类型名称2','2024-09-28 03:00:00','INV0002','2025-03-31 23:00:00','OP0002',5236.74,'2024-03-29 04:00:00','OP0002',3310.07,'2024-04-08 05:00:00','WK0002','2024-09-24 20:00:00','审核结果_2','审核意见_2','APP0002',510.82,9334.39,'2024-03-05 16:00:00','CUS0002','停用','2024-10-01 05:00:00','2024-12-18 04:00:00','2024-08-31 17:00:00','2024-04-04 19:00:00'),('BUS0003','2024-12-06 03:00:00','MG-0003','管理单位名称，如：大3','省公司名称3','地市公司名称3','CUS0003','CU-0003','客户名称3','WK0003','WK-0003','2024-07-30 08:00:00','业务类型_3','业务类型名称3','2024-01-09 22:00:00','INV0003','2024-08-12 22:00:00','OP0003',674.84,'2025-01-24 08:00:00','OP0003',7596.83,'2025-01-13 16:00:00','WK0003','2024-11-14 17:00:00','审核结果_3','审核意见_3','APP0003',5768.86,311.87,'2024-07-27 10:00:00','CUS0003','激活','2024-01-31 17:00:00','2024-08-24 08:00:00','2024-09-05 23:00:00','2024-02-12 10:00:00');
/*!40000 ALTER TABLE `dwd_cst_bus_be_accs_lfcyc_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_cust_agrt_sch_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_cust_agrt_sch_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_cust_agrt_sch_df` (
  `cust_agrt_sch_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `agrt_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `agrt_categ_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `biz_date` double DEFAULT NULL,
  `prov_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `jn_inv_agrt_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `jn_inv_agrt_flag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_unit` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_unit_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cls_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pf_eval_std` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pf_eval_std_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `timesec_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prtp_dir_trans_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hndl_stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hndl_stat_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_lv` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_lv_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `time_sec_num` double DEFAULT NULL,
  `prtp_actl_pf_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prtp_pf_adj_elec_charg_calc_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rng_exec_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cap_prc_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dmd_prc_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arch_status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prt_user_inv_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_agrt_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_acct_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_app_form_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_elec_app_rec_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `agrt_prc` double DEFAULT NULL,
  `fix_rto_val` double DEFAULT NULL,
  PRIMARY KEY (`cust_agrt_sch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_cust_agrt_sch_df`
--

LOCK TABLES `dwd_cst_bus_cust_agrt_sch_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_cust_agrt_sch_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_cust_agrt_sch_df` VALUES ('CUS0001','2024-03-02 00:00:00','AG-0001','协议类别编码1','SR-0001','服务种类名称1','EC-0001','用能类别名称1','2025-01-16 00:00:00',4935.31,'省公司名称1','地市公司名称1','CUS0001','MGT0001','MG-0001','管理单位名称1','JN-0001','联合开票协议标志名称1','ME-0001','计量单位名称1','行业分类_1','行业分类1','PR-0001','功率因数考核标准_1','功率因数考核标准名称1','2024-08-03 00:00:00','参与直接交易标志_1','变更说明测试数据1','HN-0001','处理状态名称1','VO-0001','承压等级名称1',4363.25,'参与实际功率因数_1','参与功率因数调整_1','按范围执行标志_1','容量价格标志_1','需量价格标志_1','异常','打印房客票据标志_1','CUS0001','AP-0001','SET0001','BUS0001','SRV0001','SRV0001',9452.04,2867.39),('CUS0002','2024-07-01 00:00:00','AG-0002','协议类别编码2','SR-0002','服务种类名称2','EC-0002','用能类别名称2','2024-01-11 00:00:00',2863.61,'省公司名称2','地市公司名称2','CUS0002','MGT0002','MG-0002','管理单位名称2','JN-0002','联合开票协议标志名称2','ME-0002','计量单位名称2','行业分类_2','行业分类2','PR-0002','功率因数考核标准_2','功率因数考核标准名称2','2024-09-30 00:00:00','参与直接交易标志_2','变更说明测试数据2','HN-0002','处理状态名称2','VO-0002','承压等级名称2',8328.32,'参与实际功率因数_2','参与功率因数调整_2','按范围执行标志_2','容量价格标志_2','需量价格标志_2','启用','打印房客票据标志_2','CUS0002','AP-0002','SET0002','BUS0002','SRV0002','SRV0002',6116.11,8772.53),('CUS0003','2025-01-27 00:00:00','AG-0003','协议类别编码3','SR-0003','服务种类名称3','EC-0003','用能类别名称3','2024-01-29 00:00:00',3836.87,'省公司名称3','地市公司名称3','CUS0003','MGT0003','MG-0003','管理单位名称3','JN-0003','联合开票协议标志名称3','ME-0003','计量单位名称3','行业分类_3','行业分类3','PR-0003','功率因数考核标准_3','功率因数考核标准名称3','2024-11-19 00:00:00','参与直接交易标志_3','变更说明测试数据3','HN-0003','处理状态名称3','VO-0003','承压等级名称3',5666.38,'参与实际功率因数_3','参与功率因数调整_3','按范围执行标志_3','容量价格标志_3','需量价格标志_3','停用','打印房客票据标志_3','CUS0003','AP-0003','SET0003','BUS0003','SRV0003','SRV0003',1224.01,2867.43);
/*!40000 ALTER TABLE `dwd_cst_bus_cust_agrt_sch_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_debug_rec_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_debug_rec_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_debug_rec_df` (
  `id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `debug_rec_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  `dev_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `debug_time` datetime DEFAULT NULL,
  `biz_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rem_comm_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `debug_stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_asset_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prnt_iot_point_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arch_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_debug_rec_df`
--

LOCK TABLES `dwd_cst_bus_debug_rec_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_debug_rec_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_debug_rec_df` VALUES ('ID0001','DEB0001','2024-08-11 03:00:00','设备分类_1','设备类别_1','变更类型_1','2024-03-15 20:00:00','2024-10-15 00:00:00','省公司名称1','地市公司名称1','MGT0001','MG-0001','管理单位名称1','远程通讯标志_1','正常','DE-0001','AP-0001','IO-0001','PR-0001','ARC0001','DEV0001'),('ID0002','DEB0002','2025-03-07 08:00:00','设备分类_2','设备类别_2','变更类型_2','2024-03-26 05:00:00','2024-10-01 00:00:00','省公司名称2','地市公司名称2','MGT0002','MG-0002','管理单位名称2','远程通讯标志_2','正常','DE-0002','AP-0002','IO-0002','PR-0002','ARC0002','DEV0002'),('ID0003','DEB0003','2025-04-25 01:00:00','设备分类_3','设备类别_3','变更类型_3','2025-01-27 14:00:00','2024-02-05 00:00:00','省公司名称3','地市公司名称3','MGT0003','MG-0003','管理单位名称3','远程通讯标志_3','注销','DE-0003','AP-0003','IO-0003','PR-0003','ARC0003','DEV0003');
/*!40000 ALTER TABLE `dwd_cst_bus_debug_rec_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_dev_inst_rmv_wk_rec_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_dev_inst_rmv_wk_rec_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_dev_inst_rmv_wk_rec_df` (
  `dev_inst_rmv_wk_rec_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` datetime DEFAULT NULL,
  `inst_rmv_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_rmv_categ_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_rmv_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_rmv_reason_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_rmv_date` datetime DEFAULT NULL,
  `last_mr_date` datetime DEFAULT NULL,
  `mr_date` datetime DEFAULT NULL,
  `biz_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_rmv_addr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `row_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `col_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lng` double DEFAULT NULL,
  `lat` double DEFAULT NULL,
  `alt` double DEFAULT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_rmv_org` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_rmv_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_rmv_stf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_rmv_stf_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_cls_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctnr_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reg_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reg_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctnr_asset_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_sch_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reg_read_sch_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_read` double DEFAULT NULL,
  `this_read` double DEFAULT NULL,
  PRIMARY KEY (`dev_inst_rmv_wk_rec_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_dev_inst_rmv_wk_rec_df`
--

LOCK TABLES `dwd_cst_bus_dev_inst_rmv_wk_rec_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_dev_inst_rmv_wk_rec_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_dev_inst_rmv_wk_rec_df` VALUES ('DEV0001','2025-01-31 14:00:00','装拆类别_1','装拆类别名称1','装拆原因_1','装拆原因名称1','2024-09-08 19:00:00','2024-08-31 22:00:00','2024-05-31 00:00:00','2024-05-08 00:00:00','省公司名称1','地市公司名称1','深圳市南山区aa路4号','RO-0001','CO-0001',2970.41,7898.21,9754.37,'CUS0001','CU-0001','客户名称1','华能集团','装拆单位名称1','装拆人员_1','装拆人员名称1','MGT0001','MG-0001','管理单位名称1','AS-0001','设备分类_1','设备分类名称1','容器分类_1','计度器类型_1','计度器类型名称1','INS0001','AP-0001','DEV0001','CTN0001','MET0001','REG0001',2557.22,9175.63),('DEV0002','2024-01-15 22:00:00','装拆类别_2','装拆类别名称2','装拆原因_2','装拆原因名称2','2025-03-19 23:00:00','2025-04-01 14:00:00','2024-08-30 23:00:00','2024-11-16 00:00:00','省公司名称2','地市公司名称2','广州市天河区zz路3号','RO-0002','CO-0002',8789.62,7024.01,3680.29,'CUS0002','CU-0002','客户名称2','国家电投','装拆单位名称2','装拆人员_2','装拆人员名称2','MGT0002','MG-0002','管理单位名称2','AS-0002','设备分类_2','设备分类名称2','容器分类_2','计度器类型_2','计度器类型名称2','INS0002','AP-0002','DEV0002','CTN0002','MET0002','REG0002',5158.37,8385.55),('DEV0003','2024-10-11 10:00:00','装拆类别_3','装拆类别名称3','装拆原因_3','装拆原因名称3','2025-01-07 18:00:00','2024-11-07 12:00:00','2024-04-06 14:00:00','2024-02-06 00:00:00','省公司名称3','地市公司名称3','深圳市南山区aa路4号','RO-0003','CO-0003',2135.96,5132.45,2047.33,'CUS0003','CU-0003','客户名称3','大唐集团','装拆单位名称3','装拆人员_3','装拆人员名称3','MGT0003','MG-0003','管理单位名称3','AS-0003','设备分类_3','设备分类名称3','容器分类_3','计度器类型_3','计度器类型名称3','INS0003','AP-0003','DEV0003','CTN0003','MET0003','REG0003',5796.64,8084.54);
/*!40000 ALTER TABLE `dwd_cst_bus_dev_inst_rmv_wk_rec_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_dev_rcpt_app_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_dev_rcpt_app_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_dev_rcpt_app_df` (
  `id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` datetime DEFAULT NULL,
  `rcpt_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_date` datetime DEFAULT NULL,
  `rcpt_date` datetime DEFAULT NULL,
  `biz_date` double DEFAULT NULL,
  `prov_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `applnt` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcpt_lnt` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_dept` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pro_spec_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pro_spec_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_form_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcpt_usage` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcpt_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcpt_dept` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcv_ret_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_src` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_use_stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_rslt` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_rcpt_app_dtl_info_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_dtl_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_dtl_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `return_app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pro_spec_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_num` double DEFAULT NULL,
  `aprv_num` double DEFAULT NULL,
  `rcpt_time_limit` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_dev_rcpt_app_df`
--

LOCK TABLES `dwd_cst_bus_dev_rcpt_app_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_dev_rcpt_app_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_dev_rcpt_app_df` VALUES ('ID0001','2024-07-11 19:00:00','领用类型_1','2024-05-03 17:00:00','2024-05-12 23:00:00',8802.91,'省公司名称1','地市公司名称1','CUS0001','CU-0001','客户名称1','申请人_1','领用责任人_1','联系方式_1','申请部门_1','MGT0001','MG-0001','管理单位名称1','PRO0001','品规名称1','APP0001','领用用途_1','领用说明测试数据1','领用班组_1','领退标志_1','数据来源_1','注销','检验结果_1','DEV0001','DEV0001','APP0001','AP-0001','WK-0001','AP-0001','RE-0001','PR-0001','启用',1708.16,2299.83,'2025-02-25 00:00:00'),('ID0002','2025-03-14 21:00:00','领用类型_2','2024-04-18 15:00:00','2024-06-26 08:00:00',1074.69,'省公司名称2','地市公司名称2','CUS0002','CU-0002','客户名称2','申请人_2','领用责任人_2','联系方式_2','申请部门_2','MGT0002','MG-0002','管理单位名称2','PRO0002','品规名称2','APP0002','领用用途_2','领用说明测试数据2','领用班组_2','领退标志_2','数据来源_2','激活','检验结果_2','DEV0002','DEV0002','APP0002','AP-0002','WK-0002','AP-0002','RE-0002','PR-0002','正常',7135.32,6306.44,'2024-01-07 00:00:00'),('ID0003','2024-02-14 12:00:00','领用类型_3','2024-06-02 06:00:00','2024-05-10 07:00:00',642.43,'省公司名称3','地市公司名称3','CUS0003','CU-0003','客户名称3','申请人_3','领用责任人_3','联系方式_3','申请部门_3','MGT0003','MG-0003','管理单位名称3','PRO0003','品规名称3','APP0003','领用用途_3','领用说明测试数据3','领用班组_3','领退标志_3','数据来源_3','停用','检验结果_3','DEV0003','DEV0003','APP0003','AP-0003','WK-0003','AP-0003','RE-0003','PR-0003','异常',1430.97,8682.96,'2024-10-18 00:00:00');
/*!40000 ALTER TABLE `dwd_cst_bus_dev_rcpt_app_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_elec_app_arch_rec_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_elec_app_arch_rec_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_elec_app_arch_rec_df` (
  `cust_elec_app_rec_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` datetime DEFAULT NULL,
  `ind_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `high_ec_ind_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `high_ec_ind_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dereg_attr_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dereg_attr_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `estab_acct_date` datetime DEFAULT NULL,
  `cncl_date` datetime DEFAULT NULL,
  `app_exec_beg_date` datetime DEFAULT NULL,
  `app_exec_end_date` datetime DEFAULT NULL,
  `es_date` datetime DEFAULT NULL,
  `tmp_expr_date` datetime DEFAULT NULL,
  `last_insp_date` datetime DEFAULT NULL,
  `chg_date` datetime DEFAULT NULL,
  `lastupddate` datetime DEFAULT NULL,
  `hldy` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_cons_cust_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `orgn_cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `new_cust_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bp_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `new_bp_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `main_hshd_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `main_hshd_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ecc_stat` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ecc_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_app_form_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_app_rec_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cost_ctrl_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cost_ctrl_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `impt_lv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `impt_lv_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_charts` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_charts_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_char` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_char_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `after_chg_pres_brg_pres` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `after_chg_pres_brg_pres_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tmp_ec_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tmp_ec_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prod_shift` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_supl_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_supl_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_supl_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_supl_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvr_supl_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvr_supl_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `permanent_dec_cap_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `graded_settle_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `need_drflag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_subst_srv_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prtp_mkt_trans` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_incr_srv_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_heat_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cte_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_charg_fac` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attach_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pwr_off_reason` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cstm_qry_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chkr_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exec_seq` int DEFAULT NULL,
  `arch_status` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `orgn_ctrt_cap` double DEFAULT NULL,
  `ctrt_cap` double DEFAULT NULL,
  `app_ctrt_cap` double DEFAULT NULL,
  `t_ctrt_cap` double DEFAULT NULL,
  `orgn_run_cap` double DEFAULT NULL,
  `run_cap` double DEFAULT NULL,
  `app_run_cap` double DEFAULT NULL,
  `t_run_cap` double DEFAULT NULL,
  `tfrin_ctrt_cap` double DEFAULT NULL,
  `tfr_out_ctrt_cap` double DEFAULT NULL,
  `recent_elec_cons_cap` double DEFAULT NULL,
  `fwd_elec_cons_cap` double DEFAULT NULL,
  `scy_cap` double DEFAULT NULL,
  `e_carea` double DEFAULT NULL,
  `ec_stf_num` int DEFAULT NULL,
  `app_days` int DEFAULT NULL,
  `chk_cyc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `usage_dur` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`cust_elec_app_rec_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_elec_app_arch_rec_df`
--

LOCK TABLES `dwd_cst_bus_elec_app_arch_rec_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_elec_app_arch_rec_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_elec_app_arch_rec_df` VALUES ('CUS0001','2024-12-26 09:00:00','行业分类_1','行业分类名称1','用电类别_1','用电类别名称1','高耗能行业分类_1','高耗能行业分类名称1','市场化属性分类_1','市场化属性分类名称1','2025-02-09 10:00:00','2025-02-02 13:00:00','2024-08-03 15:00:00','2024-05-14 17:00:00','2025-03-29 10:00:00','2024-05-23 18:00:00','2024-04-30 14:00:00','2024-02-19 04:00:00','2024-08-17 12:00:00','厂休日_1','省份名称1','地市名称1','ELE0001','CUS0001','CU-0001','OR-0001','客户名称1','新客户名称1','BP0001','NEW0001','客户分类_1','客户分类描述1','主户标志_1','主户标志描述1','转供户标志_1','转供户标志描述1','启用','用电客户状态描述1','MG-0001','管理单位名称1','BUS0001','CUS0001','28017.51','费控标志描述1','重要性等级_1','重要性等级描述1','负荷特性_1','负荷特性描述1','负荷性质_1','负荷性质描述1','承压_1','承压描述1','改压后承压_1','改压后承压描述1','临时用能标志_1','临时用能标志描述1','生产班次_1','停供标志_1','停供标志描述1','停供方式_1','停供方式描述1','复供方式_1','复供方式描述1','校验方式_1','永久性减容标志_1','分次结算标志_1','需求响应标志_1','电能代替服务标志_1','参与市场交易标志_1','能效提升服务标志_1','电采暖标志_1','煤改电标志_1','充换电设施标志_1','ATT0001','变更说明测试数据1','停电原因_1','CS-0001','CH-0001',719908,'激活',2387.21,240.48,7259.17,3874.58,857.34,1008.39,2341.98,9470.01,6215.17,1638.16,939.57,2864.78,7780.97,1240.37,651858,634097,'检查周期_1','使用期限_1'),('CUS0002','2025-01-31 22:00:00','行业分类_2','行业分类名称2','用电类别_2','用电类别名称2','高耗能行业分类_2','高耗能行业分类名称2','市场化属性分类_2','市场化属性分类名称2','2024-01-02 14:00:00','2024-05-29 04:00:00','2024-06-29 00:00:00','2024-04-12 18:00:00','2024-11-11 04:00:00','2024-04-12 14:00:00','2025-03-09 06:00:00','2024-02-27 05:00:00','2025-03-04 15:00:00','厂休日_2','省份名称2','地市名称2','ELE0002','CUS0002','CU-0002','OR-0002','客户名称2','新客户名称2','BP0002','NEW0002','客户分类_2','客户分类描述2','主户标志_2','主户标志描述2','转供户标志_2','转供户标志描述2','启用','用电客户状态描述2','MG-0002','管理单位名称2','BUS0002','CUS0002','27772.94','费控标志描述2','重要性等级_2','重要性等级描述2','负荷特性_2','负荷特性描述2','负荷性质_2','负荷性质描述2','承压_2','承压描述2','改压后承压_2','改压后承压描述2','临时用能标志_2','临时用能标志描述2','生产班次_2','停供标志_2','停供标志描述2','停供方式_2','停供方式描述2','复供方式_2','复供方式描述2','校验方式_2','永久性减容标志_2','分次结算标志_2','需求响应标志_2','电能代替服务标志_2','参与市场交易标志_2','能效提升服务标志_2','电采暖标志_2','煤改电标志_2','充换电设施标志_2','ATT0002','变更说明测试数据2','停电原因_2','CS-0002','CH-0002',457771,'启用',6926.29,2797.19,2150.52,9934.1,4298.34,3737.21,687.45,9767.74,5363.35,8969.2,2212.9,6862.1,6022.35,6666.42,794350,50933,'检查周期_2','使用期限_2'),('CUS0003','2024-05-06 19:00:00','行业分类_3','行业分类名称3','用电类别_3','用电类别名称3','高耗能行业分类_3','高耗能行业分类名称3','市场化属性分类_3','市场化属性分类名称3','2024-06-14 17:00:00','2025-02-28 21:00:00','2024-02-15 10:00:00','2024-05-05 16:00:00','2025-03-14 23:00:00','2024-03-28 20:00:00','2024-11-02 01:00:00','2025-05-13 04:00:00','2024-07-18 09:00:00','厂休日_3','省份名称3','地市名称3','ELE0003','CUS0003','CU-0003','OR-0003','客户名称3','新客户名称3','BP0003','NEW0003','客户分类_3','客户分类描述3','主户标志_3','主户标志描述3','转供户标志_3','转供户标志描述3','启用','用电客户状态描述3','MG-0003','管理单位名称3','BUS0003','CUS0003','76505.21','费控标志描述3','重要性等级_3','重要性等级描述3','负荷特性_3','负荷特性描述3','负荷性质_3','负荷性质描述3','承压_3','承压描述3','改压后承压_3','改压后承压描述3','临时用能标志_3','临时用能标志描述3','生产班次_3','停供标志_3','停供标志描述3','停供方式_3','停供方式描述3','复供方式_3','复供方式描述3','校验方式_3','永久性减容标志_3','分次结算标志_3','需求响应标志_3','电能代替服务标志_3','参与市场交易标志_3','能效提升服务标志_3','电采暖标志_3','煤改电标志_3','充换电设施标志_3','ATT0003','变更说明测试数据3','停电原因_3','CS-0003','CH-0003',287425,'异常',712.67,7420.15,3464.46,561.7,5208.63,6756.51,9305.65,2040.74,8877.97,1017.12,8399.07,1540.36,4677.82,7582.23,526697,4633,'检查周期_3','使用期限_3');
/*!40000 ALTER TABLE `dwd_cst_bus_elec_app_arch_rec_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_exp_chrg_rec_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_exp_chrg_rec_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_exp_chrg_rec_df` (
  `op_exp_rcvd_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` datetime DEFAULT NULL,
  `srv_kind` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvd_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvd_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `biz_date` double DEFAULT NULL,
  `prov_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_stf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_dept` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `op_exp_rcvbl_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_acct_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_acct_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `note_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acct_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvd_amt` double DEFAULT NULL,
  PRIMARY KEY (`op_exp_rcvd_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_exp_chrg_rec_df`
--

LOCK TABLES `dwd_cst_bus_exp_chrg_rec_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_exp_chrg_rec_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_exp_chrg_rec_df` VALUES ('OP0001','2024-12-26 17:00:00','服务种类_1','服务种类名称1','收费类型_1','收费类型名称1','实收年月_1','2024-03-25 00:00:00',3812.46,'省公司名称1','地市公司名称1','CUS0001','CU-0001','客户名称1','收费人员_1','收费部门_1','MGT0001','MG-0001','管理单位名称1','OP0001','PAY0001','SET0001','NOT0001','AC-0001',5108.57),('OP0002','2025-05-14 10:00:00','服务种类_2','服务种类名称2','收费类型_2','收费类型名称2','实收年月_2','2024-11-24 00:00:00',8103.84,'省公司名称2','地市公司名称2','CUS0002','CU-0002','客户名称2','收费人员_2','收费部门_2','MGT0002','MG-0002','管理单位名称2','OP0002','PAY0002','SET0002','NOT0002','AC-0002',4501.18),('OP0003','2025-01-29 22:00:00','服务种类_3','服务种类名称3','收费类型_3','收费类型名称3','实收年月_3','2024-07-10 00:00:00',8754.84,'省公司名称3','地市公司名称3','CUS0003','CU-0003','客户名称3','收费人员_3','收费部门_3','MGT0003','MG-0003','管理单位名称3','OP0003','PAY0003','SET0003','NOT0003','AC-0003',6175.06);
/*!40000 ALTER TABLE `dwd_cst_bus_exp_chrg_rec_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_gc_app_arch_rec_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_gc_app_arch_rec_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_gc_app_arch_rec_df` (
  `cust_gen_app_rec_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` datetime DEFAULT NULL,
  `srv_kind` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cncl_date` datetime DEFAULT NULL,
  `chg_date` datetime DEFAULT NULL,
  `creat_date` datetime DEFAULT NULL,
  `biz_date` datetime DEFAULT NULL,
  `prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_loc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_addr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `orig_cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `orig_cust_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chkr_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bp_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gpc_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_cust_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gc_stat` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gc_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gc_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gc_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `taxpayer_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `taxpayer_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `grid_volt_lv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `grid_volt_lv_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_pscateg` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_pscateg_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accs_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accs_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_cyc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_cyc_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_consp_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `e_consp_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cntrl_alow_model` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_alow_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_alow_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_alow_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_alow_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_alow_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_alow_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `alow_plcy` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `alow_plcy_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pv_paflag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pv_paflag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arch_status` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arch_status_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ind_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `impt_lv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `impt_lv_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `urbanrural_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `urbanrural_categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tax_rate` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tax_rate_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_app_form_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_app_rec_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_srv_addr_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_cust_app_rec_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_cap` double DEFAULT NULL,
  `ctrt_cap` double DEFAULT NULL,
  `inst_cap` double DEFAULT NULL,
  `t_cap` double DEFAULT NULL,
  `accs_cap` double DEFAULT NULL,
  PRIMARY KEY (`cust_gen_app_rec_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_gc_app_arch_rec_df`
--

LOCK TABLES `dwd_cst_bus_gc_app_arch_rec_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_gc_app_arch_rec_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_gc_app_arch_rec_df` VALUES ('CUS0001','2024-02-07 07:00:00','服务种类_1','服务种类名称1','业务类型_1','业务类型名称1','业务类别_1','业务类别名称1','2025-01-12 16:00:00','2024-03-10 21:00:00','2024-06-06 20:00:00','2024-11-12 14:00:00','省份名称1','地市名称1','安装位置_1','上海市浦东新区yy路2号','CUS0001','OR-0001','CU-0001','客户名称1','原客户名称1','CH-0001','BP0001','MG-0001','管理单位名称1','GPC0001','GEN0001','激活','发电客户状态名称1','发电客户类型_1','发电客户类型名称1','纳税人类型_1','纳税人类型名称1','并网承压等级_1','并网承压等级名称1','发电方式_1','发电方式名称1','客户电源类别_1','客户电源类别描述1','接入方式_1','接入方式名称1','检查周期_1','检查周期名称1','能源消纳方式_1','能源消纳方式名称1','投资模式_1','投资模式名称1','中央补助模式_1','省级补助标志_1','省级补助标志名称1','市级补助标志_1','市级补助标志名称1','776','县级补助标志名称1','补贴政策_1','补贴政策名称1','光伏扶贫标志_1','光伏扶贫标志名称1','备注测试数据1','客户类别_1','客户类别名称1','注销','归档状态名称1','行业分类_1','行业分类名称1','重要性等级_1','重要性等级名称1','变更说明测试数据1','城乡类别_1','城乡类别名称1','税率_1','税率名称1','BUS0001','AP-0001','CUS0001','BUS0001','GEN0001',6730.72,3540.64,9868.42,8702.12,7268.32),('CUS0002','2025-01-12 14:00:00','服务种类_2','服务种类名称2','业务类型_2','业务类型名称2','业务类别_2','业务类别名称2','2024-03-16 05:00:00','2024-03-07 09:00:00','2024-01-29 21:00:00','2025-03-10 17:00:00','省份名称2','地市名称2','安装位置_2','杭州市西湖区bb路5号','CUS0002','OR-0002','CU-0002','客户名称2','原客户名称2','CH-0002','BP0002','MG-0002','管理单位名称2','GPC0002','GEN0002','异常','发电客户状态名称2','发电客户类型_2','发电客户类型名称2','纳税人类型_2','纳税人类型名称2','并网承压等级_2','并网承压等级名称2','发电方式_2','发电方式名称2','客户电源类别_2','客户电源类别描述2','接入方式_2','接入方式名称2','检查周期_2','检查周期名称2','能源消纳方式_2','能源消纳方式名称2','投资模式_2','投资模式名称2','中央补助模式_2','省级补助标志_2','省级补助标志名称2','市级补助标志_2','市级补助标志名称2','500','县级补助标志名称2','补贴政策_2','补贴政策名称2','光伏扶贫标志_2','光伏扶贫标志名称2','备注测试数据2','客户类别_2','客户类别名称2','激活','归档状态名称2','行业分类_2','行业分类名称2','重要性等级_2','重要性等级名称2','变更说明测试数据2','城乡类别_2','城乡类别名称2','税率_2','税率名称2','BUS0002','AP-0002','CUS0002','BUS0002','GEN0002',9441.79,9144,3985.63,3209.63,8017.56),('CUS0003','2024-12-05 06:00:00','服务种类_3','服务种类名称3','业务类型_3','业务类型名称3','业务类别_3','业务类别名称3','2024-03-12 06:00:00','2024-08-08 05:00:00','2024-07-16 07:00:00','2024-03-09 08:00:00','省份名称3','地市名称3','安装位置_3','北京市朝阳区xx路1号','CUS0003','OR-0003','CU-0003','客户名称3','原客户名称3','CH-0003','BP0003','MG-0003','管理单位名称3','GPC0003','GEN0003','激活','发电客户状态名称3','发电客户类型_3','发电客户类型名称3','纳税人类型_3','纳税人类型名称3','并网承压等级_3','并网承压等级名称3','发电方式_3','发电方式名称3','客户电源类别_3','客户电源类别描述3','接入方式_3','接入方式名称3','检查周期_3','检查周期名称3','能源消纳方式_3','能源消纳方式名称3','投资模式_3','投资模式名称3','中央补助模式_3','省级补助标志_3','省级补助标志名称3','市级补助标志_3','市级补助标志名称3','930','县级补助标志名称3','补贴政策_3','补贴政策名称3','光伏扶贫标志_3','光伏扶贫标志名称3','备注测试数据3','客户类别_3','客户类别名称3','激活','归档状态名称3','行业分类_3','行业分类名称3','重要性等级_3','重要性等级名称3','变更说明测试数据3','城乡类别_3','城乡类别名称3','税率_3','税率名称3','BUS0003','AP-0003','CUS0003','BUS0003','GEN0003',5336.02,9336.84,1738.9,2440.58,2398.54);
/*!40000 ALTER TABLE `dwd_cst_bus_gc_app_arch_rec_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_inst_elec_sch_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_inst_elec_sch_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_inst_elec_sch_df` (
  `inst_elec_sch_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `creat_date` datetime DEFAULT NULL,
  `valid_date` datetime DEFAULT NULL,
  `chg_date` datetime DEFAULT NULL,
  `biz_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_lv` double DEFAULT NULL,
  `inst_mgt_order_sn` double DEFAULT NULL,
  `mr_sn` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sw_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bilg_unit_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mr_unit_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_loss_calc_mode_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_agrt_sch_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exec_seq` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_addr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prem_app_rec_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `loc_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cntrl_sta_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_sta_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prem_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_app_form_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_loc_elec_app_rec_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_agrt_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fqr_val` double DEFAULT NULL,
  `apll_calc_val` double DEFAULT NULL,
  `inst_cap` double DEFAULT NULL,
  `pt_ap_inc_loss` double DEFAULT NULL,
  `pt_rp_inc_loss` double DEFAULT NULL,
  `rp_ll_calc_val` double DEFAULT NULL,
  `response_load` double DEFAULT NULL,
  `pipeline_loss_share_agrt_val` double DEFAULT NULL,
  `e_loss_agrt_val` double DEFAULT NULL,
  PRIMARY KEY (`inst_elec_sch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_inst_elec_sch_df`
--

LOCK TABLES `dwd_cst_bus_inst_elec_sch_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_inst_elec_sch_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_inst_elec_sch_df` VALUES ('INS0001','2024-02-05 00:00:00','2024-01-15 23:00:00','2024-09-14 10:00:00','2024-11-09 22:00:00','2024-01-19 00:00:00','省公司名称1','地市公司名称1','CUS0001','CU-0001','客户名称1','MGT0001','MG-0001','管理单位名称1','IN-0001','AP-0001','安装点名称1',2176.24,760.33,'抄表顺序号_1','SW-0001','BI-0001','MR-0001','用能类别_1','PI-0001','CUS0001','执行顺序号_1','杭州市西湖区bb路5号','PRE0001','INS0001','LOC0001','CNT0001','DIS0001','PIP0001','SRV0001','PRE0001','BUS0001','IOT0001','IO-0001','SRV0001','CUS0001',9765.88,9841.18,1318.81,1223.73,4317.06,1055.62,9167.51,3442.89,222.98),('INS0002','2024-11-08 00:00:00','2024-06-24 02:00:00','2024-12-03 23:00:00','2024-10-09 16:00:00','2024-05-11 00:00:00','省公司名称2','地市公司名称2','CUS0002','CU-0002','客户名称2','MGT0002','MG-0002','管理单位名称2','IN-0002','AP-0002','安装点名称2',1351.24,4900.73,'抄表顺序号_2','SW-0002','BI-0002','MR-0002','用能类别_2','PI-0002','CUS0002','执行顺序号_2','上海市浦东新区yy路2号','PRE0002','INS0002','LOC0002','CNT0002','DIS0002','PIP0002','SRV0002','PRE0002','BUS0002','IOT0002','IO-0002','SRV0002','CUS0002',9906.14,1052.67,6248.54,259.47,8358.06,4026.54,4127.61,6862.3,1091.82),('INS0003','2024-04-18 00:00:00','2024-08-26 01:00:00','2024-08-29 23:00:00','2025-03-16 14:00:00','2025-02-07 00:00:00','省公司名称3','地市公司名称3','CUS0003','CU-0003','客户名称3','MGT0003','MG-0003','管理单位名称3','IN-0003','AP-0003','安装点名称3',5798.75,9704.99,'抄表顺序号_3','SW-0003','BI-0003','MR-0003','用能类别_3','PI-0003','CUS0003','执行顺序号_3','广州市天河区zz路3号','PRE0003','INS0003','LOC0003','CNT0003','DIS0003','PIP0003','SRV0003','PRE0003','BUS0003','IOT0003','IO-0003','SRV0003','CUS0003',6704.42,5238.64,9628.25,8625.27,4557.54,4894.33,4040.36,4934.94,841.34);
/*!40000 ALTER TABLE `dwd_cst_bus_inst_elec_sch_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_invest_order_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_invest_order_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_invest_order_df` (
  `invest_order_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` datetime DEFAULT NULL,
  `app_ind_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_ind_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_elec_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_elec_categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_date` datetime DEFAULT NULL,
  `biz_date` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_co_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_stf` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_stf_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_manager` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_opn` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_remark` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cost_ctrl_user` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acc_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fs_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `avail_es_chg_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `breach_ctrt_eactn_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `breach_ctrt_elec_cons_actn_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_reason` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_reason_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `nec_mtrl_intact_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `op_exp_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eng_ect_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eng_ect_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvr_pwr_flag_succ_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `theft_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exist_charg_pile_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exist_derflag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_e_dmd_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_e_dmd_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_e_dmd_categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_rela` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attach_id` double DEFAULT NULL,
  `cfg_out_wh` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `land_char` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `land_char_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bld_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bld_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `design_review` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eng_cnfm_opn` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_quip` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_bld_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_bld_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `invest_order_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_app_form_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_elec_cons_cap` double DEFAULT NULL,
  `app_elec_cap` double DEFAULT NULL,
  PRIMARY KEY (`invest_order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_invest_order_df`
--

LOCK TABLES `dwd_cst_bus_invest_order_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_invest_order_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_invest_order_df` VALUES ('INV0001','2024-09-25 01:00:00','申请行业分类_1','申请行业分类名称1','申请用能类别_1','申请用能类别名称1','2024-12-31 05:00:00','2024-07-25 00:00:00','省公司名称1','地市公司名称1','CUS0001','CU-0001','客户名称1','勘查员(目前源端_1','勘查员名称1','客户经理_1','MGT0001','MG-0001','管理单位名称1','勘查意见_1','勘查备注测试数据1','24819.47','转供标志_1','转供标志名称1','承压_1','承压名称1','接入标志_1','可研标志_1','可供能或变更标志_1','违约用能行为标志_1','违约用能行为描述测试数据1','故障标志_1','故障原因_1','故障原因名称1','必备资料齐全标志_1','业务费标志_1','有工程标志_1','有工程标志名称1','复供成功标志_1','失窃标志_1','充电桩标志_1','存在分布式电源标_1','综合能源需求标志_1','综合能源需求类别_1','综合能源需求类别名称1','转供关系_1',1884.93,'配置出库标志_1','土地性质_1','土地性质名称1','建设模式_1','建设模式名称1','是否设计审查_1','变更说明测试数据1','工程确认意见_1','故障装置_1','投资建设模式_1','投资建设模式名称1','IN-0001','BUS0001','AP-0001',7140.85,3606.33),('INV0002','2024-01-31 19:00:00','申请行业分类_2','申请行业分类名称2','申请用能类别_2','申请用能类别名称2','2024-09-12 21:00:00','2025-01-05 00:00:00','省公司名称2','地市公司名称2','CUS0002','CU-0002','客户名称2','勘查员(目前源端_2','勘查员名称2','客户经理_2','MGT0002','MG-0002','管理单位名称2','勘查意见_2','勘查备注测试数据2','75459.11','转供标志_2','转供标志名称2','承压_2','承压名称2','接入标志_2','可研标志_2','可供能或变更标志_2','违约用能行为标志_2','违约用能行为描述测试数据2','故障标志_2','故障原因_2','故障原因名称2','必备资料齐全标志_2','业务费标志_2','有工程标志_2','有工程标志名称2','复供成功标志_2','失窃标志_2','充电桩标志_2','存在分布式电源标_2','综合能源需求标志_2','综合能源需求类别_2','综合能源需求类别名称2','转供关系_2',8299.75,'配置出库标志_2','土地性质_2','土地性质名称2','建设模式_2','建设模式名称2','是否设计审查_2','变更说明测试数据2','工程确认意见_2','故障装置_2','投资建设模式_2','投资建设模式名称2','IN-0002','BUS0002','AP-0002',1561.58,2346.49),('INV0003','2024-01-10 04:00:00','申请行业分类_3','申请行业分类名称3','申请用能类别_3','申请用能类别名称3','2024-07-09 02:00:00','2024-08-28 00:00:00','省公司名称3','地市公司名称3','CUS0003','CU-0003','客户名称3','勘查员(目前源端_3','勘查员名称3','客户经理_3','MGT0003','MG-0003','管理单位名称3','勘查意见_3','勘查备注测试数据3','63388.83','转供标志_3','转供标志名称3','承压_3','承压名称3','接入标志_3','可研标志_3','可供能或变更标志_3','违约用能行为标志_3','违约用能行为描述测试数据3','故障标志_3','故障原因_3','故障原因名称3','必备资料齐全标志_3','业务费标志_3','有工程标志_3','有工程标志名称3','复供成功标志_3','失窃标志_3','充电桩标志_3','存在分布式电源标_3','综合能源需求标志_3','综合能源需求类别_3','综合能源需求类别名称3','转供关系_3',3229.14,'配置出库标志_3','土地性质_3','土地性质名称3','建设模式_3','建设模式名称3','是否设计审查_3','变更说明测试数据3','工程确认意见_3','故障装置_3','投资建设模式_3','投资建设模式名称3','IN-0003','BUS0003','AP-0003',197.23,8468.11);
/*!40000 ALTER TABLE `dwd_cst_bus_invest_order_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_iot_dev_sch_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_iot_dev_sch_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_iot_dev_sch_df` (
  `id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `made_time` datetime DEFAULT NULL,
  `acmp_time` datetime DEFAULT NULL,
  `run_date` datetime DEFAULT NULL,
  `biz_date` double DEFAULT NULL,
  `prov_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_dev_sch_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prnt_iot_point_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `made_dept` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `downlink_comm_chan` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `run_stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_card_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_affil` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `produce_mfr_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `trml_addr_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_asset_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_loc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_dev_sch_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `loc_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_iot_dev_sch_df`
--

LOCK TABLES `dwd_cst_bus_iot_dev_sch_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_iot_dev_sch_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_iot_dev_sch_df` VALUES ('ID0001','2024-08-09 00:00:00','2025-04-12 15:00:00','2024-06-11 02:00:00','2024-03-06 20:00:00',2141.78,'省公司名称1','地市公司名称1','CUS0001','CU-0001','客户名称1','MGT0001','MG-0001','管理单位名称1','IO-0001','AP-0001','PR-0001','IO-0001','制定部门_1','下行通信信道_1','正常','IO-0001','设备归属_1','PR-0001','TR-0001','DE-0001','安装位置_1','IOT0001','LOC0001','DEV0001'),('ID0002','2024-07-28 00:00:00','2025-01-02 11:00:00','2024-06-03 02:00:00','2025-04-22 15:00:00',551.68,'省公司名称2','地市公司名称2','CUS0002','CU-0002','客户名称2','MGT0002','MG-0002','管理单位名称2','IO-0002','AP-0002','PR-0002','IO-0002','制定部门_2','下行通信信道_2','启用','IO-0002','设备归属_2','PR-0002','TR-0002','DE-0002','安装位置_2','IOT0002','LOC0002','DEV0002'),('ID0003','2025-05-01 00:00:00','2024-07-20 06:00:00','2025-01-06 06:00:00','2024-03-30 17:00:00',6049.26,'省公司名称3','地市公司名称3','CUS0003','CU-0003','客户名称3','MGT0003','MG-0003','管理单位名称3','IO-0003','AP-0003','PR-0003','IO-0003','制定部门_3','下行通信信道_3','异常','IO-0003','设备归属_3','PR-0003','TR-0003','DE-0003','安装位置_3','IOT0003','LOC0003','DEV0003');
/*!40000 ALTER TABLE `dwd_cst_bus_iot_dev_sch_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_iot_point_sch_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_iot_point_sch_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_iot_point_sch_df` (
  `iot_point_sch_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acq_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acq_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `aux_node` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accs_task_dtl_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_sch_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iot_point_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `uplink_iot_point_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_sta_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `loc_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`iot_point_sch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_iot_point_sch_df`
--

LOCK TABLES `dwd_cst_bus_iot_point_sch_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_iot_point_sch_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_iot_point_sch_df` VALUES ('IOT0001','2025-03-26 00:00:00','物联点类型_1','物联点类型名称1','采集方式_1','采集方式名称1','省公司名称1','地市公司名称1','CUS0001','CU-0001','客户名称1','MGT0001','MG-0001','管理单位名称1','CH-0001','变更类型名称1','AU-0001','ACC0001','IO-0001','IO-0001','物联点名称1','UP-0001','DIS0001','LOC0001'),('IOT0002','2024-02-20 00:00:00','物联点类型_2','物联点类型名称2','采集方式_2','采集方式名称2','省公司名称2','地市公司名称2','CUS0002','CU-0002','客户名称2','MGT0002','MG-0002','管理单位名称2','CH-0002','变更类型名称2','AU-0002','ACC0002','IO-0002','IO-0002','物联点名称2','UP-0002','DIS0002','LOC0002'),('IOT0003','2025-02-19 00:00:00','物联点类型_3','物联点类型名称3','采集方式_3','采集方式名称3','省公司名称3','地市公司名称3','CUS0003','CU-0003','客户名称3','MGT0003','MG-0003','管理单位名称3','CH-0003','变更类型名称3','AU-0003','ACC0003','IO-0003','IO-0003','物联点名称3','UP-0003','DIS0003','LOC0003');
/*!40000 ALTER TABLE `dwd_cst_bus_iot_point_sch_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_it_sch_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_it_sch_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_it_sch_df` (
  `it_sch_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `it_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `it_categ_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `it_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `it_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_date` datetime DEFAULT NULL,
  `last_insp_date` datetime DEFAULT NULL,
  `chg_date` datetime DEFAULT NULL,
  `wk_order_acmp_time` datetime DEFAULT NULL,
  `biz_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cali_cyc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_winding_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bar_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `it_logic_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `share_it_logic_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `share_it_sch_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `it_phase` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `it_phase_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `it_volt_tr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `it_volt_tr_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `it_cur_tr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `it_cur_tr_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accu_lv` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accu_lv_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_spcl_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_spcl_flag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_desc_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `share_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `share_flag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arch_status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arch_status_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tv_accu_lv` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tv_accu_lv_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prop_own` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prop_own_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `it_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `loc_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_elec_sch_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`it_sch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_it_sch_df`
--

LOCK TABLES `dwd_cst_bus_it_sch_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_it_sch_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_it_sch_df` VALUES ('IT0001','2025-05-07 00:00:00','IT-0001','互感器类别名称1','IT-0001','互感器类型名称1','2024-11-18 06:00:00','2025-01-24 08:00:00','2025-02-26 02:00:00','2025-04-23 11:00:00','2024-04-15 00:00:00','省公司名称1','地市公司名称1','CUS0001','客户名称1','MGT0001','MG-0001','管理单位名称1','DE-0001','AP-0001','设备描述测试数据1','校验周期_1','ME-0001','BA-0001','IT0001','SHA0001','SHA0001','互感器相别_1','互感器相别名称1','互感器电压变比_1','互感器电压变比名称1','互感器电流变比_1','互感器电流变比名称1','IN-0001','安装方式名称1','准确度等级_1','准确度等级名称1','故障类型_1','故障类型名称1','计量专用标志_1','计量专用标志名称1','CH-0001','变更说明名称1','共用标志_1','共用标志名称1','激活','归档状态名称1','TV准确度等级_1','TV准确度等级名称1','产权归属_1','产权归属名称1','IT0001','INS0001','LOC0001','INS0001'),('IT0002','2025-05-11 00:00:00','IT-0002','互感器类别名称2','IT-0002','互感器类型名称2','2024-02-07 12:00:00','2024-10-26 19:00:00','2024-10-16 03:00:00','2024-01-25 22:00:00','2024-07-03 00:00:00','省公司名称2','地市公司名称2','CUS0002','客户名称2','MGT0002','MG-0002','管理单位名称2','DE-0002','AP-0002','设备描述测试数据2','校验周期_2','ME-0002','BA-0002','IT0002','SHA0002','SHA0002','互感器相别_2','互感器相别名称2','互感器电压变比_2','互感器电压变比名称2','互感器电流变比_2','互感器电流变比名称2','IN-0002','安装方式名称2','准确度等级_2','准确度等级名称2','故障类型_2','故障类型名称2','计量专用标志_2','计量专用标志名称2','CH-0002','变更说明名称2','共用标志_2','共用标志名称2','注销','归档状态名称2','TV准确度等级_2','TV准确度等级名称2','产权归属_2','产权归属名称2','IT0002','INS0002','LOC0002','INS0002'),('IT0003','2025-03-17 00:00:00','IT-0003','互感器类别名称3','IT-0003','互感器类型名称3','2025-04-21 12:00:00','2025-03-24 18:00:00','2024-06-22 04:00:00','2024-06-12 12:00:00','2024-11-20 00:00:00','省公司名称3','地市公司名称3','CUS0003','客户名称3','MGT0003','MG-0003','管理单位名称3','DE-0003','AP-0003','设备描述测试数据3','校验周期_3','ME-0003','BA-0003','IT0003','SHA0003','SHA0003','互感器相别_3','互感器相别名称3','互感器电压变比_3','互感器电压变比名称3','互感器电流变比_3','互感器电流变比名称3','IN-0003','安装方式名称3','准确度等级_3','准确度等级名称3','故障类型_3','故障类型名称3','计量专用标志_3','计量专用标志名称3','CH-0003','变更说明名称3','共用标志_3','共用标志名称3','正常','归档状态名称3','TV准确度等级_3','TV准确度等级名称3','产权归属_3','产权归属名称3','IT0003','INS0003','LOC0003','INS0003');
/*!40000 ALTER TABLE `dwd_cst_bus_it_sch_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_meter_ctnr_sch_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_meter_ctnr_sch_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_meter_ctnr_sch_df` (
  `meter_ctnr_dev_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `meter_ctnr_dev_sch_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_insp_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_date` datetime DEFAULT NULL,
  `biz_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_model` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_model_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mtrl_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mtrl_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctnr_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cntr_categ_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spec` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spec_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `metetr_row_num` double DEFAULT NULL,
  `col_num` double DEFAULT NULL,
  `lon` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `alt` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_desc_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `made_std` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `made_std_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctnr_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctnr_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arch_status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_affil` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_affil_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spec_size` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `box_meter_remain_num` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ap_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ap_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `loc_id` double DEFAULT NULL,
  `box_meter_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_elec_sch_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_id` double DEFAULT NULL,
  `ps_dev_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bar_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`meter_ctnr_dev_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_meter_ctnr_sch_df`
--

LOCK TABLES `dwd_cst_bus_meter_ctnr_sch_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_meter_ctnr_sch_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_meter_ctnr_sch_df` VALUES ('MET0001','MET0001','2024-11-04 00:00:00','服务种类_1','服务种类名称1','2024-11-10 00:00:00','2025-03-01 00:00:00','2024-10-27 20:00:00','2025-04-10 00:00:00','省公司名称1','地市公司名称1','MGT0001','MG-0001','管理单位名称1','型号_1','型号名称1','MT-0001','材料类型名称1','设备描述测试数据1','容器类别_1','容器类别名称1','规格_1','规格名称1',5667.72,3278.42,'经度_1','纬度_1','高程_1','备注测试数据1','变更说明测试数据1','变更说明名称1','安装方式_1','安装方式名称1','制造标准_1','制造标准名称1','容器类型_1','容器类型名称1','激活','ST-0001','AS-0001','资产归属名称1','具体尺寸_1','BO-0001','AP0001','接入点名称1','DE-0001','AP-0001',2391.26,'BO-0001','INS0001',7646.29,'PS0001','BA-0001'),('MET0002','MET0002','2024-04-29 00:00:00','服务种类_2','服务种类名称2','2024-05-12 00:00:00','2024-05-11 00:00:00','2024-06-27 12:00:00','2024-03-07 00:00:00','省公司名称2','地市公司名称2','MGT0002','MG-0002','管理单位名称2','型号_2','型号名称2','MT-0002','材料类型名称2','设备描述测试数据2','容器类别_2','容器类别名称2','规格_2','规格名称2',4849.13,5221,'经度_2','纬度_2','高程_2','备注测试数据2','变更说明测试数据2','变更说明名称2','安装方式_2','安装方式名称2','制造标准_2','制造标准名称2','容器类型_2','容器类型名称2','注销','ST-0002','AS-0002','资产归属名称2','具体尺寸_2','BO-0002','AP0002','接入点名称2','DE-0002','AP-0002',5095.02,'BO-0002','INS0002',223.9,'PS0002','BA-0002'),('MET0003','MET0003','2024-02-19 00:00:00','服务种类_3','服务种类名称3','2025-04-10 00:00:00','2025-02-11 00:00:00','2025-01-13 00:00:00','2024-04-08 00:00:00','省公司名称3','地市公司名称3','MGT0003','MG-0003','管理单位名称3','型号_3','型号名称3','MT-0003','材料类型名称3','设备描述测试数据3','容器类别_3','容器类别名称3','规格_3','规格名称3',2851.59,1491.57,'经度_3','纬度_3','高程_3','备注测试数据3','变更说明测试数据3','变更说明名称3','安装方式_3','安装方式名称3','制造标准_3','制造标准名称3','容器类型_3','容器类型名称3','正常','ST-0003','AS-0003','资产归属名称3','具体尺寸_3','BO-0003','AP0003','接入点名称3','DE-0003','AP-0003',8874.95,'BO-0003','INS0003',6339.76,'PS0003','BA-0003');
/*!40000 ALTER TABLE `dwd_cst_bus_meter_ctnr_sch_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_meter_sch_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_meter_sch_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_meter_sch_df` (
  `meter_sch_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_dev_tag_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_dev_tag_categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_dev_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_dev_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `instal_date` datetime DEFAULT NULL,
  `last_insp_date` datetime DEFAULT NULL,
  `chg_date` datetime DEFAULT NULL,
  `inst_date` datetime DEFAULT NULL,
  `biz_date` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_co_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_cyc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_dev_pres` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_dev_pres_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_dev_trfc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_dev_trfc_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ref_meter_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ref_meter_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ref_meter_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bar_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ap_accu_lv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ap_accu_lv_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `conn_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_prot` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_prot_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `disp_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `disp_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `card_meter_trip_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `card_meter_trip_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_desc_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arch_status` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arch_status_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pi_caliber` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `share_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `share_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `share_met_logic_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `share_met_sch_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pre_rcpt_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pre_rcpt_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `time_sec` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bidi_meter_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bidi_meter_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sprt_mod_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sprt_mod_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_date` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_date_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_id` int DEFAULT NULL,
  `inst_id` int DEFAULT NULL,
  `dev_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `loc_id` int DEFAULT NULL,
  `meter_logic_id` int DEFAULT NULL,
  `inst_elec_sch_id` int DEFAULT NULL,
  `comp_rto` double DEFAULT NULL,
  `mr_coef` double DEFAULT NULL,
  PRIMARY KEY (`meter_sch_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_meter_sch_df`
--

LOCK TABLES `dwd_cst_bus_meter_sch_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_meter_sch_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_meter_sch_df` VALUES ('MET0001','2024-03-21 00:00:00','表计装置类别_1','表计装置类别名称1','表计装置类型_1','表计装置类型名称1','2024-10-29 16:00:00','2025-04-12 12:00:00','2025-04-09 03:00:00','2024-06-03 04:00:00','2024-08-21 00:00:00','省公司名称1','地市公司名称1','CUS0001','CU-0001','客户名称1','MGT0001','MG-0001','管理单位名称1','设备描述测试数据1','检查周期_1','表计装置承压_1','表计装置承压名称1','表计装置流量_1','表计装置流量名称1','参考表标志_1','参考表标志名称1','REF0001','BA-0001','有功准确度等级_1','有功准确度等级名称1','连接方式_1','故障类型_1','通讯规约_1','通讯规约名称1','通讯方式_1','通讯方式名称1','显示方式_1','显示方式名称1','CA-0001','卡表跳闸方式名称1','CH-0001','变更说明名称1','AR-0001','归档状态名称1','管道口径_1','共用标志_1','共用标志名称1','SHA0001','SHA0001','PR-0001','预领标志名称1','2024-11-24 00:00:00','BI-0001','双向计量标志名称1','SP-0001','支持模块标志名称1','2024-12-28 00:00:00','结算日名称1',314390,669915,'DE-0001','AP-0001',908171,729036,267782,9466.37,5678.76),('MET0002','2024-11-26 00:00:00','表计装置类别_2','表计装置类别名称2','表计装置类型_2','表计装置类型名称2','2024-08-25 18:00:00','2025-03-17 21:00:00','2024-05-17 15:00:00','2024-07-24 16:00:00','2025-01-31 00:00:00','省公司名称2','地市公司名称2','CUS0002','CU-0002','客户名称2','MGT0002','MG-0002','管理单位名称2','设备描述测试数据2','检查周期_2','表计装置承压_2','表计装置承压名称2','表计装置流量_2','表计装置流量名称2','参考表标志_2','参考表标志名称2','REF0002','BA-0002','有功准确度等级_2','有功准确度等级名称2','连接方式_2','故障类型_2','通讯规约_2','通讯规约名称2','通讯方式_2','通讯方式名称2','显示方式_2','显示方式名称2','CA-0002','卡表跳闸方式名称2','CH-0002','变更说明名称2','AR-0002','归档状态名称2','管道口径_2','共用标志_2','共用标志名称2','SHA0002','SHA0002','PR-0002','预领标志名称2','2024-11-20 00:00:00','BI-0002','双向计量标志名称2','SP-0002','支持模块标志名称2','2025-03-22 00:00:00','结算日名称2',512573,945750,'DE-0002','AP-0002',496633,488686,480173,3292.07,3195.88),('MET0003','2025-03-29 00:00:00','表计装置类别_3','表计装置类别名称3','表计装置类型_3','表计装置类型名称3','2024-04-30 19:00:00','2024-12-06 12:00:00','2024-09-23 02:00:00','2024-04-01 17:00:00','2024-05-11 00:00:00','省公司名称3','地市公司名称3','CUS0003','CU-0003','客户名称3','MGT0003','MG-0003','管理单位名称3','设备描述测试数据3','检查周期_3','表计装置承压_3','表计装置承压名称3','表计装置流量_3','表计装置流量名称3','参考表标志_3','参考表标志名称3','REF0003','BA-0003','有功准确度等级_3','有功准确度等级名称3','连接方式_3','故障类型_3','通讯规约_3','通讯规约名称3','通讯方式_3','通讯方式名称3','显示方式_3','显示方式名称3','CA-0003','卡表跳闸方式名称3','CH-0003','变更说明名称3','AR-0003','归档状态名称3','管道口径_3','共用标志_3','共用标志名称3','SHA0003','SHA0003','PR-0003','预领标志名称3','2024-06-13 00:00:00','BI-0003','双向计量标志名称3','SP-0003','支持模块标志名称3','2025-02-13 00:00:00','结算日名称3',203452,909008,'DE-0003','AP-0003',22314,974261,857036,6608.79,6585.03);
/*!40000 ALTER TABLE `dwd_cst_bus_meter_sch_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_stop_rcvr_supl_app_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_stop_rcvr_supl_app_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_stop_rcvr_supl_app_df` (
  `stop_rcvr_supl_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` datetime DEFAULT NULL,
  `srv_kind` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_rcvr_supl_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_rcvr_supl_categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_rcvr_supl_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_rcvr_supl_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_stop_supl_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_stop_supl_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_ym` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_date` datetime DEFAULT NULL,
  `plan_stop_rcvr_supl_time` datetime DEFAULT NULL,
  `acpt_date` datetime DEFAULT NULL,
  `pre_time` datetime DEFAULT NULL,
  `hndl_time` datetime DEFAULT NULL,
  `wrt_time` datetime DEFAULT NULL,
  `stop_rcvr_supl_time` datetime DEFAULT NULL,
  `fdbk_stop_rcvr_supl_fdbk` datetime DEFAULT NULL,
  `biz_date` double DEFAULT NULL,
  `prov_co_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `acpt_stf` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_rcvr_supl_pic` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_supl_prer` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvr_supl_applnt` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_rcvr_supl_stf` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_stop_rcvr_supl_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_stop_rcvr_supl_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_rcvr_supl_reason` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ntce_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnfm_conc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnfm_conc_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnfm_opn` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exec_stat` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exec_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_tel` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sign_fulfl_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sign_fulfl_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spcl_stop_rcvr_supl_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spcl_stop_rcvr_supl_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cur_stop_rcvr_stat` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cur_stop_rcvr_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_rcvr_supl_rslt` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `site_stop_supl_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `site_stop_supl_mode_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_rcvr_supl_situ_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fdbk_ret_rcpt_stat` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fdbk_ret_rcpt_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fdbk_ret_rcpt_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attach_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cost_ctrl_st_app_rec_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_stop_rcvr_stat_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_rcvr_supl_fdbk_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `avail_bal` double DEFAULT NULL,
  `repet_times` double DEFAULT NULL,
  `hndl_round` double DEFAULT NULL,
  PRIMARY KEY (`stop_rcvr_supl_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_stop_rcvr_supl_app_df`
--

LOCK TABLES `dwd_cst_bus_stop_rcvr_supl_app_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_stop_rcvr_supl_app_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_stop_rcvr_supl_app_df` VALUES ('STO0001','2024-07-20 12:00:00','服务种类_1','服务种类名称1','停复供类别_1','停复供类别名称1','停复供类型_1','停复供类型名称1','计划停电方式_1','计划停电方式名称1','用能年月_1','2024-03-02 16:00:00','2024-05-21 19:00:00','2025-03-31 02:00:00','2024-03-08 10:00:00','2024-09-23 06:00:00','2024-05-07 20:00:00','2025-04-15 00:00:00','2025-03-12 23:00:00',9895.66,'省公司名称1','地市公司名称1','受理人员_1','停复供责任人_1','停供准备人_1','复供申请人_1','停复供人员_1','MGT0001','MG-0001','管理单位名称1','CUS0001','CU-0001','用电户名称1','计划停复供方式_1','计划停复供方式名称1','停复供原因_1','NT-0001','确认结论_1','确认结论名称1','确认意见_1','异常','执行状态名称1','13830489763','签订履约协议标志_1','签订履约协议标志名称1','特殊停复供类型_1','特殊停复供类型名称1','正常','当前停复供状态名称1','停复供结果_1','现场停供方式_1','现场停供方式名称1','停复供情况说明测试数据1','激活','反馈回执状态名称1','反馈回执说明测试数据1','ATT0001','COS0001','CUS0001','STO0001','AP-0001',8526.64,2319.17,6559.06),('STO0002','2025-02-21 16:00:00','服务种类_2','服务种类名称2','停复供类别_2','停复供类别名称2','停复供类型_2','停复供类型名称2','计划停电方式_2','计划停电方式名称2','用能年月_2','2024-09-02 03:00:00','2024-12-11 15:00:00','2025-04-17 19:00:00','2024-12-01 02:00:00','2025-02-13 17:00:00','2024-02-08 23:00:00','2024-12-09 23:00:00','2024-12-02 07:00:00',5356.11,'省公司名称2','地市公司名称2','受理人员_2','停复供责任人_2','停供准备人_2','复供申请人_2','停复供人员_2','MGT0002','MG-0002','管理单位名称2','CUS0002','CU-0002','用电户名称2','计划停复供方式_2','计划停复供方式名称2','停复供原因_2','NT-0002','确认结论_2','确认结论名称2','确认意见_2','停用','执行状态名称2','13889155771','签订履约协议标志_2','签订履约协议标志名称2','特殊停复供类型_2','特殊停复供类型名称2','启用','当前停复供状态名称2','停复供结果_2','现场停供方式_2','现场停供方式名称2','停复供情况说明测试数据2','启用','反馈回执状态名称2','反馈回执说明测试数据2','ATT0002','COS0002','CUS0002','STO0002','AP-0002',1097.77,6378.63,9373.45),('STO0003','2024-10-25 13:00:00','服务种类_3','服务种类名称3','停复供类别_3','停复供类别名称3','停复供类型_3','停复供类型名称3','计划停电方式_3','计划停电方式名称3','用能年月_3','2025-04-17 19:00:00','2024-05-12 21:00:00','2024-12-28 22:00:00','2024-08-31 01:00:00','2024-03-18 15:00:00','2024-01-02 09:00:00','2024-01-07 12:00:00','2024-07-21 11:00:00',3935.53,'省公司名称3','地市公司名称3','受理人员_3','停复供责任人_3','停供准备人_3','复供申请人_3','停复供人员_3','MGT0003','MG-0003','管理单位名称3','CUS0003','CU-0003','用电户名称3','计划停复供方式_3','计划停复供方式名称3','停复供原因_3','NT-0003','确认结论_3','确认结论名称3','确认意见_3','激活','执行状态名称3','13835256971','签订履约协议标志_3','签订履约协议标志名称3','特殊停复供类型_3','特殊停复供类型名称3','异常','当前停复供状态名称3','停复供结果_3','现场停供方式_3','现场停供方式名称3','停复供情况说明测试数据3','正常','反馈回执状态名称3','反馈回执说明测试数据3','ATT0003','COS0003','CUS0003','STO0003','AP-0003',2146.34,1746.98,168.33);
/*!40000 ALTER TABLE `dwd_cst_bus_stop_rcvr_supl_app_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_bus_trk_compl_eng_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_trk_compl_eng_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_trk_compl_eng_df` (
  `wk_order_affil_mtrl_rec_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `etl_time` datetime DEFAULT NULL,
  `proj_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_categ_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_affil_mtrl_rec_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_affil_mtrl_rec_cls_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_date` datetime DEFAULT NULL,
  `rcv_time` datetime DEFAULT NULL,
  `plan_veri_time` datetime DEFAULT NULL,
  `main_eng_acmp_time` datetime DEFAULT NULL,
  `rgst_date` datetime DEFAULT NULL,
  `veri_date` datetime DEFAULT NULL,
  `exam_beg_time` datetime DEFAULT NULL,
  `exam_end_time` datetime DEFAULT NULL,
  `biz_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_co_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `applnt` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rcvr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_tel` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rgst` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rvw_person` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_org` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dept_org` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_cont` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `req` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spot_chk_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cstr_rec` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_rslt` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_opn` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_remark` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rect_situ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rect_cont_and_meas` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_app_form_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attach_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `times` double DEFAULT NULL,
  PRIMARY KEY (`wk_order_affil_mtrl_rec_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_trk_compl_eng_df`
--

LOCK TABLES `dwd_cst_bus_trk_compl_eng_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_trk_compl_eng_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_trk_compl_eng_df` VALUES ('WK0001','2024-03-09 19:00:00','PR-0001','工程类别名称1','工单附属资料台账_1','工单附属资料台账分类1','2024-07-25 10:00:00','2025-02-17 18:00:00','2025-03-06 03:00:00','2024-06-14 23:00:00','2024-04-16 04:00:00','2024-12-20 12:00:00','2024-11-11 15:00:00','2024-05-03 01:00:00','2025-04-23 00:00:00','省公司名称1','地市公司名称1','CUS0001','CU-0001','客户名称1','申请人员_1','接收人_1','联系人_1','13832300884','登记人员_1','审查人_1','国家电投','国网电力公司','MGT0001','MG-0001','管理单位名称1','申请内容_1','申请方式_1','要求_1','抽检标志_1','开工备案标志_1','有效标志_1','备注测试数据1','审核结果_1','审核意见_1','审核备注测试数据1','整改情况_1','整改内容及措施_1','BUS0001','ATT0001','AP-0001',6614.51),('WK0002','2025-04-02 22:00:00','PR-0002','工程类别名称2','工单附属资料台账_2','工单附属资料台账分类2','2025-03-18 03:00:00','2024-02-12 20:00:00','2024-02-17 18:00:00','2024-01-05 11:00:00','2025-03-07 08:00:00','2025-03-08 05:00:00','2025-03-03 13:00:00','2024-03-10 12:00:00','2024-03-31 00:00:00','省公司名称2','地市公司名称2','CUS0002','CU-0002','客户名称2','申请人员_2','接收人_2','联系人_2','13845037428','登记人员_2','审查人_2','国网电力公司','华能集团','MGT0002','MG-0002','管理单位名称2','申请内容_2','申请方式_2','要求_2','抽检标志_2','开工备案标志_2','有效标志_2','备注测试数据2','审核结果_2','审核意见_2','审核备注测试数据2','整改情况_2','整改内容及措施_2','BUS0002','ATT0002','AP-0002',4747.45),('WK0003','2024-11-04 03:00:00','PR-0003','工程类别名称3','工单附属资料台账_3','工单附属资料台账分类3','2024-03-01 08:00:00','2024-11-15 09:00:00','2025-05-03 20:00:00','2024-10-01 10:00:00','2024-07-08 12:00:00','2024-08-19 20:00:00','2024-06-21 01:00:00','2024-12-24 06:00:00','2025-01-27 00:00:00','省公司名称3','地市公司名称3','CUS0003','CU-0003','客户名称3','申请人员_3','接收人_3','联系人_3','13876554876','登记人员_3','审查人_3','大唐集团','国网电力公司','MGT0003','MG-0003','管理单位名称3','申请内容_3','申请方式_3','要求_3','抽检标志_3','开工备案标志_3','有效标志_3','备注测试数据3','审核结果_3','审核意见_3','审核备注测试数据3','整改情况_3','整改内容及措施_3','BUS0003','ATT0003','AP-0003',1345.98);
/*!40000 ALTER TABLE `dwd_cst_bus_trk_compl_eng_df` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-04 12:13:49
-- MySQL dump 10.13  Distrib 8.0.39, for Linux (x86_64)
--
-- Host: localhost    Database: tupu
-- ------------------------------------------------------
-- Server version	8.0.39

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `dwd_cst_bus_wk_order_step_df`
--

DROP TABLE IF EXISTS `dwd_cst_bus_wk_order_step_df`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_bus_wk_order_step_df` (
  `id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `work_item_acct_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `step_acct_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proc_acct_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_affil_mtrl_rec_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `affil_mtrl_dtl_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `handle_src` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `step_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `step_type_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proc_source` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_subcls` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_subcls_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_type_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `handler` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `handle_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `initiator` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `work_item_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `work_item_stat_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `step_affil` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `step_affil_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exec_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exec_mode_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `step_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `step_stat_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exec_cond` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proc_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proc_stat_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `white_list_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_stat_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `step_instc_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `step_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `step_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `previous_step_acct_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `work_task_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `work_task_grp_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `task_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `task_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `task_grp_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `task_grp_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `work_item_instc_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sub_wk_order_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pro_instc_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proc_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proc_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proc_diff_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mode_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `parent_proc_acct_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `parent_wk_order_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_attr_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_attr_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sys_mgt_org_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_affil_mtrl_rec_cls` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_affil_mtrl_rec_cls_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_categ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_categ_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `applnt` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_org` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_cont` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `requirement` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `receiver` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_tel` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spot_chk_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `spot_chk_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cstr_rec` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attach_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `registrant` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `valid_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rvw_person` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_rslt` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_rslt_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_opn` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rect_situ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rect_cont_and_meas` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dept_org` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_remark` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_mode` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mtrl_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dtl_item_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dtl_item_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_type_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_cont` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `verf_org` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mtrl_num` double DEFAULT NULL,
  `the_times` double DEFAULT NULL,
  `bgn_time` datetime DEFAULT NULL,
  `end_time` datetime DEFAULT NULL,
  `actl_bgn_time` datetime DEFAULT NULL,
  `actl_end_time` datetime DEFAULT NULL,
  `rcv_time` datetime DEFAULT NULL,
  `due_time` datetime DEFAULT NULL,
  `step_acmp_time` datetime DEFAULT NULL,
  `step_alm_time` datetime DEFAULT NULL,
  `crs_alm_time` datetime DEFAULT NULL,
  `crs_due_time` datetime DEFAULT NULL,
  `proc_creat_time` datetime DEFAULT NULL,
  `proc_acmp_time` datetime DEFAULT NULL,
  `proc_expr_time` datetime DEFAULT NULL,
  `proc_alm_time` datetime DEFAULT NULL,
  `wk_order_creat_time` datetime DEFAULT NULL,
  `wk_order_acmp_time` datetime DEFAULT NULL,
  `app_date` datetime DEFAULT NULL,
  `plan_veri_time` datetime DEFAULT NULL,
  `main_proj_acmptime` datetime DEFAULT NULL,
  `wkorder_affilmtrl_rcv_time` datetime DEFAULT NULL,
  `rgst_date` datetime DEFAULT NULL,
  `aprv_date` datetime DEFAULT NULL,
  `exam_beg_time` datetime DEFAULT NULL,
  `exam_end_time` datetime DEFAULT NULL,
  `etl_time` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_bus_wk_order_step_df`
--

LOCK TABLES `dwd_cst_bus_wk_order_step_df` WRITE;
/*!40000 ALTER TABLE `dwd_cst_bus_wk_order_step_df` DISABLE KEYS */;
INSERT INTO `dwd_cst_bus_wk_order_step_df` VALUES ('ID0001','WOR0001','STE0001','PRO0001','WK0001','WK-0001','MGT0001','WK0001','AFF0001','处理来源_1','ST-0001','环节类型名称1','PR-0001','WK-0001','工单细分名称1','WK-0001','工单类型名称1','省公司名称1','地市公司名称1','处理人_1','处理人名称1','MG-0001','管理单位名称1','发起人_1','WO-0001','工作项状态名称，如待1','ST-0001','环节归属名称1','EX-0001','执行模式名称1','ST-0001','环节状态名称1','执行组件_1','PR-0001','流程状态名称1','白名单标志_1','WK-0001','工单状态名称1','STE0001','ST-0001','环节名称1','PRE0001','WOR0001','WOR0001','TA-0001','任务名称1','TA-0001','任务组名称1','WOR0001','SU-0001','PRO0001','PR-0001','流程名称1','PRO0001','MO-0001','PAR0001','工单名称1','PAR0001','BU-0001','业务属性名称1','SYS0001','WK-0001','工单附属资料台账分类1','PR-0001','工程类别名称1','申请人员_1','南方电网公司','申请内容_1','要求_1','接收人_1','联系人_1','13885483896','SP-0001','抽检标志名称1','开工备案标志_1','ATT0001','备注测试数据1','登记人员_1','VA-0001','审查人_1','VE-0001','审核结果名称1','审核意见_1','整改情况_1','整改内容及措施_1','国家电投','审核备注测试数据1','AP-0001','资料名称1','DT-0001','明细项标志名称1','CH-0001','检查类型名称1','检查内容_1','国家电投',1454.55,3302.11,'2024-01-22 23:00:00','2024-07-24 23:00:00','2024-03-17 08:00:00','2024-04-09 13:00:00','2024-07-20 22:00:00','2024-02-07 01:00:00','2024-04-09 18:00:00','2024-12-27 15:00:00','2025-04-07 09:00:00','2025-03-21 12:00:00','2025-03-30 01:00:00','2024-06-27 12:00:00','2025-05-02 12:00:00','2025-04-19 07:00:00','2024-01-25 21:00:00','2024-10-21 00:00:00','2024-11-26 15:00:00','2024-08-27 17:00:00','2025-03-22 22:00:00','2024-07-31 23:00:00','2024-01-06 07:00:00','2025-03-26 17:00:00','2024-01-03 15:00:00','2024-05-30 11:00:00','2025-02-28 00:00:00'),('ID0002','WOR0002','STE0002','PRO0002','WK0002','WK-0002','MGT0002','WK0002','AFF0002','处理来源_2','ST-0002','环节类型名称2','PR-0002','WK-0002','工单细分名称2','WK-0002','工单类型名称2','省公司名称2','地市公司名称2','处理人_2','处理人名称2','MG-0002','管理单位名称2','发起人_2','WO-0002','工作项状态名称，如待2','ST-0002','环节归属名称2','EX-0002','执行模式名称2','ST-0002','环节状态名称2','执行组件_2','PR-0002','流程状态名称2','白名单标志_2','WK-0002','工单状态名称2','STE0002','ST-0002','环节名称2','PRE0002','WOR0002','WOR0002','TA-0002','任务名称2','TA-0002','任务组名称2','WOR0002','SU-0002','PRO0002','PR-0002','流程名称2','PRO0002','MO-0002','PAR0002','工单名称2','PAR0002','BU-0002','业务属性名称2','SYS0002','WK-0002','工单附属资料台账分类2','PR-0002','工程类别名称2','申请人员_2','华能集团','申请内容_2','要求_2','接收人_2','联系人_2','13817016104','SP-0002','抽检标志名称2','开工备案标志_2','ATT0002','备注测试数据2','登记人员_2','VA-0002','审查人_2','VE-0002','审核结果名称2','审核意见_2','整改情况_2','整改内容及措施_2','国网电力公司','审核备注测试数据2','AP-0002','资料名称2','DT-0002','明细项标志名称2','CH-0002','检查类型名称2','检查内容_2','华能集团',8992.63,7045.42,'2025-04-26 01:00:00','2024-10-01 07:00:00','2025-04-13 22:00:00','2024-08-14 07:00:00','2025-03-17 06:00:00','2024-09-27 18:00:00','2024-08-20 13:00:00','2024-09-01 19:00:00','2025-04-15 04:00:00','2024-07-04 05:00:00','2024-06-18 03:00:00','2024-07-23 17:00:00','2024-09-04 21:00:00','2024-05-18 03:00:00','2024-04-22 11:00:00','2025-02-21 04:00:00','2024-12-29 19:00:00','2025-03-19 21:00:00','2024-04-24 18:00:00','2024-07-06 10:00:00','2025-02-24 18:00:00','2024-06-27 16:00:00','2024-01-27 22:00:00','2025-04-22 01:00:00','2024-04-29 00:00:00'),('ID0003','WOR0003','STE0003','PRO0003','WK0003','WK-0003','MGT0003','WK0003','AFF0003','处理来源_3','ST-0003','环节类型名称3','PR-0003','WK-0003','工单细分名称3','WK-0003','工单类型名称3','省公司名称3','地市公司名称3','处理人_3','处理人名称3','MG-0003','管理单位名称3','发起人_3','WO-0003','工作项状态名称，如待3','ST-0003','环节归属名称3','EX-0003','执行模式名称3','ST-0003','环节状态名称3','执行组件_3','PR-0003','流程状态名称3','白名单标志_3','WK-0003','工单状态名称3','STE0003','ST-0003','环节名称3','PRE0003','WOR0003','WOR0003','TA-0003','任务名称3','TA-0003','任务组名称3','WOR0003','SU-0003','PRO0003','PR-0003','流程名称3','PRO0003','MO-0003','PAR0003','工单名称3','PAR0003','BU-0003','业务属性名称3','SYS0003','WK-0003','工单附属资料台账分类3','PR-0003','工程类别名称3','申请人员_3','国网电力公司','申请内容_3','要求_3','接收人_3','联系人_3','13864327980','SP-0003','抽检标志名称3','开工备案标志_3','ATT0003','备注测试数据3','登记人员_3','VA-0003','审查人_3','VE-0003','审核结果名称3','审核意见_3','整改情况_3','整改内容及措施_3','国网电力公司','审核备注测试数据3','AP-0003','资料名称3','DT-0003','明细项标志名称3','CH-0003','检查类型名称3','检查内容_3','大唐集团',4564.83,7697.54,'2025-03-18 14:00:00','2024-01-10 22:00:00','2024-04-25 07:00:00','2025-01-16 02:00:00','2025-02-06 10:00:00','2025-01-21 09:00:00','2024-12-04 14:00:00','2024-01-18 03:00:00','2025-01-11 15:00:00','2024-06-19 11:00:00','2024-11-12 01:00:00','2024-06-01 07:00:00','2024-08-24 07:00:00','2024-01-13 22:00:00','2024-11-17 03:00:00','2024-09-09 09:00:00','2024-07-19 22:00:00','2025-05-13 17:00:00','2025-03-24 05:00:00','2024-05-31 00:00:00','2024-11-16 15:00:00','2024-12-08 20:00:00','2025-03-15 01:00:00','2024-07-05 22:00:00','2024-06-01 00:00:00');
/*!40000 ALTER TABLE `dwd_cst_bus_wk_order_step_df` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_egmt_mult_typ_power_off_on_day_freeze_dtl`
--

DROP TABLE IF EXISTS `dwd_cst_egmt_mult_typ_power_off_on_day_freeze_dtl`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_egmt_mult_typ_power_off_on_day_freeze_dtl` (
  `dist_sta_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `dist_sta_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_sta_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `junct_stat_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `junct_stat_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `junct_stat_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `affect_cons_num` double DEFAULT NULL,
  `cons_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cons_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cons_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_tm` datetime DEFAULT NULL,
  `freeze_tm` datetime DEFAULT NULL,
  `power_off_on_flg_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweron_tm` datetime DEFAULT NULL,
  `poweroff_dur` double DEFAULT NULL,
  `poweroff_typ_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_judge_caus_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweron_judge_caus_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_entry_tm` datetime DEFAULT NULL,
  `poweron_entry_tm` datetime DEFAULT NULL,
  `org_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `org_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_upward_colle_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_upward_colle_dsc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cplt_src_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cplt_src_dsc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `colle_tm` datetime DEFAULT NULL,
  `crossday_poweroff_filtration_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meas_box_asst_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eqp_poweroff_tm` datetime DEFAULT NULL,
  `eqp_poweron_tm` datetime DEFAULT NULL,
  `supply_num_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `emphasis_cons_typ_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `livelihood_cons_typ_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_essp_cons` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_cate_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_pub_term_num` double DEFAULT NULL,
  `poweroff_priv_term_num` double DEFAULT NULL,
  `poweroff_affect_pub_cons_num` double DEFAULT NULL,
  `poweroff_affect_priv_cons_num` double DEFAULT NULL,
  `src_tab` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `src_tab_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_tm` datetime DEFAULT NULL,
  `par_mon` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`dist_sta_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_egmt_mult_typ_power_off_on_day_freeze_dtl`
--

LOCK TABLES `dwd_cst_egmt_mult_typ_power_off_on_day_freeze_dtl` WRITE;
/*!40000 ALTER TABLE `dwd_cst_egmt_mult_typ_power_off_on_day_freeze_dtl` DISABLE KEYS */;
INSERT INTO `dwd_cst_egmt_mult_typ_power_off_on_day_freeze_dtl` VALUES ('DIS0001','DI-0001','配送站名称1','JUN0001','JU-0001','枢纽站名称1','PIP0001','PI-0001','管线名称1',9936.97,'CON0001','CO-0001','用户名称1','2024-09-02 13:00:00','2024-01-23 16:00:00','停复电标志代码_1','2024-10-04 00:00:00',3450.59,'停电类型代码_1','停电研判原因代码_1','复电研判原因代码_1','2024-07-26 20:00:00','2025-01-23 07:00:00','OR-0001','管理单位名称1','省份名称1','地市名称1','是否向上归集代码_1','是否向上归集描述_1','补全来源代码_1','补全来源描述_1','2024-03-01 09:00:00','CRO0001','ME-0001','2024-05-18 06:00:00','2024-02-13 11:00:00','SU-0001','重点用户类型代码_1','民生用户类型代码_1','是否保供用户（1_1','用电类别代码_1',1628.88,157.74,2846.53,2066.75,'来源表(个性化)_1','来源表名(个性化_1','2024-06-26 03:00:00','月分区(个性化)_1'),('DIS0002','DI-0002','配送站名称2','JUN0002','JU-0002','枢纽站名称2','PIP0002','PI-0002','管线名称2',3870.29,'CON0002','CO-0002','用户名称2','2024-11-26 12:00:00','2024-09-17 05:00:00','停复电标志代码_2','2024-08-03 12:00:00',5303.48,'停电类型代码_2','停电研判原因代码_2','复电研判原因代码_2','2024-05-04 19:00:00','2025-01-06 09:00:00','OR-0002','管理单位名称2','省份名称2','地市名称2','是否向上归集代码_2','是否向上归集描述_2','补全来源代码_2','补全来源描述_2','2024-11-22 03:00:00','CRO0002','ME-0002','2025-01-21 14:00:00','2025-01-23 12:00:00','SU-0002','重点用户类型代码_2','民生用户类型代码_2','是否保供用户（1_2','用电类别代码_2',5476.6,9156.84,3039.82,5161.45,'来源表(个性化)_2','来源表名(个性化_2','2024-12-19 11:00:00','月分区(个性化)_2'),('DIS0003','DI-0003','配送站名称3','JUN0003','JU-0003','枢纽站名称3','PIP0003','PI-0003','管线名称3',3638.51,'CON0003','CO-0003','用户名称3','2025-01-06 02:00:00','2024-07-14 00:00:00','停复电标志代码_3','2024-05-02 21:00:00',4849.1,'停电类型代码_3','停电研判原因代码_3','复电研判原因代码_3','2024-07-22 13:00:00','2024-07-02 21:00:00','OR-0003','管理单位名称3','省份名称3','地市名称3','是否向上归集代码_3','是否向上归集描述_3','补全来源代码_3','补全来源描述_3','2024-02-10 05:00:00','CRO0003','ME-0003','2024-06-01 21:00:00','2025-01-11 12:00:00','SU-0003','重点用户类型代码_3','民生用户类型代码_3','是否保供用户（1_3','用电类别代码_3',1082.27,5790.36,6641.94,9107.52,'来源表(个性化)_3','来源表名(个性化_3','2024-04-21 00:00:00','月分区(个性化)_3');
/*!40000 ALTER TABLE `dwd_cst_egmt_mult_typ_power_off_on_day_freeze_dtl` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_inv_mtd_rslt_mi`
--

DROP TABLE IF EXISTS `dwd_cst_inv_mtd_rslt_mi`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_inv_mtd_rslt_mi` (
  `inv_mtd_id` int NOT NULL,
  `prov_grid_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_batch_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_app_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp_ym` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_bus_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_bus_categ_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_type_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `orgn_inv_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_flag_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_flag_stat` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `setl_flag_stat_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_hndl_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_hndl_type_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `seller_taxpayer_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `seller_tin` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `seller_addr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `seller_tel` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `seller_open_bank` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `seller_open_bank_acct` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `buyer_taxpayer_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `buyer_tin` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `buyer_addr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `buyer_tel` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `buyer_open_bank` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `buyer_open_bank_acct` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_stf` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payee` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_stf` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `t_prc_tax_amt` double DEFAULT NULL,
  `tax_excl_t_amt` double DEFAULT NULL,
  `t_tax_amt` double DEFAULT NULL,
  `inv_stat` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_stat_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rela_inv_mtd_id` int DEFAULT NULL,
  `ddct_amt` double DEFAULT NULL,
  `tax_ind_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tax_ind_type_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `order_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_ym` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_chan_src` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_rslt_rec_id` int DEFAULT NULL,
  `inv_date` datetime DEFAULT NULL,
  `in_net_url_pdf` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `out_net_url_pdf` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_rslt_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_rslt_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `out_net_url_xml` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `out_net_url_ofd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `uds_res_id_pdf` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `uds_res_id_ofd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `uds_res_id_xml` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attach_id_pdf` int DEFAULT NULL,
  `attach_id_ofd` int DEFAULT NULL,
  `attach_id_xml` int DEFAULT NULL,
  `inv_channel` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `area` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv_desc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `write_time` datetime DEFAULT NULL,
  PRIMARY KEY (`inv_mtd_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_inv_mtd_rslt_mi`
--

LOCK TABLES `dwd_cst_inv_mtd_rslt_mi` WRITE;
/*!40000 ALTER TABLE `dwd_cst_inv_mtd_rslt_mi` DISABLE KEYS */;
INSERT INTO `dwd_cst_inv_mtd_rslt_mi` VALUES (34969,'PR-0003','IN-0003','IN-0003','39480.52','南方电网公司','发票业务类别描述测试数据3','国网电力公司','发票类型描述,发测试数据3','IN-0003','OR-0003','启用','结清标志描述,结测试数据3','异常','激活','南方电网公司','开票处理类型描述测试数据3','销售方纳税人名称,属3','销售方税号,属性_3','上海市浦东新区yy路2号','13891078288','销售方开户行及账号,3','SE-0003','购买方纳税人名称,属3','购买方税号,属性_3','深圳市南山区aa路4号','13834093599','购买方开户行及账号,3','62220054147240136','开票人,属性描述_3','收款人员,属性描_3','复核人,属性描述_3',9882.21,2789.95,6776.87,'正常','异常',28711,1063.16,'国家电投','税务行业类型描述测试数据3','OR-0003','2024-08-22 00:00:00','备注,属性描述：测试数据3','852',7038,'2024-08-11 00:00:00','杭州市西湖区bb路5号','广州市天河区zz路3号','IN-0003','开票结果描述测试数据3','广州市天河区zz路3号','上海市浦东新区yy路2号','PDF文件USD_3','OFD文件UDS_3','XML文件UDS_3',693184,461645,493322,'发票通道，用于记_3','MG-0003','管理单位名称,管理单3','所属区域,所属区_3','PR-0003','所属省公司名称,所属3','CI-0003','所属市公司名称,所属3','CO-0003','所属县公司名称,所属3','区域层级,属性描_3','区域层级描述,区测试数据3','2024-08-10 06:00:00'),(598488,'PR-0001','IN-0001','IN-0001','30476.78','国家电投','发票业务类别描述测试数据1','华能集团','发票类型描述,发测试数据1','IN-0001','OR-0001','注销','结清标志描述,结测试数据1','停用','正常','国网电力公司','开票处理类型描述测试数据1','销售方纳税人名称,属1','销售方税号,属性_1','北京市朝阳区xx路1号','13872223851','销售方开户行及账号,1','SE-0001','购买方纳税人名称,属1','购买方税号,属性_1','杭州市西湖区bb路5号','13896853490','购买方开户行及账号,1','62220060901921872','开票人,属性描述_1','收款人员,属性描_1','复核人,属性描述_1',1438.5,8998.34,9289.17,'注销','正常',877658,2774.67,'华能集团','税务行业类型描述测试数据1','OR-0001','2024-01-29 00:00:00','备注,属性描述：测试数据1','544',559876,'2024-04-28 18:00:00','北京市朝阳区xx路1号','杭州市西湖区bb路5号','IN-0001','开票结果描述测试数据1','杭州市西湖区bb路5号','广州市天河区zz路3号','PDF文件USD_1','OFD文件UDS_1','XML文件UDS_1',913482,715138,639991,'发票通道，用于记_1','MG-0001','管理单位名称,管理单1','所属区域,所属区_1','PR-0001','所属省公司名称,所属1','CI-0001','所属市公司名称,所属1','CO-0001','所属县公司名称,所属1','区域层级,属性描_1','区域层级描述,区测试数据1','2024-09-16 13:00:00'),(894176,'PR-0002','IN-0002','IN-0002','24599.94','国家电投','发票业务类别描述测试数据2','华能集团','发票类型描述,发测试数据2','IN-0002','OR-0002','停用','结清标志描述,结测试数据2','注销','异常','国家电投','开票处理类型描述测试数据2','销售方纳税人名称,属2','销售方税号,属性_2','深圳市南山区aa路4号','13898644021','销售方开户行及账号,2','SE-0002','购买方纳税人名称,属2','购买方税号,属性_2','深圳市南山区aa路4号','13840778571','购买方开户行及账号,2','62220082645387101','开票人,属性描述_2','收款人员,属性描_2','复核人,属性描述_2',9981.94,8846.52,7871.15,'异常','异常',493213,21.84,'国家电投','税务行业类型描述测试数据2','OR-0002','2024-08-20 00:00:00','备注,属性描述：测试数据2','496',742640,'2024-09-28 16:00:00','杭州市西湖区bb路5号','广州市天河区zz路3号','IN-0002','开票结果描述测试数据2','北京市朝阳区xx路1号','深圳市南山区aa路4号','PDF文件USD_2','OFD文件UDS_2','XML文件UDS_2',960754,918878,649347,'发票通道，用于记_2','MG-0002','管理单位名称,管理单2','所属区域,所属区_2','PR-0002','所属省公司名称,所属2','CI-0002','所属市公司名称,所属2','CO-0002','所属县公司名称,所属2','区域层级,属性描_2','区域层级描述,区测试数据2','2024-11-03 16:00:00');
/*!40000 ALTER TABLE `dwd_cst_inv_mtd_rslt_mi` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_inv_prt_rec_di`
--

DROP TABLE IF EXISTS `dwd_cst_inv_prt_rec_di`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_inv_prt_rec_di` (
  `inv_prt_rec_id` int NOT NULL,
  `inv_mtd_id` int DEFAULT NULL,
  `inv_bus_categ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_bus_categ_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prt_times` int DEFAULT NULL,
  `prt_stf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prt_time` datetime DEFAULT NULL,
  `inv_app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `exp_ym` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_hndl_type_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `seller_taxpayer_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `seller_tin` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `seller_addr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `seller_tel` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `seller_open_bank` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `seller_open_bank_acct` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `buyer_taxpayer_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `buyer_tin` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `buyer_addr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `buyer_tel` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `buyer_open_bank` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `buyer_open_bank_acct` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inv_stf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payee` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_stf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `t_prc_tax_amt` double DEFAULT NULL,
  `tax_excl_t_amt` double DEFAULT NULL,
  `t_tax_amt` double DEFAULT NULL,
  `inv_stat_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ddct_amt` double DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `area` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `province_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dist_lv_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `write_time` datetime DEFAULT NULL,
  PRIMARY KEY (`inv_prt_rec_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_inv_prt_rec_di`
--

LOCK TABLES `dwd_cst_inv_prt_rec_di` WRITE;
/*!40000 ALTER TABLE `dwd_cst_inv_prt_rec_di` DISABLE KEYS */;
INSERT INTO `dwd_cst_inv_prt_rec_di` VALUES (60522,755806,'华能集团','发票业务类别描述测试数据2',638767,'打印人:发票的打_2','2024-07-14 09:00:00','IN-0002','90513.48','IN-0002','开票处理类型描述测试数据2','销售方纳税人名称,属2','销售方税号,属性_2','上海市浦东新区yy路2号','13820500700','销售方开户行及账号,2','SE-0002','购买方纳税人名称,属2','购买方税号,属性_2','北京市朝阳区xx路1号','13860598419','购买方开户行及账号,2','62220094965338707','开票人,属性描述_2','收款人员,属性描_2','复核人,属性描述_2',78.98,3452.67,5804.75,'激活',3333.75,'MG-0002','管理单位名称,管理单2','所属区域,所属区_2','PR-0002','所属省公司名称,所属2','CI-0002','所属市公司名称,所属2','CO-0002','所属县公司名称,所属2','区域层级,属性描_2','区域层级描述,区测试数据2','2024-07-13 14:00:00'),(335706,178620,'大唐集团','发票业务类别描述测试数据1',513257,'打印人:发票的打_1','2025-03-13 23:00:00','IN-0001','54578.92','IN-0001','开票处理类型描述测试数据1','销售方纳税人名称,属1','销售方税号,属性_1','北京市朝阳区xx路1号','13862657555','销售方开户行及账号,1','SE-0001','购买方纳税人名称,属1','购买方税号,属性_1','杭州市西湖区bb路5号','13861247779','购买方开户行及账号,1','62220017159494041','开票人,属性描述_1','收款人员,属性描_1','复核人,属性描述_1',4148.1,1596.26,6658.86,'注销',7206.29,'MG-0001','管理单位名称,管理单1','所属区域,所属区_1','PR-0001','所属省公司名称,所属1','CI-0001','所属市公司名称,所属1','CO-0001','所属县公司名称,所属1','区域层级,属性描_1','区域层级描述,区测试数据1','2024-04-07 22:00:00'),(541938,894176,'国网电力公司','发票业务类别描述测试数据3',659164,'打印人:发票的打_3','2024-09-07 04:00:00','IN-0003','5672.37','IN-0003','开票处理类型描述测试数据3','销售方纳税人名称,属3','销售方税号,属性_3','杭州市西湖区bb路5号','13855206857','销售方开户行及账号,3','SE-0003','购买方纳税人名称,属3','购买方税号,属性_3','北京市朝阳区xx路1号','13887518303','购买方开户行及账号,3','62220078579424175','开票人,属性描述_3','收款人员,属性描_3','复核人,属性描述_3',5405.6,5223.34,4978.83,'注销',4393.89,'MG-0003','管理单位名称,管理单3','所属区域,所属区_3','PR-0003','所属省公司名称,所属3','CI-0003','所属市公司名称,所属3','CO-0003','所属县公司名称,所属3','区域层级,属性描_3','区域层级描述,区测试数据3','2025-05-02 12:00:00');
/*!40000 ALTER TABLE `dwd_cst_inv_prt_rec_di` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_chg_cons_cust_cur_min`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_chg_cons_cust_cur_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_chg_cons_cust_cur_min` (
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `occur_time` datetime DEFAULT NULL,
  `meter_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mfr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `i_0` double DEFAULT NULL,
  `i_a` double DEFAULT NULL,
  `i_b` double DEFAULT NULL,
  `i_c` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`cust_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_chg_cons_cust_cur_min`
--

LOCK TABLES `dwd_cst_mtcl_chg_cons_cust_cur_min` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_chg_cons_cust_cur_min` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_chg_cons_cust_cur_min` VALUES ('CUS0001','2024-03-29 00:00:00','MET0001','AS-0001','FT-0001','MF-0001','省份名称1','地市名称1','MG-0001','管理单位名称1','分区字段_1',7166.05,359.45,7689.03,4349.15,'2025-02-10 18:00:00'),('CUS0002','2024-07-28 06:00:00','MET0002','AS-0002','FT-0002','MF-0002','省份名称2','地市名称2','MG-0002','管理单位名称2','分区字段_2',7573.14,5047.6,306.77,2026.84,'2024-06-14 22:00:00'),('CUS0003','2025-01-25 00:00:00','MET0003','AS-0003','FT-0003','MF-0003','省份名称3','地市名称3','MG-0003','管理单位名称3','分区字段_3',7347.69,5838.16,6132.97,1195.71,'2024-01-11 07:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_chg_cons_cust_cur_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_chg_cons_cust_vol_min`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_chg_cons_cust_vol_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_chg_cons_cust_vol_min` (
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `occur_time` datetime DEFAULT NULL,
  `meter_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mfr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `u_a` double DEFAULT NULL,
  `u_b` double DEFAULT NULL,
  `u_c` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`cust_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_chg_cons_cust_vol_min`
--

LOCK TABLES `dwd_cst_mtcl_chg_cons_cust_vol_min` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_chg_cons_cust_vol_min` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_chg_cons_cust_vol_min` VALUES ('CUS0001','2024-11-04 10:00:00','MET0001','AS-0001','FT-0001','MF-0001','MG-0001','管理单位名称1','省份名称1','地市名称1','分区字段_1',4964.77,2663.88,7761.76,'2024-08-05 23:00:00'),('CUS0002','2024-06-15 01:00:00','MET0002','AS-0002','FT-0002','MF-0002','MG-0002','管理单位名称2','省份名称2','地市名称2','分区字段_2',5933.85,413.88,916.27,'2024-11-02 22:00:00'),('CUS0003','2024-02-11 11:00:00','MET0003','AS-0003','FT-0003','MF-0003','MG-0003','管理单位名称3','省份名称3','地市名称3','分区字段_3',5296.86,6179.07,6908.24,'2024-08-20 08:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_chg_cons_cust_vol_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_cons_cust_energy_day`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_cons_cust_energy_day`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_cons_cust_energy_day` (
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `data_date` datetime DEFAULT NULL,
  `data_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `calc_date` datetime DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cons_energy` double DEFAULT NULL,
  `cons_energy1` double DEFAULT NULL,
  `cons_energy2` double DEFAULT NULL,
  `cons_energy3` double DEFAULT NULL,
  `cons_energy4` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`cust_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_cons_cust_energy_day`
--

LOCK TABLES `dwd_cst_mtcl_cons_cust_energy_day` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_cons_cust_energy_day` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_cons_cust_energy_day` VALUES ('CUS0001','2025-01-03 06:00:00','数据类型（0：发_1','数据类型描述（0：发1','2024-09-04 15:00:00','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-06-30 00:00:00',6998.84,3942.23,6067.53,6499.07,8574.05,'2024-04-24 11:00:00'),('CUS0002','2024-10-26 05:00:00','数据类型（0：发_2','数据类型描述（0：发2','2024-02-06 02:00:00','省份名称2','地市名称2','MG-0002','管理单位名称2','2025-04-16 00:00:00',7434.88,5581.98,9276.4,4348.4,7654.74,'2024-07-28 22:00:00'),('CUS0003','2024-07-25 02:00:00','数据类型（0：发_3','数据类型描述（0：发3','2024-12-12 00:00:00','省份名称3','地市名称3','MG-0003','管理单位名称3','2024-01-24 00:00:00',2881.45,6790.6,1396.57,7161.31,6408.75,'2025-01-13 09:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_cons_cust_energy_day` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_cons_cust_energy_min`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_cons_cust_energy_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_cons_cust_energy_min` (
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `occur_time` datetime DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `energy` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`cust_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_cons_cust_energy_min`
--

LOCK TABLES `dwd_cst_mtcl_cons_cust_energy_min` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_cons_cust_energy_min` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_cons_cust_energy_min` VALUES ('CUS0001','2024-01-20 07:00:00','MG-0001','管理单位名称1','省份名称1','地市名称1','分区字段_1',7792.44,'2024-04-18 19:00:00'),('CUS0002','2024-06-25 18:00:00','MG-0002','管理单位名称2','省份名称2','地市名称2','分区字段_2',197.69,'2024-06-30 14:00:00'),('CUS0003','2024-08-06 21:00:00','MG-0003','管理单位名称3','省份名称3','地市名称3','分区字段_3',2965.63,'2024-08-18 19:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_cons_cust_energy_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_cons_cust_energy_mon`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_cons_cust_energy_mon`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_cons_cust_energy_mon` (
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `data_date` datetime DEFAULT NULL,
  `data_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_addr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `calc_date` datetime DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_cap` double DEFAULT NULL,
  `run_cap` double DEFAULT NULL,
  `cons_energy` double DEFAULT NULL,
  `cons_energy1` double DEFAULT NULL,
  `cons_energy2` double DEFAULT NULL,
  `cons_energy3` double DEFAULT NULL,
  `cons_energy4` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`cust_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_cons_cust_energy_mon`
--

LOCK TABLES `dwd_cst_mtcl_cons_cust_energy_mon` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_cons_cust_energy_mon` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_cons_cust_energy_mon` VALUES ('CUS0001','2025-01-21 15:00:00','数据类型（0：发_1','CU-0001','用电客户名称1','深圳市南山区aa路4号','异常','2024-07-17 04:00:00','MG-0001','管理单位名称1','省份名称1','地市名称1','2024-05-29 00:00:00',5882,1315.97,1530.94,2752.32,2483.77,6844.06,7592.97,'2024-07-11 01:00:00'),('CUS0002','2024-08-10 00:00:00','数据类型（0：发_2','CU-0002','用电客户名称2','北京市朝阳区xx路1号','激活','2025-01-05 16:00:00','MG-0002','管理单位名称2','省份名称2','地市名称2','2025-01-12 00:00:00',9044.33,7834.91,5279.02,4575.95,1794.56,3017.53,420.38,'2024-05-21 00:00:00'),('CUS0003','2024-12-12 06:00:00','数据类型（0：发_3','CU-0003','用电客户名称3','广州市天河区zz路3号','注销','2024-04-18 11:00:00','MG-0003','管理单位名称3','省份名称3','地市名称3','2024-12-14 00:00:00',7180.15,3332.37,8734.77,3782.68,5867.38,7264.82,5906.01,'2024-07-12 12:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_cons_cust_energy_mon` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_cust_cons_cur_min`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_cust_cons_cur_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_cust_cons_cur_min` (
  `cons_id` varchar(50) DEFAULT NULL COMMENT '用电客户ID',
  `meter_id` varchar(50) DEFAULT NULL COMMENT '电能表ID',
  `data_time` datetime DEFAULT NULL COMMENT '数据时间',
  `cur_phsa` decimal(10,2) DEFAULT NULL COMMENT 'A相电流',
  `cur_phsb` decimal(10,2) DEFAULT NULL COMMENT 'B相电流',
  `cur_phsc` decimal(10,2) DEFAULT NULL COMMENT 'C相电流',
  `data_date` date DEFAULT NULL COMMENT '数据日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='模拟数据表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_cust_cons_cur_min`
--

LOCK TABLES `dwd_cst_mtcl_cust_cons_cur_min` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_cust_cons_cur_min` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_cust_cons_cur_min` VALUES ('C100001','M000001','2024-01-02 01:01:00',27163.22,26995.25,29594.88,'2024-01-31'),('C100002','M000002','2024-01-03 02:02:00',12726.02,40981.07,28997.11,'2024-03-01'),('C100003','M000003','2024-01-04 03:03:00',34862.47,33875.44,29503.77,'2024-03-31'),('C100004','M000004','2024-01-05 04:04:00',25693.56,5653.74,1394.42,'2024-04-30'),('C100005','M000005','2024-01-06 05:05:00',2795.87,24698.73,42564.20,'2024-05-30'),('C100006','M000006','2024-01-07 06:06:00',26010.35,4768.22,21221.83,'2024-06-29'),('C100007','M000007','2024-01-08 07:07:00',49929.21,12610.67,36599.44,'2024-07-29'),('C100008','M000008','2024-01-09 08:08:00',48953.63,3546.08,48285.63,'2024-08-28'),('C100009','M000009','2024-01-10 09:09:00',7713.68,6735.25,39797.96,'2024-09-27'),('C1000010','M000010','2024-01-11 10:10:00',19396.49,40387.14,48006.55,'2024-10-27');
/*!40000 ALTER TABLE `dwd_cst_mtcl_cust_cons_cur_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_cust_cons_power_min`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_cust_cons_power_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_cust_cons_power_min` (
  `cons_id` varchar(50) DEFAULT NULL COMMENT '用电客户ID',
  `meter_id` varchar(50) DEFAULT NULL COMMENT '电能表ID',
  `data_time` datetime DEFAULT NULL COMMENT '数据时间',
  `tot_w` decimal(12,4) DEFAULT NULL COMMENT '有功功率',
  `tot_var` decimal(12,4) DEFAULT NULL COMMENT '无功功率',
  `data_date` date DEFAULT NULL COMMENT '数据日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='模拟数据表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_cust_cons_power_min`
--

LOCK TABLES `dwd_cst_mtcl_cust_cons_power_min` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_cust_cons_power_min` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_cust_cons_power_min` VALUES ('C100001','M000001','2024-01-02 01:01:00',28586.2100,28168.8400,'2024-01-31'),('C100002','M000002','2024-01-03 02:02:00',33837.6200,20189.3000,'2024-03-01'),('C100003','M000003','2024-01-04 03:03:00',32665.2400,19237.0100,'2024-03-31'),('C100004','M000004','2024-01-05 04:04:00',9003.9700,28811.9700,'2024-04-30'),('C100005','M000005','2024-01-06 05:05:00',16640.3600,20570.8200,'2024-05-30'),('C100006','M000006','2024-01-07 06:06:00',46805.8600,38529.2100,'2024-06-29'),('C100007','M000007','2024-01-08 07:07:00',31291.6000,38935.5600,'2024-07-29'),('C100008','M000008','2024-01-09 08:08:00',22986.9600,12287.7200,'2024-08-28'),('C100009','M000009','2024-01-10 09:09:00',24966.8300,6362.1600,'2024-09-27'),('C1000010','M000010','2024-01-11 10:10:00',1504.8100,23258.1300,'2024-10-27');
/*!40000 ALTER TABLE `dwd_cst_mtcl_cust_cons_power_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_cust_cons_vol_min`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_cust_cons_vol_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_cust_cons_vol_min` (
  `cons_id` varchar(50) DEFAULT NULL COMMENT '用电客户ID',
  `meter_id` varchar(50) DEFAULT NULL COMMENT '电能表ID',
  `data_time` datetime DEFAULT NULL COMMENT '数据时间',
  `phv_phsa` decimal(10,2) DEFAULT NULL COMMENT 'A相电压',
  `phv_phsb` decimal(10,2) DEFAULT NULL COMMENT 'B相电压',
  `phv_phsc` decimal(10,2) DEFAULT NULL COMMENT 'C相电压',
  `data_date` date DEFAULT NULL COMMENT '数据日期'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='模拟数据表';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_cust_cons_vol_min`
--

LOCK TABLES `dwd_cst_mtcl_cust_cons_vol_min` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_cust_cons_vol_min` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_cust_cons_vol_min` VALUES ('C100001','M000001','2024-01-02 01:01:00',13923.02,42076.10,34410.02,'2024-01-31'),('C100002','M000002','2024-01-03 02:02:00',27750.29,18245.18,27787.47,'2024-03-01'),('C100003','M000003','2024-01-04 03:03:00',36720.69,5712.66,25334.74,'2024-03-31'),('C100004','M000004','2024-01-05 04:04:00',22044.44,3843.07,34261.91,'2024-04-30'),('C100005','M000005','2024-01-06 05:05:00',9190.24,46749.38,46799.05,'2024-05-30'),('C100006','M000006','2024-01-07 06:06:00',38851.46,27812.69,46024.95,'2024-06-29'),('C100007','M000007','2024-01-08 07:07:00',8211.10,44918.07,49271.87,'2024-07-29'),('C100008','M000008','2024-01-09 08:08:00',18873.47,1556.66,31932.33,'2024-08-28'),('C100009','M000009','2024-01-10 09:09:00',26969.90,39102.35,39738.93,'2024-09-27'),('C1000010','M000010','2024-01-11 10:10:00',18493.79,36633.11,21632.60,'2024-10-27');
/*!40000 ALTER TABLE `dwd_cst_mtcl_cust_cons_vol_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_dist_sta_line_loss_day`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_dist_sta_line_loss_day`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_dist_sta_line_loss_day` (
  `dist_sta_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `stat_date` datetime DEFAULT NULL,
  `rec_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `resrc_supl_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `resrc_supl_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_manager_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_ll_manager_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `det_addr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cons_cnt` int DEFAULT NULL,
  `dist_satcap` double DEFAULT NULL,
  `ppq` double DEFAULT NULL,
  `upq` double DEFAULT NULL,
  `loss_pq` double DEFAULT NULL,
  `ll_rate` double DEFAULT NULL,
  `meter_cnt` int DEFAULT NULL,
  `meter_cover_cnt` int DEFAULT NULL,
  `cover_rate` double DEFAULT NULL,
  `is_cover` double DEFAULT NULL,
  `is_cover_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_succ_cnt` double DEFAULT NULL,
  `succ_rate` double DEFAULT NULL,
  `is_monitor` double DEFAULT NULL,
  `is_monitor_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `coll_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `coll_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_calc` double DEFAULT NULL,
  `is_calc_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pubt_pq_p` double DEFAULT NULL,
  `pubt_pq_r` double DEFAULT NULL,
  `dg_gcpq` double DEFAULT NULL,
  `lv_upq` double DEFAULT NULL,
  `lv_pq_r` double DEFAULT NULL,
  `dg_cons_cnt` int DEFAULT NULL,
  `dg_met_cnt` int DEFAULT NULL,
  `pubt_inst_cnt` int DEFAULT NULL,
  `rat` double DEFAULT NULL,
  `llr` double DEFAULT NULL,
  `rate_scope` double DEFAULT NULL,
  `rate_scope_up` double DEFAULT NULL,
  `rate_scope_low` double DEFAULT NULL,
  `is_new_tg_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_new_tg_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `white_list_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `white_list_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_small_energy` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_small_energy_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hplc_tg_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hplc_tg_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mp_cnt` int DEFAULT NULL,
  `succ_mp_cnt` int DEFAULT NULL,
  `energy_whole_rate` double DEFAULT NULL,
  `total_cons_cnt` int DEFAULT NULL,
  `low_vol_num` int DEFAULT NULL,
  `no_resident_cnt` int DEFAULT NULL,
  `lift_cons_cnt` int DEFAULT NULL,
  `ration_cnt` int DEFAULT NULL,
  `inst_cnt` int DEFAULT NULL,
  `ds_meter_cnt` int DEFAULT NULL,
  `sp_meter_cnt` int DEFAULT NULL,
  `tp_meter_cnt` int DEFAULT NULL,
  `hplc_meter_cnt` int DEFAULT NULL,
  `ll_limit_flag` double DEFAULT NULL,
  `ll_limit_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inf_small_energy_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inf_small_energy_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rat_unreason_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rat_unreason_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `model_rat_stat` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `model_rat_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ration_pq` double DEFAULT NULL,
  `normal_days` double DEFAULT NULL,
  `mon_unnor_days` double DEFAULT NULL,
  `lv_nre_rap_r` double DEFAULT NULL,
  `ll_volatility` double DEFAULT NULL,
  `is_normal` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_normal_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`dist_sta_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_dist_sta_line_loss_day`
--

LOCK TABLES `dwd_cst_mtcl_dist_sta_line_loss_day` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_dist_sta_line_loss_day` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_dist_sta_line_loss_day` VALUES ('DIS0001','2024-10-03 04:00:00','REC0001','RE-0001','配送站名称1','CU-0001','CU-0001','上海市浦东新区yy路2号','分区_1','MG-0001','管理单位名称1','省份名称1','地市名称1',679981,5813.49,2994.66,2467.43,9555.42,4925.08,249776,174296,5424.76,6025.92,'采集覆盖率是否大于等1',1528.31,2614.79,6333.01,'采集覆盖率和成功率是1','01：自动；02_1','采集类型名称1',3516.61,'是否系统计算1',5771.43,8484.9,2833.87,1641.57,3284.87,150292,614263,306601,2965.82,1118.12,7439.76,588.63,505.89,'新上台区标记 0_1','新上台区标记名称1','白名单标记 0：_1','白名单标记 名称1','小电量标记 0:_1','小电量标记名称1','HPLC台区标记_1','HPLC台区标记名称1',414419,37158,7102.78,637704,620241,948868,587257,545995,869273,812468,528267,19424,980371,477.2,'线损越限标记名称1','是否拐点小电量 _1','是否拐点小电量名称1','赋值异常台区 1_1','赋值异常台区名称1','激活','参数赋值状态名称1',1128.02,6741.85,2046.45,2517.88,3324.3,'IS-0001','线损是否合格名称1','2024-12-21 16:00:00'),('DIS0002','2024-12-29 03:00:00','REC0002','RE-0002','配送站名称2','CU-0002','CU-0002','杭州市西湖区bb路5号','分区_2','MG-0002','管理单位名称2','省份名称2','地市名称2',834767,4374.64,7262.09,3183.32,6553.04,8301.81,542199,934897,6662.8,1057.38,'采集覆盖率是否大于等2',7948.32,9296.35,4345.77,'采集覆盖率和成功率是2','01：自动；02_2','采集类型名称2',9397.64,'是否系统计算2',6628.22,322.89,2473.45,190.56,5890.28,924689,985807,578998,3872.02,2763.81,723.59,1152.11,6108.39,'新上台区标记 0_2','新上台区标记名称2','白名单标记 0：_2','白名单标记 名称2','小电量标记 0:_2','小电量标记名称2','HPLC台区标记_2','HPLC台区标记名称2',582236,297946,4163.06,913328,979156,399723,853768,330196,825527,604545,694860,846039,297492,4525.82,'线损越限标记名称2','是否拐点小电量 _2','是否拐点小电量名称2','赋值异常台区 1_2','赋值异常台区名称2','注销','参数赋值状态名称2',2350.43,7109.53,5570.39,7133.25,3479.22,'IS-0002','线损是否合格名称2','2025-05-07 21:00:00'),('DIS0003','2024-12-30 20:00:00','REC0003','RE-0003','配送站名称3','CU-0003','CU-0003','深圳市南山区aa路4号','分区_3','MG-0003','管理单位名称3','省份名称3','地市名称3',148682,1918.03,892.03,2230.81,6191.84,9312.85,461662,297870,9251.45,1041.86,'采集覆盖率是否大于等3',6570.65,9042.67,261.02,'采集覆盖率和成功率是3','01：自动；02_3','采集类型名称3',8075.89,'是否系统计算3',4336.52,732.12,980.17,7241.79,2879.73,226661,312795,141918,7071.14,9527.47,3057.11,7132.33,2947.26,'新上台区标记 0_3','新上台区标记名称3','白名单标记 0：_3','白名单标记 名称3','小电量标记 0:_3','小电量标记名称3','HPLC台区标记_3','HPLC台区标记名称3',282205,8574,6198.1,323565,517827,617789,59634,371487,737243,945732,871101,764008,988389,2572.98,'线损越限标记名称3','是否拐点小电量 _3','是否拐点小电量名称3','赋值异常台区 1_3','赋值异常台区名称3','正常','参数赋值状态名称3',8799.85,8293.51,9320.61,540.97,1483.15,'IS-0003','线损是否合格名称3','2025-01-13 00:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_dist_sta_line_loss_day` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_gen_cust_energy_day`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_gen_cust_energy_day`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_gen_cust_energy_day` (
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `energy_date` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gc_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pur_pq` double DEFAULT NULL,
  `gra_pq` double DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`cust_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_gen_cust_energy_day`
--

LOCK TABLES `dwd_cst_mtcl_gen_cust_energy_day` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_gen_cust_energy_day` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_gen_cust_energy_day` VALUES ('CUS0001','2024-11-26 00:00:00','GC-0001','MG-0001','管理单位名称1','省份名称1','地市名称1',6467.89,731.04,'2025-02-14 00:00:00','2024-12-21 09:00:00'),('CUS0002','2025-03-15 00:00:00','GC-0002','MG-0002','管理单位名称2','省份名称2','地市名称2',2501.24,7648.22,'2024-11-24 00:00:00','2025-04-08 06:00:00'),('CUS0003','2025-02-08 00:00:00','GC-0003','MG-0003','管理单位名称3','省份名称3','地市名称3',3489.52,3361.43,'2024-04-21 00:00:00','2024-12-19 00:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_gen_cust_energy_day` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_inst_energy_day`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_inst_energy_day`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_inst_energy_day` (
  `inst_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `data_date` datetime DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pap_e` double DEFAULT NULL,
  `pap_e1` double DEFAULT NULL,
  `pap_e2` double DEFAULT NULL,
  `pap_e3` double DEFAULT NULL,
  `pap_e4` double DEFAULT NULL,
  `prp_e` double DEFAULT NULL,
  `prp_e1` double DEFAULT NULL,
  `prp_e2` double DEFAULT NULL,
  `prp_e3` double DEFAULT NULL,
  `prp_e4` double DEFAULT NULL,
  `rap_e` double DEFAULT NULL,
  `rap_e1` double DEFAULT NULL,
  `rap_e2` double DEFAULT NULL,
  `rap_e3` double DEFAULT NULL,
  `rap_e4` double DEFAULT NULL,
  `rp1_e` double DEFAULT NULL,
  `rp1_e1` double DEFAULT NULL,
  `rp1_e2` double DEFAULT NULL,
  `rp1_e3` double DEFAULT NULL,
  `rp1_e4` double DEFAULT NULL,
  `rp2_e` double DEFAULT NULL,
  `rp2_e1` double DEFAULT NULL,
  `rp2_e2` double DEFAULT NULL,
  `rp2_e3` double DEFAULT NULL,
  `rp2_e4` double DEFAULT NULL,
  `rp3_e` double DEFAULT NULL,
  `rp3_e1` double DEFAULT NULL,
  `rp3_e2` double DEFAULT NULL,
  `rp3_e3` double DEFAULT NULL,
  `rp3_e4` double DEFAULT NULL,
  `rp4_e` double DEFAULT NULL,
  `rp4_e1` double DEFAULT NULL,
  `rp4_e2` double DEFAULT NULL,
  `rp4_e3` double DEFAULT NULL,
  `rp4_e4` double DEFAULT NULL,
  `rrp_e` double DEFAULT NULL,
  `rrp_e1` double DEFAULT NULL,
  `rrp_e2` double DEFAULT NULL,
  `rrp_e3` double DEFAULT NULL,
  `rrp_e4` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`inst_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_inst_energy_day`
--

LOCK TABLES `dwd_cst_mtcl_inst_energy_day` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_inst_energy_day` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_inst_energy_day` VALUES ('INS0001','2024-09-15 13:00:00','省份名称1','地市名称1','MG-0001','管理单位名称1','2025-03-24 00:00:00',4753.94,9403.21,3725.56,5800.77,2160.57,6217.26,3930.86,5804.03,6982.05,5168.49,9154.61,2723.69,9826.81,5686.81,2181.57,1203.54,4200.44,5519.23,3796.43,8802.57,3371.12,7226.38,2469.68,9196.1,9215.84,20.82,4152.15,1841.23,2002.94,8232.51,8759.4,8379.33,3923.11,2910.39,3229.71,5180.75,2047.94,973.53,7308.2,2410.44,'2024-02-26 10:00:00'),('INS0002','2024-05-21 00:00:00','省份名称2','地市名称2','MG-0002','管理单位名称2','2024-11-12 00:00:00',4239.59,7565.33,2204.75,9659.61,2881.59,5871.45,6852.2,6977.28,707.65,586.73,5577.92,2395.65,633.18,7341.34,3184.04,2188.18,2270.86,4606.22,4608.71,3572.39,7680.49,6271.94,2726.03,955.51,6942.28,2893.82,6835.22,1843.4,9191.63,4974.53,5233.39,8925.3,834.33,8302.12,2601.59,5499.25,2119.9,6764.58,4729.27,4638.14,'2024-07-28 14:00:00'),('INS0003','2024-06-21 00:00:00','省份名称3','地市名称3','MG-0003','管理单位名称3','2024-09-19 00:00:00',1347.03,9873.77,87.78,9400.84,5281.05,828.25,7954.72,8579.27,5668.26,9623.71,1226.07,5800.17,3023.07,2184.94,2819.21,4505.99,9543.19,3100.17,6517.25,1449.11,9852.06,2266.24,9784.27,9572.24,5613.97,879.75,1960.42,9918.2,9006.03,2200.72,2978.73,308.13,1636.21,1410.47,6794.06,5650.64,2655.34,2781.02,1225.04,7215.86,'2024-08-18 12:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_inst_energy_day` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_inst_energy_min`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_inst_energy_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_inst_energy_min` (
  `inst_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `occur_time` datetime DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pap` double DEFAULT NULL,
  `prp` double DEFAULT NULL,
  `rap` double DEFAULT NULL,
  `rrp` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`inst_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_inst_energy_min`
--

LOCK TABLES `dwd_cst_mtcl_inst_energy_min` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_inst_energy_min` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_inst_energy_min` VALUES ('INS0001','2024-01-18 17:00:00','MG-0001','管理单位名称1','省份名称1','地市名称1','分区字段_1',875.19,5644.15,9223.19,279.31,'2024-04-06 00:00:00'),('INS0002','2024-11-28 12:00:00','MG-0002','管理单位名称2','省份名称2','地市名称2','分区字段_2',9067.37,8504.75,4692.43,7312.29,'2025-05-10 11:00:00'),('INS0003','2025-02-03 01:00:00','MG-0003','管理单位名称3','省份名称3','地市名称3','分区字段_3',3352.65,2134.28,486.45,8669.14,'2024-08-15 15:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_inst_energy_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_inst_load_min`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_inst_load_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_inst_load_min` (
  `inst_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `occur_time` datetime DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`inst_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_inst_load_min`
--

LOCK TABLES `dwd_cst_mtcl_inst_load_min` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_inst_load_min` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_inst_load_min` VALUES ('INS0001','2025-01-08 05:00:00','省份名称1','地市名称1','MG-0001','管理单位名称1','分区字段_1',6336.35,'2024-02-21 05:00:00'),('INS0002','2025-03-31 01:00:00','省份名称2','地市名称2','MG-0002','管理单位名称2','分区字段_2',120.23,'2025-03-05 07:00:00'),('INS0003','2025-02-19 14:00:00','省份名称3','地市名称3','MG-0003','管理单位名称3','分区字段_3',610.88,'2025-04-27 16:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_inst_load_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_meter_clock`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_meter_clock`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_meter_clock` (
  `asset_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `auto_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `checking_plan_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_app_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chk_cyc` double DEFAULT NULL,
  `chk_plan_dtl_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_site` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_cls_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dev_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `dtl_stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dtl_stat_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_cls_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_date` datetime DEFAULT NULL,
  `inst_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inst_site` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_chk_date` datetime DEFAULT NULL,
  `latitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `longitude` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `md_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `md_cls_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `meter_logic_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `old_dtl_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `op_date` datetime DEFAULT NULL,
  `opr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_acmp_date` datetime DEFAULT NULL,
  `site_chk_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `site_chk_flag_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `task_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `task_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `term_date` datetime DEFAULT NULL,
  `term_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `term_stf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `upd_date_reas` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `veri_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wire_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wire_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`dev_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_meter_clock`
--

LOCK TABLES `dwd_cst_mtcl_meter_clock` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_clock` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_meter_clock` VALUES ('AS-0001','自动生成标志_1','CHE0001','CH-0001',9229.82,'CHK0001','用电户/发电户/关口1','CU-0001','北京市朝阳区xx路1号','设备分类_1','设备分类描述1','DEV0001','停用','明细状态描述1','安装点分类_1','安装点分类描述1','2025-02-15 17:00:00','INS0001','IN-0001','安装位置_1','2025-01-18 15:00:00','现场检验纬度_1','现场检验经度_1','计量装置分类_1','计量装置分类描述1','MET0001','OLD0001','2024-10-31 05:00:00','操作人员_1','2025-02-11 21:00:00','现场检验标志_1','现场检验标志描述1','任务类型_1','任务类型描述1','2024-03-11 17:00:00','终止原因_1','终止人员_1','2024-03-21 00:00:00','检定类型_1','检定类型描述1','接线方式_1','接线方式描述1','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-04-18 23:00:00'),('AS-0002','自动生成标志_2','CHE0002','CH-0002',4898.49,'CHK0002','用电户/发电户/关口2','CU-0002','北京市朝阳区xx路1号','设备分类_2','设备分类描述2','DEV0002','启用','明细状态描述2','安装点分类_2','安装点分类描述2','2025-02-11 22:00:00','INS0002','IN-0002','安装位置_2','2025-03-23 19:00:00','现场检验纬度_2','现场检验经度_2','计量装置分类_2','计量装置分类描述2','MET0002','OLD0002','2024-01-01 13:00:00','操作人员_2','2024-01-31 09:00:00','现场检验标志_2','现场检验标志描述2','任务类型_2','任务类型描述2','2025-03-03 08:00:00','终止原因_2','终止人员_2','2024-08-15 00:00:00','检定类型_2','检定类型描述2','接线方式_2','接线方式描述2','省份名称2','地市名称2','MG-0002','管理单位名称2','2024-02-29 01:00:00'),('AS-0003','自动生成标志_3','CHE0003','CH-0003',706.81,'CHK0003','用电户/发电户/关口3','CU-0003','深圳市南山区aa路4号','设备分类_3','设备分类描述3','DEV0003','注销','明细状态描述3','安装点分类_3','安装点分类描述3','2025-05-02 04:00:00','INS0003','IN-0003','安装位置_3','2024-04-09 09:00:00','现场检验纬度_3','现场检验经度_3','计量装置分类_3','计量装置分类描述3','MET0003','OLD0003','2024-05-10 21:00:00','操作人员_3','2024-10-17 08:00:00','现场检验标志_3','现场检验标志描述3','任务类型_3','任务类型描述3','2025-02-19 20:00:00','终止原因_3','终止人员_3','2024-09-29 00:00:00','检定类型_3','检定类型描述3','接线方式_3','接线方式描述3','省份名称3','地市名称3','MG-0003','管理单位名称3','2024-02-29 15:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_clock` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_meter_coll_fail_day`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_meter_coll_fail_day`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_meter_coll_fail_day` (
  `meter_id` double NOT NULL,
  `data_date` datetime DEFAULT NULL,
  `terminal_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asset_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mfr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `write_time` datetime DEFAULT NULL,
  `org_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnty_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnty_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `branch_off_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `branch_off_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pow_sup_sta_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pow_sup_sta_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pap_r` double DEFAULT NULL,
  `prp_r` double DEFAULT NULL,
  `rap_r` double DEFAULT NULL,
  `rrp_r` double DEFAULT NULL,
  `rp1_r` double DEFAULT NULL,
  `rp2_r` double DEFAULT NULL,
  `rp3_r` double DEFAULT NULL,
  `rp4_r` double DEFAULT NULL,
  `pap_demand` double DEFAULT NULL,
  `prp_demand` double DEFAULT NULL,
  `rap_demand` double DEFAULT NULL,
  `rrp_demand` double DEFAULT NULL,
  `pa_power5` double DEFAULT NULL,
  `ra_power5` double DEFAULT NULL,
  `a_power5a` double DEFAULT NULL,
  `a_power5b` double DEFAULT NULL,
  `a_power5c` double DEFAULT NULL,
  `r_power5a` double DEFAULT NULL,
  `r_power5b` double DEFAULT NULL,
  `r_power5c` double DEFAULT NULL,
  `pa_power15` double DEFAULT NULL,
  `ra_power15` double DEFAULT NULL,
  `a_power15a` double DEFAULT NULL,
  `a_power15b` double DEFAULT NULL,
  `a_power15c` double DEFAULT NULL,
  `r_power15a` double DEFAULT NULL,
  `r_power15b` double DEFAULT NULL,
  `r_power15c` double DEFAULT NULL,
  `pa_power30` double DEFAULT NULL,
  `ra_power30` double DEFAULT NULL,
  `a_power30a` double DEFAULT NULL,
  `a_power30b` double DEFAULT NULL,
  `a_power30c` double DEFAULT NULL,
  `r_power30a` double DEFAULT NULL,
  `r_power30b` double DEFAULT NULL,
  `r_power30c` double DEFAULT NULL,
  `pa_power60` double DEFAULT NULL,
  `ra_power60` double DEFAULT NULL,
  `a_power60a` double DEFAULT NULL,
  `a_power60b` double DEFAULT NULL,
  `a_power60c` double DEFAULT NULL,
  `r_power60a` double DEFAULT NULL,
  `r_power60b` double DEFAULT NULL,
  `r_power60c` double DEFAULT NULL,
  `pa_r5` double DEFAULT NULL,
  `pr_r5` double DEFAULT NULL,
  `ra_r5` double DEFAULT NULL,
  `rr_r5` double DEFAULT NULL,
  `pa_r15` double DEFAULT NULL,
  `pr_r15` double DEFAULT NULL,
  `ra_r15` double DEFAULT NULL,
  `rr_r15` double DEFAULT NULL,
  `pa_r30` double DEFAULT NULL,
  `pr_r30` double DEFAULT NULL,
  `ra_r30` double DEFAULT NULL,
  `rr_r30` double DEFAULT NULL,
  `pa_r60` double DEFAULT NULL,
  `pr_r60` double DEFAULT NULL,
  `ra_r60` double DEFAULT NULL,
  `rr_r60` double DEFAULT NULL,
  `a_volt5` double DEFAULT NULL,
  `b_volt5` double DEFAULT NULL,
  `c_volt5` double DEFAULT NULL,
  `a_volt15` double DEFAULT NULL,
  `b_volt15` double DEFAULT NULL,
  `c_volt15` double DEFAULT NULL,
  `a_volt30` double DEFAULT NULL,
  `b_volt30` double DEFAULT NULL,
  `c_volt30` double DEFAULT NULL,
  `c_volt60` double DEFAULT NULL,
  `b_volt60` double DEFAULT NULL,
  `a_volt60` double DEFAULT NULL,
  `z_cur5` double DEFAULT NULL,
  `a_cur5` double DEFAULT NULL,
  `b_cur5` double DEFAULT NULL,
  `c_cur5` double DEFAULT NULL,
  `z_cur15` double DEFAULT NULL,
  `a_cur15` double DEFAULT NULL,
  `b_cur15` double DEFAULT NULL,
  `c_cur15` double DEFAULT NULL,
  `z_cur30` double DEFAULT NULL,
  `a_cur30` double DEFAULT NULL,
  `b_cur30` double DEFAULT NULL,
  `c_cur30` double DEFAULT NULL,
  `z_cur60` double DEFAULT NULL,
  `a_cur60` double DEFAULT NULL,
  `b_cur60` double DEFAULT NULL,
  `c_cur60` double DEFAULT NULL,
  `facotr5` double DEFAULT NULL,
  `a_facotr5` double DEFAULT NULL,
  `b_facotr5` double DEFAULT NULL,
  `c_facotr5` double DEFAULT NULL,
  `facotr15` double DEFAULT NULL,
  `a_facotr15` double DEFAULT NULL,
  `b_facotr15` double DEFAULT NULL,
  `c_facotr15` double DEFAULT NULL,
  `facotr30` double DEFAULT NULL,
  `a_facotr30` double DEFAULT NULL,
  `b_facotr30` double DEFAULT NULL,
  `c_facotr30` double DEFAULT NULL,
  `facotr60` double DEFAULT NULL,
  `a_facotr60` double DEFAULT NULL,
  `b_facotr60` double DEFAULT NULL,
  `c_facotr60` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`meter_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_meter_coll_fail_day`
--

LOCK TABLES `dwd_cst_mtcl_meter_coll_fail_day` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_coll_fail_day` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_meter_coll_fail_day` VALUES (790.52,'2025-03-22 20:00:00','TER0002','AS-0002','MF-0002','FT-0002','2024-03-14 10:00:00','OR-0002','分区_2','PR-0002','省公司名称2','CI-0002','地市公司名称2','CN-0002','区县公司名称2','BR-0002','分公司名称2','PO-0002','供电所名称2','MG-0002','管理单位名称2',6577.22,6988.19,7261.11,2490.97,7121.54,1862.25,9877.62,6321.9,5497.76,5048.73,6695.26,3752.94,1767.29,6177.76,3411.63,7181.17,2068.63,6651.21,4595.15,5098.51,8202.79,1360.41,707.37,7112.4,7358.2,4803.74,1991.62,6104.75,625.79,7646.12,8861.19,8700.64,3579.22,8751.1,3222.1,8240.76,3193.34,6418.64,9332.77,3566.8,8864.4,7437.87,1977.28,3024.34,6977.94,6575.7,2336.75,4507.66,945.64,5810.83,4278.33,385.09,7569.77,7701.7,4646.93,2017.13,4988.97,1259.28,3311.24,5399.69,3960.34,7095.85,8102.05,8173.6,3952.44,6149.52,5960.32,7187.97,9099.54,5454.25,5654.19,2012.32,7824.87,5725.99,1099.61,7835.45,2916.93,2051.71,790.04,7891.83,4373.35,4500.64,470.62,7128.85,165.96,1931.4,9795.99,736.56,1115.19,8015.41,5812.77,2584.21,6494.61,2539.12,597.49,2382.58,613.83,2402.89,3414.2,597.14,2129.38,2677.64,7976.71,2963.57,'2024-04-23 06:00:00'),(945.06,'2024-08-09 09:00:00','TER0003','AS-0003','MF-0003','FT-0003','2024-06-21 12:00:00','OR-0003','分区_3','PR-0003','省公司名称3','CI-0003','地市公司名称3','CN-0003','区县公司名称3','BR-0003','分公司名称3','PO-0003','供电所名称3','MG-0003','管理单位名称3',8411.07,3996.38,4067.6,721.08,3616.48,4088.37,5898.65,7412.42,7709.78,3607.53,1122.81,9797.55,6924.94,6695.77,7510.62,5025.07,3630.44,5675.1,4652.97,9186.33,1805.55,3985.17,8381.07,4063.92,2725.85,9424.94,9205.79,8571.01,9685.31,2613.5,2687.15,8647.67,2986.04,9335.15,4051.2,2192.98,3447.81,5390.9,3627.33,4159.78,8600.56,908.4,6539.1,669.19,8584.73,6509.6,943.07,8751.49,6564.5,3381.98,5844.65,13.82,7202.13,6862.05,5682.95,7537.44,7436.33,3482.27,7080.69,724.67,4938.17,8676.81,3522.21,9784.87,1388.79,4769.22,7561.69,4326.88,1205.54,2762,5481.09,9701.99,9014.91,2126.05,185.01,6997.73,6065.28,1163.54,2378.19,4893.06,9994.6,9792.56,5306.86,8396.11,3360.42,2766.12,6083.64,4372.45,6581.9,3151.92,2456.88,5356.28,6634.2,4297.45,4352.72,4259.47,1707.9,9201.15,6877.06,7675.88,9413.49,7553.57,2941.88,6527.91,'2024-09-10 00:00:00'),(1523.48,'2024-03-04 09:00:00','TER0001','AS-0001','MF-0001','FT-0001','2025-01-31 12:00:00','OR-0001','分区_1','PR-0001','省公司名称1','CI-0001','地市公司名称1','CN-0001','区县公司名称1','BR-0001','分公司名称1','PO-0001','供电所名称1','MG-0001','管理单位名称1',3082.7,7096.83,3871.13,9163.25,3541.77,5833.99,3710.27,221.38,5451.78,2908.42,4617.43,8153.11,8936.14,2668.78,3810.86,9551.21,9315.87,4902.96,5693.02,3621.82,832.46,8839.66,7139.01,7625.49,1438.84,9819.17,5113.79,178.3,5793.46,6852.85,420.58,3237.24,3886.85,5316.21,5526.01,2437.27,9689.48,2569.33,9321.78,9095.07,6547.82,8684.3,2761.87,535.43,5534.47,6565.25,4589.84,9165.59,4977.05,859.96,6259.44,1806.91,7033.45,4071.12,5622.22,4880.07,7445,2770,9736.39,536.43,5890.56,2491.67,9672,6873.23,9899.34,8192.83,9033.98,5651.22,1205.59,5476.43,5683.11,9759.61,1889.86,2804.23,1518.87,7981.28,269.41,1097.48,9091.63,1575.95,9031.31,1044.46,801.7,9731.01,8381.25,8495.33,9814.99,3799.83,3843.85,6932.25,3833.47,6665.44,1853.78,9405.17,7599.66,4841.22,7570.36,6443.58,3328.68,7188.77,7408.57,6069.28,8153.02,8697.8,'2025-03-31 05:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_coll_fail_day` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_meter_cur_min`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_meter_cur_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_meter_cur_min` (
  `meter_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `occur_time` datetime DEFAULT NULL,
  `asset_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mfr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `i_0` double DEFAULT NULL,
  `i_a` double DEFAULT NULL,
  `i_b` double DEFAULT NULL,
  `i_c` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`meter_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_meter_cur_min`
--

LOCK TABLES `dwd_cst_mtcl_meter_cur_min` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_cur_min` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_meter_cur_min` VALUES ('MET0001','CUS0001','2025-05-07 14:00:00','AS-0001','FT-0001','MF-0001','MG-0001','管理单位名称1','省份名称1','地市名称1','分区字段_1',1285.62,2854.2,6361.77,1503.53,'2024-03-21 08:00:00'),('MET0002','CUS0002','2024-07-21 15:00:00','AS-0002','FT-0002','MF-0002','MG-0002','管理单位名称2','省份名称2','地市名称2','分区字段_2',8217.71,9248.48,1934.25,1856.67,'2024-04-12 00:00:00'),('MET0003','CUS0003','2024-02-18 05:00:00','AS-0003','FT-0003','MF-0003','MG-0003','管理单位名称3','省份名称3','地市名称3','分区字段_3',1736.45,4453.98,9920.12,66.21,'2024-06-21 00:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_cur_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_meter_demand_day`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_meter_demand_day`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_meter_demand_day` (
  `meter_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_date` datetime DEFAULT NULL,
  `asset_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mfr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `col_time` datetime DEFAULT NULL,
  `pap_acq_time` datetime DEFAULT NULL,
  `prp_acq_time` datetime DEFAULT NULL,
  `rap_acq_time` datetime DEFAULT NULL,
  `rrp_acq_time` datetime DEFAULT NULL,
  `pap_demand1_time` datetime DEFAULT NULL,
  `pap_demand2_time` datetime DEFAULT NULL,
  `pap_demand3_time` datetime DEFAULT NULL,
  `pap_demand4_time` datetime DEFAULT NULL,
  `pap_demand_quality` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pap_demand_time` datetime DEFAULT NULL,
  `prp_demand1_time` datetime DEFAULT NULL,
  `prp_demand2_time` datetime DEFAULT NULL,
  `prp_demand3_time` datetime DEFAULT NULL,
  `prp_demand4_time` datetime DEFAULT NULL,
  `prp_demand_time` datetime DEFAULT NULL,
  `rap_demand1_time` datetime DEFAULT NULL,
  `rap_demand2_time` datetime DEFAULT NULL,
  `rap_demand3_time` datetime DEFAULT NULL,
  `rap_demand4_time` datetime DEFAULT NULL,
  `rap_demand_quality` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rap_demand_time` datetime DEFAULT NULL,
  `rrp_demand_time` datetime DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pap_demand` double DEFAULT NULL,
  `pap_demand1` double DEFAULT NULL,
  `pap_demand2` double DEFAULT NULL,
  `pap_demand3` double DEFAULT NULL,
  `pap_demand4` double DEFAULT NULL,
  `prp_demand` double DEFAULT NULL,
  `prp_demand1` double DEFAULT NULL,
  `prp_demand2` double DEFAULT NULL,
  `prp_demand3` double DEFAULT NULL,
  `prp_demand4` double DEFAULT NULL,
  `rap_demand` double DEFAULT NULL,
  `rap_demand1` double DEFAULT NULL,
  `rap_demand2` double DEFAULT NULL,
  `rap_demand3` double DEFAULT NULL,
  `rap_demand4` double DEFAULT NULL,
  `rrp_demand` double DEFAULT NULL,
  `rrp_demand1` double DEFAULT NULL,
  `rrp_demand2` double DEFAULT NULL,
  `rrp_demand3` double DEFAULT NULL,
  `rrp_demand4` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`meter_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_meter_demand_day`
--

LOCK TABLES `dwd_cst_mtcl_meter_demand_day` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_demand_day` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_meter_demand_day` VALUES ('MET0001','CUS0001','2025-01-29 15:00:00','AS-0001','FT-0001','MF-0001','2024-12-04 02:00:00','2024-08-20 14:00:00','2024-02-27 13:00:00','2024-11-22 20:00:00','2024-08-31 17:00:00','2024-09-03 17:00:00','2024-11-22 04:00:00','2024-05-26 22:00:00','2024-03-23 15:00:00','异常','2025-02-01 17:00:00','2024-08-20 21:00:00','2024-10-18 19:00:00','2024-05-14 12:00:00','2025-02-01 05:00:00','2024-06-20 02:00:00','2025-03-10 03:00:00','2024-05-26 17:00:00','2025-02-22 11:00:00','2024-08-19 13:00:00','停用','2024-01-17 03:00:00','2024-11-12 09:00:00','省份名称1','地市名称1','MG-0001','管理单位名称1','分区字段_1',7390.55,8894.58,2077.18,6981.8,2374.13,6899.06,7995.46,8754.97,1473.97,5404.1,8672.68,8088.53,5564.5,1296.46,9532.2,3438.66,2907.11,491.05,5773.38,4191.06,'2024-09-19 10:00:00'),('MET0002','CUS0002','2025-04-17 23:00:00','AS-0002','FT-0002','MF-0002','2024-08-09 04:00:00','2024-02-04 18:00:00','2024-11-20 11:00:00','2024-08-03 00:00:00','2024-12-28 17:00:00','2025-04-29 18:00:00','2024-05-12 21:00:00','2025-04-20 23:00:00','2024-07-16 00:00:00','激活','2024-05-24 17:00:00','2025-02-26 08:00:00','2024-02-07 05:00:00','2024-02-11 23:00:00','2024-12-19 14:00:00','2024-01-19 04:00:00','2024-05-03 06:00:00','2025-04-17 09:00:00','2025-01-02 09:00:00','2025-02-11 04:00:00','注销','2024-09-07 19:00:00','2024-01-15 03:00:00','省份名称2','地市名称2','MG-0002','管理单位名称2','分区字段_2',2725.06,8797.01,4634.43,1188.8,2357.16,6796.09,2042.15,5287.86,5604.52,3446.15,7030.6,3243.8,8103.17,6478.92,4493.09,1834.36,7666.57,8501.16,4378.68,4999.38,'2024-07-24 13:00:00'),('MET0003','CUS0003','2024-10-29 09:00:00','AS-0003','FT-0003','MF-0003','2024-12-19 14:00:00','2024-09-05 00:00:00','2024-12-13 22:00:00','2024-12-20 22:00:00','2024-11-23 23:00:00','2024-02-01 01:00:00','2025-02-19 10:00:00','2025-01-25 01:00:00','2024-04-14 11:00:00','启用','2025-03-14 06:00:00','2024-07-31 00:00:00','2024-07-11 15:00:00','2024-09-06 14:00:00','2024-12-12 22:00:00','2025-03-01 02:00:00','2024-07-10 00:00:00','2024-02-13 10:00:00','2025-03-19 02:00:00','2025-03-23 13:00:00','注销','2024-11-30 12:00:00','2025-03-20 16:00:00','省份名称3','地市名称3','MG-0003','管理单位名称3','分区字段_3',1571.99,8869.03,8303.49,1938.74,9730.73,6704.2,9909.15,75.4,6117.67,3535.48,6617.34,5501.74,4236.32,1603.94,3315.52,2155.06,8077.09,792.71,2527.84,7034.81,'2024-03-22 01:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_demand_day` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_meter_energy_day`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_meter_energy_day`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_meter_energy_day` (
  `meter_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `data_date` datetime DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pap_e` double DEFAULT NULL,
  `pap_e1` double DEFAULT NULL,
  `pap_e2` double DEFAULT NULL,
  `pap_e3` double DEFAULT NULL,
  `pap_e4` double DEFAULT NULL,
  `prp_e` double DEFAULT NULL,
  `prp_e1` double DEFAULT NULL,
  `prp_e2` double DEFAULT NULL,
  `prp_e3` double DEFAULT NULL,
  `prp_e4` double DEFAULT NULL,
  `rap_e` double DEFAULT NULL,
  `rap_e1` double DEFAULT NULL,
  `rap_e2` double DEFAULT NULL,
  `rap_e3` double DEFAULT NULL,
  `rap_e4` double DEFAULT NULL,
  `rp1_e` double DEFAULT NULL,
  `rp1_e1` double DEFAULT NULL,
  `rp1_e2` double DEFAULT NULL,
  `rp1_e3` double DEFAULT NULL,
  `rp1_e4` double DEFAULT NULL,
  `rp2_e` double DEFAULT NULL,
  `rp2_e1` double DEFAULT NULL,
  `rp2_e2` double DEFAULT NULL,
  `rp2_e3` double DEFAULT NULL,
  `rp2_e4` double DEFAULT NULL,
  `rp3_e` double DEFAULT NULL,
  `rp3_e1` double DEFAULT NULL,
  `rp3_e2` double DEFAULT NULL,
  `rp3_e3` double DEFAULT NULL,
  `rp3_e4` double DEFAULT NULL,
  `rp4_e` double DEFAULT NULL,
  `rp4_e1` double DEFAULT NULL,
  `rp4_e2` double DEFAULT NULL,
  `rp4_e3` double DEFAULT NULL,
  `rp4_e4` double DEFAULT NULL,
  `rrp_e` double DEFAULT NULL,
  `rrp_e1` double DEFAULT NULL,
  `rrp_e2` double DEFAULT NULL,
  `rrp_e3` double DEFAULT NULL,
  `rrp_e4` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`meter_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_meter_energy_day`
--

LOCK TABLES `dwd_cst_mtcl_meter_energy_day` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_energy_day` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_meter_energy_day` VALUES ('MET0001','2024-01-24 08:00:00','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-07-05 00:00:00',9821.54,9372.95,4362.99,451.63,340.64,7712.39,8689.66,2965.07,3157.6,8592.57,8005.27,8330.85,9231.27,6947.46,8888.39,1779.76,31.18,3784.95,2448.19,9288.89,6802.84,9199.16,1524.7,2878.81,2937.48,4123.69,7141.63,4788.85,9374.58,9559.38,7819.59,7814.28,6432.89,8246.16,7450.13,8264.58,4319.8,8598.47,7692.82,1196.2,'2024-06-22 21:00:00'),('MET0002','2024-12-29 22:00:00','省份名称2','地市名称2','MG-0002','管理单位名称2','2024-02-24 00:00:00',2982.88,9456.89,3091.85,5207.54,3694.79,981.6,3062.98,2939.21,7917.5,7167.45,4501.62,9861.73,2874.35,1120.62,371.73,4595.27,4802.61,928.66,6739.99,1404.06,6111.69,387.71,688.91,7315.4,3317.06,6571.53,7017.25,3423.68,766.06,1355.35,4310.24,6263.76,4790.36,4675.68,6076.81,8588.47,8769.94,5928.49,9752.09,8654.58,'2025-01-17 03:00:00'),('MET0003','2024-06-29 09:00:00','省份名称3','地市名称3','MG-0003','管理单位名称3','2024-08-21 00:00:00',1805.19,7372.19,7898.7,1420.95,9689.86,8950.04,2448.15,1917.18,9765.28,8867.07,2407.7,6612,2970.78,159.76,8425.5,8224.34,2057,9322.94,6179.9,6253.58,754.98,5713.77,6472.91,5784.45,2511.77,775.43,1945.81,2929.84,1336.7,5400.17,1177.86,606.18,5274.15,5173.25,9025.54,1281.17,3497.45,7363.02,5733.7,4790.77,'2025-01-09 12:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_energy_day` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_meter_energy_min`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_meter_energy_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_meter_energy_min` (
  `meter_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `occur_time` datetime DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pap` double DEFAULT NULL,
  `prp` double DEFAULT NULL,
  `rap` double DEFAULT NULL,
  `rrp` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`meter_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_meter_energy_min`
--

LOCK TABLES `dwd_cst_mtcl_meter_energy_min` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_energy_min` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_meter_energy_min` VALUES ('MET0001','2025-03-03 21:00:00','MG-0001','管理单位名称1','省份名称1','地市名称1','分区字段_1',5944.61,8336.15,8979.11,7401.49,'2024-07-05 17:00:00'),('MET0002','2024-11-10 04:00:00','MG-0002','管理单位名称2','省份名称2','地市名称2','分区字段_2',4911.85,8060.77,6131.24,7409.44,'2024-06-29 18:00:00'),('MET0003','2024-09-05 08:00:00','MG-0003','管理单位名称3','省份名称3','地市名称3','分区字段_3',8872.21,6823.23,6092.91,2274.21,'2024-11-04 20:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_energy_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_meter_factor_min`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_meter_factor_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_meter_factor_min` (
  `meter_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `occur_time` datetime DEFAULT NULL,
  `asset_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mfr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `c` double DEFAULT NULL,
  `c_a` double DEFAULT NULL,
  `c_b` double DEFAULT NULL,
  `c_c` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`meter_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_meter_factor_min`
--

LOCK TABLES `dwd_cst_mtcl_meter_factor_min` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_factor_min` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_meter_factor_min` VALUES ('MET0001','CUS0001','2024-08-18 09:00:00','AS-0001','MF-0001','FT-0001','MG-0001','管理单位名称1','省份名称1','地市名称1','分区字段_1',4839.22,9947.54,7270.53,598.74,'2024-07-01 17:00:00'),('MET0002','CUS0002','2025-02-03 07:00:00','AS-0002','MF-0002','FT-0002','MG-0002','管理单位名称2','省份名称2','地市名称2','分区字段_2',5992.56,415.37,9832.27,9085.63,'2025-04-13 19:00:00'),('MET0003','CUS0003','2024-12-31 10:00:00','AS-0003','MF-0003','FT-0003','MG-0003','管理单位名称3','省份名称3','地市名称3','分区字段_3',87.89,8245.97,9362.91,1701.43,'2024-12-31 16:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_factor_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_meter_no_power`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_meter_no_power`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_meter_no_power` (
  `meter_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `input_time` datetime DEFAULT NULL,
  `asset_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mfr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `event_st` datetime DEFAULT NULL,
  `event_et` datetime DEFAULT NULL,
  `event_type_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `event_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `duration` int DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`ds`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_meter_no_power`
--

LOCK TABLES `dwd_cst_mtcl_meter_no_power` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_no_power` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_meter_no_power` VALUES ('MET0001','2024-08-27 01:00:00','AS-0001','FT-0001','MF-0001','2024-11-24 04:00:00','2025-02-11 18:00:00','EV-0001','事件类型名称1','省份名称1','地市名称1','MG-0001','管理单位名称1','DS0001',106940,'2024-06-20 06:00:00'),('MET0002','2024-04-28 04:00:00','AS-0002','FT-0002','MF-0002','2024-11-16 06:00:00','2024-07-04 17:00:00','EV-0002','事件类型名称2','省份名称2','地市名称2','MG-0002','管理单位名称2','DS0002',525976,'2024-05-06 07:00:00'),('MET0003','2025-02-17 13:00:00','AS-0003','FT-0003','MF-0003','2024-08-19 18:00:00','2024-12-25 10:00:00','EV-0003','事件类型名称3','省份名称3','地市名称3','MG-0003','管理单位名称3','DS0003',475632,'2024-01-04 11:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_no_power` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-04 12:13:50
-- MySQL dump 10.13  Distrib 8.0.39, for Linux (x86_64)
--
-- Host: localhost    Database: tupu
-- ------------------------------------------------------
-- Server version	8.0.39

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `dwd_cst_mtcl_meter_power_min`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_meter_power_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_meter_power_min` (
  `meter_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `occur_time` datetime DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `p` double DEFAULT NULL,
  `p_a` double DEFAULT NULL,
  `p_b` double DEFAULT NULL,
  `p_c` double DEFAULT NULL,
  `q` double DEFAULT NULL,
  `q_a` double DEFAULT NULL,
  `q_b` double DEFAULT NULL,
  `q_c` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`meter_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_meter_power_min`
--

LOCK TABLES `dwd_cst_mtcl_meter_power_min` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_power_min` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_meter_power_min` VALUES ('MET0001','2024-09-21 07:00:00','省份名称1','地市名称1','MG-0001','管理单位名称1','分区字段_1',114.95,1386.11,8796.99,4378.86,704.49,7750.41,9757,7603.45,'2025-01-15 16:00:00'),('MET0002','2025-05-15 05:00:00','省份名称2','地市名称2','MG-0002','管理单位名称2','分区字段_2',7011.61,972.5,3336.74,3985.71,5984.67,7773.38,5344.43,9371.52,'2024-08-05 04:00:00'),('MET0003','2024-02-12 06:00:00','省份名称3','地市名称3','MG-0003','管理单位名称3','分区字段_3',6520.43,6886.37,4915.79,4166.92,5847.6,6543.93,9685,4830.58,'2025-04-07 14:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_power_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_meter_read_day`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_meter_read_day`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_meter_read_day` (
  `meter_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `data_date` datetime DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pap_r` double DEFAULT NULL,
  `pap_r1` double DEFAULT NULL,
  `pap_r2` double DEFAULT NULL,
  `pap_r3` double DEFAULT NULL,
  `pap_r4` double DEFAULT NULL,
  `prp_r` double DEFAULT NULL,
  `prp_r1` double DEFAULT NULL,
  `prp_r2` double DEFAULT NULL,
  `prp_r3` double DEFAULT NULL,
  `prp_r4` double DEFAULT NULL,
  `rap_r` double DEFAULT NULL,
  `rap_r1` double DEFAULT NULL,
  `rap_r2` double DEFAULT NULL,
  `rap_r3` double DEFAULT NULL,
  `rap_r4` double DEFAULT NULL,
  `rp1_r` double DEFAULT NULL,
  `rp1_r1` double DEFAULT NULL,
  `rp1_r2` double DEFAULT NULL,
  `rp1_r3` double DEFAULT NULL,
  `rp1_r4` double DEFAULT NULL,
  `rp2_r` double DEFAULT NULL,
  `rp2_r1` double DEFAULT NULL,
  `rp2_r2` double DEFAULT NULL,
  `rp2_r3` double DEFAULT NULL,
  `rp2_r4` double DEFAULT NULL,
  `rp3_r` double DEFAULT NULL,
  `rp3_r1` double DEFAULT NULL,
  `rp3_r2` double DEFAULT NULL,
  `rp3_r3` double DEFAULT NULL,
  `rp3_r4` double DEFAULT NULL,
  `rp4_r` double DEFAULT NULL,
  `rp4_r1` double DEFAULT NULL,
  `rp4_r2` double DEFAULT NULL,
  `rp4_r3` double DEFAULT NULL,
  `rp4_r4` double DEFAULT NULL,
  `rrp_r` double DEFAULT NULL,
  `rrp_r1` double DEFAULT NULL,
  `rrp_r2` double DEFAULT NULL,
  `rrp_r3` double DEFAULT NULL,
  `rrp_r4` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`meter_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_meter_read_day`
--

LOCK TABLES `dwd_cst_mtcl_meter_read_day` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_read_day` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_meter_read_day` VALUES ('MET0001','2024-01-04 19:00:00','省份名称1','地市名称1','MG-0001','管理单位名称1','2024-05-21 00:00:00',1177.62,1323.78,47.06,8835.08,3038.3,4511.49,6876.21,9921.32,9011.63,3634.04,496.64,925.83,7769.85,1495.6,845.42,3679.77,5433.4,2384.65,5721.81,3492.69,2069.77,8136.94,1741.73,1891.17,2037.22,8844.23,915.92,9362.56,308.24,1299.02,7623.12,4983.53,496.48,663.04,9772.91,102.4,3119.94,5352.87,4445.79,8609.48,'2024-04-17 11:00:00'),('MET0002','2025-02-11 02:00:00','省份名称2','地市名称2','MG-0002','管理单位名称2','2024-09-14 00:00:00',8394.3,1644.7,3886.03,8139.28,9115.93,2494.38,170.78,9513.29,5820.24,8211.99,9294.04,1215.08,4535.46,44.61,4123.75,7050.51,3434.18,8851.55,7328.87,1264.12,4846.54,9066.77,4627.49,4987.62,1315.98,1346.37,9029.81,3293.06,6558.85,2785.1,521.44,1340.61,9407.66,2004.37,2530.83,1762.94,6028.38,8081.46,7541.63,328.38,'2024-01-07 06:00:00'),('MET0003','2025-04-20 05:00:00','省份名称3','地市名称3','MG-0003','管理单位名称3','2025-04-30 00:00:00',8354.79,3991.04,6144.17,7672.15,548.25,5508.59,9320.1,1397.6,5598.59,2821.45,5357.14,4858.98,8251.78,2982.88,2380.65,1233.28,7903.42,3413.87,8228.3,8744.03,6112.68,8127.26,8213.63,883.03,4928.78,1389.91,3392.84,5119.06,3142.63,9998.55,1557.23,1098.6,7396.82,8083.35,1083.47,9318.3,475.14,3801.7,2760.44,7125.88,'2024-06-25 06:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_read_day` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_meter_read_min`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_meter_read_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_meter_read_min` (
  `meter_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `occur_time` datetime DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pap` double DEFAULT NULL,
  `prp` double DEFAULT NULL,
  `rap` double DEFAULT NULL,
  `rrp` double DEFAULT NULL,
  `rp1_r` double DEFAULT NULL,
  `rp2_r` double DEFAULT NULL,
  `rp3_r` double DEFAULT NULL,
  `rp4_r` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`meter_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_meter_read_min`
--

LOCK TABLES `dwd_cst_mtcl_meter_read_min` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_read_min` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_meter_read_min` VALUES ('MET0001','2024-04-24 10:00:00','MG-0001','管理单位名称1','省份名称1','地市名称1','分区字段_1',8852.9,4934.13,6692.29,1682.33,2913.76,6975.97,5509.52,9478.19,'2024-06-06 09:00:00'),('MET0002','2024-12-18 03:00:00','MG-0002','管理单位名称2','省份名称2','地市名称2','分区字段_2',8294.05,4435.57,4547.51,8981.19,8573.73,4206.56,9053.21,4973.64,'2024-01-01 19:00:00'),('MET0003','2025-04-11 05:00:00','MG-0003','管理单位名称3','省份名称3','地市名称3','分区字段_3',538.63,3249.54,9152,4549.91,1005.89,1888.92,4538.34,6400.28,'2025-03-01 10:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_read_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_meter_vol_min`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_meter_vol_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_meter_vol_min` (
  `meter_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `cust_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `occur_time` datetime DEFAULT NULL,
  `asset_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mfr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `u_a` double DEFAULT NULL,
  `u_b` double DEFAULT NULL,
  `u_c` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  PRIMARY KEY (`meter_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_meter_vol_min`
--

LOCK TABLES `dwd_cst_mtcl_meter_vol_min` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_vol_min` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_meter_vol_min` VALUES ('MET0001','CUS0001','2024-08-21 05:00:00','AS-0001','FT-0001','MF-0001','省份名称1','地市名称1','MG-0001','管理单位名称1','分区字段_1',4582.41,9188.04,2494.16,'2024-03-23 07:00:00'),('MET0002','CUS0002','2024-07-03 14:00:00','AS-0002','FT-0002','MF-0002','省份名称2','地市名称2','MG-0002','管理单位名称2','分区字段_2',4698.74,5377.43,240.69,'2024-04-16 08:00:00'),('MET0003','CUS0003','2024-10-22 06:00:00','AS-0003','FT-0003','MF-0003','省份名称3','地市名称3','MG-0003','管理单位名称3','分区字段_3',753.2,8711.66,1527.46,'2024-06-14 13:00:00');
/*!40000 ALTER TABLE `dwd_cst_mtcl_meter_vol_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_mtcl_trml_no_power`
--

DROP TABLE IF EXISTS `dwd_cst_mtcl_trml_no_power`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_mtcl_trml_no_power` (
  `tmnl_id` double DEFAULT NULL,
  `input_time` datetime DEFAULT NULL,
  `asset_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fty_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mfr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `event_st` datetime DEFAULT NULL,
  `event_et` datetime DEFAULT NULL,
  `event_type_code` int DEFAULT NULL,
  `event_type_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `event_valid_flg_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `event_valid_flg_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `duration` int DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`ds`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_mtcl_trml_no_power`
--

LOCK TABLES `dwd_cst_mtcl_trml_no_power` WRITE;
/*!40000 ALTER TABLE `dwd_cst_mtcl_trml_no_power` DISABLE KEYS */;
INSERT INTO `dwd_cst_mtcl_trml_no_power` VALUES (7243.59,'2024-11-18 13:00:00','AS-0001','FT-0001','MF-0001','2024-04-10 01:00:00','2025-02-04 01:00:00',819591,'事件类型名称1','EV-0001','事件有效性标志名称1','省份名称1','地市名称1','MG-0001','管理单位名称1',756153,'2024-03-31 22:00:00','DS0001'),(8970.04,'2024-02-06 14:00:00','AS-0002','FT-0002','MF-0002','2024-01-04 07:00:00','2024-10-11 02:00:00',741061,'事件类型名称2','EV-0002','事件有效性标志名称2','省份名称2','地市名称2','MG-0002','管理单位名称2',769936,'2024-10-07 22:00:00','DS0002'),(9736.52,'2024-10-15 03:00:00','AS-0003','FT-0003','MF-0003','2025-04-15 09:00:00','2024-10-27 18:00:00',391505,'事件类型名称3','EV-0003','事件有效性标志名称3','省份名称3','地市名称3','MG-0003','管理单位名称3',525697,'2025-04-02 02:00:00','DS0003');
/*!40000 ALTER TABLE `dwd_cst_mtcl_trml_no_power` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_salm_ctrt_fulfl_wk_order`
--

DROP TABLE IF EXISTS `dwd_cst_salm_ctrt_fulfl_wk_order`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_salm_ctrt_fulfl_wk_order` (
  `ctrt_fulfl_order_id` int NOT NULL,
  `cust_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `informant_tel` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `informant_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rpt_info` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_fulfl_order_src` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_fulfl_order_src_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_fulfl_order_stat` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_fulfl_order_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `applnt` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `applicant_tel` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `breach_ctrt_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `breach_ctrt_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `breach_ctrt_cont` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `breach_ctrt_actn` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `breach_ctrt_actn_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `breach_ctrt_flag` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `breach_ctrt_flag_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srvy_person` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_voltage_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_voltage_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_fulfl_order_attach_id` int DEFAULT NULL,
  `gen_cons_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `gen_cons_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srvy_time` datetime DEFAULT NULL,
  `rpt_date` datetime DEFAULT NULL,
  `rpt_time` datetime DEFAULT NULL,
  `addr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `arch_time` datetime DEFAULT NULL,
  `ctrt_prfs` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_prfs_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ctrt_handle_rec_id` int DEFAULT NULL,
  `breach_ctrt_handle_opinion` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `handle_info_stat` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `handle_info_stat_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `handler` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `opr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `as_e_exp` double DEFAULT NULL,
  `as_e_qty` double DEFAULT NULL,
  `breach_ctrt_exp` double DEFAULT NULL,
  `hndl_time` datetime DEFAULT NULL,
  `cnfm_time` datetime DEFAULT NULL,
  `sue_reg_breach_ctrt_e_exp` double DEFAULT NULL,
  `clse_case_breach_ctrt_e_exp` double DEFAULT NULL,
  `as_ecc` double DEFAULT NULL,
  `prtp_tiered_qty` double DEFAULT NULL,
  `as_ecc_coef` double DEFAULT NULL,
  `cust_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_cls_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_categ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_categ_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ec_addr` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_type` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_type_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnty_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnty_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pow_sup_sta_code` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pow_sup_sta_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  `ds` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`ctrt_fulfl_order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_salm_ctrt_fulfl_wk_order`
--

LOCK TABLES `dwd_cst_salm_ctrt_fulfl_wk_order` WRITE;
/*!40000 ALTER TABLE `dwd_cst_salm_ctrt_fulfl_wk_order` DISABLE KEYS */;
INSERT INTO `dwd_cst_salm_ctrt_fulfl_wk_order` VALUES (258738,'CU-0003','CT-0003','13868284933','举报人姓名3','举报信息_3','履约工单来源_3','履约工单来源名称3','注销','履约工单状态名称3','申请人_3','13830063758','AP-0003','违约类型_3','违约类型名称3','违约内容_3','违约行为_3','违约行为名称3','有无违约_3','有无违约名称3','调查人_3','备注测试数据3','ST-0003','电压等级名称3',101030,'发用电户类型_3','发用电户类型名称3','2024-10-10 03:00:00','2024-07-24 21:00:00','2024-01-15 01:00:00','广州市天河区zz路3号','2024-10-30 22:00:00','合同专业_3','合同专业名称3',748043,'违约处理意见_3','正常','处理信息状态名称3','处理人_3','操作人_3',2076.06,6717.13,9282.13,'2024-01-17 05:00:00','2024-06-24 04:00:00',5085.06,4535.96,8874.93,3843.68,7583.07,'客户名称3','客户分类_3','客户分类名称3','用电类别_3','用电类别名称3','杭州市西湖区bb路5号','电源类型_3','电源类型名称3','MG-0003','管理单位名称3','PR-0003','省公司名称3','CI-0003','地市公司名称3','CN-0003','区县公司名称3','PO-0003','供电所名称3','2024-12-23 16:00:00','分区_3'),(441760,'CU-0002','CT-0002','13860156886','举报人姓名2','举报信息_2','履约工单来源_2','履约工单来源名称2','停用','履约工单状态名称2','申请人_2','13840296083','AP-0002','违约类型_2','违约类型名称2','违约内容_2','违约行为_2','违约行为名称2','有无违约_2','有无违约名称2','调查人_2','备注测试数据2','ST-0002','电压等级名称2',131239,'发用电户类型_2','发用电户类型名称2','2024-06-15 05:00:00','2025-03-12 22:00:00','2025-04-21 06:00:00','北京市朝阳区xx路1号','2024-09-29 12:00:00','合同专业_2','合同专业名称2',425681,'违约处理意见_2','正常','处理信息状态名称2','处理人_2','操作人_2',7349.03,7342.41,9824.97,'2024-09-02 04:00:00','2024-08-16 04:00:00',6875.63,4114.27,9600.13,9421.71,3354.19,'客户名称2','客户分类_2','客户分类名称2','用电类别_2','用电类别名称2','杭州市西湖区bb路5号','电源类型_2','电源类型名称2','MG-0002','管理单位名称2','PR-0002','省公司名称2','CI-0002','地市公司名称2','CN-0002','区县公司名称2','PO-0002','供电所名称2','2024-02-10 13:00:00','分区_2'),(972629,'CU-0001','CT-0001','13813989332','举报人姓名1','举报信息_1','履约工单来源_1','履约工单来源名称1','启用','履约工单状态名称1','申请人_1','13834895539','AP-0001','违约类型_1','违约类型名称1','违约内容_1','违约行为_1','违约行为名称1','有无违约_1','有无违约名称1','调查人_1','备注测试数据1','ST-0001','电压等级名称1',605149,'发用电户类型_1','发用电户类型名称1','2024-05-12 07:00:00','2025-03-12 01:00:00','2024-01-04 06:00:00','上海市浦东新区yy路2号','2024-09-19 10:00:00','合同专业_1','合同专业名称1',786337,'违约处理意见_1','注销','处理信息状态名称1','处理人_1','操作人_1',2155.24,4273.54,5104.12,'2025-02-13 14:00:00','2025-05-02 03:00:00',7484.72,9899.43,376.73,873.73,5075.33,'客户名称1','客户分类_1','客户分类名称1','用电类别_1','用电类别名称1','北京市朝阳区xx路1号','电源类型_1','电源类型名称1','MG-0001','管理单位名称1','PR-0001','省公司名称1','CI-0001','地市公司名称1','CN-0001','区县公司名称1','PO-0001','供电所名称1','2024-07-09 02:00:00','分区_1');
/*!40000 ALTER TABLE `dwd_cst_salm_ctrt_fulfl_wk_order` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_srv_cs_revst_wk_order`
--

DROP TABLE IF EXISTS `dwd_cst_srv_cs_revst_wk_order`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_srv_cs_revst_wk_order` (
  `cs_revst_wk_order_id` int NOT NULL,
  `revst_wk_order_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_tel` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `revst_cont` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hndl_acmp_time` datetime DEFAULT NULL,
  `hndl_stsf` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hndl_stsf_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `revst_stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `revst_stat_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `revst_mode` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `revst_mode_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnty_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cnty_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pow_sup_sta_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pow_sup_sta_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`cs_revst_wk_order_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_srv_cs_revst_wk_order`
--

LOCK TABLES `dwd_cst_srv_cs_revst_wk_order` WRITE;
/*!40000 ALTER TABLE `dwd_cst_srv_cs_revst_wk_order` DISABLE KEYS */;
INSERT INTO `dwd_cst_srv_cs_revst_wk_order` VALUES (293293,'RE-0002','13887976013','回访内容_2','2024-10-03 20:00:00','处理满意度_2','处理满意度名称2','激活','回访状态名称2','回访方式_2','回访方式名称2','MG-0002','管理单位名称2','PR-0002','省公司名称2','CI-0002','地市公司名称2','CN-0002','区县公司名称2','PO-0002','供电所名称2','2025-03-28 07:00:00','分区字段_2'),(332091,'RE-0003','13864679258','回访内容_3','2024-11-17 16:00:00','处理满意度_3','处理满意度名称3','停用','回访状态名称3','回访方式_3','回访方式名称3','MG-0003','管理单位名称3','PR-0003','省公司名称3','CI-0003','地市公司名称3','CN-0003','区县公司名称3','PO-0003','供电所名称3','2025-04-21 13:00:00','分区字段_3'),(976662,'RE-0001','13851824183','回访内容_1','2024-11-01 10:00:00','处理满意度_1','处理满意度名称1','激活','回访状态名称1','回访方式_1','回访方式名称1','MG-0001','管理单位名称1','PR-0001','省公司名称1','CI-0001','地市公司名称1','CN-0001','区县公司名称1','PO-0001','供电所名称1','2024-08-27 02:00:00','分区字段_1');
/*!40000 ALTER TABLE `dwd_cst_srv_cs_revst_wk_order` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_srv_cs_wk_order_hndl`
--

DROP TABLE IF EXISTS `dwd_cst_srv_cs_wk_order_hndl`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_srv_cs_wk_order_hndl` (
  `cs_wk_order_hndl_id` int NOT NULL,
  `cs_wk_order_id` int DEFAULT NULL,
  `app_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hndl_org_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hndl_org_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `handler` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `order_rcv_dept` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `order_rcv_stf` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `send_dept` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `resp_org` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `resp_dept` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hndl_time` datetime DEFAULT NULL,
  `hndl_situ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tak_opn` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_opn` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hndl_opn` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hndl_rslt` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `true_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `true_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `wk_order_arr_time` datetime DEFAULT NULL,
  `order_rcv_time` datetime DEFAULT NULL,
  `resp_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `resp_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `send_time` datetime DEFAULT NULL,
  `bus_hndl_sub_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cs_resp_prfs` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_cplt_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_cplt_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cmp_instc_id` int DEFAULT NULL,
  `cmp_instc_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `step_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_cmp_instc_id` int DEFAULT NULL,
  `last_cmp_instc_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `over_time` datetime DEFAULT NULL,
  `back_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `back_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `aprv_rslt` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `aprv_rslt_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `aprv_opinion` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `disqual_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `disqual_type_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hndl_stat` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `hndl_stat_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asgn_org` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `affil_county_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `unable_appeal_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `unable_appeal_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `book_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `book_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `order_hndl_book_time` datetime DEFAULT NULL,
  `book_reason` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_rural_pwr_grid_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_rural_pwr_grid_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bus_type_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attach_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `affil_county` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_bus_sub_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cs_wk_order_srv_anal_id` int DEFAULT NULL,
  `srv_anal_resrc_supl_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_anal_resrc_supl_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_anal_pipeline_no_10kv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_anal_pipeline_name_10kv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_anal_pipeline_no_04kv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_anal_pipeline_name_04kv` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cs_charg_back_rec_id` int DEFAULT NULL,
  `back_dir` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `back_dir_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `back_proc_step` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `back_reason` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `back_dept` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `back_stf` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `back_time` datetime DEFAULT NULL,
  `charg_back_cls` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `charg_back_cls_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cs_wk_order_fnl_reply_id` int DEFAULT NULL,
  `fnl_reply_cust_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fnl_reply_fnl_reply_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fnl_reply_fnl_reply_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fnl_reply_fnl_reply_cont` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fnl_reply_app_org_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fnl_reply_contact_tel1` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fnl_reply_ec_addr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fnl_reply_contact_tel2` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fnl_reply_contact_tel3` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cs_srv_app_hndl_id` int DEFAULT NULL,
  `srv_app_rcvr_ps_time` datetime DEFAULT NULL,
  `srv_app_setl_arer_time` datetime DEFAULT NULL,
  `srv_app_exist_pay_err_flag` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_app_exist_pay_err_flag_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_app_exist_pay_err_exp` int DEFAULT NULL,
  `cs_fault_hndl_id` int DEFAULT NULL,
  `frst_aid_stf` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `frst_aid_team` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `frst_aid_team_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `asgn_time` datetime DEFAULT NULL,
  `arr_site_time` datetime DEFAULT NULL,
  `reco_time` datetime DEFAULT NULL,
  `frst_aid_handle_rec` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_phen` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_phen_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_dev_pr_attr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_dev_pr_attr_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_site_cls` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_site_cls_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cs_rpt_hndl_id` int DEFAULT NULL,
  `cs_cmplt_hndl_id` int DEFAULT NULL,
  `cmplt_rcvr_pwr_time` datetime DEFAULT NULL,
  `cmplt_tmot_reason` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cmplt_tmot_reason_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cmplt_pwr_off_times` int DEFAULT NULL,
  `cmplt_plan_pwr_off_times` int DEFAULT NULL,
  `cmplt_elect_pwr_off_times` int DEFAULT NULL,
  `cmplt_meter_pwr_off_times` int DEFAULT NULL,
  `cmplt_cust_pwr_off_times` int DEFAULT NULL,
  `cmplt_temp_pwr_off_times` int DEFAULT NULL,
  `cmplt_other_pwr_off_times` int DEFAULT NULL,
  `cmplt_cmplt_supl_stop_type` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cmplt_cmplt_supl_stop_type_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cmplt_lv_reason` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cmplt_lv_reason_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cmplt_cmplt_obj_back` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cmplt_cmplt_obj_back_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cmplt_dev_pr_attr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cmplt_dev_pr_attr_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cs_elec_vehicle_hndl_id` int DEFAULT NULL,
  `elec_vehicle_cp_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_vehicle_cp_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_vehicle_cp_model` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_vehicle_cp_mfr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_vehicle_cp_strt_time` datetime DEFAULT NULL,
  `affil_org_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `affil_org_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pow_sup_station_code` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pow_sup_station_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ds` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`cs_wk_order_hndl_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_srv_cs_wk_order_hndl`
--

LOCK TABLES `dwd_cst_srv_cs_wk_order_hndl` WRITE;
/*!40000 ALTER TABLE `dwd_cst_srv_cs_wk_order_hndl` DISABLE KEYS */;
INSERT INTO `dwd_cst_srv_cs_wk_order_hndl` VALUES (288962,487105,'AP-0002','HN-0002','工单处理单位名称2','工单处理人员_2','接单部门_2','接单人员_2','发送部门_2','华能集团','工单责任部门_2','2024-03-01 05:00:00','工单处理情况_2','承办意见_2','客户意见_2','处理意见_2','处理结果_2','属实标志_2','属实标志名称2','2025-03-15 17:00:00','2024-04-14 17:00:00','责任标志_2','责任标志名称2','2024-02-04 00:00:00','业务处理子类型_2','客户服务责任专业_2','办结标志_2','办结标志名称2',130449,'活动实例名称2','ST-0002',4745,'上一活动实例名称2','2025-04-10 04:00:00','回退标志_2','回退标志名称2','工单处理审批结果_2','工单处理审批结果名称2','工单处理审批意见_2','不通过类型_2','不通过类型名称2','激活','工单处理状态名称2','华能集团','所属区县名称2','无理诉求标志_2','无理诉求标志名称2','工单预约标志_2','工单预约标志名称2','2025-03-26 21:00:00','预约原因_2','城农网标志_2','城农网标志名称2','业务类型_2','业务类型名称2','ATT0002','AF-0002','省侧业务子类型_2',45600,'SR-0002','服务分析配送站名称2','SR-0002','服务分析管线名称102','SR-0002','服务分析管线名称0.2',163427,'回退方向_2','回退方向名称2','回退环节_2','回退原因_2','回退部门_2','回退人员_2','2024-12-26 22:00:00','退单原因分类_2','退单原因分类名称2',585142,'最终答复客户名称2','最终答复标志_2','最终答复标志名称2','最终答复内容_2','FN-0002','13896967286','上海市浦东新区yy路2号','13871136815','13896694691',312974,'2024-03-31 04:00:00','2024-04-19 02:00:00','服务申请存在交费_2','服务申请存在交费差错2',141899,794825,'故障抢修人员名称2','故障抢修班组_2','故障抢修班组名称2','2024-02-13 21:00:00','2025-04-10 19:00:00','2024-05-02 10:00:00','故障现场抢修记录_2','故障现象_2','故障现象名称2','故障设备产权属性_2','故障设备产权属性名称2','处理现场分类_2','处理现场分类名称2',384719,599429,'2025-05-07 09:00:00','投诉复电超时原因_2','投诉复电超时原因名称2',198368,665488,549196,291387,968499,904316,756324,'投诉末次投诉停电_2','投诉末次投诉停电类型2','投诉低电压原因_2','投诉低电压原因名称2','投诉对象（回单）_2','投诉对象（回单）名称2','投诉设备产权属性_2','投诉设备产权属性名称2',350504,'电动汽车充电桩名称2','EL-0002','电动汽车充电桩型_2','电动汽车充电桩生_2','2024-09-19 14:00:00','AF-0002','所属单位名称2','PR-0002','省公司名称2','CI-0002','地市公司名称2','CO-0002','区县公司名称2','PO-0002','供电所名称2','2024-02-25 00:00:00','分区字段_2'),(555521,868800,'AP-0001','HN-0001','工单处理单位名称1','工单处理人员_1','接单部门_1','接单人员_1','发送部门_1','华能集团','工单责任部门_1','2024-12-06 17:00:00','工单处理情况_1','承办意见_1','客户意见_1','处理意见_1','处理结果_1','属实标志_1','属实标志名称1','2024-07-05 00:00:00','2024-06-15 09:00:00','责任标志_1','责任标志名称1','2024-09-01 23:00:00','业务处理子类型_1','客户服务责任专业_1','办结标志_1','办结标志名称1',781590,'活动实例名称1','ST-0001',306155,'上一活动实例名称1','2024-03-17 21:00:00','回退标志_1','回退标志名称1','工单处理审批结果_1','工单处理审批结果名称1','工单处理审批意见_1','不通过类型_1','不通过类型名称1','正常','工单处理状态名称1','国家电投','所属区县名称1','无理诉求标志_1','无理诉求标志名称1','工单预约标志_1','工单预约标志名称1','2024-02-06 21:00:00','预约原因_1','城农网标志_1','城农网标志名称1','业务类型_1','业务类型名称1','ATT0001','AF-0001','省侧业务子类型_1',12905,'SR-0001','服务分析配送站名称1','SR-0001','服务分析管线名称101','SR-0001','服务分析管线名称0.1',603111,'回退方向_1','回退方向名称1','回退环节_1','回退原因_1','回退部门_1','回退人员_1','2024-01-14 04:00:00','退单原因分类_1','退单原因分类名称1',114976,'最终答复客户名称1','最终答复标志_1','最终答复标志名称1','最终答复内容_1','FN-0001','13836452957','北京市朝阳区xx路1号','13843693733','13862707471',839346,'2024-03-20 03:00:00','2024-06-02 18:00:00','服务申请存在交费_1','服务申请存在交费差错1',993422,794007,'故障抢修人员名称1','故障抢修班组_1','故障抢修班组名称1','2025-04-17 14:00:00','2024-01-13 14:00:00','2024-10-19 10:00:00','故障现场抢修记录_1','故障现象_1','故障现象名称1','故障设备产权属性_1','故障设备产权属性名称1','处理现场分类_1','处理现场分类名称1',794348,168078,'2025-03-02 21:00:00','投诉复电超时原因_1','投诉复电超时原因名称1',564481,399659,481508,597848,856698,929520,302140,'投诉末次投诉停电_1','投诉末次投诉停电类型1','投诉低电压原因_1','投诉低电压原因名称1','投诉对象（回单）_1','投诉对象（回单）名称1','投诉设备产权属性_1','投诉设备产权属性名称1',806884,'电动汽车充电桩名称1','EL-0001','电动汽车充电桩型_1','电动汽车充电桩生_1','2024-07-30 09:00:00','AF-0001','所属单位名称1','PR-0001','省公司名称1','CI-0001','地市公司名称1','CO-0001','区县公司名称1','PO-0001','供电所名称1','2025-02-24 00:00:00','分区字段_1'),(606667,939212,'AP-0003','HN-0003','工单处理单位名称3','工单处理人员_3','接单部门_3','接单人员_3','发送部门_3','南方电网公司','工单责任部门_3','2024-09-19 15:00:00','工单处理情况_3','承办意见_3','客户意见_3','处理意见_3','处理结果_3','属实标志_3','属实标志名称3','2024-09-18 21:00:00','2025-01-12 03:00:00','责任标志_3','责任标志名称3','2024-08-11 02:00:00','业务处理子类型_3','客户服务责任专业_3','办结标志_3','办结标志名称3',192818,'活动实例名称3','ST-0003',83180,'上一活动实例名称3','2024-09-07 05:00:00','回退标志_3','回退标志名称3','工单处理审批结果_3','工单处理审批结果名称3','工单处理审批意见_3','不通过类型_3','不通过类型名称3','异常','工单处理状态名称3','大唐集团','所属区县名称3','无理诉求标志_3','无理诉求标志名称3','工单预约标志_3','工单预约标志名称3','2025-03-30 13:00:00','预约原因_3','城农网标志_3','城农网标志名称3','业务类型_3','业务类型名称3','ATT0003','AF-0003','省侧业务子类型_3',21786,'SR-0003','服务分析配送站名称3','SR-0003','服务分析管线名称103','SR-0003','服务分析管线名称0.3',532973,'回退方向_3','回退方向名称3','回退环节_3','回退原因_3','回退部门_3','回退人员_3','2024-01-21 15:00:00','退单原因分类_3','退单原因分类名称3',29997,'最终答复客户名称3','最终答复标志_3','最终答复标志名称3','最终答复内容_3','FN-0003','13816868007','深圳市南山区aa路4号','13870121502','13847756993',344775,'2025-01-27 04:00:00','2024-09-15 20:00:00','服务申请存在交费_3','服务申请存在交费差错3',709,97299,'故障抢修人员名称3','故障抢修班组_3','故障抢修班组名称3','2025-04-10 19:00:00','2024-08-27 20:00:00','2024-02-07 20:00:00','故障现场抢修记录_3','故障现象_3','故障现象名称3','故障设备产权属性_3','故障设备产权属性名称3','处理现场分类_3','处理现场分类名称3',888430,188102,'2024-05-30 21:00:00','投诉复电超时原因_3','投诉复电超时原因名称3',543581,369172,209816,172100,363496,204393,492766,'投诉末次投诉停电_3','投诉末次投诉停电类型3','投诉低电压原因_3','投诉低电压原因名称3','投诉对象（回单）_3','投诉对象（回单）名称3','投诉设备产权属性_3','投诉设备产权属性名称3',530677,'电动汽车充电桩名称3','EL-0003','电动汽车充电桩型_3','电动汽车充电桩生_3','2024-03-20 01:00:00','AF-0003','所属单位名称3','PR-0003','省公司名称3','CI-0003','地市公司名称3','CO-0003','区县公司名称3','PO-0003','供电所名称3','2025-05-04 00:00:00','分区字段_3');
/*!40000 ALTER TABLE `dwd_cst_srv_cs_wk_order_hndl` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_srv_poweroff_affect_cons_dtl`
--

DROP TABLE IF EXISTS `dwd_cst_srv_poweroff_affect_cons_dtl`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_srv_poweroff_affect_cons_dtl` (
  `pk_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `poweroff_info_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cons_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cons_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cons_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_lvl_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_lvl_dsc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cons_typ_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cons_typ_dsc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `imp_cust_flg` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `imp_cust_flg_dsc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sensitive_cust_flg` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sensitive_cust_flg_dsc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_tm` datetime DEFAULT NULL,
  `chg_typ` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_typ_dsc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact_addr` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contact` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tel_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tg_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tg_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eqp_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eqp_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sync_st` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sync_st_dsc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `org_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `org_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_org_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_org_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_county_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_county_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_city_org_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_city_org_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_dt` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_tm` datetime DEFAULT NULL,
  PRIMARY KEY (`pk_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_srv_poweroff_affect_cons_dtl`
--

LOCK TABLES `dwd_cst_srv_poweroff_affect_cons_dtl` WRITE;
/*!40000 ALTER TABLE `dwd_cst_srv_poweroff_affect_cons_dtl` DISABLE KEYS */;
INSERT INTO `dwd_cst_srv_poweroff_affect_cons_dtl` VALUES ('PK0001','PO-0001','CON0001','CO-0001','用户名称1','电压等级代码_1','电压等级描述_1','用户分类代码_1','用户分类描述_1','重要客户标志_1','重要客户描述_1','敏感客户标志_1','敏感客户描述_1','2025-01-18 18:00:00','变更类型_1','变更类型描述_1','上海市浦东新区yy路2号','联系人_1','TE-0001','TG-0001','台区名称1','EQ-0001','设备名称1','注销','停用','OR-0001','供电单位名称1','ST-0001','标准单位名称(个性化1','ST-0001','标准区县单位名称(个1','ST-0001','标准地市单位名称(个1','2024-10-25 00:00:00','2025-01-25 19:00:00'),('PK0002','PO-0002','CON0002','CO-0002','用户名称2','电压等级代码_2','电压等级描述_2','用户分类代码_2','用户分类描述_2','重要客户标志_2','重要客户描述_2','敏感客户标志_2','敏感客户描述_2','2025-04-23 08:00:00','变更类型_2','变更类型描述_2','广州市天河区zz路3号','联系人_2','TE-0002','TG-0002','台区名称2','EQ-0002','设备名称2','注销','激活','OR-0002','供电单位名称2','ST-0002','标准单位名称(个性化2','ST-0002','标准区县单位名称(个2','ST-0002','标准地市单位名称(个2','2024-11-27 00:00:00','2024-07-23 14:00:00'),('PK0003','PO-0003','CON0003','CO-0003','用户名称3','电压等级代码_3','电压等级描述_3','用户分类代码_3','用户分类描述_3','重要客户标志_3','重要客户描述_3','敏感客户标志_3','敏感客户描述_3','2024-10-31 03:00:00','变更类型_3','变更类型描述_3','广州市天河区zz路3号','联系人_3','TE-0003','TG-0003','台区名称3','EQ-0003','设备名称3','正常','停用','OR-0003','供电单位名称3','ST-0003','标准单位名称(个性化3','ST-0003','标准区县单位名称(个3','ST-0003','标准地市单位名称(个3','2024-03-09 00:00:00','2024-04-07 05:00:00');
/*!40000 ALTER TABLE `dwd_cst_srv_poweroff_affect_cons_dtl` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_srv_poweroff_affect_eqp_dtl`
--

DROP TABLE IF EXISTS `dwd_cst_srv_poweroff_affect_eqp_dtl`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_srv_poweroff_affect_eqp_dtl` (
  `poweroff_affect_eqp_list_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `poweroff_info_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pms_eqp_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cms_eqp_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eqp_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eqp_typ_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eqp_typ_dsc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_lvl_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_line_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_line_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_subs_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_subs_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_tm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_typ_cd` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_typ_dsc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tg_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tg_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_already_sendelec` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `scene_power_trans_tm` datetime DEFAULT NULL,
  `tg_cons_tolnum` double DEFAULT NULL,
  `inhabitant_cons_num` double DEFAULT NULL,
  `sfgd_indust_cons_num` double DEFAULT NULL,
  `imp_cons_num` double DEFAULT NULL,
  `industry_commerce_cons_num` double DEFAULT NULL,
  `is_syn` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgmt_org_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgmt_org_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_org_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_org_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_city_org_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_city_org_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_district_org_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_district_org_nm` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_dt` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_tm` datetime DEFAULT NULL,
  PRIMARY KEY (`poweroff_affect_eqp_list_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_srv_poweroff_affect_eqp_dtl`
--

LOCK TABLES `dwd_cst_srv_poweroff_affect_eqp_dtl` WRITE;
/*!40000 ALTER TABLE `dwd_cst_srv_poweroff_affect_eqp_dtl` DISABLE KEYS */;
INSERT INTO `dwd_cst_srv_poweroff_affect_eqp_dtl` VALUES ('POW0001','PO-0001','PMS0001','CMS0001','设备名称1','设备类型代码_1','设备类型描述_1','电压等级名称1','BL-0001','所属线路名称1','BL-0001','所属变电站名称1','2024-02-27 00:00:00','变更类型代码_1','变更类型描述_1','TG-0001','台区名称1','是否已经送电_1','2024-02-29 18:00:00',2474.54,2403.65,8398.19,3254.04,1503.8,'是否同步_1','MG-0001','管理单位名称1','ST-0001','标准供电单位名称(个1','ST-0001','标准地市公司名称(个1','ST-0001','标准区县公司名称(个1','2024-03-28 00:00:00','2025-03-31 16:00:00'),('POW0002','PO-0002','PMS0002','CMS0002','设备名称2','设备类型代码_2','设备类型描述_2','电压等级名称2','BL-0002','所属线路名称2','BL-0002','所属变电站名称2','2024-07-11 00:00:00','变更类型代码_2','变更类型描述_2','TG-0002','台区名称2','是否已经送电_2','2024-06-06 09:00:00',1285.97,9045.06,491.27,4476.79,1928.27,'是否同步_2','MG-0002','管理单位名称2','ST-0002','标准供电单位名称(个2','ST-0002','标准地市公司名称(个2','ST-0002','标准区县公司名称(个2','2024-07-12 00:00:00','2025-01-27 11:00:00'),('POW0003','PO-0003','PMS0003','CMS0003','设备名称3','设备类型代码_3','设备类型描述_3','电压等级名称3','BL-0003','所属线路名称3','BL-0003','所属变电站名称3','2024-12-22 00:00:00','变更类型代码_3','变更类型描述_3','TG-0003','台区名称3','是否已经送电_3','2024-11-09 19:00:00',1180.57,230.69,3399.01,1286.27,8949.95,'是否同步_3','MG-0003','管理单位名称3','ST-0003','标准供电单位名称(个3','ST-0003','标准地市公司名称(个3','ST-0003','标准区县公司名称(个3','2024-09-10 00:00:00','2025-03-29 19:00:00');
/*!40000 ALTER TABLE `dwd_cst_srv_poweroff_affect_eqp_dtl` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_srv_poweroff_send_rec`
--

DROP TABLE IF EXISTS `dwd_cst_srv_poweroff_send_rec`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_srv_poweroff_send_rec` (
  `PK_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `poweroff_info_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `subs_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `line_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tra_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tg_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_range` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_start_tm` datetime DEFAULT NULL,
  `poweroff_end_tm` datetime DEFAULT NULL,
  `mgmt_org_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgmt_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_typ_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_typ_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_area` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_caus` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sendelec_typ_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sendelec_typ_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `scene_sendelec_tm` datetime DEFAULT NULL,
  `sendelec_remark` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `already_sendelec_eqp_list` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lvl1_poweroff_caus_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lvl1_poweroff_caus_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_eqp` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_typ_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_typ_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fault_eqp_detl` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_send_SMS_give_cust` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_send_SMS_give_tg_manager` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `workst_src` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_range_typ_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_range_typ_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `subs_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `line_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tra_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tg_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `submit_st_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `submit_st_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Fill_tm` datetime DEFAULT NULL,
  `release_tm` datetime DEFAULT NULL,
  `poweroff_fill_man_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_typ` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_caus` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `affect_tg_num` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `affect_tg_cons_num` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `release_channel_src` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_pos` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lvl2_poweroff_caus_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lvl2_poweroff_caus_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `line_org` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `syn_st` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rec_info_entry_mode` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_day_stop_night_sendelec` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `day_stop_start_tm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `night_sendelec_start_tm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `volt_lvl` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cons_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cons_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sendelec_range_remark` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fst_release_tm` datetime DEFAULT NULL,
  `fst_poweroff_start_tm` datetime DEFAULT NULL,
  `fst_poweroff_end_tm` datetime DEFAULT NULL,
  `fst_sendelec_tm` datetime DEFAULT NULL,
  `is_stop_elec_modulation_elec` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_urgency_extinc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `new_entry_tm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_city_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_city_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_county_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_county_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `beca_disaster_poweroff` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `subs_volt_lvl` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_farm_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_caus_cls` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lvl3_poweroff_caus_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lvl3_poweroff_caus_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `inhabitant_cons_num` double DEFAULT NULL,
  `not_inhabitant_cons_num` double DEFAULT NULL,
  `emphasis_sfgd_cons_num` double DEFAULT NULL,
  `imp_cust_num` double DEFAULT NULL,
  `livelihood_cons_num` double DEFAULT NULL,
  `poweroff_sensitive_cons_num` double DEFAULT NULL,
  `zero_load_cons_num` double DEFAULT NULL,
  `is_ultra_thousand_poweroff` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_have_often_poweroff_cons` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_org_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_county_org_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_county_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_city_org_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_city_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_dt` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_tm` datetime DEFAULT NULL,
  `ds` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`PK_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_srv_poweroff_send_rec`
--

LOCK TABLES `dwd_cst_srv_poweroff_send_rec` WRITE;
/*!40000 ALTER TABLE `dwd_cst_srv_poweroff_send_rec` DISABLE KEYS */;
INSERT INTO `dwd_cst_srv_poweroff_send_rec` VALUES ('PK0001','PO-0001','变电站名称1','线路名称1','变压器名称1','台区名称1','停电范围_1','2024-02-05 00:00:00','2024-06-26 21:00:00','MG-0001','管理单位名称1','停电类型代码_1','停电类型描述_1','停电区域_1','停电原因_1','送电类型代码_1','送电类型描述_1','2024-06-08 19:00:00','送电说明测试数据1','已送电设备清单_1','一级停电原因_1','一级停电原因_1','故障设备_1','故障类型代码_1','故障类型描述_1','故障设备详情_1','是否发送短信给客_1','是否发送短信给台_1','工单来源_1','停电范围类型代码_1','停电范围类型描述_1','SU-0001','LI-0001','TR-0001','TG-0001','注销','停用','2025-02-15 03:00:00','2024-03-08 12:00:00','填报人_1','变更类型_1','变更原因_1','AF-0001','AF-0001','发布渠道来源_1','停电位置_1','二级停电原因代码_1','二级停电原因描述_1','国家电投','异常','记录信息录入方式_1','是否昼停夜送_1','2024-05-29 00:00:00','2025-01-25 00:00:00','电压等级_1','用户名称1','CO-0001','送电范围说明测试数据1','2024-05-07 17:00:00','2024-03-21 02:00:00','2024-12-21 07:00:00','2024-09-04 18:00:00','是否停电调电_1','是否紧急消缺_1','2024-08-08 00:00:00','ST-0001','市州行政区域名称1','ST-0001','区县行政区域名称1','因灾停电_1','变电站电压等级_1','CIT0001','停电原因分类_1','三级停电原因代码_1','三级停电原因描述_1',721.76,4789.96,4307.54,4167.3,5020.96,4577.33,9377,'是否超千户停电停_1','是否有频繁停电用_1','ST-0001','标准供电单位名称1','ST-0001','标准区县公司名称1','ST-0001','标准地市公司名称1','2024-11-06 00:00:00','2024-12-05 19:00:00','按日分区_1'),('PK0002','PO-0002','变电站名称2','线路名称2','变压器名称2','台区名称2','停电范围_2','2025-01-01 03:00:00','2024-05-24 20:00:00','MG-0002','管理单位名称2','停电类型代码_2','停电类型描述_2','停电区域_2','停电原因_2','送电类型代码_2','送电类型描述_2','2025-03-08 15:00:00','送电说明测试数据2','已送电设备清单_2','一级停电原因_2','一级停电原因_2','故障设备_2','故障类型代码_2','故障类型描述_2','故障设备详情_2','是否发送短信给客_2','是否发送短信给台_2','工单来源_2','停电范围类型代码_2','停电范围类型描述_2','SU-0002','LI-0002','TR-0002','TG-0002','激活','停用','2024-01-30 18:00:00','2024-10-22 02:00:00','填报人_2','变更类型_2','变更原因_2','AF-0002','AF-0002','发布渠道来源_2','停电位置_2','二级停电原因代码_2','二级停电原因描述_2','华能集团','注销','记录信息录入方式_2','是否昼停夜送_2','2024-02-07 00:00:00','2025-04-10 00:00:00','电压等级_2','用户名称2','CO-0002','送电范围说明测试数据2','2024-05-11 12:00:00','2024-09-24 04:00:00','2024-06-28 16:00:00','2024-02-11 08:00:00','是否停电调电_2','是否紧急消缺_2','2024-11-16 00:00:00','ST-0002','市州行政区域名称2','ST-0002','区县行政区域名称2','因灾停电_2','变电站电压等级_2','CIT0002','停电原因分类_2','三级停电原因代码_2','三级停电原因描述_2',8924,128.21,8996.23,8151.87,1540.08,3016.11,8643.82,'是否超千户停电停_2','是否有频繁停电用_2','ST-0002','标准供电单位名称2','ST-0002','标准区县公司名称2','ST-0002','标准地市公司名称2','2025-01-14 00:00:00','2024-10-26 14:00:00','按日分区_2'),('PK0003','PO-0003','变电站名称3','线路名称3','变压器名称3','台区名称3','停电范围_3','2024-03-29 20:00:00','2024-06-02 23:00:00','MG-0003','管理单位名称3','停电类型代码_3','停电类型描述_3','停电区域_3','停电原因_3','送电类型代码_3','送电类型描述_3','2024-05-21 05:00:00','送电说明测试数据3','已送电设备清单_3','一级停电原因_3','一级停电原因_3','故障设备_3','故障类型代码_3','故障类型描述_3','故障设备详情_3','是否发送短信给客_3','是否发送短信给台_3','工单来源_3','停电范围类型代码_3','停电范围类型描述_3','SU-0003','LI-0003','TR-0003','TG-0003','异常','停用','2024-03-26 07:00:00','2024-08-29 00:00:00','填报人_3','变更类型_3','变更原因_3','AF-0003','AF-0003','发布渠道来源_3','停电位置_3','二级停电原因代码_3','二级停电原因描述_3','大唐集团','激活','记录信息录入方式_3','是否昼停夜送_3','2024-07-11 00:00:00','2024-09-06 00:00:00','电压等级_3','用户名称3','CO-0003','送电范围说明测试数据3','2025-04-18 16:00:00','2024-09-28 05:00:00','2024-11-20 07:00:00','2024-11-13 10:00:00','是否停电调电_3','是否紧急消缺_3','2025-03-22 00:00:00','ST-0003','市州行政区域名称3','ST-0003','区县行政区域名称3','因灾停电_3','变电站电压等级_3','CIT0003','停电原因分类_3','三级停电原因代码_3','三级停电原因描述_3',16.93,7941.92,856.69,2154.6,9185.35,4248.52,2034.44,'是否超千户停电停_3','是否有频繁停电用_3','ST-0003','标准供电单位名称3','ST-0003','标准区县公司名称3','ST-0003','标准地市公司名称3','2024-11-22 00:00:00','2024-03-28 21:00:00','按日分区_3');
/*!40000 ALTER TABLE `dwd_cst_srv_poweroff_send_rec` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_srv_supl_stop_cust_dtl_day`
--

DROP TABLE IF EXISTS `dwd_cst_srv_supl_stop_cust_dtl_day`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_srv_supl_stop_cust_dtl_day` (
  `chg_stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_time` datetime DEFAULT NULL,
  `chg_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `csc_supl_stop_id` double DEFAULT NULL,
  `cust_cls` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_id` double DEFAULT NULL,
  `cust_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cust_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mobile_number` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pms_supl_stop_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rela_adj_volt_dev_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rela_adj_volt_dev_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rela_dist_sta_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rela_meter_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_stop_cust_dtl_id` double NOT NULL,
  `supl_stop_id` double DEFAULT NULL,
  `voltage` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`supl_stop_cust_dtl_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_srv_supl_stop_cust_dtl_day`
--

LOCK TABLES `dwd_cst_srv_supl_stop_cust_dtl_day` WRITE;
/*!40000 ALTER TABLE `dwd_cst_srv_supl_stop_cust_dtl_day` DISABLE KEYS */;
INSERT INTO `dwd_cst_srv_supl_stop_cust_dtl_day` VALUES ('激活','2024-04-29 17:00:00','变更类型_2',7747.57,'客户分类_2',879.85,'客户名称2','CU-0002','MG-0002','MO-0002','PM-0002','REL0002','关联调压设备名称2','REL0002','REL0002',3020.41,687.21,'承压_2','2024-05-19 09:00:00','2024-08-08 00:00:00'),('停用','2024-05-22 11:00:00','变更类型_3',6585.49,'客户分类_3',2348.06,'客户名称3','CU-0003','MG-0003','MO-0003','PM-0003','REL0003','关联调压设备名称3','REL0003','REL0003',7787.03,9214.57,'承压_3','2024-09-21 08:00:00','2024-08-31 00:00:00'),('注销','2025-02-21 21:00:00','变更类型_1',6372.17,'客户分类_1',2720.33,'客户名称1','CU-0001','MG-0001','MO-0001','PM-0001','REL0001','关联调压设备名称1','REL0001','REL0001',9453.89,4182.44,'承压_1','2024-07-29 06:00:00','2024-04-19 00:00:00');
/*!40000 ALTER TABLE `dwd_cst_srv_supl_stop_cust_dtl_day` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cst_srv_supl_stop_rec_day`
--

DROP TABLE IF EXISTS `dwd_cst_srv_supl_stop_rec_day`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cst_srv_supl_stop_rec_day` (
  `adj_volt_dev_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `area_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `area_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `before_stop_beg_time` datetime DEFAULT NULL,
  `before_stop_end_time` datetime DEFAULT NULL,
  `chg_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `chg_time` datetime DEFAULT NULL,
  `chg_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cntrl_sta_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cntrl_sta_id` double DEFAULT NULL,
  `cntrl_sta_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `csc_supl_stop_id` double DEFAULT NULL,
  `day_night_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `day_stop_time` datetime DEFAULT NULL,
  `dist_sta_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `extr_qry_flag` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fill_no` double DEFAULT NULL,
  `fill_stf_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fill_stf_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `fill_time` datetime DEFAULT NULL,
  `infl_cust_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `info_stat` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `issu_chan` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `issu_chan_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `issu_time` datetime DEFAULT NULL,
  `mgt_org_code` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `night_supl_time` datetime DEFAULT NULL,
  `pipeline_id` double DEFAULT NULL,
  `pipeline_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pipeline_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pms_supl_stop_no` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `protect_actn` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `srv_kind` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_rcvr_area_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_rcvr_desc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_rcvr_time` datetime DEFAULT NULL,
  `supl_rcvr_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_stop_area` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_stop_beg_time` datetime DEFAULT NULL,
  `supl_stop_end_time` datetime DEFAULT NULL,
  `supl_stop_id` double NOT NULL,
  `supl_stop_loc` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_stop_no` double DEFAULT NULL,
  `supl_stop_reason` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_stop_rng` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `supl_stop_type` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `voltage` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`supl_stop_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cst_srv_supl_stop_rec_day`
--

LOCK TABLES `dwd_cst_srv_supl_stop_rec_day` WRITE;
/*!40000 ALTER TABLE `dwd_cst_srv_supl_stop_rec_day` DISABLE KEYS */;
INSERT INTO `dwd_cst_srv_supl_stop_rec_day` VALUES ('调压设备名称2','AR-0002','行政区域名称2','2025-01-20 18:00:00','2024-05-23 09:00:00','变更说明测试数据2','变更原因_2','2024-05-16 08:00:00','变更类型_2','CN-0002',5387.85,'枢纽站名称2',2900.49,'昼停夜送标志_2','2024-02-20 01:00:00','DI-0002','外部查询标志_2',6019.87,'填报人名称2','FI-0002','2024-04-07 11:00:00','影响重要客户说明测试数据2','异常','发布渠道_2','发布渠道说明测试数据2','2025-04-19 01:00:00','MG-0002','2024-02-14 03:00:00',6570.11,'管线名称2','PI-0002','PM-0002','保护动作_2','服务种类_2','复供区域说明测试数据2','现场复供说明测试数据2','2025-02-08 11:00:00','现场复供类型_2','停供区域_2','2024-02-08 16:00:00','2024-06-23 22:00:00',3487.69,'停供位置_2',4677.58,'停供原因_2','停供范围_2','停供类型_2','承压_2','2024-03-17 14:00:00','2024-04-17 00:00:00'),('调压设备名称3','AR-0003','行政区域名称3','2024-11-22 02:00:00','2024-02-02 16:00:00','变更说明测试数据3','变更原因_3','2025-04-02 14:00:00','变更类型_3','CN-0003',5060.41,'枢纽站名称3',6728.37,'昼停夜送标志_3','2024-12-20 21:00:00','DI-0003','外部查询标志_3',9738.11,'填报人名称3','FI-0003','2024-05-12 15:00:00','影响重要客户说明测试数据3','异常','发布渠道_3','发布渠道说明测试数据3','2025-01-01 15:00:00','MG-0003','2025-03-14 12:00:00',5772.66,'管线名称3','PI-0003','PM-0003','保护动作_3','服务种类_3','复供区域说明测试数据3','现场复供说明测试数据3','2025-04-25 22:00:00','现场复供类型_3','停供区域_3','2024-07-19 02:00:00','2024-02-06 15:00:00',3719.52,'停供位置_3',8600.63,'停供原因_3','停供范围_3','停供类型_3','承压_3','2024-03-30 01:00:00','2024-03-31 00:00:00'),('调压设备名称1','AR-0001','行政区域名称1','2024-03-04 08:00:00','2024-09-21 22:00:00','变更说明测试数据1','变更原因_1','2025-03-18 17:00:00','变更类型_1','CN-0001',5204.68,'枢纽站名称1',4951.9,'昼停夜送标志_1','2025-03-08 11:00:00','DI-0001','外部查询标志_1',1782.6,'填报人名称1','FI-0001','2024-01-03 02:00:00','影响重要客户说明测试数据1','异常','发布渠道_1','发布渠道说明测试数据1','2024-04-17 07:00:00','MG-0001','2024-06-16 08:00:00',7927.26,'管线名称1','PI-0001','PM-0001','保护动作_1','服务种类_1','复供区域说明测试数据1','现场复供说明测试数据1','2024-10-27 00:00:00','现场复供类型_1','停供区域_1','2024-10-02 12:00:00','2024-10-31 22:00:00',5310.81,'停供位置_1',1149.22,'停供原因_1','停供范围_1','停供类型_1','承压_1','2024-07-16 03:00:00','2025-02-18 00:00:00');
/*!40000 ALTER TABLE `dwd_cst_srv_supl_stop_rec_day` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cust_analog_f`
--

DROP TABLE IF EXISTS `dwd_cust_analog_f`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cust_analog_f` (
  `id` int NOT NULL AUTO_INCREMENT,
  `inst_id` varchar(255) DEFAULT NULL,
  `equip_src_id` varchar(255) DEFAULT NULL,
  `measuerment_type` varchar(255) DEFAULT NULL,
  `date` varchar(255) DEFAULT NULL,
  `V0000` decimal(20,4) DEFAULT NULL,
  `V0015` decimal(20,4) DEFAULT NULL,
  `V0030` decimal(20,4) DEFAULT NULL,
  `V0045` decimal(20,4) DEFAULT NULL,
  `V0100` decimal(20,4) DEFAULT NULL,
  `V0115` decimal(20,4) DEFAULT NULL,
  `V0130` decimal(20,4) DEFAULT NULL,
  `V0145` decimal(20,4) DEFAULT NULL,
  `V0200` decimal(20,4) DEFAULT NULL,
  `V0215` decimal(20,4) DEFAULT NULL,
  `V0230` decimal(20,4) DEFAULT NULL,
  `V0245` decimal(20,4) DEFAULT NULL,
  `V0300` decimal(20,4) DEFAULT NULL,
  `V0315` decimal(20,4) DEFAULT NULL,
  `V0330` decimal(20,4) DEFAULT NULL,
  `V0345` decimal(20,4) DEFAULT NULL,
  `V0400` decimal(20,4) DEFAULT NULL,
  `V0415` decimal(20,4) DEFAULT NULL,
  `V0430` decimal(20,4) DEFAULT NULL,
  `V0445` decimal(20,4) DEFAULT NULL,
  `V0500` decimal(20,4) DEFAULT NULL,
  `V0515` decimal(20,4) DEFAULT NULL,
  `V0530` decimal(20,4) DEFAULT NULL,
  `V0545` decimal(20,4) DEFAULT NULL,
  `V0600` decimal(20,4) DEFAULT NULL,
  `V0615` decimal(20,4) DEFAULT NULL,
  `V0630` decimal(20,4) DEFAULT NULL,
  `V0645` decimal(20,4) DEFAULT NULL,
  `V0700` decimal(20,4) DEFAULT NULL,
  `V0715` decimal(20,4) DEFAULT NULL,
  `V0730` decimal(20,4) DEFAULT NULL,
  `V0745` decimal(20,4) DEFAULT NULL,
  `V0800` decimal(20,4) DEFAULT NULL,
  `V0815` decimal(20,4) DEFAULT NULL,
  `V0830` decimal(20,4) DEFAULT NULL,
  `V0845` decimal(20,4) DEFAULT NULL,
  `V0900` decimal(20,4) DEFAULT NULL,
  `V0915` decimal(20,4) DEFAULT NULL,
  `V0930` decimal(20,4) DEFAULT NULL,
  `V0945` decimal(20,4) DEFAULT NULL,
  `V1000` decimal(20,4) DEFAULT NULL,
  `V1015` decimal(20,4) DEFAULT NULL,
  `V1030` decimal(20,4) DEFAULT NULL,
  `V1045` decimal(20,4) DEFAULT NULL,
  `V1100` decimal(20,4) DEFAULT NULL,
  `V1115` decimal(20,4) DEFAULT NULL,
  `V1130` decimal(20,4) DEFAULT NULL,
  `V1145` decimal(20,4) DEFAULT NULL,
  `V1200` decimal(20,4) DEFAULT NULL,
  `V1215` decimal(20,4) DEFAULT NULL,
  `V1230` decimal(20,4) DEFAULT NULL,
  `V1245` decimal(20,4) DEFAULT NULL,
  `V1300` decimal(20,4) DEFAULT NULL,
  `V1315` decimal(20,4) DEFAULT NULL,
  `V1330` decimal(20,4) DEFAULT NULL,
  `V1345` decimal(20,4) DEFAULT NULL,
  `V1400` decimal(20,4) DEFAULT NULL,
  `V1415` decimal(20,4) DEFAULT NULL,
  `V1430` decimal(20,4) DEFAULT NULL,
  `V1445` decimal(20,4) DEFAULT NULL,
  `V1500` decimal(20,4) DEFAULT NULL,
  `V1515` decimal(20,4) DEFAULT NULL,
  `V1530` decimal(20,4) DEFAULT NULL,
  `V1545` decimal(20,4) DEFAULT NULL,
  `V1600` decimal(20,4) DEFAULT NULL,
  `V1615` decimal(20,4) DEFAULT NULL,
  `V1630` decimal(20,4) DEFAULT NULL,
  `V1645` decimal(20,4) DEFAULT NULL,
  `V1700` decimal(20,4) DEFAULT NULL,
  `V1715` decimal(20,4) DEFAULT NULL,
  `V1730` decimal(20,4) DEFAULT NULL,
  `V1745` decimal(20,4) DEFAULT NULL,
  `V1800` decimal(20,4) DEFAULT NULL,
  `V1815` decimal(20,4) DEFAULT NULL,
  `V1830` decimal(20,4) DEFAULT NULL,
  `V1845` decimal(20,4) DEFAULT NULL,
  `V1900` decimal(20,4) DEFAULT NULL,
  `V1915` decimal(20,4) DEFAULT NULL,
  `V1930` decimal(20,4) DEFAULT NULL,
  `V1945` decimal(20,4) DEFAULT NULL,
  `V2000` decimal(20,4) DEFAULT NULL,
  `V2015` decimal(20,4) DEFAULT NULL,
  `V2030` decimal(20,4) DEFAULT NULL,
  `V2045` decimal(20,4) DEFAULT NULL,
  `V2100` decimal(20,4) DEFAULT NULL,
  `V2115` decimal(20,4) DEFAULT NULL,
  `V2130` decimal(20,4) DEFAULT NULL,
  `V2145` decimal(20,4) DEFAULT NULL,
  `V2200` decimal(20,4) DEFAULT NULL,
  `V2215` decimal(20,4) DEFAULT NULL,
  `V2230` decimal(20,4) DEFAULT NULL,
  `V2245` decimal(20,4) DEFAULT NULL,
  `V2300` decimal(20,4) DEFAULT NULL,
  `V2315` decimal(20,4) DEFAULT NULL,
  `V2330` decimal(20,4) DEFAULT NULL,
  `V2345` decimal(20,4) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cust_analog_f`
--

LOCK TABLES `dwd_cust_analog_f` WRITE;
/*!40000 ALTER TABLE `dwd_cust_analog_f` DISABLE KEYS */;
INSERT INTO `dwd_cust_analog_f` VALUES (1,NULL,'MET0002','TotW','20240315',220.5000,154.3515,154.3527,154.3546,154.3579,154.3634,154.3722,154.3863,154.4085,154.4427,154.4947,154.5724,154.6864,154.8511,155.0849,155.4109,155.8578,156.4598,157.2564,158.2917,159.6129,161.2679,163.3024,165.7557,168.6559,172.0155,175.8258,180.0531,184.6357,189.4820,194.4720,199.4604,204.2826,208.7635,212.7272,216.0086,218.4649,219.9854,220.5003,219.9858,218.4659,216.0106,212.7307,208.7697,204.2932,199.4782,194.5016,189.5304,184.7136,180.1767,176.0187,172.3120,169.1045,166.4239,164.2822,162.6824,161.6233,161.1048,161.1317,161.7154,162.8750,164.6348,167.0214,170.0587,173.7610,178.1263,183.1291,188.7135,194.7894,201.2290,207.8682,214.5105,220.9348,226.9060,232.1889,236.5629,239.8372,241.8641,242.5502,241.8638,239.8364,236.5615,232.1862,226.9013,220.9269,214.4972,207.8460,201.1927,194.7309,188.6208,182.9843,177.9040,173.4246,169.5576,166.2866,163.5739),(2,NULL,'MET0003','TotW','20240315',221.0000,154.7015,154.7027,154.7046,154.7079,154.7134,154.7222,154.7364,154.7586,154.7929,154.8450,154.9229,155.0372,155.2023,155.4365,155.7633,156.2113,156.8146,157.6130,158.6506,159.9748,161.6336,163.6727,166.1316,169.0384,172.4055,176.2245,180.4614,185.0544,189.9117,194.9130,199.9127,204.7459,209.2369,213.2096,216.4984,218.9603,220.4842,221.0003,220.4847,218.9613,216.5004,213.2131,209.2431,204.7564,199.9305,194.9426,189.9602,185.1325,180.5853,176.4178,172.7027,169.4880,166.8012,164.6548,163.0513,161.9898,161.4701,161.4970,162.0821,163.2443,165.0081,167.4002,170.4443,174.1550,178.5303,183.5443,189.1414,195.2311,201.6853,208.3396,214.9969,221.4358,227.4205,232.7154,237.0994,240.3811,242.4125,243.1002,242.4122,240.3803,237.0979,232.7127,227.4159,221.4278,214.9836,208.3173,201.6489,195.1725,189.0485,183.3993,178.3074,173.8178,169.9421,166.6636,163.9448),(3,NULL,'MET0001','TotW','20240315',221.5000,155.0515,155.0527,155.0546,155.0579,155.0634,155.0723,155.0865,155.1087,155.1431,155.1954,155.2734,155.3880,155.5534,155.7882,156.1157,156.5647,157.1694,157.9696,159.0096,160.3367,161.9993,164.0430,166.5074,169.4208,172.7956,176.6232,180.8697,185.4730,190.3413,195.3540,200.3650,205.2091,209.7103,213.6919,216.9883,219.4556,220.9831,221.5003,220.9835,219.4567,216.9902,213.6955,209.7165,205.2197,200.3828,195.3837,190.3900,185.5513,180.9938,176.8170,173.0934,169.8714,167.1786,165.0273,163.4202,162.3563,161.8355,161.8624,162.4488,163.6136,165.3814,167.7789,170.8300,174.5491,178.9342,183.9596,189.5694,195.6728,202.1416,208.8109,215.4834,221.9367,227.9350,233.2419,237.6358,240.9249,242.9610,243.6502,242.9606,240.9241,237.6343,233.2392,227.9304,221.9288,215.4700,208.7886,202.1051,195.6140,189.4763,183.8142,178.7108,174.2111,170.3266,167.0407,164.3157),(4,NULL,'MET0002','TotW','20240315',222.0000,155.4015,155.4027,155.4046,155.4080,155.4134,155.4223,155.4365,155.4589,155.4933,155.5457,155.6239,155.7387,155.9045,156.1399,156.4681,156.9181,157.5242,158.3262,159.3685,160.6987,162.3650,164.4133,166.8833,169.8033,173.1857,177.0219,181.2780,185.8917,190.7710,195.7949,200.8173,205.6723,210.1837,214.1743,217.4781,219.9510,221.4819,222.0003,221.4823,219.9521,217.4800,214.1779,210.1899,205.6829,200.8352,195.8247,190.8197,185.9702,181.4024,177.2161,173.4842,170.2549,167.5560,165.3998,163.7891,162.7228,162.2008,162.2278,162.8155,163.9830,165.7547,168.1576,171.2156,174.9431,179.3381,184.3748,189.9973,196.1145,202.5979,209.2823,215.9698,222.4377,228.4495,233.7684,238.1722,241.4688,243.5094,244.2002,243.5091,241.4680,238.1707,233.7657,228.4449,222.4298,215.9563,209.2599,202.5613,196.0556,189.9040,184.2291,179.1142,174.6043,170.7110,167.4178,164.6866),(5,NULL,'MET0003','TotW','20240315',222.5000,155.7515,155.7527,155.7547,155.7580,155.7635,155.7724,155.7866,155.8090,155.8435,155.8960,155.9744,156.0895,156.2557,156.4915,156.8205,157.2715,157.8790,158.6828,159.7275,161.0606,162.7306,164.7836,167.2591,170.1857,173.5757,177.4206,181.6863,186.3104,191.2007,196.2359,201.2695,206.1355,210.6571,214.6567,217.9679,220.4464,221.9807,222.5003,221.9812,220.4474,217.9699,214.6602,210.6633,206.1462,201.2875,196.2658,191.2495,186.3890,181.8110,177.6152,173.8749,170.6384,167.9334,165.7723,164.1580,163.0893,162.5661,162.5932,163.1822,164.3523,166.1280,168.5364,171.6012,175.3371,179.7420,184.7901,190.4252,196.5562,203.0542,209.7536,216.4562,222.9387,228.9641,234.2949,238.7086,242.0126,244.0579,244.7502,244.0575,242.0118,238.7072,234.2922,228.9594,222.9307,216.4427,209.7312,203.0175,196.4972,190.3317,184.6441,179.5176,174.9976,171.0955,167.7948,165.0575),(6,NULL,'MET0001','TotW','20240315',223.0000,156.1015,156.1027,156.1047,156.1080,156.1135,156.1224,156.1367,156.1591,156.1938,156.2463,156.3249,156.4403,156.6068,156.8432,157.1729,157.6249,158.2338,159.0394,160.0864,161.4225,163.0963,165.1539,167.6350,170.5681,173.9658,177.8193,182.0945,186.7291,191.6303,196.6769,201.7218,206.5988,211.1305,215.1391,218.4577,220.9418,222.4796,223.0003,222.4800,220.9428,218.4597,215.1426,211.1367,206.6094,201.7398,196.7068,191.6793,186.8079,182.2195,178.0144,174.2656,171.0218,168.3108,166.1449,164.5269,163.4558,162.9314,162.9586,163.5490,164.7216,166.5014,168.9151,171.9868,175.7311,180.1459,185.2053,190.8531,196.9979,203.5105,210.2250,216.9426,223.4397,229.4786,234.8214,239.2451,242.5564,244.6063,245.3002,244.6060,242.5557,239.2436,234.8187,229.4739,223.4317,216.9291,210.2025,203.4738,196.9387,190.7594,185.0590,179.9210,175.3909,171.4800,168.1719,165.4284),(7,NULL,'MET0002','TotW','20240315',223.5000,156.4515,156.4527,156.4547,156.4580,156.4635,156.4725,156.4868,156.5093,156.5440,156.5967,156.6754,156.7910,156.9579,157.1949,157.5253,157.9783,158.5885,159.3960,160.4453,161.7845,163.4620,165.5242,168.0109,170.9506,174.3558,178.2179,182.5028,187.1477,192.0600,197.1179,202.1741,207.0620,211.6038,215.6214,218.9475,221.4372,222.9784,223.5003,222.9788,221.4382,218.9495,215.6250,211.6101,207.0727,202.1922,197.1479,192.1090,187.2267,182.6281,178.4135,174.6564,171.4053,168.6881,166.5174,164.8958,163.8223,163.2967,163.3239,163.9157,165.0910,166.8747,169.2938,172.3724,176.1251,180.5498,185.6206,191.2811,197.4396,203.9668,210.6963,217.4290,223.9407,229.9931,235.3479,239.7815,243.1003,245.1547,245.8502,245.1544,243.0995,239.7800,235.3452,229.9884,223.9327,217.4155,210.6738,203.9300,197.3803,191.1871,185.4739,180.3244,175.7841,171.8645,168.5490,165.7994),(8,NULL,'MET0003','TotW','20240315',224.0000,156.8015,156.8027,156.8047,156.8080,156.8136,156.8225,156.8369,156.8594,156.8942,156.9470,157.0259,157.1418,157.3091,157.5465,157.8777,158.3318,158.9433,159.7526,160.8043,162.1464,163.8277,165.8945,168.3867,171.3330,174.7459,178.6166,182.9111,187.5664,192.4897,197.5589,202.6264,207.5252,212.0772,216.1038,219.4373,221.9326,223.4772,224.0003,223.4777,221.9336,219.4393,216.1074,212.0835,207.5359,202.6445,197.5889,192.5388,187.6456,183.0367,178.8126,175.0471,171.7887,169.0655,166.8899,165.2647,164.1888,163.6620,163.6893,164.2824,165.4603,167.2480,169.6726,172.7581,176.5191,180.9537,186.0359,191.7090,197.8813,204.4231,211.1677,217.9155,224.4417,230.5076,235.8744,240.3179,243.6441,245.7032,246.4003,245.7029,243.6434,240.3164,235.8717,230.5030,224.4336,217.9019,211.1451,204.3862,197.8219,191.6148,185.8889,180.7278,176.1774,172.2490,168.9260,166.1703),(9,NULL,'MET0001','TotW','20240315',224.5000,157.1515,157.1527,157.1547,157.1581,157.1636,157.1726,157.1870,157.2095,157.2444,157.2973,157.3764,157.4925,157.6602,157.8982,158.2301,158.6852,159.2981,160.1092,161.1632,162.5083,164.1934,166.2648,168.7626,171.7155,175.1359,179.0153,183.3194,187.9851,192.9193,197.9998,203.0787,207.9885,212.5506,216.5862,219.9272,222.4280,223.9761,224.5003,223.9765,222.4290,219.9291,216.5898,212.5569,207.9992,203.0968,198.0300,192.9686,188.0644,183.4452,179.2118,175.4378,172.1722,169.4429,167.2624,165.6336,164.5553,164.0274,164.0547,164.6491,165.8296,167.6213,170.0513,173.1437,176.9132,181.3577,186.4511,192.1369,198.3230,204.8794,211.6390,218.4019,224.9427,231.0222,236.4009,240.8543,244.1880,246.2516,246.9503,246.2513,244.1872,240.8528,236.3982,231.0175,224.9346,218.3883,211.6165,204.8424,198.2634,192.0425,186.3038,181.1313,176.5706,172.6335,169.3031,166.5412),(10,NULL,'MET0002','TotW','20240315',225.0000,157.5015,157.5027,157.5047,157.5081,157.5136,157.5226,157.5370,157.5597,157.5946,157.6477,157.7269,157.8433,158.0114,158.2499,158.5825,159.0386,159.6529,160.4657,161.5221,162.8703,164.5591,166.6351,169.1385,172.0979,175.5260,179.4140,183.7277,188.4038,193.3490,198.4408,203.5310,208.4517,213.0240,217.0686,220.4170,222.9233,224.4749,225.0003,224.4753,222.9244,220.4190,217.0721,213.0303,208.4624,203.5492,198.4710,193.3984,188.4833,183.8538,179.6109,175.8286,172.5556,169.8203,167.6349,166.0025,164.9217,164.3927,164.4201,165.0158,166.1990,167.9947,170.4300,173.5293,177.3072,181.7616,186.8664,192.5648,198.7647,205.3357,212.1104,218.8883,225.4436,231.5367,236.9274,241.3908,244.7318,246.8001,247.5003,246.7997,244.7311,241.3893,236.9247,231.5320,225.4356,218.8747,212.0878,205.2986,198.7050,192.4702,186.7187,181.5347,176.9639,173.0179,169.6802,166.9121);
/*!40000 ALTER TABLE `dwd_cust_analog_f` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cust_analog_i`
--

DROP TABLE IF EXISTS `dwd_cust_analog_i`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cust_analog_i` (
  `id` int NOT NULL AUTO_INCREMENT,
  `inst_id` varchar(255) DEFAULT NULL,
  `equip_src_id` varchar(255) DEFAULT NULL,
  `measuerment_type` varchar(255) DEFAULT NULL,
  `date` varchar(255) DEFAULT NULL,
  `V0000` decimal(20,4) DEFAULT NULL,
  `V0015` decimal(20,4) DEFAULT NULL,
  `V0030` decimal(20,4) DEFAULT NULL,
  `V0045` decimal(20,4) DEFAULT NULL,
  `V0100` decimal(20,4) DEFAULT NULL,
  `V0115` decimal(20,4) DEFAULT NULL,
  `V0130` decimal(20,4) DEFAULT NULL,
  `V0145` decimal(20,4) DEFAULT NULL,
  `V0200` decimal(20,4) DEFAULT NULL,
  `V0215` decimal(20,4) DEFAULT NULL,
  `V0230` decimal(20,4) DEFAULT NULL,
  `V0245` decimal(20,4) DEFAULT NULL,
  `V0300` decimal(20,4) DEFAULT NULL,
  `V0315` decimal(20,4) DEFAULT NULL,
  `V0330` decimal(20,4) DEFAULT NULL,
  `V0345` decimal(20,4) DEFAULT NULL,
  `V0400` decimal(20,4) DEFAULT NULL,
  `V0415` decimal(20,4) DEFAULT NULL,
  `V0430` decimal(20,4) DEFAULT NULL,
  `V0445` decimal(20,4) DEFAULT NULL,
  `V0500` decimal(20,4) DEFAULT NULL,
  `V0515` decimal(20,4) DEFAULT NULL,
  `V0530` decimal(20,4) DEFAULT NULL,
  `V0545` decimal(20,4) DEFAULT NULL,
  `V0600` decimal(20,4) DEFAULT NULL,
  `V0615` decimal(20,4) DEFAULT NULL,
  `V0630` decimal(20,4) DEFAULT NULL,
  `V0645` decimal(20,4) DEFAULT NULL,
  `V0700` decimal(20,4) DEFAULT NULL,
  `V0715` decimal(20,4) DEFAULT NULL,
  `V0730` decimal(20,4) DEFAULT NULL,
  `V0745` decimal(20,4) DEFAULT NULL,
  `V0800` decimal(20,4) DEFAULT NULL,
  `V0815` decimal(20,4) DEFAULT NULL,
  `V0830` decimal(20,4) DEFAULT NULL,
  `V0845` decimal(20,4) DEFAULT NULL,
  `V0900` decimal(20,4) DEFAULT NULL,
  `V0915` decimal(20,4) DEFAULT NULL,
  `V0930` decimal(20,4) DEFAULT NULL,
  `V0945` decimal(20,4) DEFAULT NULL,
  `V1000` decimal(20,4) DEFAULT NULL,
  `V1015` decimal(20,4) DEFAULT NULL,
  `V1030` decimal(20,4) DEFAULT NULL,
  `V1045` decimal(20,4) DEFAULT NULL,
  `V1100` decimal(20,4) DEFAULT NULL,
  `V1115` decimal(20,4) DEFAULT NULL,
  `V1130` decimal(20,4) DEFAULT NULL,
  `V1145` decimal(20,4) DEFAULT NULL,
  `V1200` decimal(20,4) DEFAULT NULL,
  `V1215` decimal(20,4) DEFAULT NULL,
  `V1230` decimal(20,4) DEFAULT NULL,
  `V1245` decimal(20,4) DEFAULT NULL,
  `V1300` decimal(20,4) DEFAULT NULL,
  `V1315` decimal(20,4) DEFAULT NULL,
  `V1330` decimal(20,4) DEFAULT NULL,
  `V1345` decimal(20,4) DEFAULT NULL,
  `V1400` decimal(20,4) DEFAULT NULL,
  `V1415` decimal(20,4) DEFAULT NULL,
  `V1430` decimal(20,4) DEFAULT NULL,
  `V1445` decimal(20,4) DEFAULT NULL,
  `V1500` decimal(20,4) DEFAULT NULL,
  `V1515` decimal(20,4) DEFAULT NULL,
  `V1530` decimal(20,4) DEFAULT NULL,
  `V1545` decimal(20,4) DEFAULT NULL,
  `V1600` decimal(20,4) DEFAULT NULL,
  `V1615` decimal(20,4) DEFAULT NULL,
  `V1630` decimal(20,4) DEFAULT NULL,
  `V1645` decimal(20,4) DEFAULT NULL,
  `V1700` decimal(20,4) DEFAULT NULL,
  `V1715` decimal(20,4) DEFAULT NULL,
  `V1730` decimal(20,4) DEFAULT NULL,
  `V1745` decimal(20,4) DEFAULT NULL,
  `V1800` decimal(20,4) DEFAULT NULL,
  `V1815` decimal(20,4) DEFAULT NULL,
  `V1830` decimal(20,4) DEFAULT NULL,
  `V1845` decimal(20,4) DEFAULT NULL,
  `V1900` decimal(20,4) DEFAULT NULL,
  `V1915` decimal(20,4) DEFAULT NULL,
  `V1930` decimal(20,4) DEFAULT NULL,
  `V1945` decimal(20,4) DEFAULT NULL,
  `V2000` decimal(20,4) DEFAULT NULL,
  `V2015` decimal(20,4) DEFAULT NULL,
  `V2030` decimal(20,4) DEFAULT NULL,
  `V2045` decimal(20,4) DEFAULT NULL,
  `V2100` decimal(20,4) DEFAULT NULL,
  `V2115` decimal(20,4) DEFAULT NULL,
  `V2130` decimal(20,4) DEFAULT NULL,
  `V2145` decimal(20,4) DEFAULT NULL,
  `V2200` decimal(20,4) DEFAULT NULL,
  `V2215` decimal(20,4) DEFAULT NULL,
  `V2230` decimal(20,4) DEFAULT NULL,
  `V2245` decimal(20,4) DEFAULT NULL,
  `V2300` decimal(20,4) DEFAULT NULL,
  `V2315` decimal(20,4) DEFAULT NULL,
  `V2330` decimal(20,4) DEFAULT NULL,
  `V2345` decimal(20,4) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cust_analog_i`
--

LOCK TABLES `dwd_cust_analog_i` WRITE;
/*!40000 ALTER TABLE `dwd_cust_analog_i` DISABLE KEYS */;
INSERT INTO `dwd_cust_analog_i` VALUES (1,'INS0001','MET0002','TotW','20240315',220.5000,154.3515,154.3527,154.3546,154.3579,154.3634,154.3722,154.3863,154.4085,154.4427,154.4947,154.5724,154.6864,154.8511,155.0849,155.4109,155.8578,156.4598,157.2564,158.2917,159.6129,161.2679,163.3024,165.7557,168.6559,172.0155,175.8258,180.0531,184.6357,189.4820,194.4720,199.4604,204.2826,208.7635,212.7272,216.0086,218.4649,219.9854,220.5003,219.9858,218.4659,216.0106,212.7307,208.7697,204.2932,199.4782,194.5016,189.5304,184.7136,180.1767,176.0187,172.3120,169.1045,166.4239,164.2822,162.6824,161.6233,161.1048,161.1317,161.7154,162.8750,164.6348,167.0214,170.0587,173.7610,178.1263,183.1291,188.7135,194.7894,201.2290,207.8682,214.5105,220.9348,226.9060,232.1889,236.5629,239.8372,241.8641,242.5502,241.8638,239.8364,236.5615,232.1862,226.9013,220.9269,214.4972,207.8460,201.1927,194.7309,188.6208,182.9843,177.9040,173.4246,169.5576,166.2866,163.5739),(2,'INS0002','MET0003','TotW','20240315',221.0000,154.7015,154.7027,154.7046,154.7079,154.7134,154.7222,154.7364,154.7586,154.7929,154.8450,154.9229,155.0372,155.2023,155.4365,155.7633,156.2113,156.8146,157.6130,158.6506,159.9748,161.6336,163.6727,166.1316,169.0384,172.4055,176.2245,180.4614,185.0544,189.9117,194.9130,199.9127,204.7459,209.2369,213.2096,216.4984,218.9603,220.4842,221.0003,220.4847,218.9613,216.5004,213.2131,209.2431,204.7564,199.9305,194.9426,189.9602,185.1325,180.5853,176.4178,172.7027,169.4880,166.8012,164.6548,163.0513,161.9898,161.4701,161.4970,162.0821,163.2443,165.0081,167.4002,170.4443,174.1550,178.5303,183.5443,189.1414,195.2311,201.6853,208.3396,214.9969,221.4358,227.4205,232.7154,237.0994,240.3811,242.4125,243.1002,242.4122,240.3803,237.0979,232.7127,227.4159,221.4278,214.9836,208.3173,201.6489,195.1725,189.0485,183.3993,178.3074,173.8178,169.9421,166.6636,163.9448),(3,'INS0003','MET0001','TotW','20240315',221.5000,155.0515,155.0527,155.0546,155.0579,155.0634,155.0723,155.0865,155.1087,155.1431,155.1954,155.2734,155.3880,155.5534,155.7882,156.1157,156.5647,157.1694,157.9696,159.0096,160.3367,161.9993,164.0430,166.5074,169.4208,172.7956,176.6232,180.8697,185.4730,190.3413,195.3540,200.3650,205.2091,209.7103,213.6919,216.9883,219.4556,220.9831,221.5003,220.9835,219.4567,216.9902,213.6955,209.7165,205.2197,200.3828,195.3837,190.3900,185.5513,180.9938,176.8170,173.0934,169.8714,167.1786,165.0273,163.4202,162.3563,161.8355,161.8624,162.4488,163.6136,165.3814,167.7789,170.8300,174.5491,178.9342,183.9596,189.5694,195.6728,202.1416,208.8109,215.4834,221.9367,227.9350,233.2419,237.6358,240.9249,242.9610,243.6502,242.9606,240.9241,237.6343,233.2392,227.9304,221.9288,215.4700,208.7886,202.1051,195.6140,189.4763,183.8142,178.7108,174.2111,170.3266,167.0407,164.3157),(4,'INS0001','MET0002','TotW','20240315',222.0000,155.4015,155.4027,155.4046,155.4080,155.4134,155.4223,155.4365,155.4589,155.4933,155.5457,155.6239,155.7387,155.9045,156.1399,156.4681,156.9181,157.5242,158.3262,159.3685,160.6987,162.3650,164.4133,166.8833,169.8033,173.1857,177.0219,181.2780,185.8917,190.7710,195.7949,200.8173,205.6723,210.1837,214.1743,217.4781,219.9510,221.4819,222.0003,221.4823,219.9521,217.4800,214.1779,210.1899,205.6829,200.8352,195.8247,190.8197,185.9702,181.4024,177.2161,173.4842,170.2549,167.5560,165.3998,163.7891,162.7228,162.2008,162.2278,162.8155,163.9830,165.7547,168.1576,171.2156,174.9431,179.3381,184.3748,189.9973,196.1145,202.5979,209.2823,215.9698,222.4377,228.4495,233.7684,238.1722,241.4688,243.5094,244.2002,243.5091,241.4680,238.1707,233.7657,228.4449,222.4298,215.9563,209.2599,202.5613,196.0556,189.9040,184.2291,179.1142,174.6043,170.7110,167.4178,164.6866),(5,'INS0002','MET0003','TotW','20240315',222.5000,155.7515,155.7527,155.7547,155.7580,155.7635,155.7724,155.7866,155.8090,155.8435,155.8960,155.9744,156.0895,156.2557,156.4915,156.8205,157.2715,157.8790,158.6828,159.7275,161.0606,162.7306,164.7836,167.2591,170.1857,173.5757,177.4206,181.6863,186.3104,191.2007,196.2359,201.2695,206.1355,210.6571,214.6567,217.9679,220.4464,221.9807,222.5003,221.9812,220.4474,217.9699,214.6602,210.6633,206.1462,201.2875,196.2658,191.2495,186.3890,181.8110,177.6152,173.8749,170.6384,167.9334,165.7723,164.1580,163.0893,162.5661,162.5932,163.1822,164.3523,166.1280,168.5364,171.6012,175.3371,179.7420,184.7901,190.4252,196.5562,203.0542,209.7536,216.4562,222.9387,228.9641,234.2949,238.7086,242.0126,244.0579,244.7502,244.0575,242.0118,238.7072,234.2922,228.9594,222.9307,216.4427,209.7312,203.0175,196.4972,190.3317,184.6441,179.5176,174.9976,171.0955,167.7948,165.0575),(6,'INS0003','MET0001','TotW','20240315',223.0000,156.1015,156.1027,156.1047,156.1080,156.1135,156.1224,156.1367,156.1591,156.1938,156.2463,156.3249,156.4403,156.6068,156.8432,157.1729,157.6249,158.2338,159.0394,160.0864,161.4225,163.0963,165.1539,167.6350,170.5681,173.9658,177.8193,182.0945,186.7291,191.6303,196.6769,201.7218,206.5988,211.1305,215.1391,218.4577,220.9418,222.4796,223.0003,222.4800,220.9428,218.4597,215.1426,211.1367,206.6094,201.7398,196.7068,191.6793,186.8079,182.2195,178.0144,174.2656,171.0218,168.3108,166.1449,164.5269,163.4558,162.9314,162.9586,163.5490,164.7216,166.5014,168.9151,171.9868,175.7311,180.1459,185.2053,190.8531,196.9979,203.5105,210.2250,216.9426,223.4397,229.4786,234.8214,239.2451,242.5564,244.6063,245.3002,244.6060,242.5557,239.2436,234.8187,229.4739,223.4317,216.9291,210.2025,203.4738,196.9387,190.7594,185.0590,179.9210,175.3909,171.4800,168.1719,165.4284),(7,'INS0001','MET0002','TotW','20240315',223.5000,156.4515,156.4527,156.4547,156.4580,156.4635,156.4725,156.4868,156.5093,156.5440,156.5967,156.6754,156.7910,156.9579,157.1949,157.5253,157.9783,158.5885,159.3960,160.4453,161.7845,163.4620,165.5242,168.0109,170.9506,174.3558,178.2179,182.5028,187.1477,192.0600,197.1179,202.1741,207.0620,211.6038,215.6214,218.9475,221.4372,222.9784,223.5003,222.9788,221.4382,218.9495,215.6250,211.6101,207.0727,202.1922,197.1479,192.1090,187.2267,182.6281,178.4135,174.6564,171.4053,168.6881,166.5174,164.8958,163.8223,163.2967,163.3239,163.9157,165.0910,166.8747,169.2938,172.3724,176.1251,180.5498,185.6206,191.2811,197.4396,203.9668,210.6963,217.4290,223.9407,229.9931,235.3479,239.7815,243.1003,245.1547,245.8502,245.1544,243.0995,239.7800,235.3452,229.9884,223.9327,217.4155,210.6738,203.9300,197.3803,191.1871,185.4739,180.3244,175.7841,171.8645,168.5490,165.7994),(8,'INS0002','MET0003','TotW','20240315',224.0000,156.8015,156.8027,156.8047,156.8080,156.8136,156.8225,156.8369,156.8594,156.8942,156.9470,157.0259,157.1418,157.3091,157.5465,157.8777,158.3318,158.9433,159.7526,160.8043,162.1464,163.8277,165.8945,168.3867,171.3330,174.7459,178.6166,182.9111,187.5664,192.4897,197.5589,202.6264,207.5252,212.0772,216.1038,219.4373,221.9326,223.4772,224.0003,223.4777,221.9336,219.4393,216.1074,212.0835,207.5359,202.6445,197.5889,192.5388,187.6456,183.0367,178.8126,175.0471,171.7887,169.0655,166.8899,165.2647,164.1888,163.6620,163.6893,164.2824,165.4603,167.2480,169.6726,172.7581,176.5191,180.9537,186.0359,191.7090,197.8813,204.4231,211.1677,217.9155,224.4417,230.5076,235.8744,240.3179,243.6441,245.7032,246.4003,245.7029,243.6434,240.3164,235.8717,230.5030,224.4336,217.9019,211.1451,204.3862,197.8219,191.6148,185.8889,180.7278,176.1774,172.2490,168.9260,166.1703),(9,'INS0003','MET0001','TotW','20240315',224.5000,157.1515,157.1527,157.1547,157.1581,157.1636,157.1726,157.1870,157.2095,157.2444,157.2973,157.3764,157.4925,157.6602,157.8982,158.2301,158.6852,159.2981,160.1092,161.1632,162.5083,164.1934,166.2648,168.7626,171.7155,175.1359,179.0153,183.3194,187.9851,192.9193,197.9998,203.0787,207.9885,212.5506,216.5862,219.9272,222.4280,223.9761,224.5003,223.9765,222.4290,219.9291,216.5898,212.5569,207.9992,203.0968,198.0300,192.9686,188.0644,183.4452,179.2118,175.4378,172.1722,169.4429,167.2624,165.6336,164.5553,164.0274,164.0547,164.6491,165.8296,167.6213,170.0513,173.1437,176.9132,181.3577,186.4511,192.1369,198.3230,204.8794,211.6390,218.4019,224.9427,231.0222,236.4009,240.8543,244.1880,246.2516,246.9503,246.2513,244.1872,240.8528,236.3982,231.0175,224.9346,218.3883,211.6165,204.8424,198.2634,192.0425,186.3038,181.1313,176.5706,172.6335,169.3031,166.5412),(10,'INS0001','MET0002','TotW','20240315',225.0000,157.5015,157.5027,157.5047,157.5081,157.5136,157.5226,157.5370,157.5597,157.5946,157.6477,157.7269,157.8433,158.0114,158.2499,158.5825,159.0386,159.6529,160.4657,161.5221,162.8703,164.5591,166.6351,169.1385,172.0979,175.5260,179.4140,183.7277,188.4038,193.3490,198.4408,203.5310,208.4517,213.0240,217.0686,220.4170,222.9233,224.4749,225.0003,224.4753,222.9244,220.4190,217.0721,213.0303,208.4624,203.5492,198.4710,193.3984,188.4833,183.8538,179.6109,175.8286,172.5556,169.8203,167.6349,166.0025,164.9217,164.3927,164.4201,165.0158,166.1990,167.9947,170.4300,173.5293,177.3072,181.7616,186.8664,192.5648,198.7647,205.3357,212.1104,218.8883,225.4436,231.5367,236.9274,241.3908,244.7318,246.8001,247.5003,246.7997,244.7311,241.3893,236.9247,231.5320,225.4356,218.8747,212.0878,205.2986,198.7050,192.4702,186.7187,181.5347,176.9639,173.0179,169.6802,166.9121);
/*!40000 ALTER TABLE `dwd_cust_analog_i` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cust_analog_p`
--

DROP TABLE IF EXISTS `dwd_cust_analog_p`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cust_analog_p` (
  `id` int NOT NULL AUTO_INCREMENT,
  `inst_id` varchar(255) DEFAULT NULL,
  `equip_src_id` varchar(255) DEFAULT NULL,
  `measuerment_type` varchar(255) DEFAULT NULL,
  `date` varchar(255) DEFAULT NULL,
  `V0000` decimal(20,4) DEFAULT NULL,
  `V0015` decimal(20,4) DEFAULT NULL,
  `V0030` decimal(20,4) DEFAULT NULL,
  `V0045` decimal(20,4) DEFAULT NULL,
  `V0100` decimal(20,4) DEFAULT NULL,
  `V0115` decimal(20,4) DEFAULT NULL,
  `V0130` decimal(20,4) DEFAULT NULL,
  `V0145` decimal(20,4) DEFAULT NULL,
  `V0200` decimal(20,4) DEFAULT NULL,
  `V0215` decimal(20,4) DEFAULT NULL,
  `V0230` decimal(20,4) DEFAULT NULL,
  `V0245` decimal(20,4) DEFAULT NULL,
  `V0300` decimal(20,4) DEFAULT NULL,
  `V0315` decimal(20,4) DEFAULT NULL,
  `V0330` decimal(20,4) DEFAULT NULL,
  `V0345` decimal(20,4) DEFAULT NULL,
  `V0400` decimal(20,4) DEFAULT NULL,
  `V0415` decimal(20,4) DEFAULT NULL,
  `V0430` decimal(20,4) DEFAULT NULL,
  `V0445` decimal(20,4) DEFAULT NULL,
  `V0500` decimal(20,4) DEFAULT NULL,
  `V0515` decimal(20,4) DEFAULT NULL,
  `V0530` decimal(20,4) DEFAULT NULL,
  `V0545` decimal(20,4) DEFAULT NULL,
  `V0600` decimal(20,4) DEFAULT NULL,
  `V0615` decimal(20,4) DEFAULT NULL,
  `V0630` decimal(20,4) DEFAULT NULL,
  `V0645` decimal(20,4) DEFAULT NULL,
  `V0700` decimal(20,4) DEFAULT NULL,
  `V0715` decimal(20,4) DEFAULT NULL,
  `V0730` decimal(20,4) DEFAULT NULL,
  `V0745` decimal(20,4) DEFAULT NULL,
  `V0800` decimal(20,4) DEFAULT NULL,
  `V0815` decimal(20,4) DEFAULT NULL,
  `V0830` decimal(20,4) DEFAULT NULL,
  `V0845` decimal(20,4) DEFAULT NULL,
  `V0900` decimal(20,4) DEFAULT NULL,
  `V0915` decimal(20,4) DEFAULT NULL,
  `V0930` decimal(20,4) DEFAULT NULL,
  `V0945` decimal(20,4) DEFAULT NULL,
  `V1000` decimal(20,4) DEFAULT NULL,
  `V1015` decimal(20,4) DEFAULT NULL,
  `V1030` decimal(20,4) DEFAULT NULL,
  `V1045` decimal(20,4) DEFAULT NULL,
  `V1100` decimal(20,4) DEFAULT NULL,
  `V1115` decimal(20,4) DEFAULT NULL,
  `V1130` decimal(20,4) DEFAULT NULL,
  `V1145` decimal(20,4) DEFAULT NULL,
  `V1200` decimal(20,4) DEFAULT NULL,
  `V1215` decimal(20,4) DEFAULT NULL,
  `V1230` decimal(20,4) DEFAULT NULL,
  `V1245` decimal(20,4) DEFAULT NULL,
  `V1300` decimal(20,4) DEFAULT NULL,
  `V1315` decimal(20,4) DEFAULT NULL,
  `V1330` decimal(20,4) DEFAULT NULL,
  `V1345` decimal(20,4) DEFAULT NULL,
  `V1400` decimal(20,4) DEFAULT NULL,
  `V1415` decimal(20,4) DEFAULT NULL,
  `V1430` decimal(20,4) DEFAULT NULL,
  `V1445` decimal(20,4) DEFAULT NULL,
  `V1500` decimal(20,4) DEFAULT NULL,
  `V1515` decimal(20,4) DEFAULT NULL,
  `V1530` decimal(20,4) DEFAULT NULL,
  `V1545` decimal(20,4) DEFAULT NULL,
  `V1600` decimal(20,4) DEFAULT NULL,
  `V1615` decimal(20,4) DEFAULT NULL,
  `V1630` decimal(20,4) DEFAULT NULL,
  `V1645` decimal(20,4) DEFAULT NULL,
  `V1700` decimal(20,4) DEFAULT NULL,
  `V1715` decimal(20,4) DEFAULT NULL,
  `V1730` decimal(20,4) DEFAULT NULL,
  `V1745` decimal(20,4) DEFAULT NULL,
  `V1800` decimal(20,4) DEFAULT NULL,
  `V1815` decimal(20,4) DEFAULT NULL,
  `V1830` decimal(20,4) DEFAULT NULL,
  `V1845` decimal(20,4) DEFAULT NULL,
  `V1900` decimal(20,4) DEFAULT NULL,
  `V1915` decimal(20,4) DEFAULT NULL,
  `V1930` decimal(20,4) DEFAULT NULL,
  `V1945` decimal(20,4) DEFAULT NULL,
  `V2000` decimal(20,4) DEFAULT NULL,
  `V2015` decimal(20,4) DEFAULT NULL,
  `V2030` decimal(20,4) DEFAULT NULL,
  `V2045` decimal(20,4) DEFAULT NULL,
  `V2100` decimal(20,4) DEFAULT NULL,
  `V2115` decimal(20,4) DEFAULT NULL,
  `V2130` decimal(20,4) DEFAULT NULL,
  `V2145` decimal(20,4) DEFAULT NULL,
  `V2200` decimal(20,4) DEFAULT NULL,
  `V2215` decimal(20,4) DEFAULT NULL,
  `V2230` decimal(20,4) DEFAULT NULL,
  `V2245` decimal(20,4) DEFAULT NULL,
  `V2300` decimal(20,4) DEFAULT NULL,
  `V2315` decimal(20,4) DEFAULT NULL,
  `V2330` decimal(20,4) DEFAULT NULL,
  `V2345` decimal(20,4) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cust_analog_p`
--

LOCK TABLES `dwd_cust_analog_p` WRITE;
/*!40000 ALTER TABLE `dwd_cust_analog_p` DISABLE KEYS */;
INSERT INTO `dwd_cust_analog_p` VALUES (1,NULL,'MET0002','TotW','20240315',90.0000,63.0006,63.0011,63.0019,63.0032,63.0055,63.0091,63.0148,63.0239,63.0378,63.0591,63.0908,63.1373,63.2045,63.2999,63.4330,63.6154,63.8612,64.1863,64.6089,65.1481,65.8236,66.6541,67.6554,68.8392,70.2104,71.7656,73.4911,75.3615,77.3396,79.3763,81.4124,83.3807,85.2096,86.8274,88.1668,89.1693,89.7900,90.0001,89.7901,89.1698,88.1676,86.8289,85.2121,83.3850,81.4197,79.3884,77.3593,75.3933,73.5415,71.8444,70.3314,69.0223,67.9281,67.0540,66.4010,65.9687,65.7571,65.7680,66.0063,66.4796,67.1979,68.1720,69.4117,70.9229,72.7046,74.7466,77.0259,79.5059,82.1343,84.8442,87.5553,90.1775,92.6147,94.7710,96.5563,97.8927,98.7200,99.0001,98.7199,97.8924,96.5557,94.7699,92.6128,90.1742,87.5499,84.8351,82.1195,79.4820,76.9881,74.6875,72.6139,70.7855,69.2072,67.8721,66.7648),(2,NULL,'MET0003','TotW','20240315',70.0000,49.0005,49.0008,49.0015,49.0025,49.0042,49.0070,49.0115,49.0186,49.0294,49.0459,49.0706,49.1068,49.1591,49.2333,49.3368,49.4787,49.6698,49.9227,50.2513,50.6707,51.1962,51.8420,52.6209,53.5416,54.6081,55.8177,57.1597,58.6145,60.1530,61.7371,63.3208,64.8516,66.2741,67.5324,68.5742,69.3539,69.8366,70.0001,69.8368,69.3543,68.5748,67.5336,66.2761,64.8550,63.3264,61.7465,60.1684,58.6392,57.1990,55.8790,54.7022,53.6840,52.8330,52.1531,51.6452,51.3090,51.1444,51.1529,51.3382,51.7063,52.2650,53.0227,53.9869,55.1622,56.5480,58.1362,59.9091,61.8379,63.8822,65.9899,68.0986,70.1380,72.0336,73.7108,75.0993,76.1388,76.7822,77.0001,76.7821,76.1386,75.0989,73.7099,72.0322,70.1355,68.0943,65.9829,63.8707,61.8193,59.8796,58.0903,56.4775,55.0554,53.8278,52.7894,51.9282),(3,NULL,'MET0001','TotW','20240315',180.0000,126.0012,126.0022,126.0038,126.0065,126.0109,126.0181,126.0296,126.0477,126.0757,126.1181,126.1815,126.2746,126.4091,126.5999,126.8660,127.2309,127.7223,128.3726,129.2177,130.2962,131.6473,133.3081,135.3108,137.6783,140.4208,143.5312,146.9821,150.7230,154.6792,158.7527,162.8248,166.7613,170.4192,173.6549,176.3336,178.3387,179.5799,180.0003,179.5803,178.3395,176.3352,173.6577,170.4242,166.7700,162.8393,158.7768,154.7187,150.7866,147.0830,143.6887,140.6628,138.0445,135.8562,134.1080,132.8020,131.9374,131.5141,131.5361,132.0126,132.9592,134.3957,136.3440,138.8234,141.8457,145.4093,149.4931,154.0519,159.0117,164.2685,169.6883,175.1106,180.3549,185.2294,189.5419,193.1126,195.7855,197.4401,198.0002,197.4398,195.7848,193.1114,189.5398,185.2256,180.3485,175.0997,169.6702,164.2389,158.9640,153.9762,149.3750,145.2277,141.5711,138.4144,135.7441,133.5297),(4,NULL,'MET0002','TotW','20240315',90.0000,63.0006,63.0011,63.0019,63.0032,63.0055,63.0091,63.0148,63.0239,63.0378,63.0591,63.0908,63.1373,63.2045,63.2999,63.4330,63.6154,63.8612,64.1863,64.6089,65.1481,65.8236,66.6541,67.6554,68.8392,70.2104,71.7656,73.4911,75.3615,77.3396,79.3763,81.4124,83.3807,85.2096,86.8274,88.1668,89.1693,89.7900,90.0001,89.7901,89.1698,88.1676,86.8289,85.2121,83.3850,81.4197,79.3884,77.3593,75.3933,73.5415,71.8444,70.3314,69.0223,67.9281,67.0540,66.4010,65.9687,65.7571,65.7680,66.0063,66.4796,67.1979,68.1720,69.4117,70.9229,72.7046,74.7466,77.0259,79.5059,82.1343,84.8442,87.5553,90.1775,92.6147,94.7710,96.5563,97.8927,98.7200,99.0001,98.7199,97.8924,96.5557,94.7699,92.6128,90.1742,87.5499,84.8351,82.1195,79.4820,76.9881,74.6875,72.6139,70.7855,69.2072,67.8721,66.7648),(5,NULL,'MET0003','TotW','20240315',70.0000,49.0005,49.0008,49.0015,49.0025,49.0042,49.0070,49.0115,49.0186,49.0294,49.0459,49.0706,49.1068,49.1591,49.2333,49.3368,49.4787,49.6698,49.9227,50.2513,50.6707,51.1962,51.8420,52.6209,53.5416,54.6081,55.8177,57.1597,58.6145,60.1530,61.7371,63.3208,64.8516,66.2741,67.5324,68.5742,69.3539,69.8366,70.0001,69.8368,69.3543,68.5748,67.5336,66.2761,64.8550,63.3264,61.7465,60.1684,58.6392,57.1990,55.8790,54.7022,53.6840,52.8330,52.1531,51.6452,51.3090,51.1444,51.1529,51.3382,51.7063,52.2650,53.0227,53.9869,55.1622,56.5480,58.1362,59.9091,61.8379,63.8822,65.9899,68.0986,70.1380,72.0336,73.7108,75.0993,76.1388,76.7822,77.0001,76.7821,76.1386,75.0989,73.7099,72.0322,70.1355,68.0943,65.9829,63.8707,61.8193,59.8796,58.0903,56.4775,55.0554,53.8278,52.7894,51.9282),(6,NULL,'MET0001','TotW','20240315',180.0000,126.0012,126.0022,126.0038,126.0065,126.0109,126.0181,126.0296,126.0477,126.0757,126.1181,126.1815,126.2746,126.4091,126.5999,126.8660,127.2309,127.7223,128.3726,129.2177,130.2962,131.6473,133.3081,135.3108,137.6783,140.4208,143.5312,146.9821,150.7230,154.6792,158.7527,162.8248,166.7613,170.4192,173.6549,176.3336,178.3387,179.5799,180.0003,179.5803,178.3395,176.3352,173.6577,170.4242,166.7700,162.8393,158.7768,154.7187,150.7866,147.0830,143.6887,140.6628,138.0445,135.8562,134.1080,132.8020,131.9374,131.5141,131.5361,132.0126,132.9592,134.3957,136.3440,138.8234,141.8457,145.4093,149.4931,154.0519,159.0117,164.2685,169.6883,175.1106,180.3549,185.2294,189.5419,193.1126,195.7855,197.4401,198.0002,197.4398,195.7848,193.1114,189.5398,185.2256,180.3485,175.0997,169.6702,164.2389,158.9640,153.9762,149.3750,145.2277,141.5711,138.4144,135.7441,133.5297),(7,NULL,'MET0002','TotW','20240315',90.0000,63.0006,63.0011,63.0019,63.0032,63.0055,63.0091,63.0148,63.0239,63.0378,63.0591,63.0908,63.1373,63.2045,63.2999,63.4330,63.6154,63.8612,64.1863,64.6089,65.1481,65.8236,66.6541,67.6554,68.8392,70.2104,71.7656,73.4911,75.3615,77.3396,79.3763,81.4124,83.3807,85.2096,86.8274,88.1668,89.1693,89.7900,90.0001,89.7901,89.1698,88.1676,86.8289,85.2121,83.3850,81.4197,79.3884,77.3593,75.3933,73.5415,71.8444,70.3314,69.0223,67.9281,67.0540,66.4010,65.9687,65.7571,65.7680,66.0063,66.4796,67.1979,68.1720,69.4117,70.9229,72.7046,74.7466,77.0259,79.5059,82.1343,84.8442,87.5553,90.1775,92.6147,94.7710,96.5563,97.8927,98.7200,99.0001,98.7199,97.8924,96.5557,94.7699,92.6128,90.1742,87.5499,84.8351,82.1195,79.4820,76.9881,74.6875,72.6139,70.7855,69.2072,67.8721,66.7648),(8,NULL,'MET0003','TotW','20240315',70.0000,49.0005,49.0008,49.0015,49.0025,49.0042,49.0070,49.0115,49.0186,49.0294,49.0459,49.0706,49.1068,49.1591,49.2333,49.3368,49.4787,49.6698,49.9227,50.2513,50.6707,51.1962,51.8420,52.6209,53.5416,54.6081,55.8177,57.1597,58.6145,60.1530,61.7371,63.3208,64.8516,66.2741,67.5324,68.5742,69.3539,69.8366,70.0001,69.8368,69.3543,68.5748,67.5336,66.2761,64.8550,63.3264,61.7465,60.1684,58.6392,57.1990,55.8790,54.7022,53.6840,52.8330,52.1531,51.6452,51.3090,51.1444,51.1529,51.3382,51.7063,52.2650,53.0227,53.9869,55.1622,56.5480,58.1362,59.9091,61.8379,63.8822,65.9899,68.0986,70.1380,72.0336,73.7108,75.0993,76.1388,76.7822,77.0001,76.7821,76.1386,75.0989,73.7099,72.0322,70.1355,68.0943,65.9829,63.8707,61.8193,59.8796,58.0903,56.4775,55.0554,53.8278,52.7894,51.9282),(9,NULL,'MET0001','TotW','20240315',180.0000,126.0012,126.0022,126.0038,126.0065,126.0109,126.0181,126.0296,126.0477,126.0757,126.1181,126.1815,126.2746,126.4091,126.5999,126.8660,127.2309,127.7223,128.3726,129.2177,130.2962,131.6473,133.3081,135.3108,137.6783,140.4208,143.5312,146.9821,150.7230,154.6792,158.7527,162.8248,166.7613,170.4192,173.6549,176.3336,178.3387,179.5799,180.0003,179.5803,178.3395,176.3352,173.6577,170.4242,166.7700,162.8393,158.7768,154.7187,150.7866,147.0830,143.6887,140.6628,138.0445,135.8562,134.1080,132.8020,131.9374,131.5141,131.5361,132.0126,132.9592,134.3957,136.3440,138.8234,141.8457,145.4093,149.4931,154.0519,159.0117,164.2685,169.6883,175.1106,180.3549,185.2294,189.5419,193.1126,195.7855,197.4401,198.0002,197.4398,195.7848,193.1114,189.5398,185.2256,180.3485,175.0997,169.6702,164.2389,158.9640,153.9762,149.3750,145.2277,141.5711,138.4144,135.7441,133.5297),(10,NULL,'MET0002','TotW','20240315',90.0000,63.0006,63.0011,63.0019,63.0032,63.0055,63.0091,63.0148,63.0239,63.0378,63.0591,63.0908,63.1373,63.2045,63.2999,63.4330,63.6154,63.8612,64.1863,64.6089,65.1481,65.8236,66.6541,67.6554,68.8392,70.2104,71.7656,73.4911,75.3615,77.3396,79.3763,81.4124,83.3807,85.2096,86.8274,88.1668,89.1693,89.7900,90.0001,89.7901,89.1698,88.1676,86.8289,85.2121,83.3850,81.4197,79.3884,77.3593,75.3933,73.5415,71.8444,70.3314,69.0223,67.9281,67.0540,66.4010,65.9687,65.7571,65.7680,66.0063,66.4796,67.1979,68.1720,69.4117,70.9229,72.7046,74.7466,77.0259,79.5059,82.1343,84.8442,87.5553,90.1775,92.6147,94.7710,96.5563,97.8927,98.7200,99.0001,98.7199,97.8924,96.5557,94.7699,92.6128,90.1742,87.5499,84.8351,82.1195,79.4820,76.9881,74.6875,72.6139,70.7855,69.2072,67.8721,66.7648);
/*!40000 ALTER TABLE `dwd_cust_analog_p` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_cust_analog_u`
--

DROP TABLE IF EXISTS `dwd_cust_analog_u`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_cust_analog_u` (
  `id` int NOT NULL AUTO_INCREMENT,
  `inst_id` varchar(255) DEFAULT NULL,
  `equip_src_id` varchar(255) DEFAULT NULL,
  `measuerment_type` varchar(255) DEFAULT NULL,
  `date` varchar(255) DEFAULT NULL,
  `V0000` decimal(20,4) DEFAULT NULL,
  `V0015` decimal(20,4) DEFAULT NULL,
  `V0030` decimal(20,4) DEFAULT NULL,
  `V0045` decimal(20,4) DEFAULT NULL,
  `V0100` decimal(20,4) DEFAULT NULL,
  `V0115` decimal(20,4) DEFAULT NULL,
  `V0130` decimal(20,4) DEFAULT NULL,
  `V0145` decimal(20,4) DEFAULT NULL,
  `V0200` decimal(20,4) DEFAULT NULL,
  `V0215` decimal(20,4) DEFAULT NULL,
  `V0230` decimal(20,4) DEFAULT NULL,
  `V0245` decimal(20,4) DEFAULT NULL,
  `V0300` decimal(20,4) DEFAULT NULL,
  `V0315` decimal(20,4) DEFAULT NULL,
  `V0330` decimal(20,4) DEFAULT NULL,
  `V0345` decimal(20,4) DEFAULT NULL,
  `V0400` decimal(20,4) DEFAULT NULL,
  `V0415` decimal(20,4) DEFAULT NULL,
  `V0430` decimal(20,4) DEFAULT NULL,
  `V0445` decimal(20,4) DEFAULT NULL,
  `V0500` decimal(20,4) DEFAULT NULL,
  `V0515` decimal(20,4) DEFAULT NULL,
  `V0530` decimal(20,4) DEFAULT NULL,
  `V0545` decimal(20,4) DEFAULT NULL,
  `V0600` decimal(20,4) DEFAULT NULL,
  `V0615` decimal(20,4) DEFAULT NULL,
  `V0630` decimal(20,4) DEFAULT NULL,
  `V0645` decimal(20,4) DEFAULT NULL,
  `V0700` decimal(20,4) DEFAULT NULL,
  `V0715` decimal(20,4) DEFAULT NULL,
  `V0730` decimal(20,4) DEFAULT NULL,
  `V0745` decimal(20,4) DEFAULT NULL,
  `V0800` decimal(20,4) DEFAULT NULL,
  `V0815` decimal(20,4) DEFAULT NULL,
  `V0830` decimal(20,4) DEFAULT NULL,
  `V0845` decimal(20,4) DEFAULT NULL,
  `V0900` decimal(20,4) DEFAULT NULL,
  `V0915` decimal(20,4) DEFAULT NULL,
  `V0930` decimal(20,4) DEFAULT NULL,
  `V0945` decimal(20,4) DEFAULT NULL,
  `V1000` decimal(20,4) DEFAULT NULL,
  `V1015` decimal(20,4) DEFAULT NULL,
  `V1030` decimal(20,4) DEFAULT NULL,
  `V1045` decimal(20,4) DEFAULT NULL,
  `V1100` decimal(20,4) DEFAULT NULL,
  `V1115` decimal(20,4) DEFAULT NULL,
  `V1130` decimal(20,4) DEFAULT NULL,
  `V1145` decimal(20,4) DEFAULT NULL,
  `V1200` decimal(20,4) DEFAULT NULL,
  `V1215` decimal(20,4) DEFAULT NULL,
  `V1230` decimal(20,4) DEFAULT NULL,
  `V1245` decimal(20,4) DEFAULT NULL,
  `V1300` decimal(20,4) DEFAULT NULL,
  `V1315` decimal(20,4) DEFAULT NULL,
  `V1330` decimal(20,4) DEFAULT NULL,
  `V1345` decimal(20,4) DEFAULT NULL,
  `V1400` decimal(20,4) DEFAULT NULL,
  `V1415` decimal(20,4) DEFAULT NULL,
  `V1430` decimal(20,4) DEFAULT NULL,
  `V1445` decimal(20,4) DEFAULT NULL,
  `V1500` decimal(20,4) DEFAULT NULL,
  `V1515` decimal(20,4) DEFAULT NULL,
  `V1530` decimal(20,4) DEFAULT NULL,
  `V1545` decimal(20,4) DEFAULT NULL,
  `V1600` decimal(20,4) DEFAULT NULL,
  `V1615` decimal(20,4) DEFAULT NULL,
  `V1630` decimal(20,4) DEFAULT NULL,
  `V1645` decimal(20,4) DEFAULT NULL,
  `V1700` decimal(20,4) DEFAULT NULL,
  `V1715` decimal(20,4) DEFAULT NULL,
  `V1730` decimal(20,4) DEFAULT NULL,
  `V1745` decimal(20,4) DEFAULT NULL,
  `V1800` decimal(20,4) DEFAULT NULL,
  `V1815` decimal(20,4) DEFAULT NULL,
  `V1830` decimal(20,4) DEFAULT NULL,
  `V1845` decimal(20,4) DEFAULT NULL,
  `V1900` decimal(20,4) DEFAULT NULL,
  `V1915` decimal(20,4) DEFAULT NULL,
  `V1930` decimal(20,4) DEFAULT NULL,
  `V1945` decimal(20,4) DEFAULT NULL,
  `V2000` decimal(20,4) DEFAULT NULL,
  `V2015` decimal(20,4) DEFAULT NULL,
  `V2030` decimal(20,4) DEFAULT NULL,
  `V2045` decimal(20,4) DEFAULT NULL,
  `V2100` decimal(20,4) DEFAULT NULL,
  `V2115` decimal(20,4) DEFAULT NULL,
  `V2130` decimal(20,4) DEFAULT NULL,
  `V2145` decimal(20,4) DEFAULT NULL,
  `V2200` decimal(20,4) DEFAULT NULL,
  `V2215` decimal(20,4) DEFAULT NULL,
  `V2230` decimal(20,4) DEFAULT NULL,
  `V2245` decimal(20,4) DEFAULT NULL,
  `V2300` decimal(20,4) DEFAULT NULL,
  `V2315` decimal(20,4) DEFAULT NULL,
  `V2330` decimal(20,4) DEFAULT NULL,
  `V2345` decimal(20,4) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_cust_analog_u`
--

LOCK TABLES `dwd_cust_analog_u` WRITE;
/*!40000 ALTER TABLE `dwd_cust_analog_u` DISABLE KEYS */;
INSERT INTO `dwd_cust_analog_u` VALUES (1,NULL,'MET0002','TotW','20240315',220.5000,154.3515,154.3527,154.3546,154.3579,154.3634,154.3722,154.3863,154.4085,154.4427,154.4947,154.5724,154.6864,154.8511,155.0849,155.4109,155.8578,156.4598,157.2564,158.2917,159.6129,161.2679,163.3024,165.7557,168.6559,172.0155,175.8258,180.0531,184.6357,189.4820,194.4720,199.4604,204.2826,208.7635,212.7272,216.0086,218.4649,219.9854,220.5003,219.9858,218.4659,216.0106,212.7307,208.7697,204.2932,199.4782,194.5016,189.5304,184.7136,180.1767,176.0187,172.3120,169.1045,166.4239,164.2822,162.6824,161.6233,161.1048,161.1317,161.7154,162.8750,164.6348,167.0214,170.0587,173.7610,178.1263,183.1291,188.7135,194.7894,201.2290,207.8682,214.5105,220.9348,226.9060,232.1889,236.5629,239.8372,241.8641,242.5502,241.8638,239.8364,236.5615,232.1862,226.9013,220.9269,214.4972,207.8460,201.1927,194.7309,188.6208,182.9843,177.9040,173.4246,169.5576,166.2866,163.5739),(2,NULL,'MET0003','TotW','20240315',221.0000,154.7015,154.7027,154.7046,154.7079,154.7134,154.7222,154.7364,154.7586,154.7929,154.8450,154.9229,155.0372,155.2023,155.4365,155.7633,156.2113,156.8146,157.6130,158.6506,159.9748,161.6336,163.6727,166.1316,169.0384,172.4055,176.2245,180.4614,185.0544,189.9117,194.9130,199.9127,204.7459,209.2369,213.2096,216.4984,218.9603,220.4842,221.0003,220.4847,218.9613,216.5004,213.2131,209.2431,204.7564,199.9305,194.9426,189.9602,185.1325,180.5853,176.4178,172.7027,169.4880,166.8012,164.6548,163.0513,161.9898,161.4701,161.4970,162.0821,163.2443,165.0081,167.4002,170.4443,174.1550,178.5303,183.5443,189.1414,195.2311,201.6853,208.3396,214.9969,221.4358,227.4205,232.7154,237.0994,240.3811,242.4125,243.1002,242.4122,240.3803,237.0979,232.7127,227.4159,221.4278,214.9836,208.3173,201.6489,195.1725,189.0485,183.3993,178.3074,173.8178,169.9421,166.6636,163.9448),(3,NULL,'MET0001','TotW','20240315',221.5000,155.0515,155.0527,155.0546,155.0579,155.0634,155.0723,155.0865,155.1087,155.1431,155.1954,155.2734,155.3880,155.5534,155.7882,156.1157,156.5647,157.1694,157.9696,159.0096,160.3367,161.9993,164.0430,166.5074,169.4208,172.7956,176.6232,180.8697,185.4730,190.3413,195.3540,200.3650,205.2091,209.7103,213.6919,216.9883,219.4556,220.9831,221.5003,220.9835,219.4567,216.9902,213.6955,209.7165,205.2197,200.3828,195.3837,190.3900,185.5513,180.9938,176.8170,173.0934,169.8714,167.1786,165.0273,163.4202,162.3563,161.8355,161.8624,162.4488,163.6136,165.3814,167.7789,170.8300,174.5491,178.9342,183.9596,189.5694,195.6728,202.1416,208.8109,215.4834,221.9367,227.9350,233.2419,237.6358,240.9249,242.9610,243.6502,242.9606,240.9241,237.6343,233.2392,227.9304,221.9288,215.4700,208.7886,202.1051,195.6140,189.4763,183.8142,178.7108,174.2111,170.3266,167.0407,164.3157),(4,NULL,'MET0002','TotW','20240315',222.0000,155.4015,155.4027,155.4046,155.4080,155.4134,155.4223,155.4365,155.4589,155.4933,155.5457,155.6239,155.7387,155.9045,156.1399,156.4681,156.9181,157.5242,158.3262,159.3685,160.6987,162.3650,164.4133,166.8833,169.8033,173.1857,177.0219,181.2780,185.8917,190.7710,195.7949,200.8173,205.6723,210.1837,214.1743,217.4781,219.9510,221.4819,222.0003,221.4823,219.9521,217.4800,214.1779,210.1899,205.6829,200.8352,195.8247,190.8197,185.9702,181.4024,177.2161,173.4842,170.2549,167.5560,165.3998,163.7891,162.7228,162.2008,162.2278,162.8155,163.9830,165.7547,168.1576,171.2156,174.9431,179.3381,184.3748,189.9973,196.1145,202.5979,209.2823,215.9698,222.4377,228.4495,233.7684,238.1722,241.4688,243.5094,244.2002,243.5091,241.4680,238.1707,233.7657,228.4449,222.4298,215.9563,209.2599,202.5613,196.0556,189.9040,184.2291,179.1142,174.6043,170.7110,167.4178,164.6866),(5,NULL,'MET0003','TotW','20240315',222.5000,155.7515,155.7527,155.7547,155.7580,155.7635,155.7724,155.7866,155.8090,155.8435,155.8960,155.9744,156.0895,156.2557,156.4915,156.8205,157.2715,157.8790,158.6828,159.7275,161.0606,162.7306,164.7836,167.2591,170.1857,173.5757,177.4206,181.6863,186.3104,191.2007,196.2359,201.2695,206.1355,210.6571,214.6567,217.9679,220.4464,221.9807,222.5003,221.9812,220.4474,217.9699,214.6602,210.6633,206.1462,201.2875,196.2658,191.2495,186.3890,181.8110,177.6152,173.8749,170.6384,167.9334,165.7723,164.1580,163.0893,162.5661,162.5932,163.1822,164.3523,166.1280,168.5364,171.6012,175.3371,179.7420,184.7901,190.4252,196.5562,203.0542,209.7536,216.4562,222.9387,228.9641,234.2949,238.7086,242.0126,244.0579,244.7502,244.0575,242.0118,238.7072,234.2922,228.9594,222.9307,216.4427,209.7312,203.0175,196.4972,190.3317,184.6441,179.5176,174.9976,171.0955,167.7948,165.0575),(6,NULL,'MET0001','TotW','20240315',223.0000,156.1015,156.1027,156.1047,156.1080,156.1135,156.1224,156.1367,156.1591,156.1938,156.2463,156.3249,156.4403,156.6068,156.8432,157.1729,157.6249,158.2338,159.0394,160.0864,161.4225,163.0963,165.1539,167.6350,170.5681,173.9658,177.8193,182.0945,186.7291,191.6303,196.6769,201.7218,206.5988,211.1305,215.1391,218.4577,220.9418,222.4796,223.0003,222.4800,220.9428,218.4597,215.1426,211.1367,206.6094,201.7398,196.7068,191.6793,186.8079,182.2195,178.0144,174.2656,171.0218,168.3108,166.1449,164.5269,163.4558,162.9314,162.9586,163.5490,164.7216,166.5014,168.9151,171.9868,175.7311,180.1459,185.2053,190.8531,196.9979,203.5105,210.2250,216.9426,223.4397,229.4786,234.8214,239.2451,242.5564,244.6063,245.3002,244.6060,242.5557,239.2436,234.8187,229.4739,223.4317,216.9291,210.2025,203.4738,196.9387,190.7594,185.0590,179.9210,175.3909,171.4800,168.1719,165.4284),(7,NULL,'MET0002','TotW','20240315',223.5000,156.4515,156.4527,156.4547,156.4580,156.4635,156.4725,156.4868,156.5093,156.5440,156.5967,156.6754,156.7910,156.9579,157.1949,157.5253,157.9783,158.5885,159.3960,160.4453,161.7845,163.4620,165.5242,168.0109,170.9506,174.3558,178.2179,182.5028,187.1477,192.0600,197.1179,202.1741,207.0620,211.6038,215.6214,218.9475,221.4372,222.9784,223.5003,222.9788,221.4382,218.9495,215.6250,211.6101,207.0727,202.1922,197.1479,192.1090,187.2267,182.6281,178.4135,174.6564,171.4053,168.6881,166.5174,164.8958,163.8223,163.2967,163.3239,163.9157,165.0910,166.8747,169.2938,172.3724,176.1251,180.5498,185.6206,191.2811,197.4396,203.9668,210.6963,217.4290,223.9407,229.9931,235.3479,239.7815,243.1003,245.1547,245.8502,245.1544,243.0995,239.7800,235.3452,229.9884,223.9327,217.4155,210.6738,203.9300,197.3803,191.1871,185.4739,180.3244,175.7841,171.8645,168.5490,165.7994),(8,NULL,'MET0003','TotW','20240315',224.0000,156.8015,156.8027,156.8047,156.8080,156.8136,156.8225,156.8369,156.8594,156.8942,156.9470,157.0259,157.1418,157.3091,157.5465,157.8777,158.3318,158.9433,159.7526,160.8043,162.1464,163.8277,165.8945,168.3867,171.3330,174.7459,178.6166,182.9111,187.5664,192.4897,197.5589,202.6264,207.5252,212.0772,216.1038,219.4373,221.9326,223.4772,224.0003,223.4777,221.9336,219.4393,216.1074,212.0835,207.5359,202.6445,197.5889,192.5388,187.6456,183.0367,178.8126,175.0471,171.7887,169.0655,166.8899,165.2647,164.1888,163.6620,163.6893,164.2824,165.4603,167.2480,169.6726,172.7581,176.5191,180.9537,186.0359,191.7090,197.8813,204.4231,211.1677,217.9155,224.4417,230.5076,235.8744,240.3179,243.6441,245.7032,246.4003,245.7029,243.6434,240.3164,235.8717,230.5030,224.4336,217.9019,211.1451,204.3862,197.8219,191.6148,185.8889,180.7278,176.1774,172.2490,168.9260,166.1703),(9,NULL,'MET0001','TotW','20240315',224.5000,157.1515,157.1527,157.1547,157.1581,157.1636,157.1726,157.1870,157.2095,157.2444,157.2973,157.3764,157.4925,157.6602,157.8982,158.2301,158.6852,159.2981,160.1092,161.1632,162.5083,164.1934,166.2648,168.7626,171.7155,175.1359,179.0153,183.3194,187.9851,192.9193,197.9998,203.0787,207.9885,212.5506,216.5862,219.9272,222.4280,223.9761,224.5003,223.9765,222.4290,219.9291,216.5898,212.5569,207.9992,203.0968,198.0300,192.9686,188.0644,183.4452,179.2118,175.4378,172.1722,169.4429,167.2624,165.6336,164.5553,164.0274,164.0547,164.6491,165.8296,167.6213,170.0513,173.1437,176.9132,181.3577,186.4511,192.1369,198.3230,204.8794,211.6390,218.4019,224.9427,231.0222,236.4009,240.8543,244.1880,246.2516,246.9503,246.2513,244.1872,240.8528,236.3982,231.0175,224.9346,218.3883,211.6165,204.8424,198.2634,192.0425,186.3038,181.1313,176.5706,172.6335,169.3031,166.5412),(10,NULL,'MET0002','TotW','20240315',225.0000,157.5015,157.5027,157.5047,157.5081,157.5136,157.5226,157.5370,157.5597,157.5946,157.6477,157.7269,157.8433,158.0114,158.2499,158.5825,159.0386,159.6529,160.4657,161.5221,162.8703,164.5591,166.6351,169.1385,172.0979,175.5260,179.4140,183.7277,188.4038,193.3490,198.4408,203.5310,208.4517,213.0240,217.0686,220.4170,222.9233,224.4749,225.0003,224.4753,222.9244,220.4190,217.0721,213.0303,208.4624,203.5492,198.4710,193.3984,188.4833,183.8538,179.6109,175.8286,172.5556,169.8203,167.6349,166.0025,164.9217,164.3927,164.4201,165.0158,166.1990,167.9947,170.4300,173.5293,177.3072,181.7616,186.8664,192.5648,198.7647,205.3357,212.1104,218.8883,225.4436,231.5367,236.9274,241.3908,244.7318,246.8001,247.5003,246.7997,244.7311,241.3893,236.9247,231.5320,225.4356,218.8747,212.0878,205.2986,198.7050,192.4702,186.7187,181.5347,176.9639,173.0179,169.6802,166.9121);
/*!40000 ALTER TABLE `dwd_cust_analog_u` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_grid_mtcl_plant_energy_day`
--

DROP TABLE IF EXISTS `dwd_grid_mtcl_plant_energy_day`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_grid_mtcl_plant_energy_day` (
  `id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `date` datetime DEFAULT NULL,
  `region_code` int DEFAULT NULL,
  `region_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `integral_grid_value` double DEFAULT NULL,
  `integral_value` double DEFAULT NULL,
  `report_grid_value` double DEFAULT NULL,
  `report_value` double DEFAULT NULL,
  `tmr_disc_value` double DEFAULT NULL,
  `tmr_gen_value` double DEFAULT NULL,
  `tmr_grid_value` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_grid_mtcl_plant_energy_day`
--

LOCK TABLES `dwd_grid_mtcl_plant_energy_day` WRITE;
/*!40000 ALTER TABLE `dwd_grid_mtcl_plant_energy_day` DISABLE KEYS */;
INSERT INTO `dwd_grid_mtcl_plant_energy_day` VALUES ('ID0001','2024-01-10 09:00:00',659061,'行政区划名称1','省份名称1','地市名称1',7739.24,8155.79,5187.53,1330.55,9755.47,2037.65,5317.93,'2024-01-06 10:00:00','2024-05-14 00:00:00'),('ID0002','2024-07-08 09:00:00',900575,'行政区划名称2','省份名称2','地市名称2',9141.09,9035.89,5961.92,867.81,4495.36,1598.18,350.06,'2024-03-12 03:00:00','2024-03-09 00:00:00'),('ID0003','2024-11-06 23:00:00',659792,'行政区划名称3','省份名称3','地市名称3',6813.36,1912.7,2938.58,9661.72,9080.74,5857.21,7865.15,'2024-05-25 14:00:00','2024-12-22 00:00:00');
/*!40000 ALTER TABLE `dwd_grid_mtcl_plant_energy_day` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_grid_mtcl_plant_power_min`
--

DROP TABLE IF EXISTS `dwd_grid_mtcl_plant_power_min`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_grid_mtcl_plant_power_min` (
  `id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `occur_time` datetime DEFAULT NULL,
  `region_code` int DEFAULT NULL,
  `region_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prov_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `load_power` double DEFAULT NULL,
  `etl_time` datetime DEFAULT NULL,
  `ds` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_grid_mtcl_plant_power_min`
--

LOCK TABLES `dwd_grid_mtcl_plant_power_min` WRITE;
/*!40000 ALTER TABLE `dwd_grid_mtcl_plant_power_min` DISABLE KEYS */;
INSERT INTO `dwd_grid_mtcl_plant_power_min` VALUES ('ID0001','2024-04-27 12:00:00',184697,'行政区划名称1','省份名称1','地市名称1',6234.69,'2025-01-28 23:00:00','2024-01-20 00:00:00'),('ID0002','2025-01-18 03:00:00',392412,'行政区划名称2','省份名称2','地市名称2',3404.01,'2025-01-17 17:00:00','2024-04-25 00:00:00'),('ID0003','2024-01-03 16:00:00',579051,'行政区划名称3','省份名称3','地市名称3',5975.59,'2024-11-10 22:00:00','2024-05-28 00:00:00');
/*!40000 ALTER TABLE `dwd_grid_mtcl_plant_power_min` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_grid_opoh_ovhaul_plan`
--

DROP TABLE IF EXISTS `dwd_grid_opoh_ovhaul_plan`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_grid_opoh_ovhaul_plan` (
  `ovhaul_plan_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `ovhaul_plan_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ovhaul_plan_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ovhaul_plan_st_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ovhaul_plan_st_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ovhaul_plan_cycle_typ_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ovhaul_plan_cycle_typ_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `major_typ_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `major_typ_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_stat_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_stat_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_stat_typ_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_stat_typ_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_src_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_src_typ_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_src_typ_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `work_content` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_work_start_tm` datetime DEFAULT NULL,
  `plan_work_end_tm` datetime DEFAULT NULL,
  `is_merge` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `merge_after_ovhaul_plan_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `work_risk_lvl_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `work_risk_lvl_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `work_typ_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `work_typ_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ovhaul_work_nature_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ovhaul_work_nature_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ovhaul_lvl_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ovhaul_lvl_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `maint_team_info` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `eqp_info` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reserv_req` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `founder_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `founder_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `create_tm` datetime DEFAULT NULL,
  `mdf_pes_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mdf_pes_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mdf_tm` datetime DEFAULT NULL,
  `op_maint_team_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `op_maint_team_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `creater_blg_team_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `creater_blg_team_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `founder_blg_op_maint_org_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `founder_blg_op_maint_org_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `founder_blg_city_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `founder_blg_city_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_src_typ_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_src_typ_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_delete` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_stat_vol_lvl_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elec_stat_vol_lvl_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `founder_phone_num` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_affect_comm_fiber` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_have_sendelec_scheme` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prtc_polarity_check_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prtc_polarity_check_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elecgd_risk_lvl_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `elecgd_risk_lvl_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_inspect_org_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_inspect_org_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_wbs` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_typ` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proj_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `provc_on_duty_pes_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `provc_on_duty_pes_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_on_duty_pes_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `city_on_duty_pes_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_on_duty_pes_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `county_on_duty_pes_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_poweroff` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_poweroff_range_anal` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_eqp_typ_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_eqp_typ_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_caus_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_caus_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_dc_area` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `dc_poweroff_area_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_accom_poweroff_plan` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_energized_work` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_accept_electrify_work` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `possess_electrify_work_condt` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `electrify_work_plan_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_poweroff_start_tm` datetime DEFAULT NULL,
  `plan_poweroff_end_tm` datetime DEFAULT NULL,
  `warn_eqp_typ_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `warn_eqp_typ_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `risk_conseq_typ_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `risk_conseq_typ_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sch_auth_typ_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sch_auth_typ_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `span_substance_cd` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `span_substance_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `accept_audit_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_survey` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `survey_feedback_dsc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `ver_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `emphasis_refer` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_outsrc` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prc_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_send_oms` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `oms_plan_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `send_oms_work_content` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `oms_accept_org_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `oms_accept_org_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_net_prov_id` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_net_prov_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_city_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_county_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `adm_addr` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_org_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_org_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_city_org_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_city_org_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_county_org_no` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_county_org_nm` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_dt` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_tm` datetime DEFAULT NULL,
  `par_year` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`ovhaul_plan_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_grid_opoh_ovhaul_plan`
--

LOCK TABLES `dwd_grid_opoh_ovhaul_plan` WRITE;
/*!40000 ALTER TABLE `dwd_grid_opoh_ovhaul_plan` DISABLE KEYS */;
INSERT INTO `dwd_grid_opoh_ovhaul_plan` VALUES ('OVH0001','检修计划名称1','OV-0001','异常','正常','检修计划周期类型_1','检修计划周期类型_1','专业类型代码_1','专业类型描述_1','ELE0001','站线名称1','站线类型代码_1','站线类型描述_1','PLA0001','计划来源类型代码_1','计划来源类型描述_1','工作内容_1','2025-04-13 00:00:00','2024-12-29 12:00:00','是否合并(01:_1','MER0001','作业风险等级代码_1','作业风险等级描述_1','检修工作类型代码_1','检修工作类型描述_1','检修工作性质代码_1','检修工作性质描述_1','检修级别代码_1','检修级别描述_1','维护班组信息_1','设备信息_1','复役要求_1','FOU0001','创建人名称1','2024-08-13 23:00:00','MDF0001','修改人名称1','2024-04-25 19:00:00','OP-0001','运维班组名称1','CR-0001','创建人所属班组名称1','FO-0001','创建人所属运维单位名1','FO-0001','创建人所属地市名称1','数据来源代码_1','数据来源描述_1','APP0001','应用名称1','是否删除(01:_1','站线电压等级代码_1','站线电压等级描述_1','FO-0001','是否影响通信光缆_1','是否有送电方案(_1','保护极性校验代码_1','保护极性校验描述_1','电网风险等级代码_1','电网风险等级描述_1','PR-0001','工程项目监理单位名称1','工程项目WBS_1','工程项目类型_1','工程项目名称1','PR-0001','PRO0001','省级到岗人员名称1','CIT0001','市级到岗人员名称1','COU0001','县级到岗人员名称1','是否停电(01:_1','是否完成停电范围_1','停电设备类型代码_1','停电设备类型描述_1','停电事由代码_1','停电事由描述_1','是否直流区域(0_1','DC0001','是否陪停计划(0_1','是否带电作业(0_1','是否受理带电作业_1','是否具备带电作业_1','EL-0001','2024-07-17 14:00:00','2024-12-02 00:00:00','预警设备类型代码_1','预警设备类型描述_1','风险后果类型代码_1','风险后果类型描述_1','调度管辖类型代码_1','调度管辖类型描述_1','跨越物代码_1','跨越物描述_1','受理审核描述_1','是否勘察(02:_1','44512.65','VE-0001','重点参照物_1','是否委外(01:_1','PRC0001','备注测试数据1','是否发送OMS(_1','OM-0001','发送OMS工作内_1','OMS0001','OMS接收单位名称1','BLG0001','所属网省名称1','所属地市/洲名称1','所属区/县名称1','广州市天河区zz路3号','ST-0001','标准单位名称(个性化1','ST-0001','标准地市单位名称(个1','ST-0001','标准区县单位名称(个1','2024-06-27 00:00:00','2024-10-30 09:00:00','年分区(个性化)_1'),('OVH0002','检修计划名称2','OV-0002','启用','停用','检修计划周期类型_2','检修计划周期类型_2','专业类型代码_2','专业类型描述_2','ELE0002','站线名称2','站线类型代码_2','站线类型描述_2','PLA0002','计划来源类型代码_2','计划来源类型描述_2','工作内容_2','2025-04-09 09:00:00','2024-04-15 12:00:00','是否合并(01:_2','MER0002','作业风险等级代码_2','作业风险等级描述_2','检修工作类型代码_2','检修工作类型描述_2','检修工作性质代码_2','检修工作性质描述_2','检修级别代码_2','检修级别描述_2','维护班组信息_2','设备信息_2','复役要求_2','FOU0002','创建人名称2','2024-03-19 00:00:00','MDF0002','修改人名称2','2025-04-11 15:00:00','OP-0002','运维班组名称2','CR-0002','创建人所属班组名称2','FO-0002','创建人所属运维单位名2','FO-0002','创建人所属地市名称2','数据来源代码_2','数据来源描述_2','APP0002','应用名称2','是否删除(01:_2','站线电压等级代码_2','站线电压等级描述_2','FO-0002','是否影响通信光缆_2','是否有送电方案(_2','保护极性校验代码_2','保护极性校验描述_2','电网风险等级代码_2','电网风险等级描述_2','PR-0002','工程项目监理单位名称2','工程项目WBS_2','工程项目类型_2','工程项目名称2','PR-0002','PRO0002','省级到岗人员名称2','CIT0002','市级到岗人员名称2','COU0002','县级到岗人员名称2','是否停电(01:_2','是否完成停电范围_2','停电设备类型代码_2','停电设备类型描述_2','停电事由代码_2','停电事由描述_2','是否直流区域(0_2','DC0002','是否陪停计划(0_2','是否带电作业(0_2','是否受理带电作业_2','是否具备带电作业_2','EL-0002','2024-12-25 02:00:00','2024-09-24 06:00:00','预警设备类型代码_2','预警设备类型描述_2','风险后果类型代码_2','风险后果类型描述_2','调度管辖类型代码_2','调度管辖类型描述_2','跨越物代码_2','跨越物描述_2','受理审核描述_2','是否勘察(02:_2','3621.16','VE-0002','重点参照物_2','是否委外(01:_2','PRC0002','备注测试数据2','是否发送OMS(_2','OM-0002','发送OMS工作内_2','OMS0002','OMS接收单位名称2','BLG0002','所属网省名称2','所属地市/洲名称2','所属区/县名称2','广州市天河区zz路3号','ST-0002','标准单位名称(个性化2','ST-0002','标准地市单位名称(个2','ST-0002','标准区县单位名称(个2','2024-12-26 00:00:00','2024-07-04 06:00:00','年分区(个性化)_2'),('OVH0003','检修计划名称3','OV-0003','停用','激活','检修计划周期类型_3','检修计划周期类型_3','专业类型代码_3','专业类型描述_3','ELE0003','站线名称3','站线类型代码_3','站线类型描述_3','PLA0003','计划来源类型代码_3','计划来源类型描述_3','工作内容_3','2024-01-13 03:00:00','2024-09-17 04:00:00','是否合并(01:_3','MER0003','作业风险等级代码_3','作业风险等级描述_3','检修工作类型代码_3','检修工作类型描述_3','检修工作性质代码_3','检修工作性质描述_3','检修级别代码_3','检修级别描述_3','维护班组信息_3','设备信息_3','复役要求_3','FOU0003','创建人名称3','2024-08-05 03:00:00','MDF0003','修改人名称3','2024-03-30 18:00:00','OP-0003','运维班组名称3','CR-0003','创建人所属班组名称3','FO-0003','创建人所属运维单位名3','FO-0003','创建人所属地市名称3','数据来源代码_3','数据来源描述_3','APP0003','应用名称3','是否删除(01:_3','站线电压等级代码_3','站线电压等级描述_3','FO-0003','是否影响通信光缆_3','是否有送电方案(_3','保护极性校验代码_3','保护极性校验描述_3','电网风险等级代码_3','电网风险等级描述_3','PR-0003','工程项目监理单位名称3','工程项目WBS_3','工程项目类型_3','工程项目名称3','PR-0003','PRO0003','省级到岗人员名称3','CIT0003','市级到岗人员名称3','COU0003','县级到岗人员名称3','是否停电(01:_3','是否完成停电范围_3','停电设备类型代码_3','停电设备类型描述_3','停电事由代码_3','停电事由描述_3','是否直流区域(0_3','DC0003','是否陪停计划(0_3','是否带电作业(0_3','是否受理带电作业_3','是否具备带电作业_3','EL-0003','2025-02-15 10:00:00','2024-06-13 20:00:00','预警设备类型代码_3','预警设备类型描述_3','风险后果类型代码_3','风险后果类型描述_3','调度管辖类型代码_3','调度管辖类型描述_3','跨越物代码_3','跨越物描述_3','受理审核描述_3','是否勘察(02:_3','31463.35','VE-0003','重点参照物_3','是否委外(01:_3','PRC0003','备注测试数据3','是否发送OMS(_3','OM-0003','发送OMS工作内_3','OMS0003','OMS接收单位名称3','BLG0003','所属网省名称3','所属地市/洲名称3','所属区/县名称3','深圳市南山区aa路4号','ST-0003','标准单位名称(个性化3','ST-0003','标准地市单位名称(个3','ST-0003','标准区县单位名称(个3','2025-02-14 00:00:00','2024-01-29 16:00:00','年分区(个性化)_3');
/*!40000 ALTER TABLE `dwd_grid_opoh_ovhaul_plan` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_grid_opoh_poweroff_app`
--

DROP TABLE IF EXISTS `dwd_grid_opoh_poweroff_app`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_grid_opoh_poweroff_app` (
  `poweroff_App_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `ovhaul_plan_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `App_st_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `App_work_start_tm` datetime DEFAULT NULL,
  `App_work_end_tm` datetime DEFAULT NULL,
  `App_poweroff_start_tm` datetime DEFAULT NULL,
  `App_poweroff_end_tm` datetime DEFAULT NULL,
  `poweroff_typ_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_typ_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `declare_cate_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `declare_cate_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `work_nature_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `work_nature_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `work_content` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_sendelec_contacts_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_sendelec_contacts_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_sendelec_contacts_phone` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `tune_tube_range` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `const_receive_order_org_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `const_receive_order_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_plan_poweroff` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `App_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_App_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Applyer_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Applyer_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `App_dept_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `App_dept_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `App_org_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `App_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `Applyer_tel` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `App_cate_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `App_cate_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `oms_docs_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `stop_service_req` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `attention_matters` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `prtc_req` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `reserv_req` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sch_accept_org_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sch_recep_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_sta_tune` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_affect_comm_FIBER` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sta_line_typ_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sta_line_typ_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sta_line_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sta_line_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sta_line_volt_lvl_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sta_line_volt_lvl_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `founder_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `founder_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `create_tm` datetime DEFAULT NULL,
  `mdf_pes_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mdf_pes_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mdf_tm` datetime DEFAULT NULL,
  `blg_ship_dimension_team_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_ship_dimension_team_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_ship_dimension_org_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_ship_dimension_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `founder_blg_team_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `founder_blg_team_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `founder_blg_city_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `founder_blg_city_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_prov_org_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `blg_prov_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_src_typ_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_src_typ_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_appid` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `app_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `major_typ_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `comm_affect_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `proc_example_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_alr_send_sch` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_right_comm_affect` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_cons_poweroff` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_carry_out_debugging_proj` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_nuclear_phase` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_space_App` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_affect_power` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_affect_automation` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_mobile_end_opera` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `is_delete` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sign_in_pes_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sign_in_tm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sign_in_opinion` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `event_lvl` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_eqp_range_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_eqp_range_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_range_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `remark` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_src_typ_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `plan_src_typ_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_eqp_highest_volt_lvl_cd` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `poweroff_eqp_highest_volt_lvl_dsc` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_org_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_county_org_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_county_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_city_org_no` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `std_city_org_nm` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `data_dt` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `etl_tm` datetime DEFAULT NULL,
  PRIMARY KEY (`poweroff_App_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_grid_opoh_poweroff_app`
--

LOCK TABLES `dwd_grid_opoh_poweroff_app` WRITE;
/*!40000 ALTER TABLE `dwd_grid_opoh_poweroff_app` DISABLE KEYS */;
INSERT INTO `dwd_grid_opoh_poweroff_app` VALUES ('POW0001','OVH0001','激活','2025-01-13 03:00:00','2024-11-17 08:00:00','2025-02-05 07:00:00','2025-01-22 11:00:00','停电类型代码_1','停电类型描述_1','申报类别代码_1','申报类别描述_1','工作性质代码_1','工作性质描述_1','工作内容_1','STO0001','停送电联系人名称1','13849993978','调管范围_1','CON0001','施工受令单位名称1','是否计划停电_1','AP-0001','停电申请单名称1','APP0001','申请人名称1','APP0001','申请部门名称1','APP0001','申请单位名称1','13895167282','申请类别代码_1','申请类别描述_1','OM-0001','停役要求_1','注意事项_1','保护要求_1','复役要求_1','SCH0001','调度接收单位名称1','是否站调_1','是否影响通信光缆_1','站线类型代码_1','站线类型描述_1','STA0001','站线名称1','ST-0001','站线电压等级描述_1','FOU0001','创建人名称1','2024-05-23 05:00:00','MDF0001','修改人名称1','2024-03-07 18:00:00','BL-0001','所属运维班组名称1','BL-0001','所属运维单位名称1','FO-0001','创建人所属班组名称1','FO-0001','创建人所属地市名称1','BL-0001','所属省单位名称1','数据来源类型代码_1','数据来源类型描述_1','应用ID_1','应用名称1','专业类型代码_1','通信影响描述_1','PRO0001','是否已发送调度_1','是否对通信影响_1','是否需预告用户停_1','是否开展调试项目_1','是否核相_1','是否间隔申请_1','是否影响出力_1','是否影响自动化_1','13813953181','是否删除_1','签收人名称1','2024-10-16 00:00:00','签收意见_1','事件等级_1','停电设备范围代码_1','停电设备范围描述_1','停电范围描述_1','备注测试数据1','计划来源类型代码_1','计划来源类型描述_1','停电设备最高电压_1','停电设备最高电压_1','ST-0001','标准单位名称（个性化1','ST-0001','标准区县单位名称（个1','ST-0001','标准地市单位名称（个1','2024-06-01 00:00:00','2025-02-13 12:00:00'),('POW0002','OVH0002','注销','2024-11-27 04:00:00','2024-08-04 20:00:00','2024-09-12 03:00:00','2024-06-16 18:00:00','停电类型代码_2','停电类型描述_2','申报类别代码_2','申报类别描述_2','工作性质代码_2','工作性质描述_2','工作内容_2','STO0002','停送电联系人名称2','13896387301','调管范围_2','CON0002','施工受令单位名称2','是否计划停电_2','AP-0002','停电申请单名称2','APP0002','申请人名称2','APP0002','申请部门名称2','APP0002','申请单位名称2','13849200702','申请类别代码_2','申请类别描述_2','OM-0002','停役要求_2','注意事项_2','保护要求_2','复役要求_2','SCH0002','调度接收单位名称2','是否站调_2','是否影响通信光缆_2','站线类型代码_2','站线类型描述_2','STA0002','站线名称2','ST-0002','站线电压等级描述_2','FOU0002','创建人名称2','2025-01-01 16:00:00','MDF0002','修改人名称2','2025-01-17 05:00:00','BL-0002','所属运维班组名称2','BL-0002','所属运维单位名称2','FO-0002','创建人所属班组名称2','FO-0002','创建人所属地市名称2','BL-0002','所属省单位名称2','数据来源类型代码_2','数据来源类型描述_2','应用ID_2','应用名称2','专业类型代码_2','通信影响描述_2','PRO0002','是否已发送调度_2','是否对通信影响_2','是否需预告用户停_2','是否开展调试项目_2','是否核相_2','是否间隔申请_2','是否影响出力_2','是否影响自动化_2','13874417098','是否删除_2','签收人名称2','2024-11-25 00:00:00','签收意见_2','事件等级_2','停电设备范围代码_2','停电设备范围描述_2','停电范围描述_2','备注测试数据2','计划来源类型代码_2','计划来源类型描述_2','停电设备最高电压_2','停电设备最高电压_2','ST-0002','标准单位名称（个性化2','ST-0002','标准区县单位名称（个2','ST-0002','标准地市单位名称（个2','2025-02-14 00:00:00','2024-02-15 08:00:00'),('POW0003','OVH0003','启用','2024-07-08 01:00:00','2024-07-21 17:00:00','2024-09-15 02:00:00','2024-03-01 01:00:00','停电类型代码_3','停电类型描述_3','申报类别代码_3','申报类别描述_3','工作性质代码_3','工作性质描述_3','工作内容_3','STO0003','停送电联系人名称3','13895249709','调管范围_3','CON0003','施工受令单位名称3','是否计划停电_3','AP-0003','停电申请单名称3','APP0003','申请人名称3','APP0003','申请部门名称3','APP0003','申请单位名称3','13832764338','申请类别代码_3','申请类别描述_3','OM-0003','停役要求_3','注意事项_3','保护要求_3','复役要求_3','SCH0003','调度接收单位名称3','是否站调_3','是否影响通信光缆_3','站线类型代码_3','站线类型描述_3','STA0003','站线名称3','ST-0003','站线电压等级描述_3','FOU0003','创建人名称3','2025-04-18 05:00:00','MDF0003','修改人名称3','2025-04-04 16:00:00','BL-0003','所属运维班组名称3','BL-0003','所属运维单位名称3','FO-0003','创建人所属班组名称3','FO-0003','创建人所属地市名称3','BL-0003','所属省单位名称3','数据来源类型代码_3','数据来源类型描述_3','应用ID_3','应用名称3','专业类型代码_3','通信影响描述_3','PRO0003','是否已发送调度_3','是否对通信影响_3','是否需预告用户停_3','是否开展调试项目_3','是否核相_3','是否间隔申请_3','是否影响出力_3','是否影响自动化_3','13854122875','是否删除_3','签收人名称3','2024-12-13 00:00:00','签收意见_3','事件等级_3','停电设备范围代码_3','停电设备范围描述_3','停电范围描述_3','备注测试数据3','计划来源类型代码_3','计划来源类型描述_3','停电设备最高电压_3','停电设备最高电压_3','ST-0003','标准单位名称（个性化3','ST-0003','标准区县单位名称（个3','ST-0003','标准地市单位名称（个3','2024-12-08 00:00:00','2025-03-08 21:00:00');
/*!40000 ALTER TABLE `dwd_grid_opoh_poweroff_app` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_psr_d_grid_analog_f`
--

DROP TABLE IF EXISTS `dwd_psr_d_grid_analog_f`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_psr_d_grid_analog_f` (
  `id` int NOT NULL AUTO_INCREMENT,
  `equip_type` varchar(255) DEFAULT NULL,
  `psrid` varchar(255) DEFAULT NULL,
  `pos_code` varchar(255) DEFAULT NULL,
  `measuerment_type` varchar(255) DEFAULT NULL,
  `date` varchar(255) DEFAULT NULL,
  `V0000` decimal(20,4) DEFAULT NULL,
  `V0015` decimal(20,4) DEFAULT NULL,
  `V0030` decimal(20,4) DEFAULT NULL,
  `V0045` decimal(20,4) DEFAULT NULL,
  `V0100` decimal(20,4) DEFAULT NULL,
  `V0115` decimal(20,4) DEFAULT NULL,
  `V0130` decimal(20,4) DEFAULT NULL,
  `V0145` decimal(20,4) DEFAULT NULL,
  `V0200` decimal(20,4) DEFAULT NULL,
  `V0215` decimal(20,4) DEFAULT NULL,
  `V0230` decimal(20,4) DEFAULT NULL,
  `V0245` decimal(20,4) DEFAULT NULL,
  `V0300` decimal(20,4) DEFAULT NULL,
  `V0315` decimal(20,4) DEFAULT NULL,
  `V0330` decimal(20,4) DEFAULT NULL,
  `V0345` decimal(20,4) DEFAULT NULL,
  `V0400` decimal(20,4) DEFAULT NULL,
  `V0415` decimal(20,4) DEFAULT NULL,
  `V0430` decimal(20,4) DEFAULT NULL,
  `V0445` decimal(20,4) DEFAULT NULL,
  `V0500` decimal(20,4) DEFAULT NULL,
  `V0515` decimal(20,4) DEFAULT NULL,
  `V0530` decimal(20,4) DEFAULT NULL,
  `V0545` decimal(20,4) DEFAULT NULL,
  `V0600` decimal(20,4) DEFAULT NULL,
  `V0615` decimal(20,4) DEFAULT NULL,
  `V0630` decimal(20,4) DEFAULT NULL,
  `V0645` decimal(20,4) DEFAULT NULL,
  `V0700` decimal(20,4) DEFAULT NULL,
  `V0715` decimal(20,4) DEFAULT NULL,
  `V0730` decimal(20,4) DEFAULT NULL,
  `V0745` decimal(20,4) DEFAULT NULL,
  `V0800` decimal(20,4) DEFAULT NULL,
  `V0815` decimal(20,4) DEFAULT NULL,
  `V0830` decimal(20,4) DEFAULT NULL,
  `V0845` decimal(20,4) DEFAULT NULL,
  `V0900` decimal(20,4) DEFAULT NULL,
  `V0915` decimal(20,4) DEFAULT NULL,
  `V0930` decimal(20,4) DEFAULT NULL,
  `V0945` decimal(20,4) DEFAULT NULL,
  `V1000` decimal(20,4) DEFAULT NULL,
  `V1015` decimal(20,4) DEFAULT NULL,
  `V1030` decimal(20,4) DEFAULT NULL,
  `V1045` decimal(20,4) DEFAULT NULL,
  `V1100` decimal(20,4) DEFAULT NULL,
  `V1115` decimal(20,4) DEFAULT NULL,
  `V1130` decimal(20,4) DEFAULT NULL,
  `V1145` decimal(20,4) DEFAULT NULL,
  `V1200` decimal(20,4) DEFAULT NULL,
  `V1215` decimal(20,4) DEFAULT NULL,
  `V1230` decimal(20,4) DEFAULT NULL,
  `V1245` decimal(20,4) DEFAULT NULL,
  `V1300` decimal(20,4) DEFAULT NULL,
  `V1315` decimal(20,4) DEFAULT NULL,
  `V1330` decimal(20,4) DEFAULT NULL,
  `V1345` decimal(20,4) DEFAULT NULL,
  `V1400` decimal(20,4) DEFAULT NULL,
  `V1415` decimal(20,4) DEFAULT NULL,
  `V1430` decimal(20,4) DEFAULT NULL,
  `V1445` decimal(20,4) DEFAULT NULL,
  `V1500` decimal(20,4) DEFAULT NULL,
  `V1515` decimal(20,4) DEFAULT NULL,
  `V1530` decimal(20,4) DEFAULT NULL,
  `V1545` decimal(20,4) DEFAULT NULL,
  `V1600` decimal(20,4) DEFAULT NULL,
  `V1615` decimal(20,4) DEFAULT NULL,
  `V1630` decimal(20,4) DEFAULT NULL,
  `V1645` decimal(20,4) DEFAULT NULL,
  `V1700` decimal(20,4) DEFAULT NULL,
  `V1715` decimal(20,4) DEFAULT NULL,
  `V1730` decimal(20,4) DEFAULT NULL,
  `V1745` decimal(20,4) DEFAULT NULL,
  `V1800` decimal(20,4) DEFAULT NULL,
  `V1815` decimal(20,4) DEFAULT NULL,
  `V1830` decimal(20,4) DEFAULT NULL,
  `V1845` decimal(20,4) DEFAULT NULL,
  `V1900` decimal(20,4) DEFAULT NULL,
  `V1915` decimal(20,4) DEFAULT NULL,
  `V1930` decimal(20,4) DEFAULT NULL,
  `V1945` decimal(20,4) DEFAULT NULL,
  `V2000` decimal(20,4) DEFAULT NULL,
  `V2015` decimal(20,4) DEFAULT NULL,
  `V2030` decimal(20,4) DEFAULT NULL,
  `V2045` decimal(20,4) DEFAULT NULL,
  `V2100` decimal(20,4) DEFAULT NULL,
  `V2115` decimal(20,4) DEFAULT NULL,
  `V2130` decimal(20,4) DEFAULT NULL,
  `V2145` decimal(20,4) DEFAULT NULL,
  `V2200` decimal(20,4) DEFAULT NULL,
  `V2215` decimal(20,4) DEFAULT NULL,
  `V2230` decimal(20,4) DEFAULT NULL,
  `V2245` decimal(20,4) DEFAULT NULL,
  `V2300` decimal(20,4) DEFAULT NULL,
  `V2315` decimal(20,4) DEFAULT NULL,
  `V2330` decimal(20,4) DEFAULT NULL,
  `V2345` decimal(20,4) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_psr_d_grid_analog_f`
--

LOCK TABLES `dwd_psr_d_grid_analog_f` WRITE;
/*!40000 ALTER TABLE `dwd_psr_d_grid_analog_f` DISABLE KEYS */;
INSERT INTO `dwd_psr_d_grid_analog_f` VALUES (1,'transformer','RES0001','POS0001','TotW','20240315',100.5000,70.3507,70.3512,70.3521,70.3536,70.3561,70.3601,70.3665,70.3766,70.3923,70.4160,70.4514,70.5033,70.5784,70.6849,70.8335,71.0372,71.3116,71.6747,72.1466,72.7487,73.5031,74.4304,75.5485,76.8704,78.4016,80.1383,82.0650,84.1537,86.3625,88.6369,90.9105,93.1084,95.1507,96.9573,98.4529,99.5724,100.2655,100.5001,100.2656,99.5729,98.4538,96.9589,95.1535,93.1132,90.9186,88.6504,86.3846,84.1892,82.1214,80.2262,78.5368,77.0749,75.8531,74.8769,74.1478,73.6650,73.4287,73.4410,73.7070,74.2355,75.0376,76.1254,77.5098,79.1972,81.1868,83.4670,86.0123,88.7815,91.7166,94.7426,97.7701,100.6982,103.4197,105.8276,107.8212,109.3136,110.2374,110.5501,110.2372,109.3132,107.8205,105.8264,103.4176,100.6946,97.7640,94.7325,91.7001,88.7549,85.9700,83.4010,81.0855,79.0439,77.2813,75.7905,74.5541),(2,'transformer','RES0002','POS0002','TotW','20240315',101.0000,70.7007,70.7012,70.7021,70.7036,70.7061,70.7102,70.7166,70.7268,70.7425,70.7663,70.8019,70.8541,70.9295,71.0366,71.1859,71.3907,71.6664,72.0313,72.5055,73.1107,73.8687,74.8007,75.9244,77.2528,78.7917,80.5370,82.4733,84.5724,86.7922,89.0779,91.3628,93.5716,95.6241,97.4397,98.9427,100.0678,100.7643,101.0002,100.7645,100.0683,98.9436,97.4413,95.6269,93.5765,91.3710,89.0914,86.8144,84.6081,82.5299,80.6253,78.9275,77.4583,76.2304,75.2495,74.5167,74.0315,73.7940,73.8063,74.0737,74.6049,75.4109,76.5041,77.8954,79.5912,81.5908,83.8822,86.4402,89.2232,92.1729,95.2140,98.2565,101.1991,103.9342,106.3541,108.3576,109.8574,110.7858,111.1001,110.7857,109.8571,108.3570,106.3529,103.9321,101.1955,98.2504,95.2038,92.1563,89.1965,86.3977,83.8160,81.4889,79.4371,77.6658,76.1675,74.9250),(3,'transformer','RES0003','POS0003','TotW','20240315',101.5000,71.0507,71.0512,71.0521,71.0536,71.0561,71.0602,71.0667,71.0769,71.0927,71.1166,71.1524,71.2049,71.2807,71.3883,71.5383,71.7441,72.0212,72.3879,72.8644,73.4726,74.2344,75.1710,76.3002,77.6353,79.1817,80.9357,82.8816,84.9910,87.2219,89.5189,91.8151,94.0349,96.0975,97.9220,99.4325,100.5632,101.2631,101.5002,101.2633,100.5637,99.4334,97.9237,96.1003,94.0397,91.8233,89.5325,87.2442,85.0269,82.9385,81.0245,79.3182,77.8418,76.6078,75.6220,74.8856,74.3980,74.1594,74.1717,74.4404,74.9742,75.7843,76.8829,78.2810,79.9852,81.9947,84.2975,86.8681,89.6649,92.6292,95.6854,98.7429,101.7001,104.4488,106.8806,108.8941,110.4013,111.3343,111.6501,111.3341,110.4009,108.8934,106.8794,104.4467,101.6965,98.7368,95.6751,92.6125,89.6380,86.8255,84.2309,81.8923,79.8304,78.0503,76.5446,75.2959),(4,'transformer','RES0004','POS0004','TotW','20240315',102.0000,71.4007,71.4012,71.4021,71.4037,71.4062,71.4103,71.4168,71.4270,71.4429,71.4669,71.5029,71.5556,71.6318,71.7399,71.8908,72.0975,72.3760,72.7445,73.2234,73.8345,74.6001,75.5413,76.6761,78.0177,79.5718,81.3344,83.2899,85.4097,87.6515,89.9598,92.2674,94.4981,96.5709,98.4044,99.9224,101.0586,101.7619,102.0002,101.7622,101.0591,99.9233,98.4060,96.5737,94.5030,92.2756,89.9735,87.6739,85.4458,83.3471,81.4236,79.7089,78.2252,76.9852,75.9945,75.2545,74.7645,74.5247,74.5371,74.8071,75.3435,76.1576,77.2616,78.6666,80.3793,82.3986,84.7128,87.2961,90.1066,93.0855,96.1567,99.2294,102.2011,104.9633,107.4071,109.4305,110.9451,111.8827,112.2001,111.8826,110.9447,109.4298,107.4059,104.9612,102.1975,99.2232,96.1465,93.0687,90.0796,87.2532,84.6458,82.2957,80.2236,78.4348,76.9217,75.6668),(5,'transformer','RES0005','POS0005','TotW','20240315',102.5000,71.7507,71.7512,71.7521,71.7537,71.7562,71.7603,71.7669,71.7772,71.7931,71.8173,71.8534,71.9064,71.9830,72.0916,72.2432,72.4509,72.7308,73.1011,73.5823,74.1965,74.9658,75.9116,77.0520,78.4002,79.9618,81.7331,83.6982,85.8284,88.0812,90.4008,92.7197,94.9613,97.0443,98.8868,100.4122,101.5540,102.2608,102.5002,102.2610,101.5544,100.4131,98.8884,97.0471,94.9662,92.7280,90.4146,88.1037,85.8646,83.7556,81.8228,80.0997,78.6087,77.3626,76.3670,75.6234,75.1310,74.8900,74.9025,75.1738,75.7129,76.5309,77.6403,79.0522,80.7733,82.8025,85.1280,87.7240,90.5483,93.5418,96.6281,99.7158,102.7021,105.4778,107.9336,109.9669,111.4890,112.4311,112.7501,112.4310,111.4886,109.9662,107.9324,105.4757,102.6984,99.7096,96.6178,93.5249,90.5212,87.6809,85.0608,82.6991,80.6169,78.8193,77.2987,76.0377),(6,'transformer','RES0006','POS0006','TotW','20240315',103.0000,72.1007,72.1012,72.1022,72.1037,72.1062,72.1104,72.1170,72.1273,72.1433,72.1676,72.2039,72.2572,72.3341,72.4433,72.5956,72.8043,73.0855,73.4577,73.9412,74.5584,75.3315,76.2819,77.4278,78.7826,80.3519,82.1318,84.1064,86.2471,88.5109,90.8418,93.1720,95.4245,97.5177,99.3692,100.9020,102.0493,102.7596,103.0002,102.7598,102.0498,100.9029,99.3708,97.5205,95.4295,93.1803,90.8556,88.5335,86.2835,84.1642,82.2219,80.4904,78.9921,77.7399,76.7396,75.9922,75.4975,75.2553,75.2679,75.5405,76.0822,76.9042,78.0191,79.4379,81.1673,83.2064,85.5433,88.1519,90.9900,93.9981,97.0994,100.2022,103.2031,105.9924,108.4601,110.5033,112.0328,112.9796,113.3001,112.9794,112.0324,110.5026,108.4589,105.9902,103.1994,100.1960,97.0891,93.9812,90.9627,88.1086,85.4757,83.1025,81.0101,79.2038,77.6758,76.4087),(7,'transformer','RES0007','POS0007','TotW','20240315',103.5000,72.4507,72.4512,72.4522,72.4537,72.4563,72.4604,72.4670,72.4774,72.4935,72.5179,72.5544,72.6079,72.6852,72.7949,72.9480,73.1578,73.4403,73.8142,74.3002,74.9203,75.6972,76.6522,77.8037,79.1650,80.7420,82.5305,84.5147,86.6657,88.9405,91.2828,93.6243,95.8878,97.9910,99.8515,101.3918,102.5447,103.2584,103.5002,103.2587,102.5452,101.3927,99.8532,97.9939,95.8927,93.6326,91.2967,88.9633,86.7023,84.5727,82.6210,80.8811,79.3756,78.1173,77.1121,76.3611,75.8640,75.6206,75.6332,75.9072,76.4515,77.2775,78.3978,79.8235,81.5613,83.6103,85.9585,88.5798,91.4317,94.4544,97.5708,100.6886,103.7041,106.5069,108.9866,111.0397,112.5766,113.5280,113.8501,113.5279,112.5763,111.0391,108.9854,106.5047,103.7004,100.6823,97.5604,94.4374,91.4043,88.5363,85.8906,83.5059,81.4034,79.5883,78.0529,76.7796),(8,'transformer','RES0008','POS0008','TotW','20240315',104.0000,72.8007,72.8013,72.8022,72.8037,72.8063,72.8105,72.8171,72.8276,72.8437,72.8682,72.9049,72.9587,73.0364,73.1466,73.3004,73.5112,73.7951,74.1708,74.6591,75.2823,76.0629,77.0225,78.1796,79.5475,81.1320,82.9292,84.9230,87.0844,89.3702,91.7238,94.0766,96.3510,98.4644,100.3339,101.8816,103.0401,103.7573,104.0002,103.7575,103.0406,101.8825,100.3356,98.4673,96.3560,94.0849,91.7377,89.3930,87.1212,84.9813,83.0202,81.2719,79.7591,78.4947,77.4846,76.7300,76.2305,75.9859,75.9986,76.2740,76.8209,77.6509,78.7765,80.2091,81.9553,84.0142,86.3738,89.0077,91.8734,94.9107,98.0421,101.1750,104.2051,107.0214,109.5131,111.5762,113.1205,114.0765,114.4001,114.0763,113.1201,111.5755,109.5119,107.0192,104.2013,101.1687,98.0317,94.8936,91.8459,88.9640,86.3055,83.9094,81.7966,79.9727,78.4299,77.1505),(9,'transformer','RES0009','POS0009','TotW','20240315',104.5000,73.1507,73.1513,73.1522,73.1537,73.1563,73.1605,73.1672,73.1777,73.1939,73.2186,73.2554,73.3094,73.3875,73.4983,73.6528,73.8646,74.1499,74.5274,75.0181,75.6442,76.4286,77.3928,78.5554,79.9299,81.5221,83.3279,85.3313,87.5031,89.7999,92.1647,94.5288,96.8142,98.9378,100.8163,102.3714,103.5355,104.2561,104.5002,104.2563,103.5360,102.3724,100.8180,98.9407,96.8192,94.5373,92.1788,89.8228,87.5400,85.3899,83.4193,81.6626,80.1425,78.8721,77.8571,77.0989,76.5970,76.3513,76.3640,76.6407,77.1902,78.0242,79.1553,80.5947,82.3493,84.4182,86.7891,89.4357,92.3151,95.3670,98.5135,101.6615,104.7060,107.5359,110.0396,112.1126,113.6643,114.6249,114.9501,114.6248,113.6640,112.1119,110.0384,107.5337,104.7023,101.6551,98.5030,95.3498,92.2874,89.3917,86.7205,84.3128,82.1899,80.3572,78.8070,77.5214),(10,'transformer','RES0010','POS0010','TotW','20240315',105.0000,73.5007,73.5013,73.5022,73.5038,73.5064,73.5106,73.5173,73.5278,73.5441,73.5689,73.6059,73.6602,73.7386,73.8499,74.0052,74.2180,74.5047,74.8840,75.3770,76.0061,76.7942,77.7631,78.9313,80.3124,81.9121,83.7266,85.7396,87.9218,90.2295,92.6057,94.9811,97.2775,99.4112,101.2987,102.8613,104.0309,104.7549,105.0002,104.7552,104.0314,102.8622,101.3003,99.4141,97.2825,94.9896,92.6198,90.2526,87.9589,85.7984,83.8184,82.0533,80.5260,79.2495,78.2296,77.4678,76.9635,76.7166,76.7294,77.0074,77.5595,78.3975,79.5340,80.9803,82.7433,84.8221,87.2043,89.8636,92.7568,95.8233,98.9849,102.1479,105.2070,108.0505,110.5661,112.6490,114.2082,115.1734,115.5001,115.1732,114.2078,112.6483,110.5649,108.0483,105.2033,102.1415,98.9743,95.8060,92.7290,89.8194,87.1354,84.7162,82.5831,80.7417,79.1841,77.8923);
/*!40000 ALTER TABLE `dwd_psr_d_grid_analog_f` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_psr_d_grid_analog_i`
--

DROP TABLE IF EXISTS `dwd_psr_d_grid_analog_i`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_psr_d_grid_analog_i` (
  `id` int NOT NULL AUTO_INCREMENT,
  `equip_type` varchar(255) DEFAULT NULL,
  `psrid` varchar(255) DEFAULT NULL,
  `pos_code` varchar(255) DEFAULT NULL,
  `measuerment_type` varchar(255) DEFAULT NULL,
  `date` varchar(255) DEFAULT NULL,
  `V0000` decimal(20,4) DEFAULT NULL,
  `V0015` decimal(20,4) DEFAULT NULL,
  `V0030` decimal(20,4) DEFAULT NULL,
  `V0045` decimal(20,4) DEFAULT NULL,
  `V0100` decimal(20,4) DEFAULT NULL,
  `V0115` decimal(20,4) DEFAULT NULL,
  `V0130` decimal(20,4) DEFAULT NULL,
  `V0145` decimal(20,4) DEFAULT NULL,
  `V0200` decimal(20,4) DEFAULT NULL,
  `V0215` decimal(20,4) DEFAULT NULL,
  `V0230` decimal(20,4) DEFAULT NULL,
  `V0245` decimal(20,4) DEFAULT NULL,
  `V0300` decimal(20,4) DEFAULT NULL,
  `V0315` decimal(20,4) DEFAULT NULL,
  `V0330` decimal(20,4) DEFAULT NULL,
  `V0345` decimal(20,4) DEFAULT NULL,
  `V0400` decimal(20,4) DEFAULT NULL,
  `V0415` decimal(20,4) DEFAULT NULL,
  `V0430` decimal(20,4) DEFAULT NULL,
  `V0445` decimal(20,4) DEFAULT NULL,
  `V0500` decimal(20,4) DEFAULT NULL,
  `V0515` decimal(20,4) DEFAULT NULL,
  `V0530` decimal(20,4) DEFAULT NULL,
  `V0545` decimal(20,4) DEFAULT NULL,
  `V0600` decimal(20,4) DEFAULT NULL,
  `V0615` decimal(20,4) DEFAULT NULL,
  `V0630` decimal(20,4) DEFAULT NULL,
  `V0645` decimal(20,4) DEFAULT NULL,
  `V0700` decimal(20,4) DEFAULT NULL,
  `V0715` decimal(20,4) DEFAULT NULL,
  `V0730` decimal(20,4) DEFAULT NULL,
  `V0745` decimal(20,4) DEFAULT NULL,
  `V0800` decimal(20,4) DEFAULT NULL,
  `V0815` decimal(20,4) DEFAULT NULL,
  `V0830` decimal(20,4) DEFAULT NULL,
  `V0845` decimal(20,4) DEFAULT NULL,
  `V0900` decimal(20,4) DEFAULT NULL,
  `V0915` decimal(20,4) DEFAULT NULL,
  `V0930` decimal(20,4) DEFAULT NULL,
  `V0945` decimal(20,4) DEFAULT NULL,
  `V1000` decimal(20,4) DEFAULT NULL,
  `V1015` decimal(20,4) DEFAULT NULL,
  `V1030` decimal(20,4) DEFAULT NULL,
  `V1045` decimal(20,4) DEFAULT NULL,
  `V1100` decimal(20,4) DEFAULT NULL,
  `V1115` decimal(20,4) DEFAULT NULL,
  `V1130` decimal(20,4) DEFAULT NULL,
  `V1145` decimal(20,4) DEFAULT NULL,
  `V1200` decimal(20,4) DEFAULT NULL,
  `V1215` decimal(20,4) DEFAULT NULL,
  `V1230` decimal(20,4) DEFAULT NULL,
  `V1245` decimal(20,4) DEFAULT NULL,
  `V1300` decimal(20,4) DEFAULT NULL,
  `V1315` decimal(20,4) DEFAULT NULL,
  `V1330` decimal(20,4) DEFAULT NULL,
  `V1345` decimal(20,4) DEFAULT NULL,
  `V1400` decimal(20,4) DEFAULT NULL,
  `V1415` decimal(20,4) DEFAULT NULL,
  `V1430` decimal(20,4) DEFAULT NULL,
  `V1445` decimal(20,4) DEFAULT NULL,
  `V1500` decimal(20,4) DEFAULT NULL,
  `V1515` decimal(20,4) DEFAULT NULL,
  `V1530` decimal(20,4) DEFAULT NULL,
  `V1545` decimal(20,4) DEFAULT NULL,
  `V1600` decimal(20,4) DEFAULT NULL,
  `V1615` decimal(20,4) DEFAULT NULL,
  `V1630` decimal(20,4) DEFAULT NULL,
  `V1645` decimal(20,4) DEFAULT NULL,
  `V1700` decimal(20,4) DEFAULT NULL,
  `V1715` decimal(20,4) DEFAULT NULL,
  `V1730` decimal(20,4) DEFAULT NULL,
  `V1745` decimal(20,4) DEFAULT NULL,
  `V1800` decimal(20,4) DEFAULT NULL,
  `V1815` decimal(20,4) DEFAULT NULL,
  `V1830` decimal(20,4) DEFAULT NULL,
  `V1845` decimal(20,4) DEFAULT NULL,
  `V1900` decimal(20,4) DEFAULT NULL,
  `V1915` decimal(20,4) DEFAULT NULL,
  `V1930` decimal(20,4) DEFAULT NULL,
  `V1945` decimal(20,4) DEFAULT NULL,
  `V2000` decimal(20,4) DEFAULT NULL,
  `V2015` decimal(20,4) DEFAULT NULL,
  `V2030` decimal(20,4) DEFAULT NULL,
  `V2045` decimal(20,4) DEFAULT NULL,
  `V2100` decimal(20,4) DEFAULT NULL,
  `V2115` decimal(20,4) DEFAULT NULL,
  `V2130` decimal(20,4) DEFAULT NULL,
  `V2145` decimal(20,4) DEFAULT NULL,
  `V2200` decimal(20,4) DEFAULT NULL,
  `V2215` decimal(20,4) DEFAULT NULL,
  `V2230` decimal(20,4) DEFAULT NULL,
  `V2245` decimal(20,4) DEFAULT NULL,
  `V2300` decimal(20,4) DEFAULT NULL,
  `V2315` decimal(20,4) DEFAULT NULL,
  `V2330` decimal(20,4) DEFAULT NULL,
  `V2345` decimal(20,4) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_psr_d_grid_analog_i`
--

LOCK TABLES `dwd_psr_d_grid_analog_i` WRITE;
/*!40000 ALTER TABLE `dwd_psr_d_grid_analog_i` DISABLE KEYS */;
INSERT INTO `dwd_psr_d_grid_analog_i` VALUES (1,'transformer','RES0001','POS0001','TotW','20240315',100.5000,70.3507,70.3512,70.3521,70.3536,70.3561,70.3601,70.3665,70.3766,70.3923,70.4160,70.4514,70.5033,70.5784,70.6849,70.8335,71.0372,71.3116,71.6747,72.1466,72.7487,73.5031,74.4304,75.5485,76.8704,78.4016,80.1383,82.0650,84.1537,86.3625,88.6369,90.9105,93.1084,95.1507,96.9573,98.4529,99.5724,100.2655,100.5001,100.2656,99.5729,98.4538,96.9589,95.1535,93.1132,90.9186,88.6504,86.3846,84.1892,82.1214,80.2262,78.5368,77.0749,75.8531,74.8769,74.1478,73.6650,73.4287,73.4410,73.7070,74.2355,75.0376,76.1254,77.5098,79.1972,81.1868,83.4670,86.0123,88.7815,91.7166,94.7426,97.7701,100.6982,103.4197,105.8276,107.8212,109.3136,110.2374,110.5501,110.2372,109.3132,107.8205,105.8264,103.4176,100.6946,97.7640,94.7325,91.7001,88.7549,85.9700,83.4010,81.0855,79.0439,77.2813,75.7905,74.5541),(2,'transformer','RES0002','POS0002','TotW','20240315',101.0000,70.7007,70.7012,70.7021,70.7036,70.7061,70.7102,70.7166,70.7268,70.7425,70.7663,70.8019,70.8541,70.9295,71.0366,71.1859,71.3907,71.6664,72.0313,72.5055,73.1107,73.8687,74.8007,75.9244,77.2528,78.7917,80.5370,82.4733,84.5724,86.7922,89.0779,91.3628,93.5716,95.6241,97.4397,98.9427,100.0678,100.7643,101.0002,100.7645,100.0683,98.9436,97.4413,95.6269,93.5765,91.3710,89.0914,86.8144,84.6081,82.5299,80.6253,78.9275,77.4583,76.2304,75.2495,74.5167,74.0315,73.7940,73.8063,74.0737,74.6049,75.4109,76.5041,77.8954,79.5912,81.5908,83.8822,86.4402,89.2232,92.1729,95.2140,98.2565,101.1991,103.9342,106.3541,108.3576,109.8574,110.7858,111.1001,110.7857,109.8571,108.3570,106.3529,103.9321,101.1955,98.2504,95.2038,92.1563,89.1965,86.3977,83.8160,81.4889,79.4371,77.6658,76.1675,74.9250),(3,'transformer','RES0003','POS0003','TotW','20240315',101.5000,71.0507,71.0512,71.0521,71.0536,71.0561,71.0602,71.0667,71.0769,71.0927,71.1166,71.1524,71.2049,71.2807,71.3883,71.5383,71.7441,72.0212,72.3879,72.8644,73.4726,74.2344,75.1710,76.3002,77.6353,79.1817,80.9357,82.8816,84.9910,87.2219,89.5189,91.8151,94.0349,96.0975,97.9220,99.4325,100.5632,101.2631,101.5002,101.2633,100.5637,99.4334,97.9237,96.1003,94.0397,91.8233,89.5325,87.2442,85.0269,82.9385,81.0245,79.3182,77.8418,76.6078,75.6220,74.8856,74.3980,74.1594,74.1717,74.4404,74.9742,75.7843,76.8829,78.2810,79.9852,81.9947,84.2975,86.8681,89.6649,92.6292,95.6854,98.7429,101.7001,104.4488,106.8806,108.8941,110.4013,111.3343,111.6501,111.3341,110.4009,108.8934,106.8794,104.4467,101.6965,98.7368,95.6751,92.6125,89.6380,86.8255,84.2309,81.8923,79.8304,78.0503,76.5446,75.2959),(4,'transformer','RES0004','POS0004','TotW','20240315',102.0000,71.4007,71.4012,71.4021,71.4037,71.4062,71.4103,71.4168,71.4270,71.4429,71.4669,71.5029,71.5556,71.6318,71.7399,71.8908,72.0975,72.3760,72.7445,73.2234,73.8345,74.6001,75.5413,76.6761,78.0177,79.5718,81.3344,83.2899,85.4097,87.6515,89.9598,92.2674,94.4981,96.5709,98.4044,99.9224,101.0586,101.7619,102.0002,101.7622,101.0591,99.9233,98.4060,96.5737,94.5030,92.2756,89.9735,87.6739,85.4458,83.3471,81.4236,79.7089,78.2252,76.9852,75.9945,75.2545,74.7645,74.5247,74.5371,74.8071,75.3435,76.1576,77.2616,78.6666,80.3793,82.3986,84.7128,87.2961,90.1066,93.0855,96.1567,99.2294,102.2011,104.9633,107.4071,109.4305,110.9451,111.8827,112.2001,111.8826,110.9447,109.4298,107.4059,104.9612,102.1975,99.2232,96.1465,93.0687,90.0796,87.2532,84.6458,82.2957,80.2236,78.4348,76.9217,75.6668),(5,'transformer','RES0005','POS0005','TotW','20240315',102.5000,71.7507,71.7512,71.7521,71.7537,71.7562,71.7603,71.7669,71.7772,71.7931,71.8173,71.8534,71.9064,71.9830,72.0916,72.2432,72.4509,72.7308,73.1011,73.5823,74.1965,74.9658,75.9116,77.0520,78.4002,79.9618,81.7331,83.6982,85.8284,88.0812,90.4008,92.7197,94.9613,97.0443,98.8868,100.4122,101.5540,102.2608,102.5002,102.2610,101.5544,100.4131,98.8884,97.0471,94.9662,92.7280,90.4146,88.1037,85.8646,83.7556,81.8228,80.0997,78.6087,77.3626,76.3670,75.6234,75.1310,74.8900,74.9025,75.1738,75.7129,76.5309,77.6403,79.0522,80.7733,82.8025,85.1280,87.7240,90.5483,93.5418,96.6281,99.7158,102.7021,105.4778,107.9336,109.9669,111.4890,112.4311,112.7501,112.4310,111.4886,109.9662,107.9324,105.4757,102.6984,99.7096,96.6178,93.5249,90.5212,87.6809,85.0608,82.6991,80.6169,78.8193,77.2987,76.0377),(6,'transformer','RES0006','POS0006','TotW','20240315',103.0000,72.1007,72.1012,72.1022,72.1037,72.1062,72.1104,72.1170,72.1273,72.1433,72.1676,72.2039,72.2572,72.3341,72.4433,72.5956,72.8043,73.0855,73.4577,73.9412,74.5584,75.3315,76.2819,77.4278,78.7826,80.3519,82.1318,84.1064,86.2471,88.5109,90.8418,93.1720,95.4245,97.5177,99.3692,100.9020,102.0493,102.7596,103.0002,102.7598,102.0498,100.9029,99.3708,97.5205,95.4295,93.1803,90.8556,88.5335,86.2835,84.1642,82.2219,80.4904,78.9921,77.7399,76.7396,75.9922,75.4975,75.2553,75.2679,75.5405,76.0822,76.9042,78.0191,79.4379,81.1673,83.2064,85.5433,88.1519,90.9900,93.9981,97.0994,100.2022,103.2031,105.9924,108.4601,110.5033,112.0328,112.9796,113.3001,112.9794,112.0324,110.5026,108.4589,105.9902,103.1994,100.1960,97.0891,93.9812,90.9627,88.1086,85.4757,83.1025,81.0101,79.2038,77.6758,76.4087),(7,'transformer','RES0007','POS0007','TotW','20240315',103.5000,72.4507,72.4512,72.4522,72.4537,72.4563,72.4604,72.4670,72.4774,72.4935,72.5179,72.5544,72.6079,72.6852,72.7949,72.9480,73.1578,73.4403,73.8142,74.3002,74.9203,75.6972,76.6522,77.8037,79.1650,80.7420,82.5305,84.5147,86.6657,88.9405,91.2828,93.6243,95.8878,97.9910,99.8515,101.3918,102.5447,103.2584,103.5002,103.2587,102.5452,101.3927,99.8532,97.9939,95.8927,93.6326,91.2967,88.9633,86.7023,84.5727,82.6210,80.8811,79.3756,78.1173,77.1121,76.3611,75.8640,75.6206,75.6332,75.9072,76.4515,77.2775,78.3978,79.8235,81.5613,83.6103,85.9585,88.5798,91.4317,94.4544,97.5708,100.6886,103.7041,106.5069,108.9866,111.0397,112.5766,113.5280,113.8501,113.5279,112.5763,111.0391,108.9854,106.5047,103.7004,100.6823,97.5604,94.4374,91.4043,88.5363,85.8906,83.5059,81.4034,79.5883,78.0529,76.7796),(8,'transformer','RES0008','POS0008','TotW','20240315',104.0000,72.8007,72.8013,72.8022,72.8037,72.8063,72.8105,72.8171,72.8276,72.8437,72.8682,72.9049,72.9587,73.0364,73.1466,73.3004,73.5112,73.7951,74.1708,74.6591,75.2823,76.0629,77.0225,78.1796,79.5475,81.1320,82.9292,84.9230,87.0844,89.3702,91.7238,94.0766,96.3510,98.4644,100.3339,101.8816,103.0401,103.7573,104.0002,103.7575,103.0406,101.8825,100.3356,98.4673,96.3560,94.0849,91.7377,89.3930,87.1212,84.9813,83.0202,81.2719,79.7591,78.4947,77.4846,76.7300,76.2305,75.9859,75.9986,76.2740,76.8209,77.6509,78.7765,80.2091,81.9553,84.0142,86.3738,89.0077,91.8734,94.9107,98.0421,101.1750,104.2051,107.0214,109.5131,111.5762,113.1205,114.0765,114.4001,114.0763,113.1201,111.5755,109.5119,107.0192,104.2013,101.1687,98.0317,94.8936,91.8459,88.9640,86.3055,83.9094,81.7966,79.9727,78.4299,77.1505),(9,'transformer','RES0009','POS0009','TotW','20240315',104.5000,73.1507,73.1513,73.1522,73.1537,73.1563,73.1605,73.1672,73.1777,73.1939,73.2186,73.2554,73.3094,73.3875,73.4983,73.6528,73.8646,74.1499,74.5274,75.0181,75.6442,76.4286,77.3928,78.5554,79.9299,81.5221,83.3279,85.3313,87.5031,89.7999,92.1647,94.5288,96.8142,98.9378,100.8163,102.3714,103.5355,104.2561,104.5002,104.2563,103.5360,102.3724,100.8180,98.9407,96.8192,94.5373,92.1788,89.8228,87.5400,85.3899,83.4193,81.6626,80.1425,78.8721,77.8571,77.0989,76.5970,76.3513,76.3640,76.6407,77.1902,78.0242,79.1553,80.5947,82.3493,84.4182,86.7891,89.4357,92.3151,95.3670,98.5135,101.6615,104.7060,107.5359,110.0396,112.1126,113.6643,114.6249,114.9501,114.6248,113.6640,112.1119,110.0384,107.5337,104.7023,101.6551,98.5030,95.3498,92.2874,89.3917,86.7205,84.3128,82.1899,80.3572,78.8070,77.5214),(10,'transformer','RES0010','POS0010','TotW','20240315',105.0000,73.5007,73.5013,73.5022,73.5038,73.5064,73.5106,73.5173,73.5278,73.5441,73.5689,73.6059,73.6602,73.7386,73.8499,74.0052,74.2180,74.5047,74.8840,75.3770,76.0061,76.7942,77.7631,78.9313,80.3124,81.9121,83.7266,85.7396,87.9218,90.2295,92.6057,94.9811,97.2775,99.4112,101.2987,102.8613,104.0309,104.7549,105.0002,104.7552,104.0314,102.8622,101.3003,99.4141,97.2825,94.9896,92.6198,90.2526,87.9589,85.7984,83.8184,82.0533,80.5260,79.2495,78.2296,77.4678,76.9635,76.7166,76.7294,77.0074,77.5595,78.3975,79.5340,80.9803,82.7433,84.8221,87.2043,89.8636,92.7568,95.8233,98.9849,102.1479,105.2070,108.0505,110.5661,112.6490,114.2082,115.1734,115.5001,115.1732,114.2078,112.6483,110.5649,108.0483,105.2033,102.1415,98.9743,95.8060,92.7290,89.8194,87.1354,84.7162,82.5831,80.7417,79.1841,77.8923);
/*!40000 ALTER TABLE `dwd_psr_d_grid_analog_i` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_psr_d_grid_analog_p`
--

DROP TABLE IF EXISTS `dwd_psr_d_grid_analog_p`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_psr_d_grid_analog_p` (
  `id` int NOT NULL AUTO_INCREMENT,
  `equip_type` varchar(255) DEFAULT NULL,
  `psrid` varchar(255) DEFAULT NULL,
  `pos_code` varchar(255) DEFAULT NULL,
  `measuerment_type` varchar(255) DEFAULT NULL,
  `date` varchar(255) DEFAULT NULL,
  `V0000` decimal(20,4) DEFAULT NULL,
  `V0015` decimal(20,4) DEFAULT NULL,
  `V0030` decimal(20,4) DEFAULT NULL,
  `V0045` decimal(20,4) DEFAULT NULL,
  `V0100` decimal(20,4) DEFAULT NULL,
  `V0115` decimal(20,4) DEFAULT NULL,
  `V0130` decimal(20,4) DEFAULT NULL,
  `V0145` decimal(20,4) DEFAULT NULL,
  `V0200` decimal(20,4) DEFAULT NULL,
  `V0215` decimal(20,4) DEFAULT NULL,
  `V0230` decimal(20,4) DEFAULT NULL,
  `V0245` decimal(20,4) DEFAULT NULL,
  `V0300` decimal(20,4) DEFAULT NULL,
  `V0315` decimal(20,4) DEFAULT NULL,
  `V0330` decimal(20,4) DEFAULT NULL,
  `V0345` decimal(20,4) DEFAULT NULL,
  `V0400` decimal(20,4) DEFAULT NULL,
  `V0415` decimal(20,4) DEFAULT NULL,
  `V0430` decimal(20,4) DEFAULT NULL,
  `V0445` decimal(20,4) DEFAULT NULL,
  `V0500` decimal(20,4) DEFAULT NULL,
  `V0515` decimal(20,4) DEFAULT NULL,
  `V0530` decimal(20,4) DEFAULT NULL,
  `V0545` decimal(20,4) DEFAULT NULL,
  `V0600` decimal(20,4) DEFAULT NULL,
  `V0615` decimal(20,4) DEFAULT NULL,
  `V0630` decimal(20,4) DEFAULT NULL,
  `V0645` decimal(20,4) DEFAULT NULL,
  `V0700` decimal(20,4) DEFAULT NULL,
  `V0715` decimal(20,4) DEFAULT NULL,
  `V0730` decimal(20,4) DEFAULT NULL,
  `V0745` decimal(20,4) DEFAULT NULL,
  `V0800` decimal(20,4) DEFAULT NULL,
  `V0815` decimal(20,4) DEFAULT NULL,
  `V0830` decimal(20,4) DEFAULT NULL,
  `V0845` decimal(20,4) DEFAULT NULL,
  `V0900` decimal(20,4) DEFAULT NULL,
  `V0915` decimal(20,4) DEFAULT NULL,
  `V0930` decimal(20,4) DEFAULT NULL,
  `V0945` decimal(20,4) DEFAULT NULL,
  `V1000` decimal(20,4) DEFAULT NULL,
  `V1015` decimal(20,4) DEFAULT NULL,
  `V1030` decimal(20,4) DEFAULT NULL,
  `V1045` decimal(20,4) DEFAULT NULL,
  `V1100` decimal(20,4) DEFAULT NULL,
  `V1115` decimal(20,4) DEFAULT NULL,
  `V1130` decimal(20,4) DEFAULT NULL,
  `V1145` decimal(20,4) DEFAULT NULL,
  `V1200` decimal(20,4) DEFAULT NULL,
  `V1215` decimal(20,4) DEFAULT NULL,
  `V1230` decimal(20,4) DEFAULT NULL,
  `V1245` decimal(20,4) DEFAULT NULL,
  `V1300` decimal(20,4) DEFAULT NULL,
  `V1315` decimal(20,4) DEFAULT NULL,
  `V1330` decimal(20,4) DEFAULT NULL,
  `V1345` decimal(20,4) DEFAULT NULL,
  `V1400` decimal(20,4) DEFAULT NULL,
  `V1415` decimal(20,4) DEFAULT NULL,
  `V1430` decimal(20,4) DEFAULT NULL,
  `V1445` decimal(20,4) DEFAULT NULL,
  `V1500` decimal(20,4) DEFAULT NULL,
  `V1515` decimal(20,4) DEFAULT NULL,
  `V1530` decimal(20,4) DEFAULT NULL,
  `V1545` decimal(20,4) DEFAULT NULL,
  `V1600` decimal(20,4) DEFAULT NULL,
  `V1615` decimal(20,4) DEFAULT NULL,
  `V1630` decimal(20,4) DEFAULT NULL,
  `V1645` decimal(20,4) DEFAULT NULL,
  `V1700` decimal(20,4) DEFAULT NULL,
  `V1715` decimal(20,4) DEFAULT NULL,
  `V1730` decimal(20,4) DEFAULT NULL,
  `V1745` decimal(20,4) DEFAULT NULL,
  `V1800` decimal(20,4) DEFAULT NULL,
  `V1815` decimal(20,4) DEFAULT NULL,
  `V1830` decimal(20,4) DEFAULT NULL,
  `V1845` decimal(20,4) DEFAULT NULL,
  `V1900` decimal(20,4) DEFAULT NULL,
  `V1915` decimal(20,4) DEFAULT NULL,
  `V1930` decimal(20,4) DEFAULT NULL,
  `V1945` decimal(20,4) DEFAULT NULL,
  `V2000` decimal(20,4) DEFAULT NULL,
  `V2015` decimal(20,4) DEFAULT NULL,
  `V2030` decimal(20,4) DEFAULT NULL,
  `V2045` decimal(20,4) DEFAULT NULL,
  `V2100` decimal(20,4) DEFAULT NULL,
  `V2115` decimal(20,4) DEFAULT NULL,
  `V2130` decimal(20,4) DEFAULT NULL,
  `V2145` decimal(20,4) DEFAULT NULL,
  `V2200` decimal(20,4) DEFAULT NULL,
  `V2215` decimal(20,4) DEFAULT NULL,
  `V2230` decimal(20,4) DEFAULT NULL,
  `V2245` decimal(20,4) DEFAULT NULL,
  `V2300` decimal(20,4) DEFAULT NULL,
  `V2315` decimal(20,4) DEFAULT NULL,
  `V2330` decimal(20,4) DEFAULT NULL,
  `V2345` decimal(20,4) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_psr_d_grid_analog_p`
--

LOCK TABLES `dwd_psr_d_grid_analog_p` WRITE;
/*!40000 ALTER TABLE `dwd_psr_d_grid_analog_p` DISABLE KEYS */;
INSERT INTO `dwd_psr_d_grid_analog_p` VALUES (1,'transformer','RES0001','POS0001','TotW','20240315',180.0000,126.0012,126.0022,126.0038,126.0065,126.0109,126.0181,126.0296,126.0477,126.0757,126.1181,126.1815,126.2746,126.4091,126.5999,126.8660,127.2309,127.7223,128.3726,129.2177,130.2962,131.6473,133.3081,135.3108,137.6783,140.4208,143.5312,146.9821,150.7230,154.6792,158.7527,162.8248,166.7613,170.4192,173.6549,176.3336,178.3387,179.5799,180.0003,179.5803,178.3395,176.3352,173.6577,170.4242,166.7700,162.8393,158.7768,154.7187,150.7866,147.0830,143.6887,140.6628,138.0445,135.8562,134.1080,132.8020,131.9374,131.5141,131.5361,132.0126,132.9592,134.3957,136.3440,138.8234,141.8457,145.4093,149.4931,154.0519,159.0117,164.2685,169.6883,175.1106,180.3549,185.2294,189.5419,193.1126,195.7855,197.4401,198.0002,197.4398,195.7848,193.1114,189.5398,185.2256,180.3485,175.0997,169.6702,164.2389,158.9640,153.9762,149.3750,145.2277,141.5711,138.4144,135.7441,133.5297),(2,'transformer','RES0002','POS0002','TotW','20240315',260.0000,182.0018,182.0031,182.0054,182.0093,182.0157,182.0262,182.0428,182.0689,182.1093,182.1706,182.2622,182.3967,182.5909,182.8665,183.2509,183.7779,184.4878,185.4271,186.6478,188.2056,190.1572,192.5562,195.4489,198.8687,202.8300,207.3229,212.3075,217.7110,223.4255,229.3094,235.1914,240.8775,246.1611,250.8348,254.7040,257.6003,259.3932,260.0004,259.3937,257.6015,254.7064,250.8389,246.1683,240.8899,235.2124,229.3443,223.4826,217.8029,212.4533,207.5504,203.1797,199.3976,196.2368,193.7115,191.8251,190.5762,189.9649,189.9965,190.6849,192.0521,194.1272,196.9414,200.5228,204.8883,210.0356,215.9345,222.5194,229.6836,237.2768,245.1054,252.9376,260.5126,267.5535,273.7828,278.9404,282.8012,285.1912,286.0003,285.1908,282.8003,278.9387,273.7797,267.5481,260.5033,252.9218,245.0792,237.2340,229.6147,222.4100,215.7639,209.7734,204.4916,199.9318,196.0749,192.8762),(3,'transformer','RES0003','POS0003','TotW','20240315',300.0000,210.0020,210.0036,210.0063,210.0108,210.0182,210.0302,210.0494,210.0795,210.1261,210.1969,210.3026,210.4577,210.6818,210.9998,211.4434,212.0515,212.8705,213.9543,215.3629,217.1604,219.4121,222.1802,225.5179,229.4639,234.0347,239.2187,244.9702,251.2050,257.7986,264.5878,271.3747,277.9356,284.0320,289.4248,293.8893,297.2311,299.2999,300.0004,299.3004,297.2325,293.8919,289.4295,284.0404,277.9499,271.3989,264.6280,257.8645,251.3111,245.1384,239.4812,234.4381,230.0742,226.4270,223.5133,221.3366,219.8957,219.1902,219.2268,220.0210,221.5986,223.9929,227.2400,231.3724,236.4096,242.3488,249.1552,256.7531,265.0195,273.7809,282.8139,291.8511,300.5915,308.7156,315.9032,321.8543,326.3091,329.0668,330.0003,329.0663,326.3081,321.8523,315.8997,308.7093,300.5808,291.8329,282.7837,273.7315,264.9400,256.6270,248.9583,242.0462,235.9518,230.6906,226.2402,222.5495),(4,'transformer','RES0004','POS0004','TotW','20240315',350.0000,245.0024,245.0042,245.0073,245.0126,245.0212,245.0352,245.0576,245.0928,245.1471,245.2297,245.3530,245.5340,245.7954,246.1664,246.6840,247.3934,248.3490,249.6134,251.2567,253.3537,255.9808,259.2102,263.1043,267.7078,273.0404,279.0885,285.7986,293.0725,300.7651,308.6857,316.6038,324.2582,331.3707,337.6622,342.8708,346.7696,349.1832,350.0005,349.1839,346.7713,342.8739,337.6678,331.3804,324.2749,316.6320,308.7327,300.8419,293.1962,285.9948,279.3948,273.5111,268.4199,264.1649,260.7655,258.2261,256.5449,255.7219,255.7645,256.6912,258.5317,261.3250,265.1134,269.9345,275.8112,282.7402,290.6810,299.5453,309.1895,319.4111,329.9495,340.4929,350.6901,360.1682,368.5538,375.4967,380.6940,383.9112,385.0004,383.9107,380.6928,375.4944,368.5496,360.1609,350.6776,340.4717,329.9143,319.3534,309.0967,299.3981,290.4513,282.3873,275.2771,269.1390,263.9469,259.6411),(5,'transformer','RES0005','POS0005','TotW','20240315',90.0000,63.0006,63.0011,63.0019,63.0032,63.0055,63.0091,63.0148,63.0239,63.0378,63.0591,63.0908,63.1373,63.2045,63.2999,63.4330,63.6154,63.8612,64.1863,64.6089,65.1481,65.8236,66.6541,67.6554,68.8392,70.2104,71.7656,73.4911,75.3615,77.3396,79.3763,81.4124,83.3807,85.2096,86.8274,88.1668,89.1693,89.7900,90.0001,89.7901,89.1698,88.1676,86.8289,85.2121,83.3850,81.4197,79.3884,77.3593,75.3933,73.5415,71.8444,70.3314,69.0223,67.9281,67.0540,66.4010,65.9687,65.7571,65.7680,66.0063,66.4796,67.1979,68.1720,69.4117,70.9229,72.7046,74.7466,77.0259,79.5059,82.1343,84.8442,87.5553,90.1775,92.6147,94.7710,96.5563,97.8927,98.7200,99.0001,98.7199,97.8924,96.5557,94.7699,92.6128,90.1742,87.5499,84.8351,82.1195,79.4820,76.9881,74.6875,72.6139,70.7855,69.2072,67.8721,66.7648),(6,'transformer','RES0006','POS0006','TotW','20240315',150.0000,105.0010,105.0018,105.0031,105.0054,105.0091,105.0151,105.0247,105.0398,105.0631,105.0984,105.1513,105.2289,105.3409,105.4999,105.7217,106.0257,106.4353,106.9772,107.6814,108.5802,109.7061,111.0901,112.7590,114.7319,117.0173,119.6094,122.4851,125.6025,128.8993,132.2939,135.6873,138.9678,142.0160,144.7124,146.9446,148.6156,149.6499,150.0002,149.6502,148.6163,146.9460,144.7148,142.0202,138.9750,135.6994,132.3140,128.9322,125.6555,122.5692,119.7406,117.2190,115.0371,113.2135,111.7566,110.6683,109.9478,109.5951,109.6134,110.0105,110.7993,111.9964,113.6200,115.6862,118.2048,121.1744,124.5776,128.3765,132.5098,136.8905,141.4069,145.9255,150.2958,154.3578,157.9516,160.9272,163.1546,164.5334,165.0002,164.5332,163.1540,160.9262,157.9498,154.3547,150.2904,145.9164,141.3918,136.8658,132.4700,128.3135,124.4791,121.0231,117.9759,115.3453,113.1201,111.2747),(7,'transformer','RES0007','POS0007','TotW','20240315',200.0000,140.0014,140.0024,140.0042,140.0072,140.0121,140.0201,140.0329,140.0530,140.0841,140.1312,140.2017,140.3052,140.4545,140.6665,140.9623,141.3677,141.9137,142.6362,143.5752,144.7736,146.2747,148.1201,150.3453,152.9759,156.0231,159.4791,163.3135,167.4700,171.8658,176.3918,180.9164,185.2904,189.3547,192.9498,195.9262,198.1541,199.5332,200.0003,199.5336,198.1550,195.9280,192.9530,189.3602,185.2999,180.9326,176.4187,171.9097,167.5407,163.4256,159.6541,156.2920,153.3828,150.9514,149.0088,147.5578,146.5971,146.1268,146.1512,146.6807,147.7324,149.3286,151.4934,154.2483,157.6064,161.5658,166.1034,171.1687,176.6797,182.5206,188.5426,194.5674,200.3943,205.8104,210.6022,214.5696,217.5394,219.3778,220.0002,219.3776,217.5387,214.5682,210.5998,205.8062,200.3872,194.5553,188.5225,182.4877,176.6267,171.0847,165.9722,161.3641,157.3012,153.7937,150.8268,148.3663),(8,'transformer','RES0008','POS0008','TotW','20240315',300.0000,210.0020,210.0036,210.0063,210.0108,210.0182,210.0302,210.0494,210.0795,210.1261,210.1969,210.3026,210.4577,210.6818,210.9998,211.4434,212.0515,212.8705,213.9543,215.3629,217.1604,219.4121,222.1802,225.5179,229.4639,234.0347,239.2187,244.9702,251.2050,257.7986,264.5878,271.3747,277.9356,284.0320,289.4248,293.8893,297.2311,299.2999,300.0004,299.3004,297.2325,293.8919,289.4295,284.0404,277.9499,271.3989,264.6280,257.8645,251.3111,245.1384,239.4812,234.4381,230.0742,226.4270,223.5133,221.3366,219.8957,219.1902,219.2268,220.0210,221.5986,223.9929,227.2400,231.3724,236.4096,242.3488,249.1552,256.7531,265.0195,273.7809,282.8139,291.8511,300.5915,308.7156,315.9032,321.8543,326.3091,329.0668,330.0003,329.0663,326.3081,321.8523,315.8997,308.7093,300.5808,291.8329,282.7837,273.7315,264.9400,256.6270,248.9583,242.0462,235.9518,230.6906,226.2402,222.5495),(9,'transformer','RES0009','POS0009','TotW','20240315',380.0000,266.0026,266.0046,266.0080,266.0136,266.0230,266.0382,266.0626,266.1008,266.1598,266.2494,266.3832,266.5798,266.8636,267.2664,267.8283,268.5985,269.6360,271.0088,272.7930,275.0698,277.9220,281.4282,285.6561,290.6542,296.4439,303.0104,310.2956,318.1930,326.5449,335.1445,343.7413,352.0517,359.7739,366.6047,372.2598,376.4927,379.1131,380.0006,379.1139,376.4945,372.2631,366.6107,359.7844,352.0699,343.7719,335.1955,326.6284,318.3273,310.5086,303.3429,296.9549,291.4273,286.8076,283.1168,280.3597,278.5345,277.6410,277.6872,278.6933,280.6916,283.7243,287.8374,293.0717,299.4521,306.9751,315.5965,325.2206,335.6914,346.7892,358.2309,369.6780,380.7493,391.0397,400.1441,407.6822,413.3249,416.8179,418.0004,416.8174,413.3236,407.6796,400.1396,391.0318,380.7356,369.6550,358.1927,346.7266,335.5907,325.0608,315.3472,306.5919,298.8723,292.2081,286.5710,281.8960),(10,'transformer','RES0010','POS0010','TotW','20240315',70.0000,49.0005,49.0008,49.0015,49.0025,49.0042,49.0070,49.0115,49.0186,49.0294,49.0459,49.0706,49.1068,49.1591,49.2333,49.3368,49.4787,49.6698,49.9227,50.2513,50.6707,51.1962,51.8420,52.6209,53.5416,54.6081,55.8177,57.1597,58.6145,60.1530,61.7371,63.3208,64.8516,66.2741,67.5324,68.5742,69.3539,69.8366,70.0001,69.8368,69.3543,68.5748,67.5336,66.2761,64.8550,63.3264,61.7465,60.1684,58.6392,57.1990,55.8790,54.7022,53.6840,52.8330,52.1531,51.6452,51.3090,51.1444,51.1529,51.3382,51.7063,52.2650,53.0227,53.9869,55.1622,56.5480,58.1362,59.9091,61.8379,63.8822,65.9899,68.0986,70.1380,72.0336,73.7108,75.0993,76.1388,76.7822,77.0001,76.7821,76.1386,75.0989,73.7099,72.0322,70.1355,68.0943,65.9829,63.8707,61.8193,59.8796,58.0903,56.4775,55.0554,53.8278,52.7894,51.9282);
/*!40000 ALTER TABLE `dwd_psr_d_grid_analog_p` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `dwd_psr_d_grid_analog_u`
--

DROP TABLE IF EXISTS `dwd_psr_d_grid_analog_u`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dwd_psr_d_grid_analog_u` (
  `id` int NOT NULL AUTO_INCREMENT,
  `equip_type` varchar(255) DEFAULT NULL,
  `psrid` varchar(255) DEFAULT NULL,
  `pos_code` varchar(255) DEFAULT NULL,
  `measuerment_type` varchar(255) DEFAULT NULL,
  `date` varchar(255) DEFAULT NULL,
  `V0000` decimal(20,4) DEFAULT NULL,
  `V0015` decimal(20,4) DEFAULT NULL,
  `V0030` decimal(20,4) DEFAULT NULL,
  `V0045` decimal(20,4) DEFAULT NULL,
  `V0100` decimal(20,4) DEFAULT NULL,
  `V0115` decimal(20,4) DEFAULT NULL,
  `V0130` decimal(20,4) DEFAULT NULL,
  `V0145` decimal(20,4) DEFAULT NULL,
  `V0200` decimal(20,4) DEFAULT NULL,
  `V0215` decimal(20,4) DEFAULT NULL,
  `V0230` decimal(20,4) DEFAULT NULL,
  `V0245` decimal(20,4) DEFAULT NULL,
  `V0300` decimal(20,4) DEFAULT NULL,
  `V0315` decimal(20,4) DEFAULT NULL,
  `V0330` decimal(20,4) DEFAULT NULL,
  `V0345` decimal(20,4) DEFAULT NULL,
  `V0400` decimal(20,4) DEFAULT NULL,
  `V0415` decimal(20,4) DEFAULT NULL,
  `V0430` decimal(20,4) DEFAULT NULL,
  `V0445` decimal(20,4) DEFAULT NULL,
  `V0500` decimal(20,4) DEFAULT NULL,
  `V0515` decimal(20,4) DEFAULT NULL,
  `V0530` decimal(20,4) DEFAULT NULL,
  `V0545` decimal(20,4) DEFAULT NULL,
  `V0600` decimal(20,4) DEFAULT NULL,
  `V0615` decimal(20,4) DEFAULT NULL,
  `V0630` decimal(20,4) DEFAULT NULL,
  `V0645` decimal(20,4) DEFAULT NULL,
  `V0700` decimal(20,4) DEFAULT NULL,
  `V0715` decimal(20,4) DEFAULT NULL,
  `V0730` decimal(20,4) DEFAULT NULL,
  `V0745` decimal(20,4) DEFAULT NULL,
  `V0800` decimal(20,4) DEFAULT NULL,
  `V0815` decimal(20,4) DEFAULT NULL,
  `V0830` decimal(20,4) DEFAULT NULL,
  `V0845` decimal(20,4) DEFAULT NULL,
  `V0900` decimal(20,4) DEFAULT NULL,
  `V0915` decimal(20,4) DEFAULT NULL,
  `V0930` decimal(20,4) DEFAULT NULL,
  `V0945` decimal(20,4) DEFAULT NULL,
  `V1000` decimal(20,4) DEFAULT NULL,
  `V1015` decimal(20,4) DEFAULT NULL,
  `V1030` decimal(20,4) DEFAULT NULL,
  `V1045` decimal(20,4) DEFAULT NULL,
  `V1100` decimal(20,4) DEFAULT NULL,
  `V1115` decimal(20,4) DEFAULT NULL,
  `V1130` decimal(20,4) DEFAULT NULL,
  `V1145` decimal(20,4) DEFAULT NULL,
  `V1200` decimal(20,4) DEFAULT NULL,
  `V1215` decimal(20,4) DEFAULT NULL,
  `V1230` decimal(20,4) DEFAULT NULL,
  `V1245` decimal(20,4) DEFAULT NULL,
  `V1300` decimal(20,4) DEFAULT NULL,
  `V1315` decimal(20,4) DEFAULT NULL,
  `V1330` decimal(20,4) DEFAULT NULL,
  `V1345` decimal(20,4) DEFAULT NULL,
  `V1400` decimal(20,4) DEFAULT NULL,
  `V1415` decimal(20,4) DEFAULT NULL,
  `V1430` decimal(20,4) DEFAULT NULL,
  `V1445` decimal(20,4) DEFAULT NULL,
  `V1500` decimal(20,4) DEFAULT NULL,
  `V1515` decimal(20,4) DEFAULT NULL,
  `V1530` decimal(20,4) DEFAULT NULL,
  `V1545` decimal(20,4) DEFAULT NULL,
  `V1600` decimal(20,4) DEFAULT NULL,
  `V1615` decimal(20,4) DEFAULT NULL,
  `V1630` decimal(20,4) DEFAULT NULL,
  `V1645` decimal(20,4) DEFAULT NULL,
  `V1700` decimal(20,4) DEFAULT NULL,
  `V1715` decimal(20,4) DEFAULT NULL,
  `V1730` decimal(20,4) DEFAULT NULL,
  `V1745` decimal(20,4) DEFAULT NULL,
  `V1800` decimal(20,4) DEFAULT NULL,
  `V1815` decimal(20,4) DEFAULT NULL,
  `V1830` decimal(20,4) DEFAULT NULL,
  `V1845` decimal(20,4) DEFAULT NULL,
  `V1900` decimal(20,4) DEFAULT NULL,
  `V1915` decimal(20,4) DEFAULT NULL,
  `V1930` decimal(20,4) DEFAULT NULL,
  `V1945` decimal(20,4) DEFAULT NULL,
  `V2000` decimal(20,4) DEFAULT NULL,
  `V2015` decimal(20,4) DEFAULT NULL,
  `V2030` decimal(20,4) DEFAULT NULL,
  `V2045` decimal(20,4) DEFAULT NULL,
  `V2100` decimal(20,4) DEFAULT NULL,
  `V2115` decimal(20,4) DEFAULT NULL,
  `V2130` decimal(20,4) DEFAULT NULL,
  `V2145` decimal(20,4) DEFAULT NULL,
  `V2200` decimal(20,4) DEFAULT NULL,
  `V2215` decimal(20,4) DEFAULT NULL,
  `V2230` decimal(20,4) DEFAULT NULL,
  `V2245` decimal(20,4) DEFAULT NULL,
  `V2300` decimal(20,4) DEFAULT NULL,
  `V2315` decimal(20,4) DEFAULT NULL,
  `V2330` decimal(20,4) DEFAULT NULL,
  `V2345` decimal(20,4) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `dwd_psr_d_grid_analog_u`
--

LOCK TABLES `dwd_psr_d_grid_analog_u` WRITE;
/*!40000 ALTER TABLE `dwd_psr_d_grid_analog_u` DISABLE KEYS */;
INSERT INTO `dwd_psr_d_grid_analog_u` VALUES (1,'transformer','RES0001','POS0001','TotW','20240315',100.5000,70.3507,70.3512,70.3521,70.3536,70.3561,70.3601,70.3665,70.3766,70.3923,70.4160,70.4514,70.5033,70.5784,70.6849,70.8335,71.0372,71.3116,71.6747,72.1466,72.7487,73.5031,74.4304,75.5485,76.8704,78.4016,80.1383,82.0650,84.1537,86.3625,88.6369,90.9105,93.1084,95.1507,96.9573,98.4529,99.5724,100.2655,100.5001,100.2656,99.5729,98.4538,96.9589,95.1535,93.1132,90.9186,88.6504,86.3846,84.1892,82.1214,80.2262,78.5368,77.0749,75.8531,74.8769,74.1478,73.6650,73.4287,73.4410,73.7070,74.2355,75.0376,76.1254,77.5098,79.1972,81.1868,83.4670,86.0123,88.7815,91.7166,94.7426,97.7701,100.6982,103.4197,105.8276,107.8212,109.3136,110.2374,110.5501,110.2372,109.3132,107.8205,105.8264,103.4176,100.6946,97.7640,94.7325,91.7001,88.7549,85.9700,83.4010,81.0855,79.0439,77.2813,75.7905,74.5541),(2,'transformer','RES0002','POS0002','TotW','20240315',101.0000,70.7007,70.7012,70.7021,70.7036,70.7061,70.7102,70.7166,70.7268,70.7425,70.7663,70.8019,70.8541,70.9295,71.0366,71.1859,71.3907,71.6664,72.0313,72.5055,73.1107,73.8687,74.8007,75.9244,77.2528,78.7917,80.5370,82.4733,84.5724,86.7922,89.0779,91.3628,93.5716,95.6241,97.4397,98.9427,100.0678,100.7643,101.0002,100.7645,100.0683,98.9436,97.4413,95.6269,93.5765,91.3710,89.0914,86.8144,84.6081,82.5299,80.6253,78.9275,77.4583,76.2304,75.2495,74.5167,74.0315,73.7940,73.8063,74.0737,74.6049,75.4109,76.5041,77.8954,79.5912,81.5908,83.8822,86.4402,89.2232,92.1729,95.2140,98.2565,101.1991,103.9342,106.3541,108.3576,109.8574,110.7858,111.1001,110.7857,109.8571,108.3570,106.3529,103.9321,101.1955,98.2504,95.2038,92.1563,89.1965,86.3977,83.8160,81.4889,79.4371,77.6658,76.1675,74.9250),(3,'transformer','RES0003','POS0003','TotW','20240315',101.5000,71.0507,71.0512,71.0521,71.0536,71.0561,71.0602,71.0667,71.0769,71.0927,71.1166,71.1524,71.2049,71.2807,71.3883,71.5383,71.7441,72.0212,72.3879,72.8644,73.4726,74.2344,75.1710,76.3002,77.6353,79.1817,80.9357,82.8816,84.9910,87.2219,89.5189,91.8151,94.0349,96.0975,97.9220,99.4325,100.5632,101.2631,101.5002,101.2633,100.5637,99.4334,97.9237,96.1003,94.0397,91.8233,89.5325,87.2442,85.0269,82.9385,81.0245,79.3182,77.8418,76.6078,75.6220,74.8856,74.3980,74.1594,74.1717,74.4404,74.9742,75.7843,76.8829,78.2810,79.9852,81.9947,84.2975,86.8681,89.6649,92.6292,95.6854,98.7429,101.7001,104.4488,106.8806,108.8941,110.4013,111.3343,111.6501,111.3341,110.4009,108.8934,106.8794,104.4467,101.6965,98.7368,95.6751,92.6125,89.6380,86.8255,84.2309,81.8923,79.8304,78.0503,76.5446,75.2959),(4,'transformer','RES0004','POS0004','TotW','20240315',102.0000,71.4007,71.4012,71.4021,71.4037,71.4062,71.4103,71.4168,71.4270,71.4429,71.4669,71.5029,71.5556,71.6318,71.7399,71.8908,72.0975,72.3760,72.7445,73.2234,73.8345,74.6001,75.5413,76.6761,78.0177,79.5718,81.3344,83.2899,85.4097,87.6515,89.9598,92.2674,94.4981,96.5709,98.4044,99.9224,101.0586,101.7619,102.0002,101.7622,101.0591,99.9233,98.4060,96.5737,94.5030,92.2756,89.9735,87.6739,85.4458,83.3471,81.4236,79.7089,78.2252,76.9852,75.9945,75.2545,74.7645,74.5247,74.5371,74.8071,75.3435,76.1576,77.2616,78.6666,80.3793,82.3986,84.7128,87.2961,90.1066,93.0855,96.1567,99.2294,102.2011,104.9633,107.4071,109.4305,110.9451,111.8827,112.2001,111.8826,110.9447,109.4298,107.4059,104.9612,102.1975,99.2232,96.1465,93.0687,90.0796,87.2532,84.6458,82.2957,80.2236,78.4348,76.9217,75.6668),(5,'transformer','RES0005','POS0005','TotW','20240315',102.5000,71.7507,71.7512,71.7521,71.7537,71.7562,71.7603,71.7669,71.7772,71.7931,71.8173,71.8534,71.9064,71.9830,72.0916,72.2432,72.4509,72.7308,73.1011,73.5823,74.1965,74.9658,75.9116,77.0520,78.4002,79.9618,81.7331,83.6982,85.8284,88.0812,90.4008,92.7197,94.9613,97.0443,98.8868,100.4122,101.5540,102.2608,102.5002,102.2610,101.5544,100.4131,98.8884,97.0471,94.9662,92.7280,90.4146,88.1037,85.8646,83.7556,81.8228,80.0997,78.6087,77.3626,76.3670,75.6234,75.1310,74.8900,74.9025,75.1738,75.7129,76.5309,77.6403,79.0522,80.7733,82.8025,85.1280,87.7240,90.5483,93.5418,96.6281,99.7158,102.7021,105.4778,107.9336,109.9669,111.4890,112.4311,112.7501,112.4310,111.4886,109.9662,107.9324,105.4757,102.6984,99.7096,96.6178,93.5249,90.5212,87.6809,85.0608,82.6991,80.6169,78.8193,77.2987,76.0377),(6,'transformer','RES0006','POS0006','TotW','20240315',103.0000,72.1007,72.1012,72.1022,72.1037,72.1062,72.1104,72.1170,72.1273,72.1433,72.1676,72.2039,72.2572,72.3341,72.4433,72.5956,72.8043,73.0855,73.4577,73.9412,74.5584,75.3315,76.2819,77.4278,78.7826,80.3519,82.1318,84.1064,86.2471,88.5109,90.8418,93.1720,95.4245,97.5177,99.3692,100.9020,102.0493,102.7596,103.0002,102.7598,102.0498,100.9029,99.3708,97.5205,95.4295,93.1803,90.8556,88.5335,86.2835,84.1642,82.2219,80.4904,78.9921,77.7399,76.7396,75.9922,75.4975,75.2553,75.2679,75.5405,76.0822,76.9042,78.0191,79.4379,81.1673,83.2064,85.5433,88.1519,90.9900,93.9981,97.0994,100.2022,103.2031,105.9924,108.4601,110.5033,112.0328,112.9796,113.3001,112.9794,112.0324,110.5026,108.4589,105.9902,103.1994,100.1960,97.0891,93.9812,90.9627,88.1086,85.4757,83.1025,81.0101,79.2038,77.6758,76.4087),(7,'transformer','RES0007','POS0007','TotW','20240315',103.5000,72.4507,72.4512,72.4522,72.4537,72.4563,72.4604,72.4670,72.4774,72.4935,72.5179,72.5544,72.6079,72.6852,72.7949,72.9480,73.1578,73.4403,73.8142,74.3002,74.9203,75.6972,76.6522,77.8037,79.1650,80.7420,82.5305,84.5147,86.6657,88.9405,91.2828,93.6243,95.8878,97.9910,99.8515,101.3918,102.5447,103.2584,103.5002,103.2587,102.5452,101.3927,99.8532,97.9939,95.8927,93.6326,91.2967,88.9633,86.7023,84.5727,82.6210,80.8811,79.3756,78.1173,77.1121,76.3611,75.8640,75.6206,75.6332,75.9072,76.4515,77.2775,78.3978,79.8235,81.5613,83.6103,85.9585,88.5798,91.4317,94.4544,97.5708,100.6886,103.7041,106.5069,108.9866,111.0397,112.5766,113.5280,113.8501,113.5279,112.5763,111.0391,108.9854,106.5047,103.7004,100.6823,97.5604,94.4374,91.4043,88.5363,85.8906,83.5059,81.4034,79.5883,78.0529,76.7796),(8,'transformer','RES0008','POS0008','TotW','20240315',104.0000,72.8007,72.8013,72.8022,72.8037,72.8063,72.8105,72.8171,72.8276,72.8437,72.8682,72.9049,72.9587,73.0364,73.1466,73.3004,73.5112,73.7951,74.1708,74.6591,75.2823,76.0629,77.0225,78.1796,79.5475,81.1320,82.9292,84.9230,87.0844,89.3702,91.7238,94.0766,96.3510,98.4644,100.3339,101.8816,103.0401,103.7573,104.0002,103.7575,103.0406,101.8825,100.3356,98.4673,96.3560,94.0849,91.7377,89.3930,87.1212,84.9813,83.0202,81.2719,79.7591,78.4947,77.4846,76.7300,76.2305,75.9859,75.9986,76.2740,76.8209,77.6509,78.7765,80.2091,81.9553,84.0142,86.3738,89.0077,91.8734,94.9107,98.0421,101.1750,104.2051,107.0214,109.5131,111.5762,113.1205,114.0765,114.4001,114.0763,113.1201,111.5755,109.5119,107.0192,104.2013,101.1687,98.0317,94.8936,91.8459,88.9640,86.3055,83.9094,81.7966,79.9727,78.4299,77.1505),(9,'transformer','RES0009','POS0009','TotW','20240315',104.5000,73.1507,73.1513,73.1522,73.1537,73.1563,73.1605,73.1672,73.1777,73.1939,73.2186,73.2554,73.3094,73.3875,73.4983,73.6528,73.8646,74.1499,74.5274,75.0181,75.6442,76.4286,77.3928,78.5554,79.9299,81.5221,83.3279,85.3313,87.5031,89.7999,92.1647,94.5288,96.8142,98.9378,100.8163,102.3714,103.5355,104.2561,104.5002,104.2563,103.5360,102.3724,100.8180,98.9407,96.8192,94.5373,92.1788,89.8228,87.5400,85.3899,83.4193,81.6626,80.1425,78.8721,77.8571,77.0989,76.5970,76.3513,76.3640,76.6407,77.1902,78.0242,79.1553,80.5947,82.3493,84.4182,86.7891,89.4357,92.3151,95.3670,98.5135,101.6615,104.7060,107.5359,110.0396,112.1126,113.6643,114.6249,114.9501,114.6248,113.6640,112.1119,110.0384,107.5337,104.7023,101.6551,98.5030,95.3498,92.2874,89.3917,86.7205,84.3128,82.1899,80.3572,78.8070,77.5214),(10,'transformer','RES0010','POS0010','TotW','20240315',105.0000,73.5007,73.5013,73.5022,73.5038,73.5064,73.5106,73.5173,73.5278,73.5441,73.5689,73.6059,73.6602,73.7386,73.8499,74.0052,74.2180,74.5047,74.8840,75.3770,76.0061,76.7942,77.7631,78.9313,80.3124,81.9121,83.7266,85.7396,87.9218,90.2295,92.6057,94.9811,97.2775,99.4112,101.2987,102.8613,104.0309,104.7549,105.0002,104.7552,104.0314,102.8622,101.3003,99.4141,97.2825,94.9896,92.6198,90.2526,87.9589,85.7984,83.8184,82.0533,80.5260,79.2495,78.2296,77.4678,76.9635,76.7166,76.7294,77.0074,77.5595,78.3975,79.5340,80.9803,82.7433,84.8221,87.2043,89.8636,92.7568,95.8233,98.9849,102.1479,105.2070,108.0505,110.5661,112.6490,114.2082,115.1734,115.5001,115.1732,114.2078,112.6483,110.5649,108.0483,105.2033,102.1415,98.9743,95.8060,92.7290,89.8194,87.1354,84.7162,82.5831,80.7417,79.1841,77.8923);
/*!40000 ALTER TABLE `dwd_psr_d_grid_analog_u` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-08-04 12:13:50
