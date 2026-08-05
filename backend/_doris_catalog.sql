DROP CATALOG IF EXISTS mysql_tupu;
CREATE CATALOG mysql_tupu PROPERTIES (
  "type"="jdbc",
  "user"="root",
  "password"="root",
  "jdbc_url"="jdbc:mysql://host.docker.internal:3306/tupu?yearIsDateType=false&tinyInt1isBit=false&useUnicode=true&characterEncoding=utf-8",
  "driver_url"="http://172.28.80.2:8888/mysql-connector-j-8.0.33.jar",
  "driver_class"="com.mysql.cj.jdbc.Driver"
);
