---
name: trace-lineage
description: 字段/实体血缘追溯。用户问数据来源/血缘/从哪来（cust_no从哪来的、XX表从哪些源表加工、XX字段来源）。查建模信息和关联关系，不拼SQL不执行。
---

# trace-lineage 字段/实体血缘追溯

## 何时使用
用户问数据血缘、来源、加工链路。典型：cust_no 字段从哪个表来的、XX表从哪些源表加工、数据来源是什么。

## 能力包
- **explore**：search_entities（查实体建模信息 + 搜源字段）
- **relate**：get_entity_relations（查关联关系推断上下游）

## 要点：三源组织血缘报告
LLM 先判定追溯对象（字段级/实体级），再按以下三源查信息并组织：

1. **来源1 实体建模信息**（search_entities(entity_code)）
   - kg_entity_modelings 记录 model_table_en（建模目标物理表）和 model_columns
   - 能回答"这个实体对应哪个物理表"
   - 注意：目前只有2条记录，可能查不到
2. **来源2 实体关系**（get_entity_relations）
   - 关系表记录 JOIN 字段，source->target 方向可理解为数据流向
   - 能推断上下游
3. **来源3 源字段表**（search_entities(keyword)）
   - kg_source_field_imports 有 table_en（源表）和 field_en（源字段）
   - 是物理层来源

## 输出格式
```
血缘追溯报告：<实体/字段名>

1. 建模信息
   - 图谱实体：entity_code（entity_name）
   - 建模物理表：model_table_en
   - 建模字段：model_columns 摘要

2. 上游关联
   - 关联实体A（关系名：XX，JOIN字段：XX）
   - 关联实体B（关系名：XX，JOIN字段：XX）

3. 源系统信息
   - 源表：table_en（table_cn）
   - 源字段：field_en（field_cn）
```

## 降级
- kg_entity_modelings 没有记录 -> 告知"该实体暂无建模信息"，用来源2/来源3
- kg_entity_relations 没有关联 -> 告知"该实体暂无关联关系"
- 所有来源都没有 -> 告知"该实体暂无血缘信息"，建议 explore-graph 浏览结构
- 血缘数据有限，结果可能不完整，需如实告知覆盖情况
