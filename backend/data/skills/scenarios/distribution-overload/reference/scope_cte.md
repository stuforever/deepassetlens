# 范围控制 CTE 模板（v3.1 判定单范围校验配套）

判定单须声明**结果范围(result_scope)**与**逻辑来源范围(logical_source_scope)**两级（v3.1 共识第6点）。用户限定客户时（如"只查客户001和003，其他不要检索"），SQL 必须满足：
- **结果范围**：主查询最终结果只含声明客户（WHERE `cust_name IN (...)`）
- **逻辑来源范围**：先锁定目标客户再关联配变/计量点，避免 JOIN 过程带入其他客户数据

`scope_checker` 会从 SQL 提取 `cust_name IN (...)` 的客户名集合，校验其 ⊆ 判定单声明范围（越界即闸门拒绝，原工具不执行）。两种合规写法：

**模板A（结果范围·默认）**--在主查询 WHERE 直接过滤：
```sql
SELECT c.cust_name, i.inst_id, i.dist_sta_id
FROM ⟦能源客户⟧ c
JOIN ⟦计量点⟧ i ON c.cust_id = i.cust_id
WHERE c.cust_name IN ('客户001','客户003')   -- result_scope: 结果只含声明客户
```

**模板B（逻辑来源范围·严格，先锁客户再关联）**--用户限定客户时优先用，CTE 先解析 cust_id 锁定来源：
```sql
WITH 目标客户 AS (                            -- logical_source_scope: 先锁客户, 后续 JOIN 基于此来源
  SELECT cust_id, cust_name, cust_no, ind_cls_name FROM ⟦能源客户⟧
  WHERE cust_name IN ('客户001','客户003')
)
SELECT t.cust_name, t.cust_no, t.ind_cls_name, i.inst_id, i.dist_sta_id
FROM 目标客户 t
JOIN ⟦计量点⟧ i ON t.cust_id = i.cust_id   -- 关联基于已锁定客户, 不带入其他客户
```

> **CTE 必须包含主查询需要的所有列**：不要只 SELECT cust_id, cust_name，主查询用到的列（cust_no, ind_cls_name 等）要一并选出，否则  报 column does not exist。

> 模板B 更严：客户集合在 JOIN 前 即锁定，多表关联不会稀释范围。第1步户变关系用户限定客户时，把 `⟦能源客户⟧ c` 的 `cust_name IN (...)` 条件提到独立 `WITH 目标客户 AS (...)` CTE，再 `JOIN 目标客户 t`，即满足 logical_source_scope 严格级。
