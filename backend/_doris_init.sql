-- Doris Docker 初始化脚本
-- 在 Doris 启动后通过 mysql -h 127.0.0.1 -P 9030 -u root 执行

-- 1. 创建数据库
CREATE DATABASE IF NOT EXISTS test_db;

-- 2. 创建表
USE test_db;
DROP TABLE IF EXISTS dim_cst_elec_cons_cust;
CREATE TABLE `dim_cst_elec_cons_cust` (
  `cust_id` varchar(64) NOT NULL,
  `cust_name` varchar(200) NULL,
  `ec_addr` varchar(500) NULL,
  `cust_type` varchar(50) NULL,
  `voltage_level` varchar(20) NULL
) ENGINE=OLAP
DUPLICATE KEY(`cust_id`)
DISTRIBUTED BY HASH(`cust_id`) BUCKETS 1
PROPERTIES (
"replication_allocation" = "tag.location.default: 1",
"storage_medium" = "hdd",
"storage_format" = "V2",
"light_schema_change" = "true"
);

-- 3. 插入数据（10行）
INSERT INTO dim_cst_elec_cons_cust VALUES
('C100001','北京华能电力科技有限公司','北京市海淀区中关村南大街2号','大工业','10kV'),
('C100002','上海浦东供电服务有限公司','上海市浦东新区张江高科技园区科苑路88号','一般工商业','10kV'),
('C100003','广州天河商贸中心有限公司','广州市天河区天河路208号','一般工商业','10kV'),
('C100004','深圳前海智能制造有限公司','深圳市南山区前海路66号','大工业','35kV'),
('C100005','杭州西湖大数据产业园','杭州市西湖区文三路478号','一般工商业','10kV'),
('C100006','成都高新电子制造有限公司','成都市高新区天府大道北段1700号','大工业','35kV'),
('C100007','武汉光谷光电科技有限公司','武汉市东湖高新区光谷大道1号','一般工商业','10kV'),
('C100008','南京江北新材料有限公司','南京市江北新区研创园江淼路88号','大工业','110kV'),
('C100009','西安航天动力机械厂','西安市航天基地航天中路369号','大工业','35kV'),
('C100010','重庆两江新能源汽车有限公司','重庆市两江新区龙兴镇迎龙路19号','大工业','35kV');

-- 4. 创建 Catalog（指向 Windows MySQL，host.docker.internal 从容器访问宿主机）
DROP CATALOG IF EXISTS mysql_tupu;
CREATE CATALOG mysql_tupu PROPERTIES (
  "type"="jdbc",
  "user"="root",
  "password"="root",
  "jdbc_url"="jdbc:mysql://host.docker.internal:3306/tupu?yearIsDateType=false&tinyInt1isBit=false&useUnicode=true&characterEncoding=utf-8",
  "driver_url"="file:///opt/apache-doris/fe/jdbc_drivers/mysql-connector-j-8.0.33.jar",
  "driver_class"="com.mysql.cj.jdbc.Driver"
);

-- 5. 验证
SELECT COUNT(*) AS cnt FROM test_db.dim_cst_elec_cons_cust;
SELECT COUNT(*) AS wbs_cnt FROM mysql_tupu.tupu.biz_work_order;
