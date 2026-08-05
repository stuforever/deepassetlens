---
name: explain-concept
description: 概念解释。用户问概念含义/区别（什么是、是什么意思、和...区别）。查图谱概念定义并组织成自然语言。不拼SQL不执行。
---

# explain-concept 概念解释

## 何时使用
用户问概念定义、含义、区别。典型：什么是用电客户、L2是什么意思、用电客户和发电客户区别。

## 能力包
- **explore**：search_concepts 搜概念、search_entities 搜关联实体
- **locate**：fetch_subgraph 兜底（来源3）

## 要点：三级降级源组织解释
LLM 按以下优先级组织解释，前一级有实质内容就不用后一级：

1. **来源1 概念描述**（search_concepts 返回的 description）
   - description 有实质内容（非 "nan"/空）-> 直接用
   - 为空 -> 进来源2
2. **来源2 实体信息**（search_entities 搜关联实体）
   - 用实体的 entity_name + description 补充
   - 例："用电客户"概念描述为空，但关联实体 dim_cst_elec_cons_cust 有描述
3. **来源3 图谱结构兜底**（fetch_subgraph 拿子图）
   - 从子图的实体列表和属性推断概念含义
   - 例："电能表"概念，从子图实体 dim_cst_meter 和属性（表号、表计类型）推断

## 输出
- 用自然语言组织，不要只输出原始 JSON
- 结构：定义 -> 包含的实体 -> 关键属性 -> 与其他概念的关系（如果有）
- 问"区别"：对比两个概念的组织结构

## 降级
- 概念搜不到 -> 告知"未找到该概念"，建议 explore-graph 浏览结构
- 所有来源都没实质内容 -> 告知"该概念暂无详细定义"，列出相关实体让用户选择
