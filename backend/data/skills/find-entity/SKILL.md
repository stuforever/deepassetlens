---
name: find-entity
description: 反查实体和字段。用户找字段或表的位置（叫XX的字段在哪个表、XX表有哪些字段、有没有跟XX相关的字段/表）。搜kg_entities和kg_source_field_imports双数据源，不拼SQL不执行。
---

# find-entity 反查实体和字段

## 何时使用
用户要找字段或表的位置。典型：叫"客户编号"的字段在哪些表、哪些表有地址相关字段、XX表有哪些字段、有没有跟"电话"相关的字段。

## 能力包
- **explore**：search_entities（keyword 模式搜字段+表，entity_code 模式查数据字典）

## 要点：双数据源匹配
search_entities 同时搜两个数据源，LLM 根据返回组织结果：
- **kg_entities**（图谱建模实体，107个）：匹配 entity_code/entity_name/属性名
- **kg_source_field_imports**（源系统字段，5372行）：匹配 table_en/table_cn/field_en/field_cn

两种数据源互补：kg_entities 是图谱建模的实体，kg_source_field_imports 是源系统字段。

## 3 场景由 LLM 看问句自主挑
1. **按字段名搜**（叫XX的字段在哪个表/有没有XX字段）-> search_entities(keyword)，从 fields 列表匹配
2. **按表名查字段**（XX表有哪些字段/数据字典）-> search_entities(entity_code)，返回所有 attributes
3. **模糊搜表**（有没有叫XX的表/哪些表跟XX相关）-> search_entities(keyword)，从 entities 列表匹配

## 输出格式
- 字段搜索结果：表格（表英文名 | 表中文名 | 字段英文名 | 字段中文名）
- 数据字典：表格（字段英文名 | 字段中文名）
- 表搜索结果：表格（表英文名 | 表中文名 | 描述）

## 边界
- 搜索无结果 -> 告知"未找到匹配的字段/表"，建议换关键词
- 搜索结果太多（>20条）-> 提示用户缩小范围
- 表名不在 kg_entities -> 尝试在 kg_source_field_imports 的 table_en 搜
