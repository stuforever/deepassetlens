---
name: explore-graph
description: 浏览图谱结构。用户问结构/层级/包含关系/关系（有哪些、包含什么、下面是什么、有什么实体、什么关系）。查层级树/子图/关系，不拼SQL不执行。
---

# explore-graph 浏览图谱结构

## 何时使用
用户问图谱结构、层级、包含关系、实体关系。典型：有哪些业务域、下面有什么实体、有哪些属性、是什么关系。

## 能力包
- **locate**：fetch_l1_l2_tree（层级树）、fetch_subgraph（子图实体列表）
- **relate**：get_entity_relations（查关系）
- **explore**：search_entities（查属性）

## 要点：4 场景由 LLM 看问句自主挑能力包
1. **问业务域层级**（有哪些业务域/板块/分类）-> locate 的 fetch_l1_l2_tree，按问句范围筛选展示
2. **问实体列表**（XX下面有哪些实体/表）-> locate 定位 L2 + fetch_subgraph，输出实体列表（主表标注）
3. **问实体属性**（XX实体有哪些字段/属性）-> explore 的 search_entities(entity_code)，输出属性列表
4. **问实体关系**（XX和XX是什么关系/关联了什么）-> relate 的 get_entity_relations，输出关系列表（源->关系->目标+JOIN字段）

## 输出格式
- 层级/实体列表：缩进树形或表格
- 属性列表：表格（字段名 | 中文名）
- 关系列表：表格（源表 | 关系 | 目标表 | JOIN字段）
- 不拼 SQL、不执行

## 边界
- 用户问的 L2 不存在 -> explore 的 search_concepts 搜索，建议从层级树选择
- 用户问的实体不存在 -> 告知 + 建议用 find-entity 搜索
- 实体无关联关系 -> 告知"暂无已登记关系"（kg_entity_relations 目前只有13条）
