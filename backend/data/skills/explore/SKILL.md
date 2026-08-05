---
name: explore
description: 搜索能力包。自由搜索实体、概念、字段，不拼SQL不执行。何时用：搜概念定义、搜实体/字段位置、查数据字典、或其它能力包边界兜底搜字段时。
---

# explore 搜索能力包

## 用途
自由搜索实体、概念、字段，不拼 SQL 不执行。

## 工具清单（按需挑用）
- **search_entities**：搜实体/字段。两种模式：
  - keyword 模式 `{"keyword":"关键词"}`：模糊搜，同时搜 kg_entities(107实体) + kg_source_field_imports(5372源字段)
  - entity_code 模式 `{"entity_code":"表名"}`：精确查数据字典（返回该实体所有属性）
- **search_concepts**：搜概念定义。参数 `{"keyword":"关键词"}`。返回 concepts（id/name/level/description）。

## 硬约束
- entity_code 是逻辑代码，entity_en_name 才是物理表名
- 两个数据源互补：kg_entities 是图谱建模实体，kg_source_field_imports 是源系统字段

## 挑用示例
- 搜概念定义 -> search_concepts
- 搜字段在哪个表 -> search_entities(keyword)
- 查某表数据字典 -> search_entities(entity_code)
- 模糊搜表 -> search_entities(keyword) 从 entities 列表匹配

## 搜索技巧
- 用户给中文字段名（如"客户编号"）-> keyword 搜，同时匹配 field_cn 和 field_en
- 用户给英文字段名（如 cust_no）-> keyword 搜 field_en
- 用户给表名 -> entity_code 精确查
- 搜索无结果 -> 换关键词重试
